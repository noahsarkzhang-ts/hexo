---
title: Docker 安装部署 
date: 2022-01-29 15:43:58
tags:
- docker
categories:
- 部署
---

记录 Docker 在 CentOS 7 版本上的安装流程。

<!-- more -->

## 使用 Docker 仓库进行安装
设置 Docker 仓库，从仓库中更新 Docker。

### 设置仓库
安装所需的软件包。yum-utils 提供了 yum-config-manager ，并且 device mapper 存储驱动程序需要 device-mapper-persistent-data 和 lvm2.

```bash
$ sudo yum install -y yum-utils \
  device-mapper-persistent-data \
  lvm2

```

配置一个仓库进行下载安装。
**1. 官方仓库（国外比较慢）**

```bash
$ sudo yum-config-manager \
    --add-repo \
    https://download.docker.com/linux/centos/docker-ce.repo
```

**2. 阿里云**

```bash
$ sudo yum-config-manager \
    --add-repo \
    http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
```

**3. 清华大学源**

```bash
$ sudo yum-config-manager \
    --add-repo \
    https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/docker-ce.repo
```

### 安装 Docker Engine-Community
安装最新版本的 Docker Engine-Community 和 containerd.
```bash
$ sudo yum install docker-ce docker-ce-cli containerd.io
```

**安装特定版本**
**1. 查看版本列表**

```bash
$ yum list docker-ce --showduplicates | sort -r
```
输出结果：
```bash
Loading mirror speeds from cached hostfile
Loaded plugins: fastestmirror, langpacks
Installed Packages
docker-ce.x86_64            3:20.10.9-3.el7                    docker-ce-stable 
docker-ce.x86_64            3:20.10.8-3.el7                    docker-ce-stable 
docker-ce.x86_64            3:20.10.7-3.el7                    docker-ce-stable 
docker-ce.x86_64            3:20.10.6-3.el7                    docker-ce-stable 
docker-ce.x86_64            3:20.10.5-3.el7                    docker-ce-stable 
docker-ce.x86_64            3:20.10.4-3.el7                    docker-ce-stable 
docker-ce.x86_64            3:20.10.3-3.el7                    docker-ce-stable 
docker-ce.x86_64            3:20.10.2-3.el7                    docker-ce-stable 
docker-ce.x86_64            3:20.10.1-3.el7                    docker-ce-stable 
docker-ce.x86_64            3:20.10.12-3.el7                   docker-ce-stable 
docker-ce.x86_64            3:20.10.12-3.el7                   @docker-ce-stable
docker-ce.x86_64            3:20.10.11-3.el7                   docker-ce-stable 
docker-ce.x86_64            3:20.10.10-3.el7                   docker-ce-stable 

```

**2. 选择特定版本**

通过其完整的软件包名称安装特定版本，该软件包名称是软件包名称（docker-ce）加上版本字符串（第二列），从第一个冒号（:）一直到第一个连字符，并用连字符（-）分隔。例如：docker-ce-20.10.9.

```bash
# 格式： sudo yum install docker-ce-<VERSION_STRING> docker-ce-cli-<VERSION_STRING> containerd.io

$ sudo yum install docker-ce-<VERSION_STRING> docker-ce-cli-<VERSION_STRING> containerd.io
```

## 启动 Docker

```bahs
$ sudo systemctl start docker
```
验证是否启动成功。

```bash
$ sudo docker run hello-world
```

## 卸载 Docker
**1. 删除安装包**

```bash
yum remove docker-ce
```

**2. 删除 Docker 根目录**

```bash
rm -rf /var/lib/docker
```

## 更改 Docker 根目录
默认情况下，Docker 的根目录设置为 /var/lib/docker, 在该目录下会存放镜像及容器数据，会大量占用系统根目录的空间，较为合理的方式是将目录挂载到数据盘上。

### 查看默认目录

```bash
$ docker info

Client:
 Context:    default
 Debug Mode: false
 Plugins:
  app: Docker App (Docker Inc., v0.9.1-beta3)
  buildx: Docker Buildx (Docker Inc., v0.7.1-docker)
  scan: Docker Scan (Docker Inc., v0.12.0)

Server:
 Containers: 2
  Running: 2
  Paused: 0
  Stopped: 0
 Images: 2
 Server Version: 20.10.12
 Storage Driver: overlay2
  Backing Filesystem: extfs
  Supports d_type: true
  Native Overlay Diff: true
  userxattr: false
 Logging Driver: json-file
 Cgroup Driver: cgroupfs
 Cgroup Version: 1
 Plugins:
  Volume: local
  Network: bridge host ipvlan macvlan null overlay
  Log: awslogs fluentd gcplogs gelf journald json-file local logentries splunk syslog
 Swarm: inactive
 Runtimes: io.containerd.runc.v2 io.containerd.runtime.v1.linux runc
 Default Runtime: runc
 Init Binary: docker-init
 containerd version: 7b11cfaabd73bb80907dd23182b9347b4245eb5d
 runc version: v1.0.2-0-g52b36a2
 init version: de40ad0
 Security Options:
  seccomp
   Profile: default
 Kernel Version: 3.10.0-1160.11.1.el7.x86_64
 Operating System: CentOS Linux 7 (Core)
 OSType: linux
 Architecture: x86_64
 CPUs: 4
 Total Memory: 7.638GiB
 Name: VM-0-4-centos
 ID: YJBI:CN3F:YHTX:DJYD:7EBN:B4Z6:CRCP:2FQQ:4JDW:6F63:PRPW:6LOF
 Docker Root Dir: /var/lib/docker
 Debug Mode: false
 Registry: https://index.docker.io/v1/
 Labels:
 Experimental: false
 Insecure Registries:
  127.0.0.0/8
 Live Restore Enabled: false

```
可以看到 Docker 根目录为 /var/lib/docker

### 修改根目录

官方文档推荐的方式是 /etc/docker/daemon.json 文件，该文件默认没有创建，在该文件加入下面的内容：

```json
{
  "data-root": "/data/docker"
}
```

修改后重启 Docker 生效。

## Docker 镜像加速

国内从 DockerHub 拉取镜像速度会比较慢，可以配置国内的镜像加速器。Docker 官方和国内很多云服务商都提供了国内加速器服务，例如：

- 科大镜像：https://docker.mirrors.ustc.edu.cn/
- 网易：https://hub-mirror.c.163.com/
- 阿里云：https://<你的ID>.mirror.aliyuncs.com
- 七牛云加速器：https://reg-mirror.qiniu.com

在 /etc/docker/daemon.json 中加入如下内容可以设置镜像加速器。

```json
{
  "registry-mirrors": ["http://hub-mirror.c.163.com"],
  "data-root": "/data/docker"
}
```

## 碰到的问题
### 无法正常停止 Docker 进程

执行 `systemctl stop docker` 命令后，不能停止 Docker 进程，提示如下警告信息：

```bash
Warning: Stopping docker.service, but it can still be activated by:
  docker.socket
```

**解决办法：**

**停止 docker socket**
**1. 停止服务**
```bash
# 停止 docker 服务
sudo systemctl stop docker.socket
sudo systemctl stop docker.service
```

**2. 重启服务**
```bash
# 启动 docker 服务
sudo systemctl daemon-reload
sudo systemctl restart docker.service
```


<br>

**参考：**

----
[1]:https://www.runoob.com/docker/centos-docker-install.html
[2]:https://zhuanlan.zhihu.com/p/95533274
[3]:https://www.runoob.com/docker/docker-mirror-acceleration.html
[4]:https://blog.51cto.com/wutengfei/2946943

[1.CentOS Docker 安装][1]

[2.修改 Docker 的默认存储路径][2]

[3.Docker 镜像加速][3]

[4.无法正常停止docker进程][4]




