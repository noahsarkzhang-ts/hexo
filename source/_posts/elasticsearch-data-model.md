---
title: Elasticsearch 数据建模
date: 2022-07-09 12:21:07
tags:
- 数据建模
- Text
- Keyword
- Nested
- Join
categories:
- Elasticsearch
---

这篇文章讲述在 Elasticsearch 中如何选择字段的类型，它是对极客时间《Elasticsearch 核心技术与实战》之《数据建模》章节的读书笔记。

<!-- more -->

## 数据建模

数据建模是创建数据模型的过程，数据模型是对真实世界进行抽象描述的一种工具和方法，是对现实世界的映射，它包含三个过程：概念模型===>逻辑模型===>物理模型。

- 概念模型：确定系统的核心需求和范围边界，明确实体与实体之间的关系；
- 逻辑模型：对概念模型的进一步分解和细化，描述了实体、实体属性以及实体之间的关系；
- 物理模型：选择一个数据库生产来实现逻辑模型，包括数据库产品对应的数据类型、长度、索引等因素，为逻辑模型选择一个最有的物理存储环境；

本文主要是针对 Elasticsearch 进行物理建模。

## Elasticsearch 建模

Elasticsearch 物理建模包括四个环节：
1. 选择合适的字段类型；
2. 判断是否需要检索及分词；
3. 判断是否需要聚合及排序；
4. 判断是否需要额外存储。

## 字段类型 

### Text & Keyword

**Text**
用于全文本字段，文本会被 Analyzer 分词，默认不支持聚合分析及排序，如需支持，需要将 fielddata 属性设置为 true;

**Keyword**
主要用于 id, 枚举等不需要分词的文本，例如电话号码，email地址，邮政编码，性别等，适用于 Filter(精确分配)， 排序和聚合；

### 设置多字段类型

Elasticsearch 默认会将文本设置为 Text, 并且设置一个 Keyword 的子字段；在处理需要搜索的文本时，可以通过增加`英文`，`标准`及`拼音` 分词器，提供多种搜索方式；

### 结构化数据

- 数值类型：尽量选择贴近的类型，例如可以用 byte, 就不要用 long;
- 枚举类型：设置为 keyword, 即便是数字，也应该设置成 keyword, 以便获得更佳的性能；
- 其它：设置合适的日期/布尔/地理信息类型。

## 搜索及分词

- 如不需要检索，可以将 index 设置为 false; 
- 对需要检索的字段，可以通过 Index options /Norms 属性，设定存储粒度，不需要归一化数据，可以关闭 Norms 属性；
- 如不需要检索，排序和聚合分析，可以将 enable 设置为 false.


## 聚合及排序

如不需排序或者聚合分析功能，可以将 Doc values/ fielddata 设置为 false; 更新频繁，聚合查询频繁的 keyword 类型的字段，推荐 eager global ordinals 设置为 true; 

## 额外存储

store 设置为 true, 可以存储该字段的原始内容；一般结合 _source 的 enable 为 false 时候使用。Disable _source, 可以节约磁盘，适用于指标型数据的存储。一般建议不 Disable _source， 优先考虑增加压缩比来提高存储效率；Disable _source 字段之后，无法做 Reindex 和 Update 操作。

## 属性定义

可以用下图总结上述属性的定义：
![es-attribute](/images/es/es-attribute.jpg "es-attribute")

## 处理关联关系

在处理 `join` 关系时，可以参照如下的步骤选择合适的类型：

![es-join](/images/es/es-join.jpg "es-join")

### Object 类型

Elasticsearch 将 Object 对象存成扁平式的键值对，以下面的数据为例：

```json
POST my_movies/_doc/1
{
  "title":"Speed",
  "actors":[
    {
      "first_name":"Keanu",
      "last_name":"Reeves"
    },

    {
      "first_name":"Dennis",
      "last_name":"Hopper"
    }

  ]
}
```

movies 对象会存成如下的结构：
```json
title: "Speed"
actors.first_name: ["Keanu","Dennis"]
actors.last_name: ["Reeves","Reeves"]
```

在这种存储结构如下，`first_name`, `last_name` 分属在不同的数组中，使用这两个字段进行联合查询时，不能精确匹配。

### Nested 类型

`Object` 类型查询的问题，可以使用 `Nested` 类型解决，在 Nested 类型中, `first_name`, `last_name` 代表的对象可以独立索引，在 Elasticsearch 内部，Nested 文档会被保存在不同的 Lucene 文档中，在查询时做 Join 处理；不过，每次更新时，需要重新索引整个对象，包括根对象和嵌套对象。

### Child/Parent 类型

Child/Parent 类型主要解决级联更新的问题，父文档和子文档是两个独立的文档，更新父文档无需重新索引子文档，对子文档进行添加，更新及删除不会父文档和其它的子文档。

**Nested VS Child/Parent(Join)**

| Item | Nested | Child/Parent(Join) |
| ----------- | ----------- | ----------- |
| 优点      | 文档存储在一起，读取性能高       | 父子文档可以独立更新       |
| 缺点   | 更新 Nested 的子文档时，需要更新整个文档        | 需要额外的内存维护关系，读取性能相对较差       |
| 适用场景   | 子文档偶尔更新，以查询为主        | 子文档频繁更新       |

**说明：**
尽可能非范式化数据（冗余数据），从而获得最佳的性能：
1. 使用 Nested 类型的数据，查询速度会慢几倍；
2. 使用 Child/Parent 类型的数据，查询速度会慢几百倍；

**参考：**

----
[1]:https://mp.weixin.qq.com/s/LXhE-D0FlT_hOns1s1rBmg

[1. 干货 | 论Elasticsearch数据建模的重要性][1]
