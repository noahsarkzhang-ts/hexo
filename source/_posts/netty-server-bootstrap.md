---
title: Netty 系列：ServerBootstrap
date: 2021-08-26 14:39:14
tags:
- ServerBootstrap
categories:
- Netty
---

## 1. 概述
因Netty 中大量使用异步的调用方式，启动流程中的代码在不同的线程中执行，给分析其启动的顺序带来了一定的麻烦。这篇文章主要是对 ServerBootstrap 服务器启动流程做一个整体性的讲述，分析了每一个步骤所承担的工作，以及前后步骤的触发关系，即前一个步骤怎么调用后一个步骤。仍然以服务器启动的代码为例，分析其流程。

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

### 2.4 执行 bind 操作

### 2.5 执行 read 操作

## 3. 总结
