---
title: Git系列：Git 对象
date: 2024-04-04 19:10:57
updated: 2024-04-04 19:10:57
tags:
- git 对象
categories: 
- 笔记
---

Git 中有四种主要的数据类型，分别是数据对象、树对象、提交对象及标签对象，在这篇文章中主要介绍前三种。

<!-- more -->

## 数据对象
Git 是一个内容寻址文件系统，这意味着，Git 的核心部分是一个简单的键值对数据库（key-value data store）。 你可以向 Git 仓库中插入任意类型的内容，它会返回一个唯一的键，通过该键可以在任意时刻再次取回该内容。

**数据对象（blob object）**，顾名思义就是存放文件内容（数据）的对象，对应文件系统中的文件（FILE）,可以通过底层命令 **git hash-object** 来创建一个数据对象。该命令可将任意数据保存于 **.git/objects** 目录（即对象数据库），并返回指向该数据对象的唯一的键。

```bash
$ echo 'test content' | git hash-object -w --stdin
d670460b4b4aece5915caf5c68d12f560a9fe3e4
```

此命令输出一个长度为 40 个字符的校验和。 这是一个 SHA-1 哈希值，该哈希值由两部分内容一起做 SHA-1 校验运算得到，它们分别是：1）待存储的数据；2）头部信息（header），最后会进到其生成算法。生成的数据对象位于 **.git/objects** 目录下。

**说明：**
- -w 选项会指示该命令不要只返回键，还要将该对象写入数据库中；
- --stdin 选项则指示该命令从标准输入读取内容；若不指定此选项，则须在命令尾部给出待存储文件的路径。

```bash
$ find .git/objects -type f
.git/objects/d6/70460b4b4aece5915caf5c68d12f560a9fe3e4
```

查看 objects 目录，那么可以在其中找到一个与新内容对应的文件。 一个文件对应一条内容， 该文件以 SHA-1 校验和文件命名。 校验和的前两个字符用于命名子目录，余下的 38 个字符则用作文件名。

一旦你将内容存储在了对象数据库中，那么可以通过 **cat-file** 命令从 Git 那里取回数据。为 **cat-file** 指定 -p 选项可指示该命令自动判断内容的类型，并为我们显示大致的内容：

```bash
$ git cat-file -p d670460b4b4aece5915caf5c68d12f560a9fe3e4
test content
```

使用数据对象的写入、读取命令，我们可以对一个文件实现简单的版本控制。首先，创建一个文件并将内容存入数据库：
```bash
$ echo 'version 1' > test.txt
$ git hash-object -w test.txt
83baae61804e65cc73a7201a7252750c76066a30
```

接着，向文件里写入新内容，并再次将其存入数据库：
```bash
$ echo 'version 2' > test.txt
$ git hash-object -w test.txt
1f7a7a472abf3dd9643fd615f6da379c4acb3e3a
```

对象数据库记录下了该文件的两个不同版本，当然之前存入的第一条内容也还在：
```bash
$ find .git/objects -type f
.git/objects/1f/7a7a472abf3dd9643fd615f6da379c4acb3e3a
.git/objects/83/baae61804e65cc73a7201a7252750c76066a30
.git/objects/d6/70460b4b4aece5915caf5c68d12f560a9fe3e4
```

现在可以在删掉 test.txt 的本地副本，然后用 Git 从对象数据库中取回它的第一个版本：
```bash
$ git cat-file -p 83baae61804e65cc73a7201a7252750c76066a30 > test.txt
$ cat test.txt
version 1
```

或者第二个版本：
```bash
$ git cat-file -p 1f7a7a472abf3dd9643fd615f6da379c4acb3e3a > test.txt
$ cat test.txt
version 2
```

最后，也可以使用 **git cat-file -t** 命令，查看对象的类型：
```bash
$ git cat-file -t 1f7a7a472abf3dd9643fd615f6da379c4acb3e3a
blob
```

blob表示为数据对象。数据对象有两个问题：1）一个数据对象对应一个 SHA-1，要记忆它还是比较困难的；2）数据对象仅保存了文件内容，没有保存文件名，接下来的树对象可以解决文件名保存的问题。

## 树对象
**树对象（tree object）**对应文件系统中的目录，它能解决文件名保存的问题，也允许将多个文件组织到一起。 Git 以一种类似于 UNIX 文件系统的方式存储内容，但作了些许简化。 所有内容均以树对象和数据对象的形式存储，其中树对象对应了 UNIX 中的目录项，数据对象则大致上对应了 inodes 或文件内容。 一个树对象包含了一条或多条树对象记录（tree entry），每条记录含有一个指向数据对象或者子树对象的 SHA-1 指针，以及相应的模式、类型、文件名信息。 例如，某项目当前对应的最新树对象可能是这样的：

```bash
$ git cat-file -p master^{tree}
100644 blob a906cb2a4a904a152e80877d4088654daad0c859    README
100644 blob 8f94139338f9404f26296befa88755fc2598c289      Rakefile
040000 tree 99f1a6d12cb4b6f19c8655fca46c3ecf317074e0      lib
```

**master^{tree}** 语法表示 master 分支上最新的提交所指向的树对象。 请注意，lib 子目录（所对应的那条树对象记录）并不是一个数据对象，而是一个指针，其指向的是另一个树对象。
```bash
$ git cat-file -p 99f1a6d12cb4b6f19c8655fca46c3ecf317074e0
100644 blob 47c6340d6459e05787f644c2447d2595f5d3a54b      simplegit.rb
```

从概念上讲，Git 内部存储的数据有点像这样：
![树对象](/images/git/git-data-model-1.png "树对象")

通常，Git 根据某一时刻暂存区（即 index 区域，下同）所表示的状态创建并记录一个对应的树对象， 如此重复便可依次记录（某个时间段内）一系列的树对象。 因此，为创建一个树对象，首先需要通过暂存一些文件来创建一个暂存区，暂存区存储在 **.git/index** 文件中。

可以通过底层命令 **git update-index** 为一个test.txt 文件创建一个暂存区。 利用该命令，可以把 test.txt 文件的首个版本人为地加入一个新的暂存区。 必须为上述命令指定 --add 选项，因为此前该文件并不在暂存区中（甚至都还没来得及创建一个暂存区）； 同样必需的还有 --cacheinfo 选项，因为将要添加的文件位于 Git 数据库中，而不是位于当前目录下。 同时，需要指定文件模式、SHA-1 与文件名：
```bash
$ git update-index --add --cacheinfo 100644 \
  83baae61804e65cc73a7201a7252750c76066a30 test.txt
```

本例中，指定的文件模式为 100644，表明这是一个普通文件。 其他选择包括：100755，表示一个可执行文件；120000，表示一个符号链接。 这里的文件模式参考了常见的 UNIX 文件模式，但远没那么灵活——上述三种模式即是 Git 文件（即数据对象）的所有合法模式（当然，还有其他一些模式，但用于目录项和子模块）。

现在，可以通过 **git write-tree** 命令将暂存区内容写入一个树对象。 此处无需指定 -w 选项——如果某个树对象此前并不存在的话，当调用此命令时， 它会根据当前暂存区状态自动创建一个新的树对象：
```bash
$ git write-tree
d8329fc1cc938780ffdd9f94e0d364e0ea74f579
$ git cat-file -p d8329fc1cc938780ffdd9f94e0d364e0ea74f579
100644 blob 83baae61804e65cc73a7201a7252750c76066a30      test.txt
```

用 **git cat-file** 命令验证一下它确实是一个树对象：
```bash
$ git cat-file -t d8329fc1cc938780ffdd9f94e0d364e0ea74f579
tree
```

接着来创建一个新的树对象，它包括 test.txt 文件的第二个版本，以及一个新的文件：
```bash
$ echo 'new file' > new.txt
$ git update-index --add --cacheinfo 100644 \
  1f7a7a472abf3dd9643fd615f6da379c4acb3e3a test.txt
$ git update-index --add new.txt
```

暂存区现在包含了 test.txt 文件的新版本，和一个新文件：new.txt。 记录下这个目录树（将当前暂存区的状态记录为一个树对象），然后观察它的结构：
```bash
$ git write-tree
0155eb4229851634a0f03eb265b69f5a2d56f341
$ git cat-file -p 0155eb4229851634a0f03eb265b69f5a2d56f341
100644 blob fa49b077972391ad58037050f2a75f74e3671e92      new.txt
100644 blob 1f7a7a472abf3dd9643fd615f6da379c4acb3e3a      test.txt
```

另外，可以将已经创建的树对象作为子目录，加载到当前对象中：
```bash
$ git read-tree --prefix=bak d8329fc1cc938780ffdd9f94e0d364e0ea74f579
$ git write-tree
3c4e9cd789d88d8d89c1073707c3585e41b0e614
$ git cat-file -p 3c4e9cd789d88d8d89c1073707c3585e41b0e614
040000 tree d8329fc1cc938780ffdd9f94e0d364e0ea74f579        bak
100644 blob fa49b077972391ad58037050f2a75f74e3671e92      new.txt
100644 blob 1f7a7a472abf3dd9643fd615f6da379c4acb3e3a      test.txt
```

通过调用 **git read-tree** 命令，可以把树对象读入暂存区。通过指定 --prefix 选项，指定目录的名称。

如果基于这个新的树对象创建一个工作目录，你会发现工作目录的根目录包含两个文件以及一个名为 bak 的子目录，该子目录包含 test.txt 文件。其结构如下：
![树对象](/images/git/git-data-model-2.png "树对象")

**命令参考：**
查看index区文件
```bash
git ls-files --stage
```

删除index区的文件
```bash
git rm --cached file
git reset -- files 用来撤销最后一次git add files，你也可以用git reset 撤销所有暂存区域文件
```

## 提交对象

如果你做完了以上所有操作，那么现在就有了三个树对象，分别代表想要跟踪的不同项目快照。 然而问题依旧：若想重用这些快照，你必须记住所有三个 SHA-1 哈希值。并且，你也完全不知道是谁保存了这些快照，在什么时刻保存的，以及为什么保存这些快照。 而以上这些，正是**提交对象（commit object）**能为你保存的基本信息。

可以通过调用 **git commit-tree** 命令创建一个提交对象，为此需要指定一个树对象的 SHA-1 值，以及该提交的父提交对象（如果有的话）。 从之前创建的第一个树对象开始：
```bash
$ echo 'first commit' | git commit-tree d8329f
fdf4fc3344e67ab068f836878b6c4951e3b15f3d
```
由于创建时间和作者数据不同，你现在会得到一个不同的散列值。 现在可以通过 **git cat-file** 命令查看这个新提交对象：
```bash
$ git cat-file -p fdf4fc3
tree d8329fc1cc938780ffdd9f94e0d364e0ea74f579
author Scott Chacon <schacon@gmail.com> 1243040974 -0700
committer Scott Chacon <schacon@gmail.com> 1243040974 -0700

first commit
```

提交对象的格式很简单：它先指定一个顶层树对象，代表当前项目快照； 然后是可能存在的父提交（前面描述的提交对象并不存在任何父提交）； 之后是作者/提交者信息（依据你的 user.name 和 user.email 配置来设定，外加一个时间戳）； 留空一行，最后是提交注释。

接着，创建另外两个提交对象，它们分别引用各自的上一个提交（作为其父提交对象）：
```bash
$ echo 'second commit' | git commit-tree 0155eb -p fdf4fc3
cac0cab538b970a37ea1e769cbbde608743bc96d
$ echo 'third commit'  | git commit-tree 3c4e9c -p cac0cab
1a410efbd13591db07496601ebc7a059dd55cfe9
```

这三个提交对象分别指向之前创建的三个树对象快照中的一个。 现在，如果对最后一个提交的 SHA-1 值运行 **git log** 命令，会出乎意料的发现，你已有一个货真价实的、可由 **git log** 查看的 Git 提交历史了：
```bash
$ git log --stat 1a410e
commit 1a410efbd13591db07496601ebc7a059dd55cfe9
Author: Scott Chacon <schacon@gmail.com>
Date:   Fri May 22 18:15:24 2009 -0700

	third commit

 bak/test.txt | 1 +
 1 file changed, 1 insertion(+)

commit cac0cab538b970a37ea1e769cbbde608743bc96d
Author: Scott Chacon <schacon@gmail.com>
Date:   Fri May 22 18:14:29 2009 -0700

	second commit

 new.txt  | 1 +
 test.txt | 2 +-
 2 files changed, 2 insertions(+), 1 deletion(-)

commit fdf4fc3344e67ab068f836878b6c4951e3b15f3d
Author: Scott Chacon <schacon@gmail.com>
Date:   Fri May 22 18:09:34 2009 -0700

    first commit

 test.txt | 1 +
 1 file changed, 1 insertion(+)
```

没有借助任何上层命令，仅凭几个底层操作便完成了一个 Git 提交历史的创建。 这就是每次我们运行 git add 和 git commit 命令时，Git 所做的工作实质就是将被改写的文件保存为数据对象， 更新暂存区，记录树对象，最后创建一个指明了顶层树对象和父提交的提交对象。 这三种主要的 Git 对象——数据对象、树对象、提交对象——最初均以单独文件的形式保存在 .git/objects 目录下。 下面列出了目前示例目录内的所有对象，辅以各自所保存内容的注释：

```bash
$ find .git/objects -type f
.git/objects/01/55eb4229851634a0f03eb265b69f5a2d56f341 # tree 2
.git/objects/1a/410efbd13591db07496601ebc7a059dd55cfe9 # commit 3
.git/objects/1f/7a7a472abf3dd9643fd615f6da379c4acb3e3a # test.txt v2
.git/objects/3c/4e9cd789d88d8d89c1073707c3585e41b0e614 # tree 3
.git/objects/83/baae61804e65cc73a7201a7252750c76066a30 # test.txt v1
.git/objects/ca/c0cab538b970a37ea1e769cbbde608743bc96d # commit 2
.git/objects/d6/70460b4b4aece5915caf5c68d12f560a9fe3e4 # 'test content'
.git/objects/d8/329fc1cc938780ffdd9f94e0d364e0ea74f579 # tree 1
.git/objects/fa/49b077972391ad58037050f2a75f74e3671e92 # new.txt
.git/objects/fd/f4fc3344e67ab068f836878b6c4951e3b15f3d # commit 1
```
如果跟踪所有的内部指针，将得到一个类似下面的对象关系图：
![提交对象](/images/git/git-data-model-3.png "提交对象")

## 对象存储

Git 仓库提交的所有对象都会有一个头部信息，并与文件内容一起存储。 下面使用Ruby 脚本语言演示一个数据对象的生成，其内容是字符串“what is up, doc?”。

可以通过 irb 命令启动 Ruby 的交互模式：
```bash
$ irb
>> content = "what is up, doc?"
=> "what is up, doc?"
```

Git 首先会以识别出的对象的类型作为开头来构造一个头部信息，本例中是一个“blob”字符串。 接着 Git 会在头部的第一部分添加一个空格，随后是数据内容的字节数，最后是一个空字节（null byte）：
```bash
>> header = "blob #{content.length}\0"
=> "blob 16\u0000"
```

Git 会将上述头部信息和原始数据拼接起来，并计算出这条新内容的 SHA-1 校验和。 在 Ruby 中可以这样计算 SHA-1 值——先通过 require 命令导入 SHA-1 digest 库， 然后对目标字符串调用 Digest::SHA1.hexdigest()：
```bash
>> store = header + content
=> "blob 16\u0000what is up, doc?"
>> require 'digest/sha1'
=> true
>> sha1 = Digest::SHA1.hexdigest(store)
=> "bd9dbf5aae1a3862dd1526723246b20206e5fc37"
```

我们来比较一下 **git hash-object** 的输出。 这里使用了 echo -n 以避免在输出中添加换行。
```bash
$ echo -n "what is up, doc?" | git hash-object --stdin
bd9dbf5aae1a3862dd1526723246b20206e5fc37
```

Git 会通过 zlib 压缩这条新内容。在 Ruby 中可以借助 zlib 库做到这一点。 先导入相应的库，然后对目标内容调用 Zlib::Deflate.deflate()：
```bash
>> require 'zlib'
=> true
>> zlib_content = Zlib::Deflate.deflate(store)
=> "x\x9CK\xCA\xC9OR04c(\xCFH,Q\xC8,V(-\xD0QH\xC9O\xB6\a\x00_\x1C\a\x9D"
```

最后，需要将这条经由 zlib 压缩的内容写入磁盘上的某个对象。 要先确定待写入对象的路径（SHA-1 值的前两个字符作为子目录名称，后 38 个字符则作为子目录内文件的名称）。 如果该子目录不存在，可以通过 Ruby 中的 FileUtils.mkdir_p() 函数来创建它。 接着，通过 File.open() 打开这个文件。最后，对上一步中得到的文件句柄调用 write() 函数，以向目标文件写入之前那条 zlib 压缩过的内容：
```bash
>> path = '.git/objects/' + sha1[0,2] + '/' + sha1[2,38]
=> ".git/objects/bd/9dbf5aae1a3862dd1526723246b20206e5fc37"
>> require 'fileutils'
=> true
>> FileUtils.mkdir_p(File.dirname(path))
=> ".git/objects/bd"
>> File.open(path, 'w') { |f| f.write zlib_content }
=> 32
```
我们用 git cat-file 查看一下该对象的内容：
```bash
$ git cat-file -p bd9dbf5aae1a3862dd1526723246b20206e5fc37
what is up, doc?
```
就是这样——你已创建了一个有效的 Git 数据对象。

所有的 Git 对象均以这种方式存储，区别仅在于类型标识——另两种对象类型的头部信息以字符串“commit”或“tree”开头，而不是“blob”。 另外，虽然数据对象的内容几乎可以是任何东西，但提交对象和树对象的内容却有各自固定的格式。

</br>

**参考：**

----
[1]:https://git-scm.com/book/zh/v2/Git-%E5%86%85%E9%83%A8%E5%8E%9F%E7%90%86-Git-%E5%AF%B9%E8%B1%A1

[1. Git 内部原理 - Git 对象][1]
