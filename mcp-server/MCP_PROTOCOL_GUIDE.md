# MCP 协议调用原理与架构详解

## 一、什么是 MCP (Model Context Protocol)

MCP (Model Context Protocol) 是一个开放协议，用于标准化应用程序如何为 LLM 提供上下文。它定义了 AI 模型与应用程序之间交互的标准格式，就像 AI 应用的 "USB-C" 接口。

### MCP 的核心概念

```
┌─────────────────────────────────────────────────────────────────┐
│                          LLM / AI 模型                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 需要访问外部工具/数据
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        StartAgent 平台                           │
│                     (MCP 客户端实现)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ MCP 协议通信
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        MCP 服务器                                │
│                     (提供工具和资源)                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Tools (工具) - 可调用的功能                              │  │
│  │    • cmdb_server_query                                    │  │
│  │    • server_public_ip_query                               │  │
│  │    • project_deployment_query                            │  │
│  │    • product_query                                        │  │
│  │    • project_basis_query                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Resources (资源) - 可访问的数据                          │  │
│  │    • config/api_endpoints.json                            │  │
│  │    • references/mock_responses.json                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 实际数据访问
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        外部系统                                  │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│    │ CMDB API │  │ 公网IP   │  │ 部署记录  │  │ 产品信息  │     │
│    └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## 二、MCP 通信模式

### 1. stdio 模式（标准输入输出）

这是 MCP 的经典模式，通过进程的标准输入输出进行通信。

**通信流程**：

```
StartAgent 平台                  MCP 服务器进程
      │                               │
      │  启动进程                      │
      ├─────────────────────────────>│
      │   python3 mcp_server.py      │
      │                               │
      │  初始化握手 (JSON-RPC)         │
      ├─────────────────────────────>│  initialize
      │<─────────────────────────────┤  initialized
      │                               │
      │  获取工具列表                  │
      ├─────────────────────────────>│  tools/list
      │<─────────────────────────────┤  返回工具定义
      │  [cmdb_server_query, ...]     │
      │                               │
      │  Skill 调用工具                │
      ├─────────────────────────────>│  tools/call
      │  {"name": "cmdb_server_       │
      │   query", "arguments": {...}} │
      │                               │
      │  处理请求（调用 API 或 Mock）  │
      │  （内部处理）                  │
      │                               │
      │<─────────────────────────────┤  返回结果
      │  {"result": {...}}            │
      │                               │
      │  传递给 Skill                  │
```

**协议格式（JSON-RPC 2.0）**：

```json
// 请求
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}

// 响应
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "cmdb_server_query",
        "description": "查询 CMDB 服务器信息",
        "inputSchema": {
          "type": "object",
          "properties": {
            "ip": {"type": "string"},
            "currentPage": {"type": "integer", "default": 1}
          }
        }
      }
    ]
  }
}
```

**优点**：
- ✅ 无需网络端口，安全性高
- ✅ 简单可靠，不需要 HTTP 服务器
- ✅ 适合本地开发环境

**缺点**：
- ❌ 进程必须保持运行
- ❌ 无法远程访问

### 2. SSE (Server-Sent Events) 模式

通过 HTTP/HTTPS 进行通信，支持远程访问。

**通信流程**：

```
StartAgent 平台                  MCP 服务器
      │                               │
      │  HTTP 连接                     │
      ├─────────────────────────────>│  GET /sse
      │<─────────────────────────────┤  SSE 连接建立
      │                               │
      │  获取工具列表                  │
      ├─────────────────────────────>│  tools/list (POST)
      │<─────────────────────────────┤  返回工具定义
      │                               │
      │  Skill 调用工具                │
      ├─────────────────────────────>│  tools/call (POST)
      │<─────────────────────────────┤  返回结果
      │                               │
```

**优点**：
- ✅ 支持远程访问
- ✅ 可以跨机器部署
- ✅ 支持多个客户端连接

**缺点**：
- ❌ 需要网络端口
- ❌ 需要 HTTP 服务器

## 三、在 StartAgent 平台上的完整调用流程

### 架构示意图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          StartAgent 平台                                    │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    MCP 连接管理器                                      │  │
│  │                                                                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐   │  │
│  │  │         ops-data-query MCP 服务器                               │   │  │
│  │  │         (连接配置: stdio 或 SSE)                                 │   │  │
│  │  │                                                                 │   │  │
│  │  │  已注册工具:                                                     │   │  │
│  │  │  • cmdb_server_query                                            │   │  │
│  │  │  • server_public_ip_query                                       │   │  │
│  │  │  • project_deployment_query                                    │   │  │
│  │  │  • product_query                                                │   │  │
│  │  │  • project_basis_query                                         │   │  │
│  │  └────────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                 │                                            │
│                                 │ 工具发现                                    │
│                                 ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      Skill 执行引擎                                   │  │
│  │                                                                        │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │  │
│  │  │  Skill A     │  │  Skill B     │  │  Skill C     │                │  │
│  │  │              │  │              │  │              │                │  │
│  │  │ 需要查询     │  │ 需要查询     │  │ 需要查询     │                │  │
│  │  │ 服务器信息   │  │ 公网IP       │  │ 部署记录     │                │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                │  │
│  │         │                 │                 │                        │  │
│  │         └─────────────────┼─────────────────┘                        │  │
│  │                           │                                          │  │
│  │                           ▼                                          │  │
│  │                 ┌─────────────────┐                                  │  │
│  │                 │  MCP 工具调用   │                                  │  │
│  │                 │  协议层         │                                  │  │
│  │                 └────────┬────────┘                                  │  │
│  └───────────────────────────────────┼──────────────────────────────────┘  │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │
                                       │ MCP 协议 (stdio/SSE)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   ops-data-query MCP 服务器 (独立进程)                     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     MCP 协议处理器                                    │   │
│  │  • 解析 JSON-RPC 请求                                                │   │
│  │  • 路由到对应的工具函数                                              │   │
│  │  • 序列化响应结果                                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                 │                                          │
│                                 ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     CMDBAPIClient                                     │   │
│  │  • 连接池管理                                                         │   │
│  │  • 超时控制                                                           │   │
│  │  • 自动降级到 Mock                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                 │                                          │
│                                 ▼                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  CMDB API    │  │  公网IP API  │  │  部署记录API │  │  产品信息API │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 详细调用步骤

#### 步骤 1：在 StartAgent 平台注册 MCP 服务器

在平台的「MCP 连接管理」中添加连接：

**配置示例（stdio 模式）**：
```json
{
  "name": "ops-data-query",
  "type": "mcp",
  "transport": "stdio",
  "command": "python3 /path/to/mcp-server/scripts/mcp_server.py --transport mcp",
  "description": "企业 CMDB 运维数据综合查询",
  "enabled": true
}
```

**配置示例（SSE 模式）**：
```json
{
  "name": "ops-data-query",
  "type": "mcp",
  "transport": "sse",
  "url": "http://mcp-server-host:8000/sse",
  "description": "企业 CMDB 运维数据综合查询",
  "enabled": true
}
```

#### 步骤 2：StartAgent 启动并初始化 MCP 连接

```python
# StartAgent 平台内部伪代码
mcp_client = MCPClient(config)

# 1. 启动 MCP 服务器进程（stdio 模式）或建立连接（SSE 模式）
mcp_client.connect()

# 2. 初始化握手
mcp_client.initialize()

# 3. 获取工具列表
tools = mcp_client.list_tools()
# 返回：
# [
#   {
#     "name": "cmdb_server_query",
#     "description": "查询 CMDB 服务器信息",
#     "inputSchema": {...}
#   },
#   ...
# ]

# 4. 注册工具到平台的工具注册表
tool_registry.register("ops-data-query", tools)
```

#### 步骤 3：Skill 需要调用工具

假设有一个 Skill 需要查询服务器信息：

```python
# Skill 代码 (在 StartAgent 平台执行)
def get_server_details(ip_address):
    """
    获取服务器详细信息
    """
    # 通过 StartAgent 平台的工具调用接口
    # 平台会自动路由到对应的 MCP 工具
    
    result = platform.call_tool(
        mcp_server="ops-data-query",
        tool_name="cmdb_server_query",
        arguments={
            "ip": ip_address,
            "currentPage": 1,
            "pageSize": 10
        }
    )
    
    # 返回的数据
    if result.get("code") == 200:
        return result["data"]["records"]
    else:
        return []
```

#### 步骤 4：StartAgent 平台通过 MCP 协议调用

```python
# StartAgent 平台内部处理流程

def call_tool(mcp_server, tool_name, arguments):
    # 1. 查找对应的 MCP 连接
    mcp_client = get_mcp_client(mcp_server)
    
    # 2. 通过 MCP 协议发送工具调用请求
    response = mcp_client.call_tool(tool_name, arguments)
    
    # 实际发送的 JSON-RPC 请求：
    # {
    #   "jsonrpc": "2.0",
    #   "id": 123,
    #   "method": "tools/call",
    #   "params": {
    #     "name": "cmdb_server_query",
    #     "arguments": {
    #       "ip": "192.168.7.101",
    #       "currentPage": 1,
    #       "pageSize": 10
    #     }
    #   }
    # }
    
    return response
```

#### 步骤 5：MCP 服务器处理请求

```python
# mcp_server.py 内部处理

@mcp.tool
def cmdb_server_query(**params):
    # 收到的参数: params = {"ip": "192.168.7.101", ...}
    
    # 调用 CMDBAPIClient
    result = client.query_server(**params)
    
    # 返回 JSON 字符串
    return json.dumps(result, ensure_ascii=False)
```

#### 步骤 6：结果返回到 Skill

```
MCP 服务器                    StartAgent 平台                  Skill
     │                              │                            │
     │  返回结果                     │                            │
     ├─────────────────────────────>│                            │
     │  {                           │                            │
     │    "jsonrpc": "2.0",         │                            │
     │    "id": 123,                │                            │
     │    "result": "{\"code\":200  │                            │
     │      ,\"message\":\"success\" │                            │
     │      ,\"data\":{...}}"        │                            │
     │  }                           │                            │
     │                              │                            │
     │                              │  解析并返回给 Skill        │
     │                              ├───────────────────────────>│
     │                              │  {                          │
     │                              │    "code": 200,            │
     │                              │    "message": "success",   │
     │                              │    "data": {               │
     │                              │      "records": [...]      │
     │                              │    }                       │
     │                              │  }                          │
     │                              │                            │
     │                              │  处理数据                  │
     │                              │  [Skill 继续执行...]       │
```

## 四、为什么需要 MCP 协议？

### 传统方式的缺点

```
❌ 传统方式：Skill 直接调用 HTTP API

┌─────────────────┐      HTTP      ┌─────────────────┐
│   StartAgent    │ ─────────────> │  外部 API 服务  │
│                 │               │                 │
│  ┌───────────┐  │               │  ┌───────────┐  │
│  │  Skill A  │  │               │  │  API A    │  │
│  │  Skill B  │  │               │  │  API B    │  │
│  │  Skill C  │  │               │  │  API C    │  │
│  └───────────┘  │               │  └───────────┘  │
└─────────────────┘               └─────────────────┘

问题：
• Skill 需要知道 API 的 URL、认证方式、参数格式
• 每个重复实现 HTTP 调用逻辑
• 错误处理、超时控制分散在各个 Skill
• 无法统一监控和审计
```

### MCP 方式的优势

```
✅ MCP 方式：通过标准协议调用

┌─────────────────────────────────────────────────────────────────┐
│                    StartAgent 平台                               │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Skill A     │  │  Skill B     │  │  Skill C     │          │
│  │  (无需关心   │  │  (无需关心   │  │  (无需关心   │          │
│  │   API 细节) │  │   API 细节) │  │   API 细节) │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                  │
│         └─────────────────┼─────────────────┘                  │
│                           │                                    │
│                           ▼                                    │
│              ┌─────────────────────┐                          │
│              │   MCP 客户端层      │                          │
│              │   • 统一调用接口    │                          │
│              │   • 自动发现工具    │                          │
│              │   • 统一错误处理    │                          │
│              └─────────┬───────────┘                          │
└────────────────────────────┼────────────────────────────────────┘
                             │ MCP 协议
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MCP 服务器 (独立部署)                         │
│                                                                 │
│  • 统一管理 API 调用                                            │
│  • 连接池、超时、降级                                            │
│  • 工具自动注册和 Schema 定义                                    │
└─────────────────────────────────────────────────────────────────┘

优势：
• Skill 只需关注业务逻辑，调用 "cmdb_server_query" 即可
• API 细节由 MCP 服务器统一管理
• 连接复用、错误处理集中化
• 工具自动发现，无需手动配置
• 支持多种传输模式（stdio/SSE）
```

## 五、实际配置示例

### 方式 1：stdio 模式（本地部署）

```bash
# 1. 部署 MCP 服务器代码到服务器
scp -r mcp-server/ user@server:/opt/mcp-server/

# 2. 在 StartAgent 平台配置连接
```

平台配置：
```json
{
  "name": "ops-data-query",
  "type": "mcp",
  "transport": "stdio",
  "command": "python3 /opt/mcp-server/scripts/mcp_server.py --transport mcp",
  "env": {
    "PYTHONPATH": "/opt/mcp-server"
  },
  "description": "企业 CMDB 运维数据综合查询"
}
```

### 方式 2：SSE 模式（远程部署）

```bash
# 1. 启动 MCP 服务器（带 SSE 支持）
cd /opt/mcp-server
nohup python3 scripts/mcp_server.py --transport sse --port 8000 > server.log 2>&1 &

# 2. 在 StartAgent 平台配置连接
```

平台配置：
```json
{
  "name": "ops-data-query",
  "type": "mcp",
  "transport": "sse",
  "url": "http://mcp-server-host:8000/sse",
  "description": "企业 CMDB 运维数据综合查询",
  "headers": {
    "Authorization": "Bearer YOUR_TOKEN"
  }
}
```

## 六、对比总结

| 特性 | 传统 HTTP API | MCP 协议 |
|------|-------------|---------|
| **Skill 代码复杂度** | 需要实现 HTTP 调用 | 只需调用工具名 |
| **工具发现** | 手动配置 | 自动发现 |
| **参数验证** | 需要自己实现 | Schema 自动验证 |
| **连接管理** | 每次调用新建连接 | 连接复用 |
| **错误处理** | 分散在各 Skill | 集中处理 |
| **降级机制** | 需要自己实现 | 服务器统一管理 |
| **监控审计** | 难以统一 | 集中管理 |
| **扩展性** | 改 API 需改所有 Skill | 只需更新 MCP 服务器 |
| **安全性** | API Key 分散 | 统一认证 |

## 七、快速验证

### 测试 MCP 协议通信

```bash
# 1. 启动 MCP 服务器（stdio 模式）
cd /Users/a666/Documents/trae_projects/opencode_skill/mcp-server
python3 scripts/mcp_server.py --transport mcp

# 2. 在另一个终端发送 JSON-RPC 请求（模拟 StartAgent 平台）
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | \
  python3 scripts/mcp_server.py --transport mcp

# 预期返回工具列表
```

### 测试 HTTP 模式

```bash
# 1. 启动 HTTP 模式服务器
./start.sh http

# 2. 测试 API
curl http://localhost:8000/
curl -X POST http://localhost:8000/api/cmdb-server-query \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.7.101"}'
```

## 八、常见问题

### Q1: MCP 服务器和 HTTP 服务器有什么区别？

**MCP 服务器**：
- 使用 MCP 协议（JSON-RPC over stdio/SSE）
- 需要支持 MCP 的客户端（如 StartAgent 平台）
- 工具自动发现，Schema 自动定义
- 适合 AI 平台集成

**HTTP 服务器**：
- 使用标准 HTTP REST API
- 可以被任何 HTTP 客户端调用
- 需要手动定义 API 文档
- 适合传统 Web 应用集成

我们的 `mcp_server.py` 同时支持两种模式！

### Q2: Skill 如何调用 MCP 工具？

Skill 不直接调用 MCP 服务器，而是通过 StartAgent 平台的工具调用接口：

```python
# Skill 代码
def my_skill_function():
    # 通过平台调用，平台会自动路由到对应的 MCP 工具
    result = platform.call_tool(
        mcp_server="ops-data-query",
        tool_name="cmdb_server_query",
        arguments={"ip": "192.168.7.101"}
    )
    return result
```

### Q3: MCP 协议的数据格式是什么？

MCP 协议使用 JSON-RPC 2.0 格式：

```json
// 请求
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "cmdb_server_query",
    "arguments": {"ip": "192.168.7.101"}
  }
}

// 响应
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"code\":200,\"data\":{...}}"
      }
    ]
  }
}
```

## 参考资料

- [MCP 官方文档](https://modelcontextprotocol.io)
- [JSON-RPC 2.0 规范](https://www.jsonrpc.org/specification)
- [FastMCP 文档](https://github.com/jlowin/fastmcp)