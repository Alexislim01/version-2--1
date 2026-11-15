You are modifying my existing FireAtlas website for the NASA MODIS–VIIRS hotspot harmonization project. Inspect the repository and attached screenshots to understand the current implementation before editing it. Implement the changes below, preserving the existing visual identity and working features.

The screenshots show existing behavior and visual references. My written requirements describe the intended changes. Work only on this scope for now.

## 1. Make the import confirmation mandatory

In “Data & imports,” this checkbox currently has no effect:

“This is a complete export for the current AOI from 2019-01-01 to 2023-12-31. Days without detections may be treated as zero.”

Change it so that:

- It is unchecked initially.
- “Import FIRMS CSV files” is disabled until it is checked.
- The actual import handler also checks the confirmation, including any alternative import entry points.
- Unchecking it disables importing again.
- Show a short explanation beside the disabled button.
- The confirmation text reflects the actual selected AOI and date interval rather than hardcoded dates.
- Reset confirmation when the AOI or date interval changes.

This is a user declaration of completeness, not proof that the file is complete. Preserve CSV validation and coverage handling. Treat days without detections as zero only within the explicitly confirmed spatial and temporal scope; missing coverage elsewhere must remain missing. Update any surrounding text that currently suggests importing without confirmation is supported.

Preserve:

- The FIRMS CSV import functionality.
- “Get archive data,” linking to the FIRMS archive download page.
- “Get a free MAP_KEY,” linking to NASA’s map-key registration page.
- Source files, attribution, and provenance information at the bottom.

Do not add a feature for users to upload, enter, or replace map keys. Preserve the current key configuration and keep secrets out of source code and shared links.

## 2. Open with a true 3D globe and satellite imagery

Currently, the website opens centered on Malaysia/Borneo and displays a flat map. Change the fresh-load default to:

- Satellite imagery enabled.
- A zoomed-out view showing the entire Earth as a true 3D globe.
- A globe large enough to be useful within the existing map viewport.

Use the attached “God’s Eye View” screenshot as inspiration only for the Earth’s appearance when fully zoomed out: a spherical Earth against a dark background with a subtle atmospheric edge. Do not copy its dashboard, overlays, labels, or unrelated features. If consulting its source, verify the correct repository and license rather than guessing.

The current satellite imagery looks good. Preserve its provider, visual quality, colors, and detail wherever technically possible. Inspect the current rendering stack and choose the least disruptive approach that supports a genuine globe and the existing overlays.

Required behavior:

- Drag to rotate/navigate the globe.
- Mouse-wheel zoom and existing + / − buttons work.
- Smooth navigation from the whole Earth down to regional detail.
- Detections, grids, boundaries, and drawn areas remain geographically aligned.
- No markers from the far side of Earth show through the globe.
- Preserve Map, Satellite, and Grid functionality.
- Preserve the recenter button: it returns to the selected AOI, including an active custom AOI.

Distinguish camera position from data selection. Opening with the entire globe visible does not imply global observation coverage or require silently changing the selected AOI. Continue to communicate that bundled observations cover Malaysian territory for 2019–2023.

A shared-view URL must restore its saved view instead of being overridden by the fresh-load globe default.

## 3. Replace the area sidebar interaction with a cascading dropdown

Clicking the current area selector, labelled “Borneo,” should open an anchored dropdown instead of the existing side panel.

Required structure:

- First level: continents.
- Hovering over a continent opens a submenu of its countries.
- Selecting a country selects its AOI and navigates the map to it.
- Offer continent-level selection and a World option.
- Preserve useful existing regional presets, such as Borneo, in a clearly labelled section.
- Preserve GeoJSON AOI upload through an accessible entry point.

Use real geographic boundaries/extents and a documented country-to-continent mapping. Handle multipart countries and antimeridian-crossing extents correctly.

The dropdown examples are references for the menu interaction, not a replacement for FireAtlas styling. Keep its dark palette, typography, and accent colors.

Support click, keyboard, and touch as well as hover. Submenus must remain usable while moving the pointer between levels and must fit within the viewport.

Countries without loaded observations must remain selectable for navigation. Display missing coverage honestly rather than inventing observations or showing zero activity.

## 4. Replace the date sidebar interaction with a date popover

Clicking the calendar/year selector should open an anchored popover instead of the side panel. Provide two switchable modes:

**Years / months**

- Years have checkboxes.
- Hovering over or expanding a year reveals months with checkboxes.
- Selecting a whole year selects all its months.
- Partially selected years show an indeterminate state.
- Support multiple years and months, including noncontiguous selections.

**Calendar**

- Allow selecting an individual day.
- Allow dragging across dates to choose an inclusive start/end interval.
- Provide a click-based and keyboard-accessible alternative to dragging.
- Support ranges spanning months and years, with clear selection highlighting.

Both modes must update the same underlying date selection. Preserve exact selected dates when switching modes; do not silently fill gaps or broaden the selection.

Use a clear Apply/Cancel interaction. Update the toolbar label to summarize the applied selection. Keep the map, activity calendar, charts, counts, summaries, and share links consistent with that selection. Dates outside loaded coverage must be presented as missing data.

## 5. Keep Filters in a more compact side panel

The Filters button may continue opening a side panel.

Make it more compact through tighter spacing, grouped controls, and appropriate collapsible sections while retaining readable labels and usable controls.

Preserve existing advanced functionality, including:

- Sensor selection.
- Existing satellite/platform selection, where supported.
- Map grid size.
- Confidence filtering.
- Reset/apply behavior and other existing filter options.

Do not remove functionality just because it is not visible in one screenshot.

## 6. Add optional advanced controls directly over the map

Add a clearly labelled “Advanced settings” checkbox in the map interface.

- Checked: reveal a compact map control panel.
- Unchecked: hide the panel without resetting applied filters.
- Keep the panel clear of essential map controls.

Include sensor selection, supported satellite/platform controls, grid size, and sensor-specific confidence controls.

Preserve existing grid options:

- 0.1° — More detail.
- 0.25° — Balanced.
- 0.5° — Less detail.

The map controls and Filters sidebar must use one shared filter state. Applied changes from either location must appear in the other and affect the same observations. Any pending sidebar edits should be clearly distinguished from applied settings.

### Sensor-specific confidence

Do not apply one numeric confidence scale to both sensor families.

**MODIS selected**

- Show numeric MODIS confidence controls on its native 0–100 scale.
- Provide a minimum/maximum range, with clear labels.
- Here, “percentage/percentile” means the original MODIS confidence value, not a percentile ranking of the dataset.

**VIIRS selected**

- Show three independently selectable checkboxes: Low, Nominal, High.
- Correctly interpret the actual imported category encodings.
- Do not convert these categories into invented numeric MODIS equivalents.

**Both selected**

- Show both sets of controls.
- Apply the MODIS range only to MODIS records.
- Apply VIIRS category selections only to VIIRS records.
- Combine the resulting enabled observations for display.

Preserve each sensor’s last settings when toggling sensors off and on. Handle unknown or missing confidence explicitly rather than silently assigning a value. If no sensors or no VIIRS categories are selected, show an appropriate empty result without crashing.

## 7. Let users exit a drawn AOI

Preserve rectangle and polygon drawing and their existing spatial filtering.

After a drawn area is applied:

- Show a visible “Exit drawn area” or “Clear drawn area” control.
- Clicking it removes the custom geometry and its spatial filter.
- Restore the previously selected named AOI and navigate back to it.
- Preserve the selected dates, sensors, confidence settings, metric, and basemap.
- Update charts, summaries, counts, and share state consistently.

Also allow cancelling an unfinished drawing. Exiting an AOI must not delete imported observations.

## 8. Preserve and extend Share view

Currently, Share view creates and immediately copies a URL that restores the selected area, dates, metric, and enabled sensors. Preserve that behavior.

Extend the saved state as necessary to restore:

- Globe camera position and zoom.
- Basemap.
- Named or drawn AOI.
- Exact date selection, including noncontiguous selections.
- Sensor/platform selections.
- MODIS confidence range and VIIRS confidence categories.
- Grid size and selected metric.

Maintain compatibility with older shared links where feasible. Validate URL state and use safe fallbacks for invalid values.

Browser-session imports are not automatically available to another person opening a link. Preserve that distinction and show a useful missing-data message when necessary. Never include credentials or raw imported datasets in the shared URL.

## Implementation and verification

Inspect the current map library, application state, imports, coverage logic, filtering, and share-link code before changing them. Implement these requirements in the existing application.

Preserve the existing FireAtlas branding, satellite imagery, navigation, analysis features, exports, attribution, and unrelated behavior. Keep new controls responsive and accessible.

Verify at least:

1. Importing is blocked until confirmation is checked, including at handler level.
2. Changing the AOI or dates resets confirmation.
3. A fresh load shows the whole 3D Earth with satellite imagery.
4. Dragging, zooming, recentering, overlays, and drawing work on the globe.
5. Area and date selectors open popovers rather than the side panel.
6. Country selection and both date modes update the actual data selection.
7. Sidebar and map advanced controls remain synchronized.
8. MODIS and VIIRS confidence filters work independently and together.
9. Exiting a drawn AOI restores the previous named AOI without resetting unrelated settings.
10. Shared links restore the configured view and filters.
11. Missing coverage stays missing, including outside Malaysia.
12. Existing relevant checks and the production build pass.

Use browser interaction to verify the visible behavior where available. Report what changed, what was tested, and any remaining limitations. If a requirement cannot be completed, say precisely which part and why; do not replace working behavior with a decorative mockup or claim unverified completion.
