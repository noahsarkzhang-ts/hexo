---
title: 网络流量工具
date: 2023-02-12 10:04:27
tags:
- iftop
- nload
- nethogs
categories:
- 工具
---

本文介绍三个用来检测网络流量的常用工具：1) 查看整体流量：nload; 2) 按进程查看流量：nethogs; 3) 按连接查看流量：iftop. 

<!-- more -->

## 概述
在真实环境中，要查看网络流量的占用问题，可以从下几个维度去考虑：
1. 查看整体流量带宽，判断机器的上下行带宽是否被打满，如果带宽超过了本机的限额，就要考虑增加带宽或增加节点；
2. 根据进程查看流量占用，从而判断出那个程序占用流量较大；
3. 知道进程占用流量情况之后，再查看连接的流量使用，从而可以判断出那个连接占用流量最大。

网络相关的命令较多，我们可以选择三个常用的命令：
1. nload：查看整体流量；
2. nethogs：按进程查看流量；
3. iftop：按连接查看流量。

**说明：**
安装的环境为 `CentOS 7.6`.

## 整体带宽(nload)

**1. 安装**
```bash
yum -y install nload
```

**2. 运行命令**

```bash
$ nload -m

Device docker0 [172.17.0.1] (1/10):
===============================================================================================
Incoming:                                                                     Outgoing:
Curr: 0.00 Bit/s                                                              Curr: 0.00 Bit/s
Avg: 192.00 Bit/s                                                             Avg: 144.00 Bit/s
Min: 0.00 Bit/s                                                               Min: 0.00 Bit/s
Max: 1.27 kBit/s                                                              Max: 1.09 kBit/s
Ttl: 16.22 GByte                                                              Ttl: 1.04 GByte

Device eth0 [172.18.12.12] (2/10):
================================================================================================
Incoming:                                                                     Outgoing:
Curr: 1.40 kBit/s                                                             Curr: 54.27 kBit/s
Avg: 5.45 kBit/s                                                              Avg: 64.84 kBit/s
Min: 952.00 Bit/s                                                             Min: 20.41 kBit/s
Max: 68.84 kBit/s                                                             Max: 158.58 kBit/s
Ttl: 71.15 GByte                                                              Ttl: 78.86 GByte

Device lo [127.0.0.1] (3/10):
================================================================================================
Incoming:                                                                     Outgoing:
Curr: 0.00 Bit/s                                                              Curr: 0.00 Bit/s
Avg: 0.00 Bit/s                                                               Avg: 0.00 Bit/s
Min: 0.00 Bit/s                                                               Min: 0.00 Bit/s
Max: 0.00 Bit/s                                                               Max: 0.00 Bit/s
Ttl: 13.23 MByte                                                              Ttl: 13.23 MByte

Device veth14e1c44 (4/10):
=================================================================================================
Incoming:                                                                     Outgoing:
Curr: 0.00 Bit/s                                                              Curr: 0.00 Bit/s
Avg: 0.00 Bit/s                                                               Avg: 0.00 Bit/s
Min: 0.00 Bit/s                                                               Min: 0.00 Bit/s
Max: 0.00 Bit/s                                                               Max: 0.00 Bit/s
Ttl: 14.21 MByte                                                              Ttl: 937.65 kByte

```

nload 按网络设备分组，显示每一个设备的入口/出口带宽。显示的内容也很直观，`Incoming` 表示入口带宽，`Outgoing` 表示出口带宽。其它字段含义如下：
- Curr: 当前流量；
- Avg: 平均流量；
- Min: 最小流量；
- Max: 最大流量；
- Ttl: 总流量。

**3. 常用命令**

```bash
$ nload -m         # 查看所有设备的流量情况
$ nload eth0       # 查看指定设备的流量情况
$ nload -u m       # 指定流量的单位为 MBit/S, 
                   # 可供选择的单位有：
                   # h: auto, b: Bit/s, k: kBit/s, m: MBit/s etc,
                   # H: auto, B: Byte/s, K: kByte/s, M: MByte/s etc
```

## 按进程查看流量(nethogs)

**1. 安装**

```bash
yum -y install nethogs
```

**2. 运行命令**

```bash
$ nethogs
NetHogs version 0.8.5

    PID USER     PROGRAM                                          DEV        SENT      RECEIVED       
   6390 root     /usr/bin/dockerd                                 ens160     34.871       1.075 KB/sec
  28001 root     sshd: root@pts/0,pts/1                           ens160      0.200       0.059 KB/sec
  25891 rabbit.. /usr/lib64/erlang/erts-9.3.3/bin/beam.smp        ens160      0.000       0.000 KB/sec
      ? root     unknown TCP                                                  0.000       0.000 KB/sec
  
  TOTAL                                                                      35.071       1.134 KB/sec

```

可以看到每一个进程流量的使用情况。

**3. 常用命令**
```bash
$ nethogs eth0          # 查看指定设备的流量情况
```

## 按连接查看流量(iftop)

**1. 安装**
`iftop` 依赖 libpcap, libncurses 库，需提前安装。
```bash
$ yum -y install libpcap libpcap-devel ncurses ncurses-devel
$ yum -y install iftop
```

**2. 运行命令**
```bash
$ iftop -n -i ens160
                    19.1Mb              38.1Mb               57.2Mb              76.3Mb         95.4Mb
+-------------------+-------------------+--------------------+-------------------+--------------------
192.168.100.101                         => 192.168.100.102                       348Kb   348Kb   317Kb
                                        <=                                      7.38Kb  7.51Kb  6.84Kb
192.168.100.101                         => 192.168.100.103                        208b    166b     97b
                                        <=                                        240b    192b    106b



------------------------------------------------------------------------------------------------------
TX:             cum:    872KB   peak:    350Kb                        rates:    348Kb   348Kb   317Kb
RX:                    19.1KB           8.40Kb                                 7.62Kb  7.70Kb  6.94Kb
TOTAL:                  891KB            358Kb                                  356Kb   356Kb   324Kb
```

命令内容分为三个部分：
1. 第一行表示带宽，单位为 bit;
2. 中间部分为活跃的连接，每一连接用两行来表示，第一行表示发送，用 `=>` 表示，第二行表示接收，用 `<=` 表示，最后三列的数据表示最近 2 秒，10 秒和 40 秒的平均流量；
3. 最后三行是统计数据，分别表示发送，接收和全部的流量，cum 列表示运行到目前的流量，peak 列表示峰值，rates 列表示最近 2 秒，10 秒和 40 秒的平均流量。

**3. 常用命令**

```bash
$ iftop           # 默认是监控第一块网卡的流量
$ iftop -i eth1   # 监控eth1
$ iftop -n        # 直接显示IP, 不进行DNS反解析
```
