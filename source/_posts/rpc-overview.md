---
title: RPC：RPC 概述
date: 2021-11-07 20:04:33
tags:
- rpc
- send-oneway
- request-response
- request-stream
- stream-response
- stream-stream
categories:
- RPC
---

这篇文章是 RPC 系列的第一篇，打算写一个系列的文章，简单介绍下 Duboo2, Dubbo3, gRPC 及 RScoket 的使用方法及差异。在 Alligator 项目中借鉴了其中的一些思想，基于 TCP, Websocket 及 MQ，实现了一个简单的 RPC。RPC 涉及到内容比较多，这里选取了两个方面做为切入点：1）通信模式，包括 request-response, request-stream, stream-response, stream-stream, send-oneway; 2）协议，主要是协议字段，通过这些字段可以大概猜测出其实现方式。

<!-- more -->

## 一句话 RPC
Wikipedia 对 RPC 的解释：
> In distributed computing, a remote procedure call (RPC) is when a computer program causes a procedure (subroutine) to execute in a different address space (commonly on another computer on a shared network), which is coded as if it were a normal (local) procedure call, without the programmer explicitly coding the details for the remote interaction. 

这里有几个重点：
1. RPC 调用通常是不同进程间的调用，而这些进程一般通过网络进行连接；
2. 对上层应用而言，本地调用与远程调用在使用方式上没有差异；
3. RPC 封装了底层通信的细节，不需要开发人员显示地编码。

下面以一个例子说明：

**接口定义：**
```
public interface HelloService {
    String sayHello(String message);
}
```

**客户端：**

```java
public class HelloClient {

    public static void main(String[] args) {
        HelloService helloService = getProxy(HelloService.class,"127.0.0.1",10240);
        String result = helloService.sayHello("hi, charles");

        System.out.println("result = " + result);
    }

    public static  <T> T getProxy(Class<T> interfaceClass, String host, int port){
        return (T) Proxy.newProxyInstance(interfaceClass.getClassLoader(),
                new Class<?>[] {interfaceClass},
                new InvocationHandler() {

                    public Object invoke(Object proxy, Method method, Object[]
                            arguments) throws Throwable {
                        Socket socket = new Socket(host, port);
                        ObjectOutputStream output = new ObjectOutputStream(socket.getOutputStream());

                        output.writeUTF(method.getName());
                        output.writeObject(method.getParameterTypes());
                        output.writeObject(arguments);

                        ObjectInputStream input = new
                                ObjectInputStream(socket.getInputStream());

                        return input.readObject();}
                });
    }
}

```

在客户端为接口生成一个代理，并将方法名及参数序列化之后，通过一定的协议发送给服务器，最后同步读取服务端返回的数据作为方法的响应。

**服务器：**

```java
// 接口实现类
public class HelloServiceImpl implements HelloService {
    @Override
    public String sayHello(String message) {
        return message;
    }
}

// 服务器
public class HelloServer {

    public static void main(String[] args) {

        int port = 10240;
        HelloService service = new HelloServiceImpl();

        System.out.println("server startup...");
        try {
            ServerSocket server = new ServerSocket(port);
            for (; ; ) {
                final Socket socket = server.accept();
                new Thread(() -> {
                    try {
                        ObjectInputStream input = new ObjectInputStream(socket.getInputStream());

                        String methodName = input.readUTF();
                        Class<?>[] parameterTypes = (Class<?>[]) input.readObject();
                        Object[] arguments = (Object[]) input.readObject();

                        System.out.println("receive request:");
                        System.out.println("method:" + methodName);

                        ObjectOutputStream output = new ObjectOutputStream(socket.getOutputStream());
                        Method method = service.getClass().getMethod(methodName,parameterTypes);

                        Object result = method.invoke(service, arguments);
                        System.out.println("result = " + result);

                        output.writeObject(result);
                    } catch (Exception ex) {
                        ex.printStackTrace();
                    }
                }).start();
            }
        } catch (IOException ex) {
            ex.printStackTrace();
        }
    }

}

```
在服务端实现接口，监听网络的请求，按照协议，反序列化方法名及参数，并通过反射的方式映射到具体的接口实现，转换为本地方法调用，调用结束之后，再将结果返回给客户端。

一句话总结：RPC 就是一种网络编程技术，结合代理、序列化/反序列技术，通过一定的通信协议，实现类似本地方法调用的功能。

## 通信模式
RPC 一般有如下五种通信模式。
### Send-Oneway
特点：只发送请求数据，服务器不需要响应，适用于发送一些不关键的数据，如日志上报。
![send-oneway](/images/rpc/send-oneway.jpg "send-oneway")

### Request-Response
特点：最常见的模式，客户端发送一个请求，服务器响应一个结果。
![unary-rpc](/images/rpc/unary-rpc.jpg "unary-rpc")

### Reqeust-Stream
特点：发送一个请求，可以返回多个响应结果。
![request-stream-rpc](/images/rpc/request-stream-rpc.jpg "request-stream-rpc")

### Stream-Response
特点：发送多个请求，响应一个结果。
![stream-response-rpc](/images/rpc/stream-response-rpc.jpg "stream-response-rpc")

### Stream-Stream
特点：双向流的模式，客户端及服务器都向对方发送多个数据，互不干扰。
![stream-stream-rpc](/images/rpc/send-oneway.jpg "stream-stream-rpc")

## 总结
一个完整的 RPC 流程包括三个步骤：
1. 定义接口：可以使用中间语言，也可以使用特定的语言定义，如 JAVA；
2. 生成客户端代理：根据接口定义，通过代码生成客户端代理，它封装了向服务端请求的代码；
3. 编写服务器接口实现：生成服务器通信代码及编写接口的实现。

一个 RPC 框架通常提供代码生成的功能，客户端代理、服务器通信功能、序列化/反序列化的代码都会生成，开发者只需要编写接口定义及接口实现即可。


