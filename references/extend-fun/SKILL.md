---
name: "extend-fun"
description: "检索JeeSite扩展功能文档（BPM工作流、AI、CMS、SSO、OAuth2、消息推送等）。Invoke when user asks about workflow, AI, CMS, SSO, OAuth2, or extension features."
---

# 扩展功能专题

JeeSite 扩展功能开发指南，包括 BPM 工作流、CMS 内容管理、消息推送、单点登录、OAuth2 认证等。

## 文档获取方式

按需缓存，有效期3天。优先从本地缓存读取，缓存过期或不存在时自动下载并转换为 Markdown：

- **缓存目录**: `references/.cache/extend-fun/`（权限不足时自动回退到 `~/.cache/jeesite/extend-fun/`）
- **缓存命令**: `python3 scripts/cache_docs.py --skill extend-fun --permalink <permalink>`
- **强制更新**: `python3 scripts/cache_docs.py --skill extend-fun --permalink <permalink> --force`

## 关键词

BPM、工作流、Flowable、CMS、内容管理、AI、消息推送、SSO、单点登录、OAuth2、作业调度、对象存储、OSS、可视化、报表、文件管理、文件预览、UniApp、手机端移动端、三员管理、RAG、知识库、智能助手、CAS、Quartz、S3、ECharts、UReport、认证服务器、流程设计、审批、会签、退回、加签、站内信、消息提醒、定时任务、大屏、文件柜、在线预览、App

## 触发场景

- BPM工作流怎么用
- CMS内容管理怎么用
- AI知识库智能助手
- 消息推送怎么配
- 单点登录怎么配
- OAuth2认证服务器
- 作业调度怎么用
- 对象存储怎么配
- 用户类型怎么扩展
- 可视化大屏怎么用
- 报表设计器怎么用
- 文件管理怎么用
- 文件在线预览
- UniApp移动端开发
- 三员管理怎么配
- Flowable流程引擎
- RAG知识库
- CAS单点登录
- Quartz定时任务
- S3对象存储
- ECharts图表
- UReport报表
- 流程设计器
- 审批流程
- 会签并行
- 退回加签
- 站内信通知
- 认证授权

## 文档映射

| 文档标题 | sidebarTitle | permalink | 摘要与关键章节 | 关联文档 |
|----------|-------------|-----------|---------------|---------|
| BPM工作流 | BPM业务流程系统 | /bpm/ | Flowable工作流引擎、流程设计、审批。关键章节：流程设计、办理、退回 | /code-gen/、/install-deploy/ |
| AI+CMS | AI知识库智能助手 | /ai-cms/ | AI知识库、RAG智能助手、CMS内容管理。关键章节：AI配置、知识库、RAG | /cms/、/bpm/ |
| 消息推送 | 消息推送、消息提醒 | /msg-push-use/ | 消息推送、站内信、消息提醒。关键章节：推送配置、消息模板 | /job/ |
| SSO单点登录 | 单点登录、OAuth2 | /sso-cas/ | SSO单点登录、CAS、OAuth2客户端。关键章节：CAS配置、OAuth2客户端 | /oauth2-server/、/permi-shiro/ |
| 作业调度 | 作业监控、任务调度 | /job/ | 定时任务、Quartz作业调度。关键章节：任务配置、监控 | /msg-push-use/ |
| 对象存储 | 对象存储、文件存储 | /oss-client/ | OSS对象存储、S3文件存储。关键章节：存储配置、上传下载 | /filemanager/ |
| 用户类型 | 用户类型、类型扩展 | /user-type/ | 多用户体系、用户类型扩展。关键章节：类型定义、扩展方法 | /permi-shiro/ |
| 可视化大屏 | 可视化数据大屏 | /visual/ | 可视化数据大屏、ECharts图表。关键章节：大屏设计、数据源 | /ureport/ |
| 报表设计器 | 在线报表设计器 | /ureport/ | UReport在线报表设计。关键章节：报表设计、数据源 | /visual/ |
| 文件管理 | 文件管理、文件柜 | /filemanager/ | 文件管理、文件柜。关键章节：上传下载、分类管理 | /oss-client/、/filepreview/ |
| 文件预览 | 在线预览图片文档 | /filepreview/ | 文件在线预览。关键章节：预览配置、支持格式 | /filemanager/ |
| UniApp移动端 | 手机端移动端、Uni-App | /uniapp/ | UniApp移动端开发。关键章节：项目结构、API调用 | /mobile-rest-api/ |
| CMS内容管理 | CMS内容管理系统 | /cms/ | CMS内容管理、文章管理、站点管理。关键章节：站点配置、栏目管理 | /ai-cms/ |
| 三员管理 | 涉密"三员"管理 | /manager3/ | 涉密三员管理。关键章节：角色配置、权限分离 | /permi-shiro/ |
| OAuth2认证 | OAauth2统一认证服务 | /oauth2-server/ | OAuth2统一认证服务器。关键章节：认证配置、授权模式 | /sso-cas/、/permi-shiro/ |

## 检索策略

1. 根据用户问题匹配"触发场景"或"关键词"
2. 在"文档映射"表中定位最相关的文档，获取 permalink
3. 执行缓存命令：`python3 scripts/cache_docs.py --skill extend-fun --permalink <permalink>`
   - 若缓存有效（3天内），直接返回缓存文件路径
   - 若缓存过期或不存在，自动下载并转换为 Markdown 保存
4. 使用 Read 工具读取返回的缓存文件路径
5. 基于文档内容回答用户

## 常见问题映射

| 用户问题 | 推荐文档 | WebFetch URL |
|----------|----------|-------------|
| BPM工作流怎么用？ | BPM工作流 | https://jeesite.com/docs/bpm/ |
| AI知识库怎么用？ | AI+CMS | https://jeesite.com/docs/ai-cms/ |
| 消息推送怎么配？ | 消息推送 | https://jeesite.com/docs/msg-push-use/ |
| 单点登录怎么配？ | SSO单点登录 | https://jeesite.com/docs/sso-cas/ |
| 作业调度怎么用？ | 作业调度 | https://jeesite.com/docs/job/ |
| 对象存储怎么配？ | 对象存储 | https://jeesite.com/docs/oss-client/ |
| 可视化大屏怎么用？ | 可视化大屏 | https://jeesite.com/docs/visual/ |
| 报表设计器怎么用？ | 报表设计器 | https://jeesite.com/docs/ureport/ |
| 文件管理怎么用？ | 文件管理 | https://jeesite.com/docs/filemanager/ |
| 文件在线预览？ | 文件预览 | https://jeesite.com/docs/filepreview/ |
| 移动端怎么开发？ | UniApp移动端 | https://jeesite.com/docs/uniapp/ |
| CMS内容管理怎么用？ | CMS内容管理 | https://jeesite.com/docs/cms/ |
| OAuth2认证怎么配？ | OAuth2认证 | https://jeesite.com/docs/oauth2-server/ |
