---
name: project-deployment-query
description: 查询项目部署记录，包括部署时间、版本、环境、状态、部署人等。支持按项目名、环境、状态、时间范围筛选。
version: 3.0.0
author: Skill Agent Team
---

# 项目部署查询技能

> ⚠️ **v3.0 说明**：通用参数映射、输出模板、错误处理已抽离到共享文件，详见下方链接。

## 功能描述

查询项目部署记录，包括：
- 部署基本信息：项目名、环境、状态
- 时间信息：开始时间、结束时间、耗时
- 版本信息：Git 分支、版本号、部署人
- 服务器列表：每台部署目标服务器的状态

## 触发条件

**关键词**：部署、部署记录、部署状态、部署历史、发布、上线

**排他条件**：
- 查服务器配置 → 使用 `cmdb-server-query`
- 查公网IP → 使用 `server-public-ip-query`
- 查产品信息 → 使用 `product-query`
- 查项目代码 → 使用 `project-basis-query`

## 输入参数

| 参数名 | 类型 | 说明 | 默认值 | 来源 |
|--------|------|------|--------|------|
| projectName | string | 项目名称（模糊匹配） | - | 用户输入 |
| environment | integer | 环境代码 | - | param_mappings.json → env_mapping |
| statusCode | integer | 部署状态 | - | param_mappings.json → deploy_status_mapping |
| deployer | string | 部署人 | - | 用户输入 |
| startTime | string | 开始时间（YYYY-MM-DD） | - | 用户输入 |
| endTime | string | 结束时间（YYYY-MM-DD） | - | 用户输入 |
| currentPage | integer | 页码 | 1 | 自动 |
| pageSize | integer | 每页条数 | 40 | 数量词映射（默认40，非15） |

## 工具调用 Schema

```json
{
  "name": "project_deployment_query",
  "description": "查询项目部署记录，包括部署时间、版本、环境、状态、部署人等",
  "parameters": {
    "type": "object",
    "properties": {
      "projectName": { "type": "string", "description": "项目名称（模糊匹配）" },
      "environment": { "type": "integer", "description": "环境代码：1=测试, 2=灰度, 3=生产, 4=研发" },
      "statusCode": { "type": "integer", "description": "部署状态：0=成功, 1=失败, 2=进行中, 3=待部署" },
      "deployer": { "type": "string", "description": "部署人姓名" },
      "startTime": { "type": "string", "description": "开始时间，格式 YYYY-MM-DD" },
      "endTime": { "type": "string", "description": "结束时间，格式 YYYY-MM-DD" },
      "currentPage": { "type": "integer", "description": "页码", "minimum": 1 },
      "pageSize": { "type": "integer", "description": "每页条数", "minimum": 1, "maximum": 100 }
    },
    "required": []
  }
}
```

## API 信息

**端点**：`POST https://oss.tech.ctseelink.cn/a/cmdb/baseProject/`
**来源**：`config/api_endpoints.json` → `project-deployment-query`

## 响应字段

### records 中的字段

| 字段 | 类型 | 说明 | 格式化 |
|------|------|------|--------|
| id | string | 部署记录 ID | - |
| projectName | string | 项目名称 | - |
| environment | string | 环境名称 | 测试/灰度/生产/研发 |
| environmentCode | integer | 环境代码 | 同上 |
| deploymentStatus | string | 部署状态（中文） | ✅成功/❌失败 |
| statusCode | integer | 状态代码 | 0=成功, 1=失败, 2=进行中 |
| startTime | string | 开始时间 | YYYY-MM-DD HH:mm:ss |
| endTime | string | 结束时间 | YYYY-MM-DD HH:mm:ss |
| duration | integer | 耗时（秒） | 格式化为 X分Y秒 |
| deployer | string | 部署人 | - |
| version | string | 版本号 | - |
| gitBranch | string | Git 分支 | - |
| serverList | array | 部署目标服务器列表 | 格式化列表 |
| errorMessage | string | 错误信息 | ❌ + 红色高亮 |

### serverList 数组格式

```json
[
  {"hostName": "prod-guizhou-app-01", "ip": "192.168.7.101", "status": "成功"},
  {"hostName": "prod-guizhou-app-02", "ip": "192.168.7.102", "status": "成功"}
]
```

格式化：`主机名(IP) ✅` 或 `主机名(IP) ❌（失败原因）`

### 分页字段

| 标准名 | API 字段 |
|--------|---------|
| currentPage | currentPage |
| pageSize | pageSize |
| total | total |

## 输出格式

### 标准输出

使用 `references/output_templates.md` 中的标准模板，标准模式字段：

```
| 项目名 | 环境 | 状态 | 部署时间 | 耗时 | 版本 | 部署人 |
|--------|------|------|---------|------|------|--------|
```

### 详细输出

增加以下字段：Git分支、服务器列表（成功/失败详情）、错误信息

> ⚠️ `statusCode=1`（失败）时，`errorMessage` 必须用 ❌ 红色高亮显示

### 降级输出

当 API 失败时，从 `references/mock_responses.json` → `project-deployment-query` 获取 Mock 数据。

## 示例

**输入**："查最近7天部署失败的项目"

**工具调用**：
```json
{
  "tool_name": "project_deployment_query",
  "parameters": {
    "statusCode": 1,
    "startTime": "2026-06-17",
    "currentPage": 1,
    "pageSize": 40
  }
}
```

**输入**："查 guizh-rules-api 项目的生产部署"

**工具调用**：
```json
{
  "tool_name": "project_deployment_query",
  "parameters": {
    "projectName": "guizh-rules-api",
    "environment": 3,
    "currentPage": 1,
    "pageSize": 40
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
| `config/param_mappings.json` | ✅ env_mapping, deploy_status_mapping |
| `config/api_endpoints.json` | ✅ API 端点配置 |
| `config/field_mappings.json` | ✅ 响应字段标准化 |

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 3.0 | 2026-06-24 | 抽离共享内容，统一 pageSize=40，修复 serverList 展示 |
| 2.0 | 2026-06-18 | 统一字段为英文 key，修复数据模型 |
| 1.0 | 2026-05-20 | 初始版本 |
