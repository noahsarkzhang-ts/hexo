---
title: mysql和ignite更新性能对比
date: 2020-05-16 16:58:02
updated: 2020-05-16 16:58:02
tags:
- mysql
- ignite
- update
- b+tree
- 固化内存
categories:
- 数据库
---

前段时间，需要对内存数据库ignite进行造型，将mysql与ignite进行了性能测试，这篇文章主要是讲在update操作上两者的差异。

<!-- more -->

我们首先假定数据库表如下：
```sql
CREATE TABLE t_token_info (
	id int(11) NOT NULL AUTO_INCREMENT,
	token_id CHAR(32) NOT NULL,
	state TINYINT(4) NOT NULL,
	server_id INT(11) NOT NULL,
	room_id INT(11) NOT NULL,
	update_date datetime NOT NULL,
	PRIMARY KEY (datetime)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE UNIQUE INDEX idx_token_id ON t_token_info (token_id);

CREATE INDEX idx_server_id ON t_token_info (server_id);

CREATE INDEX idx_room_id ON t_token_info (room_id);
```
t_token_info表上有4个索引，其中在字段id上建立主键索引，token_id上建立唯一索引，server_id和room_id上建立B+Tree索引。更新的场景包括两方面：1）在token_id上进行更新，只影响一条件记录；2）批量更新，根据server_id及room_id上进行批量更新，一次server_id操作影响的记录为2000条。下面将对mysql及ignite两种数据库进行分析 ，首先分析update操作背后的逻辑，然后再根据场景进行性能测试，最后得出结论。

## 1. Mysql
### 1.1 单条记录更新
以下面的更新为例，分析mysql的操作过程：
```sql
update t_token_info set state=1,update_date=now(),server_id=12 where  token_id=token1;
```
![mysql-update](/images/mysql-update.jpg "mysql-update")
 
涉及到的IO操作如下：
1. 读取记录：包括B+Tree索引结点及数据的读取，假定索引及数据没有加载到内存，且B+Tree索引深度为2（分支因子为500且结点大小为4K的四级树可以存储256 TB的数据），则需要3次IO操作，两次读取索引结点，一次读取数据；
2. 写入操作：包括预写日志（存储引擎的redo log日志）、binlog日志及写入的数据，至少三次IO操作，如果新写入的数据，导致B+Tree叶子结点进行分裂操作，则需要更多的IO操作；
3. 更新索引操作：因为更新的字段state及activeId是二级索引，更新这两个值，在事务中需要更新索引。更新索引又涉及到读取索引结点，更新索引的内容，等同于多次对数据进行更新操作，索引越多，则IO操作越多。

### 1.2 批量更新
```sql
update t_token_info set state=1,update_date=now() where server_id=12;
```
批量更新操作最终会转换为多次主键更新操作，这个操作由mysql服务器中执行器模块来执行，如下图所示：
![mysql-batch-update](/images/mysql-batch-update.jpg "mysql-batch-update")

批量更新的操作如下：
1. 根据activeId的索引找到更新的tokenId列表；
2. 遍历tokenId列表，取到tokenId，再根据主键索引找到token的数据；
3. 执行单个token的执行操作，直到所有的token更新完毕；
4. 批量更新的时间与影响的记录数存在线性的关系，记录数越多，时间越长。

## 2. ignite
### 2.1 ignite固化内存模型
![Durable_Memory_Diagram](/images/Durable_Memory_Diagram.png "Durable_Memory_Diagram")
iginte固化内存模型的层次：
- 内存区域：可以根据业务需要，可以将内存分为不同的大小的段，每一个区域分为不同的页，如存放key-value对（ignite本质是基于key-value的内存数据库）的数据页；B+Tree元数据页，存放每一个索引的根结点及层次信息；索引页面，存放B+Tree结点，根据索引字段进行排序，值存储数据结点的页号及偏移值；空闲页，由多个空闲链表进行维护。
- 页：分为不同类型，一般为4K，可以进行配置。

### 2.2 B+Tree和索引页面
![page-memory-b-tree](/images/page-memory-b-tree.png "page-memory-b-tree")
应用定义和使用的SQL索引是以B+Tree数据结构的形式进行维护的。每个唯一索引Ignite会实例化并且管理一个专用的B+Tree实例。
整个B+Tree的目的就是链接和排序在固化内存中分配和存储的索引页面。从内部来说，索引页面包括了定位索引值、索引指向的缓存条目在数据页面中的偏移量、还有到其它索引页面的引用（用来遍历树）等所有必要的信息，缓存的键也会存储于B+Tree，它们通过哈希值进行排序。
B+树的元页面需要获得特定B+Tree的根和它的层次，以高效地执行范围查询。比如，当执行myCache.get(keyA)时，它会触发下面的操作流程：
1. Ignite会查找myCache属于那个内存区；
在该内存区中，会定位持有myCache的键的B+Tree的元页面；
2. 根据keyA的哈希值，然后在B+Tree中检索该键所属的索引页面；
3. 如果对应的索引页面在内存/磁盘中没找到，那么意味着其在myCache中不存在，然后Ignite会返回null；
4. 如果索引页面存在，那么它会包含找到缓存条目keyA所在的数据页面的所有必要信息；
5. Ignite定位keyA所属的数据页面然后将值返回给应用。

3、数据的存储
 ![inginte-data](/images/inginte-data.png "inginte-data")
上图是一个数据页的内部结构，包括三个部分：1）Page Header；2）Data Header；3）Page Data，数据区，存放key-value对。

4、更新操作流程
```sql
update t_token_info set state=1,update_date=now(),server_id=12 where  token_id=token1;
```
在ignite内部中，一次操作为转化为缓存的一次put操作。myCache.put(keyA,valueA)操作的执行流程如下：
1. Ignite会找到myCache所属的内存区；
2. 在该内存区中，会定位持有myCache的键的B+树的元数据页面；
3. 根据keyA的哈希值，然后在B+树中检索该键所属的索引页面；
4. 如果对应的索引页面在内存或者磁盘上都没有找到，那么会从空闲列表中申请一个新的页面，成功之后，它就会被加入B+树；
5. 如果索引页面是空的（即未引用任何数据页面），根据总的缓存条目大小会从空闲列表中分配一个新的数据页面，然后在索引页面中添加到新数据页面的引用；
6. 该缓存条目会加入该数据页面。

5、批量更新
```sql
update t_token_info set state=1,update_date=now() where server_id=12;
```

在ignite中，批量更新操作，内部会转化为两个操作：1）select * from tokeninfo where activeId=12，先进行一次select操作，查询出修改的记录；2）再调用cache.invokeAll(...) 修改数据。
使用这种方式，批量更新的操作等同于：一次select操作（客户端操作） + n次单条记录的更新操作（客户端批量提交到服务器器），下面就对批量更新的性能进行验证。

## 3. 性能验证
1. 场景1：假定有20万token数据，每一个服务器上的token数为2000个；
2. 场景1：假定有20万token数据，每一个服务器上的token数为200个；
3. 场景1：假定有20万token数据，每一个服务器上的token数为20个；

分别在三种场景下，执行两种操作：1）按照唯一键token_id更新; 2）按照server_id进行批量更新。

## 4. 结论（ignite使用纯内存）
1. ignite按照主键进行更新，QPS可以达到10,000，响应时间在5~10ms，性能相比mysql，有较大的提升。
2. ignite中批量更新操作会转换为：一个select操作 + n个token的更新操作。在批量执行token前，客户端需要执行一次select操作，获取影响的记录（获取主键），然后向服务器批量提交更新操作（根据主键进行操作）。客户端执行一次select操作，性能上会有一定的影响；
3. 根据三种场景的测试，按照服务器进行批量更新操作，QPS及响应时间受两个因素影响：1）数据库服务器1S内可更新的缓存数量SC；2）一个操作影响的记录数ST。在SC确定的情况下，ST越大，QPS越小，响应时间越长，ST越小，QPS越大，响应时间越短。目前测试得出，在单台服务上1S可以完成对20，000个缓存的更新操作，如果ST为2000个，QPS只能达到10，受SC影响，如果ST为200个，QPS增大10倍，响应时间减少到10/1。

**参考：**

----
[1]:https://www.ignite-service.cn/doc/java/DurableMemory.html#_1-%E5%9B%BA%E5%8C%96%E5%86%85%E5%AD%98
[2]:https://cwiki.apache.org/confluence/display/IGNITE/Ignite+Durable+Memory+-+under+the+hood


[1. 固化内存][1]

[2. Ignite Durable Memory - under the hood][2]


