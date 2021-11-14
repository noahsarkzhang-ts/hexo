---
title: RPC：gRPC
date: 2021-11-14 20:05:48
tags:
- grpc
categories:
- RPC
---

这篇文章内容主要包括：1）gRPC 基本介绍；2）Java gRPC 实例；3）HTTP2 协议介绍；4）gRPC over HTTP2，流协议的介绍；

## 概述
Wikipiedia 对 gRPC 的描述：
> gRPC (gRPC Remote Procedure Calls[1]) 是 Google 发起的一个开源远程过程调用 (Remote procedure call) 系统。该系统基于 HTTP/2 协议传输，使用Protocol Buffers 作为接口描述语言。
提供的功能有：
- 认证（ authentication）
- 双向流（bidirectional streaming）
- 流控制（flow control）
- 超时（timeouts）

在这篇文章重点是基于 HTTP2 协议，如何实现双向流。

## Java gRPC 实例

在该实例中，构建工具使用 maven。

### 引入 jar 包及编译插件
1. 引入 gRPC jar 包
gRPC 使用的版本是 1.41.0
```XML
<properties>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    <grpc.version>1.41.0</grpc.version><!-- CURRENT_GRPC_VERSION -->
    <protoc.version>3.17.2</protoc.version>
    <netty.tcnative.version>2.0.34.Final</netty.tcnative.version>
    <maven.compiler.source>1.9</maven.compiler.source>
    <maven.compiler.target>1.9</maven.compiler.target>
</properties>

<dependencies>

    <dependency>
        <groupId>io.grpc</groupId>
        <artifactId>grpc-protobuf</artifactId>
    </dependency>
    <dependency>
        <groupId>io.grpc</groupId>
        <artifactId>grpc-stub</artifactId>
    </dependency>
    <dependency>
        <groupId>org.apache.tomcat</groupId>
        <artifactId>annotations-api</artifactId>
        <version>6.0.53</version>
        <scope>provided</scope> <!-- not needed at runtime -->
    </dependency>
    <dependency>
        <groupId>io.grpc</groupId>
        <artifactId>grpc-netty</artifactId>
    </dependency>
    <dependency>
        <groupId>io.netty</groupId>
        <artifactId>netty-tcnative-boringssl-static</artifactId>
        <version>${netty.tcnative.version}</version>
        <scope>runtime</scope>
    </dependency>

    <dependency>
        <artifactId>slf4j-api</artifactId>
        <groupId>org.slf4j</groupId>
        <version>1.7.26</version>
    </dependency>

    <dependency>
        <groupId>ch.qos.logback</groupId>
        <artifactId>logback-classic</artifactId>
        <version>1.2.6</version>
    </dependency>

    <dependency>
        <groupId>junit</groupId>
        <artifactId>junit</artifactId>
    </dependency>
</dependencies>

<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>io.grpc</groupId>
            <artifactId>grpc-bom</artifactId>
            <version>${grpc.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

2. 引入 Java rRPC 编译插件
```xml
<build>
        <extensions>
            <extension>
                <groupId>kr.motd.maven</groupId>
                <artifactId>os-maven-plugin</artifactId>
                <version>1.6.2</version>
            </extension>
        </extensions>

        <plugins>
            <plugin>
                <groupId>org.xolstice.maven.plugins</groupId>
                <artifactId>protobuf-maven-plugin</artifactId>
                <version>0.6.1</version>
                <configuration>
                    <protocArtifact>com.google.protobuf:protoc:${protoc.version}:exe:${os.detected.classifier}
                    </protocArtifact>
                    <pluginId>grpc-java</pluginId>
                    <pluginArtifact>io.grpc:protoc-gen-grpc-java:${grpc.version}:exe:${os.detected.classifier}
                    </pluginArtifact>
                </configuration>
                <executions>
                    <execution>
                        <goals>
                            <goal>compile</goal>
                            <goal>compile-custom</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
        </plugins>
</build>
```

执行 maven 打包时便生成 gRPC 的代码。

### 定义接口文件

### 客户端代码

### 服务端代码

## HTTP2

## gRPC over HTTP2

</br>

**参考：**

----
[1]:https://grpc.io/docs/what-is-grpc/core-concepts/
[2]:https://zh.wikipedia.org/wiki/GRPC
[3]:https://www.rabbitmq.com/confirms.html
[4]:https://www.rabbitmq.com/vhosts.html
[5]:https://www.rabbitmq.com/queues.html
[6]:https://www.rabbitmq.com/getstarted.html
[7]:https://www.rabbitmq.com/access-control.html
[8]:https://www.rabbitmq.com/rabbitmqctl.8.html
[9]:https://www.rabbitmq.com/production-checklist.html

[1. Core concepts, architecture and lifecycle][1]

[2. gRPC][2]

[3. Consumer Acknowledgements and Publisher Confirms][3]

[4. Virtual Hosts][4]

[5. queues][5]

[6. RabbitMQ Tutorials][6]

[7. Authentication, Authorisation, Access Control][7]

[8. rabbitmqctl(8)][8]

[9. Production Checklist][9]

