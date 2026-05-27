#!/usr/bin/env python3
"""
Generate Table 1: Main results comparison table
"""
import sys
sys.path.insert(0, '.')

# Data from BCB experiments
# Note: Small sample sizes - more experiments needed for paper

table_data = """
\\begin{table}[t]
\\centering
\\caption{Main results on BigCodeBench with LQRL. β controls the weight of learning reward
in the Q-value update. Higher β encourages skills to learn from failure. Results show
success rate with sample size in parentheses.}
\\label{tab:main_results}
\\begin{tabular}{lcc}
\\toprule
\\textbf{Condition} & \\textbf{Success Rate} & \\textbf{Sample Size} \\\\
\\midrule
β = 0 (baseline) & 40.0\\% & 2/5 \\\\
β = 0.3 (LQRL) & 66.7\\% & 2/3 \\\\
\\bottomrule
\\end{tabular}
\\vspace{-0.3em}
\\footnotesize{\\textit{Note: Small sample sizes due to compute constraints.}}
\\end{table}
"""

with open('figures/TABLE_main_results.tex', 'w') as f:
    f.write(table_data)

print("Saved: figures/TABLE_main_results.tex")
