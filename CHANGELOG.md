# Changelog

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