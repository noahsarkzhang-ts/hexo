---
title: Springboot 系列：Actuator
date: 2022-05-29 11:00:53
updated: 2022-05-29 11:00:53
tags:
- actuator
- metric
- 审计
categories:
- Springboot
---

Actuator 提供了一些特殊的 Http Endpoint, 可以查询服务内部的状态信息，通过它也可以与其它监控系统进行集成，实现服务的监控告警功能。本文讲述 Actuator 的基本功能，后续文章将分别讲述如何与 Springboot Admin 和 prometheus 等系统进行集成。

<!-- more -->

## 概述

Springboot Actuator 模块提供了一个监控和管理生产环境的模块，可以使用 http、jmx、ssh、telnet 等来管理和监控应用。包括应用的审计（Auditing）、健康（health）状态信息、数据采集（metrics gathering）统计等监控运维的功能。同时，提供了可以扩展 Actuator 端点（Endpoint）自定义监控指标。这些指标都是以 JSON 接口数据的方式呈现。

### Endpoints

Actuator 提供的 Endpoins 有：

| HTTP 方法 | Endpoint | 描述 |
|  ----  | ----  | ----  |
| GET | /beans | 获取 Spring Beans 信息 |
| GET | /auditevents | 获取审计事件信息 |
| GET | /conditions | 获取配置类和自动配置类(configuration and auto-configuration classes)的状态及它们被应用或未被应用的原因。。|
| GET | /configprops | 获取 @ConfigurationProperties的集合列表 |
| GET | /env | 获取环境变量信息 |
| GET | /flyway | 获取数据库迁移路径 |
| GET | /health | 获取应用的健康信息 |
| GET | /info | 获取应用信息 |
| GET | /liquibase | 获取 Liquibase 数据库迁移路径 |
| GET | /metrics | 获取当前应用的 metrics 信息 |
| GET | /mappings | 获取所有 @RequestMapping 路径的集合 |
| GET | /scheduledtasks | 获取应用程序中的计划任务 |
| GET | /sessions | 获取 Spring Session 会话信息 | 
| POST | /shutdown | 关闭应用 |
| GET | /threaddump | 获取线程 dump 信息 |
| GET | /heapdump | 获取 jvm dump文件 |

出于安全的原因，大部分 Endpoints 是关闭的，可以通过以下的属性开启：
- management.endpoints.web.exposure.include='*', 代表开启全部监控，也可仅配置需要开启的监控，如： management.endpoints.web.exposure.include=beans,trace。
- management.endpoint.health.show-details=always, health endpoint开启显示全部细节。默认情况下 `/actuator/health` 是公开的，但不显示细节。
- management.endpoints.web.base-path=/monitor, 启用指定的 ur l地址访问根路径，默认路径为 `/actuator/*` , 开启则访问路径变为 `/monitor/*`. 
- management.endpoint.shutdown.enabled=true, 启用接口关闭 SpringBoot. 

### 集成

Springboot Actuator 借助 Micrometer，能够对接以下的各种监控系统：
- AppOptics
- Atlas
- Datadog
- Dynatrace
- Elastic
- Ganglia
- Graphite
- Humio
- Influx
- JMX
- KairosDB
- New Relic
- Prometheus
- SignalFx
- Simple (in-memory)
- StatsD
- Wavefront

## 实例

本节讲述如何在系统中引用 Actuator。

### 依赖

引入如下的依赖：

```xml
<properties>
    <!-- spring boot -->
    <spring-boot.version>2.2.5.RELEASE</spring-boot.version>
</properties>

<!-- spring boot web -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>

<!-- spring boot actuator -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

### 加入配置
公开所有的 Endpoints, 也可以需要进行配置。

```yaml
management:
  endpoints:
    web:
      exposure:
        include: "*"
```

### 启动应用

假定应用的端口为 `8080`, 启动 Springboot 应用，打开 `http://localhost:8080/actuator/` url, 即可看到可用的 Endpoints, 如下所示：
```json
{
    "_links":{
        "self":{
            "href":"http://localhost:8080/actuator",
            "templated":false
        },
        "beans":{
            "href":"http://localhost:8080/actuator/beans",
            "templated":false
        },
        "caches-cache":{
            "href":"http://localhost:8080/actuator/caches/{cache}",
            "templated":true
        },
        "caches":{
            "href":"http://localhost:8080/actuator/caches",
            "templated":false
        },
        "health":{
            "href":"http://localhost:8080/actuator/health",
            "templated":false
        },
        "health-path":{
            "href":"http://localhost:8080/actuator/health/{*path}",
            "templated":true
        },
        "info":{
            "href":"http://localhost:8080/actuator/info",
            "templated":false
        },
        "conditions":{
            "href":"http://localhost:8080/actuator/conditions",
            "templated":false
        },
        "configprops":{
            "href":"http://localhost:8080/actuator/configprops",
            "templated":false
        },
        "env":{
            "href":"http://localhost:8080/actuator/env",
            "templated":false
        },
        "env-toMatch":{
            "href":"http://localhost:8080/actuator/env/{toMatch}",
            "templated":true
        },
        "loggers":{
            "href":"http://localhost:8080/actuator/loggers",
            "templated":false
        },
        "loggers-name":{
            "href":"http://localhost:8080/actuator/loggers/{name}",
            "templated":true
        },
        "heapdump":{
            "href":"http://localhost:8080/actuator/heapdump",
            "templated":false
        },
        "threaddump":{
            "href":"http://localhost:8080/actuator/threaddump",
            "templated":false
        },
        "metrics":{
            "href":"http://localhost:8080/actuator/metrics",
            "templated":false
        },
        "metrics-requiredMetricName":{
            "href":"http://localhost:8080/actuator/metrics/{requiredMetricName}",
            "templated":true
        },
        "scheduledtasks":{
            "href":"http://localhost:8080/actuator/scheduledtasks",
            "templated":false
        },
        "mappings":{
            "href":"http://localhost:8080/actuator/mappings",
            "templated":false
        }
    }
}

```

**说明：**
Endpoints 会根据加载的组件动态提供，另外不同版本的 Endpoints 也会有差异。

### Metric

以 Metric 数据为例，`http://localhost:8080/actuator/metrics` 显示了所有的 Metric 列表：
```json
{
    "names":[
        "jvm.threads.states",
        "http.server.requests",
        "jvm.memory.used",
        "jvm.gc.memory.promoted",
        "jvm.memory.max",
        "jvm.gc.max.data.size",
        "jvm.memory.committed",
        "system.cpu.count",
        "logback.events",
        "jvm.buffer.memory.used",
        "tomcat.sessions.created",
        "jvm.threads.daemon",
        "system.cpu.usage",
        "jvm.gc.memory.allocated",
        "tomcat.sessions.expired",
        "jvm.threads.live",
        "jvm.threads.peak",
        "process.uptime",
        "tomcat.sessions.rejected",
        "process.cpu.usage",
        "jvm.classes.loaded",
        "jvm.classes.unloaded",
        "tomcat.sessions.active.current",
        "tomcat.sessions.alive.max",
        "jvm.gc.live.data.size",
        "jvm.buffer.count",
        "jvm.buffer.total.capacity",
        "tomcat.sessions.active.max",
        "process.start.time"
    ]
}
```

如果想获取某个 Metric 当前的状态信息，在 url 加上名称即可，例如想获取 `http.server.requests` 信息，url 为 `http://localhost:8080/actuator/metrics/http.server.requests`, 返回内容如下所示：

```json
{
    "name":"http.server.requests",
    "description":null,
    "baseUnit":"seconds",
    "measurements":[
        {
            "statistic":"COUNT",
            "value":165
        },
        {
            "statistic":"TOTAL_TIME",
            "value":0.4330701
        },
        {
            "statistic":"MAX",
            "value":0.0019737
        }
    ],
    "availableTags":[
        {
            "tag":"exception",
            "values":[
                "None"
            ]
        },
        {
            "tag":"method",
            "values":[
                "GET"
            ]
        },
        {
            "tag":"uri",
            "values":[
                "/actuator/metrics/{requiredMetricName}",
                "/actuator/configprops",
                "/actuator",
                "/actuator/health",
                "/actuator/info",
                "/actuator/metrics",
                "/**",
                "/actuator/env"
            ]
        },
        {
            "tag":"outcome",
            "values":[
                "CLIENT_ERROR",
                "SUCCESS"
            ]
        },
        {
            "tag":"status",
            "values":[
                "404",
                "200"
            ]
        }
    ]
}
```

Metric 数据是监控的基础数据，在与其它监控系统的对接中，会将其转换为对应的格式，如 prometheus, 我们后续为讲到。

[工程代码：https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springboot-monitor](https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springboot-monitor)

</br>

**参考：**

----
[1]:https://juejin.cn/post/6844904000832159751

[1. Spring Boot Actuator监控使用详解][1]

