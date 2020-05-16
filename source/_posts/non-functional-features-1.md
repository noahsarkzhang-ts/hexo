---
title: 系统设计-非功能性特性
date: 2020-04-25 20:49:32
tags:
- 可靠性
- 可扩展性
- 可维护性
categories:
- 非功能性特性
---

在大多数软件系统中，功能特性决定了系统能做什么，而非功能特性决定了系统能走多远，本篇文章专注于非功能特性中三个比较重要的特性：
- 可靠性（Reliability）：当出现意外情况如硬件、软件故障、人为失误等，系统应可以继续正常运转：虽然性能可能有所降低，但确保功能正确。
- 可扩展性（Scalability）:随着规模的增长，例如数据量、流量或复杂性，系统应以合理的方式来匹配这种增长。
- 可维护性（Maintainability）：随着时间的推移，许多新的人员参与到系统开发和运维，以维护现有功能或适配新场景等，系统都应高效运转。

## 1. 可靠性
可靠性意味着即使发生故障，系统也可以正常工作。故障包括硬件（通常是随机的，不相关的），软件（缺陷通常是系统的，更加难以处理）以及人为（总是很难避免时不时会出错）方面。容错技术可以很好地隐藏某种类型故障，避免影响最终用户。

## 2. 可扩展性
可扩展性是指负载增加时，有效保持系统性能的相关技术策略。即使系统现在工作可靠，并不意味着它将来一定能够可靠运转。发生退化的一常见原因是负载增加：例如并发用户从最初的10 000个增长到100 000个，或从100万到1000万；又或者系统目前要处理的数据量超出之前很多倍。可扩展性是用来描述系统应对负载增加能力的术语，为了讨论可扩展性，首先需要明确如何定量描述负载和性能？
### 2.1 负载
负载可以用称为负载参数的若干数字来描述，参数的最佳选择取决于系统的体系结构，它可能是Web服务器的每秒请求处理次数，数据库写入的比例，聊天室的同时活动用户数量，缓存命中率等。有时平均值很重要，有时系统瓶颈来自于少数峰值。

以Twitter为例，使用其2012年11月发布的数据。Twitter的两个典型业务操作是：
- 发布tweet消息：用户可以快速推送新消息到所有的关注者，平均大约4.6k requests/sec，峰值约12k requests/sec。
- 主页时间线（Home timeline）浏览：平均300k requests/sec 查看关注对象的最新消息。

### 2.2 性能
如果负载增加将会发生什么，有两种考虑方式：
- 负载增加，但系统资源（如CPU、内存、网络带宽等）保持不变，系统性能会发生什么变化；
- 负载增加，如果要保持性能不变，需要增加多少资源？

这两个问题都会关注性能指标，那如何描述系统性能？

在批处理系统中如Hadoop中，通常关心吞吐量(throughput)，即每秒可处理的记录条数，或者在某指定数据集上运行作业所需的总时间；而在线系统通常更重服务的响应时间(response time)，即客户端从发送请求到接收响应之间的间隔。

服务的响应时间通常是使用服务请求的平均响应时间，即n个请求响应时间的算术平均值。然而，如果想知道多少用户实际经历了多少延迟，最好使用百分位数(percentiles)。如果已经搜集到响应时间信息，将其从最快到最慢排序，中位数(median)就是列表中间的响应时间。例如，如果中位数响应时间为200ms，那意味着有一半的请求响应不到200ms，而另一半请求则需要更长的时间。

中位数指标非常适合描述多少用户需要等待多长时间：一半的用户请求的响应时间少于中位数响应时间，另一半则多于中位数的时间。因此中位数也称为50百分位数，有时也缩写为p50。为了弄清楚异常有多糟糕，需要关注更大的百分位数如常见的第95、99和99.9（缩写为p95、p99和p999）值。作为典型的响应时间阈值，它们分别表示为95%、99%或99.9%的请求响应时间快于阈值。例如95百分位数响应时间为1.5s，这意味着100个请求中的95个请求快于1.5s，而5个请求则需要1.5s或更长的时间。

## 3. 可维护性
可维护性则意味着许多方面，但究其本质是为了让工程和运营团队更为轻松。良好的抽象可以帮助降低复杂性，并使系统更易于修改和适配新场景。良好的可操作性意味着对系统健康状况有良好的可观测性和有效的管理方法。

可运维性在软件设计时就需要开始考虑，尽可能减少维护期间的麻烦，甚至避免造出容易过期的系统。为此，需要特别关注软件系统的三个设计原则：
- 可运维性：方便运营团队来保持系统平衡地运行；
- 简单性：简化系统复杂性，使新工程师能够轻松理解系统。
- 可演化性：后续工程师能够轻松对系统进行改进，并根据需求变化将其适配到非典型场景，也称为可延伸性、易修改性或可塑性。

## 4. 总结
知易行难，使应用程序可靠、可扩展或可维护并不容易，需要结合使用的场景选择不同的策略和技术。


**参考：**

----
[1]:https://book.douban.com/subject/30329536/

[1. 数据密集型应用系统设计][1]
