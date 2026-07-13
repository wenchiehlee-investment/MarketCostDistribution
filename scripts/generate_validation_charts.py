import os
import matplotlib.pyplot as plt
import numpy as np

# Set premium styling
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.sans-serif'] = ['Inter', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

output_dir = 'output'
os.makedirs(output_dir, exist_ok=True)

# Colors
C_V1 = '#3A86FF'
C_V2 = '#FF006E'
C_BOTH = '#8338EC'
C_BG = '#F8F9FA'

# 1. Venn Diagram of Signal Partitions (V1 vs. V2)
fig, ax = plt.subplots(figsize=(8, 6), facecolor=C_BG)
ax.set_facecolor(C_BG)

# Draw V1 Circle
c_v1 = plt.Circle((-1.0, 0.0), 2.2, color=C_V1, alpha=0.4, label='Model v1 (Total: 20,552)')
ax.add_patch(c_v1)
# Draw V2 Circle
c_v2 = plt.Circle((1.0, 0.0), 1.8, color=C_V2, alpha=0.4, label='Model v2 (Total: 12,959)')
ax.add_patch(c_v2)

# Add outline rings
r_v1 = plt.Circle((-1.0, 0.0), 2.2, color=C_V1, fill=False, linewidth=2)
ax.add_patch(r_v1)
r_v2 = plt.Circle((1.0, 0.0), 1.8, color=C_V2, fill=False, linewidth=2)
ax.add_patch(r_v2)

# Text Labels
plt.text(-2.0, 0.0, 'V1-only\n17,163\n(51.79% BR)', fontsize=13, fontweight='bold', ha='center', va='center', color='#1D2D44')
plt.text(1.8, 0.0, 'V2-only\n9,570\n(50.63% BR)', fontsize=13, fontweight='bold', ha='center', va='center', color='#1D2D44')
plt.text(0.0, 0.0, 'Both\n3,389\n(44.73% / 45.00% BR)', fontsize=12, fontweight='bold', ha='center', va='center', color='#4A0E4E')

ax.set_xlim(-4.0, 4.0)
ax.set_ylim(-3.0, 3.0)
ax.axis('off')
plt.title('Signal Partition Venn Diagram (A/B Test Signal Breakdown)', fontsize=15, fontweight='bold', pad=20, color='#1A1A1A')
plt.legend(loc='lower center', bbox_to_anchor=(0.5, -0.05), ncol=2, frameon=True, facecolor='white', edgecolor='none')
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'validation_venn_diagram.png'), dpi=300, facecolor=C_BG)
plt.close()

# 2. Out-of-Sample Threshold Sensitivity Curve
thresholds = [0.8, 0.9, 1.0, 1.1, 1.2]
low_group = [15.67, 17.04, 17.29, 17.98, 18.93]
high_group = [27.56, 26.00, 26.56, 26.00, 23.94]

fig, ax = plt.subplots(figsize=(9, 5.5), facecolor=C_BG)
ax.set_facecolor('white')

plt.plot(thresholds, high_group, marker='o', linewidth=3, color='#FF5A5F', label='High-Turnover Group (Turnover > Threshold)', markersize=8)
plt.plot(thresholds, low_group, marker='s', linewidth=2.5, color='#00A699', label='Low-Turnover Group (Turnover <= Threshold)', markersize=8)

# Formatting
plt.title('Out-of-Sample Threshold Sensitivity Analysis (2023-2026)', fontsize=14, fontweight='bold', pad=15, color='#222222')
plt.xlabel('Turnover Rate Split Threshold (% per day)', fontsize=11, labelpad=10)
plt.ylabel('OOS Excess Bounce Rate (Model v1 - VP Baseline, %)', fontsize=11, labelpad=10)
plt.xticks(thresholds, [f'{t:.1f}%' for t in thresholds])
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'+{y:.1f}%'))

# Grid & Spines
plt.grid(True, linestyle='--', alpha=0.5)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#CCCCCC')
ax.spines['bottom'].set_color('#CCCCCC')

# Highlight Stump split
plt.axvline(1.0049, color='#8E9AAF', linestyle=':', label='Optimal Stump split (1.0049%)', linewidth=2)

plt.legend(loc='best', frameon=True, facecolor='white', framealpha=0.9)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'oos_threshold_sensitivity.png'), dpi=300, facecolor=C_BG)
plt.close()

# 3. Path Sensitivity & Ranking Robustness Bar Chart
models = ['SMA 200', 'Rolling VWAP', 'Volume Profile', 'Cost Model v2', 'Cost Model v1']
worst = [41.26, 44.76, 48.22, 49.16, 50.62]
best = [44.15, 48.30, 52.18, 53.70, 55.47]
exclude = [41.04, 44.91, 48.69, 49.86, 51.54]

x = np.arange(len(models))
width = 0.25

fig, ax = plt.subplots(figsize=(10, 6), facecolor=C_BG)
ax.set_facecolor('white')

rects1 = ax.bar(x - width, worst, width, label='Worst-case (Stop Breach first)', color='#457B9D', alpha=0.95)
rects2 = ax.bar(x, best, width, label='Best-case (Target Touch first)', color='#E63946', alpha=0.95)
rects3 = ax.bar(x + width, exclude, width, label='Exclude (Discard same-day double touches)', color='#A8DADC', alpha=0.95)

# Formatting
ax.set_ylabel('5-Day Bounce Rate (%)', fontsize=11, labelpad=10)
ax.set_title('Path Ambiguity & Ranking Robustness Sensitivity Analysis', fontsize=14, fontweight='bold', pad=20, color='#1D3557')
ax.set_xticks(x)
ax.set_xticklabels(models, fontsize=10, fontweight='bold')
ax.set_ylim(35, 60)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0f}%'))

# Grid & Spines
plt.grid(True, axis='y', linestyle='--', alpha=0.5)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#CCCCCC')
ax.spines['bottom'].set_color('#CCCCCC')

# Legend
ax.legend(loc='upper left', frameon=True, facecolor='white', framealpha=0.9)

# Bar labels helper
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.1f}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=8, color='#333333')

autolabel(rects1)
autolabel(rects2)
autolabel(rects3)

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'path_sensitivity_comparison.png'), dpi=300, facecolor=C_BG)
plt.close()

print("All validation charts generated successfully.")
