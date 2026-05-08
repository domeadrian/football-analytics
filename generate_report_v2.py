"""
Generate Final Project Report for Skillab Course - Lesson 11
Romanian Superliga 2025-2026 Complete Data Analysis

This is the main orchestrator that calls all modular parts:
  - report_data.py: Data loading & preparation
  - report_charts_1.py: Charts for pages 1-6
  - report_charts_2.py: Charts for pages 7-13
  - report_charts_3.py: Charts for pages 14-16
  - report_document_1.py: Word document sections 1-8
  - report_document_2.py: Word document sections 9-23

Run: python generate_report.py
Output: Football_Analytics_Report_Final.docx + report_images/
"""

from docx import Document
from docx.shared import Pt

from report_data import prepare_data
from report_charts_1 import generate_charts_part1
from report_charts_2 import generate_charts_part2
from report_charts_3 import generate_charts_part3
from report_charts_4 import generate_charts_part4
from report_document_1 import build_document_part1
from report_document_2 import build_document_part2
from report_document_3 import build_document_part3


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

    # Step 4: Save
    output_path = "Football_Analytics_Report_Final.docx"
    doc.save(output_path)
    print(f"\n=== Report Complete ===")
    print(f"Document: {output_path}")
    print(f"Charts: {total_charts} images in report_images/")
    print(f"Sections: 23 (covering all 19 dashboard pages)")
    print("Done!")


if __name__ == "__main__":
    main()
