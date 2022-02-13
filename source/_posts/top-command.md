---
title: 性能：Top 命令
date: 2022-02-12 20:21:08
tags:
- top
categories:
- Performance
---

在日常工作，查看服务器的负载、CPU 及内存使用情况，尤其查看进程使用内存、CPU 的占比，定位哪个进程占用了最多的内存及 CPU 周期，这个时候，就可以使用 Top 命令了。

<!-- more -->
## 命令介绍

### 命令格式
```bash
top [参数]
```

### 功能介绍
> 显示当前系统正在执行的进程的相关信息，包括进程 ID、内存占用率、CPU 占用率等命令参数。

### 常用参数
- -c：显示完整的程序启动命令
- -p：<进程号> 指定进程
- -n：<次数> 循环显示的次数，然后退出

## 命令解析
### 命令执行
```bash
# top

top - 20:39:43 up 743 days,  4:18,  1 user,  load average: 0.01, 0.04, 0.05
Tasks: 112 total,   1 running, 111 sleeping,   0 stopped,   0 zombie
%Cpu(s):  1.3 us,  1.5 sy,  0.0 ni, 97.2 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
KiB Mem :  3880256 total,   165932 free,  2718472 used,   995852 buff/cache
KiB Swap:        0 total,        0 free,        0 used.   885852 avail Mem 

  PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND                                                                                                                                                                  
24312 root      20   0 5345664   1.2g   6456 S   2.0 31.3 956:38.51 java                                                                                                                                                                     
25450 root      10 -10  131724  12652   6028 S   2.0  0.3   1755:50 AliYunDun                                                                                                                                                                
 7895 root      10 -10   74368  30596   1836 S   0.3  0.8 123:19.93 AliYunDunUpdate                                                                                                                                                          
 9635 polkitd   20   0   52812   2044    380 S   0.3  0.1 199:12.44 redis-server                                                                                                                                                             
24267 root      20   0 3662180 939528   5476 S   0.3 24.2  54:03.87 java    
...

```

### 输出解析
```bash
top - 20:39:43 up 743 days,  4:18,  1 user,  load average: 0.01, 0.04, 0.05
```
输出系统的负载情况，参数解析如下：

- 20:39:43, 当前系统时间；
- up 743 days, 服务器已经运行了 743 天；
- 1 user, 当前有 1 个用户登录系统；
- load average: 0.01, 0.04, 0.05, load average 后面的三个数分别是 1 分钟、5 分钟、15 分钟的负载情况。

> 说明：load average 是衡量 CPU 繁忙程度的重要指标，该值与 CPU 核数强相关。该值除以 CPU 核数大于 1, 则说明 CPU 满负荷运行。

```bash
Tasks: 112 total,   1 running, 111 sleeping,   0 stopped,   0 zombie
```
输出系统任务的分布情况：

- 112, 系统总共有 112 个进程；
- 1, 1 个进程在运行；
- 111, 111 个进程在休眠；
- 0, 0 个进程停止；
- 0, 0 个僵尸进程。

```bash
%Cpu(s):  1.3 us,  1.5 sy,  0.0 ni, 97.2 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
```
输出 CPU 使用情况：
- 1.3 us, 用户空间占用 CPU 的百分比。
- 1.5 sy, 内核空间占用 CPU的百分比。
- 0.0 ni, 改变过优先级的进程占用 CPU 的百分比
- 97.2 id, 空闲 CPU 百分比
- 0.0 wa, IO 等待占用 CPU 的百分比
- 0.0 hi, 硬中断（Hardware IRQ）占用CPU的百分比
- 0.0 si, 软中断（Software Interrupts）占用CPU的百分比
- 0.0 st, 表示被强制等待虚拟CPU的时间

> 说明：通过该行，可以查看 CPU 的繁忙情况，如果 id 较大，说明系统较空闲，us 较大，说明应用占用 CPU 较多，CPU 资源可能不够，wa 较大，IO 有可能是瓶颈。

```bash
KiB Mem :  3880256 total,   165932 free,  2718472 used,   995852 buff/cache
```
内存使用情况：

- 3880256 total, 物理内存总量（4 GB）
- 165932 free, 空闲内存总量（165 MB）
- 2718472 used, 使用中的内存总量（2.7 GB）
- 995852 buffers, 缓存的内存量 （1 GB)

> 说明：该行直观地显示内存的使用，可以评估内存的整体使用情况。

```bash
KiB Swap:        0 total,        0 free,        0 used.   885852 avail Mem
```
交换分区使用情况：

- 0 total, 交换区总量（0）
- 0 free, 空闲交换区总量（0）
- 0 used, 使用的交换区总量（0）
- 885852 avail Mem, 虚拟内存总量（885 MB）

```bash
PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ 
```
进程监控信息：

- PID, 进程 id; 
- USER, 进程所有者; 
- PR, 进程优先级; 
- NI, nice 值。负值表示高优先级，正值表示低优先级; 
- VIRT, 进程使用的虚拟内存总量，单位 kb。VIRT = SWAP + RES; 
- RES, 进程使用的、未被换出的物理内存大小，单位kb。RES = CODE + DATA;
- SHR, 共享内存大小，单位 kb; 
- S, 进程状态。D = 不可中断的睡眠状态 R = 运行 S = 睡眠 T = 跟踪/停止 Z = 僵尸进程;
- %CPU, 上次更新到现在的 CPU 时间占用百分比;
- %MEM, 进程使用的物理内存百分比; 
- TIME+, 进程使用的CPU时间总计，单位1 / 100 秒;
- COMMAND, 进程名称（命令名/命令行;

> 说明：RES, %MEM 可以查看进程内存使用情况，%CPU 可以查看进程 CPU 使用情况。

### 常用交互命令
在 top 命令执行过程中可以使用的一些交互命令：

- h: 显示帮助画面，给出一些简短的命令总结说明；
- k: 终止一个进程；
- q: 退出程序；
- l: 切换显示平均负载和启动时间信息；
- m: 切换显示内存信息；
- t: 切换显示进程和 CPU 状态信息；
- c: 切换显示命令名称和完整命令行；
- M: 根据驻留内存大小进行排序；
- P: 根据CPU使用百分比大小进行排序；
- T: 根据时间/累计时间进行排序；

> 说明：使用 M 命令，对所有进程按照内存使用情况排序，从而查看哪个进程占用最多内存，而 C 命令，可以查看占用 CPU 周期最多的进程。

<br>

**参考：**

----
[1]:https://segmentfault.com/a/1190000040426212?utm_source=sf-similar-article


[1.Linux之top命令][1]