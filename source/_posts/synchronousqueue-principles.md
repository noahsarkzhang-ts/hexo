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

## 5. 线程池应用

## 6. 总结

**参考：**

----
[1]:https://www.jianshu.com/p/376d368cb44f
[2]:https://blog.csdn.net/boling_cavalry/article/details/77793224
[3]:https://tech.meituan.com/2018/11/15/java-lock.html
[4]:https://blog.csdn.net/iter_zc/article/details/41847887

[1. Java阻塞队列SynchronousQueue详解][1]

[2. Java的wait()、notify()学习三部曲之一：JVM源码分析][2]

[3. 不可不说的Java“锁”事][3]

[4. 聊聊JVM（六）理解JVM的safepoint][4]
