---
title: RocketMQ系列：NameServer概览
date: 2020-01-20 18:27:30
tags:
- rocketmq
- namesrv
categories:
- rocketmq系列
---

NameServer 作为消息中间件 RocketMQ 的核心组件之一， 起着注册中心的作用，这篇文章主要是从整体上分析一下NameServer的实现。
![rocketmq-namesrv-overview](/images/rocketmq-namesrv-overview.jpg "rocketmq-namesrv-overview")
NameServer可以分为三个层次（暂且这么分，方便理解），1）通信层，使用 Netty 作为底层通信组件，封装统一的网络 IO 事件处理流程，同时用户也可以自定义事件。2）服务层，封装通用的业务逻辑：a）统一请求处理流程；b）定义三种调用方式，如同步调用，异步调用及单向调用（发出请求不需要响应数据）；c）响应超时处理；d）IO事件处理。3）业务层，实现请求处理器及事件监听器注册接口，处理NameServer相关的数据，如broker地址及保活信息、topic队列信息及服务器过滤信息。

- 通信层：Netty 使用 Reactors 的多线程模型，MainReactor 负责客户端的连接请求，并将请求转交给 SubReactor，SubReactor 负责相应通道的 IO 读写请求。在这里，BossGroup 承担MainReactor的角色，一般只需要一个线程即可（一个 EventLoop 实质就是一个线程），Work Group 承担 SubReactor 的角色，在RomcketMQ中默认是三个线程。从上面的关系可以看出，EventLoopGroup 包含多个 EventLoop，而一个 EventLoop 代表了一个独立的事件循环，循环等待 IO 事件，一般由一个线程来处理，一个 EventLoop 可以同时处理多个 tcp 连接（Channel），同时一个 Channel 所有事件只能在一个 EventLoop 中处理，一个 Channel 一旦分配给一个 EventLoop 之后将不会改变这种关联关系。在 Netty 中事件处理使用了责任链的模式，将事件处理分为不同的处理单元，让数据以水流的方式在管道中流动处理，每一个阀门都有一个独立的处理逻辑，这些处理单元包括但不限此，如数据的编/解码、数据的转换、空闲连接的检测及数据的消费，在 Netty 中，这些处理单元叫做 Handler 对象。每一个 Handler 对象存储在 ChannelHandlerContext 对象中，再将 ChannelHandlerContext 对象串连起来，形成一个双向链表。根据处理事件的不同，Handler 对象可以分为出站或入站对象，入站代表读事件，出站代表了写事件，所以，访问 ChannelHandlerContext 链表也分为出站和入站两种，入站从链首开始，正向访问，而出站则从链尾开始，反向访问。 在 ChannelPipeline 对象中，存储 ChannelHandlerContext 链表的链首及链尾对象，每一个 Channel 对象都会关联一个 ChannelPipeline 对象，在处理事件的时候，可方便调用相应的 Handler 对象，上层应用只要定义相应的 Handle对象 到Netty中即可。下图是 EventLoop 处理事件的流程。
![rocketmq-namesrv-netty](/images/rocketmq-namesrv-netty.jpg "rocketmq-namesrv-netty")
可以看到，EventLoop 主要处理三件事：1）在多路复用器 Selector 上调用 select 方法，监听所有的 Channel的 IO 事件；2）执行 IO 处理流程，调用 ChannelHandlerContext 链表，执行业务处理；3）执行提交的任务，在 EventLoop 中，可以处理定时任务，在处理完业务逻辑之后，会调用已经到期的任务执行。定时任务存放在一个优先级队列（scheduleTaskQueue队列，实现类为PriorityQueue队列）中，按照时间进行排序，执行任务前会将已经到期的任务移到 taskQueue 队列中，然后依次执行 taskQueue 队列中的所有任务。

- 服务层：定义了四个基本功能，1）统一请求处理流程，每一个命令可以注册一个处理器（Processor对象）及处理线程池，不同业务请求可以由不同的线程池处理，这样有做到业务隔离和提高并发处理能力；2）定义了三种调用方式，分别是同步调用、异步调用及单向调用（发出请求不需要响应数据），同步调用及异步调用都是使用 Future 对象来实现，区别在于：同步调用需要在 Future 对象上等待一个超时时间，而异步调用只需定义一个回调方法即可；3）响应超时处理，在异步调用中，调用结束之后程序已经返回了，响应的数据需要在另外一个线程处理，为了方便响应数据找到对应的请求，需要构造一个 Future 对象存储到响应结果表中，请求及响应数据包含相同的请求序号，可以方便地从表中检索到 Future 对象，调用对应的回调函数。在这里，有一个问题，如果一直没有响应怎么办？这就需要一个线程定时扫描响应结果表，将已经超时的请求移除响应结果表；4）IO事件处理，主要包括连接、空闲、关闭及异常事件，上层应用注册事件监听器（ChannelEventListener）来处理相关的事件。

- 业务层：业务层维护了 broker 地址及保活信息、topic 队列信息及服务器过滤信息，Broker 定期向 NameServer 发送心跳信息，心跳信息中就包含了这些信息，另外生产者和消费者也会向 NameServer查询Broker及topic的信息，业务层通过向服务层注册请求处理器（Processor对象）及事件监听器（ChannelEventListener对象），来处理心跳、查询等请求。

通过上面的分析可以看出，NameServer 在设计结构比较清晰，在业务处理过程中，使用了异步的处理方式，大大提高了服务器的处理能力。


