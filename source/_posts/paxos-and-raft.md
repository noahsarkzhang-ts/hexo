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
 
Paxos 协议分为两个阶段：
1、第一阶段 Prepare

P1a：Proposer 发送 Prepare

Proposer 生成全局唯一且递增的提案 ID（Proposalid，以高位时间戳 + 低位机器 IP 可以保证唯一性和递增性），向 Paxos 集群的所有机器发送 PrepareRequest，这里无需携带提案内容，只携带 Proposalid 即可。



P1b：Acceptor 应答 Prepare
Acceptor 收到 PrepareRequest 后，做出“两个承诺，一个应答”。



两个承诺：

第一，不再应答 Proposalid 小于等于（注意：这里是 <= ）当前请求的 PrepareRequest；

第二，不再应答 Proposalid 小于（注意：这里是 < ）当前请求的 AcceptRequest



一个应答：

返回自己已经 Accept 过的提案中 ProposalID 最大的那个提案的内容，如果没有则返回空值;



注意：这“两个承诺”中，蕴含两个要点：



就是应答当前请求前，也要按照“两个承诺”检查是否会违背之前处理 PrepareRequest 时做出的承诺；

应答前要在本地持久化当前 Propsalid。




2、第二阶段 Accept

P2a：Proposer 发送 Accept
“提案生成规则”：Proposer 收集到多数派应答的 PrepareResponse 后，从中选择proposalid最大的提案内容，作为要发起 Accept 的提案，如果这个提案为空值，则可以自己随意决定提案内容。然后携带上当前 Proposalid，向 Paxos 集群的所有机器发送 AccpetRequest。


P2b：Acceptor 应答 Accept

Accpetor 收到 AccpetRequest 后，检查不违背自己之前作出的“两个承诺”情况下，持久化当前 Proposalid 和提案内容。最后 Proposer 收集到多数派应答的 AcceptResponse 后，形成决议。

### 2.2 Multi-Paxos

## 3. raft

## 4. raft实现

## 5. 总结


