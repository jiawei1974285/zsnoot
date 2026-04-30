# Wiki Schema — 民警随手记

## 页面类型

| 类型 | 目录 | 用途 |
|------|------|------|
| case | wiki/cases/ | 案件记录（治安案件、刑事案件） |
| person | wiki/persons/ | 相关人员（嫌疑人、受害人、证人等） |
| location | wiki/locations/ | 案发地点、相关地点 |
| law | wiki/laws/ | 相关法条、法规依据 |
| technique | wiki/techniques/ | 办案技巧、技战法 |
| note | wiki/notes/ | 日常工作记录、巡逻笔记 |
| summary | wiki/summaries/ | 跨案件分析、串并案研判 |

## 命名规范

- 文件：`kebab-case.md`（小写连字符）
- 案件：`YYYY-类型-简述.md`（例：`2024-盗窃-小区电动车.md`）
- 人物：`类型-姓名.md`（例：`嫌疑人-张某.md`、`受害人-李某.md`）
- 地点：`地点名称.md`（例：`XX小区.md`、`XX街道.md`）
- 法规：`法规名-条款.md`（例：`治安管理处罚法-第49条.md`）
- 技战法：`技法名称.md`（例：`视频追踪技战法.md`）
- 笔记：`YYYY-MM-DD-简述.md`（例：`2024-03-15-巡逻记录.md`）

## Frontmatter 格式

所有页面必须包含 YAML frontmatter：

```yaml
---
type: case | person | location | law | technique | note | summary
title: 人类可读标题
tags: []
related: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

**案件页面额外字段：**
```yaml
case_type: 盗窃 | 诈骗 | 伤害 | 纠纷 | 其他
status: 立案 | 侦查中 | 已结案 | 串并案
date_occurred: YYYY-MM-DD
```

**人物页面额外字段：**
```yaml
role: 嫌疑人 | 受害人 | 证人 | 其他
case_ref: "[[case-slug]]"
```

**地点页面额外字段：**
```yaml
address: 详细地址
case_refs:
  - "[[case-slug]]"
```

## 索引格式

`wiki/index.md` 按类型列出所有页面，每条格式：
```
- [[page-slug]] — 一句话描述
```

## 日志格式

`wiki/log.md` 按时间倒序记录活动：
```
## YYYY-MM-DD

- 做了什么 / 发现了什么
```

## 交叉引用规则

- 使用 `[[page-slug]]` 语法在页面间建立链接
- 每个实体和概念都应出现在 `wiki/index.md` 中
- 案件页链接相关人物、地点、法规
- 人物页链接相关案件
- 地点页链接相关案件

## 矛盾处理

当信息冲突时：
1. 在相关页面标注矛盾点
2. 创建 query 页面跟踪待解决问题
3. 两个来源都从 query 页面链接
4. 证据充分时在 summary 页面解决

## 警务工作规范

- 案件记录要客观准确，区分事实和推断
- 人物信息注意隐私保护（使用化名/缩写）
- 定期更新案件状态
- 发现串并案线索及时创建 summary 页面
- 技战法页面要可操作、可复用

<!-- CUSTOM_CATEGORIES_START -->

## 自定义页面类型

| 类型 | 目录 | 用途 |
|------|------|------|
| type | wiki/type/ | 违法犯罪类型 |

自定义类型由系统配置生成。LLM 入库时可根据材料语义选择这些类型，并将页面写入对应目录。

Frontmatter `type` 允许使用以上自定义类型。

<!-- CUSTOM_CATEGORIES_END -->
