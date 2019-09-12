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
- DelayWorkQueue : 底层的存储结构是一个小堆，

## 2. DelayWorkQueue

## 3. FutureTask

## 4. ScheduledThreadPoolExecutor

## 5. 总结

**参考：**

----
[1]:https://www.jianshu.com/p/376d368cb44f
[2]:http://cmsblogs.com/?p=2418

[1. Java阻塞队列SynchronousQueue详解][1]

[2. 【死磕Java并发】—–J.U.C之阻塞队列：SynchronousQueue][2]