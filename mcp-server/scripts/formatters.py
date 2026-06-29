#!/usr/bin/env python3
"""
MCP Server 数据格式化模块
将 API 返回的原始数据格式化为用户友好的 Markdown 表格
不依赖 StarAgent 平台的模板渲染
"""

import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_script_dir)
_config_dir = os.path.join(_root_dir, 'config')

# 状态映射
STATE_MAP = {
    '0': '🟢 在线',
    '1': '🟡 库存',
    '2': '🟠 计划上线',
    '3': '🔧 维修中',
    '4': '⚫ 已报废',
    '5': '⬜ 待分配',
    '6': '🔴 待清退'
}

STATUS_MAP = {
    '0': '✅ 成功',
    '1': '❌ 失败',
    '2': '🔄 进行中',
    '3': '⏳ 待部署'
}

SERVER_TYPE_MAP = {
    '0': '物理机',
    '1': '虚拟机',
    '2': '云服务器'
}

# 各技能的字段配置
FIELD_CONFIGS = {
    'cmdb-server-query': {
        'standard': ['hostName', 'ip', 'node', 'state', 'serverType', 'cpuCores', 'memory', 'productName'],
        'detailed': ['hostName', 'ip', 'publicIp', 'vip', 'node', 'state', 'serverType', 'cpuCores', 'memory', 'os', 'environment', 'productName', 'projectName', 'operA', 'operB', 'assetNo', 'rack', 'bandWidth'],
        'headers': {
            'hostName': '主机名',
            'ip': 'IP',
            'publicIp': '公网IP',
            'vip': 'VIP',
            'node': '机房',
            'state': '状态',
            'serverType': '类型',
            'cpuCores': 'CPU',
            'memory': '内存',
            'os': '操作系统',
            'environment': '环境',
            'productName': '产品',
            'projectName': '项目',
            'operA': '运维A',
            'operB': '运维B',
            'assetNo': '资产编号',
            'rack': '机架',
            'bandWidth': '带宽'
        }
    },
    'server-public-ip-query': {
        'standard': ['publicIp', 'ip', 'node', 'bandwidth', 'bandwidthType'],
        'detailed': ['publicIp', 'publicIpv6', 'ip', 'vip', 'node', 'privatePort', 'publicPort', 'bandwidth', 'bandwidthType', 'billingType'],
        'headers': {
            'publicIp': '公网IP',
            'publicIpv6': '公网IPv6',
            'ip': '内网IP',
            'vip': 'VIP',
            'node': '机房',
            'privatePort': '内网端口',
            'publicPort': '公网端口',
            'bandwidth': '带宽',
            'bandwidthType': '带宽类型',
            'billingType': '计费方式'
        }
    },
    'project-deployment-query': {
        'standard': ['projectName', 'environment', 'deploymentStatus', 'version', 'deployer', 'startTime'],
        'detailed': ['projectName', 'environment', 'environmentCode', 'deploymentStatus', 'statusCode', 'startTime', 'endTime', 'duration', 'deployer', 'version', 'gitBranch'],
        'headers': {
            'projectName': '项目名称',
            'environment': '环境',
            'environmentCode': '环境代码',
            'deploymentStatus': '部署状态',
            'statusCode': '状态码',
            'startTime': '开始时间',
            'endTime': '结束时间',
            'duration': '耗时',
            'deployer': '部署人',
            'version': '版本',
            'gitBranch': '分支'
        }
    },
    'product-query': {
        'standard': ['productName', 'department', 'productManager', 'opsLead', 'enabled'],
        'detailed': ['productName', 'productFunction', 'parentProduct', 'productLevel', 'enabled', 'department', 'productManager', 'opsLead'],
        'headers': {
            'productName': '产品名称',
            'productFunction': '产品功能',
            'parentProduct': '父产品',
            'productLevel': '级别',
            'enabled': '启用状态',
            'department': '部门',
            'productManager': '产品经理',
            'opsLead': '运维负责人'
        }
    },
    'project-basis-query': {
        'standard': ['projectName', 'chineseName', 'productName', 'projectType', 'repoPath'],
        'detailed': ['projectName', 'chineseName', 'productName', 'repoPath', 'description', 'projectType', 'parentProject', 'group'],
        'headers': {
            'projectName': '项目名称',
            'chineseName': '中文名称',
            'productName': '所属产品',
            'repoPath': '代码仓库',
            'description': '描述',
            'projectType': '项目类型',
            'parentProject': '父项目',
            'group': '所属组'
        }
    }
}


def _format_value(field_name, value, skill_id):
    """格式化字段值"""
    if value is None:
        return '-'
    
    value = str(value)
    
    if value == '':
        return '-'
    
    # 状态格式化
    if field_name == 'state':
        return STATE_MAP.get(value, value)
    
    if field_name == 'statusCode':
        return STATUS_MAP.get(value, value)
    
    if field_name == 'serverType':
        return SERVER_TYPE_MAP.get(value, value)
    
    # 内存格式化
    if field_name == 'memory' and value and not value.endswith('GB'):
        return f"{value}GB"
    
    # CPU格式化
    if field_name == 'cpuCores' and value:
        return f"{value}核"
    
    # 耗时格式化
    if field_name == 'duration' and value.isdigit():
        seconds = int(value)
        if seconds >= 3600:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}小时{minutes}分"
        elif seconds >= 60:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}分{secs}秒"
        else:
            return f"{seconds}秒"
    
    return value


def _build_table(records, fields, headers, skill_id):
    """构建 Markdown 表格"""
    if not records:
        return None
    
    # 构建表头
    header_row = "| " + " | ".join([headers.get(f, f) for f in fields]) + " |"
    separator_row = "| " + " | ".join(["---" for _ in fields]) + " |"
    
    # 构建数据行
    data_rows = []
    for record in records:
        row_values = []
        for field in fields:
            raw_value = record.get(field)
            formatted_value = _format_value(field, raw_value, skill_id)
            row_values.append(formatted_value)
        data_row = "| " + " | ".join(row_values) + " |"
        data_rows.append(data_row)
    
    return {
        'header': header_row,
        'separator': separator_row,
        'rows': data_rows,
        'full': f"{header_row}\n{separator_row}\n" + "\n".join(data_rows)
    }


def format_output(skill_id, api_response, user_query="", detail=False):
    """
    格式化 API 响应为用户友好的 Markdown 输出
    
    Args:
        skill_id: 技能 ID
        api_response: API 响应数据
        user_query: 用户查询条件
        detail: 是否显示详细模式
    
    Returns:
        dict: 包含原始数据和格式化文本
    """
    result = {
        'success': False,
        'raw_data': api_response,
        'formatted_text': '',
        'summary': {}
    }
    
    if api_response.get('code') != 200:
        result['formatted_text'] = f"## 查询失败\n\n**错误信息**: {api_response.get('message', '未知错误')}"
        return result
    
    data = api_response.get('data', {})
    records = data.get('records', [])
    total = data.get('total', 0)
    current_page = data.get('currentPage', data.get('current', 1))
    page_size = data.get('pageSize', data.get('size', 10))
    show_count = len(records)
    
    result['success'] = True
    result['summary'] = {
        'total': total,
        'current_page': current_page,
        'page_size': page_size,
        'show_count': show_count
    }
    
    # 获取字段配置
    config = FIELD_CONFIGS.get(skill_id, {})
    fields = config.get('detailed', config.get('standard', [])) if detail else config.get('standard', [])
    headers = config.get('headers', {})
    
    # 构建表格
    table = _build_table(records, fields, headers, skill_id)
    
    # 技能名称映射
    skill_name_map = {
        'cmdb-server-query': 'CMDB 服务器查询',
        'server-public-ip-query': '公网 IP 查询',
        'project-deployment-query': '项目部署查询',
        'product-query': '产品信息查询',
        'project-basis-query': '项目基础查询'
    }
    skill_name = skill_name_map.get(skill_id, skill_id)
    
    # 构建输出
    if not records:
        formatted = f"""## {skill_name}查询结果

**查询条件**: {user_query}
**匹配技能**: {skill_name}

---

**结果摘要**: 未查询到符合条件的记录

---

💡 您可以尝试其他查询条件，如：
- 贵州机房的服务器
- 天翼看家产品
- 最近的部署记录
"""
    else:
        formatted = f"""## {skill_name}查询结果

**查询条件**: {user_query}
**匹配技能**: {skill_name}

---

**结果摘要**: 共查询到 {total} 条记录，当前显示前 {show_count} 条（第 {current_page} 页）

---

{table['full']}

---

💡 您可以说：
- "查看详细信息" - 显示更多字段
- "下一页" - 查看更多结果
- "查看全部" - 显示所有结果
"""
    
    result['formatted_text'] = formatted
    return result


def test_formatting():
    """测试格式化功能"""
    import json
    
    mock_path = os.path.join(_root_dir, 'references', 'mock_responses.json')
    with open(mock_path, 'r', encoding='utf-8') as f:
        mock_data = json.load(f)
    
    # 测试服务器查询
    print("=" * 70)
    print("测试: CMDB 服务器查询")
    print("=" * 70)
    server_response = mock_data['cmdb-server-query']
    result = format_output('cmdb-server-query', server_response, '贵州机房的服务器')
    print(result['formatted_text'])
    print()
    
    # 测试公网IP查询
    print("=" * 70)
    print("测试: 公网 IP 查询")
    print("=" * 70)
    ip_response = mock_data['server-public-ip-query']
    result = format_output('server-public-ip-query', ip_response, '贵州机房的公网IP')
    print(result['formatted_text'])
    print()
    
    # 测试部署查询
    print("=" * 70)
    print("测试: 项目部署查询")
    print("=" * 70)
    deploy_response = mock_data['project-deployment-query']
    result = format_output('project-deployment-query', deploy_response, 'guizh-rules-api 的部署记录')
    print(result['formatted_text'])
    print()
    
    # 测试产品查询
    print("=" * 70)
    print("测试: 产品信息查询")
    print("=" * 70)
    product_response = mock_data['product-query']
    result = format_output('product-query', product_response, '云公司的产品')
    print(result['formatted_text'])
    print()
    
    # 测试项目基础查询
    print("=" * 70)
    print("测试: 项目基础查询")
    print("=" * 70)
    basis_response = mock_data['project-basis-query']
    result = format_output('project-basis-query', basis_response, '规则引擎平台的项目')
    print(result['formatted_text'])


if __name__ == "__main__":
    test_formatting()