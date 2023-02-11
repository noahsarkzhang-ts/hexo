---
title: Mqtt 系列：服务加载(SPI)
date: 2023-02-11 11:43:55
tags:
- 服务加载
- SPI
categories:
- MQTT
---
这篇文章讲述在 `MQTT Broker` 项目中组件(或类)的加载方式。

<!-- more -->

## 概述

在项目中，集群有两种模式：1）单机模式；2）集群模式，单机模式方便测试。缓存/数据库也有多种类型可供选择，缓存有 Memory(内存版本)、Redis、Memcached 等，数据库有 Memory（内存版本）、Mysql等，其整体的关系如下所示：

![mqtt-service-loader](/images/mqtt/mqtt-service-loader.jpg "mqtt-service-loader")

集群模式需要借助 `MqttEventBus`及 `MqttEventBusManager` 两个接口实现，每一个接口都有两个实现的版本：`Singleton`, `Cluster`, 分别对应单机模式和集群模式。`CacheBeanFactory` 及 `DbBeanFactory` 对应缓存组件和数据库组件的接口，目前都有两种实现。服务加载模块便是根据配置文件的定义，来加载不同的实现类。

## SPI

为了实现上述功能，决定使用 `SPI` 的技术。`SPI` 全称为 `Service Provider Interface`，是一种服务发现机制。`SPI` 的本质是将接口实现类的全限定名配置在文件中，并由服务加载器读取配置文件，加载实现类。这样可以在运行时，动态为接口替换实现类。

查询相关资料，目前 `SPI` 大概有三种服务加载的模式：
1. JDK SPI：通过在 `META-INF/services` 目录下添加与接口同名的文件，并将实现类写入到文件中，最后通过 `ServiceLoader` 类加载。通过这种方式，可以加载一组服务的实现类；
2. Dubbo SPI: 扩展了 JDK SPI，在其基础上，可以按照别名实现服务的加载；
3. Spring SPI: 与 JDK SPI 功能类似，配置文件为 `META-INF/spring.factories`.

为了尽量避免依赖第三方的组件，在项目中，作用了 `JDK SPI` 的方式。

## SPI 实现方式

**1. 定义接口**
以 `MqttEventBus` 为例，它负责集群内部消息的发送和接收。

```java
public interface MqttEventBus extends Lifecycle {

    /**
     * 向集群广播消息
     * @param msg 消息
     */
    void broadcast(ClusterMessage msg);

    /**
     * 接收集群消息
     * @param msg 消息
     */
    void receive(ClusterMessage msg);

    /**
     * 以阻塞方式获取消息
     * @param timeout 超时时间
     * @param unit 时间单位
     * @return 消息
     * @throws InterruptedException 异常
     */
    ClusterMessage poll(long timeout, TimeUnit unit) throws InterruptedException;

    /**
     * 向本节点客户端推送消息
     * @param message 消息
     */
    void publish2Subscribers(PublishInnerMessage message);
}
```

**2. 编写 MqttEventBus 实现类**
可以根据需要，编写不同的实现类，如 `SingletonEventBus` 和 `ClustersEventBus`.

**3. 添加服务接口文件**
向 `META-INF/services` 目录添加与 `MqttEventBus` 同名的接口配置文件，如 `org.noahsark.mqtt.broker.clusters.MqttEventBus`, 其内容为两个实现类。
```txt
org.noahsark.mqtt.broker.clusters.SingletonEventBus
org.noahsark.mqtt.broker.clusters.ClustersEventBus
```

**4. 服务加载**
通过 `ServiceLoader` 类加载服务，代码如下所示：
```java
// 调用方法
loadService(MqttEventBus.class);

// 加载的方法
private void loadService(Class<? extends Initializer> classz) {

    ServiceLoader<? extends Initializer> sl = ServiceLoader.load(classz);
    Iterator<? extends Initializer> iterator = sl.iterator();

    while (iterator.hasNext()) {
        Initializer service = iterator.next();
        String alias = service.alias();

        // 只加载指定的对象
        if (!alias.equals(aliasMap.get(classz))) {
            continue;
        }

        service.load(conf);
        service.init();

        Map<String, Object> beanMap = beans.get(classz);
        if (beanMap == null) {
            beanMap = new HashMap<>();

            beans.put(classz, beanMap);
        }

        beanMap.put(alias, service);
    }
}
```

**说明：**
服务加载有一个限制，接口实现类必须包含**无参的构造函数**。

## 别名加载

在实现中，不用加载所有的实现类，只需要加载指定的实现类即可，如在配置文件中指定加载的类型。
```properties
# Cluster config,value=cluster|singleton
cluster.model=singleton
server.id=1
server.1=192.168.100.100:2883
server.2=192.168.100.101:2883

# Cache config,value=redis|memory(for test)
# cache.type=memory

cache.type=redis
cache.redis.host=192.168.100.110
cache.redis.port=6379

# DB config,value=mysql|memory(for test)
# db.type=memory

db.type=mysql
db.mysql.driver=com.mysql.cj.jdbc.Driver
db.mysql.url=jdbc:mysql://192.168.100.110:3306/alligator_mqtt?serverTimezone=Asia/Shanghai&useUnicode=true&characterEncoding=utf8&useSSL=false
db.mysql.username=root
db.mysql.password=123456
```

如果 `cluster.model` 指定了 `singleton` 之后，只需要加载 `SingletonEventBus` 实现类即可。

另外，每一个组件有不同的配置参数，每一个实现类需要读取属于自己的参数，最后也有可能需要实现类的初始化操作，如缓存或数据库的连接创建。为了满足以上需求。每个组件必须实现如下接口：
```java
public interface Initializer  {

    /**
     * 初始化组件
     */
    void init();

    /**
     * 加载配置信息
     * @param configuration 配置文件
     */
    void load(Configuration configuration);

    /**
     * 组件别名
     * @return 别名
     */
    String alias();
}
```

**说明：**
1. load: 加载配置文件；
2. alias: 设置别名,`alias` 方法返回的字段与配置文件中的类型保持一致，则可以在 `loadService` 方法中按照别名进行过滤加载；
3. init: 初始化操作，如缓存或数据库的连接创建。

## 总结

通过上述方法，便可以实现组件的按需加载，但也引入了一个循环依赖的问题，即不能在组件的构造方法中引用另外一个组件，因为另外一个组件可能还未完成初始化，由此引发空指针异常，因此要避免在组件的构造方法中引用另外一个组件。




