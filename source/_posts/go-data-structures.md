---
title: Go系列：Go 数据结构
date: 2024-06-10 19:48:12
updated: 2024-06-10 19:48:12
tags:
- go 数据结构
categories: 
- 笔记
---

这篇文章主要讲述 Go 语言用到的数据结构。

<!-- more -->

## string 字符串
string 是不可变的字节序列，它可以包含任意数据，主要是人类可读的文本。

内置的len函数返回字符串的字节数，下标访问操作 `s[i]` 则读取第i个字符。
不能用下标操作进行赋值操作，`s[i]='L'`,是不合法的。

子串生成操作 `s[i:j]` 产生一个新的字符串，内容取自原字符串的字节，下标从i（含边界值）开始，直到j（不含边界值）。结果的大小是 j-i 个字节。
string 的子串操作是非常高效的，因为字串与原字符串共用一段底层内存，字串本质上就是一个包含指针和长度的数据结构，指针指向原字符串特定的位置。

原生字符串字面量,用反引号` `表示。原生的字符串字面量内，转义序列不起作用；实质内容也字面写法严格一致。原生的字面量适用于HTML模板、JSON字面量、命令行提示信息，以及需要多行文本的场景。

4 个关于字符串操作的函数包：
1. strings: 用于搜索、替换、比较、修整、切分与连接字符串；
2. bytes：用于操作字节 slice; 
3. strconv：用于数值与字符串之间的转换；
4. unicode：包括文字符号类型的函数，如IsDigit, IsLetter, IsUpper和IsLower。

字符串与字节slice相互转换：
```go
s := "abc"
b := []byte(s)
s2 := string(b)
```

字符串和数字的相互转换
1. fmt.Springf()
2. strconv.Itoa()

```go
// int -> string
x := 123
y := fmt.Springf("%d",x)
z := strconv.Itoa(x)

// string -> int
x,err := strconv.Atoi("123")
y,err := strconv.ParseInt("123",10,64) // 十进制，最长为64位
```

## 数组
数组是具有固定长度且拥有零个或者多个想再数据类型元素的序列。由于数组的长度固定，所以在Go里面很少直接使用。slice的长度可以增长和缩短，在很多场合下使用得更多。

数组定义: 
```go
var a [3]int  // 3个整数的数组，每一个值初始为0;
```

数组中的每个元素是通过索引来访问的，索引从0到数组长度减1。内置的函数len可以返回数组中元素个数。
```go
fmt.Println(a[0])
fmt.Println(a[len(a)-1])
```

数组遍历:
```go
for i,v := range a {
	fmt.Printf("%d %d\n",i,v)
}
```
range 输出两个元素：索引和元素。

数组的一些定义：
```go
var q [3]int = [3]int{1,2,3}
var r [3]int = [3]int{1,3}

s := [...]int{1,2,3} // 数组长度由元素个数自动确认，s类型为[3]int

t := [...]int{99:-1} // 也可以指定下标，定义了一个拥有100个元素的数组t,除了最后一个元素值是 -1 外，该数组中的其它元素值都是 0.
```

数组的长度是数组类型的一部分，所以 [3]int 和 [4]int 是两种不同的数组类型

如果一人数组的元素类型是可比较的，那么这个数组也是可比较的，这样就可以直接使用 == 操作符来比较两个数组，比较的结果是两边元素的值是否完全相同。使用 != 来比较两个数组是否不同。
```go
a := [2]int{1,2}
b := [...]int{1,2}
c := [2]int{1,3}

a == b // true
a == c // false
b == c // false

d := [3]int{1,2}
a == d // 编辑错误：无法比较 [2]int == [3]int
```

## slice
slice 表示一个拥有相同类型元素的可变长度的序列。slice 通常写成 []T, 其中元素的类型都是T; 

slice 是一种轻量级的数据结构，可以用来访问数组的部分或全部的元素，而这个数组称为slice的底层数组。slice有三个属性：指针、长度和容量。指针指向数组的可以从slice中访问的第一个元素，这个元素并不一定是数组的第一个元素。长度是指slice中元素的个数，它不能超过slice的容量。容量的大小通常是从slice的起始位置到底层数组的最后一个元素间元素的个数。内置函数len和cap返回slice的长度和容量。
```go
months := [...]string{1: "January", /* .. */, 12: "Deceber"}
```

建立一个13个元素的数组，其中months[0]为空字符串。
```go
Q2 := months[4:7]  // len(Q2) = 7-4 = 3, cap(Q2) = len(months)-4=13-4=9
summer := months[6:9] // len(summer) = 9-6 = 3, cap(summer) = len(months)-6=13-6=7
```

slice操作符 s[i:j]（其中 0<= i <= j <= cap(s)）创建了一个新的slice，这个新的slice引用了序列 s 中从i 到 j-1 索引位置的所有元素，这里的 s 既可以是数组或者指向数组的指针，也可以是slice. 新slice的元素个数是 j-i 个。常见引用：
```go
r := months[:6] // i=0,取0~6之间的元素，不包含6。
s := months[1:] // j= len(s) = 13，取1~13之间的元素，不包含13。
t := months[:]  // i=0,j=len(s)=13,取所有元素。 
```

因为slice包含了指向数组元素的指针，所以将一个slice传递给函数的时候，可以函数内部修改底层数组的元素。

slice的定义与数组类型，区别在于不用指定元素的个数。
```go
var summer [3]string = [3]string{"June","July","August"}
var summer []string = months[6:9]
```

和数组不同，slice 无法做比较，因此不能用 == 来测试两个slice是否拥有相同的元素。标准库里面提供了高度优化的函数bytes.Equal来比较两个字节slice([]byte)。但是对其它类型的slice,程序必须自己写函数来比较。

slice类型的零值是 nil。值为nil的slice没有对应的底层数组。值为nil的slice长度和容量都是零，但是也有非nil的slice长度和容量是零，例如 `[]int{}或make([]int,3)[3:]`.

对于任何类型，如果它们的值可以是 nil,那么它们就可以转换为nil,如[]int(nil)

使用make函数创建slice:
```go
make([]T,len)
make([]T,len,cap)
```

append函数：调用append函数，会向slice中加入一个或多个元素，并返回包含新元素的slice。appen函数会根据容量不足时，会自动扩充底层数组，将返回一个新的slice,所以要求用新的slice更新旧的slice，如下所示：
```go
var runes []runes
runes = append(runes,'H')
```

可以使用slice来实现栈。给定一个空的slice元素stack, 可以使用append向slice尾部追加值：
```go
stack = append(stack,v)
```
获取栈顶元素：
```go
top := statck[len(statck)-1]
```
元素出栈：
```go
stack = stack[:len(stack)-1]
```

## map
在Go语言中，map是散列表的引用，map的类型是map[K]V，其中 K 和 V 是字典的键和值对应的数据类型。键的类型K,必须是可以通过操作符 == 来进行比较的数据类型，通过 map 可以检测某一个键是否已经存在。

创建 map:
```go
ages := make(map[string]int)
```
或
```go
ages := map[string]int {
	"alice": 31,
	"charlie": 34,
}
```

赋值:
```go
ages["alice"] = 32
```

删除元素，使用内置函数:
```go
delete(ages,"alice")
```

map使用给定的键来查找元素，如果对应的元素不存在，就返回值类型的零值。

遍历元素，使用for循环，如下所如示：
```go
for name,age := range ages {
	// ...
}
```

range 返回 K，V.

获取长度：`len(ages)`

获取元素是否存在:
```go
age, ok :=ages["bob"]
if !ok {
	// ..
}
```

或者
```go
if age,ok := ages["bob"]; !ok {
	// ...
}
```

可以使用map[T]bool来实现集合类。

## 结构体struct
结构体是将零个或者多个任意类型的命名变量组合在一起的聚合数据类型，每一个变量都叫做结构体的成员。结构体定义如下：
```go
type Employee struct {
	ID	int
	Name string
	Address string
	...
}

var dilbert Employee
```

结构体的成员通过点号来进行访问，如 dilbert.Name.
结构体的成员及结构体本身都可以通过指针访问
```go
address := &dilbert.Address

var ep *Employee = &dilbert
ep.Address += " street."
```
或
```go
(*ep).Address += " street."
```

结构体成员变量名称首字母是大写的，表示这个变量是可导出（在其它包可以访问）的，一个结构体可同时包含可导出和不可导出的成员变量。

结构体命名类型S 不可以包含结构体本身类型的变量，不过可以定义一个 S 指针类型的变量。

结构体的零值由结构体成员的零值组成。没有任何成员变量的结构体称为空结构体，写作 struct{},它没有长度，也不携带任何信息。在程序中，用它来替代被当作集合中的布尔值，通过它来强调只有键是有用的，但由于这种方式节约的内存很少并且语法复杂，所以一般尽量避免这样用。
```go
seen := make(map[string]struct{}) // 字符串集合
// ...
if _,ok := seen[s]; !ok {
	seen[s] = struct{}{} 
	// ... 首次出现 s
}
```

结构体字面量:
```go
type Point strcut {X,Y int}

第一种形式：
```go
p := Point{1,2}
```

第二种形式：
```go
p := Point{X:1,Y:2}
```

结构体的比较:
如果结构体的所有成员变量都可以比较，那么这个结构体就是可以比较的。两个结构体的比较可以使用 == 或者 !=. 其中 == 操作符按照顺序比较两个结构体变量的成员变量。
和其它可比较类型一样，可以比较的结构体类型都可以作为 map 的键类型。

结构体嵌套和匿名成员变量
Go 允许定义不带名称的结构体成员，只需要指定类型即可，这种结构体成员称为匿名成员。如下所示：
```go
type Circle struct {
	Point
	Radius int
}
```

Point 类型嵌套到 Circle 中。
匿名成员变量的好处是访问变量便捷，如下所示：
```go
var c Circle
c.X = 8 // 等同于 c.Point.X = 8
c.Y = 8 // 等同于 c.Point.Y = 8
c.Radius = 5

初始化
```go
c = Circle{Point{8,8},5}
```
或
```go
c = Circle{
	Point: Point {X:8,Y:8},
	Radius: 5,
}
```
说明：
上面最后一个逗号”,”不能省略，Go会报错，这个逗号有助于我们去扩展这个结构，所以习惯后，这是一个很好的特性。



