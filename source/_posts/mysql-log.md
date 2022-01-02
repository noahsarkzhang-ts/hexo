---
title: Mysql 事务日志
date: 2021-01-31 17:56:29
tags:
- redo
- undo
- binlog
- 事务
categories:
- 数据库
---

## 1. 概述
在 Mysql 中，存储有三种日志，分别是 binlog log、undo log及 redo log，其中 binlog 日志由 Mysql Server 生成，用来记录对数据库的更新操作，使用场景有主从同步及数据恢复；undo log及 redo log由 Innodb 存储引擎生成，用于保障事务进行。undo日志用于事务的回滚及MVCC，实现事务的原子性，而 redo log基于 WAL（ Write-Ahead Logging） 技术，存储事务过程中对数据表的修改，主要是数据页的修改，保证了事务的持久性。这三种日志在数据库表的更新操作（包括新增、修改及删除）中，相互配合，保障了事务的顺利执行，下图以一次数据更新操作演示了它们的工作机制。
![mysql-transaction-overview](/images/mysql-log/mysql-transaction-overview.jpg "mysql-transaction-overview")
1. undo log 存储在系统表空间中（新版的 Mysql 已经可以设置独立的表空间），对 undo log 的更改同样记录到 redo log中；
2. redo log 由独立的日志文件存储，日志文件只有追加操作，顺序写入到磁盘中，相比数据页的随机写入，具有较高的效率；
3. binlog log 配合 redo log，实现了内部的 XA 协议，保证了数据在 Innodb 及 Mysql 之间的一致性。

<!-- more -->

## 2. 基础概念
**内存缓冲池**
如果 Mysql 不使用内存缓冲池，每次读取数据时，都需要访问磁盘，会大大的增加磁盘的 IO 请求，导致效率低下；Innodb 引擎在读取数据的时候，把相应的数据和索引载入到内存的缓冲池（buffer pool）中，一定程度的提高了数据的读写速度。

**buffer pool**
用来存放各种数据的缓存，这些数据包括：索引页、数据页、undo 页、插入缓冲、自适应哈希索引、Innodb 存储的锁信息及数据字典等。工作方式是将数据库文件按照页（每页16k）读取到缓冲池，然后按照最近最少使用算法（LRU）来保留缓冲池中的缓冲数据。如果数据库文件需要修改，总是首先修改在缓冲池中的页（发生修改后即成为脏页），然后在按照一定的频率将缓冲池中的脏页刷新到文件。

**表空间**
表空间可以看作是 InnoDB 存储引擎 逻辑结构的最高层。表空间文件：InnoDB默认的表空间文件为 ibdata1。
- 页：每页数据为16kb，且不能进行修改。常见的页类型有：数据页，Undo页，系统页，事务数据页，插入缓冲位图页，插入缓冲空闲列表页，未压缩的二进制大对象页，压缩的二进制大对象页
- 区：由64个连续的页组成，每个页大小为16kb，即每个区的大小为1024kb即1MB
- 段：表空间由各个段组成，常见的段有数据段，索引段，回滚段（undo log段）等。

## 3. redo log
缓存技术是一种常用的性能优化技术，在 Mysql 中，使用 Buffer Pool 来缓存表数据，它是以数据页为单位。引入缓存，也会引入同步数据到磁盘的问题，如果每一个事务都同步数据，由于一个事务可能涉及到数据面，同步数据的操作是一个随机 IO 的操作，性能损耗很大。为了解决问题，使用了WAL（ Write-Ahead Logging）技术，引入 redo log。它的基本思想是：将数据页修改写入 redo log，日志文件是顺序写入，性能很高，同时Buffer Pool 数据异步写入磁盘。通过 redo log，即使 Mysql 宕机，也可以通过 redo log 进行恢复。

redo log由两部分组成：
1. redo log缓冲区 Log Buffer；
2. redo log日志文件，在 InnoDB 中，redo log 是固定大小的，比如可以配置为一组 4 个文件，每个文件的大小是 1GB，从头开始写，写到末尾又回到开头循环写，如下图所示：
![undo-circle](/images/mysql-log/undo-circle.png "undo-circle")

write pos 是当前记录的位置，一边写一边后移动，写到第 3 号文件末尾后就回到 0 号文件开头。checkpoint 是当前要删除的位置，也是往后推移并且循环的，删除记录前要把记录更新到数据文件。
write pos 和 checkpoint 之间的部分可以用来记录新的操作。如果 write pos 追上 checkpoint，表示文件满了，这时候不能再执行新的更新，需要先删除一些记录，把 checkpoint 推进一下。
有了 redo log，InnoDB 就可以保证即使数据库发生异常重启，之前提交的记录都不会丢失，这个能力称为 crash-safe。
另外，为了实现数据完整性，在 Buffer Pool 刷新到磁盘之前，必须先把 redo log 写入到磁盘。除了数据页，聚集索引、辅助索引以及 undo log 都需要记录到 redo log中。

**redo log的记录内容**
undo log和 redo log 本身是分开的。Innodb 的 undo log 是记录在数据文件（系统表空间）中的，而且 innodb 将 undo log 的内容看做是数据，因此对undo log本身的操作（如向undo log插入一条undo log记录等），都会记录到redo log。undo log 可以通过redo log 将其恢复。因此当数据表插入一条记录时，涉及到的操作如下所示：
- 向 undo log 插入一条 undo log 记录；
- 向 redo log 中插入一条 “插入 undo log 记录”的redo log记录；
- Buffer Pool 中插入数据 （异步同步到磁盘）；
- 向 redo log 插入一条 “insert” 的 redo log记录。


**redo log 参数**
- innodb_log_files_in_group
redo log 文件的个数，命名方式如：ib_logfile0，iblogfile1... iblogfilen。默认2个，最大100个。

- innodb_log_file_size
文件设置大小，默认值为 48M，最大值为512G，注意最大值指的是整个 redo log系列文件之和，即（innodb_log_files_in_group * innodb_log_file_size ）不能大于最大值512G。

- innodb_log_group_home_dir
文件存放路径

- innodb_log_buffer_size
redo Log 缓存区，默认8M，可设置1-8M。延迟事务日志写入磁盘，把redo log 放到该缓冲区，然后根据 innodb_flush_log_at_trx_commit参数的设置，再把日志从buffer 中flush 到磁盘中。

- innodb_flush_log_at_trx_commit
    - innodb_flush_log_at_trx_commit=1，每次commit都会把redo log从redo log buffer写入到system，并fsync刷新到磁盘文件中。
    - innodb_flush_log_at_trx_commit=2，每次事务提交时MySQL会把日志从redo log buffer写入到system，但只写入到file system buffer，由系统内部来fsync到磁盘文件。如果数据库实例crash，不会丢失redo log，但是如果服务器crash，由于file system buffer还来不及fsync到磁盘文件，所以会丢失这一部分的数据。
    - innodb_flush_log_at_trx_commit=0，事务发生过程，日志一直激励在redo log buffer中，跟其他设置一样，但是在事务提交时，不产生redo 写操作，而是MySQL内部每秒操作一次，从redo log buffer，把数据写入到系统中去。如果发生crash，即丢失1s内的事务修改操作。


## 4. undo log
Innodb 为了支持回滚和 MVCC，需要备份旧数据，undo log 就负责存储这些数据，在操作任何数据之前，首先将数据备份到undo log，然后进行数据的修改。如果出现了错误或者用户手动执行了 rollback，系统可以利用 undo log 中的备份将数据恢复到事务开始之前的状态。与 redo log不同的是，磁盘上不存在单独的 undo log 文件，它存放在数据库内部的特殊段（segment）中，这称之为 undo 段（undo segment），undo 段位于共享表空间内。
![undo-tablespace](/images/mysql-log/undo-tablespace.png "undo-tablespace")

其中32个rollback segment创建在临时表空间中，96个创建在系统表空间中，每一个rollback segment可以分配 1024个 slot，也就是可以支持96*1024个并发的事务。

### 4.1 undo log 类型
undo log有两种类型，分别是 insert undo log 和 update undo log。前者记录的是insert 语句对应的undo log，后者对应的是 update、delete 语句对应的undo log。

1. insert undo log
nsert undo log 只对事务本身可见，所以insert undo log在事务提交后可直接删除，无需通过 purge 线程执行清理操作。insert undo log 包含的字段如下：
![insert-undo-log](/images/mysql-log/insert-undo-log.jpg "insert-undo-log")

2. update undo log
执行 update 或者 delete 会产生 undo log，会影响已存在的记录，为了实现MVCC，会将同一个记录的多个版本的 undo log 串联起来，根据隔离级别的不同，会看到不同版本的数据，update undo log 不能在事务提交时立刻删除，需要等待 purge 线程进行最后的删除操作。如果是长事务，会产生大量的 undo log。undo log 包含的字段如下：
![update-undo-log](/images/mysql-log/update-undo-log.jpg "update-undo-log")

### 4.2 事务回滚
事务根据 sql的类型，进行相应的处理：
- insert sql : 在 undo log 中记录下 insert 进来的数据的 ID，当 rollback 时，根据 ID 完成精准的删除；
- delete sql ：在 undo log 中记录删除的数据，当回滚时会将删除前的数据 insert 进去；
- update sql ：在 undo log 中记录下修改前的数据，回滚时只需要反向update即可；
- select sql ：select不需要回滚。

对于 insert 类型的 undo log，由于只对当前事务可见（没有事务会对还未插入的数据感兴趣），在事务提交之后该 undo log就会被删除。但对于 update 类型的 undo log 来说，该操作会影响当前的记录，由于同时可能会有多个事务对当前记录进行 update 操作，Innodb 使用 DATA_ROLL_ID 指针将多个版本的 undo log 串联起来，而链条的起点则是行记录中的隐藏字段 DB_ROLL_PTR 。

Innodb 为每个记录中记录了三个隐藏字段：
- 6字节的事务ID（DB_TRX_ID）；
- 7字节的回滚指针（DB_ROLL_PTR）；
- 隐藏的主键id，如果没有主键，Mysql 自动生成一个主键。

以 test 表为例，我们分别进行 insert及upadte 操作来演示 undo log 日志。
```sql
CREATE TABLE `test`(
   `id` INT UNSIGNED AUTO_INCREMENT,
   `a` VARCHAR(16) NOT NULL,
   `b` VARCHAR(16) NOT NULL,
   PRIMARY KEY ( `id` )
)ENGINE=InnoDB DEFAULT CHARSET=utf8;

# 执行的操作
insert into test(id, a, b) values(1, 'redo','undo');

update test set a="redo log" where id=1;

delete from test where id=1;

```
其 undo log 链如下所示：
![undo-log-list](/images/mysql-log/undo-log-list.jpg "undo-log-list")
如上图，删除的数据行不会立刻删除，而是在行记录头信息记录了一个 deleted_flag 标志位。最终会在 purge 线程 purge undo log 的时候进行实际的删除操作，这个时候undo log也会清理掉。

## 5. binlog log
binlog 用于记录数据库执行的更新操作(不包括查询)信息，以二进制的形式保存在磁盘中。 binlog 是 Mysql 的逻辑日志，并且由 Server 层进行记录，使用任何存储引擎的 mysql 数据库都会记录 binlog log。

**binlog log 格式**
binlog log 有三种格式，分别为 STATMENT 、 ROW 和 MIXED 。
- STATMENT ： 基于 SQL 语句的复制( statement-based replication, SBR )，每一条会修改数据的 sql 语句会记录到 binlog 中；
- ROW ： 基于行的复制( row-based replication, RBR )，不记录每条 sql 语句的上下文信息，仅需记录哪条数据被修改了；
- MIXED ： 基于 STATMENT 和 ROW 两种模式的混合复制( mixed-based replication, MBR )，一般的复制使用 STATEMENT 模式保存 binlog ，对于 STATEMENT 模式无法复制的操作使用 ROW 模式保存 binlog。

**binlog log 写盘**
在写 binlog，通过参数 sync_binlog 来控制何时将 binlog fsync到磁盘。
- 0：事务提交是没有立即 fsync 文件到磁盘，而是依赖于操作系统的 fsync 机制；
- 1：每次 commit 的时候都要将 binlog fsync 磁盘；
- N：指定提交次数后，统一fsync到磁盘。

要保证数据的可持久性，sync_binlog 必须设置为 1。

**使用场景**
1. 主从同步；
2. 数据恢复。

## 6. 内部 XA 协议
从上面的内容可知，一个更新操作需要 Server 及 Innodb 协同完成，一个事务，Server 会写 binlog log， Innodb 会写 redo/undo log，这两部分是怎么保证数据的一致性及数据不丢失？在 Myslq 内部，使用了“两阶段提交”来实现这两个特性， 在此处的“两阶段提交”称为内部的 XA 协议，有别于多数据源的分布式事务。

```sql
update test set a='redo' where id=1;
```
以上面的 update 操作为例，更新的流程如下：
![two-phase-commit](/images/mysql-log/two-phase-commit.jpg "two-phase-commit")

**两阶段提交过程**
MySQL 采用了如下的过程实现内部 XA 的两阶段提交：
1. Prepare 阶段：Innodb 将回滚段设置为 prepare 状态；将 redo log 写文件并刷盘；
2. Commit 阶段：binlog 写入文件；binlog 刷盘；Innodb commit；

两阶段提交保证了事务在多个引擎和 binlog 之间的原子性，以 binlog 写入成功作为事务提交的标志，而 InnoDB 的 commit 标志并不是事务成功与否的标志。

在崩溃恢复中，是以 binlog 中的 xid 和 redo log 中的 xid 进行比较，xid 在 binlog 里存在则提交，不存在则回滚。我们来看崩溃恢复时具体的情况：
- 在 prepare 阶段崩溃，即已经写入 redolog，在写入 binlog 之前崩溃，则会回滚；
- 在 commit 阶段，当没有成功写入 binlog 时崩溃，也会回滚；
- 如果已经写入 binlog，在写入 InnoDB commit 标志时崩溃，则重新写入 commit 标志，完成提交。

## 7. 总结
这篇文章分析了 Mysql 的三种日志文件，通过日志文件，Mysql 实现的事务的原子性及持久性，其中 undo log 实现了原子性，同时也用来实现 MVCC，redo log 实现了持久性，保证在服务宕机的情况下进行事务的恢复。另外，使用两阶段提交，结合 binlog 及 redo log，保证了 Mysql Sever 及 Innodb 数据的一致性。

**参考：**

----
[1]:https://segmentfault.com/a/1190000009122071
[2]:https://mp.weixin.qq.com/s/b7Qnzh1EIM4wbExwmIkJyA 
[3]:https://www.cnblogs.com/xinysu/p/6555082.html 
[4]:http://mysql.taobao.org/monthly/2016/07/01/ 
[5]:https://segmentfault.com/a/1190000023827696
[6]:https://mp.weixin.qq.com/s/zDiuK1wTIdwK4U3W3mrIlg 
[7]:https://xie.infoq.cn/article/ed531f74ecfd44eacb1a98258 
[8]:http://mysql.taobao.org/monthly/2018/12/04/ 
[9]:http://mysql.taobao.org/monthly/2020/05/07/
[10]:https://time.geekbang.org/column/article/68633

[1. Innodb中的buffer poll和redo undo log][1]
[2. 一个线上SQL死锁异常分析：深入了解事务和锁][2]
[3. 说说MySQL中的Redo log Undo log都在干啥][3]
[4. MySQL · 特性分析 ·MySQL 5.7新特性系列三][4]
[5. 必须了解的mysql三大日志-binlog、redo log和undo log][5]
[6. 简介undo log、truncate、​以及undo log如何帮你回滚事物？][6]
[7. 洞悉 MySQL 底层架构：游走在缓冲与磁盘之间][7]
[8. MySQL的事务处理—两阶段事务提交2PC][8]
[9. MySQL · 源码分析 · 内部 XA 和组提交][9]
[10. 日志系统：一条SQL更新语句是如何执行的？][10]
