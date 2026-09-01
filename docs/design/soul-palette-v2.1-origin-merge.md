# Soul Palette V2.1 — Origin merge

**Base:** V2.1 Soul Palette, approved by Reed 2026-08-29
**Merged:** OriginBA analytics portal, 2026-09-01
**Contrast:** 14 pairs, all AA in both columns

V2.1 is adopted **verbatim** — all fifteen V1 anchors, the neutral ramp, both brand
ramps and the six chart aliases keep their approved values. The OriginBA portal adds
seven tokens for roles the conversion app does not have, and asks for **no changes to
any V2.1 value**.

| | |
| --- | --- |
| **37** | tokens adopted verbatim — surfaces, text, status pairs, neutral ramp, brand ramps, chart aliases, value for value, both columns |
| **7** | tokens added by the portal — page-title ink, cross-filter selection, the three value-ramp anchors, the button gradient end |
| **0** | changes requested to V2.1 — nothing in the approved set is redefined, renamed or overridden |

---

## The merged palette

`V1` marks a V2.1 anchor · `+BA` marks a portal addition.

### Surfaces

| Token | Light | Dark | |
| --- | --- | --- | --- |
| `background` | `#FFFFFF` | `#0B1723` | V1 |
| `card` | `#FFFFFF` | `#14202D` | V1 |
| `muted` | `#F2F5F8` | `#212C39` | V1 |
| `band` | `#EFF5FB` | `#1B2835` | V1 |
| `border` | `#D9E1E8` | `#343E4A` | V1 |
| `input` | `#7A8FA0` | `#606A76` | V1 |

### Text and brand

| Token | Light | Dark | |
| --- | --- | --- | --- |
| `foreground` | `#1B2530` | `#E6ECF2` | V1 |
| `muted-foreground` | `#56636E` | `#A4ACB4` | V1 |
| `heading` | `#1C7884` | `#8ACAD4` | V1 |
| `primary` | `#006FAC` | `#6BB2EA` | V1 |
| `primary-foreground` | `#FFFFFF` | `#07121E` | V1 |
| `ring` | `#006FAC` | `#6BB2EA` | V1 |
| `title` | `#1B2530` | `#E6ECF2` | **+BA** |

### Status pairs

| Token | Light | Dark | |
| --- | --- | --- | --- |
| `ok` | `#0B5A2E` | `#96D6A7` | V1 |
| `ok-bg` | `#E4F1E8` | `#003A15` | V1 |
| `over` | `#8B1515` | `#FF998D` | V1 |
| `over-bg` | `#FBEAEA` | `#610000` | V1 |
| `warn-fg` | `#3D2E00` | `#F2E5B1` | V1 |
| `warn-bg` | `#F3E5AB` | `#403103` | V1 |

### Neutral ramp

| Token | Light | Dark |
| --- | --- | --- |
| `neutral-0` | `#FFFFFF` | `#0B1723` |
| `neutral-1` | `#F2F5F8` | `#14202D` |
| `neutral-2` | `#D9E1E8` | `#343E4A` |
| `neutral-3` | `#A4B8C8` | `#5A6470` |
| `neutral-4` | `#7A8FA0` | `#838D98` |
| `neutral-5` | `#56636E` | `#B1B8C1` |
| `neutral-6` | `#1B2530` | `#E6ECF2` |

### Brand ramps

| Token | Light | Dark |
| --- | --- | --- |
| `brand-blue-1` | `#28A0EE` | `#A2E6FF` |
| `brand-blue-2` | `#006FAC` | `#6BB2EA` |
| `brand-blue-3` | `#004B86` | `#1A7BB9` |
| `brand-teal-1` | `#5DA5B0` | `#BCE7EE` |
| `brand-teal-2` | `#1C7884` | `#8ACAD4` |
| `brand-teal-3` | `#00535F` | `#388E9A` |

### Chart palette

| Token | Light | Dark | |
| --- | --- | --- | --- |
| `chart-1` | `#006FAC` | `#6BB2EA` | = `brand-blue-2` |
| `chart-2` | `#1C7884` | `#8ACAD4` | = `brand-teal-2` |
| `chart-3` | `#28A0EE` | `#A2E6FF` | = `brand-blue-1` |
| `chart-4` | `#00535F` | `#388E9A` | = `brand-teal-3` |
| `chart-5` | `#004B86` | `#1A7BB9` | = `brand-blue-3` |
| `chart-6` | `#7A8FA0` | `#838D98` | = `neutral-4` |
| `chart-selected` | `#A85E00` | `#F0B429` | **+BA** |

### Value ramp

| Token | Light | Dark | |
| --- | --- | --- | --- |
| `ramp-high` | `#006FAC` | `#6BB2EA` | **+BA** (= `primary`) |
| `ramp-mid` | `#695166` | `#BFAABE` | **+BA** |
| `ramp-low` | `#8B1515` | `#FF998D` | **+BA** (= `over`) |

---

## The value ramp, and the one thing that needed fixing

Portal bar charts encode magnitude by colour: the tallest bar is brand blue, the
shortest is red. The portal's original ramp swept hue in HSL, which takes the short
way round the wheel and lands mid-range values in vivid magenta and violet — colours
that exist nowhere in V2.1 and read as a third category rather than a middling value.

**Before** (HSL hue sweep):

`#CF4934` → `#CF3473` → `#CF34C6` → `#AF34CF` → `#8534CF` → `#3436CF` → `#3489CF`

**After** (Oklab, between two palette tokens):

`#8B1515` → `#823235` → `#76434E` → `#695166` → `#575C7D` → `#3F6694` → `#006FAC`

Dark column: `#FF998D` → `#EBA09E` → `#D6A5AF` → `#BFAABE` → `#A7AECD` → `#8CB0DC` → `#6BB2EA`

Re-interpolating the same two endpoints in Oklab keeps the middle low-chroma and
inside the palette, and anchors the bottom to V2.1's own `over` red — so the suite
has exactly one red. In the conversion app it marks a file above its error target; in
the portal it marks the bottom of a measured range. Same hue, same alarm weight.

---

## Contrast, recomputed at merge time

Every V2.1 pair was recomputed from the published hex values and matches the V2.1
sheet exactly. The two added pairs are listed with them. AA needs 4.5:1.

| Text on background | Where it appears | Light | Dark |
| --- | --- | ---: | ---: |
| foreground on background | body text | 15.51 | 15.20 |
| muted-foreground on background | captions, legend | 6.17 | 7.87 |
| heading on background | section headings | 5.16 | 9.89 |
| primary on background | active nav, links | 5.43 | 7.91 |
| primary-foreground on primary | table header, buttons | 5.43 | 8.24 |
| foreground on band | zebra rows | 14.13 | 12.59 |
| foreground on muted | tile, chips | 14.18 | 11.89 |
| muted-foreground on card | chart text | 6.17 | 7.17 |
| ok on ok-bg | Meets target chip | 7.17 | 7.72 |
| over on over-bg | Above target chip | 8.15 | 6.76 |
| warn-fg on warn-bg | banner, Unexplained | 10.45 | 10.02 |
| foreground on input | text on input border | 4.63 | 4.62 |
| **title on card** *(+BA)* | page titles | 15.51 | 13.85 |
| **selected-fg on chart-selected** *(+BA)* | cross-filter bar label | 4.92 | 10.11 |

---

## Decisions inside the additions

1. **`--title`, not a redefined `--heading`.** V2.1 puts teal on h1/h2 at 5.16:1, which
   is right for a status dashboard's short headings. Portal page titles run long and
   analytic ("Frozen bill segments by bill cycle, trailing 90 days"), so they take ink
   at 15.51:1 while teal stays on the eyebrow above them. Both tokens keep their V2.1
   meaning; the portal simply uses one more.

2. **`--chart-selected` is amber because the categorical set is blue and teal.**
   Clicking a bar cross-filters the dashboard, and the selected bar has to leave the
   series palette entirely or the selection is invisible. Amber at `#A85E00` / `#F0B429`
   carries its own value label (4.92:1 light, 10.11:1 dark) and is the only warm hue in
   the chart layer, so it never competes with a category.

3. **The value ramp shares V2.1's red.** Anchoring the low end to `over` rather than a
   new red means the suite has exactly one red.

4. **The button gradient ends inside the blue ramp.** The portal's primary button is a
   gradient; its second stop is now `brand-blue-3` instead of the indigo it used to
   carry, so the button is Origin blue at both ends.

5. **Teal is never a category colour.** Adopted from V2.1 as written — teal stays on
   headings, target lines and single-series accents. Two-series charts pair `chart-1`
   with `chart-3`.

---

## Shipped in the portal, 2026-09-01

The merge is implemented and running. The portal was on a Tailwind sky/indigo/slate
palette whose neutrals and primary already sat within 2–11° of V2.1's hues, so the
surfaces barely moved. Four things changed visibly:

- **Chart series lost their rainbow.** Indigo, violet and amber categories are now the
  blue/teal aliases — the largest single shift in the app.
- **Dark mode is the V2.1 navy.** `#0B1723` page, `#14202D` card, replacing the
  portal's near-black ground.
- **Status colours are tokens.** 205 hardcoded Tailwind emerald/red/amber/sky classes
  across 39 files now resolve to the six status tokens, and the brand-audit script
  fails the build on any Tailwind palette class so they cannot come back.
- **The value ramp no longer goes magenta.** Verified live: a five-bar chart renders
  `#006FAC → #734755 → #8B1515` in light and `#6BB2EA → #CFA7B3 → #FF998D` in dark —
  no step outside the palette.

---

## CSS, ready to paste

```css
:root {
  /* V2.1, verbatim */
  --background:#FFFFFF; --card:#FFFFFF; --muted:#F2F5F8; --band:#EFF5FB;
  --border:#D9E1E8; --input:#7A8FA0;
  --foreground:#1B2530; --muted-foreground:#56636E; --heading:#1C7884;
  --primary:#006FAC; --primary-foreground:#FFFFFF; --ring:#006FAC;
  --ok:#0B5A2E; --ok-bg:#E4F1E8; --over:#8B1515; --over-bg:#FBEAEA;
  --warn-fg:#3D2E00; --warn-bg:#F3E5AB;
  --neutral-0:#FFFFFF; --neutral-1:#F2F5F8; --neutral-2:#D9E1E8; --neutral-3:#A4B8C8;
  --neutral-4:#7A8FA0; --neutral-5:#56636E; --neutral-6:#1B2530;
  --brand-blue-1:#28A0EE; --brand-blue-2:#006FAC; --brand-blue-3:#004B86;
  --brand-teal-1:#5DA5B0; --brand-teal-2:#1C7884; --brand-teal-3:#00535F;
  --chart-1:var(--brand-blue-2); --chart-2:var(--brand-teal-2); --chart-3:var(--brand-blue-1);
  --chart-4:var(--brand-teal-3); --chart-5:var(--brand-blue-3); --chart-6:var(--neutral-4);

  /* OriginBA additions */
  --title:var(--neutral-6);
  --chart-selected:#A85E00; --chart-selected-foreground:#FFFFFF;
  --ramp-high:var(--brand-blue-2); --ramp-mid:#695166; --ramp-low:var(--over);
  --accent:var(--primary); --accent-2:var(--brand-blue-3);
}

.dark {
  /* V2.1, verbatim */
  --background:#0B1723; --card:#14202D; --muted:#212C39; --band:#1B2835;
  --border:#343E4A; --input:#606A76;
  --foreground:#E6ECF2; --muted-foreground:#A4ACB4; --heading:#8ACAD4;
  --primary:#6BB2EA; --primary-foreground:#07121E; --ring:#6BB2EA;
  --ok:#96D6A7; --ok-bg:#003A15; --over:#FF998D; --over-bg:#610000;
  --warn-fg:#F2E5B1; --warn-bg:#403103;
  --neutral-0:#0B1723; --neutral-1:#14202D; --neutral-2:#343E4A; --neutral-3:#5A6470;
  --neutral-4:#838D98; --neutral-5:#B1B8C1; --neutral-6:#E6ECF2;
  --brand-blue-1:#A2E6FF; --brand-blue-2:#6BB2EA; --brand-blue-3:#1A7BB9;
  --brand-teal-1:#BCE7EE; --brand-teal-2:#8ACAD4; --brand-teal-3:#388E9A;

  /* OriginBA additions */
  --title:var(--neutral-6);
  --chart-selected:#F0B429; --chart-selected-foreground:#07121E;
  --ramp-high:var(--brand-blue-2); --ramp-mid:#BFAABE; --ramp-low:var(--over);
  --accent:var(--primary); --accent-2:var(--brand-blue-3);
}
```

---

To approve the merge, reply **"merge approved"**. To change one addition, name the
token and the direction ("selection warmer", "ramp middle lighter"). No V2.1 value is
in question — this document only proposes what sits beside it.
