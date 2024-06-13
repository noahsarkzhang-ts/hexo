---
title: Linux 常用命令
date: 2024-04-04 22:30:38
updated: 2024-04-04 22:30:38
tags:
- linux 命令
- systemctl 命令
- find 命令
- grep 命令
- curl 命令
- top 命令
- tcpdump 命令
categories: 
- 运维
---

这篇文章主要记录在工作中用到的常用 Linux 命令。

<!-- more -->
## 服务相关命令
**1. 查看所有的服务**

```bash
systemctl list-units --type=service
```

**2. 查看当前运行的服务**

```bash
systemctl list-units --type=service --state=running
```

服务文件目录： **/usr/lib/systemd/system**

## 查找文件
**1. 按照文件名查找文件**
-name file name

```bash
# 在/dir目录及其子目录下面查找名字为filename的文件
find /dir -name filename
# 在当前目录及其子目录（用“.”表示）中查找任何扩展名为“c”的文件
find . -name "*.c" 
```

**2. 按照文件的更改时间来查找文件**
-mtime -n +n
-n 表示文件更改时间距现在 n 天以内，+n 表示文件更改时间距现在 n 天以前。

```bash
# 在系统根目录下查找更改时间在5日以内的文件
find / -mtime -5 -print
# 在/var/adm目录下查找更改时间在3日以前的文件
find /var/adm -mtime +3 -print
```
**3. 按照类型查找文件**
-type
查找某一类型的文件，诸如：
b - 块设备文件。
d - 目录。
c - 字符设备文件。
p - 管道文件。
l - 符号链接文件。
f - 普通文件。

```bash
# 在/etc目录下查找所有的目录
find /etc -type d –print 
# 在当前目录下查找除目录以外的所有类型的文件
find . ! -type d –print 
# 在/etc目录下查找所有的符号链接文件
find /etc -type l –print 
```

## 查找文件内容
**1. 查询且忽略大小写**

```bash
grep -i exception
```

**2. 指定上下文**
用 grep -A,-B,-C 来查看after/before/around 行
-A, 显示匹配后N行
-B, 显示匹配前N行
-C, 显示匹配前后N行

**3. 搜索所有的文件及子目录**

```bash
grep -r exception
```

## 文件打包命令
**1. tar命令**

```bash
tar [-j|-z] [cv] [-f 建立的文件名] filename... <==打包不压缩
tar [-j|-z] [tv] [-f 建立的文件名]             <==察看文件名
tar [-j|-z] [xv] [-f 建立的文件名] [-C 目录]   <==解压缩
```

选顷不参数：
-c  ：建立打包文件，可搭配 -v 来察看过程中被打包的文件名(filename)
-t  ：察看打包文件的内容有哪些文件名，重点在察看『文件名』就是了
-x  ：解打包或解压缩的功能，可以搭配 -C (大写) 在特定目录解开
      特别留意的是， -c, -t, -x 不可同时出现在一串命令行中。
-j  ：透过 bzip2 的支持迚行压缩/解压缩：此时文件名最好为 *.tar.bz2
-z  ：透过 gzip  的支持迚行压缩/解压缩：此时文件名最好为 *.tar.gz
-v  ：在压缩/解压缩的过程中，将正在处理的文件名显示出来！
-f filename：-f 后面要被处理的文件名！建议 -f 单独写一个参数！
-C 目录    ：这个参数用在解压缩，若要在特定目录解压缩，可以使用这个参数。
其他会使用到的参数介绍：
-p  ：保留备份数据的原本权限与属性，常用于备份(-c)重要的配置文件
-m  : 使用当前时间更新文件的修改时间
-P(大写)  ：保留绝对路径，亦即允讲备份数据中含有根目录
--exclude=FILE：在压缩的过程中，不要将 FILE 打包！ 

**2. 打包**

```bash
tar -zpcv -f etc.tar.gz etc
```

**3. 解压缩**

```bash
tar -xzvf etc.tar.gz -C 欲解压缩的目录
```

**4. unzip命令**

```bash
unzip etc.zip -d 目录
```

## 端口查看
**1. 查看指定端口**

```bash
lsof -i :8080
```

**2. 查看进程**

```bash
lsof -p pid
```

**3. 查看某端口的连接情况**

```bash
netstat -anp| grep port
```
## curl命令
-d参数用于发送 POST 请求的数据体。
```bash
$ curl -d'login=emma＆password=123'-X POST https://google.com/login
# 或者
$ curl -d 'login=emma' -d 'password=123' -X POST  https://google.com/login
```

使用-d参数以后，HTTP 请求会自动加上标头Content-Type : application/x-www-form-urlencoded。并且会自动将请求转为 POST 方法，因此可以省略-X POST。

-e参数用来设置 HTTP 的标头Referer，表示请求的来源。
```bash
curl -e 'https://google.com?q=example' https://www.example.com
```
上面命令将Referer标头设为https://google.com?q=example。
-H参数可以通过直接添加标头Referer，达到同样效果。
```bash
curl -H 'Referer: https://google.com?q=example' https://www.example.com
```

-H参数添加 HTTP 请求的标头。
```bash
$ curl -H 'Accept-Language: en-US' https://google.com
```
上面命令添加 HTTP 标头Accept-Language: en-US。

```bash
$ curl -H 'Accept-Language: en-US' -H 'Secret-Message: xyzzy' https://google.com
```
上面命令添加两个 HTTP 标头。
```bash
$ curl -d '{"login": "emma", "pass": "123"}' -H 'Content-Type: application/json' https://google.com/login
```
上面命令添加 HTTP 请求的标头是Content-Type: application/json，然后用-d参数发送 JSON 数据。

-v参数输出通信的整个过程，用于调试。
```bash
$ curl -v https://www.example.com
```
--trace参数也可以用于调试，还会输出原始的二进制数据。
```bash
$ curl --trace - https://www.example.com
```

-X参数指定 HTTP 请求的方法。
```bash
$ curl -X POST https://www.example.com
```
上面命令对 https://www.example.com 发出 POST 请求。
HTTP 方法包括：POST,GET,DELETE,PUT

## tcpdump 命令
tcpdump 命令常用参数如下：
```bash
$ tcpdump -i eth0 -w output_file -nn -s0 -v tcp port 80

-i : 选择要捕获的接口，通常是以太网卡或无线网卡，也可以是 vlan 或其他特殊接口。如果该系统上只有一个网络接口，则无需指定。
-w : 写入到指定文件；
-nn : 单个 n 表示不解析域名，直接显示 IP；两个 n 表示不解析域名和端口。这样不仅方便查看 IP 和端口号，而且在抓取大量数据时非常高效，因为域名解析会降低抓取速度。
-s0 : tcpdump 默认只会截取前 96 字节的内容，要想截取所有的报文内容，可以使用 -s number，number 就是你要截取的报文字节数，如果是 0 的话，表示截取报文全部内容。
-v : 使用 -v，-vv 和 -vvv 来显示更多的详细信息，通常会显示更多与特定协议相关的信息。
-A : 表示使用 ASCII 字符串打印报文的全部数据，这样可以使读取更加简单，方便使用 grep 等工具解析输出内容
tcp port 80 : 这是一个常见的端口过滤器，表示仅抓取 80 端口上的流量，通常是 HTTP
```

## top命令
在top命令执行过程中可以输入以下命令对结果进行调整。
1 监控每个逻辑CPU的状况
c 切换显示命令名称和完整命令行。
M 根据驻留内存大小进行排序。
P 根据CPU使用百分比大小进行排序。
E 切换内存单位
Ctrl+L 擦除并且重写屏幕。
h或者? 显示帮助画面，给出一些简短的命令总结说明。

