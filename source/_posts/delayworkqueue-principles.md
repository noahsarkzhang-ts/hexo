---
title: DelayWorkQueue 原理
date: 2019-09-10 09:50:24
tags:
- DelayWorkQueue
- ScheduledThreadPoolExecutor
- FutureTask
- DelayQueue
- 周期性任务
categories:
- 阻塞队列
---

这篇文章主要分析在ScheduledThreadPoolExecutor中延时队列的实现，包括数据结构及相关算法，同时也会分析FutureTask的实现。

## 1. 概述

![ScheduledThreadPoolExecutor](/images/scheduled-thread-pool-executor.jpg "ScheduledThreadPoolExecutor")

从上图可以看到ScheduledThreadPoolExecutor,DelayWorkQueue及ScheduledFutureTask三者之间的关系，在ScheduledThreadPoolExecutor中使用的队列是DelayWorkQueue，提交到DelayWorkQueue中的任务是ScheduledFutureTask类型的任务，提交任务的线程可以通过ScheduledFutureTask的接口获取结果或者取消任务，下面对这三个类做一个简要描述：
- DelayWorkQueue : 底层的存储结构是一个小堆，它根据延时的时间进行排序，堆顶的元素永远是最小的；加入一个元素时，首先被加到队列的最后一个元素中，然后使用siftUp操作，跟它的父结点进行比较，如果比父结点小，则交换位置，递归执行这样的操作，直到比父结点元素都大；取出元素永远是取出堆顶元素，然后将队列中的最后一个元素移动到堆顶，执行siftDown操作，跟左右子结点中的最小元素进行比较，如果比子结点大， 则交换位置，递归执行这样的操作，直到比子结点小为止。
- ScheduledFutureTask : 提交到DalayWorkQueue队列中的元素是ScheduledFutureTask类型，它继承了Runnable接口，包含了任务的执行逻辑，同时它也继承了Future接口，具备了取消任务、同步获取返回结果的功能。在ScheduledFutureTask中有几个重要的参数：state(状态), callable(有返回值的runnable对象), outcome(返回结果), runner(执行线程), waiters(等待队列), state表示任务执行的状态，如果任务在未完成之前执行get操作（获取返回结果），那么调用线程会被阻塞，该线程会加入到waiters队列中，等待runner线程执行set操作（设置返回结果）之后被唤醒。如果ScheduledFutureTask执行了取消操作之后，它会被移除DelayWorkQueue队列，state设置为取消状态，任务将不再被执行，如果任务已经执行，将会向其发送interrupt操作。
- ScheduledThreadPoolExecutor : ScheduledThreadPoolExecutor扩展了ThreadPoolExecutor类，在ThreadPoolExecutor的基础上，可以执行延时任务和周期收性任务，借助DelayWorkQueue类，实现了任务的延时执行，对于周期性任务，在上一个周期执行结束之后，会重新计算下一个周期的延时时间，将任务重新加入到DelayWorkQueue队列中，等待下次任务的调度。

## 2. DelayWorkQueue
![DelayedWorkQueue](/images/DelayedWorkQueue.jpg "DelayedWorkQueue")
DelayedWorkQueue类图如上所示，DelayedWorkQueue是BlockingQueue的子类。

DelayedWorkQueue像DelayQueue和PriorityQueue一样是基于堆的数据结构，它需要与ScheduledFutureTask配合使用。在ScheduledFutureTask中记录了在堆中的索引，可以快速定位所在的位置，方便进行task的取消操作。

DelayedWorkQueue队列中元素的增加或删除，都会改变堆的结构，在DelayedWorkQueue中，提供了两种调整堆的操作：siftUp和siftDown，后面的章节会详细介绍。

在分析DelayedWorkQueue之前，先了解下堆这种数据结构：
> 堆（英语：Heap）是计算机科学中的一种特别的树状数据结构。若是满足以下特性，即可称为堆：“给定堆中任意节点P和C，若P是C的父母节点，那么P的值会小于等于（或大于等于）C的值”。若父母节点的值恒小于等于子节点的值，此堆称为最小堆（min heap）；反之，若父母节点的值恒大于等于子节点的值，此堆称为最大堆（max heap）。在堆中最顶端的那一个节点，称作根节点（root node），根节点本身没有父母节点（parent node）

一个小堆的结构如下所示：
![min-heap](/images/min-heap.jpg "min-heap")

在小堆中，parent结点小于等于子结点，而对两个左右子结点大小没有要求。在DelayedWorkQueue中使用的是就是小堆，从而保证返回的是延时最小的任务。



## 3. ScheduledFutureTask
![ScheduledFutureTask](/images/ScheduledFutureTask.jpg "ScheduledFutureTask")

## 4. ScheduledThreadPoolExecutor
![ScheduledThreadPoolExecutor](/images/ScheduledThreadPoolExecutor.jpg "ScheduledThreadPoolExecutor")

## 5. 总结

**参考：**

----
[1]:https://www.jianshu.com/p/376d368cb44f
[2]:http://cmsblogs.com/?p=2418

[1. Java阻塞队列SynchronousQueue详解][1]

[2. 【死磕Java并发】—–J.U.C之阻塞队列：SynchronousQueue][2]