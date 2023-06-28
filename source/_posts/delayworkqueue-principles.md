---
title: DelayedWorkQueue 原理
date: 2019-09-10 09:50:24
updated: 2019-09-10 09:50:24
tags:
- DelayedWorkQueue
- ScheduledThreadPoolExecutor
- ScheduledFutureTask
- DelayedQueue
- 周期性任务
categories:
- Java基础
---

在Java中，ScheduledThreadPoolExecutor主要作用是执行延时及周期性任务，这篇文章主要分析以下几个问题：1）任务是如何存储的？2）延时及周期性任务什么时候执行及如何执行？3）任务怎么进行取消？带着这些问题我们继续往下看。

<!-- more -->

## 1. 概述

![ScheduledThreadPoolExecutor](/images/scheduled-thread-pool-executor.jpg "ScheduledThreadPoolExecutor")

从上图可以看到ScheduledThreadPoolExecutor,DelayedWorkQueue及ScheduledFutureTask三者之间的关系，在ScheduledThreadPoolExecutor中使用的队列是DelayedWorkQueue，用于存储执行的任务；提交到DelayedWorkQueue中的是ScheduledFutureTask类型的任务，通过ScheduledFutureTask的引用可以获取结果或者取消任务，下面对这三个类做一个简要描述：
- DelayedWorkQueue : 底层的存储结构是一个小堆，它根据延时的时间进行排序，堆顶的元素永远是最小的；加入一个元素时，首先被加到队列的最后一个元素中，然后使用siftUp操作，跟它的父结点进行比较，如果比父结点小，则交换位置，递归执行这样的操作，直到比父结点元素都大；取出元素永远是取出堆顶元素，然后将队列中的最后一个元素移动到堆顶，执行siftDown操作，跟左右子结点中的最小元素进行比较，如果比子结点大， 则交换位置，递归执行这样的操作，直到比子结点小为止。
- ScheduledFutureTask : 提交到DalayWorkQueue队列中的元素是ScheduledFutureTask类型，它继承了Runnable接口，包含了任务的执行逻辑，同时它也继承了Future接口，具备了取消任务、同步获取返回结果的功能。在ScheduledFutureTask中有几个重要的参数：state(状态), callable(有返回值的runnable对象), outcome(返回结果), runner(执行线程), waiters(等待队列), state表示任务执行的状态，如果任务在未完成之前执行get操作（获取返回结果），那么调用线程会被阻塞，该线程会加入到waiters队列中，等待runner线程执行set操作（设置返回结果）之后被唤醒。如果ScheduledFutureTask执行了取消操作之后，它会被移除DelayedWorkQueue队列，state设置为取消状态，任务将不再被执行，如果任务已经执行，将会向其发送interrupt操作。
- ScheduledThreadPoolExecutor : ScheduledThreadPoolExecutor扩展了ThreadPoolExecutor类，在ThreadPoolExecutor的基础上，可以执行延时任务和周期性任务，借助DelayedWorkQueue类，实现了任务的延时执行，对于周期性任务，在上一个周期执行结束之后，会重新计算下一个周期的延时时间，将任务重新加入到DelayedWorkQueue队列中，等待下次任务的调度。

## 2. DelayedWorkQueue
![DelayedWorkQueue](/images/DelayedWorkQueue.jpg "DelayedWorkQueue")
DelayedWorkQueue类图如上所示，DelayedWorkQueue是BlockingQueue的子类。

DelayedWorkQueue跟DelayQueue、PriorityQueue一样是基于堆的数据结构，它与ScheduledFutureTask配合使用。在ScheduledFutureTask中记录了在堆中的索引，可以快速定位所在的位置，方便进行task的取消操作，同时ScheduledFutureTask必须实现Comparable和Delayed接口，Comparable接口用于比较两个任务的延时的大小，Delayed返回任务的延时，即还需多久执行任务。

DelayedWorkQueue队列中元素的增加或删除，都会改变堆的结构，在DelayedWorkQueue中，提供了两种调整堆的操作：siftUp和siftDown，后面的章节会详细介绍。

在分析DelayedWorkQueue之前，先了解下堆这种数据结构：
> 堆（英语：Heap）是计算机科学中的一种特别的树状数据结构。若是满足以下特性，即可称为堆：“给定堆中任意节点P和C，若P是C的父母节点，那么P的值会小于等于（或大于等于）C的值”。若父母节点的值恒小于等于子节点的值，此堆称为最小堆（min heap）；反之，若父母节点的值恒大于等于子节点的值，此堆称为最大堆（max heap）。在堆中最顶端的那一个节点，称作根节点（root node），根节点本身没有父母节点（parent node）

一个小堆的结构如下所示：
![min-heap](/images/min-heap.jpg "min-heap")

在小堆中，parent结点小于等于子结点，而对两个左右子结点大小没有要求，一个堆实际上是一颗完全二叉树，一般用数组来表示。在DelayedWorkQueue中使用的是小堆，来保证返回的是延时最小的任务。

### 2.1 siftUp操作
在一个小堆中的添加一个结点的过程如下：1）将结点添加到堆中的最后一个元素；2）跟parent结点进行比较，如果比parent结点小，则交换结点，直到没有parent结点为止，如下图所示：
![sift-up](/images/sift-up.jpg "sift-up")
接入一个新的最小值9，会比较三次，直到堆顶。该算法的时间复杂度为O(log(n))，n为结点个数。

### 2.2 siftDown操作
从堆顶取走最小的结点之后，会将堆中最后一个结点移动堆顶，执行siftDown过程，parent结点会跟子结点中的最小值进行比较，如果大于子结点，需要跟子结点进行交换，调整后的结构仍然是小堆，如下图所示：
![sift-down](/images/sift-down.jpg "sift-down")
该算法的时间复杂度也是O(log(n))，n为结点个数。

### 2.3 数据结构
```java
static class DelayedWorkQueue extends AbstractQueue<Runnable>
    implements BlockingQueue<Runnable> {

    // 堆的初始容量为16
    private static final int INITIAL_CAPACITY = 16;

    // 存储堆中的结点，用数组来表示堆
    private RunnableScheduledFuture<?>[] queue =
        new RunnableScheduledFuture<?>[INITIAL_CAPACITY];

    // 用于互斥访问    
    private final ReentrantLock lock = new ReentrantLock();
    private int size = 0;

    // 当前在等待堆顶结点的线程，使用了leader-follower的线程模式
    private Thread leader = null;

    // 条件变量，堆中没有结点时，阻塞线程；堆中有新的堆顶结点时，唤醒线程
    private final Condition available = lock.newCondition();
    
    ... // 略
}
```

说明：
- 初始容量：DelayedWorkQueue的容量无限的队列，其初始容量为16，随着结点数的增加，会进行自动扩容；
- 底层数据：存储结构为数组；
- leader-follow线程模式：堆顶结点会只分配一个leader线程去消费，其它线程会等待leader线程唤醒才能消费下一个结点；如果堆顶结点还需要延时delayed（ns）才能消费，那么leader需要阻塞delayed（ns）；
- 条件变量：堆中没有结点时，阻塞线程；堆中有新的堆顶结点时，唤醒线程。

### 2.4 offer操作
在DelayedWorkQueue中，添加结点可以调使用put/add/offer方法，前两个方法最终都是调用offer方法，那么我们重点来分析下offer方法。
```java
public boolean offer(Runnable x) {
    if (x == null)
        throw new NullPointerException();

    // 传入的任务是RunnableScheduledFuture的子类
    RunnableScheduledFuture<?> e = (RunnableScheduledFuture<?>)x;

    // 获取锁，互斥访问
    final ReentrantLock lock = this.lock;
    lock.lock();
    try {

        // 1.如果结点数大于等于队列长度，则需要扩容
        int i = size;
        if (i >= queue.length)
            grow();
        size = i + 1;

        // 2. 如果结点数为0，则直接赋值给第一个元素即可；
        if (i == 0) {
            queue[0] = e;
            // 2.1 将数组元素下标传递给RunnableScheduledFuture对象，以便该对象检索其在数组中的位置；
            setIndex(e, 0);
        } else {
            // 3. 如果结点数大于0，则将结点插入到堆中的最后一个结点，并执行siftUp操作
            siftUp(i, e);
        }
        // 4. 如果插入的结点是新的堆顶元素，说明有延时更短的任务加入到队列中，
        // 则将leader置空，并唤醒一个线程来消费新的堆顶。
        if (queue[0] == e) {
            leader = null;
            available.signal();
        }
    } finally {
        lock.unlock();
    }
    return true;
}
```
该方法主要包含4个步骤：
- 如果结点数大于队列长度，则执行扩容；
- 如果当前结点数为0，则直接将新插入的结点赋值给数组的第一个元素；
- 如果当前结点为大于0，则将结点插入到堆中的最后一个结点，并执行siftUp操作；
- 如果插入的结点是新的堆顶元素，说明有延时更短的任务加入到队列中，则将leader置空，并唤醒一个线程来消费新的堆顶。

```java
private void grow() {
    int oldCapacity = queue.length;
    // 容量扩大50%
    int newCapacity = oldCapacity + (oldCapacity >> 1); // grow 50%
    if (newCapacity < 0) // overflow
        newCapacity = Integer.MAX_VALUE;
    queue = Arrays.copyOf(queue, newCapacity);
}

```
扩容操作主要是新建一个数组，其容量是旧数组的1.5倍，并将老数组的元素拷贝到新数组中。

```java
private void siftUp(int k, RunnableScheduledFuture<?> key) {
    while (k > 0) {
        // 计算parent结点的下标
        int parent = (k - 1) >>> 1;
        RunnableScheduledFuture<?> e = queue[parent];
        // 如果插入的结点大于parent结点则退出
        if (key.compareTo(e) >= 0)
            break;
        queue[k] = e;
        setIndex(e, k);
        k = parent;
    }
    queue[k] = key;
    setIndex(key, k);
}
```
插入结点的类型实现了Comparable接口，结点之间的比较使用compareTo方法，该方法我们在后面的内容讲述，详细的siftUp操作可以参考2.1节。

### 2.5 take操作
获取堆顶结点以take方法为例。
```java
public RunnableScheduledFuture<?> take() throws InterruptedException {
    // 获取锁，互斥访问
    final ReentrantLock lock = this.lock;
    lock.lockInterruptibly();
    try {
        for (;;) {
            // 1. 获取堆顶结点，即最小值。
            RunnableScheduledFuture<?> first = queue[0];

            // 2. 如果堆顶为空，说明队列中没有结点，则直接阻塞调用线程。
            if (first == null)
                available.await();
            else {

                // 3. 计算堆顶结点的延时，如果已经过期，则直接返回堆顶结点，并执行siftDown操作
                long delay = first.getDelay(NANOSECONDS);
                if (delay <= 0)
                    return finishPoll(first);
                first = null; // don't retain ref while waiting

                // 4. 如果堆顶结点还未到期，则阻塞调用线程，这里分两种情况：
                // 1) 如果leader不为空，说明已经有线程在等待该结点，则直接阻塞调用线程；
                // 2) 如果leader为空，说明该结点还没有分配leader结点，则设置当前线程为leader线程，
                // 同时将阻塞时间设置为结点延时的时间。
                if (leader != null)
                    available.await();
                else {
                    Thread thisThread = Thread.currentThread();
                    leader = thisThread;
                    try {
                        available.awaitNanos(delay);
                    } finally {
                        if (leader == thisThread)
                            leader = null;
                    }
                }
            }
        }
    } finally {
        // 5. 唤醒follower线程，消费新的堆顶结点。
        if (leader == null && queue[0] != null)
            available.signal();
        lock.unlock();
    }
}

```
该方法主要包含5个步骤：
- 获取堆顶结点，即最小值；
- 如果堆顶为空，说明队列中没有结点，则直接阻塞调用线程，等待被唤醒；
- 如果堆顶不为空， 计算堆顶结点的延时，如果已经过期，则直接返回堆顶结点，并执行siftDown操作；
- 如果堆顶结点还未到期，则阻塞调用线程，这里分两种情况：1) 如果leader不为空，说明已经有线程在等待该结点，则直接阻塞调用线程；2) 如果leader为空，说明该结点还没有分配leader结点，则设置当前线程为leader线程，同时将阻塞时间设置为结点延时的时间。
- 最后leader线程唤醒follower线程，消费新的堆顶结点。

```java
private RunnableScheduledFuture<?> finishPoll(RunnableScheduledFuture<?> f) {
    // 队列长度减1；
    int s = --size;
    
    // 取出队列中最后一个元素
    RunnableScheduledFuture<?> x = queue[s];
    queue[s] = null;

    // 执行siftDown操作
    if (s != 0)
        siftDown(0, x);
    setIndex(f, -1);
    return f;
}
```
finishPoll方法有两个作用：1）压缩队列，队列数减1；2）执行siftDown操作。我们接着看siftDown操作。

```java
private void siftDown(int k, RunnableScheduledFuture<?> key) {
    int half = size >>> 1;
    while (k < half) {
        // 1. 计算左子结点；
        int child = (k << 1) + 1;
        RunnableScheduledFuture<?> c = queue[child];
        int right = child + 1;
        // 2. 判断左右子结点的最小值，并赋值给变量c;
        if (right < size && c.compareTo(queue[right]) > 0)
            c = queue[child = right];
        // 3. 子结点中最小值与key进行比较，如果子结点大于key，则直接退出；
        if (key.compareTo(c) <= 0)
            break;
        // 4. 如果子结点小于key，则将子结点赋值给parent结点；
        queue[k] = c;
        setIndex(c, k);
        k = child;
    }
    // 5. 将key赋值给最终的结点；
    queue[k] = key;
    // 6. 将key在队列中的下标传递给key。
    setIndex(key, k);
}
```
siftDown的具体操作参考2.2节。

### 2.6 小结
DelayedWorkQueue底层使用了堆的数据结构来存储延时/周期性的任务，在队列中结点按照延时时间进行排序，从队列中取出的结点都是到期的结点。另外要求结点必须实现Comparable及Delayed接口，结点通过Comparable.compareTo方法比较大小，通过Delayed.getDelay方法获取结点的延时，作为判断是否过期的依据。

## 3. ScheduledFutureTask
![ScheduledFutureTask](/images/ScheduledFutureTask.jpg "ScheduledFutureTask")
ScheduledFutureTask类的继承关系比较复杂，现在对它进行一个梳理。
- Comparable : 实现任务按照延时进行比较；
- Delayed : 获取任务所剩延时；
- Runnable ：封装任务的业务逻辑；
- Future : 实现任务的取消及同步获取返回结果。

下面将对这些功能做详细描述。

### 3.1 数据结构
```java
private class ScheduledFutureTask<V>
        extends FutureTask<V> implements RunnableScheduledFuture<V> {

    // 序号
    private final long sequenceNumber;

    // 任务执行的时间，单位为ns
    private long time;

    // 任务执行的周期，单位为ns,
    // 如果是正数，表示固定频率执行，如果是负数，表示固定延时执行，
    // 如果是0，则表示非同期性任务
    private final long period;

    RunnableScheduledFuture<V> outerTask = this;

    // 该任务在堆中的下标，用于快速取消任务
    int heapIndex;
	
    // in FutureTask
    
    // 任务的运行时状态
    // NEW : 任务的初始状态；
    // COMPLETING : 临时状态，表示任务run方法已经执行结束，但未设置返回结果；
    // NORMAL : 正常结束状态，已经设置返回结果；
    // EXCEPTIONAL : 执行有异常；
    // CANCELLED : 任务已经被取消；
    // INTERRUPTING : 临时状态，表示正在执行中断操作；
    // INTERRUPTED : 执行了中断操作。
    private volatile int state;
	
    // 封装了runnable及结果对象，真正的业务逻辑在这里
    private Callable<V> callable;
    
    // 结果对象
    private Object outcome; // non-volatile, protected by state reads/writes
    
    // 正在执行任务的线程
    private volatile Thread runner;
    
    // 线程等待队列（在等待返回结果）
    private volatile WaitNode waiters;

    // in FutureTask
    
    ... // 略
}
```
ScheduledFutureTask的属性分为两类，一是与调度时间相关的，二是与Future相关的，下面对这两类属性进行讨论。

1）调度时间相关
- sequenceNumber : 第一个任务都会分配一个唯一的自增序列号；
- time : 表示任务执行的时间点，单位为ns(纳秒)；
- period : 任务执行的周期，如果是正数，表示固定频率执行，如果是负数，表示固定延时执行， 如果是0，则表示非同期性任务，单位为ns(纳秒)；
- heapIndex ： 任务在堆中的下标，用于快速取消任务。

2）Future相关
- state ：任务的运行时状态，状态值有：NEW, COMPLETING, NORMAL, EXCEPTIONAL, CANCELLED, INTERRUPTING和INTERRUPTED，含义如下：
NEW : 任务的初始状态；
COMPLETING : 临时状态，表示任务run方法已经执行结束，但未设置返回结果；
NORMAL : 正常结束状态，已经设置返回结果；
EXCEPTIONAL : 执行有异常；
CANCELLED : 任务已经被取消；
INTERRUPTING : 临时状态，表示正在执行中断操作；
INTERRUPTED : 执行了中断操作。
状态值的转换有下面几种情况：
NEW -> COMPLETING -> NORMAL
NEW -> COMPLETING -> EXCEPTIONAL
NEW -> CANCELLED
NEW -> INTERRUPTING -> INTERRUPTED
- callable : 封装了runnable及结果对象，真正的业务逻辑在这里；
- outcome ： 结果对象；
- runner : 正在执行任务的线程；
- waiters : 线程等待队列（在等待返回结果）。

### 3.2 compareTo方法
```java
public int compareTo(Delayed other) {
    if (other == this) // compare zero if same object
        return 0;
    if (other instanceof ScheduledFutureTask) {
        ScheduledFutureTask<?> x = (ScheduledFutureTask<?>)other;
        long diff = time - x.time;
        if (diff < 0)
            return -1;
        else if (diff > 0)
            return 1;
        else if (sequenceNumber < x.sequenceNumber)
            return -1;
        else
            return 1;
    }
    long diff = getDelay(NANOSECONDS) - other.getDelay(NANOSECONDS);
    return (diff < 0) ? -1 : (diff > 0) ? 1 : 0;
}
```
compareTo方法比较简单，主要是比较两个任务执行时间的大小，如果当前结点小于比较的结点，则返回-1；如果大于比较的结点，则返回1；如果时间相等，再比较序号，序号大的返回1，序号小的返回-1；如果比较的是同一个元素，则返回0；

### 3.3 getDelay方法
```java
public long getDelay(TimeUnit unit) {
    return unit.convert(time - now(), NANOSECONDS);
}
```
getDelay方法返回当前的延时，当前延时主要是任务的执行时间点与当前时间的差值。

### 3.4 FutureTask
FutureTask可以实现三个功能：1）同步转异步，将任务交给线程池处理；2）同步/异步获取返回结果；3）取消任务。第一个功能很简单，就是封装业务逻辑，交给线程池处理，下面重点分析后两个功能。

#### 3.4.1 获取返回结果
获取返回结果用的是get方法，get有两个重载方法，一个不带参数，表示任务没有完成，则阻塞线程，直到任务完成被唤醒或线程被中断；一个带时间参数，表示任务没有完成，则睡眠指定时间，直到任务完成被唤醒或超时或线程被中断。现在以不带参数的get方法为例。
```java
public V get() throws InterruptedException, ExecutionException {
    int s = state;
    // state(状态)小于COMPLETING(正在完成)，则需要阻塞线程
    if (s <= COMPLETING)
        s = awaitDone(false, 0L);
    // 到这里说明任务已经完成，任务完成有多种情况需要在这个里
    // 判断：1）正常结束；2）取消；3）异常退出。
    return report(s);
}
```

get方法主要是根据任务的运行状态(state)来判断任务是否完成，处于NEW,COMPLETING两种状态，说明任务未完成或即将完成，这时候调用awaitDone方法，可能会阻塞线程；如果大于COMPLETING，说明任务已经完成，还需要判断完成的类型：1）正常结束；2）取消；3）异常退出，这些逻辑在report方法中处理。

```java
/**
 * 等待任务完成或中断或超时
 *
 * @param timed 是否设置超时
 * @param nanos 超时时间
 * @return state 完成状态
 */
private int awaitDone(boolean timed, long nanos)
    throws InterruptedException {
    final long deadline = timed ? System.nanoTime() + nanos : 0L;
    WaitNode q = null;
    boolean queued = false;
    for (;;) {

        // 1. 线程中断，则抛出InterruptedException，退出方法；
        if (Thread.interrupted()) {
            // 将线程从等待队列中移出；
            removeWaiter(q);
            throw new InterruptedException();
        }

        // 2. 状态大于COMPLETING，说明任务完成，退出方法；
        int s = state;
        if (s > COMPLETING) {
            if (q != null)
                q.thread = null;
            return s;
        }
        // 3. 状态等于COMPLETING，说明任务即将完成，则线程让出cpu，重新调度，
        // 目的是让当前线程等一小段时间；
        else if (s == COMPLETING) // cannot time out yet
            Thread.yield();
        // 4. 状态等于NEW且q等于null，说明任务未完成，则新建等待结点。
        else if (q == null)
            q = new WaitNode();
        // 5. 将当前线程压入等待队列的队首；
        else if (!queued)
            queued = UNSAFE.compareAndSwapObject(this, waitersOffset,
                                                 q.next = waiters, q);
        // 6. 如果设置超时，则睡眠指定时间
        else if (timed) {
            nanos = deadline - System.nanoTime();
            if (nanos <= 0L) {
                removeWaiter(q);
                return state;
            }
            LockSupport.parkNanos(this, nanos);
        }
        // 7. 未指定时间，则直接睡眠
        else
            LockSupport.park(this);
    }
}
```
awaitDone方法包含一个死循环，有三种情况退出该方法：1) 线程被中断；2）线程被唤醒，且任务已经完成，正常退出；3）超时退出。它包含以下的处理逻辑：
- 线程被中断，则抛出InterruptedException，退出方法；
- 线程状态大于COMPLETING，说明任务完成，退出方法；
- 状态等于COMPLETING，说明任务即将完成，则线程让出cpu，重新调度；
- 状态等于NEW且q等于null，说明任务未完成，则新建等待结点，并将该结点等待队列的队首；
- 如果设置超时，则睡眠指定的时间，否则直接睡眠，等待被唤醒。

分析了get方法，我们再来分析下set方法。
```java
protected void set(V v) {
    // 通过CAS设置状态为COMPLETING
    if (UNSAFE.compareAndSwapInt(this, stateOffset, NEW, COMPLETING)) {

        // 设置结果
        outcome = v;

        // 设置状态为NORMAL
        UNSAFE.putOrderedInt(this, stateOffset, NORMAL); // final state

        // 唤醒等待队列中的线程
        finishCompletion();
    }
}
```
set方法流程比较清晰，包含下面这些流程：
- 通过CAS设置状态(state)为COMPLETING；
- 设置返回结果；
- 设置状态(state)为NORMAL，可见COMPLETING是一个很短暂的状态，与NORMAL状态中间只有一个设置返回结果的操作；
- 唤醒等待队列中的线程。

```java
private void finishCompletion() {

    // 遍历等待队列，依次唤醒等待的线程
    for (WaitNode q; (q = waiters) != null;) {
        if (UNSAFE.compareAndSwapObject(this, waitersOffset, q, null)) {
            for (;;) {
                Thread t = q.thread;
                if (t != null) {
                    q.thread = null;
                    // 唤醒等待的线程
                    LockSupport.unpark(t);
                }
                WaitNode next = q.next;
                if (next == null)
                    break;
                q.next = null; // unlink to help gc
                q = next;
            }
            break;
        }
    }

    done();

    callable = null;        // to reduce footprint
}
```

finishCompletion方法逻辑比较简单，就是遍历等待队列，依次唤醒等待的线程。

通过上面的分析可以知道，get方法获取返回结果，如果任务未完成则阻塞调用线程；set方法设置返回结果，更新任务状态，唤醒被阻塞的线程。

#### 3.4.2 取消任务
在FutureTask中可以通过cancel方法取消一个任务，代码如下所示：

```java
public boolean cancel(boolean mayInterruptIfRunning) {
    if (!(state == NEW &&
          UNSAFE.compareAndSwapInt(this, stateOffset, NEW,
              mayInterruptIfRunning ? INTERRUPTING : CANCELLED)))
        return false;
    try {    // in case call to interrupt throws exception
        if (mayInterruptIfRunning) {
            try {
                Thread t = runner;
                if (t != null)
                    t.interrupt();
            } finally { // final state
                UNSAFE.putOrderedInt(this, stateOffset, INTERRUPTED);
            }
        }
    } finally {
        finishCompletion();
    }
    return true;

}
```
取消一个任务实际上就是一个操作：设置state(状态)为CANCELLED或INTERRUPTED。方法参数mayInterruptIfRunning为ture的情况下，状态设置为INTERRUPTED。从上面的代码可以看到INTERRUPTING是个临时状态，介于new和INTERRUPTED之间，和INTERRUPTED状态只相隔一个线程中断操作。

### 3.5 任务的执行
ScheduledFutureTask实现了Runnabler接口，实现了对周期性任务的支持。

```java
public void run() {
    // 1. 判断是否为周期性任务
    boolean periodic = isPeriodic();
    // 2. 判断是否需要取消任务
    if (!canRunInCurrentRunState(periodic))
        cancel(false);
    // 3. 执行非周期性任务
    else if (!periodic)
        ScheduledFutureTask.super.run();
    // 4. 执行周期性任务
    else if (ScheduledFutureTask.super.runAndReset()) {
        // 5. 设置下一次任务执行的时间
        setNextRunTime();
        // 6. 重新调度任务
        reExecutePeriodic(outerTask);
    }
}
```
ScheduledFutureTask执行逻辑包含以下几个步骤：
- 判断是否为周期性任务；
- 判断该任务是否应该取消，取消的情况包括：1）线程池是否关闭；2）线程池关闭的情况下，任务是否继续执行的策略；
- 如果是非周期性任务，调用FutureTask的run方法；
- 如果是周期性任务，调用FutureTask的runAndReset方法，调用成功之后设置下一次任务执行的时间，并将任务重新添加到DelayedWorkQueue中。

```java
public boolean isPeriodic() {
    return period != 0;
}
```
在ScheduledFutureTask中，用period属性来判断是否是周期性任务，period取值包括三种情况：1）正数，表示固定频率执行；2）负数，表示固定延时执行；3）0，表示非同期性任务，单位为ns(纳秒)。在非0的情况下，period存储了周期性任务之间的间隔时间。

接下来我们看下非周期性任务执行的逻辑，即FutureTask的run方法。
```java
public void run() {
    // 判断任务的状态是否为NEW，且设置runner为当前线程
    if (state != NEW ||
        !UNSAFE.compareAndSwapObject(this, runnerOffset,
                                     null, Thread.currentThread()))
        return;
    try {
        // 执行逻辑封装在Callable对象中
        Callable<V> c = callable;
        if (c != null && state == NEW) {
            V result;
            boolean ran;
            try {
                // 调用业务逻辑
                result = c.call();
                ran = true;
            } catch (Throwable ex) {
                result = null;
                ran = false;
                setException(ex);
            }
            // 设置返回结果
            if (ran)
                set(result);
        }
    } finally {
        // 清空runner
        runner = null;
        int s = state;
        // 判断是否有中断操作
        if (s >= INTERRUPTING)
            handlePossibleCancellationInterrupt(s);
    }
}
```
非周期性任务执行的主要逻辑如下：
- 判断当前任务的状态是为NEW，且设置任务的runner为当前线程；
- 调用Callable接口，执行真正的业务逻辑；
- 调用set操作，设置返回结果，唤醒被阻塞的线程；

下面看周期性任务的的runAndReset方法：
```java
protected boolean runAndReset() {
    if (state != NEW ||
        !UNSAFE.compareAndSwapObject(this, runnerOffset,
                                     null, Thread.currentThread()))
        return false;
    boolean ran = false;
    int s = state;
    try {
        Callable<V> c = callable;
        if (c != null && s == NEW) {
            try {
                // 执行业务逻辑
                c.call(); // don't set result
                ran = true;
            } catch (Throwable ex) {
                setException(ex);
            }
        }
    } finally {
        runner = null;
        s = state;
        if (s >= INTERRUPTING)
            handlePossibleCancellationInterrupt(s);
    }
    // state不改变
    return ran && s == NEW;
}
```
相对于非周期性任务，runAndReset有以下不同：
- 周期性任务没有返回值；
- 周期性任务不更新state(状态)，它的状态永远是NEW，以便下一次调用。

我们知道周期性任务有两种类型，一种是固定频率，另外一种是固定延时，这两种任务的不同体现在什么地方，我们接着看setNextRunTime方法。
```java
private void setNextRunTime() {
    long p = period;
    if (p > 0)
        time += p;
    else
        time = triggerTime(-p);
}

long triggerTime(long delay) {
    return now() +
        ((delay < (Long.MAX_VALUE >> 1)) ? delay : overflowFree(delay));
}
```
从上面可以看出二者的区别，下一次任务的执行时间，计算公式如下：
- 固定频率 ：上一次任务的执行时间点 + 延时，在这种情况下，如果执行时间大于延时(delay)的话，会出现两个任务的重叠，如果已经错过了下一次任务的执行时间点，提交到DelayedWorkQueue中的任务会马上执行；
- 固定延时 ：上一次任务执行后的时间（当前时间） + 延时，这种情况下，前后两个任务不会重叠。

往下看reExecutePeriodic方法：
```java
RunnableScheduledFuture<V> outerTask = this;

reExecutePeriodic(outerTask);

void reExecutePeriodic(RunnableScheduledFuture<?> task) {
    if (canRunInCurrentRunState(true)) {
        // 将当前任务加入到DelayedWorkQueue中
        super.getQueue().add(task);
        if (!canRunInCurrentRunState(true) && remove(task))
            task.cancel(false);
        else
            // 确保线程池有线程执行
            ensurePrestart();
    }
}
```
reExecutePeriodic方法有两个功能：1）将当前任务加入到DelayedWorkQueue中；2）确保线程池有线程执行。

### 3.6 小结
ScheduledFutureTask是一个比较重要的类，它包括了这些功能：1）延时任务的比较逻辑；2）执行结果的获取及任务的取消；3）对业务逻辑进行封装执行；4）对周期性任务的支持。我们讲了任务的存储及执行，那么任务的调度是在什么地方呢？接下来讲任务的任务的调度ScheduledThreadPoolExecutor类。

## 4. ScheduledThreadPoolExecutor
![ScheduledThreadPoolExecutor](/images/ScheduledThreadPoolExecutor.jpg "ScheduledThreadPoolExecutor")
从继承关系中可以看出，ScheduledThreadPoolExecutor继承了ThreadPoolExecutor类，说明支持普通任务（非周期性任务）的调度，同时实现了ScheduledExecutorService接口，加入了对周期性任务调度的支持。

### 4.1 非周期性任务的调度
非周期性任务的调度主要是使用execute/submit方法，在ScheduledThreadPoolExecutor中重写了这两个方法，统一使用schedule方法，如下所示：
```java
public void execute(Runnable command) {
    schedule(command, 0, NANOSECONDS);
}

public Future<?> submit(Runnable task) {
    return schedule(task, 0, NANOSECONDS);
}
```
非周期性任务一般是一次性任务，提交之后马上执行，所以延时(delay)设置为0，下面分析schedule方法。
```java
public ScheduledFuture<?> schedule(Runnable command,
                                   long delay,
                                   TimeUnit unit) {
    if (command == null || unit == null)
        throw new NullPointerException();
    // 构建ScheduledFutureTask对象
    RunnableScheduledFuture<?> t = decorateTask(command,
        new ScheduledFutureTask<Void>(command, null,
                                      triggerTime(delay, unit)));
    // 调度执行任务
    delayedExecute(t);
    return t;
}
```
schedule方法主要包含两个步骤：
- 构建ScheduledFutureTask对象，传入的参数包括Runnable对象，返回结果对象及下一次业务执行的时间，前两个参数为会封装到callable属性中，下一次业务执行时间赋值给time属性，执行时间是一个相对于1970-01-01 00:00:00 UTC的差值(ns);
- 调度执行任务；

接着看delayedExecute方法：
```java
private void delayedExecute(RunnableScheduledFuture<?> task) {
    // 如果线程池关闭，则拒绝任务
    if (isShutdown())
        reject(task);
    else {
        // 将任务加入到DelayedWorkQueue中
        super.getQueue().add(task);
        if (isShutdown() &&
            !canRunInCurrentRunState(task.isPeriodic()) &&
            remove(task))
            task.cancel(false);
        else
            // 确保有线程去执行任务
            ensurePrestart();
    }
}
```
可以看到，delayedExecute方法有两个主要的功能：1）将任务加入到DelayedWorkQueue中；2）确保有线程去执行任务。加入队列可以参考上面的内容，接下来我们看怎么确保有线程去执行任务。
```java
void ensurePrestart() {
    int wc = workerCountOf(ctl.get());
    if (wc < corePoolSize)
        addWorker(null, true);
    else if (wc == 0)
        addWorker(null, false);
}
```
ensurePrestart逻辑就是如果线程池线程数小于核心线程数则添加一个线程，另外，如果线程数为0也会添加一个线程，保证线程池中至少有一个线程去执行。

### 4.2 周期性任务的调度
1）固定频率的周期性任务
```java
public ScheduledFuture<?> scheduleAtFixedRate(Runnable command,
                                              long initialDelay,
                                              long period,
                                              TimeUnit unit) {
    if (command == null || unit == null)
        throw new NullPointerException();
    if (period <= 0)
        throw new IllegalArgumentException();
    ScheduledFutureTask<Void> sft =
        new ScheduledFutureTask<Void>(command,
                                      null,
                                      triggerTime(initialDelay, unit),
                                      unit.toNanos(period)); 
    RunnableScheduledFuture<Void> t = decorateTask(command, sft);
    sft.outerTask = t;
    delayedExecute(t);
    return t;
}
```

2）固定延时的周期性任务
```java
public ScheduledFuture<?> scheduleWithFixedDelay(Runnable command,
                                                 long initialDelay,
                                                 long delay,
                                                 TimeUnit unit) {
    if (command == null || unit == null)
        throw new NullPointerException();
    if (delay <= 0)
        throw new IllegalArgumentException();
    ScheduledFutureTask<Void> sft =
        new ScheduledFutureTask<Void>(command,
                                      null,
                                      triggerTime(initialDelay, unit),
                                      unit.toNanos(-delay));
    RunnableScheduledFuture<Void> t = decorateTask(command, sft);
    sft.outerTask = t;
    delayedExecute(t);
    return t;
}
```
这两种类型之间的区别仅仅是设置period的不同，固定频率是正数period，固定延时是-delay。

### 4.3 线程池的创建
ScheduledThreadPoolExecutor的创建通过Executors.newScheduledThreadPool方法，可以指定一个核心线程数或ThreadFactory类。

## 5. 总结
通过对DelayedWorkQueue,ScheduledFutureTask和ScheduledThreadPoolExecutor，我们回答了文章开关提到的三个问题：

1）任务是如何存储的？

任务是存储在DelayedWorkQueue中，底层是一个小堆的数据结构。

2）延时及周期性任务什么时候执行及如何执行？

延时及周期性任务根据执行时间点进行排序，时间最小的优先执行，对于周期性任务而言，在上一个任务执行结束之后，会重新计算下一个任务的时间点，把任务重新加入到等待队列中等待调度。线程池线程从等待队列中获取堆顶的任务执行，如果任务未到期，线程需要睡眠指定的时长，这个时长等于任务到期的时长。

3）任务怎么进行取消？

任务取消实际上是将任务的状态更改为CANCELLED或INTERRUPTED，在线程开始执行任务的时候，判断是否取消，如果取消的话则放弃执行。

