---
title: C++系列：内联函数
date: 2024-07-30 17:56:36
updated: 2024-07-30 17:56:36
tags:
- c++ 语言
- 内联函数
- inline
categories: 
- 笔记
---

这篇文章主要讲述内联函数 (inline)。

<!-- more -->

## 内联函数可避免函数调用的开销
将函数指定为内联函数(inline),通常就是将它在每个调用点上“内联地”展开。在函数的返回类型前面加上关键字 inline, 这样就可以将它声明成内联函数了，如下实例：
```c++
inline const string & shorterString(const string &s1, const string &s2) 
{
    return s1.size() <= s2.size() ? s1 : s2;
}
```
对 shorterString 进行调用：
 ```c++
cout << shorterString(s1, s2) << endl;
 ```

 将在编译过程中展开成类似于下面的形式：
 ```c++
cout << (s1.size() <= s2.size() ? s1 : s2) << endl;
 ```
 
 从而消除了 shorterString 函数的运行时开销。

 >> 内联说明只是向编译器发出的一个请求，编译器可以选择忽略这个请求。

 一般来说，内联机制用于优化规模较小、流程直接、频繁调用的函数。很多编译器都不支内联递归函数，而且一个 75 行的函数也不大可能在调用点内联地展开。
 

