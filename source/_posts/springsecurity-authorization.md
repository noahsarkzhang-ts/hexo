---
title: Springboot 系列：SpringSecurity 授权
date: 2022-04-04 19:56:22
updated: 2022-04-04 19:56:22
tags:
- Spring Security
- authorization
- 授权
- ExpressionUrlAuthorizationConfigurer
- FilterSecurityInterceptor
- Authentication
- ConfigAttribute
categories:
- Springboot
---

Spring Security 授权的本质是根据请求的 URL 找到匹配的权限规则列表，进行投票决定是否放行。本文将讲述这一过程，并分析底层的数据结构。

<!-- more -->

## 整体流程

![Authorization](/images/spring-cloud/Authorization.jpg "Authorization")

**授权流程如下：**
1. 用户认证成功之后，会绑定一个 Authentication 对象，一般是 UsernamePasswordAuthenticationToken 对象；
2. 请求被 FilterSecurityInterceptor 拦截，并根据请求的 URL 从 ExpressionBasedFilterInvocationSecurityMetadataSource 中获取匹配的一组 ConfigAttribute 列表；
3. ConfigAttribute 列表代表了一组权限规则，由用户自定义指定的，如 `permitAll`, `authenticated`, `denyAll` 等等；
4. 将请求操作封装为 FilterInvocation, 并将它作为参数，连同 Authentication, ConfigAttribute 列表传递给 AccessDecisionManager 接口，由该接口决策是否放行；
5. AccessDecisionManager 接口的实现类是 AffirmativeBased, 在该类中，会持有多个 Voter, 每一个 Voter 都可以对权限规则列表进行投票，只要一个失败便失败；
6. 在这里，Voter 使用的是 WebExpressionVoter, 它使用 SpEL (Spring 表达式语言) 进行逻辑判断。

## 相关类

在上文的整体流程中，涉及到一些数据结构，如 ConfigAttribute 列表。这是怎么产生的？这个章节将会详细讲到。我们先看一个整体的类图，然后再结合一个实例分析。

![AccessDecisionManager](/images/spring-cloud/AccessDecisionManager.jpg "AccessDecisionManager")

**关键类：**
- ExpressionUrlAuthorizationConfigurer: 授权操作的配置类，这会对创建和初始化相关的类，如上文提到的 FilterSecurityInterceptor, AccessDecisionManager,ExpressionBasedFilterInvocationSecurityMetadataSource; 
- FilterSecurityInterceptor: 授权过滤器，这会拦截所有的请求，进行权限判断，这是授权操作的入口；
- AccessDecisionManager: 它是授权判断的关键类，是否可以访问由它来决策；
- ExpressionBasedFilterInvocationSecurityMetadataSource：存储权限规则列表，每一个请求都会对应一个权限规则列表；
- ExpressionInterceptUrlRegistry: 存储用户配置的权限规则列表，ExpressionBasedFilterInvocationSecurityMetadataSource 中的数据便是由该类转化映射而来，或者说该类存储了最原始的规则列表。
- ConfigAttribute：配置属性接口，存储了权限规则的内容；
- SecurityConfig：ConfigAttribute 实现类，它只是简单将权限规则存储为 String 类型；
- WebExpressionConfigAttribute：表达式类型的 ConfigAttribute 实现类，可以使用 SpEL 表达式来判断是否有权限，它由 SecurityConfig 对象转化而来；

## 实例

以下面的配置为例，配置两个规则，`/admin/**` 请求需要 `ADMIN` 角色才能访问，其它的请求只要登陆便可访问。我们来分析它是生成什么样的 ConfigAttribute 列表；

```java
http.authorizeRequests()
    .antMatchers("/admin/**").hasRole("ADMIN")
    .anyRequest().authenticated()
```

### 引入配置类

调用 `http.authorizeRequests()` 方法后，便向 HttpSecurity 对象中加入了 ExpressionUrlAuthorizationConfigurer, 它会完成授权相关类的创建及初始化。

```java
public ExpressionUrlAuthorizationConfigurer<HttpSecurity>.ExpressionInterceptUrlRegistry authorizeRequests()
		throws Exception {
	ApplicationContext context = getContext();
	return getOrApply(new ExpressionUrlAuthorizationConfigurer<>(context))
			.getRegistry();
}
```

### 生成 SecurityConfig 对象

跟踪代码可知， `antMatchers("/admin/**")` 方法会生成一个 AuthorizedUrl 对象， 并将 `/admin/**` 转化一个 AntPathRequestMatcher 对象。`hasRole("ADMIN")` 方法首先会转化成 `hasRole('ROLE_ADMIN')` 字符串，然后生成 SecurityConfig 对象，最终转化为一个 UrlMapping 对象存储到 ExpressionInterceptUrlRegistry 对象中。

```java
// ExpressionUrlAuthorizationConfigurer
private static String hasRole(String role) {
	Assert.notNull(role, "role cannot be null");
	if (role.startsWith("ROLE_")) {
		throw new IllegalArgumentException(
				"role should not start with 'ROLE_' since it is automatically inserted. Got '"
						+ role + "'");
	}
	// 1、生成权限字符串	
	return "hasRole('ROLE_" + role + "')";
}

// AuthorizedUrl
public ExpressionInterceptUrlRegistry access(String attribute) {
	if (not) {
		attribute = "!" + attribute;
	}
	// 2、生成 SecurityConfig 对象，并存储到 UrlMapping 中
	interceptUrl(requestMatchers, SecurityConfig.createList(attribute));
	return ExpressionUrlAuthorizationConfigurer.this.REGISTRY;
}

// ExpressionUrlAuthorizationConfigurer
private void interceptUrl(Iterable<? extends RequestMatcher> requestMatchers,
		Collection<ConfigAttribute> configAttributes) {
	// 3. 将 UrlMapping 存储到 ExpressionInterceptUrlRegistry 中
	for (RequestMatcher requestMatcher : requestMatchers) {
		REGISTRY.addMapping(new AbstractConfigAttributeRequestMatcherRegistry.UrlMapping(
				requestMatcher, configAttributes));
	}
}
```

由此可知，我们知道有如下的转化关系：
- /admin/** ---> AntPathRequestMatcher
- hasRole("ADMIN") ---> hasRole('ROLE_ADMIN') ---> SecurityConfig
- antMatchers("/admin/**").hasRole("ADMIN") ---> UrlMapping

我们来看下 `ConfigAttribute`, `SecurityConfig`, `UrlMapping` 的结构：

```java
public interface ConfigAttribute extends Serializable {

	String getAttribute();
}

public class SecurityConfig implements ConfigAttribute {
	// ~ Instance fields
	// ================================================================================================

	private final String attrib;

	
	@Override
	public String getAttribute() {
		return this.attrib;
	}

	// ...

	public static List<ConfigAttribute> createList(String... attributeNames) {
		Assert.notNull(attributeNames, "You must supply an array of attribute names");
		List<ConfigAttribute> attributes = new ArrayList<>(
				attributeNames.length);

		for (String attribute : attributeNames) {
			attributes.add(new SecurityConfig(attribute.trim()));
		}

		return attributes;
	}
}

static final class UrlMapping {
	private RequestMatcher requestMatcher;
	private Collection<ConfigAttribute> configAttrs;

	// ..
}
```

UrlMapping 是一个数据存储类，它将 `antMatchers("/admin/**").hasRole("ADMIN") ` 相关的数据封装在 UrlMapping 中，并最终存储到 ExpressionInterceptUrlRegistry 中。

```java
public abstract class AbstractConfigAttributeRequestMatcherRegistry<C> extends
		AbstractRequestMatcherRegistry<C> {
	private List<UrlMapping> urlMappings = new ArrayList<>();
	private List<RequestMatcher> unmappedMatchers;

	final void addMapping(UrlMapping urlMapping) {
		this.unmappedMatchers = null;
		this.urlMappings.add(urlMapping);
	}
	
	// ...
}
```

### 转化为 WebExpressionConfigAttribute 对象

将权限配置转化为 UrlMapping 并存储到 ExpressionInterceptUrlRegistry 中之后，在 FilterSecurityInterceptor 中并不能直接使用它，而是将它转化为 WebExpressionConfigAttribute 对象。

```java
final ExpressionBasedFilterInvocationSecurityMetadataSource createMetadataSource(
		H http) {
	LinkedHashMap<RequestMatcher, Collection<ConfigAttribute>> requestMap = REGISTRY
			.createRequestMap();
	if (requestMap.isEmpty()) {
		throw new IllegalStateException(
				"At least one mapping is required (i.e. authorizeRequests().anyRequest().authenticated())");
	}
	return new ExpressionBasedFilterInvocationSecurityMetadataSource(requestMap,
			getExpressionHandler(http));
}
```

首先它将 ExpressionInterceptUrlRegistry 中的 `List<UrlMapping>` 转化为 `LinkedHashMap<RequestMatcher, Collection<ConfigAttribute>>`, 然后再将 SecurityConfig 转化为 WebExpressionConfigAttribute.

```java
public final class ExpressionBasedFilterInvocationSecurityMetadataSource
		extends DefaultFilterInvocationSecurityMetadataSource {
	
	private final Map<RequestMatcher, Collection<ConfigAttribute>> requestMap;

	// 1、构造 ExpressionBasedFilterInvocationSecurityMetadataSource
	public ExpressionBasedFilterInvocationSecurityMetadataSource(
			LinkedHashMap<RequestMatcher, Collection<ConfigAttribute>> requestMap,
			SecurityExpressionHandler<FilterInvocation> expressionHandler) {
			
		requestMap = processMap(requestMap, expressionHandler.getExpressionParser());
	}

	private static LinkedHashMap<RequestMatcher, Collection<ConfigAttribute>> processMap(
			LinkedHashMap<RequestMatcher, Collection<ConfigAttribute>> requestMap,
			ExpressionParser parser) {
		Assert.notNull(parser, "SecurityExpressionHandler returned a null parser object");

		LinkedHashMap<RequestMatcher, Collection<ConfigAttribute>> requestToExpressionAttributesMap = new LinkedHashMap<RequestMatcher, Collection<ConfigAttribute>>(
				requestMap);

		for (Map.Entry<RequestMatcher, Collection<ConfigAttribute>> entry : requestMap
				.entrySet()) {
			RequestMatcher request = entry.getKey();

			ArrayList<ConfigAttribute> attributes = new ArrayList<>(1);
			String expression = entry.getValue().toArray(new ConfigAttribute[1])[0]
					.getAttribute();

			AbstractVariableEvaluationContextPostProcessor postProcessor = createPostProcessor(
					request);
			try {
				// 2、生成 WebExpressionConfigAttribute 对象
				attributes.add(new WebExpressionConfigAttribute(
						parser.parseExpression(expression), postProcessor));
			}
			catch (ParseException e) {
				throw new IllegalArgumentException(
						"Failed to parse expression '" + expression + "'");
			}

			requestToExpressionAttributesMap.put(request, attributes);
		}

		return requestToExpressionAttributesMap;
	}
	
	// ...
}
```

至此，在 FilterSecurityInterceptor 中得到的 ConfigAttibute 已经转化为 WebExpressionConfigAttribute 对象。

### 权限的判断

在 WebExpressionVoter 中会创建一个 EvaluationContext 及 Expression 来完成权限的判断，如 `hasRole('ROLE_ADMIN')`.

```java
public int vote(Authentication authentication, FilterInvocation fi,
		Collection<ConfigAttribute> attributes) {
	assert authentication != null;
	assert fi != null;
	assert attributes != null;

	WebExpressionConfigAttribute weca = findConfigAttribute(attributes);

	if (weca == null) {
		return ACCESS_ABSTAIN;
	}

	EvaluationContext ctx = expressionHandler.createEvaluationContext(authentication,
			fi);
	ctx = weca.postProcess(ctx, fi);

	return ExpressionUtils.evaluateAsBoolean(weca.getAuthorizeExpression(), ctx) ? ACCESS_GRANTED
			: ACCESS_DENIED;
}
```

我们进一步来看下 EvaluationContext 包含什么内容？

```java
public final EvaluationContext createEvaluationContext(Authentication authentication,
		T invocation) {
	SecurityExpressionOperations root = createSecurityExpressionRoot(authentication,
			invocation);
	StandardEvaluationContext ctx = createEvaluationContextInternal(authentication,
			invocation);
	ctx.setBeanResolver(br);
	ctx.setRootObject(root);

	return ctx;
}
```

通过 Authentication 和 FilterInvocation 对象创建了一个 SecurityExpressionOperations 对象，并将其作为 StandardEvaluationContext 对象的 RootObject. 

```java

public interface SecurityExpressionOperations {

	Authentication getAuthentication();

	boolean hasAuthority(String authority);

	boolean hasAnyAuthority(String... authorities);

	boolean hasRole(String role);

	boolean hasAnyRole(String... roles);

	boolean permitAll();

	boolean denyAll();

	boolean isAnonymous();

	boolean isAuthenticated();

	boolean isRememberMe();

	boolean isFullyAuthenticated();

	boolean hasPermission(Object target, Object permission);

	boolean hasPermission(Object targetId, String targetType, Object permission);

}

```

SecurityExpressionOperations 包含了一系列权限判断的方法，而 SpEL 表达式权限的判断是调用该接口中的方法来实现的。

## 总结
- ExpressionUrlAuthorizationConfigurer 类完成对 FilterSecurityInterceptor, AccessDecisionManager, ExpressionBasedFilterInvocationSecurityMetadataSource 对象的创建及初始化；
- HttpSecurity 中的权限配置会转化为 UrlMapping 对象并存储到 ExpressionInterceptUrlRegistry 中，并最终转化为 WebExpressionConfigAttribute 对象；
- 权限判断最终转化为 SpEL 表达式值的计算，而方法的判断封装在 SecurityExpressionOperations 对象中。