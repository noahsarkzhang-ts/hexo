---
title: Alligator 系列：MQ RPC
date: 2021-10-16 10:59:56
updated: 2021-10-16 10:59:56
tags:
- MQ RPC
- RabbitMQ
- RocketMQ
categories:
- Alligator网关
---

## 1. 概览

在 Alligator 系统中，网关与业务系统之间是通过 MQ 进行通信。为了简化开发成本，基于 MQ, 实现了一套 RPC 调用，其封装了超时、同步调用及异步调用等功能，调用模型如下图所示：
![mq-rpc-model](/images/alligator/mq-rpc-model.jpg "mq-rpc-model")

- 使用两个 MQ 队列来存储信息，分别是请求及响应信息；
- 在请求端维护一个 request id,在响应信息中带上 request id,从而将请求与响应对应起来；
- 在请求端为每一个请求设置一个超时任务，避免长时间未响应结果。

<!-- more -->


## 2. 数据结构

在 MQ RPC 中，有几个关键的接口：1) MqProxy; 2) Topic; 3) Message; 4) PromisHolder; 5) ChannelHolder; 6) Consumer; 7) Producer; 除此之外，还有一个 RpcPromise, 它继承了 Netty 中的 DefaultPromise 类，实现异步转同步的功能。其类图如下所示：

![mq-rpc](/images/alligator/mq-rpc-class.jpg "mq-rpc")

1. MqProxy: MQ RPC 中的核心类，封装了 MQ 调用的实现，不同类型的 MQ 实现该接口即可。外部模块通过该类进行 RPC 的调用及响应结果的处理；
2. Topic：MQ 队列的抽象，在不同 MQ 中含义可能不同，在 RoketMQ, Kafka 中，该 Topic 对应的就是 MQ 中的 Topic, 而在 RabbitMQ 中，Topic 对应的则是一个队列；
3. Message：MQ 中传输的数据；
4. RpcPromise：代表了一次 RPC 调用，RPC 的结果就是通过 RpcPromise 通知给上层使用，一般是通过定义回调方法实现，另外调用超时的处理也是在 RpcPromise 中实现；
5. PromisHolder：RpcPromise 容器类，负责管理维护所有的 RpcPromise，其中包括生成 request id，删除 RpcPromise等等。PromisHolder 主要由 RPC 的调用方（客户端）维护。在 MQ 的实现中，request id 是全局惟一的，而在 TCP/Websocket 中，request id 只需要保证在一个 Connnection(一个客户端连接一个服务器称为一个 Connection) 惟一即可。说明：RPC 在 Alligator 中有两类实现，一类是基于 TCP/Websocket的，后续文章再讲述，一类是基于 MQ 的，即本文讲述的内容； 
6. ChannelHolder：一次 RPC 调用在服务器端的会话（Session）信息，它维护了一次 RPC 的相关状态数据，如客户端信息，以便写入响应数据； 
7. Consumer：用于订阅 MQ 中请求队列及响应队列的中的数据；
8. Producer：用于向 MQ 中发送数据；
9. MqProxyFactory：MqProxy 工厂类，用于实例化 MqProxy 类。

## 3. 结论
目前为止，对相关的抽象还不够完善，Message 及 Topic 只定义了空接口，后续可以提取公共的方法丰富其接口定义。