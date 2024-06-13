---
title: Go系列：Go Test
date: 2024-06-13 17:12:08
updated: 2024-06-13 17:12:08
tags:
- go test
categories: 
- 笔记
---

这篇文章主要讲述 Go Test.

<!-- more -->

## go test 工具
`go test` 子命令是GO语言包的测试驱动程序，这些包根据某些约定组织在一起。在一个包目录中，以 `_test.go` 结尾的文件不是 `go build` 命令编译的目标，而是 `go test` 编译的目标。

在 `*_test.go` 文件中，三种函数需要特殊对待，即功能测试函数、基准测试函数和示例运行测试函数。功能测试函数是以Test前缀命名的函数，用来检测一些程序逻辑的正确性，`go test` 运行测试函数，并且报告结果是 PAAS 还是 FAIL. 基准测试函数的名称以 `Benchmark` 开头，用来测试某些操作的性能， `go test` 汇报操作的平均执行时间。示例函数的名称，以 Example 开头，用来提供机器检查过的文档。

`go test` 工具扫描 `*_test.go` 文件来寻找特殊函数，并生成一个临时的main包来调用它们，然后编译和运行，并汇报结果，最后清空临时文件。

## Test 函数
每一个测试文件必须导入 testing 包。这些函数的函数签名如下：
```go
func TestName(t *testing.T) {
	// ...
}
```

功能测试函数必须以 Test 开头，可选的后缀名称必须以大写字母开头：
```go
func TestSin(t *testing.T) { /* ... */}
```

参数 t 提供了汇报测试失败和日志记录的功能，以下面例子为例：
```go
package word

// IsPalindrome reports whether s reads the same forward and backward.
// (Our first attempt.)
func IsPalindrome(s string) bool {
	for i := range s {
		if s[i] != s[len(s)-1-i] {
			return false
		}
	}
	return true
}
```
上面定义了一个判断字符串是否为回文的函数，回文是指前后对称的字符串，下面定义其测试用例：
```go
package word

import "testing"

func TestPalindrome(t *testing.T) {
	if !IsPalindrome("detartrated") {
		t.Error(`IsPalindrome("detartrated") = false`)
	}
	if !IsPalindrome("kayak") {
		t.Error(`IsPalindrome("kayak") = false`)
	}
}

func TestNonPalindrome(t *testing.T) {
	if IsPalindrome("palindrome") {
		t.Error(`IsPalindrome("palindrome") = true`)
	}
}
```
定义了两个函数来判断是否为回文，并且用 t.Error 来报错。

使用如下命令执行测试函数：
```bash
go test 
go test -v  // -v 可以输出包中每一个测试用例的名称和执行的时间；
go test -v -run="Freanch|Canal"   // -run 设置一个正则表达式，匹配的函数将会被执行；
```

## Benchmark 函数
基准测试就是在一定的工作负载之下检测程序性能的一种方法。在 Go 里面，基准测试函数看上去像一个测试函数，但是前缀是 Benchmark，并且有一个 *testing.B 参数，这个参数的大多数方法与 *testing.T 相同，不过额外增加了一些与性能检测相关的方法。它还提供了一个整型成员 N, 用来指定被测试函数的执行次数。
下面是 IsPalindrome 函数的基准测试，它在一个循环中调用了 IsPalindrome 共 N 次。
```go
import "testing"
func BenchmarkIsPalindrome(b *testing.B) {
	for i := 0; i < b.N; i++ {
		IsPalindrome("A man, a plan, a canal: Panama")
	}
}
```

执行 Benchmark 函数，需要在 go test 命令加上 -bench 参数，该参数指定了要运行的基准测试。它是一个匹配 Benchmark 函数名称的正则表达式，它的默认值不匹配任何函数。模式 "." 使它匹配当前包中所有的基准测试函数。因为这里只有一个基准测试函数，所以和指定 -bench=IsPalindrome 效果一样。

执行的测试命令如下：
```bash
go test -bench=.
```

## Example 函数
Example 函数既没有参数也没有结果，下面是 IsPalindrome 的一个示例函数：
```go
func ExampleIsPalindrome() {
	fmt.Println(IsPalindrome("A man, a plan, a canal: Panama"))
	fmt.Println(IsPalindrome("palindrome"))
	
	// 输出：
	// true
	// false
}
```

Example 函数有三个作用：
1. 作为文档中 Example 代码，与关联的被测试代码关联在一起，显示在 Doc 文档中；
2. 可以通过 go test 执行测试代码；
3. 在文档中提供手动实验代码。

