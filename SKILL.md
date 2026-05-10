---
name: "jeesite"
description: "JeeSite快速开发平台文档总索引。Invoke when user asks about JeeSite documentation, or when the topic doesn't clearly match a single sub-skill."
---

# JeeSite 文档 Skills 集合

JeeSite 快速开发平台文档 Skills 集合，供 AI Agent 检索和调用。

## 文档获取方式

按需缓存，有效期3天。优先从本地缓存读取，缓存过期或不存在时自动下载并转换为 Markdown：

- **缓存目录**: `references/.cache/<skill-name>/`（权限不足时自动回退到 `~/.cache/jeesite/<skill-name>/`）
- **按需缓存**: `python3 scripts/cache_docs.py --skill <skill-name> --permalink <permalink>`
- **强制更新**: `python3 scripts/cache_docs.py --skill <skill-name> --permalink <permalink> --force`

## Skills 列表

| Skill name     | 名称      | 说明                                        |
|----------------|---------|-------------------------------------------|
| quick-start    | 快速了解    | 平台简介、架构特点、技术选型、功能介绍等基础知识                  |
| backend-dev    | 后端开发手册  | 安装部署、代码生成、DAO、数据权限、Shiro等后端开发指南           |
| frontend-vue   | Vue前端手册 | Vue前端CRUD、表单、表格、组件、权限等前端开发指南              |
| frontend-beetl | 经典前端手册  | Beetl视图、Form、DataGrid、JS框架等经典前端开发指南       |
| extend-fun     | 扩展功能专题  | BPM工作流、AI相关、CMS、SSO、OAuth2、定时任务、对象存储等扩展功能 |
| cloud-arch     | 云服务技术架构 | SaaS、集群、微服务、分布式事务等云服务架构                   |
| support        | 技术支持与服务 | 技术支持服务、版本区别、联系方式                          |

## 路由策略

1. 根据用户问题，匹配上表中最相关的 Skill name
2. 加载对应 `references/<name>/SKILL.md` 获取详细文档映射
3. 根据文档映射表定位具体文档，获取 permalink
4. 执行缓存命令：`python3 scripts/cache_docs.py --skill <name> --permalink <permalink>`
   - 若缓存有效（3天内），直接返回缓存文件路径
   - 若缓存过期或不存在，自动下载并转换为 Markdown 保存
5. 使用 Read 工具读取缓存文件
6. 如果用户问题跨多个 Skill，可同时加载多个子 Skill

## 快速路由参考

| 用户问题方向 | 推荐Skill |
|-------------|-----------|
| JeeSite是什么、平台简介、架构特点、技术选型、功能介绍、标准规范、目录结构、参数配置、树表结构、更新日志、升级方法 | quick-start |
| 安装部署、环境搭建、代码生成、DAO、MyBatis、@Table、数据权限、Service、Shiro、权限认证、工具类、数据库管理、REST API、接口开发、Swagger、后端常见问题 | backend-dev |
| Vue3、前端安装、CRUD、增删改查、BasicForm、BasicTable、表单组件、表格组件、通用组件、前端权限、v-auth、图标Icon、国际化i18n、样式主题、UnoCSS、Less、外部依赖、Vue常见问题 | frontend-vue |
| Beetl、模板引擎、DataGrid、jqGrid、JS工具、经典前端、全栈版、自定义视图、修改登录页、后端国际化 | frontend-beetl |
| BPM工作流、Flowable、AI知识库、RAG、CMS内容管理、消息推送、SSO单点登录、OAuth2认证、作业调度、对象存储、用户类型、可视化大屏、报表设计器、文件管理、文件预览、UniApp移动端、三员管理 | extend-fun |
| SaaS多租户、集群部署、负载均衡、高可用、Spring Cloud微服务、Nacos、Gateway、分布式事务Seata、分库分表、读写分离、Spring Boot Admin监控、SkyWalking链路追踪、ELK日志收集 | cloud-arch |
| 技术支持、版本区别、授权、联系方式、商业版、社区版 | support |

## 跨 Skill 关联

当用户问题涉及多个领域时，同时加载多个子 Skill：

| 场景 | 需要加载的 Skills |
|------|-------------------|
| 前后端权限控制 | backend-dev + frontend-vue |
| 代码生成 + 前端CRUD | backend-dev + frontend-vue |
| 微服务 + 分布式事务 | cloud-arch + backend-dev |
| 单点登录 + 权限认证 | extend-fun + backend-dev |
| AI知识库 + CMS | extend-fun + backend-dev |
| 移动端 + REST API | extend-fun + backend-dev |
| 集群 + 安装部署 | cloud-arch + backend-dev |
| 国际化（前后端） | frontend-vue + frontend-beetl |
| 文件管理 + 对象存储 | extend-fun + cloud-arch |
