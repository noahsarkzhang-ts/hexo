---
title: 国际化资源文件加载问题
date: 2024-06-13 19:47:10
updated: 2024-06-13 19:47:10
tags:
- i18n
- spring.profiles.include
categories:
- 运维
---

这篇文章讲述在 Springboot中， 一个由于指定参数 spring.config.location 参数导致不能加载国际化资源文件的问题。

<!-- more -->

## 问题描述
在Springboot项目中，国际化文件不能加载。

## 现象描述

项目启动参数中不加入 --spring.config.location 参数,可以加载国际化资源文件，如果指定 --spring.config.location, 则国际化资源文件不能加载；

其中，国际化资源文件由独立的common-i18n模块加载，在主程序的 application.ym l中，通过 spring.profiles.include 引入，如下所示：
```bash
common-i18n
│  application-i18n.yml
│
└─i18n
        messages.properties
        messages_zh_CN.properties
```
application-i18n.yml 指定了如下内容：

```yaml
spring:
  # 资源信息
  messages:
    # 国际化资源文件路径
    basename: i18n/messages
    encoding: UTF-8
```

common-i18n模块是一个独立的模块，最终由主程序模块 application.yml 中引入：
```yaml
spring：
	profiles：
		include：i18n
```

## 定位过程
经过定位，在不指定 --spring.config.location 参数情况，资源加载文件是通过 ResourceBundleMessageSource 加载的，而指定参数之后则由 DelegatingMessageSource 加载，而 DelegatingMessageSource 对象上是空对象，没有加载任何资源文件。
ResourceBundleMessageSource 可以正确加载资源文件，ResourceBundleMessageSource 和 DelegatingMessageSource 都是MessageSource接口的实现类，一个程序中只会生成一个MessageSource实现类，到底生成那一个实现类？MessageSource 实现类的创建由 MessageSourceAutoConfiguration 完成，生成的逻辑则由 ResourceBundleCondition 类控制，看代码，发现是由 "spring.messages.basename" 配置项来控制的，有该配置则生成 ResourceBundleMessageSource，没有则生成 DelegatingMessageSource。

通过上面的分析，未加载资源文件是程序没有读到 "spring.messages.basename" 配置项，而该配置项在 application-i18n.yml 文件中定义，问题转换为没有读取到 application-i18n.yml，即在启动时指定了--spring.config.location参数，没有加载 application-i18n.yml 配置文件。--spring.config.location 参数会改变配置文件的加载？我们继续分析配置文件的加载逻辑。

属性或配置项是从一个 Environment 对象中读取的，每一个 spring 应用都至少有一个 Environment 对象，而 Environment 对象有一个 PropertySources 成员。在 Environment 的默认实现 StandardEnvironment 中，它会给 PropertySources 添加两个属性源：
1. systemProperties，PropertiesPropertySource 类型，保存所有通过 System.getProperties() 获取的属性；
2. systemEnvironment，SystemEnvironmentPropertySource 类型，保存所有通过 System.getenv() 获取的属性；
PropertiesPropertySource 同 SystemEnvironmentPropertySource 的区别是: 在 SystemEnvironmentPropertySource 的 key 中 . 和 _ 是等价的，并且不区分大小写；

当需要用到属性值时，PropertyResolver 会由头到尾顺序地从 PropertySources 遍历所有 PropertySource，从中找到匹配的属性值。
spring-boot 启动时，会向 environment 添加多个属性源，包括：
1. commandLineArgs，SimpleCommandLinePropertySource 类型，支持将命令行中 –key=value 形式的参数保存到 Map；
2. configurationProperties，ConfigurationPropertySourcesPropertySource 类型，这个类型比较特殊，它是一个 Iterable<ConfigurationPropertySource> 的包装，在这里是 SpringConfigurationPropertySources 的包装，而 SpringConfigurationPropertySources 又包装了 environment 的 propertySources；
3. random，类型是 RandomValuePropertySource。

配置文件属性源的加载由 ConfigFileApplicationListener 来实现，spring 根据设定的顺序加载配置文件，并添加所有读到的配置文件到 propertySources 中。
在 ConfigFileApplicationListener 中，默认的文件加载顺序为：
```bash
file:./config/
file:./
classpath:config/
classpath:
```

排在前面的文件优先级更高，在默认的情况下，如果这些配置文件中有 `spring.profiles.includ`e 和 `spring.profiles.active` 配置项，则会加入这些配置项指定的配置文件，如 application-i18n.yml。代码如下所示：
```java
private void applyActiveProfiles(PropertySource<?> defaultProperties) {
	List<String> activeProfiles = new ArrayList<>();
	// 默认配置不为空，则加载 spring.profiles.include 和
	// spring.profiles.active 指定的文件。
	if (defaultProperties != null) {
		Binder binder = new Binder(ConfigurationPropertySources.from(defaultProperties),
				new PropertySourcesPlaceholdersResolver(this.environment));
		activeProfiles.addAll(getDefaultProfiles(binder, "spring.profiles.include"));
		if (!this.activatedProfiles) {
			activeProfiles.addAll(getDefaultProfiles(binder, "spring.profiles.active"));
		}
	}
	this.processedProfiles.stream().filter(this::isDefaultProfile).map(Profile::getName)
			.forEach(activeProfiles::add);
	this.environment.setActiveProfiles(activeProfiles.toArray(new String[0]));
}
```

除了默认的加载排序，另外也可以通过 `spring.config.location` 和 `spring.config.additional-location`，修改加载的顺序，在这种情况下，不会加载 `spring.profiles.include` 和 `spring.profiles.active` 指定的配置文件。

通过上面代码的分析，`spring.config.location` 配置项修改了加载的顺序，更改了 `spring.profiles.include` 和 `spring.profiles.active` 的默认加载逻辑，致使 `application-i18n.yml` 被加载，下面是在两种情况下，加载的配置源：
**1）不指定 spring.config.location：**
```java
propertySourceList = {CopyOnWriteArrayList@5454}  size = 7
 0 = {ConfigurationPropertySourcesPropertySource@5456} "ConfigurationPropertySourcesPropertySource {name='configurationProperties'}"
 1 = {MapPropertySource@5457} "MapPropertySource {name='Inlined Test Properties'}"
 2 = {PropertiesPropertySource@5458} "PropertiesPropertySource {name='systemProperties'}"
 3 = {SystemEnvironmentPropertySourceEnvironmentPostProcessor$OriginAwareSystemEnvironmentPropertySource@5459} "OriginAwareSystemEnvironmentPropertySource {name='systemEnvironment'}"
 4 = {RandomValuePropertySource@5460} "RandomValuePropertySource {name='random'}"
 5 = {OriginTrackedMapPropertySource@5461} "OriginTrackedMapPropertySource {name='applicationConfig: [classpath:/application-i18n.yml]'}"
 6 = {OriginTrackedMapPropertySource@5462} "OriginTrackedMapPropertySource {name='applicationConfig: [classpath:/application.yml]'}"
```

加载了 classpath:/application-i18n.yml 配置文件。

**2）指定 spring.config.location=D:/lab/app/application.yml:**
```java
propertySourceList = {CopyOnWriteArrayList@5462}  size = 6
 0 = {ConfigurationPropertySourcesPropertySource@5464} "ConfigurationPropertySourcesPropertySource {name='configurationProperties'}"
 1 = {MapPropertySource@5465} "MapPropertySource {name='Inlined Test Properties'}"
 2 = {PropertiesPropertySource@5466} "PropertiesPropertySource {name='systemProperties'}"
 3 = {SystemEnvironmentPropertySourceEnvironmentPostProcessor$OriginAwareSystemEnvironmentPropertySource@5467} "OriginAwareSystemEnvironmentPropertySource {name='systemEnvironment'}"
 4 = {RandomValuePropertySource@5468} "RandomValuePropertySource {name='random'}"
 5 = {OriginTrackedMapPropertySource@5469} "OriginTrackedMapPropertySource {name='applicationConfig: [file:D:/lab/app/application.yml]'}"
```

未加载了 `classpath:/application-i18n.yml` 配置文件。

## 解决办法
1. 在启动参数中加入 `spring.messages.basename=i18n/messages` 配置项，让程序可以从环境变量中读取到该配置，从而生成 `ResourceBundleMessageSource` 对象，加载资源文件；
2. 修改主程序模块中 application.ym l配置，移除 spring.profiles.include 配置，加入 spring.messages.basename 配置，如下所示：
```yaml
# 移除配置项
spring：
	profiles：
		include：i18n

# 添加配置
spring:
  messages:
    # 国际化资源文件路径
    basename: i18n/messages
    encoding: UTF-8
```

第二种方式在一定程度上破坏了commin-i18n 模块的独立性，加大了模块间的耦合，建议使用第一种方式。