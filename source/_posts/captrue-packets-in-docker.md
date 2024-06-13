---
title: Dokcer 容器内抓包
date: 2024-06-13 19:48:37
updated: 2024-06-13 19:48:37
tags:
- 抓包
- nsenter
categories:
- 运维
---

这篇文章讲述一种在 Docker 容器内抓包的方法。

<!-- more -->
## 背景知识
nsenter 是一个可以用来进入到目标程序所在 Namespace 中运行命令的工具，一般常用于在宿主机上调试容器中运行的程序。

一个比较典型的用途就是进入容器的网络命名空间。通常容器为了轻量级，大多都是不包含较为基础网络管理调试工具，比如：ip、ping、telnet、ss、tcpdump 等命令，给调试容器内网络带来相当大的困扰。
nsenter 命令可以很方便的进入指定容器的网络命名空间，使用宿主机的命令调试容器网络。
除此以外，nsenter 还可以进入 mnt、uts、ipc、pid、user 等命名空间，以及指定根目录和工作目录。

## 抓包步骤
**1. 查看容器的进程id**
```bash
docker inspect --format "{{.State.Pid}}" <container id/name>
```

**2. 进入容器的命名空间**
```bash
nsenter -n -t <container root id>
```

**3. 容器内抓包（指定网卡和端口）**
```bash
sudo tcpdump -i lo tcp port 18051 -vvv -w 18051.out
```

内容输出到 18051.out 文件

**4. 使用 Wireshark 查看文件**