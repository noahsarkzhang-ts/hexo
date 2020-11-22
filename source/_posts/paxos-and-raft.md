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

Basic-Paxos 存在一个活锁的问题，如下图所示：
![liveness-lock](/images/consensus-algorithm/liveness-lock.jpg "liveness-lock")
两个Proposers交替Propose成功，Accept失败，形成活锁（Livelock）

## 3. Multi-Paxos
如果想确定一个确定，一个值，Basic-Paxos 就可以实现了。如果想确定连续多个提案，确定连续多个值，Basic-Paxos 算法就搞不定了，就要使用 Multi-Paxos。如下图所示：
![multi-paxos](/images/consensus-algorithm/multi-paxos.jpg "multi-paxos")

Multi-Paxos 就是对每一个 Paxos Instance 执行一次 Paxos 算法，确保每一台服务器上的数据都是一致的。

Multi-Paxos 有如下一些缺点：
1. 比较复杂，难以理解，工程实现难度比较大；
2. 每一个服务器都可以执行写操作，性能较差。

为了解决 Multi-Paxos 的缺点，在算法中引入了 Leader 的角色，所有的决议都通过 Leader 来进行，然后同步到其它服务器，其结构如下图所示：
![multi-paxos-2](/images/consensus-algorithm/multi-paxos-2.jpg "multi-paxos-2")

通过 Consensus Module， 完成多个连续的提案的确定，通过日志同步到各个服务器，保证服务器以相同的顺序执行，使得服务器的状态保持一致。其中，Raft 算法便是 Multi-Paxos 算法的一个实现版本。

## 4. Raft
Raft 通过选举一个 Leader，然后让它负责日志的复制来实现一致性。Leader 从客户端接收日志条目，把日志条目复制到其它服务器上，并且当保证安全性的时候告诉其它服务器应用日志条目到他们的状态机中。拥有一个 Leader 大大简化了对复制日志的管理。例如，Leader 可以决定新的日志条目需要放在日志中的什么位置而不需要和其他服务器商议，并且数据只从 Leader 流向其他服务器。一个 Leader 可以宕机，可以和其他服务器失去连接，这时一个新的 Leader 会被选举出来。

通过 Leader 的方式，Raft 将一致性问题分解成了三个相对独立的子问题：
1. Leader 选举：当现存的 Leader 宕机的时候，一个新的 Leader 需要被选举出来；
2. 日志复制：Leader 必须从客户端接收日志然后复制到集群中的其他节点，并且强制要求其它节点的日志保持和自己相同；
3. 安全性：如果有任何的服务器节点已经应用了一个确定的日志条目到它的状态机中，那么其它服务器节点不能在同一个日志索引位置应用一个不同的指令。

### 4.1 基本概念
**Server状态：**

在任何时刻，每一个服务器节点都处于这三个状态之一：Leader 、Follower 或者 Candidate。在通常情况下，系统中只有一个 Leader 并且其它的节点全部都是 Follower。Follower 都是被动的：它们不会发送任何请求，只是简单的响应来自 Leader 或者 Candidate 的请求。Leader 处理所有的客户端请求（如果一个客户端和 Leader 联系，那么 Follower 会把请求重定向给 Leader）。第三种状态，Candiate，是用来在选举新 Leader 时使用。下图展示了这些状态和它们之间的转换关系。

![raft_server_state](/images/consensus-algorithm/raft_server_state.png "raft_server_state")
- Leader : 处理客户端的请求以及日志复制；
- Follower : 接收来自 Leader 或者 Canditate 的 Message，并响应；
- Candidate : 用于选主的中间状态。

**Term：**
Raft 把时间分割成任意长度的任期，如下图所示，任期用连续的整数标记。每一段任期从一次选举开始，一个或者多个 Candidate 尝试成为 Leader。如果一个 Candidate 赢得选举，然后它就在接下来的任期内充当 Leader 的职责。在某些情况下，一次选举过程会造成选票的瓜分。在这种情况下，这一任期会以没有 Leader 结束；一个新的任期（和一次新的选举）会很快重新开始。Raft 保证了在一个给定的任期内，最多只有一个 Leader。
![raft_term](/images/consensus-algorithm/raft-term.png "raft_term")

**Message类型：**
Raft 算法中服务器节点之间通信使用远程过程调用（RPCs），并且基本的一致性算法只需要两种类型的 RPCs。请求投票（RequestVote） RPCs ，由 Candidate 在选举期间发起，然后追加条目（AppendEntries）RPCs 由Leader 发起，用来复制日志和提供一种心跳机制。安装快照 (InstallSnapshot）在新服务器启动时或者 Follower 落后太多日志时使用。

### 4.2 Leader 选择
Raft 使用心跳机制来触发 Leader 选举。当服务器程序启动时，他们都是 Follower 身份。只要从 Leader 或者 Candidate 处接收到有效的 AppendEntries RPC， 一个服务器节点继续保持着 Folllowr 状态。Leader 周期性的向所有 Follower 发送心跳包（即不包含日志项内容的追加日志项 RPCs）来维持自己的权威。如果一个 Follower 在一段时间里没有接收到任何消息，也就是选举超时，那么他就会认为系统中没有可用的 Leader,并且发起选举以选出新的 Leader。
要开始一次选举过程，Follower 先要增加自己的当前任期号并且转换到 Candidate 状态。然后它会并行的向集群中的其他服务器节点发送请求投票的 RPCs 来给自己投票。如果一个 Candidate 从整个集群的大多数服务器节点获得了针对同一个任期号的选票，那么它就赢得了这次选举并成为 Leader。每一个服务器最多会对一个任期号投出一张选票，按照先来先服务的原则，并且确保 Candidate 的日志比服务器更新。要求大多数选票的规则确保了最多只会有一个 Candidate 赢得此次选举，要求 Candidate 的日志最新，确保日志只从 Leader 流向 Follower。一旦候选人赢得选举，它就立即成为领导人。然后他它会向其他的服务器发送心跳消息来建立自己的权威并且阻止新的 Leader 的产生。

![raft-election](/images/consensus-algorithm/raft-election.jpg "raft-election")

一个 Candidate 获得集群中多数服务器的选票，并不代表真正获得了 Leader，因为它只完成了类似 Basic-Paxos的 Prepare阶段，此时它还需要向集群中的服务器发送 AppendEntries RPC，阻止其它服务器发起选主请求，其它服务器收到该 RPC 之后，将自己的状态转化为 Follower。
在Basic-Paxos 中存在活锁的问题，在 Raft 选主中也同样存在，即多个 Candidate 同时对同一个 Term 发起选主请求，选票会被多个 Candidate 瓜分，为了避免这个问题，Raft 为每一个 Candidate 选择一个随机选主超时时间，可以有效避免这种情况，即使发生这种情况，因为没有一个 Candidate 获得多数选票，等待超时时间之后，将触发下一轮的选主，而下一轮的触发的时间也是随机的。
在选主的操作中，只有那些包含更新更多日志的 Candiate 才有机会获得选票，这主要是通过比较 LastLogIndex 和 LastLogTerm 来实现的。通过这种方式，Raft 简化了后续日志复制的过程，保证了日志只会由 Leader 流向 Follower。

通过以上的方式，保证了选主的安全性：<strong style="color:red">对于一个给定的任期号，最多只会有一个领导人被选举出来。</strong>

### 4.3 日志复制
一旦一个 Leader 被选举出来，它就开始为客户端提供服务。客户端的每一个请求都包含一条被状态机执行的指令。Leader 把这条指令作为一条新的日志条目附加到日志中去，然后并行的发起追加条目 RPCs 给其他的服务器，让它们复制这条日志条目。当这条日志条目被安全的复制并回复 ACK 给Leader ，Leader 会应用这条日志条目到它的状态机中然后把执行的结果返回给客户端。如果少数派的 Follower 崩溃或者运行缓慢，再或者网络丢包，Leader 人会不断的重复尝试追加日志条目 RPCs （尽管已经回复了客户端）直到所有的 Follower 都最终存储了所有的日志条目。
![raft-log](/images/consensus-algorithm/raft-log.png "raft-log")

每一个 Log Entry 由有序序号标记的条目组成。每个条目都包含创建时的任期号，和一个状态机需要执行的指令。当一个条目复制到多数派的服务器上时就被认为已提交 (Committed) 状态了。
![raft-log-format](/images/consensus-algorithm/raft-log-format.jpg "raft-log-format")

当日志被多数派服务器持久化之后就成为 Committed 状态，应用到状态机之后变为 Applied，正常情况下，一旦日志成为 Committed 状态之后，就不允许撤消。一个未被多数派持久化的日志有可能被撤消。
![raft-log-state](/images/consensus-algorithm/raft-log-state.jpg "raft-log-state")

Leader 决定什么时候将日志应用给状态机是安全的，Raft 保证 Committed Entries 持久化，并且最终被其它状态机应用。一个 Log Entry 一旦复制给了大多数节点就成为 Committed。同时还有一种情况，如果当前待提交 Entry 之前有未提交的 Entry，即使是以前过时的 Leader 创建的，只要满足已存储在大多数节点上就一次性按顺序都提交。Leader 要追踪最新的 Committed 的 index，并在每次AppendEntries RPCs（包括心跳）都要带给其它服务器，以使其它服务器知道一个 Log Entry是已提交的，从而在它们本地的状态机上也应用。
![raft-log-flow](/images/consensus-algorithm/raft-log-flow.jpg "raft-log-flow")
从上图可以知道，日志的 Commited 状态由 Leader 来决定，并在下一次的 AppendEntries RPC 中由 leaderCommit 字段传递给 Follower。正常情况下，在返回客户端之前，日志会应用到 Leader 的状态机中，而 Follower 什么时候将日志应用到状态机，是一个异步操作，会滞后于 Leader。所以 Leader 状态机中持有最新的数据。

**日志修复**
一个日志只要多数派持久化成功，就会认为是 Committed 的。由于各种原因，总有 Follower 落后于 Leader。Leader 为每个 Follower 维护一个 nextId，标示下一个要发送的 logIndex。Follower 接收到 AppendEntries（传递 prevTermID，prevLogIndex 参数），之后会进行一致性检查，检查 AppendEntries 中指定的 LastLogIndex 是否一致，如果不一致就会向 Leader 返回失败。Leader 接收到失败之后，会将 nextId 减1，重新进行发送，直到成功。这个回溯的过程实际上就是寻找 Follower 上最后一个 CommittedId，然后 Leader 发送其后的 LogEntry。 
![raft_log_recovery](/images/consensus-algorithm/raft_log_recovery.png "raft_log_recovery")

重新选主后，新的 Leader 没有之前内存中维护的 nextId，以本地 lastLogIndex + 1 作为每个节点的 nextId。这样根据节点的 AppendEntries应答可以调整 nextId：

```java
// nextIndex
local.nextIndex = max(min(local.nextIndex-1, resp.LastLogIndex+1), 1)
```

### 4.4 日志压缩
Raft 的日志在正常操作中不断的增长，但是在实际的系统中，日志不能无限制的增长。随着日志不断增长，它会占用越来越多的空间，花费越来越多的时间来重置。如果没有一定的机制去清除日志里积累的陈旧的信息，那么会带来可用性问题。

快照是最简单的压缩方法。在快照系统中，整个系统的状态都以快照的形式写入到稳定的持久化存储中，然后到那个时间点之前的日志全部丢弃。在 Chubby 和 ZooKeeper 中同样使用快照技术。
![raft-log-conpress](/images/consensus-algorithm/raft-log-conpress.png "raft-log-conpress")
上图展示了 Raft 中快照的基础思想。每个服务器独立的创建快照，只包括已经被提交的日志。主要的工作包括将状态机的状态写入到快照中。Raft 也包含一些少量的元数据到快照中：<strong style="color:red">最后被包含索引（lastIncludedIndex）</strong>指的是被快照取代的最后的条目在日志中的索引值（状态机最后应用的日志），<strong style="color:red">最后被包含的任期（lastIncludedTerm）</strong>指的是该条目的任期号。保留这些数据是为了支持快照后紧接着的第一个条目的追加日志请求时的一致性检查，因为这个条目需要前一日志条目的索引值和任期号。为了支持集群成员更新，快照中也将最后的一次配置作为最后一个条目存下来。一旦服务器完成一次快照，他就可以删除最后索引位置之前的所有日志和快照了。
做快照的时机选择，对系统也是有影响的。如果过于频繁的快照，那么将会浪费大量的磁盘带宽；如果过于不频繁的快照，那么 Log 将会占用大量的磁盘空间，启动速度也很慢。一个简单的方式就是当 Log 达到一定大小之后再进行快照，或者是达到一定时间之后再进行快照。
快照会花费比较长的时间，如果期望快照不影响正常的 Log Entry同步，可以采用 Copy-On-Write 的技术来实现。例如，选择底层的数据结构支持 COW (Copy-On-Write)、LSM-Tree 类型的存储结构，或者是使用系统的 COW 支持，Linux的fork，或者是 ZFS 的 Snapshot 等。

### 4.5  集群成员变化

### 4.6 线性一致读

### 4.7 安全性

## 5. Multi-Raft

## 6. 总结


**参考：**

----
[1]:https://mp.weixin.qq.com/s?__biz=MzAwMDU1MTE1OQ==&mid=403582309&idx=1&sn=80c006f4e84a8af35dc8e9654f018ace&scene=1&srcid=0119gtt2MOru0Jz4DHA3Rzqy&key=710a5d99946419d927f6d5cd845dc9a72ff3d652a8e66f0ddf87d91262fd262f61f63660690d2d5da76a44a29e155610&ascene=0&uin=MjA1MDk3Njk1&devicetype=iMac+MacBookPro11%2C4+OSX+OSX+10.11.1+build(15B42)&version=11020201&pass_ticket=bhstP11nRHvorVXvQ4pt9fzB9Vdzj5sSRBe84783gsg%3D
[2]:https://mp.weixin.qq.com/s?__biz=MjM5MDg2NjIyMA==&mid=203607654&idx=1&sn=bfe71374fbca7ec5adf31bd3500ab95a&key=8ea74966bf01cfb6684dc066454e04bb5194d780db67f87b55480b52800238c2dfae323218ee8645f0c094e607ea7e6f&ascene=1&uin=MjA1MDk3Njk1&devicetype=webwx&version=70000001&pass_ticket=2ivcW%2FcENyzkz%2FGjIaPDdMzzf%2Bberd36%2FR3FYecikmo%3D
[3]:https://github.com/maemual/raft-zh_cn/blob/master/raft-zh_cn.md
[4]:https://www.sofastack.tech/blog/sofa-jraft-election-mechanism/
[5]:https://github.com/baidu/braft/blob/master/docs/cn/raft_protocol.md
[6]:https://www.sofastack.tech/blog/sofa-jraft-linear-consistent-read-implementation/
[7]:https://blog.nowcoder.net/n/dade4d8c53d144dfa78157887e2cb33e
[8]:https://zhuanlan.zhihu.com/p/60713292

[1. 架构师需要了解的Paxos原理、历程及实战][1]
[2. 一步一步理解Paxos算法][2]
[3. 寻找一种易于理解的一致性算法（扩展版）][3]
[4. SOFAJRaft 选举机制剖析 | SOFAJRaft 实现原理][4]
[5. RAFT介绍][5]
[6. SOFAJRaft 线性一致读实现剖析 | SOFAJRaft 实现原理][6]
[7. epoll源码分析][7]
[8. 带您进入内核开发的大门 | 内核中的等待队列][8]