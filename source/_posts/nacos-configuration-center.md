---
title: Springboot 序列：Nacos 配置中心
date: 2022-03-05 18:32:53
updated: 2022-03-05 18:32:53
tags:
- Nacos
- 配置中心
categories:
- Springboot
---

集中式的配置中心是微服务系统中一个比较重要组件， Nacos 在系统中可以承担两个角色：1）配置中心；2）服务注册中心。在这篇文章里，我们讲述如何在 SpringCloud 中集成 Nacos 作为配置中心来使用。

<!-- more -->

## 配置中心

配置中心主要是统一存储配置项，配置项一般是 key-value 的形式，而这些配置项存储到指定格式的文件中。在程序中通过文件的特定标识来确定配置中心的一个文件，这些文件从配置中心下载到本地之后，动态加载到程序中，供程序使用。

Nacos 有特定的数据模型来定义一个配置文件，其模型如下：
![nacos-data-model](/images/spring-cloud/nacos-data-model.jpeg "nacos-data-model")

在 Nacos 中有几个重要的概念：
1. Namespace: 用于进行租户粒度的配置隔离。不同的命名空间下，可以存在相同的 Group 或 Data ID 的配置。Namespace 的常用场景之一是不同环境的配置的区分隔离，例如开发测试环境和生产环境的资源（如配置、服务）隔离等；
2. Group: 一组相关或者不相关的配置项的集合称为配置集。在系统中，一个配置文件通常就是一个配置集，包含了系统各个方面的配置。例如，一个配置集可能包含了数据源、线程池、日志级别等配置项；
3. DataId: Nacos 中的某个配置集的 ID。配置集 ID 是组织划分配置的维度之一。Data ID 通常用于组织划分系统的配置集。一个系统或者应用可以包含多个配置集，每个配置集都可以被一个有意义的名称标识。Data ID 通常采用类 Java 包（如 com.taobao.tc.refund.log.level）的命名规则保证全局唯一性。此命名规则非强制；
4. 配置项：一个具体的可配置的参数与其值域，通常以 param-key=param-value 的形式存在。例如我们常配置系统的日志输出级别（logLevel=INFO|WARN|ERROR） 就是一个配置项；
5. Service: 通过预定义接口网络访问的提供给客户端的软件功能，主要用在注册中心中。

在 Nacos 中，Namespace + Group + DataId 可以惟一定位一个配置文件。

## 引入 Nacos

### 引入 Spring Cloud Alibaba

在这里我们使用 Spring Cloud Alibaba 来引入 Nacos, 它会依赖 Springboot 和 SpringCloud 的版本。三者的版本关系如下：

```xml
<properties>
    <maven.compiler.source>1.8</maven.compiler.source>
    <maven.compiler.target>1.8</maven.compiler.target>

    <spring-boot.version>2.2.5.RELEASE</spring-boot.version>
    <spring-cloud.version>Hoxton.SR3</spring-cloud.version>
    <spring-cloud-alibaba.version>2.2.1.RELEASE</spring-cloud-alibaba.version>
</properties>

<dependencyManagement>

    <dependencies>

        <!-- spring boot -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-dependencies</artifactId>
            <version>${spring-boot.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>

        <!-- spring cloud -->
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-dependencies</artifactId>
            <version>${spring-cloud.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>

        <!-- Spring Cloud Alibaba -->
        <dependency>
            <groupId>com.alibaba.cloud</groupId>
            <artifactId>spring-cloud-alibaba-dependencies</artifactId>
            <version>${spring-cloud-alibaba.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>

    </dependencies>

</dependencyManagement>
```

三者之间的版本依赖关系，可以在官网查看：[版本说明 Wiki](https://github.com/alibaba/spring-cloud-alibaba/wiki/%E7%89%88%E6%9C%AC%E8%AF%B4%E6%98%8E)

### 引入 Nacos 依赖

通过引入下面的依赖引入 Nacos. 

```xml
<dependency>
    <groupId>com.alibaba.cloud</groupId>
    <artifactId>spring-cloud-starter-alibaba-nacos-config</artifactId>
</dependency>
```

### 配置 Nacos 服务器

在 bootstrap.yml 中配置 application name 及 Nacos server. 默认情况下，application name 是 dataId 的一部分。

```yaml
spring:
  application:
    name: example
  cloud:
    nacos:
      config:
        server-addr: localhost:8848
        username: nacos
        password: nacos
        file-extension: properties
```

在 Nacos Spring Cloud 中，dataId 的完整格式如下：
- prefix 默认为 spring.application.name 的值，也可以通过配置项 spring.cloud.nacos.config.prefix 来配置; 
- spring.profiles.active 即为当前环境对应的 profile，详情可以参考 Spring Boot文档。 注意：当 spring.profiles.active 为空时，对应的连接符 - 也将不存在，dataId 的拼接格式变成 ${prefix}.${file-extension}; 
- file-exetension 为配置内容的数据格式，可以通过配置项 spring.cloud.nacos.config.file-extension 来配置。目前只支持 properties 和 yaml 类型。

通过这种方式配置，Namespace, GroupId 使用的是默认值，经过上述配置之后，Nacos 中相关值如下：
- Namespace: 默认为 public; 
- GroupId: 默认为 DEFAULT_GROUP; 
- DataId: example.properties

最终对应 Nacos 中的 example.properties 文件。

### 自定义配置文件

通过上面的配置方式，只能指定一个文件，如果要指定多个文件，可以自定义 Namespace, GroupId, DataId. 

**自定义 namespace 配置**

在没有明确指定 ${spring.cloud.nacos.config.namespace} 配置的情况下， 默认使用的是 Nacos 上 Public 这个 namespae。如果需要使用自定义的命名空间，可以通过以下配置来实现：

```properties
spring.cloud.nacos.config.namespace=b3404bc0-d7dc-4855-b519-570ed34b62d7
```

该配置必须放在 bootstrap.properties 文件中。此外 spring.cloud.nacos.config.namespace 的值是 namespace 对应的 id，id 值可以在 Nacos 的控制台获取。并且在添加配置时注意不要选择其他的 namespae，否则将会导致读取不到正确的配置。

**自定义 Group 配置**

在没有明确指定 ${spring.cloud.nacos.config.group} 配置的情况下， 默认使用的是 DEFAULT_GROUP 。如果需要自定义自己的 Group，可以通过以下配置来实现：

```properties
spring.cloud.nacos.config.group=DEVELOP_GROUP
```

该配置必须放在 bootstrap.properties 文件中。并且在添加配置时 Group 的值一定要和 spring.cloud.nacos.config.group 的配置值一致

**自定义 DataId 配置**
Spring Cloud Alibaba Nacos Config 从 0.2.1 版本后，可支持自定义 Data Id 的配置。一个完整的配置案例如下所示：

```properties
spring.application.name=opensource-service-provider
spring.cloud.nacos.config.server-addr=127.0.0.1:8848

# config external configuration
# 1、Data Id 在默认的组 DEFAULT_GROUP,不支持配置的动态刷新
spring.cloud.nacos.config.extension-configs[0].data-id=ext-config-common01.properties

# 2、Data Id 不在默认的组，不支持动态刷新
spring.cloud.nacos.config.extension-configs[1].data-id=ext-config-common02.properties
spring.cloud.nacos.config.extension-configs[1].group=GLOBALE_GROUP

# 3、Data Id 既不在默认的组，也支持动态刷新
spring.cloud.nacos.config.extension-configs[2].data-id=ext-config-common03.properties
spring.cloud.nacos.config.extension-configs[2].group=REFRESH_GROUP
spring.cloud.nacos.config.extension-configs[2].refresh=true
```

可以看到:

- 通过 spring.cloud.nacos.config.extension-configs[n].data-id 的配置方式来支持多个 Data Id 的配置；
- 通过 spring.cloud.nacos.config.extension-configs[n].group 的配置方式自定义 Data Id 所在的组，不明确配置的话，默认是 DEFAULT_GROUP;
- 通过 spring.cloud.nacos.config.extension-configs[n].refresh 的配置方式来控制该 Data Id 在配置变更时，是否支持应用中可动态刷新， 感知到最新的配置值。默认是不支持的。

**注意：**
- 多个 Data Id 同时配置时，他的优先级关系是 spring.cloud.nacos.config.extension-configs[n].data-id 其中 n 的值越大，优先级越高；
- spring.cloud.nacos.config.extension-configs[n].data-id 的值必须带文件扩展名，文件扩展名既可支持 properties，又可以支持 yaml/yml。 此时 spring.cloud.nacos.config.file-extension 的配置对自定义扩展配置的 Data Id 文件扩展名没有影响。

通过自定义扩展的 Data Id 配置，既可以解决多个应用间配置共享的问题，又可以支持一个应用有多个配置文件。多个应用共享的配置参见：[Spring Cloud Alibaba Nacos Config](https://github.com/alibaba/spring-cloud-alibaba/wiki/Nacos-config)

### 动态更新配置项

通过 Spring Cloud 原生注解 @RefreshScope 实现配置自动更新。

```java
@RestController
@RequestMapping("/configs")
@RefreshScope
public class ConfigController {

    @Value("${useLocalCache:false}")
    private boolean useLocalCache;

    /**
     * http://localhost:8080/configs/cache
     */
    @RequestMapping(value = "/cache",method = RequestMethod.GET)
    public boolean get() {
        return useLocalCache;
    }
}

@SpringBootApplication
public class NacosConfigApplication {

    public static void main(String[] args) {
        SpringApplication.run(NacosConfigApplication.class, args);
    }
}
```

## 启动程序并验证

运行 NacosConfigApplication，在浏览器中调用 http://localhost:8080/configs/cache, 可以在 Nacos 管理后台修改配置项，验证是否生效。

**[代码库：https://github.com/noahsarkzhang-ts/springboot-lab](https://github.com/noahsarkzhang-ts/springboot-lab)**

</br>

**参考：**

----
[1]:https://nacos.io/zh-cn/docs/quick-start-spring-cloud.html
[2]:https://github.com/alibaba/spring-cloud-alibaba/wiki/Nacos-config


[1. Nacos Spring Cloud 快速开始][1]

[2. Spring Cloud Alibaba Nacos Config][2]
