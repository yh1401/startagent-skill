# ops-data-query MCP 服务器

企业 CMDB 运维数据综合查询 MCP 服务器，提供标准化的工具调用接口。

## 架构说明

```
┌─────────────────────────────────────────────────────────────────┐
│                      StartAgent 平台                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ MCP 工具调用
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              ops-data-query MCP 服务器 (独立部署)                │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   MCP 协议层                             │  │
│  │   • cmdb_server_query           • server_public_ip_query │  │
│  │   • project_deployment_query    • product_query          │  │
│  │   • project_basis_query                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   CMDBAPIClient                          │  │
│  │   • 连接池管理  • 超时控制  • 自动降级                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │  CMDB API    │  公网IP API  │  部署记录API │  产品信息API │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Mock 数据降级 (mock_responses.json)               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 特性

- ✅ **双模式支持**：MCP 协议（Python 3.10+）和 HTTP API（Python 3.9+）
- ✅ **自动降级**：API 请求失败时自动使用 Mock 数据
- ✅ **连接复用**：使用 requests.Session 保持长连接
- ✅ **超时控制**：30秒超时保护
- ✅ **标准 Schema**：自动生成工具描述和参数定义
- ✅ **Swagger 文档**：HTTP 模式提供交互式 API 文档

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务器

```bash
# 方式一：使用启动脚本（自动检测模式）
./start.sh

# 方式二：指定模式启动
./start.sh http        # HTTP 模式
./start.sh mcp         # MCP 模式

# 方式三：直接启动 Python 脚本
python3 scripts/mcp_server.py --transport http --port 8000
python3 scripts/mcp_server.py --transport mcp
```

### 3. 访问文档

**HTTP 模式**：
- API 文档：http://localhost:8000/docs
- 服务信息：http://localhost:8000/

## 工具列表

| 工具名 | 说明 | 参数示例 |
|--------|------|---------|
| `cmdb_server_query` | 查询 CMDB 服务器信息 | `ip`, `hostName`, `node`, `state` |
| `server_public_ip_query` | 查询服务器公网 IP | `ip`, `hostName`, `node` |
| `project_deployment_query` | 查询项目部署记录 | `projectName`, `environment`, `deploymentStatus` |
| `product_query` | 查询产品信息 | `productName`, `department` |
| `project_basis_query` | 查询项目基础信息 | `projectName`, `productName`, `projectType` |

## StartAgent 平台配置

### MCP 模式配置（推荐 Python 3.10+）

在 StartAgent 平台添加 MCP 连接：

```json
{
  "name": "ops-data-query",
  "type": "mcp",
  "command": "python3 /path/to/mcp-server/scripts/mcp_server.py --transport mcp",
  "description": "企业 CMDB 运维数据综合查询"
}
```

### HTTP 模式配置（Python 3.9+ 兼容）

#### 1. 启动 HTTP 服务器

```bash
# 后台运行
nohup python3 scripts/mcp_server.py --transport http --port 8000 > server.log 2>&1 &

# 或使用 systemd/docker 部署
```

#### 2. 在 StartAgent 平台添加自定义工具

```json
{
  "name": "cmdb_server_query",
  "type": "http",
  "method": "POST",
  "url": "http://localhost:8000/api/cmdb-server-query",
  "description": "查询 CMDB 服务器信息",
  "parameters": {
    "type": "object",
    "properties": {
      "ip": {"type": "string"},
      "hostName": {"type": "string"},
      "node": {"type": "string"},
      "currentPage": {"type": "integer", "default": 1},
      "pageSize": {"type": "integer", "default": 15}
    }
  }
}
```

## API 调用示例

### HTTP 模式

```bash
# 查询服务器信息
curl -X POST http://localhost:8000/api/cmdb-server-query \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.7.101",
    "currentPage": 1,
    "pageSize": 10
  }'

# 查询公网 IP
curl -X POST http://localhost:8000/api/server-public-ip-query \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.7.101"}'

# 查询部署记录
curl -X POST http://localhost:8000/api/project-deployment-query \
  -H "Content-Type: application/json" \
  -d '{"projectName": "guizh-rules-api"}'
```

### MCP 模式

```python
# 客户端调用示例
from mcp import Client

client = Client()
result = client.call_tool("cmdb_server_query", {
    "ip": "192.168.7.101",
    "currentPage": 1,
    "pageSize": 10
})
print(result)
```

## 测试

### 单元测试

```bash
python3 -m pytest tests/
```

### 集成测试

```bash
# 启动服务器
python3 scripts/mcp_server.py --transport http --port 8000 &

# 运行测试脚本
python3 tests/test_api.py

# 清理
pkill -f "mcp_server.py"
```

## 部署

### Docker 部署

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python3", "scripts/mcp_server.py", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
```

### Systemd 部署

创建 `/etc/systemd/system/ops-data-query-mcp.service`:

```ini
[Unit]
Description=ops-data-query MCP Server
After=network.target

[Service]
Type=simple
User=appuser
WorkingDirectory=/opt/ops-data-query-mcp
ExecStart=/usr/bin/python3 /opt/ops-data-query-mcp/scripts/mcp_server.py --transport http --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable ops-data-query-mcp
sudo systemctl start ops-data-query-mcp
```

## 配置文件

- `config/api_endpoints.json` - API 端点配置
- `mock_responses.json` - Mock 数据文件

## 目录结构

```
mcp-server/
├── config/
│   └── api_endpoints.json       # API 端点配置
├── references/
│   └── mock_responses.json      # Mock 数据
├── scripts/
│   └── mcp_server.py           # 主服务器代码
├── requirements.txt             # Python 依赖
├── start.sh                     # 启动脚本
└── README.md                    # 本文档
```

## 故障排查

### 依赖安装失败

```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 端口被占用

```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>

# 或更换端口
python3 scripts/mcp_server.py --port 8080
```

### API 请求失败

服务器会自动降级到 Mock 数据，检查日志可查看详细信息：

```bash
tail -f server.log
```

## 许可证

MIT License