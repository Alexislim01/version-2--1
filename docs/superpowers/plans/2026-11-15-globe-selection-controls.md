# FireAtlas Globe and Selection Implementation Plan

> **For agentic workers:** Implement the plan task by task using available tools and the user-authorized execution method. Track steps with checkboxes.

**Goal:** Implement the eight interaction requirements while preserving real observations and missing coverage.

**Architecture:** Retain React and the existing analytical engine. Use MapLibre GL JS globe projection and the existing Esri raster tiles; keep camera separate from selection. Normalize exact selected dates as merged inclusive intervals, share one applied filter state, and snapshot confirmed import scope.

**Tech Stack:** React, TypeScript, Vite, MapLibre GL JS, Python unittest, Playwright.

**Spec:** `docs/fireatlas-interactions-spec.md`

## Global Constraints
- Keep FireAtlas branding, navigation, exports, attribution, imagery provider and source provenance.
- Never share credentials or imported datasets; no map-key editor.
- Missing coverage stays missing. Completeness is a user declaration limited to its selected geometry and dates.
- Work on `feat/globe-selection-controls`; leave main unchanged.

## Review Focus
- Antimeridian and multipart selections must filter and navigate correctly.
- Async file reads cannot reuse a stale completeness declaration after scope changes.
- Noncontiguous dates must survive mode switching and share round trips exactly.
- Empty sensors/categories and unknown confidence must not create invented observations.
- Shared invalid geometry/camera/date values need bounded safe fallbacks.

### Task 1: Selection, filters, sharing, and coverage
**Files:** create `frontend/src/selection.ts`, `scripts/test-selection.ts`; modify `frontend/src/engine.ts`, `frontend/src/main.tsx`.
**Interfaces:** `Filters`, `DateInterval`, `normalizeIntervals`, `dateSelected`, `readSharedState`, `shareParams`, `confidenceAccepted`, `importScopeKey`, `assertImportConfirmed`.
- [x] Add executable assertion tests for exact intervals, URL validation, independent confidence, antimeridian geometry, and scoped coverage.
- [x] Implement validated state and analytical integration, preserving legacy links.
- [x] Require import confirmation in the UI and handler; capture geometry and dates before reading; reject stale declarations after reads.
- [x] Run `node --experimental-strip-types scripts/test-selection.ts` and existing Python tests.

### Task 2: Globe and geographic menu
**Files:** replace `frontend/src/MapView.tsx`; create `frontend/src/geography.ts`, `frontend/src/AreaPicker.tsx`, `frontend/public/data/countries.geojson`, `docs/geography.md`.
**Interfaces:** controlled `MapView` camera/basemap/grid; `AreaPicker` produces named geometry and wrapped bbox.
- [x] Use Natural Earth country boundaries and continent properties; document source and public-domain license.
- [x] Implement globe initialization, preserved Esri tiles, native geographic overlays, navigation, drawing/cancel and exit.
- [x] Implement anchored hover/click/touch/keyboard menu and GeoJSON upload entry.
- [x] Verify globe via browser and production build.

### Task 3: Date and filter interactions
**Files:** create `frontend/src/DatePicker.tsx`, `frontend/src/FilterControls.tsx`, `frontend/src/interactions.css`; modify `frontend/src/main.tsx`.
**Interfaces:** both date modes consume/produce `DateInterval[]`; `FilterControls` accepts applied or draft Filters and emits updated Filters.
- [x] Build exact date draft with years/months, partial checks, calendar drag and explicit range inputs, Apply/Cancel.
- [x] Compact sidebar and optional map controls share one applied state; label pending edits.
- [x] Preserve previous named area when drawing and restoring, including sharing.
- [x] Browser-check imports, both popovers, filter synchronization, globe, drawing and shared views.

### Task 4: Verification and delivery
**Files:** update `scripts/verify.mjs` as needed; create verification notes.
- [x] Run TypeScript/production build, Python tests, analytical assertions, existing UI checks and focused interaction tests.
- [x] Review diff and document limitations grounded in observed results.
- [x] Push the verified feature branch for PR review, leaving main unchanged. Repository access was granted and publication succeeded.

### Server-backed parity found during final review
**Files:** `backend/main.py`, `pipeline/core.py`, `tests/test_api.py`.
- [x] Reproduce `/api/dataset` prematurely removing low/native confidence records with a failing API test.
- [x] Add validity-only `clean(..., confidence=None)` for the browser dataset; retain existing analytical API cleaning defaults.
- [x] Run all 16 Python tests; preserve raw confidence so browser-side controls work equally with Docker/FastAPI and the bundled JSON.
