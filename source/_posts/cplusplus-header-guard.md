---
title: C++系列：头文件保护符
date: 2024-07-30 17:55:58
updated: 2024-07-30 17:55:58
tags:
- c++ 语言
- 头文件保护符
- header guard
categories: 
- 笔记
---

这篇文章介绍头文件保护符 (header guard)。

<!-- more -->

## 概述

为了确保各个文件中类的定义一致，通常将类, const 和 constexpr 变量放在头文件中，而将类方法的实现放在 cpp 文件中。

另外一方面，为了确保头文件多次包含仍能正常工作，C++程序还会用到一项预处理功能：头文件保护符(header guard), 头文件保护符依赖于预处理变量。预处理变量有两种状态：已定义和未定义。 #define 指令把一个名字设定为预处理变量，另外两个指令则分别检查某个指定的预处理变量是否已经定义：#ifdef 当且仅当变量已定义时为真，#ifndef 当且仅当变量未定义时为真。一旦检查结果为真，则执行后续操作直至遇到 #endif 指令为止。

使用这些功能就能有效地防止包含的发生(Sales_data.h)：
```c++
#ifndef SALES_DATA_H
#define SALES_DATA_H
#include <string>

struct Sales_data {
    std::string bookNo;
    unsigned units_sold = 0;
    double revenue = 0.0;
}
#endif
```
第一次包含 Sales_data.h 时，#ifndef 的检查结果为真，预处理器将顺序执行后面的操作直至遇到 #endif 为止。此时，预处理变量 SALES_DATA_H 的值将变为已定义，而且 Sales_data.h 也会被拷贝到我们的程序中来。后面如果再一次包含 Sales_data.h, 则 #ifndef 的检查如果将为假，编码器将忽略 #ifndef 到 #endif 之间的部分。

整个程序中的预处理变量必须唯一，通常的做法是基于头文件中类的名字来构建保护的名字，以确保其唯一性。为了避免与程序中的其它实体发生名字冲突，一般把预处理变量的名字全部大写。

