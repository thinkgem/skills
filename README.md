# JeeSite Skills

> **让 AI 真正读懂 JeeSite，让开发效率提升10倍！**

## 为什么使用？

你是否曾经遇到过这些问题：

- 面对海量的 JeeSite 文档，找不到想要的内容
- 询问 AI 助手时，得到的答案不准确或过时
- 每次都要手动搜索、翻阅文档，效率低下
- AI 回答缺乏上下文，无法给出针对性的解决方案

**现在，这一切都将成为历史！**

这是一套专为 AI Agent 设计的智能文档检索系统，让 AI 真正理解 JeeSite，为你提供精准、实时、专业的技术支持。

## 核心亮点

### 精准路由，快速响应

包括 1 主 Skill，7 大专业子 Skill，覆盖 JeeSite 全栈开发场景：

| Skill name     | 名称    | 说明   |
|----------------|---------|---------|
| jeesite        | JeeSite | JeeSite 平台文档总索引  |
| quick-start    | 快速了解    | 平台简介、架构特点、技术选型、功能介绍等基础知识、更新日志、升级方法 |
| backend-dev    | 后端开发手册  | 安装部署、代码生成、DAO、@Table、数据权限、Shiro等后端开发指南 |
| frontend-vue   | Vue前端手册 | 前端安装、前端CRUD、表单、表格、组件、权限等前端开发指南 |
| frontend-beetl | 经典前端手册  | Beetl视图、Form、DataGrid、JS框架等经典前端开发指南 |
| extend-fun     | 扩展功能专题  | BPM工作流、AI相关、CMS、SSO、OAuth2、定时任务、对象存储、敏感词等扩展功能 |
| cloud-arch     | 云服务技术架构 | SaaS、集群、微服务、分布式事务等云服务架构 |
| support        | 技术支持与服务 | 技术支持服务、版本区别、联系方式 |

### 用户问题，推荐方向

| 用户问题方向 | 推荐Skill |
|-------------|-----------|
| JeeSite是什么、架构、技术选型、功能介绍 | quick-start |
| 安装部署、代码生成、DAO、MyBatis、Shiro、数据权限 | backend-dev |
| Vue3、前端CRUD、表单、表格、组件、前端权限 | frontend-vue |
| Beetl、DataGrid、经典前端、全栈版 | frontend-beetl |
| BPM工作流、CMS、SSO、OAuth2、消息推送、作业调度 | extend-fun |
| SaaS多租户、集群、微服务、分布式事务、分库分表 | cloud-arch |
| 技术支持、版本区别、联系方式、授权 | support |

### 语义化检索，精准匹配

不再依赖关键词匹配，而是通过：

- 触发场景识别
- 关键词智能分析
- 文档映射表精准定位
- 跨 Skill 协同检索

确保每次都能找到最相关的文档内容。

### 传统方式 vs Skills方式

| 对比项 | 传统方式            | Skills 方式    |
|--------|-----------------|--------------|
| 查找文档 | 手动搜索，耗时 5-10 分钟 | AI 自动检索，秒级响应 |
| 答案准确性 | 依赖个人经验，可能出错     | 基于官方文档，准确可靠  |
| 知识更新 | 需要手动关注更新        | 自动同步最新文档     |
| 学习效率 | 需要阅读大量文档        | AI 提炼重点，快速掌握 |
| 问题解决 | 可能需要多次尝试        | 一次性给出完整方案    |

### 核心价值

- **提升开发效率**：减少 80% 的文档查阅时间  
- **降低学习成本**：新手也能快速上手  
- **保证代码质量**：基于最佳实践的建议  
- **促进团队协作**：统一的技术标准和规范 

## 快速上手

### 一键安装

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

**在你的AI编程助手中使用**
   - Claude Code
   - Codex
   - Cursor
   - GitHub Copilot
   - Lingma
   - Trae
   - Windsurf
   - 或其他支持Skills的AI工具

### 使用方式

在提问时显式指定 Skill，获得最佳效果：

```
Use <技能名称> skill, <你的需求>
```

**总索引中**
```
Use jeesite skill, 树结构设计的优点？
```

**指定分类**
```
Use backend-dev skill, 如何配置数据权限？
Use frontend-vue skill, Vue3表单验证怎么做？
Use cloud-arch skill, SaaS多租户如何实现？
``` 

## 技术原理

### 工作流程

```
用户提问 
  ↓
智能路由（匹配最相关的Skill）
  ↓
加载文档映射表（references/<name>/SKILL.md）
  ↓
检查本地缓存（根据映射表定位具体文档，获取 permalink）
  ↓
缓存有效 → 直接读取；缓存失效 → 自动下载并转换
  ↓
AI基于文档内容生成回答
```

如果问题跨多个 Skill，可同时加载多个子 Skill

### 技术特性

- **Python脚本驱动**：自动化文档抓取和 Markdown 转换
- **模块化设计**：每个 Skill 独立维护，易于扩展
- **缓存机制**：自动拆分大文件，自动更新缓存
- **版本管理**：Git 版本控制，方便协作和回溯

### 文档缓存

文档采用按需缓存策略，Skill 在调用时自动处理缓存逻辑：

1. 优先从本地缓存读取文档，有效期3天（自动更新）
2. 缓存过期或不存在时自动下载并转换为 Markdown
3. 缓存文档自动拆分为多文件，Token 消耗降低 60%-80%
4. 网络失败时使用过期缓存作为降级方案
5. 文档中的图片可自动下载并缓存

### 缓存目录

缓存目录支持自动权限回退机制：

- **默认缓存目录**：`references/.cache/<skill-name>/`（技能目录下）
- **权限不足时自动回退到**：`~/.cache/jeesite/<skill-name>/`

**注意**：当技能安装在受保护目录（如 `/Users/admin/.agents/skills/`）时，脚本会自动检测权限并回退到用户目录，无需手动配置。

## 项目信息

- **Gitee**：<https://gitee.com/thinkgem/skills>
- **GitHub**：<https://github.com/thinkgem/skills>
- **AtomGit**：<https://atomgit.com/thinkgem/skills>

## 联系我们

- **技术支持**：<http://s.jeesite.com>
- **问题反馈**：<https://gitee.com/thinkgem/skills/issues>
- **社区交流**：加入 JeeSite 开发者社群，添加 jeesitex 邀请您

## 致谢

感谢所有JeeSite社区的贡献者，以及为这个项目提供宝贵建议的开发者们。

**让我们一起，用AI重新定义开发体验！**

*如果你觉得这个项目对你有帮助，欢迎：*
- ⭐ Star 我们的 GitHub、Gitee 或 AtomGit 仓库
- 💬 在仓库的 Issues 中，留下你的使用体验和建议
- 🔄 转发分享给更多开发者

**JeeSite Skills —— 让每一次提问都有价值！**

<img src="https://jeesite.com/assets/images/mp.png" width="180" style="margin-left:40px"><br>

> **使用微信扫码**：关注我们，获取更多 JeeSite 最新动态和技术干货！
