---
title: Alligator 系列：心跳检测
date: 2021-08-14 17:30:36
tags:
- 心跳
- heartbeat
categories:
- Alligator网关

---

## 1. 概述
在长连接系统中，客户端及服务器之间需要通过发送心跳包来感知对方的存活状态，一般来说，心跳包不承载业务信息，不过在一些场景中，会把当前服务的状态推送给对方。在 Alligator 系统中统一在客户端发送心跳包，服务器会检测当前连接的空闲时间（即多久未收到数据），若超过一定时间，则判定为连接断线。在客户端，会检测连接的空闲写时间，超过一定时间，则触发发送心跳包，同时对服务端的响应做计数，超时一定次数未收到心跳响应，则判定服务器下线，触发重连操作。在注册中心系统中，客户端发送的心跳包中，会带上当前客户端的负载信息（连接数或用户数），注册中心根据这些负载信息，可以实现流量的有效负载。

<!-- more -->

## 2. 具体实现
### 2.1 客户端
客户端主要包含两个操作：
1. 借助 IdleStateHandler 触发一个连接空闲事件；
2. 添加一个 Handler，捕获空闲事件，发送心跳包。

在第一个步骤中，使用 Netty 提供的 IdleStateHandler 类来实现连接通道空闲状态的检测，当空闲时间超过设置的数值之后，触发一个连接空闲状态的用户事件。在该类中，提供了读空闲、写空闲或两者时间的配置。在业务中，可以根据具体情况进行设置。在这里，主要是配置写空闲时间。当连接超过一写时间（如 15S）没有写数据，则触发事件，代码如下所示：

```java
ChannelPipeline pipeline = ch.pipeline();
pipeline.addLast(new IdleStateHandler(0, 15, 0));  // 设置写空间时间为 15 S
pipeline.addLast(new ClientIdleStateTrigger(this.client));
```

连接空闲状态的检测是通过向 EventLoop 中加入一个定时任务来实现的，如下所示：
```java
ScheduledFuture<?> schedule(ChannelHandlerContext ctx, Runnable task, long delay, TimeUnit unit) {
    return ctx.executor().schedule(task, delay, unit);
}
```

触发了一个空闲写事件之后，第二步是需要定义一个 Handler 类来处理该事件，一般在该 Handler 类中有两类操作：1）判断计数，如果超过一定次数，触发服务器重连操作；2）发送心跳包

```java
@Override
public void userEventTriggered(ChannelHandlerContext ctx, Object evt) throws Exception {
    if (evt instanceof IdleStateEvent) {
        IdleState state = ((IdleStateEvent) evt).state();
        if (state == IdleState.WRITER_IDLE) {

            log.info("Idle timeout,send heart beat!");

            HeartbeatStatus heartbeatStatus = remotingClient.getConnectionManager()
                .getHeartbeatStatus();

            if (heartbeatStatus.incAndtimeout()) {  // 1. 心跳计数加 1，如果超过 3 次，触发切换服务器操作。
                log.info("server time out, and toggle server");

                heartbeatStatus.reset();

                this.remotingClient.toggleServer();

                return;
            }

            this.remotingClient.ping();  // 2. 发送心跳。
        }
    } else {
        super.userEventTriggered(ctx, evt);
    }
}
 
```
心跳计数在收到心跳响应之后会被重置为 0。

在 Websoket 协议中，已经定义了心跳的格式，如 ping/pong。客户端只要发送 ping 包就行，在 TCP 协议中，需要自己定义消息格式。在 Alligator 系统中，统计定义了一套消息格式，后续文章再补充，其中使用一个特定的命令字段来表示心跳信息，同时业务上，可以根据使用场景的不同，可以自定义心跳包中承载的内容，如负载信息。

### 2.2 服务器
服务器代码则相应的检测连接的读空闲时间，如果没有收到读数据一定时间之后，则触发读空闲事件，服务器会进行连接的清理工作。代码如下所示：
```java
// 1. 设置读空闲时间为 45S，如果 45S内，没有收到请示数据，则触发读空闲事件。
pipeline.addLast(new IdleStateHandler(45, 0, 0));
pipeline.addLast(new ServerIdleStateTrigger());

// 2. 事件处理逻辑
public class ServerIdleStateTrigger extends ChannelInboundHandlerAdapter {
    @Override
    public void userEventTriggered(ChannelHandlerContext ctx, Object evt) throws Exception {
        if (evt instanceof IdleStateEvent) {
            IdleState state = ((IdleStateEvent) evt).state();
            if (state == IdleState.READER_IDLE) {

                // 连接超过，删除会话
                SessionManager.getInstance().disconnect(ctx);
            }
        } else {
            super.userEventTriggered(ctx, evt);
        }
    }
}
```

## 3. 总结
Netty 为心跳的处理、连接的超时提供较好的支持，充分理解这些组件，可以有效地提高开发效率。
