---
title: Docker 下安装 ES, Kibana
date: 2022-01-29 15:44:46
tags:
- es
- kibana
categories:
- 部署
---

记录在 Docker 中安装 Elasticsearch 7.14.2 及 Kibana 7.14.2, 构建一个单机的实验环境。

<!-- more -->

## 环境配置

**1. vm.max_map_count**

vm.max_map_count 最小设置为 262144, 
```bash
vi /etc/sysctl.conf
vm.max_map_count=262144
```
或临时生效：`sysctl -w vm.max_map_count=262144`

## 创建网络
```bash
docker network create elastic
```

## 安装 Elasticsearch 7.14.2

```bash

docker pull docker.elastic.co/elasticsearch/elasticsearch:7.14.2

docker run --name es01-test \
--net elastic -p 9200:9200 -p 9300:9300 \
-v /data/es7.14.2/config/elasticsearch.yml:/usr/share/elasticsearch/config/elasticsearch.yml \
-v /data/es7.14.2/data:/usr/share/elasticsearch/data \
-v /data/es7.14.2/logs:/usr/share/elasticsearch/logs \
-v /data/es7.14.2/plugins:/usr/share/elasticsearch/plugins \
-e "TAKE_FILE_OWNERSHIP=true" \
--privileged=true \
-d docker.elastic.co/elasticsearch/elasticsearch:7.14.2
```

**说明：**
- TAKE_FILE_OWNERSHIP=true：使用文件挂载之后，容器可能没有访问宿主机的权限，设置该环境变量，可以解决该问题；
- elasticsearch.yml：将该文件挂载到宿主机，可以方便进行配置；
- 安装目录：elasticsearch 默认安装在 /usr/share/elasticsearch 目录下。

**elasticsearch.yml 内容：**
```yml
# 集群名称
cluster.name: my-elasticsearch
# 节点名称
node.name: node-1
# 数据和日志的存储目录
path.data: /usr/share/elasticsearch/data
path.logs: /usr/share/elasticsearch/logs
# 设置绑定的ip，设置为 0.0.0.0 表示监听所有网卡
network.host: 0.0.0.0
# 端口
http.port: 9200
# 设置在集群中的所有节点名称，目前是单机，放入一个节点即可
cluster.initial_master_nodes: ["node-1"]
#indices.fielddata.cache.size: 50%
```

## 安装 Kibana 7.14.2

```bash
docker pull docker.elastic.co/kibana/kibana:7.14.2

docker run --name kib01-test \
--net elastic -p 5601:5601 \
-v /data/kibana7.14.2/config/kibana.yml:/usr/share/kibana/config/kibana.yml \
-v /data/kibana7.14.2/data:/usr/share/kibana/data \
-e "ELASTICSEARCH_HOSTS=http://es01-test:9200" \
--privileged=true \
-d docker.elastic.co/kibana/kibana:7.14.2
```

**说明：**
- kibana.yml：将该文件挂载到宿主机，可以方便进行配置；
- 目录挂载：使用文件挂载之后，容器可能没有访问宿主机的权限，可以将宿主机目录授权为所有用户访问（生产环境不建议使用）；

**kibana.yml 内容：**
```yml
#
# ** THIS IS AN AUTO-GENERATED FILE **
#

# Default Kibana configuration for docker target
server.host: "0"
server.shutdownTimeout: "5s"
elasticsearch.hosts: [ "http://elasticsearch:9200" ]
monitoring.ui.container.elasticsearch.enabled: true
```

## 停止容器

```bash
docker stop es01-test
docker stop kib01-test
```

## 启动容器
```bash
docker start es01-test
docker start kib01-test
```

## 删除容器
```bash
docker network rm elastic
docker rm es01-test
docker rm kib01-test
```

## 访问地址 (URL)

```bash
# es:
http://ip:9200/

# kibana:
http://ip:5601/
```
