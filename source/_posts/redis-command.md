---
title: Redis 常用命令
date: 2024-04-12 21:28:55
updated: 2024-04-12 21:28:55
tags:
- redis 命令
categories: 
- 运维
---

这篇文章主要记录常用的 Redis 命令。

<!-- more -->

## 查看主结信息
**1. sentinel模式下查看主结点信息**
```bash
redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster
```

## 使用命令行客户端
```bash
# 交互式： redis-cli -h {host} -p {port}
redis-cli -h 127.0.0.1 -p 6379

# 命令方式：redis-cli -h {host} -p {port} {command},直接得到命令的结果
redis-cli -h 127.0.0.1 -p 6379 get hello

# 认证指定
auth password
```

## 全局命令
**1. 查看所有键**
```bash
keys *
```

**2. 键总数**
```bash
dbsize
```

**3. 查看键是否存在**
```bash
# 如果键存在返回 1，不存在则返回 0
exists key
```

**4. 删除键**
```bash
# 返回结果为成功删除键个数，假设删除一个不存在的键，就会返回0.
del key [key ...]
```

**5. 键过期**
```bash
expire key second
```

**6. 查看键过期时间**
```bash
ttl key
ttl 命令返回键的剩余过期时间，它有 3 种返回值：
1）大于等于0的整数：键剩余的过期时间；
2）-1: 键没有设置过期时间；
3）-1: 键不存在
```

**7. 查看键的数据结构**
```bash
type key
```

## 字符串命令
**1. 设置值**
```bash
set key value [ex second] [px milliseconds] [nx|xx]

set 命令选项：
1）ex second: 为键设置秒级过期时间；
2）ex milliseconds: 为键设置毫秒级过期时间；
3）nx: 键必须不存在，才可以设置成功，用于添加；
4）xx: 与 nx 相反，键必须存在，才可以设置成功，用于更新

set name allen
```

**2. 获取值**
```bash
get key
```

**3. 批量设置值**
```bash
mset key value [key value ...]

mset a 1 b 2 c 4 d 4
```

**4. 批量获取值**
```bash
mget key [key ...]

mget a b c d
```

**5. 计数**
```bash
# 自增1
incr key
返回结果分为三种情况：
1) 值不是整数，返回错误；
2) 值是整数，返回自增后的结果；
3) 键不存在，按照值为0自增，返回结果为1.

其它命令：
# 自减1
decr key

# 自增指定数字
incrby key increment

# 自减指定数字
decrby key decrement

# 自增浮点数
incrbyfloat key increment
```

## 哈希
**1. 设置值**
```bash
hset key field value

# 实例
hset user:1 name tom
```

**2. 获取值**
```bash
hget key field
```

**3. 删除 field**
```bash
hdel key field [field ...]
```

**4. 计算 field 数**
```bash
hlen key
```

**5. 批量设置或获取 field-value**
```bash
hmget key field [field ...]
hmget key field value [field value]
```

**6. 判断 field 是否存在**
```bash
hexists key field
```

**7. 获取所有 field**
```bash
hkeys key
```

**8. 获取所有 value**
```bash
hvalus key
```

**9. 获取所有的 field-value**
```bash
hgetall key
```

**10. 自增field**
```bash
hincrby key field
hincrbyfloat key field
```

**11. 计算 value 的字符串长度**
```bash
hstrlen key field
```

**说明：其它类型的命令后续再补充**

