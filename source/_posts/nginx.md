---
title: Springboot 序列：Nginx
date: 2022-05-21 15:45:26
tags:
- nginx
- 静态资源
- 反向代理
- 限流
- 长连接
categories:
- Springboot
---

在项目中，Nginx 一般会有承担三个角色 ：1）静态资源服务器；2）反向代理服务器；3）网关限流器，本文将介绍三个功能。

<!-- more -->

## 概述

Nginx 配置文件整体结构如下：

```javascript
... #全局块

events { #events块
...
}

http #http块
{
    ... #http全局块

    server #server块
    { 
        ... #server全局块
        location [PATTERN] #location块
        {
            ...
        }
        location [PATTERN] 
        {
            ...
        }
     }

    server
    {
        ...
    }

    ... #http全局块
}
```

- main 全局块：配置影响 nginx 全局的指令。一般有运行 nginx 服务器的用户组，nginx 进程 pid 存放路径，日志存放路径，配置文件引入，允许生成worker process数等；
- events 块：配置影响 nginx 服务器或与用户的网络连接。有每个进程的最大连接数，选取哪种事件驱动模型处理连接请求，是否允许同时接受多个网路连接，开启多个网络连接序列化等；
- http 块：可以嵌套多个 server，配置代理，缓存，日志定义等绝大多数功能和第三方模块的配置。如 文件引入，mime-type 定义，日志自定义，是否使用 sendfile 传输文件，连接超时时间，单连接请求数等。
- server 块：配置虚拟主机的相关参数，一个 http 中可以有多个 server; 
- location 块：配置请求的路由，以及各种页面的处理情况。

不同模块指令关系：server 继承 main, location 继承 server, upstream 既不会继承指令也不会被继承，它有自己的特殊指令。

## 静态资源服务器

nginx 可以用做 http 静态资源服务器，其配置如下所示：

```javascript

# http://ip:port/test.html --> /data/nginx/html/test.html
location / {
    root /data/nginx/html;
    index index.html;
}

# http://ip:port/static/test.jpg --> /data/nginx/html/static/test.jpg
location /static {
    root /data/nginx/html;
    index index.html;
}

# http://ip:port/images/test.jpg --> /data/nginx/html/images//test.jpg
location /images {
    alias /data/nginx/html/images/;
    index index.html;
}
```

可以通过 `root` 或 `alias` 指令来设置文件的目录，在 nginx 的配置中，alias 目录和 root 目录是有区别的：
- alias 指定的目录是准确的，即 location 匹配访问的 path 目录下的文件直接是在 alias 目录下查找的；
- root 指定的目录是 location 匹配访问的 path 目录的上一级目录,这个 path 目录一定要是真实存在 root 指定目录下的；
- alias 指定的目录后面必须要加上 / 符号；
- alias 目录配置中，location 匹配的 path 目录如果后面不带 /，那么访问的 url 地址中这个 path 目录后面加不加 / 不影响访问，访问时它会自动加上 /；但是如果 location 匹配的 path 目录后面加上 /，那么访问的 url 地址中这个 path 目录必须要加上 /, 访问时它不会自动加上 /, 如果不加上 /, 访问就会失败；
5）root 目录配置中，location 匹配的 path 目录后面带不带 /, 都不会影响访问。


## 反向代理

nginx 可以作为反向代理服务器，为后端应用提供负载均衡的能力，其配置如下：

```javascript
http {
    ...
	
    # 1.1 设置后端应用 app1
    upstream app1_pool {
        server 192.168.1.100:9501;
        keepalive 128;
    }
    
    # 1.2 设置后端应用 app2
    upstream app2_pool {
        server 192.168.1.100:9502;
        keepalive 128;
    }
 
    server {
        listen 80;
        server_name 192.168.1.100;
        access_log  /data/nginx/logs/static.log  main;
        index index.html index.htm;
	   
        ...

        # /app1/hello -> /hello 截取app1
        # 2.1 设置反向代理
        location /app1/ {

            proxy_pass http://app1_pool/;
            proxy_redirect off;
            proxy_set_header Host $host;
            proxy_set_header X_Real_IP $remote_addr;
            proxy_set_header X-Forwarded-For $remote_addr;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
		}

        # /app1/hello->/app1/hello
        # 2.2 设置反向代理
        location /app2 {

            proxy_pass http://app2_pool;
            proxy_redirect off;
            proxy_set_header Host $host;
            proxy_set_header X_Real_IP $remote_addr;
            proxy_set_header X-Forwarded-For $remote_addr;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
        }

        ...
          
    }
}
```

**说明：**
- `location` 与 `proxy_pass` path 路径上包含 / , 则真实的路径为移除 `location` path 的内容，如 url: /app1/hello, 区别的 url: /hello; 
- `location` 与 `proxy_pass` path 路径上不包含 / , 则直接转发，如 url: /app1/hello, 区别的 url: /app1/hello; 

## 长连接设置

nginx 可以针对 http 1.1 进行长连接设置。

### 客户端长连接

默认情况下，nginx 已经自动开启了对客户端连接的长连接支持。一般场景可以直接使用，也可以进行自定义配置：

```javascript
http {
    keepalive_timeout 120s;        # 客户端链接超时时间。为 0 的时候禁用长连接。即长连接的 timeout
    keepalive_requests 1000;      # 在一个长连接上可以服务的最大请求数目。当达到最大请求数目且所有已有请求结束后，连接被关闭。默认值为100。即每个连接的最大请求数
}
```

### 后端长连接

nginx 也可以设置跟后端使用保持长连接，其配置如下：

```javascript
http {
    upstream backend {
        server 192.168.0.1：8080 weight=1 max_fails=2 fail_timeout=30s;
        server 192.168.0.2：8080 weight=1 max_fails=2 fail_timeout=30s;
        keepalive 300;       # 空闲 keepalive 连接的最大数量
    }  
	
    server {
        listen 8080;
		
        location / {
            proxy_pass http://backend;
            proxy_http_version 1.1;                   # 设置http版本为1.1
            proxy_set_header Connection "";           # 设置Connection为长连接（默认为no）
        }
    }
}
```

## 限流

在 nginx 中可以使用两个模块进行限流配置：
- ngx_http_limit_conn_module: 连接数限流模块；
- ngx_http_limit_req_module: 漏桶算法实现的请求限流模块。

这两个模块 nginx 默认已经安装，不用额外再安装。

limit_conn 用来对某个 KEY 对应的总的网络连接数进行限流，可以按照如 IP、域名维度进行限流。limit_req 用来对某个 KEY 对应的请求的平均速率进行限流，并有两种用法：平滑模式（delay）和允许突发模式(nodelay)。

### ngx_http_limit_conn_module
limit_conn 是对某个 KEY 对应的总的网络连接数进行限流。可以按照IP 来限制 IP维度 的总连接数，或者按照服务域名来限制某个域名的总连接数。但是记住不是每一个请求连接都会被计数器统计，只有那些被 Nginx 处理的且已经读取了整个请求头的请求连接才会被计数器统计。

配置实例：

```javascript
http {
 
    # 按照请求 ip 进行配置，可以设置客户端的连接数
    limit_conn_zone $binary_remote_addr zone=perip:10m;
    # 按照域名进行配置，可以设置服务器连接数
    limit_conn_zone $server_name zone=perserver:10m;
	
    limit_conn_log_level error;
    limit_conn_status 503;

    server {
        listen 80;
        server_name 192.168.1.100;
        access_log  /data/nginx/logs/static.log  main;
        index index.html index.htm;
	   
        # 将限流配置应用到 url 上，客户端同时只能一个连接进行访问	
        location /limit1 {
            limit_conn perip 1;

            alias /data/nginx/html/limit/;
            index index.html;

        }
		
        # 将限流配置应用到 url 上，服务器同时只能两个连接进行访问
        location /limit2 {
            limit_conn perserver 2;

            alias /data/nginx/html/limit/;
            index index.html;

        }
		
    }
}

```
- limit_conn：要配置存放 KEY 和计数器的共享内存区域和指定 KEY 的最大连接数；此处指定的最大连接数是 1，表示 nginx 最多同时并发处理 1 个连接；
- limit_conn_zone：用来配置限流 KEY、及存放 KEY 对应信息的共享内存区域大小；此处 的KEY 是 “$binary_remote_addr” 其表示 IP 地址，也可以使用如 $server_name 作为 KEY 来限制域名级别的最大连接数；
- limit_conn_status：配置被限流后返回的状态码，默认返回 503；
- limit_conn_log_level：配置记录被限流后的日志级别，默认 error 级别。

### ngx_http_limit_req_module

limit_req 是令牌桶算法实现，用于对指定 KEY 对应的请求进行限流，比如按照IP维度限制请求速率。

配置实例：

```javascript
http {
 
    # 按照 ip 进行配置，设置请求的 qps, 在这里设置为 1.
    limit_req_zone $binary_remote_addr zone=one:10m rate=1r/s;
    limit_conn_log_level error;
    limit_conn_status 503;

    server {
        listen 80;
        server_name 192.168.1.100;
        access_log  /data/nginx/logs/static.log  main;
        index index.html index.htm;
		
        # 将限流配置应用到 url 上
        location /limit3 {
            limit_req zone=one burst=5 nodelay;

            alias /data/nginx/html/limit/;
            index index.html;

        } 
    }
}
```

- limit_req：配置限流区域、桶容量（突发容量，默认0）、是否延迟模式（默认延迟）；
- limit_req_zone：配置限流 KEY、及存放 KEY 对应信息的共享内存区域大小、固定请求速率；此处指定的 KEY 是“$binary_remote_addr” 表示IP地址；固定请求速率使用 rate 参数配置，支持 10r/s 和 60r/m，即每秒 10 个请求和每分钟 60 个请求，不过最终都会转换为每秒的固定请求速率（10r/s 为每 100 毫秒处理一个请求；60r/m，即每 1000 毫秒处理一个请求）。

## 整体配置

```javascript
#user  nginx;
worker_processes  auto;

error_log  /data/nginx/logs/error.log notice;
pid        /data/nginx/nginx.pid;

events {
    worker_connections  1024;
}

http {
    include       /data/nginx/conf/mime.types;
    default_type  application/octet-stream;

    log_format  main  '$remote_addr - $remote_user [$time_local] [$msec] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /data/nginx/logs/access.log  main;

    sendfile        on;
    #tcp_nopush     on;

    keepalive_timeout  65;

    # 限流配置
    # 按照请求 ip 进行配置，可以设置客户端的连接数
    limit_conn_zone $binary_remote_addr zone=perip:10m;
    # 按照域名进行配置，可以设置服务器连接数
    limit_conn_zone $server_name zone=perserver:10m;
    # 按照 ip 进行配置，设置请求的 qps, 在这里设置为 1.
    limit_req_zone $binary_remote_addr zone=one:10m rate=1r/s;
    limit_conn_log_level error;
    limit_conn_status 503;

    #gzip  on;

    upstream app1_pool {
        server 192.168.1.100:9501;
        keepalive 128;
    }
    
    upstream app2_pool {
        server 192.168.1.100:9502;
        keepalive 128;
    }
 
    server {
        listen 80;
        erver_name 192.168.1.100;
        access_log  /data/nginx/logs/static.log  main;
        index index.html index.htm;
	   
        location / {
            root /data/nginx/html;
            index index.html;
        }

        location /static {
            root /data/nginx/html;
            index index.html;
        }

        location /images {
            alias /data/nginx/html/images/;
            index index.html;
        }

        location /app1/ {
            proxy_pass http://app1_pool/;
            proxy_redirect off;
            proxy_set_header Host $host;
            proxy_set_header X_Real_IP $remote_addr;
            proxy_set_header X-Forwarded-For $remote_addr;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
        }

        location /app2 {
            limit_req zone=one burst=5 nodelay;
            proxy_pass http://app2_pool;
            proxy_redirect off;
            proxy_set_header Host $host;
            proxy_set_header X_Real_IP $remote_addr;
            proxy_set_header X-Forwarded-For $remote_addr;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
        }

        # 将限流配置应用到 url 上，客户端同时只能一个连接进行访问
        location /limit1 {
            limit_conn perip 1;

            alias /data/nginx/html/limit/;
            index index.html;
        }

        # 将限流配置应用到 url 上，服务器同时只能两个连接进行访问
        location /limit2 {
            limit_conn perserver 2;

            alias /data/nginx/html/limit/;
            index index.html;
        }

        # 将限流配置应用到 url 上
        location /limit3 {
            limit_req zone=one burst=5 nodelay;

            alias /data/nginx/html/limit/;
            index index.html;

        }
          
    }
}

```

[工程代码：https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springboot-nginx](https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springboot-nginx)

</br>

**参考：**

----
[1]:https://zhuanlan.zhihu.com/p/31202053
[2]:https://xuexb.github.io/learn-nginx/example/proxy_pass.html#url-%E5%8F%AA%E6%98%AF-host
[3]:https://www.cnblogs.com/kevingrace/p/9364404.html
[4]:https://mp.weixin.qq.com/s?__biz=MzIwODA4NjMwNA==&mid=2652897782&idx=1&sn=cb46b23b2778f14ea3bcc419eb0392ce&scene=1&srcid=0614xnlcciitJsZxjl1ToKVp#wechat_redirect

[1. nginx快速入门之配置篇][1]

[2. proxy_pass url 反向代理的坑][2]

[3. Nginx中保持长连接的配置 - 运维记录][3]

[4. 聊聊高并发系统之限流特技-2][4]

