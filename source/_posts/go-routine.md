---
title: Go系列：Goroutine
date: 2024-06-13 17:11:48
updated: 2024-06-13 17:11:48
tags:
- goroutine
categories: 
- 笔记
---

这篇文章主要讲述 Goroutine。

<!-- more -->

Go 有两种并发编程的风格，一种是通信顺序进程 `CSP(Communication Sequential Process)` 模式，它在不同的执行体(goroutine) 之间传递值，主要通过通道来实现；另外一种是共享内存多线程的模式，主要是通过锁来实现。

## goroutine
在 Go 里，每一个并发执行的实体称为 goroutine. 它等同于轻量级的线程。当一个程序启动时，只有一个 goroutine 来调用 main 函数，称它为主 goroutine. 新的 goroutine 通过 go 语句进行创建。语法上，一个 go 语句是在普通函数或者方法前加上 go 关键字前缀。go 语句使函数在一个新创建的 goroutine 中调用。go 语句会立即执行：
```go
f()    // 调用 f(); 等待它返回
go f() // 新建一个调用 f() 的 goroutine, 不用等待
```

## 通道
如果说 goroutine 是 Go 程序并发的执行体，那么通道便是它们之间的连接。通道是可以让一个 goroutine 发送特定值到另一个 goroutine 的通信机制。每一个通道是一个具体类型的导管，叫做通道的元素类型。一个有 int 类型元素的通道写为 chan int.

使用内置的 make 函数来创建一个通道：
```go
ch := make(chan int)  // ch 的类型是 'chan int'
```
像 map 一样，通道是一个使用 make 创建的数据结构的引用。当复制或者作为参数传递到一个函数时，复制的是引用，这样调用者和被调用者都引用同一份数据结构。和其它引用类型一样，通道的零值是 nil.
同种类型的通道可以使用 == 符号进行比较，当二者都是同一通道数据的引用时，比较值为true. 通道也可以和 nil 进行比较。

通道有两个主要操作：发送(send) 和接收 (receive). send 语句从一个 goroutine 传输一个值到另一个在执行接收表达式的 goroutine. 两个操作都使用 <- 操作符书写。发送语句中，通道和值分别在 <- 的左右两边。在接收表达式中，<- 放在通道操作数前面。在接收表达式中，其结果未被使用也是合法的。
```go
ch <- x // 发送语句，将x值发送给通道ch
x = <-ch  // 接收通道ch 的值并赋值给 x
<-ch  // 接收语句，不需要结果
```

在接收操作中有一个变种，它返回两个结果：接收到的通道元素，以及一个布尔值（通常称为ok），它为 true 的时候代表接收成功，false 表示当前的接收操作在一个关闭的并且读完的通道上。
```go
x, ok := <- ch
if !ok {
	return // 通道关闭并且读完
}
```
另外，Go 语言也提供了 range 循环语法在通道上进行迭代，这个语法更方便接收在通道上所有发送的值，接收完最后一个值后关闭循环，如下所示：
```go
for x := range ch {
	//...
}
```

通道支持第三个操作：关闭(close), 它设置一个标志位来指示值已经发送完毕，这个通道后面没有值了。对关闭的通道执行关闭操作将导致宕机。在一个已经关闭的通道上进行接收操作，将获取所有已经发送的值，直到通道为空；这时任何接收操作会立即完成，同时获取到一个通道元素类型对应的零值。利用该特性，可以利用它创建一个广播机制，通知相关所有 goroutine，执行退出（或取消）操作。 
调用内置的 close 函数来关闭通道：
```go
close(ch)
```

程序结束时，关闭每一个通道不是必需的，只有在通知接收方 goroutine 所有的数据都发送完毕的时候才需要关闭通道。通道也是可以通过垃圾回收器根据它是否可以访问来决定是否回收它，而不是根据它是否关闭。
试图关闭一个已经关闭的通道会导致宕机，就像关闭一个空通道一样，关闭通道还可以作为一个广播机制，通知其它 goroutine 通道已经关闭，并以此来触发对应的程序逻辑，如退出，如下代码所示：
```go
// goroutine 1
var done = make(chan struct{})

func cancelled() bool {
	select {
	case <-done:
		return true
	default:
		return false
	}
}

// goroutine 2
// Cancel traversal when input is detected.
go func() {
	os.Stdin.Read(make([]byte, 1)) // read a single byte
	close(done)
}()
```

使用make函数创建通道时，可以指定第二个参数，一个表示通道容量的整数。如果容量是 0, make 创建一个无缓冲通道：
```go
ch = make(chan int)     // 无缓冲通道
ch = make(chan int, 0)  // 无缓冲通道
ch = make(chan int, 3)  // 容量为 3 的缓冲通道
```

### 无缓冲通道
无缓冲通道上执行发送/接收操作都将被阻塞，直到另一个 goroutine 在对应的通道上执行相反的操作（发送，接收互为相反操作），这时值传送完成，两个 goroutine 都可以继续执行。
使用无缓冲通道进行的通信导致发送和接收 goroutine 同步化。因此，无缓冲通道也称为同步通道。当一个值在无缓冲通道上传递时，接收值后发送方 goroutine 才被再次唤醒。

有时候，我们不在意通道的值，只在意接收/发送操作本身。这时，可以使用空结构体 struct{} 作为传值对象，不过使用 bool 或 int 类型来做会更简洁，因为 `ch <- -1` 比 `ch <- struct {}{}` 要短。

### 单向通道
Go 的类型系统提供了单向通道类型，仅仅导出发送或接收操作：
1. `chan<- int`: 只能发送的通道，允许发送但不允许接收。
2. `<-chan int`: 只能接收的通道，允许接收但不允许发送。

因为 close 操作说明了通道上没有数据再发送，仅仅在发送方 goroutine 上才能调用它，所以试图关闭一个仅能接收的通道在编译时会报错。
在任何赋值操作中将双向通道转换为单向通道都是允许的，但是反过来是不行的，一旦有一个像 chan<- int 这样的单向通道，是没有办法通过它获取到引用同一个数据结构的 chan int 数据类型的。

### 缓冲通道
缓冲通道有一个元素队列，队列的最大长度在创建的时候通过 make 的容量参数来设置。下面的语句创建一个容纳三个字符串的缓冲通道，如下所示：
```go
ch = make(chan string, 3)
```

缓冲通道上的发送操作在队列的尾部插入一个元素，接收操作从队列的头部移除一个元素。如果通道满了，发送操作会阻塞所在 goroutine 直到另一个 goroutine 对它进行接收操作来留出可用的空间。反过来，如果通道是空的，执行接收操作的 goroutine 阻塞，直到另一个 goroutine 在通道上发送数据。

使用内置的 cap 函数可以获取通道的容量，内置的 len 函数获取当前通道的元素个数。

## select 多路复用
如果程序中需要在多个通道中发送/接收数据，可以使用 select 语句，其语法如下：
```go
select {
case <- ch1:
	// ...
case x := <-ch2:
	// ... user x ...
case ch3 <- y:
	// ...
default:
	// ...
}
```
上面展示的是 select 语句的通用形式。像 switch 语句一样，它有一系列的情况和一个可行的默认分支。每一个情况指定一次通信（在一些通道上进行发送或接收操作）和关联的一段代码码。接收表达式操作可能出现在它本身上，像第一个情况，或者在一个短变量声明中，像第二个情况；第二种形式可以让你引用接收的值。
select 一直等待，直到一次通信来告知有一些情况可以执行。然后，它进行这次通信，执行此情况所对应的语句；其它的通信将不会发生。对于没有case语句的 select, select{}将永远等待。
如果多个情况同时满足，select随机选择一个，这样保证每一个通道有相同的机会被选中。

