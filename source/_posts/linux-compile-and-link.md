---
title: Linux 编译和链接
date: 2025-04-13 18:45:51
updated: 2025-04-13 18:45:51
tags:
- pkg-config
- 编译
- 链接
- ldd
categories:
- 音视频
---

这篇文章讲述 Linux 编译和链接的相关知识。

<!-- more -->

# pkg-config

## 简单介绍

pkg-config 在编译应用程序和库的时候作为一个工具来使用。例如你在命令行通过如下命令编译程序时：

```bash
# gcc -o test test.c `pkg-config --libs --cflags glib-2.0`
```

pkg-config 可以帮助你插入正确的编译选项，而不需要你通过硬编码的方式来找到glib(或其他库）。

> --cflags 一般用于指定头文件，--libs 一般用于指定库文件。

pkg-config 能够把这些头文件和库文件的位置指出来，给编译器使用。pkg-config主要提供了下面几个功能：

- 检查库的版本号。 如果所需要的库的版本不满足要求，它会打印出错误信息，避免链接错误版本的库文件；
- 获得编译预处理参数，如宏定义、头文件的位置；
- 获得链接参数，如库及依赖的其他库的位置，文件名及其他一些链接参数；
- 自动加入所依赖的其他库的设置。

pkg-config 命令的基本用法如下：
```bash
pkg-config <options> <library-name>

# 查看当前安装了哪些库
pkg-config --list-all

# 查看 glib-2.0 库头文件及库位置
pkg-config --libs --cflags glib-2.0
```

## 配置环境变量

事实上，pkg-config 只是一个工具，所以不是你安装了一个第三方库，pkg-config 就能知道第三方库的头文件和库文件的位置的。为了让 pkg-config 可以得到一个库的信息，就要求库的提供者提供一个 .pc 文件。默认情况下，比如执行如下命令：
```bash
# pkg-config --libs --cflags glib-2.0
```

pkg-config 会到 `/usr/lib/pkconfig`/目录下去寻找 glib-2.0.pc 文件。也就是说在此目录下的.pc文件，pkg-config是 可以自动找到的。然而假如我们安装了一个库，其生成的.pc文件并不在这个默认目录中的话，pkg-config就找不到了。此时我们需要通过PKG_CONFIG_PATH环境变量来指定pkg-config还应该在哪些地方去寻找.pc文件。

我们可以通过如下命令来设置 PKG_CONFIG_PATH 环境变量：
```bash
# export PKG_CONFIG_PATH=$PKG_CONFIG_PATH:/usr/local/lib/pkgconfig/
```
这样 pkg-config 就会在 `/usr/local/lib/pkgconfig/` 目录下寻找 .pc 文件了。

## pc文件说明
```bash
[root@localhost pkgconfig]# cat libevent.pc 
#libevent pkg-config source file

prefix=/usr/local
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include

Name: libevent
Description: libevent is an asynchronous notification event loop library
Version: 2.0.22-stable
Requires:
Conflicts:
Libs: -L${libdir} -levent
Libs.private: 
Cflags: -I${includedir}
```

这是libevent库的一个真实的例子。下面我们简单描述一下pc文件中的用到的一些关键词：

- Name: 一个针对library或package的便于人阅读的名称。这个名称可以是任意的，它并不会影响到pkg-config的使用，pkg-config是采用pc文件名的方式来工作的；
- Description: 对package的简短描述；
- URL: 人们可以通过该URL地址来获取package的更多信息或者package的下载地址；
- Version: 指定package版本号的字符串；
- Requires: 本库所依赖的其他库文件。所依赖的库文件的版本号可以通过使用如下比较操作符指定：=,<,>,<=,>=；
- Requires.private: 本库所依赖的一些私有库文件，但是这些私有库文件并不需要暴露给应用程序。这些私有库文件的版本指定方式与Requires中描述的类似；
- Conflicts: 是一个可选字段，其主要用于描述与本package所冲突的其他package。版本号的描述也与Requires中的描述类似。本字段也可以取值为同一个package的多个不同版本实例。例如: Conflicts: bar < 1.2.3, bar >= 1.3.0；
- Cflags: 编译器编译本package时所指定的编译选项，和其他并不支持pkg-config的library的一些编译选项值。假如所需要的library支持pkg-config,则它们应该被添加到Requires或者Requires.private中；
- Libs: 链接本库时所需要的一些链接选项，和其他一些并不支持pkg-config的library的链接选项值。与Cflags类似；
- Libs.private: 本库所需要的一些私有库的链接选项。

# pkg-config与LD_LIBRARY_PATH

pkg-config 与LD_LIBRARY_PATH 在使用时有些类似，都可以帮助找到对应的库（静态库和共享库）。我们知道一个程序从源代码到可执行程序，需要经历编译、连接和运行阶段。这里我们列出pkg-config与LD_LIBRARY_PATH的主要工作阶段：

- pkg-config: 编译时、 链接时；
- LD_LIBRARY_PATH: 链接时、 运行时。

pkg-config 主要是在编译时会用到其来查找对应的头文件、链接库等；而 LD_LIBRARY_PATH 环境变量则在链接时和运行时会用到。程序编译出来之后，在程序加载执行时也会通过 LD_LIBRARY_PATH 环境变量来查询所需要的库文件。

# LD_LIBRARY_PATH &  ldconfig

## LD_LIBRARY_PATH

库文件在链接（静态库和共享库）和运行（仅限于使用共享库的程序）时被使用，其搜索路径是在系统中进行设置的。一般 Linux 系统把 `/lib` 和 `/usr/lib` 这两个目录作为默认的库搜索路径，所以使用这两个目录中的库时不需要进行设置搜索路径即可直接使用。对于处于默认库搜索路径之外的库，需要将库的位置添加到库的搜索路径之中。设置库文件的搜索路径有下列两种方式，可任选其中一种使用：

- 在环境变量 LD_LIBRARY_PATH 中指明库的搜索路径；
- 在 /etc/ld.so.conf 文件中添加库的搜索路径；

使用 LD_LIBRARY_PATH 配置的命令如下：
```bash
# export LD_LIBRARY_PATH=/opt/gtk/lib:$LD_LIBRARY_PATH

# echo $LD_LIBRARY_PATH
```

使用这种方式，不需要 root 权限，配置较为简单。

另外，将自己可能存放库文件的路径都加入到 `/etc/ld.so.conf` 中是明智的选择。添加方法也及其简单，将库文件的绝对路径直接写进去就OK了，一行一个。比如：
```bash
/usr/X11R6/lib
/usr/local/lib
/opt/lib
```

## ldconfig

上面两种搜索路径的设置方式对于程序链接时的库（包括共享库和静态库）的定位已经足够了。但是对于使用了共享库的程序的执行还是不够的，这是因为为了加快程序执行时对共享库的定位速度，避免使用搜索路径查找共享库的低效率，所以是直接读取库列表文件 `/etc/ld.so.cache` 的方式从中进行搜索。`/etc/ld.so.cache` 是一个非文本的数据文件，不能直接编辑，它是根据 `/etc/ld.so.conf` 中设置的搜索路径由 `/sbin/ldconfig` 命令将这些搜索路径下的共享库文件集中在一起而生成的（ldconfig 命令要以 root 权限执行）。因此为了保证程序执行时对库的定位，在 `/etc/ld.so.conf` 中进行了库搜索路径的设置之后，还必须要运行 `/sbin/ldconfig` 命令更新 `/etc/ld.so.cache` 文件之后才可以。

`ldconfig`，简单的说，它的作用就是将 `/etc/ld.so.conf` 列出的路径下的库文件缓存到 `/etc/ld.so.cache` 以供使用。因此当安装完一些库文件（例如刚安装好 glib )，或者修改 `ld.so.conf` 增加新的库路径之后，需要运行一下 `/sbin/ldconfig` 使所有的库文件都被缓存到 `ld.so.cache` 中。如果没有这样做，即使库文件明明就在 `/usr/lib` 下的，也是不会被使用的，结果在编译过程中报错。

# Linux下链接库的路径顺序

## 运行时链接库的搜索顺序

Linux程序在运行时对动态链接库的搜索顺序如下：

1. 在编译目标代码时所传递的动态库搜索路径（注意，这里指的是通过`-Wl,rpath=<path1>:<path2>`或 `-R`选项传递的运行时动态库搜索路径，而不是通过 `-L` 选项传递的）
例如：
```bash
# gcc -Wl,-rpath,/home/arc/test,-rpath,/lib/,-rpath,/usr/lib/,-rpath,/usr/local/lib test.c
```
或者
```bash
# gcc -Wl,-rpath=/home/arc/test:/lib/:/usr/lib/:/usr/local/lib test.c
```
2. 环境变量 `LD_LIBRARY_PATH` 指定的动态库搜索路径；
3. 配置文件``/etc/ld.so.conf` 中所指定的动态库搜索路径(更改`/etc/ld.so.conf`之后，一定要执行命令`ldconfig`，该命令会将`/etc/ld.so.conf`文件中所有路径下的库载入内存）;
4. 默认的动态库搜索路径 `/lib`；
5. 默认的动态库搜索路径 `/usr/lib`;

## 编译时与运行时动态库查找的比较

下面是对编译时库的查找与运行时库的查找做一个简单的比较：

1. 编译时查找的是静态库或动态库， 而运行时，查找的是动态库；
2. 编译时可以用 -L 指定查找路径，或者用环境变量 LIBRARY_PATH， 而运行时可以用-Wl,rpath或者-R选项，或者修改/etc/ld.so.conf，或者设置环境变量LD_LIBRARY_PATH;
3. 编译时用的链接器是ld，而运行时用的链接器是/lib/ld-linux.so.2
4. 编译时与运行时都会查找默认路径/lib、/usr/lib
5. 编译时还有一个默认路径/usr/local/lib，而运行时不会默认查找该路径；

说明： `-Wl,rpath` 选项虽然是在编译时传递的，但是其实是工作在运行时。其本身其实也不算是 gcc`的一个选项，而是 ld 的选项，gcc 只不过是一个包装器而已。我们可以执行 man ld 来进一步了解相关信息

# ldd

ldd（英文全拼：list dynamic dependencies）命令列出程序或库文件的动态依赖关系（所依赖的共享库列表）。

## 语法
```bash
ldd [option]... file...
选项：

--version：打印指令版本号
-v：详细信息模式，打印所有相关信息
-u：打印未使用的直接依赖
-d：执行重定位和报告任何丢失的对象
-r：执行数据对象和函数的重定位，并且报告任何丢失的对象和函数
--help：显示帮助信息
参数：指定可执行程序或者库文件
```

## 原理
 ldd 不是个可执行程式，而只是个 shell 脚本；ldd 显示可执行模块的 dependency 的工作原理，其实质是通过 ld-linux.so（elf 动态库的装载器）来实现的。

## 示例
查看 ls 程序运行所依赖的库：
```bash
$ ldd /bin/ls
       linux-vdso.so.1 (0x00007ffcc3563000)
       libselinux.so.1 => /lib64/libselinux.so.1 (0x00007f87e5459000)
       libcap.so.2 => /lib64/libcap.so.2 (0x00007f87e5254000)
       libc.so.6 => /lib64/libc.so.6 (0x00007f87e4e92000)
       libpcre.so.1 => /lib64/libpcre.so.1 (0x00007f87e4c22000)
       libdl.so.2 => /lib64/libdl.so.2 (0x00007f87e4a1e000)
       /lib64/ld-linux-x86-64.so.2 (0x00005574bf12e000)
       libattr.so.1 => /lib64/libattr.so.1 (0x00007f87e4817000)
       libpthread.so.0 => /lib64/libpthread.so.0 (0x00007f87e45fa000)
```

每一行会有两列或三列，含义如下：

- 第1列：程序需要依赖什么库；
- 第2列：系统提供的与程序需要的库所对应的库；
- 第3列：库加载的开始地址。

通过上面的信息，我们可以得到以下几个信息：

- 通过对比第1列和第2列，我们可以分析程序需要依赖的库和系统实际提供的，是否相匹配；
- 通过观察第3列，我们可以知道在当前的库中的符号在对应的进程的地址空间中的开始位置；
- 如果依赖的某个库找不到，通过这个命令可以迅速定位问题所在。






