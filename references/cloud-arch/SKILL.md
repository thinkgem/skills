---
name: "cloud-arch"
description: "检索JeeSite云服务架构文档（SaaS、集群、微服务、分布式事务等）。Invoke when user asks about cloud architecture, SaaS, cluster, microservices, or distributed systems."
---

# 云服务技术架构

JeeSite 云服务架构指南，包括 SaaS 多租户、集群部署、Spring Cloud 微服务、分布式事务、分库分表等。

## 文档获取方式

按需缓存，有效期3天。优先从本地缓存读取，缓存过期或不存在时自动下载并转换为 Markdown：

- **缓存目录**: `references/.cache/cloud-arch/`（权限不足时自动回退到 `~/.cache/jeesite/cloud-arch/`）
- **缓存命令**: `python3 scripts/cache_docs.py --skill cloud-arch --permalink <permalink>`
- **强制更新**: `python3 scripts/cache_docs.py --skill cloud-arch --permalink <permalink> --force`

## 关键词

SaaS、多租户、集群、负载均衡、高可用、微服务、Spring Cloud、分布式事务、Seata、分库分表、ShardingSphere、监控、SkyWalking、ELK、日志

## 触发场景

- SaaS多租户怎么用
- 集群部署怎么配
- Spring Cloud微服务怎么搭建
- 分布式事务怎么处理
- 分库分表怎么配
- Spring Boot监控怎么用
- 链路追踪怎么配
- 日志收集怎么配

## 文档映射

| 文档标题 | sidebarTitle | permalink | 完整URL | 主题 |
|----------|-------------|-----------|---------|------|
| SaaS多租户 | SaaS架构、多租户 | /saas-corp-use/ | https://jeesite.com/docs/saas-corp-use/ | SaaS、多租户、企业版、租户隔离 |
| 集群部署 | 负载均衡、集群、高可用 | /cluster/ | https://jeesite.com/docs/cluster/ | 集群、负载均衡、高可用、Session共享 |
| Spring Cloud | SpringCloud分布式微服务 | /springcloud/ | https://jeesite.com/docs/springcloud/ | 微服务、Spring Cloud、服务注册、网关 |
| 分布式事务Seata | 分布式事务Seata、AT模式 | /springcloud-seata/ | https://jeesite.com/docs/springcloud-seata/ | Seata、分布式事务、AT模式、事务一致性 |
| 分库分表 | 读写分离、分库分表方案 | /sharding/ | https://jeesite.com/docs/sharding/ | 分库分表、ShardingSphere、数据分片、读写分离 |
| Spring Boot监控 | Spring Boot监控系统 | /webadmin/ | https://jeesite.com/docs/webadmin/ | Web管理、运维管理、Spring Boot Admin |
| SkyWalking | SkyWalking追踪系统 | /skywalking/ | https://jeesite.com/docs/skywalking/ | 链路追踪、APM、监控、SkyWalking |
| ELK日志 | ELK日志收集分析 | /elk-log/ | https://jeesite.com/docs/elk-log/ | ELK、日志收集、Elasticsearch、Logstash、Kibana |

## 检索策略

1. 根据用户问题匹配"触发场景"或"关键词"
2. 在"文档映射"表中定位最相关的文档，获取 permalink
3. 执行缓存命令：`python3 scripts/cache_docs.py --skill cloud-arch --permalink <permalink>`
   - 若缓存有效（3天内），直接返回缓存文件路径
   - 若缓存过期或不存在，自动下载并转换为 Markdown 保存
4. 使用 Read 工具读取返回的缓存文件路径
5. 基于文档内容回答用户

## 常见问题映射

| 用户问题 | 推荐文档 | WebFetch URL |
|----------|----------|-------------|
| SaaS多租户怎么用？ | SaaS多租户 | https://jeesite.com/docs/saas-corp-use/ |
| 集群部署怎么配？ | 集群部署 | https://jeesite.com/docs/cluster/ |
| Spring Cloud怎么搭建？ | Spring Cloud | https://jeesite.com/docs/springcloud/ |
| 分布式事务怎么处理？ | 分布式事务Seata | https://jeesite.com/docs/springcloud-seata/ |
| 分库分表怎么配？ | 分库分表 | https://jeesite.com/docs/sharding/ |
| Spring Boot监控？ | Spring Boot监控 | https://jeesite.com/docs/webadmin/ |
| 链路追踪怎么配？ | SkyWalking | https://jeesite.com/docs/skywalking/ |
| 日志收集怎么配？ | ELK日志 | https://jeesite.com/docs/elk-log/ |
