---
title: Alligator 系列：Protocol Buffer
date: 2021-10-17 15:11:22
tags:
- PB
- protocol bufffer
- ProtostuffUtils
categories:
- Alligator网关
---

## 1. 概述

在系统中，Protocol Buffer 的使用有两种方式：1）定义 .proto 文件，生成相应的 Bean 对象及序列化的代码；2）根据现有的 Java Bean 对象，动态生成对应的 schema, 使用工具类完成对象的序列化。这两种方式的优缺点也比较明显，.proto 文件支持向前、向后兼容，后者使用简单，引用工具类，便可支持序列化操作，缺点是存在代码兼容性问题。

<!-- more -->

<font color='red'>** 说明: **</font>
<font color='red'>这篇文章只是简单讲述两种方式的使用，详细的内容请参考官方文档。</font>

## 2. 定义 proto 文件

### 2.1 安装部署 Protocol Buffer 编译器

以 windows 环境为例，从官方下载 Protocol Buffer，如 protoc-3.18.1-win64.zip, 解压缩到指定目录，并将 bin 目录加到 Path 环境变量中即可。

```bash
SET PROTOC_HOME=D:\app\protoc-3.18.1-win64
SET PATH=%PAHTH%;%PROTOC_HOME%\bin

# 查看版本
C:\Users\Admin>protoc --version
libprotoc 3.18.1

```

<font color='red'>**下载地址:**</font>
[https://github.com/protocolbuffers/protobuf/releases/tag/v3.18.1](ttps://github.com/protocolbuffers/protobuf/releases/tag/v3.18.1)

### 2.2 定义 proto 文件

在官方的 addressbook.proto 文件基础上，添加了 map 对象的变量 people_map，在真实场景中，该对象可以通过 peoples 列表遍历得到，不需要传递 map 对象，否则会传输两份数据，在这里仅仅是演示作用。

```GO
// [START declaration]
syntax = "proto3";
package tutorial;

import "google/protobuf/timestamp.proto";
// [END declaration]

// [START java_declaration]
option java_multiple_files = true;
option java_package = "com.example.tutorial.protos";
option java_outer_classname = "AddressBookProtos";
// [END java_declaration]

// [START messages]
message Person {
  string name = 1;
  int32 id = 2;  // Unique ID number for this person.
  string email = 3;

  enum PhoneType {
    MOBILE = 0;
    HOME = 1;
    WORK = 2;
  }

  message PhoneNumber {
    string number = 1;
    PhoneType type = 2;
  }

  repeated PhoneNumber phones = 4;

  google.protobuf.Timestamp last_updated = 5;
  
}

// Our address book file.
message AddressBook {
  repeated Person peoples = 1;
  
  map<string, Person> people_map = 2;
}
// [END messages]
```
**说明：**
1. syntax: PB 版本，有 v2 和 v3 两个版本，值分别为 proto2 和 proto3;
2. package: 包名，表示命名空间，用于解决名称冲突，在 Java 中转换为 package 包名；
3. java_multiple_files：Java 申明，若为 true, 表示为每一个 message 生成独立的文件（嵌套的 message 除外）；
4. java_package：Java 申明，指定 Java 的 package 名称，它为覆盖 package 属性指定的包名；
5. java_outer_classname：Java 申明，指定输出的 Java 类名；
6. import：引入外部的 proto 文件；
7. message：定义一个消息，对应 Java 中的对象，message 可以嵌套定义；
8. enum：枚举对象，下标从 0 开始；
9. repeated：表示 0 或 n 个对象，可以定义数组对象；
10. map：map 对象；
11. optional：描述符，表示该字段为可选字段，如果没有设置的话，使用默认值，在 proto3 中已经取消 required 字段；
12. tag：如同 =1,字段在 message 中的惟一标示，在二进制编码中使用 tag 代表该字段，1~15 使用一个字节表示，处于优化的目的，常用的字段应该放在这个区域。

map 对象等同于如下的定义，它实际上就是一个包含 key 和 value 对象的数组。
```GO
message MapFieldEntry {
  key_type key = 1;
  value_type value = 2;
}

repeated MapFieldEntry map_field = N;
```

### 2.3 编译 proto 文件

```bash
protoc -I=. --java_out=. addressbookV2.proto
```
**说明：**
1. -I：指定 proto 文件所在的源目录；
2. --java_out：指定 Java 语言编译输出的目录；

生成的代码如下所示：
```bash
└─org
    └─noahsark
        └─tutorial
            └─protos
                    AddressBook.java
                    AddressBookOrBuilder.java
                    AddressBookProtos.java
                    Person.java
                    PersonOrBuilder.java
```

### 2.4 运行代码

将生成的的代码导入工程，引入 Protocol Buffer jar 包。
```xml
<dependency>
    <groupId>com.google.protobuf</groupId>
    <artifactId>protobuf-java</artifactId>
    <version>3.18.1</version>
</dependency>

```

**构造 AddressBook 对象并序列化数据**
```java
private static byte [] marshal() {
    // 构造 Person 对象
    Person john =
            Person.newBuilder()
                    .setId(1234)
                    .setName("John Doe")
                    .setEmail("jdoe@example.com")
                    .addPhones(
                            Person.PhoneNumber.newBuilder()
                                    .setNumber("555-4321")
                                    .setType(Person.PhoneType.HOME))
                    .build();

    // 构造 AddressBook 对象
    AddressBook addressBook = AddressBook.newBuilder()
            .addPeoples(john)
            .putPeopleMap(john.getName(),john).build();

    // 序列化 AddressBook 对象
    byte [] message = addressBook.toByteArray();

    return message;
}
```

**反序列化 AddressBook 对象**
```java
private static AddressBook unmarshal(byte [] message) throws InvalidProtocolBufferException {
    AddressBook addressBook = AddressBook.parseFrom(message);

    return addressBook;
}
```

**输出 AddressBook 对象**
```java
private static void listAddressBook(AddressBook addressBook) {
    for (Person person: addressBook.getPeoplesList()) {

        System.out.println("Person ID: " + person.getId());
        System.out.println("  Name: " + person.getName());
        System.out.println("  E-mail address: " + person.getEmail());

        for (Person.PhoneNumber phoneNumber : person.getPhonesList()) {
            switch (phoneNumber.getType()) {
                case MOBILE:
                    System.out.print("  Mobile phone #: ");
                    break;
                case HOME:
                    System.out.print("  Home phone #: ");
                    break;
                case WORK:
                    System.out.print("  Work phone #: ");
                    break;
            }
            System.out.println(phoneNumber.getNumber());
        }
    }
}
```

**使用 ProtocolBuffer 序列化及反序列化数据**
```java
public static void main(String[] args) throws InvalidProtocolBufferException {

    // 构造 AddressBook 对象并序列化数据
    byte [] message = marshal();

    // 反序列化 AddressBook 对象
    AddressBook addressBook = unmarshal(message);

    // 输出 AddressBook 对象
    listAddressBook(addressBook);

}
```

输出结果为：
```bash
Person ID: 1234
  Name: John Doe
  E-mail address: jdoe@example.com
  Home phone #: 555-4321
```

## 3. 运行时模式
在该种方式下，不用定义 .proto 文件，引入 protostuff 工具包，然后使用其提供的 API 便可对 Java 对象进行 ProtocolBuffer 序列化/反序列化操作。

### 3.1 引入 protostuff
在 maven pom 文件中加入如下依赖：

```xml
<!-- For the core formats (protostuff, protobuf, graph) -->
<dependency>
  <groupId>io.protostuff</groupId>
  <artifactId>protostuff-core</artifactId>
  <version>1.7.4</version>
</dependency>

<!-- For schemas generated at runtime -->
<dependency>
  <groupId>io.protostuff</groupId>
  <artifactId>protostuff-runtime</artifactId>
  <version>1.7.4</version>
</dependency>

```

### 3.2 定义 Java Bean 对象

```java
public class Person {
    private int id;
    private String name;
    private String email;
    private String mobile;

    ...
}

```

### 3.3 定义工具类
```java
public class ProtostuffUtils {

    /**
     * 避免每次序列化都重新申请 Buffer 空间
     */
    private static LinkedBuffer buffer = LinkedBuffer.allocate(LinkedBuffer.DEFAULT_BUFFER_SIZE);

    /**
     * 缓存 Schema
     */
    private static Map<Class<?>, Schema<?>> schemaCache = new ConcurrentHashMap<Class<?>, Schema<?>>();

    /**
     * 序列化方法，把指定对象序列化成字节数组
     * @param obj 序列化的对象
     * @param <T> 对象类型
     * @return 字节数组
     */
    @SuppressWarnings("unchecked")
    public static <T> byte[] serialize(T obj) {
        Class<T> clazz = (Class<T>) obj.getClass();
        Schema<T> schema = getSchema(clazz);
        byte[] data;
        try {
            data = ProtostuffIOUtil.toByteArray(obj, schema, buffer);
        } finally {
            buffer.clear();
        }
        return data;
    }

    /**
     * 反序列化方法，将字节数组反序列化成指定 Class 类型
     * @param data 字节数组
     * @param clazz 序列化对象的类型
     * @param <T> 对象类型
     * @return 反序列化后的对象
     */
    public static <T> T deserialize(byte[] data, Class<T> clazz) {
        Schema<T> schema = getSchema(clazz);
        T obj = schema.newMessage();
        ProtostuffIOUtil.mergeFrom(data, obj, schema);
        return obj;
    }

    @SuppressWarnings("unchecked")
    private static <T> Schema<T> getSchema(Class<T> clazz) {
        Schema<T> schema = (Schema<T>) schemaCache.get(clazz);
        if (schema == null) {
            schema = RuntimeSchema.getSchema(clazz);
            if (schema == null) {
                schemaCache.put(clazz, schema);
            }
        }
        return schema;
    }
}
```

### 3.4 测试代码
```java
public static void main(String[] args) {
    // 构造 Person 对象
    Person person = new Person();

    // Person 对象赋值
    person.setId(1);
    person.setName("john");
    person.setMobile("13845678912");
    person.setEmail("john@gmail.com");

    // 序列化数据
    byte [] message = ProtostuffUtils.serialize(person);

    // 反序列化数据
    Person john = ProtostuffUtils.deserialize(message, Person.class);

    // 输出 Person 对象数据
    System.out.println("person:\n" + john);

}

```
输出结果为：
```bash
person:
Person{id=1, name='john', email='john@gmail.com', mobile='13845678912'}
```

## 4. 总结

这两种方式不同的使用场景，如果后期不考虑代码的兼容问题，可以使用 protostuff 工具包，简单方便，如果代码迭代更新比较多，需要考虑不同版本的兼容问题，那最好定义合适的 .proto 文件来保证代码的兼容性。

</br>

**参考：**

----
[1]:https://developers.google.com/protocol-buffers/docs/javatutorial?hl=zh-CN
[2]:https://github.com/protocolbuffers/protobuf/releases/tag/v3.18.1
[3]:https://github.com/protostuff/protostuff
[4]:https://github.com/protocolbuffers/protobuf
[5]:https://zhuanlan.zhihu.com/p/78781763

[1. Protocol Buffer Basics: Java][1]

[2. Protocol Buffers v3.18.1][2]

[3. github:protostuff][3]

[4. github:protobuf][4]

[5. java序列化机制之protoStuff][5]
