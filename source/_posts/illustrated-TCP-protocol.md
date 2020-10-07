---
title: 图解TCP协议
date: 2020-09-20 16:58:48
tags:
- tcp协议
- NIC
- 软件中断
- RSS
- 环形队列
- 报文发送
- 报文接收
categories: 
- 网络协议
---

这篇文章讲述网络报文从网卡 NIC （network interface controller）接收，再到操作系统网络协议栈处理，最后到用户程序接收报文处理报文的简化过程，希望能对TCP协议进行一个整体、概括性的总结。

## 1. 网络子系统
从网络中发送过来的网络报文首先到达网卡 NIC，使用 DMA 技术将报文拷贝到内存中，再发起中断请求 CPU 进行中断处理，CPU 调用驱动中的方法处理网络报文，处理完毕之后传给网络协议栈处理，如流程如下图所示：

![data-received](/images/tcp/data-received.jpg "data-received")
1. 网卡 NIC 从外部网络收到报文；
2. 网卡 NIC 通过 DMA 技术直接将报文拷贝到 RAM 中，以 SKB(Socket Buffer)结构存储。NIC 一般都会在 RAM 中申请一个环形的接收队列，代表了接收的能力（同时也会发送环形队列，用于报文的发送）；
3. 网卡 NIC 向 CPU 触发一次硬件中断，通知有报文需要处理，如果只有一个 CPU，没有其它选择；如果是多 CPU 的情况，会涉及到 CPU 的选择，后面我们会进行讲述；
4. CPU 处理中断，调用 NIC 驱动注册到内核中的的中断处理函数，在这里我们以 NAPI 为例（NAPI 合并 IRQ(Interrupt ReQuest),减少中断次数）；
5. 中断处理函数会关闭中断，后续报文直接由拷贝到内存中，避免后续报文重复触发中断；
6. 触发软中断，进行报文处理，中断处理包含两个阶段：1）硬件中断，响应 NIC 中断信号，触发软件中断；2）软件中断，由专门的内核线程来执行，网络报文的处理是由软件中断来执行。

上面的流程是简要的一个流程，有些知识链条是断裂的，下面将补充三个知识点：1）软件中断；2） NIC 与环形队列的关系；3） CPU 的选择问题。

### 1.1 软件中断
在设备驱动中，一般通过中断的方式告诉 CPU 数据已经准备好，可以来取数据了。在内核中，中断处理函数优先级非常高，同时会阻塞其它中断处理。所以要求硬件中断处理函数必须尽可能快、效率尽可能高。为了减少中断处理时间，引入了软件中断，将复杂的处理延迟到软件中断中处理，如网络报文的处理，而在硬件中断中触发软件中断。

系统在启动时，会为每一个 CPU 分配一个内核线程 ksoftirqd 线程，专门处理软件中断，目前能够处理的软件中断有6个，其中网络处理的有两个，分别是接收中断 NET_RX_SOFTIRQ 和 发送中断 NET_TX_SOFTIRQ。这两个中断在net_dev_init方法中注册到内核。初始化的流程如下所示：
![softirq](/images/tcp/softirq.jpg "softirq")
1. 系统启动时，创建 ksoftirad 内核线程，处理软件中断，每一个 CPU 对应一个线程；
2. ksoftirqd 内部是一个事件处理处理函数 run_ksoftirqd，不断接收中断处理事件；
3. 驱动为每一个 CPU 生成 poll_list 链表，主要是存放触发中断事件的 NIC设备；
4. 注册软件中断处理函数 net_rx_action, 中断号为 NET_RX_SOFTIRQ(同时也会注册NET_TX_SOFTIRQ)，负责报文接收工作；
5. 收到报文时，驱动为将触发中断的 NIC 加入到 CPU 的 poll_list中；
6. 驱动设置 softirq_pending 中的 NET_RX_SOFTIRQ 标志位，表明需要处理 NET_RX_SOFTIRQ 中断；
7. run_ksoftirqd 检查到 softirq_pending 标志位，如果有设置标志位，执行 __do_softirq 函数；
8. __do_softirq 查找到 NET_RX_SOFTIRQ 对应的中断处理函数 net_rx_action，并执行该函数，处理报文的接收。

### 1.2 RSS
在多核的系统中，为了充分利用多核处理的优势，提高网络处理的吞吐量，NIC 引入了 RSS(Receive Side Scaling) 或 multiqueue 的技术。这种技术将 NIC 接收队列抽象为多个队列，每一个队列分配一个唯一的中断号，再将队列与某个 CPU 建立映射关系。输入的报文根据 NIC中的 hash 函数（根据Src ip, Src port, Dest ip, Dest port, Protocol）负载到指定的接收队列中，再根据对应的中断号触发硬件中断，后续的报文者将由指定的 CPU 来处理，整体的流程如下图所示：
![RSS](/images/tcp/RSS.jpg "RSS")
1. NIC 接收到外部报文；
2. 使用 DMA 技术将报文拷贝到 SKB 双向链表中；
3. 使用 hash 函数，将该报文负载到指定的队列中，将触发中断，每一个接收队列都对应一个环形队列，有大小的限制，超过容量之后，报文会丢弃；
4. 在硬件中断中处理软件中断，与上面的内容一致。

如果支持 RSS 的话，NIC 为每个队列分配一个 IRQ，通过 /proc/interrupts 进行查看，如下所示：
```bash
$ cat /proc/interrupts
           CPU0       CPU1       CPU2       CPU3
 56:   20209820    4671909   34469139    1896297   PCI-MSI-edge      ens160-rxtx-0
 57:    3259205    5165620    2125138    4534929   PCI-MSI-edge      ens160-rxtx-1
 58:    5883233   10958192    2339523   22326712   PCI-MSI-edge      ens160-rxtx-2
 59:    4307729    2329793    9003652   25191926   PCI-MSI-edge      ens160-rxtx-3
```
可以看到，中断号 56~59 分别分配给了 4 个队列，通过 /proc/irq/IRQ_NUMBER/smp_affinity 设置某个中断由某个 CPU 触发，我们可以查看中断号 56 的配置情况。
```bash
$ cat /proc/irq/56/smp_affinity
4
```
0 号 CPU 的掩码是 0x1 (0001)，1 号 CPU 掩码是 0x2 (0010)，2 号 CPU 掩码是 0x4 (0100)，3 号 CPU 掩码是 0x8 (1000) 依此类推。4 表示使用 CPU 2，另外可以查看或配置环形队列的长度。
```bash
$ ethtool -g ens160
Ring parameters for ens160:
Pre-set maximums:
RX:             4096
RX Mini:        0
RX Jumbo:       4096
TX:             4096
Current hardware settings:
RX:             256
RX Mini:        0
RX Jumbo:       128
TX:             512
```

在 NIC 中引入 RSS 技术，有效地提高了网络处理的吞吐量。如果硬件不支持 RSS 技术，内核提供了 RPS(Receive Packet Steering) 技术，通过软件的技术来实现多核处理网络报文。PRS 技术的原理是：硬件中断只由一个 CPU 处理，然后根据报文计算 hash 值并负载到特定的 CPU 上，通过 Inter-processor Interrupt(IPI) 通知特定的 CPU 来进行软件中断处理。 Receive Flow Steering(RFS) 一般和 RPS 配合一起工作。RPS 是将收到的报文分配到不同的 CPU 以实现负载均衡，保证同一个 Flow 的数据包都由一个 CPU 处理，类似会话绑定的技术。

![RPS](/images/tcp/RPS.jpg "RPS")

可以通过 /proc/sys/net/core/netdev_max_backlog 查看 netdev_max_backlog 的默认值。
```bash
$ cat /proc/sys/net/core/netdev_max_backlog
1000
```

### 1.3 报文处理
上面的内容讲述了硬件中断的相关内容，接下来进入软件中断的处理流程，其流程（以NAPI为例）如下所示：
![net-rx-action](/images/tcp/net-rx-action.jpg "net-rx-action")
net_rx_action 函数处理当前 CPU 中设备列表中的设备( NAPI poll structure)，这些设备主要来自两个地方：1）驱动中调用 napi_schedule 方法加入；2）使用 Inter-processor Interrupt 方法加入（RPS），具体流程如下：
1. 遍历当前 CPU 的设备列表 poll_list，处理所有的 NAPI 设备；
2. 检查 budget 及软件中断的运行时间，避免处理函数占用过多的 CPU 时间，控制 budget 可以影响执行的时间，它可以通过 net.core.netdev_budget 参数进行配置；
3. 调用驱动中注册的 poll函数，在 igb 驱动中调用的是 igb_poll 函数；
4. poll 函数读取环形队列中的 packet ；
5. 如果设备支持 GRO，则需要调用 napi_gro_receive 函数，Generic Receive Offloading(GRO) 是 Large receive offload 的一个实现，LRO 就是在收到多个数据包的时候将同一个 Flow 的多个数据包按照一定的规则合并起来交给上层处理，这样就能减少上层需要处理的数据包数量；
6. 报文传给 net_receive_skb，进行下一步处理。

在 netif_receive_skb 方法中，会根据是否开启 RPS 来进行不同处理，如果开启了 RPS，会使用 IRI (Inter-processor Interrupt )技术，将报文转给远程 CPU 进行处理，实现类似硬件 RSS 的技术；如果未开启，除了将报文分发给 taps(PCAP), 实现抓包功能，同时将报文传给 IP 协议层，由 IP 协议进行下一步处理，其流程如下所示：
![netif-receive-skb](/images/tcp/netif-receive-skb.jpg "netif-receive-skb")
开启 RPS 功能：
1. 将报文传给 enqueue_to_backlog 方法；
2. 报文加入到远程 CPU 的输入队列中；
3. 将 NIC 加入到远程 CPU 的设备列表中，使用 IRI, 触发过程 CPU 的软件中断；
4. 远程 CPU 读取输入队列中的报文；
5. 将报文传给 __net_receive_skb_core 方法；
6. 将报文分发给 taps(PCAP), 实现抓包功能；
7. 将报文传给 IP 协议层，进行下一步处理。

未开启 RPS 功能：
1. 将报文传给 __net_receive_skb_core 方法；
2. 将报文分发给 taps(PCAP), 实现抓包功能；
3. 将报文传给 IP 协议层，进行下一步处理。

## 2. IP 协议层
IP 协议层主要是实现路由功能，结合 netfilter 定义的钩子函数，可以通过 iptables 配置 ip 路由功能，流程如下所示：
![ip-rcv](/images/tcp/ip-rcv.jpg "ip-rcv")
在这里有三个 netfilter 钩子函数：
1. NF_INET_PRE_ROUTING：可以在路由前对数据包进行修改或丢弃；
2. NF_INET_FORWARD：实现转发功能；
3. NF_INET_LOCAL_IN：本地 IP 的入口，触发相应的配置。

## 3. TCP 协议层
报文到了 TCP 协议层，会根据 socket 锁被占用的状态，将报文发送到不同的接收队列，在这里有 4 个队列，分别是：receive queue, out_of_order queue, prequeue queue, backlog queue。通过接收队列，内核软件中断线程与 socket 线程实现了数据的交换。
![tcp-v4-rcv](/images/tcp/tcp-v4-rcv.jpg "tcp-v4-rcv")

4 个队列使用场景：
1. receive queue ：当 socket 没有被线程占用的时候，报文会加入到该队列；
2. out_of_order queue ：临时存放乱序的报文；
3. prequeue queue ：当 socket 被占用且 tcp_low_latency 值为 0 时，报文加入该队列；
4. backlog queue ：当 socket 正在被读取时，新收到的所有报文加入到该队列（如果报文是乱序的，后续还要加入到out_of_order queue）。

如果 tcp_low_latency 值为 1 时，报文不加入到 prequeue queue，内核软件中断线程直接将数据复制到用户态。

>接收缓存
>对收消息过程来说，Socket 占用内存量就是 Receive Queue、Prequeue、Backlog、Out of order 队列内排队的 sk_buff(SKB) 占用内存总数。在内核中可以使用两个参数进行配置：net.core.rmem_max 和 net.core.rmem_default。

最后数据拷贝到用户态之后，表示用户线程已经接到了数据，至此接收流程结束。

## 4. 报文发送
报文接收流程已经讲述完毕，接下来我们再看下报文的接收流程。
### 4.1 TCP 协议层
报文发送流程从 TCP 协议层开始，其主要流程如下所示：
![tcp-sendmsg](/images/tcp/tcp-sendmsg.jpg "tcp-sendmsg")

1. 用户线程调用 send 方法发送用户态的数据；
2. sk_stream_wait_memory：判断发送队列是否有足够的空间发送数据，如果没有则等待一定时间，等待已经发送数据的 ACK 确认信息，如果收到则释放 SKB 数据，腾出空间以便后续数据的发送。TCP 连接分配的发送缓存是有限的，可以通过（ /proc/sys/net/core/wmem_default ）进行配置；
3. tcp_sendmsg ：将用户态的数据按照 MSS ( Maximum Segment Size ) 进行分片，并封装到 SKB 结构中。为了避免数据链路层进行分片，TCP 层传输的数据应小于该层的最大传输单元（MTU）,以太网 MTU 为 1500 字节，扣除 TCP, IP 头的 40 个字节，MSS 最大的值为 1460 字节；
4. tcp_push ：根据 Nagle 算法，将发送的队列发送到 IP 协议层，这里会受滑动窗口和拥塞窗口的影响。

>滑动窗口
TCP 连接上的双方都会通知对方自己的接收窗口大小。而对方的接收窗口大小就是自己的发送窗口大小。tcp_push 在发送数据时需要与发送窗口打交道。发送窗口是一个时刻变化的值，随着 ACK 的到达会变大，随着发出新的数据包会变小。当然，最大也只能到三次握手时对方通告的窗口大小。

>拥塞窗口
>拥塞窗主要是根据网络的拥塞情况控制报文发送的数量，从而达到改善网络传输的目的。TCP 连接刚建立时，拥塞窗口的大小远小于发送窗口，它实际上是一个 MSS。每收到一个 ACK，拥塞窗口扩大一个 MSS 大小，当然，拥塞窗口最大只能到对方通告的接收窗口大小。当然，为了避免指数式增长，拥塞窗口大小的增长会更慢一些，是线性的平滑的增长过程。所以，在tcp_push发送消息时，还会检查拥塞窗口，飞行中的报文数要小于拥塞窗口个数，而发送数据的长度也要小于拥塞窗口的长度。

### 4.2 IP 协议层
IP 协议层将 IP 转换为 MAC 地址，进行下一跳数据的发送。在发送前，可以对 IP 地址进行重写，重写进行路由，实现 SNAT 功能。
![ip_send_skb](/images/tcp/ip_send_skb.jpg "ip_send_skb")

在发送阶段，同样涉及到 netfilter 钩子函数，包括：
1. NF_INET_LOCAL_OUT ：从本机发出的数据包，在查询路由成功之后，会调用__ip_local_out_sk 函数,首先进行必要字段设置和校验和计算，然后经过 NF_INET_LOCAL_OUT 钩子点，之后会调用 dst_output_sk 继续完成数据包输出的其他工作；
2. NF_INET_POST_ROUTING ：转发的数据包或者是本地输出的数据包，最后都会经过 ip_output 进行输出，设置设备和协议之后，经过NF_INET_POST_ROUTING 钩子点，之后调用 ip_finish_output 进行后续输出操作，其中包括了分片等

### 4.3 网络子系统
![dev_queue_xmit](/images/tcp/dev_queue_xmit.jpg "dev_queue_xmit")
1. dev_queue_xmit：在该函数中，会先获取设备对应的qdisc，如果没有的话（如loopback或者IP tunnels），就直接调用dev_hard_start_xmit，否则数据包将经过 Traffic Control 模块进行处理；
2. Traffic Control: 进行一些过滤和优先级处理，在这里，如果队列满了的话，数据包会被丢掉；
3. dev_hard_start_xmit： 该函数中，首先是拷贝一份 SKB 给 “packet taps” ，tcpdump 就是从这里得到数据的，然后调用 ndo_start_xmit。如果 dev_hard_start_xmit 返回错误的话，则触发软件中断 NET_TX_SOFTIRQ，交给软件中断处理程序 net_tx_action 稍后重试。
4. ndo_start_xmit：会调用驱动中的函数进行数据的发送。

### 4.4 驱动
ndo_start_xmit 调用驱动中的函数，进行数据的发送，其大概的流程如下：
1. 将 SKB 放入网卡自己的发送队列 （环形队列）；
2. 通知网卡发送数据包；
3. 网卡发送完成后发送中断给CPU；
4. 收到中断后进行 SKB 的清理工作。

## 5. Select 和 Epoll
*待补充*

## 6. 其它
在上面的内容中提到每一个 CPU 都会关联一个 softnet_data 类型的数据结构，这个数据结构存放了与网络相关的信息，其结构如下：
```c
struct softnet_data
{           
    /*throttle用于拥塞控制,当拥塞时被设置,此后来的数据包都被丢弃*/
    int throttle;

    /*netif_rx返回的拥塞级别*/
    int cng_level;
    int avg_blog;

    /*input_pkt_queue是skb的队列,接收到的skb全都进入到此队列等待后续处理*/
    struct sk_buff_head input_pkt_queue;

    /*poll_list是一个双向链表,链表的成员是有接收数据等待处理的device*/
    struct list_head poll_list;

    /*net_device链表,成员为有数据报要发送的device*/
    struct net_device *output_queue;

    /*完成发送的数据包等待释放的队列*/
    struct sk_buff *completion_queue;

    /*注意,backlog_dev不是一个指针,而是一个net_device实体,代表了调用net_rx_action时的device*/
    struct net_device backlog_dev;
};
```

## 7. 总结
这篇文章从整体的维度分析了 TCP 接收和发送报文的流程，这个流程只是一个大概且略显粗糙，如果读完这篇文章，能够对 TCP 有一个系统性的理解，目的也就达到了。

**参考：**

----
[1]:https://segmentfault.com/a/1190000008836467
[2]:https://segmentfault.com/a/1190000008926093
[3]:https://blog.packagecloud.io/eng/2017/02/06/monitoring-tuning-linux-networking-stack-sending-data/
[4]:https://blog.packagecloud.io/eng/2016/10/11/monitoring-tuning-linux-networking-stack-receiving-data-illustrated/
[5]:https://ylgrgyq.github.io/2017/08/01/linux-receive-packet-3/
[6]:https://ylgrgyq.github.io/2017/07/23/linux-receive-packet-1/
[7]:https://ylgrgyq.github.io/2017/07/24/linux-receive-packet-2/
[8]:https://blog.csdn.net/russell_tao/article/details/9950615
[9]:https://blog.csdn.net/russell_tao/article/details/9370109
[10]:https://blog.csdn.net/cloudvtech/article/details/80182074
[11]:https://blog.51cto.com/enchen/191923

[1. Linux网络 - 数据包的接收过程][1]
[2. Linux网络 - 数据包的发送过程][2]
[3. Monitoring and Tuning the Linux Networking Stack: Sending Data][3]
[4. Illustrated Guide to Monitoring and Tuning the Linux Networking Stack: Receiving Data][4]
[5. Linux 网络协议栈收消息过程-TCP Protocol Layer][5]
[6. Linux 网络协议栈收消息过程-Ring Buffer][6]
[7. Linux 网络协议栈收消息过程-Per CPU Backlog][7]
[8. 高性能网络编程3----TCP消息的接收][8]
[9. 高性能网络编程2----TCP消息的发送][9]
[10. 容器云负载均衡之三：RSS、RPS、RFS和XPS调整][10]
[11. 数据报的接收过程详解][11]