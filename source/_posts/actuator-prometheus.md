---
title: Springboot 系列：Actuator + Prometheus
date: 2022-05-29 19:00:50
updated: 2022-05-29 19:00:50
tags:
- actuator
- prometheus
- 监控系统
categories:
- Springboot
---

上篇文章我们将 Spring Actuaor 接入了 Springboot Admin, 本文将对接另外一个著名的监控系统：Prometheus.

<!-- more -->

## 概述

![promethues](/images/spring-cloud/promethues.svg "promethues")

从上图可以看到，整个 Prometheus 可以分为四大部分，分别是：

- Prometheus Server : Prometheus组件中的核心部分，负责实现对监控数据的获取，存储以及查询; 
- Exporter : Methic 数据通过 Pull/Push 两种方式推送数据到 Prometheus Server; 
- AlertManager: 通过配置报警规则，如果符合报警规则，那么就将报警推送到 AlertManager，由其进行报警处理; 
- 可视化监控界面: Prometheus 收集到数据之后，由 WebUI 界面进行可视化图标展示。也可以直接使用 Grafana 来展示。

由于 Prometheus 界面相对比较简单，我们使用 Grafana 进行前端页面展示。

## 项目中引入 Promethues 支持

在 Springboot Actuator 项目中，通过引入 `micrometer-registry-prometheus` 包，将 metric 数据转换为 Promethues 格式的时序数据，将提供 `/actuator/prometheus` endpoint 来获取数据。

```xml
<properties>
    <!-- spring boot -->
    <spring-boot.version>2.2.5.RELEASE</spring-boot.version>
</properties>

<dependencies>
    <!-- springboot actuator -->    
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
    <!-- springboot prometheus --> 
    <dependency>
        <groupId>io.micrometer</groupId>
        <artifactId>micrometer-registry-prometheus</artifactId>
        <version>1.3.20</version>
    </dependency>

</dependencies>
```

**注意：**
- Springboot 与 micrometer-registry-prometheus 的版本需要匹配。

### 加入配置项

```yaml
management:
  endpoints:
    web:
      exposure:
        include: "*"
  metrics:
    tags:
      application: ${spring.application.name}
```

- management.endpoints.web.exposure.include: 开放的监控 endpoints; 
- management.metrics.tags.application: 向 prometheus metric 时序数据中加入 application 的 tag.

## 安装 Promethues


我们使用 Docker 进行安装，选用的版本为 `2.35.0`.

### 安装/启动命令
```bash
# 摘取镜像
$ docker pull prom/prometheus:v2.35.0

# 运行 prometheus
$ docker run -d \
    -p 9090:9090 \
    --name prometheus \
    -v /data/prometheus/conf/prometheus.yml:/etc/prometheus/prometheus.yml \
    prom/prometheus:v2.35.0

```

### 添加配置项

配置文件 `prometheus.yml` 如下配置：
```yaml
scrape_configs:
  - job_name: 'mointor-prometheus'
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: '/actuator/prometheus'
    static_configs:
      - targets: ['192.168.1.100:9501']
```

在这里，Prometheus 使用拉的方式从指定的目标中拉取 metric 数据，并且可以配置拉取的间隔时间及超时时间。
- scrape_interval: 轮洵拉取数据的间隔时间；
- scrape_timeout: 请求超时时间；
- metrics_path: metric endpoit; 
- targets: 配置监控的服务。

### 启动 Promethues

运行 `docker run` 之后即可通过 `http://hostip:9090` 访问 Promethues，可以选择不同的指标进行展示，如下图所示：

![premetheus-overview](/images/spring-cloud/premetheus-overview.jpg "premetheus-overview")

## 安装 Grafana

Promethues web UI 内容相对单一，我们可以引入 Grafana 来进行 UI 展示。

### 安装/启动命令

```bash
# 拉取 grafana 镜像
$ docker pull grafana/grafana:7.5.16

# 运行 grafana
$ docker run -d --name mygrafana -p 3000:3000 grafana/grafana:7.5.16
```

启动之后，通过 `http://hostip:3000` 访问 grafana, 输入默认用户/密码: `admin/admin`, 即可登陆。

![grafana-login](/images/spring-cloud/grafana-login.jpg "grafana-login")

### 添加数据源

向 Grafana 中添加 premetheus 数据源，如下图所示：

![grafana-add-datasource](/images/spring-cloud/grafana-add-datasource.jpg "grafana-add-datasource")

添加成功之后，我们就可以通过 Grafana 查看 premetheus 中的 metric 数据。

![grafana-dashboard](/images/spring-cloud/grafana-dashboard.jpg "grafana-dashboard")

### 添加 Micrometer Dashboard

要实现丰富的数据展示，我们可以根据需要定制展示的内容，但比较费时。为了简化这个操作，Grafana 提供了官方 Micrometer Dashboard，直接添加即可。

**1. 搜索 Micrometer Dashboard**

前往 [Grafana Lab - Dashboards ](https://grafana.com/grafana/dashboards/), 输入关键词 `micrometer` 查询。

![grafana-search-dashboard](/images/spring-cloud/grafana-search-dashboard.jpg "grafana-search-dashboard")

**2. 查看 Micrometer Dashboard 详情**

打开 `Micrometer Dashboard`, 复制 `dashboard id`,方便后续导入操作。

![grafana-dashboard-id](/images/spring-cloud/grafana-dashboard-id.jpg "grafana-dashboard-id")

**3. 导入 Micrometer Dashboard 模板**

在 Grafana 中根据 `dashboard id` 导入 Micrometer Dashboard.

![grafana-imort-dashboard](/images/spring-cloud/grafana-imort-dashboard.jpg "grafana-imort-dashboard")

**4. 使用 Micrometer Dashboard**

使用 `Micrometer Dashboard` 查看 premetheus 数据源数据，其效果如下图所示：

![jvm-micrometer](/images/spring-cloud/jvm-micrometer.jpg "jvm-micrometer")

### 小结
- 引入 Prometheus, grafana 之后，可以方便整合其生态链中相关的监控工作，方便后期扩展。 


[工程代码：https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springboot-monitor](https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springboot-monitor)

</br>

**参考：**

----
[1]:https://www.itmuch.com/spring-boot/actuator-prometheus-grafana/

[1. Spring Boot 2.x监控数据可视化(Actuator + Prometheus + Grafana手把手)][1]
