---
title: Hexo 和 Next 升级
date: 2023-06-28 14:44:47
updated: 2023-06-28 14:44:47
tags:
- hexo 升级
- next 升级
categories:
- 博客
---

由于前段时间把 Node.js 升级到了 v16.19.1, 导致 Hexo 3.9.0 和 Next 6.5.0 在该 Node.js 版本下有问题，生成的 html 文件为空。所以将 Hexo 和 Next 升级到与 Node.js 最新匹配的版本，即 Hexo 升级到 6.3.0, Next 升级到 8.17.0. 

<!-- more -->
## 整体策略

在 Hexo 6.3.0 及 Next 8.17.0 版本下构建新项目，再将老项目的配置信息及 md 源文件同步到新项目中，验证没有问题之后，最后将配置文件及新模板文件拷贝到老项目即可。

**说明：** 由于新老版本中对同一个配置项的设置方法有可能已经改动，不能直接拷贝覆盖。

## 软件升级

### 卸载老版本 Hexo

将老版本的 hexo-cli 进行卸载。

```bash
$ npm uninstall -g hexo-cli
```

### 升级 Hexo 新版本

Hexo 升级到最新的版本。

```bash
$ npm install -g hexo-cli
```

### 初始化项目

以新版本初始化新项目 `new_blog`.

```bash
$ hexo init new_blog
```
查看版本信息，Hexo 已经升级到 6.3.0.

```bash
$ hexo -v
INFO  Validating config
hexo: 6.3.0
hexo-cli: 4.3.1
os: win32 10.0.17763
node: 16.19.1
v8: 9.4.146.26-node.24
uv: 1.43.0
zlib: 1.2.11
brotli: 1.0.9
ares: 1.18.1
modules: 93
nghttp2: 1.47.0
napi: 8
llhttp: 6.0.10
openssl: 1.1.1t+quic
cldr: 41.0
icu: 71.1
tz: 2022f
unicode: 14.0
ngtcp2: 0.8.1
nghttp3: 0.7.0
```

## 同步文件

### 同步博客文件

将老项目中 source 目录下的文件拷贝到新项目中，其结构如下所示：

```bash
source
├─_posts
├─about
├─categories
├─images
├─tags
└─404
```

**说明：**
- _posts: 存放博客 md 文件；
- about: 存放 “关于” 菜单首页文件；
- categories: 存放 “分类” 菜单首页文件；
- tags: 存放 “标签” 菜单首页文件；
- 404: 存放 “公益404” 菜单首页文件；
- images: 存放图片文件。

### 同步 Next 模板文件

从 github 官网下载 [Next 8.17.0 文件](https://github.com/next-theme/hexo-theme-next/releases/tag/v8.17.0). 解压缩存放到 themes 目录下，并将其命名为 `next-8.17.0`.

## 同步配置信息

将老项目中 Hexo 及 Next 配置信息同步到新项目中。

### 同步 Hexo _config.yml

根据需要，将网站的基本信息，发布信息及模板信息同步到  Hexo _config.yml 文件中，模板指定为 `next-8.17.0`, 即 themes 目录下 Next 模板的目录名。如下所示：

```yaml
# 网站信息
title: 
subtitle: ''
description: ''
keywords: 
author: 

# 语言及时区
language: zh-CN
timezone: ''

# 主题
theme: next-8.17.0

# 部署信息
deploy:
  type: git
  repo: 
  branch: master

```

### 同步 Next _config.yml

根据老项目的配置，将网站的风格，菜单，Sidebar 位置，访客统计及赞赏信息同步到新项目中，如下所示：

```yaml
# 指定风格
scheme: Mist

# 设置菜单
menu:
  home: / || fa fa-home
  tags: /tags/ || fa fa-tags
  categories: /categories/ || fa fa-th
  archives: /archives/ || fa fa-archive
  about: /about/ || fa fa-user
  #schedule: /schedule/ || fa fa-calendar
  #sitemap: /sitemap.xml || fa fa-sitemap
  commonweal: /404/ || fa fa-heartbeat

# 设置 sidebar
sidebar:
  position: right
  display: post
  padding: 18
  offset: 12

# 设置赞赏
reward:
  wechatpay: /images/wechatpay.jpg
  alipay: /images/alipay.jpg

# 设置访客统计
busuanzi_count:
  enable: true
  total_visitors: true
  total_visitors_icon: fa fa-user
  total_views: true
  total_views_icon: fa fa-eye
  post_views: true
  post_views_icon: far fa-eye

```

### 同步备案信息

由于我在页脚中加入了网站的备案信息，需要修改 `themes\next-8.17.0\layout\_partials\footer.njk` 布局文件，如下所示：

```html
<div class="copyright">
...
</div>

<div class="BbeiAn-info">
    <a target="_blank" href="https://beian.miit.gov.cn/"  rel="nofollow">粤ICP备 20210XXXXXXXX </a>
	<a target="_blank" href="http://www.beian.gov.cn/portal/registerSystemInfo?recordcode=自己的备案号" style="text-decoration:none;padding-left:30px;background:url(https://s1.ax1x.com/2018/09/29/ilmwIH.png) no-repeat left center" rel="nofollow">{{ __('粤公网安备 自己的备案号') }}</a>
</div>
```

在版权模块下面加入备案信息。

## 验证并更新老项目

在新项目中重新生成页面，验证成功之后，将配置信息及模板文件更新覆盖老项目，更新的文件及目录有：

```bash
new_blog
├─_config.yml
├─package.json
└─themes

```

最后将文件推送到 git 便完成了升级流程


## 踩坑记录

在新版本中，如果博客 md 文件 title 字段包含特殊字符，如 % ，则生成操作会失败。修改的办法也简单，将特殊字符移除即可。