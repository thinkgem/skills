---
name: "backend-dev"
description: "检索JeeSite后端开发文档（安装部署、代码生成、DAO、数据权限、Shiro等）。Invoke when user asks about backend development, installation, code generation, MyBatis DAO, or Shiro permission."
---

# 后端开发手册

JeeSite 后端开发指南，包括安装部署、代码生成、持久层、业务层、控制层、权限认证等。

## 使用流程

1. **匹配文档**：根据用户问题，在「文档映射」表中查找最相关的 permalink
2. **获取缓存**：在 jeesite skills 根目录下执行 `python3 scripts/cache_docs.py --skill backend-dev --permalink <permalink>` 脚本，缓存目录为 `references/.cache/backend-dev/`，不存在时自动回退到 `~/.cache/jeesite/backend-dev/`
3. **读取内容**：先读 `__00.md` 目录索引文件，了解章节结构，按需读取 `__01.md`~`__NN.md`
4. **回答问题**：缓存文件有效期3天，自动更新缓存，并基于读取的文档内容回答

## 关键词

安装、部署、环境搭建、代码生成、DAO、MyBatis、@Table、数据权限、Service、Shiro、权限、工具类、数据库管理、REST API、FAQ、JDK、Maven、MySQL、IDEA、新建模块、修改包名、正式部署、war、初始化数据库、多数据源、SQL映射、数据范围、事务、角色权限、按钮权限、控制层、Swagger、接口开发、移动端接口、问题排查、常见问题

## 触发场景

- 如何安装部署JeeSite
- 如何生成代码
- DAO怎么写
- MyBatis怎么用
- 数据权限怎么配置
- Shiro权限怎么控制
- 系统工具类有哪些
- 数据库管理怎么用
- REST API接口
- 后端常见问题
- 环境要求
- JDK版本
- 初始化数据库
- 新建模块
- 修改包名
- 正式部署
- 多数据源配置
- SQL映射
- 事务管理
- 角色权限配置
- 按钮权限
- Swagger文档
- 移动端接口开发

## 文档映射

| 文档标题 | sidebarTitle | permalink | 摘要与关键章节 | 关联文档 |
|----------|-------------|-----------|---------------|---------|
| 安装部署 | 快速开始、安装部署 | /install-deploy/ | 环境搭建、新建模块、修改包名、正式部署。关键章节：开发环境、初始化数据库、部署 | /vue-install-deploy/、/faq/ |
| 代码生成 | 代码生成、表结构ER图 | /code-gen/ | 代码生成器、自动生成业务代码、ER图。关键章节：生成步骤、配置说明 | /dao-mybatis/、/vue-crud-view/ |
| DAO与MyBatis | 持久层、@Table、多数据源 | /dao-mybatis/ | MyBatis DAO、@Table注解、多数据源、SQL映射。关键章节：实体类、DAO接口、多数据源 | /code-gen/、/service-datascope/ |
| 数据权限 | 业务层、数据权限、库事务 | /service-datascope/ | 数据权限、数据范围、Service层、事务管理。关键章节：数据权限配置、事务 | /permi-shiro/、/dao-mybatis/ |
| 权限与Shiro | 控制层、功能权限、Shiro | /permi-shiro/ | Shiro权限认证、角色权限、按钮权限、控制层。关键章节：权限配置、注解使用 | /service-datascope/、/vue-auth/ |
| 系统工具类 | 系统工具类 | /sys-utils/ | 系统工具类、常用API。关键章节：字符串工具、日期工具、文件工具 | /faq/ |
| 数据库管理 | 动态维护数据、表、实体 | /dbm/ | 数据库管理、数据表建模、数据源管理。关键章节：表建模、实体生成 | /code-gen/、/dao-mybatis/ |
| REST API | REST API | /mobile-rest-api/ | REST接口开发、API规范、移动端接口。关键章节：接口规范、认证方式 | /uniapp/、/permi-shiro/ |
| 常见问题 | 常见问题 | /faq/ | 后端常见问题排查。关键章节：环境问题、配置问题、运行问题 | /install-deploy/、/config/ |

## 常见问题映射

| 用户问题 | 推荐文档 | WebFetch URL |
|----------|----------|-------------|
| 如何安装部署？ | 安装部署 | https://jeesite.com/docs/install-deploy/ |
| 如何使用代码生成？ | 代码生成 | https://jeesite.com/docs/code-gen/ |
| DAO层怎么写？ | DAO与MyBatis | https://jeesite.com/docs/dao-mybatis/ |
| 数据权限怎么配？ | 数据权限 | https://jeesite.com/docs/service-datascope/ |
| Shiro权限怎么用？ | 权限与Shiro | https://jeesite.com/docs/permi-shiro/ |
| 有哪些工具类？ | 系统工具类 | https://jeesite.com/docs/sys-utils/ |
| 数据库管理怎么用？ | 数据库管理 | https://jeesite.com/docs/dbm/ |
| REST API怎么写？ | REST API | https://jeesite.com/docs/mobile-rest-api/ |
| 后端常见问题？ | 常见问题 | https://jeesite.com/docs/faq/ |
