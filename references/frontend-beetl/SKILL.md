---
name: "frontend-beetl"
description: "检索JeeSite经典前端开发文档（Beetl视图、DataGrid、JS框架等）。Invoke when user asks about classic frontend, Beetl templates, DataGrid, or legacy JS framework."
---

# 经典前端手册

JeeSite 经典前端开发指南，包括 Beetl 视图模板、DataGrid 表格、JS 工具框架、国际化、自定义视图等。

## 使用流程

1. **匹配文档**：根据用户问题，在「文档映射」表中查找最相关的 permalink
2. **获取缓存**：在 jeesite skills 根目录下执行 `python3 scripts/cache_docs.py --skill frontend-beetl --permalink <permalink>` 脚本，缓存目录为 `references/.cache/frontend-beetl/`，不存在时自动回退到 `~/.cache/jeesite/frontend-beetl/`
3. **读取内容**：先读 `__00.md` 目录索引文件，了解章节结构，按需读取 `__01.md`~`__NN.md`
4. **回答问题**：缓存文件有效期3天，自动更新缓存，并基于读取的文档内容回答

## 关键词

Beetl、视图模板、DataGrid、jqGrid、JS框架、国际化、多语言、自定义视图、经典前端、全栈版、模板引擎、Form组件、列表组件、Bootstrap、AdminLTE、登录页、内置视图、Locale、JS工具库、小插件

## 触发场景

- Beetl视图怎么写
- DataGrid怎么用
- JS工具库有哪些
- 经典前端国际化
- 如何修改内置视图
- 如何修改登录页
- 全栈版前端开发
- Beetl模板语法
- Form表单组件
- jqGrid配置
- 列表组件
- Bootstrap样式
- AdminLTE主题
- 后端国际化配置
- Locale多语言

## 文档映射

| 文档标题 | sidebarTitle | permalink | 摘要与关键章节 | 关联文档 |
|----------|-------------|-----------|---------------|---------|
| Beetl视图 | Form表单组件、Beetl | /views-beetl/ | Beetl视图模板、Form表单组件。关键章节：Beetl语法、表单组件、列表组件 | /datagrid/、/jeesite-js/ |
| DataGrid | DataGrid表格、jqGrid | /datagrid/ | DataGrid数据表格、jqGrid用法。关键章节：列配置、事件、分页 | /views-beetl/、/jeesite-js/ |
| JS框架 | JS常用工具、小插件 | /jeesite-js/ | JavaScript工具框架、小插件。关键章节：工具函数、插件列表 | /views-beetl/、/datagrid/ |
| 国际化 | 后端国际化、多语言 | /i18n-locale/ | 后端国际化、多语言配置。关键章节：语言包、Locale配置 | /vue-i18n/ |
| 自定义视图 | 修改内置视图、修改登录页 | /custom-views/ | 自定义视图、修改内置页面。关键章节：修改登录页、扩展视图 | /views-beetl/ |


## 常见问题映射

| 用户问题 | 推荐文档 | WebFetch URL |
|----------|----------|-------------|
| Beetl视图怎么写？ | Beetl视图 | https://jeesite.com/docs/views-beetl/ |
| DataGrid怎么用？ | DataGrid | https://jeesite.com/docs/datagrid/ |
| JS工具库有哪些？ | JS框架 | https://jeesite.com/docs/jeesite-js/ |
| 经典版国际化？ | 国际化 | https://jeesite.com/docs/i18n-locale/ |
| 如何修改登录页？ | 自定义视图 | https://jeesite.com/docs/custom-views/ |
