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

**说明：** 条件队列是指阻塞在条件变量上线程等待队列，这里为了与Lock变量上等待队列区分，所以叫做条件队列。

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

// 第一个参数代表第二个参数是否是绝对时间，第二个参数代表最长阻塞时间
public native void park(boolean isAbsolute, long time); 
```

仅仅两个简单的接口，就为上层提供了强大的同步原语。

## 3. JVM同步原语
在HotSpot虚拟机(Oracle JDK和Openjdk)中，park和unpark方法由底层的Parker类来实现，虚拟机中每一个线程都会关联一个Park对象，在这里三个层面的线程，分别是java线程、jvm线程和操作系统线程，先分析下它们之间的关系。

### 3.1 Thread
HotSpot虚拟机里的Thread类对应着一个OS的Thread, JavaThread类继承自Thread, JavaThread实例持有Java层的Thread实例。所以, 在Java层的Thread, 在操作系统上对应一个thread, linux上就是一个轻量级task。
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

线程的创建是最后是通过线程库pthread_create来实现的。
```cpp
// thread.cpp
os::create_thread(this, thr_type, stack_sz);
// linux_os.cpp
pthread_t tid;
int ret = pthread_create(&tid, &attr, (void* (*)(void*)) thread_native_entry, thread);
```

另外，Thread类里有两个ParkEvent和一个Parker, 其中_ParkEvent实现synchronized同步功能, _SleepEvent是用来实现Thread.sleep/wait，而parker则是用来实现的park/unpark(阻塞/唤醒)。

**注意：** synchronized的重量级锁和ReentrantLock底层都是基于互斥和条件变量来实现的，从这个角度来看的话，这两者在性能上差别不大。

### 3.2 Parker
Parker对象是实现线程阻塞/唤醒的关键，现在分析下它的结构。

```cpp
// park.hpp
class Parker : public os::PlatformParker {
    private:
        volatile int _counter ;
         Parker * FreeNext ;
        JavaThread * AssociatedWith ; // Current association

    public:
        Parker() : PlatformParker() {
            _counter       = 0 ;    // 初始化为0
            FreeNext       = NULL ;
            AssociatedWith = NULL ;
    }

    ...
    // 略
}

// os_linux.cpp 
class PlatformParker : public CHeapObj<mtInternal> {
    protected:
        enum {
            REL_INDEX = 0,
            ABS_INDEX = 1
        };

    int _cur_index;  // which cond is in use: -1, 0, 1
    pthread_mutex_t _mutex [1] ;

    // 一个是给park用, 另一个是给parkUntil用
    pthread_cond_t  _cond  [2] ; // one for relative times and one for abs.
    
    ...
    // 略
}
```

在Parker对象中有三个比较重要的变量:
- _counter:用来表示获取凭证；
- _mutex,_cond:互斥、条件变量，实现阻塞及唤醒的关键就在这里。

### 3.3 阻塞/唤醒
LockSuport.park/unpark调用UNSAFE.park/unpark，而UNSAFE再调用Parker的park及unpark方法，下面将分析Parker对象中的park/unpark流程。

#### 3.3.1 Parker::park
```cpp
// os_linux.cpp
void Parker::park(bool isAbsolute, jlong time) {

    // 如果_counter大于0，表示凭证有效(park之前执行了unpark操作)，则直接返回。
    if (Atomic::xchg(0, &_counter) > 0) return;

    Thread* thread = Thread::current();
    assert(thread->is_Java_thread(), "Must be JavaThread");
    JavaThread *jt = (JavaThread *)thread;

    // 如果当前线程有中断信息，则直接返回
    if (Thread::is_interrupted(thread, false)) {
        return;
    }

    // Next, demultiplex/decode time arguments
    timespec absTime;
    if (time < 0 || (isAbsolute && time == 0) ) { // don't wait at all
        return;
    }
    if (time > 0) {
        unpackTime(&absTime, isAbsolute, time);
    }

    ... 

    // Don't wait if cannot get lock since interference arises from
    // unblocking.  Also. check interrupt before trying wait
    // 中断或获取锁失败则返回
    if (Thread::is_interrupted(thread, false) || pthread_mutex_trylock(_mutex) != 0) {
        return;
    }

    int status ;
    f (_counter > 0)  { // no wait needed
        _counter = 0;
        status = pthread_mutex_unlock(_mutex);
        assert (status == 0, "invariant") ;
        // Paranoia to ensure our locked and lock-free paths interact
        // correctly with each other and Java-level accesses.
        OrderAccess::fence();
        return;
    }

    assert(_cur_index == -1, "invariant");
     // 传入的time参数为0，走这个分支。
     if (time == 0) {
        _cur_index = REL_INDEX; // arbitrary choice when not timed
        status = pthread_cond_wait (&_cond[_cur_index], _mutex) ;  // 调用条件变量，进行阻塞
    } else {
        _cur_index = isAbsolute ? ABS_INDEX : REL_INDEX;
        status = os::Linux::safe_cond_timedwait (&_cond[_cur_index], _mutex, &absTime) ;
        if (status != 0 && WorkAroundNPTLTimedWaitHang) {
            pthread_cond_destroy (&_cond[_cur_index]) ;
            pthread_cond_init    (&_cond[_cur_index], isAbsolute ? NULL : os::Linux::condAttr());
        }
    }

    _cur_index = -1;
    assert_status(status == 0 || status == EINTR ||
                status == ETIME || status == ETIMEDOUT,
                status, "cond_timedwait");

    // 线程被唤醒，_counter设置为0，并释放锁。
    _counter = 0 ;
    status = pthread_mutex_unlock(_mutex) ;

  ...
  // 略
}

```
主要流程：
1. 首先对_counter进行CAS原子操作，将_counter设置为0，并判断旧值是否大于0，若大于0表示凭证有效，直接返回；
2. _counter等于0，则尝试获取锁（pthread_mutex_trylock），有中断或获取锁失败直接返回；
3. 获取锁成功之后，尝试对_counter进行一次判断，如果在这期间，_counter被修改了（大于0），则将_counter设置为0，释放锁，并返回；
4. 如果_counter未被修改，则调用pthread_cond_wait，阻塞该线程；
5. 线程被唤醒，_counter设置为0，并释放锁。

**注意：** 在pthread_cond_wait中传入mutex，是为了保证_counter状态的变更和执行条件变量的操作是一个原子操作，避免在对条件变量进行操作的时候，_counter发生了变更。

#### 3.3.2 Parker::unpark

```cpp
// os_linux.cpp
void Parker::unpark() {
    int s, status ;
    status = pthread_mutex_lock(_mutex);
    assert (status == 0, "invariant") ;
     s = _counter;
     _counter = 1;

    if (s < 1) {
    // thread might be parked
    if (_cur_index != -1) {
      // thread is definitely parked
      if (WorkAroundNPTLTimedWaitHang) {
        status = pthread_cond_signal (&_cond[_cur_index]);
        assert (status == 0, "invariant");
        status = pthread_mutex_unlock(_mutex);
        assert (status == 0, "invariant");
      } else {
        status = pthread_mutex_unlock(_mutex);
        assert (status == 0, "invariant");
        status = pthread_cond_signal (&_cond[_cur_index]);
        assert (status == 0, "invariant");
      }
    } else {
      pthread_mutex_unlock(_mutex);
      assert (status == 0, "invariant") ;
    }
  } else {
    pthread_mutex_unlock(_mutex);
    assert (status == 0, "invariant") ;
  }
}
```
**主要流程：**
1. 获取锁；
2. 将_counter值修改为1；
3. 对_counter的旧值进行判断，如果小于1，则表示有线程阻塞在条件变量，执行pthread_cond_signal唤醒操作。
4. 释放锁。

Parker::unpark操作相对比较简单，1）修改_counter赋值为1；2）唤醒进程。同时也可以看到，_counter执行的赋值操作，执行一次unpark和执行多次unpark效果一样。


**源代码：**

[thread.hpp](http://hg.openjdk.java.net/jdk8/jdk8/hotspot/file/87ee5ee27509/src/share/vm/runtime/thread.hpp)
[thread.cpp](http://hg.openjdk.java.net/jdk8/jdk8/hotspot/file/87ee5ee27509/src/share/vm/runtime/thread.cpp)
[linux_os.cpp](http://hg.openjdk.java.net/jdk8/jdk8/hotspot/file/87ee5ee27509/src/os/linux/vm/os_linux.cpp)

### 3.4. mutex/cond
通过上面的分析，LockSupport.park最终调用的是pthread_cond_wait，LockSupport.unpark调用的是pthread_cond_signal，阻塞/唤醒操作是通过条件变量来实现的，另外，这两个方法调用需要互斥（mutex）来协助（pthread_mutex_lock,pthread_mutex_unlock和pthread_mutex_trylock），现在我们进一步分析mutex和cond的实现。

#### 3.4.1 pthread_mutex_t
**1. pthread_mutex_t结构**
```cpp
typedef union
{
    struct __pthread_mutex_s
    {
        int __lock;
        unsigned int __count;
        int __owner;
#if __WORDSIZE == 64
        unsigned int __nusers;
#endif
        /* KIND must stay at this position in the structure to maintain
           binary compatibility.  */
        int __kind;
#if __WORDSIZE == 64
        int __spins;
        __pthread_list_t __list;
# define __PTHREAD_MUTEX_HAVE_PREV  1
#else
        unsigned int __nusers;
        __extension__ union
        {
            int __spins;
            __pthread_slist_t __list;
        };
#endif
    } __data;
    char __size[__SIZEOF_PTHREAD_MUTEX_T];
    long int __align;
} pthread_mutex_t;
```
**主要变量：**
- __lock:锁状态；
- __owner:锁的拥有者。

初始化时这些值都为0。
```cpp
# define PTHREAD_MUTEX_INITIALIZER \
  { { 0, 0, 0, 0, 0, __PTHREAD_SPINS, { 0, 0 } } }
```

**2. pthread_mutex_lock**

省掉了部分流程，只保留了主要流程：
```cpp

#ifndef __pthread_mutex_lock
strong_alias (__pthread_mutex_lock, pthread_mutex_lock)
hidden_def (__pthread_mutex_lock)
#endif

// pthread_mutex_lock是__pthread_mutex_lock的别名

int
__pthread_mutex_lock (pthread_mutex_t *mutex)
{
    assert (sizeof (mutex->__size) >= sizeof (mutex->__data));
 
    unsigned int type = PTHREAD_MUTEX_TYPE_ELISION (mutex);
 
    LIBC_PROBE (mutex_entry, 1, mutex);
 
    if (__builtin_expect (type & ~(PTHREAD_MUTEX_KIND_MASK_NP
                 | PTHREAD_MUTEX_ELISION_FLAGS_NP), 0))
        return __pthread_mutex_lock_full (mutex);
 
    if (__glibc_likely (type == PTHREAD_MUTEX_TIMED_NP))
    {
        FORCE_ELISION (mutex, goto elision);
        simple:
        /* Normal mutex.  */
        LLL_MUTEX_LOCK (mutex);
        assert (mutex->__data.__owner == 0);
    }
    elseif (...) {
      ...
    }
 
    pid_t id = THREAD_GETMEM (THREAD_SELF, tid);
 
    /* Record the ownership.  */
    mutex->__data.__owner = id;
    #ifndef NO_INCR
    ++mutex->__data.__nusers;
    #endif
 
    LIBC_PROBE (mutex_acquired, 1, mutex);
 
    return 0;
}
```

**主要流程：**
- 判断锁的类型，普通锁会走LLL_MUTEX_LOCK (mutex)分支；
- 获取锁之后会将当前线程线程设置成为锁的拥有者，同时自增mutex变量__nusers的值，表示锁使用人数加1。

```cpp
# define LLL_MUTEX_LOCK(mutex) \
    lll_lock ((mutex) ->__data.__lock, PTHREAD_MUTEX_PSHARED (mutex))

// 将_data中的__lock作为参数填入lll_lock
```

对mutex的操作主要是对mutex.\_\_data.\_\_lock的操作。

```cpp
#define lll_lock(futex, private)    \
    __lll_lock (&(futex), private)

#define __lll_lock(futex, private)                                      \
  ((void)                                                               \
   ({                                                                   \
     int *__futex = (futex);                                            \
     if (__glibc_unlikely                                               \
         (atomic_compare_and_exchange_bool_acq (__futex, 1, 0)))        \
       {                                                                \
         if (__builtin_constant_p (private) && (private) == LLL_PRIVATE) \
           __lll_lock_wait_private (__futex);                           \
         else                                                           \
           __lll_lock_wait (__futex, private);                          \
       }                                                                \
   }))
```
**主要流程：**
- 对\_\_futex进行CAS操作，如果旧值为0，则将\_\_futex修改为1，tomic_compare_and_exchange_bool_acq就是完成这个功能。
- 如果修改成功获取锁返回，且\_\_futex值为1；
- 如果修改失败，说明\_\_futex不为0，说明其它线程获取到锁，则执行下面的分支。

tomic_compare_and_exchange_bool_acq的定义如下：如果oldval等于\*mem，那么设置\*mem=newval，并且返回0； 如果\*mem的值没有改变，那么就返回非0。 直白一点就是\*mem等于oldval就返回0，不等于就返回非0。

```cpp
/* Atomically store NEWVAL in *MEM if *MEM is equal to OLDVAL.
   Return zero if *MEM was changed or non-zero if no exchange happened. */
#ifndef atomic_compare_and_exchange_bool_acq
#ifdef __arch_compare_and_exchange_bool_32_acq
#define atomic_compare_and_exchange_bool_acq(mem, newval, oldval) \
  __atomic_bool_bysize (__arch_compare_and_exchange_bool,acq, \
                mem, newval, oldval)
#else
#define atomic_compare_and_exchange_bool_acq(mem, newval, oldval) \
  ({ /* Cannot use __oldval here, because macros later in this file might \
    call this macro with __oldval argument. */ \
     __typeof (oldval) __atg3_old = (oldval); \
     atomic_compare_and_exchange_val_acq (mem, newval, __atg3_old) \
       != __atg3_old; \
  })
#endif
#endif
```

```cpp 
/* This function doesn't get included in libc.  */

#if IS_IN (libpthread)
void
__lll_lock_wait (int *futex, int private)
{
  if (*futex == 2)
    lll_futex_wait (futex, 2, private); /* Wait if *futex == 2.  */
 
  while (atomic_exchange_acq (futex, 2) != 0)
    lll_futex_wait (futex, 2, private); /* Wait if *futex == 2.  */
}
#endif
```
阻塞的关键操作就在这里：
- 如果futex为2，则调用lll_futex_wait进行阻塞；
- 如果futex不为2，则将futex修改为2，一般是从1修改为2，再调用lll_futex_wait阻塞线程。
- 这里有两种情况：1）当前锁被占用，futex为1，但没有线程被阻塞，这是需要将futex修改为2；2）如果已经有线程被阻塞，说明futex为2，则直接阻塞当前线程。

```cpp
/* Wait while *FUTEXP == VAL for an lll_futex_wake call on FUTEXP.  */
#define lll_futex_wait(futexp, val, private) \
lll_futex_timed_wait (futexp, val, NULL, private)


#define lll_futex_timed_wait(futexp, val, timeout, private)     \
    lll_futex_syscall (4, futexp,                                 \
            __lll_private_flag (FUTEX_WAIT, private),  \
            val, timeout)
```

lll_futex_wait的操作最终会调用FUTEX_WAIT，在FUTEX_WAIT中，会传入整数的地址futexp，还有当前值val，如果在系统调用期间val改变了则直接返回，保证了数据的原子性。在lll_futex_timed_wait调用中，futexp表示mutex.\_\_data.\_\_lock，而val为2。

**3. pthread_mutex_unlock**

```cpp
int
__pthread_mutex_unlock (pthread_mutex_t *mutex)
{
    return __pthread_mutex_unlock_usercnt (mutex, 1);
}

int
internal_function attribute_hidden
__pthread_mutex_unlock_usercnt (pthread_mutex_t *mutex, int decr)
{
    int type = PTHREAD_MUTEX_TYPE_ELISION (mutex);
    if (__builtin_expect (type &
		~(PTHREAD_MUTEX_KIND_MASK_NP|PTHREAD_MUTEX_ELISION_FLAGS_NP), 0))
        return __pthread_mutex_unlock_full (mutex, decr);
 
    if (__builtin_expect (type, PTHREAD_MUTEX_TIMED_NP)
        == PTHREAD_MUTEX_TIMED_NP)
    {
    /* Always reset the owner field.  */
    normal:
        mutex->__data.__owner = 0;
        if (decr)
	    /* One less user.  */
	    --mutex->__data.__nusers;
 
         /* Unlock.  */
        lll_unlock (mutex->__data.__lock, PTHREAD_MUTEX_PSHARED (mutex));
 
        LIBC_PROBE (mutex_release, 1, mutex);
 
        return 0;
    }
    else if (__glibc_likely (type == PTHREAD_MUTEX_TIMED_ELISION_NP))
    {
        // ...
    }
    else if (__builtin_expect (PTHREAD_MUTEX_TYPE (mutex)
			      == PTHREAD_MUTEX_RECURSIVE_NP, 1))
        // ...
    else if (__builtin_expect (PTHREAD_MUTEX_TYPE (mutex)
			      == PTHREAD_MUTEX_ADAPTIVE_NP, 1))
        // ...
    }
}
```
释放锁的主要操作是：1）线程的拥有者清0；2）线程的使用人数减一；2）lll_unlock唤醒线程。

```cpp
#define __lll_unlock(futex, private)                    \
  ((void)                                               \
   ({                                                   \
     int *__futex = (futex);                            \
     int __private = (private);                         \
     int __oldval = atomic_exchange_rel (__futex, 0);   \
     if (__glibc_unlikely (__oldval > 1))               \
       lll_futex_wake (__futex, 1, __private);          \
   }))
#define lll_unlock(futex, private)	\
  __lll_unlock (&(futex), private)


#define lll_futex_wake(futexp, nr, private)                             \
  lll_futex_syscall (4, futexp,                                         \
		     __lll_private_flag (FUTEX_WAKE, private), nr, 0)
```
**主要流程：**
- 将futex（mutex.\_\_data.\_\_lock）设置为0并拿到设置之前的值（用户态操作）；
- 如果futex之前的值大于1，说明有线程阻塞在mutex上，则调用lll_futex_wake唤醒一个线程；

lll_futex_wake调用内核FUTEX_WAKE来唤醒线程。

**总结：**
- mutex锁有三种状态（mutex.\_\_data.\_\_lock的值），0：锁未被占用；1：锁被占用；2：有一个或多个线程阻塞；
- 在内核中通过mutex.\_\_data.\_\_lock地址来确定一个mutex；

#### 3.4.2 pthread_cond_t
1. pthread_cond_t定义
```cpp
/* Data structure for conditional variable handling.  Thestructure of
   the attribute type is not exposed on purpose.  */
typedef union
{
    struct
    {
        int __lock; 
        unsigned int __futex;
        __extension__ unsigned long long int __total_seq;
        __extension__ unsigned long long int __wakeup_seq;
        __extension__ unsigned long long int __woken_seq;
        void *__mutex;

        unsigned int __nwaiters;
        unsigned int __broadcast_seq; 
     } __data;
    char __size[__SIZEOF_PTHREAD_COND_T];
     __extension__ long long int __align;
} pthread_cond_t;
```
**主要成员：**
- \_\_lock: 锁变量，用于条件变量内部状态的互斥访问；
- \_\_futex: 用来执行futex_wait的变量；
- \_\_total_seq：表示执行了多少次wait操作；
- \_\_wakeup_seq：表示执行了多少次唤醒操作；
- \_\_woken_seq：表示已经被真正唤醒的线程数目；
- \_\_mutex：保存pthread_cond_wait传入的互斥锁；
- \_\_nwaiters：表示条件变量现在还有多少个线程在使用；
- \_\_broadcast_seq：表示执行了多少次broadcast。

2. pthread_cond_wait

```cpp
int
__pthread_cond_wait (cond, mutex)
     pthread_cond_t *cond;
     pthread_mutex_t *mutex;
{
    struct _pthread_cleanup_buffer buffer;
    struct _condvar_cleanup_buffer cbuffer;
     int err;
    int pshared = (cond->__data.__mutex == (void *) ~0l)
        ? LLL_SHARED : LLL_PRIVATE;

     /* Make sure we are along.  */
     // 1.获得cond锁，对cond内状态进行互斥访问。
    lll_lock (cond->__data.__lock, pshared);

    /* Now we can release the mutex.  */
    // 2.释放mutex锁，即函数传入的互斥锁。
    err = __pthread_mutex_unlock_usercnt (mutex, 0);
    if (__builtin_expect (err, 0))
    {
        lll_unlock (cond->__data.__lock, pshared);
        return err;
    }

  /* We have one new user of the condvar.  */
  // 3.修改cond状态
  // 每执行一次wait，__total_seq就会+1
  ++cond->__data.__total_seq;
  // 用来执行futex_wait的变量
  ++cond->__data.__futex;
  // 标识该cond还有多少线程在使用。
  cond->__data.__nwaiters += 1 << COND_NWAITERS_SHIFT;

  /* Remember the mutex we are using here.  If thereis already a
     different address store this is a bad user bug. Do not store
     anything for pshared condvars.  */
  if (cond->__data.__mutex != (void *) ~0l)
    cond->__data.__mutex = mutex;

  /* Prepare structure passed to cancellationhandler.  */
  cbuffer.cond = cond;
  cbuffer.mutex = mutex;

  /* Before we block we enable cancellation. Therefore we have to
     install a cancellation handler.  */
  __pthread_cleanup_push (&buffer, __condvar_cleanup, &cbuffer);

  /* The current values of the wakeup counter.  The"woken" counter
     must exceed this value.  */
  unsigned long long int val;
  unsigned long long int seq;
  val = seq = cond->__data.__wakeup_seq;
  /* Remember the broadcast counter.  */
  cbuffer.bc_seq = cond->__data.__broadcast_seq;

  do {
        unsigned int futex_val =cond->__data.__futex;

        /* Prepare to wait.  Releasethe condvar futex.  */
        // 4. 释放cond锁
        lll_unlock (cond->__data.__lock, pshared);

        /* Enable asynchronouscancellation.  Required by the standard.  */
        cbuffer.oldtype = __pthread_enable_asynccancel();

        /* Wait until woken by signal orbroadcast.  */
        // 5. 在__futex上阻塞线程
        lll_futex_wait (&cond->__data.__futex,futex_val, pshared);

        /* Disable asynchronouscancellation.  */
        // 如果执行到这里，说明我们已经被signal唤醒。
        __pthread_disable_asynccancel (cbuffer.oldtype);

        /* We are going to look at shareddata again, so get the lock.  */
        // 6. 获取cond锁。
        lll_lock (cond->__data.__lock, pshared);

        /* If a broadcast happened, weare done.  */
        if (cbuffer.bc_seq !=cond->__data.__broadcast_seq)
            goto bc_out;

        /* Check whether we are eligiblefor wakeup.  */
        val = cond->__data.__wakeup_seq;
    }while (val == seq || cond->__data.__woken_seq == val); 
    // 如果醒了, 但是woken_seq里并没有变化, 那么继续futex_wait的逻辑

    /* Another thread woken up.  */
    // 7. 修改cond状态
    ++cond->__data.__woken_seq;

    bc_out: 
    cond->__data.__nwaiters -= 1 <<COND_NWAITERS_SHIFT;

    /* If pthread_cond_destroy was called on this varaiblealready,
        notify the pthread_cond_destroy caller all waitershave left
        and it can be successfully destroyed.  */
    if (cond->__data.__total_seq == -1ULL
        && cond->__data.__nwaiters < (1<< COND_NWAITERS_SHIFT))
        lll_futex_wake (&cond->__data.__nwaiters, 1,pshared);

    /* We are done with the condvar.  */
    // 8. 释放cond锁
    lll_unlock (cond->__data.__lock, pshared);

    /* The cancellation handling is back to normal, removethe handler.  */
    __pthread_cleanup_pop (&buffer, 0);

    /* Get the mutex before returning.  */
    // 9. 获取mutex锁
    return __pthread_mutex_cond_lock (mutex);
}
```

**主要流程：**
- 获取cond锁，对cond内状态进行互斥访问;
- 释放mutex锁，即函数传入的互斥锁;
- 修改cond状态;
- 释放cond锁;
- 在__futex上阻塞线程;
- 获取cond锁;
- 修改cond状态;
- 释放cond锁;
- 获取mutex锁。

在这个流程中有几个关键的地方：

**mutex锁：** 主要是实现外面的条件判断和__pthread_cond_wait是一个原子操作，所以阻塞前要释放mutex锁，唤醒之后要重新获取mutex锁；

**cond锁：** 主要解决cond锁内状态的互斥访问。

**mutex锁的释放：** mutex锁的释放是在获取cond锁之后再释放，这样做的是为了避免在释放cond锁之后获取mutex锁之前有其它线程修改了数据；

**系统调用：** 阻塞的操作是调用lll_futex_wait方法，而该方法最终是调用FUTEX_WAIT；

**等待队列：** 线程有可能阻塞在两个锁变量上，一个是mutex.\_\_data.\_\_lock上，另外一个是cond.\_\_data.\_\_futex上。

2. pthread_cond_signal
```cpp
int
__pthread_cond_signal (cond)
     pthread_cond_t *cond;
{
    int pshared = (cond->__data.__mutex == (void *) ~0l)
        ? LLL_SHARED : LLL_PRIVATE;

    /* Make sure we are alone.  */
    // 1. 获取cond锁
    lll_lock (cond->__data.__lock, pshared);

    /* Are there any waiters to be woken?  */
    // 如果wait次数比唤醒的次数多，那么就进行一个唤醒操作。
    if (cond->__data.__total_seq > cond->__data.__wakeup_seq)
    {
        /* Yes.  Mark one of them as woken. */
        // 2. 修改cond状态
        ++cond->__data.__wakeup_seq;
        ++cond->__data.__futex;

        /* Wake one.  */
        if (! __builtin_expect (lll_futex_wake_unlock(&cond->__data.__futex, 1,
           1,&cond->__data.__lock,
           pshared), 0))
            return 0;

        // 3. 唤醒一个线程
        lll_futex_wake(&cond->__data.__futex, 1, pshared);
    }

    /* We are done.  */
    // 4. 释放cond锁
    lll_unlock (cond->__data.__lock, pshared);

    return 0;
}
```
**主要流程：**
- 获取cond锁；
- 修改cond状态；
- 如果wait次数大于wakeup次数，则唤醒一个线程；
- 释放cond锁。

3. pthread_cond_broadcast
与pthread_cond_signal类似，区别在于一次性唤醒所有线程。
```cpp
lll_futex_wake (&cond->__data.__futex, INT_MAX, pshared);
```

#### 3.4.3 总结
1. 条件变量(cond)与互斥(mutex)配合一起使用，以保证条件判断和阻塞操作是一个原子操作；
2. 条件变量(cond)内部有一个cond锁，实现对cond内部状态进行互斥访问；
3. 条件变量(cond)和互斥(mutex)阻塞/唤醒线程都是通过FUTEX_WAIT和FUTEX_WAKE系统调用来实现。






