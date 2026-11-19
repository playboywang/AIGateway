# AIGateway 当前架构

## 首期范围

- 配置体系只采用 `llm_*` 表。
- 客户端身份只依赖 `client` 与 `client_api_key`。
- 请求日志只写入 `client_request_log`。
- 不实现 access token、配额、积分计费、坐席和内嵌任务体系。
- 暂不实现视频、MCP 和其他非模型 API 能力。

## 配置优先级

运行时配置按以下顺序读取：

1. 项目 `.env` 中存在的配置键。
2. `config/defaults.py` 中的默认值。

判断依据是键是否存在，而不是值是否为空。删除或注释 `.env` 中的键才会回退到默认值。

## 核心数据模型

### 客户端与鉴权

- `client`
- `client_api_key`

### 模型路由

- `llm_logic_model`
- `llm_provider`
- `llm_provider_endpoint`
- `llm_provider_key`
- `llm_provider_model`

### 预留的模型组能力

- `llm_model_group`
- `llm_model_group_client`
- `llm_model_group_provider_mapping`
- `llm_service_model_mapping`

首期 API 流量使用 `.env` 中的 `AIGATEWAY_DEFAULT_GROUP_TYPE` 选择端点和 Key 池，默认值为 `API`。

### 请求日志

- `client_request_log`

## 模型匹配流程

```text
body.model
→ llm_logic_model
→ llm_provider_model
→ llm_provider
→ llm_provider_endpoint（protocol_code + group_type）
→ llm_provider_key（状态、过期时间、并发容量）
→ 按并发数、更新时间和 ID 选择候选 Key
```

## 协议编码

- `anthropic`
- `chat`
- `responses`
- `embeddings`（预留）

端点 `base_url` 必须是完整的上游请求地址，路由层不再拼接协议后缀。

## 数据库变更

数据库结构由 Alembic 管理：

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

应用启动不负责自动建表或修改生产表结构。
