---
title: Mqtt 系列：Clean Session
date: 2023-01-01 18:53:18
updated: 2023-01-01 18:53:18
tags:
- clean session
categories:
- MQTT
---

MQTT 可以设置是否持久化 Session 数据，这样可以保证终端断线之后重新上线可以恢复之前的 Session 数据。这个功能可以通过 `Clean Session` 设置。

<!-- more -->

## 概述

`Clean Session` 位于 CONNECT 控制报文中，如下所示：

![mqtt-connect-flag](/images/mqtt/mqtt-connect-flag.jpg "mqtt-connect-flag")

`Clean Session` 标志位用来设置客户端和服务端之间的 Session 状态，以支持跨网络连接的可靠消息传输，这个标志位用于控制 Session 状态的生存时间。

如果 CleanSession 标志被设置为 0，服务端必须基于当前 Session （使用客户端标识符识别） 的状态恢复与客户端的通信。如果没有与这个客户端标识符关联的 Session， 服务端必须创建一个新的 Session。

如果 CleanSession 标志被设置为 1， 客户端和服务端必须丢弃之前的 Session 并开始一个新的会话。

要完成 Session 数据的恢复，需要在客户端和服务端两端保存数据，其内容有：

客户端中存储的 Session 数据：
- 已发送给服务端，但是还没有完成确认的 QoS 1 与 QoS 2 消息。
- 从服务端收到的，但是还没有完成确认的 QoS 2 消息。

服务端中存储的 Session 数据：
- 会话是否存在，即使会话状态其余部分为空；
- 已发送给客户端，但是还没有完成确认的 QoS 1 与 QoS 2 消息；
- 等待传输给客户端的 QoS 0 消息（可选），QoS 1 与 QoS 2 消息；
- 从客户端收到的，但是还没有完成确认的 QoS 2 消息。

## 结论

Session 数据有两个特点：1）数据的生存时间与 Session 相关，在 Session 结束之后或数据处理结束之后便会清除，生存时间一般较短；2）数据访问需要较大的吞吐量。鉴于这两点，一般使用缓存服务来存储这些数据，缓存服务包括 Redis, Memcached 等等。 
