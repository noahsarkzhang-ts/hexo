---
title: SynchronousQueue 原理
date: 2019-09-01 13:53:11
tags:
- SynchronousQueue
- 同步队列
- 线程池
categories:
- 阻塞队列
---

这篇文章主要讲述SynchronousQueue数据结构及在线程池中的应用。

<!-- more -->

## 1. 概述
在生产者和消费者的线程模型下，生产者线程生产数据（事件，任务等），消费者线程消费数据。通常情况下，它们需要一个中间的数据结构来交换数据，如队列。生成者线程将数据存入队列，若队列满了则阻塞生产者线程，等待消费者线程唤醒；消费者线程从队列取数据，若队列为空则阻塞消费者线程，等待生产者线程唤醒。在这种场景下，如果生产数据过快，队列中会堆积很多数据，如果是无界队列的话，可能会造成问题。现在提供了另外一种选择，即SynchronousQueue，它内部没有容量，生产者线程和消费者线程进行一一匹配，亲手(handoff)交换数据。

SynchronousQueue是一种特殊的阻塞队列，它没有实际的容量，任意线程（生产者线程或者消费者线程，生产类型的操作如put/offer，消费类型的操作如poll/take）都会等待知道获得数据或者交付完成数据才会返回，一个生产者线程的使命是将线程附着着的数据交付给一个消费者线程，而一个消费者线程则是等待一个生产者线程的数据。它们会在匹配到互补线程的时候就会做数据交易，比如生产者线程遇到消费者线程时，或者消费者线程遇到生产者线程时，一个生产者线程就会将数据交付给消费者线程，然后共同退出。<sup>\[1\]<sup>

SynchronousQueue的一个使用场景是在线程池里。Executors.newCachedThreadPool()就使用了SynchronousQueue，这个线程池根据需要（新任务到来时）创建新的线程，如果有空闲线程则会重复使用，线程空闲了60秒后会被回收。因为SynchronousQueue没有容量，因此offer和take会一直阻塞(如果操作允许超时且超时时间为0，没有匹配的线程时则直接返回不回阻塞)，直到有另一个线程已经准备好参与到交付过程中。在线程池中，提交的任务尽量是执行时间短、不会被阻塞，这样才能保证线程的重复使用，否则就会在短时间内生成大量的线程，引起内存被耗尽的问题（一个线程会申请一个线程栈）。

在对SynchronousQueue进一步分析前，先对SynchronousQueue的基本结构及对外接口的接口（方法）做了一个简单的描述，在后面的部分会依赖这些知识点。

SynchronousQueue内部逻辑封装在Transferer的实现类中，该类只有一个transfer方法，put/offer及poll/take都是用它来实现，它的声明如下：
```java
abstract static class Transferer<E> {
    /**
     * 执行put/offer和poll/take方法.
     *
     * @param e 非空时,表示这个数据对象，需要消费者来消费;
     *          为空时, 则表示当前操作是一个请求操作。
     * @param timed 决定是否存在timeout时间。
     * @param nanos 超时时长。
     * @return 如果返回非空, 代表数据已经被消费或者正常提供; 
     *         如果为空，则表示由于超时或中断导致失败。
     */
    abstract E transfer(E e, boolean timed, long nanos);
}
```

SynchronousQueue中的put/offer操作主要是生产数据，put操作主要是数据交给消费者，没有匹配的消费者则会调用LockSupport.park阻塞自己，直到有消费者线程唤醒且进行匹配，可以被中断，所以要判断是正常返回还是中断返回；而offer操作主要是尝试将数据交给消费者，如果有匹配的消费者则Transferer.transfer返回数据本身，否则直接返回null,offer根据返回的结果进行判断是是否成功，该方法不会阻塞自己。线程池中使用了offer操作，offer成功表示有消费者线程可以重复使用，否则新建一个线程来运行该任务，方法定义如下：
```java

    /**
     * 加一个元素到队列中，直到有消费者接收该元素
     * 1）如果没有匹配的线程，则会阻塞调用者线程；
     * 2）如果匹配成功，则直接返回
     * @param e 添加的元素
     * 
     * @throws InterruptedException 可以被中断
     * @throws NullPointerException 元素为null，则抛出空指针异常
     */
    public void put(E e) throws InterruptedException {
        if (e == null) throw new NullPointerException();
        if (transferer.transfer(e, false, 0) == null) {
            Thread.interrupted();
            throw new InterruptedException();
        }
    }

    /**
     * 尝试将元素（数据）交给匹配的线程
     * 1）如果有匹配的消费者线程，交付成功；
     * 2）如果匹配不成功，返回false，不会阻塞调用者线程。

     * @param e 添加的元素（数据）
     * @return 如果匹配成功（加入到队列）返回true，否则返回false.
     * @throws NullPointerException 元素为null，则抛出空指针异常
     */
    public boolean offer(E e) {
        if (e == null) throw new NullPointerException();
        return transferer.transfer(e, true, 0) != null;
    }

```

SynchronousQueue中的poll/take主要是消费数据，take操作是从队列中获取数据，调用该方法会被阻塞直到被向生产者线程唤醒，也可以调用interrupted()中断返回，返回之前需要判断是正常返回还是中断返回；不带参数的poll方法尝试获取数据，如果有数据则返回成功，否则返回失败，不会阻塞调用者线程；在带超时参数的poll方法中，如果没有数据，则会将调用线程睡眠指定时间。线程池中获取数据使用了带超时参数的poll操作，超时时间为60S，如果60S都没有数据，则唤醒该线程重新获取数据，如果仍然没有数据，则释放回收该线程。
```java

    /**
     * 获取数据，如果没有则进行等待
     * 可以调用中断唤醒线程
     *
     * @return 数据
     * @throws InterruptedException 中断异常
     */
    public E take() throws InterruptedException {
        E e = transferer.transfer(null, false, 0);
        if (e != null)
            return e;
        Thread.interrupted();
        throw new InterruptedException();
    }  

     /**
     * 尝试获取数据
     *
     * @return 成功返回队首数据，否则返回null
     */
    public E poll(long timeout, TimeUnit unit) {
        return transferer.transfer(null, true, 0);
    }  

    /**
     * 尝试获取数据，成功返回队首数据，否则睡眠指定时间，被唤醒之后重新获获取数据。
     * 可以被中断。
     * @return 成功返回队首数据，否则返回null（睡眠指定时间之后，仍然没有数据）
     * @throws InterruptedException 中断异常
     */
    public E poll(long timeout, TimeUnit unit) throws InterruptedException {
        E e = transferer.transfer(null, true, unit.toNanos(timeout));
        if (e != null || !Thread.interrupted())
            return e;
        throw new InterruptedException();
    }

```

SynchronousQueue有两个版本的Transferer实现，一种为公平模式，一种为非公平模式，公平模式的实现类为TransferQueue，它使用队列来作为存储结构，请求匹配的线程总是先尝试跟队列尾部的线程进行匹配，如果失败再将请求的线程添加到队列尾部，而非公平模式的实现类为TransferStack，它使用一个stack来作为存储结构，请求匹配的线程总是试图与栈顶线程进行匹配，失败则添加到栈顶。下面针对SynchronousQueue的两个版本进行分析。

## 2. 图解TransferStack

非公平模式底层的数据结构是TransferStack，它实际是一个LIFO的栈结构，用head指针指向栈顶，根据栈的LIFO特点，在非公平模式下，匹配操作总是与栈顶元素进行，即与最后一个入栈的元素而不是第一个元素，它的不公平性主要体现在这里。TransferStack及head定义如下：
```java
/** Dual stack */
static final class TransferStack<E> extends Transferer<E> {
    
    /** 结点的模式：REQUEST(请求)，DATA(数据)及FULFILLING(正在匹配)  **/ 
    static final int REQUEST    = 0;  // 请求数据(take/poll)
    static final int DATA       = 1;  // 生产数据(put/offer)
    static final int FULFILLING = 2;  // 匹配

    /** 结点 */
    static final class SNode {
        volatile SNode next;        // 指向栈中的下一个结点
        volatile SNode match;       // 与该结点匹配的结点
        volatile Thread waiter;     // 调用线程
        Object item;                // 数据，请求操作为null
        int mode;                   // 模式

        ... // 略
    }
	
	/** The head (top) of the stack */
    volatile SNode head; // 栈顶结点
}

```

现在以图形的方式来展示TransferStack的工作原理，SynchronousQueue为生产及消费数据提供了阻塞及不阻塞两种接口，两者都是阻塞方式是最复杂的一种情况，现在就以它为例。
```java
/** 生产数据 **/
public void put(E e) throws InterruptedException

/** 消费数据 **/
public E take() throws InterruptedException
```

在实例中SNode的内存布局如下所示:
![snode](/images/snode.jpg "snode")

操作序列如下：

**1、TransferStack初始状态**

![transferstack-null](/images/transferstack-null.jpg "transferstack-null")
栈顶元素head初始状态指向NULL。

**2、生产者线程t1执行 put(task1)操作**
TransferStack栈中没有元素，构造SNode结点SNode1，结点内容如下：
- mode : 1，表示为数据模式；
- item : task1，表示需要传递给消费者的数据；
- waiter : t1，表示生产者线程；
- match : null，表示没有匹配的结点；
- next : null，表示下一个结点。

将SNode1结点压入TransferStack栈中，调用LockSupport.park方法阻塞t1线程，等待消费者线程唤醒。
![transferstack-1](/images/transferstack-1.jpg "transferstack-1")

**3、生产者线程t2执行 put(task2)操作**

生产者线程t2执行的操作是生产数据，与TransferStack栈顶元素的mode是一致的，构造新的结点SNode2，并将该结点压入栈首，内容如下：
- mode : 1，表示为数据模式；
- item : task2，表示需要传递给消费者的数据；
- waiter : t2，表示生产者线程；
- match : null，表示没有匹配的结点；
- next : SNode1，表示下一个结点。

最后阻塞t2线程，等待消费者线程唤醒。

![transferstack-2](/images/transferstack-2.jpg "transferstack-2")

**4、消费者线程t3执行 take()操作**

消费者线程t3执行REQUEST操作，与TransferStack栈顶元素的mode是互补（FULFILLING）的，此时也会构造一个新结点SNode3，加入到栈中，内容如下：
- mode : 3，DATA与FULFILLING取或操作，即1 | 2 = 3, 表示正在进行匹配操作；
- item : null，请求（REQUEST）操作没有数据；
- waiter : t3，表示生产者线程；
- match : null，表示没有匹配的结点；
- next : SNode2，表示下一个结点。

SNode3压入栈顶之后，同时尝试修改与之匹配的SNode2结点，将SNode2中的match字段修改为SNode3，表示与之匹配的结点，此时栈的状态如下所示：

![transferstack-3](/images/transferstack-3.jpg "transferstack-3")

完成匹配操作之后，t3线程LockSupport.unpark方法唤醒t2线程，并将SNode3及SNode2弹出栈，其状态如下所示：

![transferstack-4](/images/transferstack-4.jpg "transferstack-4")

最后消费者t3线程拿到生产者线程生产的数据task2，生产者线程t2被唤醒继续执行后续流程。

**5、消费者线程t4执行 take()操作**

与第4步的操作类似，此时执行的互补（FULFILLING）操作，新构建一个结点SNode4，并压入栈中，其状态如下所示：
![transferstack-5](/images/transferstack-5.jpg "transferstack-5")

最后将两个结点弹出栈，此时栈中没有结点，回到初始状态，如第1步所示，同时t4线程拿到t1线程的数据task1。


## 3. 图解TransferQueue
公平模式底层的数据结构是TransferQueue，它是一个队列结构。head引用指向队列头结点，而tail指向尾结点。它的公平体现在匹配的操作是从队列的第一个元素开始进行的。下面是TransferQueue的定义。
```java
/** Dual Queue */
static final class TransferQueue<E> extends Transferer<E> {
   
    /** Node class for TransferQueue. */
    static final class QNode {
        volatile QNode next;          // 指向队列中的下一个结点
        volatile Object item;         // 存放数据，请求为null
        volatile Thread waiter;       // 被阻塞的线程
        final boolean isData;         // 是否数据

        ... // 略
    }
	
    /** Head of queue */
    transient volatile QNode head;  // 指向头结点
    /** Tail of queue */
    transient volatile QNode tail;  // 指向尾结点

    ... // 略
}
```
QNode的内存布局如下所示：
![qnode](/images/qnode.jpg "qnode")

以上章的操作顺序来请求数据。

**1、TransferQueue初始状态**

![transferqueue-null](/images/transferqueue-null.jpg "transferqueue-null")

构建一个Dummy Node压入队列，当head,tail指向同一个结点表示队列为空。

**2、生产者线程t1执行 put(task1)操作**
TransferQueue队列为空，构造QNode结点QNode1，结点内容如下：
- isData : true，表示为数据模式；
- item : task1，表示需要传递给消费者的数据；
- waiter : t1，表示生产者线程；
- next : null，表示下一结点为空。

将QNode1结点压入TransferQueue队尾，调用LockSupport.park方法阻塞t1线程，等待消费者线程唤醒。
![transferqueue-1](/images/transferqueue-1.jpg "transferqueue-1")

**3、生产者线程t2执行 put(task2)操作**

生产者线程t2执行的操作是生产数据，与TransferQueue队首元素的isData是一样的，表示模式是一致的，构造新的结点PNode2，并将该结点压入队尾，内容如下：
- isData : true，表示为数据模式；
- item : task2，表示需要传递给消费者的数据；
- waiter : t2，表示生产者线程；
- next : null，表示下一结点为空。

最后阻塞t2线程，等待消费者线程唤醒。

![transferqueue-2](/images/transferqueue-2.jpg "transferqueue-2")

**4、消费者线程t3执行 take()操作**

消费者线程t3执行REQUEST操作，跟TransferQueue队首元素的模式是互补（FULFILLING）的，此时与TransferStack的操作不一样，不用生成新结点压入队列。它执行了以下操作：1）将PNode1(队首)元素设置为参数e，在这里是null，完成数据的交接（如果是put操作的话，传递的就是真实的数据）；2）将head指针指向PNode1，PNode1作为新的Dummy Node（等于将PNode1移除队列）；3）唤醒PNode1对应的线程，即t1。

![transferqueue-3](/images/transferqueue-3.jpg "transferqueue-3")

最后t3从PNode1中拿出数据task1并返回，生产者线程t1被唤醒继续执行后续流程。

**5、消费者线程t4执行 take()操作**

与第4步的操作类似，此时执行的互补（FULFILLING）操作，队列状态如下所示：
![transferqueue-4](/images/transferqueue-4.jpg "transferqueue-4")

回到初始状态，如第1步所示，同时t4线程拿到t2线程的数据task2，t2线程被唤醒。

## 4. 代码分析
现在以TransferStack为例，分析SynchronousQueue的流程。
```java
/**
 * Puts or takes an item.
 * put和take方法都调用这个方法
 */
@SuppressWarnings("unchecked")
E transfer(E e, boolean timed, long nanos) {

    SNode s = null; // constructed/reused as needed
    // 判断请求的模型：e为null表示消费数据，不为空为消费数据
    int mode = (e == null) ? REQUEST : DATA;

    for (;;) {
        SNode h = head;
        // 1.  栈为空或请求与栈顶节点模式相同，根据情况入栈
        if (h == null || h.mode == mode) {  // empty or same-mode
            // 1.1 设置了超时且超时时间小于等于0，则直接返回不用等待
            if (timed && nanos <= 0) {      // can't wait
                if (h != null && h.isCancelled())
                    casHead(h, h.next);     // pop cancelled node
                else
                    return null;  // 如果栈为空，offer操作直接返回null
            // 1.2 没有设置超时或超时未到，则构建SNode，压入栈顶
            } else if (casHead(h, s = snode(s, e, h, mode))) {
                // 1.2.1 自旋等待或启用LockSupport.park阻塞调用线程
                SNode m = awaitFulfill(s, timed, nanos);

                // 1.2.2 被唤醒之后判断是否被取消
                if (m == s) {               // wait was cancelled
                    clean(s);
                    return null;
                }

                // 1.2.3 将栈顶元素出栈
                if ((h = head) != null && h.next == s)
                    casHead(h, s.next);     // help s's fulfiller
                
                // 1.2.4 返回结果
                return (E) ((mode == REQUEST) ? m.item : s.item);
            }
        // 2. 请求结点与栈顶结点是互补模式，则进行匹配操作
        } else if (!isFulfilling(h.mode)) { // try to fulfill
            // 2.1 如果栈顶结点已经被取消，则将栈顶结点出栈
            if (h.isCancelled())            // already cancelled
                casHead(h, h.next);         // pop and retry
            
            // 2.2 构建新结点，模式设置为FULFILLING，并压入栈顶
            else if (casHead(h, s=snode(s, e, h, FULFILLING|mode))) {
                for (;;) { // loop until matched or waiters disappear
                    SNode m = s.next;       // m is s's match
                    // 2.2.1 如果匹配的结点的为空，则将栈置空，然后重试
                    if (m == null) {        // all waiters are gone
                        casHead(s, null);   // pop fulfill node
                        s = null;           // use new node next time
                        break;              // restart main loop
                    }
                    SNode mn = m.next;
                    // 2.2.2 两个结点尝试匹配，如果匹配成功，
                    // 则唤醒被匹配结点对应的线程
                    if (m.tryMatch(s)) {

                        // 2.2.2.1 匹配成功之后，将栈顶两个节点出栈，并返回结果
                        casHead(s, mn);     // pop both s and m
                        return (E) ((mode == REQUEST) ? m.item : s.item);
                    } else                  // lost match
                        s.casNext(m, mn);   // help unlink
                }
            }
        // 3. 栈顶已经存在一个FULFILLING模式的结点，则帮助该结点完成匹配，
        //    然后自己再进行匹配
        } else {                            // help a fulfiller
            SNode m = h.next;               // m is h's match
            // 3.1 跟2.1一样
            if (m == null)                  // waiter is gone
                casHead(h, null);           // pop fulfilling node
            else {
                SNode mn = m.next;
                // 3.2 尝试将栈顶两个元素进行匹配，
                if (m.tryMatch(h))          // help match
                    casHead(h, mn);         // pop both h and m
                else                        // lost match
                    h.casNext(m, mn);       // help unlink
            }
        }
    }
}
```

代码主要分为三种情况：
1. 如果当前的栈是空的，或者包含与请求节点模式相同的节点，那么就将这个请求的节点作为新的栈顶节点，等待被下一个请求的节点匹配，最后会返回匹配节点的数据或者null，如果被取消则会返回null。

2. 如果当前栈不为空，并且请求的节点和当前栈顶节点模式互补，那么将这个请求的节点的模式变为FULFILLING，然后将其压入栈中，和互补的节点进行匹配，完成匹配之后将两个节点一起弹出，并且返回交易的数据。

3. 如果栈顶已经存在一个模式为FULFILLING的节点，说明栈顶的节点正在进行匹配，那么就帮助这个栈顶节点快速完成匹配，然后继续匹配。

主要方法说明：
1. casHead : 通过CAS操作将nh设置为新的栈顶结点；
```java
boolean casHead(SNode h, SNode nh) {
    return h == head &&
        UNSAFE.compareAndSwapObject(this, headOffset, h, nh);
}
```
2. awaitFulfill : 自旋或阻塞一个节点，直到找到一个匹配的结点；
```java
SNode awaitFulfill(SNode s, boolean timed, long nanos) {
     // 计算超时时间
    final long deadline = timed ? System.nanoTime() + nanos : 0L;
    Thread w = Thread.currentThread();
    int spins = (shouldSpin(s) ?
                 (timed ? maxTimedSpins : maxUntimedSpins) : 0);
    for (;;) {
        if (w.isInterrupted())
            s.tryCancel();
        SNode m = s.match;
        if (m != null)
            return m;
        if (timed) {
            nanos = deadline - System.nanoTime();
            if (nanos <= 0L) {
                s.tryCancel();
                continue;
            }
        }
        // 自旋
        if (spins > 0)
            // 如果是cpu是多核，则进行自旋
            spins = shouldSpin(s) ? (spins-1) : 0;
        else if (s.waiter == null)
            s.waiter = w; // establish waiter so can park next iter
        // 如果没有设置超时，则直接阻塞调用者线程
        else if (!timed)
            LockSupport.park(this);
        // 如果设置超时时间，则设置阻塞时间
        else if (nanos > spinForTimeoutThreshold)
            LockSupport.parkNanos(this, nanos);
    }
}
```

3. tryMatch : 尝试匹配结点，如果匹配成功则唤醒结点对应的线程
```java
boolean tryMatch(SNode s) {
    if (match == null &&
        UNSAFE.compareAndSwapObject(this, matchOffset, null, s)) {
        Thread w = waiter;
        if (w != null) {    // waiters need at most one unpark
            waiter = null;
            LockSupport.unpark(w);
        }
        return true;
    }
    return match == s;
}
```

## 5. 线程池应用
SynchronousQueue的一个使用场景是线程池，使用它的目的就是保证“对于提交的任务，如果有空闲线程，则使用空闲线程来处理；否则新建一个线程来处理任务”。
```java
public static ExecutorService newCachedThreadPool(ThreadFactory threadFactory) {

    // 核心线程数为0，空闲时间为60S，最大线程数为整数的最大值。
    return new ThreadPoolExecutor(0, Integer.MAX_VALUE,
                                  60L, TimeUnit.SECONDS,
                                  new SynchronousQueue<Runnable>(),
                                  threadFactory);
}
```

首先看下线程池的任务提交流程：
```java
public void execute(Runnable command) {
    if (command == null)
        throw new NullPointerException();
    
    int c = ctl.get();

    // 1. 第1步
    if (workerCountOf(c) < corePoolSize) {
        if (addWorker(command, true))
            return;
        c = ctl.get();
    }
    // 2. 第2步
    if (isRunning(c) && workQueue.offer(command)) {
        int recheck = ctl.get();
        if (! isRunning(recheck) && remove(command))
            reject(command);
        else if (workerCountOf(recheck) == 0)
            addWorker(null, false);
    }
    // 3. 第3步
    else if (!addWorker(command, false))
        reject(command);
}
```
提交任务有在三个步骤：
1. 如果当前工作线程数小于“核心线程数”，则创建一个工作线程来执行task，在这里，由于“核心线程数”等于0，会跳过这个步骤，执行第2步；
2. 将任务加入到工作队列（SynchronousQueue）中，如果添加成功表示将任务交付给工作线程了，如果没有成功则执行第3步；
3. 如果加入到工作队列失败，会尝试创建一个工作线程来执行任务，如果工作线程数小于最大线程数（Integer.MAX_VALUE）,正常情况下，工作线程会创建成功，如果创建失败则会执行“拒绝策略”。

结合SynchronousQueue，我们来分析下线程池的执行流程：
1. 由于“核心线程数”等于0，会跳过第1个步骤；
2. 在第2步中，提交任务采用的是offer操作，在上面的内容我们提到，offer尝试将数据（任务）交给匹配的线程：
- 如果有匹配的工作者线程，交付成功；
- 如果匹配不成功，返回false，不会阻塞调用者线程；
在这里分为两种情况，1）刚开始，没有工作线程，SynchronousQueue队列为空，offer操作失败，继续执行第3步；2）执行一段时间后，SynchronousQueue中有工作线程，数据交付成功，直接返回；
3. 交付失败后，会尝试新建一个工作线程来执行任务，由于最大线程数设置为Integer.MAX_VALUE，线程都会创建成功，而不会被拒绝。在这里，线程数没有做限制，存在线程创建过多导致内存溢出的风险。

分析了提交任务（offer）,再来看获取任务的流程，获取任务的流程在工作线程的执行代码中，工作线程一直会从SynchronousQueue中获取任务，如果空闲时间超过60S则会回收该工作线程。我们来看下工作线程中获取任务的代码：
```java
private Runnable getTask() {
    boolean timedOut = false; // Did the last poll() time out?

    for (;;) {
        int c = ctl.get();
        int rs = runStateOf(c);

        // Check if queue empty only if necessary.
        if (rs >= SHUTDOWN && (rs >= STOP || workQueue.isEmpty())) {
            decrementWorkerCount();
            return null;
        }

        int wc = workerCountOf(c);

        // Are workers subject to culling?
        boolean timed = allowCoreThreadTimeOut || wc > corePoolSize;

        if ((wc > maximumPoolSize || (timed && timedOut))
            && (wc > 1 || workQueue.isEmpty())) {
            if (compareAndDecrementWorkerCount(c))
                return null;
            continue;
        }

        try {
            Runnable r = timed ?
                workQueue.poll(keepAliveTime, TimeUnit.NANOSECONDS) :
                workQueue.take();
            if (r != null)
                return r;
            timedOut = true;
        } catch (InterruptedException retry) {
            timedOut = false;
        }
    }
}
```

获取任务的关键代码主要是这行语句：
```java
workQueue.poll(keepAliveTime, TimeUnit.NANOSECONDS)
```
这行语句有如下功能：获取任务，如果没有匹配的操作，则会阻塞60S，这里的60S就是线程空闲时间；如果有匹配的操作，则直接获取交付的数据。在这里，如果是超时返回的话，该工作线程会退出，且工作线程的数量会减1。

通过上面的分析，我们可以看出，提交任务使用不阻塞的offer方法，获取任务使用带超时的阻塞方法poll。不管offer成功与否，总能保证有工作线程去马上去执行任务，如果没有可复用的工作线程，则会创建一个新的工作线程来执行，另外SynchronousQueue只会阻塞工作线程，即队列中只会有工作线程，不会有提交任务的线程。


## 6. 总结
这篇文章分析了SynchronousQueue的底层数据结构及在线程池中的运用，并对相关代码进行了分析，希望能够对想了解SynchronousQueue的同学有所帮助。

**参考：**

----
[1]:https://www.jianshu.com/p/376d368cb44f
[2]:http://cmsblogs.com/?p=2418

[1. Java阻塞队列SynchronousQueue详解][1]

[2. 【死磕Java并发】—–J.U.C之阻塞队列：SynchronousQueue][2]


