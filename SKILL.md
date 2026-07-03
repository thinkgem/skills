---
name: "jeesite"
description: "JeeSite快速开发平台文档总索引。Invoke when user asks about JeeSite documentation, or when the topic doesn't clearly match a single sub-skill."
---

# JeeSite 文档 Skills 集合

JeeSite 快速开发平台文档 Skills 集合，供 AI Agent 检索和调用。

## 使用流程

1. **匹配 Skill**：根据用户问题，在「Skills 列表」或「快速路由参考」中找到最相关的 skill-name
2. **加载子 Skill**：读取 `references/<skill-name>/SKILL.md` 获取详细文档映射
3. **匹配文档**：在子 Skill 的「文档映射」表中找到最相关的 permalink
4. **获取缓存**：执行 `python3 scripts/cache_docs.py --skill <skill-name> --permalink <permalink>` 脚本，缓存目录为 `references/.cache/<skill-name>/`，不存在时自动回退到 `~/.cache/jeesite/<skill-name>/`
5. **读取内容**：先读 `__00.md` 目录索引文件，了解章节结构，按需读取 `__01.md`~`__NN.md`
6. **回答问题**：缓存文件有效期3天，自动更新缓存，并基于读取的文档内容回答
7. **跨 Skill 场景**：如问题涉及多个领域，可同时加载多个子 Skill（见「跨 Skill 关联」）

> ⚠️ **AI 强制规则**：在执行任何「代码生成」「创建 Entity/DAO/Service/Controller」「修改代码结构」操作之前，**必须**加载 `quick-start` Skill 并读取 `/standard/`（开发规范）文档，确认生成代码符合规范约束。详见「跨 Skill 关联」表中的"代码生成类"场景。

## Skills 列表

| Skill name     | 名称    | 说明   |
|----------------|---------|---------|
| jeesite        | JeeSite | JeeSite 平台文档总索引  |
| quick-start    | 快速了解    | 平台简介、架构特点、技术选型、功能介绍等基础知识、更新日志、升级方法、**开发规范与编码规范（代码生成必读）** |
| backend-dev    | 后端开发手册  | 安装部署、代码生成、DAO、@Table、数据权限、Shiro等后端开发指南 |
| frontend-vue   | Vue前端手册 | 前端安装、前端CRUD、表单、表格、组件、权限等前端开发指南 |
| frontend-beetl | 经典前端手册  | Beetl视图、Form、DataGrid、JS框架等经典前端开发指南 |
| extend-fun     | 扩展功能专题  | BPM工作流、AI相关、CMS、SSO、OAuth2、定时任务、对象存储、敏感词等扩展功能 |
| cloud-arch     | 云服务技术架构 | SaaS、集群、微服务、分布式事务等云服务架构 |
| support        | 技术支持与服务 | 技术支持服务、版本区别、联系方式 |

## 快速路由参考

| 用户问题方向 | 推荐Skill |
|-------------|-----------|
| JeeSite是什么、平台简介、架构特点、技术选型、功能介绍、标准规范、目录结构、参数配置、树表结构、更新日志、升级方法 | quick-start |
| 安装部署、环境搭建、代码生成、DAO、MyBatis、@Table、@Column、数据权限、Service、Shiro、权限认证、工具类、数据库管理、REST API、接口开发、Swagger、后端常见问题 | backend-dev |
| Vue3、前端安装、CRUD、增删改查、BasicForm、BasicTable、表单组件、表格组件、通用组件、前端权限、v-auth、图标Icon、国际化i18n、样式主题、UnoCSS、Less、外部依赖、Vue常见问题 | frontend-vue |
| Beetl、模板引擎、DataGrid、jqGrid、JS工具、经典前端、全栈版、自定义视图、修改登录页、后端国际化 | frontend-beetl |
| BPM工作流、Flowable、AI知识库、RAG、CMS内容管理、消息推送、SSO单点登录、OAuth2认证、作业调度、对象存储、用户类型、可视化大屏、报表设计器、文件管理、文件预览、UniApp移动端、三员管理、敏感词 | extend-fun |
| SaaS多租户、集群部署、负载均衡、高可用、Spring Cloud微服务、Nacos、Gateway、分布式事务Seata、分库分表、读写分离、Spring Boot Admin监控、SkyWalking链路追踪、ELK日志收集 | cloud-arch |
| 技术支持、版本区别、授权、联系方式、商业版、社区版 | support |

## 跨 Skill 关联

当用户问题涉及多个领域时，同时加载多个子 Skill：

### 代码生成类（**必须加载规范文档**）

| 场景 | 需要加载的 Skills |
|------|-------------------|
| 代码生成 / 创建实体类 / 建表 | **quick-start** + backend-dev |
| 创建 Vue CRUD 页面 | **quick-start** + backend-dev + frontend-vue |
| 创建 Beetl CRUD 页面 | **quick-start** + backend-dev + frontend-beetl |
| 创建 Service / DAO / Controller | **quick-start** + backend-dev |
| 创建树结构功能 | **quick-start** + backend-dev |
| 主子表（一对多）功能 | **quick-start** + backend-dev |
| 导入导出 Excel | **quick-start** + backend-dev |
| 前端 CRUD 开发 | **quick-start** + frontend-vue（或 frontend-beetl） |

### 通用场景

| 场景 | 需要加载的 Skills |
|------|-------------------|
| 前后端权限控制 | **quick-start** + backend-dev + frontend-vue |
| 微服务 + 分布式事务 | cloud-arch + backend-dev |
| 单点登录 + 权限认证 | extend-fun + backend-dev |
| AI知识库 + CMS | extend-fun + backend-dev |
| 移动端 + REST API | extend-fun + backend-dev |
| 集群 + 安装部署 | cloud-arch + backend-dev |
| 国际化（前后端） | frontend-vue + frontend-beetl |
| 文件管理 + 对象存储 | extend-fun + cloud-arch |
