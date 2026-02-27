"""
PDF report generation module.
Uses ReportLab for PDF and matplotlib for chart images.
"""

import json
import io
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy.orm import Session

from ..config import settings
from ..models.database import get_db
from ..models.schemas import Task

router = APIRouter(prefix="/api/report", tags=["report"])


class ReportRequest(BaseModel):
    title: str = "AICP LLM推理性能测试报告"
    remark: str = ""
    baseline_task_id: str
    optimized_task_id: str = ""


def _load_df(task_id: str, db: Session) -> pd.DataFrame:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task or not task.data_dir:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    files = sorted(Path(task.data_dir).glob("performance_data_*.csv"))
    if not files:
        raise HTTPException(status_code=404, detail="No data")
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


def _make_chart(fig, filename: str) -> str:
    path = settings.DATA_DIR / "reports" / f"_tmp_{filename}"
    fig.savefig(str(path), dpi=150, bbox_inches="tight", facecolor="#0a0e1a")
    plt.close(fig)
    return str(path)


def _distribution_chart(series, title, xlabel, bins=10):
    fig, ax = plt.subplots(figsize=(7, 3.5), facecolor="#0a0e1a")
    ax.set_facecolor("#0a0e1a")
    ax.hist(series.dropna(), bins=bins, color="#00f0ff", alpha=0.8, edgecolor="#7c3aed")
    ax.set_title(title, color="white", fontsize=12)
    ax.set_xlabel(xlabel, color="white")
    ax.set_ylabel("Count", color="white")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#333")
    return fig


def _comparison_chart(baseline, optimized, title, ylabel):
    fig, ax = plt.subplots(figsize=(7, 3.5), facecolor="#0a0e1a")
    ax.set_facecolor("#0a0e1a")
    x_b = range(len(baseline))
    x_o = range(len(optimized))
    ax.plot(x_b, baseline, color="#ff6b6b", alpha=0.7, label="Baseline", linewidth=1)
    ax.plot(x_o, optimized, color="#00f0ff", alpha=0.9, label="Optimized", linewidth=1)
    ax.set_title(title, color="white", fontsize=12)
    ax.set_xlabel("Request Sequence", color="white")
    ax.set_ylabel(ylabel, color="white")
    ax.tick_params(colors="white")
    ax.legend(facecolor="#1a1e2e", edgecolor="#333", labelcolor="white")
    for spine in ax.spines.values():
        spine.set_color("#333")
    return fig


@router.post("/generate")
async def generate_report(req: ReportRequest, db: Session = Depends(get_db)):
    reports_dir = settings.DATA_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    baseline_df = _load_df(req.baseline_task_id, db)

    report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    pdf_path = reports_dir / f"{report_id}.pdf"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                            topMargin=20*mm, bottomMargin=20*mm,
                            leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=20)
    heading_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=14)
    normal_style = styles["Normal"]

    elements = []

    # ---- Cover ----
    elements.append(Spacer(1, 60*mm))
    elements.append(Paragraph(req.title, title_style))
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
    if req.remark:
        elements.append(Paragraph(f"Remark: {req.remark}", normal_style))
    elements.append(PageBreak())

    # ---- Chapter 1: Data Characteristics ----
    elements.append(Paragraph("1. Data Characteristics Analysis", heading_style))
    elements.append(Spacer(1, 5*mm))

    chart1 = _distribution_chart(baseline_df["prompt_tokens"], "Input Token Length Distribution", "Prompt Tokens")
    img1_path = _make_chart(chart1, "dist_tokens.png")
    elements.append(Image(img1_path, width=160*mm, height=80*mm))
    elements.append(Spacer(1, 5*mm))

    chart2 = _distribution_chart(baseline_df["e2e_latency_ms"], "E2E Latency Distribution", "Latency (ms)")
    img2_path = _make_chart(chart2, "dist_latency.png")
    elements.append(Image(img2_path, width=160*mm, height=80*mm))
    elements.append(Spacer(1, 5*mm))

    chart3 = _distribution_chart(baseline_df["cached_tokens"], "KV Cache Hits Distribution", "Cached Tokens")
    img3_path = _make_chart(chart3, "dist_cache.png")
    elements.append(Image(img3_path, width=160*mm, height=80*mm))
    elements.append(PageBreak())

    # ---- Chapter 2: Baseline Metrics ----
    elements.append(Paragraph("2. Baseline Performance Metrics", heading_style))
    elements.append(Spacer(1, 5*mm))

    def s(col):
        v = baseline_df[col]
        return [round(float(v.mean()), 2), round(float(v.quantile(0.5)), 2),
                round(float(v.quantile(0.9)), 2), round(float(v.quantile(0.99)), 2)]

    table_data = [
        ["Metric", "Avg", "P50", "P90", "P99"],
        ["TTFT (ms)"] + [str(x) for x in s("ttft_ms")],
        ["TPOT (ms)"] + [str(x) for x in s("tpot_ms")],
        ["TPS (tokens/s)"] + [str(x) for x in s("tps")],
        ["E2E Latency (ms)"] + [str(x) for x in s("e2e_latency_ms")],
    ]
    t = Table(table_data, colWidths=[40*mm, 28*mm, 28*mm, 28*mm, 28*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1e2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#333")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    elements.append(t)

    # ---- Chapter 3: Comparison (if optimized provided) ----
    if req.optimized_task_id:
        optimized_df = _load_df(req.optimized_task_id, db)
        elements.append(PageBreak())
        elements.append(Paragraph("3. Optimization Comparison", heading_style))
        elements.append(Spacer(1, 5*mm))

        b_ttft = float(baseline_df["ttft_ms"].mean())
        o_ttft = float(optimized_df["ttft_ms"].mean())
        ttft_pct = round((b_ttft - o_ttft) / b_ttft * 100, 1) if b_ttft > 0 else 0

        b_tps = float(baseline_df["tps"].mean())
        o_tps = float(optimized_df["tps"].mean())
        tps_pct = round((o_tps - b_tps) / b_tps * 100, 1) if b_tps > 0 else 0

        comp_data = [
            ["Metric", "Baseline Avg", "Optimized Avg", "Improvement"],
            ["TTFT (ms)", f"{b_ttft:.1f}", f"{o_ttft:.1f}", f"-{ttft_pct}%"],
            ["TPS (tokens/s)", f"{b_tps:.1f}", f"{o_tps:.1f}", f"+{tps_pct}%"],
        ]
        ct = Table(comp_data, colWidths=[38*mm, 35*mm, 35*mm, 35*mm])
        ct.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1e2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#333")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        elements.append(ct)
        elements.append(Spacer(1, 8*mm))

        # TTFT comparison chart
        fig_ttft = _comparison_chart(
            baseline_df["ttft_ms"].tolist(), optimized_df["ttft_ms"].tolist(),
            "TTFT Comparison", "TTFT (ms)"
        )
        img_ttft = _make_chart(fig_ttft, "cmp_ttft.png")
        elements.append(Image(img_ttft, width=160*mm, height=80*mm))
        elements.append(Spacer(1, 5*mm))

        # TPS comparison chart
        fig_tps = _comparison_chart(
            baseline_df["tps"].tolist(), optimized_df["tps"].tolist(),
            "Decode Speed (TPS) Comparison", "TPS (tokens/s)"
        )
        img_tps = _make_chart(fig_tps, "cmp_tps.png")
        elements.append(Image(img_tps, width=160*mm, height=80*mm))

    # ---- Chapter 4: Detail table (first 50 rows) ----
    elements.append(PageBreak())
    elements.append(Paragraph("4. Detailed Performance Data (Sample)", heading_style))
    elements.append(Spacer(1, 5*mm))

    detail_cols = ["序号", "ttft_ms", "tpot_ms", "tps", "e2e_latency_ms", "prompt_tokens", "completion_tokens"]
    sample = baseline_df[detail_cols].head(50)
    detail_data = [detail_cols] + sample.values.tolist()
    dt = Table(detail_data, colWidths=[15*mm, 22*mm, 22*mm, 22*mm, 28*mm, 25*mm, 28*mm])
    dt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1e2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#444")),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
    ]))
    elements.append(dt)

    doc.build(elements)

    # Cleanup temp chart images
    for tmp in reports_dir.glob("_tmp_*.png"):
        tmp.unlink(missing_ok=True)

    return {
        "report_id": report_id,
        "file_path": str(pdf_path),
        "download_url": f"/api/report/download/{report_id}",
    }


@router.get("/download/{report_id}")
async def download_report(report_id: str):
    pdf_path = settings.DATA_DIR / "reports" / f"{report_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(str(pdf_path), media_type="application/pdf", filename=f"{report_id}.pdf")


@router.get("/list")
async def list_reports():
    reports_dir = settings.DATA_DIR / "reports"
    if not reports_dir.exists():
        return []
    return [
        {
            "report_id": f.stem,
            "filename": f.name,
            "file_size": f.stat().st_size,
            "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        }
        for f in sorted(reports_dir.glob("report_*.pdf"), reverse=True)
    ]
