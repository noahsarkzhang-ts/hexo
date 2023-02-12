---
title: Mqtt 系列：QoS
date: 2022-12-31 18:50:17
tags:
- QoS
- 服务质量
- 可靠性
categories:
- MQTT
---

MQTT 协议提供了 3 种消息服务质量等级（Quality of Service），保证了在不同的网络环境下消息传递的可靠性。本文讲解这 3 种 QoS 的实现。

<!-- more -->

## 概述

很多时候，使用 MQTT 协议的设备都运行在网络受限的环境下，而只依靠底层的 TCP 传输协议，并不能完全保证消息的可靠到达。因此，MQTT 提供了 QoS 机制，其核心是设计了多种消息交互机制来提供不同的服务质量，来满足用户在各种场景下对消息可靠性的要求。

MQTT 定义了三个 QoS 等级，分别为：

- QoS 0：消息最多传递一次
如果当客户端不可用，则会丢失该消息。发布者发送一条消息之后，就不再关心它有没有发送到对方，也不设置任何重发机制。

- QoS 1：消息传递至少 1 次
包含了简单的重发机制，发布者发送消息之后等待接收者的 ACK，如果没收到 ACK 则重新发送消息。这种模式能保证消息至少能到达一次，但无法保证消息重复。

- QoS 2：消息仅传送一次。
设计了重发和重复消息发现机制，保证消息到达对方并且严格只到达一次。

其中，使用 QoS 0 可能丢失消息，使用 QoS 1 可以保证收到消息，但消息可能重复，使用 QoS 2 可以保证消息既不丢失也不重复。QoS 等级从低到高，不仅意味着消息可靠性的提升，也意味着传输复杂程度的提升。

在一个完整的从发布者到订阅者的消息投递流程中，QoS 等级是由发布者在 PUBLISH 报文中指定的，大部分情况下 Broker 向订阅者转发消息时都会维持原始的 QoS 不变。不过当订阅者的 QoS 级别小于原始的 QoS 时，Broker 转发的消息以订阅者的 QoS 为准。

## QoS

![qos-full-flow](/images/mqtt/qos-full-flow.jpg "qos-full-flow")

在一个完整的消息投递流程中，包括 Publisher --> Broker, Broker --> Subscriber 两个环节，它们的处理流程是一致的，我们将选择 Publisher --> Broker 进行描述。

### QoS 0

QoS 0 是消息投递效率最高的服务级别，其流程如下所示：

![qos0](/images/mqtt/qos0.jpg "qos0")

在该级别中由于没有确认机制，不能保证 Broker 一定能收到数据。

在 Broker 中收到 QoS 0 之后，处理也比较简单，广播消息即可。

```java
public void receivedPublishQos0(MqttSession session, PublishInnerMessage msg) {

    // 1. 验证 topic
    if (!validateTopic(session, msg)) {
        LOG.info("Topic is invalid!");

        return;
    }

    Topic topic = msg.getTopic();
    if (msg.isRetain()) {
        // QoS == 0 && retain => clean old retained
        retainedRepository.cleanRetained(topic);
    }

    // 2, QOS0 无需持久化，广播消息即可。
    // MqttPublishMessage --> PublishInnerMessage
    ClusterMessage clusterMessage = new ClusterMessage(ClusterMessage.ClusterMessageType.PUBLISH, msg);
    eventBus.broadcast(clusterMessage);
}
```

**说明：**
> 广播消息是指向其它 Broker 或 本 Broker 中匹配的终端发送 PUBLISH 消息。是否向其它 Broker 结点发送消息取决于其它 Broker 是否订阅了该 `Topic`.

### QoS 1

在 QoS 1 中加入了消息的确认及重发机制，保证 Broker 一定能收到数据，其流程如下：

![qos1](/images/mqtt/qos1.jpg "qos1")

Broker 收到 QoS 1 消息之后，处理流程包括以下几个步骤：
1. 验证 topic 权限，判断用户是否有发送 PUBLISH 的权限；
2. 持久化 PUBLISH 数据，避免消息丢失；
3. 广播 PUBLISH 消息；
4. 发送 PUBACK 确认消息；
5. 处理 `Retain` 数据，后续章节会介绍。

```java
public void receivedPublishQos1(MqttSession session, PublishInnerMessage msg) {
    // 1. 验证 topic
    if (!validateTopic(session, msg)) {
        LOG.info("Topic is invalid!");

        return;
    }

    // 2, QOS1 持久化
    // MqttPublishMessage --> StoredMessage
    StoredMessage storedMessage = convertStoredMessage(msg);
    messageRepository.store(storedMessage);

    // 2. 广播消息
    // MqttPublishMessage --> PublishInnerMessage
    ClusterMessage clusterMessage = new ClusterMessage(ClusterMessage.ClusterMessageType.PUBLISH, msg);
    eventBus.broadcast(clusterMessage);

    // 3. 发送 ACK
    session.getConnection().sendPubAck(msg.getMessageId());

    // 4. 处理 retain 数据
    processDataRetain(msg);

}
```

从流程中也可以看出，如果 `PUBACK` 确认消息丢失，则 Publisher 会重发数据，导致 Broker 重复处理数据。 

### QoS 2

为了解决重复问题，QoS 2 引入新的交互协议，保证 Broker 有且只会收到一条消息。不过每一次的 QoS 2 消息投递，都要求发送方与接收方进行至少两次请求/响应流程，增加了协议的复杂度。其流程如下：

![qos2](/images/mqtt/qos2.jpg "qos2")

Broker 收到 QoS 2 PUBLISH 消息之后, 处理比较简单，只是将其保存到 Session 中，并返回 PUBREC 消息。
```java
public void receivedPublishQos2(MqttSession session, PublishInnerMessage msg) {

    // 1. 验证 topic
    if (!validateTopic(session, msg)) {
        LOG.info("Topic is invalid!");
        return;
    }

    // 2. 存入 Session 会话中,发送 PUBREC 消息
    session.receivedPublishQos2(msg);
}
```

处理逻辑主要包含在 `PUBREL` 消息中，包含如下步骤：
1. 持久化 PUBLISH 数据，避免消息丢失；
2. 删除会话中的 PUBLISH 数据；
3. 广播 PUBLISH 消息；
4. 发送 PUBCOMP 确认消息；
5. 处理 `Retain` 数据，后续章节会介绍。


```java
public void receivePubrel(MqttSession session, PublishInnerMessage msg) {
    // 1, QOS2 持久化
    // MqttPublishMessage --> StoredMessage
    StoredMessage storedMessage = convertStoredMessage(msg);
    messageRepository.store(storedMessage);

    // 2. 删除session中的消息
    session.receivedPubRelQos2(msg.getMessageId());

    // 3. 广播消息
    ClusterMessage clusterMessage = new ClusterMessage(ClusterMessage.ClusterMessageType.PUBLISH, msg);
    eventBus.broadcast(clusterMessage);

    // 3. 发送 PUBCOMP 消息
    session.getConnection().sendPubCompMessage(msg.getMessageId());

    // 4. 处理 retain 数据
    processDataRetain(msg);
}
```

## 结论

MQTT 提供了三种级别的消息投递机制，三种 QoS ，协议越来越复杂，可靠性越来越高，成本也越来越高（吞吐量）。在实际情况中，可以根据业务需求进行选择。


</br>

**参考：**

----
[1]:https://www.emqx.com/zh/blog/introduction-to-mqtt-qos
[2]:https://www.emqx.com/zh/blog/what-is-the-mqtt-protocol


[1. MQTT QoS 0, 1, 2 介绍][1]

[2. 物联网首选协议，关于 MQTT 你需要了解这些][2]
