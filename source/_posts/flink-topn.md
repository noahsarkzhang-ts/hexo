---
title: Flink 系列：TopN 计算流程
date: 2022-09-24 15:00:41
updated: 2022-09-24 15:00:41
tags:
- flink
- aggregate function
- process window function
- keyed process function
categories:
- Flink
---


这篇文章简要介绍 Flink TopN 计算流程。 

<!-- more -->

## 概述

TopN 实现的功能用一句话来描述： 得到一个统计周期内排名前几位（TopN）的数据。它包括两个重要的步骤：
1. 对数据进行分组，得到统计周期内（如 1分钟）一个分组（一个元素）的聚合结果（如1分钟内的平均值）；
2. 归并所有的分组，并对分组进行排序，输出排名前几位的数据。

## 代码实例

在这个实例中，采集传感器的数据，统计每一个传感器 15S 内的平均值，并根据平均值，获取排名前 3位的传感器，操作步骤如下：
1. 采集传感器数据数据；
2. 根据传感器 id 进行分组，并计算出每一个传感器每 15S 的温度平均值；
3. 将得到的数据按照时间窗口进行分组，将同个窗口内的传感器数据存入状态列表；
4. 待所有的传感器数据都加入到列表后，对列表进行排序，输出前几位的数据。

代码如下所示：

```java
public class TopNStreamJob {

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

        // 使用 AggrgationFunction + ProcessWindowFunction 求平均值
        SingleOutputStreamOperator<TopSensor> avgProcessWindow = windowStream.aggregate(new MyAggrgationFunction(), new MyProcessWindowFunction());

        // 按照 windowEnd 进行分组，将相同窗口内的传感器进行排序，将输出 topN.
        final SingleOutputStreamOperator<String> topStream = avgProcessWindow.keyBy(topSensor -> topSensor.getWinEnd()).process(new TopSensorKeyedProcessFunction());

        // 输出迟到数据
        avgProcessWindow.getSideOutput(outputTag).print("late");

        // 输出TOP 数据
        topStream.print("top");

        // Execute program, beginning computation.
        env.execute("Flink TopN Job");
    }

    /**
     * 构造 TopSensor 类，获取窗口值
     */
    private static class MyProcessWindowFunction
            extends ProcessWindowFunction<Double, TopSensor, String, TimeWindow> {

        @Override
        public void process(String key,
                            Context context,
                            Iterable<Double> avgReadings,
                            Collector<TopSensor> out) {
            Double avgValue = avgReadings.iterator().next();

            out.collect(new TopSensor(key, context.window().getStart(), context.window().getEnd(), avgValue));
        }
    }

    /**
     * AggregateFunction, 增量计算平均值
     */
    private static class MyAggrgationFunction implements AggregateFunction<SensorReading, AvgValue, Double> {

        @Override
        public AvgValue createAccumulator() {
            return new AvgValue();
        }

        @Override
        public AvgValue add(SensorReading value, AvgValue accumulator) {

            accumulator.aggregate(value.getTemperature());

            return accumulator;
        }

        @Override
        public Double getResult(AvgValue accumulator) {
            return accumulator.avg();
        }

        @Override
        public AvgValue merge(AvgValue a, AvgValue b) {
            return a.merge(b);
        }
    }

    /**
     * 计算 TopN 值
     * 1. 使用状态变量存储传感器平均值；
     * 2. 使用定时器触发计算，触发器时间为：windowEnd + 1, 比当前窗口大 1 MS,
     *  从而保证所有的传感器数据已经加入到状态列表中。
     */
    private static class TopSensorKeyedProcessFunction extends KeyedProcessFunction<Long, TopSensor, String> {

        // 状态变量，存储传感器列表。
        private ListState<TopSensor> sensorList;

        @Override
        public void open(Configuration parameters) throws Exception {

            sensorList = getRuntimeContext().getListState(new ListStateDescriptor<TopSensor>("sensor-state", TopSensor.class));
        }

        @Override
        public void processElement(TopSensor value, Context ctx, Collector<String> out) throws Exception {
            sensorList.add(value);

            ctx.timerService().registerEventTimeTimer(value.getWinEnd() + 1);
        }

        @Override
        public void onTimer(long timestamp, OnTimerContext ctx, Collector<String> out) throws Exception {

            List<TopSensor> topList = new ArrayList<>();

            for (TopSensor sensor : sensorList.get()) {
                topList.add(sensor);
            }

            sensorList.clear();

            topList.sort(new Comparator<TopSensor>() {
                @Override
                public int compare(TopSensor o1, TopSensor o2) {
                    return o2.getAvgVlaue().compareTo(o1.getAvgVlaue());
                }
            });

            // 将排名信息格式化成 String, 便于打印
            StringBuilder result = new StringBuilder();
            result.append("\n====================================\n");
            result.append("时间: ").append(timestamp - 1).append("\n");


            for (int i = 0; i < topList.size() - 1; i++) {

                if (i >= 3) {
                    break;
                }

                TopSensor sensor = topList.get(i);

                result.append("No").append(i).append(":")
                        .append("  sensorId=").append(sensor.getId())
                        .append("  平均值=").append(sensor.getAvgVlaue())
                        .append("\n");
            }
            result.append("====================================\n\n");

            out.collect(result.toString());
        }
    }
}
```

相关类说明：
- `AvgValue`, 代表传感器平均值对象，用于增量累加计算；
- `SensorReading`, 代表传感器对象，包括传感器 id, 时间戳及温度值；
- `TopSensor`, 代表开窗计算之后的传感器对象，包括传感器 id, 窗口开始时间，窗口结束时间及平均值。

在 `TopSensorKeyedProcessFunction` 对象中，使用一个列表状态对象 `ListState` 来存储 `TopSensor` 对象，什么时候触发排序操作呢？需要等待所有的传感器数据开窗计算结束。在这里，使用了一个技巧，定义了时间戳为 `WindowEnd + 1` 的定时器，它在开窗计算之后执行，从而保证在所有的数据已经加入到 `ListState` 之后再执行排序操作。

## 测试输出

输入以下测试数据：
```text
sensor_1,1663041360,20.0
sensor_2,1663041360,30.0
sensor_3,1663041361,10.0
sensor_4,1663041361,36.0
sensor_1,1663041365,30.0
sensor_3,1663041365,30.0
sensor_1,1663041366,10.0
sensor_1,1663041377,10.0
sensor_1,1663041378,20.0

```

结果如下：
```text
top> 
====================================
时间: 1663041375000
No0:  sensorId=sensor_4  平均值=36.0
No1:  sensorId=sensor_2  平均值=30.0
No2:  sensorId=sensor_1  平均值=20.0
====================================
```

结果分析：
窗口为 [1663041360000,1663041375000), 因为在代码中设置了 `forBoundedOutOfOrderness(Duration.ofSeconds(2))`, 可以接受 2S 的乱序数据，即 `Watermark` 推迟 2S. 在该窗口下，`sensor_1,1663041377,10.0` 时间戳为 `1663041377` S, 比窗口结束时间大 2S, 触发窗口计算，但此时未触发定时器执行，因为定时器时间比窗口时间大 1MS。收到 `sensor_1,1663041378,20.0` 后才真正定时器执行，得到 Top3 数据。 


**[工程代码:https://github.com/noahsarkzhang-ts/flink-lab/tree/main/flink-topn-training)](https://github.com/noahsarkzhang-ts/flink-lab/tree/main/flink-topn-training)**
