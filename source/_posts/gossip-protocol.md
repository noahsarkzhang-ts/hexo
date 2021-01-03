---
title: Gossip 协议
date: 2020-11-29 17:15:14
tags:
- Gossip
- 一致性算法
- 共识算法
categories: 
- 一致性算法
---

## 1. 概述
在一致性算法中，Raft 及 Paxos 是强一致性的算法，属于 CP（一致性及分区容错性） 的使用场景，为了保证算法的准确性，必须保证大部分节点（服务器）是正常的（三个节点容忍一个节点失败）。但在 AP （可用性及分区容错性）场景中，即使只有少数机器的存在，仍然可以对外提供服务，这些场景包括：失败检测、路由同步、Pub/Sub 及动态负载均衡。而 Gossip 协议就是这样一种支持最终一致性算法的协议。

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




## 5. 总结

**参考：**

----
[1]:https://time.geekbang.org/
[2]:https://segmentfault.com/a/1190000022957348
[3]:https://www.cnblogs.com/charlieroro/articles/12655967.html
[4]:https://www.sofastack.tech/blog/sofa-jraft-election-mechanism/
[5]:https://github.com/baidu/braft/blob/master/docs/cn/raft_protocol.md
[6]:https://www.sofastack.tech/blog/sofa-jraft-linear-consistent-read-implementation/
[7]:https://www.sofastack.tech/blog/sofa-jraft-deep-dive/
[8]:https://github.com/hedengcheng/tech/blob/master/distributed/PaxosRaft%20%E5%88%86%E5%B8%83%E5%BC%8F%E4%B8%80%E8%87%B4%E6%80%A7%E7%AE%97%E6%B3%95%E5%8E%9F%E7%90%86%E5%89%96%E6%9E%90%E5%8F%8A%E5%85%B6%E5%9C%A8%E5%AE%9E%E6%88%98%E4%B8%AD%E7%9A%84%E5%BA%94%E7%94%A8.pdf


[1. Gossip协议：流言蜚语，原来也可以实现一致性][1]
[2. 漫谈 Gossip 协议][2]
[3. Gossip是什么][3]
[4. SOFAJRaft 选举机制剖析 | SOFAJRaft 实现原理][4]
[5. RAFT介绍][5]
[6. SOFAJRaft 线性一致读实现剖析 | SOFAJRaft 实现原理][6]
[7. 蚂蚁金服开源 SOFAJRaft 详解| 生产级高性能 Java 实现][7]
[8. PaxosRaft 分布式一致性算法原理剖析及其在实战中的应用.pdf][8]


