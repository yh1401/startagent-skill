#!/usr/bin/env python3
"""
独立的 MCP 服务器 - ops-data-query-mcp
为企业 CMDB 运维数据提供标准化的 MCP 工具调用接口

启动方式：
    python3 scripts/mcp_server.py --port 8000
    或 (MCP 模式)
    python3 scripts/mcp_server.py --transport mcp
    
文档：http://localhost:8000/docs
"""

import json
import os
import sys
import argparse
import logging
from typing import Optional

_script_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_script_dir)
_config_dir = os.path.join(_root_dir, 'config')
_references_dir = os.path.join(_root_dir, 'references')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('ops-data-query-mcp')

try:
    from mcp.server.fastmcp import FastMCP
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    logger.warning("未安装 mcp 模块，将使用 HTTP 模式")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("未安装 requests 模块，将仅使用 Mock 数据")

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

try:
    # 尝试从 scripts/formatters 导入
    if os.path.exists(os.path.join(_script_dir, 'formatters.py')):
        sys.path.insert(0, _script_dir)
        from formatters import format_output
        HAS_FORMATTER = True
        logger.info("加载格式化模块成功")
    else:
        HAS_FORMATTER = False
        logger.warning("格式化模块不存在，将仅返回原始数据")
except ImportError as e:
    HAS_FORMATTER = False
    logger.warning(f"格式化模块加载失败 ({e})，将仅返回原始数据")


class APIConfig:
    """API 配置管理"""
    def __init__(self):
        self.base_url = "https://oss.tech.ctseelink.cn"
        self.endpoints = {}
        self.auth_headers = {}
        self.load_config()
    
    def load_config(self):
        config_path = os.path.join(_config_dir, 'api_endpoints.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.base_url = data.get('base_url', self.base_url)
                self.endpoints = data.get('endpoints', {})
                self.auth_headers = data.get('auth_headers', {})
            logger.info(f"加载 API 配置: base_url={self.base_url}, endpoints={list(self.endpoints.keys())}")
        else:
            logger.warning(f"API 配置文件不存在: {config_path}")


def _normalize_pagination(skill_id: str, result: dict) -> dict:
    """
    统一分页字段格式
    
    部分 API 使用不同的分页字段名：
    - cmdb-server-query, project-deployment-query: currentPage/pageSize/total
    - server-public-ip-query, product-query, project-basis-query: current/size/total
    
    统一对外返回：currentPage/pageSize/total
    """
    data = result.get('data', {})
    
    if skill_id in ['server-public-ip-query', 'product-query', 'project-basis-query']:
        if 'current' in data:
            data['currentPage'] = data.pop('current')
        if 'size' in data:
            data['pageSize'] = data.pop('size')
    
    return result


class CMDBAPIClient:
    """CMDB API 客户端"""
    def __init__(self):
        self.config = APIConfig()
        self._session = None
    
    def _ensure_session(self):
        if HAS_REQUESTS and self._session is None:
            self._session = requests.Session()
            if self.config.auth_headers:
                self._session.headers.update(self.config.auth_headers)
            logger.info("创建 HTTP 会话，认证头已配置")
    
    def _request(self, skill_id: str, params: dict) -> dict:
        """发送 API 请求，失败时返回 Mock 数据"""
        endpoint = self.config.endpoints.get(skill_id, {})
        url = endpoint.get('full_url', '')
        method = endpoint.get('method', 'POST').upper()
        
        if not url:
            logger.warning(f"未找到 {skill_id} 的 API 端点，使用 Mock 数据")
            result = self._get_mock_response(skill_id)
            return _normalize_pagination(skill_id, result)
        
        try:
            if HAS_REQUESTS:
                self._ensure_session()
                logger.debug(f"发送 {method} 请求: {url}, params={params}")
                resp = self._session.request(
                    method, url,
                    json=params,
                    headers=self.config.auth_headers,
                    timeout=30
                )
                resp.raise_for_status()
                result = resp.json()
                logger.debug(f"API 响应成功 ({skill_id}): code={result.get('code')}")
                return _normalize_pagination(skill_id, result)
            else:
                logger.warning("requests 模块未安装，使用 Mock 数据")
                result = self._get_mock_response(skill_id)
                return _normalize_pagination(skill_id, result)
        except requests.exceptions.RequestException as e:
            logger.error(f"API 请求失败 ({skill_id}): {e}")
            result = self._get_mock_response(skill_id)
            return _normalize_pagination(skill_id, result)
        except Exception as e:
            logger.error(f"API 处理异常 ({skill_id}): {e}")
            result = self._get_mock_response(skill_id)
            return _normalize_pagination(skill_id, result)
    
    def _get_mock_response(self, skill_id: str) -> dict:
        """获取 Mock 响应数据"""
        mock_path = os.path.join(_references_dir, 'mock_responses.json')
        if os.path.exists(mock_path):
            with open(mock_path, 'r', encoding='utf-8') as f:
                mock_data = json.load(f)
                result = mock_data.get(skill_id, {"code": 500, "message": "服务不可用", "data": {"records": [], "total": 0}})
                logger.info(f"使用 Mock 数据: {skill_id}, 记录数={result.get('data', {}).get('total', 0)}")
                return result
        logger.error(f"Mock 数据文件不存在: {mock_path}")
        return {"code": 500, "message": "服务不可用", "data": {"records": [], "total": 0}}
    
    def query_server(self, **params) -> dict:
        """查询服务器信息"""
        return self._request('cmdb-server-query', params)
    
    def query_public_ip(self, **params) -> dict:
        """查询公网 IP"""
        return self._request('server-public-ip-query', params)
    
    def query_deployment(self, **params) -> dict:
        """查询部署记录"""
        return self._request('project-deployment-query', params)
    
    def query_product(self, **params) -> dict:
        """查询产品信息"""
        return self._request('product-query', params)
    
    def query_project_basis(self, **params) -> dict:
        """查询项目基础信息"""
        return self._request('project-basis-query', params)


# 全局客户端实例
client = CMDBAPIClient()

# ============================================================================
# MCP 模式
# ============================================================================

if HAS_MCP:
    mcp = FastMCP("ops-data-query-mcp")
    
    @mcp.tool
    def cmdb_server_query(
        hostName: Optional[str] = None,
        ip: Optional[str] = None,
        node: Optional[str] = None,
        state: Optional[str] = None,
        serverType: Optional[str] = None,
        belong: Optional[int] = None,
        xc: Optional[str] = None,
        productName: Optional[str] = None,
        projectName: Optional[str] = None,
        currentPage: int = 1,
        pageSize: int = 15
    ) -> str:
        """
        查询 CMDB 服务器信息，包括主机名、IP、机房、配置、状态等。
        
        Args:
            hostName: 主机名（模糊匹配）
            ip: 内网 IP 地址
            node: 机房节点，如 云公司->贵州
            state: 服务器状态：0=在线, 1=库存, 2=计划上线, 3=维修中, 4=已报废
            serverType: 服务器类型：0=物理机, 1=虚拟机, 2=云服务器
            belong: 归属：1=云网, 2=视联
            xc: 信创标识：1=信创, 0=非信创
            productName: 产品名称（模糊匹配）
            projectName: 项目名称（模糊匹配）
            currentPage: 页码，默认 1
            pageSize: 每页条数，默认 15
        """
        params = {}
        if hostName: params['hostName'] = hostName
        if ip: params['ip'] = ip
        if node: params['node'] = node
        if state: params['state'] = state
        if serverType: params['serverType'] = serverType
        if belong is not None: params['belong'] = belong
        if xc: params['xc'] = xc
        if productName: params['productName'] = productName
        if projectName: params['projectName'] = projectName
        params['currentPage'] = currentPage
        params['pageSize'] = pageSize
        
        result = client.query_server(**params)
        
        if HAS_FORMATTER:
            formatted = format_output('cmdb-server-query', result, f"node={node}, ip={ip}, hostName={hostName}")
            response = {
                "raw_data": result,
                "formatted_text": formatted.get('formatted_text', ''),
                "summary": formatted.get('summary', {})
            }
            return json.dumps(response, ensure_ascii=False, indent=2)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    @mcp.tool
    def server_public_ip_query(
        ip: Optional[str] = None,
        hostName: Optional[str] = None,
        node: Optional[str] = None,
        currentPage: int = 1,
        pageSize: int = 40
    ) -> str:
        """
        查询服务器公网 IP 信息，包括公网IP、带宽、网络类型等。
        
        Args:
            ip: 内网 IP 地址
            hostName: 主机名（模糊匹配）
            node: 机房节点
            currentPage: 页码，默认 1
            pageSize: 每页条数，默认 40
        """
        params = {}
        if ip: params['ip'] = ip
        if hostName: params['hostName'] = hostName
        if node: params['node'] = node
        params['current'] = currentPage
        params['size'] = pageSize
        
        result = client.query_public_ip(**params)
        
        if HAS_FORMATTER:
            formatted = format_output('server-public-ip-query', result, f"node={node}, ip={ip}, hostName={hostName}")
            response = {
                "raw_data": result,
                "formatted_text": formatted.get('formatted_text', ''),
                "summary": formatted.get('summary', {})
            }
            return json.dumps(response, ensure_ascii=False, indent=2)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    @mcp.tool
    def project_deployment_query(
        projectName: Optional[str] = None,
        environment: Optional[int] = None,
        deploymentStatus: Optional[int] = None,
        deployer: Optional[str] = None,
        startTime: Optional[str] = None,
        endTime: Optional[str] = None,
        currentPage: int = 1,
        pageSize: int = 40
    ) -> str:
        """
        查询项目部署记录，包括版本、环境、状态、部署人等。
        
        Args:
            projectName: 项目名称（模糊匹配）
            environment: 环境：1=测试, 2=灰度, 3=生产, 4=研发
            deploymentStatus: 部署状态：0=成功, 1=失败, 2=进行中, 3=待部署
            deployer: 部署人姓名
            startTime: 开始时间，格式 YYYY-MM-DD
            endTime: 结束时间，格式 YYYY-MM-DD
            currentPage: 页码，默认 1
            pageSize: 每页条数，默认 40
        """
        params = {}
        if projectName: params['projectName'] = projectName
        if environment is not None: params['environment'] = environment
        if deploymentStatus is not None: params['statusCode'] = deploymentStatus
        if deployer: params['deployer'] = deployer
        if startTime: params['startTime'] = startTime
        if endTime: params['endTime'] = endTime
        params['currentPage'] = currentPage
        params['pageSize'] = pageSize
        
        result = client.query_deployment(**params)
        
        if HAS_FORMATTER:
            formatted = format_output('project-deployment-query', result, f"projectName={projectName}, environment={environment}")
            response = {
                "raw_data": result,
                "formatted_text": formatted.get('formatted_text', ''),
                "summary": formatted.get('summary', {})
            }
            return json.dumps(response, ensure_ascii=False, indent=2)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    @mcp.tool
    def product_query(
        id: Optional[str] = None,
        name: Optional[str] = None,
        flag: Optional[int] = None,
        department: Optional[str] = None,
        currentPage: int = 1,
        pageSize: int = 40
    ) -> str:
        """
        查询产品信息，包括产品名称、负责人、所属部门等。
        
        Args:
            id: 产品 ID
            name: 产品名称（模糊匹配）
            flag: 启用标志：0=禁用, 1=启用
            department: 所属部门
            currentPage: 页码，默认 1
            pageSize: 每页条数，默认 40
        """
        params = {}
        if id: params['id'] = id
        if name: params['name'] = name
        if flag is not None: params['flag'] = flag
        if department: params['department'] = department
        params['current'] = currentPage
        params['size'] = pageSize
        
        result = client.query_product(**params)
        
        if HAS_FORMATTER:
            formatted = format_output('product-query', result, f"name={name}, department={department}")
            response = {
                "raw_data": result,
                "formatted_text": formatted.get('formatted_text', ''),
                "summary": formatted.get('summary', {})
            }
            return json.dumps(response, ensure_ascii=False, indent=2)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    @mcp.tool
    def project_basis_query(
        id: Optional[str] = None,
        name: Optional[str] = None,
        productId: Optional[str] = None,
        productName: Optional[str] = None,
        projectType: Optional[str] = None,
        currentPage: int = 1,
        pageSize: int = 40
    ) -> str:
        """
        查询工程项目基础信息，包括代码仓库、父项目、所属组等。
        
        Args:
            id: 项目 ID
            name: 项目名称（模糊匹配）
            productId: 产品 ID
            productName: 产品名称（模糊匹配）
            projectType: 项目类型
            currentPage: 页码，默认 1
            pageSize: 每页条数，默认 40
        """
        params = {}
        if id: params['id'] = id
        if name: params['name'] = name
        if productId: params['productId'] = productId
        if productName: params['productName'] = productName
        if projectType: params['projectType'] = projectType
        params['current'] = currentPage
        params['size'] = pageSize
        
        result = client.query_project_basis(**params)
        
        if HAS_FORMATTER:
            formatted = format_output('project-basis-query', result, f"name={name}, productName={productName}")
            response = {
                "raw_data": result,
                "formatted_text": formatted.get('formatted_text', ''),
                "summary": formatted.get('summary', {})
            }
            return json.dumps(response, ensure_ascii=False, indent=2)
        
        return json.dumps(result, ensure_ascii=False, indent=2)


def run_mcp():
    """运行 MCP 服务器"""
    if not HAS_MCP:
        logger.error("未安装 mcp 模块，请先安装: pip install 'mcp[cli]'")
        sys.exit(1)
    
    logger.info("启动 MCP 服务器...")
    logger.info("注册工具: cmdb_server_query, server_public_ip_query, project_deployment_query, product_query, project_basis_query")
    mcp.run()


# ============================================================================
# HTTP 模式
# ============================================================================

if HAS_FASTAPI:
    app = FastAPI(
        title="ops-data-query-mcp",
        description="企业 CMDB 运维数据综合查询服务 - HTTP/MCP 双模式",
        version="1.0.0"
    )
    
    # Pydantic 模型
    class ServerQueryParams(BaseModel):
        hostName: Optional[str] = None
        ip: Optional[str] = None
        node: Optional[str] = None
        state: Optional[str] = None
        serverType: Optional[str] = None
        belong: Optional[int] = None
        xc: Optional[str] = None
        productName: Optional[str] = None
        projectName: Optional[str] = None
        currentPage: int = 1
        pageSize: int = 15
    
    class PublicIPQueryParams(BaseModel):
        ip: Optional[str] = None
        hostName: Optional[str] = None
        node: Optional[str] = None
        currentPage: int = 1
        pageSize: int = 40
    
    class DeploymentQueryParams(BaseModel):
        projectName: Optional[str] = None
        environment: Optional[int] = None
        deploymentStatus: Optional[int] = None
        deployer: Optional[str] = None
        startTime: Optional[str] = None
        endTime: Optional[str] = None
        currentPage: int = 1
        pageSize: int = 40
    
    class ProductQueryParams(BaseModel):
        id: Optional[str] = None
        name: Optional[str] = None
        flag: Optional[int] = None
        department: Optional[str] = None
        currentPage: int = 1
        pageSize: int = 40
    
    class ProjectBasisQueryParams(BaseModel):
        id: Optional[str] = None
        name: Optional[str] = None
        productId: Optional[str] = None
        productName: Optional[str] = None
        projectType: Optional[str] = None
        currentPage: int = 1
        pageSize: int = 40
    
    @app.get("/", tags=["基础"])
    def root():
        return {
            "service": "ops-data-query-mcp",
            "version": "1.0.0",
            "description": "企业 CMDB 运维数据综合查询服务 - HTTP/MCP 双模式",
            "endpoints": [
                "/api/cmdb-server-query",
                "/api/server-public-ip-query",
                "/api/project-deployment-query",
                "/api/product-query",
                "/api/project-basis-query"
            ],
            "docs": "/docs",
            "health": "/health",
            "tools": [
                "cmdb_server_query",
                "server_public_ip_query",
                "project_deployment_query",
                "product_query",
                "project_basis_query"
            ]
        }
    
    @app.get("/health", tags=["基础"])
    def health():
        """健康检查端点"""
        mock_path = os.path.join(_references_dir, 'mock_responses.json')
        mock_exists = os.path.exists(mock_path)
        return {
            "status": "healthy",
            "service": "ops-data-query-mcp",
            "version": "1.0.0",
            "mock_data_available": mock_exists,
            "modules": {
                "mcp": HAS_MCP,
                "fastapi": HAS_FASTAPI,
                "requests": HAS_REQUESTS
            }
        }
    
    @app.post("/api/cmdb-server-query", tags=["服务器查询"])
    def http_cmdb_server_query(params: ServerQueryParams):
        """查询 CMDB 服务器信息"""
        query_params = {
            "hostName": params.hostName,
            "ip": params.ip,
            "node": params.node,
            "state": params.state,
            "serverType": params.serverType,
            "belong": params.belong,
            "xc": params.xc,
            "productName": params.productName,
            "projectName": params.projectName,
            "currentPage": params.currentPage,
            "pageSize": params.pageSize
        }
        query_params = {k: v for k, v in query_params.items() if v is not None}
        result = client.query_server(**query_params)
        
        if HAS_FORMATTER:
            formatted = format_output('cmdb-server-query', result, f"node={params.node}, ip={params.ip}, hostName={params.hostName}")
            response = {
                "raw_data": result,
                "formatted_text": formatted.get('formatted_text', ''),
                "summary": formatted.get('summary', {})
            }
            return JSONResponse(content=response)
        
        return JSONResponse(content=result)
    
    @app.post("/api/server-public-ip-query", tags=["公网IP查询"])
    def http_server_public_ip_query(params: PublicIPQueryParams):
        """查询服务器公网 IP 信息"""
        query_params = {
            "ip": params.ip,
            "hostName": params.hostName,
            "node": params.node,
            "current": params.currentPage,
            "size": params.pageSize
        }
        query_params = {k: v for k, v in query_params.items() if v is not None}
        result = client.query_public_ip(**query_params)
        
        if HAS_FORMATTER:
            formatted = format_output('server-public-ip-query', result, f"node={params.node}, ip={params.ip}, hostName={params.hostName}")
            response = {
                "raw_data": result,
                "formatted_text": formatted.get('formatted_text', ''),
                "summary": formatted.get('summary', {})
            }
            return JSONResponse(content=response)
        
        return JSONResponse(content=result)
    
    @app.post("/api/project-deployment-query", tags=["部署查询"])
    def http_project_deployment_query(params: DeploymentQueryParams):
        """查询项目部署记录"""
        query_params = {
            "projectName": params.projectName,
            "environment": params.environment,
            "statusCode": params.deploymentStatus,
            "deployer": params.deployer,
            "startTime": params.startTime,
            "endTime": params.endTime,
            "currentPage": params.currentPage,
            "pageSize": params.pageSize
        }
        query_params = {k: v for k, v in query_params.items() if v is not None}
        result = client.query_deployment(**query_params)
        
        if HAS_FORMATTER:
            formatted = format_output('project-deployment-query', result, f"projectName={params.projectName}, environment={params.environment}")
            response = {
                "raw_data": result,
                "formatted_text": formatted.get('formatted_text', ''),
                "summary": formatted.get('summary', {})
            }
            return JSONResponse(content=response)
        
        return JSONResponse(content=result)
    
    @app.post("/api/product-query", tags=["产品查询"])
    def http_product_query(params: ProductQueryParams):
        """查询产品信息"""
        query_params = {
            "id": params.id,
            "name": params.name,
            "flag": params.flag,
            "department": params.department,
            "current": params.currentPage,
            "size": params.pageSize
        }
        query_params = {k: v for k, v in query_params.items() if v is not None}
        result = client.query_product(**query_params)
        
        if HAS_FORMATTER:
            formatted = format_output('product-query', result, f"name={params.name}, department={params.department}")
            response = {
                "raw_data": result,
                "formatted_text": formatted.get('formatted_text', ''),
                "summary": formatted.get('summary', {})
            }
            return JSONResponse(content=response)
        
        return JSONResponse(content=result)
    
    @app.post("/api/project-basis-query", tags=["项目查询"])
    def http_project_basis_query(params: ProjectBasisQueryParams):
        """查询工程项目基础信息"""
        query_params = {
            "id": params.id,
            "name": params.name,
            "productId": params.productId,
            "productName": params.productName,
            "projectType": params.projectType,
            "current": params.currentPage,
            "size": params.pageSize
        }
        query_params = {k: v for k, v in query_params.items() if v is not None}
        result = client.query_project_basis(**query_params)
        
        if HAS_FORMATTER:
            formatted = format_output('project-basis-query', result, f"name={params.name}, productName={params.productName}")
            response = {
                "raw_data": result,
                "formatted_text": formatted.get('formatted_text', ''),
                "summary": formatted.get('summary', {})
            }
            return JSONResponse(content=response)
        
        return JSONResponse(content=result)


def run_http(host: str = "0.0.0.0", port: int = 8000):
    """运行 HTTP 服务器"""
    if not HAS_FASTAPI:
        logger.error("未安装 fastapi/uvicorn 模块，请先安装: pip install fastapi uvicorn")
        sys.exit(1)
    
    logger.info(f"启动 HTTP 服务器... http://{host}:{port}")
    logger.info(f"API 文档: http://{host}:{port}/docs")
    uvicorn.run(app, host=host, port=port)


# ============================================================================
# 主入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ops-data-query MCP 服务器 - 企业 CMDB 运维数据综合查询"
    )
    parser.add_argument(
        "--transport",
        choices=["mcp", "http"],
        default="http",
        help="传输协议: mcp (MCP stdio 协议) 或 http (HTTP API)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="HTTP 服务器监听地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP 服务器监听端口 (默认: 8000)"
    )
    
    args = parser.parse_args()
    
    if args.transport == "mcp":
        run_mcp()
    else:
        run_http(args.host, args.port)


if __name__ == "__main__":
    main()