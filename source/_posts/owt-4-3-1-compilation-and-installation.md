---
title: OWT 4.3.1 编译与安装
date: 2025-04-13 11:21:19
updated: 2025-04-13 11:21:19
tags:
- owt
- webrtc
- mcu
- sfu
categories:
- 音视频
---

这段时间在学习开源的直播和会议项目，发现了一个宝藏的项目，它是由 Intel 团队开源的会议项目，支持 MCU 和 SFU 模式。它为想要了解和学习会议的人提供了一个较好的机会，深度理解 MCU 的底层的实现，包括混音和混屏相关知识。这篇文章主要讲述 OWT 4.3.1 的编译与安装，并指出安装过程中碰到的问题，后续有时间继续分析其结构和代码。

<!-- more -->

# OWT 介绍
OWT 是 Intel 前些年开源的基于互联网的视频会议解决方案，可以支持 WebRTC 和 SIP 终端。这几年 WebRTC 应用的特别广泛，使用 OWT 可以快速搭建一个WebRTC视频会议系统。OWT 最初仅支持 MCU 模式，也就是服务器混流，客户端仅可订阅一路音视频即可，后来新版本也支持 SFU 模式。

OWT 项目地址: <https://github.com/open-webrtc-toolkit> , 包含服务器端 OWT-Server 和 各种客户端程序。

# OWT 编译环境
## 前提条件
1. 编译环境使用 `Ubuntu 18`; 
2. OWT 依赖比较多的第三方库，需要访问外网，建议安装一个稳定的 VPN;
3. node 使用 node 8.15.0 版本。

## 编译环境
编译环境使用是 `Ubuntu 18.04.6 LTS` 版本，其它版本没有测试，官方建议使用 `Ubuntu 18` 版本。

```bash
lsb_release -a

No LSB modules are available.
Distributor ID: Ubuntu
Description:    Ubuntu 18.04.6 LTS
Release:        18.04
Codename:       bionic
```

# OWT Server 源码编译

安装使用 `root` 账户，避免一些权限问题

## 下载 Owt server 4.3.1
```bash
mkdir /app
cd /app
wget https://github.com/open-webrtc-toolkit/owt-server/archive/refs/tags/v4.3.1.tar.gz -O owt-server-4.3.1.tar.gz
tar -xzvf owt-server-4.3.1.tar.gz
```

## 编译 Owt server
```bash
cd /app/owt-server-4.3.1/scripts
./installDepsUnattended.sh
npm install -g node-gyp@6.1.0 graceful-fs grunt-cli@1.3.2
./scripts/build.js -t mcu --check
```

**说明**

- 脚本文件中第三方库 zlib 下载地址已经失效，需要更改为 `https://github.com/madler/zlib/releases/download/v1.2.13/zlib-1.2.13.tar.gz`，在脚本文件 `installCommonDeps.sh` 中进行修改; 
- GitHub README 上写的是 -t all，但对于没有硬件加速需求/环境的情况，这样 build 会失败，对于不需要硬件加速的情况，-t mcu 即可；

# 编译 owt-client-javascript
## 下载 owt-client-javascript 4.3.1
```bash
wget https://github.com/open-webrtc-toolkit/owt-client-javascript/archive/refs/tags/v4.3.1.tar.gz -O owt-client-javascript-4.3.1.tar.gz
tar -xzvf owt-client-javascript-4.3.1.tar.gz
```

## 编译 owt-client-javascript 4.3.1
```bash
cd /app/owt-client-javascript-4.3.1/scripts
npm install --unsafe-perm && grunt
```

说明：在安装过程中会提示权限不足，需要在 `npm install ` 命令加上参数 `--unsafe-perm`。

## 碰到的问题
### process.allowedNodeEnvironmentFlags 为空

报错信息：
```bash
/usr/local/lib/nodejs/node-v8.15.0-linux-x64/lib/node_modules/grunt-cli/node_modules/v8flags/index.js:84
  var flags = Array.from(process.allowedNodeEnvironmentFlags);
                    ^

TypeError: Cannot convert undefined or null to object
    at Function.from (native)
    at getFlags (/usr/local/lib/nodejs/node-v8.15.0-linux-x64/lib/node_modules/grunt-cli/node_modules/v8flags/index.js:84:21)
    at /usr/local/lib/nodejs/node-v8.15.0-linux-x64/lib/node_modules/grunt-cli/node_modules/v8flags/index.js:142:5
    at /usr/local/lib/nodejs/node-v8.15.0-linux-x64/lib/node_modules/grunt-cli/node_modules/v8flags/index.js:47:14
    at /usr/local/lib/nodejs/node-v8.15.0-linux-x64/lib/node_modules/grunt-cli/node_modules/v8flags/index.js:70:14
    at FSReqWrap.oncomplete (fs.js:135:15)
```
原因分析：

当前 node 版本为 v8.15.0，grunt-cli 版本为 v1.5.0，grunt-cli v1.5.0 版本中，会调用 node process.allowedNodeEnvironmentFlags 方法，而 process.allowedNodeEnvironmentFlags 于 node v10.10.0 中引入，当前使用的node 版本为 v8.15.0，低于引入的版本。

解决办法：
```bash
升级 node 版本或降低 grunt-cli 版本，为了降低影响的范围，选择降低 grunt-cli 版本，降至 v1.3.2。
# 卸载 grunt-cli
npm uninstall grunt-cli -g
# 安装 grunt-cli
npm install grunt-cli@1.3.2 -g
```

### 降低 express 版本
过高的 express 版本依赖的 node 版本超过 node 8.15.0，需要降低 express 以匹配 node 版本。修改 `/app/owt-client-javascript-4.3.1/src/samples/conference/package.json` 文件，将 express 版本指定为 `4.16.4`，如下代码所示：

```json
{
  "name": "oms-sample-conference",
   ...
  "dependencies": {
    "body-parser": "~1.14.1",
    "errorhandler": "",
    "express": "4.16.4",
    "morgan": "",
    "socket.io": "^2.2.0",
    "spdy": ""
  },
  "engines": {
    "node": ">=0.10"
  }
}
```

# 打包 owt-server
执行如下打包命令：
```bash
cd /app/owt-server-4.3.1
./scripts/pack.js -f -s /app/owt-client-javascript-4.3.1/dist/samples/conference/
```

## 碰到的问题
### npm 版本过低
问题描述： invalid dependency type requested: alias.

报错信息：
```bash
npm ERR! Invalid dependency type requested: alias
```

原因分析：

npm 版本过低，从 npm v6.9.0 开始，正式支持依赖别名的功能。当前的 npm 版本低于这个版本，所以如果需要使用别名功能，需要升级 npm。

解决办法：

升级支持别名的 npm 版本，如 v6.14.0。可以使用以下命令来升级 npm：
```bash
npm install -g npm@6.14.0
```

### node 版本过低

问题描述：模块依赖的 node 版本过高，超过了当前版本。

报错信息：
```bash
npm WARN notsup Unsupported engine for express@5.1.0: wanted: {"node":">= 18"} (current: {"node":"8.15.0","npm":"6.14.0"})
npm WARN notsup Not compatible with your version of node/npm: express@5.1.0
npm WARN notsup Unsupported engine for body-parser@2.2.0: wanted: {"node":">=18"} (current: {"node":"8.15.0","npm":"6.14.0"})
npm WARN notsup Not compatible with your version of node/npm: body-parser@2.2.0
npm WARN notsup Unsupported engine for merge-descriptors@2.0.0: wanted: {"node":">=18"} (current: {"node":"8.15.0","npm":"6.14.0"})
npm WARN notsup Not compatible with your version of node/npm: merge-descriptors@2.0.0
npm WARN notsup Unsupported engine for router@2.2.0: wanted: {"node":">= 18"} (current: {"node":"8.15.0","npm":"6.14.0"})
npm WARN notsup Not compatible with your version of node/npm: router@2.2.0
npm WARN notsup Unsupported engine for send@1.2.0: wanted: {"node":">= 18"} (current: {"node":"8.15.0","npm":"6.14.0"})
npm WARN notsup Not compatible with your version of node/npm: send@1.2.0
npm WARN notsup Unsupported engine for serve-static@2.2.0: wanted: {"node":">= 18"} (current: {"node":"8.15.0","npm":"6.14.0"})
npm WARN notsup Not compatible with your version of node/npm: serve-static@2.2.0
npm WARN notsup Unsupported engine for path-to-regexp@8.2.0: wanted: {"node":">=16"} (current: {"node":"8.15.0","npm":"6.14.0"})
npm WARN notsup Not compatible with your version of node/npm: path-to-regexp@8.2.0
npm WARN notsup Unsupported engine for socket.io-parser@3.4.3: wanted: {"node":">=10.0.0"} (current: {"node":"8.15.0","npm":"6.14.0"})
npm WARN notsup Not compatible with your version of node/npm: socket.io-parser@3.4.3
```

原因分析：

由于在前端项目中，未指定相关模块如 express 的版本，便会下载当前最新的版本，而当前最新的版本需要较高的 node 版本。

解决办法：

降低模块版本，以便支持 node 8.15.0 版本。

修改 `/app/owt-server-4.3.1/source/management_api/package.jsnon`, 将 experss 指定为 `4.16.4` 版本，body-parser 指定为 `1.18.3` 版本，如下所示：

```json
{
  "name": "OWT-MCU-Management-API",
  "version":"4.3.1",
  "dependencies": {
    "amqp": "*",
    "log4js": "^1.1.1",
    "express": "4.16.4",
    "mongojs": "",
    "toml": "*",
    "ajv": "^5.2.2",
    "body-parser": "1.18.3",
    "mongoose": "^4.13.6",
    "fraction.js": "^4.0.12"
  },
  "engine": {
    "node": "8.15.0"
  },
  "bin": "server.js",
  "pkg": {
    "assets": [
      "node_modules*"
    ],
    "targets": [
      "node8"
    ]
  }
}
```

修改 `/app/owt-server-4.3.1/source/sip_portal/package.jsnon`, 将 fraction.js 指定为 `^4.0.12` 版本，如下所示：
```json
{
  "name": "OWT-MCU-SIP-Portal",
  "version":"4.3.1",
  "dependencies": {
    "amqp": "*",
    "log4js": "^1.1.1",
    "toml": "*",
    "mongoose": "^4.13.6",
    "fraction.js": "^4.0.12"
  },
  "bin": "sip_portal.js",
  "pkg": {
    "assets": [
      "node_modules*"
    ],
    "targets": [
      "node8"
    ]
  }
}
```

# 配置 owt-server
配置、运行都是在 dist 目录下，运行 Owt 需要设置 ip 地址，假定真实 ip 为  192.168.56.109, 网卡为 enp0s8，修改如下两个地方：

```bash
# vi dist/webrtc_agent/agent.toml
[webrtc]
network_interfaces = [{name="enp0s8",replaced_ip_address="192.168.56.109"}]  # default: []

# The webrtc port range
maxport = 60050 #default: 0
minport = 60000 #default: 0

# vi dist/portal/portal.toml
[portal]
ip_address = "192.168.56.109" #default: ""
```

其中，maxport 和 minport 配置 udp 端口的范围。

# 运行 owt-server

执行如下命令：
```bash
(cd dist && ./bin/init-all.sh && ./bin/start-all.sh)
```

打开默认演示页面 `https://192.168.56.109:3004/` ，由于使用自签名证书，首次打开会提示证书验证。管理后台地址为 `https://192.168.56.109:3300/console`, 使用启动服务时打印的 sampleServiceId 和sampleServiceKey 便可登录查看。

# 修改源码
修改 js 代码，只需要重新打包就行，修改 C++ 代码则需要重新编译代码，执行 `./scripts/build.js -t mcu --check` 命令。

# node 版本依赖
Owt server 4.3.1 使用的 node 版本为 8.15.0, 该版本较低。在安装过程中，项目依赖的模块有可能依赖较新的 node 版本，为了解决版本的依赖问题，需要清楚当前安装的模块版本及所依赖的 node 版本，不兼容的时候需要降低模块的版本。我们可以通过发下的一些命令看查看这些信息：
```bash
# 查看模块当前安装的版本
npm ls grunt-cli 

# 查看模块当前全局安装的版本
npm ls grunt-cli -g 

# 查看指定版本支持的 node 版本
npm view grunt-cli@1.3.2 engines

# 查看所有的版本
npm view grunt-cli versions

# 查看最新的版本
npm view grunt-cli version

# 删除模块
npm uninstall grunt-cli

# 安装指定版本的模块
npm install grunt-cli@1.3.2
```


**参考：**

----
1. [OWT 安装与初步使用说明](https://blog.csdn.net/sun007700/article/details/108358223)
2. [OWT Server 快速入门](https://blog.piasy.com/2019/04/14/OWT-Server-Quick-Start/index.html)
3. [OWT-DOCKER](https://github.com/winlinvip/owt-docker)
4. [OWT (Open WebRTC Toolkit) 5.0 初体验与开发环境搭建](https://blog.csdn.net/shaosunrise/article/details/120145318)


