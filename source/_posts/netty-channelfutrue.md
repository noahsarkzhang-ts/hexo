---
title: Netty 系列：ChannelFuture
date: 2021-08-18 14:33:15
tags:
- 异步通信
- Future
- ChannelFuture
- Netty
categories:
- Netty
---

## 1. 概述
Netty 中所有的的 I/O 操作都是异步的。I/O 操作是比较耗时的，为了不阻塞调用线程，Netty 提供了 ChannelFuture 接口，使用 addListener()方法注册一个 ChannelFutureListener 监听器，可以在 I/O 操作结束之后进行通知返回结果。在下面的代码中，bind 操作返回一个 ChannelFuture 对象，可以继续执行后续操作，也可以调用 sync() 方法同步等待执行结果，给程序开发带来了更多的开发模式，结合不同的业务场景，可以方便选择异步还是同步模式。

```java
// Configure the server.
EventLoopGroup bossGroup = new NioEventLoopGroup(1);
EventLoopGroup workerGroup = new NioEventLoopGroup();
final EchoServerHandler serverHandler = new EchoServerHandler();
try {
    ServerBootstrap b = new ServerBootstrap();
    b.group(bossGroup, workerGroup)
     .channel(NioServerSocketChannel.class)
     .option(ChannelOption.SO_BACKLOG, 100)
     .handler(new LoggingHandler(LogLevel.INFO))
     .childHandler(new ChannelInitializer<SocketChannel>() {
         @Override
         public void initChannel(SocketChannel ch) throws Exception {
             ChannelPipeline p = ch.pipeline();
             if (sslCtx != null) {
                 p.addLast(sslCtx.newHandler(ch.alloc()));
             }
             //p.addLast(new LoggingHandler(LogLevel.INFO));
             p.addLast(serverHandler);
         }
     });

    // Start the server.
    ChannelFuture f = b.bind(PORT).sync();

    // Wait until the server socket is closed.
    f.channel().closeFuture().sync();
} finally {
    // Shut down all event loops to terminate all threads.
    bossGroup.shutdownGracefully();
    workerGroup.shutdownGracefully();
}
```
这篇文章的主要目的是分析 ChannelFuture 在 Netty 中的实现原理。

## 2. 原理
ChannelFutrue 本质上是线程间交换数据的方式，一个线程等待另外一个线程的处理结果，取得结果一般有两种方式：1）同步等待，如同 get() 方法；2）注册回调，在设置结果的同时调用回调函数。其伪代码如下所示：

```java
public class ChannelFutrue {

    // 用于同步操作
    private final CountDownLatch countDownLatch = new CountDownLatch(1);

    // 用于保存回调函数
    private List<GenericFutureListener> listeners = new ArrayList<>();

    // 保存返回结果
    private volatile Object result;

    // 设置结果并调用回调
    public void setSuccess(Object result) {
        this.result = result;
        countDownLatch.countDown();

        // 调用回调函数
        listeners.stream().forEach(listener -> {
            try {
                listener.operationComplete(result);
            } catch (Exception ex) {
                ex.printStackTrace();
            }
        });
    }

    // 添加回调
    public void addListener(GenericFutureListener listener) {
        listeners.add(listener);
    }

    // 同步获取结果
    public Object get() throws InterruptedException {
        countDownLatch.await();
        return result;
    }

    public Object bind() throws InterruptedException {
        return get();
    }

    public interface GenericFutureListener {
        void operationComplete(Object result) throws Exception;
    }

}
```
通过持有 ChannelFutrue 类，调用方可以同步或异步获取执行的结果。

### 3. Netty 实现
我们来分析下
![DefaultChannelPromise](/images/netty/DefaultChannelPromisejpg "DefaultChannelPromise")




## 4. 总结


