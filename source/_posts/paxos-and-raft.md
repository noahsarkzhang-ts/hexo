---
title: Paxos 和 Raft 算法
date: 2020-11-08 16:31:26
tags:
- paxos
- raft
- 一致性算法
- 共识算法
categories: 
- 一致性算法
---

## 1. 概述
在分布式系统中，一个核心的问题就是解决数据一致性的问题，即共识问题（多副本共识问题）：
> Consensus Problem : Requires agreement among a number of processes (or agents) for a single data value.

共识问题简单来说，就是多个进程（代理）就某个单值达成一致，主要的应用场景数据多副本的复制。而 Paxos 及 Raft 算法的提出便是为了解决共识问题，它们在工程实现上得到了广泛的应用，如 Goggle 的 Chubby、Apache 的 ZooKeeper 及 Raft算法实现 Etcd。这些算法都可以统称为一致性算法。

![paxos-evolution](/images/consensus-algorithm/paxos-evolution.jpg "paxos-evolution")

一致性算法大概可以分为4个类型：
1. Basic-Paxos : 提供就一个提案达成一致的算法，是最基本的算法，在工程实践中很少使用该算法；
2. Multi-Paxos : 在 Basic-Paxos 算法的基础上，提供了就一批提案达成一致的算法，在工程中有很多类似的实现；
3. Raft : 针对 Multi-Paxos 算法难于理解及实现复杂，提供了一种简化的实现；
4. Multi-Raft : 为了提供更大的并发请求量，可以将单个 Raft 集群进行分区，提供更大的集群规模。


这篇文章就四种类型的算法进行一个概要的分析，更多的是逻辑概念层面，不会对细节及实现过多讨论，那也超出本人的认知。

## 2. Paxos
Paxos 算法解决的问题是一个分布式系统如何就某个值（提案）达成一致。一个典型的场景是，在一个分布式数据库系统中，如果各节点的初始状态一致，每个节点都执行相同的操作序列，那么他们最后能得到一个一致的状态。为保证每个节点执行相同的命令序列，需要在每一条指令上执行一个“一致性算法”以保证每个节点看到的指令一致，是分布式计算中的重要问题。

### 2.1 Basic-Paxos
在 Paxos 算法中，服务器分为三种角色：
1. Proposers：提案（value）发起者，接收客户端请求；
2. Acceptors：接收提案（value）进行决策，存储 accept 的提案（value）；
3. Learners：不参与决策，从 Proposers 和 Acceptors 学习最新达成一致的提案（value）。
由于 Learners 不参与决策，暂不讨论。
 
Paxos 算法分为两个阶段，为什么使用两个阶段，可以参考这篇文章：[一步一步理解Paxos算法](https://mp.weixin.qq.com/s?__biz=MjM5MDg2NjIyMA==&mid=203607654&idx=1&sn=bfe71374fbca7ec5adf31bd3500ab95a&key=8ea74966bf01cfb6684dc066454e04bb5194d780db67f87b55480b52800238c2dfae323218ee8645f0c094e607ea7e6f&ascene=1&uin=MjA1MDk3Njk1&devicetype=webwx&version=70000001&pass_ticket=2ivcW%2FcENyzkz%2FGjIaPDdMzzf%2Bberd36%2FR3FYecikmo%3D)

**Paxos 协议分为两个阶段：**
1. 第一阶段 Prepare：
    - Proposer 生成全局唯一且递增的提案 ID （ProposalId），向 Paxos 集群的所有机器发送 PrepareRequest，这里无需携带提案内容，只携带 ProposalId 即可。Acceptor 收到  PrepareRequest 后，做出“两个承诺，一个应答”。
    - 两个承诺主要是指：
        - 不再应答 ProposalId 小于等于（注意：这里是 <= ）当前请求的 PrepareRequest；
        - 不再应答 ProposalId 小于（注意：这里是 < ）当前请求的 AcceptRequest。
    - 一个应答主要是指：
    返回自己已经 Accept 过的提案中 ProposalID 最大的那个提案的内容，如果没有则返回空值;


2. 第二阶段 Accept：
    - P2a：Proposer 发送 Accept
    “提案生成规则”：Proposer 收集到多数派应答的 PrepareResponse 后，从中选择 ProposalId 最大的提案内容，作为要发起 Accept 的提案，如果这个提案为空值，则可以自己随意决定提案内容。然后携带上当前 ProposalId，向 Paxos 集群的所有机器发送 AccpetRequest。

    - P2b：Acceptor 应答 Accept
    Accpetor 收到 AccpetRequest 后，检查不违背自己之前作出的“两个承诺”情况下，持久化当前 ProposalId 和提案内容。最后 Proposer 收集到多数派应答的 AcceptResponse 后，形成决议。

在执行上面两个步骤之后，实际上后续还有一个步骤。在实际应用中，如使用 Paxos 算法的 KV 系统，上述两个步骤只是完成了日志在不同系统的提交，对于一个写操作，还需要将写操作提交到背后的存储结构中，这个操作往往是异步操作。

在 Paxos 两个阶段中隐含了两个规则：
1. 喜新厌旧：在第一阶段中，更大的 ProposalId 会抢占比它小的提案，前提是还没有 ProposalId 被 Accept；
2. 后者认同前者：在第二阶段中，如果提案还没有被 Accept，则提交自己新的 Proposal，如果已经提案已经被 Accept，则使用旧的提案内容进行提交。

在第一个规则中，要保证新的 ProposalId 比之前的 ProposalId 大，包含两层意思，1） 同一个 Proposer 生成的 ProposalId 是自增的；2）不同 Proposer 生成的 ProposalId 要要求是自增。正常会使用如下的方案：
假设有 n 个proposer，每个编号为ir (0 <= ir < n)，Proposor 编号的任何值 s 都应该大于它已知的最大值，并且满足：s %n = ir => s = m*n + ir。

Basic-Paxos 算法如下图所示：
![paxos-algorithem](/images/consensus-algorithm/paxos-algorithem.jpg "paxos-algorithem")

在算法中，必须持久化存储 minProposal, acceptedProposal,和 acceptedValue 三个变量。

Basic-Paxos 实例 1：
![paxos-example-1](/images/consensus-algorithm/paxos-example-1.jpg "paxos-example-1")
说明：
Proposal ID：round number(3), server id(1)，即 Proposal ID = 3.1 ，其中 3 代表轮数，1 代表 服务器编号。
P 3.1达成多数派，其 Value(X) 被 Accept，然后P 4.5学习到 Value(X)，并Accept。

实例 2：
![paxos-example-2](/images/consensus-algorithm/paxos-example-2.jpg "paxos-example-2")
P 3.1没有被多数派Accept（只有S3 Accept），但是被P 4.5学习到，P 4.5 将自己的Value 由 Y 替换为 X，Accept（X）

实例 3：
![paxos-example-3](/images/consensus-algorithm/paxos-example-3.jpg "paxos-example-3")
P 3.1 没有被多数派Accept（只有S1 Accept），同时也没有被 P 4.5学习到。由于P 4.5 Propose的所有应答，均未返回 Value，则 P 4.5 可以Accept 自己的Value（Y）。
后续 P 3.1的Accept（X）会失败，已经 Accept 的 S1，会被覆盖。

Basic-Paxos 存在一个活锁，如下图所示：
![liveness-lock](/images/consensus-algorithm/liveness-lock.jpg "liveness-lock")
两个Proposers交替Propose成功，Accept失败，形成活锁（Livelock）

### 2.2 Multi-Paxos
如果想确定一个确定，一个值，Basic-Paxos 就可以实现了。如果想确定连续多个提案，确定连续多个值，Basic-Paxos 算法就搞不定了，就要使用 Multi-Paxos。如下图所示：



## 3. Raft

## 4. Raft实现

## 5. 总结


**参考：**

----
[1]:https://mp.weixin.qq.com/s?__biz=MzAwMDU1MTE1OQ==&mid=403582309&idx=1&sn=80c006f4e84a8af35dc8e9654f018ace&scene=1&srcid=0119gtt2MOru0Jz4DHA3Rzqy&key=710a5d99946419d927f6d5cd845dc9a72ff3d652a8e66f0ddf87d91262fd262f61f63660690d2d5da76a44a29e155610&ascene=0&uin=MjA1MDk3Njk1&devicetype=iMac+MacBookPro11%2C4+OSX+OSX+10.11.1+build(15B42)&version=11020201&pass_ticket=bhstP11nRHvorVXvQ4pt9fzB9Vdzj5sSRBe84783gsg%3D
[2]:https://mp.weixin.qq.com/s?__biz=MjM5MDg2NjIyMA==&mid=203607654&idx=1&sn=bfe71374fbca7ec5adf31bd3500ab95a&key=8ea74966bf01cfb6684dc066454e04bb5194d780db67f87b55480b52800238c2dfae323218ee8645f0c094e607ea7e6f&ascene=1&uin=MjA1MDk3Njk1&devicetype=webwx&version=70000001&pass_ticket=2ivcW%2FcENyzkz%2FGjIaPDdMzzf%2Bberd36%2FR3FYecikmo%3D
[3]:https://mp.weixin.qq.com/s/bjM3uEDg61vhNN8Y661L7w
[4]:https://blog.csdn.net/dog250/article/details/50528373
[5]:https://my.oschina.net/alchemystar/blog/3008840
[6]:https://blog.csdn.net/russell_tao/article/details/17119729
[7]:https://blog.nowcoder.net/n/dade4d8c53d144dfa78157887e2cb33e
[8]:https://zhuanlan.zhihu.com/p/60713292

[1. 架构师需要了解的Paxos原理、历程及实战][1]
[2. 一步一步理解Paxos算法][2]
[3. Linux select/poll机制原理分析][3]
[4. Linux内核中网络数据包的接收-第二部分 select/poll/epoll][4]
[5. 从linux源码看epoll][5]
[6. 高性能网络编程5--IO复用与并发编程][6]
[7. epoll源码分析][7]
[8. 带您进入内核开发的大门 | 内核中的等待队列][8]