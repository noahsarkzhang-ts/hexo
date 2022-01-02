---
title: Alligator 系列：长连接网关概述
date: 2021-07-31 19:58:01
tags:
- 网关
- PRC
- TCP
- Websocket
categories:
- Alligator网关

---

## 1. 概述

在项目中经常遇到双向通信的场景，如指令的实时下发、状态的上报等，这时候使用 HTTP 协议就有点捉襟见肘。正常情况下一般会使用 TCP/Websocket 协议来实现，不过不同于 HTTP 协议简单及有大量框架的支持，使用 TCP/Websocket 需要考虑心跳、协议的定义、数据的序列化（反序列化）及 RPC 调用的实现。相对来说，入门相对比较复杂。 如果能有一个项目能够对上述功能进行封装，隐藏不同协议之间的差异，对上层应用提供一套统一的接口，上层业务只关心业务，那么就会减少开发人员的学习成本，快速接入项目。
Alligator 项目就是为了解决上述的场景而开发的，它提供了一个框架，可以让开发人员快速进行 TCP/Websocket 及 HTTP 的开发，而无需关心下层使用的协议。在此基础上，Alligator 还提供了一个进行长连接网关开发的脚手架，它是业务无关的，可以快速接入不同的业务场景。

<!-- more -->

## 2. 架构
![alligator-architecture](/images/alligator/alligator-architecture.jpg "alligator-architecture")

模块说明：
- 注册中心：实现服务的注册、发现及负载功能；
- TCP 网关：接入 TCP 协议客户端，实现用户的登陆、退出及消息的转发功能，同时它维护了客户端及网关之间的 Session 信息；
- WEBSOCKET 网关：功能同 TCP 网关，接入 WEBSOCKET 协议的客户端；
- HTTP/HTTP2 网关：实现 HTTP/HTTP2 协议的接入；
- 在线服务：接收用户登陆/退出事件，实现用户的在线维护功能；
- 聊天服务：实现聊天功能；
- MQ 服务：实现消息的存储及转发功能；

系统特点：
- 全异步编程：所有模块使用全异步通信，能有效提高模块的吞吐量；
- RPC 通信：实现 request - response ，oneway ，request - streaming（待开发） 三种双向通信模式；
- 消息存储及路由：使用 MQ 进行消息的存储及路由，减少模块之间的耦合；
- 业务无关：对底层模块进行了统一地抽象及封装，业务人员可以专注业务开发；

## 3. 总结
Alligator 不仅提供了一个快速进行长连接开发的框架，同时还提供了一个开发脚手架，让长连接网关开发不再是一件困难的事。后续将出一个序列专门介绍其底层实现；


[1]:https://github.com/noahsarkzhang-ts/alligator

[工程代码][1]