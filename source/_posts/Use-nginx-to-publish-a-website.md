---
title: 用 Nginx 发布网站
date: 2021-07-24 21:49:11
tags: 
- nginx
- docker
- hexo
- 网站
categories:
- hexo
---

之前买了一台阿里云的云主机，一直想把用起来。考虑到我的个人网站之前部署在 github 上，网页加载比较慢，正好可以用云主机进行部署，提升速度，开始操作。

## 1. 前置条件
- 购买云主机
- 购买域名
- 申请免费证书
- 网站备案
- 用 nginx 发布网站

前面的四个环节，参考阿里云的帮助文档操作即可，这篇文章主要讲述第五步：用 nginx 发布网站。

## 2. 用 Docker 安装 nginx
执行下面一条命令，即可安装最新版的 nginx。
```bash
$ docker container run \
  -d \
  -p 80:80 \
  --rm \
  --name mynginx \
  nginx
```

参数说明：
- -d：在后台运行
- -p：容器的 80 端口映射到宿主机的 80 端口
- --rm：容器停止运行后，自动删除容器文件
- --name：容器的名字为 mynginx

正常情况下，通过 80 端口便可访问到 nginx 的默认页面。

关闭命令如下：

```bash
$ docker container stop mynginx
```

## 3. 映射目录文件
网页及配置文件包含在容器里，不方便部署，现在将这两个目录映射到宿主机上，要更新直接在宿主机上更新即可。

### 3.1 网页目录
在 nginx 中，网页存放的目录是 /usr/share/nginx/html。在宿主机上建立 /data/blog/html 目录（根据需要随意指定），通过 volume 选项建立映射，命令如下：
```bash
$ docker container run \
  -d \
  -p 80:80 \
  --rm \
  --name mynginx \
  --volume /data/blog/html:/usr/share/nginx/html \
  nginx
```

### 3.2 配置文件目录
nginx 的配置文件目录在 /etc/nginx 下，先将其复制到宿主机目录下，再建立映射。
```bash
$ mkdir /data/nginx
$ cd /data/nginx

$ docker container cp mynginx:/etc/nginx .x

$ mv nginx conf

```

上面的命令将把 mynginx 容器的 /etc/nginx 拷贝到 /data/nginx 目录下，形成的目录是 /etc/nginx/nginx，最后将最后一个 nginx 目录改为 conf 目录。

最后使用如下命令建立映射：
```bash
$ docker container run \
  -d \
  -p 80:80 \
  --rm \
  --name mynginx \
  --volume /data/blog/html:/usr/share/nginx/html \
  --volume /data/nginx/conf:/etc/nginx \
  nginx
```

## 4. 配置 HTTPS 证书
在阿里云申请到 SSL 证书之后，会得到两个文件：1）证书文件（以 cert-file-name.pem 为例）； 2）私钥文件（以 cert-file-name.key 为例）。
在 /data/nginx/conf 目录下新建一个 certs 目录，将上述文件复制到该目录下，修改 /data/nginx/conf/nginx.conf 文件，将页面的配置片断加入到 http 选项中，如下所示：

```bash
http {
	...
	
	server {
		listen 443 ssl;
		#配置HTTPS的默认访问端口为443。
		#如果未在此处配置HTTPS的默认访问端口，可能会造成Nginx无法启动。
		#如果您使用Nginx 1.15.0及以上版本，请使用listen 443 ssl代替listen 443和ssl on。
		server_name yourdomain.com; #需要将yourdomain.com替换成证书绑定的域名。
		root /usr/share/nginx/html;
		index index.html index.htm;
		ssl_certificate certs/cert-file-name.pem;  #需要将cert-file-name.pem替换成已上传的证书文件的名称。
		ssl_certificate_key certs/cert-file-name.key; #需要将cert-file-name.key替换成已上传的证书密钥文件的名称。
		ssl_session_timeout 5m;
		ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE:ECDH:AES:HIGH:!NULL:!aNULL:!MD5:!ADH:!RC4;
		#表示使用的加密套件的类型。
		ssl_protocols TLSv1 TLSv1.1 TLSv1.2; #表示使用的TLS协议的类型。
		ssl_prefer_server_ciphers on;
		location / {
			root /usr/share/nginx/html;  #站点目录。
			index index.html index.htm;
		}
	}

	# 设置HTTP请求自动跳转HTTPS
	server {
		listen 80;
		server_name yourdomain.com; #需要将yourdomain.com替换成证书绑定的域名。
		rewrite ^(.*)$ https://$host$1; #将所有HTTP请求通过rewrite指令重定向到HTTPS。
		location / {
			index index.html index.htm;
		}
	}
}
```

开放 HTTPS 443 端口，命令如下：
```bash
$ docker container run \
  -d \
  -p 80:80 \
  -p 443:443 \
  --rm \
  --name mynginx \
  --volume /data/blog/html:/usr/share/nginx/html \
  --volume /data/nginx/conf:/etc/nginx \
  nginx
```

## 5. 总结
最后将 hexo public 目录下的文件复制到 /data/blog/html 即可。 

**参考：**

----
[1]:https://www.ruanyifeng.com/blog/2018/02/nginx-docker.html

[2]:https://help.aliyun.com/document_detail/98728.html

[1. Nginx 容器教程][1]
[2. 在Nginx（或Tengine）服务器上安装证书][2]