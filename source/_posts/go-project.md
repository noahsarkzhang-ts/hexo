---
title: Go系列：Go 工程搭建
date: 2024-04-12 22:59:47
updated: 2024-04-12 22:59:47
tags:
- go 模块
categories: 
- 笔记
---

这篇文章主要讲述 Go 工程或模块的构建。

<!-- more -->
从 Go 1.11 开始，Go 允许在 $GOPATH/src 外的任何目录下使用 go.mod 创建项目。在 $GOPATH/src 中，为了兼容性，Go 命令仍然在旧的 GOPATH 模式下运行。从 Go 1.13 开始，模块模式将成为默认模式。

设置环境变量，开启模块，Go 1.13之后，GO111MODULE 默认为 on.
```bash
export GO111MODULE=on
export GOPROXY=https://goproxy.io // 设置代理
```

我们假设一个多模块的场景：
1. 一个系统包含两个模块: greetings 和 hello;
2. hello 模块 会引用 greetings 模块中的函数；
3. greetings 模块是本地模块，还未发布。

## 新建 greetings 模块
假定该模块在用户home目录（可以是任意目录）下创建：
**1. 先为该模块创建目录**
```bash
mkdir greetings
cd greetings
```

**2. 使用 go mod init 命令启动模块**

运行go mod init命令，给它提供你的模块路径——在这里，使用example.com/greetings. 
```bash
$ go mod init example.com/greetings
go: creating new go.mod: module example.com/greetings
```

`go mod init`命令会创建一个 go.mod 文件来跟踪代码的依赖项。到目前为止，该文件仅包含您的模块名称和您的代码支持的 Go 版本。但是当您添加依赖项时，go.mod 文件将列出您的代码所依赖的版本。这使构建可重现，并使您可以直接控制要使用的模块版本。

> 当您运行go mod init 创建用于跟踪依赖项的模块时，您指定一个模块路径作为模块的名称。模块路径成为模块中包的导入路径前缀。一定要指定一个不会与其他模块的模块路径冲突的模块路径。通常而言，一般使用公司域名作为前缀。
模块路径通常采用以下形式:
`<prefix>/<descriptive-text>`
> 前缀通常是部分描述模块的字符串，例如描述其来源的字符串。这可能是：
> - 存储库的位置,如 `github.com/<project-name>/`；
> - 一个你控制的名字，如果您不使用存储库名称，请务必选择一个您确信不会被其他人使用的前缀。一个不错的选择是您公司的名称。

> 描述性文本，一个不错的选择是项目名称。请记住，模块路径为这些包名称创建一个命名空间。

**3. 编写代码**
创建一个用于编写代码的文件并将其命名为 greetings.go，其内容如下：
```go
package greetings

import "fmt"

// Hello 为指定的人返回问候语.
func Hello(name string) string {
    // 返回在消息中嵌入名称的问候语.
    message := fmt.Sprintf("Hi, %v. Welcome!", name)
    return message
}
```

代码说明：
- 声明一个 greetings 包来收集相关函数；
- 实现一个 Hello 函数来返回问候语，名称以大写字母开头的函数可以被外部包使用；
- 声明一个 message 变量来保存您的问候语；
- 使用 fmt 包的 Sprintf 函数创建问候消息。

## 创建 hello 调用模块
**1. 创建 hello 目录** 
在 greetings 同级目录添加 hello 目录，结构如下：
```bash
<home>/
 |-- greetings/
 |-- hello/
```

在 home 目录下，使用如下命令：
```bash
mkdir hello
cd hello
```

**2. 使用 go mod init 命令启动模块**
```bash
$ go mod init example.com/hello
go: creating new go.mod: module example.com/hello
```

**3. 创建源文件**
创建用于编写代码的源文件 hello.go

**4. 编写主函数**
编写代码来调用Hello函数，然后打印函数的返回值。
```go
package main

import (
    "fmt"

    "example.com/greetings"
)

func main() {
    // 获取问候信息并打印出来.
    message := greetings.Hello("Gladys")
    fmt.Println(message)
}
```

在此代码中:
- 声明一个main包。在 Go 中，作为应用程序执行的代码必须在main包中.
- 导入两个包：example.com/greetings 和 fmt 包。这使代码可以访问这些包中的函数。导入 example.com/greetings（您之前创建的模块中包含的包）使你可以访问 Hello 函数。您还导入了fmt，其中包含用于处理输入和输出文本（如将文本打印到控制台）的函数。
- 通过调用 greetings包的 Hello函数获取问候语。

**5. 引入 greetings 模块**
编辑 example.com/hello 模块以使用本地 example.com/greetings 模块
对于生产用途，您可以从其存储库（具有反映其已发布位置的模块路径）发布 example.com/greetings 模块，Go 工具可以在其中找到它以下载它。现在，由于尚未发布该模块，因此需要调整 example.com/hello模块，以便它可以在本地文件系统上找到 example.com/greetings 代码。
为此，请使用 go mod edit 命令编辑 example.com/hello 模块，将 Go 工具从其模块路径（模块不在的位置）重定向到本地目录（所在的位置）。

**1) 在 hello 目录中，运行以下命令：**
```bash
$ go mod edit -replace example.com/greetings=../greetings
```

该命令指定 example.com/greetings 应替换为 ../greetings，用于查找依赖项。运行该命令后，hello 目录中的 go.mod 文件应包含一个 replace 指令:
```bash
module example.com/hello

go 1.16

replace example.com/greetings => ../greetings
```

**2) 同步依赖模块**
在 hello 目录中，运行 go mod tidy 命令以同步 example.com/hello 模块的依赖项，添加代码所需的依赖项，但尚未在模块中跟踪的依赖项。
```bash
$ go mod tidy
go: found example.com/greetings in example.com/greetings v0.0.0-00010101000000-000000000000
```
命令完成后，example.com/hello 模块的 go.mod 文件应如下所示：
```bash
module example.com/hello

go 1.16

replace example.com/greetings => ../greetings

require example.com/greetings v0.0.0-00010101000000-000000000000
```
该命令在 greetings 目录中找到本地代码，然后添加了一个 require 指令来指定example.com/hello 需要 example.com/greetings。您在 hello.go 中导入greetings包时创建了此依赖项.

模块路径后面的数字是伪版本号 - 用于代替语义版本号（模块还没有）的生成的数字.

要引用已发布的模块，go.mod 文件通常会省略replace指令并使用末尾带有标记版本号的require指令。
```bash
require example.com/greetings v1.1.0
```

## 验证模块依赖
在 hello 目录下，运行代码以确认其正常工作。
```bash
$ go run .
Hi, Gladys. Welcome!
```

恭喜！您已经编写了两个功能模块.


## go 模块相关命令
```bash
# 初始化go.mod
go mod init

# 更新依赖文件
go mod tidy

# 下载依赖文件
go mod download

# 将依赖转移至本地的vendor文件
go mod vendor

# 手动修改依赖文件
go mod edit

# 打印依赖图
go mod graph

# 校验依赖
go mod verify
```

</br>

**参考：**

----
[1]:https://go.p2hp.com/go.dev/doc/tutorial/create-module
[2]:https://go.p2hp.com/go.dev/doc/tutorial/call-module-code
[3]:https://go.p2hp.com/doc/modules/managing-dependencies#naming_module

[1. 教程：创建一个 Go 模块][1]

[2. 从另一个模块调用您的代码][2]

[2. 管理依赖项#命名模块][3]



