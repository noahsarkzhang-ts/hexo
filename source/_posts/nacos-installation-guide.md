---
title: Nacos 安装部署
date: 2022-03-05 16:34:09
updated: 2022-03-05 16:34:09
tags:
- nacos
categories:
- 部署
---

Nacos 可以用来作配置中心和服务注册中心，在微服务系统中有着比较的作用。它可以单机部署和集群部署，在生产环境中建议使用集群部署，在这里，主要是它来搭建实现环境，用单机即可。

<!-- more -->

## Nacos 介绍

阿里的介绍如下：
> Nacos 致力于帮助您发现、配置和管理微服务。Nacos 提供了一组简单易用的特性集，帮助您快速实现动态服务发现、服务配置、服务元数据及流量管理。
> Nacos 帮助您更敏捷和容易地构建、交付和管理微服务平台。 Nacos 是构建以“服务”为中心的现代应用架构 (例如微服务范式、云原生范式) 的服务基础设施。

具体的详情可以参考官方网站：**[Nacos 官网](https://nacos.io/zh-cn/docs/what-is-nacos.html)**

## 版本选择

二进制版本可在 github 下载，下载地址为：[https://github.com/alibaba/nacos/releases](https://github.com/alibaba/nacos/releases)
当前最新稳定版本为 1.4.3, 也可以根据需求下载指定版本。在这里，我们下载最新版本。

## 前置依赖

Nacos 依赖 Java 环境来运行。如果您是从代码开始构建并运行 Nacos，还需要为此配置 Maven 环境，请确保是在以下版本环境中安装使用:

- 64 bit OS，支持 Linux/Unix/Mac/Windows，推荐选用 Linux/Unix/Mac。
- 64 bit JDK 1.8+；下载 & 配置。
- Maven 3.2.x+；下载 & 配置。

为了简单起见，下载二进制版本即可。

## 配置 Mysql

在 0.7 版本之前，在单机模式时 Nacos 使用嵌入式数据库实现数据的存储，不方便观察数据存储的基本情况。0.7 版本增加了支持 Mysql 数据源能力，具体的操作步骤：
1. 安装数据库，版本要求：5.6.5+ ; 
2. 初始化 Mysql 数据库，数据库初始化文件：conf/nacos-mysql.sql, 数据库名为：nacos_config; 
3. 修改 conf/application.properties 文件，增加支持 Mysql 数据源配置（目前只支持mysql），添加 Mysql 数据源的 url、用户名和密码。

```properties
### If use MySQL as datasource:
spring.datasource.platform=mysql

### Count of DB:
db.num=1

### Connect URL of DB:
db.url.0=jdbc:mysql://127.0.0.1:3306/nacos_config?characterEncoding=utf8&connectTimeout=1000&socketTimeout=3000&autoReconnect=true&useUnicode=true&useSSL=false&serverTimezone=UTC
db.user.0=root
db.password.0=123456
```

## 启动服务器
### Linux/Unix/Mac
启动命令(standalone 代表着单机模式运行，非集群模式):

```bash
sh startup.sh -m standalone
```

### Windows
启动命令(standalone代表着单机模式运行，非集群模式):

```bash
startup.cmd -m standalone
```

### 登陆

启动服务之后，使用 `http://localhost:8848/nacos/#/login` 地址登陆。

![nacos](/images/spring-cloud/nacos-login.jpg "nacos-login")

默认用户名和密码：nacos/nacos

</br>

**参考：**

----
[1]:https://nacos.io/zh-cn/docs/quick-start.html
[2]:https://nacos.io/zh-cn/docs/deployment.html


[1. Nacos 快速开始][1]

[2. Nacos部署环境][2]


