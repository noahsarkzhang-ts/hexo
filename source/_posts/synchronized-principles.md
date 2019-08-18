---
title: synchronized 原理
date: 2019-08-17 18:11:20
tags:
- synchronized
- 偏向锁
- 轻量级锁
- 重量级锁
categories:
- 并发编程
---
之前在讲ReentrantLock时，在Java中实现线程的同步与互斥，除了JUC中提供的各种锁，还可以使用snchronized关键字，它可以用在方法及方法块中，在JDK1.6之前，synchronized是基于monitor锁对象来实现的，而moniter对象是基于操作系统的futex来实现的，相对比较重量级，这种锁称为“重量级锁”。所以，在JDK1.6之后，JDK对synchronized进行了种种优化，为了减少获得锁和释放锁所带来的性能消耗，提高性能，引入了“轻量级锁”和“偏向锁”。
引入“轻量级锁”和“偏向锁”之后，synchronized锁有四种状态，即之前的“无锁”和“重量级锁”，再加上现在这两种，这四种状态有不同的使用场景，如下图所示：
![Synchronized-lock-classify](/images/Synchronized-lock-classify.jpeg "Synchronized-lock-classify")

## 1.概述
synchronized锁一共有4种状态，级别从低到高依次是：无锁、偏向锁、轻量级锁和重量级锁。锁状态只能升级不能降级，转换升级的整体流程如下所示：
![synchronized-overview](/images/synchronized-overview.jpg "synchronized-overview")

**重要的概念：**
- 对象头：在Java中，每一个对象都可以作为锁，锁的相关信息存储在每一个对象头的Mark Word（标记字段）中；
- 偏向锁：在无锁状态下，如果系统支持偏向锁（默认支持），线程使用CAS修改Mark Word的thread id字段，如果修改成功则获得偏向锁。
- 轻量级锁：如果获取偏向锁失败，当前线程会向VM线程提交撤销偏向锁的任务，提交任务后，当前线程会被阻塞，等待VM线程唤醒。VM线程执行撤销任务，这时候JVM会进入安全点，所有运行的java线程都会被阻塞（包括获取偏向锁的线程）。在VM线程中，会检查获取锁的线程的状态，如果线程已经不活动或不在同步块中，则将锁状态改为无锁状态；如果线程还在同步块中，则将锁状态升级为轻量级锁，之前获取偏向锁的线程持有轻量级锁。最后唤醒当前线程，且退出安全点，唤醒阻塞在安全点上的线程；
- 重量级锁：当前锁被唤醒之后，如果锁是无锁状态，则直接获取锁，否则膨胀为重量级锁，分配monitor对象，将锁的ower设置为之前获取锁的线程，同时将当前线程加入到monitor等待队列中，阻塞当前线程。

## 2.相关概念
### 2.1 Java对象头
在上面的内容讲到，在Java中任何对象都可以作为锁，锁的相关信息都保存在Java的对象头中，我们以Hotspot虚拟机为例，Hotspot的对象头主要包括两部分数据：Mark Word（标记字段）、Klass Pointer（类型指针）。
**Mark Word：** 默认存储对象的HashCode，分代年龄和锁标志位信息。这些信息都是与对象自身定义无关的数据，所以Mark Word被设计成一个非固定的数据结构以便在极小的空间内存存储尽量多的数据。它会根据对象的状态复用自己的存储空间，也就是说在运行期间Mark Word里存储的数据会随着锁标志位的变化而变化。在32位系统上Mark Word长度为32bit，64位系统上长度为64bit，在32位系统上各状态的格式如下所示：
![methord-header](/images/methord-header.jpg "methord-header")
锁信息存于对象的Mark Word中，当对象状态为偏向锁（biasable）时，Mark Word存储的是偏向的线程ID；当状态为轻量级锁（lightweight locked）时，Mark Word存储的是指向线程栈中Lock Record的指针；当状态为重量级锁（inflated）时，为指向堆中的monitor对象的指针。

**Klass Point：** 对象指向它的类元数据的指针，虚拟机通过这个指针来确定这个对象是哪个类的实例。

### 2.2 Monitor对象
在“重量级”锁中，每一个锁都持有一个monitor对象，等同于ReentrantLock中AQS对象，实现等待队列的管理，线程的等待及唤醒借助于操作系统的futex来实现。在上面一节中，如果是重量级锁状态下，Mark Word中存储了Monitor对象的引用，从而建立起了对象锁与monitor对象的映射关系，其关系如下所示：
![monitor-object](/images/monitor-object.png "monitor-object")
一个monitor对象包括这么几个关键字段：cxq（ContentionList），EntryList ，WaitSet，owner。其中cxq ，EntryList ，WaitSet都是由ObjectWaiter的链表结构，owner指向持有锁的线程。
当一个线程尝试获得锁时，如果该锁已经被占用，则会将该线程封装成一个ObjectWaiter对象插入到cxq的队列尾部，然后阻塞当前线程。当持有锁的线程释放锁前，会将cxq中的所有元素移动到EntryList中去，并唤醒EntryList的队首线程。
如果一个线程在同步块中调用了Object#wait方法，会将该线程对应的ObjectWaiter从EntryList移除并加入到WaitSet中，然后释放锁。当wait的线程被notify之后，会将对应的ObjectWaiter从WaitSet移动到EntryList中。

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
无锁没有对资源进行锁定，所有的线程都能访问并修改同一个资源，但同时只有一个线程能修改成功。

无锁的特点就是修改操作在循环内进行，线程会不断的尝试修改共享资源。如果没有冲突就修改成功并退出，否则就会继续循环尝试。如果有多个线程修改同一个值，必定会有一个线程能修改成功，而其他修改失败的线程会不断重试直到修改成功。上面我们介绍的CAS原理及应用即是无锁的实现。无锁无法全面代替有锁，但无锁在某些场合下的性能是非常高的。
### 3.1 偏向锁
偏向锁是指一段同步代码一直被一个线程所访问，那么该线程会自动获取锁，降低获取锁的代价。

在大多数情况下，锁总是由同一线程多次获得，不存在多线程竞争，所以出现了偏向锁。其目标就是在只有一个线程执行同步代码块时能够提高性能。

当一个线程访问同步代码块并获取锁时，会在Mark Word里存储锁偏向的线程ID。在线程进入和退出同步块时不再通过CAS操作来加锁和解锁，而是检测Mark Word里是否存储着指向当前线程的偏向锁。引入偏向锁是为了在无多线程竞争的情况下尽量减少不必要的轻量级锁执行路径，因为轻量级锁的获取及释放依赖多次CAS原子指令，而偏向锁只需要在置换ThreadID的时候依赖一次CAS原子指令即可。

偏向锁只有遇到其他线程尝试竞争偏向锁时，持有偏向锁的线程才会释放锁，线程不会主动释放偏向锁。偏向锁的撤销，需要等待全局安全点（在这个时间点上没有字节码正在执行），它会首先暂停拥有偏向锁的线程，判断锁对象是否处于被锁定状态。撤销偏向锁后恢复到无锁（标志位为“01”）或轻量级锁（标志位为“00”）的状态。

偏向锁在JDK 6及以后的JVM里是默认启用的。可以通过JVM参数关闭偏向锁：-XX:-UseBiasedLocking=false，关闭之后程序默认会进入轻量级锁状态。

### 3.2 轻量级锁
是指当锁是偏向锁的时候，被另外的线程所访问，偏向锁就会升级为轻量级锁，其他线程会通过自旋的形式尝试获取锁，不会阻塞，从而提高性能。

在代码进入同步块的时候，如果同步对象锁状态为无锁状态（锁标志位为“01”状态，是否为偏向锁为“0”），虚拟机首先将在当前线程的栈帧中建立一个名为锁记录（Lock Record）的空间，用于存储锁对象目前的Mark Word的拷贝，然后拷贝对象头中的Mark Word复制到锁记录中。

拷贝成功后，虚拟机将使用CAS操作尝试将对象的Mark Word更新为指向Lock Record的指针，并将Lock Record里的owner指针指向对象的Mark Word。

如果这个更新动作成功了，那么这个线程就拥有了该对象的锁，并且对象Mark Word的锁标志位设置为“00”，表示此对象处于轻量级锁定状态。

如果轻量级锁的更新操作失败了，虚拟机首先会检查对象的Mark Word是否指向当前线程的栈帧，如果是就说明当前线程已经拥有了这个对象的锁，那就可以直接进入同步块继续执行，否则说明多个线程竞争锁。

若当前只有一个等待线程，则该线程通过自旋进行等待。但是当自旋超过一定的次数，或者一个线程在持有锁，一个在自旋，又有第三个来访时，轻量级锁升级为重量级锁。

### 3.3 重量级锁
升级为重量级锁时，锁标志的状态值变为“10”，此时Mark Word中存储的是指向重量级锁的指针，此时等待锁的线程都会进入阻塞状态。

## 4. 总结
