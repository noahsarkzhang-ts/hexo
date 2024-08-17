---
title: C++系列：函数指针和 lambda 表达式
date: 2024-07-30 17:57:40
updated: 2024-07-30 17:57:40
tags:
- c++ 语言
- 函数指针
- lambda 表达式
- 函数对象
categories: 
- 笔记
---

这篇文章介绍函数指针和 lambda 表达式。

<!-- more -->

# 函数指针
函数指针指向的是函数而非对象。和其它指针一样，函数指针指向某种特定类型。函数的类型由它的返回类型和形参类型共同决定，与函数名无关。例如：
```c++
// 比较两个 string 对象的长度
bool lengthCompare(const string &, const string &);
```
该函数的类型是 bool(const string &, const string&)。要想声明一个可以指向该函数的指针，只需要用指针替换函数名即可：
```c++
// pf 指向一个函数，该函数的参数是两个 const string 的引用，返回值是 bool 类型
bool (*pf)(const string &, const string &);     // 未初始化
```

从我们声明的名字开始观察，pf 前面有个 *，因此 pf 是指针；右侧是形参列表，表示 pf 指向的是函数；再观察左侧，发现函数的返回类型是布尔值。因此，pf 就是一个指向函数的指针，其中该函数的参数是两个 const string 的引用，返回值是 bool 类型。

*pf 两端的括号必不可少。如果不写这对括号，则 pf 是一个返回值为 bool 指针的函数：
```c++
// 声明一个名为 pf 的函数，该函数返回 bool *
bool *pf(const string &, const string &);
```

## 使用函数指针
当我们把函数名作为一个值使用时，该函数自动地转换成指针。例如，按照如下形式，我们可以将 lengthCompare 的地址赋给 pf：
```c++
pf = lengthCompare;         // pf 指向名为 lengthCompare 的函数
pf = &lengthCompare;        // 等价的赋值语句：取地址符是可选的
```

此外，我们还能直接使用指向函数的指针调用该函数，无须提前解引用指针：
```c++
bool b1 = pf("hello", "goodbye");               // 调用 lengthCompare 函数
bool b2 = (*pf)("hello", "goodbye");            // 一个等价的调用
bool b3 = lengthCompare("hello", "goodbye");    // 另一个等价的调用
```

# lambda 表达式
我们可以向一个算法传递任何类别的**可调用对象（callable object）**。对于一个对象或表达式，如果可以对其使用调用运算符，则称它为可调用的。即，如果 e 是一个可调用的表达式，则我们可以编写代码 e(args), 其中 args 是一个逗号分隔的一个或多个参数的列表。

可调用对象有四种：1）函数；2）函数指针；3）重载了函数调用运算符的类；4）lambda 表达式（lambda expression）。

一个 lambda 表达式表示一个可调用的代码单元。我们可以将其理解为一个未命名的内联函数。与任何函数类似，一个 lambda 具有一个返回类型、一个参数列表和一个函数体。但与函数不同，lambda 可能定义在函数内部。一个 lambda 表达式具有如下形式：
```c++
[capture list] (parameter list) -> return type { function body }
``
其中，capture list（捕获列表）是一个 lambda 所在函数中定义的局部变量的列表（通常为空）；reture type、parameter list 和 function body 与任何普通函数一样，分别表示返回类型、参数列表和函数体。但是，与普通函数不同，lambda 必须使用尾置返回来指定返回类型。

我们可以忽略参数列表和返回类型，但必须永远捕获列表和函数体：
```c++
auto f = [] { return 42; };
```

此例中，我们定义了一个可调用对象 f, 它不接受参数，返回 42。

lambda 的调用方式与普通函数的调用方式相同，都是使用调用运算符：
```c++
cout << f() << endl;    // 打印 42
```

在 lambda 中忽略括号和参数列表等价于指定一个空参数列表。在此例中中，当调用 f 时，参数列表是空的。如果忽略返回类型，lambda 根据函数体中的代码推断出返回类型。如果函数体只是一个 return 语句，则返回类型从返回的表达的类型推断而来。否则，返回类型为 void.

> 如果 lambda 的函数体包含任何单一 return 语句之外的内容，且未指定返回类型，则返回 void.

**向 lambda 传递参数**
与一个普通函数调用类似，调用一个 lambda 时给定的实参被用来初始化 lambda 的形参。通常，实参和形参的类型必须匹配。但与普通函数不同，lambda 不能有默认参数。因此，一个 lambda 调用的实参数目永远与开参数目相等。一旦形参初始化完毕，就可以执行函数体了。

**使用捕获**
向 lambda 表达式传递参数有两种方式：1）通过参数列表，将值传递给 lambda 函数体；2）通过捕获列表，将外部使用到的外部局部变量传递给 lambda 函数体。如下面的实例：
```c++
[sz] (const string &a) 
    { return a.size() >= sz; }
```
lambda 以 一对 [] 开始，我们可以在其中提供一个以逗号分隔的名字列表，这些名字都是外部定义的变量。

# lambda 是函数对象
当我们编写了一个 lambda 后，编译器将该表达式翻译成一个未命名类的未命名对象。在 lambda 表达式产生的类中含有一个重载的函数调用运算符，例如，在下面的实例中，最后一个参数是 lambda 表达式：
```c++
// 根据单词的长度对其进行排序，对于长度相同的单词按照字母表顺序排序
stable_sort(words.begin(),  words.end(),
            [](const string &a, const string &b)
            { return a.size() < b.size(); } );
```

其行为类似于下面这个类的一个未命名对象
```c++
class ShorterString {
public:
    bool operator() (const string &s1, const string &s2) const 
    { return s1.size() < s2.size(); }
}
```

产生的类只有一个函数调用运算符成员，它负责接受两个 string 并比较它们的长度，它的形参列表和函数体与 lambda 表达式安全一样。

