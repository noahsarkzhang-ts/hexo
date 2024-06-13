---
title: Go系列：Go 接口
date: 2024-06-13 17:10:19
updated: 2024-06-13 17:10:19
tags:
- go 接口
categories: 
- 笔记
---

这篇文章主要讲述 Go 接口。

<!-- more -->

接口类型是对行为的概括与抽象。通过使用接口，我们可以写出更新灵活和通用的函数，这些函数不用绑定在一个特定的类型实现上。
不像其它编程语言，Go 语言的接口实现方式是隐式实现，换句话说，对于一个具体的类型，无须声明它实现了哪些接口，只要提供接口所必需的方法即可。这种设计让你无须改变已有类型的实现，就可以为这些类型接口创建新的接口，对于那些不能修改包的类型，这一点特别有用。

## 接口即约定
接口是一种抽象类型，它没有暴露所含数据的布局或者内部结构，当然也没有这些数据的基本操作，它所提供的仅仅是一些方法而已，其形式如下所示：
```go
type Writer interface {
	Write(p []byte) (n int, err error)
}
```
可以说，接口应该是一类相关方法的集合。

## 接口类型
一个接口类型定义一套方法，如果一个具体类型要实现该接口，那么必须实现接口类型定义中的所有方法。以io包中的接口类型为例。
```go
package io

type Reader interface {
	Read(p []byte) (n int, err error)
}

type Closer interface {
	Close() error
}
```

另外，还可以通过组合已有接口得到新的接口，如：
```go
type ReadWriter interface {
	Reader
	Write
}
```
如上的语法称为嵌入式接口，与嵌入式结构类似。也可以结合两种语法混合定义。
```go
type ReadWriter interface {
	Read(p []byte) (n int, err error)
	Writer
}
```
这两种声明的效果是一致的，方法的先后顺序也不影响接口的定义。

## 接口的实现
如果一个类型实现了一个接口要求的所有方法，那么这个类型实现了这个接口。
```go
type ByteCounter int

func (c *ByteCounter) Write(p []byte) (int,error) {
	*c += ByteCounter(len(p)) // 转换int 为 ByteCounter 类型
	return len(p), nil
}
```
`*ByteCounter` 实现了 `Writer` 接口中的 write 方法，可以说 `*ByteCounter` 实现了 `Writer` 接口。

## 空接口类型
接口类型 `interface{}`,表示空接口类型，它完全不包含任何方法。在程序中，空接口类型是不可缺少的，它可以用来表示任何类型。
```go
var any interface{}
any = true
any = 12.34
any = "hello"
any = map[string]int{"one",1}
any = new(bytes.Buffer)
```

## 接口值
从概念上来讲，一个接口类型的值（简称接口值）其实有两个部分：一个具体类型和该类型的一个值。二者称为接口的动态类型和动态值。
如下四个语句中，变量 w 有三个不同值：
```go
var w io.Writer
w = os.Stdout
w = new(bytes.Buffer)
w = nil
```

假定接口类型为 type，值为 value,则有:
`var w io.Writer`:
等同于：
```go
w.type = nil
w.value = nil
```

`w = os.Stdout`:
等同于：
```go
w.type = *os.File
w.value = fd int=1(stdout) // 指向一个os.File对象
```

`w = new(bytes.Buffer)`:
等同于：
```go
w.type = *byte.Buffer
w.value = &(bytes.Buffer)  // 指向一个bytes.Buffer 对象
```

`w = nil`:
等同于：
```go
w.type = nil
w.value = nil
```

接口值可以用 == 和 != 操作符来比较。如果两个接口值都是nil或者二者的动态类型安全一致且动态值相等（使用动态类型的 == 操作符来比较），那么两个接口值相等。因为接口值是可以比较的，所以它们可以作为 map 的键，也可以作为 switch 语句的操作数。
需要注意的是，在比较两个接口值时，如果两个接口值的动态类型一致，但对应的动态值是不可比较的（比如slice）,那么这个比较会以崩溃的方式失败：
```go
var x interface{} = []int{1,2,3}
fmt.Println(x == x) // 宕机：试图比较不可比较的类型 []int
```

当处理错误或者调试时，能拿到接口值的动态类型是很有帮助的。可以使用 fmt 包的 %T 来实现这个需求：
```go
var w io.Writer
fmt.Printf("%T\n",w) // "<nil>"

w = os.Stdout
fmt.Printf("%T\n",w) // "*os.File"

w = new(bytes.Buffer)
fmt.Printf("%T\n",w) // "*byte.Buffer"
```

注意：含有空指针的非空接口
nil 的接口值（类型和值都为nil）与仅仅动态值为 nil 的接口值是不一样的，它们二者不是相等关系。

## 方法转接口
在 net/http 包中实现了 Web客户端和服务器代码，其中 http.Handler 接口定义了服务端处理函数，它传入两个对象，一个是请求对象指针，用于传入请求的数据，另外一个对象是响应输出对象ResponseWriter，用于返回输出结果，如下所示：
```go
package http

type Handler interface {
	ServerHttp(w ResponseWriter, r *Request)
}

func ListenAndServer(address string, h Handler) error
```

ListenAndServer 函数需要一个服务器地址，比如"localhost:8080"，以及一个 Handler 接口的实例（用来接受所有的请求）。这个函数会一直运行，直到服务出错（或者启动时就失败了）时返回一个非空的错误。

假定一个电子商务网站，使用一个数据库来存储商品和价格，如下程序展示，它用一个 map类型（命名为database）来代表仓库，再加一个 ServerHTTP 方法来满足 http.Handler 接口，这个函数遍历整个 map 并且输出其中的元素：
```go
func main(){
	db := database{"shoes": 50,"socks":5}
	log.Fatal(http.ListenAndServe("localhost:8000", db))
}

type dollars float32

func (d dollars) String() string { return fmt.Sprintf("$%.2f",d) }

type database map[string]dollars

func (db database) ServeHTTP(w http.Responsewriter,reg *http.Request) {
	for item,price := range db {
		fmt.Fprintf(w,"%s:%s n",item, price)
	}
}
```

ServeHTTP 函数只有一个功能，输出所有产品的价格，如果要增加其它的endpoint,如/price, 用来显示单个商品的价格，商品可以在请求参数中指定，比如：/price?item=socks, 需要修改代码：
```go
func (db database) ServeHTTP(w http.Responsewriter,reg *http.Request) {
	switch req.URL.Path {
	case "/list":
		//...
	case "/price":
		//...
	default:
		w.WriteHeader(http.StatusNotFound) // 404
		fmt.Fprintf(w, "no such page: %s\n",reg.URL)
	}
}
```
现在，处理函数基于 URL 的路径部分(req.URL.Path)来决定执行哪部分逻辑。增加一个Path,增加一段处理逻辑即可。
但在真实场景中，更好的方法是将每一部分逻辑分到独立的函数和方法中。因为这些原因，net/http包提供了一个请求多工转发器ServerMux，用来简化URL与处理程序之间的关联，一个 ServeMux 把多个 http.Handler 组合到单个 http.Handler.

在下面的代码中，创建了一个 ServeMux,用于将 /list,/price 这样的 URL 和对应的处理程序关联起来，这些处理程序已经拆分到不同的方法中。最后作为主处理程序在 ListenAndServe 调用中使用这个 ServeMux:
```go
func main() {
	db := database{"shoes": 50, "socks": 5}
	mux := http.NewServeMux()
	mux.Handle("/list", http.HandlerFunc(db.list))
	mux.Handle("/price", http.HandlerFunc(db.price))
	log.Fatal(http.ListenAndServe("localhost:8000", mux))
}

type database map[string]dollars

func (db database) list(w http.ResponseWriter, req *http.Request) {
	for item, price := range db {
		fmt.Fprintf(w, "%s: %s\n", item, price)
	}
}

func (db database) price(w http.ResponseWriter, req *http.Request) {
	item := req.URL.Query().Get("item")
	price, ok := db[item]
	if !ok {
		w.WriteHeader(http.StatusNotFound) // 404
		fmt.Fprintf(w, "no such item: %q\n", item)
		return
	}
	fmt.Fprintf(w, "%s\n", price)
}
```

`mux.Handle` 是 `*ServeMux` 中的方法，定义如下：
`func (mux *ServeMux) Handle(pattern string, handler Handler)`
参数中 hanler 是 Handler 类型的接口，而 db.list 和 db.price 是如下类型的函数：
`func(w http.Responsewriter,reg *http.Request)`
db.list 和 db.price 是一个函数，它没有对 Handle 所需的方法，所以不能直接传递给 handler 参数。

在这里使用了一个类型转换，将函数转换为一个Handle接口类型，如下所示：
```go
http.HandlerFunc(db.list)
```

HandlerFunc 是一个类型，不是一个函数调用，其定义如下：
```go
package http

type HandlerFunc func(w ResponseWriter, r *Request)

func (f HandlerFunc) ServeHTTP(w ResponseWriter, r *Request) {
	f(w, r)
}
```
HandlerFunc 不仅是一个函数类型，还拥有自己的方法，也满足接口 http.Handle. 它的 ServeHTTP 方法就调用函数本身，所以 HandlerFunc 就是一个让函数值满足接口的一个适配器。在这个例子中，函数和接口的唯一方法拥有同样的签名。这个小技巧让 database 类型可以用不同的方法来满足 http.Handler 接口：一次通过 list 方法，一次通过 price 方法，依次类推。

 ## error 接口
在程序中，经常使用到 error 类型，它实际上一个接口，其定义如下：
```go
type error interface {
	Error() string
}
```

构造 error 最简单的方法是调用 error.New, 它返回一个包含指定错误信息的新 error 实例，完整的 error 包只有如下4行代码：
```go
package errors

func New(text string) error { return &errorString{text}}

type errorString struct {text string}

func (e *errorString) Error() string { return e.text }
```

底层的 errorString 类型是一个结构，而没有直接用字符串，主要是为了避免将来增加内容。满足 error 接口的是 *errorString 指针，而不是原始的 errorString, 主要是为了让每次 New 分配的 error 实例都互不相等。

除了调用 errors.New函数生成 error 实例，也可以使用 fmt.Errorf, 它额外提供了字符串格式化功能，如下所示：
```go
package fmt

import "errors"

func Errorf(format string, args ...interface{}) error {
	return errors.New(Sprintf(format, args...))
} 
```

## 类型断言
类型断言是一个作用在接口值上的操作，写出来类似于 x.(T), 其中 x 是一个接口类型的表达式，而 T 是一个类型（称为断言类型）。类型断言会检查作为操作数的动态类型是否满足指定的断言类型。在这里，T 有两种场景，它可以是具体类型，也可以是接口类型。

如果断言类型 T 是一个具体类型，那么类型断言会检查 x 的动态类型是否就是 T. 如果检查成功，类型断言的结果就是 x 的动态值，类型当前就是 T. 换句话说，类型断言就是用来从它的操作数中把具体类型取出来的操作。如果检查失败，那么操作崩溃。比如：
```go
var w io.Writer
w = os.Stdout
f := w.(*os.File) // 成功：f == os.Stdout
c := w.(*bytes.Buffer) // 崩溃：接口持有的是 *os.File,不是 *bytes.Buffer.
```

如果断言类型 T 是一个接口类型，那么类型断言检查 x 的动态类型是否满足 T. 如果检查成功，动态值并没有提取出来，结果仍然是一个接口值，接口值的类型和值部分也没有变更，只是结果的类型为接口类型T. 换句话说，类型断言是一个接口值表达式，从一个接口类型变为另外一套方法的接口类型（通常方法数量是增多），但保留了接口值中的动态类型和动态值部分。

如下类型断言代码中， w 和 rw 都持有 os.Stdout, 于是所有对应的动态类型都是 *os.File,但 w 作为 io.Writer 仅暴露了文件的 Write 方法，而 rw 还暴露了它的 Read 方法。
```go
var w io.Writer
w = os.Stdout
rw := w.(io.ReadWriter) // 成功： *os.File 有 Read 和 Write 方法。

w = new(ByteCounter)
rw = w.(io.ReadWriter) // 崩溃：*ByteCounter 没有 Read 方法。
```

无论哪种类型作为断言类型，如果操作数是一个空接口值，类型断言都会失败。很少需要从一个接口类型向一个要求更宽松的类型做类型断言，该宽松类型的接口方法比原类型的少，而且是子集。除了在操作数为 nil 的情况，在其它情况下这种操作与赋值一致，如下所示：
```go
w = rw.(io.Writer)  // 仅当 rw == nil 时失败
```
等同于：
```go
r = rw    // io.ReadWriter 可以赋给 io.Writer
```

另外，为了避免断言失败时崩溃，可以使用有两个返回值的断言类型，多出一个布尔类型的返回值表示断言是否成功，如下所示：
```go
var w io.Writer = os.Stdout

f, ok := w.(*os.File)  // 成功：ok, f == os.Stdout
b, ok := w.(*bytes.Buffer)  // 失败，!ok, b == nil
```

这种形式可以结合 if 表达式，写出比较紧凑的代码：
```go
if f, ok := w.(*os.File); ok {
	// ... 使用 f...
}
```

## 使用类型断言识别错误或查询接口特性
在程序中，可以使用类型断言来识别错误，或检查类型是否满足某一接口，如下所示：
```go
package fmt

func formatOneValue(x interface{}) string {
	if err, ok := x.(error); ok {    // 识别错误
		return err.Error()
	}
	
	if str, ok := x.(Stringer); ok {  // 判断是否满足某一接口
		return str.String()
	}
	
	// ... 所有其它类型
}
```

## 类型分支
类型断言与switch语句结合，可以进行不同类型分支的判断，如下所示：
```go

switch x.(type) {
case nil:          // ...
case int, uint:    // ...
case bool:         // ...
case string:       // ...
default:           // ...
}
```

或将类型断言的结果赋值给新的变量：
```go
switch x := x.(type) { /* ... */}
```

把新的变量也命名为 x, 也可以命名为其它名字。




