---
title: Java Fork/Join框架
date: 2019-11-19 14:15:31
tags:
- 数据结构
- 分而治之
- fork/join
categories:
- 并发编程
---
## 1. 概述
ForkJoinPool运用了Fork/Join原理，使用“分而治之”的思想，将大任务分拆成小任务，从而分配给多个线程并行执行，最后合并得到最终结果，加快计算。ForkJoinPool可以充分利用多cpu，多核cpu的优势，提高算法的执行效率，ForkJoinPool整体结构如下图所示：
![fork-join](/images/fork-join.jpg "fork-join")

- ForkJoinPool：
- WorkQueue：
- ForkJoinWorkerThread：
- ForkJoinTask：


## 2. 核心思想
ForkJoinPool的两大核心就是分而治之(Divide and conquer)和工作窃取(Work Stealing)算法，下面先对两种算法作一个介绍，后面将会具体细节做说明，这部分内容来自 [holmofy][3]，作者进行了很好的总结。

### 2.1 分而治之
ForkJoinPool主要思想是：将一个大任务拆分成多个小任务后，使用fork可以将小任务分发给其他线程同时处理，使用join可以将多个线程处理的结果进行汇总。
![devide-conquer](/images/devide-conquer.jpg "devide-conquer")

### 2.2 工作窃取
Fork/Join框架中使用的work stealing灵感来源于Cilk(开发Cilk的公司被Intel收购，原项目后来被升级为Clik Plus)。
> Intel公司除了Clik Plus还有一个TBB(Threading Building Blocks)也是使用work stealing算法实现。

Work Stealing算法是Fork/Join框架的核心思想：
- 每个线程都有自己的一个WorkQueue，该工作队列是一个双端队列；
- 队列支持三个功能push、pop、poll；
- push/pop只能被队列的所有者线程调用，而poll可以被其他线程调用；
- 划分的子任务调用fork时，都会被push到自己的队列中；
- 默认情况下，工作线程从自己的双端队列获出任务并执行；
- 当自己的队列为空时，线程随机从另一个线程的队列末尾调用poll方法窃取任务。
![work-stealing](/images/work-stealing.jpg "work-stealing")

## 3. 数据结构
### 3.1 ForkJoinPool

### 3.2 WorkQueue

### 3.3 ForkJoinWorkerThread

### 3.4 ForkJoinTask


## 4. 工作流程

## 5. 实例

## 6. 总结


**参考：**

----
[1]:http://blog.dyngr.com/blog/2016/09/15/java-forkjoinpool-internals/
[2]:https://www.jianshu.com/p/f777abb7b251
[3]:https://blog.hufeifei.cn/2018/09/15/Java/ForkJoinPool/
[4]:https://www.jianshu.com/p/de025df55363

[1. Java 并发编程笔记：如何使用 ForkJoinPool 以及原理][1]

[2. jdk1.8-ForkJoin框架剖析][2]

[3.ForkJoinPool入门篇][3]

[4.分析jdk-1.8-ForkJoinPool实现原理(上)][4]
