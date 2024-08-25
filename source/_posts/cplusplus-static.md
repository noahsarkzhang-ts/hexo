---
title: C++系列：static 关键字
date: 2024-07-30 17:56:46
updated: 2024-07-30 17:56:46
tags:
- c++ 语言
- static
categories: 
- 笔记
---

这篇文章主要讲述 static 关键字的使用。

<!-- more -->

## 局部对象
在 C++ 语言中，名字有作用域，对象有生命周期(lifetime)，理解这两个概念比较重要：
- 名字的作用域是程序文本的一部分，名字在其中可见。
- 对象的生命周期是程序执行过程中该对象存在的一段时间。

如我们所见，函数体是一个语句块。块构成一个新的作用域，我们可以在其中定义变量。形参和函数体内部定义的变量称为局部变量(local variable). 它们对函数而言是“局部”的，仅在函数的作用域内可见，同时局部变量还会隐藏(hide) 在外层作用域中同名的其他所有声明中。

在所有函数体之后定义的对象存在于程序的整个执行过程中。此类对象在程序启动时被创建，直到程序结束才会销毁。局部变量的生命周期依赖于定义的方式。

### 自动对象
对于普通局部变量对应的对象来说，当函数的控制路径经过变量定义语句时创建该对象，当到达定义所在的块末尾是销毁它。我们把只在于块执行期间的对象称为自动对象(automatic object)。当块的执行结束后，块中创建的自动对象的值就变成未定义的了。

形参是一种自动对象。函数开始时为形参申请存储空间，因为形参定义在函数体作用域之内，所以一旦函数终止，形参也就被销毁。

我们用传递给函数的实参初始化形参对应的自动对象。对于局部变量对应的自动对象来说，则分为两种情况：1）如果变量定义本身含有初始值，就用这个初始值进行初始化；2）如果变量定义本身不含初始值，执行默认初始化。这意味着内置类型的未初始化局部变量将产生未定义的值。

### 局部静态对象
某些时候，有必要令局部变量的生命周期贯穿函数调用及之后的时间。可以将局部变量定义为 static 类型从而获得这样的对象。局部静态对象(local satic object) 在程序的执行路径第一次经过对象定义语句时初始化，并且直到程序终止才被销毁，在此期间即使对象所在函数结束执行也不会对它有影响。

举个例子，下面的函数统计它自己被调用了多少次，这样的函数也许没有什么实际意义，但是足够说明问题：
```c++
size_t count_calls()
{
    static size_t ctr = 0;   // 调用结束后，这个值仍然有效
    return ++ctr;
}

int main()
{
    for (size_t i = 0; i != 10; ++i) 
    {
        cout << count_calls() << endl;    
    }

    return 0;
}
```

这段程序将输出从 1 到 10 (包括 10 在内) 的数字。

在控制流第一次经过 ctr 的定义之前，ctr 被创建并初始化为 0。每次调用将 ctr 加 1 并返回新值。每次执行 count_calls 函数时，变量 ctr 的值都已经存在并且等于函数上次退出时 ctr 的值。因此，第二次调用时 ctr 的值是 1, 第三次调用是 ctr 的值是 2，以此类推。

<font color=red>如果局部静态变量没有显式的初始值，它将执行值初始化，内置类型的局部静态变量初始化为 0。</font>

## 类的静态成员
有的时候类需要它的一些成员与类本身直接相关，而不是与类的各个对象保持关联。例如，一个银行账号类可能需要一个数据成员来表示当前的基准利率。在此例中，我们希望利率与类关联，而非与类的每个对象关联。从实现效率的角度来看，没必要每个对象都存储利率信息。而且更加重要的是，一旦利率浮动，我们希望所有的对象都能使用新值。

### 声明静态成员
我们通过在成员的声明之前加上关键字 static 使得其与类关联在一起。和其他成员一样，静态成员可以是 public 的或 private 的。静态数据成员的类型可以是常量、引用、指针、类类型等等。

举个例子，我们定义一个类，用它表示银行的账户记录：
```c++
class Account {
public:
    void calculate() { amount += amount * interestRate; }
    static double rate() { return interestRate; }
    static void rate(double);
private:
    std::string owner;
    double amount;
    static double interestRate;
    static double initRate();
};
```
类的静态成员存在于任何对象之外，对象中不包含任何与静态数据成员有关的数据。因此，每个 Account 对象将包含两个数据成员：owner 和 amount。只存在一个 interestRate 对象而且它被所有 Account 对象共享。

类似的，静态成员函数也不与任何对象绑定在一起，它们不包含 this 指针。作为结果，静态成员函数不能声明成 const 的，而且我们也不能在 static 函数体使用 this 指针。这一限制既适用于 this 的显式使用，也对调用非静态成员的隐式使用有效。

### 使用类的静态成员
我们使用作用域运算符直接访问静态成员：
```c++
double r;
r = Account::rate();      // 使用作用域运算符访问静态成员
```

虽然静态成员不属于类的某个对象，但是我们仍然可以使用类的对象、引用或者指针来访问静态成员：
```c++
Account ac1;
Account *ac2 = &ac1;

// 调用静态成员函数 rate 的等价形式
r = ac1.rate();    // 通过 Account 的对象或引用
r = ac2->rate();   // 通过指向 Account 对象的指针

```

成员函数不用通过作用域运算符就能直接使用静态成员：
```c++
class Account {
public:
    void calculate() { amount += amount * interestRate; }
private:
    static double interestRate;
};
```

### 定义静态成员
和其他的成员函数一样，我们既可以在类的内部也可以在类的外部定义静态成员函数。当在类的外部定义静态成员时，不能重复 static 关键字，该关键字只能出现在类内部的声明语句：
```c++
void Account::rate(double newRate)
{
    interestRate = newRate;
} 
```

> 和类的成员一样，当我们指向类外部的静态成员时，必须指明成员所属的类名。static 关键字则只能出现在类内部的声明语句中。

因为静态数据成员不属于类的任何一个对象，所以它们并不是在创建类的对象时被定义的。这意味着它们不是由类的构造函数初始化的。而且一般来说，我们不能在类内部初始化静态成员。相反的，必须在类的外部定义和初始化每一个静态成员。和其它对象一样，一个静态数据成员只能定义一次。
类似于全局变量，静态数据成员定义在任何函数之外。因此一旦它被定义，就将一直存在于程序的整个生命周期中。

我们定义静态数据成员的方式和在类的外部定义成员函数差不多。我们需要指定对象的类型名，然后是类名、作用域运算符以及成员自己的名字：
```c++
// 定义并初始化一个静态成员
double Account::interestRate = initRate();    
```

这条语句定义了名为 interestRate 的对象，该对象是类 Account 的静态成员，其类型是 double. 从类名开始，这条语句的剩余部分就都位于类的作用域之内了。因此，我们可以直接使用 initRate 函数。注意，虽然 initRate 是私有的，我们也能用它初始化 interestRate。和其它成员的定义一样，interestRate 的定义也可以访问类的私有成员。

> 要想确保对象只定义一次，最好的办法是把静态数据成员的定义与其他非内联函数的定义放在同一个文件中。

### 静态成员的类内初始化
通常情况下，类的静态成员不应该在类的内部初始化。然而，我们可以为静态成员提供 const 整数类型的类内初始值，不过要求静态成员必须是字面值常量类型的 constexpr。初始值必须是常量表达式，因为这些成员本身就是常量表达式，所以它们能用在所有适合于常量表达式的地方。例如，我们可以用一个初始化了的静态数据成员指定数组成员的维度：
```c++
class Account {
public:
    static double rate() { return interestRate; }
    static void rate(double);
private:
    static constexpr int peroid = 30;
    double daily_tbl[peroid];
};
```

如果某个静态成员的应用场景仅限于编译器可以替换它的值的情况，则一个初始化的 const 或 constexpr static 不需要分别定义。相反，如果我们将它用于值不能替换的场景中，则该成员必须有一条定义语句。

例如，如果 period 的唯一用途就是定义 daily_tbl 的维度，则不需要在 Account 外面专门定义 peroid. 此时，如果我们忽略了这条定义，那么对程序非常微小的改动也可能造成编译错误，因为程序找不到该成员的定义语句。举个例子，当需要把 Account::peroid 传递给一个接受 const int& 的函数时，必须定义 peroid。

如果在类的内部提供了一个初始值，则成员的定义不能再指定一个初始值了：
```c++
// 一个不带初始值的静态成员的定义
constexpr int Account::peroid;      // 初始值在类的定义内提供
```

> 即使一个常量静态数据成员在类内部被初始化了，通常情况下也应该在类的外部定义一下该成员。

### 静态成员能用于某些场景，而普通成员不能
如我们所见，静态成员独立于任何对象。因此，在某些非静态数据成员可能非法的场合，静态成员却可以正常使用。举个例子，静态数据成员可以是不安全类型。特别的，静态数据成员的类型可以就是它所属的类类型。而非静态数据成员则受到这个限制，只能声明成它所属类的指针或引用：
```c++
class Bar {
public:
    // ...
private:
    static Bar mem1;        // 正确：静态成员可以是不安全类型
    Bar *mem2;              // 正确：指针成员可以是不安全类型
    Bar mem3;               // 错误：数据成员必须是安全类型
};
```

静态成员和普通成员的另外一个区别是我们可以使用静态成员作为默认实参：
```c++
class Screen {
public:
    // bkground 表示一个类中稍后定义的静态成员
    Screen& clear(char = bkground);
private:
    static const char bkground;
};
```

非静态数据成员不能作为默认实参，因为它的值本身属于对象的一部分，这么做的结果是无法真正提供一个对象以便从中获取成员的值，最终将引发错误。