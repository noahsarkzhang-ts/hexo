---
title: Skywalking 存储模型
date: 2022-07-02 10:37:52
tags:
- skywalking
- 存储模型
- service
- service instance
- endpoint
- metric
- trace
- log
- event
categories:
- Elasticsearch
---

这篇文章讲述 Skywalking 的存储模型。

<!-- more -->

## 概述

在 Skywalking 中主要存储有四种类型的数据：
1. metric: 时序数据，该数据的特点是跟时间强相关，一般有四个元素构成：1) 名称；2）时间戳；3）数值；4）标签(tag),表示对指标的属性；
2. trace: 调用链数据；
3. log: 日志类数据，如项目中 logback 等框架输出的日志；
4. event: 事件类型，如服务启动。

其界面如下所示：

**1. Metric**
![skywalking-dashboard](/images/es/skywalking-dashboard-v2.jpg "skywalking-dashboard")

**2. Trace**
![skywalking-trace](/images/es/skywalking-trace.jpg "skywalking-trace")

**3. Log**
![skywalking-log](/images/es/skywalking-log-v2.jpg "skywalking-log")

**4. Event**
![skywalking-event](/images/es/skywalking-event-v2.jpg "skywalking-event")

## Service-Instance-Endpoint 概念

在 Skywalking 中，有三个比较重要的概念：1）Service; 2) Instance; 3) Endpoint, 在 Metric, Trace, Log 数据中都会关联这些属性，从而方便统计和查询：
- Service: 代表一个可以提供服务能力的实体，可对应微服务体系中的一个服务；
- Instance: 代表一个服务实例进程，一个 Service 可以运行多个 Instance；
- Endpoint: 代表一个请求接口，一个服务中可以包含多个 Endpoint.

### 工程结构

假定有如下的服务，其中 `NacosProviderApp` 是服务提供方，提供了一个 `/hello/{string}` endpoint, `NacosConsumerApp` 是服务消费方，通过浏览器访问。

![skywalking-example](/images/es/skywalking-example.jpg "skywalking-example")

### Service-Instance-Endpoint 索引

项目接入 Skywalking 中，会使用相应的索引存储这些信息。

| 索引名称      | 描述 |
| ----------- | ----------- |
| {namespace}_service_traffic-yyyyMMdd      |  服务信息       |
| {namespace}_instance_traffic-yyyyMMdd    | 服务实例信息        |
| {namespace}_endpoint_traffic-yyyyMMdd    | Endpoint 信息        |
| {namespace}_service_relation_server_side-yyyyMMdd    | 服务之间的关联关系        |

**说明：**
1. 假定 `namespace` 为 my-elasticsearch; 
2. 每一份表会根据业务情况按天生成索引。

### Service 索引

**1. Mapping**
通过命令 `GET my-elasticsearch_service_traffic-20220701/_mapping` 查看索引结构。

```json
{
  "my-elasticsearch_service_traffic-20220701" : {
    "mappings" : {
      "properties" : {
        "name" : {
          "type" : "keyword",
          "copy_to" : [
            "name_match"
          ]
        },
        "name_match" : {
          "type" : "text",
          "analyzer" : "oap_analyzer"
        },
        "node_type" : {
          "type" : "integer"
        },
        "service_group" : {
          "type" : "keyword"
        },
        "time_bucket" : {
          "type" : "long"
        }
      }
    }
  }
}
```

**2. 索引结构**

| 字段名称      | 类型  |   备注  |
| ----------- | ----------- | ----------- |
| _id      |  keyword      |   唯一id  |
| name      |  keyword      |   服务名称  |
| node_type    | integer        |      |
| service_group  | keyword        |   服务分组   |
| time_bucket   | long        |   时间桶   |

**3. 数据**
通过命令 `GET my-elasticsearch_service_traffic-20220701/_search` 查看数据。

```json
{
  "took" : 0,
  "timed_out" : false,
  "_shards" : {
    "total" : 1,
    "successful" : 1,
    "skipped" : 0,
    "failed" : 0
  },
  "hits" : {
    "total" : {
      "value" : 2,
      "relation" : "eq"
    },
    "max_score" : 1.0,
    "hits" : [
      {
        "_index" : "my-elasticsearch_service_traffic-20220701",
        "_type" : "_doc",
        "_id" : "TmFjb3NDb25zdW1lckFwcA==.1",
        "_score" : 1.0,
        "_source" : {
          "node_type" : 0,
          "name" : "NacosConsumerApp",
          "service_group" : null
        }
      },
      {
        "_index" : "my-elasticsearch_service_traffic-20220701",
        "_type" : "_doc",
        "_id" : "TmFjb3NQcm92aWRlckFwcA==.1",
        "_score" : 1.0,
        "_source" : {
          "node_type" : 0,
          "name" : "NacosProviderApp",
          "service_group" : null
        }
      }
    ]
  }
}
```

| _id      | name  |   node_type  | service_group | time_bucket  |
| ----------- | ----------- | ----------- | ----------- | ----------- |
| TmFjb3NQcm92aWRlckFwcA==.1      |   NacosProviderApp    |   0  | null | | 
| TmFjb3NDb25zdW1lckFwcA==.1      |   NacosConsumerApp    |   0  | null | | 

### Instace 索引
**1. Mapping**
通过命令 `GET my-elasticsearch_instance_traffic-20220701/_mapping` 查看索引结构。

```json
{
  "my-elasticsearch_instance_traffic-20220701" : {
    "mappings" : {
      "properties" : {
        "last_ping" : {
          "type" : "long"
        },
        "name" : {
          "type" : "keyword",
          "index" : false
        },
        "properties" : {
          "type" : "text",
          "index" : false
        },
        "service_id" : {
          "type" : "keyword"
        },
        "time_bucket" : {
          "type" : "long"
        }
      }
    }
  }
}

```

**2. 索引结构**

| 字段名称      | 类型  |   备注  |
| ----------- | ----------- | ----------- |
| _id      |  keyword      |   唯一id  |
| last_ping      |  long      |   最近一次 ping 的时间  |
| name    | keyword        |   "index" : false   |
| properties  | text        | 属性字段，不索引，"index" : false  |
| service_id  | keyword        |   |
| time_bucket   | long        |   时间桶   |

**3. 数据**
通过命令 `GET my-elasticsearch_instance_traffic-20220701/_search` 查看数据。

```json
{
  "took" : 0,
  "timed_out" : false,
  "_shards" : {
    "total" : 1,
    "successful" : 1,
    "skipped" : 0,
    "failed" : 0
  },
  "hits" : {
    "total" : {
      "value" : 4,
      "relation" : "eq"
    },
    "max_score" : 1.0,
    "hits" : [
      {
        "_index" : "my-elasticsearch_instance_traffic-20220701",
        "_type" : "_doc",
        "_id" : "TmFjb3NDb25zdW1lckFwcA==.1_ZWI4MjlmMzQ5ZjE4NGQ3NmI2OGQwZWI2MGNjYmFiYzFAMTkyLjE2OC42OC42Mg==",
        "_score" : 1.0,
        "_source" : {
          "last_ping" : 202207021756,
          "service_id" : "TmFjb3NDb25zdW1lckFwcA==.1",
          "name" : "eb829f349f184d76b68d0eb60ccbabc1@192.168.68.62",
          "time_bucket" : 202207011826,
          "properties" : """{"OS Name":"Windows 10","hostname":"DESKTOP-ICO161","Process No.":"7640","language":"java","ipv4s":"192.168.68.62"}"""
        }
      },
      {
        "_index" : "my-elasticsearch_instance_traffic-20220701",
        "_type" : "_doc",
        "_id" : "TmFjb3NQcm92aWRlckFwcA==.1_ZGMzMDZkYTI1NWVkNDJjMWIxYjU2NmNlZTI3NDYwZWRAMTkyLjE2OC42OC42Mg==",
        "_score" : 1.0,
        "_source" : {
          "last_ping" : 202207021757,
          "service_id" : "TmFjb3NQcm92aWRlckFwcA==.1",
          "name" : "dc306da255ed42c1b1b566cee27460ed@192.168.68.62",
          "time_bucket" : 202207011827,
          "properties" : """{"OS Name":"Windows 10","hostname":"DESKTOP-ICO161","Process No.":"22100","language":"java","ipv4s":"192.168.68.62"}"""
        }
      }
    ]
  }
}

```

| _id      | last_ping  |   name  | service_id | properties |  time_bucket  |
| ----------- | ----------- | ----------- | ----------- | ----------- |----------- |
| Tm...    |   202207021756    |   {..}@192.168.68.62  | TmFjb3NDb25zdW1lckFwcA==.1 | ... | 202207011826 | 
| Tm...    |   202207021757    |   {...}@192.168.68.62  | TmFjb3NQcm92aWRlckFwcA==.1 | ... | 202207011827 |  

**说明：**
- 通过 `last_ping` 字段进行服务的保活；
- 通过 `service_id` 关联服务索引；
- `time_bucket` 字段记录了服务启动的时间；
- `service_id` 标识了一个服务实例，格式为：{随机字串}@hostname(ip).

### Endpoint 索引
**1. Mapping**
通过命令 `GET my-elasticsearch_endpoint_traffic-20220626/_mapping` 查看索引结构。

```json
{
  "my-elasticsearch_endpoint_traffic-20220626" : {
    "mappings" : {
      "properties" : {
        "name" : {
          "type" : "keyword",
          "copy_to" : [
            "name_match"
          ]
        },
        "name_match" : {
          "type" : "text",
          "analyzer" : "oap_analyzer"
        },
        "service_id" : {
          "type" : "keyword"
        },
        "time_bucket" : {
          "type" : "long"
        }
      }
    }
  }
}

```

**2. 索引结构**

| 字段名称      | 类型  |   备注  |
| ----------- | ----------- | ----------- |
| _id      |  keyword      |   唯一id  |
| name    | keyword        |   将内容 copy_to name_match字段，进行分词索引   |
| name_match  | text        | 进行分词索引  |
| service_id  | keyword        | 关联到服务索引  |
| time_bucket   | long        |   时间桶   |

**3. 数据**

通过命令 `GET my-elasticsearch_endpoint_traffic-20220626/_search` 查看数据。

```json
{
  "took" : 0,
  "timed_out" : false,
  "_shards" : {
    "total" : 1,
    "successful" : 1,
    "skipped" : 0,
    "failed" : 0
  },
  "hits" : {
    "total" : {
      "value" : 2,
      "relation" : "eq"
    },
    "max_score" : 1.0,
    "hits" : [
      {
        "_index" : "my-elasticsearch_endpoint_traffic-20220626",
        "_type" : "_doc",
        "_id" : "TmFjb3NDb25zdW1lckFwcA==.1_e0dFVH0vZWNoby97c3RyfQ==",
        "_score" : 1.0,
        "_source" : {
          "service_id" : "TmFjb3NDb25zdW1lckFwcA==.1",
          "name" : "{GET}/echo/{str}",
          "time_bucket" : 202206261908
        }
      },
      {
        "_index" : "my-elasticsearch_endpoint_traffic-20220626",
        "_type" : "_doc",
        "_id" : "TmFjb3NQcm92aWRlckFwcA==.1_e0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn0=",
        "_score" : 1.0,
        "_source" : {
          "service_id" : "TmFjb3NQcm92aWRlckFwcA==.1",
          "name" : "{GET}/services/hello/{str}",
          "time_bucket" : 202206261908
        }
      }
    ]
  }
}

```

| _id      |   name  | service_id |  time_bucket  |
| ----------- | ----------- | ----------- | ----------- | 
| Tm...    |   {GET}/echo/{str}    |   TmFjb3NDb25zdW1lckFwcA==.1  | 202206261908 |
| Tm...  |   {GET}/services/hello/{str}    |   TmFjb3NQcm92aWRlckFwcA==.1  | 202206261908 | 

### 服务关系索引
**1. Mapping**
通过命令 `GET my-elasticsearch_service_relation_server_side-20220627/_mapping` 查看索引结构。

```json
{
  "my-elasticsearch_service_relation_server_side-20220627" : {
    "mappings" : {
      "properties" : {
        "component_id" : {
          "type" : "integer",
          "index" : false
        },
        "dest_service_id" : {
          "type" : "keyword"
        },
        "entity_id" : {
          "type" : "keyword"
        },
        "source_service_id" : {
          "type" : "keyword"
        },
        "time_bucket" : {
          "type" : "long"
        }
      }
    }
  }
}

```

**2. 索引结构**

| 字段名称      | 类型  |   备注  |
| ----------- | ----------- | ----------- |
| _id      |  keyword      |   唯一id  |
| component_id    | integer        |      |
| source_service_id  | keyword        | 源服务 id  |
| dest_service_id  | keyword        | 目标服务 id  |
| entity_id  | keyword        |   |
| time_bucket   | long        |   时间桶   |

**3. 数据**
通过命令 `GET my-elasticsearch_service_relation_server_side-20220627/_search` 查看数据。

```json
{
  "took" : 0,
  "timed_out" : false,
  "_shards" : {
    "total" : 1,
    "successful" : 1,
    "skipped" : 0,
    "failed" : 0
  },
  "hits" : {
    "total" : {
      "value" : 2,
      "relation" : "eq"
    },
    "max_score" : 1.0,
    "hits" : [
      {
        "_index" : "my-elasticsearch_service_relation_server_side-20220627",
        "_type" : "_doc",
        "_id" : "202206271817_TmFjb3NDb25zdW1lckFwcA==.1-TmFjb3NQcm92aWRlckFwcA==.1",
        "_score" : 1.0,
        "_source" : {
          "source_service_id" : "TmFjb3NDb25zdW1lckFwcA==.1",
          "component_id" : 14,
          "dest_service_id" : "TmFjb3NQcm92aWRlckFwcA==.1",
          "time_bucket" : 202206271817,
          "entity_id" : "TmFjb3NDb25zdW1lckFwcA==.1-TmFjb3NQcm92aWRlckFwcA==.1"
        }
      },
      {
        "_index" : "my-elasticsearch_service_relation_server_side-20220627",
        "_type" : "_doc",
        "_id" : "202206271817_VXNlcg==.0-TmFjb3NDb25zdW1lckFwcA==.1",
        "_score" : 1.0,
        "_source" : {
          "source_service_id" : "VXNlcg==.0",
          "component_id" : 14,
          "dest_service_id" : "TmFjb3NDb25zdW1lckFwcA==.1",
          "time_bucket" : 202206271817,
          "entity_id" : "VXNlcg==.0-TmFjb3NDb25zdW1lckFwcA==.1"
        }
      }
    ]
  }
}



```

| _id      |   component_id  | source_service_id | dest_service_id | entity_id | time_bucket  |
| ----------- | ----------- | ----------- | ----------- | 
| 202..  |   14    |   TmFjb3NDb25zdW1lckFwcA==.1 |  TmFjb3NQcm92aWRlckFwcA==.1 | Tm...  | 202206271817 | 
| 202..  |   14    |   VXNlcg==.0 | TmFjb3NDb25zdW1lckFwcA==.1  | VX...  |  202206271817 | 

**说明：**
通过 `source_service_id` 和 `dest_service_id` 两个字段，可以建立起服务之间的调用关系，从而得到服务之间的拓扑图。根据上面的关系，可以得出拓扑图为：`VXNlcg==.0(user)  --> TmFjb3NDb25zdW1lckFwcA==.1(NacosConsumerApp) --> TmFjb3NQcm92aWRlckFwcA==.1(NacosProviderApp)`.

![skywalking-topology](/images/es/skywalking-topology.jpg "skywalking-topology")

## Metric 

Skywalking 可以存储以下类别的 Metric 数据：APM, Database, Event, Istio, Istio Data Plane, K8s, SelfObservability, VM, Web Browser. 项目中对接 Skywalking 之后，便可采集 APM 的数据。在本文中，我们分析 APM metric 指标，下图展示了 APM 中包含的所有指标。

![skywalking-apm-metric](/images/es/skywalking-apm-metric.png "skywalking-apm-metric")

### 统计维度

APM metric 指标可以从四个不同的维度进行统计，分别是 Global, Service, Instance, Endpoint. 其含义如下：Global 是从全局整体的维度统计数据，其它维度参考上文的内容。

| 指标   |   索引  | 描述 |
| ----------- | ----------- | ----------- |
| all_percentile  |   {namespace}_metrics-percentile-yyyyMMdd    |  服务健康程度  |
| service_apdex  |   {namespace}_metrics-apdex-yyyyMMdd    |  服务健康程度  |
| service_resp_time  |   {namespace}_metrics-longavg-yyyyMMdd    |  服务平均响应时间  |
| service_sla  |   {namespace}_metrics-percent-yyyyMMdd    |  服务请求成功率  |
| service_cpm  |   {namespace}_metrics-cpm-yyyyMMdd    |  服务每分钟请求数  |
| service_percentile  |   {namespace}_metrics-percentile-yyyyMMdd    |  百分比响应延时  |
| service_instance_cpm  |   {namespace}_metrics-cpm-yyyyMMdd    |  服务实例每分钟请求数  |
| service_instance_resp_time  |   {namespace}_metrics-longavg-yyyyMMdd    |  每个服务实例的最大延时  |
| service_instance_sla  |   {namespace}_metrics-percent-yyyyMMdd    |  每个服务实例的请求成功率  |
| instance_jvm_cpu  |   {namespace}_metrics-doubleavg-yyyyMMdd    |  jvm占用CPU的百分比  |
| instance_jvm_memory_heap  |   {namespace}_metrics-longavg-yyyyMMdd    |  JVM内存占用大小，单位m  |
| instance_jvm_young_gc_time  |   {namespace}_metrics-sum-yyyyMMdd    |  JVM垃圾回收时间  |
| instance_jvm_thread_live_count  |   {namespace}_metrics-longavg-yyyyMMdd    |  JVM线程数量  |
| instance_jvm_thread_runnable_state_thread_count  |   {namespace}_metrics-longavg-yyyyMMdd    |  JVM不同状态线程数量  |
| instance_jvm_class_loaded_class_count  |   {namespace}_metrics-longavg-yyyyMMdd    |  JVM对象的数量  |
| endpoint_cpm  |   {namespace}_metrics-cpm-yyyyMMdd    |  每个端点的每分钟请求数  |
| endpoint_avg  |   {namespace}_metrics-longavg-yyyyMMdd    |  每个端点的最慢请求时间，单位ms |
| endpoint_sla  |   {namespace}_metrics-percent-yyyyMMdd    |  每个端点的请求成功率  |
| endpoint_percentile  |   {namespace}_metrics-percentile-yyyyMMdd    |  当前端点每个时间段的响应时间占比  |



下面以 `endpoint_avg`, `service_resp_time`,`endpoint_percentile` 为例，分析其存储模型。

### endpoint_avg: 请求响应的平均时间
**1. Mapping**
通过命令 `GET my-elasticsearch_metrics-longavg-20220702/_mapping` 查看索引结构。

```json
{
  "my-elasticsearch_metrics-longavg-20220702" : {
    "mappings" : {
      "properties" : {
        "count" : {
          "type" : "long",
          "index" : false
        },
        "entity_id" : {
          "type" : "keyword"
        },
        "metric_table" : {
          "type" : "keyword"
        },
        "service_id" : {
          "type" : "keyword"
        },
        "summation" : {
          "type" : "long",
          "index" : false
        },
        "time_bucket" : {
          "type" : "long"
        },
        "value" : {
          "type" : "long"
        }
      }
    }
  }
}


```

**2. 索引结构**

| 字段名称      | 类型  |   备注  |
| ----------- | ----------- | ----------- |
| _id      |  keyword      |   唯一id  |
| count    | long        |  数量 |
| entity_id  | keyword        | 根据 metric_table 值不同，代表不同的含义，在这里，是指 endpont Id 值 |
| metric_table  | keyword        | 指标名称 |
| service_id  | keyword        |  service Id |
| summation  | long        |  总和 |
| value  | long        |  平均值 |
| time_bucket   | long        |   时间桶, 这里是S, 如 202207021443  |

**说明：**
- metrics-longavg 索引了值为 `long` 类型的指标；
- metric_table 字段存储了指标的名称；
- entity_id 字段，根据 metric_table 值不同，代表不同的含义，在这里，是指 endpont Id 值；
- service_id 字段存储了 service 的 id;
- endpoint_avg 指标记录了 endpoint 每秒请求的数量、平均值及总和。

**3. 数据**
通过以下命令查看数据。

```json
POST /my-elasticsearch_metrics-longavg-20220702/_search
{
  "query": {
    "bool": {
      "must": [{
        "term": {
          "metric_table": {
            "value": "endpoint_avg",
            "boost": 1.0
          }
        }
      }]
    }
  }
}
```

结果如下：
```json
{
  "took" : 0,
  "timed_out" : false,
  "_shards" : {
    "total" : 1,
    "successful" : 1,
    "skipped" : 0,
    "failed" : 0
  },
  "hits" : {
    "total" : {
      "value" : 4,
      "relation" : "eq"
    },
    "max_score" : 9.878767,
    "hits" : [
      {
        "_index" : "my-elasticsearch_metrics-longavg-20220702",
        "_type" : "_doc",
        "_id" : "endpoint_avg_202207021443_TmFjb3NQcm92aWRlckFwcA==.1_e0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn0=",
        "_score" : 9.878767,
        "_source" : {
          "metric_table" : "endpoint_avg",
          "service_id" : "TmFjb3NQcm92aWRlckFwcA==.1",
          "count" : 1,
          "time_bucket" : 202207021443,
          "entity_id" : "TmFjb3NQcm92aWRlckFwcA==.1_e0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn0=",
          "value" : 468,
          "summation" : 468
        }
      },
      {
        "_index" : "my-elasticsearch_metrics-longavg-20220702",
        "_type" : "_doc",
        "_id" : "endpoint_avg_202207021443_TmFjb3NDb25zdW1lckFwcA==.1_e0dFVH0vZWNoby97c3RyfQ==",
        "_score" : 9.878767,
        "_source" : {
          "metric_table" : "endpoint_avg",
          "service_id" : "TmFjb3NDb25zdW1lckFwcA==.1",
          "count" : 1,
          "time_bucket" : 202207021443,
          "entity_id" : "TmFjb3NDb25zdW1lckFwcA==.1_e0dFVH0vZWNoby97c3RyfQ==",
          "value" : 514,
          "summation" : 514
        }
      },
      {
        "_index" : "my-elasticsearch_metrics-longavg-20220702",
        "_type" : "_doc",
        "_id" : "endpoint_avg_202207021444_TmFjb3NQcm92aWRlckFwcA==.1_e0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn0=",
        "_score" : 9.878767,
        "_source" : {
          "metric_table" : "endpoint_avg",
          "service_id" : "TmFjb3NQcm92aWRlckFwcA==.1",
          "count" : 8,
          "time_bucket" : 202207021444,
          "entity_id" : "TmFjb3NQcm92aWRlckFwcA==.1_e0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn0=",
          "value" : 518,
          "summation" : 4145
        }
      },
      {
        "_index" : "my-elasticsearch_metrics-longavg-20220702",
        "_type" : "_doc",
        "_id" : "endpoint_avg_202207021444_TmFjb3NDb25zdW1lckFwcA==.1_e0dFVH0vZWNoby97c3RyfQ==",
        "_score" : 9.878767,
        "_source" : {
          "metric_table" : "endpoint_avg",
          "service_id" : "TmFjb3NDb25zdW1lckFwcA==.1",
          "count" : 8,
          "time_bucket" : 202207021444,
          "entity_id" : "TmFjb3NDb25zdW1lckFwcA==.1_e0dFVH0vZWNoby97c3RyfQ==",
          "value" : 521,
          "summation" : 4171
        }
      }
    ]
  }
}

```

| _id      |   metric_table  | service_id | entity_id | count | summation | value | time_bucket  |
| ----------- | ----------- | ----------- | ----------- |  ----------- |  ----------- | ----------- | ----------- | 
| endpoint...  |   endpoint_avg  |   TmFjb3NQcm92aWRlckFwcA==.1 |  TmFjb3NQcm92aWRlckFwcA==.1_e0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn0= | 1 | 468 | 468 | 202207021443 | 
| endpoint...  |   endpoint_avg  |   TmFjb3NDb25zdW1lckFwcA==.1 |  TmFjb3NDb25zdW1lckFwcA==.1_e0dFVH0vZWNoby97c3RyfQ== | 1 | 4145 | 514 | 202207021443 | 
| endpoint...  |   endpoint_avg  |   TmFjb3NQcm92aWRlckFwcA==.1 |  TmFjb3NQcm92aWRlckFwcA==.1_e0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn0= | 8 | 4145 | 518 | 202207021444 | 
| endpoint...  |   endpoint_avg  |   TmFjb3NDb25zdW1lckFwcA==.1 |  TmFjb3NDb25zdW1lckFwcA==.1_e0dFVH0vZWNoby97c3RyfQ== | 8 | 4171 | 521 | 202207021444 | 

第一行表示在 `202207021443` S, `NacosProviderApp` 服务的 `{GET}/services/hello/{str}` endpint 请求了一次，平均值为 `468` ms;
第一行表示在 `202207021443` S, `NacosConsumerApp` 服务的 `{GET}/echo/{str}` endpint 请求了一次，平均值为 `514` ms;

### service_resp_time: 服务平均响应时间
**1. Mapping**

Mapping 见上文；

**2. 索引结构**

索引结构见上文。

**说明：**
- entity_id 字段在这里代表了 service id.

**3. 数据**
通过以下命令查看数据。
```json
POST /my-elasticsearch_metrics-longavg-20220702/_search
{
  "query": {
    "bool": {
      "must": [{
        "term": {
          "metric_table": {
            "value": "service_resp_time",
            "boost": 1.0
          }
        }
      }]
    }
  }
}
```

结果如下：
```json
{
  "took" : 0,
  "timed_out" : false,
  "_shards" : {
    "total" : 1,
    "successful" : 1,
    "skipped" : 0,
    "failed" : 0
  },
  "hits" : {
    "total" : {
      "value" : 4,
      "relation" : "eq"
    },
    "max_score" : 9.861144,
    "hits" : [
      {
        "_index" : "my-elasticsearch_metrics-longavg-20220702",
        "_type" : "_doc",
        "_id" : "service_resp_time_202207021443_TmFjb3NDb25zdW1lckFwcA==.1",
        "_score" : 9.861144,
        "_source" : {
          "metric_table" : "service_resp_time",
          "count" : 1,
          "time_bucket" : 202207021443,
          "entity_id" : "TmFjb3NDb25zdW1lckFwcA==.1",
          "value" : 514,
          "summation" : 514
        }
      },
      {
        "_index" : "my-elasticsearch_metrics-longavg-20220702",
        "_type" : "_doc",
        "_id" : "service_resp_time_202207021443_TmFjb3NQcm92aWRlckFwcA==.1",
        "_score" : 9.861144,
        "_source" : {
          "metric_table" : "service_resp_time",
          "count" : 1,
          "time_bucket" : 202207021443,
          "entity_id" : "TmFjb3NQcm92aWRlckFwcA==.1",
          "value" : 468,
          "summation" : 468
        }
      },
      {
        "_index" : "my-elasticsearch_metrics-longavg-20220702",
        "_type" : "_doc",
        "_id" : "service_resp_time_202207021444_TmFjb3NDb25zdW1lckFwcA==.1",
        "_score" : 9.861144,
        "_source" : {
          "metric_table" : "service_resp_time",
          "count" : 8,
          "time_bucket" : 202207021444,
          "entity_id" : "TmFjb3NDb25zdW1lckFwcA==.1",
          "value" : 521,
          "summation" : 4171
        }
      },
      {
        "_index" : "my-elasticsearch_metrics-longavg-20220702",
        "_type" : "_doc",
        "_id" : "service_resp_time_202207021444_TmFjb3NQcm92aWRlckFwcA==.1",
        "_score" : 9.861144,
        "_source" : {
          "metric_table" : "service_resp_time",
          "count" : 8,
          "time_bucket" : 202207021444,
          "entity_id" : "TmFjb3NQcm92aWRlckFwcA==.1",
          "value" : 518,
          "summation" : 4145
        }
      }
    ]
  }
}


```
| _id      |   metric_table  | service_id | entity_id | count | summation | value | time_bucket  |
| ----------- | ----------- | ----------- | ----------- |  ----------- |  ----------- | ----------- | ----------- | 
| service...  |   service_resp_time  |    |  TmFjb3NQcm92aWRlckFwcA==.1 | 1 | 468 | 468 | 202207021443 | 
| service...  |   service_resp_time  |    |  TmFjb3NDb25zdW1lckFwcA==.1 | 1 | 514 | 514 | 202207021443 | 
| service...  |   service_resp_time  |    |  TmFjb3NQcm92aWRlckFwcA==.1 | 8 | 4145 | 518 | 202207021444 | 
| service...  |   service_resp_time  |    |  TmFjb3NDb25zdW1lckFwcA==.1| 8 | 4171 | 521 | 202207021444 | 

第一行表示在 `202207021443` S, NacosProviderApp 服务被请求了一次，平均值为 `468` ms;
第一行表示在 `202207021443` S, NacosConsumerApp 服务被请求了一次，平均值为 `514` ms;

可见 `service_resp_time` 指标是指服务所有 endpoint 每秒请求的平均值、总数和总和。由于服务只有一个 endpoint, 所以，它与 `endpoint_avg` 指标值相同。

### endpoint_percentile: endpoint 每个时间段的响应时间占比
**1. Mapping**
通过命令 `GET my-elasticsearch_metrics-percentile-20220702/_mapping` 查看索引结构。

```json
{
  "my-elasticsearch_metrics-percentile-20220702" : {
    "mappings" : {
      "properties" : {
        "dataset" : {
          "type" : "text",
          "index" : false
        },
        "entity_id" : {
          "type" : "keyword"
        },
        "metric_table" : {
          "type" : "keyword"
        },
        "precision" : {
          "type" : "integer",
          "index" : false
        },
        "service_id" : {
          "type" : "keyword"
        },
        "time_bucket" : {
          "type" : "long"
        },
        "value" : {
          "type" : "text",
          "index" : false
        }
      }
    }
  }
}


```

**2. 索引结构**

| 字段名称      | 类型  |   备注  |
| ----------- | ----------- | ----------- |
| _id      |  keyword      |   唯一id  |
| dataset    | text        |  数据集 |
| entity_id  | keyword        | 根据 metric_table 值不同，代表不同的含义 |
| metric_table  | keyword        | 指标名称 |
| service_id  | keyword        |  service Id |
| precision  | integer        |   |
| value  | text        | 指标值 |
| time_bucket   | long        |   时间桶, 这里是S, 如 202207021443  |


**3. 数据**
通过以下命令查看数据。

```json
POST /my-elasticsearch_metrics-percentile-20220702/_search
{
  "query": {
    "bool": {
      "must": [{
        "term": {
          "metric_table": {
            "value": "endpoint_percentile",
            "boost": 1.0
          }
        }
      }]
    }
  }
}
```

结果如下：
```json
{
  "took" : 0,
  "timed_out" : false,
  "_shards" : {
    "total" : 1,
    "successful" : 1,
    "skipped" : 0,
    "failed" : 0
  },
  "hits" : {
    "total" : {
      "value" : 4,
      "relation" : "eq"
    },
    "max_score" : 1.8170772,
    "hits" : [
      {
        "_index" : "my-elasticsearch_metrics-percentile-20220702",
        "_type" : "_doc",
        "_id" : "endpoint_percentile_202207021443_TmFjb3NQcm92aWRlckFwcA==.1_e0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn0=",
        "_score" : 1.8170772,
        "_source" : {
          "metric_table" : "endpoint_percentile",
          "service_id" : "TmFjb3NQcm92aWRlckFwcA==.1",
          "precision" : 10,
          "time_bucket" : 202207021443,
          "entity_id" : "TmFjb3NQcm92aWRlckFwcA==.1_e0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn0=",
          "value" : "0,460|1,460|2,460|3,460|4,460",
          "dataset" : "46,1"
        }
      },
      {
        "_index" : "my-elasticsearch_metrics-percentile-20220702",
        "_type" : "_doc",
        "_id" : "endpoint_percentile_202207021443_TmFjb3NDb25zdW1lckFwcA==.1_e0dFVH0vZWNoby97c3RyfQ==",
        "_score" : 1.8170772,
        "_source" : {
          "metric_table" : "endpoint_percentile",
          "service_id" : "TmFjb3NDb25zdW1lckFwcA==.1",
          "precision" : 10,
          "time_bucket" : 202207021443,
          "entity_id" : "TmFjb3NDb25zdW1lckFwcA==.1_e0dFVH0vZWNoby97c3RyfQ==",
          "value" : "0,510|1,510|2,510|3,510|4,510",
          "dataset" : "51,1"
        }
      },
      {
        "_index" : "my-elasticsearch_metrics-percentile-20220702",
        "_type" : "_doc",
        "_id" : "endpoint_percentile_202207021444_TmFjb3NQcm92aWRlckFwcA==.1_e0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn0=",
        "_score" : 1.8170772,
        "_source" : {
          "metric_table" : "endpoint_percentile",
          "service_id" : "TmFjb3NQcm92aWRlckFwcA==.1",
          "precision" : 10,
          "time_bucket" : 202207021444,
          "entity_id" : "TmFjb3NQcm92aWRlckFwcA==.1_e0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn0=",
          "value" : "0,530|1,750|2,780|3,940|4,940",
          "dataset" : "67,1|78,1|35,1|2,1|7,1|94,1|75,1|53,1"
        }
      },
      {
        "_index" : "my-elasticsearch_metrics-percentile-20220702",
        "_type" : "_doc",
        "_id" : "endpoint_percentile_202207021444_TmFjb3NDb25zdW1lckFwcA==.1_e0dFVH0vZWNoby97c3RyfQ==",
        "_score" : 1.8170772,
        "_source" : {
          "metric_table" : "endpoint_percentile",
          "service_id" : "TmFjb3NDb25zdW1lckFwcA==.1",
          "precision" : 10,
          "time_bucket" : 202207021444,
          "entity_id" : "TmFjb3NDb25zdW1lckFwcA==.1_e0dFVH0vZWNoby97c3RyfQ==",
          "value" : "0,540|1,760|2,780|3,940|4,940",
          "dataset" : "67,1|78,1|35,1|3,1|7,1|94,1|76,1|54,1"
        }
      }
    ]
  }
}


```

| _id      |   metric_table  | service_id | entity_id | precision | dataset | value | time_bucket  |
| ----------- | ----------- | ----------- | ----------- |  ----------- |  ----------- | ----------- | ----------- | 
| endpoint...  |   endpoint_percentile  |   TmFjb3NQcm92aWRlckFwcA==.1 |  TmFjb3NQcm92aWRlckFwcA==.1_e0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn0= | 10 | ... | ... | 202207021443 | 
| endpoint...  |   endpoint_percentile  |   TmFjb3NDb25zdW1lckFwcA==.1 |  TmFjb3NDb25zdW1lckFwcA==.1_e0dFVH0vZWNoby97c3RyfQ== | 10 | ... | ... | 202207021443 | 
| endpoint...  |   endpoint_percentile  |   TmFjb3NQcm92aWRlckFwcA==.1 |  TmFjb3NQcm92aWRlckFwcA==.1_e0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn0= | 10 | ... | ... | 202207021444 | 
| endpoint...  |   endpoint_percentile  |   TmFjb3NDb25zdW1lckFwcA==.1 |  TmFjb3NDb25zdW1lckFwcA==.1_e0dFVH0vZWNoby97c3RyfQ== | 10 | ... | ... | 202207021444 | 

第一行表示在 `202207021443` S, `NacosProviderApp` 服务的 `{GET}/services/hello/{str}` endpint 的 endpoint_percentile 值为 `0,460|1,460|2,460|3,460|4,460`;
第一行表示在 `202207021443` S, `NacosConsumerApp` 服务的 `{GET}/echo/{str}` endpint 的 endpoint_percentile 值为 `0,510|1,510|2,510|3,510|4,510`.

**说明：**
- 字段 `dataset` 和 `value` 存储的值不理解，后续再深入理解。

## Trace 

Trace 日志存储在 `{namespace}_segment-yyyyMMdd` 索引中。

### Mapping
通过命令 `GET my-elasticsearch_segment-20220702/_mapping` 查看索引结构。

```json
{
  "my-elasticsearch_segment-20220702" : {
    "mappings" : {
      "properties" : {
        "data_binary" : {
          "type" : "binary"
        },
        "end_time" : {
          "type" : "long"
        },
        "endpoint_id" : {
          "type" : "keyword"
        },
        "endpoint_name" : {
          "type" : "keyword",
          "copy_to" : [
            "endpoint_name_match"
          ]
        },
        "endpoint_name_match" : {
          "type" : "text",
          "analyzer" : "oap_analyzer"
        },
        "is_error" : {
          "type" : "integer"
        },
        "latency" : {
          "type" : "integer"
        },
        "segment_id" : {
          "type" : "keyword"
        },
        "service_id" : {
          "type" : "keyword"
        },
        "service_instance_id" : {
          "type" : "keyword"
        },
        "start_time" : {
          "type" : "long"
        },
        "statement" : {
          "type" : "keyword"
        },
        "tags" : {
          "type" : "keyword"
        },
        "time_bucket" : {
          "type" : "long"
        },
        "trace_id" : {
          "type" : "keyword"
        },
        "version" : {
          "type" : "integer",
          "index" : false
        }
      }
    }
  }
}


```

### 索引结构

| 字段名称      | 类型  |   备注  |
| ----------- | ----------- | ----------- |
| _id      |  keyword      |   唯一id  |
| trace_id    | keyword        |  trace id |
| segment_id  | keyword        | segment id |
| service_id  | keyword        | service id |
| service_instance_id  | keyword     | service instance id  |
| endpoint_id  | keyword        | endpoint id |
| endpoint_name  | keyword        | endpoint name |
| endpoint_name_match  | text        |  对 endpoint name 分词索引 |
| tags  | keyword        |  标签，可根据标签进行 Keyword 匹配查询 |
| statement  | keyword        |  statement |
| is_error  | integer        |  是否错误 |
| latency  | integer        |  延时 |
| version  | integer        |  version |
| tags  | keyword        |  标签，可根据标签进行 Keyword 匹配查询 |
| start_time  | long        | 开始时间 |
| end_time  | long        | 结束时间 |
| data_binary  | data_binary        | 完整数据，通过Base64编码存储 |
| time_bucket   | long        |   时间桶  |


**说明：**
- tags 字段：使用数组存储，可以动态添加多个 tag, 但只能使用内置 tag, 不能自定义 tag; 
- data_binary 字段：segment 内容通过 Base64 编码存储，不能索引。

### 数据
通过以下命令 `GET my-elasticsearch_segment-20220702/_search` 查看数据。

```json
{
  "took" : 1,
  "timed_out" : false,
  "_shards" : {
    "total" : 5,
    "successful" : 5,
    "skipped" : 0,
    "failed" : 0
  },
  "hits" : {
    "total" : {
      "value" : 18,
      "relation" : "eq"
    },
    "max_score" : 1.0,
    "hits" : [
      {
        "_index" : "my-elasticsearch_segment-20220702",
        "_type" : "_doc",
        "_id" : "5227fe6d8fbc4af3871f4b5d6c0a78ba.88.16567442415110000",
        "_score" : 1.0,
        "_source" : {
          "trace_id" : "5227fe6d8fbc4af3871f4b5d6c0a78ba.88.16567442415110001",
          "endpoint_name" : "{GET}/echo/{str}",
          "latency" : 673,
          "end_time" : 1656744242184,
          "endpoint_id" : "TmFjb3NDb25zdW1lckFwcA==.1_e0dFVH0vZWNoby97c3RyfQ==",
          "service_instance_id" : "TmFjb3NDb25zdW1lckFwcA==.1_ZWI4MjlmMzQ5ZjE4NGQ3NmI2OGQwZWI2MGNjYmFiYzFAMTkyLjE2OC42OC42Mg==",
          "version" : 3,
          "tags" : [
            "http.method=GET",
            "http.method=GET"
          ],
          "start_time" : 1656744241511,
          "data_binary" : "CjU1MjI3ZmU2ZDhmYmM0YWYzODcxZjRiNWQ2YzBhNzhiYS44OC4xNjU2NzQ0MjQxNTExMDAwMRI1NTIyN2ZlNmQ4ZmJjNGFmMzg3MWY0YjVkNmMwYTc4YmEuODguMTY1Njc0NDI0MTUxMTAwMDAalQEIARjo0pvtmzAgiNib7ZswMhovc2VydmljZXMvaGVsbG8vc2t5d2Fsa2luZzoTc2VydmljZS1wcm92aWRlcjo4MEABSANQDWI4CgN1cmwSMWh0dHA6Ly9zZXJ2aWNlLXByb3ZpZGVyL3NlcnZpY2VzL2hlbGxvL3NreXdhbGtpbmdiEgoLaHR0cC5tZXRob2QSA0dFVBpxEP///////////wEY59Kb7ZswIIjYm+2bMDIQe0dFVH0vZWNoby97c3RyfUgDUA5iLAoDdXJsEiVodHRwOi8vbG9jYWxob3N0OjkwOTIvZWNoby9za3l3YWxraW5nYhIKC2h0dHAubWV0aG9kEgNHRVQiEE5hY29zQ29uc3VtZXJBcHAqLmViODI5ZjM0OWYxODRkNzZiNjhkMGViNjBjY2JhYmMxQDE5Mi4xNjguNjguNjI=",
          "service_id" : "TmFjb3NDb25zdW1lckFwcA==.1",
          "statement" : "{GET}/echo/{str} - 5227fe6d8fbc4af3871f4b5d6c0a78ba.88.16567442415110001",
          "time_bucket" : 20220702144401,
          "is_error" : 0,
          "segment_id" : "5227fe6d8fbc4af3871f4b5d6c0a78ba.88.16567442415110000"
        }
      },
      {
        "_index" : "my-elasticsearch_segment-20220702",
        "_type" : "_doc",
        "_id" : "4dcbfc1f16324d7fabf5bf2d2d12bb8a.85.16567442453060000",
        "_score" : 1.0,
        "_source" : {
          "trace_id" : "5227fe6d8fbc4af3871f4b5d6c0a78ba.89.16567442453030001",
          "endpoint_name" : "{GET}/services/hello/{str}",
          "latency" : 756,
          "end_time" : 1656744246062,
          "endpoint_id" : "TmFjb3NQcm92aWRlckFwcA==.1_e0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn0=",
          "service_instance_id" : "TmFjb3NQcm92aWRlckFwcA==.1_ZGMzMDZkYTI1NWVkNDJjMWIxYjU2NmNlZTI3NDYwZWRAMTkyLjE2OC42OC42Mg==",
          "version" : 3,
          "tags" : [
            "http.method=GET"
          ],
          "start_time" : 1656744245306,
          "data_binary" : "CjU1MjI3ZmU2ZDhmYmM0YWYzODcxZjRiNWQ2YzBhNzhiYS44OS4xNjU2NzQ0MjQ1MzAzMDAwMRI1NGRjYmZjMWYxNjMyNGQ3ZmFiZjViZjJkMmQxMmJiOGEuODUuMTY1Njc0NDI0NTMwNjAwMDAa5QIQ////////////ARi68JvtmzAgrvab7ZswKtkBEjU1MjI3ZmU2ZDhmYmM0YWYzODcxZjRiNWQ2YzBhNzhiYS44OS4xNjU2NzQ0MjQ1MzAzMDAwMRo1NTIyN2ZlNmQ4ZmJjNGFmMzg3MWY0YjVkNmMwYTc4YmEuODkuMTY1Njc0NDI0NTMwMzAwMDAgASoQTmFjb3NDb25zdW1lckFwcDIuZWI4MjlmMzQ5ZjE4NGQ3NmI2OGQwZWI2MGNjYmFiYzFAMTkyLjE2OC42OC42MjoQe0dFVH0vZWNoby97c3RyfUITc2VydmljZS1wcm92aWRlcjo4MDIae0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn1IA1AOYjoKA3VybBIzaHR0cDovLzE5Mi4xNjguNjguNjI6ODA3MC9zZXJ2aWNlcy9oZWxsby9za3l3YWxraW5nYhIKC2h0dHAubWV0aG9kEgNHRVQiEE5hY29zUHJvdmlkZXJBcHAqLmRjMzA2ZGEyNTVlZDQyYzFiMWI1NjZjZWUyNzQ2MGVkQDE5Mi4xNjguNjguNjI=",
          "service_id" : "TmFjb3NQcm92aWRlckFwcA==.1",
          "statement" : "{GET}/services/hello/{str} - 5227fe6d8fbc4af3871f4b5d6c0a78ba.89.16567442453030001",
          "time_bucket" : 20220702144405,
          "is_error" : 0,
          "segment_id" : "4dcbfc1f16324d7fabf5bf2d2d12bb8a.85.16567442453060000"
        }
      }
      
      // ...
    ]
  }
}

```

为了简化，只复制了部分数据。一条完成的 Segment 数据如下：

```json
{
  "trace_id" : "5227fe6d8fbc4af3871f4b5d6c0a78ba.89.16567442453030001",
  "endpoint_name" : "{GET}/services/hello/{str}",
  "latency" : 756,
  "end_time" : 1656744246062,
  "endpoint_id" : "TmFjb3NQcm92aWRlckFwcA==.1_e0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn0=",
  "service_instance_id" : "TmFjb3NQcm92aWRlckFwcA==.1_ZGMzMDZkYTI1NWVkNDJjMWIxYjU2NmNlZTI3NDYwZWRAMTkyLjE2OC42OC42Mg==",
  "version" : 3,
  "tags" : [
    "http.method=GET"
  ],
  "start_time" : 1656744245306,
  "data_binary" : "CjU1MjI3ZmU2ZDhmYmM0YWYzODcxZjRiNWQ2YzBhNzhiYS44OS4xNjU2NzQ0MjQ1MzAzMDAwMRI1NGRjYmZjMWYxNjMyNGQ3ZmFiZjViZjJkMmQxMmJiOGEuODUuMTY1Njc0NDI0NTMwNjAwMDAa5QIQ////////////ARi68JvtmzAgrvab7ZswKtkBEjU1MjI3ZmU2ZDhmYmM0YWYzODcxZjRiNWQ2YzBhNzhiYS44OS4xNjU2NzQ0MjQ1MzAzMDAwMRo1NTIyN2ZlNmQ4ZmJjNGFmMzg3MWY0YjVkNmMwYTc4YmEuODkuMTY1Njc0NDI0NTMwMzAwMDAgASoQTmFjb3NDb25zdW1lckFwcDIuZWI4MjlmMzQ5ZjE4NGQ3NmI2OGQwZWI2MGNjYmFiYzFAMTkyLjE2OC42OC42MjoQe0dFVH0vZWNoby97c3RyfUITc2VydmljZS1wcm92aWRlcjo4MDIae0dFVH0vc2VydmljZXMvaGVsbG8ve3N0cn1IA1AOYjoKA3VybBIzaHR0cDovLzE5Mi4xNjguNjguNjI6ODA3MC9zZXJ2aWNlcy9oZWxsby9za3l3YWxraW5nYhIKC2h0dHAubWV0aG9kEgNHRVQiEE5hY29zUHJvdmlkZXJBcHAqLmRjMzA2ZGEyNTVlZDQyYzFiMWI1NjZjZWUyNzQ2MGVkQDE5Mi4xNjguNjguNjI=",
  "service_id" : "TmFjb3NQcm92aWRlckFwcA==.1",
  "statement" : "{GET}/services/hello/{str} - 5227fe6d8fbc4af3871f4b5d6c0a78ba.89.16567442453030001",
  "time_bucket" : 20220702144405,
  "is_error" : 0,
  "segment_id" : "4dcbfc1f16324d7fabf5bf2d2d12bb8a.85.16567442453060000"
}
```

## Log 

Log 日志存储在 `{namespace}_log-yyyyMMdd` 索引中。

### Mapping
通过命令 `GET my-elasticsearch_log-20220702/_mapping` 查看索引结构。

```json
{
  "my-elasticsearch_log-20220702" : {
    "mappings" : {
      "properties" : {
        "content" : {
          "type" : "keyword",
          "copy_to" : [
            "content_match"
          ]
        },
        "content_match" : {
          "type" : "text",
          "analyzer" : "oap_log_analyzer"
        },
        "content_type" : {
          "type" : "integer",
          "index" : false
        },
        "endpoint_id" : {
          "type" : "keyword"
        },
        "endpoint_name" : {
          "type" : "keyword",
          "copy_to" : [
            "endpoint_name_match"
          ]
        },
        "endpoint_name_match" : {
          "type" : "text",
          "analyzer" : "oap_analyzer"
        },
        "service_id" : {
          "type" : "keyword"
        },
        "service_instance_id" : {
          "type" : "keyword"
        },
        "span_id" : {
          "type" : "integer"
        },
        "tags" : {
          "type" : "keyword"
        },
        "tags_raw_data" : {
          "type" : "binary"
        },
        "time_bucket" : {
          "type" : "long"
        },
        "timestamp" : {
          "type" : "long"
        },
        "trace_id" : {
          "type" : "keyword"
        },
        "trace_segment_id" : {
          "type" : "keyword"
        },
        "unique_id" : {
          "type" : "keyword"
        }
      }
    }
  }
}


```

### 索引结构

| 字段名称      | 类型  |   备注  |
| ----------- | ----------- | ----------- |
| _id      |  keyword      |   唯一id  |
| trace_id    | keyword        |  trace id |
| trace_segment_id  | keyword        | trace segment id |
| unique_id  | keyword        | unique id |
| span_id  | integer        | span id |
| service_id  | keyword        | service id |
| service_instance_id  | keyword     | service instance id  |
| endpoint_id  | keyword        | endpoint id |
| endpoint_name  | keyword        | endpoint name |
| endpoint_name_match  | text        |  对 endpoint name 分词索引 |
| tags  | keyword        |  标签，可根据标签进行 Keyword 匹配查询 |
| tags_raw_data  | binary        |  标签原始内容，使用 Base64 编码存储 |
| statement  | keyword        |  statement |
| is_error  | integer        |  是否错误 |
| latency  | integer        |  延时 |
| version  | integer        |  version |
| tags  | keyword        |  标签，可根据标签进行 Keyword 匹配查询 |
| timestamp  | long        | 时间戳 |
| content  | keyword        | 日志内容 |
| content_match  | text        | 日志内容 |
| content_type  | integer        | content type |
| content  | keyword        | 对日志内容分词索引 |
| time_bucket   | long        |   时间桶  |


**说明：**
- tags 字段：使用数组存储，可以动态添加多个 tag, 但只能使用内置 tag, 不能自定义 tag, 该字段只存储被索引的字段; 
- tags_raw_data 字段：tags 原始内容通过 Base64 编码存储，不能索引；

### 数据
通过以下命令 `GET my-elasticsearch_segment-20220702/_search` 查看数据。

```json
{
  "took" : 1,
  "timed_out" : false,
  "_shards" : {
    "total" : 5,
    "successful" : 5,
    "skipped" : 0,
    "failed" : 0
  },
  "hits" : {
    "total" : {
      "value" : 18,
      "relation" : "eq"
    },
    "max_score" : 1.0,
    "hits" : [
      {
        "_index" : "my-elasticsearch_log-20220702",
        "_type" : "_doc",
        "_id" : "fd0b1e10acaf4e089cec6b402a348cb2",
        "_score" : 1.0,
        "_source" : {
          "trace_id" : "5227fe6d8fbc4af3871f4b5d6c0a78ba.87.16567442400710001",
          "unique_id" : "fd0b1e10acaf4e089cec6b402a348cb2",
          "span_id" : 0,
          "endpoint_name" : null,
          "endpoint_id" : null,
          "service_instance_id" : "TmFjb3NQcm92aWRlckFwcA==.1_ZGMzMDZkYTI1NWVkNDJjMWIxYjU2NmNlZTI3NDYwZWRAMTkyLjE2OC42OC42Mg==",
          "content" : """2022-07-02 14:44:00.075 [TID:5227fe6d8fbc4af3871f4b5d6c0a78ba.87.16567442400710001] [http-nio-8070-exec-6] INFO  o.n.n.NacosProviderApplication$EchoController -Receive a request:skywalking
""",
          "tags" : [
            "level=INFO"
          ],
          "trace_segment_id" : "4dcbfc1f16324d7fabf5bf2d2d12bb8a.83.16567442400740000",
          "content_type" : 1,
          "tags_raw_data" : "Cg0KBWxldmVsEgRJTkZPCkQKBmxvZ2dlchI6b3JnLm5vYWhzYXJrLm5hY29zLk5hY29zUHJvdmlkZXJBcHBsaWNhdGlvbiRFY2hvQ29udHJvbGxlcgoeCgZ0aHJlYWQSFGh0dHAtbmlvLTgwNzAtZXhlYy02",
          "service_id" : "TmFjb3NQcm92aWRlckFwcA==.1",
          "time_bucket" : 20220702144400,
          "timestamp" : 1656744240075
        }
      },
      {
        "_index" : "my-elasticsearch_log-20220702",
        "_type" : "_doc",
        "_id" : "826963aef56b4bbab4f607c46b43faeb",
        "_score" : 1.0,
        "_source" : {
          "trace_id" : "5227fe6d8fbc4af3871f4b5d6c0a78ba.80.16567442485970003",
          "unique_id" : "826963aef56b4bbab4f607c46b43faeb",
          "span_id" : 0,
          "endpoint_name" : null,
          "endpoint_id" : null,
          "service_instance_id" : "TmFjb3NDb25zdW1lckFwcA==.1_ZWI4MjlmMzQ5ZjE4NGQ3NmI2OGQwZWI2MGNjYmFiYzFAMTkyLjE2OC42OC42Mg==",
          "content" : """2022-07-02 14:44:08.598 [TID:5227fe6d8fbc4af3871f4b5d6c0a78ba.80.16567442485970003] [http-nio-9092-exec-1] INFO  o.n.n.NacosConsumerApplication$TestController -Receive a request:skywalking
""",
          "tags" : [
            "level=INFO"
          ],
          "trace_segment_id" : "5227fe6d8fbc4af3871f4b5d6c0a78ba.80.16567442485970002",
          "content_type" : 1,
          "tags_raw_data" : "Cg0KBWxldmVsEgRJTkZPCkQKBmxvZ2dlchI6b3JnLm5vYWhzYXJrLm5hY29zLk5hY29zQ29uc3VtZXJBcHBsaWNhdGlvbiRUZXN0Q29udHJvbGxlcgoeCgZ0aHJlYWQSFGh0dHAtbmlvLTkwOTItZXhlYy0x",
          "service_id" : "TmFjb3NDb25zdW1lckFwcA==.1",
          "time_bucket" : 20220702144408,
          "timestamp" : 1656744248598
        }
      }
      // ...
    ]
  }
}


```

为了简化，只复制了部分数据。一条完成的 log 数据如下：

```json
{
  "trace_id" : "5227fe6d8fbc4af3871f4b5d6c0a78ba.80.16567442485970003",
  "unique_id" : "826963aef56b4bbab4f607c46b43faeb",
  "span_id" : 0,
  "endpoint_name" : null,
  "endpoint_id" : null,
  "service_instance_id" : "TmFjb3NDb25zdW1lckFwcA==.1_ZWI4MjlmMzQ5ZjE4NGQ3NmI2OGQwZWI2MGNjYmFiYzFAMTkyLjE2OC42OC42Mg==",
  "content" : """2022-07-02 14:44:08.598 [TID:5227fe6d8fbc4af3871f4b5d6c0a78ba.80.16567442485970003] [http-nio-9092-exec-1] INFO  o.n.n.NacosConsumerApplication$TestController -Receive a request:skywalking""",
  "tags" : [
    "level=INFO"
  ],
  "trace_segment_id" : "5227fe6d8fbc4af3871f4b5d6c0a78ba.80.16567442485970002",
  "content_type" : 1,
  "tags_raw_data" : "Cg0KBWxldmVsEgRJTkZPCkQKBmxvZ2dlchI6b3JnLm5vYWhzYXJrLm5hY29zLk5hY29zQ29uc3VtZXJBcHBsaWNhdGlvbiRUZXN0Q29udHJvbGxlcgoeCgZ0aHJlYWQSFGh0dHAtbmlvLTkwOTItZXhlYy0x",
  "service_id" : "TmFjb3NDb25zdW1lckFwcA==.1",
  "time_bucket" : 20220702144408,
  "timestamp" : 1656744248598
}

```


## Event

Event 日志存储在 `{namespace}_events-yyyyMMdd` 索引中。

### Mapping
通过命令 `GET my-elasticsearch_events-20220701/_mapping` 查看索引结构。

```json
{
  "my-elasticsearch_events-20220701" : {
    "mappings" : {
      "properties" : {
        "end_time" : {
          "type" : "long"
        },
        "endpoint" : {
          "type" : "keyword"
        },
        "message" : {
          "type" : "keyword"
        },
        "name" : {
          "type" : "keyword"
        },
        "parameters" : {
          "type" : "keyword",
          "index" : false
        },
        "service" : {
          "type" : "keyword"
        },
        "service_instance" : {
          "type" : "keyword"
        },
        "start_time" : {
          "type" : "long"
        },
        "time_bucket" : {
          "type" : "long"
        },
        "type" : {
          "type" : "keyword"
        },
        "uuid" : {
          "type" : "keyword"
        }
      }
    }
  }
}

```

### 索引结构

| 字段名称      | 类型  |   备注  |
| ----------- | ----------- | ----------- |
| _id      |  keyword      |   唯一id  |
| uuid  | keyword        | uuid |
| service  | keyword        | service |
| service_instance  | keyword     | service instance |
| endpoint  | keyword        | endpoint |
| name  | keyword        | name |
| type  | keyword        |  type |
| start_time  | long        | 开始时间 |
| end_time  | long        | 结束时间 |
| message  | keyword        | 事件内容 |
| parameters  | keyword        | 启动参数 |
| time_bucket   | long        |   时间桶  |


**说明：**
- service 字段：服务名称; 
- service_instance 字段：服务实例名称；

### 数据
通过以下命令 `GET my-elasticsearch_events-20220701/_search` 查看数据。

```json
{
  "took" : 0,
  "timed_out" : false,
  "_shards" : {
    "total" : 1,
    "successful" : 1,
    "skipped" : 0,
    "failed" : 0
  },
  "hits" : {
    "total" : {
      "value" : 4,
      "relation" : "eq"
    },
    "max_score" : 1.0,
    "hits" : [
      {
        "_index" : "my-elasticsearch_events-20220701",
        "_type" : "_doc",
        "_id" : "09e90a94-9154-48a5-a32c-6c2e18ca695d",
        "_score" : 1.0,
        "_source" : {
          "start_time" : 1656671199452,
          "endpoint" : "",
          "service" : "NacosConsumerApp",
          "name" : "Start",
          "end_time" : 1656671200887,
          "time_bucket" : 202207011826,
          "service_instance" : "",
          "type" : "Normal",
          "message" : "Start Java Application",
          "uuid" : "09e90a94-9154-48a5-a32c-6c2e18ca695d",
          "parameters" : """{"OPTS":"-Dcom.sun.management.jmxremote -Dcom.sun.management.jmxremote.authenticate\u003dfalse -Dcom.sun.management.jmxremote.port\u003d62148 -Dcom.sun.management.jmxremote.ssl\u003dfalse -Dfile.encoding\u003dUTF-8 -Djava.rmi.server.hostname\u003dlocalhost -Dspring.application.admin.enabled\u003dtrue -Dspring.liveBeansView.mbeanDomain -Dspring.output.ansi.enabled\u003dalways -XX:TieredStopAtLevel\u003d1 -Xverify:none -javaagent:C:/Java/skywalking-es7-8.6.0/agent/skywalking-agent.jar -javaagent:C:\\Java\\IDEA-2018.3.2\\lib\\idea_rt.jar\u003d62149:C:\\Java\\IDEA-2018.3.2\\bin"}"""
        }
      },
      {
        "_index" : "my-elasticsearch_events-20220701",
        "_type" : "_doc",
        "_id" : "3c64b57a-8f1c-4cd0-9622-fb9a665936b6",
        "_score" : 1.0,
        "_source" : {
          "start_time" : 1656671244223,
          "endpoint" : "",
          "service" : "NacosConsumerApp",
          "name" : "Start",
          "end_time" : 1656671245361,
          "time_bucket" : 202207011827,
          "service_instance" : "",
          "type" : "Normal",
          "message" : "Start Java Application",
          "uuid" : "3c64b57a-8f1c-4cd0-9622-fb9a665936b6",
          "parameters" : """{"OPTS":"-Dcom.sun.management.jmxremote -Dcom.sun.management.jmxremote.authenticate\u003dfalse -Dcom.sun.management.jmxremote.port\u003d62207 -Dcom.sun.management.jmxremote.ssl\u003dfalse -Dfile.encoding\u003dUTF-8 -Djava.rmi.server.hostname\u003dlocalhost -Dspring.application.admin.enabled\u003dtrue -Dspring.liveBeansView.mbeanDomain -Dspring.output.ansi.enabled\u003dalways -XX:TieredStopAtLevel\u003d1 -Xverify:none -javaagent:C:/Java/skywalking-es7-8.6.0/agent/skywalking-agent.jar -javaagent:C:\\Java\\IDEA-2018.3.2\\lib\\idea_rt.jar\u003d62208:C:\\Java\\IDEA-2018.3.2\\bin"}"""
        }
      }

      // ...
    ]
  }
}

```

为了简化，只复制了部分数据。一条完成的 event 数据如下：

```json
{
  "start_time" : 1656671244223,
  "endpoint" : "",
  "service" : "NacosConsumerApp",
  "name" : "Start",
  "end_time" : 1656671245361,
  "time_bucket" : 202207011827,
  "service_instance" : "",
  "type" : "Normal",
  "message" : "Start Java Application",
  "uuid" : "3c64b57a-8f1c-4cd0-9622-fb9a665936b6",
  "parameters" : """{"OPTS":"-Dcom.sun.management.jmxremote -Dcom.sun.management.jmxremote.authenticate\u003dfalse -Dcom.sun.management.jmxremote.port\u003d62207 -Dcom.sun.management.jmxremote.ssl\u003dfalse -Dfile.encoding\u003dUTF-8 -Djava.rmi.server.hostname\u003dlocalhost -Dspring.application.admin.enabled\u003dtrue -Dspring.liveBeansView.mbeanDomain -Dspring.output.ansi.enabled\u003dalways -XX:TieredStopAtLevel\u003d1 -Xverify:none -javaagent:C:/Java/skywalking-es7-8.6.0/agent/skywalking-agent.jar -javaagent:C:\\Java\\IDEA-2018.3.2\\lib\\idea_rt.jar\u003d62208:C:\\Java\\IDEA-2018.3.2\\bin"}"""
}

```

**参考：**

----
[1]:https://skywalking.apache.org/zh/2019-03-29-introduction-of-skywalking-and-simple-practice/
[2]:https://www.jianshu.com/p/c164be9f6f72

[1. SkyWalking调研与初步实践][1]
[2. skywalking UI指标说明][2]

