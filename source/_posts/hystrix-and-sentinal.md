---
title: Springboot 序列：Hystrix & Sentinal
date: 2022-05-02 11:15:34
tags:
- Hystrix
- Sentinal
- 线程隔离
- 限流
- 熔断降级
categories:
- Springboot
---

在系统中，遇到突发流量或依赖的下游服务出现故障时，如何保证系统有足够的弹性，进行自我恢复，而不会因为突发流量或单一模块故障问题拖累整个系统？ `Netfix Hystrix & Alibaba Sentinal` 这两个组件解决的便是这个场景的问题。

<!-- more -->

## 概述

Hystrix 和 Sentinal 可以认为解决的是同一类问题，即保护系统在可受控的情况下运行，使得系统有足够的弹性。但它们的实现方式有较大的差异：
- Hystrix: 通过隔离（线程或信号量）将不同的资源请求分隔到不同的资源池中进行访问，不同资源池之间互不影响，从而将故障限定的特定的资源池中，不影响其它资源的访问；
- Sentinal: 通过流控的方式，如控制资源请求的 QPS, 使得请求控制在合理的范围内，从而达到资源隔离的效果。

Hystrix 和 Sentinal 有不同的地方，也有相同的地方，如它们都借鉴了断路器的设计思路，使得系统具有自我修复的能力。

## Hystrix

以下面的代码为例：

```java
// 定义 Command 对象
public class RemoteServiceTestCommand extends HystrixCommand<String> {

    private final RemoteServiceTestSimulator remoteService;

    public RemoteServiceTestCommand(Setter config, RemoteServiceTestSimulator remoteService) {
        super(config);
        this.remoteService = remoteService;
    }

    // 调用外部方法
    @Override
    protected String run() throws Exception {
        return remoteService.execute();
    }

    // 设置回调方法
    @Override
    protected String getFallback() {
        return "Fallback";
    }

    public static void main(String[] args) throws Exception {
        HystrixCommand.Setter config = HystrixCommand
                .Setter
                .withGroupKey(HystrixCommandGroupKey.Factory.asKey("RemoteServiceGroupCircuitBreaker"));
        HystrixCommandProperties.Setter properties = HystrixCommandProperties.Setter();
        // 设置每次请求的超时时间
        properties.withExecutionTimeoutInMilliseconds(1000);
        // 设置断路器打开之后的睡眠时间
        properties.withCircuitBreakerSleepWindowInMilliseconds(4000);
        // 设置隔离级别为：线程模式	
        properties.withExecutionIsolationStrategy(
                HystrixCommandProperties.ExecutionIsolationStrategy.THREAD);
        // 开启断路器
        properties.withCircuitBreakerEnabled(true);
        // 在 statisticalWindow(默认为 10S) 内开启断路器的最小请求的阈值
        properties.withCircuitBreakerRequestVolumeThreshold(1);
        // 错误率达到 50% 便打开断路器		
        properties.withCircuitBreakerErrorThresholdPercentage(50);

        config.andCommandPropertiesDefaults(properties);
        // 设置线程池大小
        config.andThreadPoolPropertiesDefaults(HystrixThreadPoolProperties.Setter()
                .withMaxQueueSize(1)
                .withCoreSize(1)
                .withQueueSizeRejectionThreshold(1));
        // 构造 Command 对象
        RemoteServiceTestCommand command = new RemoteServiceTestCommand(config, new RemoteServiceTestSimulator(500));
        // 发起远程方法调用		
        String result = command.execute();
    }
	
    // 模拟远程方法调用，可以设置执行时间
    public static class RemoteServiceTestSimulator {
        // 设置等待时间，用于模拟远程方法的执行时间	
        private long wait;

        public RemoteServiceTestSimulator(long wait) throws InterruptedException {
            this.wait = wait;
        }

        String execute() throws InterruptedException {
            Thread.sleep(wait);
            return "Success";
        }
    }

}
```

它有如下特点：
- 将远程方法的请求包装成一个 Command 对象，该对象中持有一个线程池，异步去访问远程方法；
- 可以为每一个请求设置超时时间，而不依赖于第三方调用，超时时间由额外的调度线程来触发；
- 可以设置隔离级别的类型：线程和信号量；
- 可以设置默认的返回值；
- 可以根据需要打开断路器；
- 可以根据需要设置断路器的参数，如错误率，请求的最小阈值及休眠时间等等。

### 整体流程

![hystrix-command-flow-chart](/images/spring-cloud/hystrix-command-flow-chart.png "hystrix-command-flow-chart")

整体流程如下：
1. 将远程方法包装成 `HystrixCommand` 或 `HystrixObservableCommand` 对象；
2. 执行 Command 对象, 有四个方法可以执行：1) execute(): 同步方法调用; 2) queue(): 异步方法调用 ; 3) observe(): 响应式编程，返回 Observable 对象; 4) toObservable(): 跟3) 类似; 前三个方法最终会转换为第 4）个方法；
3. 判断响应结果是否有缓存，若有，直接返回；
4. 断路器是否打开，若打开，则返回默认值或错误结果；
5. 线程池/信号量资源是否已经耗尽，若是，则拒绝返回默认值或错误结果；
6. 执行 `HystrixObservableCommand.construct()` 或 `HystrixCommand.run()`, 完成方法调用，若调用失败或超时，则返回默认值或错误结果；
7. 上报并统计 `metric` 数据；
8. 调用失败或超时，则返回默认值或错误结果；
9. 若成功，则返回正确的结果数据。

**说明：**
默认返回值建议不通过网络获取，直接在本地内存可以得到，避免获取默认返回值失败。

### 隔离级别

在 Hystrix 中，使用两种隔离级别来保护单一模块故障不会扩散到其它模块，它们分别是：线程和信号量模式，两者之间的模式如下所示：

![isolation-options-1280](/images/spring-cloud/isolation-options-1280.png "isolation-options-1280")

**线程模式的特点：**
- 请求线程和调用线程(Hystrix 线程) 不是同一个线程，对远程方法的调用不会阻塞请求线程；
- 每一个请求都会独立的线程池资源，一个请求有故障不会影响到其它请求，可以实现真正的资源隔离；
- 可以方便设置请求执行的超时时间，不依赖第三方组件；
- 该种模式下，会增大调用的开销，如线程上下文的切换。

**信号量模式的特点：**
- 请求线程和调用线程在同个线程下，不存在程上下文的切换，比较轻量级；
- 通过请求的 QPS 或 线程数来实现资源的隔离；
- 不能设置请求执行的超时时间，需要依赖第三方调用组件；

这两种模式适用于不同的场景，可以根据需要进行选择。

### 断路器

资源隔离之后，结合断路器，可以根据错误率执行降级操作（返回默认值），并自我探测故障是否恢复，完成状态的转换。

![circuit-breaker-1280](/images/spring-cloud/circuit-breaker-1280.png "circuit-breaker-1280")

工作原理如下：
1. 假定一个周期的请求量达到了阈值(HystrixCommandProperties.circuitBreakerRequestVolumeThreshold());
2. 且错误比率超过了阈值(HystrixCommandProperties.circuitBreakerErrorThresholdPercentage());
3. 断路器状态从 `CLOSED` 转换为 `OPEN`;
4. 若断路器打开，所有的请求直接断路，返回默认值或异常信息；
5. 休眠一段时间之后(HystrixCommandProperties.circuitBreakerSleepWindowInMilliseconds()), 转换为 `HALF-OPEN` 状态，下一个请求让其通过，如果请求失败，则重新回到 `OPEN` 状态继续休眠一段时间；若请求成功，则转换为 `CLOSED` 状态，并重新从 1) 步骤开始执行。

## Sentinal

以下面的代码为例：

```java
public class SentinelDemo {

    private static final String KEY = "HelloWorld";

    public static void main(String[] args) {
        // 配置流量规则
        initFlowRules();
        // 配置降级规则
        initDegradeRule();

        while (true) {
            // 定义被保护资源
            try (Entry entry = SphU.entry(KEY)) {
                // 被保护的逻辑
                System.out.println("hello world");
            } catch (BlockException ex) {
                // 处理被流控的逻辑
                System.out.println("blocked!");
            }
        }
    }

    // 配置流量规则
    private static void initFlowRules() {
        List<FlowRule> rules = new ArrayList<>();
        FlowRule rule = new FlowRule();
        // 根据资源名称进行配置
        rule.setResource(KEY);
        // 按照 qps 进行流控
        rule.setGrade(RuleConstant.FLOW_GRADE_QPS);
        // 设置 qps 最小阈值
        rule.setCount(20);
        rules.add(rule);
        FlowRuleManager.loadRules(rules);
    }

    // 配置降级规则
    private static void initDegradeRule() {
        List<DegradeRule> rules = new ArrayList<>();
        // 根据资源名称进行配置
        DegradeRule rule = new DegradeRule(KEY)
                // 根据错误率进行降级
                .setGrade(CircuitBreakerStrategy.ERROR_RATIO.getType())
                // 错误率阈值为 50%
                .setCount(0.5d)
                .setStatIntervalMs(30000)
                .setMinRequestAmount(50)
                // Retry timeout (in second)
                .setTimeWindow(10);
        rules.add(rule);
        DegradeRuleManager.loadRules(rules);
    }
}

```

它有如下的特点：
- 被保护的地方可以是一个接口，也可以是一个代码块，并被赋予一个“资源名称”；
- 可以根据资源名称添加不同的规则，如流控及降级规则；

### 基本概念

**资源**
资源是 Sentinel 的关键概念。它可以是 Java 应用程序中的任何内容，例如，由应用程序提供的服务，或由应用程序调用的其它应用提供的服务，甚至可以是一段代码。
只要通过 Sentinel API 定义的代码，就是资源，能够被 Sentinel 保护起来。大部分情况下，可以使用方法签名，URL，甚至服务名称作为资源名来标示资源。

**规则**
围绕资源的实时状态设定的规则，可以包括流量控制规则、熔断降级规则以及系统保护规则。所有规则可以动态实时调整。

### Sentinel 功能和设计理念

**流量控制**

流量控制在网络传输中是一个常用的概念，它用于调整网络包的发送数据。然而，从系统稳定性角度考虑，在处理请求的速度上，也有非常多的讲究。任意时间到来的请求往往是随机不可控的，而系统的处理能力是有限的。我们需要根据系统的处理能力对流量进行控制。Sentinel 作为一个调配器，可以根据需要把随机的请求调整成合适的形状。

![sentinel-flow-overview](/images/spring-cloud/sentinel-flow-overview.jpg "sentinel-flow-overview")


流量控制有以下几个角度:
- 资源的调用关系，例如资源的调用链路，资源和资源之间的关系；
- 运行指标，例如 QPS、线程池、系统负载等；
- 控制的效果，例如直接限流、冷启动、排队等。

**熔断降级**

Sentinel 和 Hystrix 的原则是一致的: 当调用链路中某个资源出现不稳定，例如，表现为 timeout，异常比例升高的时候，则对这个资源的调用进行限制，并让请求快速失败，避免影响到其它的资源，最终产生雪崩的效果

**系统负载保护**

Sentinel 同时提供系统维度的自适应保护能力。防止雪崩，是系统防护中重要的一环。当系统负载较高的时候，如果还持续让请求进入，可能会导致系统崩溃，无法响应。在集群环境下，网络负载均衡会把本应这台机器承载的流量转发到其它的机器上去。如果这个时候其它的机器也处在一个边缘状态的时候，这个增加的流量就会导致这台机器也崩溃，最后导致整个集群不可用。

针对这个情况，Sentinel 提供了对应的保护机制，让系统的入口流量和系统的负载达到一个平衡，保证系统在能力范围之内处理最多的请求。

### 工作机制
Sentinel 的主要工作机制如下：
- 对主流框架提供适配或者显示的 API，来定义需要保护的资源，并提供设施对资源进行实时统计和调用链路分析。
- 根据预设的规则，结合对资源的实时统计信息，对流量进行控制。同时，Sentinel 提供开放的接口，方便您定义及改变规则。
- Sentinel 提供实时的监控系统，方便您快速了解目前系统的状态。

### 整体流程

在 Sentinel 里面，所有的资源都对应一个资源名称以及一个 Entry。Entry 可以通过对主流框架的适配自动创建，也可以通过注解的方式或调用 API 显式创建；每一个 Entry 创建的时候，同时也会创建一系列功能插槽（slot chain），如下所示：
![sentinel-slot-chain-architecture](/images/spring-cloud/sentinel-slot-chain-architecture.png "sentinel-slot-chain-architecture")

这些插槽有不同的职责：
- NodeSelectorSlot: 负责收集资源的路径，并将这些资源的调用路径，以树状结构存储起来，用于根据调用路径来限流降级；
- ClusterBuilderSlot: 用于存储资源的统计信息以及调用者信息，例如该资源的 RT, QPS, thread count 等等，这些信息将用作为多维度限流，降级的依据；
- StatisticSlot: 用于记录、统计不同纬度的 runtime 指标监控信息；
- FlowSlot: 用于根据预设的限流规则以及前面 slot 统计的状态，来进行流量控制；
- AuthoritySlot: 根据配置的黑白名单和调用来源信息，来做黑白名单控制；
- DegradeSlot: 通过统计信息以及预设的规则，来做熔断降级；
- SystemSlot: 通过系统的状态，例如 load1 等，来控制总的入口流量。

通过这种类型责任链的方式完成了各种规则的校验，同时 Sentinel 也通过 SPI 接口，可以自定义 slot 并编排 slot 间的顺序，从而可以给 Sentinel 添加自定义的功能。

## 总结

Hystrix 官方建议使用线程的隔离模式，为每一个请求建立一个线程池，每一个线程池互不影响，有效地隔离了单一模块引起的影响范围，不过相对比较重量级，有一定的开销。Sentinel 使用流控的方式变相地实现资源的隔离，相对比较轻量，开销较少。可以根据具体要求选择使用。

</br>

**参考：**

----
[1]:https://github.com/Netflix/Hystrix/wiki/How-it-Works
[2]:https://sentinelguard.io/zh-cn/docs/introduction.html
[3]:https://sentinelguard.io/zh-cn/docs/quick-start.html

[1. Hystrix: How it Works][1]

[2. Sentinel 介绍][2]

[3. Sentinel 快速开始][3]
