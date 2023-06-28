---
title: 搭建CAS服务器
date: 2019-05-19 20:57:44
updated: 2019-05-19 20:57:44
tags: 
- CAS
- SSO
- 自定义登陆页面
- 验证码
categories: 
- Springboot
---

**环境说明：**
JDK：1.8.0_111
Tomcat：8.5.40
Cas-Server：5.3.9
Template：thymeleaf

搭建一个基本的CAS服务器过程如下：
- 下载CAS Overlay template，以5.3.9版本为例：
地址为：https://github.com/apereo/cas-overlay-template/tree/5.3
- 配置SSL环境；
- 自定义登录页面；
- 自定义用户鉴权；
- 加入验证码；
- 自定义登录错误信息；

<!-- more -->

## 1、下载CAS overlay template 
使用5.3的分支，命令如下：
```bash
git clone -b 5.3 https://github.com/apereo/as-overlay-template.git
```
使用CAS overlay template的好处就是将用户修改的代码与官方CAS代码隔离开，在打包时通过maven overlay技术将用户代码与官方CAS代码合并打包，同名文件会被覆盖。这样做的目的是方便代码的维护及升级。在实例中使用的是官方5.3.9的包，overlay配置如下：
```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-war-plugin</artifactId>
    <version>2.6</version>
    <configuration>
        <warName>cas</warName>
        <failOnMissingWebXml>false</failOnMissingWebXml>
        <recompressZippedFiles>false</recompressZippedFiles>
        <archive>
            <compress>false</compress>
            <manifestFile>${manifestFileToUse}</manifestFile>
        </archive>
        <overlays>
            <overlay>
                <groupId>org.apereo.cas</groupId>
                <artifactId>cas-server-webapp${app.server}</artifactId>
            </overlay>
        </overlays>
    </configuration>
</plugin>
```

在上面的配置文件中是以org.apereo.cas: cas-server-webapp-tomcat:5.3.9为模板（在项目中app.server为-tomcat），将工程中的文件与该war进行合并，最终输出为cas.war的包。

## 2、配置SSL环境
### 2.1 生成证书
在下载的工程目录中有一个build.cmd的命令，可以使用bulid gencert生成证书，在该命令中域名默认为cas.example.org，可根据需要进行更改，以默认域名为例，配置如下：
```bash
@rem Call this script with DNAME and CERT_SUBJ_ALT_NAMES already set to override
@if "%DNAME%" == "" set DNAME=CN=cas.example.org,OU=Example,OU=Org,C=US
```
生成的thekeystore文件默认是在当前盘的\etc\cas目录下。

### 2.2 在hosts文件中配置域名与地址
```bash
127.0.0.1 cas.example.org
```

### 2.3 在工程中配置开启SSL
在application.properties配置文件中配置如下：
```
server.ssl.enabled=true
server.ssl.key-store=file:e:/etc/cas/thekeystore
server.ssl.key-store-password=changeit
server.ssl.key-password=changeit
```

- server.ssl.enabled：表示是否开启SSL
- server.ssl.key-store, server.ssl.key-store-password, server.ssl.key-passwords可以在生成证书时指定，这里使用默认即可。

**说明：** 文件在resources目录下，默认为空，可以往里面添加内容，覆盖默认的配置。

### 2.4 在Service文件中设置HTTPS
```json
{
  "@class" : "org.apereo.cas.services.RegexRegisteredService",
  "serviceId" : "^(https|imaps|http)://*",
  "name" : "BASE",
  "id" : 1000,
  "description" : "BASE",
  "evaluationOrder" : 10,
  "theme" : "base"
}
```
在ServiceId中配置支持的协议，可以根据需要添加或删除协议类型，默认的service文件是HTTPSandIMAPS-10000001.json文件，要对其进行修改，可以将它拷贝到工程/resources/services/目录下。

**说明：** Service是一个很强大的功能，可以配置对特定的URL使用不同的验证逻辑，使用不同的主题，这对于自定义登录页面很有用，可以达到不同的URL可以有不同的登录页面。

### 2.5 在tomcat中配置证书
在server.xml中对证书进行配置，使得tomcat支持SSL：
```xml
<Connector port="8443" protocol="org.apache.coyote.http11.Http11Protocol"
               maxThreads="150" SSLEnabled="true" scheme="https" secure="true"
               clientAuth="false" sslProtocol="TLS" keystoreFile="E:/etc/cas/thekeystore" keystorePass="changeit"  />
```

## 3、自定义登录页面
在这里结合service及theme来实现自定义登录页面，这样做的好处是不同的theme可以隔离，添加一个主题或删除一个主题，对目录进行操作即可。
### 3.1 添加Service
在resources/services目录下新建一个service文件，如BASE-1000.json，文件内容如下：
```json
{
  "@class" : "org.apereo.cas.services.RegexRegisteredService",
  "serviceId" : "^(https|imaps|http)://*",
  "name" : "BASE",
  "id" : 1000,
  "description" : "BASE",
  "evaluationOrder" : 10,
  "theme" : "base"
}
```
- @class：验证逻辑，默认即可
- serviceId：配置url的正则表达式，url匹配则使用该service。
- name：名称
- id：唯一标识id,不能冲突
- description：描述
- evaluationOrder：定义验证的顺序
- theme：使用的主题

### 3.2 定义JS,CSS等文件
在static目录下新建themes/base目录，需要以theme名称命名，所使用的静态文件统一放在该目录下，如下所示：
```bash
static
└─themes
    └─base
        ├─css
        ├─fonts
        ├─images
        └─js
```
### 3.3 定义theme属性文件
在resources下新建以theme名称命名的属性文件，如base.properties，在该文件中定义文件路径，方便在模板中引用，如下所示：
```properties
cas.standard.css.file=/css/cas.css
# base theme
cas.ico.shortcut=/themes/base/images/favicon.ico
cas.css.bootstrap=/themes/base/css/bootstrap.min.css
cas.css.font=/themes/base/css/font-awesome.min.css
cas.css.animate=/themes/base/css/animate.min.css
cas.css.style=/themes/base/css/style.min.css
cas.css.whole=/themes/base/css/whole.css
cas.css.login=/themes/base/css/login.css
cas.css.layer=/themes/base/js/plugins/layer/skin/layer.css
cas.css.layer.ext=/themes/base/js/plugins/layer/skin/layer.ext.css
cas.page.title=BASE CAS Server
```

### 3.4 定义模板文件
在resources下新建templates/base目录，在该目录下存放登录页面casLoginView.html，目录如下所示：
```bash
templates
└─base
     └─ casLoginView.html
```
casLoginView.html文件为登录页面文件，可以根据需要，使用定制的css,js及字体文件，这些文件在 theme属性文件中定义，在模板文件中可以直接使用，如下所示：
```html
<link rel="shortcut icon" th:href="@{${#themes.code('cas.ico.shortcut')}}" />
<link rel="stylesheet" th:href="@{${#themes.code('cas.css.bootstrap')}}" />
<link rel="stylesheet" th:href="@{${#themes.code('cas.css.font')}}" />
<link rel="stylesheet" th:href="@{${#themes.code('cas.css.animate')}}"  />
<link rel="stylesheet" th:href="@{${#themes.code('cas.css.style')}}" />
<link rel="stylesheet" th:href="@{${#themes.code('cas.css.whole')}}" />
<link rel="stylesheet" th:href="@{${#themes.code('cas.css.login')}}"  />
<link rel="stylesheet" th:href="@{${#themes.code('cas.css.layer')}}"  />
<link rel="stylesheet" th:href="@{${#themes.code('cas.css.layer.ext')}}" />
```
**注意：** 定制登录页面主要是修改相应的样式，表单的name,id及其它属性不要改变。

### 3.5 修改系统默认的主题
将base主题修改为系统默认主题，在application.properties文件中加入下面的配置：
```properties
# defaultThemeName
cas.theme.defaultThemeName=base
```

### 3.6 定义登录成功之后的页面
登录成功之后，CAS跳转到默认页面，在实际项目中可以对跳转页面进行更改，在application.properties中加入如下配置：
```properties
# Defines a default URL to which CAS may redirect if there is no service
# provided in the authentication request.
cas.view.defaultRedirectUrl=https://www.github.com
```
## 4、自定义用户鉴权
在这里不使用系统自带的JDBC认证方式，而是自定义验证逻辑，需要继承AuthenticationHandler类，并注册到系统当中去。
在CAS系统中，鉴权的逻辑路径如下所示：
DefaultAuthenticationTransactionManager --> 
PolicyBasedAuthenticationManager --> 
AuthenticationEventExecutionPlan --> 
AuthenticationEventExecutionPlanConfigurer --> 
AuthenticationHandler
系统中可以注册多个AuthenticationHandler，AuthenticationHandler通过AuthenticationEventExecutionPlanConfigurer类注入到AuthenticationManager中。这里有个疑问，AuthenticationEventExecutionPlanConfigurer是如何将AuthenticationHandler注册到AuthenticationManager中的? 在CasCoreAuthenticationConfiguration类中，看到如下代码：
```java
@ConditionalOnMissingBean(
    name = {"authenticationEventExecutionPlan"}
)
@Autowired
@Bean
public AuthenticationEventExecutionPlan authenticationEventExecutionPlan(List<AuthenticationEventExecutionPlanConfigurer> configurers) {
    DefaultAuthenticationEventExecutionPlan plan = new DefaultAuthenticationEventExecutionPlan();
    configurers.forEach((c) -> {
        String name = StringUtils.removePattern(c.getClass().getSimpleName(), "\\$.+");
        LOGGER.debug("Configuring authentication execution plan [{}]", name);
        c.configureAuthenticationExecutionPlan(plan);
    });
    return plan;
}
```
在这里可以看到，通过Spring容器自动收集所有的AuthenticationEventExecutionPlanConfigurer类，并执行configureAuthenticationExecutionPlan方法，在该方法中，将AuthenticationHandler注册到AuthenticationEventExecutionPlan中，代码如下所示：
```java
@Override
public void configureAuthenticationExecutionPlan(AuthenticationEventExecutionPlan plan) {
    plan.registerAuthenticationHandler(usernamePasswordCaptchaAuthenticationHandler());
}
```
最终将AuthenticationEventExecutionPlan注入到PolicyBasedAuthenticationManager类中，如下所示：
```java
@ConditionalOnMissingBean(
    name = {"casAuthenticationManager"}
)
@Autowired
@Bean
public AuthenticationManager casAuthenticationManager(@Qualifier("authenticationEventExecutionPlan") AuthenticationEventExecutionPlan authenticationEventExecutionPlan) {
    return new PolicyBasedAuthenticationManager(authenticationEventExecutionPlan, this.casProperties.getPersonDirectory().isPrincipalResolutionFailureFatal(), this.applicationEventPublisher);
}
```
可见，通过AuthenticationEventExecutionPlanConfigurer 类将AuthenticationHandler注册到AuthenticationEventExecutionPlan类中，而AuthenticationManager只要持有AuthenticationEventExecutionPlan类的引用即可。

综上所述，要实现自定义验证逻辑，只需要生成**AuthenticationEventExecutionPlanConfigurer**和**AuthenticationHandler**的子类，并注册到spring容器中。

### 4.1 生成AuthenticationHandler子类
```java
public class UsernamePasswordCaptchaAuthenticationHandler extends AbstractPreAndPostProcessingAuthenticationHandler {

    private UserService userService;

    private CasCustomProperties casCustomProperties;

       public UsernamePasswordCaptchaAuthenticationHandler(String name, ServicesManager servicesManager, PrincipalFactory principalFactory, Integer order) {
        super(name, servicesManager, principalFactory, order);
    }

    @Override
    protected AuthenticationHandlerExecutionResult doAuthentication(Credential credential) throws GeneralSecurityException, PreventedException {

        String requestCaptcha = null;

	// 自定义逻辑

        return createHandlerResult(credential, this.principalFactory.createPrincipal(username));
    }

    @Override
    public boolean supports(Credential credential) {
        return credential instanceof UsernamePasswrodCaptchaCredential
                || credential instanceof RememberMeUsernamePasswordCaptchaCredential;
    }

  }
```
UsernamePasswordCaptchaAuthenticationHandler继承了AbstractPreAndPostProcessingAuthenticationHandler类，可以在该AuthenticationHandle引用业务代码，如UserService，实现用户的查询及验证功能。doAuthentication方法是鉴权的核心方法，在该方法中，可以自定义返回的用户信息。supports方法主要是判断该AuthenticationHandle所支持的Credential类型，CAS会将登录页面表单字段映射为一个Credential对象，默认是UsernamePasswordCredential类。每一个AuthenticationHandle支持的Credential对象不一样，执行的逻辑也不一样的，通过该方法，可以决定AuthenticationHandle是否被执行。
另外，AuthenticationHandle在系统中可能有多个，在UsernamePasswordCaptchaAuthenticationHandler构造函数中，要求传入一个int类型的order值，这个参数决定了AuthenticationHandle执行的顺序。

### 4.2 生成AuthenticationEventExecutionPlanConfigurer类
```java
@Configuration("casCaptchaConfiguration")
@EnableConfigurationProperties({CasConfigurationProperties.class})
public class CasCaptchaConfiguration implements AuthenticationEventExecutionPlanConfigurer {

    @Autowired
    private CasConfigurationProperties casProperties;

    @Autowired
    @Qualifier("servicesManager")
    private ServicesManager servicesManager;

    @Autowired
    @Qualifier("userService")
    private UserService userService;


    @Bean
    public AuthenticationHandler usernamePasswordCaptchaAuthenticationHandler() {

        UsernamePasswordCaptchaAuthenticationHandler handler = new UsernamePasswordCaptchaAuthenticationHandler(
                UsernamePasswordCaptchaAuthenticationHandler.class.getSimpleName(),
                servicesManager,
                new DefaultPrincipalFactory(),
                1);
        handler.setUserService(userService);
        return handler;
    }

    @Override
    public void configureAuthenticationExecutionPlan(AuthenticationEventExecutionPlan plan) {
        plan.registerAuthenticationHandler(usernamePasswordCaptchaAuthenticationHandler());
    }

}
```
CasCaptchaConfiguration类继承了AuthenticationEventExecutionPlanConfigurer类，主要是生成UsernamePasswordCaptchaAuthenticationHandler类，并将UsernamePasswordCaptchaAuthenticationHandler注册到AuthenticationEventExecutionPlan类中。

### 4.3 将CasCaptchaConfiguration类注册到Spirng容器中
通过Springboot的AutoConfiguration机制，将CasCaptchaConfiguration类注册到Spring容器中，在META-INF/spring.factories文件中加入配置项：
```properties
org.springframework.boot.autoconfigure.EnableAutoConfiguration=net.noahsark.cas.common.config.CasCaptchaConfiguration
```

### 4.4 实现业务方法
在上面的内容中，提到将业务逻辑加入到UsernamePasswordCaptchaAuthenticationHandler类中，如UserService，加入的方式相对简单略过不表。

## 5、加入验证码
加入验证码，包含如下步骤：
- 修改登录页面，加入验证码字段；
- 创建包含验证码字段的Credential对象；
- 修改webflow中绑定的Credential对象；
- 后台生成验证码；
- 修改AuthenticationHandler对象，加入验证码逻辑；

### 5.1 修改登录页面，加入验证码字段
修改casLoginView.html文件，表单中加入验证码字段，如下所示：
```html
<div class="verify">
   <div class="verify_box">
      <input class="form-control" placeholder="验证码" id="captcha" name="captcha" autocomplete="off" maxlength="4" tabindex="3" />
   </div>
   <div class="ver_img">
      <img alt="required" onclick="this.src='captcha.jpg?'+Math.random()" src="captcha.jpg">
   </div>
</div>
```

### 5.2 创建包含验证码字段的Credential对象
生成**RememberMeUsernamePasswordCaptchaCredential**和**UsernamePasswrodCaptchaCredential**对象，它们分别继承自RememberMeUsernamePasswordCredential和UsernamePasswordCredential，在对象中都加入了String类型的captcha字段，以**RememberMeUsernamePasswordCaptchaCredential**为例：
```java
public class RememberMeUsernamePasswordCaptchaCredential extends RememberMeUsernamePasswordCredential {

    @Size(min = 5,max = 5, message = "require captcha")
    private String captcha;

    public String getCaptcha() {
        return captcha;
    }

    public void setCaptcha(String captcha) {
        this.captcha = captcha;
    }

    @Override
    public int hashCode() {
        return new HashCodeBuilder()
                .appendSuper(super.hashCode())
                .append(this.captcha)
                .toHashCode();
    }
```
### 5.3 修改webflow中绑定的Credential对象
修改默认的Credential对象，首先需要获取登录流程的Flow对象，然后创建ID为credential的FlowVariable对象，其绑定的对象便是自定义的Credential对象。由于ID相同的FlowVariable对象不会重复创建，如果默认的Credential对象先创建，则自定义Credential对象将不会在创建，为了避免这种情况的发现，必须保证自定义Credential对象先创建。
#### 5.3.1 生成CasWebflowConfigurer对象
CasWebflowConfigurer对象主要是用来获取Flow对象，并绑定自定义Credential对象，如代码如下所示：
```java
class DefaultCaptchaWebflowConfigurer extends AbstractCasWebflowConfigurer {

public DefaultCaptchaWebflowConfigurer(FlowBuilderServices flowBuilderServices, FlowDefinitionRegistry flowDefinitionRegistry, ApplicationContext applicationContext, CasConfigurationProperties casProperties) {
        super(flowBuilderServices, flowDefinitionRegistry, applicationContext, casProperties);
    }

    protected void doInitialize() {
        Flow flow = this.getLoginFlow();
        if (flow != null) {
            if (casProperties.getTicket().getTgt().getRememberMe().isEnabled()) {
                createFlowVariable(flow, CasWebflowConstants.VAR_ID_CREDENTIAL, RememberMeUsernamePasswordCaptchaCredential.class);
                final ViewState state = getState(flow, CasWebflowConstants.STATE_ID_VIEW_LOGIN_FORM, ViewState.class);
                final BinderConfiguration cfg = getViewStateBinderConfiguration(state);
                cfg.addBinding(new BinderConfiguration.Binding("rememberMe", null, false));
                cfg.addBinding(new BinderConfiguration.Binding("captcha", null, true));
            } else {
                createFlowVariable(flow, CasWebflowConstants.VAR_ID_CREDENTIAL, UsernamePasswrodCaptchaCredential.class);
                final ViewState state = getState(flow, CasWebflowConstants.STATE_ID_VIEW_LOGIN_FORM, ViewState.class);
                final BinderConfiguration cfg = getViewStateBinderConfiguration(state);
                cfg.addBinding(new BinderConfiguration.Binding("captcha", null, true));
            }
        }

    }
}
```
在**doInitialize**方法中会绑定**RememberMeUsernamePasswordCaptchaCredential**或**UsernamePasswrodCaptchaCredential**对象。

#### 5.3.2 生成Spring配置对象CaptchaWebflowConfiguration
CaptchaWebflowConfiguration是一个普通的Configuration对象，用于生成DefaultCaptchaWebflowConfigurer对象并注册到Spring容器中，并通过@AutoConfigureBefore(value = CasWebflowContextConfiguration.class)注解来保证在CasWebflowContextConfiguration配置对象之前执行，在CasWebflowContextConfiguration中有默认的CasWebflowConfigurer对象，该对象会绑定默认的Credential对象。

#### 5.3.3 自动加载CaptchaWebflowConfiguration对象
在META-INF/spring.factories文件中加入配置项：
```properties
org.springframework.boot.autoconfigure.EnableAutoConfiguration=net.noahsark.cas.common.config.CaptchaWebflowConfiguration
```

### 5.4 后台生成验证码
#### 5.4.1 引入依赖
引入com.google.code.kaptcha:kaptcha:2.3类，在pom.xml中加入依赖：
```xml
<dependency>
    <groupId>com.google.code.kaptcha</groupId>
    <artifactId>kaptcha</artifactId>
    <version>2.3</version>
</dependency>
```
#### 5.4.2 配置生成验证码的Servlet对象
```java
@Configuration
public class KaptchaConfiguration {

    @Bean
    public ServletRegistrationBean kaptchaServlet() {

        KaptchaServlet servlet = new KaptchaServlet();

        ServletRegistrationBean registration = new ServletRegistrationBean(servlet);
        registration.addUrlMappings("/captcha.jpg");

        Map<String, String> parameters = Maps.newHashMap();
        parameters.put("kaptcha.border","no");
        parameters.put("kaptcha.textproducer.char.space","4");
        parameters.put("kaptcha.textproducer.char.length","4");
        registration.setInitParameters(parameters);

        return registration;
    }
}
```
配置的访问路径为/captcha.jpg，该路径需要在登录页面中配置。

#### 5.4.3 自动加载KaptchaConfiguration对象
在META-INF/spring.factories文件中加入配置项：
```properties
org.springframework.boot.autoconfigure.EnableAutoConfiguration=net.noahsark.cas.common.config.KaptchaConfiguration
```

#### 5.4.4. 修改AuthenticationHandler对象，加入验证码逻辑
验证码的验证逻辑是在AuthenticationHandler对象的doAuthentication方法中，上面的UsernamePasswordCaptchaAuthenticationHandler对象中已经包含对验证码的处理逻辑，如下所示：
```java
@Override
protected AuthenticationHandlerExecutionResult doAuthentication(Credential credential) throws GeneralSecurityException, PreventedException {

    String requestCaptcha = null;

    if (credential instanceof  RememberMeUsernamePasswordCaptchaCredential) {
        RememberMeUsernamePasswordCaptchaCredential rmupc = (RememberMeUsernamePasswordCaptchaCredential)credential;
        requestCaptcha = rmupc.getCaptcha();
    } else if (credential instanceof UsernamePasswrodCaptchaCredential) {
        UsernamePasswrodCaptchaCredential upc = (UsernamePasswrodCaptchaCredential)credential;
        requestCaptcha = upc.getCaptcha();
    }

    ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
    Object attribute = attributes.getRequest().getSession().getAttribute(com.google.code.kaptcha.Constants.KAPTCHA_SESSION_KEY);

    String realCaptcha = attribute == null ? null : attribute.toString();

    if(StringUtils.isBlank(requestCaptcha) || !requestCaptcha.equals(realCaptcha)){
        throw new FailedCaptchaException("Verification code does not match!");
    } else {
        attributes.getRequest().getSession().removeAttribute(com.google.code.kaptcha.Constants.KAPTCHA_SESSION_KEY);
    }

    // 验证用户名/密码逻辑

    return createHandlerResult(credential, this.principalFactory.createPrincipal(username));
}
```

## 6、自定义登录错误信息
在UsernamePasswordCaptchaAuthenticationHandler对象中，会对验证码及用户名/密码进行验证，如果验证失败，可以定制显示的错误信息。
### 6.1 生成异常对象
生成异常对象，该对象可以继承自AccountException对象（子对象），如下所示：
```java
public class FailedCaptchaException extends AccountExpiredException {

    private static final long serialVersionUID = 7267347853421454216L;

    public FailedCaptchaException() {
        super();
    }

    public FailedCaptchaException(String msg) {
        super(msg);
    }
}
```
### 6.2 配置语言文件
从cas-server-webapp-tomcat-5.3.9中拷贝messages.properties或messages_zh_CN.properties文件到resources目录下，按照如下格式配置：
**authenticationFailure.异常=错误信息**
以FailedCaptchaException为例：
```propreties
# Customer Error
authenticationFailure.FailedCaptchaException=验证码不匹配
```

## 7、其它配置
### 7.1 配置数据源及业务对象
可以定义一个Configuration对象，如DataSourceConfig，配置Druid数据源及其相关对象。
### 7.2 配置Spring容器的扫描目录，加载Service及Dao对象
可以定义一个Configuration对象，如SpringConfig，指定扫描的目录，自动加载业务对象。
### 7.3 加载DataSourceConfig及SpringConfig对象
在META-INF/spring.factories文件中加入相应的配置，最后文件内容为：
```properties
org.springframework.boot.autoconfigure.EnableAutoConfiguration=net.noahsark.cas.common.config.SpringConfig,\
  net.noahsark.cas.common.config.CasCaptchaConfiguration,\
  net.noahsark.cas.common.config.CaptchaWebflowConfiguration,\
  net.noahsark.cas.common.config.KaptchaConfiguration,\
  net.noahsark.cas.common.config.DataSourceConfig
```

