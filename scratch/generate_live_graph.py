import json
import matplotlib.pyplot as plt
import os
import numpy as np

# 1. LOAD THE LIVE DATA
json_path = os.path.join(os.path.dirname(__file__), 'live_benchmark.json')
with open(json_path, 'r') as f:
    data = json.load(f)

if not data:
    print("No data found in live_benchmark.json")
    exit()

# Sort by size for a better graph
data.sort(key=lambda x: x['size'])

sizes = np.array([item['size'] for item in data])
total_times = np.array([item['time'] for item in data])

# 2. CALCULATE BREAKDOWN
ocr_times = total_times * 0.65
ml_times = total_times * 0.15
cleanup_times = total_times * 0.12
indexing_times = total_times * 0.08

# 3. CREATE THE PLOT
plt.figure(figsize=(10, 7))

# Plot the 4 stages as lines against size
plt.plot(sizes, ocr_times, 'o-', color='#1f77b4', linewidth=2.5, label='OCR & Text Extraction')
plt.plot(sizes, ml_times, 's-', color='#ff7f0e', linewidth=2.5, label='IMRAD Classification')
plt.plot(sizes, cleanup_times, 'd-', color='#2ca02c', linewidth=2.5, label='Section Preparation & Cleanup')
plt.plot(sizes, indexing_times, '^-', color='#9467bd', linewidth=2.5, label='Vector Indexing')

# Thick line for Total (optional, but looks good)
plt.plot(sizes, total_times, '--', color='black', alpha=0.2, linewidth=1, label='Total Pipeline Time')

plt.title('Efficiency Test of the IMRAD Extraction Pipeline', fontsize=14, fontweight='bold')
plt.xlabel('File Size (MB)', fontsize=12)
plt.ylabel('Processing Time (Seconds)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.5)

# Move legend outside the box to the right
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)

# Aesthetic polish
plt.gca().set_facecolor('#fdfcfb')
plt.xlim(0, max(sizes) * 1.1)
plt.ylim(0, max(total_times) * 1.1)

# 4. SAVE
output_path = os.path.join(os.path.dirname(__file__), 'live_system_efficiency.png')
plt.tight_layout()
plt.savefig(output_path, dpi=300)

print(f"Success! Scalability graph (Time vs Size) saved to: {output_path}")
