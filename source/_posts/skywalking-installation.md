---
title: Skywalking
date: 2022-06-11 19:29:26
updated: 2022-06-11 19:29:26
tags:
- skywalking
- apm
- 调用链
categories:
- Elasticsearch
---

这篇文章讲述 Skywalking 的简单安装及使用，后续再有文章分析其背后的数据模型。

<!-- more -->

## 概述

Apache Skywalking 专门为微服务架构和云原生架构系统而设计并且支持分布式链路追踪的 APM 系统。Apache Skywalking 通过加载探针的方式收集应用调用链路信息，并对采集的调用链路信息进行分析，生成应用间关系和服务间关系以及服务指标。Apache Skywalking 目前支持多种语言，其中包括 Java，.Net Core，Node.js 和 Go 语言。其架构如下所示：

![skywalking](/images/es/skywalking.jpg "skywalking")

整个系统分为三部分：
- agent：采集 tracing（调用链数据）和 metric（指标）信息并上报；
- OAP：收集 tracing 和 metric 信息通过 analysis core 模块将数据放入持久化容器中（ES，H2（内存数据库），mysql等等），并进行二次统计和监控告警；
- webapp：前后端分离，前端负责呈现，并将查询请求封装为 graphQL 提交给后端，后端通过 ribbon 做负载均衡转发给 OAP 集群，再将查询结果渲染展示。

## 安装
**1. 版本约定**

- OS: centos 7;
- Skywalking: 8.7.0 for es7; 
- Elasticsearch: 7.14.2;
- Kibana: 7.14.2

Elasticsearch 及 Kibana 安装部署参考之前的文章：[Docker 下安装 ES, Kibana](https://zhangxt.top/2022/01/29/es-deployment-in-docker/)

**2. 下载安装**

```bash
# 下载 skywalking
$ wget https://archive.apache.org/dist/skywalking/8.7.0/apache-skywalking-apm-es7-8.7.0.tar.gz

# 解压缩
$ tar -xzvf apache-skywalking-apm-es7-8.7.0.tar.gz

# 切换到安装目录
$ cd apache-skywalking-apm-es7-8.7.0

# 查看目录结构
$ ll
drwxrwxr-x.  9 1001 1002   176 7月  30 2021 agent   # agent 目录
drwxr-xr-x.  2 root root   241 6月  10 16:45 bin    # 启动脚本
drwxr-xr-x. 11 root root  4096 6月  12 15:17 config # 配置文件目录
drwxr-xr-x.  2 root root    68 6月  10 10:24 config-examples
-rwxrwxr-x.  1 1001 1002 31480 7月  30 2021 LICENSE
drwxrwxr-x.  3 1001 1002  4096 6月  10 10:24 licenses
drwxr-xr-x.  2 root root    80 6月  10 10:45 logs  # 日志目录
-rwxrwxr-x.  1 1001 1002 32519 7月  30 2021 NOTICE
drwxrwxr-x.  2 1001 1002 12288 6月  10 17:21 oap-libs # lib 目录
-rw-rw-r--.  1 1001 1002  1951 7月  30 2021 README.txt
drwxr-xr-x.  3 root root    30 6月  10 10:24 tools 
drwxr-xr-x.  2 root root    53 6月  10 10:44 webapp   # web 程序 
```

**3. 修改 Skywalking 配置**

将 Skywalking 数据存储改为 Elasticsearch7, 修改 config/application.yaml 文件。

```yaml
storage:
  selector: ${SW_STORAGE:elasticsearch7}  # 选择 elasticsearch7 作为后台存储，默认为 H2
  elasticsearch7: # elasticsearch7 参数配置
    nameSpace: ${SW_NAMESPACE:"my-elasticsearch"} # 为了避免 index 名称冲突，可以设置 namespace 作为前缀
    clusterNodes: ${SW_STORAGE_ES_CLUSTER_NODES:192.168.1.100:9200} # 配置 ES 地址 
    protocol: ${SW_STORAGE_ES_HTTP_PROTOCOL:"http"} # 使用的协议
    user: ${SW_ES_USER:"elastic"} # elasticsearch7 用户名
    password: ${SW_ES_PASSWORD:"chuanzhang"} # 密码
```

**4. 启动 Skywalking**

修改配置之后保存，便可启动 Skywalking.

```bash
# 启动 SkyWalking OAP 服务
$ bin/oapService.sh
```

**5. 修改 SkyWalking UI 服务**
```bash
# 启动 SkyWalking UI 服务
$ bin/webappService.sh
```

SkyWalking UI 默认端口是 `8080`, 可以通过 `webapp/webapp.yaml` 进行修改，在这里我们修改为 `8081`. 输入地址 `http://127.0.0.1:8081` 便可访问 Skywalking.

![skywalking-dashboard](/images/es/skywalking-dashboard.jpg "skywalking-dashboard")


## 集成

SkyWalking 已经部署完成，现在需要将应用 trace 及 metric 日志采集到 SkyWalking, 对于 Java 应用来说相对比较简单，使用 `javaagent` 便可集成 SkyWalking.

**1. 使用环境变量**

```bash
# SkyWalking Agent 配置
$ export SW_AGENT_NAME=skywalking-lab # 配置应用名称
$ export SW_AGENT_COLLECTOR_BACKEND_SERVICES=127.0.0.1:11800 # 配置 Collector 地址
$ export JAVA_AGENT=-javaagent:C:/Java/skywalking-es7-8.6.0/agent/skywalking-agent.jar # SkyWalking Agent jar 地址

# Jar 启动
$ java -jar $JAVA_AGENT -jar skywalking-lab.jar
```

**2. 使用 java 参数**
```bash
$ java -jar -javaagent:C:/Java/skywalking-es7-8.6.0/agent/skywalking-agent.jar -Dskywalking.agent.application_code=skywalking-lab -Dskywalking.collector.servers=127.0.0.1:11800 skywalking-lab.jar
```

其中：
- skywalking.agent.application_code: 配置应用名称；
- skywalking.collector.servers: 配置 Collector 地址。

另外，在开发联调阶段，也可以直接在 idea 中进行设置，如下图所示：

![skywalking-idea](/images/es/skywalking-idea.jpg "skywalking-idea")

## 日志采集

SkyWalking 除了可以采集 trace 及 metric 数据之外，也可以在 log 日志中加入 `traceId`, 并将日志上传存储到 Elasticsearch7 中，结合 trace 一起定位问题。

**1. 引入依赖**

项目中使用的是 logback 框架，引入 skywalking 依赖即可，如果是其它日志框架，可以在官网中找到相关依赖。

```xml
<dependency>
    <groupId>org.apache.skywalking</groupId>
    <artifactId>apm-toolkit-logback-1.x</artifactId>
    <version>8.6.0</version>
</dependency>
```

**2. 日志配置**
 
 在 `logback.xml` 文件中加入 skywalking 的 `appender`, 其中 `tid` 表示 `tracId`, 最后引用该 `appender` 输出日志。

 ```xml
<!-- skywalking 通过grpc采集日志 -->
<appender name="GPRC_SKYWALKING"
          class="org.apache.skywalking.apm.toolkit.log.logback.v1.x.log.GRPCLogClientAppender">
    <encoder class="ch.qos.logback.core.encoder.LayoutWrappingEncoder">
        <layout class="org.apache.skywalking.apm.toolkit.log.logback.v1.x.mdc.TraceIdMDCPatternLogbackLayout">
            <Pattern>%d{yyyy-MM-dd HH:mm:ss.SSS} [%X{tid}] [%thread] %-5level %logger{36} -%msg%n</Pattern>
        </layout>
    </encoder>
</appender>

<!-- 日志输出级别 -->
<root level="INFO">
    <appender-ref ref="STDOUT"/>
    <appender-ref ref="FILE"/>
    <appender-ref ref="GPRC_SKYWALKING"/>
</root>
 ```

 最后输出的日志格式如下所示：
 ```txt
17:20:53.698 [main] INFO  o.s.b.w.e.tomcat.TomcatWebServer - [TID:N/A] - Tomcat initialized with port(s): 8070 (http)
17:20:53.706 [main] INFO  o.a.coyote.http11.Http11NioProtocol - [TID:N/A] - Initializing ProtocolHandler ["http-nio-8070"]
10:07:21.256 [http-nio-8070-exec-9] INFO  o.n.n.NacosProviderApplication$EchoController - [TID:4e52987712fb42308887530e7c8361bb.84.16559500412520005] - Receive a request:skywalking
10:08:12.817 [http-nio-8070-exec-8] INFO  o.n.n.NacosProviderApplication$EchoController - [TID:4e52987712fb42308887530e7c8361bb.83.16559500928140003] - Receive a request:skywalking
```

未收到请求时 `traceId` 为 `[TID:N/A]`, 表示为空，收到请求之后便会正常输出。

**3. 配置 agent**

在本地 log 文件中包含了 `traceId` 之后，可以通过 gPRC 将日志传输给 skywalking, 再存储到 Elasticsearch7 中。要完成这个功能，需要在 `skywalking-es7-8.6.0/agent/config/agent.config` 文件中加入如下配置：
```properties
plugin.toolkit.log.grpc.reporter.server_host=${SW_GRPC_LOG_SERVER_HOST:192.168.1.100}
plugin.toolkit.log.grpc.reporter.server_port=${SW_GRPC_LOG_SERVER_PORT:11800}
plugin.toolkit.log.grpc.reporter.max_message_size=${SW_GRPC_LOG_MAX_MESSAGE_SIZE:10485760}
plugin.toolkit.log.grpc.reporter.upstream_timeout=${SW_GRPC_LOG_GRPC_UPSTREAM_TIMEOUT:30}
```

通过参数指定日志上报服务的地址和端口，另外这些参数也可以通过环境变量进行配置。

## 界面

引入应用之后，现在便可采集 trace 及 log 日志，其效果如下所示：

**1. trace 查询**
![skywalking-trace](/images/es/skywalking-trace.jpg "skywalking-trace")

**2. log 查询**
![skywalking-log](/images/es/skywalking-log.jpg "skywalking-log")

**参考：**

----
[1]:https://skywalking.apache.org/zh/2019-03-29-introduction-of-skywalking-and-simple-practice/
[2]:https://dubbo.apache.org/zh/docs/v2.7/admin/ops/skywalking/
[3]:https://skywalking.apache.org/zh/2020-04-19-skywalking-quick-start/

[1. SkyWalking调研与初步实践][1]
[2. 使用 Apache Skywalking 做分布式跟踪][2]
[3. SkyWalking 极简入门][3]
