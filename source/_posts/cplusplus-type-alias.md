---
title: C++系列：类型别名
date: 2024-07-30 17:55:48
updated: 2024-07-30 17:55:48
tags:
- c++ 语言
- 类型别名
categories: 
- 笔记
---

这篇文章介绍类型别名。

<!-- more -->

## 概念

类型别名（type alias）是一个名字，这是某种类型的同义词。使用类型别名有很多好处，它让复杂的类型名字变得简单明了、易于理解和使用，还有助于程序员清楚地知道使用该类型的真实目的。

有两种方法可用于定义类型别名。传统的方法是使用关键字 typedef:
```c++
typedef double wages;     // wages 是double 的同义词
typedef wages base, *p;   // base 是 double 的同义词，p 是 double* 的同义词
```

C++ 11 新标准规定了一种新的方法，使用别名声明（alias declaration）来定义类型的别名：
```c++
using SI = Sales_item; // SI 是 Sales_item 的同义词
```

这种方法用关键字 using 作为别名声明的开始，其后紧跟别名和等号，其作用是把等号左侧的名字规定成等号右侧类型的别名。
