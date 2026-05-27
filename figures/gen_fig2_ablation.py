#!/usr/bin/env python3
"""
Generate Fig 2: Beta ablation bar chart on BigCodeBench
Data source: test/bcb/test_results.json (beta=0.3 result)
            refine-logs/FINAL_PROPOSAL.md (beta=0 result: 40% on 5 tasks)
"""
import sys
sys.path.insert(0, '.')
from figures.paper_plot_style import *

# Data from BCB experiments
# beta=0: 2/5 = 40% (from FINAL_PROPOSAL.md)
# beta=0.3: 2/3 = 66.7% (from test/bcb/test_results.json)
# NOTE: Small sample sizes - more experiments needed for paper

beta_values = ['β=0\n(baseline)', 'β=0.3\n(LQRL)']
success_rates = [40.0, 66.7]
sample_sizes = ['2/5', '2/3']

fig, ax = plt.subplots(1, 1, figsize=(5, 3.5))

bars = ax.bar(beta_values, success_rates, color=[COLORS[0], COLORS[2]], width=0.5)

# Add value labels and sample sizes
for bar, rate, n in zip(bars, success_rates, sample_sizes):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, height + 1.5,
            f'{rate:.1f}%', ha='center', va='bottom', fontsize=11)
    ax.text(bar.get_x() + bar.get_width()/2, height/2,
            f'n={n}', ha='center', va='center', fontsize=9, color='white')

ax.set_ylabel('Success Rate (%)')
ax.set_ylim(0, 100)
ax.set_title('LQRL β-Ablation on BigCodeBench')

# Add horizontal grid for readability
ax.yaxis.grid(True, linestyle='--', alpha=0.3)
ax.set_axisbelow(True)

save_fig(fig, 'fig2_ablation')
plt.close()
