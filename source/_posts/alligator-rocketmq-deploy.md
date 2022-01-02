---
title: Alligator 系列：RocketMQ 基础知识及部署
date: 2021-10-02 11:40:18
tags:
- RocketMQ
- CommitLog
- ConsumeQueue
- Topic
categories:
- Alligator网关
---

## 1. 概述
### 1.1 概念模型
RocketMQ 是阿里推出的一款消息系统，用来取代 Kafka 及 RabbitMQ. 在 Alligator 中支持使用 RocketMQ, 其概念模型如下所示：

![rocketmq-conceptual-model](/images/alligator/rocketmq-conceptual-model.jpg "rocketmq-conceptual-model")

<!-- more -->

在上图中有几个关键的概念，Producer 是消息的发布者，Consumer 是消息的接收者，负责消费消息，ConsumerGroup 是同一类 Consumer 的集合，Topic 是消息的集合体，而 messageQueue 则是对 Topic 进行分区，来提高消息处理的并行度，从而提高系统的吞吐量。topic 中的 MessageQueue 由 ConsumerGroup 下的 Consumer 负责消费，根据不同的消费模式，保证消息都能被 consumer 进行消费。

### 1.2 实现架构
RocketMQ 实现架构如下图所示：
![rocketmq_architecture](/images/alligator/rocketmq_architecture.png "rocketmq_architecture")
RocketMQ架构上主要分为四部分：
- Producer：消息发布者；
- Consumer：消息消费者，支持 push 和 pull 两种消费方式。；
- NameServer：注册中心，主要包括两个功能：1)Broker管理，实现 Broker 的注册及动态发现；2）路由信息管理，保存集群的整个路由信息。
- BrokerServer：负责消息的存储、投递和查询以及服务高可用保证。

<font color='red'>** 说明: **</font>
<font color='red'>NameServer 是无状态的，彼此之间互不通信，BrokerServer 要向所有的 NameServer 上报状态，而不是其中一台（NameServer 之间没有数据同步）。</font>

RocketMQ 相关概念，来自官方网站：
>1. **消息模型（Message Model）**
RocketMQ主要由 Producer、Broker、Consumer 三部分组成，其中Producer 负责生产消息，Consumer 负责消费消息，Broker 负责存储消息。Broker 在实际部署过程中对应一台服务器，每个 Broker 可以存储多个Topic的消息，每个Topic的消息也可以分片存储于不同的 Broker。Message Queue 用于存储消息的物理地址，每个Topic中的消息地址存储于多个 Message Queue 中。ConsumerGroup 由多个Consumer 实例构成。
2. **消息生产者（Producer）**
负责生产消息，一般由业务系统负责生产消息。一个消息生产者会把业务应用系统里产生的消息发送到broker服务器。RocketMQ提供多种发送方式，同步发送、异步发送、顺序发送、单向发送。同步和异步方式均需要Broker返回确认信息，单向发送不需要。
3. **消息消费者（Consumer）**
负责消费消息，一般是后台系统负责异步消费。一个消息消费者会从Broker服务器拉取消息、并将其提供给应用程序。从用户应用的角度而言提供了两种消费形式：拉取式消费、推动式消费。
4. **主题（Topic）**
表示一类消息的集合，每个主题包含若干条消息，每条消息只能属于一个主题，是RocketMQ进行消息订阅的基本单位。
5. **代理服务器（Broker Server）**
消息中转角色，负责存储消息、转发消息。代理服务器在RocketMQ系统中负责接收从生产者发送来的消息并存储、同时为消费者的拉取请求作准备。代理服务器也存储消息相关的元数据，包括消费者组、消费进度偏移和主题和队列消息等。
6. **名字服务（Name Server）**
名称服务充当路由消息的提供者。生产者或消费者能够通过名字服务查找各主题相应的Broker IP列表。多个Namesrv实例组成集群，但相互独立，没有信息交换。
7. **拉取式消费（Pull Consumer）**
Consumer消费的一种类型，应用通常主动调用Consumer的拉消息方法从Broker服务器拉消息、主动权由应用控制。一旦获取了批量消息，应用就会启动消费过程。
8. **推动式消费（Push Consumer）**
Consumer消费的一种类型，该模式下Broker收到数据后会主动推送给消费端，该消费模式一般实时性较高。
9. **生产者组（Producer Group）**
同一类Producer的集合，这类Producer发送同一类消息且发送逻辑一致。如果发送的是事务消息且原始生产者在发送之后崩溃，则Broker服务器会联系同一生产者组的其他生产者实例以提交或回溯消费。
10. **消费者组（Consumer Group）**
同一类Consumer的集合，这类Consumer通常消费同一类消息且消费逻辑一致。消费者组使得在消息消费方面，实现负载均衡和容错的目标变得非常容易。要注意的是，消费者组的消费者实例必须订阅完全相同的Topic。RocketMQ 支持两种消息模式：集群消费（Clustering）和广播消费（Broadcasting）。
11. **集群消费（Clustering）**
集群消费模式下,相同Consumer Group的每个Consumer实例平均分摊消息。
12. **广播消费（Broadcasting）**
广播消费模式下，相同Consumer Group的每个Consumer实例都接收全量的消息。
13. **普通顺序消息（Normal Ordered Message）**
普通顺序消费模式下，消费者通过同一个消息队列（ Topic 分区，称作 Message Queue） 收到的消息是有顺序的，不同消息队列收到的消息则可能是无顺序的。
14. **严格顺序消息（Strictly Ordered Message）**
严格顺序消息模式下，消费者收到的所有消息均是有顺序的。
15. **消息（Message）**
消息系统所传输信息的物理载体，生产和消费数据的最小单位，每条消息必须属于一个主题。RocketMQ中每个消息拥有唯一的Message ID，且可以携带具有业务标识的Key。系统提供了通过Message ID和Key查询消息的功能。
16. **标签（Tag）**
为消息设置的标志，用于同一主题下区分不同类型的消息。来自同一业务单元的消息，可以根据不同业务目的在同一主题下设置不同标签。标签能够有效地保持代码的清晰度和连贯性，并优化RocketMQ提供的查询系统。消费者可以根据Tag实现对不同子主题的不同消费逻辑，实现更好的扩展性。

## 2. 基础
### 2.1 消息存储
消息存储是 RocketMQ 中最为复杂和最为重要的一部分，我们主要是从概念上对其理解，其实现不作过多分析，其存储整体结构如下所示：
![rocketmq_message_storage](/images/alligator/rocketmq_message_storage.png "rocketmq_message_storage")

消息存储架构图中主要有下面三个跟消息存储相关的文件构成。

1. CommitLog：存储消息及元数据信息，由 Producer 写入, 消息内容不是定长的。单个文件大小默认 1G, 文件名长度为 20 位，左边补零，剩余为起始偏移量，比如 00000000000000000000 代表了第一个文件，起始偏移量为 0，文件大小为 1G=1073741824；当第一个文件写满了，第二个文件为 00000000001073741824 ，起始偏移量为 1073741824 ，以此类推。消息主要是顺序写入日志文件，当文件满了，写入下一个文件；

2. ConsumeQueue：消息消费队列，等同于概念模型中的 MessageQueue，Consumer 根据 ConsumeQueue 来查找待消费的消息。其中，ConsumeQueue（逻辑消费队列）作为消费消息的索引，保存了指定 Topic 下的队列消息在 CommitLog 中的起始物理偏移量 offset，消息大小 size 和消息Tag 的 HashCode 值。consumequeue 文件可以看成是基于 topic 的 commitlog 索引文件，故 consumequeue 文件夹的组织方式如下：topic/queue/file 三层组织结构，具体存储路径为：$HOME/store/consumequeue/{topic}/{queueId}/{fileName}。同样 consumequeue 文件采取定长设计，每一个条目共 20 个字节，分别为 8 字节的 commitlog 物理偏移量、4 字节的消息长度、8 字节 tag hashcode，单个文件由 30W 个条目组成，可以像数组一样随机访问每一个条目，每个 ConsumeQueue 文件大小约 5.72M；

3. IndexFile：IndexFile（索引文件）提供了一种可以通过 key 或时间区间来查询消息的方法。Index 文件的存储位置是：$HOME \store\index${fileName}，文件名 fileName 是以创建时的时间戳命名的，固定的单个IndexFile 文件大小约为 400M，一个 IndexFile 可以保存 2000W 个索引，IndexFile 的底层存储设计为在文件系统中实现 HashMap 结构，故 RocketMQ 的索引文件其底层实现为 hash 索引。

从 RocketMQ 的消息存储整体架构图中可以看出，RocketMQ 采用的是混合型的存储结构，即为 Broker 单个实例下所有的队列共用一个日志数据文件（即为CommitLog）来存储。多个Topic的消息实体内容都存储于一个CommitLog中，Producer 发送消息到 Broker 端，然后 Broker 端使用同步或者异步的方式对消息刷盘持久化，保存至 CommitLog 中。只要消息被刷盘持久化至磁盘文件 CommitLog 中，那 么Producer 发送的消息就不会丢失。

### 2.2 消息过滤
消息过滤是订阅/消费消息的时候处理的，Consumer 先从 ConsumeQueue 中拿到消息的索引，再去 CommitLog 中取到数据，过滤的操作就是根据索引来进行的，我们先看下 ConsumeQueue 中消息索引的格式：

![rocketmq_message_index](/images/alligator/rocketmq_message_index.png "rocketmq_message_index")

可以看到其中有 8 个字节存储的 Message Tag 的哈希值，基于 Tag 的消息过滤正是基于这个字段值的。RocketMQ 支持两种过滤方式，1）Tag 过滤，Consumer 在订阅消息时除了指定 Topic 还可以指定 Tag，如果一个消息有多个 Tage ，可以用||分隔。从 ConsumeQueue 读取到记录后，会根据 tag hash 值去做过滤，由于使用 hashcode 进行判断，只能进行整体过滤，无法精确对 tag 原始字符串进行过滤，所以 Cousumer 接收到消息之后，还需要对消息的原始 tag 字符串进行比对，如果不同，则丢弃该消息，不进行消息消费。2） SQL92 过滤，使用 SQL 表达式进行过滤。

### 2.3 消息负载均衡
RocketMQ 中的负载均衡都在 Client 端完成，具体来说的话，主要可以分为 Producer 端发送消息时候的负载均衡和 Consumer 端订阅消息的负载均衡。

**Producer 端负载均衡**
Producer 端在发送消息的时候，会找到 Topic 相关的所有 MessageQueue 信息，根据一定的负载策略选择一个 MessageQueue 进行发送。

**Consumer 端负载均衡**
Consumer 端负载均衡的主要目的是将 Topic 下的 MessageQueue 分配给 CousumerGroup 中的 Consumer，并保证一个 MessageQueue 只能被一个 Consumer 消费（集群模式下）。

![rocketmq_message_allocate](/images/alligator/rocketmq_message_allocate.png "rocketmq_message_allocate")

## 3. 部署

### 3.1 单机部署
由于只是用于实验目的，只需要部署单 Master 模式。

**官方推荐配置**
1. 64bit OS, Linux/Unix/Mac is recommended;(Windows user see guide below)
2. 64bit JDK 1.8+;
3. Maven 3.2.x;
4. Git;
5. 4g+ free disk for Broker server

下载 RocketMQ V4.8.0，并解压到安装目录
<https://www.apache.org/dyn/closer.cgi?path=rocketmq/4.8.0/rocketmq-all-4.8.0-source-release.zip>

**修改配置**
**1. 修改 rocketmq-4.8.0/conf/broker.conf**
如果部署在公有云上，需要将 brokerIP 和 namesrvAddr 设置为公网 ip 地址和端口
```bash
brokerClusterName = DefaultCluster
brokerName = broker-a
brokerId = 0
deleteWhen = 04
fileReservedTime = 48
brokerRole = ASYNC_MASTER
flushDiskType = ASYNC_FLUSH
## broker ip
brokerIP1=公网ip 

## na
namesrvAddr=公网ip:9876
```

**2. 修改内存大小**
RocketMQ 默认内存配置是 4G, 单机版本配置启动 1台 nameServer 及 1台 broker, 如果配置不够的话，需要修改 runbroker.sh 和 runserver.sh 脚本。
```bash
JAVA_OPT="${JAVA_OPT} -server -Xms2g -Xmx2g -Xmn1g"
```
根据情况修改，这里修改为 2G.

### 3.2 命令
**1. 启动 nameServer**
```bash
cd rocketmq-4.8.0/bin

nohup sh mqnamesrv -n 外网ip:9876 &

# -n: 指定nameserv ip 地址
```

**2. 启动 broker**
```bash
cd rocketmq-4.8.0

nohup sh bin/mqbroker -n 外网ip:9876 -c conf/broker.conf &

# -n: 指定nameserv ip 地址
# -c: 指定配置文件
```

**3. 关闭服务器**
```bash
# 关闭 broker
./mqshutdown broker

# 关闭 namesrv
./mqshutdown namesrv
```

**4. Topic 命令**
```bash
# 创建 topic
sh mqadmin updateTopic -n 外网ip:9876 -c DefaultCluster -t <topic name>

# 查询 topic
sh mqadmin topicList –n 外网ip:9876

```

<font color='red'>** 说明: **</font>
<font color='red'>在 RocketMQ 中，Topic 须提前创建。</font>

</br>

**参考：**

----
[1]:https://github.com/apache/rocketmq/blob/master/docs/cn/concept.md
[2]:https://github.com/apache/rocketmq/blob/master/docs/cn/architecture.md
[3]:https://github.com/apache/rocketmq/blob/master/docs/cn/design.md
[4]:https://mp.weixin.qq.com/s/Efw5pXrptWPfCDQI8rc_xg
[5]:http://rocketmq.apache.org/docs/quick-start/

[1. RocketMQ 基本概念][1]

[2. RocketMQ 架构设计][2]

[3. RocketMQ 设计(design)][3]

[4. 一文讲透Apache RocketMQ技术精华][4]

[5. RocketMQ Quick Start][5]

