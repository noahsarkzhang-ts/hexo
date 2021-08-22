---
title: Netty 系列：Reactor
date: 2021-08-22 13:22:53
tags:
- reactor
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

## 4. 总结

