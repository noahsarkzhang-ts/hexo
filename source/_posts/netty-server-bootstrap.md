---
title: Netty 系列：ServerBootstrap
date: 2021-08-26 14:39:14
tags:
- ServerBootstrap
categories:
- Netty
---

## 1. 概述
因 Netty 中大量使用异步的调用方式，启动流程中的代码在不同的线程中执行，给分析其启动的顺序带来了一定的麻烦。这篇文章主要是对 ServerBootstrap 服务器启动流程做一个整体性的讲述，分析了每一个步骤所承担的工作，以及前后步骤的触发关系，即前一个步骤怎么调用后一个步骤，仍然以服务器启动的代码为例，分析其流程。

<!-- more -->

```java
EventLoopGroup bossGroup = new NioEventLoopGroup(1);
EventLoopGroup workerGroup = new NioEventLoopGroup();
final EchoServerHandler serverHandler = new EchoServerHandler();
try {
    ServerBootstrap b = new ServerBootstrap();
    b.group(bossGroup, workerGroup)
     .channel(NioServerSocketChannel.class)      // 设置服务器 channel 对象
     .option(ChannelOption.SO_BACKLOG, 100)
     .handler(new LoggingHandler(LogLevel.INFO)) // 配置 ChannelHandler 对象
     .childHandler(new ChannelInitializer<SocketChannel>() {
         @Override
         public void initChannel(SocketChannel ch) throws Exception {
             ChannelPipeline p = ch.pipeline();
             if (sslCtx != null) {
                 p.addLast(sslCtx.newHandler(ch.alloc()));
             }
             
             p.addLast(serverHandler);
         }
     });

    // 绑定端口并等待完成
    ChannelFuture f = b.bind(PORT).sync();

    // 等待 channel 关闭
    f.channel().closeFuture().sync();
} finally {
    
    bossGroup.shutdownGracefully();
    workerGroup.shutdownGracefully();
}
```
前后的文章已经分析过 EventLoopGroup 及 ChannelFutue，这里重点分析 bind 流程。

![netty-bind](/images/netty/netty-bind-v2.jpg "netty-bind")

主要流程如下：
1. 新建 NioServerSocketChannel 对象；
2. 初始化 NioServerSocketChannel 对象，主要是向其添加 ChannelHandler 对象；
3. 注册 NioServerSocketChannel 对象，主要是将该对象注册到 EventLoop 和 底层的 Selector 对象中；
4. 执行 NioServerSocketChannel 对象的 bind 操作；
5. 执行 NioServerSocketChannel read 操作，主要是向 Selector 对象注册 OP_ACCEPT 事件，完成之后便可接收网络请求。

## 2. 执行流程
### 2.1 新建 NioServerSocketChannel 对象
在 Netty 中，Nio Tcp Channel 有两种类型，一种是 NioServerSocketChannel，它代表了服务器 Channel，接收网络请求（OP_ACCEPT），另外一种是 NioSocketChannel，它代表了一次网络连接，读取网络数据。在 ServerBootstrap 中使用是 NioServerSocketChannel 对象，该对象通过反射方式生成。

```java
// 设置 channel 为 NioServerSocketChannel
b.group(bossGroup, workerGroup)
    .channel(NioServerSocketChannel.class) 

// 设置 channelFactory 为 ReflectiveChannelFactory
public B channel(Class<? extends C> channelClass) {
    return channelFactory(new ReflectiveChannelFactory<C>(
            ObjectUtil.checkNotNull(channelClass, "channelClass")
    ));
}

// ReflectiveChannelFactory 对象
public class ReflectiveChannelFactory<T extends Channel> implements ChannelFactory<T> {

    private final Constructor<? extends T> constructor;

    // 构造器，参数为 channel 对象
    public ReflectiveChannelFactory(Class<? extends T> clazz) {
        ObjectUtil.checkNotNull(clazz, "clazz");
        try {
            this.constructor = clazz.getConstructor();
        } catch (NoSuchMethodException e) {
            ...
        }
    }

    // 通过反射方式生成 channel 对象
    @Override
    public T newChannel() {
        try {
            return constructor.newInstance();
        } catch (Throwable t) {
            ...
        }
    }
}

// ServerBootstrap 方法调用
final ChannelFuture initAndRegister() {
    Channel channel = null;
    try {
        // 调用 channelFactory 生成 NioServerSocketChannel
        channel = channelFactory.newChannel();
        init(channel);
    } catch (Throwable t) {
        ...
    }

    ...

    return regFuture;
}
```

新建 NioServerSocketChannel 对象实际是使用 ReflectiveChannelFactory 对象来生成。

### 2.2 初始化 NioServerSocketChannel 对象

初始化工作主要是设置 NioServerSocketChannel 对象中的 ChannelPipeline，该 ChannelPipeline 对象以责任链模式维护一个 ChannelHandler 链表，用于处理后续的网络连接。在这里主要是加入一个 ChannelInitializer handler 类，它是一个特殊的 ChannelHandler 类，用于完成 ChannelHandler 列表的添加。在这个例子中，它加入了两个 ChannelHandler 类，一个是 LoggingHandler 类，它的功能是打印日志，由 ServerBootstrap.handler 方法加入， 一个是 ServerBootstrapAcceptor 类，它主要用来对新加入的 SocketChannel 进行初始化。

```java
void init(Channel channel) {
    setChannelOptions(channel, newOptionsArray(), logger);
    setAttributes(channel, attrs0().entrySet().toArray(EMPTY_ATTRIBUTE_ARRAY));

    ChannelPipeline p = channel.pipeline();

    final EventLoopGroup currentChildGroup = childGroup;
    final ChannelHandler currentChildHandler = childHandler;
    final Entry<ChannelOption<?>, Object>[] currentChildOptions;
    synchronized (childOptions) {
        currentChildOptions = childOptions.entrySet().toArray(EMPTY_OPTION_ARRAY);
    }
    final Entry<AttributeKey<?>, Object>[] currentChildAttrs = childAttrs.entrySet().toArray(EMPTY_ATTRIBUTE_ARRAY);

    p.addLast(new ChannelInitializer<Channel>() {
        @Override
        public void initChannel(final Channel ch) {
            final ChannelPipeline pipeline = ch.pipeline();
            ChannelHandler handler = config.handler();
            if (handler != null) {
                pipeline.addLast(handler);
            }

            ch.eventLoop().execute(new Runnable() {
                @Override
                public void run() {
                    pipeline.addLast(new ServerBootstrapAcceptor(
                            ch, currentChildGroup, currentChildHandler, currentChildOptions, currentChildAttrs));
                }
            });
        }
    });
}
```

ServerBootstrapAcceptor 主要的功能是处理 NioServerSocketChannel 的 OP_ACCEPT，即接收一个新的网络请求（对应一个 SocketChannel 对象），对其设置相关的参数及 ChannelHandler列表，这些配置来来自于 ServerBootstrap 的启动配置参数，最后为该 SocketChannel 分配一个 EventLoop 对象，实现网络连接的负载。

```java
// ServerBootstrapAcceptor
public void channelRead(ChannelHandlerContext ctx, Object msg) {
    final Channel child = (Channel) msg;

    // 设置 ChannelHandler
    child.pipeline().addLast(childHandler);

    // 设置参数
    setChannelOptions(child, childOptions, logger);
    setAttributes(child, childAttrs);

    try {
        // 分配一个 EventLoop
        childGroup.register(child).addListener(new ChannelFutureListener() {
            @Override
            public void operationComplete(ChannelFuture future) throws Exception {
                if (!future.isSuccess()) {
                    forceClose(child, future.cause());
                }
            }
        });
    } catch (Throwable t) {
        forceClose(child, t);
    }
}

```

另外说明一点，ChannelPipeline 的 addLast 操作需要在 NioServerSocketChannel 对象注册到 EventLoop 中之后再会执行，此时 NioServerSocketChannel 还未注册，所以执行 addLast 方法只是简单向 ChannelPipeline 中添加一个 PendingHandlerAddedTask，等注册操作完成之后再进行调用。

### 2.3 注册 NioServerSocketChannel 对象

注册的操作主要包括两个部分：
- 将 NioServerSocketChannel 分配给 EventLoop，该操作是通过 BossGropu 来完成；
- 将 NioServerSocketChannel 注册到 Selector 对象上，用于接收网络请求。 每一个 NioServerSocketChannel 都包含一个 Java SelectableChannel 对象，网络请求最终都是通过这个对象来完成。

register 调用顺序为 AbstractBootstrap.initAndRegister --> MultithreadEventLoopGroup.register --> SingleThreadEventLoop --> AbstractUnsafe.register，注册操作最终是调用 AbstractUnsafe 类来完成的。这里先看下 initAndRegister 方法，register 与 后续的 bind 都是异步操作，而 bind 操作需要 register 操作成功之后再执行，这两个操作的协调就是在这一步完成的。

```java
// AbstractBootstrap
final ChannelFuture initAndRegister() {
    Channel channel = null;
    try {
        channel = channelFactory.newChannel();
        init(channel);
    } catch (Throwable t) {
        ...
    }

    //1、 返回注册操作的 ChannelFuture
    ChannelFuture regFuture = config().group().register(channel);
    ...

    return regFuture;
}

// AbstractBootstrap
private ChannelFuture doBind(final SocketAddress localAddress) {
    // 返回注册操作的 ChannelFuture
    final ChannelFuture regFuture = initAndRegister();
    final Channel channel = regFuture.channel();
    if (regFuture.cause() != null) {
        return regFuture;
    }

    // 2、判断注册操作是否完成，若完成则执行 doBind0 方法；
    if (regFuture.isDone()) {
       
        ChannelPromise promise = channel.newPromise();
        // 调用 doBind0 方法
        doBind0(regFuture, channel, localAddress, promise);
        return promise;
    } else { // 3、若注册操作未完成，则添加一个回调函数，注册完成后执行 doBind0 方法；
        final PendingRegistrationPromise promise = new PendingRegistrationPromise(channel);
        regFuture.addListener(new ChannelFutureListener() {
            @Override
            public void operationComplete(ChannelFuture future) throws Exception {
                Throwable cause = future.cause();
                if (cause != null) {
                    promise.setFailure(cause);
                } else {
                    promise.registered();
                    // 调用 doBind0 方法
                    doBind0(regFuture, channel, localAddress, promise);
                }
            }
        });
        return promise;
    }
}

```

从上面的代码可以看出，register 与 bind 的操作是借助 ChannelFuture 完成的，主要是通过向 regFuture 中添加 ChannelFutureListener 监听器，在 register 完成之后调用 safeSetSuccess(regFuture) 触发调用监听器代码。

注册操作的核心代码在 AbstractUnsafe.register 方法中，再将 将 EventLoop 赋值给 AbstractChannel 对象，会向 EventLoop 提交一个异步任务用来执行 register0 方法，该方法包括了将 AbstractChannel 注册到 Selector 的 I/O 操作。

```java
public final void register(EventLoop eventLoop, final ChannelPromise promise) {
    
    // 1、将 EventLoop 赋值给 AbstractChannel 对象，
    // 一个 EventLoop 对象可以赋值给多个 AbstractChannel 对象 
    AbstractChannel.this.eventLoop = eventLoop;

    // 2、将 AbstractChannel 注册到 Selector 对象是一个 I/O 操作，
    // 需要提交给 eventLoop 执行
    if (eventLoop.inEventLoop()) {
        register0(promise);
    } else {
        try {
            eventLoop.execute(new Runnable() {
                @Override
                public void run() {
                    register0(promise);
                }
            });
        } catch (Throwable t) {
            
        }
    }
}

```

register0 方法在 EventLoop 线程中执行，它主要包括下面几个步骤：
- 执行操作系统层面的注册操作，主要是调用 java api 来实现；
- 将 channel 状态设置为注册完成状态；
- 向 pipeline 添加 ChannelHandler，在这里调用 channel 初始化时添加到 pipeline 中的 PendingHandlerAddedTask；
- 将 regFuture 设置为成功完成状态，并触发调用 ChannelFutureListener 监听器，最终会调用 bind 操作；
- 触发 ChannelRegistered 事件，调用 ChannelHandler 中的回调函数。

```java
// AbstractUnsafe
private void register0(ChannelPromise promise) {
    try {
        ...
        
        boolean firstRegistration = neverRegistered;
        
        // 1、执行操作系统层面的注册操作，主要是调用 java api 来实现；
        doRegister();
        neverRegistered = false;
        
        // 2、设置 channel 的注册状态；
        registered = true;

        ...
        
        // 3、执行 HandlerAdd 操作；
        pipeline.invokeHandlerAddedIfNeeded();

        // 4、成功设置 channelFuture 完成状态，将触发回调操作； 
        safeSetSuccess(promise);
        
        // 5、触发 ChannelRegistered 事件，调用 ChannelHandler 中的回调函数
        pipeline.fireChannelRegistered();
       
        ...
    } catch (Throwable t) {
        ...
    }
}

```

doRegister 方法调用的是 Java NIO api 完成网络层面的注册操作，代码如下所示：

```java
// AbstractNioChannel
protected void doRegister() throws Exception {
    boolean selected = false;
    for (;;) {
        try {
            // 将 channel 注册到 eventLoop 中的 Selector 对象中，此时未注册感兴趣的 I/O 事件 
            selectionKey = javaChannel().register(eventLoop().unwrappedSelector(), 0, this);
            return;
        } catch (CancelledKeyException e) {
            if (!selected) {
                eventLoop().selectNow();
                selected = true;
            } else {
                throw e;
            }
        }
    }
}

```

doRegister 方法在 AbstractNioChannel 中实现，在这个方法中，主要是将 ServerSocketChannel 注册到底层的 selector 上，由它来监听 ServerSocketChannel 的 I/O 事件，不过在此时还没有注册感兴趣的 I/O 事件，是由后面的 read 操作来完成。

### 2.4 执行 bind 操作

bind 操作主要是完成底层 ServerSocketChannel 对象的地址绑定操作，其调用顺序为：AbstractBootstrap.doBind0 --> AbstractChannel.bind --> DefaultChannelPipeline.bind --> AbstractChannelHandlerContext.bind --> HeadContext.bind --> AbstractUnsafe.bind。最后调用 AbstractUnsafe 中的 bind 方法。

在 bind 方法中，主要做了下面的工作：
- 执行地址绑定操作，具体实现取决于 Channel 的子类；
- 判断 channel 是否 Active，正常情况，绑定成功之后便会激活 channel；
- 触发 channelActive 事件，执行后续的 read 操作；
- 设置成功完成 bind 操作

```java
// AbstractUnsafe
public final void bind(final SocketAddress localAddress, final ChannelPromise promise) {
    
    ...
    
    boolean wasActive = isActive();
    try {
        // 1、执行地址绑定操作
        doBind(localAddress);
    } catch (Throwable t) {
        safeSetFailure(promise, t);
        closeIfClosed();
        return;
    }

    // 2、判断该 channel是否 Active
    // bind 操作之后正常就是 Active 了
    if (!wasActive && isActive()) {
        invokeLater(new Runnable() {
            @Override
            public void run() {
                // 3、回调 ChannelActive 事件
                pipeline.fireChannelActive();
            }
        });
    }

    // 4、设置成功完成 bind 操作
    safeSetSuccess(promise);
}

```

doBind 方法的实现由 channel 的子类实现，在这里由 NioServerSocketChannel 来实现，如代码如下所示：

```java
// NioServerSocketChannel
protected void doBind(SocketAddress localAddress) throws Exception {
    if (PlatformDependent.javaVersion() >= 7) {
        javaChannel().bind(localAddress, config.getBacklog());
    } else {
        javaChannel().socket().bind(localAddress, config.getBacklog());
    }
}
```

doBind 执行完成之后，触发 channelActive 事件，在 channelActive 回调函数中再触发读事件，最后完成 OP_ACCEPT 事件的注册。

```java
// HeadContext
public void channelActive(ChannelHandlerContext ctx) {
    ctx.fireChannelActive();

    // 1、 执行 read 操作
    readIfIsAutoRead();
}

// HeadContext
private void readIfIsAutoRead() {
    if (channel.config().isAutoRead()) {
        channel.read();
    }
}

```

在 channelActive 中触发调用 channel.read() 操作。

### 2.5 执行 read 操作

在 channelActive 中触发调用 read 的顺序为：AbstractChannel.read --> DefaultChannelPipeline.read --> AbstractChannelHandlerContext.read --> HeadContext.read --> AbstractUnsafe.beginRead，最终调用 AbstractUnsafe.beginRead 方法。

AbstractUnsafe.beginRead 中会调用 channel 的 doBeginRead 方法，该方法也是抽象文件，具体实现取决于子类，

```java
// AbstractUnsafe
public final void beginRead() {
    assertEventLoop();

    if (!isActive()) {
        return;
    }

    try {
        // 1、开始读操作，具体实现在子类中定义
        doBeginRead();
    } catch (final Exception e) {
        ...
    }
}

// AbstractNioChannel
protected void doBeginRead() throws Exception {
    // Channel.read() or ChannelHandlerContext.read() was called
    final SelectionKey selectionKey = this.selectionKey;
    if (!selectionKey.isValid()) {
        return;
    }

    readPending = true;

    final int interestOps = selectionKey.interestOps();
    if ((interestOps & readInterestOp) == 0) {
        selectionKey.interestOps(interestOps | readInterestOp);
    }
}

// NioServerSocketChannel
public NioServerSocketChannel(ServerSocketChannel channel) {
    super(null, channel, SelectionKey.OP_ACCEPT);
    config = new NioServerSocketChannelConfig(this, javaChannel().socket());
}
```

NioServerSocketChannel 类中，selectionKey 为 SelectionKey.OP_ACCEPT，即监听 ServerSocket 的 OP_ACCEPT 事件，注册完该事件之后，NioServerSocketChannel 便可接收网络请求了。

## 3. 总结

ServerBootstrap bind 方法是相对比较复杂的一个方法，它涉及到了 Netty 中各个组件，并将它们有机整合在一起。通过对 bind 方法的分析，对 Netty 的整体流程有了一个初步的理解，这会对使用 Netty 大有裨益。