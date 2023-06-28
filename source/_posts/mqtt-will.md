---
title: Mqtt 系列：Will
date: 2023-01-01 18:53:49
updated: 2023-01-01 18:53:49
tags:
- will
categories:
- MQTT
---

MQTT 提供了遗嘱 Will 功能，可以在终端异常下线时，向特定的 `Will Topic` 发送指定的 `Will Message`, 从而让第三方感知终端的异常下线。

<!-- more -->

## 概述

`Will` 功能可以在 `CONNECT` 控制报文中进行设置，如下所示：

![mqtt-connect-flag](/images/mqtt/mqtt-connect-flag.jpg "mqtt-connect-flag")

`Will` 相关的标志位有三个，分别是：`Will Flag`,`Will QoS`,`Will Retain`, 它们的含义如下：

**1. Will Flag**

遗嘱标志（Will Flag） 设置为 1, 表示设置 `Will` 功能，那么在有效载荷中必须包含 `Will Topic` 和 `Will Message` 字段。在终端异常下线时，便向 `Will Topic` 发送 `Will Message`. 如果服务端收到 DISCONNECT 报文，则不会触发 `Will` 功能，将会清除 `Will` 数据。
遗嘱消息发布的条件， 包括但不限于：

- 服务端检测到了一个 I/O 错误或者网络故障；
- 客户端在保持连接（Keep Alive）的时间内未能通讯；
- 客户端没有先发送 DISCONNECT 报文直接关闭了网络连接；
- 由于协议错误服务端关闭了网络连接。

如果遗嘱标志被设置为 0， 连接标志中的 `Will QoS` 和 `Will Retain` 字段必须设置为 0， 并且有效载荷中不能包含 `Will Topic` 和 `Will Message` 字段。

**2. Will QoS**

用于指定发布遗嘱消息时使用的服务质量等级，如果遗嘱标志被设置为 0， 遗嘱 QoS 也必须设置为 0, 如果遗嘱标志被设置为 1， 遗嘱 QoS 的值可以等于 0(0x00)， 1(0x01)， 2(0x02)。 它的值不能等于 3。

**3. Will Retain**

如果遗嘱标志被设置为 0， 遗嘱保留（Will Retain） 标志也必须设置为 0.
如果遗嘱标志被设置为 1：
- 如果遗嘱保留被设置为 0， 服务端必须将遗嘱消息当作非保留消息发布；
- 如果遗嘱保留被设置为 1， 服务端必须将遗嘱消息当作保留消息发布。

>说明：
`Retain` 消息可以参考之前的文章。 

## 相关代码

代码中，如果检测到网络连接异常断开时，便会触发如下的逻辑：

```java
public void fireWill(Will will) {
    // MQTT 3.1.2.8-17

    PublishInnerMessage publishInnerMessage = new PublishInnerMessage(new Topic(will.getTopic()), will.isRetained(),
            will.getQos(), will.getPayload());

    ClusterMessage clusterMessage = new ClusterMessage(ClusterMessage.ClusterMessageType.PUBLISH, publishInnerMessage);
    eventBus.broadcast(clusterMessage);
}
```

这段代码的逻辑主要是获取到 `Will` 相关信息后，向集群中广播 `Will Message`, 感兴趣的第三方只要订阅 `Will Topic` 即可。
