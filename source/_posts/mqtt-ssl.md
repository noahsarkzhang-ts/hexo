---
title: Mqtt 系列：SSL
date: 2023-02-18 09:47:38
updated: 2023-02-18 09:47:38
tags:
- ssl
categories:
- MQTT
---

这篇文章讲述在 `Java` 中如何使用 `SSL` 进行通信。

<!-- more -->

## 基本概念

`SSL` 通信的目的是构建一个安全可靠的通信通道，它涉及到数据加解密、数字证书等知识。本文对加密算法，如对称加密、非对称加密及摘要算法不再赘述，只讲述与 `Java` 体系相关的知识点。

### KeyStore
`KeyStore`,一个存储密钥及证书的存储设备或数据库，它用于证明服务器及客户端身份。 KeyStore 的形态可以是一个文件，也可以是一个物理设备，它可以存储三种类型的条目，根据 `KeyStore` 类型的不同，存储的条目可能不一样。 
三种类型的条目如下：
- 私钥：存储非对称算法的私钥，处于安全的考虑，访问该条目，需要提供密码；
- 证书：证书包含一个公钥及签名，用于验证服务器或客户端的身份；
- 密钥：存储对称算法的加密密钥。

**1. KeyStore Alias**
在 `KeyStore` 中，每个条目都对应一个别名，这个别名惟一对应了一个条目。可以使用别名查询 `KeyStore` 的内容。

**2. KeyStore 类型**
根据存储的条目类型及存储方式，在 `Java` 中，`KeyStore` 有一些不同的类型：`JKS`, `JCEKS`, `PKCS12`, `PKCS11`, `DKS`.
- JKS: `Java Key Store` 的首字母简写，它的实现类是 `sun.security.provider.JavaKeyStore`. `JKS` 是与 `Java` 语言相关的 `KeyStore`，不能被其它语言使用。它可以存储私钥和证书，但不能存储对称密钥，另外，它的私钥在 `Java` 中不能被提取；
- JCEKS: `JCE key store(Java Cryptography Extension KeyStore)`, 它是 `JKS `的一个超集，包含了更多的算法支持，实现类是 `com.sun.crypto.provider.JceKeyStore`. `JCEKS` 可以存储私钥，证书和密钥三种类型的条目，它使用 `Triple DES` 加密算法对私钥存储进行了加强保护。`JCEKS` 由 `SunJCE` 提供，于 `Java 1.4` 版本中引入，在 `Java 1.4` 之前的版本中，只有 `JKS` 可用；
- PKCS12: 这是一种标准的 `KeyStore`，可以被 `Java` 或其它语言使用，它扩展了 `p12 or pfx`, 其实现类是 `sun.security.pkcs12.PKCS12KeyStore`. `PKCS12` 也可以存储三种类型的条目，不同于 `JKS`，它的私钥可以被其它语言如 C, C++ or C# 提取。另外，在 Java 9 版本之前默认的 `KeyStore` 是 `JKS`, Java 9 之后改为 `JCEKS`. 可以在 `$JRE/lib/security/java.security` 中查看默认的 `KeyStore`; 
- PKCS11: 它是一种硬件类型的 `KeyStore`, 它为 Java 库连接硬件 `KeyStore` 提供了一套接口，其实现类是 `sun.security.pkcs11.P11KeyStore`. 

### TrustKeyStore
`TrustKeyStore`, 专门存储受信任的证书条目的 `KeyStore`. Java 自带了一个 `TrustKeyStore cacerts`, 它位于 `$JAVA_HOME/jre/lib/security` 目录下，包含了默认的受信任的证书。不过，可以通过 `javax.net.ssl.trustStore` 属性覆盖默认的 `TrustKeyStore`，也可以通过 `javax.net.ssl.trustStorePassword` 和 `javax.net.ssl.trustStoreType` 属性指定其密码和类型。  

**说明：**
在程序中，存放私钥、己方证书的 `KeyStore` 和存放第三方证书的 `TrustKeyStore` 可以是同一个。

### 证书类型
常用的证书包括如下类型:
- DER,CER：文件是二进制格式，只保存证书，不保存私钥，用于 Java 和 Windows 服务器中；
- PEM：一般是文本格式，可保存证书和私钥，分别使用两个文件保存，用于 Nginx 或 Apache 中；
- CRT: 文件可以是二进制格式，也可以是文本格式，与 DER 格式相同，不保存私钥；
- PFX P12: 文件是二进制格式，同时包含证书和私钥，一般有密码保护，用于 Java 语言或 Windows IIS 中；
- JKS: 二进制格式，同时包含证书和私钥，一般有密码保护，用于 Java 语言。

### keytool
`keytool` 是 `JDK` 提供的一个管理 `KeyStore` 工具，常用的命令包括：
- genkeypair: 生成非对称算法的公私钥密码对；
- exportcert: 导出证书；
- importcert: 导入证书；
- printcertreq: 打印输出证书；
- list: 列出 `KeyStore` 内容。

**1. genkeypair 参数**
```bash
-v: 输出详细日志；
-alias: 指定别名；
-keyalg：指定算法；
-keystore：指定 keystore 的文件名字；
-dname: 指定参数内容，CN:证书域名或IP,OU:组织单位；O:组织名称；L:地址；ST:省市；C:国家；
-storepass: KeyStore 密码；
-keypass: 访问 key 的密码；
-storetype: KeyStore 类型，如：jks,jceks,pkcs12.
```

> For the -keypass option, if you do not specify the option on the command line, then the keytool command first attempts to use the keystore password to recover the private/secret key. If this attempt fails, then the keytool command prompts you for the private/secret key password.

实例：
```bash
$ keytool -genkeypair -v -alias mqtt-broker -keyalg RSA -keystore ./server_ks -dname "CN=localhost,OU=cn,O=cn,L=cn,ST=cn,C=cn" -storepass 123456 -keypass 123456 
```

**2. exportcert 参数**
```bash
-v: 输出详细日志；
-alias: 指定别名；
-keystore：指定 keystore 的文件名字；
-storepass: KeyStore 密码；
-file: 指定证书名称。
```

实例：
```bash
$ keytool -exportcert -v -alias mqtt-broker -keystore ./server_ks -storepass 123456 -file server_key.cer
```

**3. importcert 参数**
```bash
-trustcacerts: 指定条目类型为“受信任的证书类型”；
-v: 输出详细日志；
-alias: 指定别名；
-keystore：指定 keystore 的文件名字；
-storepass: KeyStore 密码；
-file: 指定证书名称。
```

实例：
```bash
$ keytool -importcert -trustcacerts -v -alias mqtt-broker -file ./server_key.cer -storepass 123456 -keystore ./client_ks
```

**4. printcertreq 参数**
```bash
-v: 输出详细日志；
-file: 指定证书名称。
```

实例：
```bash
$ keytool -printcertreq -v -file server_key.cer
```

**5. list 参数**
```bash
-v: 输出详细日志；
-keystore：指定 keystore 的文件名字；
-storepass: KeyStore 密码；
-storetype: KeyStore 类型，如：jks,jceks,pkcs12.
```

实例：
```bash
$ keytool -list -v -keystore ./server_ks -storepass 123456 -storetype jks
```

详细命令参数可参见[keytool官方文档](https://docs.oracle.com/javase/8/docs/technotes/tools/unix/keytool.html).

## 双向认证实例

现在有这样一个场景，Client 和 Server 通过 SSL 通信且需要双向认证，双向认证是指 Client 和 Server 两端都要验证对方的证书。完成这个场景需要如下步骤（使用自签名证书）：
1. 生成 Client 和 Server 端公私钥对；
2. 导出各自的证书，并导入到对方的 `TrustKeyStore` 中；
3. 将 `KeyStore` 加载到程序中，初始化 `SSLContext` 对象，并生成对应的 `Socket` 对象，完成通信。

### 生成公私密钥

使用 `keytool -genkeypair` 生成 Client 和 Server 端公私钥对，别名分别是 `mqtt-broker` 和 `mqtt-client`, 域名使用 `localhost`.

```bash
# Server 端
$ keytool -genkeypair -v -alias mqtt-broker -keyalg RSA -keystore ./server_ks -dname "CN=localhost,OU=cn,O=cn,L=cn,ST=cn,C=cn" -storepass 123456 -keypass 123456 

# Client 端
$ keytool -genkeypair -v -alias mqtt-client -keyalg RSA -keystore ./client_ks -dname "CN=localhost,OU=cn,O=cn,L=cn,ST=cn,C=cn" -storepass 123456 -keypass 123456 
```

### 导出证书

Server 和 Client 端各自使用一个 `KeyStore` 来存放私钥、己方证书和第三方证书。

```bash
# 导出 Server 端证书
$ keytool -exportcert -v -alias mqtt-broker -keystore ./server_ks -storepass 123456 -file server_key.cer

# 将 Server 端证书导入到 Client 端
$ keytool -importcert -trustcacerts -v -alias mqtt-broker -file ./server_key.cer -storepass 123456 -keystore ./client_ks

# 导出 Client 端证书
$ keytool -exportcert -v -alias mqtt-client -keystore ./client_ks -storepass 123456 -file client_key.cer

# 将 Client 端证书导入到 Server 端
$ keytool -importcert -trustcacerts -v -alias mqtt-client -file ./client_key.cer -storepass 123456 -keystore ./server_ks
```

查看 Server 端 `KeyStore` 文件 `server_ks`, 它存储有两个条目，一个是别名为 `mqtt-client` 类型为 `trustedCertEntry` 的条目，它是导入的 client 端证书，还有一个别名为 `mqtt-broker` 类型为 `PrivateKeyEntry`的条目，它便是 Server 端的私钥。

```bash
$ keytool -list -v -keystore ./server_ks -storepass 123456
密钥库类型: JKS
密钥库提供方: SUN

您的密钥库包含 2 个条目

别名: mqtt-client
创建日期: 2023-2-14
条目类型: trustedCertEntry

所有者: CN=localhost, OU=cn, O=cn, L=cn, ST=cn, C=cn
发布者: CN=localhost, OU=cn, O=cn, L=cn, ST=cn, C=cn
序列号: 5ef6921
有效期为 Tue Feb 14 18:39:33 CST 2023 至 Mon May 15 18:39:33 CST 2023
证书指纹:
         MD5:  BA:76:3A:7D:0B:A2:02:E2:B6:A3:05:09:BE:79:46:4C
         SHA1: DE:6C:CF:01:A3:77:BE:96:D8:CE:A1:BE:A4:01:F7:5C:97:52:2C:B1
         SHA256: FC:E4:B2:A0:DF:AF:3F:D9:4B:A3:B0:19:8C:A5:14:6E:F2:74:B7:D1:25:1C:A7:CB:55:8A:4B:89:C1:9B:32:79
签名算法名称: SHA256withRSA
主体公共密钥算法: 2048 位 RSA 密钥
版本: 3

扩展: 

#1: ObjectId: 2.5.29.14 Criticality=false
SubjectKeyIdentifier [
KeyIdentifier [
0000: 42 7B F8 B7 18 5D 7E 83   F1 A6 90 67 5A 56 40 16  B....].....gZV@.
0010: B9 2B D2 AD                                        .+..
]
]

*******************************************
*******************************************

别名: mqtt-broker
创建日期: 2023-2-14
条目类型: PrivateKeyEntry
证书链长度: 1
证书[1]:
所有者: CN=localhost, OU=cn, O=cn, L=cn, ST=cn, C=cn
发布者: CN=localhost, OU=cn, O=cn, L=cn, ST=cn, C=cn
序列号: 5478e954
有效期为 Tue Feb 14 18:37:31 CST 2023 至 Mon May 15 18:37:31 CST 2023
证书指纹:
         MD5:  83:AF:24:AF:E4:B6:57:9B:9B:C9:53:7F:35:83:25:DF
         SHA1: 36:FF:46:E2:87:C3:AF:47:D2:C6:AE:92:08:4D:1E:F9:7D:A2:DD:83
         SHA256: 77:3A:A6:CF:E2:21:E9:B5:54:8D:E1:68:0F:FF:14:66:EE:4D:29:99:0D:44:50:12:B8:C7:EA:6A:8A:C6:63:A8
签名算法名称: SHA256withRSA
主体公共密钥算法: 2048 位 RSA 密钥
版本: 3

扩展: 

#1: ObjectId: 2.5.29.14 Criticality=false
SubjectKeyIdentifier [
KeyIdentifier [
0000: 75 F7 A3 B9 F8 EA C1 89   00 43 66 2B 03 E6 B9 A4  u........Cf+....
0010: 4C 6D 05 74                                        Lm.t
]
]

*******************************************
*******************************************

```

### 初始化 SSLContext 对象

将生成的 `KeyStore` 加载到程序中，生成 SSLContext 对象

```java
String keyStoreFile = "E:\\lab\\bell-labs\\ssl-lab\\src\\main\\resources\\cert\\server_ks";
String keyStorePwd = "123456";
String keyPwd = "123456";
String trustKeyStoreFile = "E:\\lab\\bell-labs\\ssl-lab\\src\\main\\resources\\cert\\server_ks";
String trustKeyStorePwd = "123456";

// 加载 KeyStore
KeyStore serverKeyStore = KeyStore.getInstance("JKS");
serverKeyStore.load(new FileInputStream(keyStoreFile), keyStorePwd.toCharArray());

// 加载 TrustKeyStore
KeyStore serverTrustKeyStore = KeyStore.getInstance("JKS");
serverTrustKeyStore.load(new FileInputStream(trustKeyStoreFile), trustKeyStorePwd.toCharArray());

// 初始化私钥管理器，使用 keypass
KeyManagerFactory kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
kmf.init(serverKeyStore, keyPwd.toCharArray());

// 初始化 TrustManagerFactory
TrustManagerFactory tmf = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
tmf.init(serverTrustKeyStore);

// 指定协议，并使用 KeyManagerFactory 和 TrustManagerFactory 初始化 SSLContext 对象
SSLContext sslContext = SSLContext.getInstance("TLSv1");
sslContext.init(kmf.getKeyManagers(), tmf.getTrustManagers(), null);
```

不同 JDK 版本支持的 SSL 协议可能不一样，可以通过以下代码查看支持的协议。
```java
System.out.println("Suported SSL Protocols : " + String.join(" ",
                    SSLContext.getDefault().getSupportedSSLParameters().getProtocols()));
```

在 Win10 系统 JDK 8 的环境下，支持的协议为：`SSLv2Hello SSLv3 TLSv1 TLSv1.1 TLSv1.2`.

### 生成 Socket 对象
使用 SSLContext 对象生成 Server 和 Client 端 Socket 对象。
```java
// 生成 Server 端 ServerSocket 对象
SSLServerSocketFactory sslServerSocketFactory = sslContext.getServerSocketFactory();
SSLServerSocket sslServerSocket = (SSLServerSocket) sslServerSocketFactory.createServerSocket(1883);
sslServerSocket.setNeedClientAuth(true);

// 生成 Client 端 Socket 对象
SSLSocketFactory socketFactory = sslContext.getSocketFactory();
Socket socket = socketFactory.createSocket("localhost", 1883);
```

### 输出 SSL 日志
在开发阶段，通过设置 `javax.net.debug` 参数输出 SSL 相关的日志，方便定位问题。

```java
System.setProperty("javax.net.debug", "ssl,handshake");
```

## 总结
通过上面的描述，可以知道在 `Java` 代码中引入 SSL 的步骤。不过，在 Tomcat 或 Jetty 容器中，或在 Spingboot 框架中引入 SSL 无需那么复杂，它们已经封装了这些步骤，只需要配置 `KeyStore` 文件位置和访问密码即可。

**参考：**

----
[1]:https://docs.oracle.com/javase/8/docs/technotes/tools/unix/keytool.html
[2]:https://www.baeldung.com/java-keystore-truststore-difference
[3]:https://osswangxining.github.io/java-tls/
[4]:https://www.pixelstech.net/article/1408345768-Different-types-of-keystore-in-Java----Overview

[1. keytool][1]
[2. Difference Between a Java Keystore and a Truststore][2]
[3. Java-JSSE-SSL/TLS编程代码实例-双向认证][3]
[4. Different types of keystore in Java -- Overview][4]