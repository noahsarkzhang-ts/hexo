---
title: RPC：gRPC
date: 2021-11-14 20:05:48
updated: 2021-11-14 20:05:48
tags:
- grpc
- http2
categories:
- RPC
---

这篇文章内容主要包括：1）gRPC 基本介绍；2）Java gRPC 实例；3）HTTP2 协议介绍；4）gRPC over HTTP2，流协议的介绍；

<!-- more -->

## 概述
Wikipiedia 对 gRPC 的描述：
> gRPC (gRPC Remote Procedure Calls[1]) 是 Google 发起的一个开源远程过程调用 (Remote procedure call) 系统。该系统基于 HTTP/2 协议传输，使用 Protocol Buffers 作为接口描述语言。
提供的功能有：
- 认证（ authentication）;
- 双向流（bidirectional streaming）;
- 流控制（flow control）;
- 超时（timeouts）。

在这篇文章重点是讲述基于 HTTP2 协议，如何实现双向流。

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

执行 mvn package 命令便生成 gRPC 相关的代码。

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
gRPC 底层的通信协议是 HTTP2，其 stream 的特性就是基于 HTTP2 stream 来实现的，要理解 gRPC 的实现，首先先要理解 HTTP2 协议。

### HTTP 演进
HTTP 内容比较多，每一次版本升级的特性也比较多，我们在这里仅仅选择“连接复用”的角度来阐述 HTTP 的演进。 

**HTTP 1.0**
在 HTTP 1.0 协议中，一个 TCP 连接只承载了一次网络请求，TCP 的复用率比较低，如下图所示：
![http1.0](/images/rpc/http1.0.jpg "http1.0")

在这种场景下，建立 tcp 连接占了较大一部分开销，为了提高 TCP 的复用率，HTTP 1.1 引入了“持久连接”和“管道”的技术。

**HTTP 1.1**
在 HTTP 1.1 协议中，一个 TCP 连接可以被多个 HTTP 请求共享，这些请求是按序发送，下一个请求必须在上一个请求收到响应之后才能发送，如下图所示：

![http1.1](/images/rpc/http1.1.jpg "http1.1")

为了提高发送的效率，HTTP 1.1 引入了“管道”技术，可以并行地发送多个 HTTP 请求，而不用等待上一个请求的响应。但响应结果仍然是有序的，即上一个请求的响应发送之后，才能发送下一个请求的响应。这就引发了 HTTP 的队头阻塞（head-of-line blocking）问题，上一个请求的响应会影响后续的响应。如果前一个请求的结果比较大，就会阻塞后续请求的响应。

**HTTP 2.0**
HTTP 2.0 为了解决 HTTP 队头阻塞的问题，引入了 stream 的概念。将一个 TCP 连接逻辑划分为多个 stream，每一个 stream 可独立负责一个 HTTP 请求，这些 stream 之间，1）可并行交错地发送多个请求，请求之间互不影响；2）可并行交错地发送多个响应，响应之间互不干扰；3）使用一个连接并行发送多个请求和响应。如下图所示：

![http2-multiplexing](/images/rpc/http2-multiplexing.svg "http2-multiplexing")

HTTP 2.0 解决了 HTTP 队头阻塞的问题，但由于 HTTP 2.0 底层传输协议仍然是 TCP 协议，TCP 协议本身也有队头阻塞（head-of-line blocking）问题，其主要原因是数据包超时确认或丢失阻塞了滑动窗口向右滑动，阻塞了后续数据的发送，如下图所示：

![tcp-sliding-window-v1](/images/rpc/tcp-sliding-window-v1.jpg "tcp-sliding-window-v1")

未收到 ACK 确认的消息将会占用滑动窗口，压缩了可发送窗口的大小。

**HTTP 3.0**
由于 TCP 存在队头阻塞的问题，下一代的 HTTP 3.0 将可能改用 UDP 协议，如 QUIC，它在 UDP 的基础上实现类似 TCP connection 的概念。

### HTTP2 功能
相比于 HTTP 1.0, HTTP2 所有的数据使用二进制帧进行封装，极大地提高了客户端与服务器之间的传输效率，如下图所示:
![binary_framing_layer01](/images/rpc/binary_framing_layer01.svg "binary_framing_layer01")

在 HTTP2 中有三个重要的概念：
- 数据流(stream): 已建立的连接内的双向字节流，可以承载一条或多条消息；
- 消息(message): 与逻辑请求或响应消息对应的完整的一系列帧；
- 帧(frame):HTTP2 通信的最小单位，每个帧都包含帧头，至少也会标识出当前帧所属的数据流。

它们之间的关系如下：
- 所有通信都在一个 TCP 连接上完成，此连接可以承载任意数量的双向数据流；
- 每个数据流都有一个唯一的标识符和可选的优先级信息，用于承载双向消息；
- 每条消息都是一条逻辑 HTTP 消息（例如请求或响应），包含一个或多个帧；
- 帧是最小的通信单位，承载着特定类型的数据，例如 HTTP 标头、消息负载等等。 来自不同数据流的帧可以交错发送，然后再根据每个帧头的数据流标识符重新组装。

![streams_messages_frames01](/images/rpc/streams_messages_frames01.svg "streams_messages_frames01")

在一个 TCP 连接上承载了不同的 HTTP 请求，互不干扰。

**二进制帧协议**
一个二进制帧包括两个部分，一个是 8 字节的首部，其中包含帧的长度、类型、标志，还有一个保留位和一个31位的流标识符；另外一部分是实际传输的数据，如下图所示：

![http2-binary-frame-format.](/images/rpc/http2-binary-frame-format.png "http2-binary-frame-format")

首部的定义如下：
- 16 位的长度意味着一帧可以携带最大 64 KB 的数据，不包括 8 字节首部；
- 8 位的类型字段决定如何解释帧的内容；
- 8 位的标志位字段允许不同的帧类型定义特定于帧的消息标志，<strong><font color='red'>流的结束可以通过标志位来表示</font></strong>；
- 1 位的保留字段始终置为 0；
- 31 位的流标识字段唯一标识 HTTP 2.0 的流。

其中帧类型可以分为：
- DATA：用于传输 HTTP 消息体；
- HEADERS：用于传输 HTTP header；
- SETTINGS：用于约定客户端和服务端的配置数据；
- WINDOW_UPDATE：用于调整个别流或个别连接的流量；
- PRIORITY： 用于指定或重新指定引用资源的优先级；
- RST_STREAM： 用于通知流的非正常终止；
- PUSH_PROMISE： 服务端推送许可；
- PING：用于计算往返时间，用于保活；
- GOAWAY：用于通知对端停止在当前连接中创建流；
- CONTINUATION：用于继续一系列的 HEADERS。

## gRPC over HTTP2
gRPC 通常有四种模式，unary,client streaming,server streaming 以及 bidirectional streaming，对应 request-response, stream-response, request-stream 及 stream-stream， 对于底层 HTTP/2 来说，它们都是 stream，并且仍然是一套 request + response 模型。

### 通信协议
gRPC 协议中的 Request 及 Response 定义如下：
```txt
Request → Request-Headers *Length-Prefixed-Message EOS
Response → (Response-Headers *Length-Prefixed-Message Trailers) / Trailers-Only
```
Request 主要包含三个部分：1）一个消息头： Request-Headers; 2）消息内容：0 或 多个 Length-Prefixed-Message; 3）EOS（end-of-stream）: 用来表示 stream 不会在发送任何数据，可以关闭了。 

Response 主要包含三个部分：1）一个消息头：Response-Headers; 2) 消息内容：0 或 多个 Length-Prefixed-Message; 3）Trailers; 如果报错了，只会返回 Trailers-Only，在 Trailers 中会包含 stream 结束标志。

在 Protocol Buffers 定义的方法可以很方便地跟 HTTP2 中的相关 Header 关联起来：
```go
Path : /Service-Name/{method name}
Service-Name : ?( {proto package name} "." ) {service name}
Message-Type : {fully qualified proto message name}
Content-Type : "application/grpc+proto"
```

### 实例
以官方给的 unary 为例，其消息包含如下内容：

**Request:**
```go
HEADERS (flags = END_HEADERS)
:method = POST
:scheme = http
:path = /google.pubsub.v2.PublisherService/CreateTopic
:authority = pubsub.googleapis.com
grpc-timeout = 1S
content-type = application/grpc+proto
grpc-encoding = gzip
authorization = Bearer y235.wef315yfh138vh31hv93hv8h3v

DATA (flags = END_STREAM)
<Length-Prefixed Message>
```

**Response:**
```go
HEADERS (flags = END_HEADERS)
:status = 200
grpc-encoding = gzip
content-type = application/grpc+proto

DATA
<Length-Prefixed Message>

HEADERS (flags = END_STREAM, END_HEADERS)
grpc-status = 0 # OK
trace-proto-bin = jher831yy13JHy3hc
```

## 总结
gRPC 基于底层 HTTP2 协议实现了 stream 的操作，换句话说，gRPC 不能脱离 Http2 单独存在，这跟 Rscoket 的设计理念是不一样的，Rscoket 是一种应用层协议，它对底层协议没有限制，只要支持 “连接” 的概念，甚至可以基于 UDP 来实现。从这一点来说，gRPC 跟 HTTP2 协议是强依赖的。


</br>

**参考：**

----
[1]:https://grpc.io/docs/what-is-grpc/core-concepts/
[2]:https://zh.wikipedia.org/wiki/GRPC
[3]:https://blog.csdn.net/zhuyiquan/article/details/69257126?utm_medium=distribute.pc_relevant.none-task-blog-2~default~BlogCommendFromMachineLearnPai2~default-1.control&depth_1-utm_source=distribute.pc_relevant.none-task-blog-2~default~BlogCommendFromMachineLearnPai2~default-1.control
[4]:https://www.cnblogs.com/xiaolincoding/p/12732052.html
[5]:https://developers.google.com/web/fundamentals/performance/http2?hl=zh-cn
[6]:https://github.com/grpc/grpc/blob/master/doc/PROTOCOL-HTTP2.md
[7]:https://pingcap.com/zh/blog/grpc

[1. Core concepts, architecture and lifecycle][1]
[2. gRPC][2]
[3. HTTP 2.0 原理详细分析][3]
[4. 30张图解：TCP 重传、滑动窗口、流量控制、拥塞控制][4]
[5. HTTP/2 简介][5]
[6. gRPC over HTTP2][6]
[7. 深入了解 gRPC：协议][7]


