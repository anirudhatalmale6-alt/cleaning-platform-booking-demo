"""Palettes: the picker, the persistence, and a contrast audit.

"Eye catchy colours" is the easiest request in the world to get wrong —
a bright green button with white text looks great in a mockup and is
unreadable on a phone in the sun. So this suite does two things:

  1. Proves the picker actually repaints all four surfaces and that the
     choice survives a reload and follows the visitor to the dashboards.
  2. Measures WCAG contrast on real rendered text in every palette,
     compositing semi-transparent colours over whatever is actually
     behind them, and fails if any of it drops below its threshold.

    python3 test_theme.py
"""
import pathlib, sys
from playwright.sync_api import sync_playwright

HERE   = pathlib.Path(__file__).parent
PAGES  = {
    "index":     (HERE / "index.html").as_uri(),
    "dashboard": (HERE / "dashboard.html").as_uri(),
    "cleaner":   (HERE / "cleaner.html").as_uri(),
    "admin":     (HERE / "admin.html").as_uri(),
}
THEMES = ["fresh", "electric", "forest", "heritage"]

fails = []
def check(label, ok, got=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{(': ' + str(got)) if got else ''}")
    if not ok:
        fails.append(label)

# ---------------------------------------------------------------- contrast
# Resolve the colour a browser would actually show: composite every
# semi-transparent layer over the first opaque background above it, then
# apply the WCAG 2.1 relative-luminance formula.
CONTRAST_JS = r"""
(sel) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  const parse = c => {
    const m = String(c).match(/[\d.]+/g);
    if (!m) return null;
    return [ +m[0], +m[1], +m[2], m.length > 3 ? +m[3] : 1 ];
  };
  const over = (fg, bg) => {          // src-over compositing
    const a = fg[3];
    return [ fg[0]*a + bg[0]*(1-a), fg[1]*a + bg[1]*(1-a), fg[2]*a + bg[2]*(1-a), 1 ];
  };
  // Walk up for the effective background. A gradient is only treated as
  // the background when the element ITSELF is painted with one — <body>
  // carries the two faint corner glows, so testing background-image on
  // every ancestor compared all the page's text against the brand green
  // and reported nonsense (heritage's dark-green button came out 1.45:1).
  const root = getComputedStyle(document.documentElement);
  let node = el, stack = [], grad = null;
  if (/gradient/.test(getComputedStyle(el).backgroundImage)) {
    grad = [ root.getPropertyValue('--primary').trim(),
             root.getPropertyValue('--primary-2').trim() ];
  } else {
    while (node && node !== document.documentElement) {
      const bg = parse(getComputedStyle(node).backgroundColor);
      if (bg && bg[3] > 0) { stack.push(bg); if (bg[3] === 1) break; }
      node = node.parentElement;
    }
  }
  let base = parse(getComputedStyle(document.documentElement).backgroundColor);
  if (!base || base[3] === 0) base = [255,255,255,1];
  let bg = base;
  for (const layer of stack.reverse()) bg = over(layer, bg);

  const hex = h => {
    h = h.replace('#','');
    if (h.length === 3) h = h.split('').map(c=>c+c).join('');
    return [ parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16), 1 ];
  };
  const lum = c => {
    const f = v => { v /= 255; return v <= .03928 ? v/12.92 : Math.pow((v+.055)/1.055, 2.4); };
    return .2126*f(c[0]) + .7152*f(c[1]) + .0722*f(c[2]);
  };
  const ratio = (a, b) => {
    const [h, l] = [lum(a), lum(b)].sort((x,y) => y - x);
    return (h + .05) / (l + .05);
  };
  const bgs = grad ? grad.map(hex) : [bg];
  const fgRaw = parse(getComputedStyle(el).color);
  const worst = Math.min(...bgs.map(b => ratio(over(fgRaw, b), b)));
  return { ratio: Math.round(worst * 100) / 100,
           text: el.textContent.trim().slice(0, 28) };
}
"""

# (page, selector, label, minimum). 4.5 is the WCAG AA body-text bar;
# 3.0 is the bar for large text and for deliberately muted meta lines.
AUDIT = [
    ("index",     ".hero h1 em",        "hero accent word",      3.0),
    ("index",     ".hero p.lede",       "hero paragraph",        4.5),
    ("index",     ".eyebrow",           "eyebrow",               4.5),
    ("index",     ".svc .s-t",          "service tile name",     4.5),
    ("index",     ".svc .s-d",          "service tile sub",      3.0),
    ("index",     ".svc .s-p",          "service tile price",    3.0),
    ("index",     ".btn-primary",       "primary button",        4.5),
    ("index",     ".btn-outline",       "outline button",        4.5),
    ("index",     ".protobar span",     "prototype bar",         4.5),
    ("index",     ".nav a",             "top nav link",          4.5),
    ("index",     ".note",              "green info note",       4.5),
    ("index",     ".trust .t-l",        "trust strip label",     3.0),
    ("dashboard", ".pill.ok",           "pill: confirmed",       4.5),
    ("dashboard", ".stat .s-l",         "stat label",            3.0),
    ("dashboard", ".stat .s-v",         "stat number",           3.0),
    ("dashboard", ".snav.on",           "side nav, active",      4.5),
    ("dashboard", ".snav:not(.on)",     "side nav, idle",        4.5),
    ("dashboard", ".kv dt",             "detail list key",       3.0),
    ("dashboard", ".kv dd",             "detail list value",     4.5),
    ("admin",     "table.tbl th",       "table header",          3.0),
    ("admin",     "table.tbl td",       "table cell",            4.5),
    ("admin",     ".t-sub",             "table sub-line",        3.0),
    ("admin",     ".page-head h1",      "page title",            4.5),
    ("admin",     ".page-head p",       "page subtitle",         3.0),
    ("cleaner",   ".gate.wait",         "pending-approval gate", 4.5),
    ("cleaner",   ".gate .g-t",         "gate heading",          4.5),
]

# The accent rotation gives tiles 2, 3 and 4 a different hue from tile 1,
# so auditing only the first one proves nothing about the other three.
# Amber is the one that bites: at full strength it is ~2:1 on its own
# tint, which is why the icons and numbers use --ac-ink.
for _n in (1, 2, 3, 4):
    AUDIT += [
        ("index",     f".svc:nth-child({_n}) svg",      f"service icon {_n}", 3.0),
        ("index",     f".svc:nth-child({_n}) .s-t",     f"service name {_n}", 4.5),
        ("index",     f".svc:nth-child({_n}) .s-p",     f"service price {_n}", 3.0),
        ("dashboard", f".stat:nth-child({_n}) .s-v",    f"stat number {_n}",  3.0),
        ("dashboard", f".stat:nth-child({_n}) .s-l",    f"stat label {_n}",   3.0),
    ]

# Two of the audited states are behind a click, so the page is driven to
# them once per theme rather than asserting against whatever loads first.
def reach_gate(page):
    """Sign in as the cleaner whose application is still pending."""
    page.evaluate("view = 'signin'; render()")
    page.wait_for_selector("[data-as]")
    page.locator(".task", has_text="Account is pending").first.click()
    page.wait_for_selector(".gate.wait")

SETUP = {"cleaner": reach_gate}

def set_theme(page, theme):
    page.evaluate("t => setTheme(t)", theme)
    page.wait_for_function("t => document.documentElement.dataset.theme === t", arg=theme)

def freeze(page):
    """Kill transitions and animations before measuring colour.

    .svc, .qa, .task and friends are declared `transition:.22s` with no
    property list, so `all` is animated — including background-color and
    colour. Reading a computed style right after the palette changes
    returns a value part-way through that animation, which is how the
    first run of this suite "found" a 2.93:1 service tile that is really
    17:1. Freezing makes the measurement the painted value.
    """
    page.add_style_tag(content="*,*::before,*::after{"
                               "transition:none!important;animation:none!important}")

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1280, "height": 760})
    errors = []
    pages = {}
    for name, url in PAGES.items():
        p = ctx.new_page()
        p.on("pageerror", lambda e, n=name: errors.append(f"{n}: {e}"))
        p.goto(url)
        p.wait_for_selector(".protobar")
        pages[name] = p

    print("1. The picker is on every surface")
    for name, p in pages.items():
        n = p.locator("[data-theme-btn]").count()
        check(f"{name}: four swatches", n == len(THEMES), n)

    print("\n2. Default palette, and each swatch repaints the page")
    page = pages["index"]
    check("default is fresh",
          page.evaluate("document.documentElement.dataset.theme || 'fresh'") == "fresh")
    seen = {}
    for t in THEMES:
        set_theme(page, t)
        bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        pri = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--primary').trim()")
        seen[t] = (bg, pri)
        check(f"{t}: paints", bool(bg), f"body {bg}, --primary {pri}")
    check("all four palettes differ", len(set(seen.values())) == len(THEMES),
          len(set(seen.values())))
    # the repaint has to be real, not just a different attribute
    check("fresh is no longer the old beige paper",
          seen["fresh"][0] != seen["heritage"][0],
          f"{seen['fresh'][0]} vs {seen['heritage'][0]}")
    check("heritage still restores the original green", seen["heritage"][1] == "#2C5548",
          seen["heritage"][1])

    print("\n3. The choice is remembered, and carries to the other surfaces")
    set_theme(page, "forest")
    page.reload(); page.wait_for_selector(".protobar")
    check("survives a reload",
          page.evaluate("document.documentElement.dataset.theme") == "forest")
    check("the matching swatch is marked active",
          page.locator('[data-theme-btn="forest"].on').count() == 1)
    fresh_page = ctx.new_page()
    fresh_page.goto(PAGES["admin"]); fresh_page.wait_for_selector(".protobar")
    check("a different page opens in the saved palette",
          fresh_page.evaluate("document.documentElement.dataset.theme") == "forest")
    # and no flash of the default: the attribute is set before the stylesheet
    check("set before first paint (inline head script)",
          "sparrow-theme" in fresh_page.content()[:3000]
          or "sparrow-theme" in fresh_page.evaluate("document.head.innerHTML"))
    fresh_page.close()
    set_theme(page, "fresh")

    print("\n4. Dark palette actually inverts, it does not just tint")
    set_theme(page, "forest")
    lum = page.evaluate("""() => {
        const m = getComputedStyle(document.body).backgroundColor.match(/\\d+/g);
        return (+m[0] + +m[1] + +m[2]) / 3; }""")
    check("forest background is dark", lum < 60, round(lum, 1))
    inkl = page.evaluate("""() => {
        const m = getComputedStyle(document.body).color.match(/\\d+/g);
        return (+m[0] + +m[1] + +m[2]) / 3; }""")
    check("forest text is light", inkl > 180, round(inkl, 1))

    print("\n5. Contrast audit — every palette, real rendered text")
    for p in pages.values():
        freeze(p)
    for theme in THEMES:
        print(f"  -- {theme}")
        for p in pages.values():
            set_theme(p, theme)
        for name, prep in SETUP.items():
            prep(pages[name])
            set_theme(pages[name], theme)   # render() rebuilds the chrome
            freeze(pages[name])             # ...and drops the frozen styles
        for pname, sel, label, floor in AUDIT:
            p = pages[pname]
            r = p.evaluate(CONTRAST_JS, sel)
            if r is None:
                check(f"{theme}/{label}: element present", False, sel)
                continue
            check(f"{theme}/{label} >= {floor}", r["ratio"] >= floor,
                  f'{r["ratio"]}:1  "{r["text"]}"')

    print("\n6. The accent rotation gives the tiles four different colours")
    for p in pages.values():
        set_theme(p, "fresh")
    for sel, what in [(".svc", "service tiles"), (".stat", "stat tiles")]:
        src = pages["index"] if sel == ".svc" else pages["dashboard"]
        accents = src.evaluate("""s =>
            [...document.querySelectorAll(s)].slice(0, 4)
              .map(e => [getComputedStyle(e).getPropertyValue('--ac').trim(),
                         getComputedStyle(e).getPropertyValue('--ac-ink').trim()].join('/'))""", sel)
        check(f"first four {what} use four accents", len(set(accents)) == 4, accents)
    # and the icon chip must actually be painted, not inherited from the card
    chips = pages["index"].evaluate("""() =>
        [...document.querySelectorAll('.svc svg')].slice(0, 4)
          .map(e => getComputedStyle(e).backgroundColor)""")
    check("each icon sits on its own tint", len(set(chips)) == 4, chips)

    print("\n7. No JavaScript errors")
    check("errors", not errors, errors)

    browser.close()

print("\n" + "=" * 60)
if fails:
    print(f"{len(fails)} FAILED")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("all palette checks passed")
