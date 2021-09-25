---
title: Netty 系列：内存管理（摘录）
date: 2021-09-19 11:26:47
tags:
- 内存管理
- 伙伴算法
- slab
- jemalloc
categories:
- Netty
---

## 1.概述

在操作系统中内存管理的基本单位是 page, page 大小一般是 4k。为了满足不同场景，分配不同大小的内存，操作系统提供了丰富的内存管理方法。从分层的角度来说，可以用下面的层次图来表示。

![netty-memory-management-level](/images/netty/netty-memory-management-level.jpg "renetty-memory-management-levelactor")

1. 在内核空间，Buddy 系统提供了 page 级的内存分配，可以实现较大连续内存的分配，最小的分配单位是 page；
2. 在内核空间，Buddy 最小分配单位是 4k ,即一个 page。为了避免内存空间的浪费（小于 4K 的空间也会分配一个 page），slab 提供了小内存空间的分配机制；
3. 在用户空间，一般是通过 Buddy 分配一个大内存，在这个大内存里面，使用特定的数据来管理内存的分配，满足不同场景下内存的使用，典型的分配算法有：ptmalloc,tcmalloc 及 jemalloc。

> ptmalloc 是基于 glibc 实现的内存分配器，它是一个标准实现，所以兼容性较好。pt 表示 per thread 的意思。 ptmalloc 在多线程的性能优化上下了很多功夫。不过由于过于考虑性能问题，多线程之间内存无法实现共享，每个线程都独立使用各自的内存，所以在内存开销上是有很大浪费的。

> tcmalloc 出身于 Google，全称是 thread-caching malloc，所以 tcmalloc 最大的特点是带有线程缓存，tcmalloc 非常出名，目前在 Chrome、Safari 等知名产品中都有所应有。tcmalloc 为每个线程分配了一个局部缓存，对于小对象的分配，可以直接由线程局部缓存来完成，对于大对象的分配场景，tcmalloc 尝试采用自旋锁来减少多线程的锁竞争问题。

> jemalloc 是由 Jason Evans 在 FreeBSD 项目中引入的新一代内存分配器。它是一个通用的 malloc 实现，侧重于减少内存碎片和提升高并发场景下内存的分配效率，其目标是能够替代 malloc。jemalloc 应用十分广泛，在 Firefox、Redis、Rust、Netty 等出名的产品或者编程语言中都有大量使用。
> jemalloc 借鉴了 tcmalloc 优秀的设计思路，所以在架构设计方面两者有很多相似之处，同样都包含 thread cache 的特性。但是 jemalloc 在设计上比 ptmalloc 和 tcmalloc 都要复杂，jemalloc 将内存分配粒度划分为 Small、Large、Huge 三个分类，并记录了很多 meta 数据，所以在空间占用上要略多于 tcmalloc，不过在大内存分配的场景，jemalloc 的内存碎片要少于 tcmalloc。

在 Netty 中使用 jemalloc 分配器来实现对内存的管理，借助学习 Netty 的机会，顺便学习下内存管理的基本知识。这篇文章主要是对关键的分配算法做一个概述，希望能够说清楚该分配算法的整体结构，并不会对实现细节进行分析，这也超出了我的能力范围。

## 2. Buddy 系统

> page：虚拟地址空间按照固定大小划分成被称为页（page）的若干单元，物理内存中对应的则是页框（page frame）。这两者一般来说是一样的大小，如 4KB，在本文中，我们统一用 page 表示分页。

在内存管理中，存在两种碎片，一种是内部碎片，另外一种是外部碎片。page 是操作系统中内存分配的基本单元，如果分配的对象小于 page 的大小，就会造成 page 尾部空间的浪费，形成内部碎片。而外部碎片主要是指空闲的 page 不连续，造成可用的空间不能满足大内存的分配，形成外部碎片。

Buddy 系统主要解决了外部碎片的问题，它把所有的空闲 page 分组为 11 个块链表，每个块链表由不同大小的内存块组成，大小分别为1，2，4，8，16，32，64，128，256，512 和 1024个 连续 page 的 page 块。最大可以申请 1024 个连续 page，对应 4MB 大小的连续内存。如下图所示：

![buddy-system](/images/netty/buddy-system.jpg "buddy-system")

假设要申请一个256个 page 的块，先从 256 个 page 的链表中查找空闲块，如果没有，就去 512 个 page 的链表中找，找到了则将页框块分为 2 个 256 个 page 的块，一个分配给应用，另外一个移到 256个 page 的链表中。如果 512 个 page 的链表中仍没有空闲块，继续向 1024 个 page 的链表查找，如果仍然没有，则返回错误。page 块在释放时，会主动将两个连续的 page 块合并为一个较大的 page 块。

buddy（伙伴）系统的含义就是不断合并相邻的 page，通过这种办法来减少外部碎片的存在，这也是 Buddy 系统的本质所在。

## 3. slab

在Linux中，buddy system（伙伴系统）是以 page 为单位管理和分配内存。page 默认大小为 4K，如果要分配 20 Bytes 大小的内存，就会造成很大的浪费，怎么解决这个问题呢？ slab 分配器就应运而生了，专为小内存分配而生。slab分配器分配内存以 Byte 为单位。但是 slab 分配器并没有脱离伙伴系统，而是基于伙伴系统分配的大内存进一步细分成小内存分配。先看下图：

![slab](/images/netty/slab.jpg "slab")

kmem_cache 是一个 cache_chain 的链表，描述了一个高速缓存，每个高速缓存包含了一个 slabs 的列表，这通常是一段连续的内存块。存在 3 种 slab：

1. slabs_full(完全分配的slab)
2. slabs_partial(部分分配的slab)
3. slabs_empty(空slab,或者没有对象被分配)。


slab 是 slab 分配器的最小单位，在实现上一个 slab 有一个或多个连续的 page 组成（通常只有一个 page ）。单个 slab 可以在 slab 链表之间移动，如果一个半满 slab 被分配了对象后变满了，就要从slabs_partial 中被删除，同时插入到 slabs_full 中去。

可以通过下面的命令查看 slab 信息。
```bash
root@noahsark ~]# cat /proc/slabinfo
slabinfo - version: 2.1
# name            <active_objs> <num_objs> <objsize> <objperslab> <pagesperslab> : tunables <limit> <batchcount> <sharedfactor> : slabdata <active_slabs> <num_slabs> <sharedavail>
...
UDP                  150    150   1088   15    4 : tunables    0    0    0 : slabdata     10     10      0
tw_sock_TCP          208    208    256   16    1 : tunables    0    0    0 : slabdata     13     13      0
TCP                  224    224   1984   16    8 : tunables    0    0    0 : slabdata     14     14      0
net_namespace         12     12   5248    6    8 : tunables    0    0    0 : slabdata      2      2      0
mm_struct            260    260   1600   20    8 : tunables    0    0    0 : slabdata     13     13      0
fs_cache            1856   1856     64   64    1 : tunables    0    0    0 : slabdata     29     29      0
files_cache          122    180    640   12    2 : tunables    0    0    0 : slabdata     15     15      0
task_struct          317    385   4208    7    8 : tunables    0    0    0 : slabdata     55     55      0
cred_jar             299    525    192   21    1 : tunables    0    0    0 : slabdata     25     25      0
anon_vma            2221   2448     80   51    1 : tunables    0    0    0 : slabdata     48     48      0
pid                  704    704    128   32    1 : tunables    0    0    0 : slabdata     22     22      0
shared_policy_node   6840   7480     48   85    1 : tunables    0    0    0 : slabdata     88     88      0
numa_policy           15     15    264   15    1 : tunables    0    0    0 : slabdata      1      1      0
radix_tree_node    29849  30926    584   14    2 : tunables    0    0    0 : slabdata   2209   2209      0
idr_layer_cache      285    285   2112   15    8 : tunables    0    0    0 : slabdata     19     19      0
dma-kmalloc-8192       0      0   8192    4    8 : tunables    0    0    0 : slabdata      0      0      0
dma-kmalloc-4096       0      0   4096    8    8 : tunables    0    0    0 : slabdata      0      0      0
dma-kmalloc-2048       0      0   2048   16    8 : tunables    0    0    0 : slabdata      0      0      0
dma-kmalloc-1024       0      0   1024   16    4 : tunables    0    0    0 : slabdata      0      0      0
dma-kmalloc-512        0      0    512   16    2 : tunables    0    0    0 : slabdata      0      0      0
dma-kmalloc-256        0      0    256   16    1 : tunables    0    0    0 : slabdata      0      0      0
dma-kmalloc-128        0      0    128   32    1 : tunables    0    0    0 : slabdata      0      0      0
dma-kmalloc-64         0      0     64   64    1 : tunables    0    0    0 : slabdata      0      0      0
dma-kmalloc-32         0      0     32  128    1 : tunables    0    0    0 : slabdata      0      0      0
dma-kmalloc-16         0      0     16  256    1 : tunables    0    0    0 : slabdata      0      0      0
dma-kmalloc-8          0      0      8  512    1 : tunables    0    0    0 : slabdata      0      0      0
dma-kmalloc-192        0      0    192   21    1 : tunables    0    0    0 : slabdata      0      0      0
dma-kmalloc-96         0      0     96   42    1 : tunables    0    0    0 : slabdata      0      0      0
kmalloc-8192          48     48   8192    4    8 : tunables    0    0    0 : slabdata     12     12      0
kmalloc-4096         413    432   4096    8    8 : tunables    0    0    0 : slabdata     54     54      0
kmalloc-2048         511    656   2048   16    8 : tunables    0    0    0 : slabdata     41     41      0
kmalloc-1024        1541   1744   1024   16    4 : tunables    0    0    0 : slabdata    109    109      0
kmalloc-512         1147   1232    512   16    2 : tunables    0    0    0 : slabdata     77     77      0
kmalloc-256         1837   2192    256   16    1 : tunables    0    0    0 : slabdata    137    137      0
kmalloc-192        11543  11550    192   21    1 : tunables    0    0    0 : slabdata    550    550      0
kmalloc-128         1792   2080    128   32    1 : tunables    0    0    0 : slabdata     65     65      0
kmalloc-96          2491   2604     96   42    1 : tunables    0    0    0 : slabdata     62     62      0
kmalloc-64         23476  24256     64   64    1 : tunables    0    0    0 : slabdata    379    379      0
kmalloc-32          1920   1920     32  128    1 : tunables    0    0    0 : slabdata     15     15      0
kmalloc-16          4864   4864     16  256    1 : tunables    0    0    0 : slabdata     19     19      0
kmalloc-8           4608   4608      8  512    1 : tunables    0    0    0 : slabdata      9      9      0
kmem_cache_node      192    192     64   64    1 : tunables    0    0    0 : slabdata      3      3      0
kmem_cache           112    112    256   16    1 : tunables    0    0    0 : slabdata      7      7      0
```
可以看到，系统中存在的 slab 有些形如 kmalloc-xxx 的 slab，我们称其为通用型 slab，用来满足分配通用内存。其它含有具体名字的 slab 我们称其为 专用 slab，用来为特定结构体分配内存，如 task_struct 等。

为什么要分专用和通用 slab ？ 最直观的一个原因就是通用 slab 会造成内存浪费：出于 slab 管理的方便，每个 slab 管理的对象大小都是一致的，当我们需要分配一个处于 64-96 字节中间大小的对象时，就必须从保存 96 字节的 slab 中分配。而对于专用的 slab，其管理的都是同一个结构体实例，申请一个就给一个恰好内存大小的对象，这就可以充分利用空间。

## 4. jemalloc
### 4.1 整体架构
jemalloc 是一种通用的内存管理方法， 着重于减少内存碎片和支持可伸缩的并发性。jemalloc 首次在 FreeBSD 中引入，后续增加了 heap profiling, Valgrind integration, and extensive monitoring/tuning hooks 等功能，目前在多个大型项目中都有应用。其整体结构如下图所示：
![jemalloc](/images/netty/jemalloc.jpg "jemalloc")

jemalloc 将申请的内存分为三个等级：small, large, huge.
1. Small objects 的 size 以 8, 16, 32, 64, 128, 256, 512 Bytes 分隔开，小于 page 大小；
2. Large objects的 size 以 page 为单位，等差间隔排列，小于 chunk 的大小； 
3. Huge objects的大小是 chunk 大小的整数倍。

small objects 和 large objects 由 arena 来管理， huge objects 由线程间公用的红黑树管理。对于64位操作系统，假设 chunk 大小为 4M，page 大小为 4K，内存等级分配如下：

| 分类  | 间隔   |   大小                                | 
| ----  | ----  |   ----                                |
| Small | 8	    |   [8]                                 |
| 	    | 16    |   [16, 32, 48, …, 128]                |
| 	    | 32    |   [160, 192, 224, 256]                |
|       | 64    |	[320, 384, 448, 512]                |
|       | 128   |	[640, 768, 896, 1024]               |
|       | 256	|   [1280, 1536, 1792, 2048]            |
|       | 512	|   [2560, 3072, 3584]                  |
| Large | 4 KiB |   [4 KiB, 8 KiB, 12 KiB, …, 4072 KiB] |
| Huge  | 4 MiB |	[4 MiB, 8 MiB, 12 MiB, …]           |

jemalloc 中有几个比较重要的对象，分别是：arena, chunk, bin, run 及 tcache.
1. arena: 为了减少线程间的竞争，jemalloc 将虚拟内存内存分为一定数量的 arenas。每个用户线程都会被绑定到一个 arena 上，线程采用 round-robin 轮询的方式选择可用的 arena 进行内存分配，默认每个 CPU 会分配 4 个 arena;
2. chunk: arena 由多个 chunk 组成，chunk 的大小为 2 的 k 次方，大于 page 大小。 chunk 的地址与 chunk 大小的整数倍对齐，这样可以通过指针操作在常量时间内找到分配 small/large objects 的元数据, 在对数时间内定位到分配 huge objects的元数据;
3. bin: bin 代表了相同大小对象的集合，在其大小范围内的对象就由它分配，Small objects 的分配就是通过 bin 分配的;
4. run: 每一个 bin 都维护一个红黑树，树结点便是 run 对象，用户分配的内存最终就是在 run 中分配。run 实际上就是 chunk 里的一块区域，大小是 page 的整数倍，在 run 的最开头会存储 run header 信息，存有 run 的元数据信息。run 中采用 bitmap 记录分配区域的状态， 相比采用空闲列表的方式， 采用 bitmap 具有以下优点：bitmap 能够快速计算出第一块空闲区域，且能很好的保证已分配区域的紧凑型。分配数据与应用数据是隔离的， 能够减少应用数据对分配数据的干扰，对很小的分配区域的支持更好。
5. tcache: tcache为线程对应的私有缓存空间， 用于减少线程分配内存时锁的争用， 提高内存分配的效率。如果使用 tcache 时, jemalloc 分配内存时将优先从 tcache 中分配， 只有在 tcache 中找不到才从 arena 中分配，每个 tcache 也会有一个对应的 arena, 在 tcache 内部包含一个 tbin 数组来缓存不同大小的内存块，与 arena 中的 bin 对应，用于存储用户对象。

用户内存的分配本质是对 chunk 的分配，用户对象存储在 chunk 中，chunk 目前的默认大小是 4M。chunk 以 page （默认为4K) 为单位进行管理，每个 chunk 的前几个page（默认是6个）用于存储 chunk 的元数据，后面跟着一个或多个 page 的 runs。后面的 runs 可以是未分配区域， 多个小对象组合在一起组成 run, 其元数据放在 run 的头部。 大对象构成的 run, 其元数据放在 chunk 的头部。最后，run 对象挂载到 bin 对象的红黑树上，通过 bin-->run-->chunk 的链路，实现对内存区域 chunk 的管理， 它们之间的关系如图所示：
![jemalloc_bin_chunk_run](/images/netty/jemalloc_bin_chunk_run.png "jemalloc_bin_chunk_run")

### 4.2 内存管理
jemalloc 采用多级内存分配，引入线程缓存 tcache, arena 来减少线程间锁的争用， 提高申请释放的效率和线程并发扩展性。我们先看下其分级结构：
![jemalloc_alloc_mem](/images/netty/jemalloc_alloc_mem.png "jemalloc_alloc_mem")

如图所示， jemalloc 的内存管理采用层级架构，分别是线程缓存 tcache, arena 和系统内存，不同大小的内存块对应不同的分配区。每个线程对应一tcache, 负责当前线程使用内存块的快速申请和释放， 避免线程间锁的竞争和同步。arena 的具体结构在前文已经提到，采用内存池的思想对内存区域进行合理的划分和管理，在有效保证低内存碎片的情况下实现不同大小内存块的高效管理。 system memory 是系统的内存区域。
1. small object: 当 jemalloc 支持 tcache 时， small object 的分配从 tcache 开始， tcache 不中则从 arena 申请 run 并将剩余区域缓存到 tcache， 若从 aren a中不能分配再从 system memory 中申请chunk 加入 arena 进行管理, 不支持 tcache 时， 则直接从 arena 中申请。
2. large object: 当 jemalloc 支持 tcache 时， 如果 large object 的 size 小于 tcache_maxclass，则从 tcache 开始分配， tcache 不中则从 arena 申请, 只申请需要的内存块， 不做多余 cache, 若从arena 中不能分配则从 system memory 中申请。当 large object 的 size 大于 tcache_maxclas s或者 jemmalloc 不支持 tcache 时， 直接从 arena 中申请。
3. huge object: huge object 的内存不归 arena 管理， 直接采用 mmap 从 system memory 中申请并由一棵与 arena 独立的红黑树进行管理。


## 5. 总结
这篇文章主要是对内存管理知识的一个整理，感谢参考文献中给出的文章，通过对这些文章的阅读，极大加深了操作系统内存管理相关的知识。

</br>

**参考：**

----
[1]:https://zhuanlan.zhihu.com/p/36140017
[2]:https://www.dingmos.com/2021/03/22/54.html
[3]:http://learn.lianglianglee.com/%E4%B8%93%E6%A0%8F/Netty%20%E6%A0%B8%E5%BF%83%E5%8E%9F%E7%90%86%E5%89%96%E6%9E%90%E4%B8%8E%20RPC%20%E5%AE%9E%E8%B7%B5-%E5%AE%8C/12%20%20%E4%BB%96%E5%B1%B1%E4%B9%8B%E7%9F%B3%EF%BC%9A%E9%AB%98%E6%80%A7%E8%83%BD%E5%86%85%E5%AD%98%E5%88%86%E9%85%8D%E5%99%A8%20jemalloc%20%E5%9F%BA%E6%9C%AC%E5%8E%9F%E7%90%86.md
[4]:https://engineering.fb.com/2011/01/03/core-data/scalable-memory-allocation-using-jemalloc/
[5]:https://brionas.github.io/2015/01/31/jemalloc%E6%BA%90%E7%A0%81%E8%A7%A3%E6%9E%90-%E6%A0%B8%E5%BF%83%E6%9E%B6%E6%9E%84/
[6]:https://brionas.github.io/2015/01/31/jemalloc%E6%BA%90%E7%A0%81%E8%A7%A3%E6%9E%90-%E5%86%85%E5%AD%98%E7%AE%A1%E7%90%86/

[1. Linux内核内存管理算法Buddy和Slab][1]

[2. Linux 内核 | 内存管理——slab 分配器][2]

[3. 他山之石：高性能内存分配器 jemalloc 基本原理][3]

[4. Scalable memory allocation using jemalloc][4]

[5. jemalloc源码解析-核心架构][5]

[6. jemalloc源码解析-内存管理][6]
