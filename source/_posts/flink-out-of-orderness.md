---
title: Flink 系列：乱序处理
date: 2022-09-17 13:00:14
tags:
- 乱序
- watermark
- 侧输出流
categories:
- Flink
---

这篇文章简要介绍在事件时间语义下 Flink 对乱序事件的处理逻辑。 

<!-- more -->

## 概述

在 Flink 中可以使用三种方式对乱序数据进行处理：
- 设置 `Watermark` 延迟时间，可以延迟 `Watermark` 的产生；
- 设置 `Window` 延迟关闭时间；
- 设置侧输出流，将数据输出到侧输出流，业务根据需要进行处理。

## Watermark 延迟时间

在 `WatermarkStrategy` 中将事件时间设置为乱序时间语义，并设置最大的乱序时间，如 2S.

```java
final WatermarkStrategy<SensorReading> watermarkStrategy = WatermarkStrategy
        .<SensorReading>forBoundedOutOfOrderness(Duration.ofSeconds(2))
        .withTimestampAssigner((event, timestamp) -> event.getTimestamp() * 1000);
```

**一句话描述：** `Watermark` = 事件时间 + 乱序时间，即将 `Watermark` 推迟产生设定的乱序时间。 

以窗口 [1663041345,1663041360) 为例，单位为秒。如果事件时间是有序的话，在事件时间为 `1663041360` 时，产生的 `Watermark`跟事件时间是一致的，也是 `1663041360`。假定事件时间是乱序的且乱序时间为 2S, 则 `Watermark` 的值会比事件时间晚 2S, 即在事件时间为 `1663041362` 时，才会产生时间为 `1663041360` 的 `Watermark`. 

## Window 延迟关闭时间

在 `window` 操作之后，可以设置窗口的延迟时间，如 `allowedLateness(Time.minutes(1))` 延迟关闭 1 分钟。

```java
OutputTag<SensorReading> outputTag = new OutputTag<SensorReading>("late") {
};
final WindowedStream<SensorReading, String, TimeWindow> windowStream = eventDataStream.keyBy(sensorReading -> sensorReading.getId())
        .window(TumblingEventTimeWindows.of(Time.seconds(15)))
        .allowedLateness(Time.minutes(1))  // 1 设置窗口延迟关闭时间
        .sideOutputLateData(outputTag);    // 2 设置侧输出流
```

再以窗口 [1663041345,1663041360) 为例，设置了 1 分钟的延迟时间之后，在 `1663041360` 处不会关闭窗口，要顺延 1 分钟之后，即 `1663041420` 处关闭，如果 `Watermark` 也设置了延迟时间，则还要顺延 `Watermark` 延迟时间。

**事件最终的延迟时间为：** Watermark 延迟时间 + Window 延迟关闭时间。

## 侧输出流

如果事件时间的乱序程度超过了指定的 `Watermark 延迟时间 + Window 延迟关闭时间`，则还有最后一步拯救的办法，即将事件输出的侧输出流，供业务后续处理。其代码如上文所示。

## 代码

下例代码包括了上文讲到的三种处理乱序的办法，它的主要功能是模拟采集传感器的温度值，统计每一个传感器每 5S 产生的最小值。

```java
public class OutOfOrdernessJob {

    public static void main(String[] args) throws Exception {
        // Sets up the execution environment, which is the main entry point
        // to building Flink applications.
        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // 设置 Watermark 生成间隔为 200MS
        env.getConfig().setAutoWatermarkInterval(200L);

        // 设置并行度为 1
        env.setParallelism(1);

        // 用parameter tool工具从程序启动参数中提取配置项，如 --host 192.168.1.1 --port 9000
        // 使用 nc -lk 9000 监听请求并发送数据
        final ParameterTool parameterTool = ParameterTool.fromArgs(args);
        String host = parameterTool.get("host");
        int port = parameterTool.getInt("port");

        // 获取 socket 文本流
        final DataStreamSource<String> dataStreamSource = env.socketTextStream(host, port);

        // 转换数据格式
        final SingleOutputStreamOperator<SensorReading> dataStream = dataStreamSource.map(line -> {
            String[] fields = line.split(",");

            return new SensorReading(fields[0], Long.parseLong(fields[1]), Double.parseDouble(fields[2]));
        });

        // 定义 watermarkStrategy
        final WatermarkStrategy<SensorReading> watermarkStrategy = WatermarkStrategy
                .<SensorReading>forBoundedOutOfOrderness(Duration.ofSeconds(2))
                .withTimestampAssigner((event, timestamp) -> event.getTimestamp() * 1000);

        final SingleOutputStreamOperator<SensorReading> eventDataStream = dataStream.assignTimestampsAndWatermarks(watermarkStrategy);

        // 分组，开窗及处理迟到数据
        OutputTag<SensorReading> outputTag = new OutputTag<SensorReading>("late") {
        };
        final WindowedStream<SensorReading, String, TimeWindow> windowStream = eventDataStream.keyBy(sensorReading -> sensorReading.getId())
                .window(TumblingEventTimeWindows.of(Time.seconds(15)))
                .allowedLateness(Time.minutes(1))
                .sideOutputLateData(outputTag);

        // 使用 ReduceFunction + ProcessWindowFunction 求最小值
        SingleOutputStreamOperator<Tuple5<String, Long, Long, Long, SensorReading>> reduceProcessWindow = windowStream.reduce(
                new MyReduceFunction(), new MyProcessWindowFunction());

        // 输出 ReduceFunction + ProcessWindowFunction 最小值，输出格式为<key,winStart,winEnd,minValue>
        reduceProcessWindow.print("minTemp-reduce-process");
        reduceProcessWindow.getSideOutput(outputTag).print("late");

        // Execute program, beginning computation.
        env.execute("Flink OutOfOrderness Job");
    }

    private static class MyProcessWindowFunction
            extends ProcessWindowFunction<SensorReading, Tuple5<String, Long, Long, Long, SensorReading>, String, TimeWindow> {

        @Override
        public void process(String key,
                            Context context,
                            Iterable<SensorReading> minReadings,
                            Collector<Tuple5<String, Long, Long, Long, SensorReading>> out) {
            SensorReading min = minReadings.iterator().next();
            out.collect(new Tuple5<>(key, context.window().getStart(), context.window().getEnd(), context.currentWatermark(), min));
        }
    }

    private static class MyReduceFunction implements ReduceFunction<SensorReading> {

        @Override
        public SensorReading reduce(SensorReading v1, SensorReading v2) throws Exception {
            final SensorReading sensorReading = v1.getTemperature().compareTo(v2.getTemperature()) > 0 ? v2 : v1;
            return sensorReading;
        }
    }
}
```

## 测试场景

### `Watermark` 延迟 2S

录入 `sensor_1,1663041358,35.8` 数据，`1663041358` 对应的窗口为 [1663041345,1663041360), 窗口的边界值计算见 `Flink 系列：Window 分桶`。依次录入 `sensor_2,1663041360,15.4; sensor_1,1663041361,24.0`，这时没有触发窗口计算，当录入 `sensor_1,1663041362,20.5` 时触发了计算，输出了结果。

```bash
minTemp-reduce-process> (sensor_1,1663041345000,1663041360000,1663041359999,SensorReading{id='sensor_1', timestamp=1663041358, temperature=35.8})
```
其中 `1663041345000,1663041360000` 两个值分别是窗口的边界值。sensor_1 最小值是 35.8. 在后面输入了一个比它小的值 24.0, 为什么不是 24.0? 因为 24.0 对应的时间时间为 `1663041361`,它属于下一个窗口。

### `Window` 延迟关闭 1 分钟

设置了 `Window` 延迟关闭 1 分钟，这时窗口 [1663041345,1663041360) 未关闭，仍然可以接收迟到的数据，如 `sensor_1,1663041356,20.5`, 它会更新最小值，如下所示：

```bash
minTemp-reduce-process> (sensor_1,1663041345000,1663041360000,1663041359999,SensorReading{id='sensor_1', timestamp=1663041358, temperature=35.8})
minTemp-reduce-process> (sensor_1,1663041345000,1663041360000,1663041359999,SensorReading{id='sensor_1', timestamp=1663041356, temperature=20.5})
```

继续推进事件时间，当收到事件 `sensor_1,1663041422,19.5` 时，[1663041345,1663041360) 窗口关闭。

**说明：** 1663041422 = 1663041360 + 60 + 2, 1663041360 为窗口的最大值, 60 为 `Window` 延迟关闭时间，2 为 `Watermark` 延迟时间。

### 侧输出流

当 [1663041345,1663041360) 窗口关闭之后，再收到属于该窗口的事件，如 `sensor_1,1663041355,14.5`, 这时它会输出到侧输出流，如下所示：

```bash
late> SensorReading{id='sensor_1', timestamp=1663041355, temperature=14.5}
```

**[工程代码:https://github.com/noahsarkzhang-ts/flink-lab/tree/main/flink-outoforderness-training)](https://github.com/noahsarkzhang-ts/flink-lab/tree/main/flink-outoforderness-training)**
