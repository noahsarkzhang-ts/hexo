---
title: Flink 系列：Process Function
date: 2022-09-17 15:03:27
tags:
- process function
- keyed state
- timer
categories:
- Flink
---

这篇文章简要介绍 Flink `Process Function`. 

<!-- more -->

## 概述

`ProcessFunction` 是 Flink low-level 流处理操作方法，通过它可以做如下操作：
- 访问事件；
- 获取 Keyed Stream 流状态；
- 操作基于事件时间或处理时间的定时器 (only on keyed stream).

`ProcessFunction` 可以像 `FlatMapFunction` 一样访问 Keyed 流状态及定时器，这在收到事件之后对事件进行处理。

通过 `RuntimeContext` 可以定义和访问 Keyed state 数据。

定时器允许应用根据事件时间或处理时间作出响应，可以通过 `TimerService` 注册或删除定时器，参数为一个代表某个点的时间戳。随着事件时间或处理时间的推进，会触发回调函数 `onTimer`, 在该函数中可以定义相应的处理逻辑。定时器作用范围是基于 key,即每个 key 上都会有定义自己的定时器。另外，在事件时间语义下，定时器的触发基于事件时间，如果后续没有收到事件，有可能不会触发执行。

## 代码实例

在下面的实例中，使用 `KeyedProcessFunction` 模拟了一个简单的 `Session Window` 的功能，它统计用户一次会话的请求数，一个用户持续 60 S 没有收到请求，则表明会话结束，结束会话并输出统计结果。它包含如下的功能：
- `UserRequest` 对象代表了用户的请求数据，包括用户 id, 操作类型及时间戳三个字段；
- `CountWithTimestamp` 对象状态变量，包括用户 id, 统计次数及上次访问的时间戳三个字段；
- 根据用户 id 进行分组(key by)，每一个 key 都持有一个 `CountWithTimestamp` 状态变量；
- 在 `KeyedProcessFunction` 中实现计数及更新上次访问的时间戳的功能；
- 如果某个 key 持续 60S 没有收到请求数据，则说明 Session 结束，输出统计结果。

```java
public class ProcessFunctionJob {

    public static void main(String[] args) throws Exception {
        // Sets up the execution environment, which is the main entry point
        // to building Flink applications.
        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // 设置并行度为 1
        env.setParallelism(1);

        // 设置 Watermark 生成间隔为 200MS
        env.getConfig().setAutoWatermarkInterval(200L);

        // 用parameter tool工具从程序启动参数中提取配置项，如 --host 192.168.1.1 --port 9000
        // 使用 nc -lk 9000 监听请求并发送数据
        final ParameterTool parameterTool = ParameterTool.fromArgs(args);
        String host = parameterTool.get("host");
        int port = parameterTool.getInt("port");

        // 获取 socket 文本流
        final DataStreamSource<String> dataStreamSource = env.socketTextStream(host, port);

        // 转换数据格式
        final SingleOutputStreamOperator<UserRequest> dataStream = dataStreamSource.map(line -> {
            String[] fields = line.split(",");

            return new UserRequest(fields[0], fields[1], Long.parseLong(fields[2]));
        });

        // 定义 watermarkStrategy
        final WatermarkStrategy<UserRequest> watermarkStrategy = WatermarkStrategy
                .<UserRequest>forBoundedOutOfOrderness(Duration.ofSeconds(0))
                .withTimestampAssigner((event, timestamp) -> event.getTimestamp() * 1000);
        final SingleOutputStreamOperator<UserRequest> eventDataStream = dataStream.assignTimestampsAndWatermarks(watermarkStrategy);

        final SingleOutputStreamOperator<CountWithTimestamp> processStream = eventDataStream.keyBy(userRequest -> userRequest.getUserId())
                .process(new RequestCountFunction());

        processStream.print("request-count");

        // Execute program, beginning computation.
        env.execute("Flink Process Function Job");
    }

    private static class RequestCountFunction extends KeyedProcessFunction<String, UserRequest, CountWithTimestamp> {

        // 申明状态变量，存储用户请求次数
        private ValueState<CountWithTimestamp> state;

        @Override
        public void open(Configuration parameters) throws Exception {
            // 定义状态变量
            state = getRuntimeContext().getState(new ValueStateDescriptor<>("mystate", CountWithTimestamp.class));
        }

        @Override
        public void processElement(UserRequest userRequest, Context context, Collector<CountWithTimestamp> collector) throws Exception {

            // 获取状态变量
            CountWithTimestamp current = state.value();

            // 如果状态变量为空则初始化
            if (current == null) {
                current = new CountWithTimestamp();
                current.setUserId(userRequest.getUserId());
            }

            // 计数
            current.setCount(current.getCount() + 1);

            // 设置上次的修改时间
            current.setLastModified(context.timestamp());

            // 更新状态变量
            state.update(current);

            // 注册定时器
            context.timerService().registerEventTimeTimer(current.getLastModified() + 60000);

        }

        @Override
        public void onTimer(long timestamp, OnTimerContext ctx, Collector<CountWithTimestamp> out) throws Exception {
            CountWithTimestamp result = state.value();

            // 如果两次操作之间间隔 60S, 则输出
            if (timestamp >= (result.getLastModified() + 60000)) {
                out.collect(result);
            }
        }
    }
}
```

**[工程代码:https://github.com/noahsarkzhang-ts/flink-lab/tree/main/flink-processfunction-training)](https://github.com/noahsarkzhang-ts/flink-lab/tree/main/flink-processfunction-training)**

**参考：**

----
[1]:https://nightlies.apache.org/flink/flink-docs-release-1.15/zh/docs/dev/datastream/operators/process_function/

[1. Flink Process Function][1]