"""The collections letter as a PDF: one US Letter page per letter, for a #10 window envelope.

Laid out position for position from the letter-print app's templates/letter.jrxml (JRXML and
reportlab both work in points; y here is measured DOWN from the top of the page, as in JRXML,
and flipped only when drawn). Two deliberate departures, both for the envelope: the recipient
block moved down into the #10 window (the JRXML put its first line above the opening), and the
body now starts below the window, so the letter date never prints over the barcode.

Layout is computed first and drawn second, so the tests can assert the geometry -- what shows
through the window, whether the body reaches the stub -- without parsing a PDF.
"""
from __future__ import annotations

import hashlib
import io
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from reportlab.graphics.barcode.usps4s import USPS_4State
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter as US_LETTER
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdf_canvas

from api.letters.catalog import Words
from api.letters.composer import Composed, compose, fmt, money
from api.letters.model import Letter

logger = logging.getLogger(__name__)

PAGE_H = US_LETTER[1]
LEFT, WIDTH = 54.0, 504.0


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    def inside(self, other: Box) -> bool:
        return (self.x >= other.x and self.y >= other.y
                and self.right <= other.right + 1e-6 and self.bottom <= other.bottom + 1e-6)

    def overlaps(self, other: Box) -> bool:
        return self.x < other.right and other.x < self.right and self.y < other.bottom and other.y < self.bottom


# The standard #10 window envelope (9-1/2 x 4-1/8 in): a 4-1/2 x 1-1/8 in opening 7/8 in from the
# envelope's left edge and 1/2 in from its bottom. The tri-folded sheet's top panel (264pt) rests on
# the envelope's bottom, centred side to side, which puts the opening at x 27..351, y 147..228 on
# the sheet. USPS asks for 1/8 in clearance between the delivery address (and its barcode) and the
# opening's edges, so the insert can shift without hiding a line.
WINDOW = Box(27, 147, 324, 81)
CLEARANCE = 9.0
ADDRESS_ZONE = Box(WINDOW.x + CLEARANCE, WINDOW.y + CLEARANCE, WINDOW.w - 2 * CLEARANCE, WINDOW.h - 2 * CLEARANCE)
STUB_TOP = PAGE_H - 36 - 108            # JRXML lastPageFooter: 108pt above the 36pt bottom margin
FLOW_TOP = WINDOW.bottom + 4

INK, GREY, PANEL, HAIRLINE = "#111111", "#5B6470", "#F5F0EB", "#D9D4CD"
SCALES = (1.0, 0.95, 0.9, 0.85, 0.8, 0.75)
MAX_SERVICE_ROWS = 8


# ---- fonts -------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Font:
    regular: str
    bold: str
    name: str
    note: str | None = None


# fonts-dejavu-core on Debian (the API image), then the usual local places.
FONT_DIRS = (Path("/usr/share/fonts/truetype/dejavu"), Path("/usr/share/fonts/dejavu"),
             Path("/usr/share/fonts/TTF"), Path("/usr/local/share/fonts"),
             Path.home() / "Library" / "Fonts", Path("/Library/Fonts"), Path("/opt/homebrew/share/fonts"))


@lru_cache(maxsize=8)
def resolve_font(dirs: tuple[Path, ...] = FONT_DIRS) -> Font:
    """DejaVu Sans when installed: the face the JRXML was measured and embedded with, so its line
    breaks are the approved ones. Helvetica otherwise, which always exists but wraps differently."""
    for d in dirs:
        regular, bold = d / "DejaVuSans.ttf", d / "DejaVuSans-Bold.ttf"
        if regular.is_file() and bold.is_file():
            tag = hashlib.sha1(str(d).encode()).hexdigest()[:8]
            names = (f"DejaVuSans-{tag}", f"DejaVuSans-Bold-{tag}")
            for name, path in zip(names, (regular, bold)):
                if name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(name, str(path)))
            return Font(*names, "DejaVu Sans")
    note = ("DejaVu Sans is not installed on this server; the letter is set in Helvetica, "
            "so its line breaks can differ from the approved layout.")
    logger.warning(note)
    return Font("Helvetica", "Helvetica-Bold", "Helvetica", note)


# ---- the Intelligent Mail barcode ----------------------------------------------------------------
def valid_imb(code: str | None) -> bool:
    """31 digits (barcode id 2, service type 3, mailer id + serial 15, routing 11), the barcode
    identifier's second digit 0-4."""
    return bool(code) and len(code) == 31 and code.isdigit() and code[1] <= "4"


def imb_bars(tracking: str, routing: str) -> str:
    """The 65 bars as USPS-B-3200 letters: A ascender, D descender, F full, T tracker."""
    return USPS_4State(tracking, routing).barcodes


# ---- layout ------------------------------------------------------------------------------------
@dataclass
class Item:
    role: str
    box: Box
    text: str = ""
    font: str = ""
    size: float = 0.0
    color: str = INK
    align: str = "left"
    shape: str = "text"              # text | rect | line | imb
    fill: str | None = None
    stroke: str | None = None
    line_width: float = 0.0
    dash: tuple[float, ...] | None = None
    imb: str = ""


@dataclass
class Layout:
    items: list[Item] = field(default_factory=list)

    def box(self, role: str) -> Box:
        boxes = [i.box for i in self.items if i.role == role]
        if not boxes:
            raise KeyError(role)
        x, y = min(b.x for b in boxes), min(b.y for b in boxes)
        return Box(x, y, max(b.right for b in boxes) - x, max(b.bottom for b in boxes) - y)


def _fit(text: str, font: str, size: float, width: float) -> str:
    if pdfmetrics.stringWidth(text, font, size) <= width:
        return text
    while text and pdfmetrics.stringWidth(text + "…", font, size) > width:
        text = text[:-1]
    return text.rstrip() + "…"


class _Page:
    def __init__(self, font: Font, brand: str, accent: str):
        self.font, self.brand, self.accent = font, "#" + brand, "#" + accent
        self.items: list[Item] = []

    def text(self, role, x, y, w, h, text, size, *, bold=False, color=INK, align="left"):
        face = self.font.bold if bold else self.font.regular
        self.items.append(Item(role, Box(x, y, w, h), _fit(text, face, size, w), face, size, color, align))

    def lines(self, role, x, y, w, text, size, leading, *, bold=False, color=INK) -> float:
        """Wrapped text; returns the height used."""
        face = self.font.bold if bold else self.font.regular
        wrapped = [ln for part in text.split("\n") for ln in (simpleSplit(part, face, size, w) or [""])]
        for n, line in enumerate(wrapped):
            self.items.append(Item(role, Box(x, y + n * leading, w, leading), line, face, size, color))
        return len(wrapped) * leading

    def rect(self, role, box, *, fill=None, stroke=None, line_width=0.0):
        self.items.append(Item(role, box, shape="rect", fill=fill, stroke=stroke, line_width=line_width))

    def rule(self, role, x, y, w, color, line_width, dash=None):
        self.items.append(Item(role, Box(x, y, w, 0), shape="line", stroke=color, line_width=line_width, dash=dash))


def _return_address(utility_address: tuple[str, ...]) -> str:
    """The street line(s) and the city line, without a department name."""
    keep = [ln for n, ln in enumerate(utility_address)
            if n == len(utility_address) - 1 or any(ch.isdigit() for ch in ln)]
    return " · ".join(keep)


def _letterhead(pg: _Page, words: Words, client_name: str) -> None:
    pg.text("letterhead", LEFT, 40, 300, 22, client_name, 17, bold=True, color=pg.brand)
    for n, line in enumerate(words.utility_address[:3]):
        pg.text("letterhead", LEFT, 64 + 11 * n, 300, 11, line, 8.5, color=GREY)
    for n, line in enumerate(x for x in (words.contact_phone, words.payment_url) if x):
        pg.text("letterhead", 358, 82 + 11 * n, 200, 11, line, 8.5, color=GREY, align="right")
    pg.rule("letterhead", LEFT, 112, WIDTH, pg.brand, 1.5)


def _window(pg: _Page, letter: Letter, words: Words, client_name: str) -> None:
    ret = _return_address(words.utility_address)
    if ret:
        pg.text("return_address", LEFT, WINDOW.y + 2, ADDRESS_ZONE.right - LEFT, 7, f"{client_name} · {ret}", 6,
                color=GREY)
    zone_bottom = ADDRESS_ZONE.bottom
    if valid_imb(letter.imb):
        bars = USPS_4State(letter.imb[:20], letter.imb[20:])
        box = Box(LEFT, zone_bottom - bars.height, bars.width, bars.height)
        pg.items.append(Item("imb", box, shape="imb", imb=letter.imb))
        zone_bottom = box.y - 2
    _address_block(pg, "address", letter, Box(LEFT, ADDRESS_ZONE.y, ADDRESS_ZONE.right - LEFT,
                                               zone_bottom - ADDRESS_ZONE.y), 9.5, 11.5)


def _address_block(pg: _Page, role: str, letter: Letter, box: Box, size: float, leading: float) -> None:
    """Every line of the recipient block inside `box`: a long address is set smaller, never cut."""
    lines = letter.mailing_address.lines() or (letter.customer_name,)
    leading = min(leading, box.h / len(lines))
    size = min(size, leading / 1.2)
    for n, line in enumerate(lines):
        pg.text(role, box.x, box.y + n * leading, box.w, leading, line, size)


def _glance(pg: _Page, letter: Letter, c: Composed) -> float:
    """The at-a-glance box, right of the window; returns its bottom."""
    x, y = 358.0, 120.0
    h = max(96.0, 52 + 11 * len(c.glance) + 4)
    pg.rect("glance", Box(x, y, 200, h), fill=PANEL)
    pg.rect("glance", Box(x, y, 200, 3), fill=pg.accent)
    pg.text("glance", x + 10, y + 6, 180, 11, letter.kind.label.upper(), 8.5, color=GREY)
    pg.text("glance", x + 10, y + 18, 180, 11, c.glance_label, 8.5, color=GREY)
    pg.text("glance", x + 10, y + 29, 180, 21, money(c.glance_amount), 17, bold=True, color=pg.brand)
    for n, (label, value) in enumerate(c.glance):
        pg.text("glance", x + 10, y + 52 + 11 * n, 100, 11, label, 8.5, color=GREY)
        pg.text("glance", x + 110, y + 52 + 11 * n, 80, 11, value, 8.5, align="right")
    return y + h


def _body(pg: _Page, letter: Letter, c: Composed, top: float, s: float, note: str) -> float:
    """The flowing bands at scale `s`; returns where they end."""
    y = top
    pg.text("body", LEFT, y + 2 * s, 300, 13 * s, fmt(letter.letter_date), 9.5 * s)
    pg.text("body", LEFT, y + 17 * s, WIDTH, 13 * s, c.salutation, 9.5 * s)
    y += 30 * s
    y += 2 * s + max(16 * s, pg.lines("body", LEFT, y + 2 * s, WIDTH, c.subject, 11 * s, 14 * s, bold=True,
                                      color=pg.brand)) + 2 * s
    original = letter.body.strip()
    paragraphs = [p for p in (note if original and p == original else p for p in c.paragraphs) if p]
    y += 2 * s
    for p in paragraphs:
        y += pg.lines("body", LEFT, y, WIDTH, p, 9.5 * s, 12 * s) + 5 * s
    if c.callout:
        wrapped = simpleSplit(c.callout, pg.font.bold, 10.5 * s, 480)
        h = max(24.0, 10 + 13 * len(wrapped)) * s
        pg.rect("body", Box(LEFT, y + 3 * s, WIDTH, h), fill=PANEL)
        pg.rect("body", Box(LEFT, y + 3 * s, 4, h), fill=pg.accent)
        pg.lines("body", LEFT + 14, y + 8 * s, 480, c.callout, 10.5 * s, 13 * s, bold=True)
        y += h + 6 * s
    services = letter.debt.services if letter.debt else ()
    if services:
        pg.text("body", LEFT, y + 5 * s, WIDTH, 13 * s, c.services_title, 10 * s, bold=True, color=pg.brand)
        head = y + 19 * s
        pg.rect("body", Box(LEFT, head, WIDTH, 13 * s), fill=pg.brand)
        for x, w, label, align in ((4, 200, "Service", "left"), (204, 220, "Service address", "left"),
                                   (424, 76, "Amount", "right")):
            pg.text("body", LEFT + x, head + 2 * s, w, 11 * s, label, 9 * s, bold=True, color="#FFFFFF", align=align)
        rows = list(services[:MAX_SERVICE_ROWS])
        y += 32 * s
        for sv in rows:
            pg.text("body", LEFT + 4, y + 1 * s, 200, 13 * s, sv.service_type, 9.5 * s)
            pg.text("body", LEFT + 204, y + 1 * s, 216, 13 * s, sv.premise_address, 9.5 * s)
            pg.text("body", LEFT + 424, y + 1 * s, 76, 13 * s, f"{sv.amount:,.2f}", 9.5 * s, align="right")
            y += 13 * s
        if len(services) > len(rows):
            more = sum((sv.amount for sv in services[len(rows):]), Decimal("0"))
            pg.text("body", LEFT + 4, y + 1 * s, 420, 13 * s,
                    f"and {len(services) - len(rows)} more services", 9.5 * s, color=GREY)
            pg.text("body", LEFT + 424, y + 1 * s, 76, 13 * s, f"{more:,.2f}", 9.5 * s, align="right", color=GREY)
            y += 13 * s
        y += 5 * s
    if c.ways:
        pg.text("body", LEFT, y + 6 * s, WIDTH, 13 * s, "Ways to pay", 10 * s, bold=True, color=pg.brand)
        y += 20 * s
        for way in c.ways:
            y += pg.lines("body", LEFT + 10, y, WIDTH - 10, f"•  {way}", 9 * s, 12 * s)
        y += 6 * s
    y += 2 * s + max(36 * s, pg.lines("body", LEFT, y + 2 * s, 300, c.closing, 9.5 * s, 12 * s)) + 2 * s
    if c.notes:
        pg.rule("body", LEFT, y + 2 * s, WIDTH, HAIRLINE, 0.5)
        y += 5 * s
        for n in c.notes:
            y += pg.lines("body", LEFT, y, WIDTH, n, 7.5 * s, 9.5 * s, color=GREY)
        y += 3 * s
    return y


def _stub(pg: _Page, letter: Letter, c: Composed, words: Words, client_name: str) -> None:
    y = STUB_TOP
    pg.rule("stub", LEFT, y + 1, WIDTH, INK, 0.8, dash=(3, 2))
    pg.text("stub", LEFT, y + 5, 360, 12, "Detach and return this portion with your payment", 10, bold=True,
            color=pg.brand)
    pg.text("stub", LEFT, y + 19, 240, 11, f"Account {letter.account_id}", 9.5)
    if c.stub_date:
        pg.text("stub", LEFT, y + 30, 240, 11, f"Pay by {c.stub_date}", 9.5)
    _address_block(pg, "stub", letter, Box(LEFT, y + 44, 240, 40), 8.5, 10)
    pg.text("stub", 314, y + 19, 120, 12, "Amount due", 8.5, color=GREY)
    pg.text("stub", 434, y + 17, 124, 16, money(c.stub_amount), 13, bold=True, color=pg.brand, align="right")
    pg.text("stub", 314, y + 39, 120, 12, "Amount enclosed", 8.5, color=GREY)
    pg.rect("stub", Box(434, y + 36, 124, 17), stroke=INK, line_width=0.6)
    pg.text("stub", 314, y + 58, 244, 11,
            f"Make checks payable to {words.payee}. Mail to:" if words.payee else "Mail to:", 8.5, color=GREY)
    for n, line in enumerate((words.remit_address or words.utility_address)[:3]):
        pg.text("stub", 314, y + 69 + 10 * n, 244, 10, line, 8.5)
    ref = f"Ref {letter.letter_id}" + (f" · {letter.template_code}" if letter.template_code else "")
    pg.text("stub", LEFT, y + 98, 190, 9, ref, 6.5, color=GREY)
    pg.text("stub", 244, y + 98, 314, 9,
            f"@2025, Origin Utility, Inc / Proprietary & Confidential / Expressly for {client_name}  ·  Page 1",
            6.5, color=GREY, align="right")


def layout(letter: Letter, words: Words, client_name: str, font: Font | None = None) -> Layout:
    """One page. The body shrinks (to 75%) before anything is dropped; past that, only the
    contact's own free-text note is shortened -- never the composed notice."""
    font = font or resolve_font()
    c = compose(letter, words)

    def attempt(scale: float, note: str) -> tuple[_Page, float]:
        pg = _Page(font, words.brand_color, words.accent_or_brand)
        _letterhead(pg, words, client_name)
        _window(pg, letter, words, client_name)
        top = max(FLOW_TOP, _glance(pg, letter, c) + 4)
        bottom = _body(pg, letter, c, top, scale, note)
        _stub(pg, letter, c, words, client_name)
        return pg, bottom

    original = note = letter.body.strip()
    for scale in SCALES:
        pg, bottom = attempt(scale, note)
        if bottom <= STUB_TOP:
            return Layout(pg.items)
    while note and bottom > STUB_TOP:
        note = note[: int(len(note) * 0.8)].rstrip()
        pg, bottom = attempt(SCALES[-1], note + "…" if note else "")
    if note != original:
        logger.warning("letter %s: the contact's note was shortened to fit one page", letter.letter_id)
    if bottom > STUB_TOP:
        logger.error("letter %s runs into the remittance stub", letter.letter_id)
    return Layout(pg.items)


# ---- drawing -----------------------------------------------------------------------------------
def _draw(cv: pdf_canvas.Canvas, page: Layout) -> None:
    for it in page.items:
        b = it.box
        if it.shape == "rect":
            cv.setLineWidth(it.line_width)
            if it.fill:
                cv.setFillColor(HexColor(it.fill))
            if it.stroke:
                cv.setStrokeColor(HexColor(it.stroke))
            cv.rect(b.x, PAGE_H - b.bottom, b.w, b.h, stroke=int(bool(it.stroke)), fill=int(bool(it.fill)))
        elif it.shape == "line":
            cv.setStrokeColor(HexColor(it.stroke))
            cv.setLineWidth(it.line_width)
            if it.dash:
                cv.setDash(list(it.dash))
            cv.line(b.x, PAGE_H - b.y, b.right, PAGE_H - b.y)
            if it.dash:
                cv.setDash()
        elif it.shape == "imb":
            USPS_4State(it.imb[:20], it.imb[20:]).drawOn(cv, b.x, PAGE_H - b.bottom)
        elif it.text:
            ascent, _ = pdfmetrics.getAscentDescent(it.font, it.size)
            baseline = PAGE_H - (b.y + ascent)
            cv.setFont(it.font, it.size)
            cv.setFillColor(HexColor(it.color))
            if it.align == "right":
                cv.drawRightString(b.right, baseline, it.text)
            else:
                cv.drawString(b.x, baseline, it.text)
    cv.showPage()


@dataclass(frozen=True)
class Rendered:
    pdf: bytes
    pages: int
    font: str
    note: str | None


def render_letters(letters: list[Letter], words: Words, client_name: str, *, font: Font | None = None) -> Rendered:
    """One page per letter, in the caller's order."""
    font = font or resolve_font()
    buf = io.BytesIO()
    cv = pdf_canvas.Canvas(buf, pagesize=US_LETTER)
    cv.setTitle("Collections letter")          # metadata never carries a name or an address
    for letter in letters:
        _draw(cv, layout(letter, words, client_name, font))
    cv.save()
    return Rendered(buf.getvalue(), len(letters), font.name, font.note)
