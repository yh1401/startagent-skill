---
name: cmdb-server-query
description: 查询 CMDB 服务器信息，包括主机名、IP、机房、配置、状态等。支持按机房、状态、类型、产品、项目等多维度筛选。
version: 3.0.0
author: Skill Agent Team
---

# CMDB 服务器查询技能

> ⚠️ **v3.0 说明**：通用参数映射、输出模板、错误处理已抽离到共享文件，详见下方链接。

## 功能描述

查询服务器主机信息，包括：
- 基础信息：主机名、内网IP、公网IP、VIP
- 机房信息：节点、机架、带宽
- 配置信息：CPU、内存、操作系统、服务器类型
- 业务关联：所属产品、关联项目
- 运维信息：运维负责人、资产编号

## 触发条件

**关键词**：服务器、主机、机器、设备、IP配置、CPU内存、操作系统

**排他条件**：
- 查公网IP → 使用 `server-public-ip-query`
- 查部署记录 → 使用 `project-deployment-query`
- 查产品信息 → 使用 `product-query`
- 查项目代码 → 使用 `project-basis-query`

## 输入参数

| 参数名 | 类型 | 说明 | 默认值 | 来源 |
|--------|------|------|--------|------|
| hostName | string | 主机名（模糊匹配） | - | 用户输入 |
| ip | string | 内网 IP | - | 用户输入 |
| node | string | 机房节点 | - | param_mappings.json → node_mapping |
| state | string | 服务器状态 | - | param_mappings.json → state_mapping |
| serverType | string | 服务器类型 | - | param_mappings.json → type_mapping |
| belong | integer | 归属 | - | param_mappings.json → belong_mapping |
| xc | string | 信创标识 | - | param_mappings.json → xc_mapping |
| productName | string | 产品名称 | - | 用户输入 |
| projectName | string | 项目名称 | - | 用户输入 |
| currentPage | integer | 页码 | 1 | 自动 |
| pageSize | integer | 每页条数 | 15 | 数量词映射 |

## 工具调用 Schema

```json
{
  "name": "cmdb_server_query",
  "description": "查询 CMDB 服务器信息，包括主机名、IP、机房、配置、状态等",
  "parameters": {
    "type": "object",
    "properties": {
      "hostName": { "type": "string", "description": "主机名（模糊匹配）" },
      "ip": { "type": "string", "description": "内网 IP 地址" },
      "node": { "type": "string", "description": "机房节点，如 云公司->贵州" },
      "state": { "type": "string", "description": "服务器状态：0=在线, 1=库存, 2=计划上线, 3=维修中, 4=已报废" },
      "serverType": { "type": "string", "description": "服务器类型：0=物理机, 1=虚拟机, 2=云服务器" },
      "belong": { "type": "integer", "description": "归属：1=云网, 2=视联" },
      "xc": { "type": "string", "description": "信创标识：1=信创, 0=非信创" },
      "productName": { "type": "string", "description": "产品名称（模糊匹配）" },
      "projectName": { "type": "string", "description": "项目名称（模糊匹配）" },
      "currentPage": { "type": "integer", "description": "页码", "minimum": 1 },
      "pageSize": { "type": "integer", "description": "每页条数", "minimum": 1, "maximum": 100 }
    },
    "required": []
  }
}
```

## API 信息

**端点**：`POST https://oss.tech.ctseelink.cn/api/v2/cmdbServer/getCmdbServerPageList`
**来源**：`config/api_endpoints.json` → `cmdb-server-query`

## 响应字段

### records 中的字段

| 字段 | 类型 | 说明 | 格式化 |
|------|------|------|--------|
| id | string | 服务器 ID | - |
| hostName | string | 主机名 | - |
| ip | string | 内网 IP | - |
| publicIp | string | 公网 IP | - |
| vip | string | 虚拟 IP | 空值显示 `-` |
| node | string | 机房节点 | - |
| state | string | 状态代码 | 🟢🟡🔧⚫ 状态图标 |
| serverType | string | 服务器类型 | 物理机/虚拟机/云服务器 |
| cpuCores | string | CPU 核数 | `{N}核` |
| memory | string | 内存（GB） | `{N}GB` |
| os | string | 操作系统 | - |
| environment | string | 环境 | 测试/灰度/生产 |
| productName | string | 产品名称 | - |
| projectName | string | 项目名称 | - |
| operA | string | 运维负责人A | - |
| operB | string | 运维负责人B | - |
| assetNo | string | 资产编号 | - |
| rack | string | 机架位置 | - |
| bandWidth | string | 带宽 | - |

### 分页字段

| 标准名 | API 字段 |
|--------|---------|
| currentPage | currentPage |
| pageSize | pageSize |
| total | total |

> ⚠️ 响应中 `size` 字段应映射为 `pageSize`

## 输出格式

### 标准输出

使用 `references/output_templates.md` 中的标准模板，标准模式字段：

```
| 主机名 | IP | 机房 | 状态 | 类型 | CPU | 内存 | 产品 |
|--------|-----|------|------|------|-----|------|------|
```

### 详细输出

增加以下字段：公网IP、操作系统、环境、项目、运维人、资产编号、机架、带宽

### 降级输出

当 API 失败时，从 `references/mock_responses.json` → `cmdb-server-query` 获取 Mock 数据，顶部标注 ⚠️。

## 示例

**输入**："查询贵州机房的在线物理机"

**工具调用**：
```json
{
  "tool_name": "cmdb_server_query",
  "parameters": {
    "node": "云公司->贵州",
    "state": "0",
    "serverType": "0",
    "currentPage": 1,
    "pageSize": 15
  }
}
```

---

## 共享文件引用

| 文件 | 用途 |
|------|------|
| `references/output_templates.md` | ✅ 标准/详细/降级输出模板 |
| `references/error_scenarios.md` | ✅ 错误场景处理（场景1-6） |
| `references/mock_responses.json` | ✅ Mock 数据源 |
| `references/param_guides.md` | ✅ 通用参数映射参考 |
| `config/param_mappings.json` | ✅ node/state/type/belong/xc 映射值 |
| `config/api_endpoints.json` | ✅ API 端点配置 |
| `config/field_mappings.json` | ✅ 响应字段标准化 |

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 3.0 | 2026-06-24 | 抽离共享内容，精简为本文件 |
| 2.0 | 2026-06-18 | 统一字段为英文 key |
| 1.0 | 2026-05-20 | 初始版本 |
