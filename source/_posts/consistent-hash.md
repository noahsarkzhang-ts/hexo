---
title: 一致性哈希算法
date: 2019-11-07 18:04:49
tags:
- 一致性哈希算法
- 哈希算法
categories:
- 数据结构与算法
---

## 1. 解决的问题
在分布式服务中，往往有这样的场景：将某个用户或某台机器的请求负载路由到固定的某台服务器上。简单的做法直接是使用哈希算法，**h = hash(key) % N** ，该算法的核心思想是：将服务器编号，使用哈希算法取根据某类请求参数key（用户id或IP）计算出一个哈希值，再对该哈希值用服务器数据N进行取余（%）操作，从而得到服务器编号。使用该算法有一个问题，就是服务器数据数目（N）增加中或减少的时候，h的值都会被改变，即请求会负载到新的服务器上，有可能会导致状态数据的失效。有没有一种算法，既可以将同一请求负载到同一台服务器上，又可以在服务器增加或减少的时候将请求的变更控制在一定的范围内，所以提出了一致性哈希算法。

一致性哈希算法（Consistent Hashing）最早在论文《Consistent Hashing and Random Trees: Distributed Caching Protocols for Relieving Hot Spots on the World Wide Web》中被提出，其原理如下：
> 一致性哈希算法将整个哈希值（整数）空间组织成一个0~2^32-1的虚拟哈希环，首先，服务器按照名称（或编号）取哈希，并将该哈希值放置在哈希环上，然后再对key取哈希，按照随时针方向查找离该值最近的服务器结点哈希值，从而完成key与服务器的匹配映射工作。

通过一致性哈希算法，服务器的增加或减少只会影响该服务器周围的请求，不会扩大到整个哈希环，从而保证算法的可扩展性。

一致性哈希算法也有一个问题，就是服务器较少时，可能出现服务器之间负载的请求可能不均衡，有些服务器负载的请求可能过多，而有些服务负载较少。解决这个问题的关键是增加哈希环上服务节点的数量，在物理服务器不能增加的情况下，可以将一个服务结点映射为多个虚拟结点，均匀分布在哈希环上，从而解决该问题。

<!-- more -->

## 2. 哈希算法
在一致性哈希算法中，哈希算法是一个重要的组成部分，它将服务器结点和请求字符串转换为一个整数，如何选择一个好的哈希算法？评判一个哈希算法的标准是什么？

哈希算法大致有两种类型：加密哈希算法和非加密哈希算法，加密哈希算法为了防止攻击者找出碰撞而设计的，它的速度较慢。非加密哈希算法将字符串作为输入，通过计算输出一个整数，理想的哈希算法有一个特性：输出非常均匀分布在可能的输出域，特别是当输入非常相似的时候。可以将哈希算法大致分为三代：
- 第一代：SHA-1（1993），MD5（1992），CRC（1975），Lookup3（2006）
- 第二代：MurmurHash（2008）
- 第三代：CityHash， SpookyHash（2011）

其中SHA-1和MD5属于非加密哈希算法，其它都是非加密哈希算法，在一致性哈希算法中，主要用的是非加密哈希算法。除了以上的算法，还有一些算法没有列出，如JDK中hashCode使用的算法，另外，还有专门针对一致性哈希算法设计的哈希算法，如Ketama，也得到了广泛的运用。

在一致性哈希算法的使用场景中，有几个比较重要的算法，单独说明一下：
- MurmurHash 算法：高运算性能，低碰撞率，由 Austin Appleby 创建于 2008 年，现已应用到 Hadoop、libstdc++、nginx、libmemcached 等开源系统。2011 年 Appleby被Google雇佣，随后Google推出其变种的CityHash算法。官方只提供了C语言的实现版本。Java体系中，Guava，Redis，Memcached，Cassandra，HBase，Lucene都在使用它。
- FNV算法：全名为Fowler-Noll-Vo算法，是以三位发明人Glenn Fowler，Landon Curt Noll，Phong Vo 的名字来命名的，最早在 1991 年提出。特点和用途：FNV 能快速 hash 大量数据并保持较小的冲突率，它的高度分散使它适用于hash一些非常相近的字符串，比如URL，hostname，文件名，text，IP 地址等。
- Ketama 算法：Ketama不仅提供了一个哈希算法，更是提供了一套一致性哈希算法的实现，在Dubbo及Memcached中使用了该算法。

下面针对这些算法，作一一介绍：

1）Java 字符串哈希算法
```java
public int hashCode() {
    int h = hash;
    if (h == 0 && value.length > 0) {
        char val[] = value;

        for (int i = 0; i < value.length; i++) {
            h = 31 * h + val[i];
        }
        hash = h;
    }
    return h;
}

```
Java字符串哈希算法是遍历整个字符串，按照hash \* 31 + c的算法计算，最后的哈希值为s[0] \*31^(n-1) + s[1]\*31^(n-2) + ... + s[n-1]。

2）CRC 哈希算法
```java
public class CRCHashStrategy implements HashStrategy {

    private static final int LOOKUP_TABLE[] = {0x0000, 0x1021, 0x2042, 0x3063,
            0x4084, 0x50A5, 0x60C6, 0x70E7, 0x8108, 0x9129, 0xA14A, 0xB16B,
            0xC18C, 0xD1AD, 0xE1CE, 0xF1EF, 0x1231, 0x0210, 0x3273, 0x2252,
            0x52B5, 0x4294, 0x72F7, 0x62D6, 0x9339, 0x8318, 0xB37B, 0xA35A,
            0xD3BD, 0xC39C, 0xF3FF, 0xE3DE, 0x2462, 0x3443, 0x0420, 0x1401,
            0x64E6, 0x74C7, 0x44A4, 0x5485, 0xA56A, 0xB54B, 0x8528, 0x9509,
            0xE5EE, 0xF5CF, 0xC5AC, 0xD58D, 0x3653, 0x2672, 0x1611, 0x0630,
            0x76D7, 0x66F6, 0x5695, 0x46B4, 0xB75B, 0xA77A, 0x9719, 0x8738,
            0xF7DF, 0xE7FE, 0xD79D, 0xC7BC, 0x48C4, 0x58E5, 0x6886, 0x78A7,
            0x0840, 0x1861, 0x2802, 0x3823, 0xC9CC, 0xD9ED, 0xE98E, 0xF9AF,
            0x8948, 0x9969, 0xA90A, 0xB92B, 0x5AF5, 0x4AD4, 0x7AB7, 0x6A96,
            0x1A71, 0x0A50, 0x3A33, 0x2A12, 0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E,
            0x9B79, 0x8B58, 0xBB3B, 0xAB1A, 0x6CA6, 0x7C87, 0x4CE4, 0x5CC5,
            0x2C22, 0x3C03, 0x0C60, 0x1C41, 0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD,
            0xAD2A, 0xBD0B, 0x8D68, 0x9D49, 0x7E97, 0x6EB6, 0x5ED5, 0x4EF4,
            0x3E13, 0x2E32, 0x1E51, 0x0E70, 0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC,
            0xBF1B, 0xAF3A, 0x9F59, 0x8F78, 0x9188, 0x81A9, 0xB1CA, 0xA1EB,
            0xD10C, 0xC12D, 0xF14E, 0xE16F, 0x1080, 0x00A1, 0x30C2, 0x20E3,
            0x5004, 0x4025, 0x7046, 0x6067, 0x83B9, 0x9398, 0xA3FB, 0xB3DA,
            0xC33D, 0xD31C, 0xE37F, 0xF35E, 0x02B1, 0x1290, 0x22F3, 0x32D2,
            0x4235, 0x5214, 0x6277, 0x7256, 0xB5EA, 0xA5CB, 0x95A8, 0x8589,
            0xF56E, 0xE54F, 0xD52C, 0xC50D, 0x34E2, 0x24C3, 0x14A0, 0x0481,
            0x7466, 0x6447, 0x5424, 0x4405, 0xA7DB, 0xB7FA, 0x8799, 0x97B8,
            0xE75F, 0xF77E, 0xC71D, 0xD73C, 0x26D3, 0x36F2, 0x0691, 0x16B0,
            0x6657, 0x7676, 0x4615, 0x5634, 0xD94C, 0xC96D, 0xF90E, 0xE92F,
            0x99C8, 0x89E9, 0xB98A, 0xA9AB, 0x5844, 0x4865, 0x7806, 0x6827,
            0x18C0, 0x08E1, 0x3882, 0x28A3, 0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E,
            0x8BF9, 0x9BD8, 0xABBB, 0xBB9A, 0x4A75, 0x5A54, 0x6A37, 0x7A16,
            0x0AF1, 0x1AD0, 0x2AB3, 0x3A92, 0xFD2E, 0xED0F, 0xDD6C, 0xCD4D,
            0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9, 0x7C26, 0x6C07, 0x5C64, 0x4C45,
            0x3CA2, 0x2C83, 0x1CE0, 0x0CC1, 0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C,
            0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8, 0x6E17, 0x7E36, 0x4E55, 0x5E74,
            0x2E93, 0x3EB2, 0x0ED1, 0x1EF0,};

    /**
     * Create a CRC16 checksum from the bytes. implementation is from
     * mp911de/lettuce, modified with some more optimizations
     *
     * @param bytes
     * @return CRC16 as integer value
     */
    public static int getCRC16(byte[] bytes) {
        int crc = 0x0000;

        for (byte b : bytes) {
            crc = ((crc << 8) ^ LOOKUP_TABLE[((crc >>> 8) ^ (b & 0xFF)) & 0xFF]);
        }
        return crc & 0xFFFF;
    }

    public static int getCRC16(String key) {
        return getCRC16(key.getBytes(Charset.forName("UTF-8")));
    }

    @Override
    public int getHashCode(String origin) {
        // optimization with modulo operator with power of 2
        // equivalent to getCRC16(key) % 16384
        return getCRC16(origin) & (16384 - 1);
    }
}

```

3）FNV1_32 算法
```java
public class FnvHashStrategy implements HashStrategy {

    private static final long FNV_32_INIT = 2166136261L;
    private static final int FNV_32_PRIME = 16777619;

    @Override
    public int getHashCode(String origin) {
        final int p = FNV_32_PRIME;
        int hash = (int) FNV_32_INIT;
        for (int i = 0; i < origin.length(); i++)
            hash = (hash ^ origin.charAt(i)) * p;
        hash += hash << 13;
        hash ^= hash >> 7;
        hash += hash << 3;
        hash ^= hash >> 17;
        hash += hash << 5;
        hash = Math.abs(hash);
        return hash;
    }
}
```

4）MurmurHash 算法
```java
public class MurmurHashStrategy implements HashStrategy {
    @Override
    public int getHashCode(String origin) {

        ByteBuffer buf = ByteBuffer.wrap(origin.getBytes());
        int seed = 0x1234ABCD;

        ByteOrder byteOrder = buf.order();
        buf.order(ByteOrder.LITTLE_ENDIAN);

        long m = 0xc6a4a7935bd1e995L;
        int r = 47;

        long h = seed ^ (buf.remaining() * m);

        long k;
        while (buf.remaining() >= 8) {
            k = buf.getLong();

            k *= m;
            k ^= k >>> r;
            k *= m;

            h ^= k;
            h *= m;
        }

        if (buf.remaining() > 0) {
            ByteBuffer finish = ByteBuffer.allocate(8).order(
                    ByteOrder.LITTLE_ENDIAN);
            // for big-endian version, do this first:
            // finish.position(8-buf.remaining());
            finish.put(buf).rewind();
            h ^= finish.getLong();
            h *= m;
        }
        h ^= h >>> r;
        h *= m;
        h ^= h >>> r;

        buf.order(byteOrder);
        return (int) (h & 0xffffffffL);
    }
}
```
5）Ketama 算法
```java
public class KetamaHashStrategy implements HashStrategy {

    private static MessageDigest md5Digest;

    static {
        try {
            md5Digest = MessageDigest.getInstance("MD5");
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("MD5 not supported", e);
        }
    }

    @Override
    public int getHashCode(String origin) {
        byte[] bKey = computeMd5(origin);
        long rv = ((long) (bKey[3] & 0xFF) << 24)
                | ((long) (bKey[2] & 0xFF) << 16)
                | ((long) (bKey[1] & 0xFF) << 8)
                | (bKey[0] & 0xFF);
        return (int) (rv & 0xffffffffL);
    }

    /**
     * Get the md5 of the given key.
     */
    public static byte[] computeMd5(String k) {
        MessageDigest md5;
        try {
            md5 = (MessageDigest) md5Digest.clone();
        } catch (CloneNotSupportedException e) {
            throw new RuntimeException("clone of MD5 not supported", e);
        }
        md5.update(k.getBytes());
        return md5.digest();
    }
}
```
相对来说，在一致性哈希算法中，FNV，MurmurHash及Ketama是相对较好的算法，用的场景也较多。

## 3. 算法分析
在一致性算法中，需要将哈希值空间组织成一个虚拟的哈希环，服务器结点的哈希值放置在该哈希环上，查找离请求key的哈希值最近的值。在这里提到要构建一个哈希环，它的底层数据结构是什么样的？我们可以转换一个思路，在算法中，最重要的环节是匹配两个最近的哈希值，是否可以将服务器的哈希值存储到一个有序的数据列表中，匹配的操作就是找一个小于等待key的最大值。为了提高查询效率，底层的数据结构一般使用红黑树。下面分析一致性哈希算法的一种可能实现，该算法由作者[徐靖峰][2]实现，代码的github地址：<https://github.com/lexburner/consistent-hash-algorithm>

```java
public class ConsistentHashLoadBalancer implements LoadBalancer{

    /**
     *  使用的哈希算法
     */
    private HashStrategy hashStrategy = new FnvHashStrategy();

    /**
     *  虚拟结点的个数
     */
    private final static int VIRTUAL_NODE_SIZE = 10;

    /**
     *  服务器与虚拟结点的连接符
     */
    private final static String VIRTUAL_NODE_SUFFIX = "&&";

    /**
     * 根据请求匹配服务器
     * @param servers 服务器数组
     * @param invocation 封装了调用的请求
     * @return 返回匹配的值
     */
    @Override
    public Server select(List<Server> servers, Invocation invocation) {
        int invocationHashCode = hashStrategy.getHashCode(invocation.getHashKey());
        TreeMap<Integer, Server> ring = buildConsistentHashRing(servers);
        Server server = locate(ring, invocationHashCode);
        return server;
    }

    /**
     * 从TreeMap中找出高key最近的服务器，如果没有服务器匹配，
     * 则返回第一值，形成一个环
     * @param ring 存储服务器结点的哈希
     * @param invocationHashCode 封装了调用的请求
     * @return
     */
    private Server locate(TreeMap<Integer, Server> ring, int invocationHashCode) {
        // 向右找到第一个 key
        Map.Entry<Integer, Server> locateEntry = ring.ceilingEntry(invocationHashCode);
        if (locateEntry == null) {
            // 想象成一个环，超过尾部则取第一个 key
            locateEntry = ring.firstEntry();
        }
        return locateEntry.getValue();
    }

    /**
     * 构建一个带虚拟结点的哈希环，使用TreeMap结构，底层是红黑树，
     * @param servers 服务器数组
     * @return 返回服务器数组的哈希环
     */
    private TreeMap<Integer, Server> buildConsistentHashRing(List<Server> servers) {
        TreeMap<Integer, Server> virtualNodeRing = new TreeMap<>();
        for (Server server : servers) {
            for (int i = 0; i < VIRTUAL_NODE_SIZE; i++) {
                // 新增虚拟节点的方式如果有影响，也可以抽象出一个由物理节点扩展虚拟节点的类
                virtualNodeRing.put(hashStrategy.getHashCode(server.getUrl() + VIRTUAL_NODE_SUFFIX + i), server);
            }
        }
        return virtualNodeRing;
    }

}

```
在该算法中，使用TreeMap的ceilingEntry方法返回离key的哈希值最近的服务器。

除了上面的一致性哈希算法的实现，还有一种实现，即Ketama算法，它不仅仅是一个哈希算法，更是一套完整的一致性哈希算法，在memcached中，其介绍如下：
> Ketama is an implementation of a consistent hashing algorithm, meaning you can add or remove servers from the memcached pool without causing a complete remap of all keys.
Here’s how it works:
* Take your list of servers (eg: 1.2.3.4:11211, 5.6.7.8:11211, 9.8.7.6:11211)
* Hash each server string to several (100-200) unsigned ints
* Conceptually, these numbers are placed on a circle called the continuum. (imagine a clock face that goes from 0 to 2^32)
* Each number links to the server it was hashed from, so servers appear at several points on the continuum, by each of the numbers they hashed to.
* To map a key->server, hash your key to a single unsigned int, and find the next biggest number on the continuum. The server linked to that number is the correct server for that key.
* If you hash your key to a value near 2^32 and there are no points on the continuum greater than your hash, return the first server in the continuum.
If you then add or remove a server from the list, only a small proportion of keys end up mapping to different servers.

代码实现如下所示：
```java
public class KetamaConsistentHashLoadBalancer implements LoadBalancer {

    private static MessageDigest md5Digest;

    static {
        try {
            md5Digest = MessageDigest.getInstance("MD5");
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("MD5 not supported", e);
        }
    }

    /**
     *  虚拟结点的个数，虚拟结点一般以4个为一组计算，所以数量一般同4的倍数
     */
    private final static int VIRTUAL_NODE_SIZE = 12;

    /**
     *  服务器与虚拟结点的连接符
     */
    private final static String VIRTUAL_NODE_SUFFIX = "-";

    /**
     * 根据请求匹配服务器
     * @param servers 服务器数组
     * @param invocation 封装了调用的请求
     * @return 返回匹配的值
     */
    @Override
    public Server select(List<Server> servers, Invocation invocation) {
        long invocationHashCode = getHashCode(invocation.getHashKey());
        TreeMap<Long, Server> ring = buildConsistentHashRing(servers);
        Server server = locate(ring, invocationHashCode);
        return server;
    }

    /**
     * 从TreeMap中找出高key最近的服务器，如果没有服务器匹配，
     * 则返回第一值，形成一个环
     * @param ring 存储服务器结点的哈希
     * @param invocationHashCode 封装了调用的请求
     * @return
     */
    private Server locate(TreeMap<Long, Server> ring, Long invocationHashCode) {
        // 向右找到第一个 key
        Map.Entry<Long, Server> locateEntry = ring.ceilingEntry(invocationHashCode);
        if (locateEntry == null) {
            // 想象成一个环，超过尾部则取第一个 key
            locateEntry = ring.firstEntry();
        }
        return locateEntry.getValue();
    }

    /**
     * 构建一个带虚拟结点的哈希环，使用TreeMap结构，底层是红黑树，
     * @param servers 服务器数组
     * @return 返回服务器数组的哈希环
     */
    private TreeMap<Long, Server> buildConsistentHashRing(List<Server> servers) {
        TreeMap<Long, Server> virtualNodeRing = new TreeMap<>();
        for (Server server : servers) {
            for (int i = 0; i < VIRTUAL_NODE_SIZE / 4; i++) {
                byte[] digest = computeMd5(server.getUrl() + VIRTUAL_NODE_SUFFIX + i);
                for (int h = 0; h < 4; h++) {
                    // 将digest数组按4个byte为一组，通过位操作产生一个最大32位的长整数，
                    // 一个16 byte的MD5，可以生成4个哈希值，即4个虚拟结点，所以一般将虚拟结点按照
                    // 4个为一组进行计算。
                    Long k = ((long) (digest[3 + h * 4] & 0xFF) << 24)
                            | ((long) (digest[2 + h * 4] & 0xFF) << 16)
                            | ((long) (digest[1 + h * 4] & 0xFF) << 8)
                            | (digest[h * 4] & 0xFF);
                    virtualNodeRing.put(k, server);

                }
            }
        }
        return virtualNodeRing;
    }

    /**
     * 计算字符串的Ketama哈希值
     * @param origin key值
     * @return 哈希值
     */
    private long getHashCode(String origin) {
        byte[] bKey = computeMd5(origin);
        // 使用前4个字符进行位运算得到32位的整数。
        long rv = ((long) (bKey[3] & 0xFF) << 24)
                | ((long) (bKey[2] & 0xFF) << 16)
                | ((long) (bKey[1] & 0xFF) << 8)
                | (bKey[0] & 0xFF);
        return rv;
    }

    /**
     * 根据key生成16位的MD5摘要，因此digest数组共16位
     * @param k key
     * @return MD5摘
     */
    private static byte[] computeMd5(String k) {
        MessageDigest md5;
        try {
            md5 = (MessageDigest) md5Digest.clone();
        } catch (CloneNotSupportedException e) {
            throw new RuntimeException("clone of MD5 not supported", e);
        }
        md5.update(k.getBytes());
        return md5.digest();
    }

```
在Ketama一致性哈希算法中，以四个虚拟结点为一组，将服务器名称以Md5编码后，得到16个字节的编码，每个虚拟结点对应Md5码16个字节中的4个，组成一个long型数值，做为这个虚拟结点在环中的惟一key。请求key的哈希值则以Md5中的前4个字节计算得到。

## 4. 总结
在 [对一致性Hash算法，Java代码实现的深入研究][4] 这篇文章中，作者通过数据分析，得出使用MurmurHash，FNV及Ketama这三种哈希算法，都能得到较好的性能，具有很好的参考意义。

**参考：**

----
[1]:https://www.oschina.net/translate/state-of-hash-functions
[2]:https://www.cnkirito.moe/consistent-hash-lb/
[3]:http://blog.codinglabs.org/articles/consistent-hashing.html
[4]:https://www.cnblogs.com/xrq730/p/5186728.html
[5]:https://www.iteye.com/blog/langyu-684087

[1. Hash 函数概览][1]

[2. 一致性哈希负载均衡算法的探讨][2]

[3. 一致性哈希算法及其在分布式系统中的应用][3]

[4. 对一致性Hash算法，Java代码实现的深入研究][4]

[5. Ketama一致性Hash算法(含Java代码)][5]