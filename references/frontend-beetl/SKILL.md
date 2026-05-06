---
name: "frontend-beetl"
description: "检索JeeSite经典前端开发文档（Beetl视图、DataGrid、JS框架等）。Invoke when user asks about classic frontend, Beetl templates, DataGrid, or legacy JS framework."
---

# 经典前端手册

JeeSite 经典前端开发指南，包括 Beetl 视图模板、DataGrid 表格、JS 工具框架、国际化、自定义视图等。

## 文档获取方式

按需缓存，有效期3天。优先从本地缓存读取，缓存过期或不存在时自动下载并转换为 Markdown：

- **缓存目录**: `references/.cache/frontend-beetl/`（权限不足时自动回退到 `~/.cache/jeesite/frontend-beetl/`）
- **缓存命令**: `python3 scripts/cache_docs.py --skill frontend-beetl --permalink <permalink>`
- **强制更新**: `python3 scripts/cache_docs.py --skill frontend-beetl --permalink <permalink> --force`

## 关键词

Beetl、视图模板、DataGrid、jqGrid、JS框架、国际化、多语言、自定义视图、经典前端、全栈版

## 触发场景

- Beetl视图怎么写
- DataGrid怎么用
- JS工具库有哪些
- 经典前端国际化
- 如何修改内置视图
- 如何修改登录页
- 全栈版前端开发

## 文档映射

| 文档标题 | sidebarTitle | permalink | 完整URL | 主题 |
|----------|-------------|-----------|---------|------|
| Beetl视图 | Form表单组件、Beetl | /views-beetl/ | https://jeesite.com/docs/views-beetl/ | Beetl、视图模板、页面渲染、Form组件 |
| DataGrid | DataGrid表格、jqGrid | /datagrid/ | https://jeesite.com/docs/datagrid/ | DataGrid、数据表格、列表、jqGrid |
| JS框架 | JS常用工具、小插件 | /jeesite-js/ | https://jeesite.com/docs/jeesite-js/ | JavaScript框架、JS工具库、小插件 |
| 国际化 | 后端国际化、多语言 | /i18n-locale/ | https://jeesite.com/docs/i18n-locale/ | 国际化、多语言、Locale、后端国际化 |
| 自定义视图 | 修改内置视图、修改登录页 | /custom-views/ | https://jeesite.com/docs/custom-views/ | 自定义视图、视图扩展、修改登录页 |

## 检索策略

1. 根据用户问题匹配"触发场景"或"关键词"
2. 在"文档映射"表中定位最相关的文档，获取 permalink
3. 执行缓存命令：`python3 scripts/cache_docs.py --skill frontend-beetl --permalink <permalink>`
   - 若缓存有效（3天内），直接返回缓存文件路径
   - 若缓存过期或不存在，自动下载并转换为 Markdown 保存
4. 使用 Read 工具读取返回的缓存文件路径
5. 基于文档内容回答用户

## 常见问题映射

| 用户问题 | 推荐文档 | WebFetch URL |
|----------|----------|-------------|
| Beetl视图怎么写？ | Beetl视图 | https://jeesite.com/docs/views-beetl/ |
| DataGrid怎么用？ | DataGrid | https://jeesite.com/docs/datagrid/ |
| JS工具库有哪些？ | JS框架 | https://jeesite.com/docs/jeesite-js/ |
| 经典版国际化？ | 国际化 | https://jeesite.com/docs/i18n-locale/ |
| 如何修改登录页？ | 自定义视图 | https://jeesite.com/docs/custom-views/ |
