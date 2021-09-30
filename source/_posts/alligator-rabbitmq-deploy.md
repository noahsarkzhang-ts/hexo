---
title: Alligator 系列：Rabbitmq 基础知识及部署
date: 2021-09-30 09:12:20
tags:
- rabbitmq
categories:
- Alligator网关
---

## 1. 基础
### 1.1 Consumer ACK 机制

Consumer ACK 有两种模式：1）自动；2）手动。在自动模式下，Broker 分发消息之后即认为分发成功，便可删除消息，该模式被认为是不安全的。而自动模式需要程序手动发送 Ack 确认信息，这样可以保证消息被处理。

官方文档对自动模式描述如下：
> In automatic acknowledgement mode, a message is considered to be successfully delivered immediately after it is sent. This mode trades off higher throughput (as long as the consumers can keep up) for reduced safety of delivery and consumer processing. This mode is often referred to as "fire-and-forget". Unlike with manual acknowledgement model, if consumers's TCP connection or channel is closed before successful delivery, the message sent by the server will be lost. Therefore, automatic message acknowledgement should be considered unsafe and not suitable for all workloads.

通过下面方法来设置自动或手动：
```java
boolean autoAck = false;

channel.basicConsume(queueName, autoAck, "a-consumer-tag",
     new DefaultConsumer(channel) {
         @Override
         public void handleDelivery(String consumerTag,
                                    Envelope envelope,
                                    AMQP.BasicProperties properties,
                                    byte[] body)
             throws IOException
         {
             long deliveryTag = envelope.getDeliveryTag();
             // negatively acknowledge, the message will
             // be discarded
             channel.basicReject(deliveryTag, false);
         }
     });
```
默认是自动模式，可以在 channel.basicConsume 方法中设置为 false。

**手动 Ack 有三个方法：**
- basic.ack : 用于肯定应答；
- basic.nack ：用于否定应答，可以重新 requeue 排队发送；
- basic.reject ：用于否定应答，与 nack 的区别在于是否支持批量确认。

**basic.ack 方法定义：**
```java
long deliveryTag = envelope.getDeliveryTag();

channel.basicAck(long deliveryTag, boolean multiple);
```
其中，
- deliveryTag : 消息的唯一标示，在一个channel 中一个消息具有唯一的 deliveryTag；
- multiple ：是否批量确认，true 表示 deliveryTag 之前的消息都被确认，false 只确认当前消息。

**basic.nack 方法定义：**
```java
long deliveryTag = envelope.getDeliveryTag();

channel.basicNack(long deliveryTag, boolean requeue, boolean multiple);
```
其中，
- deliveryTag : 消息的唯一标示，在一个channel 中一个消息具有唯一的 deliveryTag；
- requeue : 是否重新排队发送，true 表示重新排队，false 表示删除该消息；
- multiple ：是否批量确认，true 表示 deliveryTag 之前的消息都被确认，false 只确认当前消息。

**basic.reject方法定义：**
```java
long deliveryTag = envelope.getDeliveryTag();

basic.reject(long deliveryTag, boolean requeue);
```
其中，
- deliveryTag : 消息的唯一标示，在一个channel 中一个消息具有唯一的 deliveryTag；
- requeue : 是否重新排队发送，true 表示重新排队，false 表示删除该消息；

### 1.2 QoS

### 1.3 Producer Comfirm

### 1.4 持久化 

## 2. 部署
### 2.1 命令
使用 docker 部署单机版本，版本使用的是 3.9。
```bash
docker run -d --hostname my-rabbit --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.9-management
```
