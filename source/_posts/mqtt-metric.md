---
title: Mqtt 系列：Metric
date: 2023-03-05 12:42:00
updated: 2023-03-05 12:42:00
tags:
- metric
categories:
- MQTT
---

这篇文章讲述的 `MQTT Broker` 项目中添加 Metric 监控指标。

<!-- more -->

## 概述

Metric 属于系统可观察性的内容，它可以告诉外部系统内部的运行情况，从而及时进行干预。在之前的文章中描述过监控系统的四大黄金指标([量化：监控系统 4 大黄金指标](https://zhangxt.top/2022/01/22/four-golden-signals-of-monitor/)), 在这里，按照这个标准进行定义。

**1. 延迟：服务请求所需时间**
- 每一个 Connection 上，PUBLISH QoS1&2 消息每秒/每分钟平均响应时间（需要记录每一个报文的开发时间和结束时间）。

**2. 通讯量：监控当前系统的流量，用于衡量服务的容量需求**
- 每一个 Connection 上，PUBLISH QoS1&2 消息每秒/每分钟请求量（QPS）；
- 整个系统，PUBLISH QoS1&2 消息每秒/每分钟请求量（QPS）。

**3. 错误：监控当前系统所有发生的错误请求，衡量当前系统错误发生的速率**
- 每一个 Connection 上，PUBLISH QoS1&2 消息每秒/每分钟错误请求量（QPS）；
- 整个系统，PUBLISH QoS1&2 消息每秒/每分钟请求量（QPS）。

**4. 饱和度：衡量当前服务的饱和度**
- 当前系统的用户量（连接数）；
- 每一个 Connection 上，接收/发送报文的数量或字节数；
- 内存或 CPU 使用情况。

## 选型

### Dropwizard Metrics 

Dropwizard 提供了五种不同的指标类型，含义如下所示：

**1. Gauges**

用于度量一个对象的值，如队列的大小或其它可以表示的数值；

**2. Counters**

计数器，可以对其进行增减操作，如可以用一个 Counter 表示当前队列的大小，有对象加入加一，有对象移出就减一；



**3. Histograms**

Histogram 反映的是数据流中的值的分布情况。包含最小值、最大值、平均值、中位数、p75、p90、p95、p98、p99 以及 p999 数据分布情况。
Histogram 计算分位数的方法是先对整个数据集进行排序(底层使用的数据结构是跳跃表)，然后取排序后的数据集中特定位置的值（比如 p99 就是取倒序 1%位置的值）。这种方式适合于小数据集或者批处理系统，不适用于要求高吞吐量、低延时的服务。对于数据量较大，系统对吞吐量、时延要求较大的场景，可以采用抽样的方式获取数据，动态地抽取程序运行过程中的能够代表系统真实运行情况的一小部分数据来实现对整个系统运行指标的近似度量，这种方法叫做蓄水池算法（reservoir sampling）。
系统提供了 UniformReservoir, SlidingWindowReservoir,SlidingTimeWindowReservoir 及 ExponentiallyDecayingReservoir 四种方式，默认使用的 ExponentiallyDecayingReservoir, 该抽样可以反映最近请求的数据。

**说明：Histogram 反映是数据整体的分布情况，不反映瞬时的请求数据。**

**4. Meter**

统计系统中某一事件的响应速率，如TPS、QPS。该项指标值直接反应系统当前的处理能力，它提供了五个变量值：count(请求总量)、mean rate(平均值)、1-minute rate(1分钟内平均值)、5-minute(5分钟内平均值)、15-minute(15分钟内平均值)。

**5. Timer**

计时器，是 Meter 和 Histogram 的结合，用 Meter 统计 QPS, 用 Histogram 统计时长或报文大小的分布情况。

**说明：Dropwizard Metrics 不仅提供了指标的计算，还包括指标的输出，如输出到日志文件或第三方系统。**

### Sentinel

Sentinel 是阿里巴巴开源的一个限流工具，它可以根据请求的 QPS 阈值对请求进行降级处理。Sentinel 底层采用高性能的滑动窗口数据结构 LeapArray 来统计实时的秒级指标数据，可以很好地支撑写多于读的高并发场景，它可以计算出如下指标数据：
- passQps: 请求的 QPS; 
- blockQps: 被阻塞的 QPS;
- successQps: 成功请求的 QPS;
- exceptionQps: 异常请求的 QPS;
- rt: 响应时间。

它提供了两个时间维度：1）秒级；2）分钟级，计算逻辑封装在 `StatisticNode` 中。 

## 总结

在项目中，指标包含两一个作用：1）内部控制（如限流）的依据；2）输出到外部系统进行监控，所以要求，QPS 及响应时间的计算是实时且达到秒级。为了满足这两个要求，需要将 Dropwizard 和 Sentinel 组件组合起来，Sentinel 用来计算 QPS 和响应时间的数值，并将结果导入到 Dropwizard 中，最终输出到最三方系统。




