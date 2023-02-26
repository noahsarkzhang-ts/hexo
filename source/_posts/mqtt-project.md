---
title: Mqtt 系列：工程结构
date: 2023-02-26 15:20:04
tags:
- 工程结构
- 代码目录
categories:
- MQTT
---

本文讲述 `Alligator Mqtt Broker` 项目的代码结构。 

<!-- more -->

## 一级目录

在 `Mqtt Broker` 项目中，按照分层的结构来划分目录，其目录结构如下：

```bash
# mqtt broker 目录
Alligator mqtt broker
|-- clusters
|-- common
|-- protocol
|-- repository
|-- transport
`-- Server.java
```

**说明：**
- transport: 通信层，用于处理网络请求，解析 MQTT 网络协议，建立于客户端的连接；
- protocol: 协议层，处理 MQTT 业务逻辑；
- clusters: 集群通信层，用于集群间消息的传递；
- repository: 持久化层，用于会话数据及消息的存储；
- common: 存放工具类，如类加载、线程和缓存工具类；
- Server.java: Broker Server 启动类。

## 通信层

通信层基于 Netty MQTT 协议模块实现，接收客户端请求，解析 MQTT 协议，并将消息转发到协议层处理。

```bash

transport
|-- Dispatcher.java
|-- MqttEntryHandler.java
|-- config
|-- exception
|-- handler
|-- metric
|-- session
`-- ssl
```

**说明：**
- config: 存放通信配置相关的类；
- exception: 存放通信异常的类；
- handler: 存放 Netty 消息处理类，包括日志、超时、异常处理逻辑；
- metric: 存放统计监控相关的类，如用户登录信息、消息数量等等；
- session: 存放会话相关的类；
- ssl: 存放 SSL 相关的类；
- Dispatcher.java: 消息分发类，负责将 MQTT 消息分发到协议层，是通信层及协议层的桥梁；
- MqttEntryHandler.java: MQTT 消息处理类，负责接收来自网络底层的消息，识别消息类型并进行分发。

## 协议层

协议层是 MQTT Broker 项目中核心的业务处理模块，它主要实现了 MQTT 规范文件中定义的功能。

```bash
protocol
|-- DefaultMqttEngine.java
|-- MqttEngine.java
|-- entity
|-- processor
|   |-- ConnectProcessor.java
|   |-- DisconnectProcessor.java
|   |-- MessageProcessor.java
|   |-- PingReqProcessor.java
|   |-- PubAckProcessor.java
|   |-- PubCompProcessor.java
|   |-- PubRecProcessor.java
|   |-- PubRelProcessor.java
|   |-- PublishProcessor.java
|   |-- SubscribeProcessor.java
|   `-- UnsubscribeProcessor.java
|-- security
`-- subscription
```

**说明：**
- entity: 存放相关的实体类；
- processor: 协议处理目录，存放了所有 MQTT 消息类型的处理类；
- security: 存放安全相关的类；
- subscription: 存放 Trie 相关的类；
- MqttEngine.java: 定义了 MQTT 业务处理的接口；
- DefaultMqttEngine.java：默认的 MQTT 业务处理类，实现了 MqttEngine 接口。


## 集群通信层

集群通信层用于集群消息的传递，这些消息包括 Publish 消息、Subscription 订阅消息、用户退出消息及服务器登陆消息。

```bash
clusters
|-- AbstractMqttEventBus.java
|-- ClusterMqttEventBusManager.java
|-- ClustersEventBus.java
|-- MqttEventBus.java
|-- MqttEventBusManager.java
|-- SingletonEventBus.java
|-- SingletonMqttEventBusManager.java
|-- entity
|-- processor
|   |-- ClusterClientLogoutProcessor.java
|   |-- ClusterPublishProcessor.java
|   |-- ClusterSubscriptionProcessor.java
|   `-- ServerLoginProcessor.java
`-- serializer
```

**说明：**
- entity: 存放集群通信相关的类；
- processor: 存放集群消息的处理类，每一个集群消息对应一个处理类；
- serializer: 存放消息序列化相关的类；
- MqttEventBus.java: 定义了集群通信所需功能的接口；
- MqttEventBusManager.java: 定义了集群通信管理功能的接口；
- AbstractMqttEventBus.java: MqttEventBus 抽象类，实现了一些公共的功能；
- SingletonEventBus.java: 单实例版本的 MqttEventBus 对象；
- SingletonMqttEventBusManager.java: 单实例版本的 MqttEventBusManager 对象；
- ClustersEventBus.java: 集群版本的 MqttEventBus 对象；
- ClusterMqttEventBusManager.java: 集群版本的 MqttEventBusManager 对象；

## 持久化层

持久化层用于两类数据的持久化，这两类数据包括：会话类的数据及经过确认之后的 QoS1&2 消息数据。

```bash
repository
|-- ClientSessionRepository.java
|-- InflightMessageRepository.java
|-- MessageRepository.java
|-- OffsetGenerator.java
|-- OffsetRepository.java
|-- RetainedRepository.java
|-- SubscriptionsRepository.java
|-- UserRepository.java
|-- WillRepository.java
|-- entity
|-- factory
|-- memory
|-- mysql
`-- redis
```

**说明：**
- entity: 存放持久化相关的类；
- factory：存放对象工厂相关的类，用于加载不同类型的 Repository 对象；
- memory: 存放内存版本的 Repository 对象；
- mysql: 存放 mysql 版本的 Repository 对象；
- redis: 存放 redis 版本的 Repository 对象；
- ClientSessionRepository.java: 定义客户端持久化的 Repository 接口；
- InflightMessageRepository.java: 为发送中的消息而定义的 Repository 接口；
- MessageRepository.java: 为已经确认的 QoS1&2 消息而定义的 Repository 接口；
- OffsetGenerator.java: 定义了生成消息 Id 的 Repository 接口；
- OffsetRepository.java: 定义了消息偏移量的 Repository 接口；
- SubscriptionsRepository.java：定义了消息订阅的 Repository 接口；
- UserRepository.java: 定义了用户的 Repository 接口；
- WillRepository.java：定义了 Will 持久化相关的 Repository 接口。

## 公共类

common 目录存放了工作类，这些类包括：异常类、类加载、Redis、线程及 util.

```bash
common
|-- exception
|-- factory
|-- redis
|   |-- cmd
|   |-- config
|   `-- executor
|-- thread
`-- util
```

**说明：**
- exception: 存放公共异常类；
- factory: 存放 SPI 服务加载相关类；
- redis: Redis 相关的类；
- thread: 存放线程相关的类；
- util: 存放工具类。

工程地址：[alligator-mqtt](https://github.com/noahsarkzhang-ts/alligator-mqtt)

