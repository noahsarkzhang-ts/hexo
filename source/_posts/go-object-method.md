---
title: Go系列：Go 对象方法
date: 2024-06-13 17:10:48
updated: 2024-06-13 17:10:48
tags:
- go 对象方法
categories: 
- 笔记
---

在面向对象编程（OOP）思想中，一个对象包含属性及方法，其中方法是某种特定类型的函数。

<!-- more -->

## 方法声明
方法的声明和普通函数的声明类似，只是是在函数名称前面加了一个参数。这个参数把这个方法绑定到这个参数对应的类型上。
```go
type Point struct{X, Y float64}

// 普通的函数
func Distance(p, q Point) float64 {
	return math.Hypot(q.X-q.X, q.Y-p.Y)
}

// Point类型的方法
func (p Point) Distance(q Point) float64 {
	return math.Hypot(q.X-q.X, q.Y-p.Y)
}
```

附加的参数 p 称为方法的接收者，Go 语言中，接收者不使用特殊名（比如 this 或者 self）; 而是我们自己选择接收者的名字，就像其它的参数变量一样。这个名字最好选择简短且在整个方法中始终保持一致的名字。最常用的方法就是取类型名称的首字母，就像 Point 中的 p。

上面两个 Distance 函数声明没有冲突。第一个声明是包级别的函数，第二个声明是类型 Point 的方法。 

调用方法的时候，接收者在方法名的前面。如下所示：
```go
p := Point{1,2}
q := Point{4,6}
fmt.Println(Distance(p, q)) // 函数调用
fmt.Println(p.Distance(q))  // 方法调用
```

Go语言和许多其它面向对象的语言不同，它可以将方法绑定到任何类型上，可以很方便地为简单的类型（如数字、字符串、slice、map，甚至函数等）定义附加的行为。同一个包下的任何类型都可以声明方法，只要它的类型不是指针和接口类型。如下所示，可为slice附加一个Distance方法。
```go
type Path []Point

func (path Path) Distance() float64 {
	sum := 0.0
	for i := range path {
		if i>0 {
			sum += path[i-1].Distance(path[i])
		}
	}
	
	return sum
}
```

## 指针接收者的方法
同实参传值会复制一个副本一样，为了避免大对象复制，可以使用指针来传递变量的地址。方法的接收者也可以是指针类型，如下所示：
```go
func (p *Point) ScaleBy(factor float64) {
	p.X *= factor
	p.Y *= factor
}
```
这方法的名字是 `(*Point).ScaleBy`。圆括号是必需的，没有圆括号，表达式会被解析为`*(Point.ScaleBy)`。

正常情况下，一个类型上所有的方法接收者是统一的，要么是指针接收者，要么就是类型本身。命名类型(Point)与指向它们的指针(*Point)是唯一合法的接收者类型。而且，为防止混淆，不允许本身是指针的类型进行方法声明：
```go
type P *int
func (P) f() { /* ... */ }  // 编译错误：非法的接收者类型
```

接收者使用指针之后，有显示和隐式两种调用方式，如下所示：
```go
p := Point{1,2}
r := &p

// 使用指针方式调用
r.ScaleBy(2)

// 隐式调用，会将p 转换为指向p 的地址
p.ScaleBy(2)
```

在上例中，p是 Point类型的变量，编译器会对变量进行 &p 的隐式转换。只有变量才允许这么做，包括结构体字段。不能够对一个不能取地址的 Point 接收者参数调用 *Point 方法，因为无法获取临时变量的地址，如下所示：
```go
Point{1,2}.ScaleBy(2)  // 编译错误：不能获得 Point 类型字面量的地址。
```

总结：
下面三种调用方式是合法的：
1. 实参接收者和形参接收者是同一个类型，比如都是T类型或者都是*T类型；
```go
p := Point{1,2}
q := Point{3,4}
pptr := &p

p.Distance(q)  // Point类型
pptr.ScaleBy(2) // *Point
```

2. 实参接收者是T类型的变量而形参接收者是*T类型，编译器会隐式地获取变量的地址；
```go
p.ScaleBy(2) // 隐式转换为(&p)
```

3. 实参接收者是*T类型的变量而形参接收者是T类型，编译器会隐式地解引用接收者，获得实际的取值；
```go
pptr.Distance(q) // 隐式转换为(*pptr)
```

如果类型的所有方法接收者是 T本身（而非*T），那么复制它的实例是安全的，调用方法的时候都必须进行一次复制。但是任何方法的接收者是指针的情况下，应该避免复制T的实例，因为这么做可能会破坏内部原本的数据。

nil 是一个合法的接收者
就像一些函数允许nil指针作为实参，方法的接收者也一样。

## 通过结构体内嵌组成类型
有内嵌类型的结构体中，结构体可以直接使用内嵌类型的字段及方法，假设有结构体定义如下：
```go
type Point struct{X, Y float64}

func (p Point) Distance(q Point) float64 {
	return math.Hypot(q.X-q.X, q.Y-p.Y)
}

func (p *Point) ScaleBy(factor float64) {
	p.X *= factor
	p.Y *= factor
}

type ColoredPoint struct {
	Point
	Color color.RGBA
}
```

ColoredPoint类型的变量可以直接使用Point类型的字段和方法。
```go
var cp ColoredPoint
cp.X = 1 // 等同于 cp.Point.X = 1

p.ScaleBy(2) // 等同于 cp.Point.ScaleBy(2)
```

在上面的例子中，p.ScaleBy方法调用中，p是ColoredPoint类型，类似于ColoredPoint类型继承了Point中的方法，但不等同于ColoredPoint是Point的子类。实际上，内嵌的字段会告诉编译器生成额外的包装方法来调用 Point 声明的方法，这相当于以下代码：
```go
func (p ColoredPoint) Distance(q Point) float64 {
	return p.Point.Distance(q)
}

func (p *ColoredPoint) ScaleBy(factor float64) {
	p.Point.ScaleBy(factor)
}
```

## 方法变量与表达式
方法可以被赋值给变量，这个变量称作方法变量，如下所示：
```go
p := Point{1,2}
q := Point{4,6}

distanceFromP := p.Distance  // 方法变量
scaleP := p.ScaleBy // 方法变量

distanceFromP(q) // 方法调用
scaleP(2)

fmt.Printf("%T\n",distance) // func(Point) float64
fmt.Printf("%T\n",scaleP) // func(float64)
```

选择子 `p.Distance` 可以赋予一个方法变量，它是一个函数，把方法 `（Point.Distance）` 绑定到一个接收者 p 上，函数只需要提供实参而不需要提供接收者就能够调用。

与方法变量相关的是方法表达式。和调用一个普通的函数不同，在调用方法的时候必须提供接收者，并且按照选择子的语法进行调用。而方法表达式写成 T.f 或者(*T).f，这是一种函数变量（其中 T 是类型），把原来方法的接收者替换成函数的第一个形参，因此它可以像平常的函数一样调用。
```go
p := Point{1,2}
q := Point{4,6}

distance := Point.Distance  // 方法表达式
scaleBy := (*Point).ScaleBy   // 方法表达式

distance(p,q) // 方法调用，第一个参数是接收者
scaleBy(&p,2)  // 方法调用

fmt.Printf("%T\n",distance) // func(Point,Point) float64
fmt.Printf("%T\n",scaleP) // func(*Point,float64)
```

## 封装
如果变量或者方法是不能通过对象访问到的，这称作封装的变量或者方法。Go语言只有一种方式控制命名的可见性：定义的时候，首字母大写的标识符是可以从包中导出的，而首字母没有大写的则不导出。同样的机制也同样用于结构体的字段和类型中的方法。结论就是，要封装一个对象，必须使用结构体。
在Go语言中封装的单元是包而不是类型，无论是在函数内的代码还是方法内的代码，结构体类型内的字段对于同一个包中的所有代码都是可见的。



