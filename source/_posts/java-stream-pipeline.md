---
title: Java Stream Pipeline
date: 2019-12-08 20:13:30
updated: 2019-12-08 20:13:30
tags:
- stream pipeline
categories:
- Java基础
---
## 1. 概述
> Java 8中的Stream是对集合（Collection）对象功能的增强，它专注于对集合对象进行各种非常便利、高效的聚合操作（Aggregate operation），或者大批量数据操作(Bulk data operation)。Stream API借助于同样新出现的Lambda表达式，极大的提高编程效率和程序可读性。同时它提供串行和并行两种模式进行汇聚操作，并发模式能够充分利用多核处理器的优势，使用fork/join并行方式来拆分任务和加速处理过程<sup>1</sup>。

<!-- more -->

这篇文章重点分析Stream背后的数据结构及执行流程，以下面代码为例：
```java
List<Integer> list = Arrays.asList(1, 5, 2, 4, 8, 6, 7, 8, 9, 10);
int sum = list.stream().filter(x -> x % 2 == 0).sorted(Comparator.reverseOrder()).map(x -> x * x).reduce((x, y) -> x + y).get();
```
在这段执行代码之后，将会生成以下的数据结构：

![java-stream-pipeline](/images/java-stream-pipeline.jpg "java-stream-pipeline")
 
 - 操作的定义：对数据的一次处理，如过滤(filter)，排序(sorted)，映射(map)及规约（reduce）等等。操作有三种类型：1)Head，头结点，没有实际操作，包含了数据源；2)ReferencePipeline，中间操作，代表了一次数据处理；3)TerminalOp，结束操作，代表处理的结束。
 - ReferencePipeline对象代表了一次中间操作，描述了操作的静态信息，Stream执行的一次中间操作之后都会生成一个ReferencePipeline对象(StatelessOp及StatefulOp)，这些对象在最终操作（reduce）之前会形成一个双向链表，此时只是建立操作的前后关系，还未执行真正的操作。
 - Sink对象代表了真正的所要执行的操作，执行terminal操作(如reduce)之后，将会从后往前生成一个"操作序列"，如上图所示的wrapedSink对象。每一个ReferencePipeline对象对应一个Sink对象，代表了ReferencePipeline所要执行的操作，前一个Sink对象会持有下一个操作的Sink对象，形成一个单向链表。
 - Sink对象有四个基本方法：1）begin()，操作的开始；2）end()，代表操作结束；3）accept(E e)，真正的操作,如filter,sorted,map及reduce等数据处理；4）cancellationRequested，是否取消操作，用于断路操作，如anyMatch表示找到第一个匹配的对象，后面的数据不用再执行，直接退出；Sink对象根据需要实现这四个方法，来满足不同的数据处理需求。
 - ReferencePipeline对象有两种不同的类型：StatelessOp（无状态操作）和StatefulOp（有状态操作），这两种类型的区别就在于数据元素之间是否有依赖，如排序(sotred)操作，是一个有状态操作，需要知道所有数据元素才能进行排序，它会临时生成一个列表存放所有的数据，排序之后，重新迭代处理后面的操作，而对于无状态操作，前一个数据元素的操作与后一个数据元素操作没有关系，可以直接将多个无状态操作合并起来，即前一个操作结束之后，可将操作结果直接传给下一个操作（downstream）,在一次迭代中将所有操作执行完毕，这就是Stream处理数据高效的原因。相对而言，有状态操作会存储临时结果，重起一次迭代，而无状态操作一次迭代即可完成所有操作，如上图所示，因为有sorted操作，所有的数据处理需要两次迭代完成。
 - 上图中的执行流程是一个没有短路操作（后面会讲短路操作的流程）的流程，可以看到，主要分为三个步骤：1）执行begin()，进行初始化操作；2）执行accept()，数据处理；3）执行end()操作，进行数据收尾操作，这三个操作会递归调用，直到碰到有状态操作或结束操作才结束，如果碰到的是有状态操作，如sorted，前一个迭代的end操作将会触发下一个迭代的开始。

在文章开始前，先讲述下几个重要概念：
1、Stream
> A sequence of elements supporting sequential and parallel aggregate operations.  The following example illustrates an aggregate operation using 
>```java
int sum = widgets.stream()
                   .filter(w -> w.getColor() == RED)
                   .mapToInt(w -> w.getWeight())
                   .sum();
```


2、AbstractPipeline
>Abstract base class for "pipeline" classes, which are the core implementations of the Stream interface and its primitive specializations. Manages construction and evaluation of stream pipelines.
>An AbstractPipelinere presents an initial portion of a stream pipeline, encapsulating a stream source and zero or more intermediate operations. The individual AbstractPipeline objects are often referred to as stages, where each stage describes either the stream source or an intermediate operation.

3、Sink
>An extension of Consumer used to conduct values through the stages of a stream pipeline, with additional methods to manage size information, control flow, etc.  Before calling the  accept() method on a code Sink for the first time, you must first call the  begin() method to inform it that data is coming (optionally informing the sink how much data is coming), and after all data has been sent, you must call the end() method.  After calling end(), you should not call accept() without again calling begin(). Sink also offers a mechanism by which the sink can cooperatively signal that it does not wish to receive any more data (the cancellationRequested() method), which a source can poll before sending more data to the Sink.

## 2. AbstractPipeline

在Stream中执行的一个数据处理都对应一个操作，最终以双向链表的形式组织起来，而操作的类型分为三种：1）head头结点；2）ReferencePipeline，中间操作；3）TerminalOp，结束操作，实际上head头结点也是ReferencePipeline类型，只是它有点特殊，它没有实际的操作，所以单独把它拿出来。ReferencePipeline中间操作分为两种操作：1）有状态操作(StatefulOp)；2）无状态操作（StatelessOp）,两者的操作在上面内容已经讲述过，在这里不再赘述。TerminalOp结束操作也分为两种操作：1）非短路操作；2）短路操作，这两者之间的区别在短路操作会终止后续的操作，提前返回，关于短路操作在后面的内容重点讲述。这几种分类如下图所示：
<table width="600"><tr><td colspan="3" style="text-align:center"  border="0">Stream操作分类</td></tr><tr><td rowspan="2"  border="1">中间操作(Intermediate operations)</td><td>无状态(Stateless)</td><td>unordered() filter() map() mapToInt() mapToLong() mapToDouble() flatMap() flatMapToInt() flatMapToLong() flatMapToDouble() peek()</td></tr><tr><td>有状态(Stateful)</td><td>distinct() sorted() sorted() limit() skip() </td></tr><tr><td rowspan="2"  border="1">结束操作(Terminal operations)</td><td>非短路操作</td><td>forEach() forEachOrdered() toArray() reduce() collect() max() min() count()</td></tr><tr><td>短路操作(short-circuiting)</td><td>anyMatch() allMatch() noneMatch() findFirst() findAny()</td></tr></table>

中间操作的类图如下所示：
![ReferencePipeline](/images/ReferencePipeline.jpg "ReferencePipeline")
Head,Stateful及StatelessOp都继承自ReferencePipeline类，Head相对其它两种类型，没有实际的操作，只是包含了一个数据源。另外，这三个类也实现了Stream接口，每一个操作都可以继续调用下一个操作，实现链式调用。
ReferencePipeline类，有两个比较重要的作用：1）将中间操作以双向链表的形式组织起来，方便后面构建"操作序列"（Sink对象链）；2）构建当前操作的Sink对象，该对象是包含了真正的处理流程。以map方法为例介绍这两个作用：
```java
public final <R> Stream<R> map(Function<? super P_OUT, ? extends R> mapper) {
    Objects.requireNonNull(mapper);
	
    return new StatelessOp<P_OUT, R>(this, StreamShape.REFERENCE,
                                 StreamOpFlag.NOT_SORTED | StreamOpFlag.NOT_DISTINCT) {
        @Override
        Sink<P_OUT> opWrapSink(int flags, Sink<R> sink) {
            return new Sink.ChainedReference<P_OUT, R>(sink) {
                @Override
                public void accept(P_OUT u) {
                    downstream.accept(mapper.apply(u));
                }
            };
        }
    };
}
```
在map方法调用中，会生成一个StatelessOp对象，在构造函数中将当前的Pipeline对象（this对象）作为参数传递给新生成的对象，该StatelessOp对象继承了AbstractPipeline抽象类，在AbstractPipeline类中通过nextStage、previousStage两个字段将前后两个操作建立起前后的关联关系，代码如下图所示：
```java
/**
 * @param previousStage 前一个阶段的操作,就是构建函数中传入的this对象
 * @param opFlags the operation flags for the new stage 操作的标志
*/
AbstractPipeline(AbstractPipeline<?, E_IN, ?> previousStage, int opFlags) {
    if (previousStage.linkedOrConsumed)
        throw new IllegalStateException(MSG_STREAM_LINKED);
    previousStage.linkedOrConsumed = true;
    // 上一个阶段(前一个操作)的nextStage指向当前的StatelessOp对象
    previousStage.nextStage = this;
    
    // 当前对象的previousStage指向上一个阶段的对象(前一个操作)
    this.previousStage = previousStage;
    this.sourceOrOpFlags = opFlags & StreamOpFlag.OP_MASK;
    this.combinedFlags = StreamOpFlag.combineOpFlags(opFlags, previousStage.combinedFlags);
    this.sourceStage = previousStage.sourceStage;
    if (opIsStateful())
        sourceStage.sourceAnyStateful = true;
    this.depth = previousStage.depth + 1;
}
```

另外，在StatelessOp对象的opWrapSink方法中，构建了一个Sink.ChainedReference对象，该对象包含了map的处理逻辑。这个方法相对比较简单，数据用mapper方法处理完之后，将结果传递给下个操作(downstream)处理，其中mapper对应是Lamdba表达式：x -> x * x。

TerminalOp终止操作的类图如下所示：
![TerminalOp](/images/TerminalOp.jpg "TerminalOp")
TerminalOp有四种类型，分别是：1）ForEachOp；2）FindOp；3）MatchOp；4）ReduceOp。表格中提到的所有终止操作都是基于这四种类型来实现的，另外终止类型的操作并没有加入到由ReferencePipeline组成的双向链表中。
最后的终止操作是通过调用诸如forEach(), reduce(), collect(), anyMatch()等这些方法来触发的，这些方法最终会调用ReferencePipeline类中的evaluate()方法来完成操作，在evaluate()方法，生成一个TerminalOp对象，且封装了一个统一的处理流程，现在来看下这个evaluate()方法，其流程如下：
![stream-evaluate](/images/stream-evaluate.jpg "stream-evaluate")

- 根据不同的终止操作生成不同的TerminalOp对象，可以是上面四种类型中的任意一种；
- 构建数据源Spliterator；
- 执行evaluate()方法的中间操作ReferencePipeline对象合并TerminalOp对象的操作标志位，如是否短路操作等等；
- 判断执行的模式，并发模式暂不分析，我们主要分析Sequential模式；
- 从TerminalOp对象中构建TerminalSink对象；
- 从后往前遍历中间操作（ReferencePipeline）对象，构建每一个中间操作对应的Sink对象，并将这些Sink对象从前往后生成链表，TerminalSink对象在链尾；
- 根据操作标志位判来触发真正的动作，如短路操作，或者非短路操作，该部分内容在后面讲述；

在这里重点看一个步骤：包装Sink对象。
```java
/**
 * @param sink TerminalSink对象,链尾对象
 * @return 链首Sink对象
*/
final <P_IN> Sink<P_IN> wrapSink(Sink<E_OUT> sink) {
    Objects.requireNonNull(sink);

	// 遍历所有的中间操作
    for ( @SuppressWarnings("rawtypes") AbstractPipeline p=AbstractPipeline.this; p.depth > 0; p=p.previousStage) {
        sink = p.opWrapSink(p.previousStage.combinedFlags, sink);
    }
    return (Sink<P_IN>) sink;
}
```
通过wrapSink方法，从后往前遍历所有的AbstractPipeline对象，生成每个操作对应的Sink对象，并将后一个Sink对象作为参数传入，赋值给dowonstream字段，从而将所有的Sink对象串连起来，通过链首的Sink对象访问所有的Sink对象。

## 3. Sink
Sink对象是扩展自Comsumer接口，主要用来处理数据，除了Comsumer接口的accept()方法，还增加了三个方法：begin(),end()及cancellationRequested()。在调用accept()方法之前，先调用begin(int size)方法，告之数据源的大小，调用accept()方法之后，再调用end()方法，通知数据处理已经结束，如果有短路操作（中止后续数据的处理），必须先调用cancellationRequested()方法，这两种处理模式如下所示：
```java
// 非短路操作
if (!StreamOpFlag.SHORT_CIRCUIT.isKnown(getStreamAndOpFlags())) {
    // 1、调用begin()方法，告之数据源大小；
    wrappedSink.begin(spliterator.getExactSizeIfKnown());
    // 2、遍历数据源元素，调用wrappedSink.accept()方法处理数据；
    spliterator.forEachRemaining(wrappedSink);
    // 3、处理完数据之后，调用end()方法
    wrappedSink.end();
	
} else {  // 短路操作
    // 调用begin()方法，告之数据源大小；
    wrappedSink.begin(spliterator.getExactSizeIfKnown());
    // 2、遍历数据源元素，调用wrappedSink.accept()方法处理数据，
    // 如果上一个元素设置了“短路”标志，说明数据已经完毕，则退出遍历；
    do {
    } while (!wrappedSink.cancellationRequested() && spliterator.tryAdvance(wrappedSink));
    // 3、处理完数据之后，调用end()方法
    wrappedSink.end();
}
```
从上面的代码可以看出，所有的操作都是在一次遍历中完成的，对数据的处理操作已经按照书写顺序串连起来，即Sink对象链表，数据源中的每一个元素依次传递给Sink对象，被Sink对象的accept()方法处理，如果是短路操作，则需要设置"短路"标志，在处理下一个数据元素时，调用cancellationRequested()方法便可知道数据已经处理完毕，退出遍历返回即可。这里有两个问题，1）“短路”标志是如何设置的？2）数据的处理是否只需要一次遍历？
1) “短路”标志设置
在两个地方需要判断“短路”标志，一个是根据“短路”标志，是否执行“短路”操作，另外一个是在遍历数据源的过程中，判断数据处理是否已经被取消，需要中止操作，以anyMatch()方法为例。
![short_circuit-1](/images/short_circuit-1.jpg "short_circuit-1")
如上图所示，判断“短路”的逻辑如下：
- 在短路操作的TerminalOp对象中设置短路的标志位；
```java
// MatchOp.getOpFlags()
public int getOpFlags() {
    return StreamOpFlag.IS_SHORT_CIRCUIT | StreamOpFlag.NOT_ORDERED;
}
```
- 将TerminalOp对象中短路标志位合并到最后一个ReferencePipeline对象的combinedFlags中；
```java
// AbstractPipeline.sourceSpliterator()
if (terminalFlags != 0)  {
    // Apply flags from the terminal operation to last pipeline stage
    combinedFlags = StreamOpFlag.combineOpFlags(terminalFlags, combinedFlags);
}
```
- 根据combinedFlags判断是否执行短路操作；
```java
// AbstractPipeline.copyInto()
if (!StreamOpFlag.SHORT_CIRCUIT.isKnown(getStreamAndOpFlags())) {
    wrappedSink.begin(spliterator.getExactSizeIfKnown());
    spliterator.forEachRemaining(wrappedSink);
    wrappedSink.end();
}
else {
    copyIntoWithCancel(wrappedSink, spliterator);
}
```

中止操作的逻辑如下：
![short_circuit-2](/images/short_circuit-2.jpg "short_circuit-2")
在MatchSink中一个stop的字段，如果找到匹配的数据，则设置stop=true，在进行下一个数据匹配之前递归调用cancellationRequested()，取得stop的值，从而中止操作。
- 找到匹配的数据并设置stop；
```java
// MatchSink.accept()
public void accept(T t) {
	// 条件匹配
    if (!stop && predicate.test(t) == matchKind.stopOnPredicateMatches) {
        stop = true; // 设置stop
        value = matchKind.shortCircuitResult;
    }
}
```

- 对下一个数据元素进行数据处理前递归调用cancellationRequested()方法，调用到TerminalSink，结束调用。
```java
// ReferencePipeline.forEachWithCancel()
final void forEachWithCancel(Spliterator<P_OUT> spliterator, Sink<P_OUT> sink) {
    // 处理下一个数据之前调用cancellationRequested()方法
    do { } while (!sink.cancellationRequested() && spliterator.tryAdvance(sink));
}

// ChainedReference.cancellationRequested()
public boolean cancellationRequested() {
    // 递归调用一个Sink的cancellationRequested()方法
    return downstream.cancellationRequested();
}

// BooleanTerminalSink.cancellationRequested
// 调用到TerminalSink，结束调用
public boolean cancellationRequested() {
    return stop;
}
```

2）遍历次数
中间操作ReferencePipeline对象分为两种类型：1）无状态操作StatelessOp；2）有状态操作StatefulOp。这两种操作的区别在于：在无状态操作StatelessOp中数据元素没有依赖关系，每一个数据元素可以独立处理，而有状态操作StatefulOp中数据元素的处理依赖其它元素，每一个元素不能独立处理，以filter()和sorted()两个方法为例。
```java
// ReferencePipeline.filter()
public final Stream<P_OUT> filter(Predicate<? super P_OUT> predicate) {
    Objects.requireNonNull(predicate);
    return new StatelessOp<P_OUT, P_OUT>(this, StreamShape.REFERENCE,
                                 StreamOpFlag.NOT_SIZED) {

        @Override
        Sink<P_OUT> opWrapSink(int flags, Sink<P_OUT> sink) {
            return new Sink.ChainedReference<P_OUT, P_OUT>(sink) {
                @Override
                public void begin(long size) {
                    downstream.begin(-1);
                }

                @Override
                public void accept(P_OUT u) {
					// 如果满足过滤条件，则传递给下一个Sink处理
                    if (predicate.test(u))
                        downstream.accept(u);
                }
            };
        }
    };
}
```
在StatelessOp操作中，经过本阶段的Sink处理完毕之后，会将数据元素继续传递给下一个Sink对象处理。

```java
// sorted()方法对应的Sink对象
private static final class RefSortingSink<T> extends AbstractRefSortingSink<T> {
    // 1. 临时生成一个列表对象
    private ArrayList<T> list;

    RefSortingSink(Sink<? super T> sink, Comparator<? super T> comparator) {
        super(sink, comparator);
    }

    @Override
    public void begin(long size) {
        if (size >= Nodes.MAX_ARRAY_SIZE)
            throw new IllegalArgumentException(Nodes.BAD_SIZE);
            
        // 2. 列表对象初始化，一般生成不限长度的列表
        list = (size >= 0) ? new ArrayList<T>((int) size) : new ArrayList<T>();
    }

    @Override
    public void end() {
        // 4. 进行排序操作
        list.sort(comparator);
	
        // 5. 重新遍历数据列表，处理后续的操作
        downstream.begin(list.size()); // 通知数据处理开始
        // 6. 判断是否进行“短路”操作
        if (!cancellationWasRequested) {
            // 7. 执行非短路操作
            list.forEach(downstream::accept);
        }
        else {
            // 8. 执行短路操作
            for (T t : list) {
                if (downstream.cancellationRequested()) break;
                downstream.accept(t);
            }
        }
        
        // 9. 通知数据处理结束
        downstream.end();
        list = null;
    }

    @Override
    public void accept(T t) {
        // 3. 将数据元素添加到列表中
        list.add(t);
    }
}
```
对于排序操作而言，需要知道所有的元素才能进行，所以它临时生成了一个新的列表对象，存储完所有的数据元素之后，再进行排序操作。最后遍历列表对象，重新执行短路/非短路操作，完成剩余的操作。

总上所述，在操作序列中只有无状态操作的话，只要遍历一次即可执行完所有操作，如果包含有状态操作，则每一个有状态操作者需要增加一次遍历。

## 4. 总结
通过上面的分析，Stream的实现有以下三个特点：1）通过链表的方式将操作序列串连起来，数据元素在这个链表中依次流动（传递），可以有效减少数据遍历的次数；2）定义了一套“协议”，规范了前后两个不同操作之间的交互方式，遵循了这套协议，不同操作可按不同顺序组合，完成不同的功能；3）借助Fork/Join框架，数据源可并发执行数据处理，显著提高数据处理的效率。

**参考：**

----
[1]:https://www.ibm.com/developerworks/cn/java/j-lo-java8streamapi/index.html
[2]:https://www.cnblogs.com/CarpenterLee/p/6637118.html


[1. Java 8 中的 Streams API 详解][1]

[2. 深入理解Java Stream流水线][2]
