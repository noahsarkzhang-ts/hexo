---
title: Gossip 协议
date: 2020-11-29 17:15:14
tags:
- Gossip
- 一致性算法
- 故障检测
- Redis Cluster
categories: 
- 一致性算法
---

## 1. 概述
在一致性算法中，Raft 及 Paxos 是强一致性的算法，属于 CP（一致性及分区容错性） 的使用场景，为了保证算法的准确性，必须保证大部分节点（服务器）是正常的（三个节点容忍一个节点失败）。但在 AP （可用性及分区容错性）场景中，即使只有少数机器的存在，仍然可以对外提供服务，这些场景包括：失败检测、路由同步、Pub/Sub 及动态负载均衡。而 Gossip 协议就是这样一种支持最终一致性算法的协议。

<!-- more -->

## 2. Gossip 协议
Gossip 协议，顾名思义，就像流言蜚语一样，利用一种随机、带有传染性的方式，将信息传播到整个网络中，并在一定时间内，使得系统内的所有节点数据一致。相对于 Raft 来说，数据的一致性收敛是随机且滞后的，但提高了系统的可用性。

在一些分类中，将 Gossip 协议分为三类，分别是：
1. 直接邮寄（Direct Mail）：数据的变更直接由数据源结点复制给目标结点，不通过中间结点；
2. 反熵（Anti-entropy）：反熵指的是集群中的节点，每隔段时间就随机选择某个其他节点，然后通过互相交换自己的所有数据来消除两者之间的差异，实现数据的最终一致性：
3. 谣言传播（Rumor mongering）：它指是当一个节点有了新数据后，这个节点变成活跃状态，并周期性地联系其他节点向其发送新数据，直到所有的节点都存储了该新数据：

相比较而言，反熵需要拷贝全量数据进行比对，会消耗较大的网络带宽及性能，优势是数据可以在相对确定的时间内达成一致；而谣言传播周期性地进行部分增量数据的传播，占用网络带宽较少，具备较好的性能，缺点也是显然的，数据的收敛时间不确定。后面我们将 Gossip 协议特指谣言传播，重点说明谣言传播算法。

### 2.1 基本原理
Gossip协议 基本思想就是：一个节点想要分享一些信息给网络中的其他的一些节点。于是，它周期性的随机选择一些节点，并把信息传递给这些节点。这些收到信息的节点接下来会做同样的事情，即把这些信息传递给其他一些随机选择的节点。一般而言，信息会周期性的传递给 n 个目标节点，而不只是一个，如下图所示：
![gossip](/images/consensus-algorithm/gosssip.gif "gossip")

**容错性**
Gossip 协议具备失败容错的能力，即使节点之间没有直接相连，也可以通过其它结点传播信息；

**收敛时间**
Gossip 协议周期性随机选择 n 个结点进行消息的广播，集群中所有结点收到广播的时间是不确定的，虽然可以保证数据最终都可以收到，但收到的时候没有办法预估。可以通过另外一种办法来评估收敛的时间，即通过广播的轮数。它的计算方式如下：
![gossip-convergence.jpg](/images/consensus-algorithm/gossip-convergence.jpg "gossip-convergence.jpg")

排除传播过程中有可能重复的结点，20 个结点的集群进行三轮的广播之后就可要以将数据传播到集群中的所有结点。

## 3. 使用场景

## 4. Gossip 在 Redis 中的使用 
Redis Cluster 在 3.0 版本引入集群功能。为了让让集群中的每个实例都知道其它所有实例的状态信息，Redis 集群规定各个实例之间按照 Gossip 协议来通信传递信息。
![redis-cluster](/images/consensus-algorithm/redis-cluster.jpg "redis-cluster")

Redis Cluster 中的每个节点都维护一份集群相关的信息，主要包括：
1. 当前集群状态；
2. 集群中各节点所负责的 slots 信息及其 migrate 状态；
3. 集群中各节点的 master-slave 状态; 
4. 集群中各节点的存活状态及怀疑 Fail 状态。

Gossip 协议的主要职责就是信息交换，这些信息包括上面所说的内容。信息交换的载体就是节点彼此发送的 Gossip 消息，常用的 Gossip 消息可分为：ping 消息、pong 消息、meet 消息、fail 消息。

1. meet 消息：用于通知新节点加入。消息发送者通知接收者加入到当前集群，meet 消息通信正常完成后，接收节点会加入到集群中并进行周期性的ping、pong 消息交换；
2. ping 消息：集群内交换最频繁的消息，集群内每个节点每秒向多个其它节点发送 ping 消息，用于检测节点是否在线和交换彼此状态信息。ping 消息发送封装了自身节点和部分其它节点的状态数据；
3. pong 消息：当接收到 ping、meet 消息时，作为响应消息回复给发送方确认消息正常通信。pong消息内部封装了自身状态数据。节点也可以向集群内广播自身的 pon g消息来通知整个集群对自身状态进行更新；
4. fail 消息：当节点判定集群内另一个节点下线时，会向集群内广播一个 fail 消息，其他节点接收到 fail 消息之后把对应节点更新为下线状态。

### 4.1 消息体
一个 Gossip 协议消息常常包括一个 clusterMsg + n 个 clusterMsgData，clusterMsg 当前结点的信息，包括主从信息及本结点的 slots 信息。clusterMsgData 根据消息类型的不同表示为不同的数据结构，后面进到。消息的结构下图所示：
![redis-clusterMsg](/images/consensus-algorithm/redis-clusterMsg.jpg "redis-clusterMsg")

clusterMsg 结构如下所示：

```c
typedef struct {
    char sig[4];        /* Signature "RCmb" (Redis Cluster message bus). */
    uint32_t totlen;    /* Total length of this message */
    uint16_t ver;       /* Protocol version, currently set to 1. */
    uint16_t port;      /* TCP base port number. */
    uint16_t type;      /* Message type */
    uint16_t count;     /* Only used for some kind of messages. */
    uint64_t currentEpoch;  /* The epoch accordingly to the sending node. */
    uint64_t configEpoch;   /* The config epoch if it's a master, or the last
                               epoch advertised by its master if it is a
                               slave. */
    uint64_t offset;    /* Master replication offset if node is a master or
                           processed replication offset if node is a slave. */
    char sender[CLUSTER_NAMELEN]; /* Name of the sender node */
    unsigned char myslots[CLUSTER_SLOTS/8];  /* 本结点的 slot 信息 */
    char slaveof[CLUSTER_NAMELEN];
    char myip[NET_IP_STR_LEN];    /* Sender IP, if not all zeroed. */
    char notused1[34];  /* 34 bytes reserved for future usage. */
    uint16_t cport;      /* Sender TCP cluster bus port */
    uint16_t flags;      /* Sender node flags */
    unsigned char state; /* Cluster state from the POV of the sender */
    unsigned char mflags[3]; /* Message flags: CLUSTERMSG_FLAG[012]_... */
    union clusterMsgData data;
} clusterMsg;
```

如果是 PING, MEET and PONG 消息的话，clusterMsgData 发送的是一个 clusterMsgDataGossip 数组，clusterMsgDataGossip 描述了一个结点的简要信息，包括了结点的状态，其中就包括疑似下线结点的状态。如果是 FAIL 消息，则发送的是 clusterMsgDataFail 数据，clusterMsgDataFail 只包含一个字段，即下线结点的名字。

```c
union clusterMsgData {
    /* PING, MEET and PONG */
    struct {
        /* Array of N clusterMsgDataGossip structures */
        clusterMsgDataGossip gossip[1];
    } ping;

    /* FAIL */
    struct {
        clusterMsgDataFail about;
    } fail;

    /* PUBLISH */
    struct {
        clusterMsgDataPublish msg;
    } publish;

    /* UPDATE */
    struct {
        clusterMsgDataUpdate nodecfg;
    } update;

    /* MODULE */
    struct {
        clusterMsgModule msg;
    } module;
};

```
clusterMsgDataGossip 结构体包括了一个结点的基本信息，其中 pong_received 字段记录了该结点最近一次发送 pong 消息的时间，flags 状态记录了结点的状态，疑似下线状态就是由这个标志来记录的。

```c
/* Initially we don't know our "name", but we'll find it once we connect
 * to the first node, using the getsockname() function. Then we'll use this
 * address for all the next messages. */
typedef struct {
    char nodename[CLUSTER_NAMELEN];
    uint32_t ping_sent;
    uint32_t pong_received;
    char ip[NET_IP_STR_LEN];  /* IP address last time it was seen */
    uint16_t port;              /* base port last time it was seen */
    uint16_t cport;             /* cluster port last time it was seen */
    uint16_t flags;             /* node->flags copy */
    uint32_t notused1;
} clusterMsgDataGossip;

```

clusterMsgDataFail 结构体只包括了结点的名称，相对比较简单。

```c
typedef struct {
    char nodename[CLUSTER_NAMELEN];
} clusterMsgDataFail;
```

### 4.2 消息传播
Redis cluser 通过以下的方式进行消息的传播：
1. 每 1 S 从 5 个随机结点中选择一个最久未发送 Pong 消息的结点发送　Ping 消息。发送的消息中包括当前结点的信息及多个随机结点的简要信息和状态消息；收到消息的结点，回复一个 Pong 消息；
2. 每 100 MS 扫描一遍所有结点，比较结点上次发送 Pong 消息的时间到当前时间的时长，如果这个时长大于集群超时时间的 1/2，则立即发送 Ping 信息，避免在第一步中有结点长期未被选中的情况发生。

这个流程如下图代码所示：
![redis-clusterCron](/images/consensus-algorithm/redis-clusterCron.jpg "redis-clusterCron")

一个消息体包括发送结点本身的信息，同时会随机选择多个结点的状态信息，结点的数量小于总结点数的 1/10，这其中包括正常的结点和疑似下线的结点，流程如下所示：
![redis-clusterSendPing](/images/consensus-algorithm/redis-clusterSendPing.jpg "redis-clusterSendPing")

### 4.2 故障检测
1. 下线检测：集群中的每个节点都会定期向集群中的其它节点发送 Ping 消息，用于检测对方是否在线，如果接收 Ping 消息的节点没有在规定的时间收到响应的 Ping 消息，那么，发送 Ping 消息的节点就会将接收 Ping 消息的节点标注为疑似下线状态（Probable Fail，Pfail）；
2. 状态传递：集群中的各个节点会通过相互发送 Ping 消息的方式来交换自己掌握的集群中各个节点的状态信息，如在线、疑似下线（Pfail）、下线（fail）。如果一个结点检测到另外一结点疑似下线，该结点会将疑似下线结点的状态通过 Ping 消息传播给集群中其它结点，其它结点收到消息会更新其结点的状态；
3. 下线判定：如果在一个集群里，超过半数的持有 slot(槽) 的主节点都将某个主节点 A 报告为疑似下线，那么，主节点 A 将被标记为下线（fail），检测到 A 结点下线的主结点广播一条 A 下线的 Fail 消息，所有收到这条 Fail 消息的节点都会立即将主节点 A 标记为 fail。至此，故障检测完成。

## 5. 总结
Gossip 协议在 AP 场景及结点数量频繁变化的场景下，具有较大的优势，但是随着结点数量的增加，消息通信的成本也就更高，因此对于Redis集群来说并不是越大越好。

**参考：**

----
[1]:https://time.geekbang.org/
[2]:https://segmentfault.com/a/1190000022957348
[3]:https://www.cnblogs.com/charlieroro/articles/12655967.html
[4]:https://blog.csdn.net/Jin_Kwok/article/details/90111631
[5]:https://segmentfault.com/a/1190000038373546

[1. Gossip协议：流言蜚语，原来也可以实现一致性][1]
[2. 漫谈 Gossip 协议][2]
[3. Gossip是什么][3]
[4. 第三章：深入浅出理解分布式一致性协议Gossip和Redis集群原理][4]
[5. 一万字详解 Redis Cluster Gossip 协议][5]


