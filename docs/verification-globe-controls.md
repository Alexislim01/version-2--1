# Globe and selection verification

Verified on 15 November 2026 with Node 24, Python 3.12 and headless system Chromium at a local production preview. No production deployment or merge was performed.

## Completed checks

- Production TypeScript check and Vite build (`npm run build`) pass. Vite reports its normal large-bundle warning for the WebGL renderer; this is not a build failure.
- All 16 Python tests pass, including a new failing-then-passing test proving that the server dataset retains low/native confidence for browser controls without changing default API analysis behavior.
- `npm run test:selection` passes: canonical/disjoint intervals, leap-day month removal, independent sensor confidence, N20 platform encoding, unknown confidence exclusion, empty enabled lists, old/new URL state, invalid dates/camera, wrapped polygons, import scope guards, exact 49,133 Borneo default detections, confirmed versus missing daily coverage, and engine-level spatial coverage restrictions.
- `npm run test:ui` passes all seven existing split-layout/analysis regression checks after adapting the intentional area-selector change. Five axe WCAG scans (calendar, trends, summary, light mode and phone) report no violations.
- `npm run test:interactions` passes all 12 browser checks: fresh globe/satellite, drag/wheel/buttons/recenter, import UI and handler guards, country selection, missing coverage, exact noncontiguous dates and partial years, cross-year and single-day selection, mode switching and Cancel, synchronized map/sidebar filters and pending edits, confirmed imports, cancel/exit drawn area, shared camera/AOI/filter restoration and session-import notice, and phone popover bounds/Escape.

- `npm run test:globe` passes five additional checks: useful-sized World camera; Map/Satellite/Grid restoration; actual low-only VIIRS, native MODIS and platform filtering including empty settings; drag across a year boundary and keyboard date selection; and antimeridian GeoJSON/hole upload with exit restoration. A rear-hemisphere screenshot was visually inspected: Borneo markers do not show through the Americas-facing globe.
- `npm run test:popovers` verifies actual phone hit-testing of the visible Apply footer, exact date application and country selection after moving menus to a body portal to escape map clipping. An additional axe scan of the open date dialog reports no violations.

Screenshots are generated under ignored `artifacts/interactions/`. Browser screenshots are verification artifacts, not application assets.

## Scope and limits

- Geographic coverage is deliberately conservative: different geometries do not inherit a completeness declaration merely because one bbox contains another. Only the same explicit geometry and dates get declared zero days. Larger named areas continue to show real observations with missing gaps.
- Country outlines and continent assignments follow the bundled public-domain Natural Earth 1:50m data. Country/continent links reconstruct these boundaries by identifier; custom shapes are encoded in the URL and very detailed uploaded polygons can produce long links.
- No physical touch device was available. Pointer, click, keyboard, phone viewport layout and accessible non-drag range alternatives were checked in Chromium; hardware touch behavior remains a device test.
- Esri satellite tiles require network access. The globe needs WebGL; a clear error is shown when WebGL cannot initialize. The bundled Map basemap and observations remain local.
- Session imports remain local to the browser tab/session. Share links carry selection and camera state, never data or keys.
- The existing analytical HTTP endpoints retain their legacy contiguous-date and sensor parameter contract. The website computes its extended selection/filter analysis from `/api/dataset` or bundled JSON using the shared browser engine.

## Delivery status

Changes are isolated on branch `feat/globe-selection-controls` in `Alexislim01/harmonization-MODIS-VIIRS`. Repository access was granted and the branch was pushed successfully. Main remains unchanged; this change is submitted for review, without merging or deploying.
