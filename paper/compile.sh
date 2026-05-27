#!/bin/bash
# compile.sh - Compile the LQRL paper
# Requires: texlive-full or at least texlive-latex-base, texlive-science, texlive-bibtex-extra

set -e

PAPER_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PAPER_DIR"

echo "=== Compiling LQRL Paper ==="

# Clean previous build
latexmk -C 2>/dev/null || true

# Full compilation
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex 2>&1 | tee compile.log

# Check result
if [ -f main.pdf ]; then
    echo ""
    echo "=== Compilation Successful ==="
    ls -lh main.pdf
    pdfinfo main.pdf 2>/dev/null | grep -E "Pages:|Title:"
else
    echo ""
    echo "=== Compilation Failed ==="
    echo "Check compile.log for errors"
    exit 1
fi
