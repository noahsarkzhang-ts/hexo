---
title: Springboot 序列：SpringSecurity 整体架构
date: 2022-03-26 19:08:32
tags:
- Spring Security
- Filter
categories:
- Springboot
---

Spring Security 作为一个安全框架，它提供了两个基本的功能：1）认证；2）授权。认证表明一个是谁，授权则表示用户可以做什么。在底层实现上，这两个基本功能都是基于 Servlet Filter 来实现的，Filter 是Spring Security 框架的基座。 为了搞清楚其内部的实现原理，本文介绍了 Spring Security 中用到的 Filter 及它们之间的协作，后续再补充认证及授权流程。

<!-- more -->

## 整体结构

假定有一个场景，一个服务器基于 Spring Oauth2 实现了认证服务器的功能，其配置如下：

```java
/**
 *  Spring Security 配置
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig extends WebSecurityConfigurerAdapter {

    @Autowired
    private CustomerUserDetailsService userService;

    // 1. 配置不认证的 url
    @Override
    public void configure(WebSecurity web) {
        web.ignoring().antMatchers("/login.html", "/css/**", "/js/**", "/images/**");
    }

    // 2. 配置需要认证的 url
    @Override
    protected void configure(HttpSecurity http) throws Exception {

        http.requestMatchers()
                .antMatchers("/login")
                .antMatchers("/oauth/authorize")
                .and()
                .authorizeRequests().anyRequest().authenticated()
                .and()
                .formLogin()
                .loginPage("/login.html")
                .loginProcessingUrl("/login")
                .permitAll()
                .and()
                .csrf().disable();
    }

    // 其它方法省略
}


/**
 * 认证服务器配置
 */
@Configuration
@EnableAuthorizationServer
public class AuthorizationServerConfiguration extends AuthorizationServerConfigurerAdapter {

    @Override
    public void configure(AuthorizationServerSecurityConfigurer security) throws Exception {
        // 允许静表单访问
        security.tokenKeyAccess("permitAll()")
                .checkTokenAccess("permitAll()")
                .allowFormAuthenticationForClients();
    }

    // 其它方法省略
}

```

在上面的代码中，引入了两份配置，一个是引入 Spring Security 本身的配置，另外一份是认证中心的配置。在 Spring Security 配置中，配置了两份的 endponit 的访问权限:
- 忽略的 endponit ：`/login.html, /css/**,  /js/**, /images/**` , 这些 url 主要是静态资源，不需要授权；
- 需要权限认证的 endponit ：`/login, /oauth/authorize`, 这两个 endpoint 的访问需要经过 Spring Security 授权（注：/login 是登陆接口，直接放行）。

在认证中心的配置中，需要对 Oauth2 相关的 endpoint 授权：
- Oauth2 endpoint : `/oauth/token, /oauth/token_key, /oauth/check_token`, 这些 endpoint 的访问需要认证服务器进行授权。

**注：** Oauth2 endpoint 的 endponit 配置在 AuthorizationServerSecurityConfiguration 类中。

 针对这些 endpoint, Spring Security 会生成一个系列的 Fileter 去处理，如下图所示：

![springsecurity-filters](/images/spring-cloud/springsecurity-filters.jpg "springsecurity-filters")

1. 顶层是 DelegatingFilterProxy 类，它是 Spring Security 的入口类，它拦截所有的请求进行安全校验；
2. DelegatingFilterProxy 类的业务逻辑委托给名为 springSecurityFilterChain 的 FilterChainProxy 类进行处理；
3. FilterChainProxy 类中维护一个 DefaultSecurityFilterChain 的列表，根据不同的 endpont 路由到 DefaultSecurityFilterChain 类中, 路由判断的功能封装在 RequestMatcher 中；
4. DefaultSecurityFilterChain 由一系列配置好的 Filter 组成，每一个 Filter 包含一个安全校验功能，根据根据业务需要添加特定功能的 Filter；
5. 在忽略的 endponit (不需要认证) 对应的 DefaultSecurityFilterChain 中，Filter 列表为空，表明不做任何检查，一个 endpoint 对应一个空的 DefaultSecurityFilterChain 对象；
6. 需要权限认证的 endponit 和 Oauth2 endpoint 则由不同的 Filter 列表进行安全检查，这两个 DefaultSecurityFilterChain 由不同的 HttpSecurity 进行构建；
7. 最底层的 Filter 由 FormLoginConfigurer 进行配置，根据不同的业务功能，业务上层可以自由设置。

**<font color='red'>总上所述：一个忽略的 endponit 生成一个 DefaultSecurityFilterChain，一个 HttpSecurity 对象生成一个 DefaultSecurityFilterChain，在上面的实例中，一共分生成 6 个 DefaultSecurityFilterChain, 即 6 条处理流程。</font>**

以 Spring Security 配置为例，它生成的 Filter 列表如下所示：

- WebAsyncManagerIntegrationFilter: 将 SecurityContext 与 WebAsyncManager 整合起来，使得在 Callable 中可以使用 SecurityContext, 从而可以在异步 Servlet 中使用 Spring Security; 
- SecurityContextPersistenceFilter: 有两个功能：1）在每次请求前，向 SecurityContextHolder 中添加 SecurityContext 对象，在请求结束后再清空该对象；2）请求结束之后，向 Session 中添加  SecurityContext 对象，以便下次请求使用；
- HeaderWriterFilter: 处于安全的目的，向 http 响应添加一些 Header, 比如 X-Frame-Options, X-XSS-Protection*，X-Content-Type-Options;
- **<font color='red'>LogoutFilter :</font>** 拦截退出请求，注销用户的认证及会议信息，最后跳转到指定页面；
- **<font color='red'>UsernamePasswordAuthenticationFilter :</font>**拦截登录请求，获取用户表单信息，生成 UsernamePasswordAuthenticationToken 对象，调用 AuthenticationManager 对象的 authenticate 认证方法，完成用户的认证流程，最终生成认证结果对象 Authentication，并将该对象添加到 SecurityContextHolder 中;
- **<font color='red'>RequestCacheAwareFilter：</font>**未认证的请求认证成功之后，需要恢复 HttpRequest 的状态，如 Method,Locales,Parameters 等等，RequestCacheAwareFilter 就是用来恢复请求的状态。 
- SecurityContextHolderAwareRequestFilter：将 HttpServletRequest 对象扩展为 SecurityContextHolderAwareRequestWrapper 对象，它向 HttpServletRequest 中添加了额外的方法：1）authenticate,允许用户决他们是否已经认证成功或未认证跳转到登录页面；2）login，允许用户进行认证操作；3）logout，允许用户进行登出操作；
- AnonymousAuthenticationFilter：判断 SecurityContextHolder 是否有 Authentication 对象，没有的话则添加一个用户名为 anonymousUser、角色为 ROLE_ANONYMOUS 的 Authentication 对象；
- SessionManagementFilter：加入一些与 Session 相关的操作，如激活 session-fixation 保护机制或检测一个用户多次登陆的问题；
- **<font color='red'>ExceptionTranslationFilter ：</font>**处理转译 AccessDeniedException 和 AuthenticationException 异常。检测到 AuthenticationException 异常，重定向到登陆页面，并缓存 RequestCache 对象，便于认证成功之后恢复请求。检测到 AccessDeniedException，如果是匿名用户，则重定向到登陆页面，否则由 AccessDeniedHandlerImpl 对象处理
- **<font color='red'>FilterSecurityInterceptor：</font>**这个过滤器判断认证用户是否具备访问资源（url endpoint）的权限。

在这里面，有几个 Filter 比较重要：
- LogoutFilter: 处理登出请求，清除会话信息，并重定向到指定页面，默认页面是: /login?logout; 
- UsernamePasswordAuthenticationFilter : 处理登陆请求，验证用户信息，并最终生成一个 Authentication 对象，里面包含了用户及权限信息；
- RequestCacheAwareFilter: 一个请求如果未认证会跳转到登陆页面，登陆成功为继续之前的请求，而该 Filter 用来恢复之前的请求状态信息，包括 method, header,参数等等信息；
- ExceptionTranslationFilter：用于转译认证异常信息，若未登陆则跳转到登陆页面，若认证失败则跳转到指定页面；
- FilterSecurityInterceptor：用于用户权限判断，判断用户可以访问该资源 (endpoint).

## 加载 Filter

上文分析了 Spring Security 的 Filter 整体结构，它们是怎么加载到系统中的？如下图为示，展示了与 Filter 加载相关的类。

![springsecurity-filters-config](/images/spring-cloud/springsecurity-filters-config.jpg "springsecurity-filters-config")

### 注册 DelegatingFilterProxy

DelegatingFilterProxy 是 Spring Security Filter 的源头，它是在 SecurityFilterAutoConfiguration 类进行加载，如果项目中引入了 Spring Security 相关的 Jar 包，该配置会自动触发。

```java
@Configuration(proxyBeanMethods = false)
@ConditionalOnWebApplication(type = Type.SERVLET)
@EnableConfigurationProperties(SecurityProperties.class)
@ConditionalOnClass({ AbstractSecurityWebApplicationInitializer.class, SessionCreationPolicy.class }) // <1>
@AutoConfigureAfter(SecurityAutoConfiguration.class)
public class SecurityFilterAutoConfiguration {

        // DEFAULT_FILTER_NAME 为 springSecurityFilterChain
	private static final String DEFAULT_FILTER_NAME = AbstractSecurityWebApplicationInitializer.DEFAULT_FILTER_NAME;

        // <2>
	@Bean
	@ConditionalOnBean(name = DEFAULT_FILTER_NAME)
	public DelegatingFilterProxyRegistrationBean securityFilterChainRegistration(
			SecurityProperties securityProperties) {
		DelegatingFilterProxyRegistrationBean registration = new DelegatingFilterProxyRegistrationBean(
				DEFAULT_FILTER_NAME);
		registration.setOrder(securityProperties.getFilter().getOrder());
		registration.setDispatcherTypes(getDispatcherTypes(securityProperties));
		return registration;
	}
	
	// ...
}
```

- <1> 处该自动配置依赖项目中 AbstractSecurityWebApplicationInitializer, SessionCreationPolicy 类的存在，这两个类是 Spring Security Jar 包中的类，只要引入  Spring Security, 即可触发自动配置；
- <2> 处注册 DelegatingFilterProxy，它只是一个代理类，它依赖名为 springSecurityFilterChain 的 Filter, springSecurityFilterChain 才是真正地封装了业务逻辑。

### 加载 springSecurityFilterChain

名为 springSecurityFilterChain Bean 实际上是 FilterChainProxy 类，它由 WebSecurity 创建，其代码如下所示：

```java
@Configuration(proxyBeanMethods = false)
public class WebSecurityConfiguration implements ImportAware, BeanClassLoaderAware {
	// WebSecurity 构建
	private WebSecurity webSecurity;
	
	// <1> 构建生成 springSecurityFilterChain, 并注册到 Spring 容器中
	@Bean(name = AbstractSecurityWebApplicationInitializer.DEFAULT_FILTER_NAME)
	public Filter springSecurityFilterChain() throws Exception {
		boolean hasConfigurers = webSecurityConfigurers != null
				&& !webSecurityConfigurers.isEmpty();
		if (!hasConfigurers) {
			WebSecurityConfigurerAdapter adapter = objectObjectPostProcessor
					.postProcess(new WebSecurityConfigurerAdapter() {
					});
			webSecurity.apply(adapter);
		}
		return webSecurity.build();
	}
	
	// ...
}


public final class WebSecurity extends
		AbstractConfiguredSecurityBuilder<Filter, WebSecurity> implements
		SecurityBuilder<Filter>, ApplicationContextAware {
	
	// <2> 构建 FilterChainProxy 对象
	@Override
	protected Filter performBuild() throws Exception {
	
		// <3> 计算 DefaultSecurityFilterChain 数量，包括两个部分：1）忽略 url 的数量；2）HttpSecurity 数量。
		int chainSize = ignoredRequests.size() + securityFilterChainBuilders.size();
		
		List<SecurityFilterChain> securityFilterChains = new ArrayList<>(
				chainSize);
		
		// <4> 构建忽略 url 的 DefaultSecurityFilterChain
		for (RequestMatcher ignoredRequest : ignoredRequests) {
			securityFilterChains.add(new DefaultSecurityFilterChain(ignoredRequest));
		}
		
		// <5> 构建 HttpSecurity 对应的 DefaultSecurityFilterChain
		for (SecurityBuilder<? extends SecurityFilterChain> securityFilterChainBuilder : securityFilterChainBuilders) {
			securityFilterChains.add(securityFilterChainBuilder.build());
		}
		
		// <6> 构建 FilterChainProxy 对象
		FilterChainProxy filterChainProxy = new FilterChainProxy(securityFilterChains);
		if (httpFirewall != null) {
			filterChainProxy.setFirewall(httpFirewall);
		}
		filterChainProxy.afterPropertiesSet();
		
		Filter result = filterChainProxy;
		
		postBuildAction.run();
		return result;
	}
	
	// ....
}

```

- springSecurityFilterChain 对象是在 WebSecurityConfiguration 对象中生成并添加到 Spring 容器中，配置对象则是由 @EnableWebSecurity 注解引入的。开启 @EnableWebSecurity 会全局生成一个 WebSecurity 对象，最后由该对象生成 FilterChainProxy 类；
- FilterChainProxy 的构建逻辑是在 WebSecurity 中进行的，FilterChainProxy 内部维护一个 DefaultSecurityFilterChain 对象列表，而 DefaultSecurityFilterChain 分为两类，一类是忽略的 url 都会生成一个包含 0 个 Filter 的 DefaultSecurityFilterChain 对象，该对象不会做任何拦截操作，等于直接放行，另外一类是安全认证的 Url, 此时它会生成包含一系列 Filter 的 DefaultSecurityFilterChain 对象，具体包括什么 Filter 操作则由 HttpSecurity 配置；


**DefaultSecurityFilterChain**

DefaultSecurityFilterChain 对象包含两个部分，一是 url 匹配器，匹配的 url 都要执行 Filter 列表的控制逻辑，另外一个就是 Filter 列表，由它组成了 Spring Secuirty 的安全控制逻辑。

```java
public final class DefaultSecurityFilterChain implements SecurityFilterChain {

        // <1> url 匹配器，匹配的 url 都要执行 Filter 列表的控制逻辑。
	private final RequestMatcher requestMatcher;

        // <2> Filter 列表
	private final List<Filter> filters;

	public List<Filter> getFilters() {
		return filters;
	}
	
	public boolean matches(HttpServletRequest request) {
		return requestMatcher.matches(request);
	}

}
```

### 构建 DefaultSecurityFilterChain 

DefaultSecurityFilterChain 对象由 HttpSecurity 类构建生成，如下代码所示。在代码中，只是简单对 Filter 列表进行排序，传入 RequestMatcher 和 Filter 列表即可。那这两个对象是怎么来的呢？ 

```java
public final class HttpSecurity extends
		AbstractConfiguredSecurityBuilder<DefaultSecurityFilterChain, HttpSecurity>
		implements SecurityBuilder<DefaultSecurityFilterChain>,
		HttpSecurityBuilder<HttpSecurity> {

        // <1> 构建 DefaultSecurityFilterChain
	@Override
	protected DefaultSecurityFilterChain performBuild() {
		filters.sort(comparator);
		return new DefaultSecurityFilterChain(requestMatcher, filters);
	}
	
	// ...
}
```

**WebSecurityConfigurerAdapter**

Spring Security 提供了很多内置化的配置，直接引入 Spring Security 依赖就可以用。如果用户想自定义一些安全配置，则需要继承 WebSecurityConfigurerAdapter 类，传入相应的配置即可，如本文开头的代码所示：

```java
/**
 *  Spring Security 配置
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig extends WebSecurityConfigurerAdapter {

	// <1> 配置忽略的 url
	@Override
	public void configure(WebSecurity web) {
		web.ignoring().antMatchers("/login.html", "/css/**", "/js/**", "/images/**");
	}
	
	// <2> 配置 HttpSecurity 对象
	@Override
	protected void configure(HttpSecurity http) throws Exception {
		
		http.requestMatchers() // <3> 配置 url 匹配器
				.antMatchers("/login")
				.antMatchers("/oauth/authorize")
				.and()
				.authorizeRequests().anyRequest().authenticated()
				.and()
				.formLogin()  // <4> 配置 FormLoginConfigurer
				.loginPage("/login.html") // <5> 自定义登陆页面
				.loginProcessingUrl("/login") // <6> 自定义登陆处理逻辑，Httpe method 为 POST
				.permitAll()
				.and()
				.csrf().disable();
	}
	
	// 其它方法省略
}
```

- <1> 处配置忽略的 url，每一个 url 在 WebSecurity 中都会生成一个 DefaultSecurityFilterChain 对象；
- <2> 处配置 HttpSecurity 对象，每一个 WebSecurityConfigurerAdapter 对象都会生成一个 HttpSecurity 对象，一个 HttpSecurity 对象代表对一组 url 进行安全配置，在认证服务器中，会默认生成一个 WebSecurityConfigurerAdapter 对象，对 Oauth2 相关的 endponit 进行安全设置；
- <3> 处配置 HttpSecurity 对象的 url 匹配器，表明`/login, /oauth/authorize` 受该 HttpSecurity 控制；
- <4> 处配置表单认证逻辑，该操作会向 HttpSecurity 对象中加入一个 FormLoginConfigurer 对象，该对象最终会向 HttpSecurity 注册 Filter 来实现认证逻辑。
- <5> 与 <6> 处则是修改 FormLoginConfigurer 对象的默认参数，在后续的文章中再详细介绍。

总上所述，我们得出以下结论：
1. HttpSecurity 对象的 RequestMatcher 由 requestMatchers 方法设置，默认是拦截所有的请求，用户可以自己设置；
2. HttpSecurity 对象中的 Filter 列表由一系列的配置对象生成，而每一个配置对象代表了一个安全操作，一个安全操作则对应了一个或多个 Filter。

### 添加 Filter

HttpSecurity 对象中的 Filter 列表由一系列的配置对象生成，以 FormLoginConfigurer 对象为例，它为向 HttpSecurity 对象中添加 UsernamePasswordAuthenticationFilter 对象，如代码如下所示：
```java
public final class FormLoginConfigurer<H extends HttpSecurityBuilder<H>> extends
		AbstractAuthenticationFilterConfigurer<H, FormLoginConfigurer<H>, UsernamePasswordAuthenticationFilter> {

	/**
	* Creates a new instance
	* @see HttpSecurity#formLogin()
	*/
	public FormLoginConfigurer() {
		// <1> 调用父类方法，设置 authFilter 为 UsernamePasswordAuthenticationFilter 对象
		super(new UsernamePasswordAuthenticationFilter(), null);
		usernameParameter("username");
		passwordParameter("password");
	}
	
	@Override
	public void configure(B http) throws Exception {
		
		// <2> 初始化 UsernamePasswordAuthenticationFilter
		authFilter.setAuthenticationManager(http
				.getSharedObject(AuthenticationManager.class));
		authFilter.setAuthenticationSuccessHandler(successHandler);
		authFilter.setAuthenticationFailureHandler(failureHandler);
		if (authenticationDetailsSource != null) {
			authFilter.setAuthenticationDetailsSource(authenticationDetailsSource);
		}
		SessionAuthenticationStrategy sessionAuthenticationStrategy = http
				.getSharedObject(SessionAuthenticationStrategy.class);
		if (sessionAuthenticationStrategy != null) {
			authFilter.setSessionAuthenticationStrategy(sessionAuthenticationStrategy);
		}
		RememberMeServices rememberMeServices = http
				.getSharedObject(RememberMeServices.class);
		if (rememberMeServices != null) {
			authFilter.setRememberMeServices(rememberMeServices);
		}
		
		// <3> 向 HttpSecurity 添加 UsernamePasswordAuthenticationFilter
		F filter = postProcess(authFilter);
		http.addFilter(filter);
	}
	
	// ...
}
```

通过分析 FormLoginConfigurer 代码可知，通过其 configure 方法向 HttpSecurity 对象中添加了 UsernamePasswordAuthenticationFilter 过滤器。Spring Security 默认添加了很多的过滤器，这些过滤器在 WebSecurityConfigurerAdapter 对象中指定的，如下代码所示：

```java
public abstract class WebSecurityConfigurerAdapter implements
		WebSecurityConfigurer<WebSecurity> {
	
	// <1> 构建 HttpSecurity 对象
	protected final HttpSecurity getHttp() throws Exception {
		if (http != null) {
			return http;
		}

		// ...

		http = new HttpSecurity(objectPostProcessor, authenticationBuilder,
				sharedObjects);
		if (!disableDefaults) {
			http
				.csrf() // <2> 添加 csrf 过滤器，由于该功能被 disable,最终没有被加载
				.and()
				.addFilter(new WebAsyncManagerIntegrationFilter()) // <3> 添加 WebAsyncManagerIntegrationFilter 过滤器
				.exceptionHandling().and() // <5> 添加 ExceptionTranslationFilter 过滤器
				.headers().and() // // <6> 添加 HeaderWriterFilter 过滤器 
				.sessionManagement().and() // <7> 添加 SessionManagementFilter 过滤器
				.securityContext().and() // <8> 添加 SecurityContextPersistenceFilter 过滤器
				.requestCache().and() // <9> 添加 RequestCacheAwareFilter 过滤器
				.anonymous().and() // <10> 添加 AnonymousAuthenticationFilter 过滤器
				.servletApi().and() // <11> 添加 SecurityContextHolderAwareRequestFilter 过滤器
				.apply(new DefaultLoginPageConfigurer<>()).and()
				.logout(); // <12> 添加 LogoutFilter 过滤器
			ClassLoader classLoader = this.context.getClassLoader();
			List<AbstractHttpConfigurer> defaultHttpConfigurers =
					SpringFactoriesLoader.loadFactories(AbstractHttpConfigurer.class, classLoader);

			for (AbstractHttpConfigurer configurer : defaultHttpConfigurers) {
				http.apply(configurer);
			}
		}
		configure(http);
		return http;
	}
	
	// ...
}

```

### 小结

总上所述，我们可以得到以下结论：
1. DelegatingFilterProxy 作为一切 Filter 的源头，它代理了 FilterChainProxy 类；
2. FilterChainProxy 由 WebSecurity 对象构建生成，其配置对象是 WebSecurityConfigurerAdapter, 通过它我们可以自定义安全策略；
3. DefaultSecurityFilterChain 是一组 Filter 组合，一般由 HttpSecurity 对象构建生成；
4. DefaultSecurityFilterChain 每一个 Filter 可以通过一系列的 AbstractHttpConfigurer 对象生成，每一个 AbstractHttpConfigurer 对象代表了一个或多个 Filter.

## 整体流程

上文分析了 Spring Security 的整体结构及 Filter 的加载过程，这个章节我们将继续分析这些 Filter 如何协作来完成一个 endpoit 的安全检查工作。一个未认证的 oauth/authorize 接口请求需要经过如下图的流程，为了方便理解，这里省略了不重要的步骤，只留下了关键的环节。

![springsecurity-flow](/images/spring-cloud/springsecurity-flow.jpg "springsecurity-flow")

- `oauth/authorize` 被 Spring Security 拦截，路由对应的 DefaultSecurityFilterChain 中，被 FilterSecurityInterceptor 处理，此时用户未登陆，抛出 AuthenticationException;
- AuthenticationException 被 ExceptionTranslationFilter 捕获，在这里有两个工作：1) 将请求的信息封装成 RequestCache 对象，并保存到 Session, 以便登陆成功之后进行恢复；2）重定向到指定的登陆页面；
- 重定向到登陆页面 `/login.html`, 用户输入用户名及密码，提交给登陆处理 endpoinit, 默认为 `/login, method=POST`; 
- `/login, method=POST` 请求被 UsernamePasswordAuthenticationFilter 拦截，调用 AuthenticationManager 类中的认证方法完成用户认证工作，并返回 Authentication, 该对象包含了用户名及权限数据，方便后期进行权限判断。认证成功之后，从 Session 中取出 RequestCache 对象，重写到 `oauth/authorize`; 
- `oauth/authorize` 重新被请求，RequestCacheAwareFilter 会检查会话中的 endponit 与 `oauth/authorize` 是否匹配，匹配则使用 RequestCache 恢复请求的状态，如 method 方法；
- 请求继续，被 FilterSecurityInterceptor 拦截，取出 Session 中的 Authentication 对象，判断已经认证，直接放行；
- 完成 Spring Security 的检查，请求最终到达 `oauth/authorize` endpoint.

## 总结

至此，我们已经完成对 Spring Security Filter 的分析，包括其整体的结构、Filter 的加载流程以及 Filter 之间的协作。整体处理流程分析的粒度还比较粗，后续将对认证及授权两个环节进行单独地分析。

</br>

**参考：**

----
[1]:https://www.cnkirito.moe/spring-security-7/
[2]:https://www.cnkirito.moe/spring-security-4/

[1. Spring Security(六)—SpringSecurityFilterChain 加载流程深度解析][1]

[2. Spring Security(四)-- 核心过滤器源码分析][2]
