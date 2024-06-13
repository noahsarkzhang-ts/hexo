---
title: 在 Linux 中开启端口
date: 2024-04-06 18:01:42
updated: 2024-04-06 18:01:42
tags:
- iptables 命令
- firewall-cmd 命令
categories: 
- 运维
---

这篇文章主要记录在 Linux 中常用开启端口的命令。

<!-- more -->

**Linux 环境说明：** 命令在类 Centos 环境中使用

## iptables开启端口

**1. 管理命令**
```bash
# 安装 iptables
yum install iptables-services

# 启动 iptables
systemctl start iptables

# 关闭 iptables
systemctl stop iptables

# 查看 iptables 状态
systemctl status iptables
```

**2. 命令格式**
```bash
iptables -t 表名 <-A/I/D/R> 规则链名 [规则号] <-i/o 网卡名> -p 协议名 <-s 源IP/源子网> --sport 源端口 <-d 目标IP/目标子网> --dport 目标端口 -j 动作

# 通用匹配：源地址目标地址的匹配
# -p ：指定协议类型
# -s : --source [!] address[/mask] ：指定一个／一组地址作为源地址
# -d : --destination [!] address[/mask] ：指定目的地址
# -i : --in-interface [!] <网络接口name> ：指定数据包来自的网卡
# -o : --out-interface [!] <网络接口name> ：指定数据包出去的网卡
# --sport : 指定源端口
# --dport ：指定目标端口

# 查看管理命令
# -L: --list [chain] 列出链 chain 上面的所有规则，如果没有指定链，列出表上所有链的所有规则

# 规则管理命令
# -t : 指定表名
# -A : --append chain rule-specification, 在指定链 chain 的末尾插入指定的规则
# -I : --insert chain [rulenum] rule-specification 在链 chain 中的指定位置插入一条或多条规则，如果未指定位置，默认在链的头部插入
# -D : --delete chain rule-specification -D, --delete chain rulenum 在指定的链 chain 中删除一个或多个指定规则
# -R num：Replays替换/修改第几条规则

# -j : 指定动作，包括：
# ACCEPT ：接收数据包
# DROP ：丢弃数据包
# REDIRECT ：重定向、映射、透明代理
# SNAT ：源地址转换
# DNAT ：目标地址转换
# MASQUERADE ：IP伪装（NAT），用于ADSL
# LOG ：日志记录
# SEMARK : 添加SEMARK标记以供网域内强制访问控制（MAC）
```

**2. iptables 开放端口**
```bash
# 开放 2200 端口
iptables -A INPUT -p tcp --dport 22000 -j ACCEPT

# 允许 192.168.1 网段的 ip 访问 22 的 tcp 端口
iptables -A INPUT -s 192.168.1.0/24 -p tcp --dport 22 -j ACCEPT

# 开放 80 端口
iptables -A INPUT -p tcp --dport 80 -j ACCEPT

# 允许被ping
iptables -A INPUT -p icmp --icmp-type 8 -j ACCEPT

# 已经建立的连接可以进来
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
```

**3. 列出已设置的规则**
```bash
iptables -L [-t 表名] [链名]

# 四个表名 raw，nat，filter，mangle
# 五个规则链名 INPUT、OUTPUT、FORWARD、PREROUTING、POSTROUTING
# filter表包含INPUT、OUTPUT、FORWARD三个规则链

# 查看 INPUT 规则
iptables -L INPUT

# 详细查看所有规则
iptables -L -nv

```

**3. 保存配置**
```bash
service iptables save
```

## firewall-cmd 开启端口

**1. 启动/关闭命令**
```bash
# 安装 firewalld
yum install firewalld firewall-config

# 启动 firewalld
systemctl start  firewalld 

# 停止 firewalld
systemctl stop firewalld

# 启用自动启动 firewalld
systemctl enable firewalld 

# 禁用自动启动 firewalld
systemctl disable firewalld

 # 查看状态
systemctl status firewalld

# 查看状态
firewall-cmd --state 
```

**2. 查看打开的端口**
```bash
firewall-cmd --zone=public --list-ports
```

**3. 添加端口**
```bash
# 添加指定端口，--permanent永久生效，没有此参数重启后失效
firewall-cmd --zone=public --add-port=80/tcp --permanent

# 添加连续端口
firewall-cmd --zone=public --add-port=1000-2000/tcp --permanent 

# 添加端口之后，需要重新载入才会生效
firewall-cmd --reload
```

**4. 查看指定端口**
```bash
firewall-cmd --zone=public --query-port=80/tcp
```

**5. 删除端口**
```bash
firewall-cmd --zone=public --remove-port=80/tcp --permanent
```



