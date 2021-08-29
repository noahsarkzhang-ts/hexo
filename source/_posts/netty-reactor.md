---
title: Netty 系列：Reactor
date: 2021-08-22 13:22:53
tags:
- reactor
- mainReactor
- subReactor
- EventLoopGroup
- EventLoop
- 事件循环
categories:
- Netty
---

## 1. 概述
Reactor 模式是一种服务器网络编程模式，它根据网络数据接收的特点，将连接的建立、网络数据的读写分离，用 mainReactor 线程处理网络的连接，用 subReactor 处理数据的读写，同时为了有效利用 CPU 多核的优势，subActor 可以有多个。它的整体结构如下图所示：

![reactor](/images/netty/ractor.jpeg "reactor")

**特点：**
1. 客户端的所有连接请求统一由 mainReactor 线程处理，同时将收到请求转交 subReactor 处理；
2. subReactor 线程处理连接的读写，为了实现处理的负载，可以有多个 subReactor，通过一定的算法分配网络连接；
3. 考虑到连接的 I/O 读写比较耗时，为了提高吞吐量，读写操作可以交由线程池处理。

**说明：**
文中说到的“网络连接”与下文说到的 "channel" 和 "socketChannel" 是一个概念。

另外，这篇文章主要包含三个部分的内容：1）Reactor 概念的介绍；2）Reactor 的模拟；3）Netty 中的实现；现在我们用 Java 模拟一个 Reactor 的实现。

## 2. 原理

### 2.1 MainReactor

我们以一个例子来模拟一个 Reactor，先看 MainReactor 类的代码，它主要的功能是监听 9090 端口接收网络连接，并将网络请求注册到 SubReactor 类，代码如下所示：

```java
public class MainReactor implements Runnable {

	// 监听的端口
	private static final int PORT = 9090;

	// Selector 对象，用于实现网络 I/O 事件的监听
	private Selector selector;

	// 服务器套接字，用于接收网络请求
	private ServerSocketChannel serverChannel;

	// 用于分配 SocketChannel 到 subReactor
	// SelectorManager 存有多个 subReactor 对象
	private SelectorManager manager;

	// 标识线程是关闭
	private boolean isStop;

	public MainReactor() throws Exception {
		init();
	}

	// 初始化 MainReactor
	private void init() throws Exception {
		isStop = false;
		selector = Selector.open();
		serverChannel = ServerSocketChannel.open();
		serverChannel.socket().bind(new InetSocketAddress(PORT));
		serverChannel.configureBlocking(false);

		// 向 selector 注册 OP_ACCEPT 事件
		// MainReactor 只处理网络连接事件
		serverChannel.register(selector, SelectionKey.OP_ACCEPT);

		manager = new SelectorManager();
	}

	// 启动 MainReactor 线程
	public void doStart() {
		Thread seletorThread = new Thread(this);

		seletorThread.start();
	}

	// 处理收到的网络连接，将该请求分配给 subReactor
	private void process(SocketChannel channel) {
		manager.register(channel);
	}

	public void shutdown() {
		isStop = true;
	}

	@Override
	public void run() {

		try {

			// 事件处理循环
			while (!isStop) {
				selector.select();

				Set<SelectionKey> set = selector.selectedKeys();
				Iterator<SelectionKey> iterator = set.iterator();

				while (iterator.hasNext()) {
					System.out.println("accept thread:" + Thread.currentThread().getName());

					SelectionKey key = iterator.next();
					iterator.remove();

					ServerSocketChannel server = (ServerSocketChannel) key.channel();

					// 接收新的网络请求
					SocketChannel client = server.accept();

					System.out.println("receive a connection:" + client.socket().getRemoteSocketAddress());

					// 分配网络请求
					process(client);
				}

			}
		} catch (Exception e) {
			e.printStackTrace();
		}
	}

	// 启动 MainReactor
	public static void main(String[] args) throws Exception {
		MainReactor server = new MainReactor();
		server.doStart();
	}
}

```
MainReactor 有几个主要的属性：
1. Selector：Selector 对象，用于实现网络 I/O 事件的监听，它只监听网络请求事件；
2. ServerSocketChannel：服务器套接字，用于接收网络请求；
3. SelectorManager：用于分配 SocketChannel 到 subReactor，SelectorManager 存有多个 subReactor 对象。

### 2.2 SubReactor
SubReactor 主要是处理 SocketChannel 的读写，代码如下所示：

```java
public class SubReactor implements Runnable {

    // Selector 对象，用于 channel 数据的读写
    private Selector selector;

    // SocketChannel 列表，一个 SubReactor 可以处理多个 SocketChannel
    private List<SocketChannel> queue;

    // 标示线程是否结束
    private boolean isStop;

    // 业务线程池，用于处理读写业务
    private ThreadPoolManager pool;

    public SubReactor() {
        isStop = false;
        pool = ThreadPoolManager.getInstance();
    }

    public SubReactor(Selector sel) {
        isStop = false;
        this.selector = sel;
        queue = new LinkedList<SocketChannel>();

        pool = ThreadPoolManager.getInstance();
    }

    // 启动 subReactor
    public void start() {
        Thread thread = new Thread(this);

        thread.start();
    }

    public synchronized void register(SocketChannel channel) {
        queue.add(channel);
    }

    public void shutdown() {
        isStop = true;
    }

    @Override
    public void run() {
        try {
            // 事件处理循环
            while (!isStop) {
                // 配置
                configuration();

                int count = selector.select();
                if (count == 0) {
                    continue;
                }

                Set<SelectionKey> set = selector.selectedKeys();
                Iterator<SelectionKey> iterator = set.iterator();

                while (iterator.hasNext()) {
                    System.out.println("io thread:" + Thread.currentThread().getName());

                    SelectionKey key = iterator.next();
                    iterator.remove();

                    if (!key.isValid()) {
                        continue;
                    }

                    // 判断 channel 是否可读
                    if (key.isReadable()) {
                        System.out.println(Thread.currentThread().getName() + " read........");
                        handleRead(key);
                    }

                    // 判断 channel 是否可写
                    if (key.isValid() && key.isWritable()) {
                        System.out.println(Thread.currentThread().getName() + " write........");
                        handleWrite(key);
                    }


                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    // 将读业务提交给线程池处理
    private void process(SelectionKey key) {
        HandlerContainer container = (HandlerContainer) key.attachment();
        IoHandler handler = container.getHandler();
        handler.setKey(key);

        pool.execute(handler);
    }

    // 配置相关参数
    public synchronized void configuration() throws Exception {
        int length = queue.size();
        for (int i = 0; i < length; i++) {
            SocketChannel channel = queue.get(i);
            channel.configureBlocking(false);

            // 配置监听 channel 可读事件，channel 可写事件不用监听（可写事件会导致事件处理循环空转）
            SelectionKey key = channel.register(selector, SelectionKey.OP_READ);

            IoHandler handler = new IoHandler();
            HandlerContainer container = new HandlerContainer(handler);

            key.attach(container);
        }

        queue.clear();
    }

    // 处理读请求
    public void handleRead(SelectionKey key) throws IOException {
        SocketChannel clntChan = (SocketChannel) key.channel();

        ByteBuffer input = ByteBuffer.allocate(1024);
        HandlerContainer container = (HandlerContainer) key.attachment();
        ByteBuffer buf = container.getBuf();

        long bytesRead = clntChan.read(input);

        if (bytesRead == -1) {
            clntChan.close();

            System.out.println("connection closed!");

            return;
        }

        input.flip();
        while (input.hasRemaining()) {
            byte b = input.get();
            buf.put(b);
            if (b == '\n') {

                System.out.println("meet a new line!");
                buf.flip();

                byte[] msg = new byte[buf.limit()];
                buf.get(msg);

                buf.flip();

                String message = new String(msg);

                System.out.println("receive message:" + message);

                process(key);
            }

        }
    }

    // 处理写请求
    public void handleWrite(SelectionKey key) throws IOException {
        HandlerContainer container = (HandlerContainer) key.attachment();
        IoHandler handler = container.getHandler();

        handler.handleWrite(key);
    }

}
```

SubReactor 的功能主要是负载监听 SocketChannel 的读写事件，然后分发给线程池去处理。

### 2.3 Channel 的分配
MainReactor 接收到新的连接，会产生一个 SocketChannel 对象，按照一定的算法分配给 SubReactor。这个分配主要由 SelectorManager 对象完成，我们分析下其代码：

```java

public class SelectorManager {

    // Selector 数组，一个 SubReactor 对应一个 selector
    private Selector[] selector;

    // SubReactor 数组，数组大小等于 cpu 数
    private SubReactor[] subReactors;

    // 分配的 SubReactor 下标
    private int next;

    // SubReactor 数组的大小
    private int length;

    // 初始化 SelectorManager 对象
    public SelectorManager() throws Exception {

        // SubReactor 数组大小等于 cpu 数
        length = Runtime.getRuntime().availableProcessors();

        selector = new Selector[length];
        subReactors = new SubReactor[length];

        for (int i = 0; i < length; i++) {
            selector[i] = Selector.open();
            subReactors[i] = new SubReactor(selector[i]);
        }

        next = 0;

        for (int i = 0; i < length; i++) {
            subReactors[i].start();
        }
    }

    // 分配 channel,使用是轮洵算法
    public void register(SocketChannel channel) {
        subReactors[next].register(channel);
        selector[next].wakeup();

        System.out.println("chose subRactor:" + next);

        if (++next == length) {
            next = 0;
        }
    }
}

```

在这里，SelectorManager 的功能主要包括两个方面：1）创建及初始化 SubReactor 数组；2）根据轮洵算法分配 Channel。

## 3. 实现

Netty 实现了 Reactor 模式，其整体结构如下所示：
![netty-reactor](/images/netty/netty-reactor-v2.jpg "netty-reactor")

在 Netty 服务启动的时候会配置两个 EventLoopGroup bossGroup 和 WrokerGroup，EventLoopGroup 可以包含一个或多处 EventLoop，每一个 EventLoop 包含一个 Selector (也可能是 epoll，取决于实现)对象，同时它是一个独立的线程，可独立负载 I/O 请求。对比 Reactor，bossGroup 相当于 MainReactor，这负责监听网络的连接请求（生成 SocketChannle对象），并将其分配给 workerGroup，在这里，只包含一个 EventLoop；workerGroup 相当于 subReactor，监听连接的读写请求。下面分析下 Netty 中关于 EventLoopGroup 的代码实现。

### 3.1 初始化

**1、线程数设置**

```java
// 配置 EventLoop
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
b.group(bossGroup, workerGroup);
```

在这里使用的是 NioEventLoopGroup，bossGroup 设置的线程数为 1，而 workerGroup 没有设置线程数，使用默认配置的数量：2 * cpu size。

```java
protected MultithreadEventLoopGroup(int nThreads, Executor executor, Object... args) {
    // 线程数为 0 ，则设置为 DEFAULT_EVENT_LOOP_THREADS
    super(nThreads == 0 ? DEFAULT_EVENT_LOOP_THREADS : nThreads, executor, args);
}

// DEFAULT_EVENT_LOOP_THREADS 设置为 io.netty.eventLoopThreads 变量的值，
// 如果没有设置则为 2 * cpu size
DEFAULT_EVENT_LOOP_THREADS = Math.max(1, SystemPropertyUtil.getInt(
    "io.netty.eventLoopThreads", NettyRuntime.availableProcessors() * 2));
```

**2、创建 EventLoop 数组**

NioEventLoopGroup 是 EventLoop 对象的容器集合，持有多个 EventLoop 对象，它的数量与线程数量一致，同时 NioEventLoopGroup 负责分配 SocketChannel，需要有一个分配的策略对象，这些是在其父类的构造函数中实现。

```java
protected MultithreadEventExecutorGroup(int nThreads, Executor executor,
                                        EventExecutorChooserFactory chooserFactory, Object... args) {
    if (nThreads <= 0) {
        throw new IllegalArgumentException(String.format("nThreads: %d (expected: > 0)", nThreads));
    }

    // 1、定义 EventLoop 中的线程执行器
    if (executor == null) {
        executor = new ThreadPerTaskExecutor(newDefaultThreadFactory());
    }
    
    // 2、初始化 EventLoop 数量
    children = new EventExecutor[nThreads];

    for (int i = 0; i < nThreads; i ++) {
        boolean success = false;
        try {
            // 3、生成 EventLoop 实例对象
            children[i] = newChild(executor, args);
            success = true;
        } catch (Exception e) {
            throw new IllegalStateException("failed to create a child event loop", e);
        } finally {
            ...
    }
    
    // 4、定义 channel 的分配策略
    chooser = chooserFactory.newChooser(children);

    ...
}

```
在 MultithreadEventExecutorGroup 构造函数中，主要做了三个工作：
- 定义 EventLoop 中的线程执行器，每一个 EventLoop 都包含一个线程，其线程由 ThreadPerTaskExecutor 生成；
- 初始化及生成 EventLoop 数组 ，newChild 方法由子类来实现，不同的模式有不同的实现；
- 定义 channel 的分配策略，根据 EventLoop 的数量有不同的实现。

在 NioEventLoopGroup 中，newChild 实现代码所示：
```java
protected EventLoop newChild(Executor executor, Object... args) throws Exception {
    EventLoopTaskQueueFactory queueFactory = args.length == 4 ? (EventLoopTaskQueueFactory) args[3] : null;
    return new NioEventLoop(this, executor, (SelectorProvider) args[0],
        ((SelectStrategyFactory) args[1]).newSelectStrategy(), (RejectedExecutionHandler) args[2], queueFactory);
}
```
newChild 方法的细节在后面的文章中再进行介绍。

**3、Channel 分配策略**

channel 的分配策略有两种，分别是：PowerOfTwoEventExecutorChooser 和 GenericEventExecutorChooser，它们本质上都是轮洵算法，只是当 EventLoop 的数量是 2 的幂次方时，对算法做了优化，使用位操作代替取余操作。
```java
public EventExecutorChooser newChooser(EventExecutor[] executors) {
    if (isPowerOfTwo(executors.length)) {
        return new PowerOfTwoEventExecutorChooser(executors);
    } else {
        return new GenericEventExecutorChooser(executors);
    }
}

private static final class PowerOfTwoEventExecutorChooser implements EventExecutorChooser {
    private final AtomicInteger idx = new AtomicInteger();
    private final EventExecutor[] executors;

    PowerOfTwoEventExecutorChooser(EventExecutor[] executors) {
        this.executors = executors;
    }

    // 使用位操作
    @Override
    public EventExecutor next() {
        return executors[idx.getAndIncrement() & executors.length - 1];
    }
}

    private static final class GenericEventExecutorChooser implements EventExecutorChooser {
    private final AtomicLong idx = new AtomicLong();
    private final EventExecutor[] executors;

    GenericEventExecutorChooser(EventExecutor[] executors) {
        this.executors = executors;
    }

    // 使用取余操作
    @Override
    public EventExecutor next() {
        return executors[(int) Math.abs(idx.getAndIncrement() % executors.length)];
    }
}

```

### 3.2 Channel 注册

在 Nio 模式下，Channel 有两种类型，分别是：NioServerSocketChannel 和 NioSocketChannel，其中 NioServerSocketChannel 用于监听网络连接请求，生成 NioSocketChannel 连接，该 Channle 注册到 BossGroup 的 EventLoop 中，而 NioSocketChannel 负责真正的网络读写，注册到 WorkerGroup 的 EventLoop 中。

**1、NioServerSocketChannel 注册**

![netty-bind](/images/netty/netty-bind-v2.jpg "netty-bind")

在 Netty 的服务器启动过程中，主要的流程是一个 bind 操作，其流程包括：
- 创建 NioServerSocketChannel 类，完成初始化的工作，其中包括添加 ChannelHandler 类；
- 将 NioServerSocketChannel 注册到 EventLoop 中，同时向 Selector 对象中注册，不过此时并没有注册 OP_ACCEPT 事件；
- 执行网络层的 bind 操作；
- 执行读操作，主要是向 Selector 注册 OP_ACCEPT 事件。执行该操作后，便可接收网线的连接请求了。

NioServerSocketChannel 注册穿插在上面的 4 个步骤中，主要包括 1）将 NioServerSocketChannel 注册到 EventLoop 中；2）向 Selector 对象注册 OP_ACCEPT 事件。 

```java
// AbstractUnsafe 对象中的 register 操作
public final void register(EventLoop eventLoop, final ChannelPromise promise) {
    ...

    // 1、将 eventLoop 赋值给 AbstractChannel对象
    AbstractChannel.this.eventLoop = eventLoop;

    if (eventLoop.inEventLoop()) {
        register0(promise);
    } else {
        try {
            eventLoop.execute(new Runnable() {
                @Override
                public void run() {
                    // 2、向 Selector 对象注册 Channel
                    register0(promise);
                }
            });
        } catch (Throwable t) {
           ...
        }
    }
}

// AbstractNioChannel, 向 Selector 对象 注册 channel
// 此时没有注册 OP_ACCEPT 事件
protected void doRegister() throws Exception {
    boolean selected = false;

    while(true) {
        try {
            this.selectionKey = this.javaChannel().register(this.eventLoop().selector, 0, this);
            return;
        } catch (CancelledKeyException var3) {
            if (selected) {
                throw var3;
            }

            this.eventLoop().selectNow();
            selected = true;
        }
    }
}

// AbstractNioChannel，注册 OP_ACCEPT 事件
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

```
在上面的代码可以看到 registor 操作主要是分配一个 EventLoop，并将 EventLoop 赋值给 NioServerSocketChannel。向 Selector 注册 Channel 则分为两次，第一次注册时事件参数为 0，等于没有注册任何事件；第二次是在底层 Channel bind 操作之后，准备就绪之后，再注册 OP_ACCEPT 事件。

**2、NioSocketChannel 注册**
在 bind 操作的流程中，第一步是创建 NioServerSocketChannel 类，并进行初始化，此时会注册 ChannelHandler 类，其中就有一个 ServerBootstrapAcceptor handler 类，它的主要功能就是收到网络请求之后对NioSocketChannel 类进行参数配置，将其注册到 workerGroup 中，其核心代码如下所示：

```java
public void channelRead(ChannelHandlerContext ctx, Object msg) {
    final Channel child = (Channel) msg;
	
    // 1、添加 channelHandler 类
    child.pipeline().addLast(childHandler);

    // 2、设置 channel 的对数
    setChannelOptions(child, childOptions, logger);
    setAttributes(child, childAttrs);

    try {
		
        // 3、向 wokerGroup 注册 Channel
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
NioSocketChannel 和 NioServerSocketChannel 注册流程是一致的，差别只是注册到不同的 EventLoopGroup 及注册不同的 I/O 事件，其中  NioSocketChannel 注册的是 OP_READ 事件，而 NioServerSocketChannel 注册的是 OP_ACCEPT 事件。

### 3.3 事件循环

EventLoop 本质是一个事件循环，不断地从 Selector (Epoll) 对象中获取 I/O 事件，执行解码/反序列化操作后，再分发到上层的业务线程进行处理。另外一方面它可以执行用户自定义任务，如定时进行 Channel 空闲状态的检测，其核心代码如下所示：

```java
protected void run() {
    int selectCnt = 0;
    for (;;) {
        try {
            int strategy;
            try {
				
                // 1、计算执行策略
                strategy = selectStrategy.calculateStrategy(selectNowSupplier, hasTasks());
                switch (strategy) {
                case SelectStrategy.CONTINUE:
                    continue;

                ...
                }
            } catch (IOException e) {
                ...
            }

            selectCnt++;
            cancelledKeys = 0;
            needsToSelectAgain = false;
            final int ioRatio = this.ioRatio;
            boolean ranTasks;
            if (ioRatio == 100) {
                try {
                    if (strategy > 0) {
                        // 2、执行 I/O 事件
                        processSelectedKeys();
                    }
                } finally {
                    // 3、执行自定义任务
                    ranTasks = runAllTasks();
                }
            } else if (strategy > 0) {
                final long ioStartTime = System.nanoTime();
                try {
                    // 2、执行 I/O 事件
                    processSelectedKeys();
                } finally {
                    
                    final long ioTime = System.nanoTime() - ioStartTime;

                    // 3、执行自定义任务
                    ranTasks = runAllTasks(ioTime * (100 - ioRatio) / ioRatio);
                }
            } else {
                ranTasks = runAllTasks(0); // This will run the minimum number of tasks
            }

           ...
		   
        } catch (Throwable t) {
            handleLoopException(t);
        } finally {
           ... 
        }
    }
}

```
从上面的代码可以看到，根据计算的执行策略，可以为 I/O 事件处理及自定义任务分配不同的执行时间，详尽的代码在后面的文章介绍。
 
```java
private void processSelectedKey(SelectionKey k, AbstractNioChannel ch) {
   ...

    try {
        int readyOps = k.readyOps();

        // 1、处理 OP_CONNECT 事件
        if ((readyOps & SelectionKey.OP_CONNECT) != 0) {
            
            int ops = k.interestOps();
            ops &= ~SelectionKey.OP_CONNECT;
            k.interestOps(ops);

            unsafe.finishConnect();
        }

        // 2、处理 OP_WRITE 事件
        if ((readyOps & SelectionKey.OP_WRITE) != 0) {
            ch.unsafe().forceFlush();
        }

        // 3、处理 OP_READ 或 OP_ACCEPT 事件
        if ((readyOps & (SelectionKey.OP_READ | SelectionKey.OP_ACCEPT)) != 0 || readyOps == 0) {
            unsafe.read();
        }
    } catch (CancelledKeyException ignored) {
        unsafe.close(unsafe.voidPromise());
    }
}
```


I/O 事件的处理本质是处理 channel 的各种 I/O 事件，其中将 OP_ACCEPT 抽象为 Netty的 read 事件，可以理解为读取的数据是 NioSocketChannel 对象，其代码如下所示：

```java
protected int doReadMessages(List<Object> buf) throws Exception {
    SocketChannel ch = this.javaChannel().accept();

    try {
        if (ch != null) {
            buf.add(new NioSocketChannel(this, ch));
            return 1;
        }
    } catch (Throwable var6) {
        logger.warn("Failed to create a new channel from an accepted socket.", var6);

        try {
            ch.close();
        } catch (Throwable var5) {
            logger.warn("Failed to close a socket.", var5);
        }
    }

    return 0;
}
``` 

可以看出来，NioServerSocketChannel 收到 OP_ACCEPT 事件后，会生成 SocketChannel 对象，然后通过 ServerBootstrapAcceptor handle 类处理后，注册到 workerGroup 中，再监听 SocketChannel 对象的 OP_READ 事件，最终实现网络数据的读写。

## 4. 总结

通过对 Netty 中 Reactor 模型的分析，对 Netty 的线程模型及 I/O 的事件处理有了一个初步的认识，后续的文章将对涉及到的模块进行详尽的分析，希望能够深入理解 Netty 的设计思路。

