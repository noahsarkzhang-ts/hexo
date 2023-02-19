---
title: CPU 负载跑满 100% 问题
date: 2023-02-18 17:13:58
tags:
- cpu负载
categories:
- 性能
---

这篇文章讲述 CPU 单核跑满 100% 的原因及定位办法。

<!-- more -->

在生产环境中，代码可能存在 Bug, 被触发之后导致 CPU 跑满 100%, 从而影响其它线程的执行。这篇文章模拟种场景，使用 `top` 命令来定位有问题的线程，并找到对应的代码块。

## 命令介绍

`top` 是查看系统负载的命令，在本文中使用了以下的参数：

```bash
# 常用参数
-c: 查看进程执行的命令；
-p: 查看指定的进程；
-H: 查看线程

# 交互参数
c: 切换显示进程执行的命令；
M: 按照内存进行排序；
N: 按照 pid 进行排序；
P: 按照 CPU 负载进行排序；
T: 按照 TIME+ 进行排序；
e: 切换内存单位
```

分析该问题，关键是找到跑满 CPU 的线程，可以按照以下步骤进行：
1. 编写模拟程序；
2. 使用 `Top` 命令定位问题线程；
3. 使用 `jstack` 找到对应的代码块。

## 模拟程序
可以编写一个死循环的程序来模拟这个场景，其代码如下：
```bash
public static void main(String[] args) {

    while (true) {
        // 死循环
        System.out.println("Current Timestamp:" + System.currentTimeMillis());
    }
}
```

打包并执行命令 `java -jar fatjar-lab-jar-with-dependencies.jar`.

## 定位问题线程
使用 `top -c` 命令查看有问题的进程，如下所示：

```bash
$ top -c 
top - 18:03:33 up 149 days, 22:21,  2 users,  load average: 0.33, 0.10, 0.07
Tasks: 141 total,   1 running, 140 sleeping,   0 stopped,   0 zombie
%Cpu(s): 14.5 us, 12.6 sy,  0.0 ni, 72.7 id,  0.0 wa,  0.0 hi,  0.2 si,  0.0 st
KiB Mem :  8009820 total,  2528620 free,  1099948 used,  4381252 buff/cache
KiB Swap:  2097148 total,  2097148 free,        0 used.  6108472 avail Mem 

  PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND
22900 root      20   0 4477412  57688  11996 S  96.4  0.7   0:09.14 java -jar fatjar-lab-jar-with-dependencies.jar
13732 root      20   0  156756   5616   4220 D   8.3  0.1   0:01.52 sshd: root@pts/0,pts/1
22461 root      20   0  162012   2440   1660 R   0.7  0.0   0:00.08 top -c  
```

可以看到，有问题的进程是 `22900`, CPU 跑到了 `96.4%`, 下面使用 `top -Hp 22900` 查看线程信息，并使用交互命令 `P(大写)` 进行排序。

```bash
$ top -Hp 22900
top - 18:11:28 up 149 days, 22:29,  3 users,  load average: 1.17, 0.35, 0.17
Threads:  15 total,   1 running,  14 sleeping,   0 stopped,   0 zombie
%Cpu(s): 15.8 us, 10.3 sy,  0.0 ni, 73.6 id,  0.0 wa,  0.0 hi,  0.3 si,  0.0 st
KiB Mem :  8009820 total,  2526596 free,  1101308 used,  4381916 buff/cache
KiB Swap:  2097148 total,  2097148 free,        0 used.  6107012 avail Mem 

  PID USER      PR  NI    VIRT    RES    SHR S %CPU %MEM     TIME+ COMMAND
22901 root      20   0 4477412  57876  12104 R 92.0  0.7   0:36.46 java -jar fatjar-lab-jar-with-dependencies.jar
22906 root      20   0 4477412  57876  12104 S  0.3  0.7   0:00.02 java -jar fatjar-lab-jar-with-dependencies.jar
22900 root      20   0 4477412  57876  12104 S  0.0  0.7   0:00.00 java -jar fatjar-lab-jar-with-dependencies.jar
22902 root      20   0 4477412  57876  12104 S  0.0  0.7   0:00.00 java -jar fatjar-lab-jar-with-dependencies.jar
22903 root      20   0 4477412  57876  12104 S  0.0  0.7   0:00.00 java -jar fatjar-lab-jar-with-dependencies.jar
22904 root      20   0 4477412  57876  12104 S  0.0  0.7   0:00.00 java -jar fatjar-lab-jar-with-dependencies.jar
22905 root      20   0 4477412  57876  12104 S  0.0  0.7   0:00.00 java -jar fatjar-lab-jar-with-dependencies.jar
22907 root      20   0 4477412  57876  12104 S  0.0  0.7   0:00.00 java -jar fatjar-lab-jar-with-dependencies.jar
22908 root      20   0 4477412  57876  12104 S  0.0  0.7   0:00.00 java -jar fatjar-lab-jar-with-dependencies.jar
22909 root      20   0 4477412  57876  12104 S  0.0  0.7   0:00.00 java -jar fatjar-lab-jar-with-dependencies.jar
22910 root      20   0 4477412  57876  12104 S  0.0  0.7   0:00.23 java -jar fatjar-lab-jar-with-dependencies.jar
22911 root      20   0 4477412  57876  12104 S  0.0  0.7   0:00.25 java -jar fatjar-lab-jar-with-dependencies.jar
22912 root      20   0 4477412  57876  12104 S  0.0  0.7   0:00.07 java -jar fatjar-lab-jar-with-dependencies.jar
22913 root      20   0 4477412  57876  12104 S  0.0  0.7   0:00.00 java -jar fatjar-lab-jar-with-dependencies.jar
22914 root      20   0 4477412  57876  12104 S  0.0  0.7   0:00.03 java -jar fatjar-lab-jar-with-dependencies.jar
```

从上面的内容可以看出，线程 `22901` 占用了 `92%` 的 CPU 时间，该线程便是出问题的线程。

由于 `jstack` 命令中使用的线程 id 是 16 进制的，所以需要将 `22901` 转化为 16 进制。
```bash
$ printf "%x\n" 22901
5975
```

## 定位代码块

通过命令 `jstack 22900 | grep '0x5975' -A20 --color` 查看线程栈的信息，可以发现出问题的线程是 `main` 线程，代码位置是 `org.noahsark.fatjar.App.main(App.java:14)`. 从而最终找到问题的原因。

```bash
$ jstack 22900 | grep '0x5975' -A20 --color  

"main" #1 prio=5 os_prio=0 tid=0x00007fa8b8008800 nid=0x5975 runnable [0x00007fa8c10c9000]
   java.lang.Thread.State: RUNNABLE
        at java.io.FileOutputStream.writeBytes(Native Method)
        at java.io.FileOutputStream.write(FileOutputStream.java:326)
        at java.io.BufferedOutputStream.flushBuffer(BufferedOutputStream.java:82)
        at java.io.BufferedOutputStream.flush(BufferedOutputStream.java:140)
        - locked <0x0000000085c07420> (a java.io.BufferedOutputStream)
        at java.io.PrintStream.write(PrintStream.java:482)
        - locked <0x0000000085c066a8> (a java.io.PrintStream)
        at sun.nio.cs.StreamEncoder.writeBytes(StreamEncoder.java:221)
        at sun.nio.cs.StreamEncoder.implFlushBuffer(StreamEncoder.java:291)
        at sun.nio.cs.StreamEncoder.flushBuffer(StreamEncoder.java:104)
        - locked <0x0000000085c07540> (a java.io.OutputStreamWriter)
        at java.io.OutputStreamWriter.flushBuffer(OutputStreamWriter.java:185)
        at java.io.PrintStream.newLine(PrintStream.java:546)
        - eliminated <0x0000000085c066a8> (a java.io.PrintStream)
        at java.io.PrintStream.println(PrintStream.java:807)
        - locked <0x0000000085c066a8> (a java.io.PrintStream)
        at org.noahsark.fatjar.App.main(App.java:14)
```

**参考：**

----
[1]:https://segmentfault.com/a/1190000040763437?utm_source=sf-similar-article


[1. linux线上CPU100%排查][1]
