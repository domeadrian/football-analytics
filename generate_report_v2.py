"""
Generate Final Project Report for Skillab Course - Lesson 11
Romanian Superliga 2025-2026 Complete Data Analysis

This is the main orchestrator that calls all modular parts:
  - report_data.py: Data loading & preparation
  - report_charts_1.py: Charts for pages 1-6
  - report_charts_2.py: Charts for pages 7-13
  - report_charts_3.py: Charts for pages 14-16
  - report_charts_4.py: Charts for Romanian deep-dive
  - report_document_1.py: Word document sections 1-8
  - report_document_2.py: Word document sections 9-23
  - report_document_3.py: Word document sections 24-29

Run: python generate_report_v2.py
Output: Football_Analytics_Report_Final.docx + report_images/
"""

from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from report_data import prepare_data
from report_charts_1 import generate_charts_part1
from report_charts_2 import generate_charts_part2
from report_charts_3 import generate_charts_part3
from report_charts_4 import generate_charts_part4
from report_document_1 import build_document_part1
from report_document_2 import build_document_part2
from report_document_3 import build_document_part3

# ---- Figure captions in order of appearance ----
FIGURE_CAPTIONS = [
    "Full League Points Distribution",
    "Championship Playoff Standings",
    "Relegation Playout Standings",
    "Cross-League Top 3 Comparison",
    "Match Outcome Distribution",
    "Goals per Match Distribution",
    "Scoreline Frequency Heatmap",
    "Monthly Goals Trend",
    "Championship Probability – Monte Carlo Simulation",
    "Points Distribution Range (Box Plot)",
    "Top 3 Contenders – Win Probability Gauges",
    "European Goals Comparison by League",
    "League Competitiveness Index",
    "League Strength vs Market Value",
    "Age Distribution Across All Leagues",
    "Position Distribution",
    "Nationality Distribution – Top 20",
    "Wonderkid Radar – Top U21 Prospects",
    "Age Distribution by Position (Violin Plot)",
    "Scouting Database Coverage by League",
    "Attack vs Defense Quadrant Analysis",
    "Win/Draw/Loss Composition per Team",
    "Efficiency Matrix – PPG vs Goal Difference",
    "Top 6 Radar Comparison",
    "Goal Difference Ranking",
    "Transfer Pool Analysis by Position",
    "Young Talent Pipeline (U23)",
    "Squad Age Profile by Club",
    "Injury Risk Assessment",
    "U21 Investment per Club",
    "Player Development Curve",
    "Points-per-Value Financial Efficiency",
    "Money vs Performance Correlation",
    "Budget Tier Classification",
    "ELO Power Rating",
    "Season Points Projection",
    "Win Rate Indicator",
    "K-Means Performance Clustering",
    "Random Forest – Feature Importance",
    "Linear Regression – Points Prediction",
    "Expected Goals – Poisson Model",
    "xPoints Overperformance Analysis",
    "Consistency Index – Shannon Entropy",
    "Venue Goals Analysis",
    "Round-by-Round Trends",
    # Romanian deep-dive figures
    "Romanian Liga I – Squad Age Profile per Club",
    "Position Coverage Heatmap",
    "Romanian vs Foreign Players per Club",
    "Top 20 Most Valuable Players in Liga I",
    "Home vs Away Goal Efficiency – Butterfly Chart",
    "Squad Value Composition by Position",
    "Season Form Heatmap – Round by Round",
    "Top 6 Clubs – Strength Radar Comparison",
]

# ---- Table captions in order of appearance ----
TABLE_CAPTIONS = [
    "Report Scope Summary",
    "Key Performance Indicators",
    "Primary Data Sources",
    "Statistical Methods",
    "Analysis Framework Levels",
    "Championship Playoff – Detailed Statistics",
    "Relegation Playout – Detailed Statistics",
    "Player Database Summary Statistics",
    "Scouting Platform Tools",
    "ML Model Validation Summary",
    "Dashboard Module Overview",
    "Technical Stack",
    "Grading Criteria Coverage",
]


def _make_caption_p(text, center=False, italic=True, size_halfpts=18):
    """Create an OxmlElement <w:p> with formatted caption text."""
    p_elem = OxmlElement('w:p')
    pPr = OxmlElement('w:pPr')
    if center:
        jc = OxmlElement('w:jc')
        jc.set(qn('w:val'), 'center')
        pPr.append(jc)
    # Spacing: small space after caption
    spacing = OxmlElement('w:spacing')
    spacing.set(qn('w:after'), '120')
    pPr.append(spacing)
    p_elem.append(pPr)
    # Run with formatting
    run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    if italic:
        rPr.append(OxmlElement('w:i'))
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), str(size_halfpts))
    rPr.append(sz)
    szCs = OxmlElement('w:szCs')
    szCs.set(qn('w:val'), str(size_halfpts))
    rPr.append(szCs)
    run.append(rPr)
    t = OxmlElement('w:t')
    t.set(qn('xml:space'), 'preserve')
    t.text = text
    run.append(t)
    p_elem.append(run)
    return p_elem


def add_captions(doc):
    """Post-process: add Figure X / Table X captions to all images and tables."""
    body = doc.element.body
    fig_count = 0
    tbl_count = 0

    for element in list(body):
        # Figures: paragraphs containing inline drawings
        if element.tag == qn('w:p'):
            drawings = element.findall('.//' + qn('wp:inline'))
            if drawings:
                fig_count += 1
                caption_text = FIGURE_CAPTIONS[fig_count - 1] if fig_count <= len(FIGURE_CAPTIONS) else ""
                label = f"Figure {fig_count}: {caption_text}" if caption_text else f"Figure {fig_count}"
                caption_p = _make_caption_p(label, center=True)
                element.addnext(caption_p)

        # Tables
        elif element.tag == qn('w:tbl'):
            tbl_count += 1
            caption_text = TABLE_CAPTIONS[tbl_count - 1] if tbl_count <= len(TABLE_CAPTIONS) else ""
            label = f"Table {tbl_count}: {caption_text}" if caption_text else f"Table {tbl_count}"
            caption_p = _make_caption_p(label, center=False)
            element.addprevious(caption_p)

    return fig_count, tbl_count


def main():
    # Step 1: Load all data
    data = prepare_data()

    # Step 2: Generate all charts (35+ total)
    print("\n=== Generating Charts ===")
    charts1 = generate_charts_part1(data)
    charts2 = generate_charts_part2(data)
    charts3 = generate_charts_part3(data)
    charts4 = generate_charts_part4(data)
    total_charts = len(charts1) + len(charts2) + len(charts3) + len(charts4)
    print(f"\nTotal charts generated: {total_charts}")

    # Step 3: Build Word document
    print("\n=== Building Word Document ===")
    doc = Document()

    # Set default font
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)

    # Build both parts
    print("  Building sections 1-8...")
    doc = build_document_part1(doc, data)
    print("  Building sections 9-23...")
    doc = build_document_part2(doc, data)
    print("  Building sections 24-29 (Romanian Deep Dive)...")
    doc = build_document_part3(doc, data)

    # Step 4: Post-process - add figure & table captions
    print("  Adding figure/table captions...")
    fig_n, tbl_n = add_captions(doc)
    print(f"    {fig_n} figure captions, {tbl_n} table captions added")

    # Step 5: Save
    output_path = "Football_Analytics_Report_Final.docx"
    try:
        doc.save(output_path)
    except PermissionError:
        output_path = "Football_Analytics_Report_Final_v2.docx"
        doc.save(output_path)
        print(f"  (Original file locked, saved as {output_path})")
    print(f"\n=== Report Complete ===")
    print(f"Document: {output_path}")
    print(f"Charts: {total_charts} images in report_images/")
    print(f"Sections: 29 (covering all 19 dashboard pages + Romanian deep dive)")
    print("Done!")


if __name__ == "__main__":
    main()
