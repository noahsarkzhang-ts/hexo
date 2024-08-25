---
title: ZLMediaKit UDP 线程模型
date: 2024-08-25 15:50:33
updated: 2024-08-25 15:50:33
tags:
- ZLMediaKit
- 端口重用
- UdpServer
- EventPoller
- Session
categories: 
- 代码分析
---

这篇文章主要分析 ZLMediaKit Udp 服务器的线程模型。

<!-- more -->

# UDP 负载均衡存在的问题
对于 TCP 服务器，由于 TCP 是有连接的协议，天然存在两种类型的 Socket（或 fd），Server Socket 用来监听端口接收连接请求，一个连接请求会生成一个 Clinet Socket，用于数据的传输。一个连接有五个元素（素称五元组）来惟一标识，即协议类型（TCP）、源地址、源端口、目标地址及目标端口，由这些元素可以惟一确定一个 Client Socket，也可以找到其对应的进程（线程）。Reactor 模型就是基于这样的前提设计的，一个或多个线程监听端口处理连接并生成 Client Socket，并将 Client Socket 平均分配给其它线程单独处理读写请求。

对于 UDP 服务器，UDP 是无连接的协议，一个 UDP Socket 没有服务器客户端之分，对于服务器来说，一个 Socket 就可以接受所有的客户端数据，这必然导致数据的处理变得非常复杂，比如，如何区分不同的客户端，如何高效且安全的在多线程下处理客户端数据等。

为了充分利用多核多线程的性能优势，UDP 可以模拟成有连接的 TCP 协议，使用 Reactor 模型，即多线程 + epoll(select) 的编程模型，为了达到这个目标，需要借助以下的技术：
1. 端口重用SO_REUSEADDR、SO_REUSEPORT；
2. 模拟连接，一个客户端请求建立一个 Client，确定五元组（包括协议类型）。

## 端口重用 SO_REUSEADDR、SO_REUSEPORT

UDP 服务器使用一个端口来处理所有客户端请求，一个客户端生成一个 UDP Socket，多个客户端就会生成多个 UDP Socket，这些 UDP Socket 监听相同的服务器地址和端口。要使这些包含相同地址和
端口的 UDP Sokcet 创建成功，需要添加端口重用配置 SO_REUSEADDR、SO_REUSEPORT。

## connect 连接

通过端口重用机制，创建了 UDP Socket，五元组已经明确了三个，即协议类型（UDP）、目标地址及目标端口。现在还没有明确客户端地址及客户端端口，这时可以通过 connect 方法传入客户端地址和端口，从而模拟出一个连接，此后，从该客户端发出的数据都会传递给该 UDP Socket。

```c++
sd = socket(AF_INET, SOCK_DGRAM, 0);

// 绑定服务器地址及端口
srv_addr.sin_family = AF_INET;
srv_addr.sin_port = htons(9600);
srv_addr.sin_addr.s_addr = 0;
bind(sd, (struct sockaddr* )&srv_addr, addrlen);

// connect 客户端地址及端口
cli_addr.sin_family = AF_INET;
cli_addr.sin_port = htons(9601);
cli_addr.sin_addr.s_addr = inet_addr("192.168.1.2")
connect(sd, (struct sockaddr* )&svr_addr, addrlen);
```

调用 connect 方法之后，这条连接就可以建立了。当一个 UDP Socket 去 connect 一个远端地址和端口时，并没有发送任何的数据包，其效果仅仅是在本地建立了一个五元组 + 映射关系，可以让内核找到对应的 UDP Socket，进而找到对应的进程（或线程）。

使用 connect 方式有一个缺陷，就是客户端的地址和端口必须固定，一旦地址和端口变了，UDP Socket 也就变了。

与 TCP 服务器一样，需要一个 Server UDP Socket 来模拟接收连接请求，一般是接收到第一个数据包的时候就创建一个新的 Clien UDP Socket 来接收后续的数据包。如果客户端数据传输较快，Server UDP Socket 连续收到了多个来自同一个客户端的数据包，此时，需要将后续的包转发给 Clien UDP Socket 所在的线程进行处理。

# 网络模型

与 TcpServer 类似，使用多线程 + epoll (select)，一个 Server fd + 多个 epoll 实例。

每一个线程都创建了一个 epoll  实例，并以 ET 边沿触发模式监听同一个 Server fd 的读事件，使用 EPOLLEXCLUSIVE 标志位防止惊群效应，线程阻塞在 epoll_wait上 等待客户端连接。

> 不同系统有不同的多路复用技术，Linux 系统为 epoll，Windows 为 select, 现以 Linux 为例。

当有客户端发送数据到 Server fd 时，针对该客户端创建一个新的会话(新的文件描述符，同样使用 ET 边沿触发)，后续该客户端的数据将不会再发送到Server fd。

ZLMediaKit 使用多线程技术，每一个线程中都创建了自己私有的 epoll 实例，并以 ET 模式监听同一个 server fd 的读( UDP 还有写)事件，这种方式会有惊群效应，所以需要给每一个 fd 事件加上 EPOLLEXCLUSIV E标志位(内核 4.5+ 支持)来避免惊群。后续客户端的 fd 将均匀的分配到这多个线程中处理。

在 ZLMediaKit 中，UDP 服务器与 TCP 服务器结构与流程基本一致，下面说下它们的差异点。

# UdpServer 对象

## 注册 Server Socket 事件

在 UdpServer 对象 setupEvent 方法中，定义了收到 UDP 数据包时的回调方法，在该方法中将会创建 Client UDP Socket，同时处理收到多个数据包的问题。

```c++
void UdpServer::setupEvent() {
    _socket = createSocket(_poller);
    std::weak_ptr<UdpServer> weak_self = std::static_pointer_cast<UdpServer>(shared_from_this());
    _socket->setOnRead([weak_self](const Buffer::Ptr &buf, struct sockaddr *addr, int addr_len) {
        if (auto strong_self = weak_self.lock()) {
            strong_self->onRead(buf, addr, addr_len);
        }
    });
}
```

## 开启端口重用

在 UdpServer 启动过程中，会绑定服务器地址及端口，并设置端口重用。

```c++

// bindUdpSock 方法
int SockUtil::bindUdpSock(const uint16_t port, const char *local_ip, bool enable_reuse) {
    int fd = -1;
    int family = support_ipv6() ? (is_ipv4(local_ip) ? AF_INET : AF_INET6) : AF_INET;
    if ((fd = (int)socket(family, SOCK_DGRAM, IPPROTO_UDP)) == -1) {
        WarnL << "Create socket failed: " << get_uv_errmsg(true);
        return -1;
    }
    // 设置端口重用
    if (enable_reuse) {
        setReuseable(fd);
    }
    setNoSigpipe(fd);
    setNoBlocked(fd);
    setSendBuf(fd);
    setRecvBuf(fd);
    setCloseWait(fd);
    setCloExec(fd);

    if (bind_sock(fd, local_ip, port, family) == -1) {
        close(fd);
        return -1;
    }
    return fd;
}

// setReuseable 方法
int SockUtil::setReuseable(int fd, bool on, bool reuse_port) {
    int opt = on ? 1 : 0;
    int ret = setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, (char *) &opt, static_cast<socklen_t>(sizeof(opt)));
    if (ret == -1) {
        TraceL << "setsockopt SO_REUSEADDR failed";
        return ret;
    }
    // 设置端口重用
#if defined(SO_REUSEPORT)
    if (reuse_port) {
        ret = setsockopt(fd, SOL_SOCKET, SO_REUSEPORT, (char *) &opt, static_cast<socklen_t>(sizeof(opt)));
        if (ret == -1) {
            TraceL << "setsockopt SO_REUSEPORT failed";
        }
    }
#endif
    return ret;
}
```

## Server UDP Socket
在 TCP 服务器中，每一个 TcpServer 副本都会生成一个 Server Socket， 会存在多个 Server Socket，但所有的 Server Socket 指向同一个 Server fd，本质是同一个 Socket。而 UDP 服务器不一样，每一个 UdpServer 副本关联的 Server UDP Socket 都是独立的 Socket，它们指向独立的 Server fd，这些 Server fd 重用同一个服务器地址和端口。

```c++
void UdpServer::start_l(uint16_t port, const std::string &host) {
   
    // ... 创建 UdpServer 副本

    // 主 UdpServer 绑定服务顺路地址和端口
    if (!_socket->bindUdpSock(port, host.c_str())) {
        // udp 绑定端口失败, 可能是由于端口占用或权限问题
        std::string err = (StrPrinter << "Bind udp socket on " << host << " " << port << " failed: " << get_uv_errmsg(true));
        throw std::runtime_error(err);
    }

    // 在 UdpServer 副本中使用独立的 Socket，并绑定到相同的地址和端口
    for (auto &pr: _cloned_server) {
        // 启动子Server
#if 0
        pr.second->_socket->cloneSocket(*_socket);
#else
        // 实验发现cloneSocket方式虽然可以节省fd资源，但是在某些系统上线程漂移问题更严重
        pr.second->_socket->bindUdpSock(_socket->get_local_port(), _socket->get_local_ip());
#endif
    }
    InfoL << "UDP server bind to [" << host << "]: " << port;
}
```

## 创建 Client UDP Socket

当 Server Udp Socket 收到客户端的第一个数据包时，会触发 UdpServer 的 onRead 方法，会检查是否存在 UDP Session，如果不存在，则创建 Client UDP Socket 和 UDP Session，并将二者关联起来。

在下面的代码中，包含如下的内容：
- 分配负载最小的 EventPoller 线程对象，并与新创建的 Client UDP Socket 关联起来，这样便可将 Client UDP Socket 的读写事件注册到 EventPoller 的 epoll 实例上，由该 EventPoller 线程处理后续的请求；
- 判断分配的 EventPoller 线程是否是当前线程，如果是，则直接创建 UDP Session 并定义回调方法，如果不是，则向新分配的 EventPoller 线程添加一个异步任务，由该异步任务创建 UDP Session，并且需要复制数据包，回调给 Session 处理。

```c++
SessionHelper::Ptr UdpServer::createSession(const PeerIdType &id, const Buffer::Ptr &buf, struct sockaddr *addr, int addr_len) {
    // 此处改成自定义获取poller对象，防止负载不均衡
    auto socket = createSocket(EventPollerPool::Instance().getPoller(false), buf, addr, addr_len);
    if (!socket) {
        //创建socket失败，本次onRead事件收到的数据直接丢弃
        return nullptr;
    }

    auto addr_str = string((char *) addr, addr_len);
    std::weak_ptr<UdpServer> weak_self = std::static_pointer_cast<UdpServer>(shared_from_this());
    auto helper_creator = [this, weak_self, socket, addr_str, id]() -> SessionHelper::Ptr {
        auto server = weak_self.lock();
        if (!server) {
            return nullptr;
        }

        //如果已经创建该客户端对应的UdpSession类，那么直接返回
        lock_guard<std::recursive_mutex> lck(*_session_mutex);
        auto it = _session_map->find(id);
        if (it != _session_map->end()) {
            return it->second;
        }

        assert(_socket);
        socket->bindUdpSock(_socket->get_local_port(), _socket->get_local_ip());
        socket->bindPeerAddr((struct sockaddr *) addr_str.data(), addr_str.size());

        auto helper = _session_alloc(server, socket);
        // 把本服务器的配置传递给 Session
        helper->session()->attachServer(*this);

        std::weak_ptr<SessionHelper> weak_helper = helper;
        socket->setOnRead([weak_self, weak_helper, id](const Buffer::Ptr &buf, struct sockaddr *addr, int addr_len) {
            auto strong_self = weak_self.lock();
            if (!strong_self) {
                return;
            }

            //快速判断是否为本会话的的数据, 通常应该成立
            if (id == makeSockId(addr, addr_len)) {
                if (auto strong_helper = weak_helper.lock()) {
                    emitSessionRecv(strong_helper, buf);
                }
                return;
            }

            //收到非本peer fd的数据，让server去派发此数据到合适的session对象
            strong_self->onRead_l(false, id, buf, addr, addr_len);
        });
        socket->setOnErr([weak_self, weak_helper, id](const SockException &err) {
            // 在本函数作用域结束时移除会话对象
            // 目的是确保移除会话前执行其 onError 函数
            // 同时避免其 onError 函数抛异常时没有移除会话对象
            onceToken token(nullptr, [&]() {
                // 移除掉会话
                auto strong_self = weak_self.lock();
                if (!strong_self) {
                    return;
                }
                // 延时移除udp session, 防止频繁快速重建对象
                strong_self->_poller->doDelayTask(kUdpDelayCloseMS, [weak_self, id]() {
                    if (auto strong_self = weak_self.lock()) {
                        // 从共享map中移除本session对象
                        lock_guard<std::recursive_mutex> lck(*strong_self->_session_mutex);
                        strong_self->_session_map->erase(id);
                    }
                    return 0;
                });
            });

            // 获取会话强应用
            if (auto strong_helper = weak_helper.lock()) {
                // 触发 onError 事件回调
                TraceP(strong_helper->session()) << strong_helper->className() << " on err: " << err;
                strong_helper->enable = false;
                strong_helper->session()->onError(err);
            }
        });

        auto pr = _session_map->emplace(id, std::move(helper));
        assert(pr.second);
        return pr.first->second;
    };

    if (socket->getPoller()->isCurrentThread()) {
        // 该socket分配在本线程，直接创建helper对象
        return helper_creator();
    }

    // 该socket分配在其他线程，需要先拷贝buffer，然后在其所在线程创建helper对象并处理数据
    auto cacheable_buf = std::make_shared<BufferString>(buf->toString());
    socket->getPoller()->async([helper_creator, cacheable_buf]() {
        // 在该socket所在线程创建helper对象
        auto helper = helper_creator();
        if (helper) {
            // 可能未实质创建hlepr对象成功，可能获取到其他线程创建的helper对象
            helper->session()->getPoller()->async([helper, cacheable_buf]() {
                // 该数据不能丢弃，给session对象消费
                emitSessionRecv(helper, cacheable_buf);
            });
        }
    });
    return nullptr;
}
```

创建好 Client UDP Socket 之后，调用 bind 和 connect 方法确定一个连接。
```c++
// 绑定服务端地址和端口
socket->bindUdpSock(_socket->get_local_port(), _socket->get_local_ip());

// 连接客户端地址和端口
socket->bindPeerAddr((struct sockaddr *) addr_str.data(), addr_str.size());

// bindUdpSock 方法
bool Socket::bindUdpSock(uint16_t port, const string &local_ip, bool enable_reuse) {
    closeSock();
    int fd = SockUtil::bindUdpSock(port, local_ip.data(), enable_reuse);
    if (fd == -1) {
        return false;
    }
    return fromSock_l(std::make_shared<SockNum>(fd, SockNum::Sock_UDP));
}

// bindPeerAddr 方法，调用 connect 方法
bool Socket::bindPeerAddr(const struct sockaddr *dst_addr, socklen_t addr_len, bool soft_bind) {
    LOCK_GUARD(_mtx_sock_fd);
    if (!_sock_fd) {
        return false;
    }
    if (_sock_fd->type() != SockNum::Sock_UDP) {
        return false;
    }
    addr_len = addr_len ? addr_len : SockUtil::get_sock_len(dst_addr);
    if (soft_bind) {
        // 软绑定，只保存地址
        _udp_send_dst = std::make_shared<struct sockaddr_storage>();
        memcpy(_udp_send_dst.get(), dst_addr, addr_len);
    } else {
        // 硬绑定后，取消软绑定，防止memcpy目标地址的性能损失
        _udp_send_dst = nullptr;
        if (-1 == ::connect(_sock_fd->rawFd(), dst_addr, addr_len)) {
            WarnL << "Connect socket to peer address failed: " << SockUtil::inet_ntoa(dst_addr);
            return false;
        }
        memcpy(&_peer_addr, dst_addr, addr_len);
    }
    return true;
}

```

## 处理多数据包的问题
Server UDP Socket 可能会收到来自同一个客户端的多个数据包，第一个数据包会触发创建 Client UDP Socket 和 UDP Session。如果不作处理会存在并发问题，可能会导致同一个客户端创建多个 Client UDP Socket。在 ZLMediaKit 中，使用锁机制来控制并发或多个数据包的问题，只能有一个线程获取锁创建 Client UDP Socket 和 UDP Session，其它线程（或同一个线程）都会被阻塞，直到 Session 创建成功。后续的请求只需要获取 Session 即可。代码如下所示：

```c++
SessionHelper::Ptr UdpServer::getOrCreateSession(const UdpServer::PeerIdType &id, const Buffer::Ptr &buf, sockaddr *addr, int addr_len, bool &is_new) {
    {
        //减小临界区
        std::lock_guard<std::recursive_mutex> lock(*_session_mutex);
        auto it = _session_map->find(id);
        if (it != _session_map->end()) {
            return it->second;
        }
    }
    is_new = true;
    return createSession(id, buf, addr, addr_len);
}
```

获取 Session 之后，会将数据回调给 Session，由上层处理来处理。如果收到数据的是 Server UDP Socket，则需要将数据传递给 Client UDP Socket 所在的 EventPoller 线程，主要是通过向 EventPoller 线程添加一个异步任务来完成。

```c++
void UdpServer::onRead_l(bool is_server_fd, const UdpServer::PeerIdType &id, const Buffer::Ptr &buf, sockaddr *addr, int addr_len) {
    // udp server fd收到数据时触发此函数；大部分情况下数据应该在peer fd触发，此函数应该不是热点函数
    bool is_new = false;
    if (auto helper = getOrCreateSession(id, buf, addr, addr_len, is_new)) {
        if (helper->session()->getPoller()->isCurrentThread()) {
            //当前线程收到数据，直接处理数据
            emitSessionRecv(helper, buf);
        } else {
            //数据漂移到其他线程，需要先切换线程
            WarnL << "UDP packet incoming from other thread";
            std::weak_ptr<SessionHelper> weak_helper = helper;
            //由于socket读buffer是该线程上所有socket共享复用的，所以不能跨线程使用，必须先拷贝一下
            auto cacheable_buf = std::make_shared<BufferString>(buf->toString());
            helper->session()->async([weak_helper, cacheable_buf]() {
                if (auto strong_helper = weak_helper.lock()) {
                    emitSessionRecv(strong_helper, cacheable_buf);
                }
            });
        }

#if !defined(NDEBUG)
        if (!is_new) {
            TraceL << "UDP packet incoming from " << (is_server_fd ? "server fd" : "other peer fd");
        }
#endif
    }
}
```

</br>

**参考：**

----
[1]:https://blog.csdn.net/youlezhe/article/details/122509474
[2]:https://zhuanlan.zhihu.com/p/144490409


[1. 《ZLToolKit源码学习笔记》（22）网络模块之UdpServer][1]
[2. 告知你不为人知的 UDP：连接性和负载均衡][2]