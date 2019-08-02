---
title: Java ReentrantLock实现原理
date: 2019-07-29 16:32:27
tags:
- reentrantLock
- pthread_mutex
- pthread_cond
- futex
categories:
- 并发编程
---

在Java中要实现资源的互斥访问及线程间的同步，一般有两种方式，一种是通过synchronized（同步块或同步方法）结合Oject.wait()及Object.signal()来实现，另外一种是通过ReentrantLock和Condition来实现。为了解决不同条件下的并发问题，Java引入了一些高级锁和同步机制，如Semaphore,ReentrantReadWriteLock,CountDownLatch和CyclicBarrier等等。

在项目开发中，用ReentrantLock相对较多，但对其的理解程序仅限于Java语言层面，对于JVM及操作系统的底层实现并没有了解，没有一个全局的概念，相关知识点存在断层，如ReentrantLock在JVM和操作系统中到底对应什么实体？等待队列存储在什么地方？线程的等待及唤醒对应什么样的操作？JVM及操作系统在ReentrantLock中提供了什么样的功能？正好在学习操作系统的知识，把这些知识重新梳理下，打通认知上的盲点。

## 1. 整体结构
![reentrantlock](/images/reentrantlock.jpg "reentrantlock")
1. 在java层，维护了锁的state状态及等待队列（包括条件队列），对JVM的依赖只是线程的阻塞和唤醒。给state赋予不同的含义及控制获取锁的方式，java在语言层面实现丰富的锁结构。
2. 在JVM层，线程的阻塞和唤醒是通过互斥（pthread_mutex_t）和条件变量(pthread_cond_t)来实现的。_counter用来表示一个许可，通过_counter的值来判断是否在该条件变量上进行等待和唤醒，_counter默认值是0，表示许可未被使用，调用park之后，线程将被阻塞；执行unpark之后，_counter赋值为1，将会唤醒被等待的线程，唤醒的操作是将等待的线程从条件变量（cond）的等待队列移到互斥（mutex）的等待队列上，互斥（mutex）释放之后才将该线程进行调度。
3. futex由一个用户空间int类型的地址uaddr及相关联的等待队列组成，uaddr由mutex或cond中定义。在内核中维护一个哈希表的数据结构，以uaddr为key,通过hash操作，添加到对应的列表中，从而可以快速搜索到uaddr对应的等待线程。

## 2. ReentrantLock
在java中有一个非常重要的并发数据结构AbstractQueuedSynchronizer(AQS),它主要的功能有三个：1）维护状态值（state）;2）线程同步队列的管理；3）抽象封装流程。AQS对锁的实现进行了高度抽象，提供了一套模板方法，对申请锁和释放锁的流程进行了封装，将差异的部分由子类来实现，如state字段含义的解析，同时子类通过扩展tryAcquire,tryRelease,tryAcquireShared,tryReleaseSharede及isHeldExclusivelys方法来实现不同的锁。

### 2.1 state状态
ReentrantLock中有两个实现，分别是公平锁和不公平锁（NonfairSync和FairSync），它们都是继承自AQS，差别主要在于tryAcquire的实现，后面会进到，不过对于state的定义是一致的。在Reentrant中，state有如下的含义:
- 0:表示锁未被占用，可以获取锁，获取锁之后变为1；
- 大于0:表示锁被占用，其它线程获取锁会被阻塞，拥有锁的线程可以重复获取锁（可重入的概念），重复获取锁要对state加1。

### 2.2 等待队列
除了状态的管理，ReetrantLock还会维护一个同步队列，线程获取ReentrantLock锁失败后，会将该线程加入到队列的尾部，同时调用LockSupport.park方法让线程阻塞，等待队列是一个双向队列，其结点如下图所示：
![aqs-node](/images/aqs-node.jpg "aqs-node")
- prev:指向前一个结点；
- next:指向后一个结点；
- nextWaiter:1）用在条件队列（在条件变量上挂起的线程列表）中，指向条件队列的下一个结点；2）用来表示锁的模式，是排他还是共享模式；
- thread:对应的线程；
- waitStatus:结点的等待状态，它有五个状态：1)SIGNAL;2)CANCELLED;3)CONDITION(用于条件变量中);4)PROPAGATE;5)0(初始状态)。

一个包含两个结点的等待队列如下所示：
![sync-queue](/images/sync-queue.jpg "sync-queue")
- 在队列中有一个空的head结点，这样可以简化插入到队首的操作；
- SINGAL状态表示其后续结点需要unpark操作。

### 2.3 条件队列
ReentrantLock可以单独使用，也可以配合条件变量一起使用，使用方式如下所示:
```java
// 变量申明
private ReentrantLock lock;
private Condition full;
private Condition empty;

...
// 初始化
lock = new ReentrantLock();
full = lock.newCondition();
empty = lock.newCondition();

...
// 使用方式
try {
    lock.lock();
    while (index >= DATA_SIZE) {
        empty.await();
    }

    int value = random.nextInt();
    data[index] = value;
    ++index;

    full.signalAll();
} catch (Exception ex) {
    ex.printStackTrace();
} finally {
    ++loop;
    lock.unlock();
}

```

条件变量(Codition)通常需要与Lock配合使用，为什么需要配合使用，后面章节会有描述。每一个条件变量都会维护一个条件队列，通过await方法之后，会释放lock锁，同时将当前线程加入到条件队列中，最后阻塞当前线程。signal/signalAll则会将条件队列中一个或所有线程移到Lock对应的等待队列中，并等待唤醒。拥有两个结点的条件队列如下所示：
![con-queue](/images/con-queue.jpg "con-queue")

### 2.4 tryAcquire
在AQS中定义了一套获取锁的模板方法，如下所示：
```java
public final void acquire(int arg) {
    if (!tryAcquire(arg) &&
        acquireQueued(addWaiter(Node.EXCLUSIVE), arg))
        selfInterrupt();
}
```
流程如下：
- 尝试获取锁，失败之后将线程加入到队列；
- 加入队列失败，则执行中断。

在ReentrantLock中有两中实现，分别是公平锁和不公平锁，差别在于tryAcquire的实现，不公平锁的tryAcquire如下所示：
ReentrantLock#NonfairSync.tryAcquire.nonfairTryAcquire:
```java
final boolean nonfairTryAcquire(int acquires) {
    final Thread current = Thread.currentThread();
    int c = getState();
    if (c == 0) {
        if (compareAndSetState(0, acquires)) { // #1
            setExclusiveOwnerThread(current);
            return true;
        }
    }
    else if (current == getExclusiveOwnerThread()) {
        int nextc = c + acquires; // #2
        if (nextc < 0) // overflow
            throw new Error("Maximum lock count exceeded");
        setState(nextc);
        return true;
    }
    return false;
}
```

ReentrantLock#FairSync.tryAcquire
```java
protected final boolean tryAcquire(int acquires) {
    final Thread current = Thread.currentThread();
    int c = getState();
    if (c == 0) {
        if (!hasQueuedPredecessors() && // #3
            compareAndSetState(0, acquires)) {
            etExclusiveOwnerThread(current);
            return true;
        }
    }
    else if (current == getExclusiveOwnerThread()) {
        int nextc = c + acquires; // #4
        if (nextc < 0)
            throw new Error("Maximum lock count exceeded");
            setState(nextc);
            return true;
    }
    return false;
}
```
**公平性**

公平锁与不公平锁的区别主要体现在代码#1和#3处，重要的区别在于获取锁时是否允许抢占，在公平锁中（#3）要判断队列中是否有结点，如果有则插入到队尾进行排队；不公平锁（#1）先尝试获取锁，获取失败再进行排队。

**可重入性**

可重入性体现在代码#2和#4处，如果当前线程等于持有锁的线程，则允许获取锁，state字段加1。

### 2.5 LockSupport
如果获取锁失败，会调用LockSupport.park方法阻塞当前线程。
```java
private final boolean parkAndCheckInterrupt() {
    LockSupport.park(this);
    return Thread.interrupted();
}
```
LockSupport代码如下所示，它最终会调用UNSAFE.park方法，该方法是一个本地方法，由JVM虚拟机来实现。

LockSupport.java
```java
public static void park(Object blocker) {
    Thread t = Thread.currentThread();
    setBlocker(t, blocker);
    UNSAFE.park(false, 0L);
    setBlocker(t, null);
}
```
在ReentrantLock中，线程的唤醒同样依赖于LockSupport中的方法，最终也是调用UNSAFE的本地方法。在UNSAFE中提供给LockSupport使用的就是如下两个方法：
```java
public native void unpark(Thread jthread);
public native void park(boolean isAbsolute, long time);
```

仅仅两个简单的接口，就为上层提供了强大的同步原语。

## 3. JVM同步原语
在HotSpot虚拟机(Oracle JDK和Openjdk)中，park和unpark方法由底层的Parker类来实现，虚拟机中每一个线程都会关联一个Park对象，现在先来来分析下虚拟机中线程、java线程及操作线程的关系。

### 3.1 Thread
HotSpot里的Thread类对应着一个OS的Thread, JavaThread类继承自Thread, JavaThread实例持有Java层的Thread实例，所以, 在Java层的Thread, 在操作系统上对应一个thread, linux上就是一个轻量级task。
```cpp
// thread.hpp
class Thread: public ThreadShadow {
    friend class VMStructs;

    // OS data associated with the thread
    protected:
        OSThread* _osthread;  // Platform-specific thread information

    public:
        ParkEvent * _ParkEvent ;        // for synchronized()
        ParkEvent * _SleepEvent ;       // for Thread.sleep

    // JSR166 per-thread parker
    private:
        Parker*    _parker;

    ...
    // 略
}

class JavaThread: public Thread {
    friend class VMStructs;
    
    private:
        JavaThread*    _next;          // The next thread in the Threads list
        oop            _threadObj;     // The Java level thread object
    
    ...
    // 略
}
```

[源代码:thread.hpp](http://hg.openjdk.java.net/jdk8/jdk8/hotspot/file/87ee5ee27509/src/share/vm/runtime/thread.hpp)

线程的创建是通过线程库pthread_create来实现的。
```cpp
// thread.cpp
os::create_thread(this, thr_type, stack_sz);
// linux_os.cpp
pthread_t tid;
int ret = pthread_create(&tid, &attr, (void* (*)(void*)) thread_native_entry, thread);
```
另外，Thread类里有两个ParkEvent和一个Parker, 其中_ParkEvent实现synchronized同步功能, _SleepEvent是用来实现Thread.sleep/wait，而parker则是用来实现的park/unpark(阻塞/唤醒)。

### 3.2 Parker

