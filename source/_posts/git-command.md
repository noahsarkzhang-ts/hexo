---
title: Git 常用命令
date: 2024-04-12 21:29:21
updated: 2024-04-12 21:29:21
tags:
- git 命令
categories: 
- 运维
---

这篇文章主要记录用到的 git 命令。

<!-- more -->

## git 基本操作
**1. clone项目**
```bash
git clone ssh://user@192.168.1.100:29418/mytest.git
```

**2. 把当前文件放入暂存区域**
```bash
git add files 
```

**3. 提交修改**
```bash
git commit -m "readme.txt hacked."
```

**4. 推送代码到远程仓库**
```bash
# 推送本地的 master 分支来更新远程仓库上的 master 分支
git push origin master

# 推送代码gerrit
git push origin head:refs/for/master
```

**5. 初始化指定目录，目录未存在则新建**
```bash
git init 目录
```

**6. 重新提交（覆盖之前的提交**
```bash
git commit --amend -m ''
```

## 查看对象的信息
显示各种对象 的信息，可以是branch,commit id,tag等。
```bash
git show branch/commit_id/tag
```

## 查看记录
**1. 显示提交历史记录**
```bash
git log
```

**2. 查看最新两个提交的记录及修改记录**
```bash
git log -p -2 
```

**3. 单行显示历史提交记录**
```bash
git log --pretty=oneline 
```

**4. 用图形展示提交历史**
```bash
git log --oneline --decorate --color --graph --all

选项说明：
# --oneline: 把每一个提交压缩到了一行中
# --decorate: 让 git log 显示指向这个提交的所有引用（比如说分支、标签等）
# --color: 彩色输出信息
# --graph: 绘制一个 ASCII 图像来展示提交历史的分支结构
# --all: 显示所有分支信息

# 也可指定分支名称
git log --oneline --decorate --color --graph master
```

## 分支相关命令
**1. 列出所有分支**
```bash
git branch –a
```

**2. 查看当前分支是否远程分支**
```bash
git branch –r
```

**3. 显示所有分支**
```bash
git branch
```

**4. 创建分支**
```bash
git branch <name>
```

**5. 切换分支**
```bash
git checkout <name>
```

**6. 创建+切换分支**
```bash
git checkout -b <name>

# 实例
git checkout -b dev_4.37 origin/dev_4.37
```

**7. 合并某分支到当前分支**
```bash
git merge <name>
```

**8. Cherry Pick**
```bash
# herry-pick命令"复制"一个提交节点并在当前分支做一次完全一样的新提交
git cherry-pick commit_id
```

**9. rebase**
rebase 命令是合并分支的另一种选择，合并把两个父分支合并进行一次提交，提交历史不是线性的。rebase 在当前分支上重演另一个分支的历史，提交历史是线性的。本质上，这是线性化的自动的 cherry-pick.
```bash
git rebase branch_name
```

**10. 删除分支**
```bash
git branch -d <name>
```

## tag 相关命令
**1. 查看某个 tag 信息**
```bash
git show v0.0.1
```

**2. 查看所有 tag 信息**
```bash
git tag
```

**3. 根据 tag 创建分支**
```bash
git branch <new-branch-name> <tag-name>

# 实例
git branch qp_v1.4.0 v1.4.0
```

## 比较命令
**1. 比较两个提交间的修改**
```bash
git diff <commit-id> <commit-id>
```

**2. 输出修改的统计数据**
```bash
git diff <commit-id> <commit-id> --stat
```

**3. 比较file1文件的修改**
```bash
git diff <commit-id> <commit-id> file1
```

## 撤销命令

**1. 撤销最后一次git add files**
```bash
git reset -- files
```

**2. 把文件从暂存区域复制到工作目录，用来丢弃本地修改**
```bash
git checkout -- files
```

**3. git reset操作**
```bash
# –hard表示将本地库、working tree和index file都撤销到指定ID以前状态
git reset –-hard commit_id

# 撤销commit，而保留working tree和index file的信息
git reset –-soft commit_id

# 撤销commit和index file，只保留working tree的信息,默认配置
git reset –-mixed commit_id

```

## 放弃本地修改
```bash
git fetch --all
git reset --hard origin/master
```

## 提交代码到github
**1. 工作空间创建 .git 文件夹（默认隐藏了该文件夹）**
```bash
git init .
```

**2. 添加当前目录到暂存区**
```bash
git add . 
```

**3. 提交修改**
```bash
git commit -m "你的提交注释"
```

**4. 将本地分支修改为 main**
```bash
git branch -M main
```

**5. 本地仓库和远程 github 关联**
```bash
5.git remote add origin http://xxxxxxxxx.git
```

**6. 拉取远程代码并rebase到当前分支**
```bash
git pull --rebase origin main
```

## Git 图例
### 基本用法
![basic-usage](/images/git/basic-usage.svg.png "basic-usage")

上面的四条命令在工作目录、暂存目录(也叫做索引)和仓库之间复制文件。
- git add files 把当前文件放入暂存区域。
- git commit 给暂存区域生成快照并提交。
- git reset -- files 用来撤销最后一次git add files，你也可以用git reset 撤销所有暂存区域文件。
- git checkout -- files 把文件从暂存区域复制到工作目录，用来丢弃本地修改。

### Diff 命令
diff 命令查看两次提交之间的变动。
![git-diff](/images/git/diff.svg "git-diff")

### Merge 命令
merge 命令把不同分支合并起来。合并前，索引必须和当前提交相同。如果另一个分支是当前提交的祖父节点，那么合并命令将什么也不做。 另一种情况是如果当前提交是另一个分支的祖父节点，就导致 fast-forward 合并。指向只是简单的移动，并生成一个新的提交。
![merge-ff](/images/git/merge-ff.svg "merge-ff")

否则就是一次真正的合并。默认把当前提交(ed489 如下所示)和另一个提交(33104)以及他们的共同祖父节点(b325c)进行一次三方合并。结果是先保存当前目录和索引，然后和父节点33104一起做一次新提交。

![merge](/images/git/merge.svg "merge")

### Cherry Pick
cherry-pick 命令"复制"一个提交节点并在当前分支做一次完全一样的新提交。

![cherry-pick](/images/git/cherry-pick.svg "cherry-pick")

### Rebase
Rebase 是合并命令的另一种选择。合并把两个父分支合并进行一次提交，提交历史不是线性的。Rebase 在当前分支上重演另一个分支的历史，提交历史是线性的。 本质上，这是线性化的自动的 cherry-pick.
![rebase](/images/git/rebase.svg "rebase")
上面的命令都在 topic 分支中进行，而不是 main 分支，在 main 分支上重演，并且把分支指向新的节点。注意旧提交没有被引用，将被回收。

</br>

**参考：**

----
[1]:https://marklodato.github.io/visual-git-guide/index-zh-cn.html

[1. 图解Git][1]
