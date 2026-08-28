# Changelog

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