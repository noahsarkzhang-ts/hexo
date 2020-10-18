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

    // 提供给 poll/select/epoll 使用，获取文件当前状态, 以及就绪通知接口函数
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
在上节的 poll 函数中，会检查文件的状态（可读/可写/可连接），同时在事件的等待队列添加一个等待结点，待续结点中注册一个 callback 回调函数，事件触发时，再调用 callback 回调函数，唤醒结点中的 task 来处理事件。这种机制正时使用了 linux 内核 wakeup callback机制。
Linux 内核通过睡眠队列来组织所有等待某个事件的 task，而 wakeup 机制则可以异步唤醒整个睡眠队列上的 task，每一个睡眠队列上的节点都拥有一个 callback，wakeup 逻辑在唤醒睡眠队列时，会遍历该队列链表上的每一个节点，调用每一个节点的 callback，如果遍历过程中遇到某个节点是排他节点，则终止遍历，不再继续遍历后面的节点。总体上的逻辑可以用下面的伪代码表示：
```python
define sleep_list;
define wait_entry;
wait_entry.task = current_task;
wait_entry.callback = func1;
if (something_not_ready); then
    # 将任务加入等待队列
    add_entry_to_list(wait_entry, sleep_list);
go_on:
    # 根据情况进行睡眠或唤醒
    schedule();
    if (something_not_ready); then
        goto go_on;
    endif
    del_entry_from_list(wait_entry, sleep_list);
endif

```
唤醒的流程：
```python
something_ready;
for_each(sleep_list) as wait_entry; do
    wait_entry.callback(...);
    if(wait_entry.exclusion); then
        break;
    endif
done
```

callback 函数包含于唤醒的主要逻辑，伪代码如下所示：
```python
common_callback_func(...)
{
    do_something_private;
    wakeup_common;
}
```

在 poll/select/epoll 中都会定义各自的 callback 函数，该函数一般包括两部分：1）私有逻辑；2）唤醒 task。callback 函数由驱动来调用（在 NIC 中由软件中断调用）。

### 1.3 I/O 多路复用
I/O 多路复用是一种优化技术，它是为了避免一个线程处理一个 I/O 设备文件，转而由一个线程来监听多个 I/O 文件，来提供系统的效率。poll/select/epoll 底层使用了这种 I/O 模式。
![io-multiplexing](/images/tcp/io-multiplexing.jpg "io-multiplexing")

## 2. select

### 2.1 整体流程
select 方法调用：
```c
#define FD_SETSIZE 1024
#define NFDBITS (8 * sizeof(unsigned long))
#define __FDSET_LONGS (FD_SETSIZE/NFDBITS)

// 数据结构 
typedef struct {
    unsigned long fds_bits[__FDSET_LONGS];
} fd_set;

// select 文件调用
int select(
    int max_fd,  /* 最大文件数 */
    fd_set *readset, /* 读事件文件集合 */
    fd_set *writeset, /* 写事件文件集合 */
    fd_set *exceptset, 
    struct timeval *timeout
    ); // 返回值就绪描述符的数目


```

从 select 方法定义来看，每次调用都需要将文件集合在用户空间及内核空间进行复制，并且文件最大的数量限制在 1024 个。组合上面的内容，可以知道 select 会定义两个函数 poll_queue_proc 和 唤醒 callback 函数，注册到 poll 函数中，在这里，这两个函数分别对应：__pollwait() 和 pollwake。其整体的流程如下所示：

![select](/images/tcp/select.jpg "select")

select 调用主要做了三件事情：
1. 初始化poll_wqueues结构，包括几个关键函数指针的初始化，用于驱动中进行回调处理；
2. 循环遍历监测的文件描述符，并且调用 f_op->poll() 函数，如果有监测条件满足，则会跳出循环；
3. 在监测的文件描述符都不满足条件时，会让当前进程进行睡眠，超时唤醒，或者被所属的等待队列唤醒。

select 函数的循环退出条件有三个：
1. 检测的文件描述符满足条件；
2. 超时；
3. 由等待事件触发。

### 2.2 数据结构
接下来再看下 select 内部的数据结构：
![select_data_struct](/images/tcp/select_data_struct.jpg "select_data_struct")
在 select 方法中，会维护一个 struct poll_wqueues 结构，其中两个关键字段：
1. poll_table：该结构体中的函数指针_qproc指向__pollwait函数；
2. struct poll_table_entry[]：存放不同文件的 poll_table_entry，这些条目的增加是在驱动调用 __pollwait() 时进行初始化并完成添加的，每一个文件都会添加一个条目。

在这个数据结构可以看出，调用 poll 函数之后，会在所有文件的等待队列中加入一个结点，这个结点会持有当前 task 的信息，当事件触发之后，从而可以知道唤醒那一个进程；

从上面的分析可以看出，select 有以下的缺点：
1. 每次 select 方法调用都会传入文件集合参数，涉及到用户空间及内核空间的两次复制；
2. 每一次调用都需要遍历所有的文件调用 poll 函数，效率较低（在用户空间中，也需要遍历所有文件查看那些文件有事件触发）；
3. 监听的文件数量有限，最大 1024 个。

## 3. epoll
### 3.1 整体流程
epoll 解决了 select 的缺点，在大并发场景下，epoll 得到了广泛的应用，它从以下几个方面解决了 select 的缺点：
1. 生成一个 epoll 文件，将监听的文件描述符加入到这个文件的数据结构（红黑树）中，只用添加一次，避免了数据的来回复制；
2. epoll 文件中维护了一个可读文件队列，每次只遍历该队列，避免所有文件的遍历；
3. 监听的文件不受限制。

下面我们来看下 epoll的实现原理，首先看下调用方法：

```c
// 生成一个 ep 文件，把所有需要监听的文件都放到 ep 文件中
int epoll_create(int size); 

// epoll_ctl 添加一个监听的文件
int epoll_ctl(
	int epfd,
	int op, 
	int fd, 
	struct epoll_event *event
	); 

// epoll_wait 负责检测可读队列，没有可读的文件则阻塞进程
int epoll_wait(
	int epfd, 
	struct epoll_event * events, 
	int maxevents, 
	int timeout
	);

```
epoll_create 生成一个 ep 文件，通过 epoll_ctl 方法添加/删除文件，epoll_wait 方法只遍历满足条件的可读队列，提高了效率。这三个方法大概的逻辑如下描述。
**epoll_ctl 主要逻辑：**
1. 定义一个 epitem 结构，代表一个监听的文件，并加入到红黑树中；
2. 生成一个等待结点，加入到这文件 （socket 文件）的等待队列中；

```python
define epitem
add_epitem_to_rbtree(epitem) 

define wait_entry
wait_entry.socket = this_socket;
wait_entry.callback = epoll_wakecallback;
add_entry_to_list(wait_entry, this_socket.sleep_list);
```
**epoll_wait 主要逻辑：**
1. 定义一个等待结点，将结点的 task （实际为 private 字段，为了简要描述，定义为 task） 设置为当前 task （调用 epoll_wait的进程），并设置回调函数；
2. 判断当前可读队列是否为空，如果为空则将等待结点加入到 ep 文件的等待队列上，并阻塞该进程；
3. 如果当前可读队列不为空，则遍历准备好的可读队列，返回数据给用户进程；

```python
define single_wait_list
define single_wait_entry
single_wait_entry.callback = wakeup_common;
single_wait_entry.task = current_task;
if (ready_list_is_empty); then
    # 等待结点加入到 ep 文件的等待队列中
    add_entry_to_list(single_wait_entry, single_wait_list);
go_on:  
    # 阻塞进程
    schedule();
    if (sready_list_is_empty); then
        goto go_on;
    endif
    del_entry_from_list(single_wait_entry, single_wait_list);
endif
# 遍历准备好的可读队列
for_each_ready_list as sk; do
    event.evt = sk.poll(...);
    event.sk = sk;
    put_event_to_user;
done;

```

在这里需要注意的是，当前进程不像 select 方法，进程是阻塞在监听文件（socket 文件）的等待队列上，而是阻塞在 ep 文件自己的阻塞队列上，如上面的流程所述。这里有问题，如何唤醒阻塞的进程？答案在注册到监听文件的回调函数上，在 epoll_ctl 中，我们同样在监听文件的等待队列上加入了一个等待结点，当文件可读时，调用该回调函数，借助该函数，再唤醒阻塞在 ep 文件等待队列上的进程，其流程如下所述：
```python
epoll_wakecallback(...)
{
    add_this_socket_to_ready_list;
    wakeup_single_epoll_waitlist;
}
```
在唤醒进程之前，会将该文件加入到可读队列中。

epoll_wait 流程如下图所示：
![epoll](/images/tcp/epoll.jpg "epoll")


### 3.2 数据结构
数据结构如下所示：
![epoll_data_struct](/images/tcp/epoll_data_struct.jpg "epoll_data_struct")
关键点说明：
1. 进程阻塞在 epoll 文件的等待队列上，不是监听文件的等待队列上；
2. epoll 会将满足条件的文件提前放在可读文件队列 rdllist 中，减少文件遍历的数量；
3. epoll 将监听的文件使用红黑树管理，可有效地进行文件的添加及删除；
4. 唤醒操作由监听文件等待队列中的回调函数触发，然后再唤醒阻塞在 epoll 文件上的进程。

对应的数据结构定义为：
```c

/* 每创建一个epoll 文件, 内核就会分配一个eventpoll与之对应 */
struct eventpoll {
    /* Protect the this structure access */
    spinlock_t lock;
    /*
     * This mutex is used to ensure that files are not removed
     * while epoll is using them. This is held during the event
     * collection loop, the file cleanup path, the epoll file exit
     * code and the ctl operations.
     */

    struct mutex mtx;

    /* Wait queue used by sys_epoll_wait() */
    /* epoll 文件等待队列，进程就是阻塞在该队列上 */
    wait_queue_head_t wq;

    /* Wait queue used by file->poll() */
    wait_queue_head_t poll_wait;

    /* List of ready file descriptors */
    /* 所有已经准备好的可读文件队列 */
    struct list_head rdllist;

    /* RB tree root used to store monitored fd structs */
    /* 红黑树，存储所有监听的文件 */
    struct rb_root rbr;

    /*
     * This is a single linked list that chains all the "struct epitem" that
     * happened while transfering ready events to userspace w/out
     * holding ->lock.
     */
    struct epitem *ovflist;

    /* The user that created the eventpoll descriptor */
    struct user_struct *user;
};

/*
 * Each file descriptor added to the eventpoll interface will
 * have an entry of this type linked to the "rbr" RB tree.
 */
/* epitem 表示一个被监听的文件 */
struct epitem {
    /* RB tree node used to link this structure to the eventpoll RB tree */
    /* 代表在红黑树中的结点 */
    union {
		/* RB tree node links this structure to the eventpoll RB tree */
		struct rb_node rbn;
		/* Used to free the struct epitem */
		struct rcu_head rcu;
	};

    /* List header used to link this structure to the eventpoll ready list */
    struct list_head rdllink;

    /*
     * Works together "struct eventpoll"->ovflist in keeping the
     * single linked chain of items.
     */
    struct epitem *next;

    /* The file descriptor information this item refers to */
    /* epitem对应的文件和 struct file */
    struct epoll_filefd ffd;

    /* Number of active wait queue attached to poll operations */
    int nwait;
    /* List containing poll wait queues */

    struct list_head pwqlist;

    /* The "container" of this item */
    /* 关联的eventpoll结构 */
    struct eventpoll *ep;

    /* List header used to link this item to the "struct file" items list */
    struct list_head fllink;

    /* The structure that describe the interested events and the source fd */
    /* 当前文件关心的事件 */
    struct epoll_event event;
};

/* 红黑树结点 */
struct rb_node {
	unsigned long  __rb_parent_color;
	struct rb_node *rb_right;
	struct rb_node *rb_left;
} __attribute__((aligned(sizeof(long))));

/* 红黑树根结点 */
struct rb_root {
	struct rb_node *rb_node;
};

struct epoll_filefd {
    struct file *file;
    int fd;
};

/* Wait structure used by the poll hooks */
/* 用于构造回调函数的数据结构，在 ep_ptable_queue_proc 中使用 */
struct eppoll_entry {
    /* List header used to link this structure to the "struct epitem" */
    struct list_head llink;

    /* The "base" pointer is set to the container "struct epitem" */
    /* 关联的 epitem */
    struct epitem *base;

    /*
     * Wait queue item that will be linked to the target file wait
     * queue head.
     */
    /* 添加到监听文件等待队列中的等待结点 */
    wait_queue_t wait;

    /* The wait queue head that linked the "wait" wait queue item */
    /* 监听文件等待队列队首结点 */
    wait_queue_head_t *whead;
};

/* Wrapper struct used by poll queueing */
struct ep_pqueue {
    poll_table pt;
    struct epitem *epi;
};

/* Used by the ep_send_events() function as callback private data */
struct ep_send_events_data {
    int maxevents;
    struct epoll_event __user *events;
};
 
```

## 4. 总结
通过对 select 及 epoll 方法的分析，可以知道，epoll 从各个方面进行了优化，相对 select, 在大部分场景下，性能有了质的飞跃，这也是网络中间件中大部分选用 epoll 的原因。

**参考：**

----
[1]:https://coderbee.net/index.php/linux/20190919/1942
[2]:https://blog.csdn.net/eZiMu/article/details/54896708
[3]:https://mp.weixin.qq.com/s/bjM3uEDg61vhNN8Y661L7w
[4]:https://blog.csdn.net/dog250/article/details/50528373
[5]:https://my.oschina.net/alchemystar/blog/3008840
[6]:https://blog.csdn.net/russell_tao/article/details/17119729
[7]:https://blog.nowcoder.net/n/dade4d8c53d144dfa78157887e2cb33e
[8]:https://zhuanlan.zhihu.com/p/60713292

[1. Linux select/poll/epoll 原理（一）实现基础][1]
[2. inux驱动---file_operations之poll][2]
[3. Linux select/poll机制原理分析][3]
[4. Linux内核中网络数据包的接收-第二部分 select/poll/epoll][4]
[5. 从linux源码看epoll][5]
[6. 高性能网络编程5--IO复用与并发编程][6]
[7. epoll源码分析][7]
[8. 带您进入内核开发的大门 | 内核中的等待队列][8]
