---
title: Springboot 序列：SpringSecurity 认证
date: 2022-04-04 12:14:34
tags:
- Spring Security
- authentication
- 认证
- AuthenticationManager
- DaoAuthenticationProvider
- UserDetails
- Authentication
categories:
- Springboot
---

在之前的文章中讲述了《SpringSecurity 整体架构》，这篇文章承接上篇文章，主要讲述 SpringSecurity 的认证流程及相关的类。

<!-- more -->

## 整体流程

我们以之前文章的代码来分析认证的整体流程，关键步骤如下所示：

![Authentication-flow](/images/spring-cloud/Authentication-flow.jpg "Authentication-flow")

**登陆主要流程：**
1. 用户首先打开登陆页面，页面的 endpoint 为 `login.html, Method: GET`, 该页面直接放行，返回给浏览器渲染展现；
2. 用户输入用户名/密码，执行登陆操作，endpoint 为 `login, Method: POST`, 而 `login` 是我们指定的登陆处理 endpoint; 
3. `login, Method: POST` 请求被 UsernamePasswordAuthenticationFilter 拦截，读取参数构造请求对象 UsernamePasswordAuthenticationToken;
4. 将 UsernamePasswordAuthenticationToken 对象传递给 AuthenticationManager 进行认证，获取 Authentication 对象；
5. AuthenticationManager 是一个接口，在这里使用的是其实现类 ProviderManager, ProviderManager 对象中包含有一组 AuthenticationProvider, 每一个 AuthenticationProvider 代表了一类认证场景，我们可以根据需求自定义 AuthenticationProvider 类实现我们的业务；
6. AuthenticationProvider 的主要功能是将查询用户 UserDetails 对象并将其映射为 Authentication 对象，而每一个 AuthenticationProvider 对象只会针对特定的请求对象进行处理，在这里，由于我们的请求对象是 UsernamePasswordAuthenticationToken, 对应地， AuthenticationProvider 的实现类使用的是 DaoAuthenticationProvider; 
7. DaoAuthenticationProvider 需要获用户的信息，是通过 UserDetailsService 接口来实现的，在这里，我们自定义了 CustomerUserDetailsService 对象，实现从数据库中获取用户信息 UserDetails 对象，而 UserDetails 也是一个接口，需要我们自定义实现；
8. 在 DaoAuthenticationProvider 中获取用户信息 UserDetails 对象，需要将其转化为 Authentication 对象；
9. ProviderManager 对象中获取到 Authentication 对象之后，进行复制操作之后，返回给 UsernamePasswordAuthenticationFilter 对象。这个 Authentication 对象持有用户的账号及权限信息，在后期的授权操作中会被用到。

**登出主要流程：**
1. 登出的 endpoint 为 `logout, Method: GET`, 该 endpoint 被 LogoutFilter 拦截；
2. 在 LogoutFilter 中，登出的业务逻辑封装在 LogoutHandler 对象中，会执行会话的清理操作；
3. 操作成功之后再跳转到登出成功页面。

## 认证相关的类

![AuthenticationManager](/images/spring-cloud/AuthenticationManager.jpg "AuthenticationManager")

- AuthenticationManager: 认证的核心接口，输入为用户请求对象，如 UsernamePasswordAuthenticationToken，输出为认证对象 Authentication; 
- ProviderManager: AuthenticationManager 接口实现类，它包含一组 AuthenticationProvider 对象，而每一个 AuthenticationProvider 代表了一类认证场景，它对应只会处理对应的请求对象；
- DaoAuthenticationProvider: AuthenticationProvider 接口实现类，主要功能是从 UserDetailsService 接口获取用户对象 UserDetails, 将转换为 Authentication 对象；
- UserDetailsService：用户查询接口，根据用户名查询用户信息；
- CustomerUserDetailsService：UserDetailsService 实现类，从数据库中获取用户信息；
- UserDetails: 用户信息接口，包括了获取用户名及权限的方法；
- Authentication: 认证对象对象；

## 用户模型

![UserDetails](/images/spring-cloud/UserDetails.jpg "UserDetails")

在 SpringSecurity 中，定义了 UserDetails 及 Authentication 接口，用于存储用户及认证数据。通过 UserDetails 接口，业务系统可以将用户信息传递给 SpringSecurity, 然后封装成 Authentication, 供后续功能使用。

### UserDeails 接口

```java
public interface UserDetails extends Serializable {

	/**
	 * 获取权限列表
	 *
	 * @return 权限列表
	 */
	Collection<? extends GrantedAuthority> getAuthorities();

	/**
	 * 获取用户密码
	 *
	 * @return the password
	 */
	String getPassword();

	/**
	 * 获取用户名
	 *
	 * @return the username (never <code>null</code>)
	 */
	String getUsername();

	/**
	 * 判断用户是否过期
	 *
	 * @return <code>true</code> if the user's account is valid (ie non-expired),
	 * <code>false</code> if no longer valid (ie expired)
	 */
	boolean isAccountNonExpired();

	/**
	 * 判断用户是否被锁定
	 *
	 * @return <code>true</code> if the user is not locked, <code>false</code> otherwise
	 */
	boolean isAccountNonLocked();

	/**
	 * 判断密码是否过期
	 *
	 * @return <code>true</code> if the user's credentials are valid (ie non-expired),
	 * <code>false</code> if no longer valid (ie expired)
	 */
	boolean isCredentialsNonExpired();

	/**
	 * 判断密码是否可用
	 *
	 * @return <code>true</code> if the user is enabled, <code>false</code> otherwise
	 */
	boolean isEnabled();
}
```

UserDetails 提供了访问用户名称、状态及权限相关的方法，上层业务需要实现自己的 UserDetails 类，如下所示：

```java
public class User implements UserDetails, Serializable {

    private Long id;
    private String username;
    private String password;

    private List<Role> authorities;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    @Override
    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    @Override
    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }

    @Override
    public List<Role> getAuthorities() {
        return authorities;
    }

    public void setAuthorities(List<Role> authorities) {
        this.authorities = authorities;
    }

    // ...

}
```

UserDetails 接口会包含一组权限，SpringSecurity 也定义了权限接口，如下所示：
```java
public interface GrantedAuthority extends Serializable {


	/**
	 * 获取权限
	 *
	 * @return 权限
	 */
	String getAuthority();
}
```

在 GrantedAuthority 接口中，只是简单定义了返回权限名称的方法，业务上层可以进行扩展，用户的角色也包含在权限表中，使用 `ROLE_` 前缀来区分。

### Authentication 接口

Authentication 接口存储认证成功的信息，它由 UserDetails 封装转换而来。

```java
public interface Authentication extends Principal, Serializable {

	/**
	 * 获取权限
	 *
	 * @return 权限列表
	 */
	Collection<? extends GrantedAuthority> getAuthorities();

	/**
	 * 密码 
	 * @return 密码
	 */
	Object getCredentials();

	/**
	 * 获取请求对象相关的信息，如ip
	 *
	 * @return 详情对象
	 */
	Object getDetails();

	/**
	 * 获取用户信息
	 *
	 * @return 用户信息
	 */
	Object getPrincipal();

	/**
	 * 用户是否已经认证通过

	 * @return trur/false
	 */
	boolean isAuthenticated();

	/**
	 * 设置认证结果
	 */
	void setAuthenticated(boolean isAuthenticated) throws IllegalArgumentException;
}
```

在 Authentication 中，将 Principal 定义为用户信息，Credentials 为密码信息，GrantedAuthority 为权限信息，另外还保存了请求对象详情信息。这些信息从 UserDetails, UsernamePasswordAuthenticationToken 中获取到。


```java
public Authentication authenticate(Authentication authentication)
		throws AuthenticationException {
	Assert.isInstanceOf(UsernamePasswordAuthenticationToken.class, authentication,
			() -> messages.getMessage(
					"AbstractUserDetailsAuthenticationProvider.onlySupports",
					"Only UsernamePasswordAuthenticationToken is supported"));

	// Determine username
	String username = (authentication.getPrincipal() == null) ? "NONE_PROVIDED"
			: authentication.getName();

	boolean cacheWasUsed = true;
	UserDetails user = this.getUserDetailsService().loadUserByUsername(username);;

	// ...

	Object principalToReturn = user;

	if (forcePrincipalAsString) {
		principalToReturn = user.getUsername();
	}

	return createSuccessAuthentication(principalToReturn, authentication, user);
}

protected Authentication createSuccessAuthentication(Object principal,
		Authentication authentication, UserDetails user) {
	// Ensure we return the original credentials the user supplied,
	// so subsequent attempts are successful even with encoded passwords.
	// Also ensure we return the original getDetails(), so that future
	// authentication events after cache expiry contain the details
	UsernamePasswordAuthenticationToken result = new UsernamePasswordAuthenticationToken(
			principal, authentication.getCredentials(),
			authoritiesMapper.mapAuthorities(user.getAuthorities()));
	result.setDetails(authentication.getDetails());

	return result;
}

```

通过代码可知：
- UserDetails ---> principal
- UserDetails.getAuthorities() ---> list of GrantedAuthority
- requestAuthentication.getCredentials() ---> credentials
- requestAuthentication..getDetails() ---> details


## 默认设置

**Endpoints**
SpringSecurity 内置登陆/登出相关的 Endpoint, 用户不做任何配置即可使用，这些 Endpoint 包括：
1. /login,GET: 登陆页面，默认由 DefaultLoginPageGeneratingFilter 对象生成;
2. /login,POST: 对用户进行认证, 传入参数 `username` 和 `password` 生成 UsernamePasswordAuthenticationToken, 这两个参数名称可以修改；
3. /login?error: 登陆出错页面；
4. /login?logout: 成功登陆退出后跳转的页面。

**默认参数**
在登陆页面表单中需要配置用户名称及密码，它们的默认名称如下：

1. username: 用户名称；
2. password: 用户密码。

这些默认配置都可以在 `FormLoginConfigurer` 中配置：

```java
FormLoginConfigurer
	   	.usernameParameter("username")
	   	.passwordParameter("password")
	   	.loginPage("/authentication/login")
	   	.failureUrl("/authentication/login?failed")
	   	.loginProcessingUrl("/authentication/login/process")
```

</br>

**参考：**

----
[1]:http://learn.lianglianglee.com/%E4%B8%93%E6%A0%8F/Spring%20Security%20%E8%AF%A6%E8%A7%A3%E4%B8%8E%E5%AE%9E%E6%93%8D/03%20%20%E8%AE%A4%E8%AF%81%E4%BD%93%E7%B3%BB%EF%BC%9A%E5%A6%82%E4%BD%95%E6%B7%B1%E5%85%A5%E7%90%86%E8%A7%A3%20Spring%20Security%20%E7%94%A8%E6%88%B7%E8%AE%A4%E8%AF%81%E6%9C%BA%E5%88%B6%EF%BC%9F.md
[2]:http://learn.lianglianglee.com/%E4%B8%93%E6%A0%8F/Spring%20Security%20%E8%AF%A6%E8%A7%A3%E4%B8%8E%E5%AE%9E%E6%93%8D/02%20%20%E7%94%A8%E6%88%B7%E8%AE%A4%E8%AF%81%EF%BC%9A%E5%A6%82%E4%BD%95%E4%BD%BF%E7%94%A8%20Spring%20Security%20%E6%9E%84%E5%BB%BA%E7%94%A8%E6%88%B7%E8%AE%A4%E8%AF%81%E4%BD%93%E7%B3%BB%EF%BC%9F.md

[1. 03 认证体系：如何深入理解 Spring Security 用户认证机制？][1]

[2. 02 用户认证：如何使用 Spring Security 构建用户认证体系？][2]
