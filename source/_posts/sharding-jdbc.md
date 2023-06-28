---
title: Springboot 系列：Sharding-JDBC
date: 2022-05-15 09:51:11
updated: 2022-05-15 09:51:11
tags:
- sharding jdbc
- 分库
- 分表
categories:
- Springboot
---

分库主要是解决单库读写能力不足的问题，分表主要是解决单表数据量过大的问题，读写分离则是在读多写少场景下的一种优化方案。Sharding-JDBC 作为数据库中间件，提供了这三个功能（Sharding-JDBC 的功能不仅限于此）。这篇文章则主要讲述在 Springboot 下如何使用 Sharding-JDBC 来解决分库/分表及读写分离的问题。

<!-- more -->

## 概述

ShardingSphere 是一套开源的分布式数据库中间件解决方案组成的生态圈，它由 Sharding-JDBC、Sharding-Proxy 和 Sharding-Sidecar（计划中）这3款相互独立的产品组成。 他们均提供标准化的数据分片、分布式事务和数据库治理功能，可适用于如 Java 同构、异构语言、云原生等各种多样化的应用场景。

- Sharding-JDBC: 定位为轻量级 Java 框架，在 Java 的 JDBC 层提供的额外服务。 它使用客户端直连数据库，以 jar 包形式提供服务，无需额外部署和依赖，可理解为增强版的 JDBC 驱动，完全兼容 JDBC 和各种 ORM 框架；
- Sharding-Proxy: 定位为透明化的数据库代理端，提供封装了数据库二进制协议的服务端版本，用于完成对异构语言的支持。 目前先提供 MySQL/PostgreSQL 版本，它可以使用任何兼容 MySQL/PostgreSQL 协议的访问客户端(如：MySQL Command Client, MySQL Workbench, Navicat等 )操作数据，对 DBA 更加友好；
- Sharding-Sidecar: 定位为 Kubernetes 的云原生数据库代理，以 Sidecar 的形式代理所有对数据库的访问。 通过无中心、零侵入的方案提供与数据库交互的的啮合层，即 Database Mesh，又可称数据网格。

## 核心概念

### 数据分表

数据分片指按照某个维度将存放在单一数据库中的数据分散地存放至多个数据库或表中以达到提升性能瓶颈以及可用性的效果。

### 读写分离

对于同一时刻有大量并发读操作和较少写操作类型的应用系统来说，将数据库拆分为主库和从库，主库负责处理事务性的增删改操作，从库负责处理查询操作，能够有效的避免由数据更新导致的行锁，使得整个系统的查询性能得到极大的改善。

与将数据根据分片键打散至各个数据节点的水平分片不同，读写分离则是根据 SQL 语义的分析，将读操作和写操作分别路由至主库与从库。

### 逻辑表

水平拆分的数据库（表）的相同逻辑和数据结构表的总称。例：订单数据根据主键尾数拆分为 10 张表，分别是 t_order_0 到 t_order_9，他们的逻辑表名为 t_order.

### 真实表

在分片的数据库中真实存在的物理表。即上个示例中的 t_order_0 到 t_order_9.

### 数据节点

数据分片的最小单元。由数据源名称和数据表组成，例：ds_0.t_order_0.

### 绑定表

指分片规则一致的主表和子表。例如：t_order 表和 t_order_item 表，均按照 order_id 分片，则此两张表互为绑定表关系。绑定表之间的多表关联查询不会出现笛卡尔积关联，关联查询效率将大大提升。

### 广播表

指所有的分片数据源中都存在的表，表结构和表中的数据在每个数据库中均完全一致。适用于数据量不大且需要与海量数据的表进行关联查询的场景，例如：字典表。

## 配置数据库

以 `t_order` 例，如下图所示：

![sharding-jdbc-example](/images/spring-cloud/sharding-jdbc-example.jpg "sharding-jdbc-example")

- `t_order` 数据库有两个分片，以 `user_id` 为分片键，同一个用户的所有订单在一个库里。每一个分片有一个 slave 结点，实现主从复制；
- `t_order` 以 `order_id ` 为分片键，分为两个表；
- `t_order_item` 与 `t_order` 是绑定关系，有同样的分片键；
- `t_config` 为广播表，每个库都会 copy 一份数据。

### 主从配置

需要建立 4 个库，分别是 master0, master1, slave0, slave1, 其中 master0, master1 是主库，slave1 是 master0 的从库，slave1 是 master1 的从库。在这里，我们使用 docker 来安装 4 个库，以 master0, slave0 为例。

**安装数据库**

```bash
# 创建 master0
$ docker run -d -p 3307:3306 --name mysql-master0 \
 -v /data/mysql/master0/conf:/etc/mysql \
 -v /data/mysql/master0/logs:/var/log/mysql \
 -v /data/mysql/master0/data:/var/lib/mysql \
 -e MYSQL_ROOT_PASSWORD=123456 \
 mysql:5.7 \
 --lower_case_table_names=1 \
 --character_set_server=utf8 \
 --innodb_log_file_size=256m

# 创建 slave0
$ docker run -d -p 3308:3306 --name mysql-slave0 \
 -v /data/mysql/slave0/conf:/etc/mysql \
 -v /data/mysql/slave0/logs:/var/log/mysql \
 -v /data/mysql/slave0/data:/var/lib/mysql \
 -e MYSQL_ROOT_PASSWORD=123456 \
 mysql:5.7 \
 --lower_case_table_names=1 \
 --character_set_server=utf8 \
 --innodb_log_file_size=256m

# 创建 master1
$ docker run -d -p 3309:3306 --name mysql-master1 \
 -v /data/mysql/master1/conf:/etc/mysql \
 -v /data/mysql/master1/logs:/var/log/mysql \
 -v /data/mysql/master1/data:/var/lib/mysql \
 -e MYSQL_ROOT_PASSWORD=123456 \
 mysql:5.7 \
 --lower_case_table_names=1 \
 --character_set_server=utf8 \
 --innodb_log_file_size=256m

# 创建 slave1
$ docker run -d -p 3310:3306 --name mysql-slave1 \
 -v /data/mysql/slave1/conf:/etc/mysql \
 -v /data/mysql/slave1/logs:/var/log/mysql \
 -v /data/mysql/slave1/data:/var/lib/mysql \
 -e MYSQL_ROOT_PASSWORD=123456 \
 mysql:5.7 \
 --lower_case_table_names=1 \
 --character_set_server=utf8 \
 --innodb_log_file_size=256m
 
```

Mysql 配置参数：
- 配置文件目录：/etc/mysql
- 日志文件目录：/var/log/mysql
- 数据文件目录：/var/lib/mysql

**配置 my.cnf**

master0 `my.cnf` 配置：
```properties
[mysqld]
log-bin=mysql-bin # 开启 binlog
binlog-format=ROW # 选择 ROW 模式
server_id=1 # 配置 MySQL replaction 需要定义。
```

slave0 `my.cnf` 配置：
```properties
[mysqld]
log-bin=mysql-bin # 开启 binlog
binlog-format=ROW # 选择 ROW 模式
server_id=2 # 配置 MySQL replaction 需要定义，不要和 master 的 slaveId 重复

## relay_log 配置中继日志
relay_log=mysql-relay-bin

## 跳过主从复制中遇到的所有错误或指定类型的错误,避免slave端复制中断
## 如:1062错误是指一些主键重复,1032错误是因为主从数据库数据不一致
slave_skip_errors=1062
```

**获取 master position**

进入主结点 master0, 获取 master 状态。

```bash
# 进入容器
$ docker exec -it mysql-master0 /bin/bash

# 容器内，访问 Mysql 服务
$ mysql -uroot -p123456

# 创建 slave 用户，并赋予权限
mysql> CREATE USER slave IDENTIFIED BY 'slave';  
mysql> GRANT SELECT, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'slave'@'%';
mysql> FLUSH PRIVILEGES;

# 获取 master 状态
mysql> show master status;
+------------------+----------+--------------+------------------+-------------------+
| File             | Position | Binlog_Do_DB | Binlog_Ignore_DB | Executed_Gtid_Set |
+------------------+----------+--------------+------------------+-------------------+
| mysql-bin.000003 |      777 |              |                  |                   |
+------------------+----------+--------------+------------------+-------------------+
1 row in set (0.00 sec)

```

记下 `File` 和 `Position` 信息，后面会用到。

**获取 master0 ip 信息**

```bash
$ docker inspect --format='{{.NetworkSettings.IPAddress}}' mysql-master
172.17.0.4
```

**开启主从功能**

进入从结点，开启主从功能；
```bash
# 进入容器
$ docker exec -it mysql-master0 /bin/bash

# 容器内，访问 Mysql 服务
$ mysql -uroot -p123456

# 根据 master0 ip, position 及 slave 用户设置主从
mysql> change master to master_host='172.17.0.4',master_user='slave',master_password='slave',master_log_file='mysql-bin.000003',master_log_pos=777;

# 启动主从功能
mysql> start slave;

# 查看从结点信息
mysql> show slave status\G

```

### 初始化 Sql 脚本

```sql
CREATE DATABASE IF NOT EXISTS ds0 DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_bin;

-- ----------------------------
-- Table structure for t_config
-- ----------------------------
DROP TABLE IF EXISTS `t_config`;
CREATE TABLE `t_config` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `code` varchar(32) NOT NULL,
  `name` varchar(32) NOT NULL,
  `create_date` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for t_order_0
-- ----------------------------
DROP TABLE IF EXISTS `t_order_0`;
CREATE TABLE `t_order_0` (
  `order_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `order_no` varchar(32) NOT NULL,
  `user_id` int(11) NOT NULL,
  `name` varchar(50) NOT NULL,
  `price` decimal(10,2) NOT NULL,
  PRIMARY KEY (`order_id`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for t_order_1
-- ----------------------------
DROP TABLE IF EXISTS `t_order_1`;
CREATE TABLE `t_order_1` (
  `order_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `order_no` varchar(32) NOT NULL,
  `user_id` int(11) NOT NULL,
  `name` varchar(50) NOT NULL,
  `price` decimal(10,2) NOT NULL,
  PRIMARY KEY (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for t_order_item_0
-- ----------------------------
DROP TABLE IF EXISTS `t_order_item_0`;
CREATE TABLE `t_order_item_0` (
  `item_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `order_id` bigint(20) NOT NULL,
  `order_no` varchar(32) NOT NULL,
  `user_id` int(11) NOT NULL,
  `item_name` varchar(50) NOT NULL,
  `price` decimal(10,2) NOT NULL,
  PRIMARY KEY (`item_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for t_order_item_1
-- ----------------------------
DROP TABLE IF EXISTS `t_order_item_1`;
CREATE TABLE `t_order_item_1` (
  `item_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `order_id` bigint(20) NOT NULL,
  `order_no` varchar(32) NOT NULL,
  `item_name` varchar(50) NOT NULL,
  `user_id` int(11) NOT NULL,
  `price` decimal(10,2) NOT NULL,
  PRIMARY KEY (`item_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

```

## Java 实例

### 引入依赖

```xml
<!-- 依赖包版本管理 -->
<properties>
    <maven.compiler.source>1.8</maven.compiler.source>
    <maven.compiler.target>1.8</maven.compiler.target>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>

    <!-- spring-boot version -->
    <spring-boot.version>2.2.5.RELEASE</spring-boot.version>
	
    <!-- sharding-sphere version -->	
    <sharding-sphere.version>4.1.1</sharding-sphere.version>

    <!-- mysql version -->	
    <mysql.driver.version>8.0.16</mysql.driver.version>
    <mybatis-spring-boot.version>1.3.5</mybatis-spring-boot.version>

    <!-- druid version -->		
    <druid.version>1.2.6</druid.version>
</properties>


<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter</artifactId>
    </dependency>

    <!-- shardingsphere -->
    <dependency>
        <groupId>org.apache.shardingsphere</groupId>
        <artifactId>sharding-jdbc-spring-boot-starter</artifactId>
    </dependency>

    <!-- mysql driver -->
    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
    </dependency>

    <!-- druid -->
    <dependency>
        <groupId>com.alibaba</groupId>
        <artifactId>druid</artifactId>
    </dependency>

    <!-- mybatis -->
    <dependency>
        <groupId>org.mybatis.spring.boot</groupId>
        <artifactId>mybatis-spring-boot-starter</artifactId>
    </dependency>

    <dependency>
        <artifactId>slf4j-api</artifactId>
        <groupId>org.slf4j</groupId>
        <version>1.7.26</version>
    </dependency>

</dependencies>
```

**说明：**
使用 `druid` 连接池不需要引入 `druid-spring-boot-starter` 包，只要引入 `druid` 即可，否则加载数据源不成功。

### 定义数据库对象

以 `t_order` 为例。

```java
public class Order {

    private Long orderId;

    private String orderNo;

    private Integer userId;

    private String name;

    private BigDecimal price;

    public Order() {
    }

    ...
```

### 定义 Mapper 对象

```java
public interface OrderMapper {

    @Select("SELECT * FROM t_order")
    List<Order> getAll();

    @Select("SELECT * FROM t_order WHERE order_id = #{orderId}")
    Order get(Long orderId);

    @Insert("INSERT INTO t_order(order_no,user_id,name,price) VALUES(#{orderNo},#{userId}, #{name}, #{price})")
    @Options(useGeneratedKeys = true, keyProperty = "orderId")
    void insert(Order order);

    @Update("UPDATE t_order SET name=#{name},price=#{price} WHERE order_id =#{orderId}")
    void update(Order order);

    @Delete("DELETE FROM t_order WHERE order_id =#{orderId}")
    void delete(Long orderId);

    @Select(
            "<script>"
            + "select "
            + "o.order_id as orderId, "
            + "o.order_no as orderNo, "
            + "o.user_id as userId, "
            + "o.name as name,"
            + "o.price as price,"
            + "oi.item_id as itemId "
            + "from t_order o "
            + "left join t_order_item oi on o.order_id = oi.order_id "
            + "where o.order_id in "
            + "<foreach collection='orderIds' item='orderId' index='index' "
            + "  open='(' close=')' separator=','> "
            + "  #{orderId} "
            + "</foreach>"
            + "</script>"
            )
    List<OrderDetail> getOrderDetails(@Param("orderIds") List<Long> orderIds);    
}
```

**说明：**
- 若数据表主键由 Sharding-JDBC 生成，则在插入操作中不应包含主键，该主键由 Shardings-JDBC 生成，并改写 Sql 自动插入到数据库中，如此处的 `t_order`；
- 可通过 `Options(useGeneratedKeys = true, keyProperty = "orderId")` 选项，返回插入的主键。

### Shardings-JDBC 配置

```properties
# 定义数据源
spring.shardingsphere.datasource.names=master0,slave0,master1,slave1

# 定义数据源 master0
spring.shardingsphere.datasource.master0.type=com.alibaba.druid.pool.DruidDataSource
spring.shardingsphere.datasource.master0.driver-class-name=com.mysql.cj.jdbc.Driver
spring.shardingsphere.datasource.master0.url=jdbc:mysql://192.168.1.100:3307/ds0?serverTimezone=Asia/Shanghai&useUnicode=true&characterEncoding=utf-8&useSSL=false
spring.shardingsphere.datasource.master0.username=root
spring.shardingsphere.datasource.master0.password=123456

# 定义数据源 slave0
spring.shardingsphere.datasource.slave0.type=com.alibaba.druid.pool.DruidDataSource
spring.shardingsphere.datasource.slave0.driver-class-name=com.mysql.cj.jdbc.Driver
spring.shardingsphere.datasource.slave0.url=jdbc:mysql://192.168.1.100:3308/ds0?serverTimezone=Asia/Shanghai&useUnicode=true&characterEncoding=utf-8&useSSL=false
spring.shardingsphere.datasource.slave0.username=root
spring.shardingsphere.datasource.slave0.password=123456

# 定义数据源 master1
spring.shardingsphere.datasource.master1.type=com.alibaba.druid.pool.DruidDataSource
spring.shardingsphere.datasource.master1.driver-class-name=com.mysql.cj.jdbc.Driver
spring.shardingsphere.datasource.master1.url=jdbc:mysql://192.168.1.100:3309/ds1?serverTimezone=Asia/Shanghai&useUnicode=true&characterEncoding=utf-8&useSSL=false
spring.shardingsphere.datasource.master1.username=root
spring.shardingsphere.datasource.master1.password=123456

# 定义数据源 slave1
spring.shardingsphere.datasource.slave1.type=com.alibaba.druid.pool.DruidDataSource
spring.shardingsphere.datasource.slave1.driver-class-name=com.mysql.cj.jdbc.Driver
spring.shardingsphere.datasource.slave1.url=jdbc:mysql://192.168.1.100:3310/ds1?serverTimezone=Asia/Shanghai&useUnicode=true&characterEncoding=utf-8&useSSL=false
spring.shardingsphere.datasource.slave1.username=root
spring.shardingsphere.datasource.slave1.password=123456

# 定义 t_order 结点
spring.shardingsphere.sharding.tables.t_order.actual-data-nodes=ds$->{0..1}.t_order_$->{0..1}

# 定义 t_order 分库策略，以 user_id 为分片键
spring.shardingsphere.sharding.tables.t_order.database-strategy.inline.sharding-column=user_id
spring.shardingsphere.sharding.tables.t_order.database-strategy.inline.algorithm-expression=ds$->{user_id % 2}

# 定义 t_order 分表策略，以 order_id 为分片键
spring.shardingsphere.sharding.tables.t_order.table-strategy.inline.sharding-column=order_id
spring.shardingsphere.sharding.tables.t_order.table-strategy.inline.algorithm-expression=t_order_$->{order_id % 2}

# 定义 order_id 键的生成策略，使用 SNOWFLAKE 算法
spring.shardingsphere.sharding.tables.t_order.key-generator.column=order_id
spring.shardingsphere.sharding.tables.t_order.key-generator.type=SNOWFLAKE

# 定义 t_order_item 结点
spring.shardingsphere.sharding.tables.t_order_item.actual-data-nodes=ds$->{0..1}.t_order_item_$->{0..1}

# 定义 t_order_item 分库策略，以 user_id 为分片键
spring.shardingsphere.sharding.tables.t_order_item.database-strategy.inline.sharding-column=user_id
spring.shardingsphere.sharding.tables.t_order_item.database-strategy.inline.algorithm-expression=ds$->{user_id % 2}

# 定义 t_order_item 分表策略，以 order_id 为分片键
spring.shardingsphere.sharding.tables.t_order_item.table-strategy.inline.sharding-column=order_id
spring.shardingsphere.sharding.tables.t_order_item.table-strategy.inline.algorithm-expression=t_order_item_$->{order_id % 2}

# 定义 item_id 键的生成策略，使用 SNOWFLAKE 算法
spring.shardingsphere.sharding.tables.t_order_item.key-generator.column=item_id
spring.shardingsphere.sharding.tables.t_order_item.key-generator.type=SNOWFLAKE

# 设置 t_ordem, t_order_item 为绑定关系
spring.shardingsphere.sharding.binding-tables=t_order,t_order_item

# 设置 t_config 为广播表
spring.shardingsphere.sharding.broadcast-tables=t_config

# 定义名为 ds0 主从数据源，该数据源在数据库结点中引用
spring.shardingsphere.sharding.master-slave-rules.ds0.master-data-source-name=master0
spring.shardingsphere.sharding.master-slave-rules.ds0.slave-data-source-names=slave0

# 定义名为 ds1 主从数据源，该数据源在数据库结点中引用
spring.shardingsphere.sharding.master-slave-rules.ds1.master-data-source-name=master1
spring.shardingsphere.sharding.master-slave-rules.ds1.slave-data-source-names=slave1

# 输出改造后 sql
spring.shardingsphere.props.sql.show=true

# 设置 mybatis 对象别名目录
mybatis.type-aliases-package=org.noahsark.shardingjdbc.model

# 设置日志文件
logging.file.name=logs/jdbc.log
```

### 测试代码

**插入 Order 表**

```java
@Test
public void insertTest() {
    Integer orderNo;
    Integer userId;

    int num = 100;

    Order order = null;
    OrderItem orderItem = null;

    for (int i = 0; i < num; i++) {
        order = new Order();
        orderNo = random.nextInt(10000) + 1000;
        userId = random.nextInt(10000) + 10000;

        order.setName("order-" + orderNo);
        order.setOrderNo("" + orderNo);
        order.setUserId(userId);
        order.setPrice(new BigDecimal("1000.5"));

        orderMapper.insert(order);

        orderItem = new OrderItem();
        orderItem.setOrderId(order.getOrderId());
        orderItem.setOrderNo(order.getOrderNo());
        orderItem.setUserId(order.getUserId());
        orderItem.setItemName("Item" + random.nextInt(10000));
        orderItem.setPrice(new BigDecimal(1000.5));

        orderItemMapper.insert(orderItem);

        System.out.println("orderId:" + order.getOrderId());
        System.out.println("itemId:" + orderItem.getItemId());

    }
}
```

根据 `userId` 进行的分库，`orderId` 进行分表，`order` 表数据均衡分布到两个主库中。

**关联查询**

根据 `orderId` 列表 对 `order`, `order_item` 进行关联查询。

```java
@Test
public void getOrderDetailsTest() {

    List<Long> list = Arrays.asList(732635574220881920L, 732635574220881920L);

    List<OrderDetail> orderDetails = orderMapper.getOrderDetails(list);

    for (OrderDetail orderDetail : orderDetails) {
        System.out.println("orderDetail = " + orderDetail);
    }
}
```

关联查询因为没有分库的信息，所以会查询所有的分库（如果设置了读写分离，则从主库的从查询），再将所有分库的结果进行聚合。在每一个分库中查询，又分为两种情况：1) 绑定表；2) 非绑定表；

**绑定表**

```text
2022-05-21 15:38:24.602 [main] INFO  ShardingSphere-SQL - Logic SQL: select o.order_id as orderId, o.order_no as orderNo, o.user_id as userId, o.name as name,o.price as price,oi.item_id as itemId from t_order o left join t_order_item oi on o.order_id = oi.order_id where o.order_id in  (     ?  ,    ?  ) 

2022-05-21 15:38:24.603 [main] INFO  ShardingSphere-SQL - Actual SQL: slave0 ::: select o.order_id as orderId, o.order_no as orderNo, o.user_id as userId, o.name as name,o.price as price,oi.item_id as itemId from t_order_0 o left join t_order_item_0 oi on o.order_id = oi.order_id where o.order_id in  (     ?  ,    ?  ) ::: [732635574220881920, 732635574220881920] 
2022-05-21 15:38:24.603 [main] INFO  ShardingSphere-SQL - Actual SQL: slave1 ::: select o.order_id as orderId, o.order_no as orderNo, o.user_id as userId, o.name as name,o.price as price,oi.item_id as itemId from t_order_0 o left join t_order_item_0 oi on o.order_id = oi.order_id where o.order_id in  (     ?  ,    ?  ) ::: [732635574220881920, 732635574220881920] 

```

在两个分库两个分表的情况下，这个关联查询转化为两个查询，一个分库一个查询。由于 `orderId` 是分表键，可以定位到数据位于 `t_order_0` 和 `t_order_item_0` 表中，直接查询即可。

**非绑定表**

```text
2022-05-21 15:39:34.135 [main] INFO  ShardingSphere-SQL - Logic SQL: select o.order_id as orderId, o.order_no as orderNo, o.user_id as userId, o.name as name,o.price as price,oi.item_id as itemId from t_order o left join t_order_item oi on o.order_id = oi.order_id where o.order_id in  (     ?  ,    ?  ) 

2022-05-21 15:39:34.136 [main] INFO  ShardingSphere-SQL - Actual SQL: slave0 ::: select o.order_id as orderId, o.order_no as orderNo, o.user_id as userId, o.name as name,o.price as price,oi.item_id as itemId from t_order_0 o left join t_order_item_1 oi on o.order_id = oi.order_id where o.order_id in  (     ?  ,    ?  ) ::: [732635574220881920, 732635574220881920] 
2022-05-21 15:39:34.136 [main] INFO  ShardingSphere-SQL - Actual SQL: slave0 ::: select o.order_id as orderId, o.order_no as orderNo, o.user_id as userId, o.name as name,o.price as price,oi.item_id as itemId from t_order_0 o left join t_order_item_0 oi on o.order_id = oi.order_id where o.order_id in  (     ?  ,    ?  ) ::: [732635574220881920, 732635574220881920] 
2022-05-21 15:39:34.136 [main] INFO  ShardingSphere-SQL - Actual SQL: slave1 ::: select o.order_id as orderId, o.order_no as orderNo, o.user_id as userId, o.name as name,o.price as price,oi.item_id as itemId from t_order_0 o left join t_order_item_1 oi on o.order_id = oi.order_id where o.order_id in  (     ?  ,    ?  ) ::: [732635574220881920, 732635574220881920] 
2022-05-21 15:39:34.136 [main] INFO  ShardingSphere-SQL - Actual SQL: slave1 ::: select o.order_id as orderId, o.order_no as orderNo, o.user_id as userId, o.name as name,o.price as price,oi.item_id as itemId from t_order_0 o left join t_order_item_0 oi on o.order_id = oi.order_id where o.order_id in  (     ?  ,    ?  ) ::: [732635574220881920, 732635574220881920] 
```

在两个分库两个分表的情况下，这个关联查询转化为四个查询。在一个分库中，根据分表键 `orderId`, 可以定位到这两个 `orderId` 位于 `t_order_0 ` 中，由于 `t_order_0` 和 `t_order_item_0` 表没有绑定关系，所以 `t_order_0` 表需要与所有 `t_order_item` 表进行关联查询，最终需要执行四个查询。

**插入广播表**

```java
@Test
public void insertConfigTest() {

    Config config = new Config();
    config.setCode("OS");
    config.setName("os");
    config.setCreateDate(new Date());

    configMapper.insert(config);

    System.out.println("config:" + config);

}

```

插入广播表会在所有分库中执行插入操作。

```text
2022-05-21 15:40:27.425 [main] INFO  ShardingSphere-SQL - Logic SQL: INSERT INTO t_config(code,name,create_date) VALUES(?, ?, ?) 

2022-05-21 15:40:27.425 [main] INFO  ShardingSphere-SQL - Actual SQL: master0 ::: INSERT INTO t_config(code,name,create_date) VALUES(?, ?, ?) ::: [VISION, vision, 2022-05-21 15:40:27.155] 
2022-05-21 15:40:27.425 [main] INFO  ShardingSphere-SQL - Actual SQL: master1 ::: INSERT INTO t_config(code,name,create_date) VALUES(?, ?, ?) ::: [VISION, vision, 2022-05-21 15:40:27.155] 
config:Config{id=null, code='VISION', name='vision', createDate=Sat May 21 15:40:27 CST 2022}
```

如上所述，向 `t_config` 中插入一条数据，会中所有分库的主库中执行操作。

**查询所有数据**

```java
@Test
public void getAllTest() {

    List<Order> list = orderMapper.getAll();

    for (Order order : list) {
        System.out.println("order = " + order);
    }
}
```

查询语句中如果没有分库分表健，会默认查询所有表。

```text
2022-05-21 15:41:16.781 [main] INFO  ShardingSphere-SQL - Logic SQL: SELECT * FROM t_order 

2022-05-21 15:41:16.782 [main] INFO  ShardingSphere-SQL - Actual SQL: slave0 ::: SELECT * FROM t_order_0 
2022-05-21 15:41:16.782 [main] INFO  ShardingSphere-SQL - Actual SQL: slave0 ::: SELECT * FROM t_order_1 
2022-05-21 15:41:16.782 [main] INFO  ShardingSphere-SQL - Actual SQL: slave1 ::: SELECT * FROM t_order_0 
2022-05-21 15:41:16.782 [main] INFO  ShardingSphere-SQL - Actual SQL: slave1 ::: SELECT * FROM t_order_1
```

[工程代码：https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springcloud-sharding-jdbc](https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springcloud-sharding-jdbc)

</br>

**参考：**

----
[1]:https://shardingsphere.apache.org/document/legacy/4.x/document/cn/overview/
[2]:https://shardingsphere.apache.org/document/legacy/4.x/document/cn/manual/sharding-jdbc/configuration/config-spring-boot/
[3]:https://segmentfault.com/a/1190000038225441
[4]:https://www.cnblogs.com/crazymakercircle/p/15955254.html

[1. ShardingSphere 概览][1]

[2. Sharding-JDBC > 配置手册 > Spring Boot配置][2]

[3. 分库分表神器 Sharding-JDBC，几千万的数据你不搞一下？][3]

[4. Sharding-JDBC 实战（史上最全）][4]


