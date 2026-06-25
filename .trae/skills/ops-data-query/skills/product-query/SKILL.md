---
name: product-query
description: 查询产品信息，包括产品名称、产品级别、所属部门、产品经理、运维负责人等。支持按产品名称、ID、启用状态筛选。
version: 3.0.0
author: Skill Agent Team
---

# 产品查询技能

> ⚠️ **v3.0 说明**：通用参数映射、输出模板、错误处理已抽离到共享文件，详见下方链接。

## 功能描述

查询产品信息，包括：
- 产品名称、功能/主责
- 产品级别（级/二级）
- 上级产品
- 所属单位/部门
- 产品经理、运维负责人
- 启用状态

## 触发条件

**关键词**：产品、产品信息、产品名称、产品ID、产品列表、产品线

**排他条件**：
- 查服务器配置 → 使用 `cmdb-server-query`
- 查公网IP → 使用 `server-public-ip-query`
- 查部署记录 → 使用 `project-deployment-query`
- 查项目代码/SVN/GIT → 使用 `project-basis-query`

## 输入参数

| 参数名 | 类型 | 说明 | 默认值 | 来源 |
|--------|------|------|--------|------|
| id | string | 产品 ID | - | 用户输入 |
| name | string | 产品名称（模糊匹配） | - | 用户输入 |
| flag | integer | 启用状态 | - | 用户输入（0=禁用, 1=启用） |
| currentPage | integer | 页码 | 1 | 自动 |
| pageSize | integer | 每页条数 | 40 | 数量词映射 |

## 工具调用 Schema

```json
{
  "name": "product_query",
  "description": "查询产品信息，包括产品名称、产品级别、所属部门、产品经理、运维负责人等",
  "parameters": {
    "type": "object",
    "properties": {
      "id": { "type": "string", "description": "产品 ID" },
      "name": { "type": "string", "description": "产品名称（模糊匹配）" },
      "flag": { "type": "integer", "description": "启用标志：0=禁用, 1=启用" },
      "currentPage": { "type": "integer", "description": "页码", "minimum": 1 },
      "pageSize": { "type": "integer", "description": "每页条数", "minimum": 1, "maximum": 100 }
    },
    "required": []
  }
}
```

## API 信息

**端点**：`POST https://oss.tech.ctseelink.cn/a/cmdb/baseProduct/`
**来源**：`config/api_endpoints.json` → `product-query`

## 响应字段

### records 中的字段

| 字段 | 类型 | 说明 | 格式化 |
|------|------|------|--------|
| productName | string | 产品名称 | - |
| productFunction | string | 产品功能/主责 | - |
| parentProduct | string | 上级产品 | - |
| productLevel | string | 产品级别 | 一级/二级 |
| enabled | string | 启用状态 | 是/否 |
| department | string | 所属部门 | - |
| productManager | string | 产品经理 | - |
| opsLead | string | 运维负责人 | - |

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
| 产品名称 | 上级产品 | 级别 | 状态 |
|----------|----------|------|------|
```

### 详细输出

增加以下字段：产品功能、所属部门、产品经理、运维负责人

### 降级输出

当 API 失败时，从 `references/mock_responses.json` → `product-query` 获取 Mock 数据。

## 示例

**输入**："查询所有启用的产品"

**工具调用**：
```json
{
  "tool_name": "product_query",
  "parameters": {
    "flag": 1,
    "currentPage": 1,
    "pageSize": 100
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
