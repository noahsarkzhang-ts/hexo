---
title: Ice 常用命令
date: 2024-04-12 21:29:08
updated: 2024-04-12 21:29:08
tags:
- ice 对象
categories: 
- 运维
---

这篇文章主要记录用到的 icegridadmin  命令。

<!-- more -->

## Ice 对象

下面的 XML 是一个 ICE 应用的部署申明：
```xml
<icegrid>
    <application name="PrinterApplication">
        
		<server-template id="PrinterServerTemplate">
			<parameter name="index"/>
			<server id="PrinterServer-${index}" exe="java" activation="always">
				<option>-jar</option>
				<option>E:\bell-lab\ice\deploy-1\app\ice-lab.jar</option>
				
				<adapter name="PrinterAdapter" endpoints="tcp -p 20072" replica-group="ReplicatedPrinterAdapter"/>
				<property name="printerServiceIdentity" value="printerService"/>
							
				<property name="IceMX.Metrics.Debug.GroupBy" value="id"/>
				<property name="IceMX.Metrics.Debug.Disabled" value="1"/>
				<property name="IceMX.Metrics.ByParent.GroupBy" value="parent"/>
				<property name="IceMX.Metrics.ByParent.Disabled" value="1"/>
				
				<property name="Ice.ThreadPool.Server.SizeMax" value="20"/>
				<property name="Ice.Trace.Network" value="2"/>

			</server>
		</server-template>
		
		<replica-group id="ReplicatedPrinterAdapter">
			<load-balancing type="round-robin"/>
			<object identity="printerService" type="::org::noahsark::server::entry::IceEntry" />
	 
		</replica-group>

		<node name="node1">
			<server-instance template="PrinterServerTemplate" index="1"/>
		</node>
		
		<node name="node2">
			<server-instance template="PrinterServerTemplate" index="2"/>
		</node>
				
    </application>
</icegrid>

```

它包含以下元素（或对象）：
1）application：ICE 应用，它是由多个进程组成的公布式应用，由多个副本组成，可使用多种负载均衡的算法；
2）server: 代表应用的执行实体，简而言知，就是一个进程，如 java 进程；
3）adapter：适配器对象，封装了service，以特定的网络协议及端口对外提供服务；
4）service: 代表了一个RPC 接口的实现；
5）node: ICE 进程，负责管理 server及服务的注册，如启动和关闭；
6）registry: ICE 注册中心，负责服务的注册及发现； 
7）replica-group：副本组，表示一个 application 可以有多个副本。

部署结构如下所示：
![ice-object](/images/rpc/ice-object.jpg "ice-object")

补充说明：
1）代理对象：封装了客户端 RPC 调用的细节，由用户定义的 Slice 文件经过编译后生成的，它负责与远端的服务进行通信；
2）Servant对象: 服务端 RPC 接口的实现，由用户编写完成，需继承 ICE 服务端代码，最终包装成 service 对象发布出去。

## icegridadmin 命令
**icegridadmin** 是一个命令行工具，可以用来管理 ICE 对象。

**1. 启动**
```bash
icegridadmin --Ice.Config=config.cfg
```

配置文件内容：
```bash
Ice.Default.Locator=IceGrid/Locator:tcp -h 127.0.0.1 -p 4061

IceGridAdmin.Username=foo
IceGridAdmin.Password=bar
```

**2. 基本命令**
进入 **icegridadmin** 交互界面之后，可以输入以下命令进行查看。

```bash
help : 打印帮助信息；
exit, quit: 退出程序
CATEGORY help：打印指定分类的帮助信息；
COMMAND help：打印指定命令的帮助信息；

# 分类：
application: commands to manage applications
node: commands to manage nodes
registry: commands to manage registries
server: commands to manage servers
service: commands to manage services
adapter: commands to manage adapters
object: commands to manage objects
server template: commands to manage server templates
service template: commands to manage service templates
```

根据需要，查看不同分类或对象的信息。使用前，可以先调用 CATEGORY help 查看下命令的参数。

</br>

**参考：**

----
[1]:https://doc.zeroc.com/ice/3.7/ice-services/icegrid/icegridadmin-command-line-tool
[2]:http://localhost:4000/2022/04/03/ice-rpc/

[1. icegridadmin Command Line Tool][1]

[2. RPC：ICE][2]





