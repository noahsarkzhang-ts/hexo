---
title: Springboot 系列：使用 Oauth2 实现单点登陆
date: 2022-05-08 15:15:08
tags:
- oauth2
- sso
- cas
categories:
- Springboot
---

这篇文章主要讲述使用 Oauth2 协议来实现前后端分离场景下 SSO 的功能。

<!-- more -->

## CAS

在之前的项目中曾经使用 CAS 来解决 SSO(Single Sign-On) 的问题，它主要是通过 Cookie 来实现，其协议如下图所示：

![cas_flow_diagram](/images/spring-cloud/cas_flow_diagram.png "cas_flow_diagram")

**关键流程：**
- 访问 app1 时，如果未认证则会跳转到 CAS Server, 登陆功能集成在  CAS Server 上，用户登陆成功之后会生成一个 TGT(Ticket Granting Ticket), 存储到 TGC(Ticket Granting Cookie) 中，写入到浏览中，并颁发一个 ST (Service Ticket) 给 app1, 最后跳转回 app1; 
- 跳转回 app1 之后，使用 ST 向 CAS Server 进行验证，验证通过生成 app1 的 Cookie, 完成本次登陆，后续 app1 请求都会通过；
- 访问 app2 时，同样跳转到 CAS Server 进行登陆，不过此时浏览器已经有 TGC, 表明用户已经登陆，直接给 app2 颁发一个 ST (Service Ticket), 并跳回 app2; 
- 跳转回 app2 之后，使用 ST 向 CAS Server 进行验证，验证通过生成 app2 的 Cookie, 完成本次登陆，后续 app2 的请求都会通过。

CAS 的关键是共享一个 TGC, 在不同应用间共享用户登陆状态。一个 TGT 可以颁发多个 ST, 一个 app 一个 ST, 每一个 app 也会维护一个 Cookie, 保存该 app 的会话信息。

## Oauth2

使用 Cookie 来代表一个 Session, 比较适用于前后端集中部署在一个应用服务器(如 Tomcat) 中的情况。在前后端分离的场景中，前端应用可能部署在 CDN 或 Nginx 中，前后端不在一起，使用 Cookie 就行不通了。在这种场景下，我们使用 Oauth2 协议来实现 SSO 的功能，用 JWT token 来代替 Cookie. 同时为了避免在每一个应用中都要集成 SSO Client, 引入 Spring Cloud gateway 来写成统一的认证功能。其协议如下所示：

![SSO](/images/spring-cloud/SSO.jpg "SSO")

**关键流程：**
- 访问 app1 时，如果未认证则向 gateway 执行登陆操作，该操作必须传入如下参数：1) uuid, 惟一表示这次登陆，根据uuid, 可以获取 JWT token; 2) clientId, Oauth2 Server 分配的应用 Id; 3) redirectUri: 登陆成功之后返回的 url, 在这里表示 app1 应用；
- gateway 收到请求之后，会在本地维护本次登陆的信息，如使用 Map 结构存储这些信息，key 为 uuid, 值为上步提到的参数；
- gateway 构造 Oauth2 `oauth/authorize` 请求，使用 `authorization code` 模式向 Oauth2 Sever 发起认证请求，关键参数有：1) client_id, app1; 2) state, 使用上述请求参数中的 uuid, 该参数会包含在响应结果中，借助该参数，我们可以知道是那一个应用发起的登陆请求；3) redirect_uri: 认证成功之后的回调 url, 在这里使用 gateway 统一作为 Oauth2 服务的回调地址；4) response_type: 使用 `code` 模式；
- gateway 将 `oauth/authorize` 请求重定向到浏览器，由浏览器发起该请求。由于用户未登陆，Oauth2 Server 返回登陆页面；
- 用户输入用户名/密码，完成验证，生成一个授权码，并将登陆信息写入到 Cookie 中。Oauth2 Server 根据传入的 `redirect_uri`, 将授权码传给 gateway; 
- gateway 收到授权码之后，使用该授权码获取 JWT token, 根据 `state` 字段找到对应的 `uuid` 请求， 并将该 token 写入到请求对应的数据中；最后找到该请求对应的 `redirectUri`,带上 uuid 参数，重定向回 app1;
- app1 应用收到请求，从 url 中获取到 uuid, 使用 uuid 向 gateway 请求获取 `JWT token`, 获取到 token 之后存储到浏览器本地，后续请求 api 带上 token 即可；
- 访问 app2 时，与上述步骤类似，差别在于 Oauth2 Server 的认证操作，由于登陆信息已经写入 Cookie 中，无须再登陆；

Oauth2 的关键也是所有应用共享一个 Oauth2 Server 的用户 Cookie, 差别只是 app 使用 JWT 代表认证信息。

**说明：**
- `oauth/authorize` 请求中的 `state` 参数主要是用于防御 CSRF(跨站请求伪造), 在参数中传入该值，返回结果也会原封不动地传回给请求方，请求方验证该值便可知道该请求的真实性。借助该特性，用于将 gateway 的请求与 oauth2 请求对应起来，从而将 JWT token 返回给请求方；
- 所有 app clientId 的 secret 存储在 gateway, 避免 secret 数据的泄露。

[工程代码：https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springcloud-koala](https://github.com/noahsarkzhang-ts/springboot-lab/tree/main/springcloud-koala)

</br>

**参考：**

----
[1]:https://apereo.github.io/cas/6.0.x/protocol/CAS-Protocol.html

[1. CAS Protocol][1]
