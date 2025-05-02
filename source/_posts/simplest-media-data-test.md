---
title: 音视频数据解析
date: 2025-01-01 18:24:02
updated: 2025-01-01 18:24:02
tags:
- YUV
- RGB
- H264
- AAC
- FLV
categories:
- 音视频
---

前段时间拜读了雷霄骅大佬的音视频教程，并运行了相关实例代码。由于代码使用 VC++2011 版本开发，相对较老且 FFmpeg 版本较低。在运行的过程中，碰到了一些问题，顺便做了一些改动，主要是将工程改成由 CMake 来管理，并升级了 FFmpeg 版本。而这篇文章是其中的一篇，主题是关于音视频数据解析，在此记录下来方便后续查看。

<!-- more -->

# 改动

- 编译环境改为 CMake 来管理，支持 Clion IDE。

# 代码说明
## 功能说明

1. 像素数据处理程序。包含RGB和YUV像素格式处理的函数。
2. 音频采样数据处理程序。包含PCM音频采样格式处理的函数。
3. H.264码流分析程序。可以分离并解析NALU。
4. AAC码流分析程序。可以分离并解析ADTS帧。
5. FLV封装格式分析程序。可以将FLV中的MP3音频码流分离出来。
6. UDP-RTP协议分析程序。可以将分析UDP/RTP/MPEG-TS数据包。

## 文件说明

1. simplest_mediadata_aac.cpp: ACC 解析函数。
2. simplest_mediadata_flv.cpp: FLV 解析函数。
3. simplest_mediadata_h264.cpp：H264 解析函数。
4. simplest_mediadata_raw.cpp: YUV/RGB 解析函数。
5. simplest_mediadata_udp.cpp：UDP-RTP 解析函数。
6. simplest_mediadata_main.cpp：主函数。

# 源文地址

1. [视音频数据处理入门：RGB、YUV像素数据处理](https://blog.csdn.net/leixiaohua1020/article/details/50534150)
2. [视音频数据处理入门：PCM音频采样数据处理](https://blog.csdn.net/leixiaohua1020/article/details/50534316)
3. [视音频数据处理入门：H.264视频码流解析](https://blog.csdn.net/leixiaohua1020/article/details/50534369)
4. [视音频数据处理入门：AAC音频码流解析](https://blog.csdn.net/leixiaohua1020/article/details/50535042)
5. [视音频数据处理入门：FLV封装格式解析](https://blog.csdn.net/leixiaohua1020/article/details/50535082)
6. [视音频数据处理入门：UDP-RTP协议解析](https://blog.csdn.net/leixiaohua1020/article/details/50535230)

github地址：<https://github.com/noahsarkzhang-ts/SimplestMediaDataTest>