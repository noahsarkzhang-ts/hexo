---
title: 跳跃表
date: 2019-10-16 08:57:31
tags:
- 数据结构
- 算法
- 跳跃表
- skip list
categories:
- 数据结构与算法
---

## 1. 概述
跳跃表是一种数据结构。它允许快速查询一个有序连续元素的数据链表。跳跃表的平均查找和插入时间复杂度都是O(log n)，优于普通队列的O(n)。快速查询是通过维护一个多层次的链表，且每一层链表中的元素是前一层链表元素的子集。一开始时，算法在最稀疏的层次进行搜索，直至需要查找的元素在该层两个相邻的元素中间。这时，算法将跳转到下一个层次，重复刚才的搜索，直到找到需要查找的元素为止，跳跃表示意图如下所示。
![skip-list](/images/skip-list.png "skip-list")
从图中可以看到， 跳跃表主要由以下部分构成：
- 表头（head）：负责维护跳跃表的节点指针；
- 跳跃表节点：保存着元素值，以及多个层。
- 层：保存着指向其他元素的指针，高层的指针越过的元素数量大于等于低层的指针，为了提高查找的效率，程序总是从高层先开始访问，然后随着元素值范围的缩小，慢慢降低层次。
- 表尾：全部由 NULL 组成，表示跳跃表的末尾。

**参考：**

----
[1]:https://zh.wikipedia.org/wiki/%E8%B7%B3%E8%B7%83%E5%88%97%E8%A1%A8
[2]:https://zh.wikipedia.org/wiki/AVL%E6%A0%91
[3]:https://tech.meituan.com/2016/12/02/redblack-tree.html
[4]:https://blog.csdn.net/eson_15/article/details/51144079
[5]:https://www.jianshu.com/p/37436ed14cc6
[6]:https://github.com/julycoding/The-Art-Of-Programming-By-July/blob/master/ebook/zh/03.01.md

[1. 跳跃列表][1]

[2. AVL树][2]

[3. 红黑树深入剖析及Java实现][3]

[4. 【数据结构和算法05】 红-黑树（看完包懂~）][4]

[5. 红黑树与AVL树，各自的优缺点总结][5]

[6. 教你透彻了解红黑树][6]
