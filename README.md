# 多数据源数据分析智能体

课题 5 的第一期实现：自写 `data-mcp` 只读查询服务，接入 SQLite 销售明细和 Excel 商品成本表。

## 数据

| 表 | 来源 | 字段 |
|---|---|---|
| `sales` | `data/sales.db` | sale_date、region、category、product、qty、amount |
| `products` | `data/products.xlsx` | product、category、unit_cost |

样例数据覆盖 2024-01 到 2025-10、华东 / 华南 / 华北三个区域，以及手机、电脑、配件三类商品，可支撑同环比和柱状 / 折线 / 饼图验收。重新生成：

```bash
python data/generate_sample_data.py
```

对照 10 道验收题并打印结果：

```bash
python scripts/run_acceptance.py
```

## data-mcp 工具

- `list_tables`：列出可查询的表
- `describe_table`：查看表结构
- `run_sql`：执行只读 SQL（禁 `DROP/DELETE/UPDATE` 等写操作，自动 `LIMIT 1000`，超时 10 秒）
- `sample_rows`：查看表的样例行

查询引擎会把 SQLite 和 Excel 装入内存中的只读库，因此第 9 题的跨源 `JOIN` 可以直接跑，SQL 方言与验收题一致（含 `strftime('%Y-%m', sale_date)`）。源文件不会被改写。

## 本地运行

需要 Python 3.11 或以上。在项目根目录：

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
python data_mcp/server.py
```

MCP 默认走标准输入输出。后面会再接 Streamlit 对话区和结果三 Tab（表格 / 图 / SQL）。

## Streamlit 应用

在项目根目录、已激活虚拟环境后启动：

```bash
streamlit run app.py
```

页面左侧是对话区，右侧是结果三 Tab：表格、图、生成的 SQL。侧边栏里有 10 道验收示例题，可直接点。图表支持柱状、折线、饼图，并把当前结果、统计分析和 SQL 导出为 Excel 多 Sheet。

自然语言转 SQL 会先用表结构和 3 条示例 SQL 做 few-shot；如果配置了环境变量 `DEEPSEEK_API_KEY`，会调用 DeepSeek，先做 dry-run 再执行。没有密钥时，这 10 道验收题仍可通过本地规则生成可执行 SQL。
