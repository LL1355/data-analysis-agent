"""Streamlit app: chat + result tabs (table / chart / SQL)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from app.nl2sql import generate_sql
from app.skills.compute_stats import compute_stats
from app.skills.export_report import export_report
from app.skills.make_chart import make_chart, recommend_chart_type
from data_mcp.datasources import fetch_rows
from data_mcp.security import SqlGuardError, run_with_timeout


def _empty_state() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("last_question", "")
    st.session_state.setdefault("last_sql", "")
    st.session_state.setdefault("last_source", "")
    st.session_state.setdefault("last_df", pd.DataFrame())
    st.session_state.setdefault("last_stats", pd.DataFrame())
    st.session_state.setdefault("last_chart_type", None)
    st.session_state.setdefault("last_error", "")


def _run_question(question: str) -> None:
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.last_question = question
    st.session_state.last_error = ""
    try:
        plan = generate_sql(question)
        rows = run_with_timeout(fetch_rows, plan.sql)
        frame = pd.DataFrame(rows)
        stats = compute_stats(frame)
        chart_type = recommend_chart_type(frame, plan.chart_type)
        st.session_state.last_sql = plan.sql
        st.session_state.last_source = plan.source
        st.session_state.last_df = frame
        st.session_state.last_stats = stats
        st.session_state.last_chart_type = chart_type
        preview = f"已生成 SQL（来源: {plan.source}），返回 {len(frame)} 行。"
        st.session_state.messages.append({"role": "assistant", "content": preview})
    except (SqlGuardError, ValueError, Exception) as exc:
        st.session_state.last_error = str(exc)
        st.session_state.messages.append({"role": "assistant", "content": f"出错了：{exc}"})


def main() -> None:
    st.set_page_config(page_title="多数据源数据分析智能体", layout="wide")
    st.title("多数据源数据分析智能体")
    st.caption("自然语言提问 → 生成 SQL → 执行 → 结果表 / 图 / SQL。数据源：SQLite 销售明细 + Excel 商品成本。")

    _empty_state()

    examples = [
        "各个区域的销售总额是多少？",
        "各个类别的销售额占比是多少？",
        "按月的销售额趋势是怎样的？",
        "销售额最高的 5 个商品是哪些？",
        "全部订单的平均金额是多少？",
        "华东地区一共卖了多少件？",
        "2025 年 10 月比 9 月的销售额环比是多少？",
        "2025 年 10 月和 2024 年 10 月的销售额同比是多少？",
        "每个商品的销售毛利是多少？",
        "手机类别的销售额占全部的比例是多少？",
    ]

    with st.sidebar:
        st.subheader("示例问题")
        st.write("点击后会直接查询，对应课题的 10 道验收题。")
        for item in examples:
            if st.button(item, use_container_width=True):
                _run_question(item)
                st.rerun()

    left, right = st.columns([1, 2], gap="large")

    with left:
        st.subheader("对话")
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        question = st.chat_input("用自然语言提问，例如：各个区域的销售总额是多少？")
        if question:
            _run_question(question)
            st.rerun()

    with right:
        st.subheader("结果")
        tabs = st.tabs(["表格", "图", "生成的 SQL"])
        with tabs[0]:
            if st.session_state.last_error:
                st.error(st.session_state.last_error)
            if st.session_state.last_df is not None and not st.session_state.last_df.empty:
                st.dataframe(st.session_state.last_df, use_container_width=True)
                if st.session_state.last_stats is not None and not st.session_state.last_stats.empty:
                    st.markdown("**统计分析**")
                    st.dataframe(st.session_state.last_stats, use_container_width=True)
            else:
                st.info("还没有查询结果。先在左侧提问，或点侧边栏里的示例。")
        with tabs[1]:
            frame = st.session_state.last_df
            if frame is not None and not frame.empty:
                fig = make_chart(frame, st.session_state.last_chart_type, title=st.session_state.last_question)
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(f"图表类型：{st.session_state.last_chart_type}")
                else:
                    st.info("当前结果不适合画图，比如只有一个数字指标。可在「表格」里查看。")
            else:
                st.info("还没有可以出图的结果。")
        with tabs[2]:
            if st.session_state.last_sql:
                st.code(st.session_state.last_sql, language="sql")
                if st.session_state.last_source:
                    st.caption(f"SQL 来源：{st.session_state.last_source}")
            else:
                st.info("还没有生成 SQL。")

        if st.session_state.last_sql:
            report = export_report(
                result=st.session_state.last_df,
                stats=st.session_state.last_stats,
                sql=st.session_state.last_sql,
                question=st.session_state.last_question,
                chart_type=st.session_state.last_chart_type,
            )
            st.download_button(
                "导出报表（Excel 多 Sheet）",
                data=report,
                file_name="analysis_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


if __name__ == "__main__":
    main()
