---
title: Springboot 系列：Actuator + Admin
date: 2022-05-29 18:59:28
updated: 2022-05-29 18:59:28
tags:
- actuator
- admin
- 监控系统
categories:
- Springboot
---

Actuator 提供了查询服务内部状态的 Endpoints，Springboot Admin 则可以接入这些 Endponts, 实现对服务的统一监控及管理。本文讲述如何将 Springboot 项目接入到 Springboot Admin 中。

<!-- more -->

## 概述

Spring Boot Admin 是一个管理和监控 Spring Boot 应用程序的开源项目，在对单一应用服务监控的同时也提供了集群监控方案，支持通过 eureka、consul、zookeeper 等注册中心的方式实现多服务监控与管理。Spring Boot  admin UI 部分使用 Vue JS 将数据展示在前端。
Spring Boot Admin分为服务端（spring-boot-admin-server）和客户端（spring-boot-admin-client）两个组件：
- spring-boot-admin-server: 采集 actuator 端点数据显示在 spring-boot-admin-ui 上；
- spring-boot-admin-client：对 Actuator 进行封装，提供应用系统的性能监控数据。此外，还可以通过 spring-boot-admin 动态切换日志级别、导出日志、导出 heapdump、监控各项性能指标等。

## 引入 Springboot Admin Server
### 引入依赖

新建一个名称为 `monitor-admin` 的 Springboot 项目，引入如下的依赖：

```xml
<properties>
    <!-- spring boot -->
    <spring-boot.version>2.2.5.RELEASE</spring-boot.version>
</properties>

<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-configuration-processor</artifactId>
        <optional>true</optional>
    </dependency>

    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
    <!-- springboot admin server-->
    <dependency>
        <groupId>de.codecentric</groupId>
        <artifactId>spring-boot-admin-starter-server</artifactId>
        <version>2.2.3</version>
    </dependency>
    <!-- springboot security-->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-security</artifactId>
    </dependency>

</dependencies>
```

**说明：**
- spring-boot-admin-starter-server: Springboot admin server 包；
- spring-boot-starter-security: Spring secutiry, 用于安全认证；
- Springboot 与 Admin 版本需要匹配，否则会报错。

在 Springboot 启动类中引入 `EnableAdminServer` annotation, 开启 Springboot Admin Server 功能。
```java
@SpringBootApplication
@EnableAdminServer
public class MonitorAdminApplication {

    public static void main(String[] args) {
        SpringApplication.run(MonitorAdminApplication.class, args);
    }

}
```



### 引入 Security 配置类

新建一个 `WebSecurityConfigurerAdapter` 类型的配置类，访问 Admin 需要进行登陆验证。

```java
@Configuration
public class WebSecurityConfig extends WebSecurityConfigurerAdapter {
    private final AdminServerProperties adminServer;

    public WebSecurityConfig(AdminServerProperties adminServer) {
        this.adminServer = adminServer;
    }

    @Override
    protected void configure(HttpSecurity http) throws Exception {
        SavedRequestAwareAuthenticationSuccessHandler successHandler =
                new SavedRequestAwareAuthenticationSuccessHandler();
        successHandler.setTargetUrlParameter("redirectTo");
        successHandler.setDefaultTargetUrl(this.adminServer.getContextPath() + "/");

        http.authorizeRequests()
                .antMatchers(this.adminServer.getContextPath() + "/assets/**").permitAll()
                .antMatchers(this.adminServer.getContextPath() + "/login").permitAll()
                .anyRequest().authenticated()
                .and()
                .formLogin()
                .loginPage(this.adminServer.getContextPath() + "/login")
                .successHandler(successHandler)
                .and()
                .logout()
                .logoutUrl(this.adminServer.getContextPath() + "/logout")
                .and()
                .httpBasic()
                .and()
                .csrf()
                .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
                .ignoringRequestMatchers(
                        new AntPathRequestMatcher(this.adminServer.getContextPath()
                                + "/instances", HttpMethod.POST.toString()),
                        new AntPathRequestMatcher(this.adminServer.getContextPath()
                                + "/instances/*", HttpMethod.DELETE.toString()),
                        new AntPathRequestMatcher(this.adminServer.getContextPath() + "/actuator/**"))
                .and()
                .rememberMe()
                .key(UUID.randomUUID().toString())
                .tokenValiditySeconds(1209600);
    }
}
```

### 添加相关配置项

简单起见，登陆的用户名/密码直接在配置文件中指定。

```yaml
spring:
  security:
    user:
      name: allen
      password: 123456
```

### 登陆 Springboot Admin Server

启动 Springboot Admin Server, 进入如下的登陆界面。

![springboot-admin-login](/images/spring-cloud/springboot-admin-login.jpg "springboot-admin-login")

此时因为没有服务接入，登陆成功之后，显示没有服务。

![springboot-admin-login](/images/spring-cloud/springboot-admin-login-null.jpg "springboot-admin-login")

## 引入 Srpingboot Admin Client

### 引入依赖

在 Springboot 项目中，要接入 Srpingboot Admin, 需要引入 Srpingboot Admin Client 相关的依赖。

```xml
<properties>
    <!-- spring boot -->
    <spring-boot.version>2.2.5.RELEASE</spring-boot.version>
</properties>

<dependencies>
    <!-- springboot actuator -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>

    <!-- springboot admin client -->
    <dependency>
        <groupId>de.codecentric</groupId>
        <artifactId>spring-boot-admin-starter-client</artifactId>
        <version>2.2.3</version>
    </dependency>

</dependencies>
```

### 添加配置项

```yaml
spring:
  boot:
    admin:
      client:
        # 访问服务器用户名/密码
        username: allen
        password: 123456
        # 服务端 url
        url: http://127.0.0.1:9090
        instance:
          # 客户端实例 url
          service-url: http://127.0.0.1:8080
          prefer-ip: true
          # 客户端实例名称
          name: moniotr-actuator

```

**配置项：**
- spring.boot.admin.client.username: Springboot admin server 用户名；
- spring.boot.admin.client.password: Springboot admin server 密码；
- spring.boot.admin.client.url: Springboot admin server url;
- spring.boot.admin.client.instance.service-url: Springboot admin client 实例的 url；
- spring.boot.admin.client.instance.name: Springboot admin client 实例名；

### 启动服务

启动服务之后，该服务会注册到 Springboot admin server 中，如下图所示：
![springboot-admin-login](/images/spring-cloud/springboot-admin-login-instance.jpg "springboot-admin-login")

可以在“应用墙”中查看服务的具体信息，也可以进行日志级别的修改等等；
![springboot-admin-login](/images/spring-cloud/springboot-admin-instance-details.jpg "springboot-admin-instance-details")

### 小结
- 为了避免对 Springboot Actuator endpoints 的非法访问，可以在服务中引入 Spring Security; 
- 服务接入 Springboot Admin Server 之后，可以方便对接其它的监控功能，如邮箱或短信告警功能，可根据需要进行对接。

[工程代码：https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springboot-monitor](https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springboot-monitor)

</br>

**参考：**

----
[1]:https://developer.aliyun.com/article/826593

[1. 实战：使用Spring Boot Admin实现运维监控平台][1]
