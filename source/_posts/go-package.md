---
title: Go系列：Go Package
date: 2024-06-13 17:11:57
updated: 2024-06-13 17:11:57
tags:
- go package
categories: 
- 笔记
---

这篇文章主要讲述 Go 语言 package 机制。

<!-- more -->

任何包管理系统的目的都是通过关联的特性进行分类，组织成便于理解和修改的单元，使其与程序的其它包保持独立，从而有助于设计和维护大型的程序。模块化允许包在不同的项目中共享、复用，在组织中发布，或者在全世界范围内使用。

## 导入路径
每一个包都通过一个唯一的字符串进行标识，它称为导入路径，它们用在 import 声明中，如下所示：
```go
import (
	protoreflect "google.golang.org/protobuf/reflect/protoreflect"
	protoimpl "google.golang.org/protobuf/runtime/protoimpl"
	reflect "reflect"
	sync "sync"
)
```

对于准备共享或公开的包，导入路径需要全局唯一。为了避免冲突，除了标准库中的包之后，其它包的导入路径应该以互联网域名作为路径开始，这样也方便查找包。


## 包的声明
在每一个 GO 源文件的开头都需要进行包的声明，主要的目的是当该包被其它包引入的时候作为其默认的标识符，也称为包名。
例如，math/rand 包中每一个文件的开头都是 package rand, 这样当你导入这个包时，可以访问它的成员，比如 rand.Int, rand.Float64等。
```go
package main

import (
	"fmt"
	"math/rand"
)

func main() {
	fmt.Println(rand.Int())
}
```

通常，包名是导入路径的最后一段，于是，即使导入路径不同的两个包，二者也可以拥有同样的名字。为了避免冲突，可以对包名定义别名，如：
```go
import (
	"crypto/rand"
	mrand "math/rand"
)
```
关于取"最后一段"作为惯例，有三个例外：
1）main 函数使用的包名总是 main, 跟导入的路径没有关系；
2）目录中可能有一些文件名字以_test.go结尾，包名中会出现以_test结尾。这样一个目录中有两个包：一个普通的，再加上一个外部测试包。_test 后缀告诉 go test 两个包都需要构建，并且指明文件属于哪个包；
3）有一些依赖管理工具会在包导入路径的尾部追加版本号后缀，如"gopkg.in/yaml.v2". 包名不包含后缀，因此这个包名为 yaml。

## 导入声明
一个 Go 源文件可以在 package 声明的后面和第一个非导入声明语句前面紧接着包含零下或多个 import 声明。每一个导入可以单独指定一条导入路径，也可以通过圆括号括起来的列表一次导入多个包，下面两种方式是等价的。
```go
import "fmt"
import "os"

import (
	"fmt"
	"os"
)
```

导入的包可以通过空行进行分组，这类分组通常表示不同领域和方面的包。导入顺序不重要，但按照惯例每一组都按照字母进行排序。
```go
import (
	"fmt"
	"html/template"
	"os"
	
	"golang.org/x/net/html"
	"golang.org/x/net/ipv4"
)
```
如果需要把两个名字一样的包导入到第三个包中，导入声明就必须至少为其中的一个指定一个替代名字来避免冲突，这叫做重命名导入。
```go
import (
	"crypto/rand"
	mrand "math/rand"
)
```
替代名字仅影响当前文件。重命名导入在没有冲突时也非常有用，如用简洁的名称代替冗长的包名。

## 空导入
如果导入的包没有在文件中被引用，就会产生一个编译错误。但是，有时候，我们必须导入一个包，这仅仅是为利用其副作用：对包级别的变量执行初始化表达式值，并执行它的init函数。为了防止"未使用的导入"错误，我们必须使用一个重命名导入，它使用一个替代的名字_,这表示导入的内容为空白标识符。通常情况下，空白标识不可能被引用。
```go
import _ "image/png"   // 注册PNG解码器
```

这称为空白导入。

## 包及其命名
包及成员命名的相关建议：
1. 使用简短的名字来命名包名，如标准库中常见的包：bufio,bytes,flag,fmt,http,io,json,os,sort,sync和time等；
2. 尽可能保持可读性和无歧义，如使用 imageutil 或 ioutil 等名称清晰和具体的包名，避免使用util宽泛的包名；
3. 包名使用统一的形式，如使用 bytes, errors,和 strings 复数形式来避免与基本类型相冲突;
4. 避免使用有其它含义的包名，如temp 有温度和临时的双重含义；
5. 包成员如函数、变量的命名遵循一些通用的命名模式：包名与包成员在命名上信息不需要冗余，如 strings 包名已经传达了该包是处理字符串的包，其成员名称不用再包含 string 字串了，较合理的命名为：strings.Index，冗余的命名为：strings.IndexString。

## go工具 
go 工具将不同种类的工具集合并为一个命令集。它是包管理器，它可以查询包的作者，计算它们的依赖关系，从远程版本控制系统下载它们。它是一个构建系统，可计算文件依赖，调用编译器、汇编器和链接器。它也是一个测试驱动程序，可以执行相关的测试代码。

使用go help可以查看支持的命令集：
```bash
go help
...
    bug         start a bug report
    build       compile packages and dependencies
    clean       remove object files and cached files
    doc         show documentation for package or symbol
    env         print Go environment information
    fix         update packages to use new APIs
    fmt         gofmt (reformat) package sources
    generate    generate Go files by processing source
    get         add dependencies to current module and install them
    install     compile and install packages and dependencies
    list        list packages or modules
    mod         module maintenance
    work        workspace maintenance
    run         compile and run Go program
    test        test packages
    tool        run specified go tool
    version     print Go version
        vet         report likely mistakes in packages

Use "go help <command>" for more information about a command.
...
```

### 环境变量
常用的环境变量如下：
1. GOPATH: 指定工作空间的根目录；
2. GOROOT: 指定Go 发行版的根目录，其中提供所有标准库的包；
3. GOOS：指定操作系统，如android, linux, darwin 或者 windows;
4. GOARCH：指定目标处理器架构，如 amd64, 386 或者 arm.

go env 命令输出当前系统与go语言相关的环境变量：
```bash
go env
set GO111MODULE=on
set GOARCH=amd64
set GOHOSTARCH=amd64
set GOHOSTOS=windows
set GOOS=windows
set GOPATH=C:\Users\Allen\go
set GOROOT=c:\go
...
```

### 包的下载
go get 命令可以下载单一的包，也可以使用...符号来下载子树或仓库，该工具也计算并下载初始包所有的依赖性，如下所示：
```bash
go get gopl.io/...
```

`go get -u` 命令通常获取每一个包的最新版本，包括依赖的包。如果没有 -u 这个标记，已经存在于本地的包不会更新。

### 包的构建
go build 命令编译每一个命令行参数中的包。如果包是一个库，结果会被舍弃；对于没有编译错误的包几乎不做检查。如果包的名字是main, go build调用链接器在当前目录中创建可以执行程序，可执行程序的名字取自包的导入路径的最后一段。
命令行中的包可以使用导入路径或者一个相对目录名，目录必须以 .或 ..开头。如果没有提供参数，会使用当前目录作为参数，所以，以下命令是等价的。
假定自定义一个环境变量：GOMODROOT，它表示模块的根目录。 
第一种方式：
```bash
cd $GOMODROOT/gopl.io/ch1/helloword
go build
```

第二种方式：
```go
go build gopl.io/ch1/helloword
```

第三种方式：
```go
cd $GOMODROOT
go build ./gopl.io/ch1/helloword
```

包也可以使用一个文件列表来指定。如果包是main,可执行程序的名字来自第一个 .go文件名的主体部分。
```go
go build helloword.go
```

如果不关心编译后的包，只想快速运行，测试程序的功能，可以使用 go run 命令，如下所示：
```go
go run helloword.go
```

默认情况下，`go build` 命令构建所有需要的包以及它们所有的依赖性，然后丢弃除了最终可执行之外的所有编译后的代码。

`go install` 命令和 `go build` 非常相似，区别是它会保存每一个包的编译代码和命令，而不是丢弃它们。编译后的包保存在 `$GOPATH/pkg` 目录中，可执行的命令保存在 $GOPATH/bin目录中。

因为编译包根据操作系统平台和CPU体系结构不同而不同，所以 `go install` 保存文件的目录便与 GOOS 和 GOARCH 变量的值相关。例如，在 Mac 上面 `golang.org/x/net/html` 编译后的文件 `golang.org/x/net/html.a` 放在 `$GOPATH/pkg/darwin_amd64` 目录下面。

执行 go build 时，可以指定cpu架构，如下所示：
```go
GOARCH=386 go build gopl.io/ch10/cross
```


