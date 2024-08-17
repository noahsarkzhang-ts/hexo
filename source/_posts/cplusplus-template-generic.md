---
title: C++系列：模板及泛型编程
date: 2024-07-30 17:57:51
updated: 2024-07-30 17:57:51
tags:
- c++ 语言
- 模板
- 泛型编程
- 函数模板
- 类模板
- 成员模板
- 可变参数模板
- 模板特例化
categories: 
- 笔记
---

这篇文章讲解 C++ 模板及泛型编程。

<!-- more -->

# 概述
模板是 C++ 中泛型编程的基础。一个模板就是一个创建类或函数的蓝图或者说公式。当使用一个 vector 这样的泛型类型，或者 find 这样的泛型函数时，我们提供足够的信息，将蓝图转换为特定的类或函数。这种转换发生在编译时。

# 定义模板
假定我们希望编写一个函数来比较两个值，并指出第一个值是小于、等于还是大于第二个值。在实际中，我们可能想定义多个函数，每一个函数比较一种给定类型的值。如下所示：
```c++
// 如果两个值相等，返回 0，如果 v1 小返回 -1，如果 v2 小返回 1
int compare(const string &v1, const string &v2) 
{
    if (v1 < v2) return -1;
    if (v2 < v1) return 1;
    return 0;
}

int compare(const double &v1, const double &v2) 
{
    if (v1 < v2) return -1;
    if (v2 < v1) return 1;
    return 0;
}
```

这两个函数几乎是相同的，唯一的差异是参数的类型，函数体则完全一样。

如果对每种希望比较的类型都不得不重复定义安全一样的函数体，是非常烦琐且容易出错的，更麻烦的时，在编写程序的时候，我们就要确定可能 compare 的所有类型。如果希望在用户提供的类型上使用此函数，这种策略就失效了。

# 函数模板
我们可以定义一个通用的**函数模板（function template）**，而不是每个类型都定义一个新函数。一个函数模板就是一个公式，可以用来生成针对特定类型的函数版本。compare 的模板版本可能像下面这样：
```c++
template <typename T> 
int compare(const T &v1, const T &v2) 
{
    if (v1 < v2) return -1;
    if (v2 < v1) return 1;
    return 0;
}
```

模板定义以关键字 template 开始，后跟一个**模板参数列表（template parameter list）**, 这是一个逗号分隔的一个或多个**模板参数（template parameter）**的列表，用小于号(<) 和大于号（>）包围起来。

模板参数列表的作用很像函数参数列表。函数参数列表定义了若干特定类型的局部变量，但并未指定如何初始化它们。在运行时，调用者提供实参来初始化形参。

类似地，模板参数表示在类或函数定义中用到的类型或值。当使用模板时，我们（隐式地或显式地）指定**模板实参*（template argument）**, 将其绑定到模板参数上。

我们的 compare 函数声明了一个名为 T 的类型参数。在 compare 中，我们用名字 T 表示一个类型。而 T 表示的实际类型则在编译时根据 compare 的使用情况来确定。

## 实例化函数模板
当我们调用一个函数模板时，编译器（通常）用函数实参来为我们推断模板实参。即我们调用 compare 时，编译器使用实参的类型来确定绑定到模板参数 T 的类型。例如：
```c++
count << compare(1, 0) << endl;         // T 为 int
```
实参的类型是 int。编译器会推断出模板实参为 int，并将它绑定到模板参数 T。

编译器用推断出的模板参数来进行**实例化（instantiate）**一个特定版本的函数。当编译器实例化一个模板时，它使用实际的模板实参代替对应的模板参数来创建出模板的一个新“实例”。例如：
```c++
// 实例化出 int compare(const int&, const int&) 
count << compare(1, 0) << endl;         // T 为 int

// 实例化出 int compare(const vector<int>&, const vector<int>&) 
vector<int> vec1{1, 2, 3}, vec2(4, 5, 6)
count << compare(vec1, vec2) << endl;         // T 为 vector<int>
```
编译器会实例化出两个不同版本的 compare。对于第一个调用，编译器会编写并编译一个 compare 版本，其中 T 被替换为 int：
```c++
int compare(const int &v1, const int &v2) 
{
    if (v1 < v2) return -1;
    if (v2 < v1) return 1;
    return 0;
}
```
对于第二个调用，编译器会生成另一个 compare 版本，其中 T 被替换为 vector<int>:
```c++
int compare(const vector<int> &v1, const vector<int> &v2) 
{
    if (v1 < v2) return -1;
    if (v2 < v1) return 1;
    return 0;
}
```

这些编译器生成的版本通常称为模板的**实例（instantiation）**。

## 模板类型参数
compare 函数有一个模板**类型参数（type parameter）**。一般来说，可以将类型参数看作类型说明符，就像内置类型或类类型说明符一样使用。特别是，类型参数可以用来指定返回类型或函数的参数类型，以及在函数体用于变量声明或类型转换：
```c++
// 正确：返回类型和参数类型相同
template <typeanme T> T foo(T* p)
{
    T tmp = *p;     // tmp 的类型是将是指针 p 指向的类型
    // ...
    return tmp;
}
```

类型参数前必须使用关键字 class 或 typename，在模板参数列表中，这两个关键字的含义相同，可以互换使用。

### 非类型模板参数
除了定义类型参数，还可以在模板中定义**非类型参数（notype parameter）**。一个非类型参数表示一个值而非一个类型。它通过一个特定的类型名而非关键字 class 或 typename 来指定非类型参数。

当一个模板被实例化时，非类型参数被一个用户提供的或编译器推断出的值所代替。这些值必须是常量表达式，从而允许编译时实例化模板。

> 非类型模板参数的模板实参必须是常量表达式。

### inline 和 constexpr 的函数模板
函数模板可以声明为 inline 或 constexpr，如果非模板函数一样。inline 或 constexpr 说明符放在模板参数列表之后，返回类型之前：
```c++
// 正确：inline 说明符跟在模板参数列表之后
template <typename T> inline T min(const T&, const T&);
// 错误：inline 说明符的位置不正确
inline template <typename T> T min(const T&, const T&);
```

# 类模板
**类模板（class template）**是用来生成类的蓝图的。与函数模板的不同之处是，编译器不能为类模板推断模板参数类型。为了使用类模板，必须在模板名后的尖括号内提供额外信息————用来代替模板参数的模板实参列表。

## 定义类模板
类似函数模板，类模板以关键字 template 开始，后跟模板参数列表。在类模板（及其成员）的定义中，我们将模板参数当作替身，代替使用模板时用户需要提供的类型或值：
```c++
template <typename T> class Blob {
public:
    typedef T value_type;
    typedef typename std::vector<T>::size_type size_type;
    // 构造函数
    Blob();
    Blob(std::initializer_list<T> il);
    // Blob 中的元素数目
    size_type size() const { return data->size(); }
    bool empty() const { return data->empty(); }
    // 添加和删除元素
    void push_back(const T &t) { data->push_back(t); }
    // 移动版本
    void push_back(T &&t) { data->push_back(std::move(t)); }
    void pop_back();
    // 元素访问
    T& back();
    T& operator[](size_type i);
private:
    std::shard_ptr<std:vector<T> data;
    // 若 data[i] 无效，则抛出 msg
    void check(size_type i, const std::string &msg) const;
};
```
Blob 模板有一个名为 T 的模板类型参数，用来表示 Blob 保存的元素的类型。

## 实例化类模板
当使用类模板时，需要显式地提供模板参数，如下所示：
```c++
Blob<int> ia;                       // 空 Blob<int>
Blob<int> ia2 = {0, 1, 2, 3, 4};    // 有5个元素的 Blob<int>
```

ia 和 ia2 使用相同的特定类型版本的 Blob（即 Blob<int>）。从这两个定义，编译器会实例化出一个与下面定义等价的类：
```c++
template <> class Blob<int> {
public:
    typedef int value_type;
    typedef typename std::vector<int>::size_type size_type;
    // 构造函数
    Blob();
    Blob(std::initializer_list<int> il);
    // ...
    int& operator[](size_type i);
private:
    std::shard_ptr<std:vector<int> data;
    // 若 data[i] 无效，则抛出 msg
    void check(size_type i, const std::string &msg) const;
};
```
当编译器从 Blob 模板实例化出一个类时，它会重写 Blob 模板，将模板参数 T 的每一个实例替换为指定的模板实参，在本例中是 int.

对于指定的每一种元素类型，编译器都会生成一个不同的类。

## 类模板的成员函数
与其它任何类相同，既可以在类模板内部，也可以在类模板外部为其定义成员函数，且定义在类模板内的成员函数被隐式声明为内联函数。

类模板的成员函数本身是一个普通函数。但是，类模板的每个实例都有其自己版本的成员函数。因此，类模板的成员函数具有和模板相同的模板参数。因而，定义在类模板之外的成员函数必须以关键字 template 开始，后接类模板参数列表。其格式如下：
```c++
template <typename T>
ret-type Blob<T>::member-name(param-list)
```
实例如下：
```c++
template <typename T>
void Blob<T>::check(size_type i, const std::string &msg) const 
{
    if (i >= data->size()) 
        throw std::out_of_range(msg);
}
```

## Blob 构造函数
与其他任何定义在类模板外的成员一样，构造函数的定义要以模板参数开始：
```c++
template <typename T>
Blob<T>::Blob() : data(std::make_shared<std::vector<T>) {}
```

# 默认模板实参
在新标准中，可以为函数和类模板提供默认实参，例如，我们重写 compare, 默认使用标准库的 less 函数对象模板：
```c++
// 
template <typename T, typename F = less<T>
int compare(const T &v1, const T &v2, F f = F()) 
{
    if (f(v1, v2)) return -1;
    if (f(v2, v1)) return 1;
    return 0;
}
```
在这段代码中，我们为模板添加了第二个类型参数，名为 F, 表示可调用对象的类型；并定义了一个新的函数参数 f, 绑定到一个可调用对象上。

## 模板默认实参与类模板
无论何时使用一个类模板，我们都必须在模板名之后接上尖括号。尖括号指出类型必须从一个模板实例化而来。特别是，如果一个类模板为其所有模板参数都提供了默认实参，且我们希望使用这些默认实参，就必须在模板名之后跟一个空尖括号对：
```c++
template <typename T = int> class Numbers {     // T 默认为 int
public:
    Numbers(T v = 0): val (v) {}
    // 对数值的各种操作
private:
    T val;
};

Nubmers<long double> lots_of_precision;
Numbers<> average_precision;        // 空 <> 表示我们希望使用默认类型
```
此例中我们实例化了两个 Numbers 版本: average_precision 是用 int 代替 T 实例化得到的；lots_of_precision 是用 long double 代替 T 实例化而得到的。

# 成员模板
一个类（无论是普通类还是类模板）可以包含本身是模板的成员函数。这种成员被称为**成员模板（member template）**。成员模板不能是虚函数。

## 普通（非模板）类的成员模板
其格式如下：
```c++
class ClassName {
public:
    template <typename T> void mem(T *p) const
    { delete p; }
    // ...
};
```
与任何其他模板相同，成员模板也是以模板参数列表开始的。

## 类模板的成员模板
对于类模板，我们也可以为其定义成员模板。在此情况下，类和成员各自有自己的、独立的模板参数。如下例所示：
```c++
template <typename T> class Blob {
    template <typename It> Blob(It b, It e);
};
```
此构造函数有自己的模板类型参数 It, 作为它的两个函数参数的类型。

# 可变参数模板
一个 **可变参数模板（variadic template）**就是一个接受可变数目参数的模板函数或模板类。可变数目的参数被称为**参数包（parameter packet）**。存在两种参数包：**模板参数包（template parameter packet）**，表示零个或多个模板参数；**函数参数包（function parameter packet）**，表示零个或多个函数参数。

我们用一个省略号来指出一个模板参数或函数参数表示一个包。在一个模板参数列表中，class... 或 typename... 指出接下来的参数表示零个或多个类型的列表；一个类型名后面跟一个省略号表示零个给定类型的非类型参数的列表。在函数列表中，如果一个参数的类型是一个模板参数包，则此参数也是一个函数参数包。
```c++
// Args 是一个模板参数包；rest 是一个函数参数包
// Args 表示零个或多个模板类型参数
// rest 表示零个或多个函数参数
template <typename T, typename... Args>
void foo(const T &t, const Args& ... rest);
```

声明了 foo 是一个可变参数函数模板，它有一个名为 T 的类型参数，和一个名为 Args 的模板参数包。这个包表示零个或多个额外的类型参数。foo 的函数参数列表包含一个 const &类型的参数，指向 T 的类型，还包含一个名为 rest 的函数参数包，此包表示零个或多个函数参数。

与往常一样，编译器从函数的实参推断模板参数类型。对于一个可变参数模板，编译器还会推断包中参数的数目。例如，给定下面的调用：
```c++
int i = 0; double d = 3.14; string s = "how now brown cow";
foo(i, s, 42, d);       // 包中有三个参数
foo(s, 42, "hi");       // 包中有两个参数
foo(d, s);              // 包中有一个参数
foo("hi");              // 空包
```

编译器会为 foo 实例化出四个不同的版本：
```c++
void foo(const int&, const string&, const int&, const double&);
void foo(const string&, const int&, const char[3]&);
void foo(const double&, const string&);
void foo(const char[3]&);
```

在每个实例中，T 的类型都是从第一个实参的类型推断出来的，剩下的实参（如果有的话）提供函数额外实参的数目和类型。

## sizeof... 运算符
当我们需要知道包中有多少元素时，可以使用 sizeof... 运算符。类似 sizeof, sizeof...也返回一个常量表达式，而且不会对其实参求值：
```c++
template<typename ... Args> void g(Args ... args) {
    cout << sizeof...(Args) << endl;        // 类型参数的数目
    cout << sizeof...(args) << endl;        // 函数参数的数目
}
```

## 包扩展
对于一个参数包，除了获取其大小之外，我们能对它做的惟一的事情就是**扩展（expand）**它。当扩展一个包时，我们还要提供用于每个扩展元素的**模式（pattern）**。扩展一个包就是将它分解为构成的元素，对每个元素应该模式，获得扩展后的列表。我们通过在模式右边放一个省略号（...）来触发扩展操作。

## 转发参数包
在新标准下，我们可以组合使用可变参数模板与 forward 机制来编写函数，实现将其实参不变地传递给其它函数。如下定义：
```c++
template <class... Args>
inline 
void StrVec::emplace_back(Args&&... args) 
{
    // ...
    alloc.construct(first_free++, std::forward<Args>(args)...);
}
```

construct 调用中的扩展为：
```c++
std::forward<Args>(args)...
```
它既扩展了模板参数 Args，也扩展了函数参数包 args。引模式生成如下形式的元素：
```c++
std::forward<Ti>(ti)
```
其中 Ti 表示模板参数包中第 i 个元素的类型，ti 表示函数参数包中第 i 个元素。

# 模板特例化
在实际编码中，编写单一模板，使之适用于所有可能的类型，这是比较理想化的。在某些场景中，通用定义的代码不合适，这就需要我们自定义类或函数模板的一个特例化版本。

## 定义函数模板特例化
当特例化一个函数模板时，必须为原模板中的每个模板参数都提供实参。为了指出我们正在实例化一个模板，应该使用关键字 template 后跟一个空尖括号对 （<>）。空尖括号指出我们将为原模板的所有模板参数提供实参：
```c++
// compare 的特殊版本，处理字符数组的指针
template <>
int compare(const char* const &p1, const char* const &p2) 
{
    return strcmp(p1, p2);
}
```

## 类模板特例化
除了特例化函数版本，我们还可以特例化模板，作为一个例子，将为标准库 hash 模板定义一个特例化版本：
```c++
// 打开 std 命名空间，以便特例化 std::hash
namespace std {
template<>     // 我们正在定义一个特例化为版本，模板参数为 Sales_data
struct hash<Sales_data> 
{
    // 用来散列一个无序容器的类型
    typedef size_t result_type;
    typedef Sales_data argument_type;   // 默认情况下，此类型需要 ===
    size_t operator() (const Sales_date& s) const;
    // ...
};
size_t
hash<Sales_data>::operator()(const Sales_data& s) const
{
    return ...;
}
}   // 关闭 std 命名空间；注意：右花括号之后没有分号
```

hash<Sales_data> 定义以 template<>开始，指定我们正在定义一个全特例化的模板。