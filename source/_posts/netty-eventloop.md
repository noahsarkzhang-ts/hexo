---
title: Netty 系列：EventLoop
date: 2021-08-29 21:17:38
tags:
- EventLoop
- 事件循环
categories:
- Netty
---

## 1. 概述

EventLoop 是 Reactor 模式中的执行者，首先它持有 Selector 对象，监听多路 SocketChannel 的网络 I/O 事件，并对 I/O 事件分发处理。同时，它持有一个 Thread 对象，除了监听网络 I/O 事件， EventLoop 也可以执行提交的任务，包括定时任务，总结来说，EventLoop 具有如下三大功能：
1. 负责监听 SocketChannel 对象的 I/O 事件；
2. 处理分发 I/O 事件；
3. 执行任务，包括定时任务。

整体的处理流程如下：
```java
protected void run() {
    int selectCnt = 0;
    for (;;) {
        try {

            // 1、监听 Channel 网络事件
            if (!hasTasks()) {
                strategy = select(curDeadlineNanos);
            }
            
            final int ioRatio = this.ioRatio;
            final long ioStartTime = System.nanoTime();
            
            // 2、处理网络事件 
            try {
                processSelectedKeys();
            } finally {
                
                final long ioTime = System.nanoTime() - ioStartTime;
                
                // 3、执行任务
                ranTasks = runAllTasks(ioTime * (100 - ioRatio) / ioRatio);
            }

        } catch (Throwable t) {
            handleLoopException(t);
        } finally {
            // ... 
        }
    }
}

```

**说明：** 代码以 NioEventLoop 为例。

## 2. 流程

上文分析了 EventLoop 的主要功能，在这部分内容中这三大功能及线程的创建，我们先从线程的创建开始。

### 2.1 线程创建

线程相关的变量：

```java
// EventLoop 线程对象
private volatile Thread thread;

// 线程状态
private volatile int state = ST_NOT_STARTED;

private static final int ST_NOT_STARTED = 1;
private static final int ST_STARTED = 2;
private static final int ST_SHUTTING_DOWN = 3;
private static final int ST_SHUTDOWN = 4;
private static final int ST_TERMINATED = 5;

// 事件执行器，线程池
private final Executor executor;

```

EventLoop 中持有一个线程的引用，在第一次执行任务的时候启动，提供任务的线程如果已经是 EventLoop 线程，将任务提交给任务即可，如果是非 EventLoop 线程，则需要启动 EventLoop 线程。

```java
private void execute(Runnable task, boolean immediate) {
    boolean inEventLoop = inEventLoop();
    addTask(task);
    if (!inEventLoop) {
        startThread();
        
        // ...
    }
}

```
EventLoop 中通过 state 字段来标识是否启动，通过判断该字段来决定是否启动线程，其中 state 字段是 volatile 类型，并通过 AtomicIntegerFieldUpdater 进行原子更新，保证线程的安全。

```java
private void startThread() {
    if (state == ST_NOT_STARTED) {
        if (STATE_UPDATER.compareAndSet(this, ST_NOT_STARTED, ST_STARTED)) {
            boolean success = false;
            try {
                doStartThread();
                success = true;
            } finally {
                if (!success) {
                    STATE_UPDATER.compareAndSet(this, ST_STARTED, ST_NOT_STARTED);
                }
            }
        }
    }
}

```

线程的启动是通过 executor 添加一个任务，在 executor 中启动一个线程，再把该线程赋值给 EventLoop，等同于使用了只有一个线程的线程池来生成线程。可以看到，任务的主体是 SingleThreadEventExecutor.this.run() 方法，该方法就是前文说到的 EventLoop 主体业务逻辑。

```java
private void doStartThread() {
    assert thread == null;
    
    // 使用 executor 来启动线程
    executor.execute(new Runnable() {
        @Override
        public void run() {
            // 设置线程变量
            thread = Thread.currentThread();
            if (interrupted) {
                thread.interrupt();
            }

            boolean success = false;
            updateLastExecutionTime();
            try {
                // 执行 EventLoop 的业务逻辑
                SingleThreadEventExecutor.this.run();
                success = true;
            } catch (Throwable t) {
                logger.warn("Unexpected exception from an event executor: ", t);
            } finally {
                // ...
            }
        }
    });
}

```
executor 使用的是 ThreadPerTaskExecutor 对象，在 NioEventLoopGroup 初始化的时候生成。

```java
// Executor 为 null
public NioEventLoopGroup(int nThreads) {
    this(nThreads, (Executor) null);
}

protected MultithreadEventExecutorGroup(int nThreads, Executor executor,
                                        EventExecutorChooserFactory chooserFactory, Object... args) {
    // 如果 Executor 为 null,则使用 ThreadPerTaskExecutor
    if (executor == null) {
        executor = new ThreadPerTaskExecutor(newDefaultThreadFactory());
    }

    children = new EventExecutor[nThreads];

    for (int i = 0; i < nThreads; i ++) {
        boolean success = false;
        try {
            // 生成 EventLoop
            children[i] = newChild(executor, args);
            success = true;
        } catch (Exception e) {
            
            throw new IllegalStateException("failed to create a child event loop", e);
        } finally {
            // ...
        }
    }

    // ...
}

protected EventLoop newChild(Executor executor, Object... args) throws Exception {
    EventLoopTaskQueueFactory queueFactory = args.length == 4 ? (EventLoopTaskQueueFactory) args[3] : null;
    return new NioEventLoop(this, executor, (SelectorProvider) args[0],
        ((SelectStrategyFactory) args[1]).newSelectStrategy(), (RejectedExecutionHandler) args[2], queueFactory);
}
```

ThreadPerTaskExecutor 执行器会生成一个新的线程来执行新的任务，该线程就是 FastThreadLocalThread 对象。

```java
public final class ThreadPerTaskExecutor implements Executor {
    
    // 线程工厂对象
    private final ThreadFactory threadFactory;
   
    // 生成一个新的线程执行任务
    @Override
    public void execute(Runnable command) {
        threadFactory.newThread(command).start();
    }
}

public class DefaultThreadFactory implements ThreadFactory {

    // ...

    // 生成一个新的线程对象
    @Override
    public Thread newThread(Runnable r) {
        Thread t = newThread(FastThreadLocalRunnable.wrap(r), prefix + nextId.incrementAndGet());
        
        // ...
        
        return t;
    }

    // 生成 FastThreadLocalThread 线程
    protected Thread newThread(Runnable r, String name) {
        return new FastThreadLocalThread(threadGroup, r, name);
    }
}

```

通过上面的代码分析，EventLoop 中的线程由 ThreadPerTaskExecutor 执行器生成，线程对象为 DefaultThreadFactory。

### 2.3 监听网络 I/O 事件

Selector 相关的变量：

```java
// NioEventLoop

private Selector selector;
private Selector unwrappedSelector;
private SelectedSelectionKeySet selectedKeys;

private final SelectorProvider provider;

private static final long AWAKE = -1L;
private static final long NONE = Long.MAX_VALUE;

// nextWakeupNanos is:
//    AWAKE            when EL is awake
//    NONE             when EL is waiting with no wakeup scheduled
//    other value T    when EL is waiting with wakeup scheduled at time T
private final AtomicLong nextWakeupNanos = new AtomicLong(AWAKE);

private final SelectStrategy selectStrategy;

private int cancelledKeys;
private boolean needsToSelectAgain;

```

在这个阶段有三个重点：
1. 设置 selector 的超时时间，主要是以下一个定时任务执行的时间间隔作为参考来设置超时时间，避免阻塞定时任务的准时执行；
2. selector 唤醒的机制，如果超时时间过长，中途有任务插入，需要执行，此时需要中断 selector；
3. 重建 selector，解决 bug 8566。

```java
protected void run() {
    int selectCnt = 0;
    for (;;) {
        try {
            int strategy;
            try {
                strategy = selectStrategy.calculateStrategy(selectNowSupplier, hasTasks());
                switch (strategy) {
                case SelectStrategy.CONTINUE:
                    continue;

                case SelectStrategy.BUSY_WAIT:
                    // fall-through to SELECT since the busy-wait is not supported with NIO

                case SelectStrategy.SELECT:
                    // 1、计算出下一个定时任务的时间间隔；
                    long curDeadlineNanos = nextScheduledTaskDeadlineNanos();
                    if (curDeadlineNanos == -1L) {
                        curDeadlineNanos = NONE; // nothing on the calendar
                    }
                    
                    nextWakeupNanos.set(curDeadlineNanos);
                    try {
                        if (!hasTasks()) {
                            // 2、以下一个定时任务的时间间隔作为超时的时间，进行网络时间的监听
                            strategy = select(curDeadlineNanos);
                        }
                    } finally {
                        nextWakeupNanos.lazySet(AWAKE);
                    }
                    // fall through
                default:
                }
            } catch (IOException e) {
                // If we receive an IOException here its because the Selector is messed up. Let's rebuild
                // the selector and retry. https://github.com/netty/netty/issues/8566
                // 3、创建 Selector，解决 bug 8566。
                rebuildSelector0();
                selectCnt = 0;
                handleLoopException(e);
                continue;
            }

            // ...
        } catch (Throwable t) {
            handleLoopException(t);
        } finally {
            // ...
        }
    }
}
```
计算下一个定时任务执行的时间间隔逻辑比较简单，将 ScheduledFutureTask 任务添加到 scheduledTaskQueue 队列中，而 scheduledTaskQueue 是一个优先级队列，它已经将 ScheduledFutureTask 根据执行时间进行了排序，取出的第一个元素便是最近将要执行的任务，计算它还需要多久需要执行便可。

```java
// 计算下一个定时任务执行的时间间隔
protected final long nextScheduledTaskDeadlineNanos() {
    ScheduledFutureTask<?> scheduledTask = peekScheduledTask();
    return scheduledTask != null ? scheduledTask.deadlineNanos() : -1;
}

// 取下一个执行的定时任务
final ScheduledFutureTask<?> peekScheduledTask() {
    Queue<ScheduledFutureTask<?>> scheduledTaskQueue = this.scheduledTaskQueue;
    return scheduledTaskQueue != null ? scheduledTaskQueue.peek() : null;
}

// 优先级队列
PriorityQueue<ScheduledFutureTask<?>> scheduledTaskQueue = new DefaultPriorityQueue<ScheduledFutureTask<?>>(
                    SCHEDULED_FUTURE_TASK_COMPARATOR,
                    // Use same initial capacity as java.util.PriorityQueue
                    11);

// ScheduledFutureTask
final class ScheduledFutureTask<V> extends PromiseTask<V> implements ScheduledFuture<V>, PriorityQueueNode {
    private static final long START_TIME = System.nanoTime();

    // set once when added to priority queue
    private long id;

    private long deadlineNanos;
    /* 0 - no repeat, >0 - repeat at fixed rate, <0 - repeat with fixed delay */
    private final long periodNanos;

    private int queueIndex = INDEX_NOT_IN_QUEUE;

    // 根据 deadlineNanos 及 id 进行排序
    @Override
    public int compareTo(Delayed o) {
        if (this == o) {
            return 0;
        }

        ScheduledFutureTask<?> that = (ScheduledFutureTask<?>) o;
        long d = deadlineNanos() - that.deadlineNanos();
        if (d < 0) {
            return -1;
        } else if (d > 0) {
            return 1;
        } else if (id < that.id) {
            return -1;
        } else {
            assert id != that.id;
            return 1;
        }
    }

   // ...

}
```

外部线程执行新任务的时候，任务需要立即执行的话，需要唤醒 selector，避免因 selector 长时间等待错过执行时机。

```java
// 执行新任务
private void execute(Runnable task, boolean immediate) {
    // ...

    // 如果任务需要立即执行，则需要中断 Selector。
    if (!addTaskWakesUp && immediate) {
        wakeup(inEventLoop);
    }
}

// 唤醒 selector
protected void wakeup(boolean inEventLoop) {
    if (!inEventLoop && nextWakeupNanos.getAndSet(AWAKE) != AWAKE) {
        selector.wakeup();
    }
}

```

重建 selector，解决 bug 8566 的逻辑，后续有时间再另外分析。

### 2.4 处理及分发网络 I/O 事件

在 NioEventLoop 中，处理 I/O 事件的时间与执行任务的时间比率为 1:1，即两者的执行时间是相等的。

```java
// 默认情况下处理 I/O 事件的时间比率为 50%，即 I/O 处理的时间占执行时间的 50 %。
private volatile int ioRatio = 50;

final long ioStartTime = System.nanoTime();
try {
    // 处理 I/O 事件
    processSelectedKeys();
} finally {
    // Ensure we always run tasks.
    final long ioTime = System.nanoTime() - ioStartTime;

    // 执行任务
    ranTasks = runAllTasks(ioTime * (100 - ioRatio) / ioRatio);
}

```
现在分析 I/O 事件的处理，这里提供了两种方式，一种是经过 Netty 优化过数据结构的方式，一种是 Java 原生的方式，它们之间的区别主要是存放 SelectionKey 对象的底层数据结构的差异，而处理流程没有变。

```java
private void processSelectedKeys() {
    if (selectedKeys != null) {
        // 优化的处理方式
        processSelectedKeysOptimized();
    } else {
        processSelectedKeysPlain(selector.selectedKeys());
    }
}
```

优化的方法主要是通过反射的方式，将 Selector 中 selectedKeys 和 publicSelectedKeys 字段替换为 Netty 版的 SelectedSelectionKeySet。数据结构做了那些优化可以再深入分析源码。

```java
final Selector unwrappedSelector;
try {
    unwrappedSelector = provider.openSelector();
} catch (IOException e) {
    throw new ChannelException("failed to open a new selector", e);
}

final Class<?> selectorImplClass = (Class<?>) maybeSelectorImplClass;
final SelectedSelectionKeySet selectedKeySet = new SelectedSelectionKeySet()

try {
        Field selectedKeysField = selectorImplClass.getDeclaredField("selectedKeys");
        Field publicSelectedKeysField = selectorImplClass.getDeclaredField("publicSelectedKeys");

        // java 9 以上版本，设置 selectedKeysField 及 publicSelectedKeysField 的方式
        if (PlatformDependent.javaVersion() >= 9 && PlatformDependent.hasUnsafe()) {
            long selectedKeysFieldOffset = PlatformDependent.objectFieldOffset(selectedKeysField);
            long publicSelectedKeysFieldOffset =
                    PlatformDependent.objectFieldOffset(publicSelectedKeysField);

            if (selectedKeysFieldOffset != -1 && publicSelectedKeysFieldOffset != -1) {
                PlatformDependent.putObject(
                        unwrappedSelector, selectedKeysFieldOffset, selectedKeySet);
                PlatformDependent.putObject(
                        unwrappedSelector, publicSelectedKeysFieldOffset, selectedKeySet);
                return null;
            }
        }

        // java 9 以下版本，设置字段的方式
        Throwable cause = ReflectionUtil.trySetAccessible(selectedKeysField, true);
        if (cause != null) {
            return cause;
        }
        cause = ReflectionUtil.trySetAccessible(publicSelectedKeysField, true);
        if (cause != null) {
            return cause;
        }

        selectedKeysField.set(unwrappedSelector, selectedKeySet);
        publicSelectedKeysField.set(unwrappedSelector, selectedKeySet);
        return null;
    } catch (NoSuchFieldException e) {
        return e;
    } catch (IllegalAccessException e) {
        return e;
    }
```

处理 I/O 事件的大致流程如下：
1. 遍历 selectedKeys 集合，处理所有 Channel 的 I/O 事件，一个 SelectionKey 对象代表一个 Channel 的 I/O 事件；
2. 取出 SelectionKey 对象中的附件，该附件由 AbstractNioChannel.doRegister 方法注册到 Selector 对象上，附件就是 AbstractNioChannel 自身，触发 I/O 事件时，再由 SelectionKey 对象返回；
3. 根据附件对象的不同，调用不同的处理逻辑，这里主要是处理 Channel 的 I/O 事件

```java
private void processSelectedKeysOptimized() {
    // 遍历 selectedKeys 集合，处理所有 Channel 的 I/O 事件
    for (int i = 0; i < selectedKeys.size; ++i) {
        final SelectionKey k = selectedKeys.keys[i];
        // null out entry in the array to allow to have it GC'ed once the Channel close
        // See https://github.com/netty/netty/issues/2363
        selectedKeys.keys[i] = null;
        
        // 取出 SelectionKey 对象中的附件，由注册方法添加到 Selector 对象中。
        final Object a = k.attachment();
        
        // 根据附件对象的不同，调用不同的处理逻辑，这里主要是处理 Channel 的 I/O 事件 
        if (a instanceof AbstractNioChannel) {
            processSelectedKey(k, (AbstractNioChannel) a);
        } else {
            @SuppressWarnings("unchecked")
            NioTask<SelectableChannel> task = (NioTask<SelectableChannel>) a;
            processSelectedKey(k, task);
        }

        if (needsToSelectAgain) {
            // null out entries in the array to allow to have it GC'ed once the Channel close
            // See https://github.com/netty/netty/issues/2363
            selectedKeys.reset(i + 1);

            selectAgain();
            i = -1;
        }
    }
}

// AbstractNioChannel 注册方法
protected void doRegister() throws Exception {
    boolean selected = false;
    for (;;) {
        try {
            // 将 AbstractNioChannel 以附件的方式注册到 Selector 中。
            selectionKey = javaChannel().register(eventLoop().unwrappedSelector(), 0, this);
            return;
        } catch (CancelledKeyException e) {
           // ...
        }
    }
}

// 注册方法的申明
public abstract SelectionKey register(Selector sel, int ops, Object att)
        throws ClosedChannelException;


```

真正的处理逻辑在 processSelectedKey 方法中处理，这里有两个重点：
1. 写缓存空间充足，注册 OP_WRITE 事件会频繁触发，导致 cpu 空转，所以正常情况下，不需要注册 OP_WRITE 事件，只有在写缓存满的时候才会注册该事件，触发之后进行刷新操作；
2. 在 Netty 中，将 OP_ACCEPT 当作读操作，只不过它读取的数据比较特殊，是 SocketChannel 对象。

事件的处理逻辑包含在 AbstractNioChannel.NioUnsafe 中，由该方法调用 ChannelPipeline 中的回调方法，至此，将事件处理由网络层传递给 Netty 框架层。

```java
private void processSelectedKey(SelectionKey k, AbstractNioChannel ch) {
    // unsafe
    final AbstractNioChannel.NioUnsafe unsafe = ch.unsafe();
    // ...

    try {
        int readyOps = k.readyOps();
        
        // 1、处理 OP_CONNECT 事件
        if ((readyOps & SelectionKey.OP_CONNECT) != 0) {
            int ops = k.interestOps();
            ops &= ~SelectionKey.OP_CONNECT;
            k.interestOps(ops);

            unsafe.finishConnect();
        }

        // 2、处理 OP_WRITE 事件，正常情况下，不需要注册 OP_WRITE 事件，
        // 只有在写缓存满的时候才会注册该事件。
        if ((readyOps & SelectionKey.OP_WRITE) != 0) {
           
            ch.unsafe().forceFlush();
        }
        
        // 3、处理 OP_READ 及 OP_ACCEPT 事件。在 Netty 中，将 OP_ACCEPT 当作读操作，只不过
        // 它读取的数据比较特殊，是 SocketChannel 对象。
        if ((readyOps & (SelectionKey.OP_READ | SelectionKey.OP_ACCEPT)) != 0 || readyOps == 0) {
            unsafe.read();
        }
    } catch (CancelledKeyException ignored) {
        unsafe.close(unsafe.voidPromise());
    }
}
```

以 unsafe.read() 为例，在 NioMessageUnsafe 类的实现中，读取操作会调用 AbstractNioChannel 子类的 doReadMessages 方法读取网络数据，并写入到 readBuf 中，再调用 ChannelPipeline 中的 fireChannelRead 方法将数据传递给 Netty 框架层。

```java
private final class NioMessageUnsafe extends AbstractNioUnsafe {

    // 读 Buffer
    private final List<Object> readBuf = new ArrayList<Object>();

    @Override
    public void read() {
        
        final ChannelConfig config = config();
        final ChannelPipeline pipeline = pipeline();

        boolean closed = false;
        Throwable exception = null;
        try {
            try {
                do {
                    // 1、调用读取操作
                    int localRead = doReadMessages(readBuf);
                    
                } while (allocHandle.continueReading());
            } catch (Throwable t) {
                exception = t;
            }

            int size = readBuf.size();
            for (int i = 0; i < size; i ++) {
                readPending = false;
                // 2、触发 fireChannelRead 方法
                pipeline.fireChannelRead(readBuf.get(i));
            }
            
            // .. 
        } finally {
           // ...
        }
    }
}
```

在 NioServerSocketChannel 类 doReadMessages 实现中，读取到的数据是 SocketChannel，该对象会分配给 WorkerGroup 中，由 WorkerGroup 中的 EventLoop 去读取网络数据。

```java
// NioServerSocketChannel
protected int doReadMessages(List<Object> buf) throws Exception {
    SocketChannel ch = SocketUtils.accept(javaChannel());

    try {
        if (ch != null) {
            buf.add(new NioSocketChannel(this, ch));
            return 1;
        }
    } catch (Throwable t) {
        // ...
    }

    return 0;
}
```

而在 NioSocketChannel 类的 doReadBytes 实现中，读取到的是 ByteBuf，传递给上层的是 ByteBuf 对象，上层对象再对其进行反序列化、业务处理等操作。

```java
// NioSocketChannel
protected int doReadBytes(ByteBuf byteBuf) throws Exception {
    final RecvByteBufAllocator.Handle allocHandle = unsafe().recvBufAllocHandle();
    allocHandle.attemptedBytesRead(byteBuf.writableBytes());
    return byteBuf.writeBytes(javaChannel(), allocHandle.attemptedBytesRead());
}
```

至此，根据 I/O 事件的类型，将数据分发到了上层中，上层业务可以继续处理。

### 2.5 执行任务

#### 2.5.1 执行流程

执行任务相关的变量：

```java
// 任务队列
private final Queue<Runnable> taskQueue;

// 定时任务队列
PriorityQueue<ScheduledFutureTask<?>> scheduledTaskQueue;
```

在 EventLoop 中，有两类任务，一是常规的任务，没有时间属性，二是周期性或延时的定时任务，它们分别存放到两个不同的队列。任务执行时，先将到期的定时任务从 scheduledTaskQueue 队列移动到 taskQueue 中，再统一执行 taskQueue 队列中的任务。

任务执行的大致如下：
1. 将到期的定时任务移动到 taskQueue 中；
2. 计算此次执行的时长，如果执行的时间超过设定的执行时长，则退出进行下一轮的事件处理；
3. 遍历执行 taskQueue 中的任务，在两种情况下退出任务的执行：1）任务的执行时长超过了设定的执行时长；2）taskQueue 队列为空；

```java
protected boolean runAllTasks(long timeoutNanos) {
	// 1、将定时任务移动到 taskQueue 中
    fetchFromScheduledTaskQueue();
	
	// 2、从 taskQueue 中取出任务
    Runnable task = pollTask();
    if (task == null) {
        afterRunningAllTasks();
        return false;
    }
	
	// 3、计算任务执行的时长，如果超过传入的执行时长，需要退出进行下一轮的事件处理。
    final long deadline = timeoutNanos > 0 ? ScheduledFutureTask.nanoTime() + timeoutNanos : 0;
    long runTasks = 0;
    long lastExecutionTime;
    for (;;) {
		
		// 4、执行任务
        safeExecute(task);

        runTasks ++;

        // 5、每执行完 64 个任务之后，判断是否超过传入的执行时长，若超过，则退出
        if ((runTasks & 0x3F) == 0) {
            lastExecutionTime = ScheduledFutureTask.nanoTime();
            if (lastExecutionTime >= deadline) {
                break;
            }
        }

		// 6、执行下一个任务，如果任务为空，则退出
        task = pollTask();
        if (task == null) {
            lastExecutionTime = ScheduledFutureTask.nanoTime();
            break;
        }
    }

    afterRunningAllTasks();
    this.lastExecutionTime = lastExecutionTime;
    return true;
}
```

移动到期的定时任务逻辑相对简单：遍历 scheduledTaskQueue 队列，将到期的任务从 scheduledTaskQueue 队列中移除，再添加到 taskQueue 队列中，如果添加失败，则再添加回 scheduledTaskQueue 队列，等待下次再操作。

```java
private boolean fetchFromScheduledTaskQueue() {
    // ...
	
	// 1、nanoTime 表示从程序启动到此时的时长；
	// 时间的判断都是根据相对时间来判断，起始时间为程序启动的时间
    long nanoTime = AbstractScheduledEventExecutor.nanoTime();
    for (;;) {
		
		// 2、取出到期的任务
        Runnable scheduledTask = pollScheduledTask(nanoTime);
        if (scheduledTask == null) {
            return true;
        }
		
		// 3、将任务添加到 taskQueue 中
        if (!taskQueue.offer(scheduledTask)) {
           
		   // 4、如果添加失败，再添加回 scheduledTaskQueue 队列，等待下次添加
            scheduledTaskQueue.add((ScheduledFutureTask<?>) scheduledTask);
            return false;
        }
    }
}

```

在定时任务任务中超时的判断是基于相对时间的，起始时间为程序启动的时间。在 scheduledTask 中关联有一个任务执行的截止时间，将这个截止时间与当前计算的时间进行比较，小于当前的时间则说明已经过期，满足执行的条件，则需要将该任务移动到 taskQueue。

另外，scheduledTaskQueue 是一个优先级队列，已经根据截止时间排序，队首的元素是最先到期的任务，如果取到了未到期的任务，则停止遍历，因为后面的任务截止时间更大，没有必要进行比较了。

```java
protected final Runnable pollScheduledTask(long nanoTime) {
    assert inEventLoop();
	
	// 1、取出队首的任务
    ScheduledFutureTask<?> scheduledTask = peekScheduledTask();
	
	// 2、判断任务是否过期，判断的逻辑是：比较任务的截止时间与当前时间进行比较，如果
	// 截止时间小于当前时间，则说明过期。
    if (scheduledTask == null || scheduledTask.deadlineNanos() - nanoTime > 0) {
        return null;
    }
	
	// 3、移出对首的任务
    scheduledTaskQueue.remove();
    scheduledTask.setConsumed();
    return scheduledTask;
}

private static final long START_TIME = System.nanoTime();
// 计算相对时间
static long nanoTime() {
    return System.nanoTime() - START_TIME;
}

// 初始化 scheduledTaskQueue 队列
PriorityQueue<ScheduledFutureTask<?>> scheduledTaskQueue() {
    if (scheduledTaskQueue == null) {
        scheduledTaskQueue = new DefaultPriorityQueue<ScheduledFutureTask<?>>(
                SCHEDULED_FUTURE_TASK_COMPARATOR,
                // Use same initial capacity as java.util.PriorityQueue
                11);
    }
    return scheduledTaskQueue;
}
```

#### 2.5.2 任务的添加
上面分析了任务执行的流程，下面看下这两类任务怎么添加到任务队列中。

**1、常规任务**

常规任务是通过 execute 方法添加的，该方法含义上有执行的意思，但实际上执行该方法，只是将任务添加到 taskQueue 中，任务的执行最终是在 EventLoop 线程中完成的。

```java
// 添加一个常规任务
public void execute(Runnable task) {
    ObjectUtil.checkNotNull(task, "task");
    execute(task, !(task instanceof LazyRunnable) && wakesUpForTask(task));
}

// 添加或执行任务
private void execute(Runnable task, boolean immediate) {
    boolean inEventLoop = inEventLoop();
	
	// 将任务添加到 taskQueue 队列
    addTask(task);
    if (!inEventLoop) {
		// 如果当前线程不是 EventLoop 线程，则尝试启动 EventLoop 线程。
        startThread();
        // ...
    }

	// 如果任务不是 LazyRunnable 或 NonWakeupRunnable 子类，则
	// 唤醒 EventLoop 线程，立即执行任务
    if (!addTaskWakesUp && immediate) {
        wakeup(inEventLoop);
    }
}

// 添加任务
protected void addTask(Runnable task) {
    ObjectUtil.checkNotNull(task, "task");
	
	// 如果任务添加不成功，则拒绝任务
    if (!offerTask(task)) {
        reject(task);
    }
}

// 添加任务到 taskQueue 中
final boolean offerTask(Runnable task) {
    if (isShutdown()) {
        reject();
    }
    return taskQueue.offer(task);
}
```

**2、定时任务**
定时任务有两种：1）延时任务；2）周期性任务。它们是通过 schedule 方法添加，方法定义如下所示：

```java

// 延时任务
@Override
ScheduledFuture<?> schedule(Runnable command, long delay, TimeUnit unit);

// 带返回结果的延时任务
@Override
<V> ScheduledFuture<V> schedule(Callable<V> callable, long delay, TimeUnit unit);

// 固定比率的周期性任务
@Override
ScheduledFuture<?> scheduleAtFixedRate(Runnable command, long initialDelay, long period, TimeUnit unit);

// 固定延时的周期性任务
@Override
ScheduledFuture<?> scheduleWithFixedDelay(Runnable command, long initialDelay, long delay, TimeUnit unit);
```

两种类型的定时任务统一封装为 ScheduledFutureTask 任务，添加一个定时任务实际就是添加一个 ScheduledFutureTask 对象到 scheduledTaskQueue 中。添加 ScheduledFuture 的过程中，如果当前线程就是 EventLoop 线程，则直接操作即可，如果当前线程不是 EventLoop 线程，则添加一个常规任务，用来执行该操作。这样设计，应该是出于线程安全的考虑，保证只有 EventLoop 线程执行添加操作。在这里，还需要考虑定时任务已经过期，需要唤醒 EventLoop 线程执行任务。

```java
private <V> ScheduledFuture<V> schedule(final ScheduledFutureTask<V> task) {

	// 如果当前线程是 EventLoop 线程则直接将任务添加到 scheduledTaskQueue 中；
	// 如果不是，添加一个常规任务，用来执行添加操作。
    if (inEventLoop()) {
        scheduleFromEventLoop(task);
    } else {
		// 计算任务执行的截止时间
        final long deadlineNanos = task.deadlineNanos();
        
		// 比较任务的执行时间与 EventLoop 线程被唤醒的时间的大小，
		// 如果小于线程的唤醒时间，除了向 taskQueue 添加任务之外，需要唤醒线程执行任务；
		// 如果大于线程的唤醒时间，只是向 taskQueue 添加任务，不需要唤醒线程。
        if (beforeScheduledTaskSubmitted(deadlineNanos)) {
            execute(task);
        } else {
            lazyExecute(task);
            if (afterScheduledTaskSubmitted(deadlineNanos)) {
                execute(WAKEUP_TASK);
            }
        }
    }

    return task;
}

// 向 scheduledTaskQueue 队列添加定时任务
final void scheduleFromEventLoop(final ScheduledFutureTask<?> task) {
    // nextTaskId a long and so there is no chance it will overflow back to 0
    scheduledTaskQueue().add(task.setId(++nextTaskId));
}

// 判断任务的执行截止时间与 EventLoop 线程被唤醒的时间的大小
protected boolean beforeScheduledTaskSubmitted(long deadlineNanos) {
    // Note this is also correct for the nextWakeupNanos == -1 (AWAKE) case
    return deadlineNanos < nextWakeupNanos.get();
}

```

ScheduledFutureTask 对象封装了三个功能：
1. 执行添加任务，将 ScheduledFutureTask 对象本身添加到 scheduledTaskQueue 队列；
2. 执行延时任务，由于延时任务只会执行一次，执行完便结束；
3. 执行周期性任务，执行完本轮的任务之外，还需要将 ScheduledFutureTask 添加回 scheduledTaskQueue 队列，等待下一轮执行。

```java

final class ScheduledFutureTask<V> extends PromiseTask<V> implements ScheduledFuture<V>, PriorityQueueNode {
    private static final long START_TIME = System.nanoTime();
	
	// set once when added to priority queue
    private long id;

    private long deadlineNanos;
	
	// periodNanos 表示任务的任务：
	// 0 - no repeat, >0 - repeat at fixed rate, <0 - repeat with fixed delay 
    private final long periodNanos;
	
	private int queueIndex = INDEX_NOT_IN_QUEUE;

    static long nanoTime() {
        return System.nanoTime() - START_TIME;
    }

    static long initialNanoTime() {
        return START_TIME;
    }
	
	// ...

    @Override
    public void run() {
        assert executor().inEventLoop();
        try {
			
			// 如果未到期，则执行添加任务
            if (delayNanos() > 0L) {
                // Not yet expired, need to add or remove from queue
                if (isCancelled()) {
                    scheduledExecutor().scheduledTaskQueue().removeTyped(this);
                } else {
					// 向 scheduledTaskQueue 添加自己
                    scheduledExecutor().scheduleFromEventLoop(this);
                }
                return;
            }
			
			// 如果是延时任务，只需要执行一次
            if (periodNanos == 0) {
                if (setUncancellableInternal()) {
					// 执行任务
                    V result = runTask();
					
					// 通知执行成功
                    setSuccessInternal(result);
                }
            } else { // 如果是周期性任务，执行完任务之后，还需要重新再调度
                // check if is done as it may was cancelled
                if (!isCancelled()) {
					// 执行任务
                    runTask();
                    if (!executor().isShutdown()) {
                        if (periodNanos > 0) {
                            deadlineNanos += periodNanos;
                        } else {
                            deadlineNanos = nanoTime() - periodNanos;
                        }
                        if (!isCancelled()) {
							
							// 添加回 scheduledTaskQueue 队列，等待下一次执行
                            scheduledExecutor().scheduledTaskQueue().add(this);
                        }
                    }
                }
            }
        } catch (Throwable cause) {
            setFailureInternal(cause);
        }
    }

	// ... 
}

```
至此，任务的执行分析完毕。

## 3. 总结

EventLoop 担当了网络层与 Netty 框架间的桥梁作用，本质是一个事件循环，不断监听 Channel 的网络 I/O 事件，并进行分发处理。另外，也承担了执行任务的作用，包括常规的任务及定时任务。理解 EventLoop 的事件循环会极大加深对 Netty 的理解。