---
title: Springboot 序列：Spring Cloud RPC
date: 2022-04-16 19:57:05
tags:
- Ribbon
- Feign
- RestTemplate
categories:
- Springboot
---

在 `Spring Cloud` 体系中，可以使用 `Feign` 和 `RestTemplate` 两种方式实现服务间的 RPC 调用，它们底层使用相同的负载均衡组件 `Ribbon`。这篇文章主要介绍这两种调用方法及差异，有助于项目中进行技术选型。

<!-- more -->

## 概览

### Ribbon

负载均衡本质是使用一定的算法从多个相同的服务中选择出一个合适的服务进行访问。`Ribbon` 便是一个负载均衡组件，它会从注册中心获取一组服务器地址列表，在发送请求前通过负载均衡算法选择一个服务器，然后进行访问。`RestTemplate` 和 `Feign` 都集成了 `Ribbon`, 不过集成的方式略有不同；

### RestTemplate

为 `RestTemplate` 类添加 `@LoadBalanced` annotation, 便可在 `RestTemplate` 中添加对 `Ribbon` 的支持。

```java
@Configuration
public class RestConfig {
    @Bean
    @LoadBalanced
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
} 
```

添加 `@LoadBalanced` annotation 之后，本质上向 `RestTemplate` 中添加了一个负载均衡拦截器 `LoadBalancerInterceptor`, 在该拦截器实现对 `Ribbon` 的引入。

```java
// LoadBalancerInterceptor
@Override
public ClientHttpResponse intercept(final HttpRequest request, final byte[] body,
		final ClientHttpRequestExecution execution) throws IOException {
	final URI originalUri = request.getURI();
	String serviceName = originalUri.getHost();
	Assert.state(serviceName != null,
			"Request URI does not contain a valid hostname: " + originalUri);
	// loadBalancer 为 RibbonLoadBalancerClient 类
	return this.loadBalancer.execute(serviceName,
			this.requestFactory.createRequest(request, body, execution));
}

// RibbonLoadBalancerClient
public <T> T execute(String serviceId, LoadBalancerRequest<T> request, Object hint)
		throws IOException {
	ILoadBalancer loadBalancer = getLoadBalancer(serviceId);
	Server server = getServer(loadBalancer, hint);
	if (server == null) {
		throw new IllegalStateException("No instances available for " + serviceId);
	}
	RibbonServer ribbonServer = new RibbonServer(serviceId, server,
			isSecure(server, serviceId),
			serverIntrospector(serviceId).getMetadata(server));

	return execute(serviceId, ribbonServer, request);
}
```

`RestTemplate` 调用最终会被 `Ribbon` 接管，从而实现负载均衡的功能。

### Feign

使用 Feign, 需要两步操作。

- 定义 Feing 接口

使用 `FeignClient` 定义一个接口，Feign 为其实现一个代理类，将其添加到 Spring 容器中。客户端使用 `@Autowired` 注入即可。

```java
@FeignClient(value = "provider-service")
public interface UserFeignClient {

    @GetMapping(value = "/users/name")
    String name();

    @GetMapping("/users/online")
    UserDTO currentUser();

    @GetMapping("/users/query")
    Result<UserDTO> query();
}
```

- 开启 `EnableFeignClients`

```java
@SpringBootApplication
@EnableDiscoveryClient
@EnableFeignClients(basePackageClasses = {UserFeignClient.class})
public class FeignClientApp {

    public static void main(String[] args) {
        SpringApplication.run(FeignClientApp.class, args);
    }
}
```

添加 `EnableDiscoveryClient` annotation 之后，它会扫描所有带 `FeignClient` annotation 的接口，并为其向 Spring 容器中注册一个 `FeignClientFactoryBean` 类，`FeignClientFactoryBean` 将返回 `UserFeignClient` 接口的代理类，在该代理类中将添加对 `Ribbon` 的支持。

```java

// FeignClientFactoryBean
@Override
public Object getObject() throws Exception {
	// 返回接口实现类
	return getTarget();
}

// FeignClientFactoryBean
<T> T getTarget() {
	FeignContext context = this.applicationContext.getBean(FeignContext.class);
	Feign.Builder builder = feign(context);

	if (!StringUtils.hasText(this.url)) {
		if (!this.name.startsWith("http")) {
			this.url = "http://" + this.name;
		}
		else {
			this.url = this.name;
		}
		this.url += cleanPath();
		return (T) loadBalance(builder, context,
				new HardCodedTarget<>(this.type, this.name, this.url));
	}
	if (StringUtils.hasText(this.url) && !this.url.startsWith("http")) {
		this.url = "http://" + this.url;
	}
	String url = this.url + cleanPath();
	// 获取 RibbonLoadBalancerClient 类
	Client client = getOptional(context, Client.class);
	if (client != null) {
		if (client instanceof LoadBalancerFeignClient) {
			// not load balancing because we have a url,
			// but ribbon is on the classpath, so unwrap
			client = ((LoadBalancerFeignClient) client).getDelegate();
		}
		if (client instanceof FeignBlockingLoadBalancerClient) {
			// not load balancing because we have a url,
			// but Spring Cloud LoadBalancer is on the classpath, so unwrap
			client = ((FeignBlockingLoadBalancerClient) client).getDelegate();
		}
		builder.client(client);
	}
	Targeter targeter = get(context, Targeter.class);
	return (T) targeter.target(this, builder, context,
			new HardCodedTarget<>(this.type, this.name, url));
}

```

至此，`UserFeignClient` 接口被实例化，并添加到 `Spring` 容器中，该接口的实现类集成了 `Ribbon`.

## 项目结构

在这里我们构建一个 Demo, 在该 Demo 中实现 `Nacos` 作为注册中心，相关版本如下所示：
```xml
<properties>
    <spring-boot.version>2.2.5.RELEASE</spring-boot.version>
    <spring-cloud.version>Hoxton.SR3</spring-cloud.version>
    <spring-cloud-alibaba.version>2.2.1.RELEASE</spring-cloud-alibaba.version>
</properties>
```

工程整体结构如下：

![springcloud-rpc](/images/spring-cloud/springcloud-rpc.jpg "springcloud-rpc")

- 使用 Nacos 作为注册中心；
- rpc-service-provider 作为服务提供方，将服务到 Nacos 中；
- rpc-restemplate-client, rpc-feign-client 作为客户端使用不同协议调用服务提供方。

## 工程代码

### 服务端

**1、加入依赖**

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>

<dependency>
    <groupId>com.alibaba.cloud</groupId>
    <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
</dependency>
```

**2、服务端实现**

向外提供三个接口。

```java
@RestController
@RequestMapping("/users")
public class UserController {

    @GetMapping("/name")
    public String name() {
        return "admin";
    }

    @GetMapping("/online")
    public UserDTO currentUser() {

        UserDTO user = new UserDTO();

        user.setId(1000L);
        user.setUsername("admin");
        user.setRoles(Lists.newArrayList("admin"));

        return user;
    }

    @GetMapping("/query")
    public Result<UserDTO> query() {

        UserDTO user = new UserDTO();

        user.setId(1000L);
        user.setUsername("admin");
        user.setRoles(Lists.newArrayList("admin"));

        return Result.success(user);
    }

}
```

**3、开启服务发现功能**

通过 `EnableDiscoveryClient` annotation 引入服务发现功能。

```java
@EnableDiscoveryClient
@SpringBootApplication
public class RpcProviderApp {

    public static void main(String[] args) {
        SpringApplication.run(RpcProviderApp.class, args);
    }
}
```

**4、加入配置**
```yaml
server:
  port: 9501

spring:
  application:
    name: provider-service
  cloud:
    nacos:
      discovery:
        server-addr: 192.168.1.100:8848
        username: nacos
        password: nacos

```

### RestTemplate 客户端

**1、加入依赖**

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>

<dependency>
    <groupId>com.alibaba.cloud</groupId>
    <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
</dependency>
```

**2、构造 RestTemplate**
向 `RestTemplate` 中加入 `Ribbon` 负载均衡器。
```java
@Configuration
public class RestConfig {
    @Bean
    @LoadBalanced
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
} 
```

**3、客户端代码**
使用 `RestTemplate` 发起 RPC, 只需要将服务器地址改为服务名称 `provider-service` 即可。

```java
@RestController
@RequestMapping("/users")
public class UserController {

    @Autowired
    private RestTemplate restTemplate;

    @RequestMapping(value = "/name", method = RequestMethod.GET)
    public String name() {
        return restTemplate.getForObject("http://provider-service/users/name", String.class);
    }

    @GetMapping("/online")
    public UserDTO currentUser() {
        return restTemplate.getForObject("http://provider-service/users/online", UserDTO.class);
    }

    @GetMapping("/query")
    public Result<UserDTO> query() {

        String url = "http://provider-service/users/query";

        HttpHeaders headers = new HttpHeaders();
        MultiValueMap<String, String> map = new LinkedMultiValueMap<>();

        ResponseEntity<Result<UserDTO>> userResponse = restTemplate.exchange(url, HttpMethod.GET,
                new HttpEntity(map,headers), new ParameterizedTypeReference<Result<UserDTO>>() {
                });

        return userResponse.getBody();
    }

}
```

**4、开启服务发现功能**
```java
@SpringBootApplication
@EnableDiscoveryClient
public class RestTemplateClientApp {

    public static void main(String[] args) {
        SpringApplication.run(RestTemplateClientApp.class, args);
    }
}
```

**5、加入配置**
```yaml
server:
  port: 9092

spring:
  application:
    name: resttmplate-client
  cloud:
    nacos:
      discovery:
        server-addr: 192.168.1.100:8848
        username: nacos
        password: nacos
```

### Feign 客户端

**1、加入依赖**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>

<dependency>
    <groupId>com.alibaba.cloud</groupId>
    <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
</dependency>

<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-openfeign</artifactId>
</dependency>

```

**2、定义接口**
```java
@FeignClient(value = "provider-service")
public interface UserFeignClient {

    @GetMapping(value = "/users/name")
    String name();

    @GetMapping("/users/online")
    UserDTO currentUser();

    @GetMapping("/users/query")
    Result<UserDTO> query();
}
```

**3、客户端代码**
```java
@RestController
@RequestMapping("/users")
public class UserController {

    @Autowired
    private UserFeignClient userFeignClient;

    @RequestMapping(value = "/name", method = RequestMethod.GET)
    public String name() {
        return userFeignClient.name();
    }

    @GetMapping("/online")
    public UserDTO currentUser() {
        return userFeignClient.currentUser();
    }

    @GetMapping("/query")
    public Result<UserDTO> query() {

        return userFeignClient.query();
    }

}
```

**4、开启服务发现及 FeignClient 功能**

通过 `EnableFeignClients` annotation 扫描 `FeignClient` 接口，生成代理类。

```java
@SpringBootApplication
@EnableDiscoveryClient
@EnableFeignClients(basePackageClasses = {UserFeignClient.class})
public class FeignClientApp {

    public static void main(String[] args) {
        SpringApplication.run(FeignClientApp.class, args);
    }
}
```

**5、加入配置**
```yaml
server:
  port: 9093

spring:
  application:
    name: feign-client
  cloud:
    nacos:
      discovery:
        server-addr: 192.168.7.115:8848
        username: nacos
        password: nacos
```

## 总结

`Feign` 和 `RestTemplate` 两种方式以下面的特点：
1. `RestTemplate` 只需要通过添加 `@LoadBalanced` annotation 便可实现负载均衡的功能；
2. `RestTemplate` 的使用方式与常规的方式一样，只需要将服务地址改为服务名称即可；
3. `Feign` 需要申明客户端接口，通过代码生成技术实现代理类；
4. `RestTemplate` 使用简单，但对泛型的结果对象需要额外处理；
5. 从使用体验上来说，`Feign` 虽然额外定义一个接口，对于调用方而言，更为简单。

</br>

**参考：**

----
[1]:https://blog.51cto.com/u_15281317/3163830
[2]:https://help.aliyun.com/document_detail/122999.html
[3]:https://blog.csdn.net/f641385712/article/details/100788040

[1. Ribbon负载均衡原理，Feign是如何整合Ribbon的？][1]

[2. 实现负载均衡][2]

[3. 为何一个@LoadBalanced注解就让RestTemplate拥有负载均衡的能力？][3]
