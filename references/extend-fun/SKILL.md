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

BPM、工作流、Flowable、CMS、内容管理、AI、消息推送、SSO、单点登录、OAuth2、作业调度、对象存储、OSS、可视化、报表、文件管理、文件预览、UniApp、手机端移动端、三员管理

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

## 文档映射

| 文档标题 | sidebarTitle | permalink | 完整URL | 主题 |
|----------|-------------|-----------|---------|------|
| BPM工作流 | BPM业务流程系统 | /bpm/ | https://jeesite.com/docs/bpm/ | 工作流、Flowable、流程引擎、业务流程 |
| AI+CMS | AI知识库智能助手 | /ai-cms/ | https://jeesite.com/docs/ai-cms/ | AI、CMS、内容管理、智能助手、知识库 |
| 消息推送 | 消息推送、消息提醒 | /msg-push-use/ | https://jeesite.com/docs/msg-push-use/ | 消息推送、通知、站内信、消息提醒 |
| SSO单点登录 | 单点登录、OAuth2 | /sso-cas/ | https://jeesite.com/docs/sso-cas/ | SSO、单点登录、CAS、OAuth2客户端 |
| 作业调度 | 作业监控、任务调度 | /job/ | https://jeesite.com/docs/job/ | 定时任务、作业调度、Quartz、监控 |
| 对象存储 | 对象存储、文件存储 | /oss-client/ | https://jeesite.com/docs/oss-client/ | OSS、对象存储、文件存储、S3 |
| 用户类型 | 用户类型、类型扩展 | /user-type/ | https://jeesite.com/docs/user-type/ | 用户类型、多用户体系、类型扩展 |
| 可视化大屏 | 可视化数据大屏 | /visual/ | https://jeesite.com/docs/visual/ | 可视化、数据大屏、图表、ECharts |
| 报表设计器 | 在线报表设计器 | /ureport/ | https://jeesite.com/docs/ureport/ | 报表、UReport、报表设计、在线报表 |
| 文件管理 | 文件管理、文件柜 | /filemanager/ | https://jeesite.com/docs/filemanager/ | 文件管理、文件上传下载、文件柜 |
| 文件预览 | 在线预览图片文档 | /filepreview/ | https://jeesite.com/docs/filepreview/ | 文件预览、在线预览、图片文档预览 |
| UniApp移动端 | 手机端移动端、Uni-App | /uniapp/ | https://jeesite.com/docs/uniapp/ | UniApp、移动端、手机端、App |
| CMS内容管理 | CMS内容管理系统 | /cms/ | https://jeesite.com/docs/cms/ | CMS、内容管理、文章管理、站点管理 |
| 三员管理 | 涉密"三员"管理 | /manager3/ | https://jeesite.com/docs/manager3/ | 三员管理、涉密、安全管理员 |
| OAuth2认证 | OAauth2统一认证服务 | /oauth2-server/ | https://jeesite.com/docs/oauth2-server/ | OAuth2、认证服务器、统一认证、授权 |

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
