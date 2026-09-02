# Changelog

## [1.2.0] - 2026-09-02

### Added
- **Interactive 3D Altitude–Azimuth Sighting Sky** in the Live view (replaces the old
  flat 2D Sun–Earth–Moon diagram), rendered with PyVista / PyVistaQt:
  - Hemispherical celestial dome in the local Alt–Az frame — compass cardinals (N
    highlighted), altitude rings, azimuth grid, horizon rim and a translucent
    earth-textured ground.
  - Sun as a glowing sphere; the **Moon drawn at its true phase** — the lit crescent is
    shaded from the Sun's direction, so it faces and thins exactly as the real Moon does.
  - Observer → Sun / Moon lines, a dashed Sun–Moon angular-separation link, and ±3 h
    trails for both bodies (toggle Moon/Sun path).
  - Screen-facing Sun / Moon readouts (name, altitude, azimuth) and the observer's
    location name + Lat/Lon; Grid / Moon path / Sun path / Labels toggles; Reset, Top,
    North, South, East, West camera buttons plus click-drag / scroll-zoom.
  - All values come from the same astronomy engine as every other view.
- Added `pyvista>=0.44` and `pyvistaqt>=0.11` to `requirements.txt` (power the 3D sky).
- **3D sky animation export (MP4)** added to the existing *Export animation* dialog: a new
  *"3D sighting sky (MP4) - full 24 h + orbiting camera"* option renders the whole 3D dome
  through a complete 24-hour Sun/Moon cycle while the camera slowly orbits 360°, written to
  `animations/sky-3d-<date>.mp4` (H.264 via OpenCV).  It opens a small preview window that
  closes itself when the file is written.  Requires OpenCV (`opencv-python`).


## [1.1.0] - 2026-09-01

### Added
- **GIF animation export** (Tools ▸ *Export animation (GIF)...*, Ctrl+E): capture any
  chosen evening as an animated GIF spanning 1 hour before sunset to 1 hour after it.
  Choose the west-looking sky map (Sun, Moon and the Moon's trail), the global visibility
  map evaluated at every frame instant (Odeh 2006 / MABIMS 2023 / Danjon), or both stacked
  into a single combined GIF.  The work runs in a background sub-process with a progress
  bar and writes to the `animations/` folder.  Requires Pillow (added to
  `requirements.txt`).
- The sky animation now shows the **Sun physically setting**: it rides above the horizon
  before sunset, dips as the animation passes sunset, and fades out below the horizon
  (previously it was pinned to the horizon line); the Moon's trail also extends slightly
  below the horizon.


## [1.0.1] - 2026-08-28

### Added
- **Global lunar crescent visibility map** (Sighting view, **G**): 1° grid over
  the world, every cell evaluated at its best time with the same rules as the
  on-page verdict, re-coloured instantly by criterion (Odeh 2006 / MABIMS 2023 /
  Danjon), computed in the background and cached per date in memory so stepping
  between dates is instant; observer pin and no-sunset polar band.
- **Live view**: textured Sun, Earth and Moon (a Natural Earth black-and-white
  line map on the globe); a 24 h time scrubber with a **NOW** button; immediate
  response to location/date changes.
- User guide + README coverage and smoke tests for the above.


## [1.0.0] - 2026-08-27

### Added
- Initial release: complete PySide6/Qt port of the pygame app with six
  workspaces (Sighting, Condition, Equation, Threshold, Verify, Live),
  Ramadan/Eid dates dialog, in-app guide, verification against NASA HORIZONS
  and ~8,000 recorded sightings, and a standalone Windows executable.
- Crescent limb orientation fix (lit side aims at the Sun).