---
title: Redis 6.2 Docker 部署（单机）
date: 2021-10-23 17:36:51
tags:
- redis
- docker
categories:
- 部署
---

## 1. 拉取镜像

```bash
# 搜索 Mysql 镜像
$ docker search mysql

# 下载 Redis 镜像
$ docker pull mysql:6.2

# 查看下载镜像
$ docker images

```

## 2. 创建挂载目录

在宿主机上创建 Reids 配置文件目录及数据目录。
```bash
$ cd /app/redis6.2

# 创建 conf & data 目录
$ mkdir conf
$ mkdir data

# 下载 redis 配置文件
$ cd conf
$ wget wget http://download.redis.io/redis-stable/redis.conf

```

## 3. 修改 redis.conf 文件
```bash

# 注释 bind,否则只允许本机访问
# bind 127.0.0.1 -::1

# 关闭安全模式
protected-mode no

# 开启持久化（可选）
appendonly yes

# 后台运行
daemonize yes

# 日志文件
logfile "access.log"

# 设置访问密码
requirepass 123456

```

## 4. 启动 Redis
```bash
# 启动 Redis 6.2
$ docker run -d \
-p 6379:6379 --name redis6.2 \
-v /app/redis6.2/conf/redis.conf:/etc/redis/redis.conf \
-v /app/redis6.2/data:/data \
--privileged=true redis:6.2 redis-server \ 
/etc/redis/redis.conf --appendonly yes
```

**参数说明：**
- –name：容器名称；
- -p：端口映射，宿主机端口:容器端口；
- -v：挂载宿主机目录，宿主机目录(或文件):容器目录(或文件)；
- -d：后台运行
- redis-server --appendonly yes： 在容器执行redis-server启动命令，并打开redis持久化配置

**说明：**
Redis docker 镜像默认无配置文件。

## 5. 访问 Redis 容器
执行 `docker exec -it redis6.2 redis-cli` 命令，进入终端。

```bash
# 查看容器列表
$ docker ps

# 进入容器
$ docker exec -it redis6.2 redis-cli 
127.0.0.1:6379> 

# 或者使用 bash 命令
$ docker exec -it redis6.2 bash
$ redis-cli
```
