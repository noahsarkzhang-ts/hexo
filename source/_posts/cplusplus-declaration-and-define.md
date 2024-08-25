---
title: C++系列：声明及定义
date: 2024-07-30 17:55:24
updated: 2024-07-30 17:55:24
tags:
- c++ 语言
- 变量声明
- 变量定义
categories: 
- 笔记
---

这篇文章介绍变量声明与定义的概念。
<!-- more -->

## 概念

为了允许把程序拆分成多个逻辑部分来编写，C++ 语言支持分离式编译(separate compilation) 机制，该机制允许将程序分割为若干文件，每个文件可被独立编译。

如果将程序分为多个文件，则需要有在文件间共享代码的方法。例如，一个文件的代码可能需要使用另一个文件中定义的变量。一个实际的例子是 std::cout 和 std::cin, 它们定义于标准库，却能被我们的程序使用。

为了支持分离线编译，C++ 语言将声明和定义区分开来。声明(declaration) 使得名字为程序所知，一个文件如果想使用别处定义的名字则必须包含对那个名字的声明。而定义(definition) 负责创建与名字关联的实体。

变量声明规定了变量的类型和名字，在这一点上定义与之相同。但是除此之外，定义还申请存储空间，也可能会为变量赋一个初始值。

如果想声明一个变量而非定义它，就在变量名前添加关键字 extern, 而且不要显式地初始化变量：
```c++
extern int i;       // 声明 i 而非定义 i
int j;              // 声明并定义了 j
```

任何包含了显式初始化的声明即成为定义。我们能给由 extern 关键字标记的变量赋一个初始值，但是这么做也就抵消了 extern 的作用。extern 语句如果包含初始值就不再是声明，而变成定义了：
```c++
extern double pi = 3.1416;      // 定义
```

在函数体内部，如果试图初始化一个由 extern 关键字标记的变量，将引发错误。