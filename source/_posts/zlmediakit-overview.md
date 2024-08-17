---
title: ZLMediaKit 推拉流概述 
date: 2024-08-17 18:10:13
updated: 2024-08-17 18:10:13
tags:
- ZLMediaKit
- RtspSession
- MediaSource
- MediaSourceMuxer
- RingBuffer
- RingReader
categories: 
- 代码分析
---

最近在看 ZLMediaKit 的源码，它是一个基于 C++11 的高性能运营级流媒体服务框架。由于对其推拉流的整体流程比较感兴趣，查阅相关资料之后，再结合源码，整理出了一个概要的流程。

<!-- more -->

# 概述

在 ZLMediaKit 中，收到某种协议的推流之后，会将转换为多种协议的音视频流，以便不同的客户端进行播放，其整体流程如下，并以 RTMP 推流，RTSP 拉流举例：

![zlmediakit](/images/zlmediakit/zlmediakit.jpg "zlmediakit 整体结构")

**概念：**
1. MediaSource: 媒体源，任何 rtsp/rtmp 的直播流都源自该对象，每种协议都有自己的媒体源对象，如 RtmpMediaSource 和 RtspMediaSource；
2. RtmpSession & RtspSession：会话对象，表示一个网络连接，每种协议都有其会话对象，通过它，可以实现协议的解析及数据的接收和发送；
3. MediaSourceMuxer：媒体源复用器，使用它可以实现流媒体的协议转换，它接收两类数据：1）Track，轨道数据，它用来描述音视频元数据，一个轨道代表一股音视频流；2）Frame，音视频媒体数据；
4. MultiMediaSourceMuxer：媒体源复用聚合类，它包含所有协议的媒体源复用器；
5. RtspMediaSourceMuxer：Rtsp 媒体源复用器，它负责将音视频媒体数据封装为 Rtsp 协议的流媒体。每一个媒体源复用器都包含一个同协议的 MediaSource 源；
6. RingBuffer：环形缓存器，它用来缓存媒体数据；
7. _RingReaderDispatcher：媒体数据分发器，由于拉流对象分布在不同的线程上，由该对象完成在本线程上将数据分发给拉流对象；
8. RingReader：拉流对象，每一次拉流都会生成一个该对象。

# 拉流回调
每一次拉流的操作，都会生成一个 RingReader 对象，在该对象上注册回调函数，当有媒体数据时，调用该回调函数，最终由 Session 对象写入到网络连接中，从而实现拉流。以 Rtsp 拉流为例，注册回调由以下方法实现：
```c++
// RtspSession.cpp

void RtspSession::handleReq_Play(const Parser &parser) {
    // ...

    if (!_play_reader && _rtp_type != Rtsp::RTP_MULTICAST) {
        weak_ptr<RtspSession> weak_self = static_pointer_cast<RtspSession>(shared_from_this());

        // 生成 RingReader 对象，该对象注册绑定到 _RingReaderDispatcher 中
        _play_reader = play_src->getRing()->attach(getPoller(), use_gop);
        _play_reader->setGetInfoCB([weak_self]() {
            Any ret;
            ret.set(static_pointer_cast<SockInfo>(weak_self.lock()));
            return ret;
        });

        // 定义解绑回调
        _play_reader->setDetachCB([weak_self]() {
            auto strong_self = weak_self.lock();
            if (!strong_self) {
                return;
            }
            strong_self->shutdown(SockException(Err_shutdown, "rtsp ring buffer detached"));
        });

        // 定义读回调，有推流数据时调用该函数
        _play_reader->setReadCB([weak_self](const RtspMediaSource::RingDataType &pack) {
            auto strong_self = weak_self.lock();
            if (!strong_self) {
                return;
            }
            strong_self->sendRtpPacket(pack);
        });
    }
}
```

可见，RingReader 关联绑定到 MediaSource 的 RingBuffer 上，当 RingBuffer 有数据时，则触发该回调。

# 媒体分发
ZLMediaKit 中使用了多线程模型，拉流 RingReader 对象被平均负载到多个 poller 线程上（poller 线程代表工作线程，一个 poller 线程负责读取多个网络连接的数据）。当推流时，媒体数据会写入到 RingBuffer 中，由于推流线程和拉流线程可能不是同一个线程，为了提高分发的效率。推流线程向每个 poller 线程添加一个异步任务，具体的拉流操作由异步任务执行。具体代码如下：
```c++
// RingBuffer 对象
void write(T in, bool is_key = true) {
    if (_delegate) {
        _delegate->onWrite(std::move(in), is_key);
        return;
    }

    LOCK_GUARD(_mtx_map);
    for (auto &pr : _dispatcher_map) {
        auto &second = pr.second;
        // 向 poller 线程添加任务，并触发onRead事件
        pr.first->async([second, in, is_key]() mutable { second->write(std::move(in), is_key); }, false);
    }
    _storage->write(std::move(in), is_key);
}
```
_dispatcher_map 定义如下：`std::unordered_map<EventPoller::Ptr, typename RingReaderDispatcher::Ptr, HashOfPtr> _dispatcher_map;`，它是一个 map 对象，第一个值是 EventPoller 对象（Poller 线程对象）指针，第二个值是 _RingReaderDispatcher （RingReaderDispatcher 是其别名）对象指针，在该对象中关联了 RingReader 对象。这个 map 对象维护了与 RingBuffer 对象相关联的 Poller 线程及 RingReaderDispatcher 对象的映射关系。通过遍历 _dispatcher_map 对象，便可获取所有的拉流对象。

向 Poller 线程添加一个异步任务，该任务只有一个功能，便是向 RingReaderDispatcher 写入数据，其代码如下：
```c++
// _RingReaderDispatcher 对象
void write(T in, bool is_key = true) {
    for (auto it = _reader_map.begin(); it != _reader_map.end();) {
        auto reader = it->second.lock();
        if (!reader) {
            it = _reader_map.erase(it);
            --_reader_size;
            onSizeChanged(false);
            continue;
        }
        reader->onRead(in, is_key);
        ++it;
    }
    _storage->write(std::move(in), is_key);
}
```

_reader_map 中维护了当前 Poller 线程中所关联的 RingReader 的对象，遍历所有 RingReader 对象，并最终触发 onRead 回调，完成媒体数据的推送。

**说明：**
RingBuffer 中会缓存 GOP 数据，为了叙述的简洁，省略了该部分内容，不过不影响整体流程的准确性。


