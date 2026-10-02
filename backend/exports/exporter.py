"""
backend/exports/exporter.py
Handles CSV, Excel (multi-sheet), and executive PDF generation using ReportLab.
Supports privacy masking for customer names per PRD Section 5.4.
"""

import io
from typing import Dict, Any, Optional
import pandas as pd
from backend.analytics.currency import format_inr, convert_to_inr
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def export_to_csv(df: pd.DataFrame, include_customer_names: bool = True) -> bytes:
    """Exports DataFrame to clean CSV bytes."""
    export_df = df.copy()
    if not include_customer_names:
        for c in ["_std_customer_name", "Customer Name"]:
            if c in export_df.columns:
                export_df[c] = "[REDACTED]"
    
    # Drop internal helper columns from export
    cols_to_export = [c for c in export_df.columns if not c.startswith("_std_")]
    if not cols_to_export:
        cols_to_export = export_df.columns
    return export_df[cols_to_export].to_csv(index=False).encode("utf-8")


def export_to_excel(
    df: pd.DataFrame,
    kpis: Dict[str, Any],
    cat_df: Optional[pd.DataFrame] = None,
    reg_df: Optional[pd.DataFrame] = None,
    include_customer_names: bool = True
) -> bytes:
    """Exports structured multi-sheet Excel workbook."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: Executive KPI Summary
        kpi_rows = [
            {"Metric": "Total Sales (INR)", "Value": convert_to_inr(kpis.get("total_sales", 0) or 0)},
            {"Metric": "Total Profit (INR)", "Value": convert_to_inr(kpis.get("total_profit", 0) or 0)},
            {"Metric": "Total Orders (Distinct)", "Value": kpis.get("total_orders", 0)},
            {"Metric": "Total Quantity", "Value": kpis.get("total_quantity", 0)},
            {"Metric": "Average Order Value INR", "Value": convert_to_inr(kpis.get("aov", 0) or 0)},
            {"Metric": "Profit Margin (%)", "Value": kpis.get("profit_margin_pct", 0)},
        ]
        pd.DataFrame(kpi_rows).to_excel(writer, sheet_name="Executive Summary", index=False)

        # Sheet 2: Category Breakdown
        if cat_df is not None and not cat_df.empty:
            cat_df.to_excel(writer, sheet_name="Categories", index=False)

        # Sheet 3: Regional Breakdown
        if reg_df is not None and not reg_df.empty:
            reg_df.to_excel(writer, sheet_name="Regions", index=False)

        # Sheet 4: Raw Active Records (up to 10,000)
        export_df = df.copy()
        if not include_customer_names:
            for c in ["_std_customer_name", "Customer Name"]:
                if c in export_df.columns:
                    export_df[c] = "[REDACTED]"
        cols = [c for c in export_df.columns if not c.startswith("_std_")]
        if not cols:
            cols = export_df.columns
        export_df[cols].head(10000).to_excel(writer, sheet_name="Active Transactions", index=False)

    return output.getvalue()


def generate_executive_pdf(
    kpis: Dict[str, Any],
    findings: list,
    date_range_str: str,
    cat_df: Optional[pd.DataFrame] = None,
    state_df: Optional[pd.DataFrame] = None,
    currency_symbol: str = "₹",
    dataset_name: str = "",
    filters_summary: str = "",
) -> bytes:
    """Generates a professional 1-page executive briefing PDF using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1E3A8A"),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "SubTitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=15
    )
    section_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155")
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("Sales Performance Executive Report", title_style))
    meta = f"Reporting Scope: {date_range_str}"
    if dataset_name:
        meta += f" | Dataset: {dataset_name}"
    if filters_summary:
        meta += f" | Filters: {filters_summary}"
    story.append(Paragraph(meta + " | Generated via Sales Analytics Platform", subtitle_style))
    story.append(Spacer(1, 10))

    kpi_data = [
        ["Total Revenue", "Total Profit", "Distinct Orders", "Profit Margin"],
        [
            format_inr(kpis.get("total_sales", 0)),
            format_inr(kpis.get("total_profit", 0) or 0),
            f"{kpis.get('total_orders', 0):,}",
            f"{(kpis.get('profit_margin_pct') or 0):.1f}%"
        ]
    ]
    t = Table(kpi_data, colWidths=[130, 130, 130, 130])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#475569")),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 12),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor("#1E3A8A")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    # Executive Highlights
    story.append(Paragraph("Executive Highlights & Data-Grounded Findings", section_style))
    for f in findings[:4]:
        bullet_text = f"<b>{f.get('title')}:</b> {f.get('text')}"
        story.append(Paragraph(f"• {bullet_text}", body_style))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 10))

    # Category Breakdown Table
    if cat_df is not None and not cat_df.empty:
        story.append(Paragraph("Category Revenue & Profitability Breakdown", section_style))
        cat_table_data = [["Category", "Sales", "Profit", "Margin %"]]
        for _, row in cat_df.head(5).iterrows():
            cat_table_data.append([
                str(row.get("Category", "")),
                format_inr(row.get("Sales", 0)),
                format_inr(row.get("Profit", 0)),
                f"{row.get('Profit Margin %', 0):.1f}%"
            ])
        ct = Table(cat_table_data, colWidths=[180, 110, 110, 120])
        ct.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ]))
        story.append(ct)

    doc.build(story)
    return buffer.getvalue()
