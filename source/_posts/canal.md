---
title: Springboot 序列：Canal
date: 2022-04-10 15:10:29
tags:
- canal
- 增量更新
- instance
categories:
- Springboot
---

Canal 是阿里开源的中间件，主要用途是基于 MySQL 数据库增量日志解析，提供增量数据订阅和消费。它有较多的使用场景，一种比较常用的场景是用来做业务 cache 刷新。这篇文章主要便是用来记录 Canal 的使用方式。
<!-- more -->

## 概述

Canal 使用场景如下所示：

![canal](/images/spring-cloud/canal.jpg "canal")

- `instance` 实例代表一组 Mysql 数据库表，即一组需要订阅的数据库对象；
- Canal server 伪装成一个 Mysql slave 去订阅 Mysql 的 binlog 日志；
- 第三方应用可以集成 Canal client 客户端去 Canal server 订阅 Mysql 事件；
- 为了实现组件的高可用引入 Zookeeper，Canal server 注册到 Zookeeper, 并竞争为某一个 `instance` 的主结点，一个 `instance` 只能有一个主结点；
- Canal client 也注册到 Zookeeper，并竞争为 `instance` 客户端，为了保证消息的顺序性，同时只能有一个 Client 消费一个 `instance`;
- Zookeeper 同时也保存了 `instance` 消费的 `position`, 便于下次重启时继续消息，保证消息不会丢失。 


## 前置条件

### 开启 ROW 模式

使用 Canal, 需要 Mysql 开启 Binlog 写入功能，配置 binlog-format 为 ROW 模式，my.cnf 配置如下：

```properties
[mysqld]
log-bin=mysql-bin # 开启 binlog
binlog-format=ROW # 选择 ROW 模式
server_id=1 # 配置 MySQL replaction 需要定义，不要和 canal 的 slaveId 重复
```

查看 Binlog 是否开启的命令：
```bash
show variables like '%log_bin%'
```

### 配置用户

可以给 Canal 配置一个专门的 Mysql 用户具有作为 MySQL slave 的权限。
```bash
CREATE USER canal IDENTIFIED BY 'canal';  
GRANT SELECT, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'canal'@'%';
-- GRANT ALL PRIVILEGES ON *.* TO 'canal'@'%' ;
FLUSH PRIVILEGES;
```

## 单机模式

在单机模式下，不引入 Zookeeper, 客户端与服务器直连，是比较简单的方式，可用于功能的测试验证。

### 安装 Canal Server

- 下载
可以在 <strong>[官方网站](https://github.com/alibaba/canal/releases) </strong> 下载最新的安装包，在这里，我们下载 `1.1.5` 的版本。
```bash
wget https://github.com/alibaba/canal/releases/download/canal-1.1.5/canal.deployer-1.1.5.tar.gz
```

- 解压缩
```bash
mkdir /data/app/canal
tar zxvf canal.deployer-1.1.5.tar.gz  -C /data/app/canal
```

- 目录结构
```bash
drwxr-xr-x. 2 root root   93 4月   8 09:42 bin
drwxr-xr-x. 5 root root  123 4月  12 18:55 conf
drwxr-xr-x. 2 root root 4096 4月   7 17:40 lib
drwxrwxrwx. 4 root root   34 4月   7 18:33 logs
drwxrwxrwx. 2 root root  177 4月  19 2021 plugin
```

- 配置 canal
```properties
#################################################
#########               common argument         #############
#################################################
# tcp bind ip
canal.ip = 192.168.1.100
# register ip to zookeeper
canal.register.ip =
canal.port = 11111
canal.metrics.pull.port = 11112
# canal instance user/passwd
# canal.user = canal
# canal.passwd = E3619321C1A937C46A0D8BD1DAC39F93B27D4458

# canal admin config
#canal.admin.manager = 127.0.0.1:8089
canal.admin.port = 11110
canal.admin.user = admin
canal.admin.passwd = 4ACFE3202A5FF5CF467898FC58AAB1D615029441
# admin auto register
#canal.admin.register.auto = true
#canal.admin.register.cluster =
#canal.admin.register.name =

# canal.zkServers = 192.168.7.115:2181
# flush data to zk
canal.zookeeper.flush.period = 1000

...

#################################################
#########               destinations            #############
#################################################
canal.destinations = example
# conf root dir
canal.conf.dir = ../conf
# auto scan instance dir add/remove and start/stop instance
canal.auto.scan = true
canal.auto.scan.interval = 5
# set this value to 'true' means that when binlog pos not found, skip to latest.
# WARN: pls keep 'false' in production env, or if you know what you want.
canal.auto.reset.latest.pos.mode = false
```
    - canal.ip: 指定 ip, 系统有多张网卡，比较有用；
    - canal.zkServers: zookeeper 地址，在单机模式下没有用到；
    - canal.destinations: 配置 instance, 默认情况下配置了 `example` 实例。


- 配置 instance
Canal Server 默认自带了一个 `example` 的 `instance`, 根据实际情况进行配置，文件路径为：conf/example/instance.properties.
```properties
#################################################
## mysql serverId , v1.0.26+ will autoGen
# 设置 slaveId，不能与其它 server 及 mysql 配置冲突
canal.instance.mysql.slaveId=1024

# position info
# 配置 mysql master 节点信息
canal.instance.master.address=127.0.0.1:3306


# 设置 username/password
canal.instance.dbUsername=canal
canal.instance.dbPassword=canal
canal.instance.connectionCharset = UTF-8

# table regex
# 设置订阅的表
canal.instance.filter.regex=.*\\..*
# table black regex
# 设置不订阅的表
canal.instance.filter.black.regex=mysql\\.slave_.*
# table field filter(format: schema1.tableName1:field1/field2,schema2.tableName2:field1/field2)
#canal.instance.filter.field=test1.t_product:id/subject/keywords,test2.t_company:id/name/contact/ch
# table field black filter(format: schema1.tableName1:field1/field2,schema2.tableName2:field1/field2)
#canal.instance.filter.black.field=test1.t_product:subject/product_image,test2.t_company:id/name/contact/ch
```
    - canal.instance.mysql.slaveId: 设置 slaveId，不能与其它 server 及 mysql 配置冲突；
    - anal.instance.master.address: 配置 mysql master 节点信息；
    - canal.instance.dbUsername/dbPassword: 设置 username/password;
    - canal.instance.filter.regex: 设置订阅的表；
    - canal.instance.filter.black.regex: 设置不订阅的表。


### 启动

```bash
sh bin/startup.sh
```

### 查看日志

- 查看 server 日志
```bash
tail -f logs/canal/canal.log
```

- 查看 instance 的日志
```bash
tail -f logs/example/example.log
```

## 高可用模式

在单机模式下，Canal Server 宕机之后，Canal Client 不能实现自动切换。正常情况下，至少有两台 Canal Server, 一台宕机之后，另外一台自动接管，同时 Canal Client 也可感觉到 Canal Server 下线，执行切换操作。在这种工作模式下，需要引入 Zookeeper.

### 安装 Zookeeper

- 下载 Zookeeper
```bash
wget  https://downloads.apache.org/zookeeper/zookeeper-3.7.0/apache-zookeeper-3.7.0-bin.tar.gz

tar -xzvf apache-zookeeper-3.7.0-bin.tar.gz -C /data/zookeeper-3.7.0/
```

- 配置 `zoo.cfg`
```bash

cd conf/

cp zoo_sample.cfg zoo.cfg

```
    默认情况下没有 zoo.cfg 文件，我们使用 zoo_sample.cfg 生成，修改相关的配置：
```properties
# The number of milliseconds of each tick
tickTime=2000
# The number of ticks that the initial
# synchronization phase can take
initLimit=10
# The number of ticks that can pass between
# sending a request and getting an acknowledgement
syncLimit=5
# the directory where the snapshot is stored.
# do not use /tmp for storage, /tmp here is just
# example sakes.
dataDir=/data/zookeeper-3.7.0/data
# the port at which the clients will connect
clientPort=2181
# the maximum number of client connections.
# increase this if you need to handle more clients
#maxClientCnxns=60
#
# Be sure to read the maintenance section of the
# administrator guide before turning on autopurge.
#
# http://zookeeper.apache.org/doc/current/zookeeperAdmin.html#sc_maintenance
#
# The number of snapshots to retain in dataDir
#autopurge.snapRetainCount=3
# Purge task interval in hours
# Set to "0" to disable auto purge feature
#autopurge.purgeInterval=1
```
    - dataDir: 数据存储目录，建议修改。

- 修改日志目录
修改 conf/log4j.properties, 指定 Zookeeper 日志目录。
```properties
zookeeper.log.dir=/fsmeeting/zookeeper-3.7.0/logs
```

### 启动 Zookeeper
```bash
bin/zkServer.sh start
```

### 修改 Canal Server
- 修改 canal.properties
```properties
canal.zkServers=127.0.0.1:2181
```

## 客户端对接

启动了 Canal Server 及 Zookeeper 之后，应用就可以接入了。

### 引入依赖

```xml
<dependency>
    <groupId>com.alibaba.otter</groupId>
    <artifactId>canal.client</artifactId>
    <version>1.1.0</version>
</dependency>
```

### 接入服务器

- 单机直连模式
```java
String destination = "example";
String ip = "192.168.1.100";
CanalConnector connector = CanalConnectors.newSingleConnector(new InetSocketAddress(ip, 11111), destination,"canal","canal");
```

- HA 模式
```java
String destination = "example";
// 基于zookeeper动态获取canal server的地址，建立链接，其中一台server发生crash，可以支持failover
CanalConnector connector = CanalConnectors.newClusterConnector("192.168.1.100:2181", destination, "canal", "canal");
```

[源代码：https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springcloud-canal](https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springcloud-canal)

## Zookeeper 数据

Canal 使用 Zookeeper 来选主和存储数据，选主用来保证一个 `instance` 只能有一个 Canal Server 订阅，同时只能由一个 Canal Client 消费。数据主要是指消费 `instance` 的 binlog 位置信息。

- 连接 zk
```bash
bin/zkCli.sh -server 127.0.0.1:2181
```

- 查看消费的位置 position
```bash
get /otter/canal/destinations/example/1001/cursor
{"@type":"com.alibaba.otter.canal.protocol.position.LogPosition","identity":{"slaveId":-1,"sourceAddress":{"address":"localhost","port":3306}},"postion":{"gtid":"","included":false,"journalName":"mysql-bin.000001","position":26863,"serverId":1,"timestamp":1649662361000}}

```

- 查看客户端
```bash
get /otter/canal/destinations/example/1001/running
```

- 查看服务器
```bash
get /otter/canal/destinations/example/running
```

如果 Canal server 报有关 position 的异常信息，可以尝试删除 `/otter/canal/destinations/example/1001/cursor` 节点再重启。


</br>

**参考：**

----
[1]:https://github.com/alibaba/canal
[2]:https://segmentfault.com/a/1190000023297973
[3]:https://blog.csdn.net/XDSXHDYY/article/details/97825508

[1. canal github 官网][1]

[2. 阿里canal是怎么通过zookeeper实现HA机制的？][2]

[3. canal介绍及HA集群模式搭建][3]
