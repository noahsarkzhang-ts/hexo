---
title: Alligator 系列：Alligator RPC
date: 2021-12-26 11:52:48
updated: 2021-12-26 11:52:48
tags:
- RPC
- RpcPromise
- PromiseHolder
- 双向通信
categories:
- Alligator网关
---

## 概述
在一个长连接网关系统中，客户端与网关之间使用 TCP/Websocket 协议通信，网关与业务服务之间为了解耦，一般使用 MQ 进行通信。

![RPC-end2end](/images/alligator/RPC-end2end.jpg "RPC-end2end")

<!-- more -->

虽然底层协议不同，但上层的 RPC 协议却是一致的，在 Alligator 系统中，提供了一层抽象的 RPC 协议，可以实现相同的 RPC 语义。如下图所示：
![RPC-abstract](/images/alligator/RPC-abstract.jpg "RPC-abstract")
- RpcPromise: RPC 最关键的类，封装了一次 PRC 调用，它有如下功能：1）异步操作，或异步转同步；2）支持消息的组播；3）支持消息的流处理；4）支持调用超时处理。
- RpcCommand: RPC 消息类，包括请求及响应消息，它定义了统一的消息头，在下文专门讲述；
- PromiseHolder：RpcPromise 对象的生命周期管理类，负责管理维护所有的 RpcPromise，其中包括生成 request id，删除 RpcPromise等等。PromisHolder 主要由 RPC 的调用方（客户端）维护。在 MQ 的实现中，request id 是全局惟一的，而在 TCP/Websocket 中，request id 只需要保证在一个 Connnection(一个客户端连接一个服务器称为一个 Connection) 惟一即可。
- ChannelHolder：一次 RPC 调用在服务器端的会话（Session）信息，它维护了一次 RPC 的相关状态数据，如客户端信息，以便写入响应数据。

不同的协议接入PRC，实现 PromiseHolder 和 ChannelHolder 两个接口即可，可以根据协议的不同特点，实现其独特的功能，如在 TCP/Websocket 实现中，request id 只要保证在一个 Connection 惟一，而在 MQ 实现中，request id 是全局惟一，即要求在所有 Topic 中保持惟一。
![alligator-rpc](/images/alligator/alligator-rpc.jpg "alligator-rpc")

## 通信模型
在 Alligator 系统中，PRC 提供了1）客户端及服务器双向通信；2）Request-Respose 模式；3）Send-Oneway 模式；4）Request-Stream 模式；5）组播等功能。 
### 双向通信

在双向通信模式中，客户端、网关及业务服务都可以作为客户端向对方发起 RPC 请求，同是，也可以作为服务器接收客户端的请求。

![bidirection-commu](/images/alligator/bidirection-commu.jpg "bidirection-commu")

### Request-Response
该模式是最常用的模式，一个请求对应一个响应，响应结束之后，该 RPC 请求的生命周期也就结束了。该功能主要由 RpcPromise 提供。
![unary-rpc](/images/rpc/unary-rpc.jpg "unary-rpc")

### Send-Oneway
相对于 Request-Response 模式，Send-Oneway 只发送请求没有响应，也不用生成 RpcPromise 对象。
![send-oneway](/images/rpc/send-oneway.jpg "send-oneway")

### Request-Stream
该模式是在 Request-Response 扩展而来，在 Request-Response 模式中，只要收到第一个响应之后就认为该 RPC 可以结束了，但是在 Request-Stream 中，响应是一股流，必须由服务器明确发送结束标志告诉客户端响应结束。
![request-stream-rpc](/images/rpc/request-stream-rpc.jpg "request-stream-rpc")

### Multicast
在网关系统中，存在服务器向多个客户端发送请求的场景，在 Alligator RPC 中，提供了 Multicast 模式来支持这种场景。它的实现跟 Request-Stream 类似，只是在如何判断结束上有差异，在 Multicast 中明确知道接收多少个响应（一个请求对应一个响应），只需要判断响应的数量与请求数据相等即可。

![RPC-multicast](/images/alligator/RPC-multicast.jpg "RPC-multicast")

## 协议
### RpcCommand
RpcCommand 类代表 PRC 的消息，其定义如下图所示：
![RpcCommand](/images/alligator/RpcCommand.jpg "RpcCommand")

协议头相关字段：
- requestId：请求 id, 用于表示一次请求；
- biz：业务分类，代表后端的业务，可用于网关进行服务路由；
- cmd：命令 id, 代表具体的请求；
- type：消息类型，1：请求，2：响应，3：oneway，4：stream;
- end：流结束标志位，是否最后一个响应，0：不是，1：是；
- ver：接口版本；
- serializer：序列化类型；
- topic：发起方 topic, 用于接收结果；
- targetIds：目标用户，结合 topic 实现 Multicast 模式。

其它主要字段：
- fanout：用于表示响应的个数，如果用于判断 Multicast 模式下请求是否结束；
- payload：消息体。

### RpcPromise
RpcPromise 是实现 RPC 功能的核心类，Request-Response、Request-Stream 及 Multicast 模式都是由该类实现，其基本结构如下所示：
![rpc-promise](/images/alligator/rpc-promise.jpg "rpc-promise")

RpcPromise 本质是实现了生产者/消费者模式一个对象，通过它，调用方和被调用方可以同步/异步地交换结果数据。它存储了两类数据：
- result：结果对象；
- listeners：监听器列表，包含了回调处理逻辑。

**生产者（被调用方）：**
通过 setSuccess(成功) 和 setFailure(失败) 方法，通知调用方有结果；

**消费者（调用方）：**
调用方可以通过两种方式获取结果：
- get：同步方式，此方法消费者线程被阻塞，直到有结果；
- 添加 GenericFutureListener：异步方式，注册回调方法，有结果的时候被调用。

### Request-Response 实现
RpcPromise 本身就是一个 Request-Response 模式的实现，调用方发起一个 RPC 调用，得到一个 RpcPromise 对象。服务器返回结果，根据 requestId 找到对应的 RpcPromise ，调用 setSuccess(成功) 和 setFailure(失败) 方法通知调用方处理结果。

### Request-Stream 实现
基本的 RpcPromise 实现了 Request-Response 语义，要支持 stream 流的方式，必须对 RpcPromise 进行扩展。在 Request-Response 中，收到第一个 Response 之后，RpcPromise 生命周期便结束了便要释放其对象。在 Request-Stream 中必须有明确的标志表示流结束。在 Alligator 中，扩展的地方包括以下几个方面：
- 消息头中加入流结束标志位(end 字段)，表示流正常结束；
- 扩展结果字段，引入一个阻塞队列，缓存多个 Response；
- 扩展 setSuccess 语义，可处理多个结果；
- 扩展 RpcPromise 生命周期，只有收到结束标志位才清除 RpcPromise。

相关代码如下所示：

```java

/**
 * 1. RpcCommand 加入消息头中加入流结束标志位(end 字段)
 */
private byte end;

/**
 * 2. RpcPromise 中加入塞队列，用于缓存收到的Response数据
 */
private BlockingQueue<Object> streams = new LinkedBlockingQueue<>();

/**
 * 3. RpcPromise 加入对中间数据的处理
 */
public StreamPromise<Object> flow(Object result) {

    if (!PromiseEnum.STREAM.equals(this.type)) {
        throw new OperationNotSupported();
    }

    // 1、加入队列
    if (result != null) {
        streams.offer(result);
    }

    // 2、调用回调
    safeExecute(EVENT_EXECUTOR, () -> notifyListeners());

    return this;
}

/**
 * 4. RpcPromise 加入对最后一个响应的处理，并设置流结束标志
 */
public StreamPromise<Object> end(Object result) {

    if (!PromiseEnum.STREAM.equals(this.type)) {
        throw new OperationNotSupported();
    }

    // 1、加入队列
    if (result != null) {
        streams.offer(result);
    }

    // 2、设置结束标志
    isStop = true;

    // 3、调用回调
    safeExecute(EVENT_EXECUTOR, new Runnable() {
        @Override
        public void run() {
            notifyListeners();
        }
    });

    return this;
}

/**
 * 5. 判断 Promis 是否可以被移除，以下条件返回true:
 * 1）已经调用 setFailure;
 * 2) 是否已经结束（流模式下）;
 * 3）所有结果已经返回（Multicast模式下）
 *
 * @return 是否移除
 */
public synchronized boolean isRemoving() {

    if (isRemoved) {
        return false;
    }

    isRemoved = isFailure || isStop || this.currentFanout.get() >= fanout;

    return isRemoved;

}
```

### Multicast 实现
Multicast 与 Request-Stream 相同的逻辑，都是处理多个响应结果，差异的地方在于流结束的方式。

```java
public Promise<Object> setSuccess(Object result) {

    /**
     * GENERAL：正常调用,返回结果之后，Promise 不再允许调用；
     * MULTIPLE：将多次返回结果存放到缓存中，批量调用；
     * STREAM：执行 end 操作。
     */
    if (PromiseEnum.GENERAL.equals(this.type)) {
        this.currentFanout.incrementAndGet();

        return super.setSuccess(result);
    } else if (PromiseEnum.MULTIPLE.equals(this.type)) {
        if (this.currentFanout.get() > this.fanout) {
            return this;
        }

        // 1、 响应结果数加 1
        this.currentFanout.incrementAndGet();

        // 2、加入队列
        if (result != null) {
            streams.offer(result);
        }

        // 3、调用回调
        safeExecute(EVENT_EXECUTOR, () -> notifyListeners());
    } else if (PromiseEnum.STREAM.equals(this.type)) {
        this.end(result);
    }

    return this;
}
```
在 RpcPromise 中维护一个当前的结果数量，每收到一个结果，数量自增加 1, 当结果数量等于请求数量，则该请求结束。

## 结论
在 Alligator 系统中，实现了一个抽象的 RPC 层，而与底层协议无关，如 TCP/Websocket, MQ. 在项目开发中，开发人员只需关注业务开发，而无需关注底层 RPC 实现，从而可以极大提高开发效率。