---
title: C++系列：强制类型转换
date: 2024-07-30 17:57:32
updated: 2024-07-30 17:57:32
tags:
- c++ 语言
- static_cast
- dynamic_cast
- 强制类型转换
- const_cast
- reinterpret_cast
categories: 
- 笔记
---

这篇文章介绍强制类型转换（cast）.

<!-- more -->

# 命令的强制类型转换
一个命名的强制类型转换具有如下形式：
```c++
cast-name<type>(expression);
```
其中，type 是转换的目标类型面 expression 是要转换的值。如果 type 是引用类型，则结果是左值。cast-name 是 static_cast、dynamic_cast、const_cast 和 reinterpret_cast 中的一种。 dynamic_cast 支持运行时类型识别。cast-name 指定了执行的是哪种转换。

## static_cast
任何具有明确定义的类型转换，只要不包含底层 const，都可以使用 static_cast. 例如，通过将一个运算对象强制转换成 double 类型就能使表达式执行浮点数除法：
```c++
// 进行强制类型转换以便执行浮点数除法
double slope = static_cast<double>(j) / i;
```

当需要把一个较大的算术类型赋值给较小的类型时，static_cast 非常有用。此时，强制类型转换告诉程序的编译器：我们知道并且不在乎潜在的精度损失。

static_cast 对于编译器无法自动执行的类型转换也非常有用。例如，我们可以用 static_cast 找回存在于 void* 指针中的值：
```c++
void* p = &d;       // 正确：任何非常量对象的地址都能存入 void*

// 正确：将 void* 转换因初始的指针类型
double *dp = static_cast<double*>(p);
```

## dynamic_cast
**运行时类型识别（run-time type identification, RTTI）** 的功能由两个运算符实现：
- typedid 运算符，用于返回表达的类型；
- dynamic_cast 运算符，用于将基类的指针或引用安全地转换成派生类的指针或引用。

当我们将这两个运算符用于某种类型的指针或引用，并且该类型含有虚函数时，运算符将使用指针或引用所绑定对象的动态类型。

这两个运算符特别用于以下情况：我们想使用基类对象的指针或引用执行某个派生类操作并且该操作不是虚函数。一般来说，只要有可能我们应该尽量使用虚函数。当操作被定义成虚函数时，编译器将根据对象的动态类型自动选择正确的函数版本。

然而，并非任何时候都能定义一个虚函数。假如我们无法使用虚函数，则可以使用一个 RTTI 运算符。另一方面，与虚函数相比，使用 RTTI 运算符蕴含着更多潜在的风险：程序员必须清楚地知道转换的目标类型并且必须检查类型转换是否被成功执行。

### dynamic_cast 运算符
**dynamic_cast 运算符（dynamic_cast operator）**的使用形式如下所示：
```c++
dynamic_cast<type*>(e)
dynamic_cast<type&>(e)
dynamic_cast<type&&>(e)
```
其中，type 必须是一个类类型，并且通常情况下该类型应该含有虚函数。在第一种形式中，e 必须是一个有效的指针；在第二种形式中，e 必须是一个左值；在第三种形式中，e 不能是左值。

在上面的所有形式中，e 的类型必须符合以下三个条件中的任意一个：e 的类型是目标 type 的公有派生类、e 的类型是目标 type 的公有基类或者 e 的类型就是目标 type 的类型。如果符合，则类型转换可以到成功。否则，转换失败。如果一条 dynamic_cast 语句的转换目标是指针类型并且失败了，则结果返回 0。如果转换目标是引用类型并且失败了，则 dynamic_cast 运行符将抛出一个 bad_cast 异常。

#### 指针类型的 dynamic_cast
举个简单的例子，假定 Base 类至少含有一个虚函数，Derived 是 Base 的公有派生类，如果有一个指向 Base 的指针 bp, 则我们可以在运行时将它转换成指向 Derived 的指针，具体代码如下：

```c++
if (Derived *dp = dynamic_cast<Derived*>(bp))
{
    // 使用 dp 指向的 Derived 对象
} else {    // bp 指向一个 Base 对象
    // 使用 bp 指向的 Base 对象
}
```

如果 bp 指向 Derived 对象，则上述的类型转换初始化 dp 并令其指向 bp 所指的 Derived 对象。此时，if 语句内部使用 Derived 操作的代码是安全的，否则，类型转换的结果为 0, dp 为 0 意味着 if 语句的条件失败，此时 else 子句执行相应的 Base 操作。

> 可以对一个空指针执行 dynamic_cast，结果是所需类型的空指针。

#### 引用类型的 dynamic_cast
引用类型的 dynamic_cast 与指针类型的 dynamic_cast 在表示错误发生的方式上略有不同。因为不存在所谓的空引用，所以对于引用类型来说无法使用与指针类型完全相同的错误报告策略。当对引用的类型转换失败时，程序抛出一个名为 std::bad_cast 的异常，该异常定义在 typeinfo 标准库头文件中。
我们可以按照如下的形式改写之前的程序，令其使用引用类型：
```c++
void f(const Base &b) 
{
    try {
        const Derived &d = dynamic_cast<const Derived&>(b);
    } catch (bad_cast) {
        // 处理类型转换失败的情况
    }
}
```

### typeid 运算符
**typeid 运算符（typeid operator）** 允许程序向表达式提问：你的对象是什么类型？

typeid 的表达式形式是 **typeid(e)**，其中 e 可以是任意表达式或类型的名字。typedid 操作的结果是一个常量对象的引用，该对象的类型是标准库类型 type_info 或者 type_info 的公有派生类型。

#### 使用 typeid 运算符
通常情况下，我们使用 typeid 比较两条表达式的类型是否相同，或者比较一条表达式的类型是否与指定类型相同：
```c++
Derived *dp = new Derived;
Base *bp = dp;              // 两个指针都指向 Derived 对象
// 在运行进比较两个对象的类型
if (typeid(*bp) == typeid(*dp)) {
    // bp 和 dp 指向同一类型的对象
}

// 检查运行时类型是否某种指定类型
if (typeid(*bp) == typeid(Derived)) {
    // bp 实际指向 Derived 对象
}
```

在第一个 if 语句中，我们比较 bp 和 dp 所指的对象的动态类型是否相同。如果相同，则条件成功。类似的，当 bp 当前所指的是一个 Derived 对象时，第二个 if 语句的条件满足。


## const_cast
const_cast 只能改变运算对象的底层 const:
```c++
const char *pc;
char *p = const_cast<char*>(pc);    // 正确：但是通过 p 写值是未定义的行为
```

对于将常量对象转换成非常量对象的行为，我们一般称其为“去掉 const 性质（cast away the const）”。一旦我们去掉了某个对象的 const 性质，编译器就不再阻止我们对该对象进行写操作了。如果对象本身不是一个常量，使用强制类型转换获得写权限是合法的行为。然而如果对象是一个常量，再使用 const_cast 执行写操作就会产生未定义的后果。

只有 const_cast 能改变表达式的常量属性，使用其他形式的命名强制类型改变表达式的常量属性都将引发编译器错误。同样的，也不能使用 const_cast 改变表达式的类型：
```c++
const char *cp;
//  错误：static_cast 不能转换掉 const 性质
char *q = static_cast<char*>(cp);
static_cast<string>(cp);        // 正确：字符串字面值转换成 string 类型
const_cast<string>(cp);         // 错误：const_cast 只改变常量属性
```

const_cast 常常用于有函数重载的上下文中。

## reinterpret_cast
reinterpret_cast 通常为运算对象的位模式提供较低层次上的重新解释。举个例子，假设有如下的转换：
```c++
int *ip;
char *pc = reinterpret_cast<char*>(ip);
```

我们必须牢记 pc 所指的真实对象是一个 int 而非字符，如果把 pc 当成普通的字符打针使用可能在运行时发生错误。例如：
```c++
string str(pc);
```

可能导致异常的运行时行为。
