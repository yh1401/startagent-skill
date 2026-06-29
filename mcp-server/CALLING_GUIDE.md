# ops-data-query MCP 服务器 - 调用方案

## 概述

MCP (Model Context Protocol) 服务器已独立部署，提供企业 CMDB 运维数据的标准化查询接口。StartAgent 平台通过 MCP 协议调用该服务器，无需在 skill 内部实现逻辑。

## 架构对比

### 原有架构（不推荐）

```
┌─────────────────────────────────────────────────────────────────┐
│                      StartAgent 平台                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Skill 调用
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  ops-data-query Skill                                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  动态生成脚本 (scripts/cmdb-server-query.py)              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  CMDB API 直接请求                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**问题**：
- 每次调用都需要动态生成脚本，效率低
- 无法复用连接和会话
- 错误处理分散在各个 skill 中
- 难以统一管理和监控

### 新架构（推荐）

```
┌─────────────────────────────────────────────────────────────────┐
│                      StartAgent 平台                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Tool Call
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              ops-data-query MCP 服务器 (独立部署)                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  MCP 协议层（工具注册 & 参数定义）                        │  │
│  │    • cmdb_server_query                                    │  │
│  │    • server_public_ip_query                               │  │
│  │    • project_deployment_query                            │  │
│  │    • product_query                                        │  │
│  │    • project_basis_query                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  CMDBAPIClient（统一请求处理）                            │  │
│  │    • 连接池管理  • 超时控制  • 自动降级                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                    │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │  CMDB API    │  公网IP API  │  部署记录API │  产品信息API │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                              │                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Mock 数据降级 (references/mock_responses.json)           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**优势**：
- ✅ 标准化协议，易于集成
- ✅ 连接复用，性能提升
- ✅ 统一错误处理和降级
- ✅ 独立部署，易于扩展和监控
- ✅ 支持 MCP 和 HTTP 双模式

## MCP 服务器部署

### 1. 目录结构

```
mcp-server/
├── config/
│   ├── api_endpoints.json      # API 端点配置
│   ├── field_mappings.json     # 字段映射
│   └── param_mappings.json     # 参数映射
├── references/
│   └── mock_responses.json     # Mock 数据
├── scripts/
│   ├── mcp_server.py          # 主服务器代码（双模式）
│   └── test_client.py         # 测试客户端
├── requirements.txt            # Python 依赖
├── start.sh                    # 启动脚本
└── README.md                   # 文档
```

### 2. 安装依赖

```bash
cd /path/to/mcp-server
pip install -r requirements.txt
```

### 3. 配置 API 端点

编辑 `config/api_endpoints.json`：

```json
{
  "base_url": "https://oss.tech.ctseelink.cn",
  "endpoints": {
    "cmdb-server-query": {
      "method": "POST",
      "full_url": "https://oss.tech.ctseelink.cn/cmdb-server-query"
    }
  }
}
```

**Mock 模式**（测试/开发环境）：设置 `full_url` 为空字符串，自动返回 Mock 数据

**生产模式**：配置完整的 API URL

### 4. 启动服务器

```bash
# HTTP 模式（推荐用于 Python 3.9+）
./start.sh http

# 或指定端口
./start.sh http 0.0.0.0 8000

# 后台运行
nohup ./start.sh http > server.log 2>&1 &
```

服务器启动后访问：
- API 文档：http://localhost:8000/docs
- 服务信息：http://localhost:8000/

## StartAgent 平台配置

### 方案一：HTTP 模式（推荐）

#### 1. 部署 MCP 服务器

在生产服务器或 Docker 容器中部署 MCP 服务器：

```bash
# 启动服务器
./start.sh http 0.0.0.0 8000
```

#### 2. 在 StartAgent 添加自定义工具

在平台的「工具管理」中添加 HTTP 工具：

**工具：cmdb_server_query**
```json
{
  "name": "cmdb_server_query",
  "type": "http",
  "method": "POST",
  "url": "http://mcp-server-host:8000/api/cmdb-server-query",
  "description": "查询 CMDB 服务器信息",
  "parameters": {
    "type": "object",
    "properties": {
      "ip": {
        "type": "string",
        "description": "内网 IP 地址"
      },
      "hostName": {
        "type": "string",
        "description": "主机名（模糊匹配）"
      },
      "node": {
        "type": "string",
        "description": "机房节点，如 云公司->贵州"
      },
      "state": {
        "type": "string",
        "description": "服务器状态：0=在线, 1=库存, 2=计划上线, 3=维修中, 4=已报废"
      },
      "currentPage": {
        "type": "integer",
        "default": 1
      },
      "pageSize": {
        "type": "integer",
        "default": 15
      }
    }
  }
}
```

**工具：server_public_ip_query**
```json
{
  "name": "server_public_ip_query",
  "type": "http",
  "method": "POST",
  "url": "http://mcp-server-host:8000/api/server-public-ip-query",
  "description": "查询服务器公网 IP 信息",
  "parameters": {
    "type": "object",
    "properties": {
      "ip": {"type": "string"},
      "hostName": {"type": "string"},
      "currentPage": {"type": "integer", "default": 1},
      "pageSize": {"type": "integer", "default": 40}
    }
  }
}
```

**其他工具**：按照相同方式添加 `project_deployment_query`、`product_query`、`project_basis_query`

### 方案二：MCP 模式（需要 Python 3.10+）

#### 1. 安装 MCP 依赖

```bash
pip install 'mcp[cli]>=1.2.0'
```

#### 2. 在 StartAgent 添加 MCP 连接

```json
{
  "name": "ops-data-query",
  "type": "mcp",
  "command": "python3 /path/to/mcp-server/scripts/mcp_server.py --transport mcp",
  "description": "企业 CMDB 运维数据综合查询"
}
```

StartAgent 平台会自动发现注册的工具。

## 调用示例

### 1. HTTP 模式调用

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
```

### 2. Python 客户端调用

```python
import requests

# 查询服务器
resp = requests.post(
    "http://localhost:8000/api/cmdb-server-query",
    json={"ip": "192.168.7.101"}
)
data = resp.json()

# 处理返回数据
if data.get("code") == 200:
    records = data["data"]["records"]
    for record in records:
        print(f"{record['hostName']} - {record['ip']}")
```

### 3. StartAgent Skill 调用

在 skill 的 Python 脚本中调用：

```python
import requests

def query_cmdb_servers(ip: str):
    """调用 MCP 服务器查询 CMDB 信息"""
    url = "http://mcp-server:8000/api/cmdb-server-query"
    resp = requests.post(url, json={"ip": ip})
    return resp.json()
```

## 测试

### 1. 运行测试客户端

```bash
# 启动服务器
./start.sh http &

# 运行测试
python3 scripts/test_client.py http://localhost:8000
```

预期输出：
```
============================================================
  MCP 服务器测试客户端
  服务器地址: http://localhost:8000
============================================================
📋 测试服务器信息接口...
✅ 服务名称: ops-data-query-mcp
✅ 版本: 1.0.0

📋 测试 CMDB 服务器查询...
✅ 查询成功，返回 4 条记录

...（其他测试）

============================================================
🎉 所有测试通过！
```

### 2. 手动测试 API

```bash
# 测试服务信息
curl http://localhost:8000/

# 测试 API 端点
curl -X POST http://localhost:8000/api/cmdb-server-query \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.7.101"}'
```

## 生产部署

### Docker 部署

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python3", "scripts/mcp_server.py", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
```

构建和运行：
```bash
docker build -t ops-data-query-mcp .
docker run -d -p 8000:8000 ops-data-query-mcp
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
StandardOutput=append:/var/log/ops-data-query-mcp.log
StandardError=append:/var/log/ops-data-query-mcp-error.log

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable ops-data-query-mcp
sudo systemctl start ops-data-query-mcp
```

## 监控和日志

### 日志位置

- HTTP 模式：`server.log`（使用重定向）
- Systemd：`/var/log/ops-data-query-mcp.log`

### 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/

# 检查进程
ps aux | grep mcp_server
```

## 故障排查

### 1. 依赖安装失败

```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 端口被占用

```bash
# 查找占用进程
lsof -i :8000

# 杀死进程
kill -9 <PID>
```

### 3. API 请求超时

检查 `config/api_endpoints.json` 配置，生产环境确保 `full_url` 正确配置。

### 4. Mock 数据未加载

确保 `references/mock_responses.json` 存在，并且 JSON 格式正确。

## 版本信息

- MCP 服务器版本：1.0.0
- Python 要求：3.9+（HTTP 模式），3.10+（MCP 模式）
- 支持的传输协议：HTTP、MCP (stdio)

## 联系方式

如有问题，请联系技术支持团队。