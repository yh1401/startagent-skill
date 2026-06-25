# Mock 数据说明

> ⚠️ **已废弃**：Mock 数据已迁移至 `references/mock_responses.json`
> 
> 本文件仅保留说明，请勿继续引用其中的数据。

## 迁移说明

Mock 数据现已统一存储在 `references/mock_responses.json`，包含以下 5 个 API 的模拟响应：

| 技能 | Mock Key |
|------|----------|
| CMDB服务器查询 | `cmdb-server-query` |
| 服务器公网IP查询 | `server-public-ip-query` |
| 项目部署查询 | `project-deployment-query` |
| 产品查询 | `product-query` |
| 项目基础信息查询 | `project-basis-query` |

## 使用方式

API 调用失败时，从 `references/mock_responses.json` 中读取对应技能的 mock 数据：

```python
import json

with open("references/mock_responses.json") as f:
    mock_data = json.load(f)
    return mock_data["cmdb-server-query"]
```

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 2.0 | 2026-06-24 | 迁移到 references/mock_responses.json，统一管理 |
| 1.0 | 2026-05-20 | 初始版本 |
