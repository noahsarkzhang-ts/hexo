---
title: Redis 数据结构
date: 2019-07-07 17:59:05
updated: 2019-07-07 17:59:05
tags:
- redis
- 数据结构
categories: 
- 缓存
---

Redis中有丰富的数据结构，如简单动态字符串、链表、字典、跳跃表、整数集合及压缩列表，基于这些数据结构，封装了一套对象系统，供用户使用，这篇文章主要是对这些数据结构进行了一个总结及加深理解。

<!-- more -->

## 1.简单动态字符串（Simple Dynamic String,SDS）
### 1.1 作用
SDS在Redis中用来表示字符串结构。
### 1.2 定义
结构如下
```c
struct sdshdr {
    
    // 记录buf数组的长度，即保存字符串的长度
    int len;

    // 记录buf数组中空闲的字节数量
    int free; 

    // 字节数组，用于保存字符串
    char buf[];
}
```

### 1.3 实例
![sds](/images/sds.jpg "SDS")
- len：值为5，表示保存了5个字节长度的内容；
- free：值为5，表示这个SDS有5个字节的未分配的空间；
- buf：char类型的数组，最后一个字节存储了空字符'\0'，表示字符串结尾，这种做法遵循了C语言的规则，所以实际的长度应该是len+1，只不过系统帮我们添加了空字符。

### 1.4 内存分配机制
通过未使用空间，SDS通过空间预分配和惰性空间释放两种机制来优化内存的使用。
#### 1.4.1 空间预分配
- 初始是按需分配，len为实际长度，free为零；
- 需要修改SDS时，如果SDS的长度（len的值）小于1MB，那么Redis分配和len同样大小的未使用空间，即free=len；如果SDS的长度大于等于1MB，那么将会分配1MB的未使用空间，即free=1MB。

#### 1.4.2 惰性空间释放
惰性空间释放用于SDS字符串缩短时，Redis不会释放多余的剩余空间，字符串会从头开始存储，将剩余的未使用空间的长度存放到free字段。

### 1.5 特点
- 常数复杂度获取字符串长度；
- 使用长度len字段，杜绝缓冲区溢出；
- 使用free字段，结合内存预分配策略，可以减少内存分配次数；
- buf是字节数组，可以安全存放任何二进制数据，不局限于字符串；
- buf数组中会插入空字符'\0'，可以部分兼容C字符串函数。

## 2. 链表
### 2.1 作用
List对象的一种底层实现（List也可以用压缩列表实现）。
### 2.2 定义
链表节点结构如下：
```c
typedef struct listNode
{
    // 前置结点
    struct listNode *prev;

    // 后置结点
    struct listNode *next;

    // 节点的值
    void *value;
 } listNode;
```

这是一个典型的双向链表结点的定义，可以实现向前、向后查找。

链表定义如下：
```c
typedef struct list {
    // 头结点
    listNode *head;

    // 尾结点
    listNode *tail;

    // 节点数量
    unsigned long len;

    // 节点复制函数
    void *(*dup) (void *ptr);

    // 节点释放函数
    void *(*free) (void *ptr);

    // 节点对比函数
    int (*match) (void *ptr,void *key);
} list;
```

链表定义了表头指针head、表尾指针tail及节点数量len，同时定义了三个函数指针，实现节点的复制、释放及对比功能。

### 2.3 实例
 ![list](/images/list.jpg "list")
上图是有3个结点的链表示意图

## 3. 字典
### 3.1 作用
作为Redis字典对象的一种底层实现。
### 3.2 定义
字典底层是基于哈希表来实现的。
#### 3.2.1 哈希表
1. 哈希节点
```c
typedef struct dictEntry {
    // 键
    void *key;

    // 值
    union 
    {
        void * val;
        uint64_t u64;
        int64_t s64;
    } v;
    
    // 指向下一个哈希结点，相同哈希值的key,value组成一个链表
    struct dictEntry *next;
} dictEntry;
```

key字段保存着键值对中的键，而v字段键值对中的值，其值可以是一个指针，或者是一个uint64_t整数，又或者是一个int64_t整数。

2. 哈希表
```c
typedef struct dictht {
    // 哈希表数组
    dictEntry **table;

    // 哈希表大小
    unsigned long size;

    // 哈希表大小掩码，用于计算索引值
    // 等于size-1
    unsigned long sizemask;

    // 节点的数量
    unsigned long used;
} dictht;
```

哈希表实际上就是一个数组+链表的实现，具有相同哈希值的键值对放在同一个链表里面，解决键冲突的问题。

#### 3.2.2 字典
```c
typedef struct dict {
    // 类型特定函数
    dictType *type;

    // 私有数据
    void *privdata;

    // 哈希表
    dicht ht[2];

    // rehash索引
    int trehashidx;
} dict;
```

字典中有两个哈希表，ht[0]一个用于存放正常状态下的键值对，另外ht[1]一个主要用于哈希表调整大小（rehash）时，存放rehash后的键值对。rehash结束之后，将ht[0]指向新的哈希表，ht[1]赋值为null。
dictType字段指向了一组针对特定键值对类型的处理函数，通过这种方式，可以实现面向对象语言的多态特性，dictType定义如下：
```c
typedef struct dictType {

    // 计算哈希值的函数
    unsigned int (*hashFunction)(const void *key);

    // 复制键的函数
    void *(*keyDup)(void *privdata, const void *key);

    // 复制值的函数
    void *(*valDup)(void *privdata, const void *obj);

    // 对比键的函数
    int (*keyCompare)(void *privdata, const void *key1, const void *key2);

    // 销毁键的函数
    void (*keyDestructor)(void *privdata, void *key);

    // 销毁值的函数
    void (*valDestructor)(void *privdata, void *obj);

} dictType;
```

### 3.3 实例
 ![list](/images/dict.jpg "list") 

## 4. 跳跃表
### 4.1 作用
跳跃表（skiplist）是一种有序的数据结构，它通过在每一个节点中维持多个指向其他结点的指针，从而达到快速访问节点的目的。跳跃表支持平均O(logN)，最坏O(N)复杂度的节点查找，还可以通过顺序操作来批量节点。
在大部分情况下，跳跃表的效率可以和平衡树相媲美，并且因为跳跃表的实现比平衡树更简单，所以不少程序使用跳跃表来代替平衡树。
Redis使用跳跃表作为有序集合键的底层实现之一，如果一个有序集合包含的元素数量比较多，又或者有序集合中元素的成员是比较长的字符串时，Redis就会使用跳跃表来作为有序集合键的底层实现。

### 4.2 定义
#### 4.2.1 跳跃表结点
```c
typedef struct zskiplistNode {
    // 后退指针
    struct zskiplistNode *backword;

    // 分值
    double score;

    // 成员对象
    robj *obj;

    // 层
    struct zskiplistLevel {
        // 前进指针
        struct zskiplistNode *forward;

        // 跨度
        unsigned int span;

    } level[];

} zskiplistNode;
```
1. 层：跳跃表节点的level数组可以包含多个元素，每一个元素都包含一个指向其它结点的指针，程序通过这些层为加快访问其它结点的速度，一般来说，层的数量越多，访问其它结点的速度就越快。
每次创建一个新结点的时候，Redis都根据冥次定律（power law,越大的数出现的概念越小）随机生成一个介于1和32之间的值作为level分组的大小，这个大小就是层的“高度”。
2. 前进指针：每个层都有一个指向表尾方向的前进指针，用于从表头向表尾方向访问结点。
3. 跨度：用于记录两个节点间的距离。
4. 后退指针：用于从表尾向表头方向访问结点。
5. 分值和成员：节点的分值是一个double类型的浮点数，跳跃表中所有节点都按分值从小到大来排序。节点成员对象是一个指针，它指向一个字符串对象，而字符串则保存着一个SDS值。

#### 4.2.2 跳跃表
zskiplist结构的定义如下：
```c
typedef struct zskiplist {

    // 表头结点
    struct zskiplistNode *header;

    // 表尾结点
    struct zskiplistNode *tail;

    // 节点的数量
    unsigned long length;

    // 结点中最大层数
    int level;
} zskiplist;
```

### 4.3 实例
 ![skiplist](/images/skiplist.jpg "skiplist") 
注：箭头上的数字表示跨度。

## 5. 整数集合
### 5.1 作用
整数集合（intset）是集合键的底层实现之一，当一个集合只包含整数值元素，且这个集合的元素数量不多时，Redis就会使用整数集合作为集合键的底层实现。
### 5.2 定义
```c
typedef struct intset {
    // 编码方式
    uint32_t encoding;

    // 元素的数量
    uint32_t length;

    // 保存元素的数组
    int8_t contents[];
} intset;
```
1. encoding：表示存储的整数类型，有int16_t,int32_t和int64_t，即16位、32位及64位的有符号整数。
2. length：表示元素的数量。
3. contents：字节数组，根据encoding的值使用不同的字节数来表示整数，如：int16_t使用2字节，int32_t使用4字节，int64_t使用8字节，另外，contents同时只会存储一种类型的整数。

### 5.3 实例
  ![intset](/images/intset.jpg "intset") 
一个包含5个16位有符号整数值的整数集合

### 5.4 升级
当新增加一个元素到整数集合中时，如果新元素的值超出了当前类型的范围时，就要对整数集合进行升级操作，执行的步骤如下:
1. 根据新元素的类型，扩展contents数组（分配一个新数组），并为新元素分配空间；
2. 将之前的数组元素转换为新元素的类型，并放置在数组中合适的位置上，保持元素的顺序不变；
3. 将新元素添加到数组里面。

### 5.5 降级
整数集合不支持降级操作，一旦对数组进行了升级，编码就会保持升级后的状态。
 
## 6. 压缩列表
### 6.1 作用
压缩列表（ziplist）是列表键和哈希键的底层实现之一。当一个列表键只包含少量列表项，且每个列表项要么是小整数值，要么是长度比较短的字符串，那么Redis就使用压缩列表做列表键的底层实现。
另外，当一个哈希键只包含少量键值对，且每个键值对的键和值要么是小整数值，要么是长度比较短的字符串，那么Redis就会使用压缩列表来做哈希键的底层实现。
### 6.2 定义
Redis官方对于ziplist的定义是：
> The ziplist is a specially encoded dually linked list that is designed to be very memory efficient. It stores both strings and integer values, where integers are encoded as actual integers instead of a series of characters. It allows push and pop operations on either side of the list in O(1) time.

ziplist是一个经过特殊编码的双向链表，它的设计目标就是为了提高存储效率。ziplist可以用于存储字符串或整数，其中整数是按真正的二进制表示进行编码的，而不是编码成字符串序列。它能以O(1)的时间复杂度在表的两端提供push和pop操作。
ziplist的数据类型，没有使用结构体struct来表达，就是简单的unsigned char *。这是因为ziplist本质上就是一块连续内存，内部组成结构又是一个高度动态的设计（变长编码），也没法用一个固定的数据结构来表达。
一个压缩列表可以包含任意多个节点（entry），每个节点可以保存一个字节数组或者一个整数值，其结构如下：

1. zlbytes: 32bit，表示ziplist表占用的字节总数（也包括zlbytes本身占用的4个字节）；
2. zltail: 32bit，表示ziplist表中最后一项（entry）在ziplist中的偏移字节数。zltail的存在，使得可以很方便地找到最后一项（不用遍历整个ziplist），从而可以在ziplist尾端快速地执行push或pop操作；
3. zllen: 16bit， 表示ziplist中数据项（entry）的个数。zllen字段因为只有16bit，所以可以表达的最大值为2^16-1。这里需要特别注意的是，如果ziplist中数据项个数超过了16bit能表达的最大值，ziplist仍然可以来表示。那怎么表示呢？这里做了这样的规定：如果zllen小于等于2^16-2（也就是不等于2^16-1），那么zllen就表示ziplist中数据项的个数；否则，也就是zllen等于16bit全为1的情况，那么zllen就不表示数据项个数了，这时候要想知道ziplist中数据项总数，那么必须对ziplist从头到尾遍历各个数据项，才能计算出来；
4. entry: 表示真正存放数据的数据项，长度不定。一个数据项（entry）也有它自己的内部结构；
5. zlend: ziplist最后1个字节，是一个结束标记，值固定等于FF(255)。

#### 6.2.1 压缩列表结点
**1.previous_entry_length**

它有两种可能，要么是1个字节，要么是5个字节：
1）如果前一个数据项占用字节数小于254，那么previous_entry_length就只用一个字节来表示，这个字节的值就是前一个数据项的占用字节数。

2）如果前一个数据项占用字节数大于等于254，那么previous_entry_length就用5个字节来表示，其中第1个字节的值是254（作为这种情况的一个标记），而后面4个字节组成一个整型值，来真正存储前一个数据项的占用字节数。

**2. encoding**

根据第1个字节的不同，总共分为9种情况，前3种是存储字符串，后6种是存储整数：

1）|00pppppp| - 1 byte：第1个字节最高两个bit是00，那么encoding字段只有1个字节，剩余的6个bit用来表示长度值，最高可以表示63 (2^6-1)；
2）|01pppppp|qqqqqqqq| - 2 bytes：第1个字节最高两个bit是01，那么encoding字段占2个字节，总共有14个bit用来表示长度值，最高可以表示16383 (2^14-1)；

3）|10__|qqqqqqqq|rrrrrrrr|ssssssss|tttttttt| - 5 bytes：第1个字节最高两个bit是10，那么encoding字段占5个字节，总共使用32个bit来表示长度值（6个bit舍弃不用），最高可以表示2^32-1。需要注意的是：在前三种情况下，content都是按字符串来存储的；

4）|11000000| - 1 byte：encoding字段占用1个字节，值为0xC0，后面的数据content存储为2个字节的int16_t类型；

5）|11010000| - 1 byte：encoding字段占用1个字节，值为0xD0，后面的数据content存储为4个字节的int32_t类型；

6）|11100000| - 1 byte：encoding字段占用1个字节，值为0xE0，后面的数据content存储为8个字节的int64_t类型；

7）|11110000| - 1 byte：encoding字段占用1个字节，值为0xF0，后面的数据content存储为3个字节长的整数；

8）|11111110| - 1 byte：encoding字段占用1个字节，值为0xFE，后面的数据content存储为1个字节的整数；

9）|1111xxxx| - - (xxxx的值在0001和1101之间)：这是一种特殊情况，xxxx从1到13一共13个值，这时就用这13个值来表示真正的数据。注意，这里是表示真正的数据，而不是数据长度。也就是说，在这种情况下，后面不再需要一个单独的content字段来表示真正的数据了，而是encoding和content合二为一。

### 6.3 连锁更新
每一节点的previous_entry_length属性都记录了前一节点的长度：
- 如果前一个节点的长度小于254字节，那么previous_entry_length需要用1个字节来保存长度值；
- 如果前一个节点的长度大于等于254字节，那么previous_entry_length需要用5个字节业保存长度值。
如果压缩列表里只好有多个连续的、长度介于250字节至253字节之间的节点，在添加或删除结点时，可能会引发连锁更新，即引起多次的空间扩展操作。

### 6.4 实例
![ziplist](/images/ziplist.jpg "ziplist") 

**参考：**

----
[1]:http://zhangtielei.com/posts/blog-redis-ziplist.html

1.Redis设计与实现

[2.Redis内部数据结构详解(4)——ziplist][1]

