---
title: Alligator 系列：RabbitMQ 基础知识及部署
date: 2021-09-30 09:12:20
updated: 2021-09-30 09:12:20
tags:
- RabbitMQ
- consumer ack
- exchange
- queue
- producer confirm
categories:
- Alligator网关
---

## 1. 概览
RabbitMQ 是一种消息系统，相比较其它消息系统，除了 queue，它多了一个 exchange 交换器的概念，在 Alligator 中支持使用 RabbitMQ, 其整体结构如下图所示：
![rabbitmq-overview](/images/alligator/rabbitmq-overview.png "rabbitmq-overview")

<!-- more -->

现在假设有这样一个业务场景，一个 web app 具备生成 PDF 文档的能力，而生成 PDF 文档是一个耗时的操作，需要交给后台的 PDF 任务去执行。为了提高系统的吞吐量，引入 RabbitMQ 缓存请求，其流程为：
1. 用户发送一个生成 PDF 的请求给 web app;
2. Web app (Producer) 发送一个消息给 RabbitMQ;
3. Exchange 收到消息并路由消息到合适的 Queue; 
4. PDF 任务(Consumer) 接收来自 Queue 的消息，生成 PDF.

消息不是直接发送到 Queue 中，而是发送到 Exchange 中，最后通过 routing Key 在 Exchange 和 Queue 中建立一个 binding 关系，从而将消息路由到不同的 Queue 中。

![exchanges-bidings-routing-keys](/images/alligator/exchanges-bidings-routing-keys.png "exchanges-bidings-routing-keys")

RabbitMQ 中消息处理流程：
1. Producer 发布一个消息到 Exchange 中，在创建 Exchange 时必须指定其类型；
2. Exchange 收到消息并负责消息的路由，Exchange 会根据消息的属性进行路由，其中，routing key 是一个关键的属性，根据 Exchange 类型，可以有不同的路由策略；
3. Bindings(绑定关系) 必须创建，它决定了消息从 Exchange 路由到哪个 Queue，在这个 case 中，有两个绑定关系，路由到那个 Queue，取决于消息的属性；
4. 消息路由到 Queue 中，并等待 Consumer 处理；
5. Consumer 接收消息并处理。

Exchange 有四种类型：direct, topic, headers 和 fanout.
![exchanges-topic-fanout-direct](/images/alligator/exchanges-topic-fanout-direct.png "exchanges-topic-fanout-direct")

1. Direct: Binding Key 与 Routing Key 精确匹配。binding key 是 exchange 与 queue 建立绑定关系指定的属性，而 routing key 则是由 Producer 发送消息是指定的属性，如果两个 key 相同，消息则路由到与 binding key 相关联的 queue 中；
2. Fanout: 广播所有的消息；
3. Topic: 是比较灵活的类型，可以在 binding key 中指定通配符(\*,#)，如 eu.fe.\*, us.#, 其中，\* 表示匹配一个单词，# 表示匹配多个单词。通过通配符，可以实现层次结构的匹配；
4. Headers: Headers exchanges 使用消息的属性进行路由。

**Binding Key 与 Routing Key：**
```java
// exchange 申明, 可以指定 type
AMQP.Exchange.DeclareOk exchangeDeclare​(String exchange, String type, boolean durable) throws IOException

// 建立绑定关系，指定 bindingKey
AMQP.Queue.BindOk queueBind​(String queue, String exchange, String bindingKey, Map<String,​Object> arguments) throws IOException

// 发布消息，指定 routingKey
void basicPublish​(String exchange, String routingKey, boolean mandatory, AMQP.BasicProperties props, byte[] body) throws IOException
```

通过 routingKey 与 bindingKey 进行匹配，从而实现消息的路由。

```bash
root@my-rabbit:/# rabbitmqctl list_exchanges
Listing exchanges for vhost / ...
name    type
amq.topic       topic
amq.fanout      fanout
amq.direct      direct
amq.headers     headers
amq.match       headers
                direct(default)
amq.rabbitmq.trace      topic
```
通过 rabbitmqctl 命令可以查看 exchange 信息，在这个列表中，一些是 amq.* 打头的 exchange, 还一个没有命名，空名字的 exchange, 这个空的 exchange 是默认的 exchange. 它们都是默认创建好的。

在发布消息的时候，可以不指定 exchange 的名称, 如下代码所示：
```java
channel.basic_publish(exchange='',
                      routing_key='task_queue',
                      body=message)
```
空的 exchange 代表了默认或无名的 exchange: 消息会路由到与 routing_key 同名的 queue 中，在这个 case 中，消息最终路由到 task_queue queue 中。

## 2. 基础知识
### 2.1 Consumer ACK 机制

Consumer ACK 有两种模式：1）自动；2）手动。在自动模式下，Broker 分发消息之后即认为分发成功，便可删除消息，该模式被认为是不安全的。而自动模式需要程序手动发送 Ack 确认信息，这样可以保证消息被处理。

官方文档对自动模式描述如下：
> In automatic acknowledgement mode, a message is considered to be successfully delivered immediately after it is sent. This mode trades off higher throughput (as long as the consumers can keep up) for reduced safety of delivery and consumer processing. This mode is often referred to as "fire-and-forget". Unlike with manual acknowledgement model, if consumers's TCP connection or channel is closed before successful delivery, the message sent by the server will be lost. Therefore, automatic message acknowledgement should be considered unsafe and not suitable for all workloads.

通过下面方法来设置自动或手动：
```java
boolean autoAck = false;

channel.basicConsume(queueName, autoAck, "a-consumer-tag",
     new DefaultConsumer(channel) {
         @Override
         public void handleDelivery(String consumerTag,
                                    Envelope envelope,
                                    AMQP.BasicProperties properties,
                                    byte[] body)
             throws IOException
         {
             long deliveryTag = envelope.getDeliveryTag();
             // negatively acknowledge, the message will
             // be discarded
             channel.basicReject(deliveryTag, false);
         }
     });
```
默认是自动模式，可以在 channel.basicConsume 方法中设置为 false。

**手动 Ack 有三个方法：**
- basic.ack : 用于肯定应答；
- basic.nack ：用于否定应答，可以重新 requeue 排队发送；
- basic.reject ：用于否定应答，与 nack 的区别在于是否支持批量确认。

**basic.ack 方法定义：**
```java
long deliveryTag = envelope.getDeliveryTag();

channel.basicAck(long deliveryTag, boolean multiple);
```
其中，
- deliveryTag : 消息的唯一标示，在一个channel 中一个消息具有唯一的 deliveryTag；
- multiple ：是否批量确认，true 表示 deliveryTag 之前的消息都被确认，false 只确认当前消息。

**basic.nack 方法定义：**
```java
long deliveryTag = envelope.getDeliveryTag();

channel.basicNack(long deliveryTag, boolean requeue, boolean multiple);
```
其中，
- deliveryTag : 消息的唯一标示，在一个channel 中一个消息具有唯一的 deliveryTag；
- requeue : 是否重新排队发送，true 表示重新排队，false 表示删除该消息；
- multiple ：是否批量确认，true 表示 deliveryTag 之前的消息都被确认，false 只确认当前消息。

**basic.reject方法定义：**
```java
long deliveryTag = envelope.getDeliveryTag();

basic.reject(long deliveryTag, boolean requeue);
```
其中，
- deliveryTag : 消息的唯一标示，在一个channel 中一个消息具有唯一的 deliveryTag；
- requeue : 是否重新排队发送，true 表示重新排队，false 表示删除该消息；

### 2.2 QoS
QoS 主要是为了控制向 Consumer 发送消息的频率，通过配置当前未确认的消息数量来控制是否发送，如 Qos = 5，则表示如果有 5 条消息未被确认，则不向 Consumer 发送消息。通过配置 QoS，可以避免消息在 Consumer 中堆积。正常情况下，QoS 是配合手动 Ack 一起使用的。
在生产环境中，需要根据压测结果选择合适的值进行配置，QoS = 0 表示不限制，QoS = 1 是保守的配置，为了提高系统的吞吐量，一般可以设置较大的值。QoS 可以配置在 Channel 或 Consumer 上，Channel 的配置如下：
```java
channel.basicQos(1);
```

### 2.3 Producer Comfirm

Consumer 通过 Ack 机制保证消息被消费，同样，Producer 通过 Confirm 机制保证投递到 broker 中，可以通过下面的代码开启 Comfirm。
```java
// 开启 confirm
ch.confirmSelect();

// 同步等待
ch.waitForConfirmsOrDie(5_000);
```

可以结合业务，实现单个消息、批量消息的确认及消息的异步确认。

### 2.4 持久化
消息的持久化，包括 exchange 及 queue 的持久化，其参数配置如下：
```java
// exchange 申明
channel.exchangeDeclare​(String exchange, String type, boolean durable);

// queue 申明
channel.queueDeclare​(String queue, boolean durable, boolean exclusive, boolean autoDelete, Map<String,​Object> arguments);

// 将 queue 绑定到 exchange 上
channel.queueBind​(String queue, String exchange, String routingKey);

```

**Exchange 申明：**
```java
AMQP.Exchange.DeclareOk exchangeDeclare​(String exchange, String type, boolean durable) throws IOException
```

参数说明：
- exchange: exchange 名称
- type: exchange type
- durable: 是否持久化，若为 true，服务器重启之后，exchange 还会存在。

**Queue​ 申明：**
```java
AMQP.Queue.DeclareOk queueDeclare​(String queue, boolean durable, boolean exclusive, boolean autoDelete, Map<String,​Object> arguments) throws IOException
```

参数说明：
- queue: queue 名称
- durable: 是否持久化，若为 true，服务器重启后，queue 仍然存在
- exclusive: 是否具有排他性，若为 true, 不允许其它客户端连接
- autoDelete: 是否自动删除，若为 true, 队列没有使用时，则为自动删除
- arguments: 其它参数

**QueueBind​ 申明：**
```java
AMQP.Queue.BindOk queueBind​(String queue, String exchange, String routingKey, Map<String,​Object> arguments) throws IOException
```

参数说明：
- queue: queue 名称
- exchange: exchange 名称
- routingKey: 路由 key
- arguments: 其它参数

**basicPublish 申明：**
```java
void basicPublish​(String exchange, String routingKey, boolean mandatory, AMQP.BasicProperties props, byte[] body) throws IOException
```

参数说明：
- exchange: exchange 名称
- routingKey: 路由 key
- mandatory: 若为 tue,表示消息若不能路由，则将消息 return 给发送者，发送者可以定义重发逻辑，若为 false, 则将消息丢弃或发送给另外的 exchange
- props: 参数，可以指定消息的类型或是否持久化
- body: 消息内容

示例：
```java
channel.basicPublish(exchangeName, routingKey, true, MessageProperties.PERSISTENT_TEXT_PLAIN,
                        body.getBytes("UTF-8"));
```

<font color='red'>** 说明: **</font>
<font color='red'>在 RabbitMQ 中，exchange 及 queue 不用提前创建，调用上面的申明方法时，如果没有不存在，则会自动创建。</font>

### 2.5 Virtual Hosts
> RabbitMQ is multi-tenant system: connections, exchanges, queues, bindings, user permissions, policies and some other things belong to virtual hosts, logical groups of entities

RabbitMQ 是一个多租户系统，connections, exchanges, queues, bindings, user 权限, 策略及其它东西都属于一个 virtual host。使用 virtual host，需要用户提前创建，系统默认的 vhost 是 '/'。


## 3. 部署

<font color='red'>** 说明: **</font>
<font color='red'>只是用于实验目的，安装单机版本。</font>

### 3.1 安装 Rabbitmq
使用 docker 部署单机版本，版本使用的是 3.9。
```bash
// 安装 rabbitmq
docker run -d --hostname my-rabbit --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.9-management

// 进入容器
docker exec -it 容器id bash
```

### 3.2 创建 virtual host
```bash
// 创建 alligator vhost
rabbitmqctl add_vhost <vhost_name>

rabbitmqctl add_vhost alligator

// 查看 vhost
rabbitmqctl list_vhosts

```

### 3.3 创建用户
```bash
// 创建 user
rabbitmqctl add_user test_user 123456

// 查看 user
rabbitmqctl list_users

// rabbitmqctl 用户相关的命令
add_user <username> <password>
delete_user <username>
change_password <username> <newpassword>
clear_password <username>
authenticate_user <username> <password>
set_user_tags <username> <tag> ...
list_users
```

rabbitmq 角色有：none,management,policymaker,monitoring 及 administrator，可以通过下面的命令设置角色。

```bash
// 设置角色
rabbitmqctl set_user_tags <user> <role>

// 设置为超级管理员
rabbitmqctl set_user_tags test_user administrator
```

### 3.4 授权用户
```bash
// 授权用户
rabbitmqctl set_permissions [-p <vhost>] <user> <conf> <write> <read>

// 授权 test_user 具备 alligator vhost 下所有资源的读写权限
rabbitmqctl set_permissions -p alligator  allen '.*' '.*' '.*'

```

### 3.5 管理后台
RabbitMQ 默认创建了 guest(密码为 guest)，处于安全考虑，建议删除该用户，新建一个自定义用户，用于后台的管理。

```bash
// 删除 guest 用户
rabbitmqctl delete_user guest

// 新建 admin 用户
rabbitmqctl add_user admin ********

// 设置 admin 为 administrator 角色
rabbitmqctl set_user_tags admin administrator

// 将 / (vhost) 所有权限授权给 admin
rabbitmqctl set_permissions -p / admin '.*' '.*' '.*'

```

</br>

**参考：**

----
[1]:https://www.cloudamqp.com/blog/part1-rabbitmq-for-beginners-what-is-rabbitmq.html
[2]:https://rabbitmq.github.io/rabbitmq-java-client/api/4.x.x/com/rabbitmq/client/Channel.html
[3]:https://www.rabbitmq.com/confirms.html
[4]:https://www.rabbitmq.com/vhosts.html
[5]:https://www.rabbitmq.com/queues.html
[6]:https://www.rabbitmq.com/getstarted.html
[7]:https://www.rabbitmq.com/access-control.html
[8]:https://www.rabbitmq.com/rabbitmqctl.8.html
[9]:https://www.rabbitmq.com/production-checklist.html

[1. part 1: RabbitMQ for beginners - What is RabbitMQ?][1]

[2. rabbitmq api doc][2]

[3. Consumer Acknowledgements and Publisher Confirms][3]

[4. Virtual Hosts][4]

[5. queues][5]

[6. RabbitMQ Tutorials][6]

[7. Authentication, Authorisation, Access Control][7]

[8. rabbitmqctl(8)][8]

[9. Production Checklist][9]

