---
title: Redis对象系统
date: 2019-07-13 13:29:41
tags:
- redis
- redisObject
- 空转时长
categories: 
- redis
---
Redis使用对象来表示数据库中的键和值，每当在Redis中新建一个键值对，至少会创建两个对象，一个对象用作键（键对象），一个用作值（值对象）。本篇文章主要是对Redis的对象系统做一个笔记。

## 对象定义
在Redis中对象的定义如下：
```c
typedef struct redisObject {

    // 类型
    unsigned type:4;

    // 编码
    unsigned encoding:4;

    // 指向底层的数据结构
    void *ptr;

    // 引用计数
    int refcount;

    // 最后一次程序访问的时间
    unsigned lru:22

} robj;
```

### 类型
type属性记录了对象的类型，有五种对象类型，分别是字符串对象、列表对象、哈希对象、集合对象和有序集合对象,可以在键上使用TYPE命令查看键的类型，如果一个键是字符串类型，用命令查看如下所示:

```bash
redis> TYPE msg
string
```

type属性的值及命令输出对应如下表所示：

|  对象   | type属性对应的值  | TYPE命令输出  |
|  ---------  | ------------ |------------ |
| 字符串对象   | REDIS_STRING | string |
| 列表对象  | REDIS_LIST |list |
| 哈希对象  |  REDIS_HASH|hash |
| 集合对象  | REDIS_SET |set |
|有序集合对象  |  REDIS_ZSET |zset |

### 编码和实现
对于一种对象，根据不同的使用场景可以有不同的底层数据结构来实现，不同的实现由encoding属性来表示，可以使用OBJECT ENCODING命令查看一个键值对值的编码，如果一个值是REDIS_ENCODING_EMBSTR，其输出如下所示：
```bash
redis> OBJECT ENCODING msg
"embstr"
```

encoding取值范围及代表的数据结构如下所示：

|  encoding取值范围   | 代表的数据结构  | OBJECT ENCODING命令输出  |
|  ---------  | ------------ |------------ |
| REDIS_ENCODING_INT   | long类型的整数 |int |
| REDIS_ENCODING_EMBSTR | embstr编码的简单的动态字符串 |embstr |
| REDIS_ENCODING_RAW  | 简单动态字符串|raw |
| REDIS_ENCODING_HT  | 字典 |hashtable |
|REDIS_ENCODING_LINKEDLIST  |  双向链表 |linkedlist |
| REDIS_ENCODING_ZIPLIST   | 压缩列表 |ziplist |
| REDIS_ENCODING_INTSET   | 整数集合 |intset |
| REDIS_ENCODING_SKIPLIST   | 跳跃表和字典|skiplist |

在Redis中有五种对象，每一种对象根据不同的使用场景可以有不同的数据结构来实现，类型type和编码encoding的关系对应如下表所示：

| type  | encoding  |对象  |
| ------------ |------------ |------------ |
| REDIS_STRING | REDIS_ENCODING_INT |使用整数值实现的字符串对象 |
| REDIS_STRING | REDIS_ENCODING_EMBSTR |使用embstr编码实现的SDS字符串对象 |
| REDIS_STRING | REDIS_ENCODING_RAW |SDS字符串对象 |
| REDIS_LIST |REDIS_ENCODING_LINKEDLIST |使用双向链表实现的列表对象 |
| REDIS_LIST |REDIS_ENCODING_ZIPLIST |使用压缩列表实现的列表对象 |
| REDIS_HASH|REDIS_ENCODING_HT |使用字典实现的哈希对象 |
| REDIS_HASH|REDIS_ENCODING_ZIPLIST |使用压缩列表实现的哈希对象 |
| REDIS_SET |REDIS_ENCODING_INTSET |使用整数集合实现的集合对象 |
| REDIS_SET |REDIS_ENCODING_HT |使用字典实现的集合对象 |
| REDIS_ZSET |REDIS_ENCODING_ZIPLIST |使用压缩列表实现的有序集合对象 |
| REDIS_ZSET |REDIS_ENCODING_SKIPLIST |使用跳跃表和字典实现的有序集合对象 |

### 引用计数
Redis在对象系统中构建了一个基于引用计数的内存回收机制，通过这个机制，在每一个对象的refcount属性中记录引用计数信息，Redis可以通过跟踪对象的这些引用计数信息，在适当的时候自动释放对象并进行内存回收。
对象的引用计数信息会随着对象的使用状态而不断变化：
- 在创建一个新对象时，引用计数的值会被初始化为1；
- 当一个对象被引用时，它的引用计数值为加1；
- 当一个对象被解除引用时，它的引用计数值为减1；
- 当对象的引用计数值变为0时，对象会被释放。

可以使用OBJECT REFCOUNT命令查看一个键对应的值被引用的次数，如下所示：
```bash
redis> OBJECT REFCOUNT key
(integer) 2
```

### 对象的空转时长
redisObject中的lru属性记录了该对象最后一次被访问的时间，可以使用OBJECT IDLETIME命令打印给定键的空转时长，这个空转时长是通过当前时间减去键的值对象的lru时间计算出来的，单位为钞（S），命令如下所示：
```bash
redis> OBJECT IDLETIME msg
(integer) 10
```
键的空转时长还有另外一个作用：如果Redis打开了maxmemory选项，并且服务器内存回收算法为volatile-lru或allkeys-lru，那么当服务器占用的内存超过了maxmemory选项所设置的上限值时，空转时长较高的那部分键会被优先释放，从而回收内存。

## 字符串对象
字符串对象的编码可以是int、embstr或者raw。
### int编码的字符串
如果一个字符串对象保存的是整数值，并且这个整数值可以用long类型来表示，那么字符串对象中的ptr将指向一个long类型的地址，如下图所示：
![string-int](/images/string-int.jpg "string-int")

### raw编码的字符串
如果字符串对象保存的是一个字符串值，并且这个字符串值的长度大于39个字节，那么字符串对象将使用简单字符串（SDS）来保存这个字符串值，如下图所示：
![string-raw](/images/string-raw.jpg "string-raw")

### embstr编码的字符串
如果字符串对象保存的是一个字符串值，并且这个字符串值的长度小于等于39个字节，那么字符串对象将使用embstr编码的方式保存这个字符串值。
embstr编码是专门用于保存短字符串的一种优化编码方式，这种编码和raw编码都使用sdshdr结构来保存字符串，区别主要在于内存分配：embstr编码会将redisobject和sdshdr作为一个整体，一次性分配相邻的空间来保存这两个对象，而raw编码则使用两次。embstr编码的内存结构如下所示：
![string-embstr](/images/string-embstr.jpg "string-embstr")

### double类型的字符串
double类型的浮点数在Redis中是作为字符串保存的。如果要保存一个浮点数到字符串对象里面，Redis首先将这个浮点数转换成字符串，然后再保存到字符串对象中，编码可以是embstr或者raw。

### 编码转换
int编码的字符串对象和embstr编码的字符串对象在条件满足的情况下，会被转换为raw编码的字符串对象。
#### int-->raw
如果对int编码的字符串对象执行了一些命令，使得这个对象保存的不再是整数值，而是一个字符串，那么字符串对象的编码将从int变为raw。

#### ebmstr-->raw
ebmstr编码的字符串对象是只读的，如果要对该对象进行修改操作，则会将embstr编码的字符串对象转换为raw编码的字符串对象。

## 列表对象
列表对象的编码可以是ziplist或者linkedlist。
### ziplist编码的列表对象
ziplist编码的列表对象使用压缩列表作为底层实现，每一个压缩列表结点（entry）保存了一个列表对象。
### linkedlist编码的列表对象
linkedlist编码的列表对象使用双向链表作为底层实现，每一个双向链表结点（node）都保存了一个字符串对象，而每一个字符串对象都保存了一个列表元素。

### 编码转换
当列表对象同时满足以下两个条件时，列表对象使用ziplist编码：
1. 列表对象保存的所有字符串元素的长度都小于64字节；
2. 列表对象保存的元素数量小于512个。

不能满足这两个条件的列表对象需要使用linkedlist编码。

**注：list-max-ziplist-value和list-max-ziplist-entries两个选项可以修改上面两个值。**

对于使用ziplist编码的列表对象来说，当使用ziplist编码所需的两个条件的任意一个不能被满足时，就会进行编码的转换，将ziplist转换为linkedlist。

## 哈希对象
哈希对象的编码可以是ziplist或者hashtable。

### ziplist编码的哈希对象
ziplist编码的哈希对象使用压缩列表作为底层实现，每当有新的键值对加入到哈希对象时，Redis依次将键结点、值结点推入到压缩列表表尾。

### hashtable编码的哈希对象
hashtable编码的哈希对象使用字典作为底层实现，哈希对象的键值都分别是一个字符串对象。

### 编码转换
当哈希对象同时满足以下条件时，哈希对象使用ziplist编码：
1. 哈希对象保存的所有键值的字符串长度长度都小于64字节；
2. 哈希对象保存的键值对数量小于512个。

不能满足这两个条件的哈希对象需要使hashtable编码。

**注：hash-max-ziplist-value和hash-max-ziplist-entries两个选项可以修改上面两个值。**

对于使用ziplist编码的哈希对象来说，当使用ziplist编码所需的两个条件的任意一个不能被满足时，就会进行编码的转换，将ziplist转换为hashtable。

## 集合对象
集合对象的编码可以是intset或者hashtable。
### intset编码的集合对象
intset编码的集合对象使用整数集合作为底层实现，集合对象包含的所有元素都是整数。
### hashtable编码的集合对象
hashtable编码的集合对象使用字典作为底层实现，字典的每一个键都是一个字符串对象，保存了集合元素，而字典的值全部设置为NULL。

### 编码转换
当集合对象同时满足以下条件时，集合对象使用intset编码：
1. 集合对象保存的所有元素都是整数值；
2. 集合对象保存的元素数量小于512个。

不能满足这两个条件的集合对象需要使hashtable编码。

**注：第二个条件是要可以通过set-max-intset-entries选项进行修改。**

对于使用intset编码的集合对象来说，当使用intset编码所需的两个条件的任意一个不能被满足时，就会进行编码的转换，将intset转换为hashtable。

## 有序集合对象
有序集合的编码可以是ziplist或者skiplist。
### ziplist编码的有序集合对象
ziplist编码的有序集合对象使用压缩列表作为底层实现，每个集合元素使用两个紧挨在一起的压缩列表结点来保存，第一个结点保存元素的成员（member），第二个结点则保存元素的分值（score）。
压缩列表的集合元素按分值从小到大进行排序，分值较小的元素被放置在靠近表头的位置，而分值较大的元素则被放置表尾的位置。

### skiplist编码的有序集合对象
skiplis编码的有序集合对象使用zset结构来作为底层实现，一个zset结构同时包含一个字典和一个跳跃表，其结构如下所示：
```c
typedef struct zset {
    
    // 跳跃表
    zskiplist *zsl;

    // 字典
    dict *dict;
} zset;
```
zset结构中的zsl跳跃表按分值从小到大保存了所有集合元素，每个跳跃表结点保存了一个集合元素：object属性保存了元素的成员，score保存了元素的分值；
zset结构中的dict字典为有序集合创建一个成员到分值的映射，字典中的每个键值对保存了一个元素：字典的键保存了元素的成员，而字典的值则保存了分值。

使用跳跃表和字典来实现有序集合，可以充分两者的优点：
1. 通过跳跃表，可以O(NlogN)时间复杂度的范围查询；
2. 通过字典，可以O(1)时间复杂度的查找元素成员。

### 编码转换
当有序集合对象同时满足以下条件时，集合对象使用ziplist编码：
1. 有序集合对象保存的元素数量小于128个；
2. 有序集合对象保存的所有元素的长度都小于64个字节。

不能满足这两个条件的有序集合对象需要使skiplist编码。

**注：zset-max-ziplist-value和zset-max-ziplist-entries两个选项可以修改上面两个值。**

对于使用ziplist编码的有序集合对象来说，当使用ziplist编码所需的两个条件的任意一个不能被满足时，就会进行编码的转换，将ziplist转换为skiplist。

## 字符串和整数
Redis作为一个键值对数据库，构建了五种对象类型，原始类型如字符串和整数和对象类型的关系如下：
1. 字符串和整数存放在字符串对象，整数集合和压缩列表中；
2. 在列表对象（linkedlist）、哈希对象（hashtable）和集合对象（hashtable）和有序集合对象（skiplist）中不直接存储字符串和整数，而是存储字符串对象。

## Redis存储效率
Redis数据库的整体结构如下图所示，为了方便描述，将字符串对象、哈希对象及列表对象进行的简化。

![redis-server](/images/redis-server.jpg "redis-server")

一个Redis服务器默认有16个数据库（DB），每个DB实际就是一个键值数据库，底层的数据结构是字典（dict），所有的数据都以键值对存储在dict中，其中键是一个字符串对象，而值可以是五种Redis对象中任意一种，即字符串对象、列表对象、哈希对象、集合对象及有序集合对象。

下面以一个字符串键值对为例来分析Redis的存储效率，即有效存储空间与所占空间的比率：
```bash
redis> SET message "Hello Redis"
```
根据上图所示，增加一个新的字符串键值对需要增加如下对象：
1. 两个字符串对象；
2. 一个字典结点对象，message及值就存储在这个结点中。

如下图所示：

![dict-node](/images/dict-node.jpg "dict-node")

### 字符串对象 

字符串对象的内存结构如下所示：

![redis-object](/images/redis-object.jpg "redis-object")

message字符串对象：12 + 12 + 7 + 1 = 32字节

值对象：12 + 12 + 11 + 1 = 36字节

其中前两个12字节分别是redisObject和sdshdr结构体所占的空间，而最后1字节是'\0'空字符。

### 字典结点对象

字典结点对象的内存结构如下所示：

![dictEntry](/images/dictEntry.jpg "dictEntry")

dictEntry：4 + 4 + 4 = 12字节

### 存储效率
存储一个字符串键值对需要额外的空间为：25 + 25 + 12 = 62字节
存储效率：(7 + 11) / (7 + 11 + 62) = 22.5%


**参考：**

----
[1]:http://zhangtielei.com/posts/blog-redis-ziplist.html

1.Redis设计与实现

