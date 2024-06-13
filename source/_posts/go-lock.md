---
title: Go系列：Go 锁
date: 2024-06-13 17:11:07
updated: 2024-06-13 17:11:07
tags:
- go 锁
categories: 
- 笔记
---

在 Go 语言中，共享变量的并发问题主要是通过锁机制来解决的。

<!-- more -->

## 竞态
竞态是指在多个 goroutine 按某些交错顺序执行执行时程序无法给出正确的结果。而数据竞态是其中的一个场景，数据竞态发生于两个或多个 goroutine 并发读写同一个变量并且至少其中一个是写入时。一般有三种办法避免数据竞态：
1. 不修改变量，把数据提前加载，如启动时；
2. 避免从多个 goroutine 访问同一个变量，Go 箴言：不要通过共享内存来通信，而应该通信来共享内存。
3. 引入互斥机制，多个 goroutine 对同一个变量进行互斥访问，如通过加锁实现互斥访问。

## 互斥锁：sync.Mutex
互斥锁模式应用非常广泛，所以 sync 包有一个单独的 Mutex 类型来支持这种模式。它的 Lock 方法用于获取令牌（token,此过程也称为上锁），Unlock 方法用于释放令牌，Lock及Unlock方法必须成对出现，如下所示：
```go
import "sync"

var (
	mu      sync.Mutex // guards balance
	balance int
)

func Deposit(amount int) {
	mu.Lock()
	balance = balance + amount
	mu.Unlock()
}

func Balance() int {
	mu.Lock()
	b := balance
	mu.Unlock()
	return b
}
```

在 Lock 和 Unlock 之间的代码，可以自由地读取和修改共享变量，这部分称为临界区域。在锁的持有人调用 Unlock 之前，其它 goroutine 不能获取锁。所以很重要的一点是，goroutine 在使用完成后就应当释放锁。

Go 语言的互斥量是不可再入的，已经一个 goroutine 已经获取了一个互斥锁 mu, 不能再获取互斥锁 mu, 这会导致死锁。这种情况一般发生在未释放锁的情况下，再次调用了需要申请同一个锁的函数或方法。这跟 Java 语言不一样。

## 读写互斥锁：sync.RWMutex
加了互斥锁之后，所有读写操作都会互斥访问，这样解决了数据准确性的问题。不过这样会带来访问效率低下的问题，正常情况下，一般是读多写少，大量的并发读也需要互斥访问，显然为带来不必要的开销。为了解决这个问题，引入了读写互斥锁。在 Go 语言中的 sync.RWMutex 提供了这种功能，它允许只读操作可以并发执行，但写操作需要获取完全独享的访问权限。
```go
var mu sync.RWMutex
var balance int

func Balance() int {
	mu.RLock()  // 读锁
	defer mu.RUnlock()
	return balance
}

func Deposit(amount int) {
	mu.Lock()  // 写锁
	balance = balance + amount
	mu.Unlock()
}
```

Balance 函数可以调用 RLock 和 RUnlock 方法来分别获取和释放一个读锁（也称为共享锁）。Deposit 函数无须更改，它通过 mu.Lock 和 mu.Unlock 来分别获取和释放一个写锁（也称为互斥锁）。

