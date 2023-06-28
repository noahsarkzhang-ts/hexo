---
title: Elasticsearch 常用操作
date: 2022-02-05 16:05:22
updated: 2022-02-05 16:05:22
tags:
- es
- Elasticsearch
categories:
- Elasticsearch
---

记录 Elasticsearch 常用的操作，如索引、查询、分词及调试等等相关的操作。

<!-- more -->
## 运维相关
### 查看集群健康状态
```json
GET _cat/health?v

epoch      timestamp cluster          status node.total node.data shards pri relo init unassign pending_tasks max_task_wait_time active_shards_percent
1644228538 10:08:58  my-elasticsearch yellow          1         1     20  20    0    0        6             0                  -                 76.9%

```

**说明：v 是表示结果中返回表头**

### 查看集群结点
```json
GET _cat/nodes?v

ip         heap.percent ram.percent cpu load_1m load_5m load_15m node.role   master name
172.19.0.2           50          98   2    0.04    0.03     0.05 cdfhilmrstw *      node-1

```

### 查看所有索引
```json
GET _cat/indices?v

health status index                           uuid                   pri rep docs.count docs.deleted store.size pri.store.size
yellow open   sports                          DZ0tM97mQKeibg9-vCLZgA   1   1         22            0     10.3kb         10.3kb
yellow open   catalog                         su6kerZsTP6stMBEPpb8-A   1   1          1            0        6kb            6kb
green  open   .apm-agent-configuration        t0UuBydGRF6YdD9lSb5u5w   1   0          0            0       208b           208b

```

## 文档操作
### 创建一个文档
```json
POST twitter/_doc/1
{
  "user": "GB",
  "uid": 1,
  "city": "Shenzhen",
  "province": "Guangdong",
  "country": "China"
}
```

### 修改一个文档
```json
PUT twitter/_create/1
{
  "user": "GB",
  "uid": 1,
  "city": "Shenzhen",
  "province": "Guangdong",
  "country": "China"
}
```

### 部分更新一个文档（更新部分字段）
```json
POST twitter/_update/1
{
  "doc": {
    "city": "成都",
    "province": "四川"
  }
}
```

### 插入或更新操作
```json
POST /catalog/_update/3
{
     "doc": {
       "author": "Albert Paro",
       "title": "Elasticsearch 5.0 Cookbook",
       "description": "Elasticsearch 5.0 Cookbook Third Edition",
       "price": "54.99"
      },
     "doc_as_upsert": true
}
```

使用 `doc_as_upsert` 合并到 ID 为 3 的文档中，或者如果不存在则插入一个新文档。


### 检查一个文档是否存在
```json
HEAD twitter/_doc/1
```

### 删除一个文档
```json
DELETE twitter/_doc/1
```

### 查询删除（删除满足查询的 doc）
```json
POST twitter/_delete_by_query
{
  "query": {
    "match": {
      "city": "上海"
    }
  }
}

```

## 索引
### 检查一个索引是否存在
```json
HEAD twitter
```

### 删除一个索引
```json
DELETE twitter
```

### 查询 settings
```json
GET twitter/_settings
```

### 修改 settings
```json
PUT twitter
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1
  }
}
```

### 查询 mapping
```json
GET twitter/_mapping
```

### 修改 mapping
```json
DELETE twitter

PUT twitter/_mapping
{
  "properties": {
    "address": {
      "type": "text",
      "fields": {
        "keyword": {
          "type": "keyword",
          "ignore_above": 256
        }
      }
    },
    "age": {
      "type": "long"
    },
    "city": {
      "type": "text",
      "fields": {
        "keyword": {
          "type": "keyword",
          "ignore_above": 256
        }
      }
    },
    "country": {
      "type": "text",
      "fields": {
        "keyword": {
          "type": "keyword",
          "ignore_above": 256
        }
      }
    },
    "location": {
      "type": "geo_point"
    },
    "message": {
      "type": "text",
      "fields": {
        "keyword": {
          "type": "keyword",
          "ignore_above": 256
        }
      }
    },
    "province": {
      "type": "text",
      "fields": {
        "keyword": {
          "type": "keyword",
          "ignore_above": 256
        }
      }
    },
    "uid": {
      "type": "long"
    },
    "user": {
      "type": "text",
      "fields": {
        "keyword": {
          "type": "keyword",
          "ignore_above": 256
        }
      }
    }
  }
}
```

### 批量添加 doc
```json
POST _bulk
{ "index" : { "_index" : "twitter", "_id": 1} }
{"user":"双榆树-张三","message":"今儿天气不错啊，出去转转去","uid":2,"age":20,"city":"北京","province":"北京","country":"中国","address":"中国北京市海淀区","location":{"lat":"39.970718","lon":"116.325747"}}
{ "index" : { "_index" : "twitter", "_id": 2 }}
{"user":"东城区-老刘","message":"出发，下一站云南！","uid":3,"age":30,"city":"北京","province":"北京","country":"中国","address":"中国北京市东城区台基厂三条3号","location":{"lat":"39.904313","lon":"116.412754"}}

```

## 查询
### 查询所有文档
```json
POST twitter/_search
```

### 查询行数
```json
GET twitter/_count
```

### 指定分页
```json
GET twitter/_search?size=2&from=2
```

### 指定分页
```json
GET twitter/_search?size=2&from=2

# 第二种方式
GET twitter/_search
{
  "size": 2,
  "from": 2, 
  "query": {
    "match_all": {}
  }
}
```

### 带条件查询数量
```json
GET twitter/_count
{
  "query": {
    "match": {
      "city": "北京"
    }
  }
}
```

### 查询字段是否可以被聚合/搜索所有的文档
```json
GET twitter/_field_caps?fields=country
```

## 分词
### 查看分词结果（使用标准分词器进行分词）
```json
GET twitter/_analyze
{
  "text": [
    "Happy Birthday"
  ],
  "analyzer": "standard"
}

# 结果
{
  "tokens" : [
    {
      "token" : "happy",
      "start_offset" : 0,
      "end_offset" : 5,
      "type" : "<ALPHANUM>",
      "position" : 0
    },
    {
      "token" : "birthday",
      "start_offset" : 6,
      "end_offset" : 14,
      "type" : "<ALPHANUM>",
      "position" : 1
    }
  ]
}

```
对 Happy Birthday 使用 standard 分词器进行分词


## 调试
### 打开Profile 调试工具
```json
GET twitter/_search
{
  "profile": "true", 
  "query": {
    "match": {
      "city": "北京"
    }
  }
}

```

添加`"profile": "true"`属性。

</br>

**参考：**

----
[1]:https://elasticstack.blog.csdn.net/article/details/99481016
[2]:https://elasticstack.blog.csdn.net/article/details/99546568

[1.开始使用 Elasticsearch （1）][1]

[2.开始使用 Elasticsearch （2）][2]

