---
title: RPC：RScocket
date: 2021-11-21 12:45:56
tags:
- rscocket
categories:
- RPC
---

## 概述
RSocket 官网对 RSocket 定义：
> RSocket is a binary protocol for use on byte stream transports such as TCP, WebSockets, and Aeron.RSocket provides a protocol for Reactive Streams semantics between client-server, and server-server communication.

RSocket 是一个构建在字节流传输协议，如 TCP, WebSocket 和 Aeron(UDP) 之上的二进制协议，同时，它也是一个为client-server,server-server 之间通信提供了反应式流语义的协议。本质上来说，RSocket 是基于反应式编程的一个二进制协议。一个反应式系统应该具备如下特征：
- Responsive: 只要有可能，系统就会及时地作出反应;
- Resilient: 系统出现 failure 时仍然保持响应性，并能够独立恢复;
- Elastic: 系统在不断变化的工作负载之下依然能保持即时响应性;
- Message Driven: 异步非阻塞消息驱动架构。

RSocket 作为一个应用层的协议，提供了丰富的功能：
- Multiplexed, Binary Protocol：多路复用的二进制协议；
- Bidirectional Streaming: 双向流；
- Flow Control: 流控制；
- Socket Resumption: 连接恢复；
- Message passing: 消息传递模型；
- Transport independent: 与传输层解耦的应用层协议。

在这篇文章，主要讲述与流相关的功能。

## Reactive Streams 

### Flux & Mono
在 RSocket 中，使用 Flux 和 Mono 两个 Reactive Streams 框架来处理流数据，其中 Flux 处理一个流中 0 个或多个消息的场景，而 Mono 处理 0 个或最多 1 个消息的场景。

>Flux: A Reactive Streams Publisher with rx operators that emits 0 to N elements, and then completes (successfully or with an error).

![flux](/images/rpc/flux.svg "flux")

>Mono: A Reactive Streams Publisher with basic rx operators that emits at most one item via the onNext signal then terminates with an onComplete signal (successful Mono, with or without value), or only emits a single onError signal (failed Mono).

![mono](/images/rpc/mono.svg "mono")

Flux 和 Mono 都继承自 Publisher 接口，Publisher 接口只有一个方法 subscribe() 方法，这个方法主要是用来订阅 Subscriber 对象，而 Subscriber 对象用来消息处理数据。

![rsocket-publisher-class](/images/rpc/rsocket-publisher-class.jpg "rsocket-publisher-class")

Publisher 使用了观察者模式，消费者订阅观察者对象 Subscriber，生产者通过 Publisher 对象发布数据，再通知给 Subscriber 对象。

![rsocket-publiser](/images/rpc/rsocket-publisher.jpg "rsocket-publisher")

Subscriber 接口是消息最终处理接口，其定义如下：
```java
public interface Subscriber<T> {
    /**
     * Invoked after calling {@link Publisher#subscribe(Subscriber)}.
     * 
     * @param s Subscription
     */
    public void onSubscribe(Subscription s);

    /**
     * 通知或接收数据
     * 
     * @param t the element signaled
     */
    public void onNext(T t);

    /**
     * Failed terminal state.
     *
     * @param t the throwable signaled
     */
    public void onError(Throwable t);

    /**
     * Successful terminal state.
     *
     */
    public void onComplete();
}
```
Subscriber 接口的定义和功能与 gRPC 中 StreamObserver 是类似的。

### Frame 格式
RSocket 使用二进制帧进行通信，其格式如下所示：
```go
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|0|                         Stream ID                           |
+-----------+-+-+---------------+-------------------------------+
|Frame Type |I|M|     Flags     |
+-------------------------------+-------------------------------+
|              Metadata Length                  |
+---------------------------------------------------------------+
|                       Metadata Payload                       ...
+---------------------------------------------------------------+
|                       Payload of Frame                       ...
+---------------------------------------------------------------+

```
**字段描述：**
- Stream ID: (31 bits = max value 2^31-1 = 2,147,483,647), 用 31 位无符号整数表示 StreamId, 0 专门用来描述整个连接；
- Frame Type:(6 bits = max value 63) 帧类型，下文会介绍；
- Flags: (10 bits), 标志位，具体值取决于帧类型，0 表示不设置。协议要求，所有帧要带两个标志位: (I)gnore: 如果不识别该帧是否忽略 ,(M)etadata: 是否带有 Metadata; 
- Metadata Length: (24 bits = max value 16,777,215), 24 位无符号整数表示 Metadata 长度, 该部分可选，取决于是否有 Metadata; 
- Metadata: Metadata 元数据; 
- Payload: 数据。

**帧类型：**

|   Type    |	Value |	Description |
|   ---- |---- |---- |
| RESERVED  |	0x00 |	Reserved |
| <font color="red">SETUP</font>     |	0x01 | Setup: Sent by client to initiate protocol processing.|
| LEASE	    |   0x02 |	Lease: Sent by Responder to grant the ability to send requests. |
| KEEPALIVE |	0x03 |	Keepalive: Connection keepalive. |
| <font color="red">REQUEST_RESPONSE</font> |	0x04 |  Request Response: Request single response. |
| <font color="red">REQUEST_FNF</font>	| 0x05    |	Fire And Forget: A single one-way message. |
| <font color="red">REQUEST_STREAM </font>|	0x06    |	Request Stream: Request a completable stream. |
| <font color="red">REQUEST_CHANNEL</font> |	0x07 |	Request Channel: Request a completable stream in both directions. |
| REQUEST_N |	0x08 |	Request N: Request N more items with Reactive Streams semantics. |
| CANCEL    |	0x09 |	Cancel Request: Cancel outstanding request. |
| <font color="red">PAYLOAD</font>   |	0x0A |	Payload: Payload on a stream. For example, response to a request, or message on a channel. |
| ERROR  |	0x0B |	Error: Error at connection or application level. |
| METADATA_PUSH	| 0x0C |	Metadata: Asynchronous Metadata frame |
| <font color="red">RESUME</font>    |	0x0D |	Resume: Replaces SETUP for Resuming Operation (optional) |
| RESUME_OK |	0x0E |	Resume OK : Sent in response to a RESUME if resuming operation possible (optional) |
| EXT   |	0x3F |	Extension Header: Used To Extend more frame types as well as extensions. |

在建立好连接之后，发送的第一帧是 SETUP 或 RESUME，主要用于协商客户端与服务器相关的信息，其中 RESUME 用于连接的重建。SETUP 帧的格式如下所示：

```go
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         Stream ID = 0                         |
+-----------+-+-+-+-+-----------+-------------------------------+
|Frame Type |0|M|R|L|  Flags    |
+-----------+-+-+-+-+-----------+-------------------------------+
|         Major Version         |        Minor Version          |
+-------------------------------+-------------------------------+
|0|                 Time Between KEEPALIVE Frames               |
+---------------------------------------------------------------+
|0|                       Max Lifetime                          |
+---------------------------------------------------------------+
|         Token Length          | Resume Identification Token  ...
+---------------+-----------------------------------------------+
|  MIME Length  |   Metadata Encoding MIME Type                ...
+---------------+-----------------------------------------------+
|  MIME Length  |     Data Encoding MIME Type                  ...
+---------------+-----------------------------------------------+
                      Metadata & Setup Payload
```

协商的内容包括协议的版本、KEEPALIVE 间隔时间(单位:ms)、服务保活最大时长(单位:ms)、用于 Resume 的 token(恢复连接时进行比对)、Metadata 编码类型及 Data 编码类型。一旦协商成功，就可以发送后续的请求帧。

### 通信模型
在 RSocket 中支持四种通信模型，分别是：
- Fire-Forget: 只发送 Request，不用 Response;
- Request-Response: 一个 Request，一个 Response;
- Request-Stream: 一个 Request, 响应为 Stream;
- Channel：双向流。

![rsocket-interaction-model](/images/rpc/rsocket-interaction-model.png "rsocket-interaction-model")

四种通信模型对应的帧请求分别为:REQUEST_FNF,REQUEST_RESPONSE,REQUEST_STREAM 及 REQUEST_CHANNEL, 响应结果使用 PAYLOAD 帧，PAYLOAD 用来传输数据。另外，响应结束的 COMPLETE 标志位在 PAYLOAD 帧中定义。 PAYLOAD 定义如下：
```go
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           Stream ID                           |
+-----------+-+-+-+-+-+---------+-------------------------------+
|Frame Type |0|M|F|C|N|  Flags  |
+-------------------------------+-------------------------------+
                     Metadata & Data
```

- Frame Type: (6 bits) 0x0A;
- Flags: (10 bits):
    - (M)etadata: 带有 Metadata 数据；
    - (F)ollows: 表示是否将数据分包(fragments),请求数据大于一个 Frame 长度时使用；
    - (C)omplete: 流结束标志位，如果设置，onComplete() 方法会被调用; 
    - (N)ext: 传递数据，如果设置，onNext(Payload) 方法会被调用;
- Payload Data: 数据

REQUEST_FNF, REQUEST_RESPONSE, REQUEST_STREAM 及 REQUEST_CHANNEL 定义比较类似，也相对简单，以 REQUEST_RESPONSE 为例：

```go
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           Stream ID                           |
+-----------+-+-+-+-------------+-------------------------------+
|Frame Type |0|M|F|     Flags   |
+-------------------------------+
                     Metadata & Request Data
```
- Frame Type: (6 bits) 0x04;
- Flags: (10 bits):
    - (M)etadata: 带有 Metadata 数据；
    - (F)ollows: 表示是否将数据分包(fragments),请求数据大于一个 Frame 长度时使用；
Request Data: 请求的数据

说完帧的格式，我们来看下 Requester 和 Responder 之间的通信流程，以 Request-Response 为例，先作以下约定：
> "RQ -> RS" refers to Requester sending a frame to a Responder. And "RS -> RQ" refers to Responder.
> "*" refers to 0 or more and "+" refers to 1 or more.

**Request-Response:**
```go
1. RQ -> RS: REQUEST_RESPONSE
2. RS -> RQ: PAYLOAD with COMPLETE
or

1. RQ -> RS: REQUEST_RESPONSE
2. RS -> RQ: ERROR[APPLICATION_ERROR|REJECTED|CANCELED|INVALID]
or

1. RQ -> RS: REQUEST_RESPONSE
2. RQ -> RS: CANCEL
```
有三种情况：
1. 请求正常，Requester 发送一个 REQUEST_RESPONSE 帧，Responder 响应一个带 COMPLETE 标志位的 PAYLOAD;
2. 请求出错，Requester 发送一个 REQUEST_RESPONSE 帧，Responder 响应一个 ERROR 帧，帧中带有错误码及错误信息；
3. 请求取消，Requester 发送一个 REQUEST_RESPONSE 帧，紧接着发送一个 CANCEL, 取消请求。

对于 Stream 的情况，则会发送多个 PAYLOAD 帧。

## 实例

### 引入依赖
```xml
<dependencies>
    <dependency>
        <groupId>io.rsocket</groupId>
        <artifactId>rsocket-core</artifactId>
        <version>0.11.13</version>
    </dependency>
    <dependency>
        <groupId>io.rsocket</groupId>
        <artifactId>rsocket-transport-netty</artifactId>
        <version>0.11.13</version>
    </dependency>
</dependencies>
```

实例底层的传输使用的是 TCP, 框架采用的是 Netty.

### 服务器端

```java
public interface RSocket extends Availability, Closeable {
 
    Mono<Void> fireAndForget(Payload payload);
 
    Mono<Payload> requestResponse(Payload payload);
 
    Flux<Payload> requestStream(Payload payload);
 
    Flux<Payload> requestChannel(Publisher<Payload> payloads);
 
    Mono<Void> metadataPush(Payload payload);
 
}
```

在服务端需要实现 RSocket 接口，并将其添加到服务器中。

```java
public Server() {
    // 初始化服务器，并向器添加服务实现 RSocketImpl
    this.server = RSocketFactory.receive()
            .acceptor((setupPayload, reactiveSocket) -> Mono.just(new RSocketImpl()))
            .transport(TcpServerTransport.create("localhost", TCP_PORT))
            .start()
            .doOnNext(x -> LOG.info("Server started"))
            .subscribe();

    initService();
}
```

服务端的 RSocketImpl 代码逻辑如下所示：
```java
/**
 * RSocket implementation
 */
private class RSocketImpl extends AbstractRSocket {

    /**
     * Handle Request/Response messages
     * 将请求数据返回给客户端
     * @param payload Message payload
     * @return payload response
     */
    @Override
    public Mono<Payload> requestResponse(Payload payload) {
        try {
            LOG.info("payload:{}", payload);
            return Mono.just(payload); // reflect the payload back to the sender
        } catch (Exception x) {
            return Mono.error(x);
        }
    }

    /**
     * Handle Fire-and-Forget messages
     * 将数据发布到 dataPublisher 中
     * @param payload Message payload
     * @return nothing
     */
    @Override
    public Mono<Void> fireAndForget(Payload payload) {
        try {
            dataPublisher.publish(payload); // forward the payload
            return Mono.empty();
        } catch (Exception x) {
            return Mono.error(x);
        }
    }

    /**
     * Handle Request/Stream messages. Each request returns a new stream.
     * 使用 dataPublisher 作为响应，数据来源自 fireAndForget 中的数据
     * @param payload Payload that can be used to determine which stream to return
     * @return Flux stream containing simulated measurement data
     */
    @Override
    public Flux<Payload> requestStream(Payload payload) {
        String streamName = payload.getDataUtf8();
        if (DATA_STREAM_NAME.equals(streamName)) {
            return Flux.from(dataPublisher);
        }
        return Flux.error(new IllegalArgumentException(streamName));
    }

    /**
     * Handle request for bidirectional channel
     *
     * @param payloads Stream of payloads delivered from the client
     * @return
     */
    @Override
    public Flux<Payload> requestChannel(Publisher<Payload> payloads) {
        Flux.from(payloads)
                .subscribe(gameController::processPayload);
        Flux<Payload> channel = Flux.from(gameController);
        return channel;
    }
}

/**
 * Simple PUblisher to provide async data to Flux stream
 */
public class DataPublisher implements Publisher<Payload> {

    private List<Subscriber<? super Payload>> subscribers = new ArrayList<>();

    @Override
    public void subscribe(Subscriber<? super Payload> subscriber) {
        this.subscribers.add(subscriber);
    }

    /**
     * 发布数据
     * @param payload 数据
     */
    public void publish(Payload payload) {

        subscribers.stream().forEach(subscriber -> subscriber.onNext(payload));
    }

    /**
     * 数据结束
     */
    public void complete() {

        subscribers.stream().forEach(subscriber -> subscriber.onComplete());
    }

}
```

### 客户端代码

**Fire-and-Forget**
客户端定时 50s 发送一次数据到服务器，不用服务器响应。
```java
/**
 * 客户端 socket
 */
private final RSocket socket;
private final List<Float> data;

/**
 * 构建客户端
 */
public FireNForgetClient() {
    this.socket = RSocketFactory.connect()
            .transport(TcpClientTransport.create("localhost", TCP_PORT))
            .start()
            .block();
    this.data = Collections.unmodifiableList(generateData());
}

/**
 * Send binary velocity (float) every 50ms
 */
public void sendData() {
    Flux.interval(Duration.ofMillis(50))
            .take(data.size())
            .map(this::createFloatPayload)
            .flatMap(socket::fireAndForget)
            .blockLast();
}
```

**Request-Response**
```java
/**
 * 发送一个字符串到服务器，并同步等待结果
 * @param string 参数
 * @return 结果
 */
public String callBlocking(String string) {
    return socket
            .requestResponse(DefaultPayload.create(string))
            .map(Payload::getDataUtf8)
            .onErrorReturn(ERROR_MSG)
            .block();
}
```

**Request-Stream**
```java
/**
 * 返回一个 Float 列表，一个响应一个 Float
 * @return Float 数字
 */
public Flux<Float> getDataStream() {
    return socket
            .requestStream(DefaultPayload.create(DATA_STREAM_NAME))
            .map(Payload::getData)
            .map(buf -> buf.getFloat())
            .onErrorReturn(null);
}
```

**Stream-Stream**
通过 GameController 类，既实现了数据在发送，也实现了数据的处理。
```java
/**
 * 客户端 socket
 */
private final RSocket socket;

/**
 * 发送流及处理流
 * 发送流：fireAtWill 方法，线程定时发送数据
 * 接收流：processPayload 方法，处理响应数据
 */
private final GameController gameController;

/**
 * 构建客户端
 */
public ChannelClient() {
    this.socket = RSocketFactory.connect()
            .transport(TcpClientTransport.create("localhost", TCP_PORT))
            .start()
            .block();

    this.gameController = new GameController("Client Player");
}

/**
 * 双向数据流
 */
public void playGame() {
    socket.requestChannel(Flux.from(gameController))
            .doOnNext(gameController::processPayload)
            .blockLast();
}

```

GameController 处理逻辑如下：

```java

public class GameController implements Publisher<Payload> {

    private static final Logger LOG = LoggerFactory.getLogger(GameController.class);

    private final String playerName;
    private final List<Long> shots;
    private Subscriber<? super Payload> subscriber;
    private boolean truce = false;

    public GameController(String playerName) {
        this.playerName = playerName;
        this.shots = generateShotList();
    }

    /**
     * Create a random list of time intervals, 0-1000ms
     *
     * @return List of time intervals
     */
    private List<Long> generateShotList() {
        return Flux.range(1, SHOT_COUNT)
                .map(x -> (long) Math.ceil(Math.random() * 1000))
                .collectList()
                .block();
    }

    @Override
    public void subscribe(Subscriber<? super Payload> subscriber) {
        this.subscriber = subscriber;
        fireAtWill();
    }

    /**
     * Publish game events asynchronously
     */
    private void fireAtWill() {
        new Thread(() -> {
            for (Long shotDelay : shots) {
                try { Thread.sleep(shotDelay); } catch (Exception x) {}
                if (truce) {
                    break;
                }
                LOG.info("{}: bang!", playerName);
                subscriber.onNext(DefaultPayload.create("bang!"));
            }
            if (!truce) {
                LOG.info("{}: I give up!", playerName);
                subscriber.onNext(DefaultPayload.create("I give up"));
            }
            subscriber.onComplete();
        }).start();
    }

    /**
     * Process events from the opponent
     *
     * @param payload Payload received from the rSocket
     */
    public void processPayload(Payload payload) {
        String message = payload.getDataUtf8();
        switch (message) {
            case "bang!":
                String result = Math.random() < 0.5 ? "Haha missed!" : "Ow!";
                LOG.info("{}: {}", playerName, result);
                break;
            case "I give up":
                truce = true;
                LOG.info("{}: OK, truce", playerName);
                break;
        }
    }
}
```

<strong>说明：</strong>
<font color="red">流的操作主要是通过 Publisher 类来实现的。</font>

### 测试代码

```java
@Test
public void whenSendingAString_thenRevceiveTheSameString() {
    ReqResClient client = new ReqResClient();
    String string = "Hello RSocket";

    assertEquals(string, client.callBlocking(string));

    client.dispose();
}

@Test
public void whenSendingFireForget() {
    FireNForgetClient fnfClient = new FireNForgetClient();

    // start sending the data
    List<Float> data = fnfClient.getData();
    data.stream().forEach(System.out::println);
    fnfClient.sendData();

    try {
        TimeUnit.SECONDS.sleep(10);
    } catch (InterruptedException ex) {
        ex.printStackTrace();
    }
}

/**
 * 1. 通过 FireNForgetClient 向服务器定时发送 Float 数据；
 * 2. 服务器接收数据，向 dataPublisher 发布数据；
 * 3. 通过 ReqStreamClient 向服务器请求流数据，数据来自 dataPublisher；
 * 4. ReqStreamClient 订阅来自服务器的数据并处理；
 * 5. 通过 dataPublisher 实现了将 FireNForgetClient 产生的数据发送给了 ReqStreamClient。
 */
@Test
public void whenSendingStream_thenReceiveTheSameStream() {
    // create the client that pushes data to the server and start sending
    FireNForgetClient fnfClient = new FireNForgetClient();
    // create a client to read a stream from the server and subscribe to events
    ReqStreamClient streamClient = new ReqStreamClient();

    // get the data that is used by the client
    List<Float> data = fnfClient.getData();
    // create a place to count the results
    List<Float> dataReceived = new ArrayList<>();

    // assert that the data received is the same as the data sent
    Disposable subscription = streamClient.getDataStream()
            .index()
            .subscribe(
                    tuple -> {
                        assertEquals("Wrong value", data.get(tuple.getT1().intValue()), tuple.getT2());
                        LOG.info("index:{},data:{}",tuple.getT1(),tuple.getT2());
                        dataReceived.add(tuple.getT2());
                    },
                    err -> LOG.error(err.getMessage())
            );

    // start sending the data
    fnfClient.sendData();

    // wait a short time for the data to complete then dispose everything
    try {
        Thread.sleep(5000);
    } catch (Exception x) {
    }
    subscription.dispose();
    fnfClient.dispose();

    // verify the item count
    assertEquals("Wrong data count received", data.size(), dataReceived.size());
}

@Test
public void whenRunningChannelGame_thenLogTheResults() {
    ChannelClient client = new ChannelClient();
    client.playGame();
    client.dispose();
}
```

## 总结
通过分析 RSocket 通信协议，我们理解了 RSocket 四种通信模型的基本原理，不过 RSocket 提供的功能不仅限于这些，它还提供了更多高级的功能，如文章开头介绍的那样。RSocket 官网提供了翔实的文档，如果感兴趣的话，可以深入理解下。

**参考：**

----
[1]:https://rsocket.io/
[2]:https://zhuanlan.zhihu.com/p/100511637
[3]:https://www.reactivemanifesto.org/zh-CN
[4]:https://www.baeldung.com/rsocket
[5]:https://projectreactor.io/docs/core/release/api/reactor/core/publisher/Flux.html
[6]:https://projectreactor.io/docs/core/release/api/reactor/core/publisher/Mono.html
[7]:https://medium.com/@b3rnoulli/reactive-service-to-service-communication-with-rsocket-introduction-5d64e5b6909
[8]:https://rsocket.io/about/protocol/
[9]:https://javakk.com/1820.html

[1. rsocket 官方文档][1]
[2. RSocket 基于消息传递的反应式应用层网络协议][2]
[3. 反应式宣言][3]
[4. Introduction to RSocket][4]
[5. Flux API][5]
[6. Mono API][6]
[7. Reactive service to service communication with RSocket — Introduction][7]
[8. Rsocket protocol][8]
[9. 响应式服务通信协议RSocket][9]