---
title: Nvm 和 Npm 常用命令
date: 2025-04-13 18:44:21
updated: 2025-04-13 18:44:21
tags:
- nodejs
- nvm
- npm
categories:
- 前端
---

这篇文章讲述 Nvm 和 Npm 的常用命令。

<!-- more -->

# 概述

日常开发中经常会遇到这种情况：手上有好几个项目，每个项目的需求不同，进而不同项目必须依赖不同版的 NodeJS 运行环境。如果没有一个合适的工具，这个问题将非常棘手。nvm 应运而生，nvm是node.js版本管理工具。一句话来描述，nvm 和 npm 都是 node.js应用程序开发的常用工具。nvm是node.js版本管理工具，npm是JavaScript包管理工具。

# Nvm命令

## Nvm常用命令 

```bash
# 安装最新的版本
nvm install latest

#卸载某个版本
nvm uninstall 版本号

#查看当前版本
nvm version 或 nvm current

# 安装的版本列表
nvm list

# 切换版本
nvm use 版本号
```

## 安装多版本 node/npm

安装4.2.2版本，可以用如下命令：
```bash
nvm install 4.2.2
```

## 在Node不同版本间切换

每当我们安装了一个新版本 Node 后，全局环境会自动把这个新版本设置为默认。

nvm 提供了 nvm use 命令。这个命令的使用方法和 install 命令类似。

例如，切换到 4.2.2：
```bash
nvm use 4.2.2
```

## 列出已安装实例
```bash
nvm ls
```

## 在项目中使用不同版本的 Node

可以通过创建项目目录中的 .nvmrc 文件来指定要使用的 Node 版本。之后在项目目录中执行 nvm use 即可。.nvmrc 文件内容只需要遵守上文提到的语义化版本规则即可。

在多环境中，使用npm

每个版本的 Node 都会自带一个不同版本的 npm，可以用 npm -v 来查看 npm 的版本。全局安装的 npm 包并不会在不同的 Node 环境中共享，因为这会引起兼容问题。它们被放在了不同版本的目录下，例如 `~/.nvm/versions/node/<version>/lib/node_modules</version>` 这样的目录。这刚好也省去我们在 Linux 中使用 sudo 的功夫了。因为这是用户的主文件夹，并不会引起权限问题。

但问题来了，我们安装过的 npm 包，都要重新再装一次？幸运的是，我们有个办法来解决我们的问题，运行下面这个命令，可以从特定版本导入到我们将要安装的新版本 Node：
```bash
nvm install v5.0.0 --reinstall-packages-from=4.2
```

# Npm命令

## Npm常用命令
```bash
# 查看当前npm版本
npm -v

# 安装包
npm install 包名
npm install 包名 -g : 全局安装，安装后在命令行任意目录下可直接使用包命令

# 更新包
npm install 包名@latest

# 卸载包 
npm uninstall 包名
```

## 查看版本
```bash
# 查看所有的版本
npm view jquery versions

# 查看最新的版本
npm view jquery version

# 查看指定版本支持的 node 版本
npm view grunt-cli@1.3.2 engines

# 查看当前安装的版本
npm ls jquery 

# 查看当前全局安装的版本
npm ls jquery -g 
```


