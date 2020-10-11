---
title: select和epoll实现
date: 2020-10-08 18:17:33
tags:
- select
- epoll
categories: 
- 网络协议
---

这篇文章主要讲述 select 和 epoll 的实现原理，包括底层的数据结构、与设备的回调处理机制及两种实现之间的差异。

## 1. 知识储备
在介绍 select 和 epoll 的实现原理前，先介绍两个知识点，分别是 1）文件的 poll 函数；2）linux 的wakeup callback机制。select 和 epoll 很大程度上就是基于这两点构建的。

### 1.1 poll 函数
在 linux 中，设备的操作抽象为文件的操作，对网络设备的操作同样也是文件操作。为了实现非阻塞的数据读取，文件提供了 poll 操作，该操作为上层应用提供了探测设备文件是否有数据可读的接口，同时结合文件的等待队列，上层应用可以对感兴趣的事件添加处理函数，这个处理函数通常是向等待队列中添加一个等待结点，这个等待结点会关联一个 callback 函数，当相关事件满足时触发 callback 函数，最后 poll 函数返回当前设备文件的状态，上层应用根据返回状态决定是否阻塞该线程，poll 函数不阻塞线程。通过这种方式，设备文件提供了基于事件处理的回调机制，select/poll/epoll 就是基于这种方式来实现的。 

![poll](/images/tcp/poll.jpg "poll")

poll 函数分为三个步骤：
1. 获取事件对应的等待队列；
2. 初始化一个等待结点，设置 callback 函数，并将等待结点加入到等待队列中，此时并不阻塞调用线程；
3. 获取设备当前的状态并返回。

在 poll 函数中，上层应用可以根据业务的不同可以自定义 poll_queue_proc 和 唤醒 callback 函数，从而实现不同的功能，select/poll/epoll 分别实现了这两个函数，它们之间的差异从这两个函数中也可以看出。下面是一个 poll 函数实例。

```c
unsigned int scull_p_poll(struct file *filp, poll_table *wait)
{
	Scull_Pipe *dev = filp->private_data;
	unsigned int mask = 0;
	
	/*
	* The buffer is circular; it is considered full
	* if "wp" is right behind "rp". "left" is 0 if the
	* buffer is empty, and it is "1" if it is completely full.
	*/
	// 处理私有业务
	int left = (dev->rp + dev->buffersize - dev->wp) % dev->buffersize;
	
	// 在不同的等待队列上调用 poll_wait 函数
	poll_wait(filp, &dev->inq, wait);
	poll_wait(filp, &dev->outq, wait);
	
	/* readable */
	if (dev->rp != dev->wp) mask |= POLLIN | POLLRDNORM;
	
	/* writable */
	if (left != 1) mask |= POLLOUT | POLLWRNORM;
	
	return mask;
}
```

poll 函数的定义如下：
```c

// 文件操作  
struct file_operations {

    // 提供给poll/select/epoll 使用，获取文件当前状态, 以及就绪通知接口函数
    unsigned int (*poll) (struct file *, struct poll_table_struct *); 
    
    ...
};

// 向文件注册事件及处理函数  
typedef struct poll_table_struct {
    // 处理函数
    poll_queue_proc _qproc;

    // 事件
    unsigned long  _key;  
} poll_table;

// poll_queue_proc 函数定义
typedef void (*poll_queue_proc)(struct file *, wait_queue_head_t *, struct poll_table_struct *);  

```


### 1.2 wakeup callback机制


### 1.3 I/O 多路复用

## 2. select

## 3. epoll

## 4. 总结


**参考：**

----
[1]:https://coderbee.net/index.php/linux/20190919/1942
[2]:https://blog.csdn.net/eZiMu/article/details/54896708
[3]:https://mp.weixin.qq.com/s/bjM3uEDg61vhNN8Y661L7w
[4]:https://blog.csdn.net/dog250/article/details/50528373
[5]:https://my.oschina.net/alchemystar/blog/3008840

[1. Linux select/poll/epoll 原理（一）实现基础][1]
[2. inux驱动---file_operations之poll][2]
[3. Linux select/poll机制原理分析][3]
[4. Linux内核中网络数据包的接收-第二部分 select/poll/epoll][4]
[5. 从linux源码看epoll][5]

