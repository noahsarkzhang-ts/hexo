---
title: C++系列：运算符重载
date: 2024-07-30 17:57:24
updated: 2024-07-30 17:57:24
tags:
- c++ 语言
- 运算符重载
- 下标运算符
- 函数调用运算符
categories: 
- 笔记
---

这篇文章简单介绍下运算符重载。

<!-- more -->

# 基本概念

重载的运算符是具有特殊名字的函数：它们的名字由关键字 operator 和其后要定义的运算符共同组成。和其它函数一样，重载的运算符也包含返回类型、参数列表以及函数体。

重载运算符函数的参数数量与该运算符作用的运算对象数量一样多。一元运算符有一个参数，二元运算符有两个。对于二元运算符来说，左侧运算对象传递给第一个参数，而右侧运算对象传递给第二个参数。除了重载的函数调用运算符 operator() 之外，其它重载运算符不能含有默认实参。

如果一个运算符函数是成员函数，则它的第一个（左侧）运算对象绑定到隐式的 this 指针上。因此，成员运算符函数的（显式）参数数量比运算符的运算对象总数少一个。

> 当一个重载的运算符是成员函数时，this 绑定到左侧运算对象。成员运算符函数的（显式）参数数量比运算对象的数量少一个。

对于一个运算符函数来说，它或者是类的成员，或者至少含有一个类类型的参数。

我们可以重载大多数的运算符，除了以下运算符：1）:: ; 2) .* ; 3) . ; 4) ?:。

## 直接调用一个重载的运算符函数
通常情况下，我们将运算符作用于类型正确的实参，从而以这种间接方式“调用”重载的运算符函数。然而，我们也能像调用普通函数一样直接调用运算符函数，先指定函数名字，然后传入数量正确、类型适当的实参：
```c++
// 一个非成员运算符函数的等价调用
data1 + data1;              // 普通的表达式
operator+(data1, data2);    // 等价的函数调用
```

这两次调用是等价的，它们都调用了非成员函数 operator+, 传入 data1 作为第一个实参、传入 data2 作为第二个实参。

我们像调用其他函数一样显式地调用成员运算符函数。具体做法是，首先指定运行函数对象（或指针）的名字，然后使用点运算符（或箭头运算符）访问希望调用的函数：
```c++
data1 += data2;                 // 基于 “调用” 的表达式
data1.operator+=(data2);        // 对成员运算符函数的等价调用
```
这两条语句都调用成员函数 operator+=, 将 this 绑定到 data1 的地址，将 data2 作为实参传入了参数。

下面介绍几种常见的运算符。

# 下标运算符
表示容器的类通常可以通过元素在容器中位置访问元素，这些类一般会定义下标运算符 opeeerator[]。

> 下标运算符必须是成员函数。

为了与下标的原始定义兼容，下标运算符通常以所访问元素的引用作为返回值，这样做的好处是下标可以出现在赋值运算符的任意一端。进一步，我们最好同时定义下标运算符的常量版本和非常量版本，当作用于一个常量对象时，下标运算符返回常量引用以确保我们不会给返回的对象赋值。

> 如果一个类包含下标运算符，则它通常会定义两个版本：一个返回普通引用，另一个类是类的常量成员并且返回常量引用。

# 函数调用运算符
如果类重载了函数调用运算符，则我们可以像使用函数一样使用该类的对象。因为这样的类同时也能存储状态，所以与普通函数相比它们更加灵活。

举个简单的例子，下面这个名为 absInt 的 struct 含有一个调用运算符，该运算符负责返回其参数的绝对值：
```c++
struct absInt {
    int operator()(int val) const {
        return val < 0 ? -val : val;
    }
};
```
这个类只定义了一种操作：函数调用运算符，它负责接受一个 int 类型的实参，然后返回该实参的绝对值。

我们使用调用运算符的方式是令一个 absInt 对象作用于一个实参列表，这一过程看起来非常像调用函数的过程：
```c++
int i = -42;
absInt absObj;          // 含有函数调用运算符的对象
int ui = absObj(i);     // 将 i 传递给 absObj.operator()
```

即使 absObj 只是一个对象而非函数，我们也能“调用”该对象。调用对象实际上是在运行重载的调用运算符。在此例中，该运算符接受一个 int 值并返回其绝对值。

> 函数调用运算符必须成员函数。一个类可以定义多个不同版本的调用运算符，相互之间应该在参数数量或类型上有所区别。

如果类定义了调用运算符，则该类的对象称作**函数对象（function object）**。因为可以调用这种对象，所以我们说这些对象的“行为像函数一样”。


