---
title: 红黑树
date: 2019-10-11 09:58:08
tags:
- 数据结构
- 红黑树
- Red-Black tree
categories:
- 数据结构与算法
---

## 1. 概述

红黑树（Red–black tree）是一种平衡二叉查找树，它可以在 O(logn)时间内完成查找，插入和删除，这里的n是树中元素的数目，我们首先介绍下二叉查找树。

二叉查找树（Binary Search Tree），也称为二叉搜索树、有序二叉树（ordered binary tree）或排序二叉树（sorted binary tree），是指一棵空树或者具有下列性质的二叉树：

- 若任意节点的左子树不空，则左子树上所有节点的值均小于它的根节点的值；
- 若任意节点的右子树不空，则右子树上所有节点的值均大于它的根节点的值；
- 任意节点的左、右子树也分别为二叉查找树；
- 没有键值相等的节点。

在理想的情况下，二叉查找树插入、删除、查询的时间复杂度为O(logn)，最坏的情况下为O(N)。如果插入的数据是有序的情况下，二叉查找树会出现倾斜，退化为链表，如下图所示：
![incline](/images/incline.jpg "incline")

为了解决倾斜的问题，引入了平衡二叉查找树，AVL和红黑树是其两种类型，它们都能保证在时间复杂度为O(logn)下实现二叉查找树的增删查，下面对AVL树做下介绍。

在AVL树中，任一节点对应的两棵子树的最大高度差为1，因此它也被称为高度平衡树。查找、插入和删除在平均和最坏情况下的时间复杂度都是O(logn)。插入和删除元素的操作需要进行一次或多次旋转，以实现树的重新平衡，实际上插入操作最多两次旋转，而删除操作需要最多O(logn)次旋转。

红黑树相对于AVL树来说，牺牲了部分平衡性以换取插入/删除操作时少量的旋转操作，整体来说性能要优于AVL树。在红黑树中，进行插入操作和删除操作只需要少量O(logn)的颜色变更和不超过三次树旋转（对于插入操作是两次），虽然插入和删除很复杂，但操作时间仍可以保持为O(logn)次。

红黑树的实际应用非常广泛，比如Linux内核中的完全公平调度器、高精度计时器、ext3文件系统等等，各种语言的函数库如Java的TreeMap和TreeSet，C++ STL的map、multimap、multiset等等。

红黑树的插入和删除操作相对来说还是比较复杂，为了简化算法，引入了一种新的数据结构跳跃表（Skip List）。Skip List是一种随机化的数据结构，基于并联的链表，其效率可比拟于二叉查找树（对于大多数操作需要O(logn)平均时间）。跳跃列表的插入和删除的实现与普通的链表操作类似，相对比较简单，但高层元素必须在进行多个链表中进行插入或删除。

跳跃列表的发明者对跳跃列表的评价是：“跳跃列表是在很多应用中有可能替代平衡树而作为实现方法的一种数据结构。跳跃列表的算法有同平衡树一样的渐进的预期时间边界，并且更简单、更快速和使用更少的空间。”，跳跃表的一个应用场景是作为Redis有序集合对象的底层实现，跳跃表将在后面的文章中讲述。

现在对这几种数据结构做一个比较对比：
![rbt-comparison](/images/rbt-comparison.jpg "rbt-comparison")

## 2. 概念
### 2.1 定义
红黑树是每个节点都带有颜色属性的二叉查找树，颜色为红色或黑色。其特点如下：

- 1)节点是红色或黑色；
- 2)根是黑色；
- 3)所有叶子都是黑色的（叶子是NIL节点）；
- 4)每个红色节点必须有两个黑色的子节点（从每个叶子到根的所有路径上不能有两个连续的红色节点）；
- 5)从任一节点到其每个叶子的所有简单路径都包含相同数目的黑色节点。

下图就是一个红黑树的图例，来自维基百科。
![red-black-tree](/images/red-black-tree.png "red-black-tree")

叶子结点用NIL节点表示。

红黑树代码定义如下：
```java
public class RBTree<T extends Comparable<T>> {
    private RBNode<T> root; // 根结点
    private static final boolean RED = false;
    private static final boolean BLACK = true;

    // 结点定义
    private class RBNode<T extends Comparable<T>> {
        boolean color; // 颜色
        T key; // 键值
        RBNode<T> left; // 左结点
        RBNode<T> right; // 右结点
        RBNode<T> parent; // 父结点
        
        ...
    }
    ...
}

```

对红黑树进行插入及删除操作时，会改变红黑树的平衡，需要通过变色、左旋及右旋三种操作来修正，使其满足红黑树的定义。

### 2.2 变色
变色操作比较简单，代价也比较代，只是对结点的赋值操作，代码如下所示：
```java
public void setRed(RBNode<T> node) {
    if (node != null) {
        node.color = RED;
    }
}

public void setBlack(RBNode<T> node) {
    if (node != null) {
        node.color = BLACK;
    }
}


```

### 2.3 左旋

### 2.4 右旋


## 3. 插入

## 4. 删除

## 5. 总结

**参考：**

----
[1]:https://zh.wikipedia.org/wiki/%E7%BA%A2%E9%BB%91%E6%A0%91
[2]:https://zh.wikipedia.org/wiki/AVL%E6%A0%91
[3]:https://tech.meituan.com/2016/12/02/redblack-tree.html
[4]:https://blog.csdn.net/eson_15/article/details/51144079
[5]:https://www.jianshu.com/p/37436ed14cc6
[6]:https://github.com/julycoding/The-Art-Of-Programming-By-July/blob/master/ebook/zh/03.01.md

[1. 红黑树][1]

[2. AVL树][2]

[3. 红黑树深入剖析及Java实现][3]

[4. 【数据结构和算法05】 红-黑树（看完包懂~）][4]

[5. 红黑树与AVL树，各自的优缺点总结][5]

[6. 教你透彻了解红黑树][6]






