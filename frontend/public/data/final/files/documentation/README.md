# docs — how the system works and how far to trust it

| File | Language | Use |
|---|---|---|
| `System_Explanation_EN.pdf` | English | For the Space Apps submission and judges |
| `系统说明_中文.pdf` | 中文 | For the team |
| `System_Explanation_EN.md`, `系统说明_中文.md` | — | Editable sources of the two PDFs (same content) |

Both documents contain, in this order:
1. **At a glance** — what goes in, what comes out, how accurate each output is, and what it can be trusted for
2. The problem (why MODIS and VIIRS counts differ)
3. Data (NASA FIRMS files, cleaning rules)
4. Theory (pixel size, missed small fires, viewing angle, day/night)
5. Workflow and functions (gridding, multipliers, the Fusion G1 random forest, the leave-one-year-out test)
6. Accuracy (every held-out year, all methods, Malaysia and Indonesia)
7. Point-level synthetic VIIRS (method and test)
8. The converted 2003–2011 record and the 2011/2012 continuity check
9. Limitations, figures and references
