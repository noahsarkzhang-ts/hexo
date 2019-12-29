---
title: Java Stream Pipeline
date: 2019-12-08 20:13:30
tags:
- stream pipeline
categories:
- Java基础
---
## 1. 概述
> Java 8中的Stream是对集合（Collection）对象功能的增强，它专注于对集合对象进行各种非常便利、高效的聚合操作（Aggregate operation），或者大批量数据操作(Bulk data operation)。Stream API借助于同样新出现的Lambda表达式，极大的提高编程效率和程序可读性。同时它提供串行和并行两种模式进行汇聚操作，并发模式能够充分利用多核处理器的优势，使用fork/join并行方式来拆分任务和加速处理过程。

这篇文章不是讲怎么使用Stream，而是重点讲述其背后的数据结构及算法，下面将结合以下代码断进行分析。
```java
List<Integer> list = Arrays.asList(1, 5, 2, 4, 8, 6, 7, 8, 9, 10);
int sum = list.stream().filter(x -> x % 2 == 0).sorted(Comparator.reverseOrder()).map(x -> x * x).reduce((x, y) -> x + y).get();
```

## 2. 

## 6. 总结


**参考：**

----
[1]:https://www.ibm.com/developerworks/cn/java/j-lo-java8streamapi/index.html
[2]:https://www.cnblogs.com/CarpenterLee/p/6637118.html
[3]:https://blog.hufeifei.cn/2018/09/15/Java/ForkJoinPool/
[4]:https://www.jianshu.com/p/de025df55363

[1. Java 8 中的 Streams API 详解][1]

[2. 深入理解Java Stream流水线][2]

[3.ForkJoinPool入门篇][3]

[4.分析jdk-1.8-ForkJoinPool实现原理(上)][4]