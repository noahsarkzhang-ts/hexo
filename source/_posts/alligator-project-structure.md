---
title: Alligator 系列：工程结构
date: 2022-01-02 15:06:24
updated: 2022-01-02 15:06:24
tags:
- 目录结构
categories:
- Alligator网关
---

## 概述
这篇文章主要是介绍 Alligator 系统的工程结构。

<!-- more -->

## 目录结构
Alligator 目录结构如下所示：

```bash
├─alligator
│  ├─biz
│  │  └─online
│  ├─client
│  │  └─online
│  ├─common
│  ├─db
│  │  └─redis
│  ├─gateway
│  │  ├─http
│  │  ├─http-common
│  │  ├─http2
│  │  ├─http2-client
│  │  ├─persistent-common
│  │  ├─tcp
│  │  └─websocket
│  ├─mq
│  │  ├─common
│  │  ├─facade
│  │  ├─kafka
│  │  ├─rabbitmq
│  │  └─rocketmq
│  ├─registration
│  │  ├─client
│  │  ├─common
│  │  └─server
│  └─server
│      ├─common
│      ├─tcp
│      └─websocket
```

**目录简述**
- server: RPC 接口定义及实现
    - common: RPC 接口定义及主体功能实现；
    - tcp: TCP 协议 Client 及 Server 实现；
    - websocket: websocket 协议 Client 及 Server 实现；
- common：通用消息格式的定义
- gateway: 各种协议的网关实现
    - http-common：http/http2 协议的公共类，包括统一异常处理、通用的 Request 及 Reponse 封装；
    - http: 基于 http 协议的网关服务器；
    - http2: 基于 http2 协议的网关服务器；
    - http2-client：基于 ok-client 的客户端；
    - persistent-common：长连接的公共类；
    - tcp：基于 tcp 协议的网关服务器；
    - websocket：基于 websocket 协议的网关服务器；
- registration：注册中心实现
    - common：公共类，如消息格式的定义；
    - server：注册中心的服务端，使用基于内存的存储实现，基于 redis 的还需要完善；
    - client：注册中心客户端；
- biz：后端服务的实现
    - online：在线服务的实现；
- client：客户端服务
    - online：在线客户端，基于 web 浏览器实现；
- mq：MQ RPC 的实现
    - common：通用接口定义；
    - rabbitmq：基于 rabbitmq 的 RPC 实现；
    - rocketmq：基于 rocketmq 的 RPC 实现；
    - kafka：未实现
    - facade：门面类，隐藏背后的 Mq实现，客户基于统一的协议调用 RPC；
- db: 后端存储
    - redis: 使用 redis 存储后端数据。

## 事件通知
RPC 框架层向业务层提供了三个通信事件，用于通知上层服务器及客户端的连接状态，包括服务器成功启动、客户端连接成功及客户端下线事件，业务层可以结合业务定义相关的回调处理函数。

![event-bus](/images/alligator/event-bus.jpg "event-bus")