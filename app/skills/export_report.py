"""export_report skill: write an Excel workbook with data, stats, SQL and an optional chart sheet."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.chart.series import DataPoint
from openpyxl.chart.label import DataLabelList
from openpyxl.drawing.fill import PatternFillProperties, ColorChoice
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet


def export_report(
    result: pd.DataFrame,
    stats: pd.DataFrame | None = None,
    sql: str | None = None,
    question: str | None = None,
    chart_type: str | None = None,
) -> bytes:
    workbook = Workbook()
    data_sheet = workbook.active
    data_sheet.title = "结果表"
    if question:
        data_sheet["A1"] = "问题"
        data_sheet["B1"] = question
        start_row = 3
    else:
        start_row = 1
    _write_frame(data_sheet, result, start_row)
    _maybe_add_chart(data_sheet, result, chart_type, start_row)

    stats_sheet = workbook.create_sheet("统计分析")
    _write_frame(stats_sheet, stats if stats is not None else pd.DataFrame(), 1)

    sql_sheet = workbook.create_sheet("生成SQL")
    sql_sheet["A1"] = "SQL"
    sql_sheet["A2"] = sql or ""
    sql_sheet.column_dimensions["A"].width = 100

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def save_report(path: str | Path, **kwargs) -> Path:
    output = Path(path)
    output.write_bytes(export_report(**kwargs))
    return output


def _write_frame(sheet: Worksheet, df: pd.DataFrame, start_row: int) -> None:
    if df is None or df.empty:
        sheet.cell(start_row, 1, "（无数据）")
        return
    for offset, row in enumerate(dataframe_to_rows(df, index=False, header=True)):
        for col, value in enumerate(row, start=1):
            sheet.cell(start_row + offset, col, _excel_value(value))
    for column in sheet.columns:
        letter = column[0].column_letter
        sheet.column_dimensions[letter].width = min(40, max(12, sheet.column_dimensions[letter].width or 12))


def _excel_value(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, AttributeError):
            return str(value)
    return value


def _maybe_add_chart(sheet: Worksheet, df: pd.DataFrame, chart_type: str | None, start_row: int) -> None:
    if df is None or df.empty or df.shape[1] < 2 or chart_type not in {"bar", "line", "pie"}:
        return
    header_row = start_row
    data_rows = len(df)
    cats = Reference(sheet, min_col=1, min_row=header_row + 1, max_row=header_row + data_rows)
    values = Reference(sheet, min_col=2, min_row=header_row, max_row=header_row + data_rows)
    if chart_type == "line":
        chart = LineChart()
    elif chart_type == "pie":
        chart = PieChart()
        chart.dataLabels = DataLabelList()
        chart.dataLabels.showPercent = True
        chart.dataLabels.showVal = False
        chart.dataLabels.showCatName = True
    else:
        chart = BarChart()
    chart.title = "结果图"
    chart.add_data(values, titles_from_data=True)
    chart.set_categories(cats)
    chart.shape = 4
    sheet.add_chart(chart, "E3")
