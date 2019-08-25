---
title: Synchronized 原理
date: 2019-08-17 18:11:20
tags:
- synchronized
- 偏向锁
- 轻量级锁
- 重量级锁
categories:
- 并发编程
---
之前在讲ReentrantLock时，在Java中实现线程的同步与互斥，除了JUC中提供的各种锁，还可以使用snchronized关键字，它被用于方法及方法块中，在JDK1.6之前，synchronized是基于monitor锁对象来实现的，而moniter对象是基于操作系统的futex来实现的，相对比较重量级，这种锁也被称为“重量级锁”。所以，在JDK1.6之后，JDK对synchronized进行了种种优化，为了减少获得锁和释放锁所带来的性能消耗，提高性能，引入了“轻量级锁”和“偏向锁”。
引入“轻量级锁”和“偏向锁”之后，synchronized锁有四种状态，即之前的“无锁”和“重量级锁”，再加上现在这两种，这四种状态有不同的使用场景，如下图所示：
![Synchronized-lock-classify](/images/Synchronized-lock-classify.jpeg "Synchronized-lock-classify")

## 1.概述
synchronized锁一共有4种状态，级别从低到高依次是：无锁、偏向锁、轻量级锁和重量级锁。锁状态只能升级不能降级，转换升级的整体流程如下所示：
![synchronized-overview](/images/synchronized-overview.jpg "synchronized-overview")

**重要的概念：**
- 对象头：在Java中，每一个对象都可以作为锁，锁的相关信息存储在每一个对象头的Mark Word（标记字段）中；
- 偏向锁：在无锁状态下，如果系统支持偏向锁（默认支持），线程使用CAS修改Mark Word的thread id字段，如果修改成功则获得偏向锁。
- 轻量级锁：如果获取偏向锁失败，当前线程会向VM线程提交撤销偏向锁的任务，提交任务后，当前线程会被阻塞，直到任务结束后才会被VM线程唤醒。VM线程执行撤销任务，这时候JVM会进入安全点，所有运行的java线程都会被阻塞（包括获取偏向锁的线程）。在VM线程中，会检查获取锁的线程的状态，如果线程已经不活动或不在同步块中，则将锁状态改为无锁状态；如果线程还在同步块中，则将锁状态升级为轻量级锁，之前获取偏向锁的线程持有轻量级锁。执行完操作之后唤醒被阻塞的当前线程，且退出安全点，所有阻塞在安全点上的线程也会被唤醒；
- 重量级锁：当前线程被唤醒之后，如果锁是无锁状态，则直接获取锁，否则膨胀为重量级锁。在膨胀过程中，会执行以下操作：1）分配monitor对象；2）锁的_owner设置为之前获取锁的线程；3）将当前线程加入到monitor等待队列中，并阻塞当前线程。

## 2.相关概念
### 2.1 Java对象头
在上面的内容讲到，在Java中任何对象都可以作为锁，锁的相关信息都保存在Java的对象头中，我们以Hotspot虚拟机为例，Hotspot的对象头主要包括两部分数据：Mark Word（标记字段）、Klass Pointer（类型指针）。
**Mark Word：** 默认存储对象的HashCode，分代年龄和锁标志位信息。这些信息都是与对象自身定义无关的数据，所以Mark Word被设计成一个非固定的数据结构以便在极小的空间内存存储尽量多的数据。它会根据对象的状态复用自己的存储空间，也就是说在运行期间Mark Word里存储的数据会随着锁标志位的变化而变化。在32位系统上Mark Word长度为32bit，64位系统上长度为64bit，在32位系统上各状态的格式如下所示：
![methord-header](/images/methord-header.jpg "methord-header")
锁信息存于对象的Mark Word中，当对象状态为偏向锁（biasable）时，Mark Word存储的是偏向的线程ID；当状态为轻量级锁（lightweight locked）时，Mark Word存储的是指向线程栈中Lock Record的指针；当状态为重量级锁（inflated）时，为指向堆中的monitor对象的指针。

**Klass Point：** 对象指向它的类元数据的指针，虚拟机通过这个指针来确定这个对象是哪个类的实例。

### 2.2 Monitor对象
在“重量级”锁中，每一个锁都持有一个monitor对象，等同于ReentrantLock中AQS对象，实现等待队列的管理、线程的等待及唤醒等功能，同样地，线程的等待及唤醒借助于操作系统的futex来实现。在上面一节中，如果是重量级锁状态下，Mark Word中存储了Monitor对象的引用，从而建立起了对象锁与monitor对象的映射关系，其关系如下所示：
![monitor-object](/images/monitor-object.jpg "monitor-object")
一个monitor对象包括这么几个关键字段：_cxq，_EntryList ，_WaitSet，_owner。其中_cxq ，_EntryList ，_WaitSet都是由ObjectWaiter的链表结构，_owner指向持有锁的线程。
当一个线程尝试获得锁时(lock)，如果该锁已经被占用，则会将该线程封装成一个ObjectWaiter对象插入到_cxq的队列头部，然后阻塞当前线程。当持有锁的线程释放锁(unlock)时，会根据不同的策略取_cxq或_EntryList的中的对象来进行唤醒。
如果一个线程在同步块中调用了Object#wait方法，会创建对应的ObjectWaiter并加入到WaitSet中，然后释放锁。当wait的线程被notify之后，会将对应的ObjectWaiter从_WaitSet移动到_EntryList中。

### 2.3 安全点（safepoint）
在第一章中讲到偏向锁的撤销是在VM线程中执行，所有的Java线程都进入安全点，即所有线程都被阻塞（stop the world），从而保证对持有锁的线程的更改是原子的。那么安全点是什么？怎么保证所有的线程都暂停？

safepoint安全点顾名思义是指一些特定的位置，当线程运行到这些位置时，线程的一些状态可以被确定(the thread's representation of it's Java machine state is well described)，比如记录OopMap的状态，从而确定GC Root的信息，使JVM可以安全的进行一些操作，比如开始GC。
safepoint指的特定位置主要有:
1. 循环的末尾 (防止大循环的时候一直不进入safepoint，而其他线程在等待它进入safepoint)
2. 方法返回前
3. 调用方法的call之后
4. 抛出异常的位置

safepoint使用场景主要有：
1. Garbage collection pauses
2. Code deoptimization
3. Flushing code cache
4. Class redefinition (e.g. hot swap or instrumentation)
5. **Biased lock revocation**
6. Various debug operation (e.g. deadlock check or stacktrace dump

JVM有两种执行方式：解释型和编译型(JIT)，JVM要保证这两种执行方式下safepoint都能工作。

在JIT执行方式下，JIT编译的时候直接把safepoint的检查代码加入了生成的本地代码，当JVM需要让Java线程进入safepoint的时候，只需要设置一个标志位，让Java线程运行到safepoint的时候主动检查这个标志位，如果标志被设置，那么线程被阻塞，如果没有被设置，那么继续执行。

例如hotspot在x86中为轮询safepoint会生成一条类似于“test %eax,0x160100”的指令，JVM需要进入gc前，先把0x160100设置为不可读，那所有线程执行到检查0x160100的test指令后都会被阻塞。

在解释器执行方式下，JVM会设置一个2字节的dispatch tables,解释器执行的时候会经常去检查这个dispatch tables，当有safepoint请求的时候，就会让线程去进行safepoint检查。

## 3. 锁实现
### 3.1 无锁
无锁没有对资源进行锁定，所有的线程通过CAS操作来获取锁，同时只有一个线程获取成功。

### 3.2 偏向锁

在JDK1.6中为了**提高一个对象在一段很长的时间内都只被一个线程用做锁对象场景下的性能**，引入了偏向锁，在第一次获得锁时，会有一个CAS操作，之后该线程再获取锁，只需要判断线程id与Mark Word中的thread id一致即可。

**对象创建**

当JVM启用了偏向锁模式（1.6以上默认开启），当新创建一个对象的时候，如果该对象所属的class没有关闭偏向锁模式（什么时候会关闭一个class的偏向模式下文会说，默认所有class的偏向模式都是是开启的），那新创建对象的Mark Word将是可偏向状态，此时Mark Word中的thread id为0，表示未偏向任何线程，也叫做匿名偏向(anonymously biased)。

**加锁过程**

case 1：当该对象第一次被线程获得锁的时候，发现是匿名偏向状态，则会用CAS指令，将Mark Word中的thread id由0改成当前线程Id。如果成功，则代表获得了偏向锁，继续执行同步块中的代码。否则，将偏向锁撤销，升级为轻量级锁。如下代码所示：[bytecodeInterpreter.cpp#l1881](
http://hg.openjdk.java.net/jdk8u/jdk8u/hotspot/file/9ce27f0a4683/src/share/vm/interpreter/bytecodeInterpreter.cpp#l1881)
```cpp
// try to bias towards thread in case object is anonymously biased
markOop header = (markOop) ((uintptr_t) mark 
        & ((uintptr_t)markOopDesc::biased_lock_mask_in_place
        | uintptr_t)markOopDesc::age_mask_in_place
        | epoch_mask_in_place));
if (hash != markOopDesc::no_hash) {
    header = header->copy_set_hash(hash);
}

// 将线程id设置为当前线程id
markOop new_header = (markOop) ((uintptr_t) header | thread_ident);
// debugging hint
DEBUG_ONLY(entry->lock()->set_displaced_header((markOop) (uintptr_t) 0xdeaddead);)
// 执行CAS操作，操作成功即可获得偏向锁
if (Atomic::cmpxchg_ptr((void*)new_header, lockee->mark_addr(), header) == header) {
    if (PrintBiasedLockingStatistics)
		(* BiasedLocking::anonymously_biased_lock_entry_count_addr())++;
}
else {
    // 失败则升级到轻量级锁
     CALL_VM(InterpreterRuntime::monitorenter(THREAD, entry), handle_exception);
}
success = true;
```

case 2：当被偏向的线程再次进入同步块时，发现锁对象偏向的就是当前线程，在通过一些额外的检查后，会往当前线程的栈中添加一条Displaced Mark Word为空的Lock Record中，然后继续执行同步块的代码，因为操纵的是线程私有的栈，因此不需要用到CAS指令；由此可见偏向锁模式下，当被偏向的线程再次尝试获得锁时，仅仅进行几个简单的操作就可以了，在这种情况下，synchronized关键字带来的性能开销基本可以忽略。

case 3：当其他线程进入同步块时，发现已经有偏向的线程了，则会进入到撤销偏向锁的逻辑里，一般来说，会在safepoint中去查看偏向的线程是否还存活，如果存活且还在同步块中则将锁升级为轻量级锁，原偏向的线程继续拥有锁，当前线程则走入到锁升级的逻辑里；如果偏向的线程已经不存活或者不在同步块中，则将对象头的Mark Word改为无锁状态（unlocked），之后再升级为轻量级锁。

由此可见，偏向锁升级的时机为：当锁已经发生偏向后，只要有另一个线程尝试获得偏向锁，则该偏向锁就会升级成轻量级锁。

**解锁过程**

当有其他线程尝试获得锁时，是根据遍历偏向线程的Lock Record来确定该线程是否还在执行同步块中的代码。因此偏向锁的解锁很简单，仅仅将栈中的最近一条Lock Record的obj字段设置为null。需要注意的是，偏向锁的解锁步骤中并不会修改对象头中的thread id。

偏向锁在JDK 6及以后的JVM里是默认启用的。可以通过JVM参数关闭偏向锁：-XX:-UseBiasedLocking=false，关闭之后程序默认会进入轻量级锁状态。

**Lock Record**

当前线程每一次进入同步块时都会分配一个Lock Record对象，并将该对象的obj字段指向锁对象，并在解锁的时候将该字段设置为null。在VM线程中执行撤销操作时判断该字段即可知道是否还在同步块中，代码：[bytecodeInterpreter.cpp#l1816](
http://hg.openjdk.java.net/jdk8u/jdk8u/hotspot/file/9ce27f0a4683/src/share/vm/interpreter/bytecodeInterpreter.cpp#l1816)

```cpp
// 设置Lock Record对象
CASE(_monitorenter): {
    // lockee为锁对象
    oop lockee = STACK_OBJECT(-1);
    // derefing's lockee ought to provoke implicit null check
    CHECK_NULL(lockee);
    // find a free monitor or one already allocated for this object
    // if we find a matching object then we need a new monitor
    // since this is recursive enter
	
    // 找到一个空闲的Lock Record对象
    BasicObjectLock* limit = istate->monitor_base();
    BasicObjectLock* most_recent = (BasicObjectLock*) istate->stack_base();
    BasicObjectLock* entry = NULL;
    while (most_recent != limit ) {
        if (most_recent->obj() == NULL) entry = most_recent;
        else if (most_recent->obj() == lockee) break;
        most_recent++;
    }
	
    if (entry != NULL) {
        // 将obj字段指向lockee
        entry->set_obj(lockee);
		... // 略
	}
	
	... // 略
	
}

// 解锁清空Lock Record对象
CASE(_monitorexit): {
    oop lockee = STACK_OBJECT(-1);
    CHECK_NULL(lockee);
	
    // derefing's lockee ought to provoke implicit null check
    // find our monitor slot
    BasicObjectLock* limit = istate->monitor_base();
    BasicObjectLock* most_recent = (BasicObjectLock*) istate->stack_base();
    while (most_recent != limit ) {
        if ((most_recent)->obj() == lockee) {
            BasicLock* lock = most_recent->lock();
            markOop header = lock->displaced_header();

            // 设置Lock Record对象obj为空，退出同步块
            most_recent->set_obj(NULL);
            if (!lockee->mark()->has_bias_pattern()) {
              bool call_vm = UseHeavyMonitors;
              // If it isn't recursive we either must swap old header or call the runtime
              if (header != NULL || call_vm) {

                // 轻量级锁逻辑：lockee不指向Lock Record对象，说明锁升级为重量级锁，否则将锁设置为无锁状态
                if (call_vm || Atomic::cmpxchg_ptr(header, lockee->mark_addr(), lock) != lock) {
                  // restore object for the slow case
                  most_recent->set_obj(lockee);
                  // 膨胀为重量级锁
                  CALL_VM(InterpreterRuntime::monitorexit(THREAD, most_recent), handle_exception);
                }
              }
            }
            UPDATE_PC_AND_TOS_AND_CONTINUE(1, -1);
          }
          most_recent++;
    }
}

```

### 3.3 轻量级锁
JVM的开发者发现在很多情况下，在Java程序运行时，同步块中的代码都是不存在竞争的，不同的线程交替的执行同步块中的代码。这种情况下，用重量级锁是没必要的。因此JVM引入了轻量级锁的概念。

线程在执行同步块之前，JVM会先在当前的线程的栈帧中创建一个Lock Record，其包括一个用于存储对象头中的 mark word（官方称之为Displaced Mark Word）以及一个指向对象的指针。下图右边的部分就是一个Lock Record。
![Lock-Record](/images/Lock-Record.png "Lock-Record")

**加锁过程：**

1. 在线程栈中创建一个Lock Record，将其obj（即上图的Object reference）字段指向锁对象；
2. 直接通过CAS指令将Lock Record的地址存储在对象头的Mark Word中，如果对象处于无锁状态则修改成功，代表该线程获得了轻量级锁。如果失败，进入到步骤3；
3. 如果是当前线程已经持有该锁了，代表这是一次锁重入。设置Lock Record第一部分（Displaced Mark Word）为null，起到了一个重入计数器的作用。然后结束；
4. 走到这一步说明发生了竞争，需要膨胀为重量级锁。

**释放锁过程：**
1. 遍历线程栈,找到所有obj字段等于当前锁对象的Lock Record；
2. 如果Lock Record的Displaced Mark Word为null，代表这是一次重入，将obj设置为null后continue；
3. 如果Lock Record的Displaced Mark Word不为null，则利用CAS指令将对象头的Mark Word恢复成为Displaced Mark Word。如果成功，则continue，否则膨胀为重量级锁。

### 3.4 重量级锁
重量级锁是我们常说的传统意义上的锁，其利用操作系统底层的同步机制去实现Java中的线程同步。重量级锁的状态下，对象的Mark Word为指向一个堆中monitor对象的指针，在上面的内容已经讲过。
monitor对象包括三个链表：_cxq，_EntryList及_WaitSet，被阻塞的线程封装为ObjectWaiter对象，而**ObjectWaiter对象存在于WaitSet、EntryList、cxq等集合中，或者正在这些集合中移动**，那么ObjectWaiter是怎么移动的？下面的内容将进行分析。

**wait方法**
1. 当前线程封装成ObjectWaiter对象，状态为TS_WAIT；
2. ObjectWaiter对象被放入_WaitSet中；
3. 释放锁；
3. 当前线程挂起；

**monitorenter竞争锁**
1. 偏向锁逻辑：判断是否偏向锁，不是则执行轻量级锁逻辑；
2. 轻量级锁逻辑：如果是无锁状态，就通过CAS去竞争锁，否则判断重入，如果不是当前线程持有锁，执行锁膨胀；
3. 重量级锁逻辑：构造OjectMonitor对象，通过CAS去设置owner，如果失败就将线程加入_cxq队列的首位；
4. 执行无限循环，竞争锁成功就退出循环，竞争失败线程挂起，等待被唤醒后继续竞争；

代码如下：

[objectMonitor.cpp#l502](http://hg.openjdk.java.net/jdk8u/jdk8u/hotspot/file/9ce27f0a4683/src/share/vm/runtime/objectMonitor.cpp#l502)

```cpp
void ATTR ObjectMonitor::EnterI (TRAPS) {
    Thread * Self = THREAD ;
    ... // 略

    // 封装ObjectWaiter对象
    ObjectWaiter node(Self) ;
    Self->_ParkEvent->reset() ;
    node._prev   = (ObjectWaiter *) 0xBAD ;
    node.TState  = ObjectWaiter::TS_CXQ ;

    // 加入到_cxq队首
    ObjectWaiter * nxt ;
    for (;;) {
        node._next = nxt = _cxq ;
        if (Atomic::cmpxchg_ptr (&node, &_cxq, nxt) == nxt) break ;

        // Interference - the CAS failed because _cxq changed.  Just retry.
        // As an optional optimization we retry the lock.
        if (TryLock (Self) > 0) {
            assert (_succ != Self         , "invariant") ;
            assert (_owner == Self        , "invariant") ;
            assert (_Responsible != Self  , "invariant") ;
            return ;
        }
    }

    TEVENT (Inflated enter - Contention) ;
    int nWakeups = 0 ;
    int RecheckInterval = 1 ;

    for (;;) {

        if (TryLock (Self) > 0) break ;
        assert (_owner != Self, "invariant") ;

        if ((SyncFlags & 2) && _Responsible == NULL) {
           Atomic::cmpxchg_ptr (Self, &_Responsible, NULL) ;
        }

        // park self
        if (_Responsible == Self || (SyncFlags & 1)) {
            TEVENT (Inflated enter - park TIMED) ;
            Self->_ParkEvent->park ((jlong) RecheckInterval) ;
            // Increase the RecheckInterval, but clamp the value.
            RecheckInterval *= 8 ;
            if (RecheckInterval > 1000) RecheckInterval = 1000 ;
        } else {
            TEVENT (Inflated enter - park UNTIMED) ;
            
            // 阻塞当前线程
            Self->_ParkEvent->park() ;
        }

        if (TryLock(Self) > 0) break ;

       ... // 略
    }
	
	... // 略
}
```

**notify方法**
1. 执行过wait方法的线程都在队列_WaitSet中，此处从_WaitSet中取出第一个；
2. 根据Policy的不同，将这个线程放入_EntryList或者_cxq队列中的起始或末尾位置。

Policy逻辑如下：

1. Policy == 0：放入_EntryList队列的排头位置；
2. Policy == 1：放入_EntryList队列的末尾位置；
3. Policy == 2：_EntryList队列为空就放入_EntryList，否则放入_cxq队列的排头位置；
4. Policy == 3：放入_cxq队列中，末尾位置；
5. Policy等于其他值，立即唤醒ObjectWaiter对应的线程。

**monitorexit释放锁**
1. 偏向锁逻辑，此处不是；
2. 轻量级锁逻辑，此处不是，执行锁膨胀；
3. 重量级锁逻辑，根据QMode的不同，将ObjectWaiter从_cxq或者_EntryList中取出后唤醒；
4. 唤醒的线程会继续执行挂起前的代码。

QMode逻辑如下：
1. QMode = 2，并且_cxq非空：取_cxq队列排头位置的ObjectWaiter对象，调用ExitEpilog方法，该方法会唤醒ObjectWaiter对象的线程，此处会立即返回，后面的代码不会执行了；
2. QMode = 3，并且_cxq非空，把_cxq队列首元素放入_EntryList的尾部，执行第5步；
3. QMode = 4，并且_cxq非空，把_cxq队列首元素放入_EntryList的头部，执行第5步；
4. QMode = 0，执行第5步；
5. 如果_EntryList的首元素非空，就取出来调用ExitEpilog方法，该方法会唤醒ObjectWaiter对象的线程，然后立即返回；如果_EntryList的首元素为空，就取_cxq的首元素，放入_EntryList，然后再从_EntryList中取出来执行ExitEpilog方法，然后立即返回，以上操作，均是执行过ExitEpilog方法然后立即返回，如果取出的元素为空，就执行循环继续取。

**总结：** 通过设置Policy及QMode，可以实现不同的调度逻辑。

## 4. 总结
总的来说synchronized的重量级锁和ReentrantLock的实现上还是有很多相似的，包括其数据结构、挂起线程方式等等，底层都是基于操作系统的futex实现。如果没有什么特殊要求使用synchronized即可。

**参考：**

----
[1]:https://github.com/farmerjohngit/myblog/issues/12
[2]:https://blog.csdn.net/boling_cavalry/article/details/77793224
[3]:https://tech.meituan.com/2018/11/15/java-lock.html
[4]:https://blog.csdn.net/iter_zc/article/details/41847887

[1. 死磕Synchronized底层实现--概论][1]

[2. Java的wait()、notify()学习三部曲之一：JVM源码分析][2]

[3. 不可不说的Java“锁”事][3]

[4. 聊聊JVM（六）理解JVM的safepoint][4]

