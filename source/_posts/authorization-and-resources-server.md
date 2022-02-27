---
title: Springboot 系列：授权服务器
date: 2022-02-27 11:23:53
tags:
- 认证服务器
- 资源服务器
- SpringSecurity
- Oauth2
- Jwt
categories:
- Springboot
---

授权服务器是一个系统中比较重要的模块，主要提供请求的访问认证和资源的授权。在这里，使用 SpringSecurity + Oauth2 + Jwt 实现一个授权服务器。

<!-- more -->

## 背景

Spring Security OAuth 项目提供了基于 Oauth2 的授权服务器 (Authorization Server)，Springboot 和 Springcloud 对其进行了封装，可以很方便引入。目前 Spring Security OAuth 项目已经被弃用，相关的功能会迁移到 Spring Security 5 中，不过并没有包含授权服务器，这意味着使用最新的 Spring Security 5 版本将不能使用授权服务器。官方建议使用第三方的授权服务器，不过鉴于开发者的强烈反馈。Spring 官方发起了 [Spring Authorization Server](https://github.com/spring-projects/spring-authorization-server) 项目，该项目是由 Spring Security 主导的一个社区驱动项目，旨在向 Spring 社区提供授权服务器支持，目前的版本是 V 0.2.2，还没有达到 GA 的标准。

考虑到 Spring Authorization Server 项目还没有稳定，在这里仍然使用 Spring Security OAuth 项目。<strong style="color:red"> Springboot 2.3.4 版本后 Spring Security 5.2.x. 不支持 Authorization Server </strong>, 需要选取之前的版本。

上面进到可以通过 Springboot 和 Springcloud 两种方式引入授权服务器 (Authorization Server)，其中 Springboot 引入的包如下：
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-oauth2-client</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-oauth2-resource-server</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.security.oauth.boot</groupId>
    <artifactId>spring-security-oauth2-autoconfigure</artifactId>
</dependency>
```

Springcloud 包：
```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-oauth2</artifactId>
</dependency>

<dependency>
    <groupId>org.springframework.security</groupId>
    <artifactId>spring-security-oauth2-jose</artifactId>
</dependency>
```

只要选择其中一种即可，在这里使用的 Springcloud 的方式，版本如下：
```xml
<spring-boot.version>2.2.2.RELEASE</spring-boot.version>
<spring-cloud.version>Hoxton.SR9</spring-cloud.version>
```

<strong style="color:red">注意： Springboot 2.3.4 版本后 Spring Security 5.2.x. 不支持 Authorization Server</strong>

## 授权服务器
### 整体流程
配置 Spring Security OAuth 授权服务器，需要对 Oauth2 协议有所了解，如果不了解可以参考这两篇文章： [OAuth 2.0 协议](https://oauth.net/2/), [理解 OAuth 2.0](https://www.ruanyifeng.com/blog/2014/05/oauth_2_0.html). 

配置授权服务器包含以下步骤：
1. 初始化数据库表，包括存储客户端、token 及用户等信息的表；
2. 配置用户读取及认证的方式；
3. 配置客户端及 token 存储及读取方式；
4. 配置 JWT; 
5. 配置授权相关的 endpoint.

### 初始化数据库表
在这里需要存储两类数据库表，一类是 Oauth2 相关的表，包括客户端及 token 表，这个可以由 Spring 官方提供。另一类是业务相关的用户权限的表，它们的表结构如下：

1. Oauth2 表

```sql
-- ----------------------------
-- Table structure for clientdetails
-- ----------------------------
DROP TABLE IF EXISTS `clientdetails`;
CREATE TABLE `clientdetails` (
  `appId` varchar(128) NOT NULL,
  `resourceIds` varchar(256) DEFAULT NULL,
  `appSecret` varchar(256) DEFAULT NULL,
  `scope` varchar(256) DEFAULT NULL,
  `grantTypes` varchar(256) DEFAULT NULL,
  `redirectUrl` varchar(256) DEFAULT NULL,
  `authorities` varchar(256) DEFAULT NULL,
  `access_token_validity` int(11) DEFAULT NULL,
  `refresh_token_validity` int(11) DEFAULT NULL,
  `additionalInformation` varchar(4096) DEFAULT NULL,
  `autoApproveScopes` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`appId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for oauth_access_token
-- ----------------------------
DROP TABLE IF EXISTS `oauth_access_token`;
CREATE TABLE `oauth_access_token` (
  `token_id` varchar(256) DEFAULT NULL,
  `token` blob,
  `authentication_id` varchar(128) NOT NULL,
  `user_name` varchar(256) DEFAULT NULL,
  `client_id` varchar(256) DEFAULT NULL,
  `authentication` blob,
  `refresh_token` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`authentication_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for oauth_approvals
-- ----------------------------
DROP TABLE IF EXISTS `oauth_approvals`;
CREATE TABLE `oauth_approvals` (
  `userId` varchar(256) DEFAULT NULL,
  `clientId` varchar(256) DEFAULT NULL,
  `scope` varchar(256) DEFAULT NULL,
  `status` varchar(10) DEFAULT NULL,
  `expiresAt` datetime DEFAULT NULL,
  `lastModifiedAt` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for oauth_client_details
-- ----------------------------
DROP TABLE IF EXISTS `oauth_client_details`;
CREATE TABLE `oauth_client_details` (
  `client_id` varchar(128) NOT NULL,
  `resource_ids` varchar(256) DEFAULT NULL,
  `client_secret` varchar(256) DEFAULT NULL,
  `scope` varchar(256) DEFAULT NULL,
  `authorized_grant_types` varchar(256) DEFAULT NULL,
  `web_server_redirect_uri` varchar(256) DEFAULT NULL,
  `authorities` varchar(256) DEFAULT NULL,
  `access_token_validity` int(11) DEFAULT NULL,
  `refresh_token_validity` int(11) DEFAULT NULL,
  `additional_information` varchar(4096) DEFAULT NULL,
  `autoapprove` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`client_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for oauth_client_token
-- ----------------------------
DROP TABLE IF EXISTS `oauth_client_token`;
CREATE TABLE `oauth_client_token` (
  `token_id` varchar(256) DEFAULT NULL,
  `token` blob,
  `authentication_id` varchar(128) NOT NULL,
  `user_name` varchar(256) DEFAULT NULL,
  `client_id` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`authentication_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for oauth_code
-- ----------------------------
DROP TABLE IF EXISTS `oauth_code`;
CREATE TABLE `oauth_code` (
  `code` varchar(256) DEFAULT NULL,
  `authentication` blob
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Table structure for oauth_refresh_token
-- ----------------------------
DROP TABLE IF EXISTS `oauth_refresh_token`;
CREATE TABLE `oauth_refresh_token` (
  `token_id` varchar(256) DEFAULT NULL,
  `token` blob,
  `authentication` blob
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
```

为了测试，加入了两个客户端 dev 和 oauth2，dev 用于接口访问，oauth2 用于资源服务器。

```sql
-- ----------------------------
-- Records of oauth_client_details
-- ----------------------------
INSERT INTO `oauth_client_details` VALUES ('dev', 'oauth2', 'dev', 'app', 'password,client_credentials,authorization_code,refresh_token', 'http://www.example.com', '', '3600', '3600', '{\"country\":\"CN\",\"country_code\":\"086\"}', 'false');
INSERT INTO `oauth_client_details` VALUES ('oauth2', '', 'oauth2', 'app', 'password,client_credentials,authorization_code,refresh_token', 'http://www.example.com', '', '3600', '3600', '{\"country\":\"CN\",\"country_code\":\"086\"}', 'false');

```

2. 用户权限表

```sql
-- ----------------------------
-- Table structure for user
-- ----------------------------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(255) COLLATE utf8_bin NOT NULL,
  `password` varchar(255) COLLATE utf8_bin NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

-- ----------------------------
-- Records of user
-- ----------------------------
INSERT INTO `user` VALUES ('1', 'user', 'e10adc3949ba59abbe56e057f20f883e');
INSERT INTO `user` VALUES ('2', 'admin', 'e10adc3949ba59abbe56e057f20f883e');
```

为了简单起见，只创建了一个用户表，并添加了两个用户，密码为 **123456**. 


### 配置用户认证信息

在 Spring security 中提供了通用的认证功能，需要指定三个信息，分别是：
1. UserDetailsService: 用户查询接口；
2. UserDetails: 用户详情；
3. PasswordEncoder: 用于密码字段的加解密。

**UserDetailsService**
定义了如何获取用户信息，它是一个接口，定义了一个根据用户名称获取用户的方法，定义如下：
```java
public interface UserDetailsService {
    // 根据用户名返回用户信息
    UserDetails loadUserByUsername(String var1) throws UsernameNotFoundException;
}
```

**UserDetails**
定义了一个用户具备什么元素，它也是一个接口，其定义如下：
```java
public interface UserDetails extends Serializable {
    // 返回用户具有的权限
    Collection<? extends GrantedAuthority> getAuthorities();

    // 获取用户密码
    String getPassword();

    // 获取用户名称
    String getUsername();

    // 用户是否已经过期
    boolean isAccountNonExpired();

    // 用户是否被锁定
    boolean isAccountNonLocked();

    // 密码是否过期
    boolean isCredentialsNonExpired();

    // 用户是否有效
    boolean isEnabled();
}
```

**PasswordEncoder**
用于用户密码字段的加密及验证，其定义如下：
```java
public interface PasswordEncoder {
    // 密码加密
    String encode(CharSequence var1);

    // 密码匹配验证
    boolean matches(CharSequence var1, String var2);

    default boolean upgradeEncoding(String encodedPassword) {
        return false;
    }
}
```

 WebSecurityConfigurerAdapter 类是 Spring security 中提供给用户进行安全配置的类，用户验证的功能也是在这个类进行配置。我们只需要继承该类加入我们的自定义配置即可，代码如下：
 ```java
@Configuration
// 1. 开启 WebSecurity
@EnableWebSecurity
public class SecurityConfig extends WebSecurityConfigurerAdapter {

    // 2. 自定义 serDetailsService 类
    @Autowired
    private MyUserDetailsService userService;

    @Override
    protected void configure(AuthenticationManagerBuilder auth) throws Exception {

        // 3. 注册 serDetailsService 类
        auth.userDetailsService(userService)
        // 4. 注册 PasswordEncoder类
        .passwordEncoder(new PasswordEncoder() {
            // 对密码进行加密
            @Override
            public String encode(CharSequence charSequence) {
                return DigestUtils.md5DigestAsHex(charSequence.toString().getBytes());
            }

            // 对密码进行判断匹配
            @Override
            public boolean matches(CharSequence charSequence, String s) {
                String encode = DigestUtils.md5DigestAsHex(charSequence.toString().getBytes());
                boolean res = s.equals(encode);
                return res;
            }
        });

    }

    /**
     * 返回 AuthenticationManager 类，在 Oauth2 中会复用该类进行用户的认证。
     * @return AuthenticationManager
     * @throws Exception 异常
     */
    @Override
    @Bean
    public AuthenticationManager authenticationManagerBean() throws Exception {
        return super.authenticationManager();
    }

    /**
     * 用于 Http Basic 认证方式中，用户名/密码的验证
     * 在 oauth2 中 clientId/secret 的验证，此时不用密码不用加密
     * @return PasswordEncoder
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new PasswordEncoder() {
            @Override
            public String encode(CharSequence charSequence) {
                return charSequence.toString();
            }

            @Override
            public boolean matches(CharSequence charSequence, String s) {
                return Objects.equals(charSequence.toString(), s);
            }
        };
    }

}
```

### 配置客户端及 Token 相关信息
授权服务器相关的配置在 AuthorizationServerConfigurerAdapter 中配置，整体框架如下所示：
```java
@Configuration
// 1. 开启 AuthorizationServer 配置
@EnableAuthorizationServer
public class AuthorizationServerConfiguration extends AuthorizationServerConfigurerAdapter {

    /**
     * 2. 注入权限验证控制器 来支持 password grant type
     */
    @Autowired
    private AuthenticationManager authenticationManager;

    /**
     * 3. 注入userDetailsService，开启refresh_token需要用到
     */
    @Autowired
    private MyUserDetailsService userDetailsService;

    /**
     * 4. 注入 tokenStore
     * 保存 token的方式，一共有五种，分别是：
     * 1. Memory
     * 2. Jwt
     * 3. Jwk
     * 4. jdbc
     * 5. redis
     */
    @Autowired
    private TokenStore tokenStore;

    // 5. 配置 tokenStore
    @Bean
    public TokenStore tokenStore() {
    }

    // 6. 配置接口的安全设置，如访问权限等等
    @Override
    public void configure(AuthorizationServerSecurityConfigurer security) throws Exception {
    }

    // 7. 配置客户端访问服务
    @Override
    public void configure(ClientDetailsServiceConfigurer clients) throws Exception {
    }

    // 8. 配置 endpoint 
    @Override
    public void configure(AuthorizationServerEndpointsConfigurer endpoints) throws Exception {
    }
}
```

**客户端配置**

客户端的相关设置是在 ClientDetailsServiceConfigurer 类进行的，在这里，将 Client 信息存储到 Mysql 中，其配置如下：
```java
@Override
public void configure(ClientDetailsServiceConfigurer clients) throws Exception {
    // 1. 自定义 ClientDetailsService，可以加入缓存等技术
    CustomClientDetailsService clientDetailsService = new CustomClientDetailsService(dataSource);
    clients.withClientDetails(clientDetailsService);

    // 2. 使用自带的 JdbcClientDetailsService
    // clients.jdbc(dataSource);
}
```

JdbcClientDetailsService 类封装了访问 oauth_client_details 表的 sql 方法，默认是直接访问数据库，可以根据需要，自定义 JdbcClientDetailsService 类，扩展功能，如加入缓存。

**Tokenstore配置**
TokenStore 封装了存取 token 的方式，它有五种存储方式，分别是：1) Memory; 2) Jwt; 2) Jwk; 4) jdbc (db); 5) Redis。可以根据需要，自行选择，在这里我们使用 Redis 的存储方式，需要额外引入相关的 Jar 包。配置方式如下：

```java
public TokenStore tokenStore() {

    // Redis tokenStore
    return new RedisTokenStore(connectionFactory);

    // Jwt TokenStore
    /* return new JwtTokenStore(jwtAccessTokenConverter());*/
}
```

<strong style="color:red">说明：token 使用 JWT token, tokenstore 也可以选择 redis, 不代表使用 Jwt, tokenstore 就一定要使用 Jwt 模式。</strong>

### 配置 JWT

授权服务器在默认情况下生成的 token 是类似一个 uuid 的随机字串，它本身不携带任何用户信息，资源服务器验证 token 的有效性都需要通过授权服务器进行，会加大网络开销。Jwt 则不同，它本身可以携带不敏感的业务信息，如用户名及权限消息，只需要向授权服务器获取一次签名字段的密钥（对称密钥或非对称密钥），在客户端（或资源服务器）就可以在本地验证 token 的有效性，有效提高系统的效率。

Jwt 的格式如下：
1. Header: JSON 对象，用来描述 JWT 的元数据,alg 属性表示签名的算法,typ 标识 token 的类型；
2. Payload: JSON 对象，重要部分，除了默认的字段，还可以扩展自定义字段，比如用户 ID、姓名、角色等等；
3. Signature: 对 Header、Payload 这两部分进行签名，授权服务器使用私钥签名，然后在资源服务器使用公钥验签，保证数据不被篡改。

配置的流程包括：
1. 设置 JwtAccessTokenConverter, 加入对 Jwt 的支持；
2. 设置 Jwt 签名密钥；
3. 设置 TokenEnhancer, 可以加入额外的业务信息；
4. 将 1),4) 加入到授权服务器中。

**设置 JwtAccessTokenConverter, 将设置签名密钥**
```java
/**
 * 使用非对称加密算法对token签名
 */
@Bean
public JwtAccessTokenConverter jwtAccessTokenConverter() {
    JwtAccessTokenConverter converter = new JwtAccessTokenConverter();
    converter.setKeyPair(keyPair());
    return converter;
}

/**
 * 从classpath下的密钥库中获取密钥对(公钥+私钥)
 */
@Bean
public KeyPair keyPair() {

    KeyStoreKeyFactory keyStoreKeyFactory = new KeyStoreKeyFactory(
            new ClassPathResource("oauth2.jks"), "123456".toCharArray());
    KeyPair keyPair = keyStoreKeyFactory.getKeyPair("oauth2");

    return keyPair;
}
```

Jwt 签名有对称和非对称两种方式：
1. 对称方式：授权服务器和资源服务器使用同一个密钥进行加签和验签 ，默认算法 HMAC; 
2. 非对称方式：授权服务器使用私钥加签，资源服务器使用公钥验签，默认算法 RSA;

项目中使用 RSA 非对称签名方式，具体实现步骤如下：
1. 从密钥库获取密钥对(密钥 + 私钥)，如 oauth2.jks;
2. 授权服务器使用私钥对 token 签名；
3. 授权服务器提供 /oauth/token_key 接口，资源服务器通过该接口获取公钥，验证 token 签名。

密钥库可以通过下面的命令生成：
```bash
keytool -genkey -alias oauth2 -keyalg RSA -keystore oauth2.jks -storepass 123456

```

**参数说明：**
- -genkey 生成密钥
- -alias 别名
- -keyalg 密钥算法
- -keypass 密钥口令
- -keystore 生成密钥库的存储路径和名称
- -storepass 密钥库口令

**设置 TokenEnhancer**

```java
/**
 * JWT内容增强
 */
@Bean
public TokenEnhancer tokenEnhancer() {
    return (accessToken, authentication) -> {
        Map<String, Object> map = new HashMap<>(2);
        User user = (User) authentication.getUserAuthentication().getPrincipal();
        map.put("userId", user.getId());
        ((DefaultOAuth2AccessToken) accessToken).setAdditionalInformation(map);
        return accessToken;
    };
}
```

可以向 Jwt 中加入 userId 等业务字段。

**将配置加入到授权服务器**

```java
@Override
public void configure(AuthorizationServerEndpointsConfigurer endpoints) throws Exception {
    TokenEnhancerChain tokenEnhancerChain = new TokenEnhancerChain();
    tokenEnhancerChain.setTokenEnhancers(
            Arrays.asList(tokenEnhancer(), jwtAccessTokenConverter()));
	// 加入 Jwt 支持
    endpoints.tokenEnhancer(tokenEnhancerChain);
	
	...
}
```

通过 AuthorizationServerEndpointsConfigurer 类加入 Jwt 支持。

### 配置 endpoint

授权服务器提供了如下 endpoint :
- /oauth/authorize：授权端点
- /oauth/token：获取令牌端点
- /oauth/confirm_access：用户确认授权端点
- /oauth/check_token：校验令牌端点
- /oauth/error：用于在授权服务器中呈现错误
- /oauth/token_key：获取 jwt 公钥端点

为了让资源服务器可以访问这些 endpoint, 需要开通访问权限。

```java
@Override
public void configure(AuthorizationServerSecurityConfigurer security) throws Exception {
    // 允许静表单访问
    security.tokenKeyAccess("permitAll()")
            .checkTokenAccess("permitAll()")
            .allowFormAuthenticationForClients();
}

```

最后，Jwt, tokenstore, authenticationManager 及 userDetailsService 加入到 AuthorizationServerEndpointsConfigurer 中，完成对授权服务器的配置

```java
@Override
public void configure(AuthorizationServerEndpointsConfigurer endpoints) throws Exception {
    TokenEnhancerChain tokenEnhancerChain = new TokenEnhancerChain();
    tokenEnhancerChain.setTokenEnhancers(
            Arrays.asList(tokenEnhancer(), jwtAccessTokenConverter()));
    // 加入 Jwt 支持
    endpoints.tokenEnhancer(tokenEnhancerChain);

    //开启密码授权类型
    endpoints.authenticationManager(authenticationManager);
    //配置token存储方式
    endpoints.tokenStore(tokenStore);
    //自定义登录或者鉴权失败时的返回信息
    // endpoints.exceptionTranslator(webResponseExceptionTranslator);
    //要使用refresh_token的话，需要额外配置userDetailsService
    endpoints.userDetailsService(userDetailsService);

}
```

## 资源服务器

配置资源服务器相对比较简单，包含如下流程。

### 引入依赖包
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>

<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-oauth2</artifactId>
</dependency>

<dependency>
    <groupId>org.springframework.security</groupId>
    <artifactId>spring-security-oauth2-jose</artifactId>
</dependency>
```

### 配置 ResourceServer

继承 ResourceServerConfigurerAdapter 类，并进行相关的配置

```java
@Slf4j
@Configuration
// 1. 开启 ResourceServer
@EnableResourceServer
public class ResourceServerConfig extends ResourceServerConfigurerAdapter {

    /**
     * 2. 读取配置文件
     */
    @Autowired
    private ResourceServerProperties resourceServerProperties;

    @Override
    public void configure(ResourceServerSecurityConfigurer resources) throws Exception {
        // 3. 设置资源服务器的 id
        resources.resourceId(resourceServerProperties.getResourceId());
    }

    /**
     * 4. 设置需要 token 验证的 url
     */
    @Override
    public void configure(HttpSecurity http) throws Exception {
        http.requestMatchers().antMatchers("/hello")
                .and()
                .authorizeRequests()
                .antMatchers("/hello").authenticated();
    }
}
```

### 配置访问 URL
设置授权服务器 URL，如 check_token 及 token_key，同时可以设置公钥信息。

```yml
security:
  oauth2:
    resource:
      token-info-uri: http://localhost:8080/oauth/check_token
      id: oauth2
      jwt:
        key-uri: http://localhost:8080/oauth/token_key
        # 如果没有配置这项，会自动从授权服务器获取
        key-value: |
          -----BEGIN PUBLIC KEY-----
          MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAiNMiywFLjao8P86kkhwu
          49Ycys35RRZaKgqZ6JNtbgFq5dCA2kBtdArhm2GS2zplOyPGDlog3r9Ka2jA33Pf
          A9vl60zq1oI1AAAd8CLnyTvIekCnpwaGeBfYFv++LwhWPPT617XVhmF46c25F29t
          tMnGuzHzqKprysgdfBaIXUKZkMeVudGSLPgR0RjZvcM8MMs1cZ1rAISRgIT/D1RL
          Do/HhQkKOvhW2IrQgrqrgu+R/V+7AqS6dz/YAdroYpcBoXKSai+HtZ6yTDxrWdxh
          pbaTCvW2M/IObYVZaHpdOYNTufOzR6+w4SXagT++OopWEQ8w1vLKQzHk+uTrBfzQ
          kQIDAQAB
          -----END PUBLIC KEY-----
    client:
      access-token-uri: http://localhost:8080/oauth/token
      client-id: oauth2
      client-secret: oauth2
      grant-type: authorization_code,password,refresh_token
      scope: all
```

### 开发资源接口

接下来我们开发需要受保护的 RESTFul 接口。

```java
@RestController
public class HelloController {

    @GetMapping("/hello")
    public String hello(String name){
        return "hello , " + name;
    }

}

```

## 测试

### 获取 Jwt token

```bash
$ curl -X POST -d "username=admin&password=123456&grant_type=password&client_id=dev&client_secret=dev" http://localhost:8080/oauth/token | json_pp
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  1502    0  1420  100    82   1283     74  0:00:01  0:00:01 --:--:--  1359
{
   "access_token" : "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsib2F1dGgyIl0sInVzZXJfbmFtZSI6ImFkbWluIiwic2NvcGUiOlsiYXBwIl0sImV4cCI6MTY0NTk2ODc5NSwidXNlcklkIjoyLCJhdXRob3JpdGllcyI6WyJBRE1JTiJdLCJqdGkiOiI0NzFkMzk3MC0xNzkzLTQ0MTQtOWIyYS0xOGNjMjRiMGJjOGIiLCJjbGllbnRfaWQiOiJkZXYifQ.gRcGmDAxdL4Kfmn3zyaIOo-5aceZs_DUYQz656bQbeDr7kdKJyf0BhVSbkUrgVUtqH6SmKIRZlxaDFY56Bf-QMWQ7tR__2q47wvom932tItmd31QShyMqmzBYzAkm1oM-lSo6bGNqip04x4kRjdCdk6cd49IekW3tfFBotUIYbd7GmXbDjNrDSQZEUEBa--R6kX4JAJdOE_AgM8nnEtHa5ng8Plnx6_lWnEvo2k0H5oKLMlmtYIGjmDjQlkNs22XP7t6-pvSLYyUOjv9XeTjpJw58Ss7_gJMgSNCZ48IW1hRF4tPJigjzD88UQsjgrjB5UX2kBUiTHLZCjcIEUbLfQ",
   "expires_in" : 3599,
   "jti" : "471d3970-1793-4414-9b2a-18cc24b0bc8b",
   "refresh_token" : "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsib2F1dGgyIl0sInVzZXJfbmFtZSI6ImFkbWluIiwic2NvcGUiOlsiYXBwIl0sImF0aSI6IjQ3MWQzOTcwLTE3OTMtNDQxNC05YjJhLTE4Y2MyNGIwYmM4YiIsImV4cCI6MTY0NTk2ODc5NSwidXNlcklkIjoyLCJhdXRob3JpdGllcyI6WyJBRE1JTiJdLCJqdGkiOiJmN2Q2NzVjOS1iOGY5LTQ3YmUtYjAxYi1jYmRiMTA2NzlhNDMiLCJjbGllbnRfaWQiOiJkZXYifQ.a5LcQyHn3FmbbcMI-5xgqr9kjZ1blSTKn8YoiayBwF_wVhFMJnOgbchv2st5jEPR2C5PpjfyeLOFBYoHhj1pm9bGBcnQCcMTmyyolulg6OfMju59xHXeLCHBsOWI8L38hWmtqay-P-2PHnRqL2oGBt95D01mxoVmztxVHa9k4S9aLNbL4x6AmThCFZK7DOzpstA4mdy9FpO1UJGVHQxERaXyyxOZtzSMR6Sd7-i34W0bCPe8YAjiVY4I0VqzKamodmek15b3R51Yl97JsT6ffi6Y31jkT_H_9CPUM9hFN5GgEkXsxoIVyRD44IvcJDKtbUY-e6Fl-NqbO3RTLNsPZw",
   "scope" : "app",
   "token_type" : "bearer",
   "userId" : 2
}

```

### 访问资源服务器

带上 access_token 访问资源服务器。

```bash
$ curl http://localhost:9091/hello?name=world \
>   -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsib2F1dGgyIl0sInVzZXJfbmFtZSI6ImFkbWluIiwic2NvcGUiOlsiYXBwIl0sImV4cCI6MTY0NTk2ODc5NSwidXNlcklkIjoyLCJhdXRob3JpdGllcyI6WyJBRE1JTiJdLCJqdGkiOiI0NzFkMzk3MC0xNzkzLTQ0MTQtOWIyYS0xOGNjMjRiMGJjOGIiLCJjbGllbnRfaWQiOiJkZXYifQ.gRcGmDAxdL4Kfmn3zyaIOo-5aceZs_DUYQz656bQbeDr7kdKJyf0BhVSbkUrgVUtqH6SmKIRZlxaDFY56Bf-QMWQ7tR__2q47wvom932tItmd31QShyMqmzBYzAkm1oM-lSo6bGNqip04x4kRjdCdk6cd49IekW3tfFBotUIYbd7GmXbDjNrDSQZEUEBa--R6kX4JAJdOE_AgM8nnEtHa5ng8Plnx6_lWnEvo2k0H5oKLMlmtYIGjmDjQlkNs22XP7t6-pvSLYyUOjv9XeTjpJw58Ss7_gJMgSNCZ48IW1hRF4tPJigjzD88UQsjgrjB5UX2kBUiTHLZCjcIEUbLfQ"
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    13  100    13    0     0    114      0 --:--:-- --:--:-- --:--:--   115

hello , world

```

</br>

**[代码库：https://github.com/noahsarkzhang-ts/springboot-lab](https://github.com/noahsarkzhang-ts/springboot-lab)**

</br>

**参考：**

----
[1]:https://oauth.net/2/
[2]:https://www.ruanyifeng.com/blog/2014/05/oauth_2_0.html
[3]:https://segmentfault.com/a/1190000040295266
[4]:https://mp.weixin.qq.com/s/0PAUErDh0qmcR4SUsTn15Q?spm=a2c6h.12873639.0.0.4c8d6b9bPR8JCI
[5]:https://www.cnblogs.com/haoxianrui/p/13719356.html

[1. OAuth 2.0 协议][1]

[2. 理解 OAuth 2.0][2]

[3. 微服务中使用Spring Security + OAuth 2.0 + JWT 搭建认证授权服务][3]

[4. Spring Boot Security 整合 OAuth2 设计安全API接口服务][4]

[5. Spring Cloud实战 | 第六篇：Spring Cloud Gateway + Spring Security OAuth2 + JWT实现微服务统一认证授权鉴权][5]
