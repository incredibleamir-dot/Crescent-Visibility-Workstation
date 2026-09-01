# Moon Watch - Crescent Visibility Workstation — Release Notes

**Version 1.1.0** · PySide6 desktop app for predicting and analysing new-crescent
visibility (Ramadan / Eid) from any location.

> Repository: [Crescent-Visibility-Workstation](https://github.com/incredibleamir-dot/Crescent-Visibility-Workstation)

---

## What's new in v1.1.0

- **GIF animation export** (new): **Tools ▸ Export animation (GIF)...** (Ctrl+E) turns any
  chosen evening into an animation running from 1 hour before sunset to 1 hour after it.
  Three outputs: the **west-looking sky** (Sun, Moon and the trail the Moon traces through
  the whole window), the **global visibility map** recoloured at every instant with the same
  Odeh / MABIMS / Danjon rules as the app, and an optional **combined** GIF (sky above the
  map). A date picker, output-folder choice and progress bar are in the dialog; the heavy
  grid computation runs in a background sub-process so the interface never freezes.
- **Physically setting sun**: the sun in the sky frames now climbs before sunset, touches
  the horizon at sunset, and sinks out of view — it is no longer glued to the horizon line.
- **Dependency**: added Pillow (used for GIF frame assembly).

## What's new in v1.0.1

- **Global lunar crescent visibility map** (new): in the Sighting view, press
  **G** (or use the top-left selector) to switch from the local sky diagram to
  a whole-world map of the same evening. Every 1° cell is classified at that
  location's sunset by the chosen criterion and coloured **green** (visible) /
  **amber** (borderline) / **red** (not visible); the no-sunset polar band is
  left clear. A criterion dropdown (Odeh 2006 default, MABIMS 2023, Danjon
  limit) re-colours the map instantly — the ≈64k-point grid is computed once
  per date in a background sub-process (~2–4 s). Your city is pinned on the
  map, and the four classes are the same ones used by the local verdict pill.
- **Live view — fully textured Sun, Earth and Moon**: all three bodies now use
  the bundled texture maps, not just the Earth.
- **Live time scrubber**: slide through the 24 h of the selected date to watch
  the Sun-Earth-Moon system at any time of day; press **NOW** to return to the
  live clock (fixed 5 s updates). The scrub control bar is slim.
- **Instant location response**: changing the date/location updates the Live
  view (observer dot + clock) immediately instead of waiting for the next
  tick.

## Bug fixes in v1.0.1

- **UTC offset no longer rounds** in the status bar: `UTC+5.5` really shows
  `UTC+5.5` (was `UTC+6`).
- **Textures actually load**: the Live view always drew plain circles because
  the texture loader was broken on the current PySide6 (`QImage.bits()` now
  returns a `memoryview`); Earth/Moon/Sun maps now render.
- **Earth night side** in the Live view is no longer near-pure-black — dim but
  visible.
- Crescent limb orientation was fixed earlier (lit side aims at the Sun) and
  remains correct across sky map, sidebar thumbnail and Live view.

## Requirements & build

- Python 3.11+, `pip install -r requirements.txt` (PySide6, numpy, pandas, Pillow).
- Run: `python main.py`
- Build: `python -m PyInstaller --clean --noconfirm MoonWatch.spec`
  → `dist/MoonWatch.exe`

## Notes / limitations

- The **NASA HORIZONS** comparison needs internet; everything else is offline.
- The global map classifies using values at each cell's *sunset*; the polar
  no-sunset band is uncoloured.
- Islamic dates use the app's local-visibility rule, so they can differ from a
  fixed civil calendar.

## Thanks

- Original pygame app + engine: [moon-watch](https://github.com/incredibleamir-dot/moon-watch)
- Recorded-sightings database: [HilalPy](https://github.com/msyazwanfaid/hilalpy)
- `solarsystem` (Paul Schlyter's algorithms): MIT licence
- Textures: [Solar System Scope](https://www.solarsystemscope.com/textures/), CC BY 4.0

See `CHANGELOG.md`, `CREDITS.md` and `PYGAME_TO_PYSIDE6.md`.