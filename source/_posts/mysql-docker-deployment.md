---
title: Mysql 5.7 Docker 部署（单机）
date: 2021-10-23 11:19:50
tags:
- mysql
- docker
categories:
- 部署
---

在项目开发中，有时需要用到 Mysql 来验证功能，使用 Docker 部署 Mysql 便是一个比较方便快捷的选择，在本文中主要是安装 Mysql 5.7，其它版本可以自行选择。

<!-- more -->

## 1. 拉取镜像

```bash
# 搜索 Mysql 镜像
$ docker search mysql

# 下载 Mysql 5.7 镜像
$ docker pull mysql:5.7

# 查看下载镜像
$ docker images

```
<font color='red'>**Mysql 官方镜像地址:**</font>
[https://hub.docker.com/_/mysql/](https://hub.docker.com/_/mysql/)

**说明：**
其它版本可以在官方网站查看

## 2. 启动镜像

```bash
# 运行 Mysql 容器
$ docker run -d -p 3306:3306 --name mysql -e MYSQL_ROOT_PASSWORD=123456 mysql:5.7

# 运行 Mysql 容器，映射目录，设置 Mysql 参数
$ docker run -d -p 3306:3306 --name mysql \
-v /data/mysql/conf:/etc/mysql \
-v /data/mysql/logs:/var/log/mysql \
-v /data/mysql/data:/var/lib/mysql \
-e MYSQL_ROOT_PASSWORD=123456 \
mysql:5.7 \
--lower_case_table_names=1 \
--character_set_server=utf8 \
--innodb_log_file_size=256m

```

**Docker 参数说明：**
- -d：后台运行容器，并返回容器 ID;
- -p：指定端口映射，格式为：主机(宿主)端口 : 容器端口；
- --name：容器名称，此处为 mysql;
- -v：宿主机和容器的目录映射关系，格式为：宿主机目录 ：容器目录；
- -e：设置环境变量，此处配置 Mysql 的 root 密码；

**Mysql 目录说明：**
- 配置文件目录：/etc/mysql
- 日志文件目录：/var/log/mysql
- 数据文件目录：/var/lib/mysql

**Mysql 参数说明（根据需要配置）：**
- lower_case_table_names=1：设置表名参数名等忽略大小写；
- max-allowed-packet=1073741824：设置最大插入和更新数据限制为 1G（1024 * 1024 * 1024 = 1073741824），单位：字节；
- character_set_server=utf8：设置 utf8 字符集；
- innodb_log_file_size=256m：设置日志文件大小；

## 3. 访问 Mysql

```bash
# 进入容器
$ docker exec -it mysql bash

# 容器内，访问 Mysql 服务
$ mysql -uroot -p123456

# 设置 root 用户允许远程访问
> GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' ;
> FLUSH PRIVILEGES;

# 宿主机上安装 Mysql 客户端
$ rpm -ivh https://repo.mysql.com/mysql57-community-release-el7-11.noarch.rpm
$ yum install mysql-community-client.x86_64

# 宿主机访问
$ mysql -h 127.0.0.1 -uroot -p123456

```

**Mysql 用户管理：**

```bash
# 添加用户，以 root 用户登陆到 mysql 
# 格式：create user new_user identified by password;
> create user dev  identified by '123456';

# 授权
# grant privilegesCode on dbName.tableName to username@host;
> grant all privileges on *.* to dev@'%';
> flush privileges;

# 查看用户信息
> select * from mysql.db where User ='dev'

```

**授权命令说明：**
命令格式：grant privilegesCode on dbName.tableName to username@host;

<font color='red'>privilegesCode</font> 表示授予的权限类型，常用的有以下几种类型：
- all privileges：所有权限；
- select：读取权限；
- delete：删除权限；
- update：更新权限；
- create：创建权限；
- drop：删除数据库、数据表权限。

<font color='red'>dbName.tableName</font> 表示授予权限的具体库或表，常用的有以下几种选项：
- \*.\*：授予该数据库服务器所有数据库的权限；
- dbName.*：授予dbName数据库所有表的权限；
- dbName.dbTable：授予数据库 dbName 中 dbTable 表的权限。

<font color='red'>username@host</font> 表示授予的用户以及允许该用户登录的IP地址。其中Host有以下几种类型：

- localhost：只允许该用户在本地登录，不能远程登录。
- %：允许在除本机之外的任何一台机器远程登录。
- 192.168.7.115：具体的 IP 表示只允许该用户从特定 IP 登录。

<font color='red'>flush privileges</font> 表示刷新权限变更。

</br>

**参考：**

----
[1]:https://hub.docker.com/_/mysql
[2]:https://www.cnblogs.com/sablier/p/11605606.html
[3]:https://www.cnblogs.com/chanshuyi/p/mysql_user_mng.html
[4]:https://linuxize.com/post/how-to-create-mysql-user-accounts-and-grant-privileges/


[1. mysql Official Image][1]

[2. 使用Docker搭建MySQL服务][2]

[3. MySQL用户管理：添加用户、授权、删除用户][3]

[4. How to Create MySQL Users Accounts and Grant Privileges][4]



