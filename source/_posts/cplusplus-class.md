---
title: C++系列：class 类
date: 2024-07-30 17:56:54
updated: 2024-07-30 17:56:54
tags:
- c++ 语言
- class 类
- 抽象数据类型
- 数据成员
- 成员函数
- 友元
- 访问控制
- 构造函数
categories: 
- 笔记
---

这篇文章主要讲述类的相关知识。

<!-- more -->

## 基础概念
类的基本思想是数据抽象 (data abstraction) 和封装 (encapsulation). 数据抽象是一种依赖于接口 (interface) 和 实现 （implementation）分离的编程（以及设计）技术。类的接口包括用户所能执行的操作：类的实现则包括类的数据成员、负责接口实现的函数以及定义类所需的各种私有函数。

封装实现类的接口和实现的分离。封装后的类隐藏了它的实现细节，也就是说，类的用户只能使用接口而无法访问实现部分。

类要实现数据抽象和封装，需要首先定义一个抽象数据类型(abstrace data type). 在抽象数据类型中，由类的设计者负责考虑类的实现过程；使用该类的程序员则只需要抽象地思考类型做了什么，而无须了解类型的工作细节。

## 定义抽象数据类型
我们可以使用 strcut 或 class 来定义抽象数据类型，在这个章节我们使用 class，这两者之间的区别的后面的内容讲解
```c++
class Sales_data {
public:     // 添加了访问说明符
    Sales_data() = default;
    Sales_data(const std::string &s, unsigned n, double p):
                bookNo(s), units_sold(n), revenue(p*n) {}
    Sales_data(const std::string &s) : bookNo(s) {}
    Sales_data(std::istream&);
    std::string isbn() const { return bookNo; }
    Sales_data &combine(const Sales_data&);
private:
    double avg_price() const 
        { return units_sold ? revenue/units_sold : 0; }
    std::string bookNo;
    unsigned units_sold = 0;
    double revenue = 0.0;
};
```
> 注意：需要在类定义的最后加上分号。

## 定义数据成员
类的数据成员定义了类的对象的具体内容，每个对象有自己的一份数据成员拷贝。修改一个对象的数据成员，不会影响其它的 Sales_data 的对象。

定义数据成员的方法和定义普通变量一样：首先说明一个基本类型，随后紧跟一个或多个声明符。在 Sales_data 类中，定义了 3 个数据成员：bookNo, string 类型，表示 ISBN 编号；units_sold, unsigned 类型，表示某本书的销量；以及 revenue, double 类型，表示这本书的总销售收入。每一个 Sales_data 的对象都包括这 3 个数据成员。

C++ 新标准规定，可以为数据成员提供一个**类内初始值(in-class initiallizer)**。创建对象时，类内初始值将用于初始化数据成员。没有初始值的成员将被默认初始化，因此当定义 Sales_data 的对象时，units_sold 和 revenue 都将初始化为 0，bookNo 将初始化为空字符串。

使用类内初始值有一些限制：或者放在花括号里，或者放在等号右边，但不能使用圆括号。

## 定义成员函数
在 Sales_data 中有三个成员函数：isbn, combine 和 avg_price。所有的成员函数必须在类的内部声明，但是成员函数可以在定义类内也可以类外。其中 isbn 定义在了类内，而 combine 和 avg_price 定义在了类外。

> 定义在类内部的函数是隐式的 inline 函数。

### 引入 this
成员函数通过一个名为 **this** 的额外的隐式参数来访问调用它的那个对象。当我们调用一个成员函数时，用请求该函数的对象地址初始化 this, 例如，如果这个调用：
```c++
total.isbn();   // total 为 Sales_data 对象
```
则编译器负责把 total 的地址传递给 isbn 的隐式形参 this, 可以等价地认为编译器将该调用写成了如下的形式：
```c++
// 伪代码，用于说明调用成员函数的实际执行过程
Sales_data::isbn(&total);
```
其中，调用 Sales_data 的 isbn 成员时传入了 total 的地址。

在成员函数内部，我们可以直接使用调用该函数的对象的成员，而无须通过成员访问运算符来做到这一点，因为 this 所指的正是这个对象。任何对类成员的直接访问都被看作 this 的隐式引用，也就是说，当 isbn 使用 bookNo 时，它隐式地使用 this 指向的成员，就像我们书写了 this->bookNo 一样。

对于我们来说，this 形参是隐式定义的。实际上，任何自定义为 this 的参数或变量的行为都是非法的。我们可以在成员函数体内部使用 this, 因此尽管没有必要，但我们还是能把 isbn 定义成如下的形式：
```c++
std::string isbn() const { return this->bookNo; }
```
因为 this 的目的总是指向 “这个” 对象，所以 this 是一个常量指针，我们不允许改变 this 中保存的地址。

### 引入 const 成员函数
isbn 函数的另一个关键之处是紧随参数列表之后的 const 关键字，这里，const 的作用是修改隐式 this 指针的类型。

默认情况下，this 的类型是指向类类型非常量版本的常量指针。例如 Sales_data 成员函数中，this 的类型是 Sales_data *const。尽管 this 是隐式的，但它仍需要遵循初始化规则，意味着（在默认情况下）我们不能把 this 绑定一个常量对象上。这一情况也就使得我们不能在一个常量对象上调用普通的成员函数。

如果 isbn 是一个普通函数而且 this 是一个普通的指针参数，则我们应该把 this 声明成 const Sales_data *const。 毕竟，在 isbn 的函数体内不会改变 this 所指的对象，所以把 this 设置为指向常量的指针有助于提高函数的灵活性。

然而，this 是隐式的并且不会出现在参数列表中，所以在那儿将 this 声明成指向常量的指针就成为我们必须面对的问题。 C++ 语言的做法是允许把 const 关键字放在成员函数的参数列表之后。此时，紧跟在参数列表后面的 const 表示 this 是一个指向常量的指针。像这样使用 const 的成员函数被称作 **常量成员函数(const member function)**。

可以把 isbn 的函数想象成如下的形式：
```c++
// 伪代码，说明隐式的 this 指针是如何使用的
// 下面的代码是非法的：因为我们不能显式地定义自己折 this 指针
// 谨记此处的 this 是一个指向常量的指针，因为 isbn 是一个常量成员
std::string Sales_data::isbn(const Sales_data *const this) 
{ return this->isbn }
```

因为 this 是指向常量的指针，所以常量成员函数不能改变调用它的对象的内容。在上例中，isbn 可以读取调用它的对象的数据成员，但是不能写入新值。

> 常量对象，以及常量对象的引用或指针都只能调用常量成员函数。

### 类作用域和成员函数
类本身就是一个作用域，类的成员函数的定义嵌套在类的作用域内，因此，isbn中用到的名字 bookNo 其实就是定义在 Sales_data 内的数据成员。

### 在类的外部定义成员函数
像其他函数一样，当我们在类的外部定义成员函数时，成员函数的定义必须与它的声明匹配。也就是说，返回类型、参数类型、参数列表和函数名称都得与类内部的声明一致。如果成员函数被声明成常量成员函数，那么它的定义也必须在参数列表后明确指定 const 属性。同时，类外部定义的成员的名字必须包含它所属的类名：
```c++
double Sales_data::avg_price() const { 
    return units_sold ? revenue/units_sold : 0; 
}
```
函数名 Sales_data::avg_price 使用作用域运算符来说明如下事实：我们定义了一个名为 avg_price 的函数，并且该函数被声明在类 Sales_data 的作用域内。一旦编译器看到这个函数名，就能理解剩余的代码是位于类的作用域内的。因此，当 avg_price 使用 revenue 和 units_sold 时，实际上它隐式地使用了 Sales_data 的成员。

### 定义一个返回 this 对象的函数
函数 combine 的设计初衷类似于复合赋值运算符 +=，调用该函数的对象代表的是赋值运行符左侧的运算对象，右侧运行对象则通过显式的实参被传入函数：
```c++
Sales_data& Sales_data::combine(const Sales_data &rhs) 
{
    units_sold += rhs.units_sold;   // 把 rhs 的成员加到 this 对象的成员上
    revenue += rhs.revenue;
    return *this;                   // 返回调用该函数的对象
}
```

当我们的交易处理程序调用如下的函数时：
```c++
total.combine(trans);       // 更新变量 total 当前的值
```
total 的地址被绑定到隐式的 this 参数上，而 rhs 绑定到了 trans 上。因此，当 combine 执行下面的语句时：
```c++
units_sold += rhs.units_sold;   // 把 rhs 的成员加到 this 对象的成员上
```
效果等同于求 total.units_sold 和 rhs.units_sold 的和，然后把结果保存到 total.units_sold 中。

该函数一个值得关注的部分是它的返回类型和返回语句。一般来说，当我们定义的函数类似于某个内置运算符时，应该令该函数的行为尽量模仿这个运算符。内置的赋值运算算把它的左侧运算对象当成左值返回，因此为了与它保持一致，combine 函数必须返回引用类型。因为此时的左侧运算对象是一个 Sales_data 的对象，所以返回类型应该是 Sales_data&。

如前所述，我们无须使用隐式的 this 指针访问函数调用者的某个具体成员，而是需要把调用函数的对象当成一个整体来访问：
```c++
return *this;
```
其中，return 语句解引用 this 指针以获得执行该函数的对象，换句话说，上面的这个调用返回 total 的引用。

## 构造函数
每个类都分别定义了它的对象被初始化的方式，类通过一个或几个特殊的成员函数来控制其对象的初始化过程，这些函数叫做**构造函数（constructor）**。构造函数的任务是初始化类对象的数据成员，无论何时只要类的对象被创建，就会执行构造函数。

构造函数的名字和类名相同。和其他函数不一样的是，构造函数没有返回类型；除此之外类似于其他的函数，构造函数也有一个（可能为空）参数列表和一个(可能为空的)函数体。类可以包含多个构造函数，和其它重载函数差不多，不同的构造函数之间必须在参数数量或参数类型上有所区别。

不同于其他成员函数，构造函数不能被声明成 const 的。当我们创建类的一个 const 对象时，直到构造函数完成初始化过程，对象才能真正取得其"常量"属性。因此，构造函数在 const 对象的构造过程中可以向其写值。

### 合成的默认构造函数
在 C++ 中，类通过一个特殊的构造函数来控制默认初始化过程，这个函数叫做**默认构造函数（default constructor）**，默认构造函数无须任何实参。

即使没有在类中没有定义任何构造函数，程序仍然可以正确地编译和运行。这主要是因为，编译器为程序创建了一个默认的构造函数，这个函数被称为 **合成的默认构造函数（synthesized default constructor）**。对于大多数类来说，这个合成的默认构造函数将按照如下规则初始化类的数据成员：
- 如果存在类内的初始值，用它来初始化成员；
- 否则，默认初始化该成员，如数值类型赋值为 0，string 类型赋值为空串。

因为 Sales_data 为 units_sold 和 revenue 提供了初始值，所以合成的默认构造函数将使用这些值来初始化对应的成员；同时，它把 bookNo 默认初始化成一个空字符串。

### 不适用合成默认构造函数的场景

对于一个普通的类来说，以下场景必须定义它自己的默认构造函数：
1. 只有当类没有声明任何构造函数时，编译器才会自动生成默认构造函数，一旦我们定义了一些其他的构造函数，那么除非我们再定义一个默认的构造函数，否则类将没有默认构造函数；
2. 如果类包含有内置类型或者复合类型（比如数组和指针）的成员，则只有当这些成员全都赋予了类内的初始值时，这个类才适用于合成的的默认构造函数，否则需要自定义默认构造函数；
3. 如果类中包含一个其它类类型的成员且这个成员的类型没有默认构造函数，那么编译器将无法初始化该成员。对于这样的类来说。我们必须自定义默认构造函数，否则该类将没有可用的默认的构造函数。

### =default 的含义
我们从解释默认构造函数的含义开始：
```c++
Sales_data() = default;
```
首先先明确一点：因为该构造函数不接受任何实参，所以它是一个默认构造函数。我们定义这个构造函数的目的仅仅是因为我们既需要其他形式的构造函数，也需要默认的构造函数。我们希望这个函数的作用完全等同于之前使用的合成默认构造函数。

在 C++ 新标准中，如果我们需要默认的行为，那么可以通过在参数列表后面加上 **= default** 来要求编译器生成构造函数。其中，= default 既可以和声明一起出现在类的内部，也可以作为定义出现在类的外部。和其它函数一样，如果 = default 在类的内部，则默认构造函数是内联的；如果它在类的外部，则该成员默认情况下不是内联的。

> 上面的默认构造函数之所以对 Sales_data 有效，是因为我们为内置的数据成员提供了初始值。如果你的编译器不支持类内初始值，那么你的默认构造函数就应该使用构造函数初始值列表来初始化类的每个成员。

### 构造函数初始值列表
接下来我们介绍类中定义的另外两个构造函数：
```c++
Sales_data(const std::string &s, unsigned n, double p):
        bookNo(s), units_sold(n), revenue(p*n) {}
Sales_data(const std::string &s) : bookNo(s) {}
```
在这两个定义中出现了新的部分，即冒号以及冒号和花括号之间的代码，其中花括号定义了（空的）函数体。我们把新出现的部分称为**构造函数初始值列表（constructor initialize list）**，它负责为新创建的对象的一个或几个数据成员赋初值。构造函数初始值是成员名字的一个列表，每个名字后面紧跟括号括起来的（或者在花括号内的）。不同成员的初始值通过逗号分隔开来。

含有三个参数的构造函数分别使用它的前两个参数初始化成员 bookNo 和 units_sold，revenue 的初始值则通过将售出图书总数和每本书单价相乘计算得到。

只有一个 string 类型参数的构造函数使用这个 string 对象初始化 bookNo, 对于 units_sold 和 revenue 则没有显式地初始化。当某个数据成员被构造函数初始值列表忽略时，它将以与合成默认构造函数相同的方式隐式初始化。在此例中，这样的成员使用类内初始值初始化。因此只接受一个 string 参数的构造函数等价于：
```c++
Sales_data(const std::string &s):
        bookNo(s), units_sold(0), revenue(0) {}
```

通常情况下，构造函数使用类内初始值不失为一种好的选择，因为只要这样的初始值存在我们就能确保为成员赋予一个正确的值。不过，如果你的编译器不支持类内初始值，则所有构造函数都应该显式地初始化每个内置类型的成员。

有一点需要注意，在上面的两个构造函数中函数体都是空的。这是因为这些构造函数的唯一目的就是为数据成员赋初值，一旦没有其他任务需要执行，函件体也就为空了。

### 在类的外部定义构造函数
与其他几个构造函数不同，以 istream 为参数的构造函数需要执行一些实际的操作。在它的函数体内，调用了 read 函数以给数据成员赋以初值：
```c++
Sales_data::Sales_data(std::istream &is) 
{
    read(is,*this);     // read 函数的作用是 is 中读取一条交易信息然后存入 this 对象中。
}
```

构造函数没有返回类型，所以上述定义从我们指定的函数名字开始。和其他成员函数一样，当我们在类外部定义构造函数时，必须指定该构造函数是哪个类的成员。因此，Sales_data::Salles_data 的含义是我们定义 Salses_data 类的成员，它的名字是 Sales_data。又因为该成员的名字和类名相同，所以它是一个构造函数。

这个构造函数没有构造函数初始值列表，或者讲得更准确一点，它的构造函数初始值列表是空的。尽管构造函数初始值列表是空的，但是由于执行了构造函数体，所以对象的成员仍然能被初始化。

没有出现在构造函数初始值列表中的成员通过相应的类内初始值（如果存在的话）初始化，或者执行默认初始化。对于 Sales_data 来说，这意味着一旦函数开始执行，则 bookNo 将被初始化为空 string 对象，而 units_sold 和 revenue 将是 0。

更详细的关于构造函数的内容将在后续的文章讲解。

## 拷贝、赋值和析构
除了定义类的对象如何初始化之外，类还需要控制拷贝、赋值和销毁对象时发生的行为。对象在几种情况下会被拷贝，如我们初始化变量以及以值的方式传递或返回一个对象等。当我们使用了赋值运算符时会进行对象的赋值操作。当对象不再存在时执行销毁操作，比如一个局部对象会在创建它的块结束时销毁，当 vector 对象（或者数组）销毁时存储在其中的对象也会被销毁。

如果我们不主动定义这些操作，则编译器将替我们合成它们。一般来说，编译器生成的版本将对对象的每个成员执行拷贝、赋值和销毁操作。

### 某些类不能依赖于合成的版本
尽管编译器能替我们合成拷贝、赋值和销毁的操作。但是必须要清楚的一点是，对于某些类来说合成的版本无法正常工作。特别是，当类需要分配对象之外的资源时，合成的版本常常失效。如管理动态内存的类通常不能依赖于上述操作的合成版本。

不过值得注意的是，很多需要动态内存的类能（而且应该）使用 vector 对象或者 string 对象管理必要的存储空间。使用 vector 或者 string 的类能避免分配和释放内存带来的复杂性。

进一步讲，如果类包含 vector 或者 string 成员，则其拷贝、赋值和销毁的合成版本能够正常工作。当我们对含有 vector 成员的对象执行拷贝或者赋值操作时，vector 类会设法拷贝或赋值成员中的元素。当这样的对象被销毁时，将销毁 vector 对象，也就是依次销毁 vector 中的每一个元素。这一点与 string 是非常类似的。

## 访问控制与封装
在 C++ 语言中，我们使用访问说明符（access specifiers）加强类的封装性：
- 定义在 **public** 说明符之后的成员在整个程序内可被访问，public 成员定义类的接口；
- 定义在 **private** 说明符之后的成员可以被类的成员函数访问，但是不能被使用该类的代码访问，private 部分封装了（即隐藏了）类的实现细节。

**使用 class 或 struct 关键字**
使用 class 或 struct 都可以自定义数据结构，区别在于它们的默认访问权限不一样。如果不指定访问说明符，struct 默认为 public，而 class 默认为 private.

### 友元
类可以允许其它类或者函数访问它的非公有成员，方法是令其他类或者函数成为它的**友元(friend)**。如果类想把一个函数作为友元，只需要增加一条以 friend 关键字开始的函数声明语句即可：
```c++
class Sales_data {
// 为 Sales_data 的非成员函数所做的友元声明
friend Sales_data add(const Sales_data&, const Sales_data&);
friend std::istream &read(std::istream&, Sales_data&);
friend std::ostream &print(std::ostream&, const Sales_data&);

public:     // 添加了访问说明符
    Sales_data() = default;
    Sales_data(const std::string &s, unsigned n, double p):
                bookNo(s), units_sold(n), revenue(p*n) {}
    Sales_data(const std::string &s) : bookNo(s) {}
    Sales_data(std::istream&);
    std::string isbn() const { return bookNo; }
    Sales_data &combine(const Sales_data&);
private:
    double avg_price() const 
        { return units_sold ? revenue/units_sold : 0; }
    std::string bookNo;
    unsigned units_sold = 0;
    double revenue = 0.0;
};

// Sales_data 接口的非成员组成部分的声明
Sales_data add(const Sales_data&, const Sales_data&);
std::istream &read(std::istream&, Sales_data&);
std::ostream &print(std::ostream&, const Sales_data&);
```

友元声明只能出现在类定义的内部，但是在类内出现的具体位置不限。友元不是类的成员也不受它所在区域访问控制级别的约束。

> 一般来说，最好在类定义开始或结束前的位置集中声明友元。

### 友元的声明
友元的声明仅仅指定了访问的权限，而非一个通常意义上的函数声明。如果我们希望类的用户能够调用某个友元函数，那么我们就必须在友元声明之外再专门对函数进行一次声明。

为了使友元对类的用户可见，我们通常把友元的声明与类本身放置在同一个头文件中（类的外部）。因此，我们的 Sales_data 头文件应该为 read、print 和 add 提供独立的声明（除了类内部的友元声明之外）。

## 类的其他特性
这些特性包括：类型成员、类的成员的类内初始值、可变数据成员、内联成员函数、从成员函数返回 *this、类类型及友元类。

为了展示这些新的特性，我们需要定义一对相互关联的类，它们分别是 Screen 和 Window_mgr。

### 定义一个类型成员
Screen 表示显示器中的一个窗口。每个 Screen 包含一个用于保存 Screen 内容的 string 成员和三个 string::size_type 类型的成员，它们分别表示光标的位置以及屏幕的高和宽。

除了定义数据和函数成员之外，类还可以自定义某种类型在类中的别名。由类定义的类型名字和其他成员一样存在访问限制，可以是 public 或者 private 中的一种：
```c++
class Screen {
public:
    typedef std::string::size_type pos;
private:
    pos cursor = 0;
    pos height = 0, width = 0;
    std:string contents;
}
```

我们在 Screen 的 public 部分定义了 pos, 这样用户就可以使用这个名字。Screen 的用户不应该知道 Screen 使用了一个 string 对象来存放它的数据，因此通过把 pos 定义成 public 成员可以隐藏 Screen 实现的细节。

关于 pos 的声明有两点需要注意。首先，我们使用了 typedef, 也可以等价地使用类型别名：
```c++
class Screen {
public:
    // 使用类型另名等价地声明一个类型名字
    using pos std::string::size_type;
```

<font color=red>需要注意一点的是，用来定义类型的成员必须先定义后使用。</font>

### Screen 类的成员函数
为了使得 Screen 更实用，我们加入一些成员函数：
```c++
class Screen {
public:
    typedef std::string::size_type pos;
    Screen() = default;     // 因为 Screen 有另一个构造函数
                            // 所以本函数是必需的
    // cursor 被其类内初始值初始化为 0
    Screen(pos ht, pos wd, char c): height(ht), width(wd),
    contents(ht * wd, c) {}
    char get() const                    // 读取光标处的字符
        { return contents[cursor]; }    // 隐式内联
    inline char get(pos ht, pos wd) const:  // 显式内联
    Screen &move(pos r, pos c);         // 能在之后被设为内联
private:
    pos cursor = 0;
    pos height = 0, width = 0;
    std:string contents;
}
```
因为我们已经提供了一个构造函数，所以编译器将不会自动生成默认的构造函数。如果我们需要的类需要默认构造函数，必须显式地把它声明出来。在此例中，我们使用 =default 告诉编译器为我们合成默认的构造函数。

### 令成员作为内联函数
在类中，常有一些规模较小的函数适合于被声明成内联函数。定义在类内部的成员函数是自动 inline 的。因此，Screen 的构造函数和返回光标所指字符的 get 函数默认是 inline 函数。

可以在类的内部把 inline 作为声明的一部分显式地声明成员函数，同样的，也能在类的外部用 inline 关键字修饰函数的定义：
```c++
inline                      // 可以在函数的定义处指定 inline
Scrren *Screen::move(pos r, pos c)
{
    pos row = r * width;    // 计算行的位置
    cursor = row + c;       // 在行内将光标移动指定的列
    return *this;           // 以左值的形式返回对象
}

char Screen::get(pos r, pos c) const // 在类内部声明成 inline
{
    pos row = r * width;        // 计算行的位置
    return contents[row + c];   // 返回给定列的字符
}
```

虽然无须在声明和定义的地方同时说明 inline, 但这么做其实是合法的。不过，最好只在类外部定义的地方说明 inline, 这样可以使类更容易理解。

### 可变数据成员
有时会发生这样一种情况，我们希望能修改类的某个数据成员，即使是在一个 const 成员函数内。可以通过在变量的声明中加入 mutable 关键字做到这一点。如下所示：
```c++
class Screen {
public:
    void some_member() const;
private:
    mutable size_t access_ctr;      // 即使在一个 const 对象内也能被修改
    // ...
};

void Screen::some_member() const
{
    ++access_ctr;           // 保存一个计数值，用于记录成员函数调用的次数
    // ...
}

```
尽管 some_member 是一个 const 成员函数，它仍然能够改变 access_ctr 的值。该成员是个可变成员，因此任何成员函数，包括 const 函数在内都能改变它的值。

### 娄数据成员的初始值
在定义好 Screen 类之后，将继续定义一个窗口管理类并用它表示显示器上的一组 Screen。这个类将包含一个 Screen 类型的 vector, 每个元素表示一个特定的 Screen。默认情况下，我们希望 Window_mgr 类开始时拥有一个默认初始化的 Screen。在 C++ 新标准中，最好的方式就是把这个默认值声明成一个类内初始值。
```c++
class Window_mgr {
private:
    // 这个默认 Window_mgr 追踪的 Screen
    // 默认情况下，一个 Window_mgr包含一个标准尺寸的空白 Screen
    std::vector<Screen> screens{Screen(24, 80, ' ')};
}
```

类内初始值必须使用 = 的初始形式（初始化 Screen 的数据成员是所用的） 或者花括号括起来的直接初始化形式（初始化 screens 所用）。


## 类类型
对于两个类来说，即使它们的成员完全一样，这两个类也是两个不同的类型。

我们可以把类名作为类型的名字使用，从而直接指向类类型。或者，我们也可以把类名跟在关键字 class 或 struct 后面：
```c++
Sales_data item1;       // 默认初始化 Sales_data 类型的对象
class Sales_data item1; // 与上面的声明等价
```
上面这两种使用类类型的方式是等价的，其中第二种方式从 C 语言继承而来，并且在 C++ 语言中也是合法的。

### 类的声明
就像可以把函数的声明和定义分离开来一样，我们也能仅仅声明而暂时不定义它：
```c++
class Screen;       // Screen 类的声明
```
这种声明有时被称为 **前向声明（forward declaration）**，它向程序中引入了名字 Screen 并且声明 Screen 是一种类型。对于类型 Screen 来说，在它声明之后定义之前是一个**不完全类型（incomplete type）**，也就是说，此时我们已知 Screen 是一个类类型，但是不清楚它到底包含哪些成员。

不安全类型只能在非常有限的情景下使用：可以定义指向这种类型的指针和引用，也可以声明（但是不能定义）以不完全类型作为参数或者返回类型的函数。

## 友元再探
之前在我们在 Sales_data 类中把三个普通的非成员函数定义成了友元。类还可以把其它的类定义成友元，也可以把其它类的成员函数定义成友元。此外，友元函数能定义在在娄的内部，这样的函数是隐式内联的。

### 类之间的友元关系
举个友元的例子，我们的 Window_mgr 类的某些成员可能需要访问它管理的 Screen 类的内部数据。例如，假设我们需要为 Window_mgr 添加一个名为 clear 的成员，它负责把一个指定的 Screen 的内容都设为空白。为了完成这个任务，clear 需要访问 Screen 的私有成员；而要想令这种访问合法，Screen 需要把 Window_mgr 指定成它的友元：
```c++
class Screen {
    // Window_mgr 的成员可以访问 Screen 类的私有部分
    friend class Window_mgr;
    // Screen 类的剩余部分
};
```

如果一个类指定了友元类，则友元类的成员函数可以访问此类包括非公有成员在内的所有成员。通过上面的声明，Window_mgr 被指定为 Screen 的友元，因此我们可以将 Window_mgr 的 clear 成员写成如下的形式：
```c++
class Window_mgr {
public:
    // 窗口中每一个屏幕的编号
    using ScreenIndex = std::vector<Screen>::size_type;
    // 按照编号将指定的 Screen 重置为空白
    void clear(ScreenIndex);
private:
    std::vector<Screen> screens{ Screen(24, 80, '')};
};

void Window_mgr::clear(ScreenIndex i) 
{
    // s 是一个 Screen 的引用，指向我们想清空的那个屏幕
    Screen &s = screens[i];
    // 将那个选定的 Screen 重置为空白
    s.contents = string(s.height * s.width, ' ');
}
```
将 Window_mgr 定义为 Screen 的友元类之后，在 Window_mgr 对象的成员函数中就可以直接访问 Screen 对象的私有字段 contents。

需要注意一点，友元关系不存在传递性。也就是说，如果 Window_mgr 有它自己的友元，则这些友元并具有访问 Screen 的特权。

> 每个类负责控制自己的友元或友元函数。

### 令成员函数作为友元
除了令整个 Window_mgr 作为友元之外，Screen 还可以只为 clear 提供访问权限。当把一个成员函数声明成友元时，我们必须明确指出该成员函数属于哪个类：
```c++
class Screen {
    // Window_mgr::clear 必须在 Screen 类之前声明
    friend void Window_mgr::clear(ScreenIndex);
    // Screen 类的剩余部分
};
```

要想令某个成员函数作为友元，我们必须仔细组织程序的结构以满足声明和定义的彼此依赖关系。在这个例子中，我们必须按照如下方式设计程序：
- 首先定义 Window_mgr 类，其中声明 clear 函数，但是不能定义它。在 clear 使用 Screen 的成员之前必须先声明 Screen；
- 接下来定义 Screen，包括对于 clear 的友元声明；
- 最后定义 clear, 此时它才可以使用 Screen 的成员。

### 函数重载和友元
如果一个类想把一组重载函数声明成它的友元，它需要对这组函数中的每一个函数分别声明。

### 友元声明和作用域
在类中声明了友元函数，即使该友元函数在类内部进行了定义，也必须在类的外部提供相应的声明从而使得函数可见。换句话说，即使我们仅仅是用声明友元的类的成员调用该友元函数，它也必须是被声明过的：
```c++
struct X {
    friend void f() { /* 友元函数可以定义在类的内部 */ }
    X() { f(); }        // 错误：f 还没有声明
    void g();
    void h();
};

void X::g() { f(); }    // 错误：f 还没有被声明
void f();               // 声明那个定义在 X 中的函数
void X::h() { f(); }    // 正确：现在 f 的声明在使用域中了
```

### 类的作用域

一个类就是一个作用域，一旦遇到了类名，成员函数定义的剩余部分就在类的作用域之内了，这里的剩余部分包括参数列表和函数体。如果就是，我们可以直接使用类的其它成员而无须两次授权了。如下面的代码：

```c++
void Window_mgr::clear(ScreenIndex i) 
{
    // s 是一个 Screen 的引用，指向我们想清空的那个屏幕
    Screen &s = screens[i];
    // 将那个选定的 Screen 重置为空白
    s.contents = string(s.height * s.width, ' ');
}
因为编译器在处理参数列表之前已经明确了我们当前正位于 Window_mgr 类的作用域中，所以不必再专门说明 ScreenIndex 是 Window_mgr 类定义的。出于同样的原因，也能知道函数体中用到的 screens 也是在 Window_mgr 类中定义的。

另一方面，函数的返回类型通常出现在函数名之前。因此当成员函数定义在类的外部时，返回类型中使用的名字都位于类的作用域之外。这时，返回类型必须指明它是哪个类的成员。例如，我们可能向 Window_mgr 类中添加一个新的 addScreen 的函数，它负责向显示器添加一个新的屏幕。这个成员的返回类型将是 ScreenIndex，用户可以通过它定位到指定的 Screen：

```c++
class Window_mgr {
public:
    // 窗口中每一个屏幕的编号
    ScreenIndex addScreen(const Screen&);
};

Window_mgr::ScreenIndex 
Window_mgr::addScreen(const Screen &s)
{
    screens.push_back(s);
    return screens.size() - 1;
}
```
因为返回类型出现在类名之前，所以事实上它是位于 Window_mgr 类的作用域之外的。在这种情况下，要想使用 ScreenIndex 作为返回类型，我们必须明确指定哪个类定义了它。

## 构造函数再探

### 构造函数初始值列表
构造函数的执行包括两个步骤：
- 数据成员的初始化；
- 执行函数体(或进行赋值)。

在执行构造函数体之前，需要进行数据成员的初始化。如果没有构造函数初始值列表，则执行默认初始化。

在一些场景下，不能缺少构造函数初始值列表。如果成员是 const、引用，或者属于某种未提供默认构造函数的类类型，我们必须通过构造函数初始值列表为这些成员提供初始值。

### 默认实参和构造函数

如果一个构造函数为所有参数都提供了默认实参，则它实际上也是作为默认构造函数。

### 委托构造函数
C++11 新标准扩展了构造函数初始值的功能，使得我们可以所谓的**委托构造函数（delegating constructor）**。一个委托构造函数使用它所属类的其它构造函数来执行它自己的初始化过程，或者说它把它自己的一些（或者全部）职责委托给了其他构造函数。如下例子所示:
```c++
class Sales_data {
public:
    // 非委托构造函数使用对应的实参初始化成员
    Sales_data(const std::string s, unsigned n, double p):
                bookNo(s), units_sold(n), revenue(p*n) {}
    // 其余构造函数全部委托给另一个构造函数
    Sales_data() : Sales_data("", 0, 0) {}
    Sales_data(std::string s) : Sales_data(s, 0, 0) {}
    Sales_data(std::istream &is) : Sales_data() 
                                {  read(is, *this) }

    // ...
};
```
要这个 Sales_data 类中，除了一个构造函数外其他的的都委托了它们的工作。第一个构造函数接受三个实参，使用这些实参初始化数据成员，然后结束工作。我们定义默认构造函数令其使用三参数的构造函数完成初始化过程，它也无须执行其他任务，在这一点从空的构造函数体能看得出来。接受一个 string 要构造函数同样委托给了三参数的版本。

接受 istream& 的构造函数也是委托函数，它委托给了默认构造函数，默认构造函数又接着委托给三参数构造函数。当这些受委托的构造函数执行完成后，接着执行 istream& 构造函数体的内容。它的构造函数体调用 read 函数读取给定的 istream。

当一个构造函数委托给另一个构造函数时，受委托的构造函数的初始值列表和函数体依次执行。在 Sales_data 类中，受委托的构造函数体恰好是空的。假如函数体包含有代码的话，将先执行这些代码，然后控制权才会交还给委托者的函数体。

### 隐式的类类型转换
如果构造函数只接受一个实参，则它实际上定义了转换为此类类型的隐式转换机制，有时我们把这种构造函数称作**转换构造函数（converting constructor）**。如下所示：
```c++
class Sales_data {
public:
    Sales_data() = default;
    Sales_data(const std::string &s) : bookNo(s) {}
    Sales_data(std::istream&);
    Sales_data &combine(const Sales_data&);
    // ...
};
```
在 Sales_data 类中，接受了 string 的构造函数和接受 istream 的构造函数分别定义了从这两种类型向 Sales_data 隐式转换的规则。也就是说，在需要使用 Sales_data 的地方，我们可以使用 string 或者 istream 作为替代：
```c++
// 从 string 到 Sales_data 的转换
string null_book = "9-999-99999-9";
// 构造一个临时的 Sales_data 对象
// 该对象的 units_sold 和 vevenue 等于 0，bookNo 等于 null_book
item.combine(null_book);

// 从 istream 到 Sales_data 的转换
// 使用 istream 构造函数创建一个临时对象 Sales_data 传递给 combine。
std::istream cin;
item.combine(cin);

```

#### 只允许一步类类型转换
编译器只会自动地执行一步类型转换。例如，因为下面的代码隐式地使用了两种转换规则，所以它是错误的：
```c++
// 错误：需要用户定义的两种转换：
// 1) 把 "9-999-99999-9" 转换成 string;
// 2) 再把这个（临时）string 转换成 Sales_data
item.combine("9-999-99999-9");

```

#### expicit 关键字
如果要阻止类类型的隐式转换，可以通过添加 expicit 关键字来实现。
```c++
class Sales_data {
public:
    Sales_data() = default;
    expicit Sales_data(const std::string &s) : bookNo(s) {}
    expicit Sales_data(std::istream&);
    Sales_data &combine(const Sales_data&);
    // ...
};

```
此时，没有任何构造函数能用于隐式创建 Sales_data 对象，之前的两种用法都无法通过编译：
```c++
item.combine(null_book);    // 错误：string 构造函数是 expicit 的
item.combine(cin);          // 错误：istream 构造函数是 expicit 的
```

关键字 expicit 只对一个实参的构造函数有效，需要多个实参的构造函数不能用于隐式转换，所以无须将这些构造函数指定为 expicit。只能在类内声明构造函数是使用 expicit 关键字。在类外部定义是不应重复。

#### expicit 构造函数只能用于直接初始化
我们只能在使用直接初始化使用 expicit 构造函数：
```c++
Sales_data item1(null_book);     // 正确：直接初始化

// 错误：不能将 expicit 构造函数用于拷贝形式的初始化过程
Sales_data item1 = null_book;
```

#### 为转换显式地使用构造函数
尽管编译器不会将 expicit 的构造函数用于隐式转换过程，但是我们可以使用这样的构造函数显式地强制进行转换：
```c++
// 正确：实参是一个显式构造的 Sales_data 对象
item.combine(Sales_data(null_book));

// 正确：static_cast 可以使用 expicit 的构造函数
item.combine(static_cast<Sales_data>(cin))
```

### 聚合类
**聚合类（aggregate class）**使得用户可以直接访问其成员，并且具有特殊的初始化语法形式。当一个类满足如下条件时，我们说它是聚合的：
- 所有成员都是 public 的；
- 没有定义任何构造函数；
- 没有类内初始值；
- 没有基类，也没有 virtual 函数。

例如，下面的类是一个聚合类：
```c++
struct Data {
    int ival; 
    string s;
}
```
我们可以提供一个花括号括起来的成员初始值列表，并且它初始化聚合类的数据成员：
```c++
// val1.ival = 0, val1.s = string("Anna")
Data val1 = { 0, "Anna"};
```
另外，初始值的顺序必须与声明的顺序一致，否则会报错。

### 字面值常量类
类类型也可以是字面值类型，数据成员都是字面值类型的聚合类是字面值常量类。如果一个类不是聚合类，但它符合下述要求，则它也是一个字面常量类：
- 数据成员都必须是字面值类型；
- 类必须至少含有一个 constexpr 构造函数；
- 如果一个数据成员含有类内初始值，则内置类型成员的初始值必须是一条常量表达式；或者如果成员属于某种类类型，则初始值必须使用成员自己的 constexpr 构造函数；
- 类必须使用析构函数的默认定义，该成员负责销毁类的对象。

#### constexpr 构造函数
尽管构造函数不能是 const 的，但是字面值常量类构造函数可以是 constexpr 函数。事实上，一个字面常量类必须至少提供一个 constexpr 构造函数。

constexpr 构造函数必须初始化所有的数据成员，初始值或者使用 constexpr 构造函数，或者是一条常量表达式。

