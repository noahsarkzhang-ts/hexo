---
title: RPC：Dubbo
date: 2021-11-21 10:14:06
tags:
- dubbo
- triple
- http2
categories:
- RPC
---

## 概述
Dubbo 官网对 Dubbo 的描述：
> Apache Dubbo 是一款微服务开发框架，它提供了 RPC通信 与 微服务治理 两大关键能力。这意味着，使用 Dubbo 开发的微服务，将具备相互之间的远程发现与通信能力， 同时利用 Dubbo 提供的丰富服务治理能力，可以实现诸如服务发现、负载均衡、流量调度等服务治理诉求。同时 Dubbo 是高度可扩展的，用户几乎可以在任意功能点去定制自己的实现，以改变框架的默认行为来满足自己的业务需求。

Dubbo 目前有两个大的版本：2.x 和 3.0，2.x 版本也是我们在项目中使用的版本，这是一个同步的 Request-Response 模型的 RPC 框架，而 3.0 版本通过引入 triple 协议，支持了更多的通信模型：
- 消费端异步请求(Client Side Asynchronous Request-Response)
- 提供端异步执行（Server Side Asynchronous Request-Response）
- 消费端请求流（Request Streaming）
- 提供端响应流（Response Streaming）
- 双向流式通信（Bidirectional Streaming）

Dubbo 官网将 triple 定义为下一代 RPC 通信协议，是这样描述的：
> 定义了全新的 RPC 通信协议 – Triple，一句话概括 Triple：它是基于 HTTP/2 上构建的 RPC 协议，完全兼容 gRPC，并在此基础上扩展出了更丰富的语义。 使用 Triple 协议，用户将获得以下能力:
- 更容易到适配网关、Mesh架构，Triple 协议让 Dubbo 更方便的与各种网关、Sidecar 组件配合工作。
- 多语言友好，推荐配合 Protobuf 使用 Triple 协议，使用 IDL 定义服务，使用 Protobuf 编码业务数据。
- 流式通信支持。Triple 协议支持 Request Stream、Response Stream、Bi-direction Stream。

从同步/异步和通信模型两个维度来总结：
- Dubbo 2.x 是一个同步的、只支持 Request-Response 模型的 RPC 框架；
- Dubbo 3.0 支持异步、支持 Request Stream、Response Stream、Bi-direction Stream 多种通信模型的下一代 RPC 通信框架。

后面以一个 Java 实例来演示下它的功能。

## Dubbo 服务模型
### 一个简化模型
在 Dubbo 服务模型中有几个重要的概念：
- Invoker：它是 Dubbo 的核心模型，其它模型都向它靠扰，或转换成它，它代表一个可执行体，可以向它发起调用，它有可能是一个本地的实现，也可能是一个远程的实现，也可能一个集群实现；在客户端，它作为服务的调用方，向服务端发起调用，在服务端，它封装了服务实现类，代表了最终的服务提供方；
- Exporter：它封装了服务端的 Invoker 对象，将服务发布出去；
- Protocol: 它负责 Exporter 和 Invoker 对象的生命周期管理；
- Invocation：它持有调用过程中的变量，比如方法名，参数等。

一个简化的模型如下图所示：
![dubbo-model](/images/rpc/dubbo-model.png "dubbo-model")

### 发布服务
在服务端，将服务实现封装成为一个 Invoker 对象，通过 Exporter 发布出去。
![dubbo-deploy-servie](/images/rpc/dubbo-deploy-servie.png "dubbo-deploy-servie")

### 引用服务
在客户端，将一次远程 RPC 调用转化为本地 Invoker 对象的调用，再通过 Invoker 对象发起远程的调用。
![dubbo-refer-servie](/images/rpc/dubbo-refer-servie.png "dubbo-refer-servie")

## Java Dubbo 实例
### 引入依赖
Triple 协议依赖 Protocol Buffers 及 gRPC, Protocol Buffers 用来作为数据的序列化及服务的定义，在 Java 实例里没有使用 Protocol Buffers 来进行服务定义，如果是其它语言，官方建议使用  Protocol Buffers 作为 IDL 来描述服务，从而获得跨平台的能力。另外，Dubbo 扩展了 grpc-java 代码生成插件，从这点来看，Dubbo Triple 协议是否也可以理解为 gRPC 协议的扩展？

```xml
<properties>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    <maven.compiler.source>1.9</maven.compiler.source>
    <maven.compiler.target>1.9</maven.compiler.target>
    <source.level>1.9</source.level>
    <target.level>1.9</target.level>
    <dubbo.version>3.0.4</dubbo.version>
    <grpc.version>1.40.1</grpc.version>
    <maven-compiler-plugin.version>3.7.0</maven-compiler-plugin.version>
    <maven-failsafe-plugin.version>2.21.0</maven-failsafe-plugin.version>
    <protoc.version>3.7.1</protoc.version>
    <dubbo.compiler.version>0.0.4-SNAPSHOT</dubbo.compiler.version>
</properties>

<dependencies>

    <dependency>
        <groupId>org.apache.dubbo</groupId>
        <artifactId>dubbo</artifactId>
        <version>${dubbo.version}</version>
    </dependency>
    <dependency>
        <groupId>com.google.protobuf</groupId>
        <artifactId>protobuf-java</artifactId>
        <version>3.14.0</version>
    </dependency>
    <dependency>
        <groupId>org.apache.dubbo</groupId>
        <artifactId>dubbo-dependencies-zookeeper</artifactId>
        <version>${dubbo.version}</version>
        <type>pom</type>
    </dependency>
    <dependency>
        <groupId>io.grpc</groupId>
        <artifactId>grpc-all</artifactId>
        <version>${grpc.version}</version>
    </dependency>

    <dependency>
        <groupId>org.testcontainers</groupId>
        <artifactId>testcontainers</artifactId>
        <version>1.12.3</version>
        <scope>test</scope>
    </dependency>
</dependencies>

<build>
    <extensions>
        <extension>
            <groupId>kr.motd.maven</groupId>
            <artifactId>os-maven-plugin</artifactId>
            <version>1.6.1</version>
        </extension>
    </extensions>
    <plugins>
        <plugin>
            <groupId>org.xolstice.maven.plugins</groupId>
            <artifactId>protobuf-maven-plugin</artifactId>
            <version>0.6.1</version>
            <configuration>
                <protocArtifact>com.google.protobuf:protoc:${protoc.version}:exe:${os.detected.classifier}</protocArtifact>
                <pluginId>grpc-java</pluginId>
                <pluginArtifact>io.grpc:protoc-gen-grpc-java:${grpc.version}:exe:${os.detected.classifier}</pluginArtifact>
                <protocPlugins>
                    <protocPlugin>
                        <id>dubbo</id>
                        <groupId>org.apache.dubbo</groupId>
                        <artifactId>dubbo-compiler</artifactId>
                        <version>${dubbo.compiler.version}</version>
                        <mainClass>org.apache.dubbo.gen.dubbo.Dubbo3Generator</mainClass>
                    </protocPlugin>
                </protocPlugins>
            </configuration>
            <executions>
                <execution>
                    <goals>
                        <goal>compile</goal>
                        <goal>test-compile</goal>
                        <goal>compile-custom</goal>
                        <goal>test-compile-custom</goal>
                    </goals>
                </execution>
            </executions>
        </plugin>
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-compiler-plugin</artifactId>
            <version>${maven-compiler-plugin.version}</version>
            <configuration>
                <source>${source.level}</source>
                <target>${target.level}</target>
            </configuration>
        </plugin>
    </plugins>
</build>
```

### 接口定义
接口定义分为两个部分，一个是接口描述，另外一个是请求及响应参数描述。在这里，接口使用 Java 语言描述，而参数使用 Protocol Buffers 来描述。

**接口描述**
```java
public interface IGreeter {

    /**
     * Request-Response
     * @param request 请求
     * @return 响应
     */
    HelloReply sayHello(HelloRequest request);

    /**
     * stream-stream
     * @param replyStream response stream 
     * @return request stream
     */
    StreamObserver<HelloRequest> bidiHello(StreamObserver<HelloReply> replyStream);

    /**
     * request-stream
     * @param request 请求
     * @param replyStream 响应
     */
    void lotsOfReplies(HelloRequest request, StreamObserver<HelloReply> replyStream);

    /**
     * stream-response
     * @param replyStream response stream
     * @return request stream
     */
    StreamObserver<HelloRequest> lotsOfGreetings(StreamObserver<HelloReply> replyStream);
}
```

**参数描述**
```go
syntax = "proto3";

option java_multiple_files = true;
option java_package = "org.apache.dubbo.hello";
option java_outer_classname = "HelloWorldProto";
option objc_class_prefix = "HLW";

package helloworld;

// The request message containing the user's name.
message HelloRequest {
  string name = 1;
}

// The response message containing the greetings
message HelloReply {
  string message = 1;
}
```

执行 mvn package 生成代码。


### 客户端代码

```java
// 定义服务消费
class ApiConsumer {
    private final IGreeter delegate;

    /**
     * 定义服务消费方
     */
    ApiConsumer() {
        // 定义一个服务引用
        ReferenceConfig<IGreeter> ref = new ReferenceConfig<>();
        ref.setInterface(IGreeter.class);
        ref.setCheck(false);
        ref.setInterface(IGreeter.class);
        ref.setCheck(false);
        ref.setProtocol(CommonConstants.TRIPLE);
        ref.setLazy(true);
        ref.setTimeout(100000);

        ApplicationConfig applicationConfig = new ApplicationConfig("demo-consumer");
        applicationConfig.setQosPort(33333);

        DubboBootstrap bootstrap = DubboBootstrap.getInstance();
        bootstrap.application(applicationConfig)
                .registry(new RegistryConfig(TriSampleConstants.ZK_ADDRESS))
                .reference(ref)
                .start();

        // 生成代理对象
        this.delegate = ref.get();
    }

    /**
     * request-stream
     */
    public void lotsOfReplies() {
        delegate.lotsOfReplies(HelloRequest.newBuilder()
                .setName("allen")
                .build(), new StdoutStreamObserver<>("serverStream"));
    }

    /**
     * stream-response
     */
    public void lotsOfGreetings() {
        final StreamObserver<HelloRequest> request = delegate.lotsOfGreetings(new StdoutStreamObserver<>("lotsOfGreetings"));
        for (int i = 0; i < 10; i++) {
            request.onNext(HelloRequest.newBuilder()
                    .setName("allen")
                    .build());
        }
        request.onCompleted();
    }

    /**
     * stream-stream
     */
    public void bidiHello() {
        final StreamObserver<HelloRequest> request = delegate.bidiHello(new StdoutStreamObserver<>("stream"));
        for (int i = 0; i < 10; i++) {
            request.onNext(HelloRequest.newBuilder()
                    .setName("allen")
                    .build());
        }
        request.onCompleted();
    }

    /**
     * request-response
     */
    public void sayHello() {
        try {
            final HelloReply reply = delegate.sayHello(HelloRequest.newBuilder()
                    .setName("allen")
                    .build());
            TimeUnit.SECONDS.sleep(1);
            System.out.println("Reply:" + reply);
        } catch (Throwable t) {
            t.printStackTrace();
        }
    }

    /**
     * 程序入口
     * @param args 入口参数
     * @throws IOException 异常
     */
    public static void main(String[] args) throws IOException {
        final ApiConsumer consumer = new ApiConsumer();
        System.out.println("dubbo triple consumer started");

        consumer.sayHello();
        consumer.bidiHello();
        consumer.lotsOfReplies();
        consumer.lotsOfGreetings();

        System.in.read();
    }

}

```

### 服务端代码

```java
// 服务实现代码
public class Greeter1Impl implements IGreeter {
    @Override
    public HelloReply sayHello(HelloRequest request) {

        return HelloReply.newBuilder()
                .setMessage(request.getName())
                .build();
    }

    public HelloReply sayHelloException(HelloRequest request) {
        RpcContext.getServerContext().setAttachment("str", "str")
                .setAttachment("integer", 1)
                .setAttachment("raw", new byte[]{1, 2, 3, 4});
        throw new RuntimeException("Biz Exception");
    }

    @Override
    public StreamObserver<HelloRequest> bidiHello(StreamObserver<HelloReply> replyStream) {
        return new StreamObserver<HelloRequest>() {
            @Override
            public void onNext(HelloRequest data) {
                replyStream.onNext(HelloReply.newBuilder()
                        .setMessage(data.getName())
                        .build());
            }

            @Override
            public void onError(Throwable throwable) {
                throwable.printStackTrace();
                replyStream.onError(new IllegalStateException("Stream err"));
            }

            @Override
            public void onCompleted() {
                replyStream.onCompleted();
            }
        };
    }

    @Override
    public void lotsOfReplies(HelloRequest request, StreamObserver<HelloReply> replyStream) {
        for (int i = 0; i < 10; i++) {
            replyStream.onNext(HelloReply.newBuilder()
                    .setMessage(request.getName())
                    .build());
        }
        replyStream.onCompleted();
    }

    @Override
    public StreamObserver<HelloRequest> lotsOfGreetings(StreamObserver<HelloReply> replyStream) {
        StdoutStreamObserver stdoutStreamObserver = new StdoutStreamObserver("lotsOfGreetings");

        return new StreamObserver<HelloRequest>() {
            @Override
            public void onNext(HelloRequest data) {
                stdoutStreamObserver.onNext(data.getName());
            }

            @Override
            public void onError(Throwable throwable) {
                throwable.printStackTrace();
                stdoutStreamObserver.onError(new IllegalStateException("Stream err"));
            }

            @Override
            public void onCompleted() {
                HelloReply reply = HelloReply.newBuilder().setMessage("completed,lotsOfGreetings").build();

                replyStream.onNext(reply);
                replyStream.onCompleted();

                stdoutStreamObserver.onCompleted();
            }
        };
    }
}

// 服务发布
class ApiProvider {
    public static void main(String[] args) {
        // 内置 zk 注册中心
        new EmbeddedZooKeeper(TriSampleConstants.ZK_PORT, false).start();

        // 服务发布定义
        ServiceConfig<IGreeter> service = new ServiceConfig<>();
        service.setInterface(IGreeter.class);
        service.setRef(new Greeter1Impl());
        service.setToken(true);

        // 启动服务
        DubboBootstrap bootstrap = DubboBootstrap.getInstance();
        bootstrap.application(new ApplicationConfig("demo-provider"))
                .registry(new RegistryConfig(TriSampleConstants.ZK_ADDRESS))
                .protocol(new ProtocolConfig(CommonConstants.TRIPLE, TriSampleConstants.SERVER_PORT))
                .service(service)
                .start()
                .await();

    }
}
```

## 总结
可以发现，不管在客户端还是服务端，对于异步和 stream 操作都是通过 StreamObserver 对象来实现，它跟 gRPC 中的是一致，用过 gRPC 的话，可以无缝衔接 Dubbo 的 Triple，使用方式及相关的类都是一样的。


**参考：**

----
[1]:https://dubbo.apache.org/zh/docs/

[1. dubbo 官方文档][1]

