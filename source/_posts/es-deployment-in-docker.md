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
# 设置在集群为单结点模式
discovery.type: single-node
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

## 设置安全账号
使用基本和试用许可证时，默认情况下会禁用 Elasticsearch 安全功能。开启安全功能之后，在单结点模式下可以不用开启 SSL. 在集群模式同时需要开启结点间的 SSL, 否则不能启动。最终配置的结果是通过 url 及 kibana 访问集群需要输入用户名及密码。

### 开启 Elastic 安全功能

操作之前先停止 Kibana 及 Elasticsearch 服务。

**1. 开启 xpack.security.enabled**
在  ES_PATH_CONF/elasticsearch.yml 文件中加入如下配置：

```yml
xpack.security.enabled: true
```

**2. 启用 single-node 发现模式**
在 ES_PATH_CONF/elasticsearch.yml 文件中加入如下配置：

```yml
discovery.type: single-node
```

**3. 重启 Kibana 及 ElElasticsearch**
完成以上两项配置之后重启 Kibana 及 Elasticsearch.

### 为内置用户编辑创建密码
使用 /bin/elasticsearch-setup-passwords 设置内置用户的密码，这些用户用于特定的管理目的：apm_system，beats_system，elastic，kibana，logstash_system 和 remote_monitoring_user.

```bash
# 进入容器
$ docker exec -it es01-test bash

# 进入到 Elasticsearch 目录
$ cd /usr/share/elasticsearch

# 
$ ./bin/elasticsearch-setup-passwords interactive
Initiating the setup of passwords for reserved users elastic,apm_system,kibana,logstash_system,beats_system,remote_monitoring_user.
You will be prompted to enter passwords as the process progresses.
Please confirm that you would like to continue [y/N]

```
按照提示可以为每一个内置用户生成一个密码。完成之后使用 `http://ip:9200/` 访问集群，需要输入 elastic 用户的密码。

### 为 Kibana 添加内置用户
启用 Elasticsearch 安全功能后，用户必须使用有效的用户 ID 和密码登录 Kibana。
Kibana 还执行一些需要使用内置 kibana 用户的任务。
如果对安全没有强烈要求的话，可以 kibana.yml 文件中配置 kibana 用户名及密码。

```yml
elasticsearch.username: "kibana"
elasticsearch.password: "your_password"
```

另外也可以通过 创建 Kibana 密钥库来保存密码，或在启动参数中加入用户名/密码。

**参考：**

----
[1]:https://blog.csdn.net/UbuntuTouch/article/details/100548174

[1. Elasticsearch：设置 Elastic 账户安全][1]

