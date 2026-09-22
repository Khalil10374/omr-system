"""
OMR Barcode & QR Code Engine
Specialized generator for Bangladesh Primary Education (DPE) & Academic OMR Sheets.
"""

import os
import io
import qrcode
import qrcode.image.svg
from PIL import Image, ImageDraw, ImageFont
from typing import Optional


# The OMR strip has 32 positions. The first and last positions are reserved
# as fixed black markers; the 30 positions between them carry the unique ID.
OMR_TOTAL_BITS = 32
OMR_PAYLOAD_BITS = 30
MAX_UNIQUE_CODE_ID = (1 << OMR_PAYLOAD_BITS) - 1


def build_fixed_marker_binary(unique_code_id: int) -> str:
    """Return a 32-bit OMR value with black marker bits at both ends."""
    try:
        value = int(unique_code_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Unique code ID must be an integer.") from exc

    if not 0 <= value <= MAX_UNIQUE_CODE_ID:
        raise ValueError(
            f"Unique code ID must be between 0 and {MAX_UNIQUE_CODE_ID:,}."
        )

    return f"1{value:0{OMR_PAYLOAD_BITS}b}1"


def normalize_binary32(binary_str: str) -> str:
    """Normalize any binary input to 32 bits and force both marker bits to 1."""
    value = str(binary_str).strip()
    if not value or any(bit not in "01" for bit in value):
        raise ValueError("Binary code must contain only 0 and 1 characters.")

    raw = value.ljust(OMR_TOTAL_BITS, "0")[:OMR_TOTAL_BITS]
    return f"1{raw[1:OMR_TOTAL_BITS - 1]}1"

def calculate_hex_suffix(binary_str: str) -> str:
    """
    Takes a 31 or 32-bit binary string and calculates the exact 8-character hex suffix.
    Algorithm:
    1. Pad to 32 bits with '0' if needed.
    2. Split into 4 bytes (8 bits each).
    3. Reverse the bits of each byte (LSB to MSB).
    4. Format each as a 2-digit uppercase hex.
    5. Concatenate in Little-Endian byte order (Byte 3 + Byte 2 + Byte 1 + Byte 0).
    """
    b32 = normalize_binary32(binary_str)
    bytes_list = [b32[i:i+8] for i in range(0, 32, 8)]
    rev_bytes = [f'{int(b[::-1], 2):02X}' for b in bytes_list]
    return f'{rev_bytes[3]}{rev_bytes[2]}{rev_bytes[1]}{rev_bytes[0]}'

def number_to_binary32(number: int) -> str:
    """Converts an integer to a 32-bit binary string."""
    return f'{number:032b}'

def generate_qr_image(payload: str, box_size: int = 10, border: int = 2) -> Image.Image:
    """Generates a PIL Image of the QR code."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border
    )
    qr.add_data(payload)
    qr.make(fit=True)
    return qr.make_image(fill_color='black', back_color='white').convert('RGB')

def generate_qr_svg(payload: str, box_size: int = 10, border: int = 2) -> str:
    """Generates SVG string of the QR code."""
    factory = qrcode.image.svg.SvgPathImage
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
        image_factory=factory
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image()
    stream = io.BytesIO()
    img.save(stream)
    return stream.getvalue().decode('utf-8')

def generate_omr_barcode_svg(binary_str: str, width: int = 800, height: int = 110, add_alignment_bars: bool = True) -> str:
    """Generates scalable vector (SVG) for the OMR timing strip with perfect typography."""
    b32 = normalize_binary32(binary_str)
    margin_x = 42 if add_alignment_bars else 20
    box_x1 = margin_x
    box_y1 = 15
    box_x2 = width - margin_x
    box_y2 = height - 15
    box_w = box_x2 - box_x1
    box_h = box_y2 - box_y1

    start_x = box_x1 + 25
    available_w = box_w - 50
    spacing = available_w / (len(b32) - 1)
    sym_y = box_y1 + 45
    sq_size = 13.5
    r = 5.5

    symbols = []
    for i, bit in enumerate(b32):
        cx = start_x + i * spacing
        cy = sym_y
        if bit == '1':
            symbols.append(f'<rect x="{cx - sq_size/2:.2f}" y="{cy - sq_size/2:.2f}" width="{sq_size:.2f}" height="{sq_size:.2f}" fill="#111111" />')
        else:
            symbols.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="none" stroke="#222222" stroke-width="2" />')

    side_bars = ""
    if add_alignment_bars:
        side_bars = f'''
        <rect x="12" y="10" width="8" height="{height - 20}" fill="black" />
        <rect x="{width - 20}" y="10" width="8" height="{height - 20}" fill="black" />
        '''

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
    <rect width="{width}" height="{height}" fill="#ffffff" />
    {side_bars}
    <!-- Container Box -->
    <rect x="{box_x1}" y="{box_y1}" width="{box_w}" height="{box_h}" fill="#f5cfd5" stroke="#777777" stroke-width="1" />
    <!-- Notice Text in Bengali -->
    <text x="{width / 2}" y="{box_y1 + 20}" font-family="'Kalpurush', 'Nirmala UI', 'SolaimanLipi', 'Hind Siliguri', sans-serif" font-size="15" font-weight="600" fill="#c01828" text-anchor="middle">এই বক্সের মধ্যে কোনো দাগ দেওয়া যাবে না</text>
    <!-- Symbols -->
    {''.join(symbols)}
</svg>'''
    return svg_content

def generate_omr_barcode_png(binary_str: str, width: int = 800, height: int = 110, add_alignment_bars: bool = True) -> Image.Image:
    """Generates PNG raster image of the OMR barcode."""
    b32 = normalize_binary32(binary_str)
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    margin_x = 42 if add_alignment_bars else 20
    box_x1 = margin_x
    box_y1 = 15
    box_x2 = width - margin_x
    box_y2 = height - 15

    if add_alignment_bars:
        draw.rectangle([12, 10, 20, height - 10], fill='black')
        draw.rectangle([width - 20, 10, width - 12, height - 10], fill='black')

    draw.rectangle([box_x1, box_y1, box_x2, box_y2], fill='#f5cfd5', outline='#737373', width=1)

    # Fonts
    bangla_text = 'এই বক্সের মধ্যে কোনো দাগ দেওয়া যাবে না'
    font_path = r'C:\Windows\Fonts\kalpurush.ttf'
    if not os.path.exists(font_path):
        font_path = r'C:\Windows\Fonts\Nirmala.ttc'

    try:
        font = ImageFont.truetype(font_path, 16)
        bbox = draw.textbbox((0, 0), bangla_text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((width - tw) // 2, box_y1 + 6), bangla_text, fill='#c01828', font=font)
    except Exception:
        draw.text(((width - 250) // 2, box_y1 + 6), bangla_text, fill='#c01828')

    start_x = box_x1 + 25
    available_w = (box_x2 - box_x1) - 50
    spacing = available_w / (len(b32) - 1)
    sym_y = box_y1 + 45
    sq_size = 13
    r = 5.5

    for i, bit in enumerate(b32):
        cx = start_x + i * spacing
        cy = sym_y
        if bit == '1':
            draw.rectangle([cx - sq_size/2, cy - sq_size/2, cx + sq_size/2, cy + sq_size/2], fill='black')
        else:
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline='#222222', width=2)

    return img

def create_full_omr_code_pair(binary_or_id: str, unique_code_id: Optional[int] = None):
    """
    Creates both the Barcode and QR code for a given input.
    Input can be a 31/32 bit binary string, or an integer/serial.
    For production generation, pass a unique_code_id so the serial number can
    remain independent from the 30-bit barcode payload.
    Returns:
        dict with binary_32, hex_suffix, qr_payload, barcode_png, qr_png, barcode_svg, qr_svg
    """
    input_value = str(binary_or_id).strip()

    if unique_code_id is not None:
        binary_32 = build_fixed_marker_binary(unique_code_id)
    elif all(c in '01' for c in input_value) and len(input_value) >= 24:
        binary_32 = normalize_binary32(input_value)
    else:
        # It's an ID or integer
        try:
            val = int(input_value)
            binary_32 = normalize_binary32(number_to_binary32(val))
        except ValueError:
            # Hash or encode string into 32-bit
            import zlib
            val = zlib.crc32(input_value.encode('utf-8'))
            binary_32 = normalize_binary32(number_to_binary32(val))

    hex_suffix = calculate_hex_suffix(binary_32)
    qr_payload = binary_32[:31] + hex_suffix

    barcode_png = generate_omr_barcode_png(binary_32)
    qr_png = generate_qr_image(qr_payload)
    barcode_svg = generate_omr_barcode_svg(binary_32)
    qr_svg = generate_qr_svg(qr_payload)

    return {
        'binary_32': binary_32,
        'unique_code_id': unique_code_id,
        'hex_suffix': hex_suffix,
        'qr_payload': qr_payload,
        'barcode_png': barcode_png,
        'qr_png': qr_png,
        'barcode_svg': barcode_svg,
        'qr_svg': qr_svg
    }
