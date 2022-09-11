---
title: Flink 系列：Window 分桶
date: 2022-09-10 17:41:14
tags:
- window
- 分桶
- ReduceFunction
- AggregateFunction
- 增量聚合
categories:
- Flink
---


这篇文章简要介绍 Flink `Window` 分桶。 

<!-- more -->

## 概述

Flink Window 一句话描述就是对数据进行切割分桶，方便后续业务的计算，以下面的图示为例。

![flink-window](/images/flink/flink-window.jpg "flink-window")

**数据流程：**
1. 数据源：传感器每 1S 采集上报的数据，数据格式为：`<传感器id,时间戳(ms),温度>`；
2. 数据分组: 数据按照`传感器id`进行分组，执行该操作之后，为分为三股逻辑数据流，每一股流包含了一个`传感器id`所有的数据；
3. 分桶：将一个`传感器id`上的数据按照每 5S 进行切割分桶，如 0~4S,5-9S. 一个桶中包含了同一个时间段内的所有数据；
4. 窗口函数：数据分桶之后，可以对其应用窗口函数，如从每个桶中取最小值、最大值、平均值等等。

后文将使用一个实例来模拟这个过程。

## 窗口 API

### 基本结构

Flink 窗口有两种类型：keyed streams 和 non-keyed streams. 它们的区别在于是否需要对数据进行分组（keyBy 操作），不进行 keyBy 操作是将所有数据作为一个逻辑上的 Stream, 所有的窗口计算会被同一个 task 完成，也就是 parallelism 为 1. 在调用方式上，keyed streams 要调用 keyBy(...) 后再调用 window(...) ， 而 non-keyed streams 只用直接调用 windowAll(...)。

**Keyed Windows**
```java
stream
       .keyBy(...)               <-  仅 keyed 窗口需要
       .window(...)              <-  必填项："assigner"
      [.trigger(...)]            <-  可选项："trigger" (省略则使用默认 trigger)
      [.evictor(...)]            <-  可选项："evictor" (省略则不使用 evictor)
      [.allowedLateness(...)]    <-  可选项："lateness" (省略则为 0)
      [.sideOutputLateData(...)] <-  可选项："output tag" (省略则不对迟到数据使用 side output)
       .reduce/aggregate/apply()      <-  必填项："function"
      [.getSideOutput(...)]      <-  可选项："output tag"

```

**Non-Keyed Windows**
```java
stream
       .windowAll(...)           <-  必填项："assigner"
      [.trigger(...)]            <-  可选项："trigger" (else default trigger)
      [.evictor(...)]            <-  可选项："evictor" (else no evictor)
      [.allowedLateness(...)]    <-  可选项："lateness" (else zero)
      [.sideOutputLateData(...)] <-  可选项："output tag" (else no side output for late data)
       .reduce/aggregate/apply()      <-  必填项："function"
      [.getSideOutput(...)]      <-  可选项："output tag"
```

上面方括号（[…]）中的命令是可选的。也就是说，Flink 允许自定义多样化的窗口操作来满足需求。

### 窗口生命周期

简单来说，一个窗口在第一个属于它的元素到达时就会被创建，然后在时间（event 或 processing time） 超过窗口的“结束时间戳 + 用户定义的 allowed lateness ” 时被完全删除。Flink 仅保证删除基于时间的窗口，其他类型的窗口不做保证， 比如全局窗口。 例如，对于一个基于 event time 且范围互不重合（滚动）的窗口策略， 如果窗口设置的时长为五分钟、可容忍的迟到时间（allowed lateness）为 1 分钟， 那么第一个元素落入 12:00 至 12:05 这个区间时，Flink 就会为这个区间创建一个新的窗口。 当 watermark 越过 12:06 时，这个窗口将被摧毁。

另外，每个窗口会设置自己的 Trigger 和 function (ProcessWindowFunction、ReduceFunction、或 AggregateFunction）。该 function 决定如何计算窗口中的内容， 而 Trigger 决定何时窗口中的数据可以被 function 计算。 Trigger 的触发（fire）条件可能是“当窗口中有多于 4 条数据”或“当 watermark 越过窗口的结束时间”等。 Trigger 还可以在 window 被创建后、删除前的这段时间内定义何时清理（purge）窗口中的数据。 这里的数据仅指窗口内的元素，不包括窗口的 meta data。也就是说，窗口在 purge 后仍然可以加入新的数据。

除此之外，也可以指定一个 Evictor （详见 Evictors），在 trigger 触发之后，Evictor 可以在窗口函数的前后删除数据。

### keyBy

keyBy 定义了是否对数据进行分组操作，类似于 SQL 语句中的 `GROUP BY` 操作，可以指定多个字段进行分组操作。

### Window assigner 

Window assigner 定义了 stream 中的元素如何被分发到各个窗口。 在 window(...)（用于 keyed streams）或 windowAll(...) （用于 non-keyed streams）中可以指定一个 WindowAssigner。 WindowAssigner 负责将 stream 中的每个数据分发到一个或多个窗口中。 Flink 为最常用的情况提供了一些定义好的 window assigner，也就是 tumbling windows、 sliding windows、 session windows 和 global windows。另外，也可以继承 WindowAssigner 类来实现自定义的 window assigner。 所有内置的 window assigner（除了 global window）都是基于时间分发数据的，processing time 或 event time 均可。 

基于时间的窗口用 start timestamp（包含）和 end timestamp（不包含）描述窗口的大小。 在代码中，Flink 处理基于时间的窗口使用的是 TimeWindow， 它有查询开始和结束 timestamp 以及返回窗口所能储存的最大 timestamp 的方法 maxTimestamp()。

### 窗口函数（Window Functions）

窗口函数（Window Functions）定义了 Triggers 触发计算后，如何计算每个窗口中的数据。

窗口函数有三种：ReduceFunction、AggregateFunction 或 ProcessWindowFunction。 前两者执行起来更高效，因为 Flink 可以在每条数据到达窗口后进行增量聚合（incrementally aggregate）。 而 ProcessWindowFunction 会得到能够遍历当前窗口内所有数据的 Iterable，以及关于这个窗口的 meta-information。

使用 ProcessWindowFunction 的窗口转换操作没有其他两种函数高效，因为 Flink 在窗口触发前必须缓存里面的所有数据。 ProcessWindowFunction 可以与 ReduceFunction 或 AggregateFunction 合并来提高效率。 这样做既可以增量聚合窗口内的数据，又可以从 ProcessWindowFunction 接收窗口的 metadata。

**ReduceFunction**

ReduceFunction 指定两条输入数据如何合并起来产生一条输出数据，输入和输出数据的类型必须相同。 Flink 使用 ReduceFunction 对窗口中的数据进行增量聚合。

```java
DataStream<Tuple2<String, Long>> input = ...;

input
    .keyBy(<key selector>)
    .window(<window assigner>)
    .reduce(new ReduceFunction<Tuple2<String, Long>>() {
      public Tuple2<String, Long> reduce(Tuple2<String, Long> v1, Tuple2<String, Long> v2) {
        return new Tuple2<>(v1.f0, v1.f1 + v2.f1);
      }
    });
```

上面的例子是对窗口内元组的第二个属性求和。

**AggregateFunction**

ReduceFunction 是 AggregateFunction 的特殊情况。 AggregateFunction 接收三个类型：输入数据的类型(IN)、累加器的类型（ACC）和输出数据的类型（OUT）。 输入数据的类型是输入流的元素类型，AggregateFunction 接口有如下几个方法： 把每一条元素加进累加器、创建初始累加器、合并两个累加器、从累加器中提取输出（OUT 类型）。

与 ReduceFunction 相同，Flink 会在输入数据到达窗口时直接进行增量聚合。

```java
/**
 * The accumulator is used to keep a running sum and a count. The {@code getResult} method
 * computes the average.
 */
private static class AverageAggregate
    implements AggregateFunction<Tuple2<String, Long>, Tuple2<Long, Long>, Double> {
  @Override
  public Tuple2<Long, Long> createAccumulator() {
    return new Tuple2<>(0L, 0L);
  }

  @Override
  public Tuple2<Long, Long> add(Tuple2<String, Long> value, Tuple2<Long, Long> accumulator) {
    return new Tuple2<>(accumulator.f0 + value.f1, accumulator.f1 + 1L);
  }

  @Override
  public Double getResult(Tuple2<Long, Long> accumulator) {
    return ((double) accumulator.f0) / accumulator.f1;
  }

  @Override
  public Tuple2<Long, Long> merge(Tuple2<Long, Long> a, Tuple2<Long, Long> b) {
    return new Tuple2<>(a.f0 + b.f0, a.f1 + b.f1);
  }
}

DataStream<Tuple2<String, Long>> input = ...;

input
    .keyBy(<key selector>)
    .window(<window assigner>)
    .aggregate(new AverageAggregate());
```

上例计算了窗口内所有元素第二个属性的平均值。

**ProcessWindowFunction**

ProcessWindowFunction 有能获取包含窗口内所有元素的 Iterable， 以及用来获取时间和状态信息的 Context 对象，比其他窗口函数更加灵活。 ProcessWindowFunction 的灵活性是以性能和资源消耗为代价的， 因为窗口中的数据无法被增量聚合，而需要在窗口触发前缓存所有数据。

```java
ataStream<Tuple2<String, Long>> input = ...;

input
  .keyBy(t -> t.f0)
  .window(TumblingEventTimeWindows.of(Time.minutes(5)))
  .process(new MyProcessWindowFunction());

/* ... */

public class MyProcessWindowFunction 
    extends ProcessWindowFunction<Tuple2<String, Long>, String, String, TimeWindow> {

  @Override
  public void process(String key, Context context, Iterable<Tuple2<String, Long>> input, Collector<String> out) {
    long count = 0;
    for (Tuple2<String, Long> in: input) {
      count++;
    }
    out.collect("Window: " + context.window() + "count: " + count);
  }
}

```

上例使用 ProcessWindowFunction 对窗口中的元素计数，并且将窗口本身的信息一同输出。

**增量聚合的 ProcessWindowFunction**

ProcessWindowFunction 可以与 ReduceFunction 或 AggregateFunction 搭配使用， 使其能够在数据到达窗口的时候进行增量聚合。当窗口关闭时，ProcessWindowFunction 将会得到聚合的结果。 这样它就可以增量聚合窗口的元素并且从 ProcessWindowFunction` 中获得窗口的元数据。

1. 使用 ReduceFunction 增量聚合

```java
DataStream<SensorReading> input = ...;

input
  .keyBy(<key selector>)
  .window(<window assigner>)
  .reduce(new MyReduceFunction(), new MyProcessWindowFunction());

// Function definitions

private static class MyReduceFunction implements ReduceFunction<SensorReading> {

  public SensorReading reduce(SensorReading r1, SensorReading r2) {
      return r1.value() > r2.value() ? r2 : r1;
  }
}

private static class MyProcessWindowFunction
    extends ProcessWindowFunction<SensorReading, Tuple2<Long, SensorReading>, String, TimeWindow> {

  public void process(String key,
                    Context context,
                    Iterable<SensorReading> minReadings,
                    Collector<Tuple2<Long, SensorReading>> out) {
      SensorReading min = minReadings.iterator().next();
      out.collect(new Tuple2<Long, SensorReading>(context.window().getStart(), min));
  }
}

```

上例组合 ReduceFunction 与 ProcessWindowFunction，返回窗口中的最小元素和窗口的开始时间

2. 使用 AggregateFunction 增量聚合

```java
DataStream<Tuple2<String, Long>> input = ...;

input
  .keyBy(<key selector>)
  .window(<window assigner>)
  .aggregate(new AverageAggregate(), new MyProcessWindowFunction());

// Function definitions

/**
 * The accumulator is used to keep a running sum and a count. The {@code getResult} method
 * computes the average.
 */
private static class AverageAggregate
    implements AggregateFunction<Tuple2<String, Long>, Tuple2<Long, Long>, Double> {
  @Override
  public Tuple2<Long, Long> createAccumulator() {
    return new Tuple2<>(0L, 0L);
  }

  @Override
  public Tuple2<Long, Long> add(Tuple2<String, Long> value, Tuple2<Long, Long> accumulator) {
    return new Tuple2<>(accumulator.f0 + value.f1, accumulator.f1 + 1L);
  }

  @Override
  public Double getResult(Tuple2<Long, Long> accumulator) {
    return ((double) accumulator.f0) / accumulator.f1;
  }

  @Override
  public Tuple2<Long, Long> merge(Tuple2<Long, Long> a, Tuple2<Long, Long> b) {
    return new Tuple2<>(a.f0 + b.f0, a.f1 + b.f1);
  }
}

private static class MyProcessWindowFunction
    extends ProcessWindowFunction<Double, Tuple2<String, Double>, String, TimeWindow> {

  public void process(String key,
                    Context context,
                    Iterable<Double> averages,
                    Collector<Tuple2<String, Double>> out) {
      Double average = averages.iterator().next();
      out.collect(new Tuple2<>(key, average));
  }
}
```
上例组合 AggregateFunction 与 ProcessWindowFunction，计算平均值并与窗口对应的 key 一同输出。

### Triggers

Trigger 决定了一个窗口（由 window assigner 定义）何时可以被 window function 处理。 每个 WindowAssigner 都有一个默认的 Trigger。 如果默认 trigger 无法满足需求，可以在 trigger(...) 调用中指定自定义的 trigger。

Trigger 接口提供了五个方法来响应不同的事件：
- onElement(): 该方法在每个元素被加入窗口时调用；
- onEventTime(): 该方法在注册的 event-time timer 触发时调用；
- onProcessingTime(): 该方法在注册的 processing-time timer 触发时调用；
- onMerge(): 该方法与有状态的 trigger 相关。该方法会在两个窗口合并时， 将窗口对应 trigger 的状态进行合并，比如使用会话窗口时；
- clear()：该方法处理在对应窗口被移除时所需的逻辑。

### Evictors 

Flink 的窗口模型允许在 WindowAssigner 和 Trigger 之外指定可选的 Evictor。 通过 evictor(...) 方法传入 Evictor。 Evictor 可以在 trigger 触发后、调用窗口函数之前或之后从窗口中删除元素。 

### Allowed Lateness 

在使用 event-time 窗口时，数据可能会迟到，即 Flink 用来追踪 event-time 进展的 watermark 已经越过了窗口结束的 timestamp 后，数据才到达。默认情况下，watermark 一旦越过窗口结束的 timestamp，迟到的数据就会被直接丢弃。 但是 Flink 允许指定窗口算子最大的 allowed lateness。 Allowed lateness 定义了一个元素可以在迟到多长时间的情况下不被丢弃，这个参数默认是 0。 在 watermark 超过窗口末端、到达窗口末端加上 allowed lateness 之前的这段时间内到达的元素， 依旧会被加入窗口。取决于窗口的 trigger，一个迟到但没有被丢弃的元素可能会再次触发窗口，比如 EventTimeTrigger。

为了实现这个功能，Flink 会将窗口状态保存到 allowed lateness 超时才会将窗口及其状态删除。默认情况下，allowed lateness 被设为 0。即 watermark 之后到达的元素会被丢弃。

使用 GlobalWindows 时，没有数据会被视作迟到，因为全局窗口的结束 timestamp 是 Long.MAX_VALUE。

## 代码实例

### 数据源

自定义一个数据源，每秒为 10 个传感器生成随机数据。

```java
public class MySensorSource implements SourceFunction<SensorReading> {

    /**
     * 定义一个标识位，用来控制数据的产生
     */
    private boolean running = true;

    // 设置10个传感器的初始温度
    private HashMap<String, Double> sensorTempMap = new HashMap<>();

    public MySensorSource() {

        // 定义一个随机数发生器
        Random random = new Random();

        for (int i = 0; i < 10; i++) {
            sensorTempMap.put("sensor_" + (i + 1), 60 + random.nextGaussian() * 20);
        }

    }

    @Override
    public void run(SourceContext<SensorReading> sourceContext) throws Exception {

        Random random = new Random();

        while (running) {

            sensorTempMap.entrySet().stream().forEach(entry -> {
                String sensorId = entry.getKey();

                // 在当前温度基础上随机波动
                Double newTemp = entry.getValue() + random.nextGaussian();
                sensorTempMap.put(sensorId, newTemp);

                sourceContext.collect(new SensorReading(sensorId, System.currentTimeMillis(),newTemp));


            });

            // 睡眠 1S
            TimeUnit.SECONDS.sleep(1);
        }

    }

    @Override
    public void cancel() {
        running = false;
    }
}
```

### 程序骨架

程序的处理流程如下：
1. 设置流处理执行环境；
2. 设置事件时间语义，将 Watermark 间隔时间设置为 200 MS;
3. 设置定定义 Source；
4. 定义 WatermarkStrategy, Watermark 设置为单调自增模式，没有乱序，且设置 Timestamp 的提取方式；
5. 定义分组且设置窗口为滚动事件窗口，窗口大小为 5S;
6. 使用 ReduceFunction 求最小值，输出格式为：`SensorReading`;
7. 使用 ReduceFunction + ProcessWindowFunction 求最小值，输出格式为：`<Key,WindowEnd,SensorReading>`；
8. 输出执行结果。

```java
public class FlinkWindowTrainingJob {

    public static void main(String[] args) throws Exception {
        // 设置流处理执行环境
        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // 设置事件时间语义
        env.getConfig().setAutoWatermarkInterval(200L);
        env.setParallelism(1);

        // 1. 设置 Source
        DataStream<SensorReading> dataStream = env.addSource(new MySensorSource());

        // 2. 定义 WatermarkStrategy
        WatermarkStrategy<SensorReading> watermarkStrategy = WatermarkStrategy.<SensorReading>forMonotonousTimestamps()
                .withTimestampAssigner((event, timestamp) -> event.getTimestamp());

        final SingleOutputStreamOperator<SensorReading> eventDataStream = dataStream.assignTimestampsAndWatermarks(watermarkStrategy);

        // 3. 使用滚动事件窗口，窗口大小为 5S
        WindowedStream<SensorReading, String, TimeWindow> windowStream = eventDataStream.keyBy(sensorReading -> sensorReading.getId())
                .window(TumblingEventTimeWindows.of(Time.seconds(5)));

        // 4. 使用 ReduceFunction 求最小值
        final SingleOutputStreamOperator<SensorReading> minTempStream = windowStream
                .reduce(new ReduceFunction<SensorReading>() {
                    @Override
                    public SensorReading reduce(SensorReading v1, SensorReading v2) throws Exception {
                        final SensorReading sensorReading = v1.getTemperature().compareTo(v2.getTemperature()) > 0 ? v2 : v1;
                        return sensorReading;
                    }
                });

        // 5. 输出 ReduceFunction 最小值
        minTempStream.print("minTemp-reduce");

        // 6. 使用 ReduceFunction + ProcessWindowFunction 求最小值
        SingleOutputStreamOperator<Tuple3<String, Long, SensorReading>> reduceProcessWindow = windowStream.reduce(new ReduceFunction<SensorReading>() {
            @Override
            public SensorReading reduce(SensorReading v1, SensorReading v2) throws Exception {
                final SensorReading sensorReading = v1.getTemperature().compareTo(v2.getTemperature()) > 0 ? v2 : v1;
                return sensorReading;
            }
        }, new MyProcessWindowFunction());

        // 7. 输出 ReduceFunction + ProcessWindowFunction 最小值，输出格式为<key,timestamp,minValue>
        reduceProcessWindow.print("minTemp-reduce-process");

        // 8. 执行程序
        env.execute("Flink Window Training");
    }

    private static class MyProcessWindowFunction
            extends ProcessWindowFunction<SensorReading, Tuple3<String, Long, SensorReading>, String, TimeWindow> {

        @Override
        public void process(String key,
                            Context context,
                            Iterable<SensorReading> minReadings,
                            Collector<Tuple3<String, Long, SensorReading>> out) {
            SensorReading min = minReadings.iterator().next();
            out.collect(new Tuple3<String, Long, SensorReading>(key, context.window().getStart(), min));
        }
    }

}
```

## 窗口的起始值

窗口是一个左闭右开的区间范围 `[windonStart, windowStart + size)`, 它的取值包括 `windonStart`, 但不包括 `windowEnd(windowStart + size)`. 只要确定了 `windonStart`, 便可确定窗口时间范围。

以 `TumblingEventTimeWindows` 为例，`windonStart` 计算公式如下所示：

```java
@PublicEvolving
public class TumblingEventTimeWindows extends WindowAssigner<Object, TimeWindow> {
    private static final long serialVersionUID = 1L;

    private final long size;

    private final long globalOffset;

    private Long staggerOffset = null;

    private final WindowStagger windowStagger;

    protected TumblingEventTimeWindows(long size, long offset, WindowStagger windowStagger) {
        if (Math.abs(offset) >= size) {
            throw new IllegalArgumentException(
                    "TumblingEventTimeWindows parameters must satisfy abs(offset) < size");
        }

        this.size = size;
        this.globalOffset = offset;
        this.windowStagger = windowStagger;
    }

    @Override
    public Collection<TimeWindow> assignWindows(
            Object element, long timestamp, WindowAssignerContext context) {
        if (timestamp > Long.MIN_VALUE) {
            if (staggerOffset == null) {
                staggerOffset =
                        windowStagger.getStaggerOffset(context.getCurrentProcessingTime(), size);
            }
            // Long.MIN_VALUE is currently assigned when no timestamp is present
            long start =
                    TimeWindow.getWindowStartWithOffset(
                            timestamp, (globalOffset + staggerOffset) % size, size);
            return Collections.singletonList(new TimeWindow(start, start + size));
        } else {
            throw new RuntimeException(
                    "Record has Long.MIN_VALUE timestamp (= no timestamp marker). "
                            + "Is the time characteristic set to 'ProcessingTime', or did you forget to call "
                            + "'DataStream.assignTimestampsAndWatermarks(...)'?");
        }
    }

    /**
     * Creates a new {@code TumblingEventTimeWindows} {@link WindowAssigner} that assigns elements
     * to time windows based on the element timestamp.
     *
     * @param size The size of the generated windows.
     * @return The time policy.
     */
    public static TumblingEventTimeWindows of(Time size) {
        return new TumblingEventTimeWindows(size.toMilliseconds(), 0, WindowStagger.ALIGNED);
    }
	
    ...
}

```

关键的计算逻辑如下：

```java
// TumblingEventTimeWindows
@Override
public Collection<TimeWindow> assignWindows(
        Object element, long timestamp, WindowAssignerContext context) {
    if (timestamp > Long.MIN_VALUE) {
        if (staggerOffset == null) {
            staggerOffset =
                    windowStagger.getStaggerOffset(context.getCurrentProcessingTime(), size);
        }
        // Long.MIN_VALUE is currently assigned when no timestamp is present
        long start =
                TimeWindow.getWindowStartWithOffset(
                        timestamp, (globalOffset + staggerOffset) % size, size);
        return Collections.singletonList(new TimeWindow(start, start + size));
    } else {
        throw new RuntimeException(
                "Record has Long.MIN_VALUE timestamp (= no timestamp marker). "
                        + "Is the time characteristic set to 'ProcessingTime', or did you forget to call "
                        + "'DataStream.assignTimestampsAndWatermarks(...)'?");
    }
}

// TimeWindow
public static long getWindowStartWithOffset(long timestamp, long offset, long windowSize) {
    final long remainder = (timestamp - offset) % windowSize;
    // handle both positive and negative cases
    if (remainder < 0) {
        return timestamp - (remainder + windowSize);
    } else {
        return timestamp - remainder;
    }
}
```

一句话总结 `windonStart`: 最靠近小于 `timestamp` 且为 windowSize 整数倍的数值。计算逻辑如下：

```java
// 1. 当前时间戳减去余数，保证可以得到 windowSize 整数倍；
windonStart = timestamp - remainder; 
// 1.1 余数为负时，需要加上窗口大小，保证 windonStart 要小于当前 timestamp;
windonStart = timestamp - (remainder + windowSize);

// 2. 余数的计算公式, 使用 timestamp 对 windowSize 取余。
// offset 可以调整偏移的位置
remainder = (timestamp - offset) % windowSize;

// 3. offset 的计算公式，它由两个参数决定：globalOffset, staggerOffset; 
// 3.1 globalOffset 等同于用户传入的 offset 参数；
// 3.2 staggerOffset 由 WindowStagger 类型决定，默认类型为 WindowStagger.ALIGNED, staggerOffset 值为 0; 
offset = (globalOffset + staggerOffset) % size;

```

以 `TumblingEventTimeWindows.of(Time.seconds(5))` 为例：

```java
globalOffset = 0; 
staggerOffset = 0; 
windowSize = 5;

windonStart = timestamp - (timestamp % 5)

```

即 `windonStart` 为最靠近小于 `timestamp` 且为 5 整数倍的数值。

**[工程代码:https://github.com/noahsarkzhang-ts/flink-lab/tree/main/flink-window-training)](https://github.com/noahsarkzhang-ts/flink-lab/tree/main/flink-window-training)**

**参考：**

----
[1]:https://nightlies.apache.org/flink/flink-docs-release-1.15/zh/docs/dev/datastream/operators/windows/

[1. Flink 窗口][1]
