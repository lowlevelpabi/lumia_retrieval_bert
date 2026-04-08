import fitz
import os
import base64
from io import BytesIO

# Paper 2 path
pdf_path = r"uploads\6d8a6a82-d764-400d-8356-64922bb3f8f5_BARROWED_THESIS_OK1.pdf"
output_dir = "artifacts"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

doc = fitz.open(pdf_path)

# Based on the snippet, the table was T_46_4 (Page 46)
page_num = 46
page = doc.load_page(page_num - 1)

# Find tables
tabs = page.find_tables()
if tabs.tables:
    for i, tab in enumerate(tabs.tables):
        bbox = fitz.Rect(tab.bbox)
        # Add a small margin for the caption which is usually just above
        # In current logic, caption is included in the clip if it matches.
        # Here we just want to show the table content.
        pix = page.get_pixmap(clip=bbox, matrix=fitz.Matrix(2, 2))
        img_name = f"sample_table_bug_{page_num}_{i}.png"
        pix.save(os.path.join(output_dir, img_name))
        print(f"Saved {img_name}")

doc.close()
