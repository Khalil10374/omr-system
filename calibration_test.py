"""
OMR Pre-Printed Paper Alignment & Calibration Test Generator
Prints a sample test PDF with precision registration crosshairs and box outlines
to verify exact fit onto previously printed OMR sheets.
"""

import os
import fitz
import omr_pdf_overlay_system
import omr_qr_engine

def generate_calibration_sheet(
    template_path: str = "omr_template.pdf",
    output_path: str = "omr_calibration_test.pdf",
    sample_roll: str = "2512100001",
    offset_x_mm: float = 0.2,
    offset_y_mm: float = 0.8
):
    """
    Creates a 2-page test PDF:
    Page 1: Exact overlay-only codes (pure black on blank page) for feeding pre-printed paper into the printer.
    Page 2: Same codes with delicate 0.3pt box outline guides & center crosshairs to check alignment on a light table.
    """
    doc = fitz.open(template_path)
    rect = doc[0].rect
    doc.close()

    out_doc = fitz.open()

    # --- Page 1: Standard Overlay Test (Print this directly onto 1 pre-printed sheet) ---
    p1 = out_doc.new_page(width=rect.width, height=rect.height)
    roll_val = int(sample_roll)
    b32 = f"{roll_val:032b}"
    omr_pdf_overlay_system.apply_codes_to_pdf_page(
        p1,
        binary_str=b32,
        roll_number=sample_roll,
        clean_background=False,
        offset_x_mm=offset_x_mm,
        offset_y_mm=offset_y_mm,
        show_alignment_marks=False
    )
    # Add top banner note
    p1.insert_text(
        fitz.Point(30, 25),
        f"[TEST PAGE 1] Pre-Printed Overlay Test | Roll: {sample_roll} | Offset X: {offset_x_mm}mm, Y: {offset_y_mm}mm",
        fontname="helv",
        fontsize=8,
        color=(0.2, 0.2, 0.2)
    )

    # --- Page 2: Precision Calibration with Guides & Crosshairs ---
    p2 = out_doc.new_page(width=rect.width, height=rect.height)
    omr_pdf_overlay_system.apply_codes_to_pdf_page(
        p2,
        binary_str=b32,
        roll_number=sample_roll,
        clean_background=False,
        offset_x_mm=offset_x_mm,
        offset_y_mm=offset_y_mm,
        show_alignment_marks=True
    )
    p2.insert_text(
        fitz.Point(30, 25),
        f"[TEST PAGE 2] Alignment Guide with Crosshairs (Hold against light to inspect pre-printed box borders)",
        fontname="helv",
        fontsize=8,
        color=(0.8, 0.1, 0.1)
    )

    # Add millimeter ruler markers on the left and top edge to easily measure shift
    shape = p2.new_shape()
    pt_mm = 72.0 / 25.4
    # Vertical ruler (every 5mm on left edge)
    for mm in range(10, 270, 5):
        y_pos = mm * pt_mm
        tick_w = 6 if mm % 10 == 0 else 3
        shape.draw_line(fitz.Point(10, y_pos), fitz.Point(10 + tick_w, y_pos))
        if mm % 20 == 0:
            shape.insert_text(fitz.Point(18, y_pos + 3), f"{mm}mm", fontsize=6, color=(0.4, 0.4, 0.4))

    # Horizontal ruler (every 5mm on top edge)
    for mm in range(10, 210, 5):
        x_pos = mm * pt_mm
        tick_h = 6 if mm % 10 == 0 else 3
        shape.draw_line(fitz.Point(x_pos, 35), fitz.Point(x_pos, 35 + tick_h))
        if mm % 20 == 0:
            shape.insert_text(fitz.Point(x_pos - 6, 48), f"{mm}mm", fontsize=6, color=(0.4, 0.4, 0.4))

    shape.finish(color=(0.5, 0.5, 0.5), width=0.4)
    shape.commit()

    out_doc.save(output_path)
    out_doc.close()
    print(f"Calibration test sheet generated: {output_path}")
    return output_path

if __name__ == '__main__':
    generate_calibration_sheet()
