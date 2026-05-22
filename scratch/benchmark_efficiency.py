import os
import sys
import time
import matplotlib.pyplot as plt
import numpy as np

# Ensure Python can find the 'app' module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ocr_service import ocr_service

sample_dir = r"c:\Users\Maruf\Documents\BSCS-4A (2025)\Undergrad Thesis 1\Final Thesis System\Thesis Backend\sample_documents"
output_image = r"c:\Users\Maruf\Documents\BSCS-4A (2025)\Undergrad Thesis 1\Final Thesis System\Thesis Backend\scratch\system_efficiency.png"

# Filter for PDF files
pdfs = [f for f in os.listdir(sample_dir) if f.endswith(".pdf") and "TEST" not in f]

results = []

print(f"Starting Benchmark for {len(pdfs)} documents...")

for pdf_name in pdfs:
    pdf_path = os.path.join(sample_dir, pdf_name)
    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    
    print(f"Processing {pdf_name} ({file_size_mb:.2f} MB)...")
    
    start_time = time.time()
    try:
        # Measure the actual extraction time
        ocr_service.extract_metadata_sync(pdf_path, session_id="benchmark")
        end_time = time.time()
        
        duration = end_time - start_time
        results.append({
            "name": pdf_name,
            "size": file_size_mb,
            "time": duration
        })
        print(f"  Completed in {duration:.2f} seconds.")
    except Exception as e:
        print(f"  Failed: {e}")

# --- Plotting ---
if not results:
    print("No results to plot.")
    sys.exit(1)

# Sort by size for a cleaner line
results.sort(key=lambda x: x["size"])
sizes = [r["size"] for r in results]
times = [r["time"] for r in results]

plt.figure(figsize=(10, 6))
plt.plot(sizes, times, marker='o', linestyle='-', color='#2c3e50', linewidth=2, markersize=8, label='Processing Time')

# Add a trend line (Polynomial fit)
if len(sizes) > 1:
    z = np.polyfit(sizes, times, 1)
    p = np.poly1d(z)
    plt.plot(sizes, p(sizes), "r--", alpha=0.5, label='Efficiency Trend')

plt.title('System Processing Efficiency (OCR + IMRAD Extraction)', fontsize=14)
plt.xlabel('File Size (MB)', fontsize=12)
plt.ylabel('Time (Seconds)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend()

# Add Figure label
plt.figtext(0.5, 0.01, "Figure 9. Processing latency across various document sizes", 
            wrap=True, horizontalalignment='center', fontsize=12)

plt.tight_layout(rect=[0, 0.05, 1, 1])
plt.savefig(output_image, dpi=300)
print(f"\nSuccess! Efficiency graph saved to: {output_image}")
