---
title: Flink 系列： Hello World
date: 2022-09-08 16:13:21
tags:
- flink
- wordcount
- quickstart
categories:
- Flink
---

这篇文章编写一个简单的 `World Count` 程序。 

<!-- more -->

## 项目配置

### 项目约定

本工程使用的环境如下：
- Flink 版本：1.15
- IDE: IDEA 社区版
- JDK 版本：JDK 9
- 构建工具：Maven

### 创建项目

可以使用 maven 命令创建一个模板工程：
```bash
mvn archetype:generate                \
  -DarchetypeGroupId=org.apache.flink   \
  -DarchetypeArtifactId=flink-quickstart-java \
  -DarchetypeVersion=1.15.0
```

或在 IDEA 中根据 `Archetype` 创建一个工程。

![flink-maven-archetype](/images/flink/flink-maven-archetype.png "flink-maven-archetype")

通过上面两种方式，会引入依赖的 Flink Jar, 同时生成一个骨架程序，便可在其中添加逻辑程序。

**说明：**
1. 引入的 Flink Jar 包 Maven Scope 类型为 `provided`, 执行时会报 `错误: 无法初始化主类 org.example.HelloWorldStreamJob`, 需要在 `Configurations` 中加入 `Include dependencies with ‘Provided’ scope` 选项;
2. 工程中引入了 `maven-shade-plugin` 插件，它会将所有的依赖连同代码打成一个 fat jar, 并指定启动类 `mainClass`.

## 骨架代码

程序的功能如下：从 TCP 9000 端口读取字符串，并统计每 15 S 单词出现的次数。

```java
public class HelloWorldStreamJob {

    public static void main(String[] args) throws Exception {

        // 设置流环境
        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // 用parameter tool工具从程序启动参数中提取配置项，如 --host 192.168.1.1 --port 9000
        // 使用 nc -lk 9000 监听请求并发送数据
        final ParameterTool parameterTool = ParameterTool.fromArgs(args);
        String host = parameterTool.get("host");
        int port = parameterTool.getInt("port");

        // 时间语义为处理时间（事件处理的时间）
        env.getConfig().setAutoWatermarkInterval(0L);

        // 从 TCP 文本流中读取数据
        DataStream<String> text = env.socketTextStream(host, port, "\n");

        // 将字符串按照空格分隔，得到二元组 <world, 1>, 第一个元素为单词，第二个元素为数字1，表示单词的数量
        DataStream<Tuple2<String, Integer>> wordCounts = text
                .flatMap(new FlatMapFunction<String, Tuple2<String, Integer>>() {
                    @Override
                    public void flatMap(String value, Collector<Tuple2<String, Integer>> out) {
                        for (String word : value.split("\\s")) {
                            out.collect(Tuple2.of(word, 1));
                        }
                    }
                });

        // 将二元组按照第一个元素，即单词分组，然后按照时间进行分桶，统计每 15S 单词出现的次数
        DataStream<Tuple2<String, Integer>> windowCounts = wordCounts
                .keyBy(tuple -> tuple.f0)
                .window(TumblingProcessingTimeWindows.of(Time.seconds(10)))
                .sum(1);

        // 设置并行度为1(方便测试)
        windowCounts.print().setParallelism(1);

        // 定义任务名称并启动任务.
        env.execute("Hello World Job");
    }
}
```

**代码流程如下：**
1. 设置执行环境为流执行环境；
2. 从执行参加中读取 `host`, `port` 参数；
3. 将时间设置为处理时间语义；
4. 建立 TCP 连接，读取文本流；
5. 将字符串按照空格分隔，得到二元组 <world, 1>, 第一个元素为单词，第二个元素为数字1，表示单词的数量；
6. 将二元组按照第一个元素，即单词分组，然后按照时间进行分桶，统计每 15S 单词出现的次数；
7. 设置并行度为1; 
8. 定义任务名称并启动任务。

## 任务执行

### 启动 nc
```bash
# nc -lk 9000  
hello flink
hello tree
hello allen
hello world

```

### 启动任务

设置参数：
![flink-hello-world-params](/images/flink/flink-hello-world-params.png "flink-hello-world-params")

执行结果：

```bash
(hello,1)
(flink,1)
(hello,1)
(tree,1)
(hello,2)
(world,1)
(allen,1)
```

## 代码部署

使用 Maven 打包输出 hello-count.jar, 有两种方式把任务提交到集群。

### 命令行模式

```bash
# 切换到 Flink 目录
$ cd /app/flink-1.15.0

# 使用 flink 命令提交任务
$ ./bin/flink run task/hello-count.jar --host 192.168.56.104 --port 9000

# 查询输出结果
$ tail log/flink-*-taskexecutor-*.out
(hello,2)
(world,1)
(flink,1)
(hello,1)
(allen,1)

# 查询当前任务列表
$ ./bin/flink list
Waiting for response...
------------------ Running/Restarting Jobs -------------------
09.09.2022 19:46:24 : 17fb86d9fb840d83e4802b657d478c09 : Hello World Job (RUNNING)
--------------------------------------------------------------
No scheduled jobs.

# 取消任务执行
$ ./bin/flink cancel 17fb86d9fb840d83e4802b657d478c09
Cancelling job 17fb86d9fb840d83e4802b657d478c09.
Cancelled job 17fb86d9fb840d83e4802b657d478c09.

```

### Flink Dashboard

Flink 提供了一个 Web Dashboard, 地址一般为：`http://jobmanager:8081`, 可以在上面提交任务。

![flink-ui-submit](/images/flink/flink-ui-submit.png "flink-ui-submit")

可以在 `Task Managers` 菜单中查看执行日志：

![flink-ui-log](/images/flink/flink-ui-log.png "flink-ui-log")

另外，也可以在页面上管理任务，如取消、停止任务等等。

**参考：**

----
[1]:https://nightlies.apache.org/flink/flink-docs-release-1.15/zh/docs/dev/configuration/overview/
[2]:https://nightlies.apache.org/flink/flink-docs-release-1.15/zh/docs/deployment/cli/

[1. Flink 项目配置][1]
[2. Flink 命令行界面][2]