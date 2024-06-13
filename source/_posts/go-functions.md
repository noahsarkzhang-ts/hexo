---
title: Go系列：Go 函数
date: 2024-06-10 20:00:02
updated: 2024-06-10 20:00:02
tags:
- go 函数
categories: 
- 笔记
---

这篇文章主要讲述 Go 函数。

<!-- more -->

## 函数申明
```go
func name(parameter-list)(result-list) {
	body
}
```

说明：
1. 返回值可以有多个，这是区别于其它编程语言的地方。
实例：
`func findLinks(url string) ([]string,error) {}`
其中，该函数有一个形参，两个返回值。
返回值也可以包含名称，如下所示：
`func Size(rect image.Rectangle) (width,height int)`
返回值有名称，在函数中，可以省略 return 语句的操作数。

## 错误
在 GO 语言中，没有使用异常机制来报告错误，而是通过使用普通的错误返回值来告诉调用方有错误发生。GO语言中的异常只是针对程序bug导致的预料外的错误，而不能作为常规的错误处理方法出现在程序中。
函数一般是通过最后一个参数来反馈错误，如下：
```go
func process(params map[string]string) (map[string]int, bool)
```
或
```go
func process(params map[string]string) (map[string]int, error)
```

如果只关心函数处理成功与否，可返回 bool 类型，如果关注错误的内容，则需要返回 error 类型.

error 是内置的接口类型，它主要返回一个意义的字符串，便于问题定位.可使用error.New快速生成一个error对象。
```go
errors.New("Client is not available!")
```

可以通过发下方法输出error的内容：
```go
fmt.Println(err)
```
或
```go
fmt.Printf("%v",err)
```

在程序中，收到一个程序返回的 error 之后，如果需要将 error上报给业务上层以便进行定位处理，可以使用 fmt.Errorf 方法，在原有错误信息的基础上，拼接上本次调用的上下文信息，形成一个清晰的调用链条，最后上报给业务最上层。
```go
fmt.Errorf("parsing %s as HTML:%v",url,err)
```
fmt.Errorf使用fmt.Sprintf函数格式化一条错误信息并且返回一个新的错误值，使用该方法，可以将错误消息串联起来，方便定位。

说明：
1. `log.Fatalf("Site is down: %v\n",err)`, 如果产生的错误，不能恢复，可以打印日志退出程序。

## 函数变量
函数在 Go 语言中是头等重要的值：就像其它值，函数变量也有类型，而且它们可以赋给变量或者传递或者从其它函数中返回，另外，函数变量也可以像其它函数一样调用，比如：
```go
func square(n int) int { returun n*n }
func negative(n int) int { return -n }

var f func(int) int // 定义函数变量
f = square
f(3)

f = negative
f(3)
```

函数变量可以当作参数进行传递，以标准库中 strings.Map为例，它对字符串的每一个字符调用一个函数，将结果连接起来变成另一个字符串。
```go
func add1(r rune) rune { return r+1}

// 调用
fmt.Println(strings.Map(add1,"HAL-9000")) // 输出：IBM.:111
```

另外，函数也是一种类型，可以接合 type 进行定义，如：
```go
type RpcProcessor func(ctx context.Context, rpcContext *Context, message *msg.RpcMsg)
type RpcCallback func(message *msg.RpcMsg)
```

## 匿名函数
在这个实例中，也可以使用匿名函数，如下所示：
```go
fmt.Println(strings.Map(func(r rune) rune { return r+1},"HAL-9000))
```

匿名函数是一个表达式，它就像函数声明，但在func关键字后面没有函数的名称。

使用匿名函数有一个优势，它能够获取到整个词法环境，里层的函数可以使用外层函数中的变量，如下所示：
```go
func squares() func() int {
	var x int
	return func() int {
		x++
		return x*x
	}
}

func main() {
	f := squares()
	fmt.Println(f()) // 1
	fmt.Println(f()) // 4
	fmt.Println(f()) // 9
	fmt.Println(f()) // 16
}
```

函数 squares 返回了另一个函数，类型是 `func() int`. 调用 square 创建了一个局部变量 x 而且返回了一个匿名函数，每次调用 squares 都会递增 x 的值然后返回 x 的平方。第二次调用 squares 函数将创建第二个变量 x, 然后返回一个递增 x 值的新匿名函数。
f 函数变量不仅是一段代码还还可以拥有状态。里层的匿名函数能够获取和更新外层 squares 函数的局部变量。Go程序员通常把函数变量称为闭包。

**循环变量陷阱**
在循环体内中，如果函数变量引用循环变量，程序会存在陷阱。函数变量本意是引用循环变量在某个循环中的临时值，但由于循环变量在迭代中一直在变化。迭代对事之后，函数变量在执行时，引用的循环变量最终的值，而不是某个循环中的临时值，造成程序错误。如下所示：
假设一个程序创建一系列的目录之后又会删除它们，可以使用一个包含函数变量 slice 进行清理操作。
```go
var rmdirs []func()

for _,dir := range tempDirs() {
	os.MkdirAll(dir,0755)
	rmdirs = append(rmdirs, func() {
		os.RemoveAll(dir) // 不正确
	})
}

for _,rmFunc := range rmdirs {
	rmFunc()
}
```

在上面的程序中，dir 变量的值在不断地迭代中更新，因此当调用清理函数时，dir变量已经被 for 循环更新多次。因此，dir 变量的实际取值是最后一次迭代时的值并且所有的 os.RemoveAll 调用最终都试图删除同一个目录。
可以通过引入一个内部变量来解决这个问题，这个内部变量拷贝循环变量的值，如下所示：
```go
for _, dir := range tempDirs() {
	dir := dir // 声明内部dir,并以外部dir初始化
	// ...
}
```

这种隐患，同样存在于 go 语句和 defer 语句中，这是因为这两个逻辑都会推迟函数的执行时机。

## 变长函数
变长函数可传递多个可变的参数，形式如下：
```go
fun sum(vals ...int) int 
```
在参数列表的类型名称之前使用省略号"..."表示声明一个变长函数，调用这个函数的时候可以传递该类型任意数目的参数。

```go
sum()
sum(1,2)
sum(1,2,3)
```

或者传递一个slice,如下所示：
```go
values := []int{1,2,3}
sum(values...)
```

说明：在最后一个参数后面放一个省略号。

## 延迟函数调用
在语法上，延迟函数就是在普通函数之前加一个 defer 关键字。函数和参数表达式会在语句执行时求值，并保证在函数退出前执行。在正常情况下，执行return语句或函数执行完毕之后，延迟函数会被执行。在异常情况下，如宕机之后，延迟函数也会继续执行。defer 语句没有限制使用次数，在一个函数中可以包含多个defer 语句；执行的时候以调用fefer语句顺序的倒序执行。

defer 语句经常使用资源的回收和释放，一般是成对的操作，如打开和关闭，连接和断开，加锁和解锁。正确使用defer语句的方式是在成功获取资源之后，否则引用一个资源，会产生宕机。

如果对返回结果进行命名，那么 defer 语句可以引用或修改返回结果，如下所示：
```go
func double(x int) (result int) {
	defer func() { fmt.Printf("double(%d) = %d\n",x, result)}
	// defer func() { result += x}
	return x + x
}
```

## 宕机
GO 语言运行时检测到一些错误，如数组越界访问或引用空指针等，它就会发生宕机。发生宕机之后，正常的程序执行会终止，gorouting 中所有的延迟函数会执行，然后程序会异常退出并留下一条日志消息。日志消息包括宕机的值，它代表某种错误消息，另外每一个 goroutine 都会在宕机的时候显示一个函数的栈跟踪消息。
GO语言提供了内置的宕机函数 panic,它可以接受任何值作为参数。如果碰到“不可能发生”的状况，宕机是最好的处理方式，比如语句执行到逻辑上不可能到达的地方时。
宕机会引起程序异常退出，只有在发生严重的错误时候才会使用宕机。

## 恢复
退出程序通常是正确处理宕机的方式，如果不想程序退出，也可以使用内置的 recover函数，使得函数可以从宕机中恢复，继续执行。
recover 函数包含在延迟函数的内部，如果包含延迟函数的函数发生宕机，recover会终止当前的宕机状态并且返回宕机的值。函数会结束宕机流程而是正常返回。如果recover在没有宕机的情况下运行则它没有任何效果且返回nil。其形式如下：
```go
func Parse(input string) (s *Syntax,err error) {
	defer func() {
		if p := recover(); p != nil {
			err = fmt.Errorf("internal err:%v",p)
		}
	}()
	
}
```

recover函数返回是宕机panic的值，可以根据宕机的值进行判断是否进行恢复。
```go
func soleTitle(doc *html.Node) (title string, err error) {
	type bailout struct{} // 定义宕机的值
	
	defer func() {
		switch p := recover(); p {
		case nil:
			// 没有宕机
		case bailout{}:
			// “预期的”宕机
			err = fmt.Errorf("multiple title elements")
		default:
			panic(p) // 未预期的宕机；继续宕机过程
		}
	}()
	
    // 如发生预期的错误，则宕机
	if title != "" {
		panic(bailout{})
	}
	
	return title,nil
	
}
```

延迟的处理函数调用 recover,检查宕机值，如果该值是 `bailout{}` 则返回一个普通的错误，所有其它非空的值则说明是预料外的宕机，这时处理函数使用宕机值作为参数调用 panic, 忽略 recover 的作用并且继续之前的宕机状态。
