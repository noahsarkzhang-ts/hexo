---
title: Mysql 常用命令
date: 2024-04-12 21:27:27
updated: 2024-04-12 21:27:27
tags:
- mysql 命令
- mysqldump 命令
categories: 
- 运维
---

这篇文章主要记录用到 Mysql 命令。

<!-- more -->

## 登陆 mysql 服务器
```bash
$ mysql -h 127.0.0.1 -uroot -P 3306 -p

选项说明：
-h: 指定主机
-u: 指定用户
-P: 指定端口（大写P）
-p: 指定密码（小写p）
```

## 常用命令
**1. 查看所有的数据库**
```bash
show databases; 
```

**2. 创建一个叫test的数据库**
```bash
create database test; 
```

**3. 删除一个叫test的数据库**
```bash
drop database test;
```

**4. 选中库**
```bash
use test;
```

**5. 查看所有表**
```bash
show tables;
```

**6. 查看表结构**
```bash
desc 表名;
```

**7. 删除表**
```bash
drop table 表名; 
```

**8. 查看创建库的详细信息**
```bash
show create databases 库名;
```

**9. 查看创建表的详细信息**
```bash
show create table 表名; 
```

## 常用查询命令
**1. 插入操作**
```bash
insert into 表名(字段1，字段2...) values(值1，值2，....);
```

**2. 删除操作**
```bash
delete from 表名 where 条件;
```

**3. 更新操作**
```bash
update 表名 set字段1 = 值1, 字段2 = 值2 where 条件；
```

**4. 查询操作**
```bash
select 字段 from 表名 where 条件；
```

**5. 关联删除**
```bash
DELETE tablea FROM tablea  LEFT JOIN tableb  ON tablea.room_id = tableb.room_id WHERE tableb.room_id IS NULL;
```

## 导入及导出命令
**1. 导出**
```bash
mysqldump -uroot -p 123456 t_tablea > t_tablea.sql

选项说明：
-u:指定用户
-p:指定密码
```

**2. 导入**
```bash
mysql -h 192.168.1.118 -uuser -pWGFhJPsqaCRy_H5t -P 3306 -Dtest < proceduces.sql

选项说明：
-h: 指定主机
-u: 指定用户
-p: 指定密码
-P: 指定端口
-D: 指定数据库
```

## 用户管理及授权
**1. 用户管理**
```bash
# 添加用户，以 root 用户登陆到 mysql 
# 格式：create user new_user identified by password;
create user dev identified by '123456';
```

**2. 授权**
```bash
# grant privilegesCode on dbName.tableName to username@host;
grant all privileges on *.* to dev@'%';
flush privileges;
```

**3. 查看用户信息**
```bash
select * from mysql.db where User ='dev'
```

**4. 授权命令说明**
```bash
命令格式：grant privilegesCode on dbName.tableName to username@host;

privilegesCode 表示授予的权限类型，常用的有以下几种类型：

all privileges：所有权限；
select：读取权限；
delete：删除权限；
update：更新权限；
create：创建权限；
drop：删除数据库、数据表权限。
dbName.tableName 表示授予权限的具体库或表，常用的有以下几种选项：

*.*：授予该数据库服务器所有数据库的权限；
dbName.*：授予dbName数据库所有表的权限；
dbName.dbTable：授予数据库 dbName 中 dbTable 表的权限。
username@host 表示授予的用户以及允许该用户登录的IP地址。其中Host有以下几种类型：

localhost：只允许该用户在本地登录，不能远程登录。
%：允许在除本机之外的任何一台机器远程登录。
192.168.7.115：具体的 IP 表示只允许该用户从特定 IP 登录。

flush privileges 表示刷新权限变更。
```


