---
title: Springboot 序列：Nacos 服务发现 
date: 2022-03-06 11:11:50
tags:
- Nacos
- 注册中心
- 服务发现
categories:
- Springboot
---

服务发现是微服务架构体系中最关键的组件之一。Nacos 除了可以作为配置中心，也可以用于服务发现，服务端将接口注册到 Nacos 中，消费端动态获取服务列表，使用特定的负载算法选择其中一个服务来完成服务的调用。在这篇文章里，使用官方的代码实例来学习 Nacos 服务发现功能。

<!-- more -->

## 实例介绍 

![nacos-discovery-example](/images/spring-cloud/nacos-discovery-example.png "nacos-discovery-example")

实例包含两个程序，一个是服务提供者用于实现特定的功能，是服务的提供者，一个是服务的消费者，是服务的调用方。

## 版本依赖

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

## 引入 Nacos Discovery Starter

使用 Nacos Discovery Starter 引入 Nacos 的服务发现功能。

```xml
<dependency>
    <groupId>com.alibaba.cloud</groupId>
    <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
</dependency>
```

## 配置服务提供者

配置服务提供者，可以将其服务注册到 Nacos server 上。

### 配置 application.yml(propertities)

设置服务器的端口、Nacos 的地址、用户名及密码信息。

```yaml
server:
  port: 8070

spring:
  application:
    name: service-provider
  cloud:
    nacos:
      discovery:
        server-addr: 127.0.0.1:8848
        username: nacos
        password: nacos
```

### 开启服务发现

通过 Spring Cloud 原生注解 @EnableDiscoveryClient 开启服务注册发现功能

```java
@SpringBootApplication
@EnableDiscoveryClient
public class NacosProviderApplication {

    public static void main(String[] args) {
        SpringApplication.run(NacosProviderApplication.class, args);
    }

    @RestController
    @RequestMapping("/services")
    class EchoController {
        @RequestMapping(value = "/echo/{string}", method = RequestMethod.GET)
        public String echo(@PathVariable String string) {
            return "Hello Nacos Discovery " + string;
        }
    }
}
```

## 配置服务消费者

配置服务消费者，服务消费者可以通过 Nacos 的服务注册发现功能从 Nacos server 上获取到它要调用的服务。

### 配置 application.yml(propertities)

配置服务器的端口、Nacos 的地址、用户名及密码信息。

```yaml
server:
  port: 8080

spring:
  application:
    name: service-consumer
  cloud:
    nacos:
      discovery:
        server-addr: 127.0.0.1:8848
        username: nacos
        password: nacos
```

### 开启服务发现

通过 Spring Cloud 原生注解 @EnableDiscoveryClient 开启服务注册发现功能。给 RestTemplate 实例添加 @LoadBalanced 注解，开启 @LoadBalanced 与 Ribbon 的集成：

```java
@SpringBootApplication
@EnableDiscoveryClient
public class NacosConsumerApplication {

    @LoadBalanced
    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }

    public static void main(String[] args) {
        SpringApplication.run(NacosConsumerApplication.class, args);
    }

    @RestController
    public class TestController {

        private final RestTemplate restTemplate;

        @Autowired
        public TestController(RestTemplate restTemplate) {
            this.restTemplate = restTemplate;
        }

        @RequestMapping(value = "/echo/{str}", method = RequestMethod.GET)
        public String echo(@PathVariable String str) {
            return restTemplate.getForObject("http://service-provider/services/echo/" + str, String.class);
        }
    }
}
```

## 启动并测试

启动 ProviderApplication 和 ConsumerApplication ，调用 http://localhost:8080/echo/2022，返回内容为 Hello Nacos Discovery 2022。

**[代码库：https://github.com/noahsarkzhang-ts/springboot-lab](https://github.com/noahsarkzhang-ts/springboot-lab)**

</br>

**参考：**

----
[1]:https://nacos.io/zh-cn/docs/quick-start-spring-cloud.html
[2]:https://github.com/alibaba/spring-cloud-alibaba/wiki/Nacos-discovery
[3]:https://github.com/alibaba/spring-cloud-alibaba/wiki/%E7%89%88%E6%9C%AC%E8%AF%B4%E6%98%8E

[1. Nacos Spring Cloud 快速开始][1]

[2. Spring Cloud Alibaba Nacos Discovery][2]

[2. Spring Cloud Alibaba 版本说明][2]

