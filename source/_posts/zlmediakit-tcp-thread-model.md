---
title: ZLMediaKit TCP 线程模型
date: 2024-08-24 19:13:25
updated: 2024-08-24 19:13:25
tags:
- ZLMediaKit
- Reactor
- TcpServer
- EventPoller
- Session
categories: 
- 代码分析
---

这篇文章主要分析 ZLMediaKit TCP 服务器的线程模型。

<!-- more -->

# 概述

在 Java 体系的 Netty 框架中使用了 Reactor 网络开发模型，即一个线程负责监听接收 Accept 请求，多个工作线程（或 IO 线程）负责具体连接 Socket 的读写请求，结合 epoll 或 select 等技术，可以有效提高网络的读写效率，相关知识可以参见之前的文章 [Netty 系列：Reactor](https://zhangxt.top/2021/08/22/netty-reactor/) 。

使用 Reactor 模型有一个缺点：Accept 处理瓶颈。Accept 请求只由一个线程来处理，在短时间内大量客户端同时连接的场景下，可能会有性能问题。这个问题的本质是单线程处理能力有限，可以使用多线程来解决这个问题。

在 ZLMediaKit 最新的版本中，便使用多线程来处理 Accept 请求，并使用负载均衡算法将客户端连接平均分配到某个工作线程中，整体的结构如下图所示：

![zlmediakit-tcp-model](/images/zlmediakit/zlmediakit-tcp-model.jpg "zlmediakit TCP")

**对象介绍：**
1. TcpServer：TCP 服务器对象，负责服务的启动、端口的监听、客户端连接的创建及 Session 会话的创建等功能；
2. Server Socket：ZLMediaKit 抽象的 Socket 对象，代表服务器 Socket 对象，负责端口的监听、接收 Accept 事件回调等功能；
3. Client Socket：ZLMediaKit 抽象的 Socket 对象，代表客户端 Socket 对象，表示与客户端的一个连接，负责1）读取数据并传递给 Session 对象，2）将数据写入到网络上；
4. SockNum：持有操作系统 Socket 文件描述符，并有一个类型字段，表明 Socket 的类型，有四种类型，分别是：Sock_Invalid，Sock_TCP，Sock_UDP 和 Sock_TCP_Server；
5. fd 文件描述符：操作系统 Socket 文件描述符；
6. Session：会话对象，Socket 的读写操作最终由 Session 对象来处理；
7. EventPoller：事件轮询对象，它持有 epoll 或 select 文件描述符， Server Socket 和 Client Socket 将添加到 epoll 或 select 结构中，EventPoller 负责事件轮询，将读写事件回调给 Socket 对象，另外，在 EventPoller 中，持有一个 PipeWrap 对象，用于触发内部事件；
8. thread：操作系统线程，一个 EventPoller 对象持有一个 thread 对象；
9. EventPollerPool：EventPoller 容器，由多个 EventPoller 对象组成，对象的数量一般就是 cpu 的数量; 

# 网络模型

使用多线程 + epoll (select)，一个 Server fd + 多个 epoll 实例。每一个线程都创建了一个 epoll 实例，并以 ET 边沿触发模式监听同一个 Server fd 的读事件，使用 EPOLLEXCLUSIVE 标志位防止惊群效应，线程阻塞在 epoll_wait上 等待客户端连接。

> 不同系统有不同的多路复用技术，Linux 系统为 epoll，Windows 为 select, 现以 Linux 为例。

当有客户端发送数据到 Server fd 时，针对该客户端创建一个新的会话(新的文件描述符，同样使用 ET 边沿触发)，后续该客户端的数据将不会再发送到Server fd。

ZLMediaKit 使用多线程技术，每一个线程中都创建了自己私有的 epoll 实例，并以 ET 模式监听同一个 server fd 的读事件，这种方式会有惊群效应，所以需要给每一个 fd 事件加上 EPOLLEXCLUSIV E标志位(内核4.5+支持)来避免惊群。后续客户端的 fd 将均匀的分配到这多个线程中处理。

# TcpServer 对象
TcpServer 是 TCP 模块的关键对象，它负责其它对象的创建工作，如： EventPoller，Socket 及 Session 等等。一个 TcpServer 对象包含一个 EventPoller 对象和一个 Server Socket 对象，而 Server Socket 会向 EventPoller 对象注册读事件，所有的 Server Socket 对象包含相同的文件描述符。

EventPoller 的数量一般是跟 cpu 的核数（同时能够处理的任务数）相关，同时一个 EventPoller 对象会关联到一个 TcpServer 对象中，这就导致生成多个 TcpServer 对象的副本，最终 TcpServer 对象的数量跟 EventPoller 数量是一样的。作者为什么这么设计呢？据我分析，主要的目的为了实现 Server Socket 对象的负载均衡。Server Socket 存放在 TcpServer 对象中，而 Server Socket 对象的数量是与 EventPoller 数量一致的， 它要向所有 EventPoller 对象注册 Accept 事件，作为 Server Socket 的容器对象，必然也要有多个。这纯粹是个人分析，若有错误，还请指正。

## 创建 EventPoller

TcpServer 对象创建时便会创建多个 EventPoller 对象，数量一般根据 cpu 数量来确定，代码路径：`TcpServer -> Server -> EventPollerPool -> TaskExecutorGetterImp.addPoller`。

```c++
size_t TaskExecutorGetterImp::addPoller(const string &name, size_t size, int priority, bool register_thread, bool enable_cpu_affinity) {
    // 获取 cpu 数量
    auto cpus = thread::hardware_concurrency();
    size = size > 0 ? size : cpus;
    for (size_t i = 0; i < size; ++i) {
        auto full_name = name + " " + to_string(i);
        auto cpu_index = i % cpus;
        EventPoller::Ptr poller(new EventPoller(full_name));
        poller->runLoop(false, register_thread);
        poller->async([cpu_index, full_name, priority, enable_cpu_affinity]() {
            // 设置线程优先级
            ThreadPool::setPriority((ThreadPool::Priority)priority);
            // 设置线程名
            setThreadName(full_name.data());
            // 设置cpu亲和性
            if (enable_cpu_affinity) {
                setThreadAffinity(cpu_index);
            }
        });
        _threads.emplace_back(std::move(poller));
    }
    return size;
}
```

在 TcpServer 的启动操作中，会完成 TcpServer 副本对象的创建，数量与 EventPoller 对象一致，并与 EventPoller 完成绑定，最后每一个 TcpServer 对象都会持有一个 EventPoller 对象。

```c++
void TcpServer::start_l(uint16_t port, const std::string &host, uint32_t backlog) {
    setupEvent();

    //新建一个定时器定时管理这些tcp会话
    weak_ptr<TcpServer> weak_self = std::static_pointer_cast<TcpServer>(shared_from_this());
    _timer = std::make_shared<Timer>(2.0f, [weak_self]() -> bool {
        auto strong_self = weak_self.lock();
        if (!strong_self) {
            return false;
        }
        strong_self->onManagerSession();
        return true;
    }, _poller);

    // 创建 TcpServer 对象副本
    EventPollerPool::Instance().for_each([&](const TaskExecutor::Ptr &executor) {
        EventPoller::Ptr poller = static_pointer_cast<EventPoller>(executor);
        if (poller == _poller) {
            return;
        }
        auto &serverRef = _cloned_server[poller.get()];
        if (!serverRef) {
            serverRef = onCreatServer(poller);
        }
        if (serverRef) {
            serverRef->cloneFrom(*this);
        }
    });

    if (!_socket->listen(port, host.c_str(), backlog)) {
        // 创建tcp监听失败，可能是由于端口占用或权限问题
        string err = (StrPrinter << "Listen on " << host << " " << port << " failed: " << get_uv_errmsg(true));
        throw std::runtime_error(err);
    }
    for (auto &pr: _cloned_server) {
        // 启动子Server
        pr.second->_socket->cloneSocket(*_socket);
    }

    InfoL << "TCP server listening on [" << host << "]: " << port;
}
```

如上代码所示，TcpServer 副本会复制主 TcpServer 对象的数据，包括 Socket 对象。

## 创建 Server Socket

在 TcpServer 启动过程中，也会创建 Server Socket 对象，并设置 OnBeforeAccept 和 OnAccept 函数，这两个函数在接收 Accept 事件时触发。

```c++
void TcpServer::setupEvent() {
    _socket = createSocket(_poller);
    weak_ptr<TcpServer> weak_self = std::static_pointer_cast<TcpServer>(shared_from_this());
    _socket->setOnBeforeAccept([weak_self](const EventPoller::Ptr &poller) -> Socket::Ptr {
        if (auto strong_self = weak_self.lock()) {
            return strong_self->onBeforeAcceptConnection(poller);
        }
        return nullptr;
    });
    _socket->setOnAccept([weak_self](Socket::Ptr &sock, shared_ptr<void> &complete) {
        if (auto strong_self = weak_self.lock()) {
            auto ptr = sock->getPoller().get();
            auto server = strong_self->getServer(ptr);
            ptr->async([server, sock, complete]() {
                //该tcp客户端派发给对应线程的TcpServer服务器
                server->onAcceptConnection(sock);
            });
        }
    });
}
```

# 负载均衡
负载均衡主要包括两个方面：1）Accept 负责均衡；2）客户端连接 Clien Socket 负载均衡。

## Accept 负载均衡
为了解决 Accept 请求瓶颈的问题，使用多线程同时处理 Accept 请求，一个请求只能由一个线程处理，具体分配那个线程取决于操作系统负责均衡的算法。

每一个 EventPoller 线程都创建了一个 epoll 实例，并以 ET 边沿触发模式监听同一个 Server fd 的读事件，使用 EPOLLEXCLUSIVE 标志位防止惊群效应，线程阻塞在 epoll_wait 上等待客户端连接。

Server fd 包含在 Server Socket 对象中，且所有的 Server Socket 对象都指向同一个 Server fd。该 Server fd 注册到所有 EventPoller 对象的 epoll 实例上。有连接请求时，由操作系统负责分配一个 EventPoller 线程处理，从而实现了 Accept 的负载均衡。

在上面的内容中讲到，TcpServer 与 EventPoller 一一对应，Server Socket 对象会向 EventPoller 注册事件回调，注册有两个时机，一是调用 Socket listen 方法时，二是复制 Socket 对象时。具体内容在后续的章节中进行描述。

## Client Socket 负载均衡
EventPoller 收到 Accept 事件时会生成一个 Client Socket 客户端连接对象，该客户端连接对象最终分配给哪一个 EventPoller 线程处理？一般有两个策略：
1. 使用当前 EventPoller 线程，即处理 Accept 请求的 EventPoller 线程；
2. 根据业务负载均衡算法，分配一个负载较小的 EventPoller 线程。

第 1 种方法相对比较简单，负载是否均衡取决于操作系统底层的负载均衡算法，根据 ZLMediaKit 作者的测试，在 cpu 核数较多的情况下，负载均衡算法不是很理想。第 2 种方法则是根据业务上的统计指标，分配一个负载较小的的线程。实际上，在 ZLMediaKit 中都使用了这两种方法，优先使用第 2 中方法，第 2 种方法失败了，则使用第 1 种的方法，代码所下所示：

```c++
int Socket::onAccept(const SockNum::Ptr &sock, int event) noexcept {
    int fd;
    struct sockaddr_storage peer_addr;
    socklen_t addr_len = sizeof(peer_addr);
    while (true) {
        if (event & EventPoller::Event_Read) {
            do {
                fd = (int)accept(sock->rawFd(), (struct sockaddr *)&peer_addr, &addr_len);
            } while (-1 == fd && UV_EINTR == get_uv_error(true));

            ...
            
            Socket::Ptr peer_sock;
            try {
                // 此处捕获异常，目的是防止socket未accept尽，epoll边沿触发失效的问题
                LOCK_GUARD(_mtx_event);
                // 拦截Socket对象的构造
                peer_sock = _on_before_accept(_poller);
            } catch (std::exception &ex) {
                ErrorL << "Exception occurred when emit on_before_accept: " << ex.what();
                close(fd);
                continue;
            }

            if (!peer_sock) {
                // 此处是默认构造行为，也就是子Socket共用父Socket的poll线程并且关闭互斥锁
                peer_sock = Socket::createSocket(_poller, false);
            }

            ...
    }
}
```

优先调用 _on_before_accept 回调方法创建客户端 Socket, 失败了则使用当前 EventPoller 线程创建。

_on_before_accept 回调方法在创建 Server Socket 时指定，具体内容包括：
```c++
_socket->setOnBeforeAccept([weak_self](const EventPoller::Ptr &poller) -> Socket::Ptr {
    if (auto strong_self = weak_self.lock()) {
        return strong_self->onBeforeAcceptConnection(poller);
    }
    return nullptr;
});

Socket::Ptr TcpServer::onBeforeAcceptConnection(const EventPoller::Ptr &poller) {
    assert(_poller->isCurrentThread());
    //此处改成自定义获取poller对象，防止负载不均衡
    return createSocket(EventPollerPool::Instance().getPoller(false));
}
```

在 _on_before_accept 方法中最终会调用 TcpServer 的 onBeforeAcceptConnection 方法，在该方法中调用 EventPollerPool 的 getPoller 方法分配一个 EventPoller 一个线程。

分配的算法在 TaskExecutor 中实现，具体就是取最小负载的线程。

```c++
TaskExecutor::Ptr TaskExecutorGetterImp::getExecutor() {
    auto thread_pos = _thread_pos;
    if (thread_pos >= _threads.size()) {
        thread_pos = 0;
    }

    TaskExecutor::Ptr executor_min_load = _threads[thread_pos];
    auto min_load = executor_min_load->load();

    for (size_t i = 0; i < _threads.size(); ++i) {
        ++thread_pos;
        if (thread_pos >= _threads.size()) {
            thread_pos = 0;
        }

        auto th = _threads[thread_pos];
        auto load = th->load();

        if (load < min_load) {
            min_load = load;
            executor_min_load = th;
        }
        if (min_load == 0) {
            break;
        }
    }
    _thread_pos = thread_pos;
    return executor_min_load;
}
```

# 事件回调

在上面的内容中，我们提到，Socket 将读写事件注册到 EventPoller 对象上。实际上是注册到 EventPoller 对象中的多路复用对象上，如 epoll，kqueue 和 select。ZLMediaKit 会根据系统类型自行选择。

## 事件注册

Socket 事件注册通过 attachEvent 方法完成，其中 Tcp 服务器注册读和错误事件，回调方法为 onAccept，而客户端会注册读写和错误事件。这些读写事件最终会添加到 EventPoller 对象的 epoll，kqueue 和 select 结构中。

```c++
bool Socket::attachEvent(const SockNum::Ptr &sock) {
    weak_ptr<Socket> weak_self = shared_from_this();
    if (sock->type() == SockNum::Sock_TCP_Server) {
        // tcp服务器
        auto result = _poller->addEvent(sock->rawFd(), EventPoller::Event_Read | EventPoller::Event_Error, [weak_self, sock](int event) {
            if (auto strong_self = weak_self.lock()) {
                strong_self->onAccept(sock, event);
            }
        });
        return -1 != result;
    }

    // tcp客户端或udp
    auto read_buffer = _poller->getSharedBuffer();
    auto result = _poller->addEvent(sock->rawFd(), EventPoller::Event_Read | EventPoller::Event_Error | EventPoller::Event_Write, [weak_self, sock, read_buffer](int event) {
        auto strong_self = weak_self.lock();
        if (!strong_self) {
            return;
        }

        if (event & EventPoller::Event_Read) {
            strong_self->onRead(sock, read_buffer);
        }
        if (event & EventPoller::Event_Write) {
            strong_self->onWriteAble(sock);
        }
        if (event & EventPoller::Event_Error) {
            strong_self->emitErr(getSockErr(sock->rawFd()));
        }
    });

    return -1 != result;
}
```
Socket 回调方法说明：
- onAccept: 处理 Servet socket Accept 事件；
- onRead：处理 Client socket Reead 事件；
- onWriteAble：处理 Client socket 可写事件；
- emitErr：处理 Client socket Error 事件

以 epoll 为例，Socket 事件添加到 epoll 结构中：
```c++
int EventPoller::addEvent(int fd, int event, PollEventCB cb) {
    TimeTicker();
    if (!cb) {
        WarnL << "PollEventCB is empty";
        return -1;
    }

    if (isCurrentThread()) {
#if defined(HAS_EPOLL)
        struct epoll_event ev = {0};
        ev.events = (toEpoll(event)) | EPOLLEXCLUSIVE;
        ev.data.fd = fd;
        int ret = epoll_ctl(_event_fd, EPOLL_CTL_ADD, fd, &ev);
        if (ret != -1) {
            _event_map.emplace(fd, std::make_shared<PollEventCB>(std::move(cb)));
        }
        return ret;
    ...
}
```
Socket 的文件描述符通过系统调用 epoll_ctl 添加到 epoll 中，后续产生的相关事件都会触发回调方法的调用。

## 事件触发

在 EventPoller 中，通过 runLoop 方法进行事件轮询，检查 Socket 文件描述符是否有事件产生，有的话则调用注册的回调方法。这是采用事件驱动的编程模式，有事件就触发事件的回调。代码如下所示：

```c++
void EventPoller::runLoop(bool blocked, bool ref_self) {
    if (blocked) {
        if (ref_self) {
            s_current_poller = shared_from_this();
        }
        _sem_run_started.post();
        _exit_flag = false;
        uint64_t minDelay;
#if defined(HAS_EPOLL)
        struct epoll_event events[EPOLL_SIZE];
        while (!_exit_flag) {
            minDelay = getMinDelay();
            startSleep();//用于统计当前线程负载情况
            int ret = epoll_wait(_event_fd, events, EPOLL_SIZE, minDelay ? minDelay : -1);
            sleepWakeUp();//用于统计当前线程负载情况
            if (ret <= 0) {
                //超时或被打断
                continue;
            }

            _event_cache_expired.clear();

            for (int i = 0; i < ret; ++i) {
                struct epoll_event &ev = events[i];
                int fd = ev.data.fd;
                if (_event_cache_expired.count(fd)) {
                    //event cache refresh
                    continue;
                }

                auto it = _event_map.find(fd);
                if (it == _event_map.end()) {
                    epoll_ctl(_event_fd, EPOLL_CTL_DEL, fd, nullptr);
                    continue;
                }
                auto cb = it->second;
                try {
                    // 调用回调方法
                    (*cb)(toPoller(ev.events));
                } catch (std::exception &ex) {
                    ErrorL << "Exception occurred when do event task: " << ex.what();
                }
            }
        }
        
        ...

    } else {
        _loop_thread = new thread(&EventPoller::runLoop, this, true, ref_self);
        _sem_run_started.wait();
    }
}
```

### Accept 回调

在 Socket Accept 回调中，主要是创建 Client Socket，并根据负载均衡方法，分配一个负载最小的 EventPoller 线程。并最终调用到 TcpServer 对象中的 onAcceptConnection 方法，在方法中完成如下功能：
- 创建 Session 对象；
- 注册 Client Socket 事件回调，将读写事件路由到 Session 对象的方法中。

根据业务的不同，可以有多种的 Session 子类，如 RtspSession，RtmpSession 和 HttpSession。Socket 的数据最终将由这些 Session 对象来处理。

```c++
// 接收到客户端连接请求
Session::Ptr TcpServer::onAcceptConnection(const Socket::Ptr &sock) {
    assert(_poller->isCurrentThread());
    weak_ptr<TcpServer> weak_self = std::static_pointer_cast<TcpServer>(shared_from_this());
    //创建一个Session;这里实现创建不同的服务会话实例
    auto helper = _session_alloc(std::static_pointer_cast<TcpServer>(shared_from_this()), sock);
    auto session = helper->session();
    //把本服务器的配置传递给Session
    session->attachServer(*this);

    //_session_map::emplace肯定能成功
    auto success = _session_map.emplace(helper.get(), helper).second;
    assert(success == true);

    weak_ptr<Session> weak_session = session;
    //会话接收数据事件
    sock->setOnRead([weak_session](const Buffer::Ptr &buf, struct sockaddr *, int) {
        //获取会话强应用
        auto strong_session = weak_session.lock();
        if (!strong_session) {
            return;
        }
        try {
            strong_session->onRecv(buf);
        } catch (SockException &ex) {
            strong_session->shutdown(ex);
        } catch (exception &ex) {
            strong_session->shutdown(SockException(Err_shutdown, ex.what()));
        }
    });

    SessionHelper *ptr = helper.get();
    auto cls = ptr->className();
    //会话接收到错误事件
    sock->setOnErr([weak_self, weak_session, ptr, cls](const SockException &err) {
        //在本函数作用域结束时移除会话对象
        //目的是确保移除会话前执行其onError函数
        //同时避免其onError函数抛异常时没有移除会话对象
        onceToken token(nullptr, [&]() {
            //移除掉会话
            auto strong_self = weak_self.lock();
            if (!strong_self) {
                return;
            }

            assert(strong_self->_poller->isCurrentThread());
            if (!strong_self->_is_on_manager) {
                //该事件不是onManager时触发的，直接操作map
                strong_self->_session_map.erase(ptr);
            } else {
                //遍历map时不能直接删除元素
                strong_self->_poller->async([weak_self, ptr]() {
                    auto strong_self = weak_self.lock();
                    if (strong_self) {
                        strong_self->_session_map.erase(ptr);
                    }
                }, false);
            }
        });

        //获取会话强应用
        auto strong_session = weak_session.lock();
        if (strong_session) {
            //触发onError事件回调
            TraceP(strong_session) << cls << " on err: " << err;
            strong_session->onError(err);
        }
    });
    return session;
}

```

# TcpServer 使用实例
TcpServer 使用如下所示，启动时需要指定一个 Session 实例对象，该对象承担了上层的业务数据处理。

```
TcpServer::Ptr server(new TcpServer());
server->start<EchoSession>(9000);//监听9000端口
```

</br>

**参考：**

----
[1]:https://blog.csdn.net/youlezhe/article/details/122384271


[1. 《ZLToolKit源码学习笔记》（20）网络模块之TcpServer][1]




