---
title: Netty 系列：ChannelPipeline
date: 2021-08-28 22:48:35
tags:
- ChannelPipeline
- DefaultChannelPipeline
- ChannelHandler
- ChannelHandlerContext
- Intercepting Filter
- 责任链
categories:
- Netty
---

## 1. 概述

ChannelPipeline 可以理解为一个 ChannelHandler 列表，而 ChannelHandler 是一个能够独立处理 channel 入站 (inbound) 事件或出站 (outbound) 操作的处理器。ChannelPipeline 实现了 "Intercepting Filter" 模式，它给用户提供了事件处理及 ChannelHandler 之间交互的能力，用户可以根据业务场景定义 ChannelHandler，以类似插件的方式添加到 ChannelPipeline 中。

### 1.1 整体流程

每一个 channel 都包含一个属于自己的 ChannelPipeline，在创建 channel 的时候自动创建，下图描述了 ChannelPipeline 是如何处理 I/O 事件的，一个 I/O 事件要么被 ChannelInboundHandler 处理，要么被 ChannelOutboundHandler，同时通过 ChannelHandlerContext 将事件传递给下一个 ChannelHandler，如通过如下方法：ChannelHandlerContext#fireChannelRead(Object) 和 ChannelHandlerContext#write(Object)

```
                                                    I/O Request
                                              via Channel or ChannelHandlerContext
                                                        |
                                                        |
    +---------------------------------------------------+---------------+
    |                           ChannelPipeline         |               |
    |                                                  \|/              |
    |    +---------------------+            +-----------+----------+    |
    |    | Inbound Handler  N  |            | Outbound Handler  1  |    |
    |    +----------+----------+            +-----------+----------+    |
    |              /|\                                  |               |
    |               |                                  \|/              |
    |    +----------+----------+            +-----------+----------+    |
    |    | Inbound Handler N-1 |            | Outbound Handler  2  |    |
    |    +----------+----------+            +-----------+----------+    |
    |              /|\                                  .               |
    |               .                                   .               |
    | ChannelHandlerContext.fireIN_EVT() ChannelHandlerContext.OUT_EVT()|
    |        [ method call]                       [method call]         |
    |               .                                   .               |
    |               .                                  \|/              |
    |    +----------+----------+            +-----------+----------+    |
    |    | Inbound Handler  2  |            | Outbound Handler M-1 |    |
    |    +----------+----------+            +-----------+----------+    |
    |              /|\                                  |               |
    |               |                                  \|/              |
    |    +----------+----------+            +-----------+----------+    |
    |    | Inbound Handler  1  |            | Outbound Handler  M  |    |
    |    +----------+----------+            +-----------+----------+    |
    |              /|\                                  |               |
    +---------------+-----------------------------------+---------------+
                    |                                  \|/
    +---------------+-----------------------------------+---------------+
    |               |                                   |               |
    |       [ Socket.read() ]                    [ Socket.write() ]     |
    |                                                                   |
    |  Netty Internal I/O Threads (Transport Implementation)            |
    +-------------------------------------------------------------------+


```

如左边的图所示，入站（inbound）事件从自底向上的方向被 inbound handler 处理，处理的数据来自于 I/O 线程，这些数据通常来自于远程的机器，通过 SocketChannel#read(ByteBuffer) 方法读到。如果一个入站事件传递到了最后一个 inbound handler，它通常会被丢弃，或者日志输出。

出站（outbound）事件从自顶向下的方向被 outbound handler 处理，outbound handler 通常对写数据进行转换或处理，并传递给 I/O 线程，I/O 线程最后通过 SocketChannel#write(ByteBuffer) 方法写入到网络上，传输给远程的机器。

举一个例子，假设以下面的方式创建 pipeline：

```java
ChannelPipeline p = new DefaultChannelPipeline();
p.addLast("1", new InboundHandlerA());
p.addLast("2", new InboundHandlerB());
p.addLast("3", new OutboundHandlerA());
p.addLast("4", new OutboundHandlerB());
p.addLast("5", new InboundOutboundHandlerX());
```

在上面的代码中，以 Inbound 开头的 Handler 代表 InboundHandler，以 Outbound 开头的 Handler 代表 OutboundHandler。对于入站（inbound）事件而言，Handler 执行顺序为 1，2，3，4，5，由于 3 和 4 是 Outbound Handler，执行的时候会直接跳过，真正执行的 Handler 顺序为 1，2，5；对于 Outbound 而言，执行相反的顺序：5，4，3，2，1，跳过 2 和 1，最后的执行顺序为 5，4，3。因为 5 同时实现了 ChannelInboundHandler 和 ChannelOutboundHandler，入站和出站事件都需要执行它。

如果添加的 Handler 比较耗时，建议将该 Handler 提交到指定的线程中处理，以免阻塞 I/O 线程，如下所示：

```java
ChannelPipeline p = new DefaultChannelPipeline();

pipeline.addLast("decoder", new MyProtocolDecoder());
pipeline.addLast("encoder", new MyProtocolEncoder());

EventExecutorGroup group = new  DefaultEventExecutorGroup(16);
pipeline.addLast(group, "handler", new MyBusinessLogicHandler());

```

### 1.2 事件传播

在 ChannelPipeline 中，事件主要主要是通过调用 ChannelHandlerContext 中的方法进行传播，这些方法包括：

**Inbound event propagation method**
- ChannelHandlerContext#fireChannelRegistered()        
- ChannelHandlerContext#fireChannelActive()            
- ChannelHandlerContext#fireChannelRead(Object)        
- ChannelHandlerContext#fireChannelReadComplete()      
- ChannelHandlerContext#fireExceptionCaught(Throwable) 
- ChannelHandlerContext#fireUserEventTriggered(Object) 
- ChannelHandlerContext#fireChannelWritabilityChanged()
- ChannelHandlerContext#fireChannelInactive()          
- ChannelHandlerContext#fireChannelUnregistered() 

**Outbound event propagation method**
- ChannelHandlerContext#bind(SocketAddress, ChannelPromise)
- ChannelHandlerContext#connect(SocketAddress, SocketAddress, ChannelPromise)
- ChannelHandlerContext#write(Object, ChannelPromise)
- ChannelHandlerContext#flush()
- ChannelHandlerContext#read()
- ChannelHandlerContext#disconnect(ChannelPromise)
- ChannelHandlerContext#close(ChannelPromise)
- ChannelHandlerContext#deregister(ChannelPromise)

在处理完当前的 Handler 之后，需要调用 ChannelHandlerContext 中的传播方法，如 ctx.fireChannelActive() 和 ctx.close(promise)，如下面的代码所示：

```java
public class MyInboundHandler extends ChannelInboundHandlerAdapter {
    @Override
    public void channelActive(ChannelHandlerContext ctx) {
        System.out.println("Connected!");
        // 将入站事件传播给下一个 Handler
        ctx.fireChannelActive();
    }
}

public class MyOutboundHandler extends ChannelOutboundHandlerAdapter {
    @Override
    public void close( ChannelHandlerContext ctx, ChannelPromise promise) {
        System.out.println("Closing ..");
        // 将 close 事件传播给下一个 Handler
        ctx.close(promise);
    }
}     

```

## 2. 数据结构
上面讲述了 ChannelPipeline 的整体流程，现在我们分析下 ChannelPipeline 的数据结构及 ChannelPipeline,ChannelHandlerContext,ChannelHandler 三者之间的关系。

### 2.1 整体结构
![netty-channel-pipeline](/images/netty/netty-channel-pipeline.jpg "netty-channel-pipeline")

如图所示：
1. ChannelHandler 与 ChannelHandlerContext 是一一对应关系，ChannelHandlerContext 持有 ChannelHandler 的引用；
2. 多个 ChannelHandlerContext 之间使用双向循环链表进行关联；
3. ChannelPipeline 持有 ChannelHandlerContext 链表 head,tail 结点的引用；
4. HeadContext,TailContext 是特殊的 ChannelHandlerContext，它们不仅继承了 ChannelHandlerContext，也继承了 ChannelHandler，所以不需要引用 ChannelHandler；
5. 入站事件 Handler 执行顺序为：head --> tail，出站事件则相反：tail --> head。

**HeadContext**
HeadContext 是一个特殊的 ChannelHandlerContext，它不仅继承了 AbstractChannelHandlerContext，同时也继承了出站和入站的 ChannelHandler，这有以下的特点：
1. 对于入站事件，它是第一个执行的 ChannelHandler，内部做了一些处理之后，调用 ChannelHandlerContext 相对应的方法，将事件传播给下一个 ChannelHandler；
2. 对于出站事件，它是最后一个执行的 ChannelHandler，它直接调用 AbstractChannel.AbstractUnsafe 的方法，由 AbstractUnsafe 做处理。

```java
final class HeadContext extends AbstractChannelHandlerContext
        implements ChannelOutboundHandler, ChannelInboundHandler {
    
    // 指向 AbstractChannel.AbstractUnsafe
    // 调用 channel 底层的网络接口
    private final Unsafe unsafe;

    HeadContext(DefaultChannelPipeline pipeline) {
        super(pipeline, null, HEAD_NAME, HeadContext.class);
        unsafe = pipeline.channel().unsafe();
        setAddComplete();
    }
    
    // 出站回调，调用底层的 bind 接口
    // HeadContext 是最后一个出站的 handler, 不用再调用 handler
    @Override
    public void bind(
            ChannelHandlerContext ctx, SocketAddress localAddress, ChannelPromise promise) {
        unsafe.bind(localAddress, promise);
    }

    ...
    
    // 入站回调，传播下一个 handler
    @Override
    public void channelRegistered(ChannelHandlerContext ctx) {
        invokeHandlerAddedIfNeeded();
        
        // 将事件传播给下一个 handler
        ctx.fireChannelRegistered();
    }

    @Override
    public void channelRead(ChannelHandlerContext ctx, Object msg) {
        ctx.fireChannelRead(msg);
    }

    ... 
}

```

**TailContext**

TailContext 同样是一个特殊的 ChannelHandlerContext，它除了继承 AbstractChannelHandlerContext，也同时继承了入站的 ChannelInboundHandler，它是最后一个执行的 ChannelInboundHandler，回调的方法大部分是空方法，不做业务处理。

```java
final class TailContext extends AbstractChannelHandlerContext implements ChannelInboundHandler {

    TailContext(DefaultChannelPipeline pipeline) {
        super(pipeline, null, TAIL_NAME, TailContext.class);
        setAddComplete();
    }

    @Override
    public ChannelHandler handler() {
        return this;
    }
    
    // 入站方向，最后一个ChannelInboundHandler，不处处理
    @Override
    public void channelRegistered(ChannelHandlerContext ctx) { }

    ...

    // 入站方向，最后一个ChannelInboundHandler，不处处理
    @Override
    public void channelRead(ChannelHandlerContext ctx, Object msg) {
        onUnhandledInboundMessage(ctx, msg);
    }

    @Override
    public void channelReadComplete(ChannelHandlerContext ctx) {
        onUnhandledInboundChannelReadComplete();
    }
}
```

### 2.2 初始化

ChannelInitializer 是一个特殊的 ChannelInboundHandlerAdapter 子类，通过 initChannel 方法，当 Channel 注册到 EventLoop 之后，就会调用该方法，完成 ChannelHandler 的添加。

```java
// 自定义 ChannelInitializer，初始化 Handler
public class MyChannelInitializer extends ChannelInitializer {
    public void initChannel(Channel channel) {
        channel.pipeline().addLast("myHandler1", new MyHandler1());
        channel.pipeline().addLast("myHandler2", new MyHandler2());
    }
}

ServerBootstrap bootstrap = new ServerBootstrap();
// 设置 ChannelInitializer
bootstrap.childHandler(new MyChannelInitializer());

// ChannelInitializer
public abstract class ChannelInitializer<C extends Channel> extends ChannelInboundHandlerAdapter {
    
    // 初始化方法
    protected abstract void initChannel(C ch) throws Exception;

    ...

    @Override
    public void handlerAdded(ChannelHandlerContext ctx) throws Exception {
        if (ctx.channel().isRegistered()) {
            if (initChannel(ctx)) {

                // 执行完 initChannel 之后 ，将 ChannelInitializer 自己移除
                removeState(ctx);
            }
        }
    }
}
```

ChannelInitializer 类特殊的地方在于，执行 initChannel 方法之后，ChannelInitializer 实例将会从 ChannelPipeline 中移除。

## 3. 总结

ChannelPipeline 是 Netty 中的一个重要组件，它是 ChannelHandler 的容器类，管理着入站和出站 ChannelHandler 列表，并通过 ChannelHandlerContext 在 ChannelHandler 间传播 I/O 事件。同时ChannelPipeline 实现了责任链的设计模式， 业务逻辑可以按照功能拆分为多个独立的 ChannelHandler ，如果需要更新某个 ChannelHandler ，不用改动其它 ChannelHandler，使得应用具有较好的扩展性。