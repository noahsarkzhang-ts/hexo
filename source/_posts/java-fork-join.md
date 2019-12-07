---
title: Java Fork/Join框架
date: 2019-11-19 14:15:31
tags:
- 数据结构
- 分而治之
- fork/join
categories:
- 并发编程
---
## 1. 概述
ForkJoinPool运用了Fork/Join原理，使用“分而治之”的思想，将大任务分拆成小任务，从而分配给多个线程并行执行，最后合并得到最终结果，加快计算。ForkJoinPool可以充分利用多cpu，多核cpu的优势，提高算法的执行效率，ForkJoinPool整体结构如下图所示：
![fork-join](/images/fork-join.jpg "fork-join")

- ForkJoinPool：框架的主体，存放了工作队列数组，对线程、工作队列及任务进行统一的管理。
- WorkQueue：工作队列，是任务存储的容器，也是实现Work-Stealing的关键数据结构。
- ForkJoinWorkerThread：工作线程，是任务的执行单元。
- ForkJoinTask：封装业务的执行逻辑，包括任务fork及join流程。

## 2. 核心思想
ForkJoinPool的两大核心就是分而治之(Divide and conquer)和工作窃取(Work Stealing)算法，下面先对两种算法作一个介绍，后面将会具体细节做说明，这部分内容来自 [holmofy][3]，作者进行了很好的总结。

### 2.1 分而治之
ForkJoinPool主要思想是：将一个大任务拆分成多个小任务后，使用fork可以将小任务分发给其他线程同时处理，使用join可以将多个线程处理的结果进行汇总。
![devide-conquer](/images/devide-conquer.jpg "devide-conquer")

### 2.2 工作窃取
Fork/Join框架中使用的work stealing灵感来源于Cilk(开发Cilk的公司被Intel收购，原项目后来被升级为Clik Plus)。
> Intel公司除了Clik Plus还有一个TBB(Threading Building Blocks)也是使用work stealing算法实现。

Work Stealing算法是Fork/Join框架的核心思想：
- 每个线程都有自己的一个WorkQueue，该工作队列是一个双端队列；
- 队列支持三个功能push、pop、poll；
- push/pop只能被队列的所有者线程调用，而poll可以被其他线程调用；
- 划分的子任务调用fork时，都会被push到自己的队列中；
- 默认情况下，工作线程从自己的双端队列获出任务并执行；
- 当自己的队列为空时，线程随机从另一个线程的队列末尾调用poll方法窃取任务。
![work-stealing](/images/work-stealing.jpg "work-stealing")

## 3. 数据结构
### 3.1 ForkJoinPool
ForkJoinPool中的几个关键字段如下：
```java
volatile long ctl;                   // main pool control
volatile int runState;               // lockable status
final int config;                    // parallelism, mode
int indexSeed;                       // to generate worker index
volatile WorkQueue[] workQueues;     // main registry
```

#### 3.1.1 ctl字段
ctl有64位，分成4组各16位，代表了不同的状态，在ForkJoinPool中是一个很重要的字段，很多控制逻辑都要根据ctl来完成，如下图所示：
![ctl](/images/ctl.jpg "ctl")
- AC：活跃线程的数量，初始化-parallelism；
- TC：所有线程的数量，初始化-parallelism；
- SS：表示空闲线程栈（Treiber stack）栈顶元素的版本和状态；
- ID：表示空闲线程栈（Treiber stack）栈顶元素在workQueues数组中的下标；

parallelism表示ForkJoinPool的最大线程数，其最大值由MAX_CAP(32767)限定，默认情况下等于cpu的核数（Runtime.getRuntime().availableProcessors()），要改变这个值也可以通过构造函数设置。

为了方便运算，AC和TC初始化parallelism负值，当AC和TC为负数时，表示线程数未达到最大线程数，可以新建线程。SP是ctl的低32位，可通过sp=(int)ctl取到，如果是否零的情况下，表示有空闲线程。

在ForkJoinPool中，线程是绑定在WorkQueue上的，即一个线程必然有绑定WorkQueue（但WorkQueue不一定绑定线程，外部线程提交任务创建的WorkQueue绑定的线程为null）。ID存放的实际是空闲线程对应的WorkQueue在WorkQueue\[\]数组中的下标，后面为了描述的方便，统一说成是空闲线程的下标。下一个空闲线程（其实保存的也是WorkQueue\[\]的下标）保存在WorkQueue的stackPred字段中，讲到WorkQueue时，我们再对空闲线程栈进行深入描述。

ForkJoinPool中定义的常量字段：
```java
// Bounds
static final int SMASK        = 0xffff;        // short bits == max index
static final int MAX_CAP      = 0x7fff;        // max #workers - 1
static final int EVENMASK     = 0xfffe;        // even short bits
static final int SQMASK       = 0x007e;        // max 64 (even) slots

// Masks and units for WorkQueue.scanState and ctl sp subfield
static final int SCANNING     = 1;             // false when running tasks
static final int INACTIVE     = 1 << 31;       // must be negative
static final int SS_SEQ       = 1 << 16;       // version count

// Mode bits for ForkJoinPool.config and WorkQueue.config
static final int MODE_MASK    = 0xffff << 16;  // top half of int
static final int LIFO_QUEUE   = 0;
static final int FIFO_QUEUE   = 1 << 16;
static final int SHARED_QUEUE = 1 << 31;       // must be negative

// Lower and upper word masks
private static final long SP_MASK    = 0xffffffffL;
private static final long UC_MASK    = ~SP_MASK;

// Active counts
private static final int  AC_SHIFT   = 48;
private static final long AC_UNIT    = 0x0001L << AC_SHIFT;
private static final long AC_MASK    = 0xffffL << AC_SHIFT;

// Total counts
private static final int  TC_SHIFT   = 32;
private static final long TC_UNIT    = 0x0001L << TC_SHIFT;
private static final long TC_MASK    = 0xffffL << TC_SHIFT;
private static final long ADD_WORKER = 0x0001L << (TC_SHIFT + 15); // sign 48位是TC的符号位
```

1、ctl的初始化(ForkJoinPool)：AC=TC=-parallelism,SS=ID=0
```java
this.config = (parallelism & SMASK) | mode;
long np = (long)(-parallelism); // offset ctl counts
this.ctl = ((np << AC_SHIFT) & AC_MASK) | ((np << TC_SHIFT) & TC_MASK);
```
假定parallelism值为4，np为-4，16进制为FFFF FFFF FFFF FFFC，np << AC_SHIFT 表示np左移48（AC_SHIFT）位，得到FFFC 0000 0000 0000，再与AC_MASK(0XFFFF 0000 0000 0000)进行&（与）操作，((np << AC_SHIFT) & AC_MASK)得到的值为FFFC 0000 0000 0000，同理，((np << TC_SHIFT) & TC_MASK)，得到的值为0000 FFFC 0000 0000，最后再将这两个值进行|（或）操作，得到的值为FFFC FFFC 0000 0000，即将AC，TC赋值为-4赋值，SS和ID为0。

2、添加线程(tryAddWorker)：AC=TC=+1
```java
long nc = ((AC_MASK & (c + AC_UNIT)) |
           (TC_MASK & (c + TC_UNIT)));
```
添加线程的时候，会将AC和TC都加1，其中c为当前CTL的值，新值为nc。假定c为FFFC FFFC 0000 0000，c + AC_UNIT 可以表示为FFFC FFFC 0000 0000 + 0001 0000 000 000，即在TC部分加1，得到的值为FFFD FFFC 0000 0000，再与AC_MASK(FFFF 0000 0000 0000)进行&(与操作)，(AC_MASK & (c + AC_UNIT))的值为FFFD 0000 0000 0000。同理TC_MASK & (c + TC_UNIT))为0000 FFFD 0000 0000，最后将这个值进行|(或)操作，得到FFFD FFFD 0000 0000。

3、睡眠线程(scan)：AC:-1,ID=new ID
```java
int ss = w.scanState; // w为WorkQueue的变量
int ns = ss | INACTIVE;       // try to inactivate
long nc = ((SP_MASK & ns) |
           (UC_MASK & ((c = ctl) - AC_UNIT)));
w.stackPred = (int)c;         // hold prev stack top
```
ss的值为WorkQueue的scanState，scanState初始值为WorkQueue在WorkQueue\[\]中的下标（如果是外部线程提交任务产生的WorkQueue，scanState为INACTIVE），假定scanState为3，c为FFFD FFFD 0000 0000。ss | INACTIVE(0X8000 0000)等于8000 0011，SP_MASK & ns等于0000 0000 8000 0011，(UC_MASK & ((c = ctl) - AC_UNIT))等于FFFC FFFD 0000 0000，最后nc等于FFFC FFFD 8000 0011，即将空闲线程的下标设置在ID上。

4、唤醒空闲线程(signalWork)：AC:+1,ID=v.stackPred
```java
// 以下代码进行了精简，与signalWork方法中的顺序不一定一致。
long c = ctl;
int sp = (int)c;
int i = sp & SMASK; // 空闲线程的下标
WorkQueue v = ws[i]; // 空闲线程绑定的WorkQueue
long nc = (UC_MASK & (c + AC_UNIT)) | (SP_MASK & v.stackPred);
```
假定c为FFFC FFFD 8000 0011,v.stackPred为5。将c的类型强制转化为int后，sp得到了c低32位的值，即SS与ID。sp与SMASK(0X0000 FFFF)得到低16位的值，即得到下标值(3)。再根据下标i得到对应的WorkQueue v，取到下一个空闲线程的下标(5)，并将这个下标设置到新ctl中的ID中。

c + AC_UNIT表示AC加1,(UC_MASK & (c + AC_UNIT))得到的值为FFFD FFFD 0000 0000，SP_MASK & v.stackPred为0000 0000 0000 0101，最后这两个值进行|(或)操作，nc的值为FFFE FFFF 0000 0101。

#### 3.1.2 config
```java
// 常量
static final int LIFO_QUEUE   = 0;
static final int FIFO_QUEUE   = 1 << 16;

boolean asyncMode = false; // 默认为LIFO
int mode = asyncMode ? FIFO_QUEUE : LIFO_QUEUE,
this.config = (parallelism & SMASK) | mode;
```
config主要是存放两部分信息：1) parallelism,ForkJoinPool线程数；2) ForkJoinPool同步或异步模式，同步用LIFO模式，异步用FIFO，默认为LIFO。parallelism存放在int的低16位，LIFO_QUEUE为0，两者进行|（或）操作，还是parallelism本身。如果模式是FIFO_QUEUE的话，则将int第17位设置为1，假定parallelism为4，最后|（操作）之后，config的值为0X0001 0004。

#### 3.1.3 workQueues
workQueues是ForkJoinPool中非常重要的数据结构，存放多个工作队列WorkQueue，工作队列主要有两种类型：1）外部线程提交一次ForkJoinTask任务，都会生成一个WorkQueue，用来存放提交的的任务（一次可提交多个任务），该队列不属于任何一个线程，会等待其它线程来偷取(Work Stealing)任务，这类WorkQueue存放在workQueues的偶数下标处；2）新增一个工作线程WorkerThread时，都会生成一个WorkQueue，用来存放该线程需要执行的子任务，该WorkQueue绑定在工作线程上，这类WorkQueue存放在workQueues的奇数下标处。

1、workQueues初始化
```java
// create workQueues array with size a power of two
int p = config & SMASK; // ensure at least 2 slots
int n = (p > 1) ? p - 1 : 1;
n |= n >>> 1; n |= n >>> 2;  n |= n >>> 4;
n |= n >>> 8; n |= n >>> 16; n = (n + 1) << 1;
workQueues = new WorkQueue[n];
```
p存放parallelism的值，经过一系列的符号右移及或操作之后，保证n为奇数，最后对n加1，再左移1位，得到一个2的倍数的值，一般情况下workQueues等于parallelism的2倍。

2、提交任务的WorkQueue
```java
// SQMASK常量
static final int SQMASK  = 0x007e;   // max 64 (even) slots

int m = ws.length - 1; // m等于workQueues长度减一，是一个奇数

int k = r & m & SQMASK;
WorkQueue q = new WorkQueue(this, null);
q.hint = r; // r是一个随机值， r = ThreadLocalRandom.getProbe()
q.config = k | SHARED_QUEUE; // k是存放在workqueue[]中的位置
q.scanState = INACTIVE; // 初始化scanState的状态

if (rs > 0 &&  (ws = workQueues) != null &&
    k < ws.length && ws[k] == null)
    ws[k] = q;  // else terminated
```
r是一个随机数，m是数组长度减一，r & m 操作得到一个介于0~m的随机数字。SQMASK是数组的最大值64，其最低位是0，进行与操作，最低位必然是0，从而保证r & m & SQMASK的值是一个介于0~m的随机偶数。k是一个随机数，主要是为了减少插入位置的冲突。

3、工作线程的WorkQueue
```java
WorkQueue w = new WorkQueue(this, wt);
int i = 0;                                    // assign a pool index
int mode = config & MODE_MASK;
int rs = lockRunState();
try {
    WorkQueue[] ws; int n;                    // skip if no array
    if ((ws = workQueues) != null && (n = ws.length) > 0) {
        int s = indexSeed += SEED_INCREMENT;  // unlikely to collide
        int m = n - 1;
        i = ((s << 1) | 1) & m;               // odd-numbered indices
        if (ws[i] != null) {                  // collision
            int probes = 0;                   // step by approx half n
            int step = (n <= 4) ? 2 : ((n >>> 1) & EVENMASK) + 2;
            while (ws[i = (i + step) & m] != null) {
                if (++probes >= n) {
                    workQueues = ws = Arrays.copyOf(ws, n <<= 1);
                    m = n - 1;
                    probes = 0;
                }
            }
        }
        w.hint = s;                           // use as random seed
        w.config = i | mode;
        w.scanState = i;                      // publication fence
        ws[i] = w;
    }
} finally {
    unlockRunState(rs, rs & ~RSLOCK);
}
```
重点看以下代码：
```java
WorkQueue w = new WorkQueue(this, wt);

n = ws.length
int s = indexSeed += SEED_INCREMENT;  // unlikely to collide
int m = n - 1;
i = ((s << 1) | 1) & m;

ws[i] = w;
```
s是一个随机值， ((s << 1) | 1)表达式得到一个随机的奇数，即最低为1。再与m(也是一个奇数)进行&(与)操作，得到一个介于0~m(包括m)的的奇数。从而保证工作线程的WorkQueue存放在workQueues的奇数位置。

#### 3.1.4 indexSeed
```java
/**
* Increment for seed generators. See class ThreadLocal for
* explanation.
*/
private static final int SEED_INCREMENT = 0x9e3779b9;

int s = indexSeed += SEED_INCREMENT;
```
indexSeed主要是用来随机生成WorkQueue的下标。

### 3.2 WorkQueue
WorkQueue是存储ForkJoinTask的容器，也是Work-Stealing依赖的数据结构。外部提交新的ForkJoinTask任务，会新建一个WorkQueue，将任务存放到WorkQueue的ForkJoinTask数组中，最后将该WorkQueue存放到ForkJoinPool对象的workQueues数组中（存放到偶数下标处），新的任务会被工作线程窃取。另外一方面工作线程中产生的子任务会存放到该线程绑定的工作队列中。下面是WorkQueue的一些关键字段。
```java
// Instance fields
volatile int scanState;    // versioned, <0: inactive; odd:scanning
int stackPred;             // pool stack (ctl) predecessor
int nsteals;               // number of steals
int hint;                  // randomization and stealer index hint
int config;                // pool index and mode
volatile int qlock;        // 1: locked, < 0: terminate; else 0
volatile int base;         // index of next slot for poll
int top;                   // index of next slot for push
ForkJoinTask<?>[] array;   // the elements (initially unallocated)
final ForkJoinPool pool;   // the containing pool (may be null)
final ForkJoinWorkerThread owner; // owning thread or null if shared
volatile Thread parker;    // == owner during call to park; else null
volatile ForkJoinTask<?> currentJoin;  // task being joined in awaitJoin
volatile ForkJoinTask<?> currentSteal; // mainly used by helpStealer
```
#### 3.2.1 stackPred
通过ctl的ID字段与stackPred可以形成一个空闲线程列表栈，栈首存放在ID字段中，stackPred存放的是下一个空闲线程的下标，如下图所示：
![idle-thread-list](/images/idle-thread-list.jpg "idle-thread-list")

#### 3.2.2 array,base,top
这三个字段主要是用来存取ForkJoinTask任务的，array是一个ForkJoinTask类型的数组，以双端队列的方式提供服务；base是队列的底部，外部线程窃取任务就是从base开始；top是队列的顶部，工作队列绑定的线程push/pop都是在top上操作。这三个值的初始状态如下图所示：
![workqueue-array-init](/images/workqueue-array-init.jpg "workqueue-array-init")

array的初始大小为8192，最大为64M，base及top默认值为初始大小的一半4096，代码定义如下：

```java
static final int INITIAL_QUEUE_CAPACITY = 1 << 13; // 8192 数组初始大小
static final int MAXIMUM_QUEUE_CAPACITY = 1 << 26; // 64M 数组最大值

base = top = INITIAL_QUEUE_CAPACITY >>> 1; // base及top默认值
```

工作窃取时的队列如下所示:
![workqueue-array](/images/workqueue-array.jpg "workqueue-array")

#### 3.2.2 currentSteal,currentJoin
currentSteal表示当前工作线程从外部工作队列中窃取到的任务，currentJoin表示当前工作线程处在join中的任务，通过这两个参数的配合使用，可以将递归类型的任务分布在多个工作线程执行，同时父级任务线程可以帮子任务或孙子任务线程执行任务，它们的关系如下图所示：
![workqueue-join-steal](/images/workqueue-join-steal.jpg "workqueue-join-steal")

wt1线程当前join的任务就是wt2线程窃取的任务，当wt1线程队列没有任务的时候，它会找到窃取它任务的wt2线程，发现wt2线程的任务队列为空，再去查找窃取wt2线程任务的wt3线程，发现wt3线程队列不为空，则窃取wt3线程工作队列base位置的任务t-1-2-1，并执行它。

### 3.3 ForkJoinWorkerThread
ForkJoinWorkerThread对象继承自Thread对象，是任务执行的实体，继承关系如下图所示：
![ForkJoinWorkerThread](/images/ForkJoinWorkerThread.jpg "ForkJoinWorkerThread")

ForkJoinWorkerThread有内部有两个字段，主要是保存了WorkQueue及ForkJoinPool的引用，定义如下所示：
```java
final ForkJoinPool pool;                // the pool this thread works in
final ForkJoinPool.WorkQueue workQueue; // work-stealing mechanics
```

### 3.4 ForkJoinTask
ForkJoinTask封装了计算的流程，实现了fork及join方法，它是分治算法中两个核心的方法，这两个方法我们在后面的部分详细介绍。ForkJoinTask有两个子类：RecursiveTask和ForkJoinTask，它们的区别主要是计算有没有返回值。这两个子类都提供了一个抽象方法compute，由具体的业务算法来实现，主要包括子任务的划分及结果的合并逻辑，其核心思想如下所示：
```
if(任务很小）{
    直接计算得到结果
}else{
    分拆成N个子任务
    调用子任务的fork()进行计算
    调用子任务的join()合并计算结果
}
```

## 4. 工作流程
### 4.1 提交任务
![invoke-task](/images/invoke-task.jpg "invoke-task")

流程：
1） 提交线程
- 提交线程（不是工作线程）构建ForkJoinTask，提交给ForkJoinPool执行，如通过invoke方法；
- 如果ForkJoinPool中的工作队列数组workQueues没有创建，则创建该数组，默认为parallelism的2倍；
- 创建工作队列q，并将该队列添加到workQueues的偶数下标处；
- 创建工作队列q的任务数组array，默认大小了8192，base和top的初始值为数组大小的一半，即4096；
- 提交线程会走到“激活工作线程”的流程，该流程会在后面的内容讲到。

2）工作线程
- 启动工作线程wt，扫描ForkJoinPool的workQueues数组，窃取一个ForkJoinTask去执行；
- 随机生成一个在数组大小范围内的奇数，作为扫描的起始位置，这样可以避免多个线程同时从一个位置扫描，减少竞争；
- 遍历工作队列workQueues数组，如果工作队列中有任务，则从其base位置处取得任务t，如果该队列中还有其它任务，则“激活工作线程”，让其它工作线程来窃取其它任务；
- 设置工作线程wt的currentSteal（在工作队列中）的值为t，表示工作窃取了任务t；
- 执行任务t；
- 任务执行结束，将currentSteal设置为null；
- 遍历工作队列workQueues数组，如果都没有找到任务，则会将当前工作线程加入到空闲线程列表中，并睡眠当前工作线程等待激活。

### 4.2 fork流程
![fork-flow](/images/fork-flow.jpg "fork-flow")

流程：
- 执行fork的线程可以是外部线程，也可以是工作线程，这两种方式处理方法不一样；
- 判断线程的类型是否ForkJoinWorkerThread；
- 如果是ForkJoinWorkerThread类型，则将任务提交到工作线程的工作队列中，执行“激活工作线程”流程；
- 如果不是ForkJoinWorkerThread类型，则将任务提交到commonForkJoinPool中，与“提交任务”流程是一样的。

#### 4.2.1 激活工作线程
![singal-worker](/images/singal-worker.jpg "singal-worker")

流程：
- 设置工作队列数组为ws,当前工作队列为q；
- 判断当前活跃线程是否小于parallelim，如果已经大于parallelim，则直接退出；
- 再判断是否有空闲线程，有空闲线程则唤醒空闲线程；
- 如果没有空闲线程，同时线程总数小于parallelim，则创建一个新的工作线程wt来执行任务；
- 建立线程相关的工作队列w，建立线程与队列的关联关系，并将工作队列添加到数组ws的奇数下标处；
- 启动wt线程。

### 4.3 join流程
![join-flow](/images/join-flow.jpg "join-flow")

流程：
- 执行join的任务为task，执行join方法的线程为wt，wt的工作队列为w；
- 判断task任务是否已经结束，如果已经结束，直接返回结果即可；
- task没有结束，则判断wt的类型，是否为ForkJoinWorkerThread；
- 如果wt不是ForkJoinWorkerThread类型的线程，则说明是外部线程执行了join方法，则阻塞该线程，等待任务结束后被唤醒；
- 如果wt是ForkJoinWorkerThread类型的线程，则分为三种情况；
- 1）task在w的栈首位置，则直接将task出栈，执行task即可；
- 2）task在w中，但不在栈首位置，处于w的中间位置，则将w中的task转换为空任务（空操作，因为该任务已经被提前执行），执行task；
- 3）task不在w中，表示该任务已经被其它工作线程窃取了，此时如果w的队列为空，则执行“工作窃取流程”，帮助窃取任务的线程，让它更快结束；
- 在一个步骤中，如果w的队列不为空，则睡眠线程wt，在睡眠之前，作为补偿，会创建一个新的工作线程或唤醒一个空闲线程来执行任务。

#### 4.3.1 工作窃取流程
![work-stealing-flow](/images/work-stealing-flow.jpg "work-stealing-flow")

流程：
- 设置task为被窃取的任务，w为当前工作线程的工作队列；
- 遍历工作队列数组，找到窃取task任务的工作线程,其工作队列为v，判断条件为工作线程的v.cureentSteal==task; 
- 判断工作队列v是否为空；
- 如果v不为空，则从工作队列v的base位置窃取任务t，在当前线程w中执行任务t，并设置w.currentSteal=t，直到v为空；
- 如果v为空，则说明任务被其它线程窃取，通过其currentJoin字段找到被窃取的任务，并将该字段设置为task的值，从第一步重新执行，从而帮助儿子任务、孙子任务等等后代任务快速结束。

## 5. 实例
我们通过ForkJoinPool框架实现快速排序算法，来展示将在一个线程中执行的递归算法转化为在多个线程中“分治”执行的算法。维基百科关于快速排序的定义如下：
> 快速排序使用分治法（Divide and conquer）策略来把一个序列（list）分为较小和较大的2个子序列，然后递归地排序两个子序列。
步骤为：
- 挑选基准值：从数列中挑出一个元素，称为“基准”（pivot），
- 分割：重新排序数列，所有比基准值小的元素摆放在基准前面，所有比基准值大的元素摆在基准后面（与基准值相等的数可以到任何一边）。在这个分割结束之后，对基准值的排序就已经完成，
- 递归排序子序列：递归地将小于基准值元素的子序列和大于基准值元素的子序列排序。
递归到最底部的判断条件是数列的大小是零或一，此时该数列显然已经有序。

### 5.1 递归算法

```java
public class RecursiveQuicksort {

    /**
     * 交换数组中两个元素
     * @param array 数组
     * @param left 左边的下标
     * @param right 右边的下标
     */
    private void swap(int[] array, int left, int right) {

        int tmp = array[left];
        array[left] = array[right];
        array[right] = tmp;
    }

    /**
     * 分隔数组为两个子数组
     * @param array 数组
     * @param left 左边的下标
     * @param right 右边的下标
     * @return 分隔的下标
     */
    private int partition(int[] array, int left, int right) {

        // 计算基准的下标
        int index = (left + right) / 2;
        int privot = array[index];

        int i = left;
        int j = right - 1;

        swap(array, index, right);

        while (i < j) {
            while (i <= right && array[i] < privot) {
                i++;
            }

            while ( j >= left && array[j] > privot) {
                j--;
            }

            if (i < j) {
                swap(array, i, j);
                i++;
                j--;
            }
        }

        if (array[i] > array[right]) {
            swap(array, i, right);
        }

        return i;
    }

    /**
     * 快速排序算法
     * @param array 数组
     * @param left 左边的下标
     * @param right 右边的下标
     */
    public void quicksort(int[] array, int left, int right) {
        if (left >= right || array == null || array.length <= 1) {
            return;
        }

        int privot = partition(array, left, right);
        quicksort(array, left, privot - 1);
        quicksort(array, privot + 1, right);
    }

    public static void main(String[] args) {

        int[] array = new int[]{3, 4, 5, 6, 20, 21, 22, 30, 32, 65, 100, 102};
        new RecursiveQuicksort().quicksort(array, 0, array.length - 1);

        IntStream stream = IntStream.of(array);
        stream.forEach(a -> System.out.println(a));
    }
}

```

### 5.2 Fork/Join

```java
public class ForkJoinQuicksort extends RecursiveAction {

    private int[] array;
    private int left;
    private int right;

    public ForkJoinQuicksort() {
        super();
    }

    public ForkJoinQuicksort(int[] array, int left, int right) {
        super();
        this.array = array;
        this.left = left;
        this.right = right;
    }
    
    @Override
    protected void compute() {

        if (left >= right || array == null || array.length <= 1) {
            return;
        }

        int privot = partition(array, left, right);
        ForkJoinQuicksort leftTask = new ForkJoinQuicksort(array, left, privot - 1);
        ForkJoinQuicksort rightTask = new ForkJoinQuicksort(array, privot + 1, right);

        leftTask.fork();    // 提交异步子任务
        rightTask.fork();

        rightTask.join();   // 等待任务执行结束
        leftTask.join();
    }

    public static void main(String[] args) {
        ForkJoinPool pool = new ForkJoinPool();

        int[] array = new int[]{3, 4, 50, 23, 20, 44, 22, 51, 32, 65, 2, 5};

        ForkJoinQuicksort task = new ForkJoinQuicksort(array, 0, array.length - 1);
        pool.invoke(task);  // 提交任务

        IntStream stream = IntStream.of(array);
        stream.forEach(value -> System.out.println(value));
    }
}

```
ForkJoinQuicksort主要是继承RecursiveAction（没有返回值），算法逻辑在compute方法实现即可。

## 6. 总结
ForkJoinPool主要是提供了“分治算法”的多线程版本，基于“Work-Stealing”，可以有效使用cpu多核的优势，提高算法的速度。ForkJoinPool 最适合的是计算密集型的任务，如果存在 I/O、线程间同步、sleep() 等会造成线程长时间阻塞的情况时，最好配合使用 ManagedBlocker。

**参考：**

----
[1]:http://blog.dyngr.com/blog/2016/09/15/java-forkjoinpool-internals/
[2]:https://www.jianshu.com/p/f777abb7b251
[3]:https://blog.hufeifei.cn/2018/09/15/Java/ForkJoinPool/
[4]:https://www.jianshu.com/p/de025df55363

[1. Java 并发编程笔记：如何使用 ForkJoinPool 以及原理][1]

[2. jdk1.8-ForkJoin框架剖析][2]

[3.ForkJoinPool入门篇][3]

[4.分析jdk-1.8-ForkJoinPool实现原理(上)][4]
