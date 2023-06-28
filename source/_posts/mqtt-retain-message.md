---
title: Mqtt 系列：Retain Message
date: 2023-01-01 18:53:39
updated: 2023-01-01 18:53:39
tags:
- retain message
categories:
- MQTT
---

MQTT 可以设置 `Topic` `Retain` 消息，每当有新的订阅关系匹配时，所属的新终端便会收到该 `Retain` 消息。如果有需要在新建订阅时，推送一些初始化信息，可以使用该功能。

<!-- more -->

## 概述

`Retain` 消息在 PUBLISH 控制报文中设置，如下所示：

![mqtt-retain-flag](/images/mqtt/mqtt-retain-flag.jpg "mqtt-retain-flag")

`Retain` 标志位设置为 0 时，不保存消息，如果为 1，则有如下规则：

1. Retain = 1, qos = 0, 清空该 `Topic` 下的 `Retain` 消息； 
```java
public void receivedPublishQos0(MqttSession session, PublishInnerMessage msg) {
    ......
    Topic topic = msg.getTopic();
    if (msg.isRetain()) {
        // QoS == 0 && retain => clean old retained
        retainedRepository.cleanRetained(topic);
    }

    ......
}
```

2. Retain = 1, qos >= 1, 若 playload 为空，则清空消息，若 playload 不为空，则保存消息。
```java
private void processDataRetain(PublishInnerMessage msg) {
    // 1. case 1: retain = 1 且 payload 为 null, 清除 retain 消息
    // 2. case2: retain = 1 且 payload 不为 null，则更新 retain 消息，每一个 topic，retain 消息只保留最新的一条。
    Topic topic = msg.getTopic();
    if (msg.isRetain()) {
        if (msg.getPayload() == null || msg.getPayload().length == 0) {
            retainedRepository.cleanRetained(topic);
        } else {
            // before wasn't stored
            retainedRepository.retain(topic, new RetainedMessage(msg.getQos(), msg.getPayload()));
        }
    }
}
```

在添加新的订阅关系时，如果订阅的 `Topic` 有 `Retain` 消息，则会向其推送 `Retain` 消息，代码如下所示：
```java
private void publishRetainedMessagesForSubscriptions(MqttSession session, List<Subscription> newSubscriptions) {

    for (Subscription subscription : newSubscriptions) {
        final String topicFilter = subscription.getTopicFilter().toString();
        final List<RetainedMessage> retainedMsgs = retainedRepository.retainedOnTopic(topicFilter);

        if (retainedMsgs.isEmpty()) {
            // not found
            continue;
        }
        for (RetainedMessage retainedMsg : retainedMsgs) {
            final MqttQoS retainedQos = MqttQoS.valueOf(retainedMsg.getQos());
            MqttQoS qos = lowerQosToTheSubscriptionDesired(subscription, retainedQos);

            final ByteBuf payloadBuf = Unpooled.wrappedBuffer(retainedMsg.getPayload());
            session.sendRetainedPublishOnSessionAtQos(subscription.getTopicFilter(), qos, payloadBuf);
        }
    }
}
```
