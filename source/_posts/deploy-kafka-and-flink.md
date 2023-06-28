---
title: Kafka 及 Flink 单机环境部署
date: 2022-02-13 17:13:13
updated: 2022-02-13 17:13:13
tags:
- kafka
- flink
categories:
- 部署
---

在 Centos 7.6 上部署一个单机的 kakfa 及 Flink, 用于学习的目的。

<!-- more -->


## 安装 Kafka

前置条件：提前安装好 Java 8 或者以上版本。

### 下载 Kafka

从 kafka 官方网站下载最新稳定版，当前最新版本为 `kafka_2.13-3.1.0.tgz`, 如果要下载稳定版本，可以自行选择。

官方下载地址：<https://kafka.apache.org/downloads>

> 说明： kafka_[scala version]-[kafak version].tgz, 其中 2.13 是 Scala version, 3.1.0 是 kafka 版本。

### 解压缩
```bash
$ tar -xzvf kafka_2.13-3.1.0.tgz
```

### 启动 Zookeeper

```bash
$ cd kafka_2.13-3.1.0/

$ nohup bin/zookeeper-server-start.sh config/zookeeper.properties > zk.log 2>&1 &
```

### 启动 Kafka

```bash
$ nohup bin/kafka-server-start.sh config/server.properties > kafka.log 2>&1 & 
```

### 创建 Topic

```bash
$ bin/kafka-topics.sh --create --topic quickstart-events --bootstrap-server localhost:9092
```

### 查看 Topic 信息

```bash
$ bin/kafka-topics.sh --describe --topic quickstart-events --bootstrap-server localhost:9092
Topic: quickstart-events        TopicId: hhAhnQswQeS64o3-xxjouA PartitionCount: 1       ReplicationFactor: 1    Configs: segment.bytes=1073741824
        Topic: quickstart-events        Partition: 0    Leader: 0       Replicas: 0     Isr: 0

```

### 列出所有 Topic
```bash
$ bin/kafka-topics.sh --list -bootstrap-server localhost:9092
```

### 生产数据到指定 Topic
```bash
$ bin/kafka-console-producer.sh --topic quickstart-events --bootstrap-server localhost:9092
>hello kafka
>hello flink
>
```

### 消费指定 Topic 的数据
```bash
$ bin/kafka-console-consumer.sh --topic quickstart-events --from-beginning --bootstrap-server localhost:9092
hello kafka
hello flink
```

### 删除 Topic
```bash
$ bin/kafka-topics.sh --delete --bootstrap-server localhost:9092 --topic quickstart-events
```

## 安装 Flink

前置条件：提前安装好 Java 8 或者以上版本。

### 下载 Flink

Flink 当前最新稳定版本是 `flink-1.14.3-bin-scala_2.12.tgz`, 我们从官方网站下载。
官方下载地址：<https://flink.apache.org/downloads.html>

> 说明：flink-1.14.3-bin-scala_2.12.tgz 中可以指定特定的 scala 版本，这里我们选择的是 scala 2.12 版本。

### 解压缩
```bash
$ tar -xzf flink-1.14.3-bin-scala_2.12.tgz 

$ cd -xzf flink-1.14.3-bin-scala_2.12
```

### 启动集群（standalone 模式）
```bash
$ ./bin/start-cluster.sh
Starting cluster.
Starting standalonesession daemon on host.
Starting taskexecutor daemon on host.
```

### 提交作业

使用 Flink 自带的 example, 提交作业。

```bash
$ ./bin/flink run examples/streaming/WordCount.jar
$ tail log/flink-*-taskexecutor-*.out
  (nymph,1)
  (in,3)
  (thy,1)
  (orisons,1)
  (be,4)
  (all,2)
  (my,1)
  (sins,1)
  (remember,1)
  (d,4)
```

### 停止集群

```bash
$ ./bin/stop-cluster.sh
```