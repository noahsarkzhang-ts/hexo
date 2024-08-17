---
title: C++系列：constexpr 函数
date: 2024-07-30 17:56:21
updated: 2024-07-30 17:56:21
tags:
- c++ 语言
- constexpr 函数
categories: 
- 笔记
---

这篇文章主要讲述 constexpr 函数 (constexpr function)。

<!-- more -->

## constexpr 函数
constexpr 函数(constexpr function) 是指能用于常量表达式的函数。定义 constexpr 函数的方法与其它函数类似，不过要遵循几项约定：函数的返回类型及所有形参的类型都得是字面值类型，而且函数体中必须有且只有一条 return 语句：
```c++
constexpr int new_sz() { return 42; }
constexpr int foo = new_sz();   // 正确： foo 是一个常量表达式
```

我们把 new_sz 定义成无参数的 constexpr 函数。因为编译器能在程序编译时验证 new_sz 函数返回的是常量表达式，所以可以用 new_sz 函数初始化 constexpr 类型的变量 foo.

执行该初始化任务时，编译器把 constexpr 函数的调用替换成其结果值。为了能在编译过程中随时展开，constexpr 函数被隐式地指定为内联函数。

constexpr 函数体内也可以包含其他语句，只要这些语句在运行时不执行操作就行。例如，constexpr 函数中可以有空语句、类型另名以及 using 声明。

我们允许 constexpr 函数的返回值并非一个常量：
```c++
// 如果 arg 是常量表达式，则 scale(arg) 也是常量表达式
constexpr size_t scale(size_t cnt) { return new_sz() * cnt; }
```

当 scale 的实参是常量表达式时，它的返回值也是常量表达式；反之则不然：
```c++
int arr[scale(2)];      // 正确：scale(2) 是常量表达式
int i = 2;              // i 不是常量表达式
int a2[scale(i)];       // 错误：scale(i) 不是常量表达式
```

如上例所示，当我们给 scale 函数传入一个形如字面值 2 的常量表达式时，它的返回类型也是常量表达式。此时，编译器用相应的结果值替换对 scale 函数的调用。

如果我们用一个非常量表达式调用 scale 函数，比如 int 类型的对象 i, 则返回值是一个非常量表达式。当把 scale 函数用在需要常量表达式的上下文中时，由编译器负责函数的结果是否符合要求。如果结果恰好不是常量表达式，编译器将发出错误信息。

>> constexpr 函数不一定返回常量表达式。

## 把内联函数和 constexpr 函数放在头文件内
和其它函数一样，内联函数和 constexpr 函数可以在程序中多次定义。毕竟，编编译器要想展开函数仅有函数声明是不够的，还需要函数的定义。不过，对于某个给定的内联函数或者 constexpr 函数来说，它的多个定义必须安全一致。基于这个原因，内联函数和 constexpr 函数通常定义在头文件中。


