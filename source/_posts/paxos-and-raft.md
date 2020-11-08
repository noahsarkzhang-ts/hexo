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
在分布式系统中，一致性算法主要解决数据多副本共识问题，我们先看下什么是共识问题：
> Consensus Problem : Requires agreement among a number of processes (or agents) for a single data value.

共识问题简单来说，就是多个进程（代理）就某个单值达成一致，主要的应用场景数据多副本的复制，而 Paxos 及 Raft 算法的提出便是为了解决共识问题，在工程实现上得到了广泛的应用，如 Goggle 的 Chubby、Apache 的 ZooKeeper 及 Raft算法实现 Etcd。

这篇文章的内容主要侧重在对算法的理解上，不会对细节及实现过多讨论，那也超出本人的认知。

## 2. Paxos

### 2.1 Basic-Paxos
Paxos 协议：Paxos 协议是一个解决分布式系统中，多个节点之间就某个值（提案）达成一致（决议）的通信协议。它能够处理在少数派离线的情况下，剩余的多数派节点仍然能够达成一致。
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


