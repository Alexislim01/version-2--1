# GitHub Pages Implementation Plan

> **For agentic workers:** Implement the plan task by task using available tools and the user-authorized execution method. Track steps with checkboxes.

**Goal:** Host the browser version of FireAtlas on GitHub Pages.
**Architecture:** Build Vite with the repository base path and upload its static output with GitHub Actions. Keep root-path local/FastAPI builds working by default.
**Tech Stack:** Vite, React, GitHub Actions, GitHub Pages.
**Spec:** User requests GitHub hosting for testing, without Vercel.

## Global Constraints
- Preserve observations, imports, imagery, share links, and existing server configuration.
- GitHub Pages serves static files and cannot run FastAPI or ingestion jobs.
- Submit changes on a branch for review; do not merge main.

## Review Focus
- Data URLs must respect the repository subdirectory.
- Existing root-path hosting must remain supported.
- Generated shared links must retain the page pathname.
- Pages must use GitHub Actions as its configured source.
- No credentials or runtime datasets are added to the workflow.

### Task 1: Base paths and deployment
**Files:** `.github/workflows/pages.yml`, `vite.config.js`, `frontend/src/main.tsx`, `frontend/src/MapView.tsx`, `frontend/src/vite-env.d.ts`, `README.md`.
**Interfaces:** `FIREATLAS_BASE_PATH` selects Vite's public base; `import.meta.env.BASE_URL` prefixes bundled data.
- [x] Build and test selection logic with the GitHub Pages repository base.
- [x] Browser-check the actual repository subpath, including data, imagery and shared links.
- [x] Document Pages setup and static-hosting limits.
- [ ] Push the branch and open a PR.
