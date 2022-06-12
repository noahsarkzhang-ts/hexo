---
title: ELK
date: 2022-06-05 12:44:28
tags:
- ELK
- logstash
categories:
- Elasticsearch
---

这篇文章包含两部分内容：1）Springboot 项目集成 ELK; 2）分析 log 数据的存储模型。

<!-- more -->

## 概述

![elk-logstash-flow](/images/es/elk-logstash-flow.jpg "elk-logstash-flow")

ELK 是 Elasticsearch, Logstash, Kibana 三个组件的首字母，对应三个处理步骤：
- Logstash: 采集模块，读取日志文件写入到 Elasticsearch, 可以使用拉/推两种方式：1）直接读取日志文件；2）开放端口，将数据推送上来；
- Elasticsearch: 存储模块，存储日志文件；
- Kibana: 从 Elasticsearch 搜索查询日志文件。

在本文中，日志采集使用推的方式，Springboot 项目将日志推送到 Logstash 的指定端口上。另外，在本文中，我们只安装 Logstash, Elasticsearch 及 Kibana 安装部署参考之前的文章：[Docker 下安装 ES, Kibana](https://zhangxt.top/2022/01/29/es-deployment-in-docker/)

**约定：**
ELK 三个组件的版本为：V7.14.2.

## 安装 Logstash

### 下载及部署 Logstash
从官方网址下载指定的版本：[Logstash 下载地址](https://www.elastic.co/cn/downloads/past-releases/logstash-7-14-2) 

```bash
# 下载 Logstash
$ wget https://artifacts.elastic.co/downloads/logstash/logstash-7.14.2-linux-x86_64.tar.gz

# 解压缩
$ tar -xzvf logstash-7.14.2-linux-x86_64.tar.gz
```

### 添加配置文件
在 `config` 目录下新建一个配置文件 `logstash-logback.conf` 文件，内容如下：

```conf
input {
        tcp {
        host => "0.0.0.0"
        port => 9999
        mode => "server"
        codec => json_lines
        }
}

filter{
    date{
        match => ["timestamp","dd-MMM-yyyy:HH:mm:ss Z"]
    }
}

output {
        stdout { codec => rubydebug }
        elasticsearch { 
                hosts => "192.168.1.100:9200"
                index => "logstash-%{+YYYY.MM.dd}"
                user => "elastic"
                password => "yourpassword"
        }
}

```

有三个部分的内容：
- input: 开启 tcp 9999 端口，接收日志；
- filter: 定义 timestamp 格式；
- output：定义两个输出，一个是控制台，方便定位问题，一个写入 Elasticsearch, 按天生成索引；

### 启动 Logstash

```bash
# 切换到 logstash 安装目录
$ cd logstash 安装目录

# 启动 logstash
$ nohup ./bin/logstash -f config/logstash-logback.conf &

```

## 集成 Logstash

假定在 Springboot 中使用 Logback 日志框架，需要引入 `logstash-logback-encoder` 相关 jar 包。

### 相关依赖

```xml
<properties>
    <!-- spring boot -->
    <spring-boot.version>2.2.5.RELEASE</spring-boot.version>
</properties>

<dependencies>
    <!--logStash-->
    <dependency>
        <groupId>net.logstash.logback</groupId>
        <artifactId>logstash-logback-encoder</artifactId>
        <version>7.2</version>
    </dependency>

    <dependency>
        <artifactId>slf4j-api</artifactId>
        <groupId>org.slf4j</groupId>
        <version>1.7.26</version>
    </dependency>

</dependencies>
```

### 修改 Logback 配置文件

添加 Logstash Appender, 指定 Logstash 的地址及日志级别便可将日志推送上去。

```xml
<configuration debug="false">
    <!-- 读取配置文件中的 appname -->   
    <springProperty scope="context" name="appName" source="spring.application.name"/>

    <!-- 其它配置 --> 

   <!-- 添加 Logstash Appender --> 
    <appender name="LOGSTASH" class="net.logstash.logback.appender.LogstashTcpSocketAppender">
        <!-- 指定 logstash 的地址 -->
        <destination>192.168.1.100:9999</destination>
        <param name="Encoding" value="UTF-8"/>
        <!-- 指定编码格式 -->
        <encoder charset="UTF-8" class="net.logstash.logback.encoder.LogstashEncoder" >
            <!-- 添加自定义字段，如 appName -->
            <customFields>{"appName":"${appName}"}</customFields>
        </encoder>
    </appender>

    <!-- 日志输出级别 -->
    <root level="INFO">
        <appender-ref ref="LOGSTASH"/>
    </root>

</configuration>
```

### 修改应用配置项
如果 logback 配置文件需要通过 `springProperty` 读取配置项的内容，由于加载顺序的原因，使用 `logback.xml` 不能加载 `${appName}` 变量的内容。必须新建一个 logback 配置文件，如 logback-spring.xml, 并在 `application.yaml` 文件中指定其路径。

```yaml
logging:
  config: classpath:logback-spring.xml
  file:
    name: logs/logstash
```

### 写日志

启动项目之后，与常规的写日志方式一样便可将日志推送到 Logstash 中。其格式如下所示： 

```json
{
    "thread_name" => "scheduling-1",
          "level" => "INFO",
           "host" => "192.168.1.100",
        "message" => "logstash test!",
    "level_value" => 20000,
           "port" => 55360,
       "@version" => "1",
     "@timestamp" => 2022-05-31T02:59:30.001Z,
    "logger_name" => "org.noahsark.monitor.MonitorLogstashApplication",
        "appName" => "moniotr-logstash"
}

```

## 查询日志

要在 Kibana 中查询日志，需要先定义一个 index pattern, 然后通过 Discover 查询日志。

### 定义 Index Pattern

按照以下的路径创建 Index Pattern: Management --> Stack Management --> Index patterns --> Create index pattern.

![kibana-index-pattern](/images/es/kibana-index-pattern.jpg "kibana-index-pattern")

### 查询日志

创建 Index Pattern 之后，便可通过 Discover 功能查询日志，如下图所示：

![kibana-search-log](/images/es/kibana-search-log.jpg "kibana-search-log")

## 存储模型

### Index Mapping

可以通过 `Index Management` 查看 index 的信息。

![kibana-index-mapping](/images/es/kibana-index-mapping.jpg "kibana-index-mapping")

Log 日志的 Index Mapping 定义如下所示：

```json
{
  "mappings": {
    "_doc": {
      "dynamic_templates": [
        {
          "message_field": {
            "path_match": "message",
            "match_mapping_type": "string",
            "mapping": {
              "norms": false,
              "type": "text"
            }
          }
        },
        {
          "string_fields": {
            "match": "*",
            "match_mapping_type": "string",
            "mapping": {
              "fields": {
                "keyword": {
                  "ignore_above": 256,
                  "type": "keyword"
                }
              },
              "norms": false,
              "type": "text"
            }
          }
        }
      ],
      "properties": {
        "@timestamp": {
          "type": "date"
        },
        "@version": {
          "type": "keyword"
        },
        "appName": {
          "type": "text",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          },
          "norms": false
        },
        "geoip": {
          "dynamic": "true",
          "properties": {
            "ip": {
              "type": "ip"
            },
            "latitude": {
              "type": "half_float"
            },
            "location": {
              "type": "geo_point"
            },
            "longitude": {
              "type": "half_float"
            }
          }
        },
        "host": {
          "type": "text",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          },
          "norms": false
        },
        "level": {
          "type": "text",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          },
          "norms": false
        },
        "level_value": {
          "type": "long"
        },
        "logger_name": {
          "type": "text",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          },
          "norms": false
        },
        "message": {
          "type": "text",
          "norms": false
        },
        "port": {
          "type": "long"
        },
        "thread_name": {
          "type": "text",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          },
          "norms": false
        }
      }
    }
  }
}
```

### Field 分析

**1. Dynamic templates**
在 Elasticsearch 中，可以通过设置 `dynamic` 参数为 `true` 或 `runtime` 来动态识别字段，这些识别的规则是内置的。另外，也可以通过 `Dynamic templates` 来自定义识别规则，格式如下所示：

```yaml
"dynamic_templates": [
    {
      "my_template_name": { // 1
        ... match conditions ... // 2
        "mapping": { ... }  // 3
      }
    },
    ...
  ]
```

- 1 为模板的名称；
- 2 为匹配的表达式，包括：match_mapping_type, match, match_pattern, unmatch, path_match, path_unmatch;
- 3 为转换之后的映射。

**匹配表达式的含义：**
- match_mapping_type: Elasticsearch 自动识别出的类型；
- match and unmatch：用于匹配字段名称；
- path_match and path_unmatch: 用于匹配字段的路径及字段。

**实例 1：**
```json
{
  "message_field": {
    "path_match": "message",
    "match_mapping_type": "string",
    "mapping": {
      "norms": false,
      "type": "text"
    }
  }
}
```
这个 `Dynamic templates` 的含义为将字段名为 `message` 且类型为 `string` 的字段映射为 `text` 类型,且 `norms` 为 `fasle`.

**实例 2：**
```json
{
  "string_fields": {
    "match": "*",
    "match_mapping_type": "string",
    "mapping": {
      "fields": {
        "keyword": {
          "ignore_above": 256,
          "type": "keyword"
        }
      },
      "norms": false,
      "type": "text"
    }
  }
}
```

这个 `Dynamic templates` 的含义为任意类型为 `string` 的字段映射为多字段类型：一个字段为 `text` 类型,且 `norms` 为 `fasle`, 另外一个 `keyword` 类型，且只索引前 256 个字符。

> Norms ：Norms are index-time scoring factors. If you do not care about scoring, which would be the case for instance if you never sort documents by score, you could disable the storage of these scoring factors in the index and save some space. 

如果一个字段匹配多个 `Dynamic templates`, 如何选择呢？ Elasticsearch 按照顺序选择匹配的第一个。

> Templates are processed in order — the first matching template wins. 

**2. Multi-field**
可以对一个 `field` 定义多个类型，或设置多种分词格式，如下所示：
```json
"appName": {
  "fields": {
    "keyword": {
      "type": "keyword",
      "ignore_above": 256
    }
  },
  "type": "text",
  "norms": false
}
```

`appName` 设置为 `text` 和 `keyword` 类型，`text` 可以对字段进行分词，而 `keyword` 不分词，只索引。

**3. 时间戳**

在 `log` index 里，设置了类型为 `date` 的 `@timestamp` 字段用来表示日志发生的时间。

**4. Object 类型**

Elasticsearch 是一个文档型数据库，它存储的数据为 json 类型，字段类型可以是基本类型，如 string, int, long, double 等等，也可以是 Ojbect 类型，如下所示：

```json
"properties": {

  "geoip": {
    "dynamic": "true",
    "properties": {
      "ip": {
        "type": "ip"
      },
      "latitude": {
        "type": "half_float"
      },
      "location": {
        "type": "geo_point"
      },
      "longitude": {
        "type": "half_float"
      }
    }
  },
  // ...
}
```
`geoip` 是一个 `Object` 类型，包括：ip, latitude, location, longitude 等等。


[工程代码：https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springboot-monitor](https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springboot-monitor)

</br>

**参考：**

----
[1]:https://www.elastic.co/guide/en/elasticsearch/reference/current/dynamic-templates.html
[2]:https://www.elastic.co/guide/en/elasticsearch/reference/current/multi-fields.html

[1. Elasticsearch: Dynamic templates ][1]
[2. Elasticsearch: fields][2]
