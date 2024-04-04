---
title: Git系列：Git 远程仓库
date: 2024-04-04 21:51:34
updated: 2024-04-04 21:51:34
tags:
- git 过程仓库
categories: 
- 笔记
---

这篇文章主要讲述远程仓库的使用。

<!-- more -->
## origin 远程仓库
使用 **git clone** Git 会跟 clone 的仓库服务器一个默认的名称，这个名称便是 origin.
```bash
$ git clone https://github.com/schacon/ticgit
```

使用该命令之后，会生成一个origin的远程仓库，可使用 **git remote -v** 命令查看：
```bash
$ git remote -v
origin	https://github.com/schacon/ticgit (fetch)
origin	https://github.com/schacon/ticgit (push)
```

**<font color='red'>origin</font>** 并无特殊含义
远程仓库名字 “origin” 与分支名字 “master” 一样，在 Git 中并没有任何特别的含义一样。 同时 “master” 是当你运行 **git init** 时默认的起始分支名字，原因仅仅是它的广泛使用， “origin” 是当你运行 **git clone** 时默认的远程仓库名字。 如果你运行 **git clone -o booyah**，那么你默认的远程分支名字将会是 booyah/master。

## 添加远程仓库
添加一个远程仓库，命令如下：
```bash
$ git remote add <shortname> <url>
```

添加一个新的远程 Git 仓库，同时指定一个方便使用的简写, 如添加一个 bp 的远程仓库。
```bash
$ git remote add pb https://github.com/paulboone/ticgit
$ git remote -v
origin	https://github.com/schacon/ticgit (fetch)
origin	https://github.com/schacon/ticgit (push)
pb	https://github.com/paulboone/ticgit (fetch)
pb	https://github.com/paulboone/ticgit (push)
```

现在你可以在命令行中使用字符串 pb 来代替整个 URL。 例如，如果你想拉取 pb 的仓库中有但你没有的信息，可以运行 **git fetch pb**：
```bash
$ git fetch pb
remote: Counting objects: 43, done.
remote: Compressing objects: 100% (36/36), done.
remote: Total 43 (delta 10), reused 31 (delta 5)
Unpacking objects: 100% (43/43), done.
From https://github.com/paulboone/ticgit
 * [new branch]      master     -> pb/master
 * [new branch]      ticgit     -> pb/ticgit
```

## 从远程仓库中抓取与拉取
```bash
$ git fetch <remote>
```
这个命令会访问远程仓库，从中拉取所有你还没有的数据。 执行完成后，你将会拥有那个远程仓库中所有分支的引用，可以随时合并或查看。

如果你使用 clone 命令克隆了一个仓库，命令会自动将其添加为远程仓库并默认以 “origin” 为简写。 所以，git fetch origin 会抓取克隆（或上一次抓取）后新推送的所有工作。 必须注意 git fetch 命令只会将数据下载到你的本地仓库，它并不会自动合并或修改你当前的工作。 当准备好时你必须手动将其合并入你的工作。

如果你的当前分支设置了跟踪远程分支， 那么可以用 **git pull** 命令来自动抓取后合并该远程分支到当前分支。 这或许是个更加简单舒服的工作流程。默认情况下，**git clone** 命令会自动设置本地 master 分支跟踪克隆的远程仓库的 master 分支（或其它名字的默认分支）。 运行 **git pull** 通常会从最初克隆的服务器上抓取数据并自动尝试合并到当前所在的分支。

## 推送到远程仓库
```bash
$ git push <remote> <branch>
```
当你想要将 master 分支推送到 origin 服务器时（再次说明，克隆时通常会自动帮你设置好那两个名字）。

## 查看某个远程仓库
```bash
$git remote show <remote> 
```
如果想要查看某一个远程仓库的更多信息,可以使用这个命令
```bash
$ git remote show origin
* remote origin
  Fetch URL: https://github.com/schacon/ticgit
  Push  URL: https://github.com/schacon/ticgit
  HEAD branch: master
  Remote branches:
    master                               tracked
    dev-branch                           tracked
  Local branch configured for 'git pull':
    master merges with remote master
  Local ref configured for 'git push':
    master pushes to master (up to date)
```
它同样会列出远程仓库的 URL 与跟踪分支的信息。 这些信息非常有用，它告诉你正处于 master 分支，并且如果运行 **git pull**， 就会抓取所有的远程引用，然后将远程 master 分支合并到本地 master 分支。 它也会列出拉取到的所有远程引用。

## 远程仓库的重命名与移除
```bash
$ git remote rename oldname newname
```
可以运行 **git remote rename** 来修改一个远程仓库的简写名。 例如，想要将 pb 重命名为 paul：
```bash
$ git remote rename pb paul
$ git remote
origin
paul
```
值得注意的是这同样也会修改你所有远程跟踪的分支名字。 那些过去引用 pb/master 的现在会引用 paul/master。

如果因为一些原因想要移除一个远程仓库，你已经从服务器上搬走了或不再想使用某一个特定的镜像了，又或者某一个贡献者不再贡献了，可以使用 **git remote remove** 或 **git remote rm** ：
```bash
$ git remote remove paul
$ git remote
origin
```
一旦你使用这种方式删除了一个远程仓库，那么所有和这个远程仓库相关的远程跟踪分支以及配置信息也会一起被删除。
