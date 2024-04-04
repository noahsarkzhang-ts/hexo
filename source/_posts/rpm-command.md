---
title: Rpm 命令
date: 2024-04-04 23:03:56
updated: 2024-04-04 23:03:56
tags:
- rpm 命令
categories: 
- 运维
---

这篇文章主要记录 Rpm 常用的命令。

<!-- more -->

**1、RPM 查询操作**
命令：
```bash
rpm -q …
```

附加查询命令：
a 查询所有已经安装的包
以下附加命令用于查询安装包的信息；
i 显示安装包的信息；
l 显示安装包中的所有文件被安装到哪些目录下；
s 显示安装版中的所有文件状态及被安装到哪些目录下；
以下附加命令用于指定需要查询的是安装包还是已安装后的文件；
p 查询的是安装包的信息；
f 查询的是已安装的某文件信息；
举例如下：

```bash
rpm -qa | grep tomcat4 # 查看 tomcat4 是否被安装；
rpm -qip example.rpm # 查看 example.rpm 安装包的信息；
rpm -qif /bin/df # 查看/bin/df 文件所在安装包的信息；
rpm -qlf /bin/df # 查看/bin/df 文件所在安装包中的各个文件分别被安装到哪个目录下；
```

**2、RPM 安装操作**
命令：
```bash
rpm -i 需要安装的包文件名
```

举例如下：
```bash
rpm -i example.rpm # 安装 example.rpm 包；
rpm -iv example.rpm # 安装 example.rpm 包并在安装过程中显示正在安装的文件信息；
rpm -ivh example.rpm # 安装 example.rpm 包并在安装过程中显示正在安装的文件信息及安装进度；
```

**3、RPM 卸载操作**
命令：

```bash
rpm -e 需要卸载的安装包
```

在卸载之前，通常需要使用```rpm -q …```命令查出需要卸载的安装包名称。
举例如下：

```bash
rpm -e tomcat4 # 卸载 tomcat4 软件包
rpm -evh example # 卸载example软件包并在卸载过程中显示卸载的文件信息及卸载进度；
```




