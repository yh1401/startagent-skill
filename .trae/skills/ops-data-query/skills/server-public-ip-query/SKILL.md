---
name: server-public-ip-query
description: 查询服务器公网 IP、带宽、网络类型、计费方式等信息。支持按机房节点、内网 IP 精确查询。
version: 3.0.0
author: Skill Agent Team
---

# 服务器公网 IP 查询技能

> ⚠️ **v3.0 说明**：通用参数映射、输出模板、错误处理已抽离到共享文件，详见下方链接。

## 功能描述

查询服务器公网 IP 配置信息，包括：
- 公网 IP 地址（含 IPv6）
- 内网 IP 映射
- 机房节点
- 带宽规格和类型（独享/共享）
- 计费方式（按带宽/按流量）
- 端口映射

## 触发条件

**关键词**：公网IP、外网IP、带宽、出口IP、网络类型、公网IP列表

**排他条件**：
- 查服务器配置详情（CPU/内存/状态）→ 使用 `cmdb-server-query`
- 查部署记录 → 使用 `project-deployment-query`
- 查产品信息 → 使用 `product-query`
- 查项目代码 → 使用 `project-basis-query`

## 输入参数

| 参数名 | 类型 | 说明 | 默认值 | 来源 |
|--------|------|------|--------|------|
| publicIp | string | 公网 IP（精确匹配） | - | 用户输入 |
| ip | string | 内网 IP | - | 用户输入 |
| node | string | 机房节点 | - | param_mappings.json → node_mapping |
| currentPage | integer | 页码 | 1 | 自动 |
| pageSize | integer | 每页条数 | 40 | 数量词映射 |

## 工具调用 Schema

```json
{
  "name": "server_public_ip_query",
  "description": "查询服务器公网 IP、带宽、网络类型、计费方式等信息",
  "parameters": {
    "type": "object",
    "properties": {
      "publicIp": { "type": "string", "description": "公网 IP 地址（精确匹配）" },
      "ip": { "type": "string", "description": "内网 IP 地址" },
      "node": { "type": "string", "description": "机房节点，如 云公司->贵州" },
      "currentPage": { "type": "integer", "description": "页码", "minimum": 1 },
      "pageSize": { "type": "integer", "description": "每页条数", "minimum": 1, "maximum": 100 }
    },
    "required": []
  }
}
```

## API 信息

**端点**：`POST https://oss.tech.ctseelink.cn/a/cmdb/serverPublicIp/`
**来源**：`config/api_endpoints.json` → `server-public-ip-query`

## 响应字段

### records 中的字段

| 字段 | 类型 | 说明 | 格式化 |
|------|------|------|--------|
| publicIp | string | 公网 IPv4 | - |
| publicIpv6 | string | 公网 IPv6 | 空值显示 `-` |
| ip | string | 内网 IP | - |
| vip | string | 虚拟 IP | 空值显示 `-` |
| node | string | 机房节点 | - |
| privatePort | string | 内网端口 | - |
| publicPort | string | 公网端口 | - |
| sharedBandwidthId | string | 共享带宽 ID | - |
| bandwidth | string | 带宽值 | `{N}Mbps` |
| bandwidthType | string | 带宽类型 | 独享/共享 |
| billingType | string | 计费方式 | 按带宽/按流量计费 |

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
| 公网IP | 内网IP | 机房 | 带宽 | 带宽类型 | 计费方式 |
|--------|--------|------|------|---------|---------|
```

### 详细输出

增加以下字段：IPv6地址、内网端口、公网端口、共享带宽ID

### 降级输出

当 API 失败时，从 `references/mock_responses.json` → `server-public-ip-query` 获取 Mock 数据。

## 示例

**输入**："查贵州机房的公网IP"

**工具调用**：
```json
{
  "tool_name": "server_public_ip_query",
  "parameters": {
    "node": "云公司->贵州",
    "currentPage": 1,
    "pageSize": 40
  }
}
```

**用户输入**："查 192.168.7.101 的公网IP"

**工具调用**：
```json
{
  "tool_name": "server_public_ip_query",
  "parameters": {
    "ip": "192.168.7.101"
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
| `config/param_mappings.json` | ✅ node_mapping |
| `config/api_endpoints.json` | ✅ API 端点配置 |
| `config/field_mappings.json` | ✅ ⚠️ 本 API 分页字段为 current/size |

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 3.0 | 2026-06-24 | 抽离共享内容，标注分页字段差异 |
| 2.0 | 2026-06-18 | 统一字段为英文 key |
| 1.0 | 2026-05-20 | 初始版本 |
