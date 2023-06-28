---
title: Paxos 和 Raft 算法
date: 2020-11-08 16:31:26
updated: 2020-11-08 16:31:26
tags:
- paxos
- raft
- 一致性算法
- 共识算法
categories: 
- 数据结构与算法
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

<!-- more -->

## 2. Paxos
Paxos 算法解决的问题是一个分布式系统如何就某个值（提案）达成一致。一个典型的场景是，在一个分布式数据库系统中，如果各节点的初始状态一致，每个节点都执行相同的操作序列，那么他们最后能得到一个一致的状态。为保证每个节点执行相同的命令序列，需要在每一条指令上执行一个“一致性算法”以保证每个节点看到的指令一致，是分布式计算中的重要问题。

### 2.1 Basic-Paxos
在 Paxos 算法中，节点分为三种角色：
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
Proposal ID：round number(3), server id(1)，即 Proposal ID = 3.1 ，其中 3 代表轮数，1 代表 节点编号。
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

Multi-Paxos 就是对每一个 Paxos Instance 执行一次 Paxos 算法，确保每一台节点上的数据都是一致的。

Multi-Paxos 有如下一些缺点：
1. 比较复杂，难以理解，工程实现难度比较大；
2. 每一个服务器都可以执行写操作，性能较差。

为了解决 Multi-Paxos 的缺点，在算法中引入了 Leader 的角色，所有的决议都通过 Leader 来进行，然后同步到其它节点，其结构如下图所示：
![multi-paxos-2](/images/consensus-algorithm/multi-paxos-2.jpg "multi-paxos-2")

通过 Consensus Module， 完成多个连续的提案的确定，通过日志同步到各个节点，保证节点以相同的顺序执行，使得节点的状态保持一致。其中，Raft 算法便是 Multi-Paxos 算法的一个实现版本。

## 4. Raft
Raft 通过选举一个 Leader，然后让它负责日志的复制来实现一致性。Leader 从客户端接收日志条目，把日志条目复制到其它节点上，并且当保证安全性的时候告诉其它节点应用日志条目到他们的状态机中。拥有一个 Leader 大大简化了对复制日志的管理。例如，Leader 可以决定新的日志条目需要放在日志中的什么位置而不需要和其他节点商议，并且数据只从 Leader 流向其他节点。一个 Leader 可以宕机，可以和其他节点失去连接，这时一个新的 Leader 会被选举出来。

通过 Leader 的方式，Raft 将一致性问题分解成了三个相对独立的子问题：
1. Leader 选举：当现存的 Leader 宕机的时候，一个新的 Leader 需要被选举出来；
2. 日志复制：Leader 必须从客户端接收日志然后复制到集群中的其他节点，并且强制要求其它节点的日志保持和自己相同；
3. 安全性：如果有任何的节点节点已经应用了一个确定的日志条目到它的状态机中，那么其它节点节点不能在同一个日志索引位置应用一个不同的指令。

### 4.1 基本概念
**Server状态：**

在任何时刻，每一个节点节点都处于这三个状态之一：Leader 、Follower 或者 Candidate。在通常情况下，系统中只有一个 Leader 并且其它的节点全部都是 Follower。Follower 都是被动的：它们不会发送任何请求，只是简单的响应来自 Leader 或者 Candidate 的请求。Leader 处理所有的客户端请求（如果一个客户端和 Leader 联系，那么 Follower 会把请求重定向给 Leader）。第三种状态，Candiate，是用来在选举新 Leader 时使用。下图展示了这些状态和它们之间的转换关系。

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
集群成员变化主要是指集群节点数量的增删，在实际场景中，集群的扩容（副本数的增加）或者节点当机下线都是常见的事情。在不停机的情况下，由于节点不能一次性原子地变更节点的成员配置信息，会导致同一时间，同一个任期出现两个领导者，违背了算法安全性原则，如下图所示：
![raft-membership](/images/consensus-algorithm/raft-membership.png "raft-membership")
3 个节点的集群扩展到 5 个节点的集群，直接扩展可能会造成 Server1 和Server2 构成老的多数集合，Server3、Server4 和 Server5 构成新的多数集合，产生两个领导者。

**Joint-Consensus**
Raft 算法采用协同一致性的方式来解决节点的变更，先提交一个包含新老节点结合的 Configuration 命令，当这条消息 Commit 之后再提交一条只包含新节点的 Configuration 命令。新老集合中任何一个节点都可以成为 Leader，这样 Leader 当机之后，如果新的 Leader 没有看到包括新老节点集合的 Configuration 日志，继续以老节点集合组建集群；如果新的 Leader 看到了包括新老节点集合的 Configuration 日志，将未完成的节点变更流程走完。具体流程如下：
1. 加入新对节点，从 Leader 中追加数据；
2. 全部新节点完成数据同步之后，向新老集合发送 Cold+new 命令；
3. 如果新节点集合多数和老节点集合多数都应答了 Cold+new，就向新老节点集合发送 Cnew 命令；
4. 如果新老节点集合多数应答了 Cnew，完成节点切换。

在这里，我们可以把 Cold+new 理解为包含新老结点地址集合，如果当前集群包括 server1, server2 及 server3, 新加的结点为 server4, server5,那么 Cold+new 等同于集合 [server1, server2, server3, server4, server5], Cold 为 [server1, server2, server3], Cnew 为 [server4, server5]。

![raft-member-transmit](/images/consensus-algorithm/raft-member-transmit.png "raft-member-transmit")
虚线表示已经被创建但是还没有被提交的配置日志条目，实线表示最后被提交的配置日志条目。领导人首先创建了 Cold+new 的配置条目在自己的日志中，并提交到 Cold+new 中（Cold 的大多数和 Cnew 的大多数）。然后它创建 Cnew 条目并提交到 Cnew 中的大多数。这样就不存在 Cnew 和 Cold 可以同时做出决定的时间点。
如果 Cold+new 被 Commit 到新老集合多数的话，即使过程终止，新的 Leader 依然能够看到 Cold+new，并继续完成 Cnew 的流程，最终完成节点变更；如果 Cold+new 没有提交到新老集合多数的话，新的Leader可能看到了 Cold+new 也可能没有看到，如果看到了依然可以完成 Cnew 的流程，如果没有看到，说明 Cold+new 在两个集合都没有拿到多数应答，重新按照 Cold 进行集群操作，两阶段过程中选主需要新老两个集合都达到多数同意。

节点配置变更过程中需要满足如下规则：
- 新老集合中的任何节点都可能成为 Leader；
- 任何决议都需要新老集合的多数通过。

在这里有一个关键的点就是：<strong style="color:red">任何决议都需要新老集合的多数通过。</strong>如果不能形成两个多数集合，算法是否就可以简化？单节点变更就是基于这个想法产生的。

**Single-Server Change**
单节点变更是对 Joint-Consensus 的简化， 它每次只增删一个节点，这样就不会出现两个多数集合，不会造成决议冲突的情况，如果需要变更多个节点，那需要执行多次单节点变更。比如将 3 节点集群扩容为 5 节点集群，这时你需要执行 2 次单节点变更，先将 3 节点集群变更为 4 节点集群，然后再将 4 节点集群变更为 5 节点集群，如下图所示：
![raft-node-new](/images/consensus-algorithm/raft-node-new.jpg "raft-node-new")
还是以三结点 Raft 集群为例，演示下变更为五结点的过程，假定节点 A 为 Leader。
![raft-node-evolution-1](/images/consensus-algorithm/raft-node-evolution-1.jpg "raft-node-evolution-1")
目前的集群配置为[A, B, C]，先向集群中加入节点 D，这意味着新配置为[A, B, C, D]。成员变更，是通过两步实现的：
1. Leader（节点 A）向新节点（节点 D）同步数据；
2. Leader（节点 A）将新配置 [A, B, C, D] 作为一个日志项，复制到新配置中所有节点（节点 A、B、C、D）上，然后将新配置的日志项应用（Apply）到本地状态机，完成单节点变更。
![raft-node-evolution-2](/images/consensus-algorithm/raft-node-evolution-2.jpg "raft-node-evolution-2")

变更完成后，集群的配置变为 [A, B, C, D],接着向集群加入结点 E，即新配置为[A, B, C, D, E]，流程类似:
1. Leader（节点 A）向新节点（节点 E）同步数据；
2. Leader（节点 A）将新配置 [A, B, C, D, E] 作为一个日志项，复制到新配置中所有节点（节点 A、B、C、D、E）上，然后将新配置的日志项应用（Apply）到本地状态机，完成单节点变更。
![raft-node-evolution-3](/images/consensus-algorithm/raft-node-evolution-3.jpg "raft-node-evolution-3")

通过连续执行两次单结点变更，完成了集群结点的扩容。

一次性加入一个结点，重点在于新老配置的结点不会形成两个多数派，新老配置要形成多数派总会有重叠的结点，重叠的结点不会给同一任期的两个结点投两次票，这是由 Raft 算法的安全性保证的。

![raft-node-evolution](/images/consensus-algorithm/raft-node-evolution.jpg "raft-node-evolution")

不管节点数是偶数还是奇数，增加或减少一个结点都不能形成新老配置的两个多数派，两个集合总会有重叠，从而确保了算法的安全性。

另外，在分区错误、节点故障等情况下，有可能并发执行单节点变更，那么就可能出现一次单节点变更尚未完成，新的单节点变更又在执行，导致集群出现 2 个 Leader 的情况。解决的办法是，可以在 Leader 启时 （选主成功之后）时，创建一个 NO_OP 日志项（也就是空日志项），只有当 Leader将 NO_OP 日志项应用后，再执行成员变更请求。

### 4.6 线性一致读
什么是线性一致读? 所谓线性一致读，一个简单的例子是在 t1 的时刻写入了一个值，那么在 t1 之后，一定能读到这个值，不可能读到 t1 之前的旧值(类似 Java 中的 volatile 关键字，即线性一致读就是在分布式系统中实现 Java volatile 语义)。简而言之是需要在分布式环境中实现 Java volatile 语义效果，即当 Client 向集群发起写操作的请求并且获得成功响应之后，该写操作的结果要对所有后来的读请求可见。和 volatile 的区别在于 volatile 是实现线程之间的可见，而线性一致读需要实现 Server 之间的可见。
![raft-linearizability-read](/images/consensus-algorithm/raft-linearizability-read.png "raft-linearizability-read")
如上图 Client A、B、C、D 均符合线性一致读，其中 D 看起来是 Stale Read，其实并不是，D 请求横跨 3 个阶段，而 Read 可能发生在任意时刻，所以读到 1 或 2 都行。

**Raft Log read**
实现线性一致读最常规的办法是走 Raft 协议，将读请求同样按照 Log 处理，通过 Log 复制和状态机执行来获取读结果，然后再把读取的结果返回给客户端。因为 Raft 本来就是一个为了实现分布式环境下线性一致性的算法，所以通过 Raft 非常方便的实现线性 Read，也就是将任何的读请求走一次 Raft Log，等此 Log 提交之后在 apply 的时候从状态机里面读取值，一定能够保证这个读取到的值是满足线性要求的。

因为每次 Read 都需要走 Raft 流程，Raft Log 存储、复制带来刷盘开销、存储开销、网络开销，走 Raft Log 不仅仅有日志落盘的开销，还有日志复制的网络开销，另外还有一堆的 Raft “读日志” 造成的磁盘占用开销，导致 Read 操作性能是非常低效的，所以在读操作很多的场景下对性能影响很大，在读比重很大的系统中是无法被接受的，通常都不会使用。

个人理解：<strong style="color:red">Raft Log read 关键点在于提交一次读操作并应用到状态机后，将之前处于 Commited　状态的 log 都应用到状态机，确保状态机的状态是最新的。</strong>

在 Raft 算法中，执行一次写操作，由客户端向 Leader 发起，首先 Leader 将本次操作写入本地日志，然后向所有的 Follower 同步日志，Follower 收到日志之后写入本地，并回复给 Leader ； Leader 收到半数以上的回复之后将本次操作应用到本地的状态机，并返回客户端写入成功，最后 Leader 在下次同步日志时再将本次日志 Commited 的信息传递给 Follower , Follower再异步更新本地状机。可见，一次写入操作之后，Leader 状态机拥有最新的状态，而 Follower 状态机的状态有可能落后于 Leader。如果直接从 Follower 读到数据，会读到 Stale 数据。如果从 Leader 读取数据的话，则可以保证线性读取最新的数据。现在关键的问题是：<strong style="color:red">如何确认 Leader 在处理这次 Read 的时候一定是 Leader ? </strong>，在这里，有两种方法：
1. ReadIndex Read;
2. Lease Read.

**ReadIndex Read**
ReadIndex Read 有两个关键点：
1. Leader 向 Follower 发送心跳确认自己仍然是 Leader，避免 Leader 已经过期而不自知；
2. 维护一个 ReadIndex , 初始值等于 Leader 的 CommitIndex , 并将 ReadIndex 指向的所有 Log 都应用到状态机中，确保所有的写操作都已经应用。

ReadIndex Read 可以从 Leader 和 Followr 读取，过程如下描述。

从 Leader 读取：
1. Leader 将自己当前 Log 的 commitIndex 记录到一个 Local 变量 ReadIndex 里面；
2. 接着向 Followers 节点发起一轮 Heartbeat，如果半数以上节点返回对应的 Heartbeat Response，那么 Leader就能够确定现在自己仍然是 Leader；
3. Leader 等待自己的 StateMachine 状态机执行，至少应用到 ReadIndex 记录的 Log，直到 applyIndex 超过 ReadIndex，这样就能够安全提供 Linearizable Read，也不必管读的时刻是否 Leader 已飘走；
4. Leader 执行 Read 请求，将结果返回给 Client。

从 Follower 读取：
1. Follower 节点向 Leader 请求最新的 ReadIndex；
2. Leader 仍然走一遍之前的流程，执行上面前 3 步的过程(确定自己真的是 Leader)，并且返回 ReadIndex 给 Follower；
3. Follower 等待当前的状态机的 applyIndex 超过 ReadIndex；
4. Follower 执行 Read 请求，将结果返回给 Client

**Lease Read**
在 ReadIndex Read 中执行一次读操作，Leader 都要向 Follower 发送心跳确认当前自己仍然是 Leader，还是存在网络开销，是否可以优化？ Leader 的选主是通过选择超时时间进行的，在这里引入任期的概念，在下一次选主前，都可以认为当前 Leader 的角色都是不会改变的，在这期间的读操作，可以节省心跳的操作。
Raft 论文里面提及一种通过 Clock + Heartbeat 的 Lease Read 优化方法，也就是 Leader 发送 Heartbeat 的时候首先记录一个时间点 Start，当系统大部分节点都回复 Heartbeat Response，由于 Raft 的选举机制，Follower 会在 Election Timeout 的时间之后才重新发生选举，下一个 Leader 选举出来的时间保证大于 Start + Election Timeout/Clock Drift Bound，所以可以认为 Leader 的 Lease 有效期可以到 Start + Election Timeout/Clock Drift Bound 时间点。

Lease Read 基本思路是 Leader 取一个比 Election Timeout 小的租期（最好小一个数量级），在租约期内不会发生选举，确保 Leader 不会变化，所以跳过 ReadIndex 的第二步也就降低延时。由此可见 Lease Read 的正确性和时间是挂钩的，依赖本地时钟的准确性，因此虽然采用 Lease Read 做法非常高效，但是仍然面临风险问题，也就是存在预设的前提即各个服务器的 CPU Clock 的时间是准的，即使有误差，也会在一个非常小的 Bound 范围里面，时间的实现至关重要，如果时钟漂移严重，各个服务器之间 Clock 走的频率不一样，这套 Lease 机制可能出问题。

Lease Read 实现方式包括：
1. 定时 Heartbeat 获得多数派响应，确认 Leader 的有效性；
2. 在租约有效时间内，可以认为当前 Leader 是唯一有效 Leader，可忽略 ReadIndex 中的 Heartbeat 确认步骤；
3. Leader 等待自己的状态机执行，直到 applyIndex 超过 ReadIndex，这样就能够安全的提供 Linearizable Read

### 4.7 安全性
使用 Raft 算法，需要保证如下的安全性：
1. 选举安全特性：对于一个给定的任期号，最多只会有一个领导人被选举出来；
2. 领导人只附加原则：领导人绝对不会删除或者覆盖自己的日志，只会增加；
3. 日志匹配原则：如果两个日志在相同的索引位置的日志条目的任期号相同，那么我们就认为这个日志从头到这个索引位置之间全部完全相同；
4. 领导人完全特性：如果某个日志条目在某个任期号中已经被提交，那么这个条目必然出现在更大任期号的所有领导人中；
4. 状态机安全特性：如果一个领导人已经将给定的索引值位置的日志条目应用到状态机中，那么其他任何的服务器在这个索引位置不会应用一个不同的日志。

## 5. Multi-Raft
因为 Raft 集群内只有 Leader 提供读写服务，所以读写也会形成单点的瓶颈。因此为了支持水平扩展，可以按某种 Key 进行分片部署，比如用户 ID，让 Group 1 对 [0, 10000) 的 ID 提供服务，让 Group 2 对 [10000, 20000) 的 ID 提供服务，以此类推。如下是 SOFAJRaft 的实现：

![multi-raft](/images/consensus-algorithm/multi-raft.png "multi-raft")

## 6. 总结
这篇文章对主要的一致性算法进行了一个概念上描述，并没有深入到具体实现细节。在工程实践境中，已经有几个 Raft 的实现用于生产环境中，如 GO 语言版本的 Etcd、C++ 语言的 braft 及 Java 语言的 SOFAJRaft 。后面有时间，专门研究分析下 SOFAJRaft 源码，提升对共识算法的理解。

**参考：**

----
[1]:https://mp.weixin.qq.com/s?__biz=MzAwMDU1MTE1OQ==&mid=403582309&idx=1&sn=80c006f4e84a8af35dc8e9654f018ace&scene=1&srcid=0119gtt2MOru0Jz4DHA3Rzqy&key=710a5d99946419d927f6d5cd845dc9a72ff3d652a8e66f0ddf87d91262fd262f61f63660690d2d5da76a44a29e155610&ascene=0&uin=MjA1MDk3Njk1&devicetype=iMac+MacBookPro11%2C4+OSX+OSX+10.11.1+build(15B42)&version=11020201&pass_ticket=bhstP11nRHvorVXvQ4pt9fzB9Vdzj5sSRBe84783gsg%3D
[2]:https://mp.weixin.qq.com/s?__biz=MjM5MDg2NjIyMA==&mid=203607654&idx=1&sn=bfe71374fbca7ec5adf31bd3500ab95a&key=8ea74966bf01cfb6684dc066454e04bb5194d780db67f87b55480b52800238c2dfae323218ee8645f0c094e607ea7e6f&ascene=1&uin=MjA1MDk3Njk1&devicetype=webwx&version=70000001&pass_ticket=2ivcW%2FcENyzkz%2FGjIaPDdMzzf%2Bberd36%2FR3FYecikmo%3D
[3]:https://github.com/maemual/raft-zh_cn/blob/master/raft-zh_cn.md
[4]:https://www.sofastack.tech/blog/sofa-jraft-election-mechanism/
[5]:https://github.com/baidu/braft/blob/master/docs/cn/raft_protocol.md
[6]:https://www.sofastack.tech/blog/sofa-jraft-linear-consistent-read-implementation/
[7]:https://www.sofastack.tech/blog/sofa-jraft-deep-dive/
[8]:https://github.com/hedengcheng/tech/blob/master/distributed/PaxosRaft%20%E5%88%86%E5%B8%83%E5%BC%8F%E4%B8%80%E8%87%B4%E6%80%A7%E7%AE%97%E6%B3%95%E5%8E%9F%E7%90%86%E5%89%96%E6%9E%90%E5%8F%8A%E5%85%B6%E5%9C%A8%E5%AE%9E%E6%88%98%E4%B8%AD%E7%9A%84%E5%BA%94%E7%94%A8.pdf


[1. 架构师需要了解的Paxos原理、历程及实战][1]
[2. 一步一步理解Paxos算法][2]
[3. 寻找一种易于理解的一致性算法（扩展版）][3]
[4. SOFAJRaft 选举机制剖析 | SOFAJRaft 实现原理][4]
[5. RAFT介绍][5]
[6. SOFAJRaft 线性一致读实现剖析 | SOFAJRaft 实现原理][6]
[7. 蚂蚁金服开源 SOFAJRaft 详解| 生产级高性能 Java 实现][7]
[8. PaxosRaft 分布式一致性算法原理剖析及其在实战中的应用.pdf][8]