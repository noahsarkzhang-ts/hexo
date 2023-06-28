---
title: Memcached 内存模型
date: 2019-07-20 09:57:07
updated: 2019-07-20 09:57:07
tags:
- memcached
- slab
- chunk
- slabclass
categories: 
- 缓存
---
Memcached是一个基于内存的缓存系统，存储的是key/value的键值对，与Redis类似。不过相对于Redis，值是无类型的字节数组（类比于Reidis中的String类型）。在Reidis中构建了一个对象系统来存储键值对，Memcached内部是如何处理的？抱着这份好奇心来分析下Memcached的内存模型。

<!-- more -->

## 1. 整体结构
在开始之前，先说明一些概念：
1. item：存储key/value的数据结构，同时维护了hashtable、LRU链表的指针的信息，是数据的载体；
2. chunk：存放item，具有固定大小的内存块;
3. slab：是Memcached一次申请内存的最小单位，默认为1M，然后切分为chunk大小的内存块，是chunk的容器；
4. slabclass：是管理slab及chunk的数据结构，一个slabclass可分配多个slab，一个slab可分配多个chunk，同时一个slabclass中的chunk具有相同的大小；
5. slabclass []：管理多个slabclass，不同的slabclass成员管理不同大小的chunk（同一个slabclass中的chunk大小一样）；
6. LRU list: 管理各个slabclass的最近访问过的item, 以便进行item的清理，list头部是最近访问过的item，每一个slabclass都有一个LRU list；
7. hashtable: 用于item寻址，对key计算hash值，定位到item所在数组下标，再从item链表中找到对应的item。
8. slots list: slabclass中用于管理当前slabclass中空闲的item list。

下面是Memcached内存模型的整体结构：
![memory-model](/images/memcached-memory-model.jpg "memory-model")

1. slabclass中的slots字段指向空闲链表的头指点，通过item中的next及prev指针形成一个双向链表，新创建且未使用的item或过期释放的item会加入到该链表中；
2. 每一个slabclass都有个LRU list，可以从链表头部和尾部访问LRU链表，一旦item被分配出去，就将该item从空闲链表移到LRU链表中；
3. 一个item指针数组加上item链表构成了一个hashtable，item中的h_next字段指向冲突的下一个结点；
2. item是非常关键的数据结构，不仅存储了key/value数据，同时也作为hashtable，空闲链表及LRU链表中的元素，存放相关的指针信息。

## 2. 数据结构
### 2.1 slabclass

```c
typedef struct {
    unsigned int size;      /* item的大小*/
    unsigned int perslab;   /* 单个slab可存放的item的个数*/

    void *slots;            /* item空闲链表 */
    unsigned int sl_curr;   /* 当前位置*/

    unsigned int slabs;     /* 表示已经使用的slab_list的大小*/

    void **slab_list;       /* 分配的slab数组 */
    unsigned int list_size; /* 表示分配的slab_list的大小*/

    unsigned int killing;   /* 在进行slab reassign时使用*/
    size_t requested;       /* 此slabclass所占用的实际空间的大小*/
} slabclass_t;
```
**重点说明的字段：**
1. size&perslab：表示item的大小及一个slab包含item的数量；
2. slots：指向第一个空闲的item；
3. slab_list：分配的slab数组；

slabclass管理了一系列的slab，每一个slab又被切分为相同大小的chunk，而chunk存储最终的item，其关系如下图所示：
![slabclass](/images/memcached-slabclass.jpg "slabclass")

Memcached把slab分为40类（class1～class40），每一个类的slab在内部由一个slabclass数据结构来维护，在slabclass 1中，chunk的大小为96字节，一个slab的大小是固定的1M（1048576字节），因此在slabclass 1中最多可以有perslab = 10922个chunk：
```c
10922 × 80 + 64 = 1048576
```
在slabclass 1中，剩余的64字节因为不够一个chunk的大小（96byte），因此会被浪费掉。

每类chunk的大小有一定的计算公式，假定i代表分类，class i的计算公式如下：
```c
chunk size(class i) = (default_size + item_size) * f^(i-1) + CHUNK_ALIGN_BYTES
```
1. default_size：默认大小为48字节,也就是Memcached默认的key+value的大小为48字节，启动时可以使用-n参数来调节其大小；
2. item_size：item结构体的长度，固定为48字节。default_size大小为48字节,item_size为48字节，因此slabclass 1的chunk大小为48+48=96字节；
3. f：f为factor，是chunk变化大小的因素，默认值为1.25，调节f可以影响chunk的步进大小，启动时可以使用-f参数来指定;
4. CHUNK_ALIGN_BYTES：CHUNK_ALIGN_BYTES是一个修正值，用来保证chunk的大小是某个值的整数倍（在32位机器上要求chunk的大小是4的整数倍）。

Memcached分配内存的时候, 根据请求内存块的大小, 找到大小最合适的chunk所在的 slabclass, 然后从这个slabclass找空闲的chunk分配出去. 所谓最合适就是指chunk 的大小能够满足要求, 而且碎片最小。

### 2.2 item
```c
typedef struct _stritem {
    struct _stritem *next;      /* 指向LRU list或空闲列表中的下一个item */
    struct _stritem *prev;      /* 指向在LRU list或空闲列表中的上一个item*/
    struct _stritem *h_next;    /* 指向此Hashtable中的下一个item*/
    rel_time_t      time;       /* 最近的访问时间*/
    rel_time_t      exptime;    /* 过期时间*/
    int             nbytes;     /* 数据的长度*/
    unsigned short  refcount;   /* 引用次数*/
    uint8_t         nsuffix;    /* 标志及长度的后辍串的长度*/
    uint8_t         it_flags;   /* ITEM的状态 */
    uint8_t         slabs_clsid;/* 位于的slabclass的id */
    uint8_t         nkey;       /* key的长度*/
    union {
        uint64_t cas;
        char end;
    } data[];

    /* 如果启用cas则在结构尾部接8byte的cas数，即uint64_t*/
    /* 然后是1byte的终止符\0 */
    /* then " flags length\r\n" (no terminating null) */
    /* then data with terminating \r\n (no terminating null; it's binary!) */
} item;
```
**重点说明的字段：**
1. 指针：next,prev用于LRU list及空闲列表，而h_next指向相同哈希值的下一个item；
2. 时间：time,exptime记录了最近访问的时间及过期的时间；
3. 数据长度：nbytes,nkey分别记录了数据的长度及key的长度，nkey的数据类型为uint8_t,决定了key的最大长度为256(8位无符号整数的最大值)；而数据的最大长度由一个slab的值决定，即1M。
4. data：存储的数据，包括四个部分：cas(可行) + key + suffix + value，整体的结构如下图所示：
![item](/images/memcached-item.jpg "item")

### 2.3 hashtable
```c
static item** primary_hashtable = 0;        //main hashtable
```
hashtable由两部分组成：item哈希数组+item链表，其中primary_hashtable便是哈希数组，根据key计算哈希值，从而快速定位到key所在数组中的index；为了解决key冲突的问题，引入了链表，将冲突的key用链表连接起来，如在整体结构图中所示：item4与item5具有相同的index，用h_next串连起来。
### 2.4 LRU list
```c
//LRU list
static item *heads[LARGEST_ID];   //指向各slabclass的LRU链表的head结点
static item *tails[LARGEST_ID];   //指向各slabclass的LRU链表的tail结点
```
 当Memcached没有足够的内存使用时,根据LRU算法回收item, 这就需要维护一个按照最近访问时间排序的LRU 队列。 在Memcached 中,每个slabclass 维护一个链表, 比如 slabclass[i]的链表头指针为heads[i], 尾指针为tails[i],已分配出去的item都存储在链表中。而且链表中item按照最近访问时间排序, 这相当于一个LRU 队列。

 ## 3. 内存分配
结合数据模型，对slab及item的使用做一下总结：
1. 初始化slabclass数组，每个元素slabclass[i]都是不同size的slabclass；
2. 每分配一个新的slab，都会根据所在的slabclass的size来切分chunk，切分完chunk之后，把chunk空间初始化成一个个free item，并插入到slot链表中；
3. 每使用一个free item都会从slot链表中删除掉并插入到LRU链表相应的位置；
4. 每当一个used item被访问的时候都会更新它在LRU链表中的位置，以保证LRU链表从尾到头淘汰的权重是由高到低的；
5. 会有另一个叫“item爬虫”的线程慢慢地从LRU链表中去爬，把过期的item淘汰掉然后重新插入到slot链表中；
6. 当进行内存分配时，例如一个SET命令，它的一般步骤是：
    1. 计算出要保存的数据的大小，选择相应的slabclass；
    2. 从相应的slabclass LRU链表的尾部开始，尝试找几次（默认是5次），看看有没有过期的item，如果有就利用这个过期的item空间；
    3. 如果没找到过期的，则尝试去slot链表中拿空闲的free item；
    4. 如果slot链表中没有空闲的free item了，尝试申请内存，分配一块新的slab，分配成功后，slot链表就有可用的free item了，返回可用的free item.
    5. 如果分配不了新的slab那说明内存都已经满了，用完了，只能淘汰，所以用LRU链表尾部找出一个item并将其淘汰，返回该item。

## 4. 总结
在Memcached的内存模型中，没有为hashtable及LRU list定义单独的数据结构，而是和slabclass共用了item，分配和释放item的时候只需要修改相应的指针，整体结构比较紧凑，有效利用了内存空间。

**参考：**

----
[1]:http://yaowhat.com/2014/10/02/memcached-memory-manage.html
[2]:https://www.zybuluo.com/phper/note/443547
[3]:http://calixwu.com/2014/11/memcached-yuanmafenxi-neicunguanli.html
[4]:https://kenby.iteye.com/blog/1423989

[1.memcached系列二——内存模型][1]

[2.彻底弄清楚memcached][2]

[3.Memcached源码分析之内存管理][3]

[4.Memcached源码分析之内存管理篇][4]
