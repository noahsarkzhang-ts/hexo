---
title: Docker 镜像与分层
date: 2019-03-31 20:42:33
tags: 
- docker
- 镜像
- 分层
- 文件
categories: 
- docker
---

一直对Docker中的镜像（image），分层（layer）及文件（file）三者之间的关系一直很好奇，这篇文章讲述就是这三者之间的关系。

**环境说明：**
虚拟机：VirtualBox 5.1.38
操作系统：Ubuntu 16.04.5 LTS
docker：18.06.1-ce
Storage Driver：overlay2

## 1、镜像存储位置
Docker里面存放镜像的目录主要有两个：**/var/lib/docker/image/{graph_driver}/及/var/lib/docker/{graph_driver}/**，前一个主要是存放镜像的元数据，存储逻辑上的镜像和镜像层，后一个主要是存放镜像的数据文件，包括只读层和可读写层的文件。

## 2、镜像的元数据管理
以overlay2存储驱动为例，/var/lib/docker/image/overlay2/目录下结构为：
```bash
# tree -L 1 overlay2/
overlay2/
├── distribution
├── imagedb
├── layerdb
└── repositories.json
```
- distribution目录存放layer的diff_id与digest的对应关系，关于二者的关系后面内容再描述；
- imagedb、layerdb分别存放镜像及分层的元数据；
- repositories.json存放镜像仓库的相关数据；


### 2.1 repositories.json
repositories.json 中记录了和本地 image 相关的 repository 信息，主要是 name 和 image id 的对应关系，当 image 从 registry 上被 pull 下来后，就会更新该文件。
```bash
# cat repositories.json | python -mjson.tool
{
    "haproxy": {
            "haproxy:latest": "sha256:08d602ba77646c322b68eee5f6e436f4438e1ae3a1ad3cba26f9baa4c148d5ec",  
            "haproxy@sha256:530809f5a9910de8688fe85f6b4f0533a2418365b448a82bb590b197fe7529c0": "sha256:08d602ba77646c322b68eee5f6e436f4438e1ae3a1ad3cba26f9baa4c148d5ec"
        }
}
```
- 存放了**repository**名称**haproxy**、**tag(latest)** 及**image id(08d602...)d**的信息；
- 存放了**repository image id**与**digest**的对应关系，haproxy:latest签名为：haproxy@sha256:530809...，可以通过两种方式pull镜像，即名称(haproxy:latest)和digest；
- image id是Image的唯一标示，其数值根据该镜像的元数据配置文件采用sha256算法的计算获得。

镜像的元数据配置文件存放在 **/var/lib/docker/image/overlay2/imagedb/content/sha256/** 目录下，文件为Image id，对该文件内容计算sha256摘要即为image id。
```bash
# sha256sum 08d602ba77646c322b68eee5f6e436f4438e1ae3a1ad3cba26f9baa4c148d5ec
08d602ba77646c322b68eee5f6e436f4438e1ae3a1ad3cba26f9baa4c148d5ec  08d602ba77646c322b68eee5f6e436f4438e1ae3a1ad3cba26f9baa4c148d5e
```

### 2.2 imagedb
imagedb存放了image的元数据配置文件，该文件记录了image元数据信息，包括镜像架构、操作系统、镜像默认配置、构建该镜像的容器ID和配置、创建时间、创建该镜像的Docker版本、构建镜像的历史信息及rootfs。通过构建镜像的历史信息及rootfs中的diff_ids，可以将image和layer关联起来，还可以计算出该镜像层的存储索引chainID，计算方式见后面内容。
镜像元数据配置文件目录：**/var/lib/docker/image/overlay2/imagedb/content/sha256/{image_id}**，查看haproxy元数据配置文件如下：
```bash
# cat 08d602ba77646c322b68eee5f6e436f4438e1ae3a1ad3cba26f9baa4c148d5ec | python -mjson.tool
{
    "architecture": "amd64",
    "config": {
        "ArgsEscaped": true,
        "AttachStderr": false,
        "AttachStdin": false,
        ......
    },
    "container": "5fa7b90388c618ba33fc3cc68f4768ec2f1fa113da15ffefbb2e1d1abede8ada",
    "container_config": {
        "ArgsEscaped": true,
        "AttachStderr": false,
        "AttachStdin": false,
        "AttachStdout": false,
       
    },
    "created": "2019-03-05T04:39:53.999146965Z",
    "docker_version": "18.06.1-ce",
    "history": [
        {
            "created": "2019-03-04T23:22:21.800977094Z",
            "created_by": "/bin/sh -c #(nop) ADD file:5ea7dfe8c8bcc... in / "
        },
        ......
    ],
    "os": "linux",
    "rootfs": {
        "diff_ids": [
            "sha256:6744ca1b11903f4db4d5e26145f6dd20f9a6d321a7f725f1a0a7a45a4174c579",
            "sha256:885806cf466d56e36824a1623f362349202c6e4e8f7aab64e174519b66484fea",
            "sha256:28de19851da2a6dbe597cf23e1637b14d4c51f7074ae01dd9818e131c62e430e"
        ],
        "type": "layers"
    }
}
```
- 在rootfs中diff_ids包含了三个分层layer，从上到下依次是从底层到顶层，最底层是6744a...，最顶层是28de1...，通过diff_ids，可以将镜像与分层关联起来，如何关联见下面内容。
- 在该镜像中，有三个只读层，再加上一个init层，一个可读写层，总共有五个分层layer。

### 2.3 layerdb
docker中的镜像是分层的，划分为只读层和读写层。其中docker定义了roLayer接口来描述只读的镜像层，定义了mountLayer来描述可读写的容器层。这两个层分别存放在了两个目录中：
**roLayer:/var/lib/docker/image/overlay2/layerdb/sha256/{chainID}**
**mountLayer:/var/lib/docker/image/overlay2/layerdb/mounts/{container_id}**

#### 2.3.1 layer只读层
在layer的属性中，diffID采用SHA256算法，基于分层文件包中的内容计算得到。而chainID是基于内容存储的索引，这是根据当前层与所有祖先镜像层diffId计算出来的，具体算法如下：
1. 如果该镜像层是最底层（没有父镜像层），该层的diffID便是chainID；
2. 如果不是最底层，chainID的计算公式为：chainID(n)=SHA256(chain(n-1) diffID(n))，也就是第n层的chainID根据父层的chainID加上一个空格和当前的diffID，再计算SHA256摘要。

根据计算公式，haproxy对应的chainID分别为：
第一层：6744ca1b11903f4db4d5e26145f6dd20f9a6d321a7f725f1a0a7a45a4174c579
第二层：68972fe3e03c5b26652f08aa8af0b06702c02208f987da2b1b873e057d456467
```bash
# echo -n "sha256:6744ca1b11903f4db4d5e26145f6dd20f9a6d321a7f725f1a0a7a45a4174c579 sha256:885806cf466d56e36824a1623f362349202c6e4e8f7aab64e174519b66484fea"|sha256sum -
68972fe3e03c5b26652f08aa8af0b06702c02208f987da2b1b873e057d456467  -
```
第三层：b5e0c75383b6d3a7dc43abebb31431017676f1e4209d4704963f52ce0b32b96b
```bash
# echo -n "sha256:68972fe3e03c5b26652f08aa8af0b06702c02208f987da2b1b873e057d456467 sha256:28de19851da2a6dbe597cf23e1637b14d4c51f7074ae01dd9818e131c62e430e"|sha256sum -
b5e0c75383b6d3a7dc43abebb31431017676f1e4209d4704963f52ce0b32b96b  -
```
以第二层为例，查看第二层的目录/var/lib/docker/image/overlay2/layerdb/sha256/68972fe3e03c5b26652f08aa8af0b06702c02208f987da2b1b873e057d456467
```bash
# tree -L 1 68972fe3e03c5b26652f08aa8af0b06702c02208f987da2b1b873e057d456467
68972fe3e03c5b26652f08aa8af0b06702c02208f987da2b1b873e057d456467
├── cache-id
├── diff
├── parent
├── size
└── tar-split.json.gz
```
- **cache-id**：由宿主机随即生成的一个uuid，与镜像层文件一一对应，指向真正存放 layer 文件的地方；
```bash
# more cache-id 
9c58547be8d230a221107f2ac644c713eb9b8c820e1a22b351ce3e686b730b1b
```
- **diff**：镜像层校验ID、根据该镜像层的打包文件校验获得；
```bash
# more diff
sha256:885806cf466d56e36824a1623f362349202c6e4e8f7aab64e174519b66484fea
```

- **parent**：父镜像层的chainID(最底层不含该文件)；
```bash
# more parent
sha256:6744ca1b11903f4db4d5e26145f6dd20f9a6d321a7f725f1a0a7a45a4174c579
```

- **size**：当前layer的大小，单位是字节；
```bash
# more size
16815636
```
- **tar-split.json.gz**：layer 压缩包的 split 文件，通过这个文件可以还原 layer 的 tar 包，详情可参考 https://github.com/vbatts/tar-split。

#### 2.3.2 容器可读写层
容器可读写层在容器启动之后挂载在以容器id为目录的目录下。
```bash
# docker run -it --name HAProxy -p 6301:6301 haproxy /bin/bash
# docker ps 
CONTAINER ID        IMAGE               COMMAND                  CREATED             STATUS              PORTS                    NAMES
3c262b6de295        haproxy             "/docker-entrypoint.…"   19 seconds ago      Up 18 seconds       0.0.0.0:6301->6301/tcp   HAProxy
```
根据haproxy的容器3c262b6de295(前12位)，查看/var/lib/docker/image/overlay2/layerdb/mounts/3c262b6de2955f531994d547f2902752bf52f88f1172ca0c6c29fbfa60ac4b7a目录：
```bash
# tree -L 1 3c262b6de2955f531994d547f2902752bf52f88f1172ca0c6c29fbfa60ac4b7a
3c262b6de2955f531994d547f2902752bf52f88f1172ca0c6c29fbfa60ac4b7a/
├── init-id
├── mount-id
└── parent
```

- **init-id**：容器init层的mount-id，指向了layer数据文件目录；
```bash
# more init-id
c3deeb4325373415ca2d2043aed5b28c5098169e72b3f25788b1d5eb1b4f420e-init
```

- **mount-id**：读写层的mount-id，指向了layer数据文件目录；
```bash
# more mount-id
c3deeb4325373415ca2d2043aed5b28c5098169e72b3f25788b1d5eb1b4f420e
```

- **parent**：容器层的父镜像层的chainID，对应只读层中的最顶层即第三层。
```bash
# more parent
sha256:b5e0c75383b6d3a7dc43abebb31431017676f1e4209d4704963f52ce0b32b96b
```

根据

## 3、layer数据文件
layer镜像分层的数据文件存储在/var/lib/docker/overlay2/{mount-id}/下，根据元数据目录下的cache-id就是mount-id，如下所示：
```bash
# more 6744ca1b11903f4db4d5e26145f6dd20f9a6d321a7f725f1a0a7a45a4174c579/cache-id
367818b00c1569667c3f0eb8b0580c770251612d4ab16a477c5349dd20a6fd65
```

### 3.1 最底层layer本地文件
chainId为6744ca1b11903f4db4d5e26145f6dd20f9a6d321a7f725f1a0a7a45a4174c579的layer对应的cacheID为367818b00c1569667c3f0eb8b0580c770251612d4ab16a477c5349dd20a6fd65，查看/var/lib/docker/overlay2/367818b00c1569667c3f0eb8b0580c770251612d4ab16a477c5349dd20a6fd65：
```bash
# tree -L 2 367818b00c1569667c3f0eb8b0580c770251612d4ab16a477c5349dd20a6fd65/
367818b00c1569667c3f0eb8b0580c770251612d4ab16a477c5349dd20a6fd65/
├── diff
│   ├── bin
│   ├── boot
│   ├── dev
│   ├── etc
│   ├── home
│   ├── lib
│   ├── lib64
│   ├── media
│   ├── mnt
│   ├── opt
│   ├── proc
│   ├── root
│   ├── run
│   ├── sbin
│   ├── srv
│   ├── sys
│   ├── tmp
│   ├── usr
│   └── var
└── link
```

- **diff**：该目录存放了真实的数据；
- **link**：该文件存放了该层的符号链接名称，该符号链接更短，主要用来避免挂载时超出页面大小的限制，指向diff目录；
```bash
# more link
7UCN35ON2ZKX3DX5BA2E6NIBNF
```

符号链接定义如下：
```bash
# ll l/7UCN35ON2ZKX3DX5BA2E6NIBNF
l/7UCN35ON2ZKX3DX5BA2E6NIBNF -> ../367818b00c1569667c3f0eb8b0580c770251612d4ab16a477c5349dd20a6fd65/diff/
```

### 3.2 第二层Layer本地文件
```bash
# tree -L 1 9c58547be8d230a221107f2ac644c713eb9b8c820e1a22b351ce3e686b730b1b/
9c58547be8d230a221107f2ac644c713eb9b8c820e1a22b351ce3e686b730b1b/
├── diff
├── link
├── lower
└── work
```
- 在第二层多了一个lower文件及work目录，其中lower文件内容是所有祖先layer diff目录的短符号链接名称， work 目录则是用来完成如 copy-on_write 的操作。
```bash
# more lower
l/7UCN35ON2ZKX3DX5BA2E6NIBNF
```
文件的内容即为父层diff目录的短符号连接文件。

第三层同第二层，略

### 3.3 init层本地文件
根据init-id文件中的内容，定位到该本地文件目录：
```bash
# tree -L 1 c3deeb4325373415ca2d2043aed5b28c5098169e72b3f25788b1d5eb1b4f420e-init
c3deeb4325373415ca2d2043aed5b28c5098169e72b3f25788b1d5eb1b4f420e-init/
├── diff
├── link
├── lower
└── work
```
- lower文件存放了三个只读层的符号链接文件；
```bash
# more lower
l/FU73TC6QKNZAZFGL5OLEHODVJY:l/Z34ST5SRLSB2UZTL6AUMICY7NI:l/7UCN35ON2ZKX3DX5BA2E6NIBNF
```

### 3.4 读写层本地文件
```bash
# tree -L 1 c3deeb4325373415ca2d2043aed5b28c5098169e72b3f25788b1d5eb1b4f420e
c3deeb4325373415ca2d2043aed5b28c5098169e72b3f25788b1d5eb1b4f420e
├── diff
├── link
├── lower
├── merged
└── work
```
- **lower** ：该文件存放了init层及三个只读层diff目录的短符号链接文件名称；
- **merged** ：每当启动一个容器时，会将 link 指向的镜像层目录以及 lower 指向的镜像层目录联合挂载到 merged 目录，因此，容器内的视角就是 merged 目录下的内容。

## 4 结论
通过镜像文件的元数据信息我们可以找到分层Layer及本地数据文件之间的关联，对理解docker文件系统有很大的帮助：
1. 在本地镜像仓库文件repositories.json找到镜像的imageid，根据imageid找到image的元数据配置文件；
2. 在image元数据配置文件rootfs元素中找到layer的diffid;
3. 根据计算公式，将diffid转化为chaninid，chainid即为只读分层元数据文件的目录；
4. 在chainid目录下，cache-id文件存储了该分层数据文件的挂载目录cacheid；
5. 根据cacheid在overlays存储驱动下即可找到该层的数据文件；
6. 根据启动之后的contanerid,找到可读写层的元文件目录，init-id文件内容即为init层的挂载目录，而mount-id即为可读写层的挂载目录；
7. 根据可读写层的挂载目录即可找到相应的数据文件。
