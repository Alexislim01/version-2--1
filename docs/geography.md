# Geography and globe rendering

Country geometry is Natural Earth Admin 0 Countries, 1:50m, retrieved 15 November 2026 from:
https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_50m_admin_0_countries.geojson

Natural Earth data is public domain: https://www.naturalearthdata.com/about/terms-of-use/
The bundled `countries.geojson` retains geometry and only `NAME_EN`, `ADM0_A3`, and `CONTINENT` (renamed to `name`, `id`, and `continent`). This is the documented country-to-continent mapping used by the menu, including Natural Earth's whole-country assignments for transcontinental countries. Territories follow the source's administrative units and map-unit continent. Boundaries are a cartographic dataset, not a legal position on sovereignty. The menu includes 242 countries/territories, seven continents, World, and existing regional presets.

Multipart geometries are retained. Bounds use the complement of the largest longitude gap to represent antimeridian-crossing extents (`west > east`). Ring tests unwrap consecutive longitude coordinates, including holes. The map fits wrapped bounds using an eastern longitude greater than 180 when necessary. Countries/continents are shared by identifier and reconstructed from the same bundled atlas, avoiding huge boundary strings in URLs. Custom geometries are explicitly shared as GeoJSON.

The renderer uses MapLibre GL JS's real globe projection. Esri World Imagery retains the original tile URL, colors, imagery data, 256px tile size, and maximum zoom 12. Native geographic sources/layers place detections, grids, geometry and drawing on the globe and clip the rear hemisphere. No God's Eye View code or assets are used. Natural Earth, NASA FIRMS and Esri attribution remains visible.

Coverage is conservative. Complete Malaysian country files establish complete daily coverage only when the selected geometry is Malaysia. Larger presets (including Borneo), World, and other countries show actually observed days without interpreting unobserved parts as zero. A user-confirmed import establishes zero days only for the same selected geometry and explicitly selected dates, and only for sensor families represented in its files. Other geometries conservatively fall back to observed days; geometric subset coverage is not inferred from bounding-box containment. Imported rows remain available if selection changes; imports are never included in URLs.

Browser-session imports are not persistent, and a shared URL cannot restore someone else's imported data. Shared camera state is validated independently of AOI state. Legacy links without camera state navigate to their saved AOI; fresh visits open a viewport-sized whole Earth.

Bundled atlas SHA-256: `feb9dfc97ca063e13ac7172e8c3565236355a0123e8040c288954aadbe275091`.
