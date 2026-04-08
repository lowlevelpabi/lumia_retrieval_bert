import fitz
import os

pdf_path = r"uploads\6d8a6a82-d764-400d-8356-64922bb3f8f5_BARROWED_THESIS_OK1.pdf"
output_dir = "artifacts"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

doc = fitz.open(pdf_path)
page_num = 46
page = doc.load_page(page_num - 1)

pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
img_name = f"page_{page_num}_sample.png"
pix.save(os.path.join(output_dir, img_name))
print(f"Saved {img_name}")

# Print text blocks
blocks = page.get_text("blocks")
for b in blocks:
    print(f"BBox: {b[:4]} Text: {b[4].strip()}")

doc.close()
