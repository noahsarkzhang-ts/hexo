---
title: Java 内存模型
date: 2020-06-14 20:36:17
updated: 2020-06-14 20:36:17
tags:
- JMM
- 指令重排
categories:
- Java基础
---

## 1. 概述

处于优化的目的，在不同的编译器及不同体系架构的cpu 中，会将指令重排，即程序中排在后面的指令有可能比排在前面的指令先执行。同时由于cpu 中存在读写缓冲区，会将指令相关的运行时数据暂存在这些缓冲区中，也会导致指令重排的问题。目前的cpu 都是多核的体系架构，同一个语言编写的程序在不同硬件体系中，在多线程执行环境下，多次执行的结果可能不一致。在Java 中，怎么解决这个问题？为了屏蔽不同硬件架构的差异，给程序员提供一致的运行结果，Java 提出了 JMM(内存模型)的概念。

<!-- more -->

Java 内存模型（JMM）描述了在Java 语言中线程如何与主内存（Main Memory）进行交互，定义了一套线程对共享变量的访问规则，同时决定一个线程对共享变量的写入何时对另外一个线程可见。

在Java 中，共享变量主要包括实例字段、静态字段和数组元素，这些变量存储在堆内存中，由所有线程共享。而局部变量、方法参数和异常处理参数不会在线程间共享，不存在可见性（一个线程对变量的写入对另外的线程可见）的问题，不受内存模型的的影响。

从抽象的角度来看，JMM 定义了线程和主内存之间的抽象关系：线程之间的共享变量存储在主内存（Main Memory）中，每个线程都有一个私有的本地内存（Local memory），本地内存中存储了该线程读/写共享变量的副本。本地内存是JMM 的一个抽象概念，并不真实存在，它涵盖了缓存、写缓存区、寄存器以及其它硬件。JMM 抽象示意图如下所示：
![JMM](/images/JMM.jpg "JMM")

从上图来看，线程A与线程B要进行通过的话，必须要经历两个步骤：
1. 首先，线程A将在本地内存中修改的共享变量刷新到主内存中；
2. 最后，线程B重新从主内存加载修改后的共享变量，从而看到被修改后的内容。

本质上来说，JMM 通过控制主内存与每个线程的本地内存之间的交互，来提供内存可见性的保证。

## 2. 重排序
在执行程序时为了提高性能，编译器和处理器常常会对指令做重排序。重排序分三种类型：
1. 编译器优化的重排序。编译器在不改变单线程程序语义的前提下，可以重新安排语句的执行顺序。
2. 指令级并行的重排序。现代处理器采用了指令级并行技术（Instruction-Level Parallelism， ILP）来将多条指令重叠执行。如果不存在数据依赖性，处理器可以改变语句对应机器指令的执行顺序。
3. 内存系统的重排序。由于处理器使用缓存和读/写缓冲区，这使得加载和存储操作看上去可能是在乱序执行。
从java源代码到最终实际执行的指令序列，会分别经历下面三种重排序：
![java-instruction-reorder](/images/java-instruction-reorder.png "java-instruction-reorder")

上述的1属于编译器重排序，2和3属于处理器重排序。这些重排序都可能会导致多线程程序出现内存可见性问题。对于编译器，JMM的编译器重排序规则会禁止特定类型的编译器重排序（不是所有的编译器重排序都要禁止）。对于处理器重排序，JMM的处理器重排序规则会要求java编译器在生成指令序列时，插入特定类型的内存屏障（memory barriers，intel称之为memory fence）指令，通过内存屏障指令来禁止特定类型的处理器重排序（不是所有的处理器重排序都要禁止）。
JMM属于语言级的内存模型，它确保在不同的编译器和不同的处理器平台之上，通过禁止特定类型的编译器重排序和处理器重排序，为程序员提供一致的内存可见性保证。

## 3. 内存系统重排序
现代处理器与内存存在较大的性能差异，以主频为3GHZ的cpu为例，cpu访问一次内存时间在10~100ns内，但cpu  在100ns内可以执行1200条指令（假定一个时钟周期可以同时执行4条指令，一个时间周期为0.3ns）。因此，现代处理器在内存之间引入了多级的缓存结构，同时为了提高指令的执行效率，在cpu 寄存器与缓存之间引入了读/写缓冲区。写缓冲区可以保证指令流水线持续运行，它可以避免由于处理器停顿下来等待向内存写入数据而产生的延迟。同时，通过以批处理的方式刷新写缓冲区，以及合并写缓冲区中对同一内存地址的多次写，可以减少对内存总线的占用。读缓冲区可以缓存当前指令读取的数据，实现cpu异步读取数据，提高cpu的吞吐率。以Intel x86 CPU （2012 Sandy Bridge）为例，如下图所示：
![memory-heirarchy](/images/memory-heirarchy.png "memory-heirarchy")
其内部组成包括：
1. 寄存器：在每个cpu 核心上，有160个用于整数和144个用于浮点的寄存器单元。访问这些寄存器只需要一个时钟周期，这构成了对执行核心来说最快的内存。编译器会将本地变量和函数参数分配到这些寄存器上。当使用超线程技术（ hyperthreading ）时，这些寄存器可以在超线程协同下共享。
2. 读写缓冲区：读写缓存区包含64个load 缓冲条目和36个的store 缓冲条目。这些缓冲区用于记录等待缓存子系统时正在执行的操作。store 缓冲区保存将要写到L1 缓存的数据。load 缓冲区保存正要被寄存器读取的数据。由于读/写缓存仅对当前cpu 核心可见，这会造成指令的重排序，需要通过内存屏障来保证其执行顺序。
3. L1 & L2 缓存：L1和L2 是一个本地核心内的缓存，它们在大小和速度上存在差异。
4. L3 缓存： 同插槽的所有cpu 核心共享L3缓存。L3缓存被分为多个2MB的段，所有段组成一环形网络。每一个核心都连接到这个环形网络上，地址通过hash的方式映射到段上以达到更大的吞吐量。
5. 主内存：在缓存没命中的情况下，内存的平均延迟为65ns。
7. NUMA：在一个多插槽的服务器上，会使用非一致性内存访问机制（ non-uniform memory access ）。之所以要使用该方式主要是因为需要的数据在另外一个远程插槽上，需要跨越QPI 总线且额外花费40ns。 

在上文讲到的多级缓存系统中，L1,L2,L3级缓存与主内存之间一致性一般是通过Cache Conherence技术来实现的，Intel 使用MESIF协议，AMD 使用 MOESI，在这里不再描述，我们假定：一旦内存数据被推送到L1 缓存，就会有消息协议来确保所有的缓存会对所有的共享数据同步并保持一致。

现在我们来分析引入读写缓冲区带来的问题，先看下两者的作用：
> When a store is issued to the out-of-order core for renaming and scheduling, an entry in the store buffer is allocated (in-order) for the address and the data. The store buffer will hold the address and data until the instruction has retired and the data has been written to the L1 cache.

> Analogously, when a load is issued, an entry in the load buffer is reserved for the address. However, loads must also compare the load address against the contents of the entire store buffer to check for aliasing with older stores. If the load address matches an older store, then the load must wait for the older store to complete to preserve the dependency. Most x86 processors optimize this further, by allowing the store to forward data to the load without accessing the cache. The load buffer entry can be released, once the instruction has retired and the load data is written into the register file.

> Because of the strong x86 ordering model, the load buffer is snooped by coherency traffic. A remote store must invalidate all other copies of a cache line. If a cache line is read by a load, and then invalidated by a remote store, the load must be cancelled, since it potentially read invalid data. The x86 memory model does not require snooping the store buffer.

其要点包括：1）写缓冲区缓存指令的地址及数据信息，直到指令执行完毕且数据写入到L1 缓存中，写入到L1 缓存中之后，会通过MESIF协议通知其它cpu 核心失效相关的缓存行；2）读缓冲区按照地址缓存数据，直到指令执行完毕且数据被读到寄存器中；2）读缓冲区缓存了来自L1 缓存的数据，所以受MESIF协议的侦测，如果数据被其它远程的写缓冲区修改，根据MESIF协议，它会失效所有的数据拷贝，包括读缓冲区中的数据。

由于读写缓冲区只对当前cpu 核心有效，会造成指令重排的问题，要解决这个问题，需要引入“内存屏障”的技术。内存屏障提供了两个功能。首先，它们通过确保从另一个cpu 来看屏障的两边的所有指令都是正确的程序顺序，而保持程序顺序的外部可见性；其次它们可以实现内存数据可见性，确保内存数据会同步到cpu L1。

**Store Barrier**
Store 屏障，是x86的”sfence“ 指令，强制所有在store 屏障指令之前的store 指令，都在该store 屏障指令执行之前被执行，并把store 缓冲区的数据都刷到L1 ，这会使得程序状态对其它cpu 可见。

**Load Barrier**
Load 屏障，是x86 上的”ifence“ 指令，强制所有在load 屏障指令之后的load 指令，都在该load 屏障指令执行之后被执行，并且一直等到load 缓冲区被该cpu 读完才能执行之后的load 指令。这使得从其它cpu 暴露出来的程序状态对该cpu 可见，这之后cpu 可以进行后续处理。

**Full Barrier**
Full 屏障，是x86 上的”mfence“ 指令，复合了load 和save 屏障的功能。

## 4. 编译器重排序
**数据依赖性**
如果两个操作访问同一个变量，且这两个操作中有一个为写操作，此时这两个操作之间就存在数据依赖性。数据依赖分下列三种类型：

| 名称  | 代码示例 | 说明 |
| ----  | ------- | ---- |
| 写后读 | a = 1;b = a; | 写一个变量之后，再读这个位置 |
| 写后写 | a = 1;a = 2; | 写一个变量之后，再写这个变量 |
| 读后写 | a = b;b = 1; | 读一个变量之后，再写这个变量 |

上面三种情况，只要重排序两个操作的执行顺序，程序的执行结果将会被改变。

前面提到过，编译器和处理器可能会对操作做重排序。编译器和处理器在重排序时，会遵守数据依赖性，编译器和处理器不会改变存在数据依赖关系的两个操作的执行顺序

**as-if-serial 语义**
as-if-serial 语义的意思指：不管怎么重排序（编译器和处理器为了提高并行度），（单线程）程序的执行结果不能被改变。编译器，runtime 和处理器都必须遵守 as-if-serial 语义。

为了遵守 as-if-serial 语义，编译器和处理器不会对存在数据依赖关系的操作做重排序，因为这种重排序会改变执行结果。但是，如果操作之间不存在数据依赖关系，这些操作可能被编译器和处理器重排序。

## 5. JMM内存屏障
为了保证内存可见性，Java 编译器在生成指令序列的适当位置会插入内存屏障指令来禁止特定类型的处理器重排序。JMM把内存屏障指令分为下列四类：

| 屏障类型 |指令示例| 说明 |
| ------------------- |  ------------------------- | -------------------------------------------  |
| LoadLoad Barriers |	Load1; LoadLoad; Load2 |	确保Load1数据的装载，之前于Load2及所有后续装载指令的装载。|
| StoreStore Barriers |	Store1; StoreStore; Store2 | 确保Store1数据对其他处理器可见（刷新到内存），<br>之前于Store2及所有后续存储指令的存储。|
| LoadStore Barriers |	Load1; LoadStore; Store2 |	确保Load1数据装载，之前于Store2及所有后续<br>的存储指令刷新到内存。|
| StoreLoad Barriers |	Store1; StoreLoad; Load2 |	确保Store1数据对其他处理器变得可见（指刷新到内存），<br>之前于Load2及所有后续装载指令的装载。StoreLoad Barriers <br>会使该屏障之前的所有内存访问指令（存储和装载指令）完成之后，<br>才执行该屏障之后的内存访问指令。| 

StoreLoad Barriers是一个“全能型”的屏障，它同时具有其他三个屏障的效果。现代的多处理器大都支持该屏障（其他类型的屏障不一定被所有处理器支持）。执行该屏障开销会很昂贵，因为当前处理器通常要把写缓冲区中的数据全部刷新到内存中（buffer fully flush）。

**JMM 内存屏障与cpu 内存屏障的映射**
在不同cpu 架构中，实现的内存屏障是不同的，如上面的X86体系中，只允许StoreLoad指令重排，所以只用实现StoreLoad Barriers，而其它cpu 体系则有所不同，其对应关系如下图所示：
![cpu-barriers-map-jmm](/images/cpu-barriers-map-jmm.png "cpu-barriers-map-jmm")

由于常见的cpu 内存屏障比 JMM 要弱，java 编译器在生成字节码时，会在执行指令序列的适当位置插入内存屏障来限制处理器的重排序。同时，由于各种处理器内存屏障的强弱并不相同，为了在不同的处理器平台向程序员展示一个一致的内存模型，JMM 在不同的处理器中需要插入的内存屏障的数量和种类也不相同。

## 6. happen-before
JMM 使用happens-before 的概念来阐述操作之间的内存可见性，如果一个操作执行的结果需要对另一个操作可见，那么这两个操作之间必须要存在happens-before 关系。这里提到的两个操作既可以是在一个线程之内，也可以是在不同线程之间。
与程序员密切相关的happens-before 规则如下：
1. 程序顺序规则：一个线程中的每个操作，happens-before 于该线程中的任意后续操作。
2. 监视器锁规则：对一个监视器锁的解锁，happens-before 于随后对这个监视器锁的加锁。
3. volatile变量规则：对一个volatile域的写，happens-before 于任意后续对这个volatile域的读。
4. 传递性：如果A happens- before B，且B happens- before C，那么A happens- before C。

注意，两个操作之间具有happens-before关系，并不意味着前一个操作必须要在后一个操作之前执行！happens-before 仅仅要求前一个操作（执行的结果）对后一个操作可见，且前一个操作按顺序排在第二个操作之前（the first is visible to and ordered before the second）。
happens-before与JMM的关系如下图所示：
![happens-before](/images/happens-before.png "happens-before")

## 7. 总结
通过JMM 模型的定义，使得Java语言真正实现了跨平台，在不同平台，多线程的执行总能得到一致的结果，同时定义happens-before 规则，简化了对JMM 理解难度。

**参考：**

----
[1]:https://www.infoq.cn/article/java-memory-model-1/
[2]:https://www.infoq.cn/article/java-memory-model-2/
[3]:https://download.oracle.com/otn-pub/jcp/memory_model-1.0-pfd-spec-oth-JSpec/memory_model-1_0-pfd-spec.pdf?AuthParam=1593252270_c3d47e052ce05eb43eb35a8c96217567
[4]:https://www.realworldtech.com/haswell-tm-alt/2/
[5]:http://ifeve.com/cpu-cache-flushing-fallacy/
[6]:http://ifeve.com/memory-barriersfences/


[1. 深入理解 Java 内存模型（一）——基础][1]
[2. 深入理解 Java 内存模型（二）——重排序][2]
[3. SR-133: JavaTM Memory Model and Thread Specification][3]
[4. Haswell Transactional Memory Alternatives][4]
[5. CPU Cache Flushing Fallacy][5]
[6. Memory Barriers/Fences][6]


