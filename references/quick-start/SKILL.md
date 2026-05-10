---
name: "quick-start"
description: "检索JeeSite平台基础知识文档（简介、架构、技术选型、功能介绍等）。Invoke when user asks about JeeSite overview, architecture, tech stack, or platform basics."
---

# 快速了解

JeeSite 平台基础知识，包括平台简介、架构特点、技术选型、功能介绍等。

## 文档获取方式

按需缓存，有效期3天。优先从本地缓存读取，缓存过期或不存在时自动下载并转换为 Markdown：

- **缓存目录**: `references/.cache/quick-start/`（权限不足时自动回退到 `~/.cache/jeesite/quick-start/`）
- **缓存命令**: `python3 scripts/cache_docs.py --skill quick-start --permalink <permalink>`
- **强制更新**: `python3 scripts/cache_docs.py --skill quick-start --permalink <permalink> --force`

## 关键词

简介、概述、架构、技术选型、功能、标准、目录、配置、树表、Vue、升级、更新日志、版本、Spring Boot、MyBatis、Vue3、Antdv、安全、性能、规范、编码规范、命名规范、项目结构、文件组织、application.yml、参数配置、树形结构、数据表设计、前后分离、Vben Admin、changelog

## 触发场景

- JeeSite是什么
- JeeSite简介
- 平台介绍
- 架构特点
- 技术选型
- 功能介绍
- 目录结构
- 配置参数
- 树表结构
- JeeSite Vue
- 如何升级
- 更新日志
- 版本变更
- 编码规范
- 命名规范
- 项目结构
- 文件组织
- 前后分离版介绍
- 平台优势
- 核心优势
- 发展史

## 文档映射

| 文档标题 | sidebarTitle | permalink | 摘要与关键章节 | 关联文档 |
|----------|-------------|-----------|---------------|---------|
| 平台简介 | 平台简介 | /overview/ | 平台介绍、核心优势、发展史。关键章节：平台介绍、发展史 | /feature/、/technology/ |
| 架构特点 | 架构特点 | /feature/ | 架构特点、安全机制、平台优势。关键章节：架构特点、安全、优势 | /overview/、/technology/ |
| 技术选型 | 技术选型 | /technology/ | 技术栈详解：Spring Boot、MyBatis、Vue3、Beetl。关键章节：后端技术、前端技术 | /feature/、/jeesite-vue/ |
| 功能介绍 | 功能介绍 | /function/ | 功能模块全景：系统管理、代码生成、工作流等。关键章节：内置功能、核心功能 | /overview/、/bpm/ |
| 标准规范 | 标准规范 | /standard/ | 编码规范、开发规范、命名规范。关键章节：Java规范、Vue规范、数据库规范 | /catalog/、/code-gen/ |
| 目录结构 | 目录结构 | /catalog/ | 项目目录结构、文件组织说明。关键章节：后端目录、前端目录 | /standard/、/install-deploy/ |
| 参数配置 | 参数配置 | /config/ | application.yml 配置参数详解。关键章节：核心配置、数据源配置 | /install-deploy/、/faq/ |
| 树表结构 | 树表结构 | /treetable/ | 树形结构数据表设计与实现。关键章节：数据表设计、代码生成 | /code-gen/、/dao-mybatis/ |
| JeeSite Vue | JeeSite Vue | /jeesite-vue/ | Vue3 前后分离版介绍、Vben Admin。关键章节：技术栈、与经典版区别 | /vue-install-deploy/、/technology/ |
| 更新日志 | 平台更新日志 | /upgrade/ | 版本更新日志、升级方法。关键章节：最新版本、升级步骤 | /install-deploy/、/support/ |

## 检索策略

1. 根据用户问题匹配"触发场景"或"关键词"
2. 在"文档映射"表中定位最相关的文档，获取 permalink
3. 执行缓存命令：`python3 scripts/cache_docs.py --skill quick-start --permalink <permalink>`
   - 若缓存有效（3天内），直接返回缓存文件路径
   - 若缓存过期或不存在，自动下载并转换为 Markdown 保存
4. 使用 Read 工具读取返回的缓存文件路径
5. 基于文档内容回答用户

## 常见问题映射

| 用户问题 | 推荐文档 | WebFetch URL |
|----------|----------|-------------|
| JeeSite 是什么？ | 平台简介 | https://jeesite.com/docs/overview/ |
| JeeSite 有什么优势？ | 架构特点 | https://jeesite.com/docs/feature/ |
| 用了哪些技术？ | 技术选型 | https://jeesite.com/docs/technology/ |
| 有哪些功能？ | 功能介绍 | https://jeesite.com/docs/function/ |
| 目录结构是怎样的？ | 目录结构 | https://jeesite.com/docs/catalog/ |
| 如何配置参数？ | 参数配置 | https://jeesite.com/docs/config/ |
| 如何升级？ | 更新日志 | https://jeesite.com/docs/upgrade/ |
