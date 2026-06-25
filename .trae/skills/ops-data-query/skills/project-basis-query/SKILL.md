---
name: project-basis-query
description: 查询工程项目基础信息，包括项目名称、中文名、所属产品、SVN/GIT 仓库地址、项目类型、父项目等。
version: 3.0.0
author: Skill Agent Team
---

# 工程项目信息查询技能

> ⚠️ **v3.0 说明**：通用参数映射、输出模板、错误处理已抽离到共享文件，详见下方链接。

## 功能描述

查询工程项目基础信息，包括：
- 项目名称（唯一标识）、中文名
- 所属产品
- SVN/GIT 仓库地址
- 项目类型（核心组件/中间件等）
- 父项目、分组信息

## 触发条件

**关键词**：工程项目、项目信息、项目配置、代码仓库、SVN、GIT、仓库地址、项目名称

**排他条件**：
- 查服务器配置 → 使用 `cmdb-server-query`
- 查公网IP → 使用 `server-public-ip-query`
- 查部署记录 → 使用 `project-deployment-query`
- 查产品信息 → 使用 `product-query`

## 输入参数

| 参数名 | 类型 | 说明 | 默认值 | 来源 |
|--------|------|------|--------|------|
| id | string | 项目 ID | - | 用户输入 |
| name | string | 工程项目名称（模糊匹配） | - | 用户输入 |
| productId | string | 产品 ID | - | 用户输入 |
| productName | string | 产品名称（模糊匹配） | - | 用户输入 |
| currentPage | integer | 页码 | 1 | 自动 |
| pageSize | integer | 每页条数 | 40 | 数量词映射 |

## 工具调用 Schema

```json
{
  "name": "project_basis_query",
  "description": "查询工程项目基础信息，包括项目名称、中文名、所属产品、SVN/GIT仓库地址、项目类型、父项目等",
  "parameters": {
    "type": "object",
    "properties": {
      "id": { "type": "string", "description": "项目 ID" },
      "name": { "type": "string", "description": "工程项目名称（模糊匹配）" },
      "productId": { "type": "string", "description": "产品 ID" },
      "productName": { "type": "string", "description": "产品名称（模糊匹配）" },
      "currentPage": { "type": "integer", "description": "页码", "minimum": 1 },
      "pageSize": { "type": "integer", "description": "每页条数", "minimum": 1, "maximum": 100 }
    },
    "required": []
  }
}
```

## API 信息

**端点**：`POST https://oss.tech.ctseelink.cn/a/cmdb/baseProjectBasis/`
**来源**：`config/api_endpoints.json` → `project-basis-query`

## 响应字段

### records 中的字段

| 字段 | 类型 | 说明 | 格式化 |
|------|------|------|--------|
| projectName | string | 项目名称（唯一标识） | - |
| chineseName | string | 中文名 | - |
| productName | string | 所属产品 | - |
| repoPath | string | SVN/GIT 仓库地址 | - |
| description | string | 项目描述 | - |
| projectType | string | 项目类型 | 核心组件/中间件等 |
| parentProject | string | 父项目名 | - |
| group | string | 分组 | - |

### 分页字段 ⚠️

> ⚠️ 本 API 的分页字段名与其他 API 不同！

| 标准名 | API 字段 |
|--------|---------|
| currentPage | current |
| pageSize | size |

> 处理响应时：`data.current` → 标准 currentPage，`data.size` → 标准 pageSize

## 输出格式

### 标准输出

使用 `references/output_templates.md` 中的标准模板，标准模式字段：

```
| 项目名称 | 中文名 | 所属产品 | 项目类型 |
|----------|--------|----------|----------|
```

### 详细输出

增加以下字段：代码仓库、父项目、分组、项目描述

### 降级输出

当 API 失败时，从 `references/mock_responses.json` → `project-basis-query` 获取 Mock 数据。

## 示例

**输入**："找天翼看家的工程项目"

**工具调用**：
```json
{
  "tool_name": "project_basis_query",
  "parameters": {
    "productName": "天翼看家",
    "currentPage": 1,
    "pageSize": 100
  }
}
```

**输入**："查 tykj-kafka-test 项目的代码仓库"

**工具调用**：
```json
{
  "tool_name": "project_basis_query",
  "parameters": {
    "name": "tykj-kafka-test"
  }
}
```

---

## 共享文件引用

| 文件 | 用途 |
|------|------|
| `references/output_templates.md` | ✅ 标准/详细/降级输出模板 |
| `references/error_scenarios.md` | ✅ 错误场景处理 |
| `references/mock_responses.json` | ✅ Mock 数据源 |
| `references/param_guides.md` | ✅ 通用参数映射参考 |
| `config/param_mappings.json` | ✅ 通用参数 |
| `config/api_endpoints.json` | ✅ API 端点配置 |
| `config/field_mappings.json` | ✅ ⚠️ 本 API 分页字段为 current/size |

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 3.0 | 2026-06-24 | 抽离共享内容，标注分页字段差异 |
| 2.0 | 2026-06-18 | 统一字段为英文 key |
| 1.0 | 2026-05-20 | 初始版本 |
