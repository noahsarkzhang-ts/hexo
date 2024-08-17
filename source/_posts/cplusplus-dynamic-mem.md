---
title: C++系列：动态内存
date: 2024-07-30 17:58:00
updated: 2024-07-30 17:58:00
tags:
- c++ 语言
- 动态内存
- 智能指针
- shared_ptr
- unique_ptr
- weak_ptr
categories: 
- 笔记
---

这篇文章主要记录 C++ 动态内存相关知识。

<!-- more -->

# 概述
C++ 语言中，程序有三种类型的内存可以使用，分别是：1）静态内存；2）栈内存；3）堆（heap）。静态内存用来保存局部 static 对象、类 static 数据成员以及定义在任何函数之外的变量。栈内存用来保存定义在函数内的非 static 对象。堆用来存储**动态分配（dynamically allocate）**的对象，即那些在程序运行时分配的对象。

分配在静态或栈内存中的对象由编译器自动创建和销毁。对于栈对象，仅在其定义在程序块运行时才存在，而 static 对象在使用之前分配，在程序结束时销毁。动态对象的生存期由程序来控制，也就是说，当动态对象不再使用时，我们的代码必须显式地销毁它们。

# 动态内存与智能指针
在 C++ 中，动态内存的管理是通过一对运算符来完成的：**new**,在动态内存中为对象分配空间并返回一个指向该对象的指针，我们可以选择对对象进行初始化；**delete**, 接受一个动态对象的指针，销毁该对象，并释放与之关联的内存。

为了更容易（同时也更安全）地使用动态内存，新的标准库提供了两种**智能指针（smart pointer）**类型来管理动态对象。智能指针的行为类似常规指针，重要的匹配是它负责自动释放所指向的对象。新标准库提供的这两种智能指针的区别在于管理底层指针的方式：**shared_ptr** 允许多个指针指向同一个对象；**unique_ptr** 则“独占”所指向的对象。标准库还定义了一个名为 **weak_ptr**的伴随类，它是一种弱引用，指向 shared_ptr 管理的对象。这三种类型都定义在 memory 头文件中。

## shared_ptr 类
类似 vector，智能指针也是模板。因此，当我们创建一个智能指针时，必须提供额外的信息————指针可以指向在类型。与 vecotr 一样，我们在尖括号内给出类型，之后是所定义的这种智能指针的名字：

```c++
shared_ptr<string> p1;      // 可以指向 string
shared_ptr<<list<int>>> p2; // 可以指向 int 的 list
```

默认初始化的智能指针中保存着一个空指针。

### make_shared 函数
最安全的分配和使用动态内存的方法是调用一个为 make_shared 的标准函数，此函数在动态内存中分配一个对象并初始化它，返回指向此对象的 shared_ptr. 例如：
```c++
// 指向一个值为 42 的 int 的 shared_ptr
shared_ptr<int> p3 = make_shared<int>(42);
// 指向一个值为 “9999999999” 的 string
shared_ptr<string> p4 = make_shared<string>(10,'9');
// 指向一个值为初始化的 int, 即，值为 0
shared_ptr<int> p5 = make_shared<int>();
```
make_shared 用其参数来构造给定类型的对象，例如，调用 make_shared<string> 时传递的参数必须与 string 的某个构造函数相匹配，调用 make_shared<int> 时传递的参数必须能用为初始化一个 int，依此类推。如果我们不传递任何参数，对象就会进行值初始化。

我们也可以用 auto 定义一个对象来保存 make_shared 的结果，这种方式较为简单：
```c++
// p6 指向一个动态分配的空 vector<string>
auto p6 = make_shared<vector<string>>();
```

### shared_ptr 的拷贝和赋值
每个 shared_ptr 类都有一个关联的计数器，通过称其为**引用计数（reference count）**。无论何时拷贝一个 shared_ptr，计数器都会递增，并且它们都指向相同的对象。

### shared_ptr 自动销毁所管理的对象
当指向一个对象的最后一个 shared_ptr 被销毁时，shared_ptr 类会自动销毁此对象，指针指向的内存也会被销毁。它是通过另一个特殊成员函数————析构函数（destructor）完成销毁工作的。

## unique_ptr
一个 unique_ptr “拥有” 它所指向的对象。与 shared_ptr 不同，某个时刻只能有一个 unique_ptr 指向一个给定对象。当 unique_ptr 被销毁时，它所指向的对象也被销毁。

与 shared_ptr 不同，没有类似 make_shared 的标准库函数返回一个 unique_ptr，当我们定义一个 unique_ptr 时，需要将其绑定到一个 new 返回的指针上。类似 shared_ptr,初始化 unique_ptr 必须采用直接初始化形式：
```c++
unique_ptr<double> p1;      // 可以指向一个 double 的 unique_ptr
unique_ptr<int> p2(new int(42));    // p2 指向一个值为 42 的 int
```
由于一个 unique_ptr 拥有它指向的对象，因此 unique_ptr 不支持普通的拷贝或赋值操作。

虽然我们不能拷贝或赋值 unique_ptr，但可以通过 release 或 reset 将指针的所有权从一个 （非 const）unique_ptr 转移给另一个 unique_ptr：
```c++
// 将所有权从 p1 转移给 p2
unique_ptr<string> p2(p1.release());        // release 将 p1 置为空
unique_ptr<string> p3(new string("Trex")); 
// 将所有权从 p3 转移给 p2
p2.reset(p3.release());     // reset 释放了 p2 原来指向的内存
```

release 成员返回 unique_ptr 当前保存的指针并将其置为空。因此，p2 被初始化为 p1 原来保存的指针，而 p1 被置为空。

reset 成员接受一个可选的指针参数，令 unique_ptr 重新指向给定的指针。如果 unique_ptr 不为空，它原来指向的对象被释放。因此，对 p2 调用 reset 释放了之前使用的内存，将 p3 对指针的所有权转移给 p2, 并将 p3 置为空。

调用 release 会切断 unique_ptr 和它原来管理的对象间的联系。release 返回的指针通常被用来初始化另一个智能指针或给另一个智能指针赋值。在本例中，管理内存的责任简单地从一个智能指针转移给另一个。但是，如果我们不用另一个智能指针来保存 release 返回的指针，我们的程序就要负责资源的释放：
```c++
p2.release();               // 错误：p2 不会释放内存，而且我们丢失了指针
auto p = p2.release();      // 正确，但我们必须记得 delete(p)
```

## weak_ptr
weak_ptr 是一种不控制所指向对象生存期的智能指针，它指向一个 shared_ptr 管理的对象。将一个 weak_ptr 绑定到一个 shared_ptr 不会改变 shared_ptr 的引用计数。一旦最后一个指向对象的 shared_ptr 被销毁，对象也会被释放。即使有 weak_ptr 指向对象，对象也还是会被释放，因此，weak_ptr 的名字抓住了这种智能指针“弱”共享对象的特点。

当我们创建一个 weak_ptr 时，要用一个 shared_ptr 来初始化它：
```c++
auto p = make_shared<int>(42);
weak_ptr<int> wp(p);        // wp 弱共享，p 的引用计数示改变
```
本例中 wp 和 p 指向相同的对象。由于是弱共享，创建 wp 不会改变 p 的引用计数；wp 指向的对象可能被释放掉。

由于对象可能不存在，我们不能使用 weak_ptr 直接访问对象，而必须调用 lock。此函数检查 weak_ptr 指向的对象是否仍存在。如果存在，lock 返回一个指向共享对象的 shared_ptr。与任何其它 shared_ptr 类似，只要 shared_ptr 存在，它所指向的底层对象也就会一直存在。例如：
```c++
if (shared_ptr<int> np = wp.lock()) {   // 如果 np 不为空则条件成立
    // 在 if 中，np 与 p 共享对象
}
```

在这段代码中，只有当 lock 调用返回 true 时我们才会进入 if 语句体。在 if 中，使用 np 访问共享对象是安全的。

