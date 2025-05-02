---
title: Springboot 脚手架
date: 2025-04-26 17:38:36
updated: 2025-04-26 17:38:36
tags:
- springboot
- 脚手架
categories:
- 脚手架
---

在日常开发中，同一类型的项目使用的框架、目录结构及开发模式是及其相似的，为了避免做重复的工作，对项目中相似的模块进行抽象提取，组成一个脚手架程序。这篇文章则是介绍自己总结出来的后台 Springboot 脚手架，它包含了一些常用的工具类，并且引入代码生成机制来提高开发效率。

<!-- more -->

## 功能介绍

1. 常用工具类，如日期，Json等等；
2. 国际化处理；
3. 统一的异常处理；
4. 请求日志处理；
5. Token 缓存管理类，结合缓存保证 token 的有效性；
6. 定义一套编码风格；
7. 加入代码生成器。

**Github代码：**[springboot-scaffolding](https://github.com/noahsarkzhang-ts/alligator-scaffolding/tree/main/springboot-scaffolding) 

