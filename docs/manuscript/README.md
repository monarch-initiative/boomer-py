# Boomer-Py Manuscript

This directory contains the manuscript and supplementary materials for the Boomer-Py system paper.

## Files

- `boomer-py-paper.md` - Main manuscript in Markdown format
- `bibliography.bib` - BibTeX bibliography
- `supplementary-materials.md` - Extended algorithms, experiments, and user guide
- `figures/` - Figures and diagrams (to be added)

## Building the Manuscript

### Convert to PDF using Pandoc

```bash
pandoc boomer-py-paper.md \
  --bibliography=bibliography.bib \
  --csl=ieee.csl \
  -o boomer-py-paper.pdf \
  --pdf-engine=xelatex
```

### Convert to LaTeX

```bash
pandoc boomer-py-paper.md \
  --bibliography=bibliography.bib \
  -o boomer-py-paper.tex
```

### Convert to Word

```bash
pandoc boomer-py-paper.md \
  --bibliography=bibliography.bib \
  -o boomer-py-paper.docx
```

## Abstract

The paper presents Boomer-Py, a Python implementation of Bayesian OWL Ontology MErgER (BOOMER), which performs probabilistic reasoning over ontological knowledge bases with uncertainty. Key contributions include:

1. **Graph-based partitioning algorithm** using strongly connected components
2. **Adaptive clique management** for computational tractability
3. **Efficient search implementation** with probabilistic pruning
4. **Flexible architecture** supporting multiple reasoning backends

## Citation

If you use Boomer-Py in your research, please cite:

```bibtex
@article{mungall2024boomerpy,
  title={Boomer-Py: A Python Implementation of Bayesian Ontology Reasoning with Scalable Graph Partitioning},
  author={Mungall, Christopher J.},
  journal={arXiv preprint},
  year={2024}
}
```

## Contact

Christopher J. Mungall
Environmental Genomics and Systems Biology Division
Lawrence Berkeley National Laboratory
Email: cjm@berkeleybop.org