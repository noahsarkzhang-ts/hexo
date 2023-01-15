---
title: Mqtt 序列：Subscription
date: 2023-01-14 22:33:32
tags:
- subscription
categories:
- MQTT
---

在 `Moquette` 中使用类似 `Trie`(单词查找树) 的数据结构来实现 `Topic` 的匹配，本文主要介绍这种数据结构。

<!-- more -->

## Trie

`Trie` 树，又称单词查找树，是一种树形结构，是一种哈希树的变种。典型应用是用于统计，排序和保存大量的字符串（但不仅限于字符串），所以经常被搜索引擎系统用于文本词频统计。它的优点是：利用字符串的公共前缀来减少查询时间，最大限度地减少无谓的字符串比较，查询效率比哈希树高。

![mqtt-trie](/images/mqtt/mqtt-trie.jpg "mqtt-trie")

每一条边或结点可代表一个字母，兄弟结点有相同的公共前缀。在搜索时，从头结点（头结点没有数据）开始，逐个字母进行匹配，从匹配的链路中继续同样的操作，直到所有字母匹配完毕。

## CTrie

在 `Moquette` 中，参考`Trie` 树，实现了 `CTrie` 树来进行订阅关系的匹配，如下图便是由 `Topic Filter` 构成的 `CTrie` 树：

![mqtt-ctrie](/images/mqtt/mqtt-ctrie.jpg "mqtt-ctrie")

`CTrie` 树有以下特点：
1. 起始结点为 `ROOT` 结点，该结点不关联数据；
2. 每一个结点关联一个 `Token` 和一组订阅该 `Token`（确切地说应该是 `Topic Filter`） 的客户端；
3. 从 `ROOT` 结点到每一个结点都代表了一个 `Topic Filter`;
4. `Topic Filter` 中可以包括通配符，如 `#`,`+`, 其中 `#` 代表零个或多个层级，位于最后一个 `Token`, `+` 代表一个层级，可位于任意位置；
5. 每一个层级都会关联一组订阅关系，该订阅关系包括如下内容：`TF(Topic Filter)`, `QoS` 及 `U`(User, 代表一个客户端)；

**说明：**
1. `Topic`: 消息主题，每一个消息都会有一个所属的 `Topic`; 
2. `Topic Filter`: 主题过滤器，也可叫主题表达式，每一个客户端订阅感兴趣的 `Topic` 时，都需要定义一个 `Topic Filter`，用来匹配或筛选消息；
3. `Token`: `Topic` 具有层次结构，层级间使用 `/` 进行分隔，而一个 `Token` 则代表其中一个层级；
4. `Topic Filter` 中可以包含通配符，如`#`,`+`，但 `Topic`中不能包含通配符。

**实例：**
以 `sport/tennis/#` `Topic Filter` 为例，它表示匹配 `sport/tennis` 及 `sport/tennis/..`下任意层级的 `Topic`, 其中 `sport`, `tennis`, `#` 代表三个层级或三个 `Token`.

**重点说明：**
`sport/tennis` 和 `sport/tennis/` 是不一样的 `Topic`,`sport/tennis` 其中包括二个层级`sport` 和 `tennis`, 而 `sport/tennis/` 包括三个层级 `sport`, `tennis` 和 `""`, 空串也是一层级。

## 匹配规则

在 `MQTT` 中，订阅关系中的 `Topic Filter` 会生成一棵 `CTrie`, `MQTT Broker` 每当收到一个消息时，便会使用该消息的 `Topic` 去 `CTrie` 树中查找订阅该 `Topic` 的客户端。匹配的本质便是 `CTrie` 树的查找匹配过程。

### 任意层级的匹配

可以使用 `#` 进行多个层级的匹配，如下图所示：

![mqtt-multi](/images/mqtt/mqtt-multi.jpg "mqtt-multi")

**说明：**
1. `#` 可以匹配父级 `Topic`, 如 `sport/tennis`;
2. `#` 可以匹配任意多级 `Topic`, 如：`sport/tennis/player1,sport/tennis/player1/score`.

### 单个层级的匹配

可以使用 `+` 进行单个层级的匹配，如下图所示：

![mqtt-single](/images/mqtt/mqtt-single.jpg "mqtt-single")

**说明：**
1. `+` 不匹配父级 `Topic`;
2. `+` 只匹配一级 `Token`, 如：`sport/tennis/,sport/tennis/player1,sport/tennis/player2`.