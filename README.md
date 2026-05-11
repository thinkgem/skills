# JeeSite Skills

JeeSite 快速开发平台文档 Skills 集合，供 AI Agent 检索和调用。共 7 个子 Skill，覆盖 JeeSite 在线文档。

* Gitee: <https://gitee.com/thinkgem/skills>
* Github: <https://github.com/thinkgem/skills>
* AtomGit: <https://atomgit.com/thinkgem/skills>

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

## 快速路由

| 用户问题方向 | 推荐Skill |
|-------------|-----------|
| JeeSite是什么、架构、技术选型、功能介绍 | quick-start |
| 安装部署、代码生成、DAO、MyBatis、Shiro、数据权限 | backend-dev |
| Vue3、前端CRUD、表单、表格、组件、前端权限 | frontend-vue |
| Beetl、DataGrid、经典前端、全栈版 | frontend-beetl |
| BPM工作流、CMS、SSO、OAuth2、消息推送、作业调度 | extend-fun |
| SaaS多租户、集群、微服务、分布式事务、分库分表 | cloud-arch |
| 技术支持、版本区别、联系方式、授权 | support |

## 安装方法

```bash
# 添加 JeeSite 技能
npx skills add thinkgem/skills -g
# 或者
npx skills add https://gitee.com/thinkgem/skills.git -g

# 添加 Antdv Next 技能
npx skills add antdv-next/skills -g

# 添加 pinia、pnpm、tsdown、turborepo、vite、unocss、vue、vue-* 技能
npx skills add antfu/skills --skill='*' -g

# 添加 Spring Boot 技能
npx skills add github/awesome-copilot --skill java-springboot -g
```

推荐：添加 -g 参数，全局安装。

## 使用方法

为了获得最稳定的效果，建议在提示词前加上：

```
Use <技能名称> skill, <你的需求>
```

这样可以显式触发技能；否则可能因匹配度不足导致触发不稳定。

### 文档缓存机制（自动）

文档采用按需缓存策略，有效期3天。Skill 在调用时自动处理缓存逻辑：

1. 优先从本地缓存读取文档
2. 缓存过期或不存在时自动下载并转换为 Markdown
3. 缓存文档自动拆分为多文件，Token 消耗降低 60%-80%
4. 网络失败时使用过期缓存作为降级方案
5. 文档中的图片可自动下载并缓存

### 缓存目录

缓存目录支持自动权限回退机制：

- **默认缓存目录**：`references/.cache/<skill-name>/`（技能目录下）
- **权限不足时自动回退到**：`~/.cache/jeesite/<skill-name>/`

**注意**：当技能安装在受保护目录（如 `/Users/admin/.agents/skills/`）时，脚本会自动检测权限并回退到用户目录，无需手动配置。

## 工作流程

1. 根据用户问题，匹配最相关的子 Skill
2. 加载对应 `references/<name>/SKILL.md` 获取文档映射
3. 根据映射表定位具体文档，获取 permalink
4. 执行缓存命令获取文档内容
5. 基于文档内容回答用户问题
6. 如果问题跨多个 Skill，可同时加载多个子 Skill

## 许可证

Apache License 2.0，详见 [LICENSE](LICENSE)。
