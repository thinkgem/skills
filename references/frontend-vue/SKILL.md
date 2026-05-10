---
name: "frontend-vue"
description: "检索JeeSite Vue前端开发文档（CRUD、表单、表格、组件、权限等）。Invoke when user asks about Vue frontend, form development, table components, or Vue3 development."
---

# Vue 前端手册

JeeSite Vue3 前端开发指南，包括安装部署、CRUD视图、表单、表格、组件、权限、国际化等。

## 文档获取方式

按需缓存，有效期3天。优先从本地缓存读取，缓存过期或不存在时自动下载并转换为 Markdown：

- **缓存目录**: `references/.cache/frontend-vue/`（权限不足时自动回退到 `~/.cache/jeesite/frontend-vue/`）
- **缓存命令**: `python3 scripts/cache_docs.py --skill frontend-vue --permalink <permalink>`
- **强制更新**: `python3 scripts/cache_docs.py --skill frontend-vue --permalink <permalink> --force`

## 关键词

Vue、Vue3、前端分离、CRUD、表单、Form、表格、Table、组件、权限、图标、国际化、样式、Webpack、BasicForm、BasicTable、v-auth、Icon、i18n、Less、UnoCSS、Vite、TypeScript、Antdv、Vben Admin、Hooks、路由守卫、菜单权限、按钮权限、主题、编译打包、外部依赖、第三方库

## 触发场景

- Vue前端如何安装部署
- 如何开发CRUD页面
- 表单组件怎么用
- 表格组件怎么用
- 有哪些通用组件
- 前端权限怎么控制
- 图标怎么用
- 国际化怎么配
- 样式主题怎么改
- 如何引入外部依赖
- Vue前端常见问题
- BasicForm怎么用
- BasicTable怎么用
- v-auth指令
- 路由守卫
- 菜单权限
- 按钮权限
- 主题定制
- 编译打包
- Vite配置
- TypeScript
- Ant Design Vue

## 文档映射

| 文档标题 | sidebarTitle | permalink | 摘要与关键章节 | 关联文档 |
|----------|-------------|-----------|---------------|---------|
| 安装部署 | 快速开始、安装部署 | /vue-install-deploy/ | Vue前端环境搭建、编译打包。关键章节：环境要求、安装步骤、打包部署 | /install-deploy/、/vue-faq/ |
| CRUD视图 | 源码解析、表单列表 | /vue-crud-view/ | CRUD增删改查视图开发、源码解析。关键章节：列表页、表单页、详情页 | /vue-basic-form/、/vue-basic-table/ |
| 基础表单 | BasicForm 表单组件 | /vue-basic-form/ | BasicForm表单组件用法。关键章节：表单配置、校验规则、联动 | /vue-crud-view/、/vue-comp/ |
| 基础表格 | BasicTable 表格组件 | /vue-basic-table/ | BasicTable表格组件用法。关键章节：列配置、分页、排序、筛选 | /vue-crud-view/、/vue-comp/ |
| 通用组件 | 常用组件库、Hooks | /vue-comp/ | 通用组件库、Hooks用法。关键章节：组件列表、Hooks API | /vue-basic-form/、/vue-basic-table/ |
| 配置设置 | 配置参数、主题配置 | /vue-settings/ | 前端配置参数、主题设置。关键章节：应用配置、主题定制 | /vue-style/、/vue-i18n/ |
| 权限控制 | 前端权限、按钮权限 | /vue-auth/ | 前端权限控制、v-auth指令、菜单权限。关键章节：权限指令、路由守卫 | /permi-shiro/、/vue-crud-view/ |
| 图标 | 图标 Icon Svg 组件 | /vue-icon/ | 图标Icon使用、SVG组件。关键章节：内置图标、自定义图标 | /vue-comp/ |
| 国际化 | 国际化、多语言 | /vue-i18n/ | 前端国际化i18n、多语言配置。关键章节：语言包、切换语言 | /i18n-locale/、/vue-settings/ |
| 样式主题 | LessCSS 样式库 | /vue-style/ | LessCSS样式库、主题定制。关键章节：样式变量、主题切换 | /vue-settings/ |
| 引入外部依赖 | 引入外部依赖 | /webpack-lib/ | Webpack构建、引入第三方库。关键章节：依赖引入、构建配置 | /vue-install-deploy/ |
| 常见问题 | 分离版常见问题 | /vue-faq/ | Vue前端常见问题排查。关键章节：安装问题、编译问题、运行问题 | /vue-install-deploy/、/faq/ |

## 检索策略

1. 根据用户问题匹配"触发场景"或"关键词"
2. 在"文档映射"表中定位最相关的文档，获取 permalink
3. 执行缓存命令：`python3 scripts/cache_docs.py --skill frontend-vue --permalink <permalink>`
   - 若缓存有效（3天内），直接返回缓存文件路径
   - 若缓存过期或不存在，自动下载并转换为 Markdown 保存
4. 使用 Read 工具读取返回的缓存文件路径
5. 基于文档内容回答用户

## 常见问题映射

| 用户问题 | 推荐文档 | WebFetch URL |
|----------|----------|-------------|
| Vue前端如何安装？ | 安装部署 | https://jeesite.com/docs/vue-install-deploy/ |
| 如何开发CRUD页面？ | CRUD视图 | https://jeesite.com/docs/vue-crud-view/ |
| 表单组件怎么用？ | 基础表单 | https://jeesite.com/docs/vue-basic-form/ |
| 表格组件怎么用？ | 基础表格 | https://jeesite.com/docs/vue-basic-table/ |
| 有哪些通用组件？ | 通用组件 | https://jeesite.com/docs/vue-comp/ |
| 前端权限怎么控制？ | 权限控制 | https://jeesite.com/docs/vue-auth/ |
| 图标怎么用？ | 图标 | https://jeesite.com/docs/vue-icon/ |
| 国际化怎么配？ | 国际化 | https://jeesite.com/docs/vue-i18n/ |
| 样式主题怎么改？ | 样式主题 | https://jeesite.com/docs/vue-style/ |
| 如何引入第三方库？ | 引入外部依赖 | https://jeesite.com/docs/webpack-lib/ |
| Vue前端常见问题？ | 常见问题 | https://jeesite.com/docs/vue-faq/ |
