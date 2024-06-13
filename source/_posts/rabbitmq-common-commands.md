---
title: Rabbitmq 常用运维命令
date: 2024-04-06 17:59:57
updated: 2024-04-06 17:59:57
tags:
- rabbitmqctl 命令
- rabbitmq
categories: 
- 运维
---

这篇文章主要记录在工作中用 **rabbitmqctl** 命令协助定位 **Rabbitmq** 问题。 

<!-- more -->

**1. 查看帮助**
```bash
rabbitmqctl --help
```

**2. 创建用户名及密码**
```bash
# 创建 admin 用户，密码为 123456
rabbitmqctl add_user admin 123456
```


**3. 设置用户角色**
```bash
# 设置 admin 为 administrator 角色
rabbitmqctl set_user_tags admin administrator
```

**4. 创建 vhost**
```bash
# 创建名为 test 的虚拟主机
rabbitmqctl add_vhost test
```

**5. 设置host权限 -p host**
```bash
# 设置 admin 用户具有虚拟主机 test 的读写权限
rabbitmqctl set_permissions -p test admin '.*' '.*' '.*'
```

**6. 查看用户**
```bash
rabbitmqctl list_users
```

**7. 查看vhosts**
```bash
rabbitmqctl list_vhosts 
name
live
/
test
```

**8. 查看queue信息**
```bash
# -p 指定虚拟主机
rabbitmqctl list_queues -p test
```

**9. 查看exchange的信息**
```bash
# -p 指定虚拟主机
rabbitmqctl list_exchanges -p test
```

**10. 查看绑定信息**
```bash
# -p 指定虚拟主机
rabbitmqctl list_bindings -p test
```

**11. 查看链接信息**
```bash
rabbitmqctl list_connections
```

**12. 查看目前所有的channels**
```bash
rabbitmqctl list_channels 
```

**13. 查看consumers**
```bash
# -p 指定虚拟主机
rabbitmqctl list_consumers -p test
```

**14. 查看event_push绑定信息**
```bash
# -p 指定虚拟主机
# 查看绑定在队列 event_push 上的绑定信息
rabbitmqctl list_bindings -p test|grep event_push
```