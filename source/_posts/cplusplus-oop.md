---
title: C++系列：继承和动态绑定
date: 2024-07-30 17:57:15
updated: 2024-07-30 17:57:15
tags:
- c++ 语言
- 面向对象程序设计
- 继承
- 动态绑定
- 基类
- 派生类
- 虚函数
- 抽象基类
- 纯虚函数
categories: 
- 笔记
---

这篇文章讲解 C++ 对象的继承和动态绑定相关知识。

<!-- more -->

# 概述
**面向对象程序设计（object-oriented programming）**的核心思想是数据抽象、继承和动态绑定。通过数据抽象，我们可以将类的接口与实现分离；使用继承，可以定义相似的类型并对其相似关系建模；使用动态绑定，可以在一定程度上忽略相似类型的区别，而以统一的方式使用它们的对象。

## 继承
通过**继承（inheritance）**联系在一起的类构成一种层次关系。通常在层次关系的根部有一个**基类（base class）**，其他类则直接或间接地从基类继承而来，这些继承得到的类称为**派生类（derived class）**。基类负责定义在层次关系中所有类共同拥有的成员，而每个派生类定义各自特有的成员。

为了演示继承关系，我们定义如下的类：Quote 是一个基类，表示按原价销售的书籍。 Quote 派生出另一个它为 Bulk_quote 的类，它表示可以打折销售的书籍。

这些类将包含下面的两个成员函数：
- isbn()，返回书籍的 ISBN 编号。该操作不涉及派生类的特殊性，因此只定义在 Quote 类中。
- net_price(size_t), 返回书籍的实际销售价格，前提是用户购买该书的数量达到一定标准。这个操作显然是类型相关的，Quote 和 Bulk_quote 都应该包含该函数。

在 C++ 语言中，基类将类型相关的函数与派生类不做改变直接继承的函数区分对待。对于某些函数，基类希望它的派生类各自定义适合自身的版本，此时基类就将这些函数声明成**虚函数（virtual fuction）**。因此，我们可以将 Quote 类编写成：
```c++
class Quote {
public:
    std::string isbn() const;
    virtual double net_price(std::size_t n) const;
};
```

派生类必须通过使用**类派生列表（class derivation list）**明确指出它是从哪个（哪些）基类继承而来的。类派生列表的形式是：首先是一个冒号，后面紧跟以逗号分隔的基类列表，其中每个基类前面可以有访问说明符：
```c++
class Bulk_quote : public Quote {   // Bulk_quote 继承了 Quote
public:
    double net_price(std::size_t) const override;
};

```
因为 Bulk_quote 在它的派生列表中使用了 public 关键字。因此我们完全可以把 Bulk_quote 的对象当成 Quote 的对象来使用。

派生类必须在其内部对所有重新定义的虚函数进行声明。派生类可以在这样的函数之前加上 virtual 关键字，但这不是必须的。C++11 新标准允许派生类显式地注明它将使用哪个成员函数改定基类的虚函数，具体措施是在该函数的形参列表之后增加一个 override 关键字。

## 动态绑定
通过使用**动态绑定（dynamic binding）**，我们能用同一段代码分别处理 Quote 和 Bulk_quote 的对象，例如，当要购买的书籍和购买的数量都已知时，下面的函数负责打印总的费用：
```c++
// 计算并打印销售给定数量的某种书籍所得的费用
double print_total(ostream &os,
                    const Quote &item, size_t n) 
{
    // 根据传入 item 形参的对象类型调用 Quote::net_price
    // 或者 Bulk_quote:net_price
    double ret = item.net_price(n);
    os << "ISBN: " << item.isbn()   // 调用 Quote::isbn
       << " # sold: " << n << " total due: " << ret << endl;
    
    return ret;
}
```

该函数非常简单：它返回调用 net_price() 的结果，并将该结果连同调用 isbn() 的结果一起打印出来。

函数 print_total 的 item 形参是基类 Qutoe 的一个引用。它既可以接受 Qutoe 对象，也可以接受 Bulk_quote 的对象，根据实际的类型来决定调用那一个版本的 net_price 函数。
```c++
// basic 的类型是 Qutoe, bulk 的类型的是 Bulk_quote
print_total(cout, basic, 20);       // 调用 Qutoe 的 net_price
print_total(count, bulk, 20);       // 调用 Bulk_quote 的 net_price
```

在上述过程中函数的运行版本由实参决定，即在运行时选择函数的版本，所以动态绑定有时又被称为**运行进绑定（run-time binding）**。

> 在 C++ 语言中，当我们使用基类的引用（或指针）调用一个虚函数时将发生动态绑定。

# 定义基类和派生类
## 定义基类
```c++
class Quote {
public:
    Quote() = default;      // 生成默认参数
    Quote(const std::string &book, double sales_price):
        bookNo(book), price(sales_price) { }
    std::string isbn() const { return bookNo; }
    // 返回给定数量的书籍的销售总额
    // 派生类负责改写并使用不同的折扣计算算法
    virtual double net_price(std::size_t n) const 
                { return n * price; }
    virtual ~Quote() = default;     // 对析构函数进行动态绑定
private:
    std::string bookNo;     // 书籍的ISBN编号
protected:
    double price = 0.0;     // 代表普通状态下不打折的价格
};
```

### virtual 函数
在 C++ 语言中，基类必须将它的两种成员函数区分开来：一种是基类希望其派生类进行覆盖的函数；另一种是基类希望派生类直接继承而不要改变的函数。对于前者，基类通常将定义为**虚函数（virtual）**。当我们使用指针或引用调用虚函数时，该调用将被动态绑定。根据引用或指针所绑定的对象类型不同，该调用可能执行该基类的方法，也可能执行某个派生类的版本。

### 访问控制与继承
有三种的访问运算符：
- public: 公开的成员对于类的用户或派生类来说可以访问的；
- private: 私有的成员对于类的用户或派生类来说是不可以访问的；
- protected: 受保护的成员对于类的用户来说是不可访问的，对于派生类的成员和友元来说是可访问的，另外，派生类的成员或友元只能通过派生类对象来访问基类的受保护成员。派生类对于一个基类对象中的受保护成员没有任何访问特权。

> 一个类有三种不同的用户：1）普通用户；2）类本身或友元；3）派生类。普通用户，使用类的外部代码，这部分代码只能访问类的公有（接口）成员；类的其它成员函数或友元既能访问类的公有部分，也能访问类的私有（实现）总部分；派生类可以访问基类的公有及受保护的部分，普通用户不能访问受保护的成员。

## 虚析构函数
通常来讲，基类都应该定义一个虚析构函数，当 delete 一个对象指针时，会动态调用其不同类型的析构函数，如果指向基类，调用基类的析构函数，如果指向派生类，则调用派生类的析构函数。

## 定义派生类

派生类必须通过使用**类派生列表（class derivation list）**明确指出它是从哪个（哪些）基类继承而来的。类派生列表的形式是：首先是一个冒号，后面紧跟以逗号分隔的基类列表，其中每个基类前面可以有三种访问说明符中一个：public、protected 或者 private。

派生类必须将需要覆盖的那些成员函数重新声明，因此，Bulk_quote 类必须包含一个 net_price 成员：
```c++
class Bulk_quote : public Quote {       // Bulk_quote 继承自 Quote
public:
    Bulk_quote() = default;
    Bulk_quote(const std::string&, double, std::size_t, double);
    // 覆盖基类的函数版本以实现基于大量购买的折扣政策
    double net_price(std::size_t) const override;
private:
    std::size_t min_qty = 0;        // 适用折扣政策的最低购买量
    double discount = 0.0;          // 以小数表示的折扣额
}
```

Bulk_quote 类从它的基类 Quote 那里继承了 isbh 函数和 bookNo、price 等数据成员。此外，它还定义了 net_price 的新版本，同时拥有两个新增加的数据成员 min_qty 和 discount。这两个成员分别用于说明享受折扣所需购买的最低数量以及一旦该数量达到后具体的折扣信息。

### 公有、私有和受保护继承
类派生列表中的访问说明符目的是用来控制派生类用户（包括派生类的的派生类在内）对于基类成员的访问权限：
- public: 派生类的普通用户可以访问基类的 public 成员；派生类成员或友元可以访问基类的 pubic 或 protectd 成员；
- private: 派生类的普通用户不能访问基类的成员；派生类成员或友元可以访问基类的 pubic 或 protectd 成员；
- protectd: 派生类的普通用户不能访问基类的成员；派生类成员或友元可以访问基类的 pubic 或 protectd 成员；

派生类访问符对于派生类的成员（及友元）能否访问其直接基类的成员没什么影响。对基类成员的访问权限只与基类中的访问说明符有关。

### 派生类中的虚函数
正常情况下，派生类经常覆盖基类的中的虚函数，如果派生类没有覆盖其基类的某个虚函数，则该虚函数的行为类似于其它的普通成员，派生类会直接继承其在基类中的版本。

C++新标准允许派生类显式地注明它覆盖虚函数，具体做法是在形参列表后面、或者在 const 成员函数的 const 关键字后面、或者在引用成员函数的引用限定符后面添加一个关键字 override.

### 派生类对象及派生类向基类的类型转换
一个派生类对象包含多个组成部分：一个含有派生类自己定义的（非静态）成员的子对象，以及一个与基类对应的子对象，如果有多个类，那么这样的子对象也有多个。因此，一个 Bulk_quote 对象将包含四个数据元素：它从 Quote 继承而来的 bookNo 和 price 数据成员，以及 Bulk_quote 自己定义的 min_qty 和 discount 成员。

C++ 标准并没有明确规定派生类的对象在内存中如何分布，但是可以认为 Bulk_quote 的对象包含如下的两部分：

                                    Bulk_quote对象
                                    --------------   从Quote 继承而来的成员 
                                    |   bookNO    |    
                                    |   price     |
                                    ---------------
                                    |   min_qty   |   从Bulk_quote 继承而来的成员
                                    |   discount  |
                                    ---------------
                                Bulk_quote 对象的概念结构

因为派生类对象中含有与其基类对应的组成部分，所以我们能把派生类的对象当成基类对象来使用，而且我们也能将基类的指针或引用绑定到派生类对象中的基类部分上。

```c++
Quote item;         // 基类对象
Bulk_quote bulk;    // 派生类对象
Quote *p = &item;   // p 指向 Quote 对象
p = &bulk;          // p 指向 bulk 的 Quote 部分
Quote &r = bulk;    // r 绑定到 bulk 的 Quote 部分
```

这种转换通常称为 **派生类到基类的（derived-to-base）类型转换**。和其他类型转换一样，编译器会隐式地执行派生类到基类的转换。

这种隐式特性意味着我们可以把派生类对象或者派生类对象的引用用在需要基类引用的地方；同样的，我们也可以把派生类对象的指针用在需要基类指针的地方。

### 派生类构造函数
派生类中的数据成员包括两部分：基类数据成员和派生类数据成员，每个类控制它自己的成员初始过程。派生类以通过构造函数初始化列表来指定基类构造函数，否则派生类对象的基类部分会像数据成员一样执行默认初始化。

```c++
Bulk_quote(const std::string& book, double p,
            std::size_t qty, double disc) : 
            Quote(book, p), min_qty(qty), discount(disc) {}
// ...
```

可以看到，在构造函数初始化列表来中可以明确指定基类构造函数，并向其传递相关参数。

### 派生类使用基类的成员

派生类中可以访问基类的公有成员和受保护成员：

```c++
// 如果达到了购买书籍的某个最低限量值，就可以享受折扣价格了
double Bulk_quote::net_price(size_t cnt) const 
{
    if (cnt >= min_qty) 
        return cnt * (1 - discount) * price;
    else 
        return cnt * price;
}
```
price 成员属于基类 Quote, 在派生类中可以正常使用。

### 继承与静态成员

如果基类定义了一个静态成员，则在整个继承体系中只存在该成员的唯一定义。不论从基类中派生出来多少个派生类，对于每个静态成员来说都只存在唯一的实例。
```c++
class Base {
public:
    static void statmem();
};

class Derived : public Base {
    void f(const Derived&);
};
```

静态成员遵循通用的访问控制规则，如果基类中的成员是 private 的，则派生类无权访问它。假设某静态成员是可访问的，则我们既能通过基类使用也能通过派生类使用它：

```c++
void Derived::f(const Derived &derived_obj) 
{
    Base::statmem();            // 正确：Base 定义了 statmem
    Derived::statmem();         // 正确：Derived 继承了 statmem
    // 正确：派生类的对象能访问基类的静态成员
    derived_obj.statmem();      // 通过 Derived 对象访问
    statmem();                  // 通过 thtis 对象访问
}
```

### 派生类的声明
派生类的声明与其他类差别不大，声明中包含类名但是不包含它的派生列表：
```c++
class Bulk_quote : public Quote;        // 错误：派生列表不能出现在声明里
class Bulk_quote;                       // 正确
```

#### 被用作基类的类
如果我们想将某个类用作基类，则该类必须已经定义而非仅仅声明：
```c++
class Quote;            // 声明但未定义
// 错误：Quote 必须定义
class Bulk_quote : public Quote { ... };
```
这一规定的原因显而易见：派生类中包含并且可以使用它从基类继承而来的成员，为了使用这些成员，派生类当然要知道它们是什么。

一个类是基类，同时它也可以是一个派生类：
```c++
class Base { /* ... */ };
class D1: public Base { /* ... */ };
class D2: public D1 { /* ... */ };
```

在这个继承关系中， Base 是 D1 的**直接基类（direct base）**，同时是 D2 的**间接基类（indirect base）**。直接基类出现在派生列表中，而间接基类由派生类通过其直接基类继承而来。

每个类都会继承直接基类的所有成员。对于一个最终的派生类来说，它会继承其直接基类的成员；该直接基类的成员又含有其基类的成员；依此类推直至继承链的顶端。因此，最终的派生类将包含它的直接基类的子对象及每个间接基类的子对象。

### 防止继承的发生
有时我们会定义这样一种类，我们不希望其他类继承它，或者不想考虑它是否适合作为一个基类。为了实现这一目的，C++11 新标准提供了一种防止继承发生的方法，即在类名后跟一个关键字 final:
```c++
class NoDerived final { /* ... */ };        // NoDerived 不能作为基类
class Base { /* ... */ };
// Last 是 final 的；我们不能继承 Last
class Last final : Base { /* ... */ };      // Last 不能作为基类
class Bad : NoDerived { /* ... */ };        // 错误：NoDerived 是 final 的
class Bad2 : Last { /* ... */ };            // 错误：Last 是 final 的
```

## 类型转换与继承
引入继承关系之后，可以将基类的指针或引用绑定到派生类对象上。另外，和内置指针一样，智能指针类也支持派生类向基类的类型转换，这意味着我们可以将一个派生类对象的指针存储到一个基类的智能指针内。

### 静态类型与动态类型

当使用存在继承关系的类型时，必须将一个变量或其他表达式的**静态类型（static type）**与该表达式对象的**动态类型（dynamic type）**区分开来。表达式的静态类型在编译时总是已知的，它是变量声明时的类型或表达式生成的类型；动态类型则是变量或表达式内存中对象的类型，动态类型直到运行时才可知。

基类的指针或引用的静态类型可能与其动态类型不一致，非引用或指针的变量或表达式，它的动态类型永远与静态类型一致。

### 不存在从基类向派生类的隐式类转换

因为一个基类的对象可能是派生类对象的一部分，也可能不是，所以不存在从基类向派生类的自动类型转换：

```c++
Quote base;
Bulk_quote* bulkP = &base;      // 错误：不能将基类转换成派生类
Bulk_quote& bulkRef = base;     // 错误：不能将基类转换成派生类
```

如果上述赋值是合法的，则我们有可能会使用 bulkP 或 bulkRef 访问 base 中本不存在的成员。

除此之后还有一种情况，即使一个基类指针或引用绑定在一个派生类对象上，我们也不能执行从基类向派生类的转换：

```c++
Bulk_quote bulk;
Quote* itemP = &bulk;           // 正确：动态类型是 Bulk_quote
Bulk_quote* bulkP = itemp;      // 错误：不能将基类转换成派生类
```

编译器在编译时无法确定某个特定的转换在运行时是否安全，这是因为编译器只能通过检查指针或引用的静态编译类型来推断该转换是否合法。如果在基类中含有一个或多个虚函数，我们可以使用 dynamic_cast 请求一个类型转换，该转换安全检查将在运行时执行。同样，如果我们已知某个基类向派生类的转换是安全的，则可以使用 static_cast 来强制覆盖编译器的检查工作。

### 在对象之间不存在类型转换
派生类向基类的自动类型转换只对指针或引用类型有效，在派生类类型和基类类型之间不存在这样的转换。

# 虚函数
在 C++ 语言中，当我们使用基类的引用或指针调用一个虚成员函数时会执行动态绑定。因为我们直到运行时才能知道到底调用了哪个版本的虚函数，所以所有虚函数都必须有定义。通常情况下，如果我们不使用某个函数，则无须为该函数提供定义。但是我们必须为每一个虚函数都提供定义，而不管它是否被用到了，这是因为连编译器也无法确定到底会使用哪个虚函数。

## 关键概念：C++的多态性
OOP 的核心思想是多态性（polymorphism）。多态性这个词源自希腊语，其含义是“多种形式”。我们把具有继承关系的多个类型称为多态类型，因为我们能使用这些类型的“多种形式”而无须在意它们的差异。引用或指针的静态类型与动态类型不同这一事实是 C++ 语言支持多态性的根本所在。

当我们使用基类的引用或指针调用基类中定义的一个函数时，我们并不知道该函数真正作用的对象是什么类型，因为它可能是一个基类对象也可能是一个派生类的对象。如果该函数是虚函数，则直到运行时才会决定到底执行哪个版本，判断的依据是引用或指针所绑定的对象的真实类型。

另一方面，对非虚函数的调用在编译时进行绑定。类似的，通过对象进行的函数（虚函数或非虚函数）调用也在编译时绑定。对象的类型是确定不变的，我们无论如何都不可能令对象的动态类型也静态类型不一致。因此，通过对象进行的函数调用将在编译时绑定到该对象所属类中的函数版本上。

当且仅当对通过指针或引用调用虚函数时，才会在运行时解析该调用，也只有在这种情况下对象的动态类型才有可能与静态类型不同。

## 派生类中的虚函数
当我们在派生类中覆盖了某个虚函数时，可以再一次使用 virtual 关键字指出该函数的性质。然而这么做并非必须，因为一旦某个函数被声明成虚函数，则在所有派生类中它都是虚函数。

一个派生类的函数如果覆盖了某个继承而来的虚函数，则它的形参类型必须与被它覆盖的基类函数安全一致。

同样，派生类中虚函数的返回类型也必须与基类函数匹配。该规则存在一个例外，当类的虚函数返回类型是类本身的指针或引用时，上述规则无效。也就是说，如果 D 由 B 派生得到，则基类的虚函数可以返回 B* 而派生类的对应函数可以返回 D*，只不过这样的返回类型要求从 D 到 B 的类型转换是可访问的。

> 基类中的虚函数在派生类中隐含地也是一个虚函数。当派生类覆盖了某个虚函数时，该函数在基类中形参必须与派生类中的形参严格匹配。

### final 和 override 说明符
派生类如果定义了一个函数与基类中虚函数的名字相同但是形参列表不同，这仍然是合法的行为。编译器将认为新定义的这个函数与基类中原有的函数是相互独立的。这时，派生类的函数并没有覆盖掉基类中的版本。为了避免这种错误，在C++11 新标准中我们可以使用 override 关键字来说明派生类中的虚函数。这么做的好处是使得程序员的意图更加清晰的同时让编译器可以为我们发现一些错误。如果我们使用 override 标记了某个函数，但该函数并没有覆盖已存在的虚函数，此时编译器将报错：
```c++
struct B {
    virtual void f1(int) const;
    virtual void f2();
    void f3();
};

struct D1 : B {
    void f1(int) const override;    // 正确：f1 与基类中的 f1 匹配
    void f2(int) override;           // 错误： B 没有形如 f2(int) 的函数
    void f3() override;             // 错误： f3 不是虚函数
    void f4() override;             // 错误： B 没有名为 f4的函数
};
```

另外，我们还能把某个函数指定为 final, 如果我们已经函数定义为 final 了，则之后的任何尝试覆盖该函数的操作都将引发错误：
```c++
struct D2 : B {
    // 从 B 继承 f2() 和 f3(), 覆盖 f1(int)
    void f1(int) const final;   // 不允许后续的其他类覆盖 f1(int)
};

struct D3 : D2 {
    void f2();                // 正确：覆盖从间接基类 B 继承而来的 f2
    void f1(int) const;     // 错误： D2 已经将 f1 声明成 final
};
```

final 和 override 说明符出现在形参列表（包括任何 const 或引用修饰符）以及尾置返回类型之后。

### 虚函数与默认实参
和其他函数一样，虚函数也可以拥有默认实参。如果某次函数调用使用默认实参，则该实参值由本次调用的静态类型决定。

换句话说，如果我们通过基类的引用或指针调用函数，则使用基类中定义的默认实参，即使实际运行的是派生类中的函数版本也是如此。此时，传入派生类函数的将是基类函数定义的默认实参。如果派来类函数依赖不同的实参，则程序结果将与我们的预期不符。

### 回避虚函数的机制
在某些情况下，我们希望对虚函数的调用不要进行动态绑定，而是强迫其执行虚函数的某个特定版本。使用作用域运算符可以实现这一目的，例如下面的代码：
```c++
// 强行调用基类中定义的函数版本而不管 baseP 的动态类型到底是什么
double undiscounted = baseP->Quote::net_price(42);
```

# 抽象基类
假设我们希望扩展程序并令其支持不同的折扣策略，此时可以添加一个 Disc_quote 类来支持不同的扣策略，它包含两个数据成员：一个购买量的值和和一个折扣的值。Disc_quote 负责保存购买量的值和折扣的值。其他的表示某种特定策略的类（如 Bulk_quote）将分别继承自 Disc_quote，每个派生类通过定义自己的 net_price 函数来实现各自的折扣策略。

由于各自的折扣策略由 Disc_quote 的派生类来实现，net_price 函数在 Disc_quote 中没有实际的意义，仅仅是表示一种约定或契约，真正的功能由派生类实现。

## 纯虚函数
针对上面的场景，我们可以将 net_price 定义成**纯虚（pure virtual）函数**从而令程序实现我们的设计意图，这样做可以清晰明了地告诉用户当前这个 net_price 函数是没有实际意义的。和普通的虚函数不一样，一个纯虚函数无须定义。我们通过在函数体的位置（即在声明语句的分号之前）书写 =0 就可以将一个虚函数说明为纯虚函数。其中 =0 只能出现在类内部的虚函数声明语句处：
```c++
// 用于保存折扣值和购买量的类，派生类使用这些可以实现不同的体格策略
class Disc_quote : public Quote {   
public:
    Disc_quote() = default;
    Disc_quote(const std::string& book, double price,
                std::size_t qty, double disc) :
                    Quote(book, price),
                    quantity(qty), discount(disc) {}
    double net_price(std::size_t) const =0;
protected:
    std::size_t quantity = 0;   // 折扣适用的购买量
    double discount = 0.0;      // 表示折扣的小数值
};
```

值得注意的是，我们也可以为纯虚函数提供定义，不过函数体必须定义在类的外部。也就是说，我们不能在类的内部为一个 =0 的函数提供函数体。

## 含有纯虚函数的类是抽象基类
含有（或者未经覆盖直接继承）纯虚函数的类是**抽象基类（abstract base class）**。抽象基类负责定义接口，而后续的其它类可以覆盖该接口。我们不能（直接）创建一个抽象基类的对象。因为 Disc_quote 将 net_price 定义为纯虚函数，所以我们不能定义 Disc_quote 的对象。我们可以定义 Disc_quote 的派生类的对象，前提是这些类覆盖了 net_price 函数：
```c++
// Disc_quote 声明了纯虚函数，而 Bulk_quote 将覆盖该函数
Disc_quote discounted;          // 错误：不能定义 Disc_quote 的对象
Bulk_quote  bulk;               // 正确：Bulk_quote 中没有纯虚函数
```

Disc_quote 的派生类必须给出自己的 net_price 定义，否则它们仍将是抽象基类。

> 不能创建抽象基类的对象。

## 派生类构造函数只能初始化它的直接基类
接下来可以重新实现 Bulk_quote 了，这一次我们让它继承 Disc_quote 而非直接继承 Quote:
```c++
// 当同一书籍的销售量超过某个值是启用折扣
// 折扣的值是一个小于 1 的正在小数值，以此来降低正常销售价格
class Bulk_quote : public Disc_quote {   
public:
    Bulk_quote() = default;
    Bulk_quote(const std::string& book, double price,
                std::size_t qty, double disc) :
                    Disc_quote(book, price, qty, disc) {}
    // 覆盖其中的函数版本以实现一种新折扣策略
    double net_price(std::size_t) const override;
};
```
这个版本的 Bulk_quote 的直接基类是 Disc_quote，间接基类是 Quote。每个 Bulk_quote 对象包含三个子对象：一个（空的）Bulk_quote 部分、一个 Disc_quote 子对象和一个 Quote 对象。

如前所述，每个类各自控制其对象的初始化过程。因此，即使 Bulk_quote 没有的数据成员，它也仍然需要像原来一样提供一个接受四个参数的构造函数。该构造函数将它的实参传递给 Disc_quote 的构造函数，随后 Disc_quote 的构造函数继续调用 Quote 的构造函数。Quote 的构造函数首先初始化 bookNo 和 price 成员，当 Quote 的构造函数结束后，开始运行 Disc_quote 的构造函数并初始化 quantity 和 discount 成员，最后 运行 Bulk_quote 的构造函数，该函数无须执行实际的初始化或其他工作。

# 访问控制与继承
每个类分别控制自己的成员初始化过程，与之类似，每个类还分别控制着其成员对于派生类来说是否可访问（accessible）。

## 受保护的成员
如前所述，一个类使用 protected 关键字来声明那些它希望与派生类分享但是不想被其他公共访问使用的成员。protected 说明符可以看作是 public 和 private 中和后的产物。
- 和私有成员类似，受保护的成员对于类的用户来说是不可访问的；
- 和公有成员类似，受保护的成员对于派生类的成员和友元来说是可访问的；

此外，protected 还有另外一条重要的性质：
- 派生类的成员物友元只能通过派生类对象来访问基类的受保护成员。派生类对于一个基类对象的受保护成员没有任何访问特权。

为了理解最后一条规则，请参考下面的例子：
```c++
class Base {
protected:
    int prot_mem;       // protected 成员
};

class Sneaky : public Base {
    friend void clobber(Sneaky&);       // 能访问 Sneaky::prot_mem
    friend void clobber(Base&);         // 不能访问 Base::prot_mem
    int j;                              // j 默认是 private
};

// 正确：clobber 能访问 Sneaky 对象的 private 和 protected 成员
void clobber(Sneaky &s) { s.j = s.prot_mem = 0; }
// 错误：clobber 不能访问 Base 的 protected 成员
void clobber(Base &b) { b.prot_mem = 0; }
```

如果派生类（及其友元）能访问基类对象的受保护成员，则上面的第二个 clobber（接受一个 Base&）将是合法的。该函数不是 Base 的友元，但是它仍然能够改变一个 Base 对象的内容。如果按照这样的思路，则我们只要定义一个形如 Sneakey 的新类就能非常简单地规避掉 prtoected 提供的访问保护了。

要想阻止以上的用法，我们就要做出如下规定，即派生类的成员和友元只能访问派生类对象中的基类部分的受保护成员；对于普通的基类对象中的成员不具有特殊的访问权限。

## 公有、私有和受保护继承
某个类对其继承而来的成员的访问受到两个因素影响：一是在基类中该成员的访问说明符，二是在派生类的派生列表中的访问说明符。举个例子，考虑如下的继承关系：
```c++
class Base {
public:
    void pub_mem();             // public 成员
protected:
    int prot_mem();             // protected 成员
private:
    char priv_mem;              // private 成员
};

struct Pub_Derv : public Base {
    // 正确：派生类能访问 protectd 成员
    int f() { return prot_mem; }
    // 错误：private 成员对于派生类来说不可访问的
    char g() { return priv_mem; }
};

struct Priv_Derv : private Base {
    // private 不影响派生类的访问权限
    int f1() const { return prot_mem; }
};
```

派生访问说明符对于派生类的成员（及友元）能否访问其直接基类的成员没什么影响。对基类成员的访问权限只与基类中的访问说明符有关。Pub_Derv 和 Priv_Derv 都能访问受保护的成员 prot_mem，同时它们都不能访问私有成员 priv_mem。

派生访问说明符的目的是控制派生类用户（包括派生类的派生类在内）对于基类成员的访问权限：
```c++
Pub_Derv d1;        // 继承自 Base 的成员是 public 的
Priv_Derv d2;       // 继承自 Base 的成员是 private
d1.pub_mem();       // 正确：pub_mem 在派生类是 public 的
d2.pub_mem();       // 错误：pub_mem 在派生类中是 private 的
```
Pub_Derv 和 Priv_Derv 都继承了 pub_mem 函数。如果继承是公有的，则成员将遵循其原有的访问说明符，此时 d1 可以调用 pub_mem。在 Priv_Derv 中，Base 的成员是私有的，因此类的用户不能调用 pub_mem。

派生访问说明符还可以控制继承自派生类的新类的访问权限：
```c++
struct Derived_from_Public : public Pub_Derv {
    // 正确：Base::prot_mem 在 Pub_Derv 中仍然是 protected
    int use_base() { return prot_mem; }
};

struct Derived_from_Private : public Priv_Derv {
    // 正确：Base::prot_mem 在 Priv_Derv 中是 private 的
    int use_base() { return prot_mem; }
};
```

Pub_Derv 的派生类之所以能访问 Base 的 prot_mem 成员是因为该成员在 Pub_Derv 中仍然是受保护的。相反，Priv_Derv 的派生类无法执行类的访问，对于它们来说，Priv_Derv 继承自 Base 的所有成员都是私有的。

假设我们之前还定义了一个名为 Prot_Derv 的类，它采用受保护继承，则 Base 的所有公有成员在新定义的类都是受保护的。Prot_Derv 的用户不能访问 pub_mem，但是 Prot_Derv 的成员和友元可以访问那些继承而来的成员。

## 派生类向基类转换的可访问性
派生类向基类的转换是否可访问由该转换的代码决定，同时派生类的派生访问符也会有影响。假定 D 继承自 B:
- 只有当 D 公有地继承 B 时，用户代码才能使用派生类向基类的转换；如果 D 继承 B 的方式是受保护或者私有的，则用户代码不能使用该转换；
- 不论 D 以什么方式继承 B, D 的成员函数和友元都能使用派生类向基类的置换；派生类向其直接基类的类型转换对于派生类的成员和友元来说永远是可访问的；
- 如果 D 继承 B 的方式是公有的或者受保护的，则 D 的派生类和成员或友元可以使用 D 向 B 的类型转换；反之，如果 D 继承 B 的方式是私有的，则不能使用。

## 友元与继承
就像友元关系不能传递一样，友元关系同样也不能继承。基类的友元在访问派生类成员时不具有特殊性，类似地，派生类的友元不不能随意访问基类的成员：
```c++
class Base {
    // 添加 friend 声明，其他成员与之前的版本一致
    friend class Pal;       // Pal 在访问 Base 的派生类时不具有特殊性
};

class Pal {
public:
    int f(Base b) { return b.prot_mem; }        // 正确：Pal 是 Base 的友元
    int f2(Sneaky s) { return s.j }             // 错误：Pal 不是 Sneakey 的友元
    // 对基类的访问权限由基类本身控制，即使对于派生类的基类部分也是如此
    int f3(Sneaky s) { return s.prot_mem; }     // 正确：Pal 是 Base 的友元
};

```
如前所述，每个类负责控制自己的成员的访问权限，因此尽管看起来有点儿奇怪，但 f3 确实是正确的。Pal 是 Base 的友元，所以 Pal 能够访问 Base 对象的成员，这种可访问性包括了 Base 对象内嵌在其派生类对象中的情况。

当一个类将另一个声明成友元时，这种关系只对做出声明的类有效。对于原来那个类来说，其友元的基类或者派生类不具有特殊的访问能力：
```c++
// D2 对 Base 的 protected 和 private 成员不具有特殊的访问能力
class D2 : public Pal {
public:
    int mem(Base b) 
        { return b.prot_mem; }          // 错误：友元关系不能继承
};
```

## 改变个别成员的可访问性
有时我们需要改变派生类继承的某个名字的访问级别，通过使用 using 声明可以达到这一目的：
```c++
class Base {
public:
    std::size_t size() const { return n; }
protected:
    std::size_t n;
};

class Derived : private Base {
public:
    // 公开 size 方法
    using Base::size;
protected:
    using Base::n;
};

```
因为 Derived 使用了私有继承，所以继承而来的成员 size 和 n (在默认情况下)是 Derived 的私有成员。然而，我们使用 using 声明语句改变了这些成员的可访问性。改为之后，Derived 的用户将可以使用 size 成员，而 Derived 的派生类将能使用 n。

通过在类内部使用 using 声明语句，我们可以将该类的直接或间接基类中的任何可访问成员（例如，非私有成员）标记出来。using 声明语句中名字的访问权限由该 using 声明语句之前的访问说明符来决定。也就是说，如果一条 using 声明语句出现在类的 private 部分，则该名字只能被类的成员和友元访问；如果 using 声明语句位于 protected 部分，则该名字对于成员、友元和派生类是可访问的。

> 派生类只能为那些它可以访问的名字提供 using 声明。

## 默认的继承保护级别
struct 和 class 关键字定义的类具有不同的默认访问说明符。类似的，默认派生运算符也由定义派生类所用的关键字来决定。默认情况下，使用 class 关键字定义的派生类是私有继承的；而使用 struct 关键字定义的派生类是公有继承的：
```c++
class Base { /* ... */ };
struct D1 : Base { /* ... */ };         // 默认 public 继承
class D2 : Base { /* ... */ };          // 默认 private 继承
```
