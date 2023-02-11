---
title: Mqtt 系列：持久化
date: 2023-02-05 16:41:06
tags:
- MQTT
- 持久化
categories:
- MQTT
---

这篇文章主要讲述在 `MQTT Broker` 中数据如何进行持久化操作，包括什么数据需要进行持久化 `(WHO)` 以及怎么进行持久化操作 `(HOW)`。 

<!-- more -->

## 概述

根据存活时间的长短，可以将数据分为两种类型：
1. 会话数据：跟 `Client` 会话同周期，随着 `Client` 退出而销毁，如会话状态、发送/接收中的数据、`Will` 数据及订阅数据；
2. 静态数据：需要长时间存在的数据，如用户及 `QoS 1&2` 级别的数据。

根据数据存储的特性，两种类型的数据分别使用不同的持久化工具，对于会话数据而言，根据需要实时读取及存活周期较短的特性，可以使用缓存来进行存储，如 `Redis`； 而对于需要长期存储的静态数据，可以使用数据库来进行存储，如 `Mysql`. 在本文中，便是使用了 `Redis` 和 `Mysql` 来存储数据；

## 会话数据

在 `MQTT broker` 中，会话数据包括以下类型：
- 会话信息及状态；
- 发送/接收中的 `QoS 1&2` 数据；
- `Topic` 消息消费偏移量；
- `Will` 数据；
- 订阅数据(Subscription); 
- `Retain` 数据（严格来说，它并不算会话数据，只是适合用缓存存储）。

### 会话信息及状态
会话代表了一次 `Client` 的登陆，`Client` 后续的操作都需要绑定在会话上。

**1. 数据格式**

```java
public class StoredSession {

    /**
     * 会话所属的客户端 id
     */
    private String clientId;

    /**
     * 用户名称
     */
    private String userName;

    /**
     * 会话是否保持
     */
    private boolean clean;

    /**
     * 所在的 Broker 服务器 id
     */
    private int serverId;

    /**
     * 会话状态
     */
    private int status;

    /**
     * 创建时间
     */
    private long timestamp;

}
```

**说明：**
- clean: 表明会话是否保持，如果不保持，则每一次登陆都是一个新的会话；
- serverId: 表明登陆的 `Broker id`, 客户端重新登陆之后，可能不在之前的 `Broker` 上。

**2. 操作方法**

```java
public interface ClientSessionRepository {

    /**
     * 获取指定 clientId 的会话信息
     *
     * @param clientId 客户端id
     * @return 客户端会话
     */
    StoredSession getSession(String clientId);

    /**
     * 添加 clientId 的会话消息
     *
     * @param clientId 客户端id
     * @param session  会话信息
     */
    void addSession(String clientId, StoredSession session);

    /**
     * 更新 clientId 的会话消息
     *
     * @param clientId 客户端id
     * @param session  会话信息
     */
    void updateSession(String clientId, StoredSession session);

    /**
     * 移除 clientId 的会话信息
     *
     * @param clientId 客户端id
     */
    void removeSession(String clientId);

    /**
     * 是否包含会话
     * @param clientId 客户端id
     * @return 是否存在
     */
    boolean contain(String clientId);

}
```

**3. 存储格式**
```java
/**
 *  Client Session 的 redis key
 *  格式：s:ol:{clientId}
 *  数据类型：String
 */
private static final String SESSION_KEY_FORMAT = "s:ol:%s";
```

### 发送/接收中的 `QoS 1&2` 数据
发送中的数据包括：1）`QoS 1&2` 级别中已发送但未确认的 `PUBLISH` 消息；2）`QoS 2` 级别中已发送但未确认的 `PUBREL` 消息；接收中的数据包括 `QoS 2` 级别的 `PUBLISH` 消息。

**1. 数据格式**

```java
public class PublishInnerMessage{

    /**
     * 消息主题
     */
    private String topic;

    /**
     * 是否是 Retain 数据
     */
    private boolean retain;

    /**
     *  qos 级别
     */
    private int qos;

    /**
     * 消息内容
     */
    private byte[] payload;

    /**
     * 消息的 packageId
     */
    private int messageId;

    /**
     * 产生的时间戳
     */
    private long timestamp;

}

```

**2. 操作方法**

```java
public interface InflightMessageRepository {

    /**
     * 添加正在发送中或接收中的 Publish 消息
     *
     * @param clientId  客户端id
     * @param message   Publish 消息
     * @param isSending 发送中/接收中
     */
    void addMessage(String clientId, PublishInnerMessage message, boolean isSending);

    /**
     * 移除正在发送中或接收中的 Publish 消息
     *
     * @param clientId  客户端id
     * @param packetId  消息id
     * @param isSending 发送中/接收中
     */
    void removeMessage(String clientId, int packetId, boolean isSending);

    /**
     * 获取正在发送中或接收中的 Publish 消息
     *
     * @param clientId  客户端id
     * @param packetId  消息id
     * @param isSending 发送中/接收中
     */
    PublishInnerMessage getMessage(String clientId, int packetId, boolean isSending);

    /**
     * 获取所有正在发送中或接收中的 Publish 消息
     *
     * @param clientId  客户端id
     * @param isSending 发送中/接收中
     */
    List<PublishInnerMessage> getAllMessages(String clientId, boolean isSending);

    /**
     * 判断是否包含该 packetId
     *
     * @param clientId  客户端id
     * @param packetId  消息id
     * @param isSending 发送中/接收中
     * @return
     */
    boolean contain(String clientId, int packetId, boolean isSending);

    /**
     * 添加发送中的 PubRel消息，只需要存储 packetId 即可
     *
     * @param clientId 客户端id
     * @param packetId 消息id
     */
    void addPubRel(String clientId, int packetId);

    /**
     * 移除发送中的 PubRel消息
     *
     * @param clientId 客户端id
     * @param packetId 消息id
     */
    void removePubRel(String clientId, int packetId);

    /**
     * 获取所有发送中的 PubRel消息
     *
     * @param clientId 客户端id
     */
    Set<Integer> getAllPubRel(String clientId);

    /**
     * 清空 inflight 数据
     * @param clientId 客户端id
     */
    void clean(String clientId);

}
```

**3. 存储格式**
```java
/**
 *  存放发送中的 QOS1&2 PublishMessage 消息
 *  格式：s:f:p:{clientId}
 *  数据类型：Hash,{key=packetId, value=message}
 */
private static final String SESSION_INFLIGHT_KEY_FORMAT = "s:f:p:%s";

/**
 *  存放发送中的 QOS2 PubRel 消息
 *  格式：s:f:r:{clientId}
 *  数据类型：Set,{packetId...}
 */
private static final String SESSION_PUBREL_KEY_FORMAT = "s:f:r:%s";

/**
 *  存放收到的 QOS1&2 PublishMessage 消息
 *  格式：s:f:r:{clientId}
 *  数据类型：Hash,{key=packetId, value=message}
 */
private static final String SESSION_RECEIVE_KEY_FORMAT = "s:f:ri:%s";
```

### `Topic` 消息消费偏移量
会话中需要记录 `QoS 1&2` 级别消息的消费偏移量，这样可以保证 `QoS 1&2` 消息的语义，消息不会丢，下次登陆时，可以继续消费之前数据。同时，根据偏移量可以实时判断出是否有数据丢失，再从数据库读取缺失的数据，从而保证数据的可靠性。

**1. 数据格式**

只要记录 `Client`, `Topic` 及 `Offset` 三者之间的关系即可。

**2. 操作方法**

```java
public interface OffsetRepository {

    /**
     * 添加指定 clientId 下指定 topic 的消费进度
     *
     * @param clientId 客户端id
     * @param topic    消息主题
     * @param offset   消费进度
     */
    void addTopicOffset(String clientId, String topic, long offset);

    /**
     * 更新指定 clientId 下指定 topic 的消费进度
     *
     * @param clientId 客户端id
     * @param topic    消息主题
     * @param offset   消费进度
     */
    void updateTopicOffset(String clientId, String topic, long offset);

    /**
     * 获取指定 clientId 下指定 topic 的消费进度
     *
     * @param clientId 客户端id
     * @param topic    消息主题
     */
    int getTopicOffset(String clientId, String topic);

    /**
     * 获取指定 clientId 下所有 topic 的消费进度
     *
     * @param clientId 客户端id
     * @return 消费进度
     */
    Map<String, Integer> getAllTopicOffsets(String clientId);

}
```

**3. 存储格式**
```java
/**
 *  存放 QOS1&2 级别 Topic 的 offset 位置
 *  格式：s:t:{clientId}
 *  数据类型：Hash,{key=topic, value=offset}
 */
private static final String SESSION_TOPIC_OFFSET_FORMAT = "s:t:%s";
```

### `Will` 数据

`Will` 数据主要是 `Client` 异常下线之后发送的消息。

**1. 数据格式**
```java
public class Will {
    /**
     * 消息主题
     */
    private String topic;

    /**
     * 消息内容
     */
    private byte [] payload;

    /**
     * QoS 级别
     */
    private int qos;

    /**
     * 是否是 retain 数据
     */
    private boolean retained;
}
```

**2. 操作方法**

```java
public interface WillRepository {

    /**
     * 获取指定 clientId 的Will消息
     *
     * @param clientId 客户端id
     * @return Will消息
     */
    Will getWill(String clientId);

    /**
     * 添加指定 clientId 的Will消息
     *
     * @param clientId 客户端id
     * @param will     Will 消息
     */
    void addWill(String clientId, Will will);

    /**
     * 更新指定 clientId 的Will消息
     *
     * @param clientId 客户端id
     * @param will     Will 消息
     */
    void updateWill(String clientId, Will will);

    /**
     * 移除指定客户端的Will消息
     *
     * @param clientId 客户端id
     */
    void removeWill(String clientId);

}
```

**3. 存储格式**
```java
/**
 *  存放客户端的 Will 信息
 *  格式：s:t:{clientId}
 *  数据类型：String
 */
private static final String SESSION_WILL_FORMAT = "s:w:%s";
```

### 订阅数据(Subscription)

订阅数据(Subscription) 主要是存储 `Client` 与 `Topic` 之间的订阅关系。

**1. 数据格式**
```java
public class StoredSubscription {

    /**
     * 服务级别
     */
    private int qos;

    /**
     * 客户端id
     */
    private String clientId;

    /**
     * topic 过滤器
     */
    private String topicFilter;
}
```

**2. 操作方法**
```java
public interface SubscriptionsRepository {

    /**
     * 获取指定 clientId 的订阅信息
     *
     * @param clientId 客户端id
     * @return 订阅关系列表
     */
    List<StoredSubscription> getAllSubscriptions(String clientId);

    /**
     * 向指定 clientId 下添加订阅关系
     *
     * @param clientId     客户端id
     * @param subscription 订阅关系
     */
    void addSubscription(String clientId, StoredSubscription subscription);

    /**
     * 移除指定clientId下的订阅关系
     *
     * @param clientId 客户端id
     * @param topic    topicFilter
     */
    void removeSubscription(String clientId, String topic);
}
```

**3. 存储格式**
```java
/**
 *  存放客户端的订阅关系
 *  格式：s:s:{clientId}
 *  数据类型：Hash,{key=topic, value=subscription}
 */
private static final String SESSION_SUBSCRIPTION_FORMAT = "s:s:%s";
```

### `Retain` 数据

`Retain` 数据实际是设置在 `Topic` 维度上的，与单个 `Client` 没有关系。它是类似 `Topic-->List` 的结构，便于使用 `Redis` 中的 `KV` 结构进行存储。

**1. 数据格式**
```java
public class RetainedMessage {

    /**
     * QoS 级别
     */
    private int qos;

    /**
     * 消息内容
     */
    private byte[] payload;
}
```

**2. 操作方法**
```java
public interface RetainedRepository {

    /**
     * 清空topic下的Retain消息
     *
     * @param topic 消息主题
     */
    void clean(String topic);

    /**
     * 向指定topic下添加Retain消息
     *
     * @param topic 消息主题
     * @param msg   Retain消息
     */
    void addRetainMessage(String topic, RetainedMessage msg);

    /**
     * 获取topic下所有的 Retain消息
     *
     * @param topic 消息主题
     * @return Retain消息列表
     */
    List<RetainedMessage> getAllRetainMessage(String topic);
}
```

**3. 存储格式**

```java
/**
 *  存放 Topic 的 Retain 信息
 *  格式：t:r:{topic}
 *  数据类型：List
 */
private static final String TOPIC_RETAIN_FORMAT = "t:r:%s";
```

## 静态数据

静态数据的特点是需要长期存储且访问不是很频繁，适合存储到数据库中。

### 消息存储

经过确认的 `QoS 1&2` 级别的消息最终会存储到数据库中，主要有两个作用：1）可以读取离线数据；2）可以解决消息在集群中传递丢失的问题（消息经过确认落库之后再广播消息，可能存在消息丢失的问题）。这个两个功能都要结合 `Client Offset` 来实现；

**1. 数据格式**
```java
public class StoredMessage {

    /**
     * 逻辑主键，自增id
     */
    private long id;

    /**
     * 消息id
     */
    private int packageId;

    /**
     * 消息主题
     */
    private String topic;

    /**
     * 服务级别
     */
    private int qos;

    /**
     * 消息内容
     */
    private byte[] payload;

    /**
     * 全局id
     */
    private long offset;
}
```
**说明：**
- packageId: 消息 id, 在一次会话中是惟一的，同一个 `Client` 不同会话间, packageId 有可能会重复；
- offset：全局消息 id, 在同一个 `Topic` 中, `offset` 是惟一的，不会重复。

在现有的实现中。全局消息 id 通过 `Redis` 的自增 `String Key` 来实现，其定义如下：

```java
/**
 *  存放 Topic 当前 offset
 *  格式：t:o:{topic}
 *  数据类型：String(int)
 */
private static final String TOPIC_OFFSET_FORMAT = "t:o:%s";
```

**2. 操作方法**

```java
public interface MessageRepository {

    /**
     * Publish 消息入库
     * Offset: 全局的消息id
     *
     * @param msg Publish 消息
     */
    void addMessage(StoredMessage msg);

    /**
     * 根据 offset 获取消息id
     *
     * @param topic  消息主题
     * @param offset offset
     * @return Publish 消息
     */
    StoredMessage getMessage(String topic, long offset);

    /**
     * 获取指定 offset 之后的消息
     *
     * @param topic       消息主题
     * @param startOffset 起始的offset
     * @return 消息列表
     */
    List<StoredMessage> getAllMessage(String topic, long startOffset);
}
```

消息根据 `offset` 可以实现精准及范围查询。

### 用户信息

用户信息主要是存储用户基本信息，包括用户名及密码信息。

**1. 数据格式**
```java
public class StoredUser {

    /**
     * 用户名
     */
    private String username;

    /**
     * 密码
     */
    private String password;

    /**
     * 状态
     */
    private byte status;
}
```

**2. 操作方法**
```java
public interface UserRepository {

    /**
     * 根据用户名查询用户信息
     *
     * @param username 用户名
     * @return 用户数据
     */
    StoredUser findUser(String username);

}
```

可以根据用户名查询用户信息。







