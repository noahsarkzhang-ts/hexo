---
title: Socket RPC 脚手架
date: 2025-05-02 19:23:53
updated: 2025-05-02 19:23:53
tags:
- tcp
- websocket
- rpc
- netty
- 脚手架
categories:
- 脚手架
---

不同于 Socket 脚手架，Socket RPC 脚手架定义了私有的 PRC 协议，Socket 和 MQ 使用一套协议进行通信。

<!-- more -->

# 功能介绍

1. Socket & MQ 使用同一套协议 RPC 进行通信；
2. Socket 支持 websocket 和 tcp 两种协议；
3. MQ 支持 nats；
4. Socket 支持心跳、离线消息缓存及断线重连功能；
5. 支持服务及用户在线功能；
6. 支持消息推送功能。

# 协议

## RPC 请求

```java
public class Request implements Serializable {

    public static final byte REQUEST = (byte) 1;

    public static final byte RESPONSE = (byte) 2;

    public static final byte ONEWAY = (byte) 3;

    /**
     * 请求序号id
     */
    private int seqId;

    /**
     * 请求命令
     */
    private int cmd;

    /**
     * 消息类型，1：请求；2：响应；3：oneway
     */
    private byte type;

    /**
     * 消息内容
     */
    private Object data;
    
    ...
}
```

**字段说明：**

- seqId：请求序号id，每一个消息都有一个唯一的序号id，在代码中使用自增id，保证同一个会话中，该id 不会重复；
- cmd：请求命令，每一个操作需要定义一个命令，可以根据业务的不同，采用分段定义，100 以下的命令是系统命令，其中 10 用以心跳保活；
- type：消息类型，有三种类型，分别是：1）请求；2）响应；3）oneway；
- data：消息内容。

消息类型介绍可以参考文章：[Alligator 系列：Alligator RPC](https://zhangxt.top/2021/12/26/alligator-rpc/)

## RPC 响应

```java
public class Response implements Serializable {

    /**
     * 请求序号id
     */
    private int seqId;

    /**
     * 请求命令
     */
    private int cmd;

    /**
     * 消息类型，1：请求；2：响应；3：oneway
     */
    private byte type;

    /**
     * 消息内容
     */
    private Object data;

    /**
     * 返回值
     */
    private int code;

    /**
     * 返回消息
     */
    private String msg;
    
    ...
}
```

相对于 `Request` 对象，`Response` 加入了两个字段：`code` 和 `msg`，分别代表返回值和返回消息。


## MQ RPC 请求

```java
public class MqMultiRequest extends Request {

    /**
     * 目标用户
     */
    private List<EndUser> targets;

    /**
     * Topic
     */
    private String topic;

    /**
     * 响应 Topic
     */
    private String repliedTopic;

    ...
}
```

MQ RPC 请求需要指定发送的用户，同时指定接收响应消息的 topic。MQ 需要两个 topic, 一个是目标用户所在 topic,另外一个是接收响应消息的 topic.

## MQ PRC 响应

```java
public class MqMultiResponse extends Response {

    /**
     * Topic
     */
    private String topic;
    
    ...
}
```
MQ RPC 响应消息在 `Response` 的基础上加入了目标用户所在的 topic.


# 工程结构

```txt
socket-rpc-scaffolding
|-- socket-rpc-app
|   |-- socket-rpc-app-base
|   |-- socket-rpc-app-nats
|   |-- socket-rpc-app-online
|   |-- socket-rpc-app-user
|   `-- socket-rpc-app-wsgw
|-- socket-rpc-common
|-- socket-rpc-mq
|-- socket-rpc-tcp
|-- socket-rpc-ws
`-- sql
```

**目录说明：**

- socket-rpc-common: RPC 公共模块；
- socket-rpc-mq: Nats mq rpc 模块；
- socket-rpc-tcp: TCP rpc 模块；
- socket-rpc-ws: Websocket rpc 模块；
- socket-rpc-app：应用模块；
- socket-rpc-app-base: 应用公共模块；
- socket-rpc-app-nats：nats 模块公共模块；
- socket-rpc-app-online：服务及用户在线模块；
- socket-rpc-app-user：用户模块；
- socket-rpc-app-wsgw：Websocket 网关；
- sql：数据库脚本

# 部署

## 下载 nats 
安装过程可以参考：[安装、运行和部署NATS服务](https://docs.natsclub.cn/cn/yun-xing-yi-ge-nats-fu-wu/introduction/installation)

安装完成后修改 nats 地址：
```yaml
# nats 配置
nats:
  enable: true # 是否开启，默认不开启
  servers: nats://@192.168.1.100:4222
```

## 初始化数据库脚本
数据库使用 pgsql，脚本在 sql目录下，初始化完成之后修改数据库配置：
```yaml
# nats 配置
# datasource 配置
spring:
  datasource:
    #type: com.alibaba.druid.pool.DruidDataSource
    #url: jdbc:postgresql://124.71.211.247:18059/vssp?useUnicode=true&characterEncoding=utf-8&serverTimezone=GMT%2B8&allowMultiQueries=true
    type: com.alibaba.druid.pool.DruidDataSource
    url: jdbc:postgresql://127.0.0.1:5432/rpc_scaffolding?useUnicode=true&characterEncoding=utf-8&serverTimezone=GMT%2B8&allowMultiQueries=true
    username: pgsql
    password: pgsql
```

# 启动服务
## 启动网关
在 IDE 中启动网关程序：WsGwServerApp。该网关会打开一个TCP 端口，用于客户端进行连接。


## 启动客户端测试代码
客户端测试代码为 `UserLoginTest.java`，运行单元测试便可连接到网关。登录请求需要一个 `JWT` token，该 token 可以在 `JwtTokenTest` 中生成。数据库已经内置了一个用户，可以使用该用户进行登录请求。

## 推送消息到客户端
测试代码为 `PushEventTest.java`，该代码向客户端推送一个消息并接收响应。


# 代码
**Github代码：**[socket-rpc-scaffolding](https://github.com/noahsarkzhang-ts/alligator-scaffolding/tree/main/socket-rpc-scaffolding) 
