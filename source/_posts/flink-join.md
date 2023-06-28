---
title: Flink 系列：Connect
date: 2022-09-17 20:56:58
updated: 2022-09-17 20:56:58
tags:
- connect
- join
- KeyedCoProcessFunction
- CoProcessFunction 
categories:
- Flink
---

这篇文章简要介绍 Flink 多流 Connect 操作。 

<!-- more -->

## 概述

要实现多流 low-level joing 操作，应用可以使用 `CoProcessFunction` 或 `KeyedCoProcessFunction`. 这些类使用 `processElement1(...) `,`processElement2(...)` 方法来处理不同的输入流，每股流的事件都会传给相应的方法来处理。

可以使用以下的模式来实现 log-level join 操作：
- 为每一个输入（每个流）创建一个 state 对象；
- 收到事件之后更新对应的流状态；
- 两股流中的事件都收到后，聚合状态变量并输出结果；
- 可以为等待另一股流事件设置一个超时时间，如果在指定时间内未收到事件，则执行超时逻辑。

## Watermark 推进

在多流操作中，`Watermark` 推进如下图所示：

![watermark](/images/flink/watermark.png "watermark")

一个算子有多个上游算子（或多个输入多股流），其 `Watermark` 从多个上游算子输入的 `Watermark`中选择最小值，如果其中一股流或一个算子没有输入，则会阻塞算子的执行。

## 代码实例

在下面的例子中，采集出租车乘坐事件(TaxiRide) 和费用事件(TaxiFare), 根据 `rideId` 执行 join 操作。如果其中一个事件等待另一个事件超时 60S, 则执行超时逻辑，将事件输出到侧输出流中，供后续业务处理。

实例的主要逻辑如下：
- `TaxiRide` 代表了乘坐事件，包括乘坐 id (riderId), 事件类型及事件时间三个字段；
- `TaxiFare` 代表了乘坐费用，包括乘坐 id (riderId), 费用及事件时间三个字段；
- `RideFare` 代表了结果对象，包含了 `TaxiRide` 和 `TaxiFare` 两个对象；
- `TaxiRide`与 `TaxiFare` 通过 乘坐 id (riderId) 进行关联；
- 为每一个乘坐事件设置一个状态变量，存储 `TaxiRide` 对象；
- 为每一个费用事件设置一个状态变量，存储 `RideFare` 对象；
- 收到其中一个事件之后，设置一个超时时间，等待另外一个事件，如果在超时时间范围内收到另外一个事件，则聚合内容输出到主流，如果超时未收到事件，则将事件输出到侧输出流中。

代码如下：

```java
public class JoinDataStreamJob {

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
        String host1 = parameterTool.get("host1");
        int port1 = parameterTool.getInt("port1");

        // 获取 socket 文本流
        final DataStreamSource<String> rideSource = env.socketTextStream(host1, port1);

        // 转换数据格式
        final SingleOutputStreamOperator<TaxiRide> rideDataStream = rideSource.map(line -> {
            String[] fields = line.split(",");

            return new TaxiRide(fields[0], fields[1], Long.parseLong(fields[2]));
        });

        // 定义 watermarkStrategy
        final WatermarkStrategy<TaxiRide> riderWatermarkStrategy = WatermarkStrategy
                .<TaxiRide>forBoundedOutOfOrderness(Duration.ofSeconds(0))
                .withTimestampAssigner((event, timestamp) -> event.getTimestamp() * 1000)
                .withIdleness(Duration.ofSeconds(1));

        final SingleOutputStreamOperator<TaxiRide> rideEventDataStream = rideDataStream.assignTimestampsAndWatermarks(riderWatermarkStrategy);


        String host2 = parameterTool.get("host2");
        int port2 = parameterTool.getInt("port2");

        // 获取 socket 文本流
        final DataStreamSource<String> fareSource = env.socketTextStream(host2, port2);

        // 转换数据格式
        final SingleOutputStreamOperator<TaxiFare> fareDataStream = fareSource.map(line -> {
            String[] fields = line.split(",");

            return new TaxiFare(fields[0], Double.parseDouble(fields[1]), Long.parseLong(fields[2]));
        });

        // 定义 watermarkStrategy
        final WatermarkStrategy<TaxiFare> fareWatermarkStrategy = WatermarkStrategy
                .<TaxiFare>forBoundedOutOfOrderness(Duration.ofSeconds(0))
                .withTimestampAssigner((event, timestamp) -> event.getTimestamp() * 1000)
                .withIdleness(Duration.ofSeconds(1));

        final SingleOutputStreamOperator<TaxiFare> fareEventDataStream = fareDataStream.assignTimestampsAndWatermarks(fareWatermarkStrategy);

        final KeyedStream<TaxiRide, String> taxiRideStringKeyedStream = rideEventDataStream.keyBy(taxiRide -> taxiRide.getRideId());
        final KeyedStream<TaxiFare, String> taxiFareStringKeyedStream = fareEventDataStream.keyBy(taxiFare -> taxiFare.getRideId());

        final SingleOutputStreamOperator<RideFare> rideFareStream = taxiRideStringKeyedStream.connect(taxiFareStringKeyedStream)
                .process(new RiderFareProcessMapFuntion());
        rideFareStream.print("ride-fare");

        OutputTag<RideFare> outputTag = new OutputTag<RideFare>("ride-fare") {
        };
        final DataStream<RideFare> sideOutputStream = rideFareStream.getSideOutput(outputTag);
        sideOutputStream.print("side-output");


        // Execute program, beginning computation.
        env.execute("Flink Join Training Job");
    }

    private static class RiderFareProcessMapFuntion extends KeyedCoProcessFunction<String, TaxiRide, TaxiFare, RideFare> {

        // 超时时间为 60 S
        private static final int TIMET_OUT_MS = 60 * 1000;

        // 存放 TaxiRide 状态
        private ValueState<TaxiRide> rideState;

        // 存放 TaxiFare 状态
        private ValueState<TaxiFare> fareState;

        // 存放超时时间戳
        private ValueState<Long> timeoutState;

        @Override
        public void open(Configuration parameters) throws Exception {
            rideState = getRuntimeContext().getState(new ValueStateDescriptor<TaxiRide>("ride", TaxiRide.class));
            fareState = getRuntimeContext().getState(new ValueStateDescriptor<TaxiFare>("fare", TaxiFare.class));
            timeoutState = getRuntimeContext().getState(new ValueStateDescriptor<Long>("timeout", Long.class));
        }

        @Override
        public void processElement1(TaxiRide value, Context ctx, Collector<RideFare> out) throws Exception {
            TaxiFare fare = fareState.value();
            if (fare != null) {
                fareState.clear();
                out.collect(new RideFare(value, fare));

                Long timeout = timeoutState.value();

                ctx.timerService().deleteEventTimeTimer(timeout);
                System.out.println("del Timer:" + timeout);

                timeoutState.clear();

            } else {
                rideState.update(value);

                Long timeout = ctx.timestamp() + TIMET_OUT_MS;
                timeoutState.update(timeout);

                ctx.timerService().registerEventTimeTimer(timeout);
                System.out.println("reg Timer:" + timeout);
            }

        }

        @Override
        public void processElement2(TaxiFare value, Context ctx, Collector<RideFare> out) throws Exception {
            TaxiRide ride = rideState.value();
            if (ride != null) {
                rideState.clear();
                out.collect(new RideFare(ride, value));

                Long timeout = timeoutState.value();

                ctx.timerService().deleteEventTimeTimer(timeout);
                System.out.println("del Timer:" + timeout);

                timeoutState.clear();

            } else {
                fareState.update(value);

                Long timeout = ctx.timestamp() + TIMET_OUT_MS;
                timeoutState.update(timeout);

                ctx.timerService().registerEventTimeTimer(timeout);
                System.out.println("reg Timer:" + timeout);
            }
        }

        @Override
        public void onTimer(long timestamp, OnTimerContext ctx, Collector<RideFare> out) throws Exception {

            System.out.println("onTimer");

            TaxiRide ride = rideState.value();
            TaxiFare fare = fareState.value();

            RideFare rideFare = new RideFare();
            rideFare.setFare(fare);
            rideFare.setRide(ride);

            OutputTag<RideFare> outputTag = new OutputTag<RideFare>("ride-fare") {
            };
            ctx.output(outputTag, rideFare);

            rideState.clear();
            fareState.clear();
            timeoutState.clear();
        }
    }
}
```

**[工程代码:https://github.com/noahsarkzhang-ts/flink-lab/tree/main/flink-join-training)](https://github.com/noahsarkzhang-ts/flink-lab/tree/main/flink-join-training)**