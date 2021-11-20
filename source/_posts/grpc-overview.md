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
> gRPC (gRPC Remote Procedure Calls[1]) 是 Google 发起的一个开源远程过程调用 (Remote procedure call) 系统。该系统基于 HTTP/2 协议传输，使用 Protocol Buffers 作为接口描述语言。
提供的功能有：
- 认证（ authentication）
- 双向流（bidirectional streaming）
- 流控制（flow control）
- 超时（timeouts）

在这篇文章重点是基于 HTTP2 协议，如何实现双向流。

## Java gRPC 实例

在该实例中，构建工具使用 maven。

### 引入 jar 包及编译插件
**1. 引入 gRPC jar 包**

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

**2. 引入 Java gRPC 编译插件**

编译插件主要是根据接口定义文件自动生成客户端及服务端代码，接口文件放在工程源代码目录下：src/main/proto，生成的代码位于如下目录：target/generated-sources/protobuf。

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

执行 mvn package 打包时便生成 gRPC 的代码。

### 定义接口文件

接口文件使用 Protocol Buffers 定义，在这里定义了一个 Greeter 服务，它提供了 gRPC 支持的四种通信模式：
1. SayHello, 实现 request-response 模式；
2. LotsOfReplies, 实现 request-stream 模式；
3. LotsOfGreetings, 实现 stream-response 模式；
3. BidiHello, 实现 stream-stream 模式。

其中, HelloRequest 是请求消息，HelloReply 是响应结果。

```go
syntax = "proto3";

option java_multiple_files = true;
option java_package = "org.noahsark.examples.helloworld";
option java_outer_classname = "HelloWorldProto";
option objc_class_prefix = "HLW";

package helloworld;

// 接口定义
service Greeter {

  // request <--> response
  rpc SayHello(HelloRequest) returns (HelloReply) {}

  // request <--> stream
  rpc LotsOfReplies(HelloRequest) returns (stream HelloReply){}

  // stream <--> response
  rpc LotsOfGreetings(stream HelloRequest) returns (HelloReply) {}

  // stream <--> stream
   rpc BidiHello(stream HelloRequest) returns (stream HelloReply) {}
}

// 请求消息
message HelloRequest {
  string name = 1;
}

// 响应消息
message HelloReply {
  string message = 1;
}
```

stream 的处理逻辑主要通过 StreamObserver 接口来实现，只要持有该对象，我们就可以接收和发送 stream 数据，其定义如下：
```java
public interface StreamObserver<V> {
    void onNext(V var1);

    void onError(Throwable var1);

    void onCompleted();
}
```
其中：
- onNext: 接收或发送下一个数据；
- onError: 接收或发送一个异常；
- onCompleted: 结束流操作。

### 客户端代码

通过代码可以看到，gRPC 提供了两类连接服务器的客户端代码：GreeterBlockingStub 和 GreeterStub，它们的区别是阻塞和非阻塞，其中，除了 request-response 可以使用阻塞式的客户端，有 stream 的请求都是使用非阻塞的。stream 的操作通过 StreamObserver 实现。

```java
public class HelloWorldClient {
    private static final Logger logger = LoggerFactory.getLogger(HelloWorldClient.class.getName());

    // 同步客户端(stub),由 gRPC 编译器生成
    private final GreeterGrpc.GreeterBlockingStub blockingStub;

    // 异步客户端(stub),由 gRPC 编译器生成
    private final GreeterGrpc.GreeterStub stub;

    /**
     * 构造函数
     * @param channel gRPC channel
     */
    public HelloWorldClient(Channel channel) {

        blockingStub = GreeterGrpc.newBlockingStub(channel);
        stub = GreeterGrpc.newStub(channel);
    }

    /**
     * request-response
     */
    public void sayHello() {
        logger.info("Send a sayHello request ...");

        HelloRequest request = HelloRequest.newBuilder().setName("Allen").build();
        HelloReply response;
        try {
            response = blockingStub.sayHello(request);
        } catch (StatusRuntimeException e) {
            logger.info("RPC failed: {0}", e.getStatus());
            return;
        }
        logger.info("Greeting: " + response.getMessage());
    }

    /**
     * request-stream
     */
    public void lotsOfReplies() {
        logger.info("Send lotsOfReplies request......");

        HelloRequest request = HelloRequest.newBuilder()
                .setName("Allen")
                .build();

        StreamObserver<HelloReply> response = new StdoutStreamObserver("lotsOfReplies");

        stub.lotsOfReplies(request, response);
    }

    /**
     * stream-stream
     */
    public void bidiHello() {

        logger.info("send bidiHello......");

        StreamObserver<HelloReply> response = new StdoutStreamObserver("bidiHello");
        final StreamObserver<HelloRequest> request = stub.bidiHello(response);

        for (int i = 0; i < 10; i++) {
            HelloRequest helloRequest = HelloRequest.newBuilder()
                    .setName("Allen")
                    .build();

            logger.info("send a request:{}", helloRequest.getName());

            request.onNext(helloRequest);
        }
        request.onCompleted();

    }

    /**
     * stream-response
     */
    public void lotsOfGreetings() {

        logger.info("send lotsOfGreetings......");

        StreamObserver<HelloReply> response = new StdoutStreamObserver("lotsOfGreetings");
        final StreamObserver<HelloRequest> request = stub.lotsOfGreetings(response);

        for (int i = 0; i < 10; i++) {
            HelloRequest helloRequest = HelloRequest.newBuilder()
                    .setName("Allen")
                    .build();

            logger.info("Send a request:{}", helloRequest.getName());

            request.onNext(helloRequest);
        }
        request.onCompleted();

    }

    /**
     * 程序入口
     * @param args 启动参数
     * @throws Exception 运行异常
     */
    public static void main(String[] args) throws Exception {
        // Access a service running on the local machine on port 50051
        String target = "localhost:50051";

        ManagedChannel channel = ManagedChannelBuilder.forTarget(target)
                .usePlaintext()
                .build();
        try {
            HelloWorldClient client = new HelloWorldClient(channel);
            client.sayHello();
            client.lotsOfReplies();
            client.lotsOfGreetings();
            client.bidiHello();

            // pause program ...
            new CountDownLatch(1).await(10, TimeUnit.SECONDS);
        } catch (Exception ex) {
            logger.warn("stop the program.");
        }
    }
}

```

### 服务端代码

gRPC 提供了服务器 Sever 的实现，对于开发者而言，只要提供一个接口的实现类，如 GreeterImpl, 并注册到 Sever 中即可。

```java
public class HelloWorldServer {

    private static final Logger logger = LoggerFactory.getLogger(HelloWorldServer.class.getName());

    // gRPC server
    private Server server;

    /**
     * 服务实现类
     */
    static class GreeterImpl extends GreeterGrpc.GreeterImplBase {

        @Override
        public void sayHello(HelloRequest req, StreamObserver<HelloReply> responseObserver) {

            logger.info("Recevice an unary rpc:{}", req.getName());
            HelloReply reply = HelloReply.newBuilder().setMessage("Hello " + req.getName()).build();

            responseObserver.onNext(reply);
            responseObserver.onCompleted();
        }

        public void lotsOfReplies(HelloRequest request, StreamObserver<HelloReply> responseObserver) {
            logger.info("receive an request in lotsOfReplies.");

            for (int i = 0; i < 10; i++) {
                responseObserver.onNext(HelloReply.newBuilder()
                        .setMessage("Hello " + request.getName())
                        .build());
            }

            responseObserver.onCompleted();
        }

        @Override
        public StreamObserver<HelloRequest> bidiHello(StreamObserver<HelloReply> responseObserver) {
            logger.info("receive an request in bidiHello.");

            return new StreamObserver<HelloRequest>() {
                @Override
                public void onNext(HelloRequest data) {
                    responseObserver.onNext(HelloReply.newBuilder()
                            .setMessage("Hello " + data.getName())
                            .build());
                }

                @Override
                public void onError(Throwable throwable) {
                    throwable.printStackTrace();
                    responseObserver.onError(new IllegalStateException("Stream err"));
                }

                @Override
                public void onCompleted() {
                    responseObserver.onCompleted();
                }
            };
        }

        @Override
        public StreamObserver<HelloRequest> lotsOfGreetings(StreamObserver<HelloReply> responseObserver) {
            logger.info("receive an request in lotsOfGreetings.");

            return new StreamObserver<HelloRequest>() {
                @Override
                public void onNext(HelloRequest data) {
                    logger.info("receive a message:{}", data.getName());
                }

                @Override
                public void onError(Throwable throwable) {
                    throwable.printStackTrace();
                    responseObserver.onError(new IllegalStateException("Stream err"));
                }

                @Override
                public void onCompleted() {
                    HelloReply reply = HelloReply.newBuilder().setMessage("completed,lotsOfGreetings").build();

                    responseObserver.onNext(reply);
                    responseObserver.onCompleted();
                }
            };
        }
    }

    /**
     * 启动服务
     * @throws IOException 异常
     */
    private void start() throws IOException {
        /* The port on which the server should run */
        int port = 50051;
        server = ServerBuilder.forPort(port)
                .addService(new GreeterImpl()) // 注册服务实现类
                .build()
                .start();
        logger.info("Server started, listening on " + port);
        Runtime.getRuntime().addShutdownHook(new Thread() {
            @Override
            public void run() {
                // Use stderr here since the logger may have been reset by its JVM shutdown hook.
                System.err.println("*** shutting down gRPC server since JVM is shutting down");
                try {
                    HelloWorldServer.this.stop();
                } catch (InterruptedException e) {
                    e.printStackTrace(System.err);
                }
                System.err.println("*** server shut down");
            }
        });
    }

    /**
     * 服务关闭
     * @throws InterruptedException 异常
     */
    private void stop() throws InterruptedException {
        if (server != null) {
            server.shutdown().awaitTermination(30, TimeUnit.SECONDS);
        }
    }

    /**
     * 阻塞服务器
     * @throws InterruptedException 异常
     */
    private void blockUntilShutdown() throws InterruptedException {
        if (server != null) {
            server.awaitTermination();
        }
    }

    /**
     * 程序入口
     * @param args 入口参数
     * @throws IOException IO 异常
     * @throws InterruptedException 中断异常
     */
    public static void main(String[] args) throws IOException, InterruptedException {
        final HelloWorldServer server = new HelloWorldServer();
        server.start();
        server.blockUntilShutdown();
    }

}
```

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

