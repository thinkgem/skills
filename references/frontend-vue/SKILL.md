---
name: "frontend-vue"
description: "检索JeeSite Vue前端开发文档（CRUD、表单、表格、组件、权限等）。Invoke when user asks about Vue frontend, form development, table components, or Vue3 development."
---

# Vue 前端手册

JeeSite Vue3 前端开发指南，包括安装部署、CRUD视图、表单、表格、组件、权限、国际化等。

## 使用流程

1. **匹配文档**：根据用户问题，在「文档映射」表中查找最相关的 permalink
2. **获取缓存**：在 jeesite skills 根目录下执行 `python3 scripts/cache_docs.py --skill frontend-vue --permalink <permalink>` 脚本，缓存目录为 `references/.cache/frontend-vue/`，不存在时自动回退到 `~/.cache/jeesite/frontend-vue/`
3. **读取内容**：先读 `__00.md` 目录索引文件，了解章节结构，按需读取 `__01.md`~`__NN.md`
4. **回答问题**：缓存文件有效期3天，自动更新缓存，并基于读取的文档内容回答

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
- Antdv Next

### AI 强制触发（代码生成前置条件）

**以下场景必须先加载 quick-start Skill 并读取 `/standard/` 规范文档**：
- 创建 Vue CRUD 页面（list/form/api）
- 表单字段控件选择（showType → Vue 组件映射）
- 栅格布局配置（gridRowCol）
- 字段验证规则书写
- 金额/日期/数字字段格式化显示
- 前端权限注解 v-auth 使用

## 文档映射

| 文档标题 | sidebarTitle | permalink | 摘要与关键章节 | 关联文档 |
|----------|-------------|-----------|---------------|---------|
| 安装部署 | 快速开始、安装部署 | /vue-install-deploy/ | Vue前端环境搭建、编译打包。关键章节：环境要求、安装步骤、打包部署 | /install-deploy/、/vue-faq/ |
| CRUD视图 | 源码解析、表单列表 | /vue-crud-view/ | CRUD增删改查视图开发、源码解析。**⚠️ 开发前先读 /standard/ 前端规范（showType控件映射、gridRowCol布局、验证规则）** | /standard/、/vue-basic-form/、/vue-basic-table/ |
| 基础表单 | BasicForm 表单组件 | /vue-basic-form/ | BasicForm表单组件用法。关键章节：表单配置、校验规则、联动。**⚠️ 字段验证参照 /standard/ fieldValid 映射** | /standard/、/vue-crud-view/、/vue-comp/ |
| 基础表格 | BasicTable 表格组件 | /vue-basic-table/ | BasicTable表格组件用法。关键章节：列配置、分页、排序、筛选。**⚠️ 列对齐/显示格式参照 /standard/ 数据列表规范** | /standard/、/vue-crud-view/、/vue-comp/ |
| 通用组件 | 常用组件库、Hooks | /vue-comp/ | 通用组件库、Hooks用法。关键章节：组件列表、Hooks API | /vue-basic-form/、/vue-basic-table/ |
| 配置设置 | 配置参数、主题配置 | /vue-settings/ | 前端配置参数、主题设置。关键章节：应用配置、主题定制 | /vue-style/、/vue-i18n/ |
| 权限控制 | 前端权限、按钮权限 | /vue-auth/ | 前端权限控制、v-auth指令、菜单权限。关键章节：权限指令、路由守卫 | /permi-shiro/、/vue-crud-view/ |
| 图标 | 图标 Icon Svg 组件 | /vue-icon/ | 图标Icon使用、SVG组件。关键章节：内置图标、自定义图标 | /vue-comp/ |
| 国际化 | 国际化、多语言 | /vue-i18n/ | 前端国际化i18n、多语言配置。关键章节：语言包、切换语言 | /i18n-locale/、/vue-settings/ |
| 样式主题 | LessCSS 样式库 | /vue-style/ | LessCSS样式库、主题定制。关键章节：样式变量、主题切换 | /vue-settings/ |
| 引入外部依赖 | 引入外部依赖 | /webpack-lib/ | Webpack构建、引入第三方库。关键章节：依赖引入、构建配置 | /vue-install-deploy/ |
| 常见问题 | 分离版常见问题 | /vue-faq/ | Vue前端常见问题排查。关键章节：安装问题、编译问题、运行问题 | /vue-install-deploy/、/faq/ |

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
