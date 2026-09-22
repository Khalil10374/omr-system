"""
OMR PDF Exact Coordinate Overlay System
Fits OMR Timing Barcode Squares & QR Codes directly onto the Madrasah / DPE Board PDF.
Optimized for high-speed industrial printing and pre-printed paper overlays.
"""

import os
import io
import fitz  # PyMuPDF
from typing import List, Optional, Tuple
import omr_qr_engine

# --- Master Coordinates for Primary Madrasah Board Template (612.79 x 793.11 pt) ---
MASTER_BOX_Y_COORDS = [66.435, 330.948, 619.504]
MASTER_BIT_CENTERS_X = [
    115.563, 127.569, 139.575, 151.580, 163.586, 175.618, 187.688, 199.603,
    211.609, 223.614, 235.620, 247.626, 259.631, 271.637, 283.643, 295.649,
    307.655, 319.660, 331.665, 343.671, 355.677, 367.683, 379.689, 391.695,
    403.700, 415.706, 427.711, 439.717, 451.723, 463.729, 475.735, 487.740
]

MASTER_QR1_RECT = fitz.Rect(118.309, 179.836, 160.814, 222.341)
MASTER_QR2_RECT = fitz.Rect(319.218, 453.985, 361.723, 496.490)
MASTER_QR3_RECT = fitz.Rect(535.0, 632.0, 577.5, 674.5)

# --- Legacy Fallback Coordinates (812 x 976 pt) ---
LEGACY_BOX_Y_COORDS = [178.509, 443.022, 731.578]
LEGACY_BIT_CENTERS_X = [261.698 + i * 12.0057 for i in range(32)]
LEGACY_QR1_RECT = fitz.Rect(264.444, 291.907, 306.949, 334.411)
LEGACY_QR2_RECT = fitz.Rect(465.354, 566.055, 507.859, 608.560)
LEGACY_QR3_RECT = fitz.Rect(658.0, 706.0, 700.5, 748.5)

PT_PER_MM = 72.0 / 25.4  # ~2.83465 points per mm


def get_template_coordinates(page: fitz.Page, offset_x_pt: float = 0.0, offset_y_pt: float = 0.0) -> dict:
    """
    Returns exact coordinate dictionary matching the page size, with optional offsets.
    """
    rect = page.rect
    is_master = rect.width < 700

    if is_master:
        base_box_y = MASTER_BOX_Y_COORDS
        base_bit_x = MASTER_BIT_CENTERS_X
        qr1 = MASTER_QR1_RECT
        qr2 = MASTER_QR2_RECT
        qr3 = MASTER_QR3_RECT
        sq_half = 4.8  # Increased from 3.2 to 4.8 pt (3.39 mm) to fully cover the 3.2mm circle
        roll_p = fitz.Point(475, 29)
    else:
        base_box_y = LEGACY_BOX_Y_COORDS
        base_bit_x = LEGACY_BIT_CENTERS_X
        qr1 = LEGACY_QR1_RECT
        qr2 = LEGACY_QR2_RECT
        qr3 = LEGACY_QR3_RECT
        sq_half = 5.2
        roll_p = fitz.Point(680, 115)

    # Apply offsets
    box_y = [y + offset_y_pt for y in base_box_y]
    bit_centers_x = [x + offset_x_pt for x in base_bit_x]
    qr1_shifted = fitz.Rect(qr1.x0 + offset_x_pt, qr1.y0 + offset_y_pt, qr1.x1 + offset_x_pt, qr1.y1 + offset_y_pt)
    qr2_shifted = fitz.Rect(qr2.x0 + offset_x_pt, qr2.y0 + offset_y_pt, qr2.x1 + offset_x_pt, qr2.y1 + offset_y_pt)
    qr3_shifted = fitz.Rect(qr3.x0 + offset_x_pt, qr3.y0 + offset_y_pt, qr3.x1 + offset_x_pt, qr3.y1 + offset_y_pt)
    roll_shifted = fitz.Point(roll_p.x + offset_x_pt, roll_p.y + offset_y_pt)

    return {
        'box_y': box_y,
        'bit_centers_x': bit_centers_x,
        'qr1_rect': qr1_shifted,
        'qr2_rect': qr2_shifted,
        'qr3_rect': qr3_shifted,
        'sq_half': sq_half,
        'roll_pos': roll_shifted
    }


def generate_qr_bytes(payload: str) -> bytes:
    """Generates PNG image bytes for QR code in memory without writing to disk."""
    qr_img = omr_qr_engine.generate_qr_image(payload)
    buf = io.BytesIO()
    qr_img.save(buf, format='PNG')
    return buf.getvalue()


def apply_codes_to_pdf_page(
    page: fitz.Page,
    binary_str: str,
    include_qr3: bool = False,
    roll_number: Optional[str] = None,
    clean_background: bool = False,
    offset_x_mm: float = 0.0,
    offset_y_mm: float = 0.0,
    show_alignment_marks: bool = False
):
    """
    Overlays the exact 32-bit timing barcode squares and QR codes onto a PDF page.
    - Uses in-memory image streaming (zero disk I/O).
    - Supports micro millimeter offset shifts for press alignment.
    - clean_background: True for full-sheet overlay, False for pre-printed paper.
    """
    b32 = omr_qr_engine.normalize_binary32(binary_str)
    hex_suffix = omr_qr_engine.calculate_hex_suffix(b32)
    qr_payload = b32[:31] + hex_suffix

    # Convert mm offset to points
    offset_x_pt = offset_x_mm * PT_PER_MM
    offset_y_pt = offset_y_mm * PT_PER_MM

    coords = get_template_coordinates(page, offset_x_pt, offset_y_pt)

    # 1. Clean background only if requested (full sheet mode)
    if clean_background:
        shape_clean = page.new_shape()
        shape_clean.draw_rect(coords['qr1_rect'])
        shape_clean.finish(fill=(1, 1, 1), color=(1, 1, 1))
        shape_clean.draw_rect(coords['qr2_rect'])
        shape_clean.finish(fill=(1, 1, 1), color=(1, 1, 1))
        if include_qr3 and coords.get('qr3_rect'):
            shape_clean.draw_rect(coords['qr3_rect'])
            shape_clean.finish(fill=(1, 1, 1), color=(1, 1, 1))
        shape_clean.commit()

    # 2. Fast In-Memory QR insertion
    qr_bytes = generate_qr_bytes(qr_payload)
    page.insert_image(coords['qr1_rect'], stream=qr_bytes)
    page.insert_image(coords['qr2_rect'], stream=qr_bytes)
    if include_qr3 and coords.get('qr3_rect'):
        page.insert_image(coords['qr3_rect'], stream=qr_bytes)

    # 3. Draw solid black vector squares where bit == '1' for all 3 timing boxes
    shape = page.new_shape()
    sq_half = coords['sq_half']

    for y in coords['box_y']:
        for i, bit in enumerate(b32):
            if bit == '1':
                cx = coords['bit_centers_x'][i]
                rect = fitz.Rect(cx - sq_half, y - sq_half, cx + sq_half, y + sq_half)
                shape.draw_rect(rect)
                shape.finish(fill=(0, 0, 0), color=None)

    # 4. Optional: Print Roll Number if provided
    if roll_number and coords.get('roll_pos'):
        shape.insert_text(coords['roll_pos'], str(roll_number), fontname="helv", fontsize=13, color=(0, 0, 0))

    # 5. Optional: Calibration alignment crosshairs
    if show_alignment_marks:
        mark_len = 8.0
        # Corner marks around QR1 and QR2
        for q_rect in [coords['qr1_rect'], coords['qr2_rect']]:
            # Top-left crosshair
            shape.draw_line(fitz.Point(q_rect.x0 - mark_len, q_rect.y0), fitz.Point(q_rect.x0 + mark_len, q_rect.y0))
            shape.draw_line(fitz.Point(q_rect.x0, q_rect.y0 - mark_len), fitz.Point(q_rect.x0, q_rect.y0 + mark_len))
            # Bottom-right crosshair
            shape.draw_line(fitz.Point(q_rect.x1 - mark_len, q_rect.y1), fitz.Point(q_rect.x1 + mark_len, q_rect.y1))
            shape.draw_line(fitz.Point(q_rect.x1, q_rect.y1 - mark_len), fitz.Point(q_rect.x1, q_rect.y1 + mark_len))
            shape.finish(color=(1, 0, 0), width=0.4)

    shape.commit()


def generate_overlaid_pdf(
    template_pdf_path: str,
    output_pdf_path: str,
    items: List[dict],
    mode: str = "overlay_only",  # "full" or "overlay_only"
    include_qr3: bool = False,
    offset_x_mm: float = 0.0,
    offset_y_mm: float = 0.0,
    show_alignment_marks: bool = False
):
    """
    Generates a ready-to-print multi-page PDF.
    items: list of dicts [{'roll': '...', 'binary': '...'}, ...]
    mode:
      'full': Combines master color PDF template with the codes.
      'overlay_only': Creates transparent/white pages with ONLY black codes for pre-printed paper.
    """
    if mode == "full":
        doc = fitz.open(template_pdf_path)
        out_doc = fitz.open()

        for item in items:
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=0, to_page=0)
            page = new_doc[0]

            b_str = item.get('binary')
            if not b_str:
                roll_val = int(item.get('roll', 0))
                b_str = f"{roll_val:032b}"

            apply_codes_to_pdf_page(
                page,
                b_str,
                include_qr3=include_qr3,
                roll_number=item.get('roll'),
                clean_background=True,
                offset_x_mm=offset_x_mm,
                offset_y_mm=offset_y_mm,
                show_alignment_marks=show_alignment_marks
            )
            out_doc.insert_pdf(new_doc)
            new_doc.close()

        out_doc.save(output_pdf_path, deflate=True)
        out_doc.close()
        doc.close()
    else:
        # overlay_only mode: ultra fast, blank background
        # Get page dimensions from template
        template_rect = fitz.Rect(0, 0, 612.786, 793.111)
        if os.path.exists(template_pdf_path):
            try:
                tdoc = fitz.open(template_pdf_path)
                template_rect = tdoc[0].rect
                tdoc.close()
            except Exception:
                pass

        out_doc = fitz.open()
        for item in items:
            page = out_doc.new_page(width=template_rect.width, height=template_rect.height)
            b_str = item.get('binary')
            if not b_str:
                roll_val = int(item.get('roll', 0))
                b_str = f"{roll_val:032b}"

            apply_codes_to_pdf_page(
                page,
                b_str,
                include_qr3=include_qr3,
                roll_number=item.get('roll'),
                clean_background=False,
                offset_x_mm=offset_x_mm,
                offset_y_mm=offset_y_mm,
                show_alignment_marks=show_alignment_marks
            )

        out_doc.save(output_pdf_path, deflate=True)
        out_doc.close()

    return output_pdf_path


if __name__ == '__main__':
    template = "omr_template.pdf"
    demo_items = [
        {'roll': '2512100077'},
        {'roll': '2512100078'}
    ]
    generate_overlaid_pdf(template, "output_print_ready.pdf", demo_items, mode="full", include_qr3=False)
    generate_overlaid_pdf(template, "output_black_overlay_only.pdf", demo_items, mode="overlay_only", include_qr3=False)
    print("Demo PDF generation complete.")
