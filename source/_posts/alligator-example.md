---
title: Alligator 系列：实例
date: 2022-01-02 16:37:41
updated: 2022-01-02 16:37:41
tags:
- 实例
categories:
- Alligator网关
---

## 概述
这篇文章主要介绍 Alligator 系统的部署启动过程。

<!-- more -->

## 配置
启动 Alligator 系统，需要启动 4 个服务，分别是：
- 注册中心：实现服务的注册与发现，单机部署；
- 在线服务：实现用户的在线管理；
- 网关： 接收客户端的连接并将消息转发到注册中心，单机部署；
- 客户端：连接网关并实现消息的接收及处理。

### MQ topic 配置
在 Alligator 系统中，网关与后端服务使用 MQ 进行通信，需要为每一个服务（每一台机器）配置一个 Topic, 其说明如下：
- TopicTest：在线服务；
- TopicTest-1：网关服务；
- UserEvent：用于广播用户登陆/下线事件；
- ServiceEvent：用于广播服务上线/下线事件，由注册中心广播出去。

在该实例中，使用 RocketMQ 作为消息组件，还需要定义两个惟一的参数：producerGroup 及 consumerGroup。MQ 参数定义完整实例如下：
```yml
common:
  mqProxy:
    nameSrv: MQ 命名服务器地址
    producerGroup: online-produce-3
    consumerGroup: online-consumer-2
    topic: TopicTest
  sysEvent:
    userTopic: UserEvent
    serviceTopic: ServiceEvent
```
引入多 MQ 支持之后，配置调整如下（网关的配置）：
```yml
common:
  mqProxy:
    dialect: rocketmq
    topic: TopicTest-1
    rocketMq:
      nameSrv: MQ 命名服务器地址
      producerGroup: online-produce-1
      consumerGroup: online-consumer-1

  sysEvent:
    userTopic: UserEvent
    serviceTopic: ServiceEvent
```
在新的配置中，需要指定使用的 MQ 类型，并根据每一种类型设置与其相关的参数。

### 服务信息配置
在后端服务中，需要向注册中心注册其服务，注册的消息包括 zone, id, name, topic 及 load 等信息，同时需要指定注册中心的地址及端口，配置如下所示（网关服务）：
```yml
common:
  serverConfig:
    host: 192.168.3.014
    port: 9091
    zone: 1
    id: gw-ws-01
    name: gw-ws-01
  regServer:
    host: 192.168.3.014
    port: 9090
```
另外，每一个服务如果开发端口，必须指定 ip 及 端口。
```yml
common:
  serverConfig:
    host: ip
    port: 端口
```
各服务地址端口如下配置：
- 9090: 注册中心端口；
- 9091: 网关端口；
- 9098: 客户端服务端口；

在配置中，可以设置一些通用的配置，如工作队列大小及线程池大小。
```yml
common:
  workQueue:
    maxQueueNum: 1000
    maxThreadNum: 100
```

### 请求链路
![alligator-process](/images/alligator/alligator-process.jpg "alligator-process")

在这里有几个关键的点：
- 服务发现是通过注册中心来实现的；
- 网关与后端服务是通过 MQ 来通信的；
- 所有的客户端连接到网关上，网关下线，注册到该网关的用户都会下线；
- 用户登陆成功之后，会调用获取全量用户信息，用户在线数据可能比较大，在这里使用 request-stream 方式进行通信；

## 启动流程
1. 启动 RocketMQ, 并创建相关的 topic;
2. 启动注册中心，工程为：alligator-registration-server;
3. 启动在线服务，工程为：alligator-biz-online;
4. 启动网关服务，工程为：alligator-gateway-websocket; 
5. 启动在线客户端，工程为：alligator-client-online; 
6. 访问在线客户端：http://ip:9098.

**说明：**
用户名和密码可以任意输入，没有校验。



