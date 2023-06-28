---
title: 垃圾回收之指针判定及堆的遍历
date: 2020-08-09 11:03:19
updated: 2020-08-09 11:03:19
tags:
- 指定判定
- 堆的遍历
categories: 
- Java基础
---

 在 [垃圾回收之回收算法](https://noahsarkzhang-ts.github.io/2020/07/19/garbage-collecton/) 这篇文章中预设了两个前提：
 1. 根集合及对象中的指针集合已经得到；
 2. 堆是可遍历的，即从一个对象可直接定位到下一个对象；


 为了描述的方便，在上篇文章中直接得出了结论，而这篇文章的目的就是解释这两个问题。

 <!-- more -->

 ## 1. 指针的判定
从位置上来说，可以初步将指针分为两类：1）根上指针，主要包括寄存器、线程栈及全局变量上的指针；2）堆内指针，主要是指堆中对象内指向其它对象的指针，正常来说，根上指针需要运行时才能确定，而堆内指针对于静态类型的语言来说在编译时就可以确定。两者的关系如下图所示：
![pointer](/images/gc/pointer.jpg "pointer")

识别出堆上或根上的数据是否是指针，是垃圾回收的前提，根据识别的程度，可以将垃圾回收分为三类：
1. 准确式 GC (precise GC) ：能够识别根上指针和堆内指针，明确数据是否是指针类型；
2. 半保守式 GC ：也叫根上保守，它能识别堆内指针，但不能识别根上指针；
3. 保守式GC（conservative GC）: 不能完全识别指针类型，它根据一些规则来排除不是指针，这些规则包含上下边界检查（GC堆的上下界是已知的）、对齐检查（通常分配空间的时候会有对齐要求，假如说是4字节对齐，那么不能被4整除的数字就肯定不是指针）。

### 1.1 堆内指针的判定
要识别出堆内的指针，一般要求对象上记录对象的类型信息，在扫描堆的时候，可以根据类型信息，来判断对象中的数据是否是指针类型。如果是JVM的话，这些数据可能在类加载器或者对象模型的模块里计算得到，不需要编译器的支持。

### 1.2 根上指针的判定
根上的数据，如寄存器和线程栈，是运行时产生的数据，与堆内指针的判定方法不一样，以 JVM 为例，一般有以下几个方法：
1. 让数据自身带上标记（tag）；
2. 让编译器为每个方法生成特别的扫描代码；
3. 从外部记录下类型信息，存成映射表。现在三种主流的高性能 JVM 实现，HotSpot、JRockit 和 J9 都是这样做的。其中，HotSpot把这样的数据结构叫做OopMap，JRockit 里叫做livemap，J9 里叫做GC map。Apache Harmony的 DRLVM 也把它叫 GCMap。

JVM 中指令的执行会影响寄存器和线程栈中的数据，要实现映射表，需要 JVM 的解释器和 JIT 编译器都有相应的支持，由它们来生成足够的元数据（类型）提供给垃圾回收器。在HotSpot中，如果 JVM 以解释的方式运行代码，映射表（OopMap）可以由解释器来收集；如果使用 JIT 编译器编译后的代码，则需要在一些关键点插入代码来记录映射表（OopMap）。这些关键点也叫做“安全点”（safepoint），之所以要选择一些特定的位置来记录OopMap，是因为如果对每条指令（的位置）都记录 OopMap 的话，这些记录就会比较大，那么空间开销会显得不值得。选用一些比较关键的点来记录就能有效的缩小记录的数据量，这些关键点包括：

1. 循环的末尾；
2. 方法临返回前 / 调用方法的call指令后；
3. 可能抛异常的位置。

所以说，垃圾回收不是在任意位置都可以进入，只能在 safepoint 处进入。

平时这些 OopMap 都是压缩存在内存里，在垃圾回收的时候才按需解压出来使用，一般有两种使用方式：
1. 每次都遍历原始的OopMap，循环的一个个偏移量扫描过去；这种用法也叫“解释式”；
2. 为每个 OopMap生成一块定制的扫描代码，以后每次要用 OopMap 就直接执行生成的扫描代码；这种用法也叫“编译式”。

HotSpot 是用“解释式”的方式来使用 OopMap 的，每次都循环变量里面的项来扫描对应的偏移量。

### 1.3 OopMap

在 HotSpot 中，对象的类型信息里有记录自己的 OopMap，记录了在该类型的对象内什么偏移量上是什么类型的数据。所以从对象开始向外的扫描可以是准确的，这些数据是在类加载过程中计算得到的。另外，在“安全点”中记录了根上数据类型及偏移量，保证了根上的数据类型也是准确的，通过这两种方法，HotSpot 实现了准确式 GC 。现在我们来看下，在 JVM 中 OopMap 相关的信息。

> Oop maps are bit maps specifying which stack and register locations hold oops for a given pc. During GC, these locations need to be visited since they represent roots for GC. Also, if GC moves objects, pointers must be updated.

#### 1.3.1 根集合上关联的OopMap

如果 JVM 使用翻译器，则在翻译器中收集 OopMap 中，如果使用 JIT 编译器，则在指定位置插入特定的代码收集 OopMap，我们以下面的代码为例，反汇编代码，分析 OopMap相关的结构。

```java
public class DisAssemblyTest {

    public void invoke() {
        String name = "test";
        String newName = name.intern();
        System.out.println(name == newName);
    }

    public static void main(String[] args) {
        new DisAssemblyTest().invoke();
    }
}
```

使用如下参数，运行代码：
```
-XX:+UnlockDiagnosticVMOptions -XX:+PrintAssembly -Xcomp 
-XX:CompileCommand=dontinline,*DisAssemblyTest.invoke 
-XX:CompileCommand=compileonly,*DisAssemblyTest.invoke
```

反汇编的代码如下：
```asm
[Entry Point]
[Constants]
  # {method} {0x0000000057252b68} 'invoke' '()V' in 'org/noahsrak/jvm/DisAssemblyTest'
  #           [sp+0x40]  (sp of caller)
  0x000000000296baa0: mov    0x8(%rdx),%r10d
  0x000000000296baa4: cmp    %rax,%r10
  ...
[Verified Entry Point]
  0x000000000296bac0: mov    %eax,-0x6000(%rsp)
  ...
  0x000000000296bb9f: callq  0x00000000028a61a0  ; OopMap{[32]=Oop off=260}
                                                ;*invokevirtual intern
                                                ; - org.noahsrak.jvm.DisAssemblyTest::invoke@4 (line 12)
                                                ;   {optimized virtual_call}
  0x000000000296bba4: nopl   0x0(%rax)
  0x000000000296bba8: jmpq   0x000000000296bd3c  ;   {no_reloc}
  0x000000000296bbad: add    %al,(%rax)
  0x000000000296bbaf: add    %al,(%rax)
  0x000000000296bbb1: add    %ah,0xf(%rsi)
  ...
  0x000000000296bcb5: movabs $0xffffffffffffffff,%rax
  0x000000000296bcbf: callq  0x00000000028a63e0  ; OopMap{off=548}
                                                ;*invokevirtual println
                                                ; - org.noahsrak.jvm.DisAssemblyTest::invoke@21 (line 13)
                                                ;   {virtual_call}
  0x000000000296bcc4: add    $0x30,%rsp
  0x000000000296bcc8: pop    %rbp
  0x000000000296bcc9: test   %eax,-0x253bbcf(%rip)        # 0x0000000000430100
                                                ;   {poll_return}
  0x000000000296bccf: retq   
  0x000000000296bcd0: mov    %rsi,0x8(%rsp)
  0x000000000296bcd5: movq   $0xffffffffffffffff,(%rsp)
  0x000000000296bcdd: callq  0x000000000296a460  ; OopMap{rdx=Oop off=578}
                                                ;*synchronization entry
                                                ; - org.noahsrak.jvm.DisAssemblyTest::invoke@-1 (line 11)
                                                ;   {runtime_call}
  0x000000000296bce2: jmpq   0x000000000296bafb
  0x000000000296bce7: movabs $0x0,%r8           ;   {oop(NULL)}
  ...
```

这段输出含有一条callq指令，用来实现对intern()方法的调用：
```java
OopMap{[32]=Oop off=260}
```
它的含义是：有一个OopMap与这条callq指令之后的一条指令（nopl）关联在一起，该指令位置上有一个活跃的引用，在离栈顶偏移量为32的位置上。

OopMap记录输出的日志的构成是：
```java
OopMap{零到多个“数据位置=内容类型”的记录 off=该OopMap关联的指令的位置}  
```
在这个例子中，\[32\]表示栈顶指针+偏移量0，这里就是\[rsp + 32\]，也就是栈顶偏移量为32的位置；右边的"=Oop"说明这个位置存着一个普通对象指针（ordinary object pointer，HotSpot 将指向GC堆中对象开头位置的指针称为Oop）

off=260 就是这个 OopMap 记录关联的指令在方法的指令流中的偏移量，这个数字是十进制的。可以看到，该方法的指令流是从地址0x000000000296baa0开始的；十进制的260就是十六进制的0x104；`0x000000000296baa0 + 0x104 = 0x000000000296bba4`，正好就是例子中callq指令后的`nopl   0x0(%rax)`所在的位置。

#### 1.3.2 对象上关联的OopMap
除了在根集合上收集 OopMap，在对象上也会关联 OopMap，用来描述对象中字段的引用信息，对象中的 OopMap 存放在对象的类信息中，在类进行加载的时候进行初始化。分析 OopMap 之前，我们先了解下 java 中对象与类的关系。
![klass](/images/gc/klass.png "klass")

HotSpot中采用了 OOP-Klass 模型来描述 Java 对象与类的关系：
1. OOP 或 OOPS （Ordinary Object Pointer）指的是普通对象指针，主要职能是表示对象的实例数据，存储在堆里面；
2. Klass 用来描述对象实例的具体类型，实现语言层面的 Java 的 Class 对象，在 JVM 中用 Klass 表示，存储在元空间（方法区）。

在 Java 中，每创建一个 Java 对象，在 JVM 内部也会相应创建一个 OOP 对象来表示 Java 对象。OOP类的共同基类型是oopDesc，它有多个子类，instanceOopDesc 表示对象，arrayOopDesc 表示数组。

其中，instanceOopDesc 和 arrayOopDesc 又称为对象头，instanceOopDesc 对象头包括以下两部分信息：Mark Word 和 元数据指针(Klass*)：
1. Mark Word，主要存储对象运行时记录信息，如hashcode、GC分代年龄、锁状态标志、线程持有的锁、偏向线程ID、偏向时间戳等;
2. 元数据指针，用来存储 klass 指针，对应的klass 指针指向一个存储类的元数据的 Klass 对象。

instanceOopDesc 用于表示 Java 对象，instanceKlass 用于描述 instanceOopDesc，instanceKlassKlass 用来描述 instanceKlass，为了避免无限描述下去，所以有个klassKlass作为这个描述链上的终结符。

对象中的 OopMap 就是在 Klass 对象中存放，其布局如下所示：
```c++
InstanceKlass layout:
  [C++ vtbl pointer           ] Klass
  [subtype cache              ] Klass
  [instance size              ] Klass
  [java mirror                ] Klass
  [super                      ] Klass
  [access_flags               ] Klass
  [name                       ] Klass
  [first subklass             ] Klass
  [next sibling               ] Klass
  [array klasses              ]
  [methods                    ]
  [local interfaces           ]
  [transitive interfaces      ]
  [fields                     ]
  [constants                  ]
  [class loader               ]
  [source file name           ]
  [inner classes              ]
  [static field size          ]
  [nonstatic field size       ]
  [static oop fields size     ]
  [nonstatic oop maps size    ]
  [has finalize method        ]
  [deoptimization mark bit    ]
  [initialization state       ]
  [initializing thread        ]
  [Java vtable length         ]
  [oop map cache (stack maps) ]
  [EMBEDDED Java vtable             ] size in words = vtable_len
  [EMBEDDED nonstatic oop-map blocks] size in words = nonstatic_oop_map_size
    The embedded nonstatic oop-map blocks are short pairs (offset, length)
    indicating where oops are located in instances of this klass.
  [EMBEDDED implementor of the interface] only exist for interface
  [EMBEDDED host klass        ] only exist for an anonymous class (JSR 292 enabled)
```

在上面的布局中可以看到有一个 oop map cache 的字段，猜测就是用来存放 OopMap相关的信息。

#### 1.3.3 小结
用一句话来描述，OopMap 存放了堆、栈及寄存器上指针信息，借助 OopMap 不仅可以准确判定一个数值是否是指针，同时直接扫描 OopMap 集合可以加快标记的速度，从而提高垃圾回收的效率。

## 2. 堆的遍历

### 2.1 内存分配
在垃圾回收算法中，需要对堆进行清除及整理操作，这时候就需要对堆从头到尾进行遍历，遍历的方式跟内存的分配方式极为相关，我们先介绍内存的分配方式。内存的分配方式有两种基本的分配策略：1）顺序分配；2）空闲链表分配。

1. 顺序分配
顺序分配使用一个较大的空闲内存块，从一端根据大小顺序分配，它的数据结构比较简单，只需要一个空闲指针（free pointer）和一个界限指针（limit pointer）。根据分配的内存块大小，只要简单移动空闲指针即可。如果存在字节对齐要求，则可能需要额外增加填充字节，分配的逻辑如下图所示：
![sequence-allocation](/images/gc/sequence-allocation.jpg "sequence-allocation")
顺序分配的特点是简单、高效，适用于大块内存及内存比较规整的情况下，可以在复制回收及标记整理算法中使用。使用顺序分配的堆中，要实现堆的遍历，每一个分配的内存块需要包含一个头部，描述内存块的信息，如块的大小等等。

2. 空闲链表分配
空闲链表使用某种数据结构来记录空闲内存单元（free cell）的位置和大小，该数据结构将所有的空闲内存块串联起来进行统一分配。严格来讲，空闲内存单元的组织方式不一定是链表，也可以采用其它形式。下面是使用双向空闲链表的结构：
![linklist-allocation](/images/gc/linklist-allocation.jpg "linklist-allocation")
内存块中都会有一个头部，表明块的大小及是否已分配。另外在每一个空闲块中，都会包含一个pred（前驱）和succ（后继）指针，从而可以对空闲块进行双向遍历。
在需要分配内存时，分配器顺序检测每一个空闲内存单元，依照某种策略选择一个并从中进行分配。其算法实现通常是顺序扫描所有空闲内存单元，直到发现第一个符合条件的内存单元为止，因而也叫做顺序适应分配。典型的算法包括首次适应（first-fit）、循环首次适配（next-fit）、最佳适应（best-fit）。
**1) 首次适应分配**
对于一次内存分配请求，首次适应分配器将在所发现的第一个满足分配要求的内存单元中进行分配。如果该内存单元的空间大于所需的空间，则会进行分裂操作，将剩余的空间归还到空闲链表中。
**2) 循环首次适应分配**
循环首次适应分配是首次适应分配算法的一个变种。在分配内存时，该算法不是每次都从空闲链表头部开始查找，而是从上次成功分配的位置开始。该算法可以有效避免对空闲链表前端较小空间内存单元的遍历。
**3) 最佳适应分配**
最佳适应分配是指在空闲链表中找到满足分配要求且空间最小的空闲内存单元，其目的在于减少空间浪费，同时避免不必要的内存单元分裂。

使用空闲链表分配的堆内存，进行堆的遍历相对比较容易，根据内存单元的头部信息可以快速定位到下一个内存单元。

### 2.2 JVM内存分配
#### 2.2.1 Java对象布局
在分析 JVM 内存分配之前，先要理解一个 Java 对象在内存中的布局，Java 对象的布局如下所示：
![object-layout](/images/gc/object-layout.jpg "object-layout")
一个Java对象在内存中包括对象头、实例数据和对齐填充3个部分：
1、对象头
Mark Word：用于存储对象自身的运行时数据，如哈希码、GC分代年龄、锁状态标志、线程持有的锁、偏向线程ID、偏向时间戳等，在32位系统占4字节，在64位系统中占8字节；
klass：用来指向对象对应的 Klass 对象（其对应的元数据对象）的内存地址，在32位系统占4字节，在64位系统中占8字节；
Length：如果是数组对象，还有一个保存数组长度的空间，占4个字节；
2、实例数据
存储对象各字段的内容。
3、对齐填充
HotSpot 要求对象起始地址必须是8字节的整数，即对象的大小必须是8字节的整数倍。当对象实例数据部分没有对齐时，就需要通过对齐填充来补全。

Klass指针指向的元数据对象就是我们上节讲到的InstanceKlass，它存有对象描述信息及OopMap，在垃圾回收算法中起到比较关键的作用。

#### 2.2.2 内存分配
在 JVM 中要分配一个对象，有两种分配方式：1）指针碰撞；2）空闲列表。这两种方式跟我们在上面讲的分配方式是类似的，可以认为这两种方式是其具体的实现。
1、指针碰撞
![bump-the-pointer](/images/gc/bump-the-pointer.jpg "bump-the-pointer")

使用该算法，直接根据分配对象的大小，移动空闲指针即可。在对象头中存放了对象元数据对象的指针，可以方便得到对象的大小，进而定位到下一个对象的位置，实现堆的遍历。

2、空闲列表
![free-list-before](/images/gc/free-list-before.jpg "free-list-before")
使用空闲列表算法，已分配的内存块和释放的内存块互相间隔，在遍历堆的时候需要跳过释放的内存块或未分配的内存块，一种可选的做法是用一个“填充对象”覆盖释放的内存块，如下图所示：
![free-list-after](/images/gc/free-list-after.jpg "free-list-after")
当释放一个对象时，回收器使用一个“填充对象”覆盖其空间，而“填充对象”内部包含一个表示自身大小的域（可以当作一个字节数组），清扫器（标记-清扫算法）可以据此快速跳过空闲内存单元并找到下一个真正的对象。

## 3. 总结
在这篇文章里，我们分析了垃圾回收中的两个问题：1）指针的判定；2）堆的遍历。在 JVM 中通过维护 OopMap 解决了指针的判定，同时通过对象对象头记录的元数据，可以方便定位对象的位置，从而解决对象的遍历。

**参考：**

----
[1]:https://www.iteye.com/blog/rednaxelafx-1044951
[2]:https://book.douban.com/subject/26740958/
[3]:https://book.douban.com/subject/26912767/
[4]:https://www.iteye.com/blog/rednaxelafx-730461
[5]:https://blog.csdn.net/jyxmust/article/details/88255594

[1. 找出栈上的指针/引用][1]
[2. 垃圾回收算法手册——自动内存管理的艺术][2]
[3. 深入理解计算机系统][3]
[4. 借助HotSpot SA来一窥PermGen上的对象][4]
[5. 浅谈JVM OOP-Klass二分模型][5]