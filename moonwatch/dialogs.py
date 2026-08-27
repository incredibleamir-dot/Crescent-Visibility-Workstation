"""Modal dialogs: date & location, Ramadan / Eid dates, User guide, About."""

import datetime
import os

from PySide6.QtCore import Qt, QDate, QUrl
from PySide6.QtGui import QImage, QTextDocument, QColor
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QDateEdit, QComboBox,
                               QDoubleSpinBox, QGroupBox, QFormLayout,
                               QTextBrowser, QScrollArea, QWidget, QFrame,
                               QLineEdit, QTableWidget, QTableWidgetItem,
                               QHeaderView, QAbstractItemView)

try:
    from PySide6.QtPrintSupport import QPrinter, QPrintDialog
    _HAS_PRINT = True
except Exception:
    _HAS_PRINT = False

import islamic

from . import theme
from .controller import fmt_date, app_logo
from .charts import F

CITIES = [
    ("Ludhiana, India", 30.90, 75.85, 5.5),
    ("Roorkee, India", 29.87, 77.89, 5.5),
    ("Delhi, India", 28.61, 77.21, 5.5),
    ("Makkah, Saudi Arabia", 21.42, 39.83, 3.0),
    ("Karachi, Pakistan", 24.86, 67.01, 5.0),
    ("Kuala Lumpur, Malaysia", 3.14, 101.69, 8.0),
    ("Jakarta, Indonesia", -6.21, 106.85, 7.0),
    ("London, UK", 51.51, -0.13, 0.0),
    ("New York, USA", 40.71, -74.01, -5.0),
]


class LocationDateDialog(QDialog):
    """Pick the sighting evening and place (city preset or raw coordinates)."""

    def __init__(self, ctrl, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Date & location")
        self.setModal(True)
        self.setMinimumWidth(420)

        self.lat, self.lon, self.tz = ctrl.lat, ctrl.lon, ctrl.tz
        self.city = ctrl.city
        self.date = ctrl.date

        form = QGroupBox("Sighting evening and place")
        fl = QFormLayout(form)

        qd = QDate(ctrl.date.year, ctrl.date.month, ctrl.date.day)
        self.date_edit = QDateEdit(qd)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd MMM yyyy")
        fl.addRow("Date", self.date_edit)

        self.city_combo = QComboBox()
        self.city_combo.addItem("Custom...", None)
        for name, la, lo, tz in CITIES:
            self.city_combo.addItem(name, (la, lo, tz))
        idx = self.city_combo.findData(
            (round(ctrl.lat, 2), round(ctrl.lon, 2), ctrl.tz))
        if idx < 0:
            for i, (name, la, lo, tz) in enumerate(CITIES, start=1):
                if name == ctrl.city:
                    idx = i
                    break
        self.city_combo.setCurrentIndex(max(0, idx))
        fl.addRow("Preset place", self.city_combo)
        self.city_combo.currentIndexChanged.connect(self._pick_city)

        self.lat_spin = QDoubleSpinBox(); self.lat_spin.setRange(-90, 90)
        self.lat_spin.setDecimals(2); self.lat_spin.setValue(ctrl.lat)
        self.lon_spin = QDoubleSpinBox(); self.lon_spin.setRange(-180, 180)
        self.lon_spin.setDecimals(2); self.lon_spin.setValue(ctrl.lon)
        self.tz_spin = QDoubleSpinBox(); self.tz_spin.setRange(-14, 14)
        self.tz_spin.setDecimals(1); self.tz_spin.setValue(ctrl.tz)
        fl.addRow("Latitude (N+)", self.lat_spin)
        fl.addRow("Longitude (E+)", self.lon_spin)
        fl.addRow("UTC offset (hours)", self.tz_spin)

        hint = QLabel("Coordinates to two decimal places. Choosing a preset "
                      "fills the coordinate fields.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: %s;" % theme.TEXT_DIM)

        btns = QHBoxLayout()
        btns.addStretch(1)
        ok = QPushButton("Apply")
        ok.setProperty("primary", True)
        ok.setDefault(True)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        btns.addWidget(cancel)
        btns.addWidget(ok)

        lay = QVBoxLayout(self)
        lay.addWidget(form)
        lay.addWidget(hint)
        lay.addSpacing(6)
        lay.addLayout(btns)

    def _pick_city(self, idx):
        data = self.city_combo.itemData(idx)
        if data is None:
            return
        la, lo, tz = data
        self.lat_spin.setValue(la)
        self.lon_spin.setValue(lo)
        self.tz_spin.setValue(tz)

    def result(self):
        """(city, lat, lon, tz, datetime) selected by the user."""
        la, lo = self.lat_spin.value(), self.lon_spin.value()
        tz = self.tz_spin.value()
        idx = self.city_combo.currentIndex()
        name = self.city_combo.currentText()
        if idx == 0 or any(name == c[0] for c in CITIES) is False:
            name = "Custom"
        qd = self.date_edit.date()
        when = datetime.datetime(qd.year(), qd.month(), qd.day())
        return name, la, lo, tz, when


class DatesDialog(QDialog):
    """Ramadan / Eid dates derived from local crescent visibility."""

    def __init__(self, ctrl, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ramadan & Eid dates")
        self.setModal(True)
        self.resize(1240, 660)
        self._build(ctrl)

    @staticmethod
    def _dates_table(prev_rows, next_rows):
        """One table per event: 6 previous + 6 next occurrences.

        No horizontal scrollbar, and tall enough to show the rows comfortably.
        """
        headers = ["AH", "Sighting evening", "First civil day"]
        n = 2 + len(prev_rows) + len(next_rows)
        t = QTableWidget(n, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(20)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.NoSelection)
        t.setFocusPolicy(Qt.NoFocus)
        t.setShowGrid(True)
        t.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Fixed)
        widths = (54, 132, 130)
        for ci, w in enumerate(widths):
            t.setColumnWidth(ci, w)
        t.setMinimumWidth(sum(widths))
        afont = F(8, mono=True)

        def section(row, text, color, bg):
            item = QTableWidgetItem("  " + text)
            item.setFont(F(8, bold=True))
            item.setForeground(QColor(color))
            item.setBackground(QColor(bg))
            t.setSpan(row, 0, 1, len(headers))
            t.setItem(row, 0, item)

        def data(row, ah_year, civil):
            start = civil - datetime.timedelta(days=1)
            cells = ("%d AH" % ah_year,
                     start.strftime("%a %d %b %Y"),
                     civil.strftime("%a %d %b %Y"))
            for ci, txt in enumerate(cells):
                item = QTableWidgetItem(txt)
                item.setFont(afont)
                t.setItem(row, ci, item)

        ri = 0
        section(ri, "Previous (6)", theme.OK, theme.OK_BG)
        ri += 1
        for ah_year, civil in prev_rows:
            data(ri, ah_year, civil)
            ri += 1
        section(ri, "Next (6)", theme.C_TODAY, theme.ACCENT_BG)
        ri += 1
        for ah_year, civil in next_rows:
            data(ri, ah_year, civil)
            ri += 1

        t.setFixedHeight(hh.height() + 2 + n * 20 + 4)
        return t

    def _build(self, ctrl):
        lay = QVBoxLayout(self)
        title = QLabel("Ramadan & Eid dates")
        title.setObjectName("section")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: %s;" % theme.ACCENT)
        sub = QLabel("Found from local crescent visibility at this place")
        sub.setStyleSheet("color: %s;" % theme.TEXT_MUT)
        note = QLabel("An Islamic day begins at sunset. Each evening below is "
                      "the sighting night on which the new month begins; the "
                      "civil calendar day of the occasion follows in the last "
                      "column.")
        note.setWordWrap(True)
        note.setStyleSheet("color: %s; font-weight: 600;" % theme.WARN)
        lay.addWidget(title)
        lay.addWidget(sub)
        lay.addWidget(note)

        data = islamic.event_series(ctrl.lat, ctrl.lon, ctrl.tz, ctrl.date)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        hbox = QHBoxLayout(holder)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(12)
        hbox.addStretch(1)
        for ev in data["events"]:
            box = QGroupBox(ev["name"])
            bl = QVBoxLayout(box)
            d = QLabel(ev["desc"])
            d.setWordWrap(True)
            d.setStyleSheet("color: %s;" % theme.TEXT_MUT)
            bl.addWidget(d)
            bl.addWidget(self._dates_table(ev["prev6"], ev["next6"]))
            bl.addStretch(1)
            hbox.addWidget(box)
        hbox.addStretch(1)
        scroll.setWidget(holder)
        lay.addWidget(scroll, 1)

        city = next((c for c in CITIES if c[1] == ctrl.lat and
                     c[2] == ctrl.lon and c[3] == ctrl.tz), None)
        where = city[0] if city else ("lat %.2f, lon %.2f, UTC%+.1f"
                                      % (ctrl.lat, ctrl.lon, ctrl.tz))
        foot = QLabel(
            "Place: %s\nSelected date: %s   |   Today: %s" % (
                where, ctrl.date.strftime("%d %b %Y"),
                data["today"].strftime("%d %b %Y")))
        foot.setStyleSheet("color: %s;" % theme.TEXT_DIM)
        lay.addWidget(foot)

        btns = QHBoxLayout()
        btns.addStretch(1)
        close = QPushButton("Close")
        close.setDefault(True)
        close.clicked.connect(self.accept)
        btns.addWidget(close)
        lay.addLayout(btns)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setModal(True)
        self.resize(470, 380)

        text = QTextBrowser()
        text.setOpenExternalLinks(True)
        text.setStyleSheet("QTextBrowser { border: none; }")
        text.setHtml(
            "<h3>Moon Watch</h3>"
            "<p>A moon-sighting workstation for Ramadan, Eid and every new "
            "crescent. Predict whether the young crescent can be seen on any "
            "given evening from any place.</p>"
            "<p><b>Workspaces</b><br>"
            "Sighting - evening sky diagram, 14-evening forecast and the "
            "MABIMS 2023 / Danjon / Odeh (2006) criteria.<br>"
            "Condition - criteria limits against 8,000+ recorded evenings.<br>"
            "Equation - fitted visibility boundary.<br>"
            "Threshold - minimum observed values by observing method.<br>"
            "Verification - cross-check against NASA/JPL HORIZONS and the "
            "recorded sighting database.<br>"
            "Live - Sun-Earth-Moon positions for right now.</p>"
            "<p><b>Calculations</b><br>"
            "Ephemerides: the vendored solarsystem library.  Database "
            "analysis: adapted from the analytical methods of the open-source "
            "crescent database project "
            "(<a href='https://github.com/msyazwanfaid/hilalpy'>database "
            "project</a>).</p>"
            "<p><b>Author</b><br>Amir Arshad - "
            "<a href='https://github.com/incredibleamir-dot'>"
            "github.com/incredibleamir-dot</a>.</p>"
            "<p><b>Interface</b><br>"
            "A full PySide6 desktop port; the original pygame build is "
            "available in the upstream repository.</p>"
        )
        cr = QFrame()
        cr.setFrameShape(QFrame.HLine)
        cr.setStyleSheet("color: %s;" % theme.BORDER)
        version = QLabel("Moon Watch - PySide6 edition")
        version.setStyleSheet("color: %s;" % theme.TEXT_DIM)
        btns = QHBoxLayout()
        btns.addStretch(1)
        close = QPushButton("Close")
        close.setDefault(True)
        close.clicked.connect(self.accept)
        btns.addWidget(close)

        lg = QLabel()
        lg.setPixmap(app_logo().pixmap(64, 64))
        lg.setAlignment(Qt.AlignHCenter)
        lay = QVBoxLayout(self)
        lay.addWidget(lg, 0, Qt.AlignHCenter)
        lay.addWidget(text, 1)
        lay.addWidget(cr)
        lay.addWidget(version)
        lay.addLayout(btns)


# ---------------------------------------------------------------------------
# User guide
# ---------------------------------------------------------------------------

_SHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "assets", "screenshots")
_SHOTS = ["sight", "cond", "equa", "thres", "verify", "live", "dates", "about"]

_GUIDE_HTML = """<html><body>
<h2>Moon Watch - User Guide</h2>
<p>A moon-sighting workstation. Pick a date and a place, and Moon Watch
computes whether the young crescent should be visible that evening, how the
Islamic months behave at that location, and how our numbers compare with
NASA/JPL HORIZONS and 8,000+ recorded crescent sightings.</p>

<p><b>Contents</b></p>
<ol>
<li><a href="#quick">Quick start</a></li>
<li><a href="#sight">The Sighting page</a></li>
<li><a href="#times">How the times are calculated</a></li>
<li><a href="#quant">The core quantities</a></li>
<li><a href="#crit">Visibility criteria</a></li>
<li><a href="#islamic">The Islamic calendar</a></li>
<li><a href="#cond">The Condition page</a></li>
<li><a href="#equa">The Equation page</a></li>
<li><a href="#thres">The Threshold page</a></li>
<li><a href="#verify">The Verification page</a></li>
<li><a href="#live">The Live page</a></li>
<li><a href="#short">Keyboard shortcuts</a></li>
<li><a href="#gloss">Glossary and references</a></li>
</ol>

<a name="quick"></a><h3>1&nbsp;&nbsp;Quick start</h3>
<p>Use <b>File &gt; Date &amp; location...</b> (or <b>Ctrl+L</b>) to set the
date, city, latitude, longitude and UTC offset, then step through evenings
with the <b>&larr; / &rarr;</b> keys. The status bar always shows the current
date, place and bottom-line verdict. The <b>Ramadan &amp; Eid dates...</b>
dialog (<b>D</b>) lists the last and next Ramadan, Eid ul Fitr and Eid ul Adha
for your location.</p>

<a name="sight"></a><h3>2&nbsp;&nbsp;The Sighting page</h3>
<p><img src="guide://shot-sight" width="740"></p>
<p><b>Left, top - the evening sky diagram.</b> You are looking <i>west</i> at
sunset. The curving ground line is the horizon; the dashed arcs above it are
10&deg;, 20&deg; and 30&deg; altitude rings, and the labels along the bottom
(S, SW, W, NW, N) give compass azimuths. The setting Sun is drawn at the
horizon with its glow. The crescent is placed at its true altitude and
azimuth, with a dashed line dropping to the horizon so you can judge its
height by eye. The dotted trail climbing from the horizon shows the path the
moon follows from sunset to moonset. The top-left caption lists the sunset /
moonset times, the moon altitude and arc of light at sunset, and the age of
the moon. Underneath is the <b>14-evening forecast</b>: one bar per evening,
the moon's altitude at that sunset, green when at or above the MABIMS 3&deg;
line and amber below it; the current evening is highlighted in gold as
TODAY.</p>
<p><b>Right panel.</b> The big pill at the top is the bottom-line verdict
(CRESCENT VISIBLE / BORDERLINE / NOT VISIBLE / NO SUNSET). Below it: the Odeh
zone, a table of the three criteria, the evening parameters table (moon age,
illumination, altitude, azimuth, elongation, arc of vision, lag time, width,
distances) and a plain-English reading.</p>

<a name="times"></a><h3>3&nbsp;&nbsp;How the times are calculated</h3>
<p>Everything is computed from two engines: the vendored
<b>solarsystem</b> package for the Moon, and Schlyter's low-precision solar
elements for the Sun (wrapped in <code>astronomy.py</code>).</p>
<p><b>Time base.</b> All celestial math runs on the Julian Date (UTC). A civil
datetime is converted with</p>
<p><code>JD = JDN + (h - 12)/24</code></p>
<p>where <code>JDN</code> is the integer Julian day number from the standard
Gregorian formula. The caller subtracts the UTC offset so the work is always
in UTC.</p>
<p><b>Where is the Sun?</b> The solar elements use days since the epoch</p>
<p><code>D = JD - 2451543.5</code></p>
<p>then the longitude of perihelion, eccentricity and mean anomaly</p>
<p><code>w = 282.9404 + 4.70935e-5 &middot; D</code><br>
<code>e = 0.016709 - 1.151e-9 &middot; D</code><br>
<code>M = 356.047 + 0.9856002585 &middot; D</code></p>
<p>Kepler's equation is solved approximately for the eccentric anomaly and
the true position is found from the ellipse:</p>
<p><code>E = M + e&middot;sin M</code>&nbsp;&nbsp;(one Newton step in practice)<br>
<code>x = cos E - e,&nbsp;&nbsp;y = &radic;(1 - e&sup2;)&nbsp;&middot;&nbsp;sin E</code><br>
<code>longitude = atan2(y, x) + w</code></p>
<p>This gives the Sun's geocentric ecliptic longitude and distance <code>R</code>
in AU.</p>
<p><b>Where is the Moon?</b> The Moon's position, distance and parallax are
taken from the Moon model of <code>vendor/solarsystem.py</code>, evaluated
geocentrically (or topocentrically when the observer's latitude / longitude
are supplied) directly at the required Julian instant.</p>
<p><b>From the ecliptic to the horizon.</b> First rotate the ecliptic
coordinates into the equator by the obliquity of the ecliptic</p>
<p><code>&epsilon; = 23.4393&deg; - 3.563e-7&nbsp;&middot;&nbsp;D</code></p>
<p>to get right ascension and declination. Then, with GST (Greenwich sidereal
time) and the observer's longitude, compute the local sidereal time and the
hour angle <code>H</code>:</p>
<p><code>LST = GST + longitude</code><br>
<code>H = LST - RA</code></p>
<p>and finally the horizontal coordinates for latitude <code>&phi;</code>;</p>
<p><code>sin(alt) = sin &phi; sin &delta; + cos &phi; cos &delta; cos H</code></p>
<p>with the azimuth following from the same triangle. Azimuth 0 = North,
90 = East, 180 = South, 270 = West.</p>
<p><b>Sunset and moonset.</b> A body is "set" when the <i>upper limb</i>
touches the horizon, i.e. the centre reaches the depression angle</p>
<p><code>alt = -0.833&deg; = -34' (refraction) - 16' (disk half-diameter)</code></p>
<p>The code bisects the time window (60 iterations) until the altitude
equals that target. Sunset searches 11:00-23:59 local; moonset searches
10:00 to 06:00 the next day so a moon that sets just after midnight is still
caught. If there is no sign change (polar day / night) the app reports
"no sunset".</p>
<p><b>The "best time".</b> Crescent visibility is judged near the moment the
atmospheric path is longest while the sky is still dark - Yallop's classic
recommendation, adopted by Odeh:</p>
<p><code>best = sunset + (4/9) &middot; (moonset - sunset)</code></p>
<p>If the moon is already down at sunset, best = sunset + 15 minutes.</p>
<p><b>Conjunction and moon age.</b> The geocentric new moon is the instant the
signed difference in the sun-moon ecliptic longitudes crosses zero; the code
scans the previous 32 days for that sign change and bisects it. The age is
then simply</p>
<p><code>age (hours) = (JD - JD<sub>conjunction</sub>) &middot; 24</code></p>

<a name="quant"></a><h3>4&nbsp;&nbsp;The core quantities</h3>
<p>At the best time (and, for some quantities, at sunset) the app reports:</p>
<p><b>Elongation, "arc of light" (<code>ArcL</code> / <code>arc_l</code>).</b>
The angular separation between the Sun and the Moon as seen from Earth, found
from the spherical-law formula</p>
<p><code>cos d = sin b<sub>1</sub> sin b<sub>2</sub>
+ cos b<sub>1</sub> cos b<sub>2</sub> cos(&lambda;<sub>1</sub>-&lambda;<sub>2</sub>)</code></p>
<p>For a young crescent this is a few degrees to tens of degrees; it is the
most reliable predictor of visibility.</p>
<p><b>Arc of vision (<code>ArcV</code> / <code>arc_v</code>).</b> The vertical
separation of the moon above the sun at the best time:</p>
<p><code>arcv = altitude<sub>moon</sub> - altitude<sub>sun</sub></code></p>
<p>(When the sun is below the horizon, its "altitude" is negative, so the arc
of vision can exceed the moon's altitude.)</p>
<p><b>Crescent width (<code>W</code>).</b> The width of the lit sliver in
arcminutes, from the topocentric semi-diameter and the elongation:</p>
<p><code>W = SD<sub>topo</sub> &middot; (1 - cos &lambda;)</code></p>
<p>with the parallactic augmentation making the apparent disc slightly bigger
when the moon is high:</p>
<p><code>SD<sub>topo</sub> = SD &middot; (1 + sin(alt) &middot; sin(&pi;))</code></p>
<p><b>Illumination (<code>illum</code>).</b> The fraction of the disc that is
lit. The exact phase, computed at the <i>Moon</i> (not at the observer), uses
the triangle Sun-Moon-Earth with distances <code>R</code> (AU) and
<code>r</code> (Earth radii converted to AU):</p>
<p><code>m = &radic;(R&sup2; + r&sup2; - 2 R r cos &lambda;)</code>&nbsp;&nbsp;(Sun-Moon distance)<br>
<code>cos i = (r&sup2; + m&sup2; - R&sup2;) / (2 r m)</code>&nbsp;&nbsp;(phase angle at the Moon)<br>
<code>illumination = (1 + cos i) &nbsp;/&nbsp; 2</code></p>
<p><b>Lag time (<code>LT</code>).</b> How long the moon stays up after sunset:
<code>moonset - sunset</code>, in minutes. It matters: enough time must pass
for the twilight to fade while the moon is still above the horizon.</p>
<p><b>Relative azimuth (<code>DAZ</code>).</b> How far the moon sits to the
left (north) or right (south) of the sunset point, wrapped to 0..180&deg;.
It is shown for completeness but is not one of the hard thresholds.</p>

<a name="crit"></a><h3>5&nbsp;&nbsp;Visibility criteria</h3>
<p>The app evaluates three criteria side by side.</p>
<p><b>MABIMS 2023.</b> Visible when <i>both</i> hold at sunset:</p>
<p><code>ArcL &ge; 6.4&deg;</code>&nbsp;&nbsp;and&nbsp;&nbsp;<code>altitude at sunset &ge; 3&deg;</code></p>
<p><b>Danjon limit.</b> Below 7&deg; of elongation the crescent cannot be seen
at all, because the dark side of the Moon is illuminated by earthshine alone
and the sliver is too thin:</p>
<p><code>ArcL &ge; 7&deg;</code></p>
<p><b>Odeh (2006).</b> The most detailed. The threshold curve is a cubic in the
crescent width <code>W</code> (arcminutes):</p>
<p><code>arcv' = 7.1651 - 6.3226 W + 0.7319 W&sup2; - 0.1018 W&sup3;</code></p>
<p>and the observed arc of vision is compared against it with the margin</p>
<p><code>v = arcv - arcv'</code></p>
<p>giving the familiar zones</p>
<table border="1" cellspacing="0" cellpadding="4">
<tr><td><b>Zone</b></td><td><b>Condition</b></td><td><b>Meaning</b></td></tr>
<tr><td>A</td><td>v &ge; 5.65&deg;</td><td>easily visible to the naked eye</td></tr>
<tr><td>B</td><td>2.0 &le; v &lt; 5.65</td><td>visible with optical aid / maybe naked eye</td></tr>
<tr><td>C</td><td>-0.96 &le; v &lt; 2.0</td><td>visible with optical aid only</td></tr>
<tr><td>D</td><td>v &lt; -0.96 &nbsp;or&nbsp; ArcL &lt; 6.4&deg;</td><td>not visible</td></tr>
</table>
<p>The bottom-line pill combines them: A or B = <b>CRESCENT VISIBLE</b>;
C (or failing MABIMS/Danjon) = <b>BORDERLINE</b>; otherwise <b>NOT VISIBLE</b>.
"NO SUNSET" means the sun never sets there that evening.</p>

<a name="islamic"></a><h3>6&nbsp;&nbsp;The Islamic calendar</h3>
<p><img src="guide://shot-dates" width="740"></p>
<p>Moon Watch follows the same rule as the rest of the app: an Islamic day
<b>starts at sunset</b>. A month begins the day <i>after</i> the first evening
on which the young crescent is actually above the horizon at sunset at your
location. The lunations are anchored to the well-known date
<b>1 Ramadan 1446 AH = 1 March 2025</b> and stepped forward / backward by the
synodic month length</p>
<p><code>synodic month = 29.530588853 days</code></p>
<p>In the <b>Ramadan &amp; Eid dates</b> dialog (<b>D</b>) each of the three
occasions - first <b>Ramadan</b> (1 Ramadan), then <b>Eid ul Fitr</b>
(1 Shawwal) and <b>Eid ul Adha</b> (10 Dhul Hijjah) - has its own box with a
single table of the 6 previous and 6 next occurrences: the <b>AH</b> year, the
<b>sighting evening</b> (the night the month begins, at sunset) and the
<b>first civil day</b>. Small print: the dates are computed purely
astronomically for your exact place; local religious announcements may shift
civil dates by a day.</p>

<a name="cond"></a><h3>7&nbsp;&nbsp;The Condition page</h3>
<p><img src="guide://shot-cond" width="740"></p>
<p>Each dot is one recorded evening from <code>data/Final.csv</code>; green =
sighted, red = not sighted; filled circles are naked-eye reports, small
squares are optical-aid reports. The amber cross-lines are the MABIMS limits
(6.4&deg; arc of light, 3&deg; altitude). A dot in the upper-right box should
have been visible under MABIMS; a dot in the lower-left should not have been;
dots on the "wrong" side of a line are the errors. The panels on the right
turn that into numbers: the <b>error rate</b> is the share of seen evenings
below the limit plus the share of unseen evenings above it (false negatives +
false positives), reported for the whole dataset, for naked-eye records and
for optical-aid records, so you can see how well the line fits each method.
The gold ring with "THIS EVENING" marks where your current date/location sits.</p>

<a name="equa"></a><h3>8&nbsp;&nbsp;The Equation page</h3>
<p><img src="guide://shot-equa" width="740"></p>
<p>Same database plot, but now the boundary is the fitted curve (moon lag time
on the horizontal axis, arc of light on the vertical axis):</p>
<p><code>ArcL = 10.8467 - 0.5058 x + 0.0059 x&sup2; - 0.000021 x&sup3;</code></p>
<p>with <code>x</code> = lag time in minutes. A dot <i>above</i> the purple
curve should be visible; a dot below should not. The golden ring again shows
this evening. Use the error tables the same way as in Condition.</p>

<a name="thres"></a><h3>9&nbsp;&nbsp;The Threshold page</h3>
<p><img src="guide://shot-thres" width="740"></p>
<p>For the evenings where the crescent was <i>actually seen</i> (evening
records only), this shows the distribution of one parameter (default: arc of
light), split into naked-eye and optical-aid groups. Box = the middle half of
the records (Q1 to Q3), the dark bar = the median, the whiskers = the smallest
and largest observed values, and the label below gives the sample size
<i>n</i>. Switch the parameter with <b>X</b> (or the drop-down): <code>ArcL</code>,
<code>MAlt</code>, <code>ArcV</code>, <code>W</code>, <code>LT</code>,
<code>MA</code> (= moon age). The gold horizontal line marks where your
current evening's value falls, with its label.</p>

<a name="verify"></a><h3>10&nbsp;&nbsp;The Verification page</h3>
<p><img src="guide://shot-verify" width="740"></p>
<p>Two independent audits of the engine, both run in background sub-processes
so the interface never freezes.</p>
<p><b>NASA/JPL HORIZONS (online).</b> Press "Run comparison" (<b>R</b>, or the
same button again after changing the date). The app asks the NASA/JPL
HORIZONS API for the Sun's and Moon's topocentric azimuth / elevation plus
illumination and elongation through the sunset window at your exact
coordinates, interpolates its tables to our sunset instant, and prints a
difference table: sunset (&plusmn;8 min), moonset (&plusmn;12 min), moon
altitude (&plusmn;1.5&deg;), azimuth (&plusmn;4&deg;), arc of light
(&plusmn;2&deg;), illumination (&plusmn;1.5%). Our/Astro columns are followed
by a PASS/FAIL chip per row. Requires internet.</p>
<p><b>Recorded sightings (offline).</b> Run automatically on this page. The
app recomputes the MABIMS verdict for a fast sample of the 8,000+ real world
records (each with its own place, date and outcome) and reports the agreement
percentage - overall and per observing method - plus the mean, maximum and
p90 difference in arc of light, moon altitude and lag time between our
calculation and the recorded values.</p>

<a name="live"></a><h3>11&nbsp;&nbsp;The Live page</h3>
<p><img src="guide://shot-live" width="740"></p>
<p>A Sun-Earth-Moon snapshot for <i>right now</i>, refreshed every 5 seconds
(and on every visit). It is a top-down view: the Sun on the left, the Earth
textured with the sub-solar point facing you, the Moon on its orbit ring at
its true elongation from the Sun. The green arc of the orbit is the part where
the moonlight would see the crescent above the horizon at your location; grey
is below. The ring around the moon is green when the moon is up, grey when it
is down (altitude &gt; 0&deg;). Your city is marked on the Earth's disk. The
caption under the chart gives the phase name, illumination, and age.</p>
<p>Use the <b>LIVE time</b> slider under the chart to scrub through the 24 hours
of the selected date (great for "when does the moon set tonight?"); press
<b>NOW</b> to return to the current time and resume the 5-second live
updates.</p>

<a name="short"></a><h3>12&nbsp;&nbsp;Keyboard shortcuts</h3>
<table border="1" cellspacing="0" cellpadding="4">
<tr><td><b>Key</b></td><td><b>Action</b></td></tr>
<tr><td>&larr; / &rarr;</td><td>previous / next day</td></tr>
<tr><td>T</td><td>back to today</td></tr>
<tr><td>1..6 or S C E H V L</td><td>switch workspace</td></tr>
<tr><td>Ctrl+L</td><td>date &amp; location...</td></tr>
<tr><td>D</td><td>Ramadan &amp; Eid dates...</td></tr>
<tr><td>R</td><td>run (or re-run) the NASA/JPL HORIZONS comparison</td></tr>
<tr><td>X</td><td>cycle the Threshold parameter</td></tr>
<tr><td>Ctrl+F1</td><td>this user guide</td></tr>
<tr><td>F1</td><td>About Moon Watch</td></tr>
<tr><td>F11</td><td>fullscreen</td></tr>
<tr><td>Ctrl+Q</td><td>quit</td></tr>
</table>

<a name="gloss"></a><h3>13&nbsp;&nbsp;Glossary and references</h3>
<p><b>ArcL</b> - arc of light: geocentric elongation of the moon from the sun
(deg). <b>ArcV</b> - arc of vision: moon altitude minus sun altitude at the
best time (deg). <b>MAlt</b> - altitude of the moon at sunset (deg).
<b>W</b> - crescent width (arcmin). <b>LT</b> - lag time, moonset minus sunset
(min). <b>MA</b> - moon age (h). <b>DAZ</b> - relative azimuth of the moon
from the sunset point (deg). <b>AH</b> - Anno Hegirae, the Islamic calendar.
<b>MABIMS</b> - the four-nation religious committee (Brunei, Indonesia,
Malaysia, Singapore) whose 2023 criteria these are. <b>HORIZONS</b> - the
NASA/JPL solar-system ephemeris service.</p>
<p>References: Meeus, <i>Astronomical Algorithms</i>, 2nd ed. (1998);
Odeh, <i>New criterion for lunar crescent visibility</i> (2006);
Yallop, <i>A method for predicting the first visibility of the lunar
crescent</i> (1997); Danjon (1936); Schlyter, <i>How to compute planetary
positions</i> (2009).</p>
</body></html>
"""


def _guide_images():
    """Load the bundled screenshots, sized for comfortable inline reading."""
    images = {}
    for name in _SHOTS:
        path = os.path.join(_SHOT_DIR, "shot-%s.png" % name)
        if os.path.exists(path):
            img = QImage(path)
            if not img.isNull():
                scaled = img.scaledToWidth(740)
                images["guide://shot-%s" % name] = scaled
    return images


class UserGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Moon Watch - User Guide")
        self.setModal(False)
        self.resize(820, 640)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setOpenLinks(True)
        browser.setStyleSheet(
            "QTextBrowser { border: 1px solid %s; border-radius: 6px;"
            " padding: 8px; }" % theme.BORDER)
        doc = browser.document()
        for name, img in _guide_images().items():
            doc.addResource(QTextDocument.ImageResource, QUrl(name), img)
        browser.setHtml(_GUIDE_HTML)
        self.browser = browser

        find = QLineEdit()
        find.setPlaceholderText("Search the guide... (Enter = next match)")
        find.setClearButtonEnabled(True)
        find.returnPressed.connect(self._find_next)

        btns = QHBoxLayout()
        close = QPushButton("Close")
        close.setDefault(True)
        close.clicked.connect(self.accept)
        btns.addStretch(1)
        if _HAS_PRINT:
            print_btn = QPushButton("Print...")
            print_btn.clicked.connect(self._print)
            btns.addWidget(print_btn)
        btns.addWidget(close)

        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        lay.addWidget(browser, 1)
        lay.addWidget(find)
        lay.addLayout(btns)

    def _find_next(self):
        self.browser.find(self.sender().text())

    def _print(self):
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec():
            self.browser.document().print_(printer)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F1:
            self.close()
            return
        super().keyPressEvent(event)