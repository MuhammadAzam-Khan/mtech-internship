"""
report_generator.py
---------------------
Generates a professional multi-page PDF report summarizing the sentiment
analysis results, including statistics, charts, a word cloud, and a
sample of the underlying data table.
"""

import os
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # headless rendering for report generation
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak,
)

from utils.logger import log_event

try:
    from wordcloud import WordCloud
    _WORDCLOUD_AVAILABLE = True
except Exception:
    _WORDCLOUD_AVAILABLE = False


class ReportError(Exception):
    pass


def _make_pie_chart(stats: dict, tmpdir: str) -> str:
    labels = ["Positive", "Negative", "Neutral"]
    values = [stats.get("positive", 0), stats.get("negative", 0), stats.get("neutral", 0)]
    colors_map = ["#2ecc71", "#e74c3c", "#95a5a6"]
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    if sum(values) == 0:
        values = [1, 1, 1]
    ax.pie(values, labels=labels, autopct="%1.1f%%", colors=colors_map, startangle=90)
    ax.set_title("Sentiment Distribution")
    path = os.path.join(tmpdir, "pie.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _make_bar_chart(stats: dict, tmpdir: str) -> str:
    labels = ["Positive", "Negative", "Neutral"]
    values = [stats.get("positive", 0), stats.get("negative", 0), stats.get("neutral", 0)]
    colors_map = ["#2ecc71", "#e74c3c", "#95a5a6"]
    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.bar(labels, values, color=colors_map)
    ax.set_ylabel("Number of Comments")
    ax.set_title("Sentiment Counts")
    path = os.path.join(tmpdir, "bar.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _make_source_chart(df: pd.DataFrame, tmpdir: str) -> str:
    fig, ax = plt.subplots(figsize=(5, 3.5))
    counts = df["source"].value_counts()
    ax.bar(counts.index, counts.values, color="#3498db")
    ax.set_ylabel("Mentions")
    ax.set_title("Mentions by Source")
    plt.xticks(rotation=30, ha="right")
    path = os.path.join(tmpdir, "sources.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _make_wordcloud(text: str, tmpdir: str, filename: str, colormap: str = "viridis") -> str:
    if not _WORDCLOUD_AVAILABLE or not text.strip():
        return ""
    wc = WordCloud(width=800, height=400, background_color="white", colormap=colormap)
    wc.generate(text)
    path = os.path.join(tmpdir, filename)
    wc.to_file(path)
    return path


def generate_pdf_report(
    df: pd.DataFrame,
    stats: dict,
    output_path: str,
    project_title: str = "Customer Sentiment Analyzer",
    positive_text: str = "",
    negative_text: str = "",
    recommendations: list = None,
) -> str:
    """
    Build a full PDF report and write it to `output_path`.

    Args:
        df: The analyzed comments DataFrame (must include a 'sentiment' column).
        stats: Dictionary of summary statistics (counts, averages, etc.).
        output_path: Destination .pdf file path.
        project_title: Title displayed on the cover section.
        positive_text: Concatenated text of positive comments (for word cloud).
        negative_text: Concatenated text of negative comments (for word cloud).
        recommendations: List of recommendation strings.

    Returns:
        The output_path, on success.
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            doc = SimpleDocTemplate(output_path, pagesize=A4,
                                     leftMargin=2 * cm, rightMargin=2 * cm,
                                     topMargin=1.5 * cm, bottomMargin=1.5 * cm)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle("TitleStyle", parent=styles["Title"], fontSize=22,
                                          textColor=colors.HexColor("#2c3e50"))
            heading_style = ParagraphStyle("HeadingStyle", parent=styles["Heading2"],
                                            textColor=colors.HexColor("#34495e"), spaceBefore=12)
            body_style = styles["BodyText"]

            elements = []

            # --- Cover / summary ---
            elements.append(Paragraph(project_title, title_style))
            elements.append(Paragraph("AI-Powered Sentiment Analysis Report", styles["Heading3"]))
            elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style))
            elements.append(Spacer(1, 0.5 * cm))

            summary_text = (
                f"This report summarizes the sentiment analysis performed on "
                f"{stats.get('total', len(df))} customer comments collected from "
                f"multiple sources. The analysis combines rule-based sentiment "
                f"scoring with a machine learning classifier to provide a "
                f"comprehensive view of customer opinion."
            )
            elements.append(Paragraph(summary_text, body_style))
            elements.append(Spacer(1, 0.5 * cm))

            # --- Statistics table ---
            elements.append(Paragraph("Summary Statistics", heading_style))
            stat_rows = [
                ["Metric", "Value"],
                ["Total Comments", str(stats.get("total", len(df)))],
                ["Positive Comments", str(stats.get("positive", 0))],
                ["Negative Comments", str(stats.get("negative", 0))],
                ["Neutral Comments", str(stats.get("neutral", 0))],
                ["Average Sentiment Score", f"{stats.get('avg_score', 0):.3f}"],
                ["Average Confidence", f"{stats.get('avg_confidence', 0):.1f}%"],
                ["Most Active Source", stats.get("top_source", "N/A")],
            ]
            table = Table(stat_rows, colWidths=[8 * cm, 8 * cm])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.6 * cm))

            # --- Charts ---
            elements.append(Paragraph("Sentiment Distribution", heading_style))
            pie_path = _make_pie_chart(stats, tmpdir)
            bar_path = _make_bar_chart(stats, tmpdir)
            elements.append(Image(pie_path, width=9 * cm, height=9 * cm))
            elements.append(Image(bar_path, width=12 * cm, height=8.4 * cm))
            elements.append(Spacer(1, 0.4 * cm))

            if "source" in df.columns and df["source"].nunique() > 1:
                elements.append(Paragraph("Mentions by Source", heading_style))
                source_path = _make_source_chart(df, tmpdir)
                elements.append(Image(source_path, width=13 * cm, height=9 * cm))

            # --- Word clouds ---
            if _WORDCLOUD_AVAILABLE:
                pos_wc = _make_wordcloud(positive_text, tmpdir, "pos_wc.png", "Greens")
                neg_wc = _make_wordcloud(negative_text, tmpdir, "neg_wc.png", "Reds")
                if pos_wc or neg_wc:
                    elements.append(PageBreak())
                    elements.append(Paragraph("Word Clouds", heading_style))
                    if pos_wc:
                        elements.append(Paragraph("Positive Comments", styles["Heading4"]))
                        elements.append(Image(pos_wc, width=14 * cm, height=7 * cm))
                        elements.append(Spacer(1, 0.3 * cm))
                    if neg_wc:
                        elements.append(Paragraph("Negative Comments", styles["Heading4"]))
                        elements.append(Image(neg_wc, width=14 * cm, height=7 * cm))

            # --- Recommendations ---
            if recommendations:
                elements.append(PageBreak())
                elements.append(Paragraph("Automated Recommendations", heading_style))
                for rec in recommendations:
                    elements.append(Paragraph(f"• {rec}", body_style))
                    elements.append(Spacer(1, 0.15 * cm))

            # --- Data sample table ---
            elements.append(PageBreak())
            elements.append(Paragraph("Sample of Analyzed Comments", heading_style))
            sample = df.head(20)
            table_data = [["ID", "Comment", "Source", "Sentiment", "Confidence"]]
            for _, row in sample.iterrows():
                comment_text = str(row.get("comment", ""))
                if len(comment_text) > 60:
                    comment_text = comment_text[:57] + "..."
                table_data.append([
                    str(row.get("id", "")),
                    comment_text,
                    str(row.get("source", "")),
                    str(row.get("sentiment", "")).capitalize(),
                    f"{row.get('confidence', 0):.0f}%" if "confidence" in row else "",
                ])
            data_table = Table(table_data, colWidths=[1.2 * cm, 8 * cm, 2.8 * cm, 2.5 * cm, 2.2 * cm])
            data_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            elements.append(data_table)

            doc.build(elements)

        log_event("EXPORT", f"Generated PDF report: {os.path.basename(output_path)}")
        return output_path
    except Exception as exc:
        raise ReportError(f"Failed to generate PDF report: {exc}")
