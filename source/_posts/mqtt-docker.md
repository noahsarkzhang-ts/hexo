---
title: Mqtt 系列：Docker 部署
date: 2023-02-18 19:36:14
updated: 2023-02-18 19:36:14
tags:
- docker
categories:
- MQTT
---

这篇文章讲述 `MQTT Broker` 项目的 Docker 镜像打包及 Docker Compose 部署模式。

<!-- more -->

## 镜像打包

本项目使用的构建工具是 Maven, 自然地使用 Maven Plugin 来进行镜像打包。具体的操作包括以下步骤：
1. 构建打包环境；
2. 引入 Maven Dockfile 插件；
3. 编辑 Dockfile 文件；
4. 输出镜像。

### 构建打包环境
Docker 使用是 Client-Server 的架构，打包的资源和文件可以在 Client 端，通过特定的端口传输到 Server 端，体验跟直接在 Server 端打包是一样的。这种方式使得我们可以在 Windows 环境编码，在远程 Linux 环境打包，只需要进行如下配置即可：

**Docker Deamon 配置:**
```bash
# 编辑 docker.server, 开放 2375 端口
$ vim /usr/lib/systemd/system/docker.service
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd -H tcp://0.0.0.0:2375 -H unix://var/run/docker.sock

# 重启 docker
$ systemctl daemon-reload
$ systemctl restart docker

```

**Windows Client 配置:**
配置 Docker host 的地址，使用 Doker client 便可连接该服务器。
```bash
# 添加环境变量
DOCKER_HOST=tcp://192.168.100.101:2375
```

### 引入打包插件

### 引入 maven-assembly-plugin

首先，将项目打包成一个 fatjar, 可以简化后续的镜像打包。这里选用的是 `maven-assembly-plugin` 插件，需要指定 `MainClass`, 作为程序启动类，另外，打包后的文件名格式为：`${project.build.finalName}-jar-with-dependencies.${project.packaging}`.

```xml
<plugin>
    <artifactId>maven-assembly-plugin</artifactId>
    <version>3.0.0</version>
    <configuration>
        <archive>
            <manifest>
                <mainClass>org.noahsark.mqtt.broker.Server</mainClass>
            </manifest>
        </archive>
        <descriptorRefs>
            <descriptorRef>jar-with-dependencies</descriptorRef>
        </descriptorRefs>
    </configuration>
    <executions>
        <execution>
            <id>make-assembly</id>
            <phase>package</phase>
            <goals>
                <goal>single</goal>
            </goals>
        </execution>
    </executions>
</plugin>
```

### 引入 dockerfile-maven-plugin

在 `dockerfile-maven-plugin` 中定义仓库名称和 tag, 并向 Docker 文件中传入三个参数：1) JAR_FILE; 2) VERSION; 3) NAME. 这三个参数在 Docker 文件中有用到。

```xml
<plugin>
    <groupId>com.spotify</groupId>
    <artifactId>dockerfile-maven-plugin</artifactId>
    <version>1.4.3</version>
    <configuration>
        <repository>noahsark/mqtt-broker</repository>
        <tag>${project.version}</tag>
        <useMavenSettingsForAuth>true</useMavenSettingsForAuth>
        <buildArgs>
            <JAR_FILE>${project.build.finalName}-jar-with-dependencies.${project.packaging}</JAR_FILE>
            <VERSION>${project.version}</VERSION>
            <NAME>${project.artifactId}</NAME>
        </buildArgs>
    </configuration>
</plugin>
```

### 编辑 Dockfile 文件

在 Dockerfile 中包括几个重要的部分：
1. 定义基础镜像；
2. 接收输入的参数；
3. 设定时区和加入字体；
4. 新建用户，避免使用 root 用户；
5. 新建程序的运行目录；
6. 拷贝启动脚本、配置文件和可执行程序；
7. 定义可执行程序运行所需的环境变量，如配置文件和日志目录；
8. 添加权限及声明端口。


```properties
# 定义基础镜像
FROM openjdk:8-alpine

# 接收参数
ARG NAME
ARG VERSION
ARG JAR_FILE

# 定义标签
LABEL name=$NAME \
      version=$VERSION

# 设定时区
ENV TZ=Asia/Shanghai
RUN set -eux; \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime; \
    echo $TZ > /etc/timezone

# 加入字体
RUN apk add --update --no-cache \
    ttf-dejavu fontconfig \
    && rm -rf /var/cache/apk/*

# 新建用户java-app
RUN set -eux; \
    addgroup --gid 1000 java-app; \
    adduser -S -u 1000 -g java-app -h /home/java-app/ -s /bin/sh -D java-app; \
    mkdir -p /home/java-app/lib /home/java-app/config /home/java-app/jmx-ssl /home/java-app/logs /home/java-app/tmp /home/java-app/jmx-exporter/lib /home/java-app/jmx-exporter/etc; \
    chown -R java-app:java-app /home/java-app

# 导入启动脚本
COPY --chown=java-app:java-app docker-entrypoint.sh /home/java-app/docker-entrypoint.sh

# 添加执行权限
RUN chmod +x /home/java-app/docker-entrypoint.sh

# 导入配置文件
COPY --chown=java-app:java-app config/alligator.properties /home/java-app/config/alligator.properties

# 设置环境变量
ENV ALLIGATOR_CONFIG_FILE=/home/java-app/config/alligator.properties ALLIGATOR_LOG_DIR=/home/java-app/logs

# 导入JAR
COPY --chown=java-app:java-app target/${JAR_FILE} /home/java-app/lib/app.jar

USER java-app

ENTRYPOINT ["/home/java-app/docker-entrypoint.sh"]

EXPOSE 1883 8080
```

程序是通过 `docker-entrypoint.sh` 启动脚本来启动的，其内容如下：
```bash
#!/bin/sh

set -ex;

exec /usr/bin/java \
  $JAVA_OPTS \
  -Djava.security.egd=file:/dev/./urandom \
  -Djava.net.preferIPv4Stack=true \
  -Djava.io.tmpdir="/home/java-app/tmp" \
  -jar \
  /home/java-app/lib/app.jar \
  "$@"
```

### 输出镜像

Docker 文件编辑完成之后，便可使用如下命令进行打包。
```bash
# 构建镜像
mvn dockerfile:build
```

最后通过如下命令启动服务：
```bash
docker run -d -p 1883:1883 -p 8080:8080 --name mqtt-broker \
	--privileged=true \
	noahsark/mqtt-broker:1.0-SNAPSHOT 
```

## Docker Compose 部署

使用 Docker Compose 的目的主要是运行一个包含所有服务的最小单节点集合。包含的服务有：1) Redis; 2) Mysql; 3) MQTT Broker. 在构建服务中，有一个关键的问题，就是如何让 MQTT Broker 节点找到 redis 和 mysql 服务。在这里使用的方案是：自定义 bridge 网络，使用服务名称(如 redis,mysql) 来引用服务。使用自定义网络之后，Docker Deamon 使用自带的 DNS 服务器将服务名称作为域名解析，从而将动态的 IP 与静态的容器名称建立映射，方便程序内部使用，

```yaml
version: '3'

networks:
  mqtt:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 10.212.12.0/24
          gateway: 10.212.12.1

services:
  redis:
    container_name: mqtt_redis
    image: redis:6.2
    restart: always
    networks:
      - mqtt
    ports:
      - 6379:6379

  mysql:
    container_name: mqtt_mysql
    image: mysql:5.7
    restart: always
    networks:
      - mqtt
    ports:
      - 3306:3306
    environment:
      - MYSQL_ROOT_PASSWORD=123456

  mqtt_broker:
    container_name: mqtt_broker
    restart: always
    image: noahsark/mqtt-broker:1.0-SNAPSHOT
    networks:
      - mqtt
    ports:
      - 1883:1883
      - 8081:8081

```

在程序中使用服务名称来引用服务：
```properties
# 引用 redis 服务
cache.redis.host=redis
cache.redis.port=6379

# 引用 mysql 服务
db.mysql.url=jdbc:mysql://mysql:3306/alligator_mqtt?serverTimezone=Asia/Shanghai&useUnicode=true&characterEncoding=utf8&useSSL=false
db.mysql.username=root
db.mysql.password=123456
```

编辑完 `docker-compose.yaml` 文件之后，便可启动服务。
```bash
# 启动服务
docker-compose up -d

# 关闭服务
docker-compose down
```

**说明：**
启动服务之后，还需要将项目中的 sql 脚本导入到 Mysql 服务中，对其进行数据初始化。


**参考：**

----
[1]:https://segmentfault.com/a/1190000016449865
[2]:https://docs.docker.com/develop/develop-images/dockerfile_best-practices/


[1. Java程序制作Docker Image推荐方案][1]
[2. Best practices for writing Dockerfiles][2]

