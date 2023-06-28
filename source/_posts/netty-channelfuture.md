---
title: Netty 系列：ChannelFuture
date: 2021-08-18 14:33:15
updated: 2021-08-18 14:33:15
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

<!-- more -->

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
通过持有 ChannelFutrue 类，调用方可以同步或异步获取执行的结果，在这个例子中，为了简化操作，我们使用 CountDownLatch 进行同步，而在 ChannelFutrue 使用 synchronized + notify/await 来实现线程的同步。

## 3. Netty 实现
我们以 ServerBootstrap 中的 bind 方法为例，分析 ChannelFuture 在这个流程中的使用方式，bind 方法的主要流程如下所示（其中的实现细节在后续篇章介绍）：

![ChannelFuture-flow](/images/netty/ChannelFuture-flow.jpg "ChannelFuture-flow")

在 bind 方法中主要包含在 4 个步骤：
1. 生成 NioServerSocketChannel 对象；
2. 将 NioServerSocketChannel 对象注册到 EventLoop 中；
3. 执行 bind 操作；
4. 同步等待 bind 操作执行完成。

### 3.1 register 流程
可以看到第 2 和 3 步都是一个 I/O 操作，为了避免调用线程被阻塞，它们都被提交到 EventLoop 线程（每一个 EventLoop 对象都会绑定一个线程）中执行，并返回一个 ChannelFuture 对象，一个 I/O 操作会对应一个ChannelFuture 对象，调用线程与 EventLoop 通过该对象完成执行结果的交换。下面以 register 方法为例，分析下 ChannelFuture 对象的使用。

**1、生成 ChannelFuture 对象**

调用 register 之后返回一个 DefaultChannelPromise 对象，该对象是 ChannelFuture 的子类。

```java
// SingleThreadEventLoop
@Override
public ChannelFuture register(Channel channel) {
    return register(new DefaultChannelPromise(channel, this));
}

@Override
public ChannelFuture register(final Channel channel, final ChannelPromise promise) {
    ObjectUtil.checkNotNull(promise, "promise");
    ObjectUtil.checkNotNull(channel, "channel");
    channel.unsafe().register(this, promise);
    return promise;
}

```

**2、提交异步注册任务**

提交注册任务的逻辑在 AbstractChannel.AbstractUnsafe 中，提交的时候会判断当前线程，如果当前线程是 eventLoop 线程，直接执行即可，如果不是，则提交一个任务到 eventLoop 线程 中。

```java
// AbstractChannel.AbstractUnsafe
@Override
public final void register(EventLoop eventLoop, final ChannelPromise promise) {
    ObjectUtil.checkNotNull(eventLoop, "eventLoop");
    if (isRegistered()) {
        promise.setFailure(new IllegalStateException("registered to an event loop already"));
        return;
    }
    if (!isCompatible(eventLoop)) {
        promise.setFailure(
                new IllegalStateException("incompatible event loop type: " + eventLoop.getClass().getName()));
        return;
    }

    AbstractChannel.this.eventLoop = eventLoop;

    // 如果当前线程是 eventLoop 线程，直接执行即可；
    // 如果不是，则提交一个任务到 eventLoop 线程 中。
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
            logger.warn(
                    "Force-closing a channel whose registration task was not accepted by an event loop: {}",
                    AbstractChannel.this, t);
            closeForcibly();
            closeFuture.setClosed();
            safeSetFailure(promise, t);
        }
    }
}
```

**3、执行注册逻辑**

register0 是在 EventLoop 线程中执行的，与调用注册方法的线程不是同一个。注册的逻辑通过子类的 doRegister() 方法实现，注册完成之后通过 safeSetSuccess(promise) 和 safeSetFailure(promise, t) 通知注册结果。

```java
// AbstractChannel.AbstractUnsafe
private void register0(ChannelPromise promise) {
    try {
        if (!promise.setUncancellable() || !ensureOpen(promise)) {
            return;
        }
        boolean firstRegistration = neverRegistered;

        // 真正的注册逻辑，由子类实现
        doRegister();
        neverRegistered = false;
        registered = true;

        pipeline.invokeHandlerAddedIfNeeded();

        // 执行成功之后调用 promise 对象通知注册完成
        safeSetSuccess(promise);
        pipeline.fireChannelRegistered();
       
        if (isActive()) {
            if (firstRegistration) {
                pipeline.fireChannelActive();
            } else if (config().isAutoRead()) {
               
                beginRead();
            }
        }
    } catch (Throwable t) {
        
        closeForcibly();
        closeFuture.setClosed();

        // 失败之后调用 promise 对象通知注册失败
        safeSetFailure(promise, t);
    }
}

```

**4、结果通知**

结果通知主要包含两个操作：
1. 设置处理结果，唤醒所有等待的线程；
2. 调用注册到 ChannelFuture 中的监听器；

```java
// AbstractChannel.AbstractUnsafe
protected final void safeSetSuccess(ChannelPromise promise) {
    if (!(promise instanceof VoidChannelPromise) && !promise.trySuccess()) {
        logger.warn("Failed to mark a promise as success because it is done already: {}", promise);
    }
}

// 最终调到 DefaultPromis 类的 setValue0 方法
private boolean setValue0(Object objResult) {
    if (RESULT_UPDATER.compareAndSet(this, null, objResult) ||
        RESULT_UPDATER.compareAndSet(this, UNCANCELLABLE, objResult)) {
        if (checkNotifyWaiters()) {
            notifyListeners();
        }
        return true;
    }
    return false;
}

// 如果有线程等待，唤醒所有等待的线程
private synchronized boolean checkNotifyWaiters() {
    if (waiters > 0) {
        notifyAll();
    }
    return listeners != null;
}

// 调用监听器
private void notifyListeners() {
    EventExecutor executor = executor();
    if (executor.inEventLoop()) {
        final InternalThreadLocalMap threadLocals = InternalThreadLocalMap.get();
        final int stackDepth = threadLocals.futureListenerStackDepth();
        if (stackDepth < MAX_LISTENER_STACK_DEPTH) {
            threadLocals.setFutureListenerStackDepth(stackDepth + 1);
            try {
                notifyListenersNow();
            } finally {
                threadLocals.setFutureListenerStackDepth(stackDepth);
            }
            return;
        }
    }

    safeExecute(executor, new Runnable() {
        @Override
        public void run() {
            notifyListenersNow();
        }
    });
}

// 调用回调函数
private static void notifyListener0(Future future, GenericFutureListener l) {
    try {
        l.operationComplete(future);
    } catch (Throwable t) {
        if (logger.isWarnEnabled()) {
            logger.warn("An exception was thrown by " + l.getClass().getName() + ".operationComplete()", t);
        }
    }
}

```

### 3.2 异步操作的协同
在上面的操作中，bind 操作依赖 register 操作的结果，由于这两个操作都是异步操作，如何进行协同？即在 register 操作成功执行 bind 操作。正常情况下，有两种办法：1）同步等待操作执行完成；2）通过添加 GenericFutureListener 监听器，执行完由 EventLoop 线程进行回调。在这里是通过第二种方式来操作的。
在执行 initAndRegister 操作之后，会得到一个 ChannelFuture regFuture 对象，此时 register 已经提交给 EventLoop 执行，不一定执行完成，需要判断执行结果，如果未完成，则向 regFuture 对象中添加监听器，在监听器中调用 bind 操作，而监听器会中注册完成之后调用。

```java
// AbstractBootstrap
private ChannelFuture doBind(final SocketAddress localAddress) {
        // 执行初始化及注册操作
        final ChannelFuture regFuture = initAndRegister();
        final Channel channel = regFuture.channel();
        if (regFuture.cause() != null) {
            return regFuture;
        }

        // 如果注册操作完成，则执行 bind 操作。
        if (regFuture.isDone()) {
            
            ChannelPromise promise = channel.newPromise();
            doBind0(regFuture, channel, localAddress, promise);
            return promise;
        } else {
           
            // 如果注册操作示完成，则向 regFuture 中添加监听器，在监听器中调用 bind 操作
            final PendingRegistrationPromise promise = new PendingRegistrationPromise(channel);
            regFuture.addListener(new ChannelFutureListener() {
                @Override
                public void operationComplete(ChannelFuture future) throws Exception {
                    Throwable cause = future.cause();
                    if (cause != null) {
                        promise.setFailure(cause);
                    } else {
                        promise.registered();

                        doBind0(regFuture, channel, localAddress, promise);
                    }
                }
            });
            return promise;
        }
    }

// 提交 bind 任务到 EventLoop 任务中
private static void doBind0(
        final ChannelFuture regFuture, final Channel channel,
        final SocketAddress localAddress, final ChannelPromise promise) {

    channel.eventLoop().execute(new Runnable() {
        @Override
        public void run() {
            if (regFuture.isSuccess()) {
                channel.bind(localAddress, promise).addListener(ChannelFutureListener.CLOSE_ON_FAILURE);
            } else {
                promise.setFailure(regFuture.cause());
            }
        }
    });
}
```

### 3.3 sync 同步操作
由于 bind 操作是一个异步操作，此时在调用线程中需要等待绑定的结果，所以调用了 sync 方法。另外，在程序的最后，也使用了一个 ChannelFuture，用于等待 Channel 关闭事件。

```java
/// 绑定端口并等待完成
ChannelFuture f = b.bind(PORT).sync();

// 等待 channel 关闭
f.channel().closeFuture().sync();

```

### 3.3 ChannelFuture 线程同步
ChannelFuture 中的线程同步方式是 synchronized 同步块，如下代码如下：

```java

// 等待操作
public Promise<V> await() throws InterruptedException {
    if (isDone()) {
        return this;
    }

    if (Thread.interrupted()) {
        throw new InterruptedException(toString());
    }

    checkDeadLock();

    synchronized (this) {
        while (!isDone()) {
            incWaiters();
            try {
                wait();
            } finally {
                decWaiters();
            }
        }
    }
    return this;
}

// 唤醒操作
private synchronized boolean checkNotifyWaiters() {
    if (waiters > 0) {
        notifyAll();
    }
    return listeners != null;
}

```

在调用 await 操作时，如果没有结果（操作未完成），则会调用 wait 方法阻塞该线程，同时增加等待的线程数；操作完成之后会调用 notifyAll 方法，通知所有等待的线程继续执行，这样完成了调用结果在不同线程间的交互。

## 4. 总结

ChannelFuture 本质是线程间通信的一种工具，通过 ChannelFuture，可以实现 I/O 的异步操作，并完成操作结果的通知功能。
