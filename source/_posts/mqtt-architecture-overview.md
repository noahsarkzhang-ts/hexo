---
title: Mqtt 系列：MQTT 整体架构
date: 2022-12-31 11:41:20
updated: 2022-12-31 11:41:20
tags:
- 架构
- QoS
- Subsriber
- Publisher
- Broker
categories:
- MQTT
---

参考现有一些厂商 `MQTT` Broker 的实现，发现大部分都要依赖于外部系统 MQ 来实现消息的存储或转发，`MQTT` Broker 仅用于终端的接入及协议的解析。在这种架构下，各结点可方便进行扩展，可应对大规模终端的接入。在小规模（几十万）的场景下，这个架构相对比较复杂。本文的目的主要是实现一个架构相对比较紧凑，且易于学习的 `MQTT` Broker 服务器，该服务器不用依赖于外部系统 MQ , 自带消息的集群路由功能。 

<!-- more -->

## 概述

`MQTT` 是一种基于发布/订阅模式的轻量级消息传输协议，专门针对低带宽和不稳定网络环境的物联网应用而设计，可以用极少的代码为联网设备提供实时可靠的消息服务。`MQTT` 协议广泛应用于物联网、移动互联网、智能硬件、车联网、智慧城市、远程医疗、电力、石油与能源等领域。
`MQTT` 有以下几个特点：
- 单容易实现
- 支持 QoS（设备网络环境复杂）
- 轻量且省带宽
- 数据无关（不关心 Payload 数据格式）
- 有持续地会话感知能力（时刻知道设备是否在线）

## 整体架构

![mqtt-architecture-overview](/images/mqtt/mqtt-architecture-overview.jpg "mqtt-architecture-overview")

### 参与的角色

如上图所示，参与通信的角色有三方：
1. Publisher: 消息发布者，向指定名称的 `Topic` 发送消息； 
2. Broker: 消息中转者，负责消息的路由转发，路由包括 Broker 间消息路由及单 Broker 终端路由；
3. Subscirber: 消息订阅者，向 Broker 订阅指定的 `Topic`, Broker 根据特定的规则匹配满足条件的 Subscirber.

### 整体流程：
1. Subsriber 订阅 `Topic`, Broker 保存 `Topic` 与该终端的订阅关系，同时会将该订阅消息广播给所有的 Broker, 建立起 Broker 间的订阅关系；
2. Publisher 发送消息到指定的 `Topic`，该消息发送到其中一台 Broker 上；
3. Broker 根据 Broker 间的订阅关系，将消息转发给订阅该 `Topic` 的 broker，Broker 最终根据匹配规则找到对应的终端，并将消息转发给该终端；
4. Subscirber 收到消息并进行处理。

### 用户会话数据

每一个终端登陆 Broker 之后，会生成生个对应的 Session 对象，该对象代表了一个在线的终端。消息的订阅及推送都是以 Session 为单位进行的，一个 Session 对象包含了如下的数据：1）登陆数据；2）QoS 数据；3）Topic Offset；4）Will Topic。

**1. 终端登陆数据**

这些数据包括：clientId, 用户名，登陆的 broker 信息及在线状态。如果一个终端重复登陆，它会迫使之前的终端下线。由于前后两次登陆可能位于不同的 Broker 上，所以需要存储登陆的 Broker 信息，方便进行通知其终端下线。

**2. QoS 数据**

包括：
- 已经发送给客户端， 但是还没有完成确认的 QoS 1 和 QoS 2 级别的 PUBLISH 消息；
- 即将传输给客户端的 QoS 1 和 QoS 2 级别的消息；
- 客户端已经接收， 但是还没有完成确认的 QoS 2 级别的 PUBREL 消息；
- 准备发送给客户端的 QoS 0 级别的消息（可选）。

**3. Topic Offset**

为了保证 QoS，Session 需要记录 `Topic` 当前消费的进度，方便终端异常下线之后也能消费之前的数据。


**4. Will Topic**

终端在登陆时，可以指定 `Will Topic`，当终端异常下线时便可向该 `Topic` 推送终端异常下线消息。 

### 缓存数据

除了与用户相关的会话数据需要缓存之外，还需要缓存一些全局数据，方便快速访问。

**1. Retain 数据**

每一个 `Topic` 可以维护一条 `Retain` 数据，每当有新终端订阅该 `Topic` 时，便可把该数据推送给新终端。

**2. 订阅数据**

终端 `Topic` 订阅关系需要缓存，避免终端异常下线之后订阅关系丢失。

### 持久化数据

要满足 QoS 1 和 QoS 2 级别的服务要求，需要将消息进行持久化，保证在异常情况下，数据也不会丢失。持久化数据需要满足以下条件：
1. `Topic` offset(或 id ) 实现全局自增，根据 offset 的大小便可判断出是否有未消费的数据；
2. 可以按照 offset(或 id) 实现精准查询；
3. 也可以按照 offset 实现快速范围查询。

</br>

**参考：**

----
[1]:https://mp.weixin.qq.com/s?__biz=Mzg2NDcxMzgzMA==&mid=2247485615&idx=1&sn=da584abbf1ced2e6cedbaa74bc219221&chksm=ce6465a6f913ecb080b28307f0e0a60abac175535d3b92289dd7c44ffc27d7fa5a017d15d34a&token=414245110&lang=zh_CN#rd
[2]:https://mp.weixin.qq.com/s/Fd92fkl5ZwQ0ZQDvLtQZ5A
[3]:https://www.hivemq.com/blog/how-to-get-started-with-mqtt/
[4]:https://www.emqx.com/zh/blog/what-is-the-mqtt-protocol


[1. 基于 RocketMQ 的 MQTT 服务架构在小米的实践][1]

[2. 干货分享 | 基于RocketMQ构建MQTT集群系列（1）—从MQTT协议和MQTT集群架构说起][2]

[3. Introduction to MQTT][3]

[4. 物联网首选协议，关于 MQTT 你需要了解这些][4]
