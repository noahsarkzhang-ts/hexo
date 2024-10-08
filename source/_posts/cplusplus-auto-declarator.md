---
title: C++系列：auto 类型说明符
date: 2024-07-30 17:54:01
updated: 2024-07-30 17:54:01
tags:
- c++ 语言
- 类型说明符
- decltype
categories: 
- 笔记
---

这篇文章介绍 auto 类型说明符。

<!-- more -->

## 概述

编程时常常需要把表达式的值赋给变量，这就要求在声明变量的时候清楚地知道表达式的类型。然而要做到这一点并非那么容易，有时甚至根据做不到。为这解决这个问题，C++11 新标准引入了 auto 类型说明符，用它就能让编译器替我们去分析表达式所属的类型。和原来那些只对应一种特定的说明符（比如 double）不同，auto 让编译器通过初始值来推算变量的类型。显然，auto 定义的变量必须有初始值：
```c++
// 由val1和val2相加的结果推断出item的类型
auto item = val1 + val2; // item 初始化为 val1 和 val2 相加的结果
```

此处编译器将根据 val1 和 val2 相加的结果来推断 item 的类型，如果 val1 和 val2 是类 Sales_item 的对象，则 item 的类型就是 Sales_item; 如果这两个变量的类型是 double, 则 item 的类型就是 double, 以此类推。

使用 auto 也能在一条语句中声明多个变量。因为一条声明语句只能有一个基本数据类型，所以该语句中所有变量的初始基本数据类型都必须一样：
```c++
auto i = 0, *p = &i; 	  // 正确：i 是整数，p是整型指针
auto sz = 0, pi = 3.14    // 错误：sz 和 pi 的类型不一致
```

**复合类型，常量和 auto**
编译器推断出来的 auto 类型有时候和初始值的类型并不安全一样，编译器会适当地改变结果类型剑使其更符合初始化规则。
首先，正如我们所熟知的，使用引用其实是使用引用的对象，特别是当引用被用作初始值时，真正参与初始化的其实是引用对象的值。此时编译器以引用对象的类型作为 atuo 的类型：
```c++
int i = 0, &r = i;
auto a = r;         // a 是一个整数（r 是 i 的别名，而 i 是一个整数）
```

其次，atuo 一般会忽略掉顶层 const, 同时底层 const 则会保留下来，比如当初始值是一个指向常量的指针时：
```c++
const int ci = i, &cr = ci;
auto b = ci;     // b 是一个整数（ci 的顶层 const 特性被忽略掉了）
auto c = cr;     // c 是一个整数（cr是 ci 的别名，ci 本身是一个顶层const）
auto d = &i；	 // d 是一个整型指针（整数的地址就是指向整数的指针）
auto e = &ci;    // e 是一个指向整数常量的指针（对常量对象取地址是一个底层const）
```

如果希望推断出的 atuo 类型是一个顶层 const, 需要明确指出：
```c++
const auto f = ci;   // ci 的推演类型是 int , f 是 const int
```

还可以将引用的类型设为 auto, 此进原来的初始化规则仍然适用：
```c++
auto &q = ci;         // g是一个整型常量引用，绑定到ci
auto &h = 42;         // 错误：不能为非常量引用绑定字面值
const auto &j = 42;   // 正确：可以为常量引用绑定字面值
```

设置一个类型为 auto 的引用时，初始值中的顶层常量属性仍然保留。和往常一样，如果我们给初始值绑定一个引用，则此时的常量就不是顶层常量了。
要在一条语句中定义多个变量，切记，符号 & 和 * 只从属于某个声明符，而非基本数据类型中的一部分，因此初始值必须是同一个类型：
```c++
auto k = ci, &l = i         // k是整数，l 是整型引用
auto &m = ci, *p = &ci;     // m 是对整型常量的引用，p 是指向整型常量的指针
auto &n = i, *p2 = &ci;     // 错误：i 的类型是 int 而 &ci 的类型是 const int
```
