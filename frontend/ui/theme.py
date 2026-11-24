"""
Global stylesheet for the learning-platform look.

inject_css() must run right after st.set_page_config() on every page.

Selector rules:
- Custom HTML components (frontend/ui/components.py) use the plain
  classes defined here (.course-card, .badge, ...).
- Real Streamlit widgets are styled through keyed containers:
  st.container(key="hero-controls") gets the CSS class
  .st-key-hero-controls, which is stable across Streamlit releases.
- Otherwise only data-testid / aria / data-* attributes are used,
  never generated .st-emotion-* classes.
"""

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap');

/* ============================================================
   Design tokens
   ============================================================ */
:root {
    --blue: #0056D2;
    --blue-dark: #00419E;
    --ink: #1F1F1F;
    --muted: #5B6780;
    --line: #DAE1ED;
    --band: #F0F6FF;
    --panel: #E8F0FE;
    --dark: #16181D;
    --grad-hero: linear-gradient(90deg, #5B21D6 0%, #3B3FE0 45%, #0056D2 100%);
    --grad-section: linear-gradient(90deg, #0056D2 0%, #3B3FE0 55%, #5B21D6 100%);
    --pill-border: #C1CAD9;
    --shadow-hover: 0 4px 16px rgba(0, 0, 0, .10);
    --font: "Source Sans 3", "Source Sans", -apple-system, BlinkMacSystemFont,
        "Segoe UI", Roboto, "Helvetica Neue", Arial, "Apple Color Emoji",
        "Segoe UI Emoji", "Noto Color Emoji", sans-serif;
    /* Source Sans 3 ships monochrome glyphs for some emojis (e.g. 🤖), so
       components wrap emojis in .emoji, which uses this stack first. */
    --font-emoji: "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif;
}

/* ============================================================
   Typography: everything, except icon glyphs and code
   ============================================================ */
html, body,
[data-testid="stApp"],
[data-testid="stApp"] *:not([data-testid="stIconMaterial"]):not([data-testid^="stExpanderIcon"]):not([data-testid="stIconEmoji"]):not(.emoji):not(code):not(pre):not(code *):not(pre *) {
    font-family: var(--font) !important;
}

[data-testid="stIconEmoji"],
.emoji {
    font-family: var(--font-emoji) !important;
    font-weight: 400 !important;
}

[data-testid="stApp"] {
    color: var(--ink);
}

/* ============================================================
   Streamlit chrome: header, footer, Deploy, sidebar
   ============================================================ */
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"],
footer {
    display: none !important;
}

/* The top navbar replaces the sidebar. The sidebar stays only while a
   page still keeps real controls in it (page 2's topic selector) and
   disappears automatically once it holds none. It cannot be collapsed,
   because the hidden header holds the button that would reopen it. */
[data-testid="stSidebar"]:not(:has([data-testid="stSidebarUserContent"] [data-testid="stSelectbox"])) {
    display: none !important;
}

[data-testid="stSidebarCollapseButton"],
[data-testid="stExpandSidebarButton"] {
    display: none !important;
}

[data-testid="stMain"] {
    overflow-x: hidden;
}

[data-testid="stMainBlockContainer"] {
    max-width: 1320px !important;
    margin: 0 auto !important;
    padding: 0 32px 64px !important;
}

/* Elements that only carry CSS take no space */
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] style),
[data-testid="stElementContainer"]:has(style) {
    display: none !important;
}

/* ============================================================
   Navbar (keyed container "navbar" + HTML brand/avatar)
   ============================================================ */
[data-testid="stLayoutWrapper"]:has(> .st-key-navbar),
.st-key-navbar {
    position: sticky !important;
    top: 0;
    z-index: 1000;
}

.st-key-navbar,
.navbar {
    height: 64px;
    min-height: 64px;
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 28px !important;
    padding: 0 !important;
    margin-bottom: 8px;
    background: transparent;
}

/* Full-bleed white bar behind the 1320px content width */
.st-key-navbar::before {
    content: "";
    position: absolute;
    top: 0;
    bottom: 0;
    left: 50%;
    width: 100vw;
    transform: translateX(-50%);
    background: #FFFFFF;
    border-bottom: 1px solid var(--line);
    z-index: -1;
}

.navbar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    color: var(--blue);
    font-weight: 700;
    font-size: 20px;
    letter-spacing: -0.01em;
    white-space: nowrap;
}

.navbar-brand .navbar-logo {
    font-size: 24px;
    line-height: 1;
}

.st-key-navbar [data-testid="stPageLink-NavLink"] {
    padding: 8px 16px !important;
    border-radius: 999px !important;
    background: transparent;
    transition: background-color .15s ease;
}

.st-key-navbar [data-testid="stPageLink-NavLink"] p {
    color: var(--ink) !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    white-space: nowrap;
}

.st-key-navbar [data-testid="stPageLink-NavLink"]:hover {
    background: #F2F5FA !important;
}

[class*="st-key-navlink-active-"] [data-testid="stPageLink-NavLink"] {
    background: var(--panel) !important;
}

[class*="st-key-navlink-active-"] [data-testid="stPageLink-NavLink"] p {
    color: var(--blue) !important;
}

.navbar-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: var(--dark);
    color: #FFFFFF;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 15px;
}

.st-key-navbar-signout button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 6px 8px !important;
    min-height: 0 !important;
}

.st-key-navbar-signout button p {
    color: var(--muted) !important;
    font-weight: 600 !important;
}

.st-key-navbar-signout button:hover p {
    color: var(--blue) !important;
}

/* ============================================================
   Full-bleed bands and banners
   ============================================================ */
.welcome-band {
    position: relative;
    isolation: isolate;  /* keeps the ::before band above the page background */
    padding: 32px 0 28px;
    margin-bottom: 8px;
}

.welcome-band::before {
    content: "";
    position: absolute;
    top: 0;
    bottom: 0;
    left: 50%;
    width: 100vw;
    transform: translateX(-50%);
    background: var(--band);
    z-index: -1;
}

.welcome-band h1,
.welcome-band .welcome-title {
    font-size: 28px;
    font-weight: 600;
    line-height: 1.25;
    color: var(--ink);
    margin: 0;
    padding: 0;
}

.welcome-band .welcome-subtitle {
    margin-top: 6px;
    font-size: 16px;
    color: var(--ink);
}

.welcome-band .welcome-caption {
    margin-top: 4px;
    font-size: 14px;
    color: var(--muted);
}

/* Gradient banner holding real widgets (keyed container) */
.st-key-hero-controls,
.hero-banner {
    background: var(--grad-hero) !important;
    border-radius: 24px !important;
    padding: 32px !important;
    border: none !important;
    color: #FFFFFF;
}

.hero-banner-title {
    font-size: 32px;
    font-weight: 700;
    line-height: 1.2;
    color: #FFFFFF;
    letter-spacing: -0.01em;
}

.hero-banner-text {
    margin-top: 8px;
    font-size: 16px;
    color: rgba(255, 255, 255, .9);
}

.st-key-hero-controls [data-testid="stWidgetLabel"] p,
.st-key-hero-controls [data-testid="stMarkdownContainer"] p,
.st-key-hero-controls [data-testid="stCaptionContainer"] {
    color: #FFFFFF !important;
}

/* The selectbox's visible box is the div that directly holds its
   <input> (1.67 renders no data-baseweb attributes here). */
.st-key-hero-controls [data-testid="stTextInputRootElement"],
.st-key-hero-controls [data-testid="stTextAreaRootElement"],
.st-key-hero-controls [data-testid="stSelectbox"] div:has(> input) {
    background: transparent !important;
    border: 1px solid rgba(255, 255, 255, .6) !important;
    border-radius: 6px !important;
}

.st-key-hero-controls [data-testid="stTextInputRootElement"] :is(div, input),
.st-key-hero-controls [data-testid="stTextAreaRootElement"] :is(div, textarea),
.st-key-hero-controls [data-testid="stSelectbox"] div:has(> input) * {
    background: transparent !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF;
}

.st-key-hero-controls [data-testid="stSelectbox"] div:has(> input) ~ * {
    color: #FFFFFF !important;
}

.st-key-hero-controls :is(input, textarea)::placeholder {
    color: rgba(255, 255, 255, .7) !important;
    -webkit-text-fill-color: rgba(255, 255, 255, .7);
}

.st-key-hero-controls [data-testid="stSelectbox"] svg {
    fill: #FFFFFF !important;
}

.st-key-hero-controls :is([data-testid="stBaseButton-primary"],
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-primaryFormSubmit"],
    [data-testid="stBaseButton-secondaryFormSubmit"]) {
    background: #FFFFFF !important;
    border: 1px solid #FFFFFF !important;
    border-radius: 6px !important;
    color: var(--blue) !important;
}

.st-key-hero-controls :is([data-testid="stBaseButton-primary"],
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-primaryFormSubmit"],
    [data-testid="stBaseButton-secondaryFormSubmit"]) p {
    color: var(--blue) !important;
    font-weight: 600 !important;
}

/* Dark rail with a horizontally scrolling row of cards */
.dark-rail {
    display: grid;
    grid-template-columns: minmax(220px, 300px) minmax(0, 1fr);
    gap: 32px;
    align-items: center;
    background: var(--dark);
    color: #FFFFFF;
    border-radius: 24px;
    padding: 32px;
}

.dark-rail-title {
    font-size: 28px;
    font-weight: 600;
    line-height: 1.25;
    color: #FFFFFF;
}

.dark-rail-text {
    margin-top: 10px;
    font-size: 16px;
    line-height: 1.5;
    color: rgba(255, 255, 255, .8);
}

.rail-scroll {
    display: flex;
    gap: 16px;
    overflow-x: auto;
    padding: 4px 4px 12px;
    scroll-snap-type: x mandatory;
}

.rail-scroll > .course-card {
    flex: 0 0 260px;
    scroll-snap-align: start;
}

.rail-scroll::-webkit-scrollbar {
    height: 8px;
}

.rail-scroll::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, .3);
    border-radius: 999px;
}

/* ============================================================
   Course cards
   ============================================================ */
.card-grid {
    --cols: 4;
    display: grid;
    grid-template-columns: repeat(var(--cols), minmax(0, 1fr));
    gap: 20px;
}

/* Responsive card grids: full column count from 1000px, 2 columns
   below 1000px, 1 column below 640px. */
@media (max-width: 999px) {
    .card-grid { --cols: 2 !important; }
    .dark-rail { grid-template-columns: 1fr; }
}

@media (max-width: 639px) {
    .card-grid { --cols: 1 !important; }
}

/* Card rows built from st.columns: interactive topic cards
   (key "card-..."), KPI cards ("kpi-..."), review-history cards
   ("lp_card_history_...") and HTML .course-card evidence cards.
   Only columns whose DIRECT content is a card match, so columns nested
   around card rows (e.g. the dark rail) are left alone.
   - every card in a row stretches to the row's tallest card;
   - 640-999px: card rows wrap to 2 per row (below 640px Streamlit
     already stacks columns one per row). KPI rows keep their layout. */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > :is([class*="st-key-card-"], [class*="st-key-ev-"])),
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-lp_card_history_"]),
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-kpi-"]),
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] .course-card) {
    align-items: stretch !important;
}

[data-testid="stColumn"]:has(> [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > :is([class*="st-key-card-"], [class*="st-key-ev-"])),
[data-testid="stColumn"]:has(> [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-lp_card_history_"]),
[data-testid="stColumn"]:has(> [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-kpi-"]),
[data-testid="stColumn"]:has(> [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] .course-card) {
    display: flex !important;
    flex-direction: column !important;
}

[data-testid="stColumn"] > [data-testid="stVerticalBlock"]:has(> [data-testid="stLayoutWrapper"] > :is(:is([class*="st-key-card-"], [class*="st-key-ev-"]), [class*="st-key-lp_card_history_"], [class*="st-key-kpi-"])),
[data-testid="stColumn"] > [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .course-card) {
    flex: 1 1 auto;
}

[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:has(> :is(:is([class*="st-key-card-"], [class*="st-key-ev-"]), [class*="st-key-lp_card_history_"], [class*="st-key-kpi-"])) {
    flex: 1 1 auto;
    display: flex !important;
    flex-direction: column !important;
}

[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > :is(:is([class*="st-key-card-"], [class*="st-key-ev-"]), [class*="st-key-lp_card_history_"], [class*="st-key-kpi-"]) {
    flex: 1 1 auto;
}

/* HTML evidence cards: stretch every wrapper between column and card */
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(.course-card),
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(.course-card) :has(.course-card) {
    display: flex !important;
    flex-direction: column !important;
    flex: 1 1 auto;
}

[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] .course-card {
    flex: 1 1 auto;
}

/* KPI cards fill their keyed container */
[class*="st-key-kpi-"] > [data-testid="stElementContainer"]:has([data-testid="stMetric"]) {
    flex: 1 1 auto;
}

[class*="st-key-kpi-"] [data-testid="stMetric"] {
    height: 100%;
    box-sizing: border-box;
}

@media (min-width: 640px) and (max-width: 999px) {
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > :is([class*="st-key-card-"], [class*="st-key-ev-"])),
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-lp_card_history_"]),
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] .course-card) {
        flex-wrap: wrap !important;
    }

    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > :is([class*="st-key-card-"], [class*="st-key-ev-"])) > [data-testid="stColumn"],
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-lp_card_history_"]) > [data-testid="stColumn"],
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] .course-card) > [data-testid="stColumn"] {
        flex: 1 1 calc(50% - 1rem) !important;
        min-width: calc(50% - 1rem) !important;
        max-width: calc(50% - 0.5rem) !important;
    }

    /* A short last row leaves empty columns; don't let them hold a slot */
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > :is([class*="st-key-card-"], [class*="st-key-ev-"])) > [data-testid="stColumn"]:not(:has([data-testid="stElementContainer"])),
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-lp_card_history_"]) > [data-testid="stColumn"]:not(:has([data-testid="stElementContainer"])),
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] .course-card) > [data-testid="stColumn"]:not(:has([data-testid="stElementContainer"])) {
        display: none !important;
    }
}

.course-card {
    display: flex;
    flex-direction: column;
    gap: 10px;
    background: #FFFFFF;
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 10px;
    color: var(--ink);
    transition: box-shadow .2s ease, transform .2s ease;
}

.course-card:hover {
    box-shadow: var(--shadow-hover);
}

.thumb {
    position: relative;
    height: 160px;
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    align-items: flex-end;
    padding: 12px;
}

/* Abstract network: nodes, links and a dot grid, all CSS gradients */
.thumb::before {
    content: "";
    position: absolute;
    inset: 0;
    background:
        radial-gradient(circle at 18% 28%, rgba(255,255,255,.55) 0 4px, transparent 5px),
        radial-gradient(circle at 46% 18%, rgba(255,255,255,.45) 0 3px, transparent 4px),
        radial-gradient(circle at 72% 40%, rgba(255,255,255,.55) 0 5px, transparent 6px),
        radial-gradient(circle at 34% 62%, rgba(255,255,255,.4) 0 3px, transparent 4px),
        radial-gradient(circle at 84% 72%, rgba(255,255,255,.45) 0 4px, transparent 5px),
        radial-gradient(circle at 60% 82%, rgba(255,255,255,.3) 0 2px, transparent 3px),
        linear-gradient(28deg, transparent 47%, rgba(255,255,255,.22) 48%, rgba(255,255,255,.22) 49%, transparent 50%),
        linear-gradient(-34deg, transparent 49%, rgba(255,255,255,.18) 50%, rgba(255,255,255,.18) 51%, transparent 52%),
        radial-gradient(rgba(255,255,255,.16) 1px, transparent 1.6px) 0 0 / 14px 14px;
}

.thumb::after {
    content: "";
    position: absolute;
    width: 180px;
    height: 180px;
    right: -50px;
    top: -60px;
    border-radius: 50%;
    background: rgba(255, 255, 255, .12);
}

.thumb-label {
    position: relative;
    z-index: 1;
    color: #FFFFFF;
    font-weight: 700;
    font-size: 18px;
    line-height: 1.2;
    text-shadow: 0 1px 2px rgba(0, 0, 0, .2);
}

.thumb-chip {
    position: absolute;
    z-index: 1;
    top: 10px;
    left: 10px;
    padding: 2px 10px;
    border-radius: 999px;
    background: #FFFFFF;
    color: var(--ink);
    font-size: 12px;
    font-weight: 600;
}

.provider-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--muted);
}

.logo-box {
    width: 24px;
    height: 24px;
    flex: 0 0 24px;
    border: 1px solid var(--line);
    border-radius: 4px;
    background: #FFFFFF;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
    color: var(--blue);
}

.course-title {
    font-size: 16px;
    font-weight: 600;
    line-height: 1.3;
    color: var(--ink);
}

.meta {
    font-size: 13px;
    color: var(--muted);
    line-height: 1.4;
}

/* ============================================================
   Badges and pills
   ============================================================ */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    width: fit-content;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    line-height: 1.6;
    white-space: nowrap;
}

.badge-purple { background: #EFE7FF; color: #5B21B6; }
.badge-pink { background: #FDE8EC; color: #B4233C; }
.badge-green { background: #DFF5E6; color: #1E6B34; }
.badge-yellow { background: #FFF1C2; color: #7A5B00; }
.badge-outline { background: #FFFFFF; color: var(--ink); border: 1px solid var(--pill-border); }

/* ============================================================
   Panels, strips and feature cards
   ============================================================ */
.section-title {
    font-size: 28px;
    font-weight: 600;
    line-height: 1.25;
    color: var(--ink);
    margin: 24px 0 12px;
}

.trend-panel {
    background: var(--panel);
    border-radius: 16px;
    padding: 24px;
}

.trend-panel-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--ink);
    margin-bottom: 16px;
}

.trend-panel-title .arrow {
    color: var(--blue);
    margin-left: 6px;
}

.info-strip {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px 10px;
    background: var(--panel);
    border-radius: 12px;
    padding: 14px 20px;
    font-size: 15px;
    color: var(--ink);
}

.info-strip strong {
    font-weight: 700;
}

.link-blue,
a.link-blue {
    color: var(--blue) !important;
    font-weight: 600;
    text-decoration: none;
}

a.link-blue:hover {
    text-decoration: underline;
}

.btn-outline {
    display: inline-flex;
    align-items: center;
    padding: 8px 18px;
    border: 1px solid var(--blue);
    border-radius: 4px;
    background: #FFFFFF;
    color: var(--blue) !important;
    font-weight: 600;
    text-decoration: none;
}

.feature-card {
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
    gap: 32px;
    align-items: center;
    background: #FFFFFF;
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 28px;
    transition: box-shadow .2s ease;
}

.feature-card:hover {
    box-shadow: var(--shadow-hover);
}

.feature-main {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.feature-title {
    font-size: 24px;
    font-weight: 600;
    line-height: 1.25;
    color: var(--ink);
}

.feature-skills {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.feature-rating {
    font-size: 14px;
    font-weight: 600;
    color: var(--ink);
}

.feature-rating .star {
    color: #F5B301;
}

.step-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 12px;
}

.step-thumb {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.step-thumb .thumb {
    height: 96px;
    padding: 8px;
}

.step-thumb .thumb-label {
    font-size: 13px;
}

.step-caption {
    font-size: 12px;
    color: var(--muted);
}

@media (max-width: 999px) {
    .feature-card { grid-template-columns: 1fr; }
}

/* ============================================================
   Real widgets
   ============================================================ */
/* Chips: st.pills / st.segmented_control whose key (or enclosing
   container key) starts with "chips", e.g. key="chips" or
   key="chips_review_decision".
   In Streamlit 1.67 these buttons carry no data-testid; their state is
   exposed through the aria-checked attribute. */
:is([class*="st-key-chips"], [class*="st-key-up_chips"], .st-key-grid_filter, .st-key-grid_sort, .st-key-ev_view, .st-key-ev_sort) [data-testid="stButtonGroup"] button {
    border-radius: 999px !important;
    background: #FFFFFF !important;
    border: 1px solid var(--pill-border) !important;
    color: var(--ink) !important;
    padding: 6px 16px !important;
    margin: 0 !important;
    box-shadow: none !important;
}

:is([class*="st-key-chips"], [class*="st-key-up_chips"], .st-key-grid_filter, .st-key-grid_sort, .st-key-ev_view, .st-key-ev_sort) [data-testid="stButtonGroup"] button:hover {
    border-color: var(--ink) !important;
}

:is([class*="st-key-chips"], [class*="st-key-up_chips"], .st-key-grid_filter, .st-key-grid_sort, .st-key-ev_view, .st-key-ev_sort) [data-testid="stButtonGroup"] button[aria-checked="true"] {
    background: var(--ink) !important;
    border-color: var(--ink) !important;
    color: #FFFFFF !important;
}

:is([class*="st-key-chips"], [class*="st-key-up_chips"], .st-key-grid_filter, .st-key-grid_sort, .st-key-ev_view, .st-key-ev_sort) [data-testid="stButtonGroup"] button :is(p, span) {
    color: inherit !important;
    font-weight: 600 !important;
}

/* Segmented control normally joins its buttons; space them as pills */
:is([class*="st-key-chips"], [class*="st-key-up_chips"], .st-key-grid_filter, .st-key-grid_sort, .st-key-ev_view, .st-key-ev_sort) [data-testid="stButtonGroup"] div:has(> button) {
    gap: 8px !important;
    flex-wrap: wrap;
}

/* "Show more" button inside key="show-more" */
.st-key-show-more button {
    background: #FFFFFF !important;
    border: 1px solid var(--blue) !important;
    border-radius: 4px !important;
    color: var(--blue) !important;
    padding: 8px 20px !important;
}

.st-key-show-more button p {
    color: var(--blue) !important;
    font-weight: 600 !important;
}

.st-key-show-more button:hover {
    background: var(--panel) !important;
}

/* Primary buttons everywhere */
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primaryFormSubmit"] {
    background: var(--blue) !important;
    border: 1px solid var(--blue) !important;
    border-radius: 4px !important;
    color: #FFFFFF !important;
}

[data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-primaryFormSubmit"] p {
    color: #FFFFFF !important;
    font-weight: 600 !important;
}

[data-testid="stBaseButton-primary"]:hover,
[data-testid="stBaseButton-primaryFormSubmit"]:hover {
    background: var(--blue-dark) !important;
    border-color: var(--blue-dark) !important;
}

/* Disabled buttons must look disabled (e.g. "Generate Learning
   Insights" for view-only accounts), including inside the banners. */
:is([data-testid="stBaseButton-primary"],
    [data-testid="stBaseButton-primaryFormSubmit"],
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-secondaryFormSubmit"]):disabled,
:is([data-testid="stBaseButton-primary"],
    [data-testid="stBaseButton-primaryFormSubmit"],
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-secondaryFormSubmit"]):disabled:hover {
    background: #E9EDF3 !important;
    border-color: var(--line) !important;
    color: #7A8499 !important;
    cursor: not-allowed !important;
}

:is([data-testid="stBaseButton-primary"],
    [data-testid="stBaseButton-primaryFormSubmit"],
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-secondaryFormSubmit"]):disabled p {
    color: #7A8499 !important;
}

/* Expanders, forms and dataframes as white cards */
[data-testid="stExpander"] details,
[data-testid="stForm"] {
    background: #FFFFFF !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
    transition: box-shadow .2s ease;
}

[data-testid="stExpander"] details:hover,
[data-testid="stForm"]:hover {
    box-shadow: var(--shadow-hover);
}

[data-testid="stExpander"] summary p {
    font-weight: 600 !important;
}

/* ============================================================
   Dashboard sections built from real widgets (keyed containers)
   ============================================================ */
.card-title {
    font-size: 20px;
    font-weight: 600;
    line-height: 1.3;
    color: var(--ink);
    margin-bottom: 4px;
}

/* Gradient section (blue -> purple) holding the AI assistant */
.st-key-ai-section {
    background: var(--grad-section) !important;
    border-radius: 24px !important;
    padding: 32px !important;
    margin-top: 16px;
    border: none !important;
}

.st-key-ai-section .hero-banner-title {
    font-size: 28px;
}

.st-key-ai-card {
    background: #FFFFFF !important;
    border-radius: 16px !important;
    padding: 20px !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, .12);
}

/* Large white feature cards built from real widgets:
   st.container(key="feature-<name>"), e.g. the video card and the
   question card on the Educator Assistant page. */
[class*="st-key-feature-"] {
    background: #FFFFFF !important;
    border: 1px solid var(--line) !important;
    border-radius: 16px !important;
    padding: 28px !important;
    transition: box-shadow .2s ease;
}

[class*="st-key-feature-"]:hover {
    box-shadow: var(--shadow-hover);
}

[class*="st-key-feature-"] [data-testid="stVideo"] {
    border-radius: 12px;
    overflow: hidden;
}

/* Thumbnails showing a real image instead of a gradient */
.thumb-image::before {
    background: linear-gradient(180deg, transparent 45%, rgba(0, 0, 0, .65) 100%);
}

.thumb-image::after {
    display: none;
}

/* Student comments */
.comment-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.comment-row {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    height: 100%;
    box-sizing: border-box;
}

.comment-text {
    font-size: 15px;
    line-height: 1.45;
    color: var(--ink);
}

.comment-meta {
    font-size: 12px;
    color: var(--muted);
}

.trend-panel .card-grid {
    gap: 12px;
}

/* Review-history cards */
.review-summary {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 14px;
    color: var(--ink);
}

.review-summary .badge {
    margin-bottom: 4px;
}

.review-label {
    color: var(--muted);
    font-weight: 600;
}

.review-line {
    line-height: 1.4;
    overflow-wrap: anywhere;
}

[data-testid="stDataFrame"] {
    background: #FFFFFF;
    border: 1px solid var(--line);
    border-radius: 12px;
    overflow: hidden;
}

[data-testid="stAlertContainer"] {
    border-radius: 12px !important;
}

/* ============================================================
   White cards from real widgets: st.container(border=True,
   key="lp_card_<name>") and st.metric (KPI cards)
   ============================================================ */
[class*="st-key-lp_card_"],
[data-testid="stMetric"] {
    background: #FFFFFF !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
    transition: box-shadow .2s ease;
}

[class*="st-key-lp_card_"] {
    padding: 24px !important;
}

[data-testid="stMetric"] {
    padding: 18px 22px !important;
}

[class*="st-key-lp_card_"]:hover,
[data-testid="stMetric"]:hover {
    box-shadow: var(--shadow-hover);
}

[data-testid="stMetricLabel"] p {
    color: var(--muted) !important;
    font-weight: 600 !important;
}

[data-testid="stMetricValue"],
[data-testid="stMetricValue"] > div {
    font-size: 30px !important;
    font-weight: 700 !important;
}

[data-testid="stMarkdownContainer"] > hr:only-child {
    border: none !important;
    margin: 4px 0 !important;
}

/* ============================================================
   Interactive cards (components.topic_card / clickable_metric)
   Card    = st.container(key="card-<location>-<topic_id>")
   Overlay = st.button(key="cardsel-...")  transparent, covers the card
   Actions = st.container(key="cardact-...") real buttons above it
   ============================================================ */
:is([class*="st-key-card-"], [class*="st-key-ev-"]) {
    position: relative !important;
    background: #FFFFFF !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
    padding: 10px !important;
    gap: 10px !important;
    cursor: pointer;
    transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
}

:is([class*="st-key-card-"], [class*="st-key-ev-"]):hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 24px rgba(0, 0, 0, .14);
}

/* Selected card: blue ring and glow */
:is([class*="st-key-card-"], [class*="st-key-ev-"]):has(.selected-pill) {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 2px var(--blue), 0 0 0 7px rgba(0, 86, 210, .16);
}

:is([class*="st-key-card-"], [class*="st-key-ev-"]):has(.selected-pill):hover {
    box-shadow: 0 0 0 2px var(--blue), 0 0 0 7px rgba(0, 86, 210, .16),
        0 10px 24px rgba(0, 0, 0, .14);
}

.topic-card-body {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

/* Streamlit gives every Markdown block margin-bottom:-16px; inside a
   card that would pull the action pills over the last line of text. */
:is([class*="st-key-card-"], [class*="st-key-ev-"]) [data-testid="stMarkdownContainer"]:has(> :is(.topic-card-body, .ev-card-body)) {
    margin-bottom: 0 !important;
}

/* Transparent overlay button stretched over the whole card */
:is([class*="st-key-cardsel-"], [class*="st-key-evsel-"]),
[class*="st-key-kpisel-"] {
    position: absolute !important;
    inset: 0 !important;
    z-index: 1;
    margin: 0 !important;
    width: auto !important;
    height: auto !important;
}

:is([class*="st-key-cardsel-"], [class*="st-key-evsel-"]) :not(p, span),
[class*="st-key-kpisel-"] :not(p, span) {
    width: 100% !important;
    height: 100% !important;
}

:is([class*="st-key-cardsel-"], [class*="st-key-evsel-"]) button,
[class*="st-key-kpisel-"] button {
    opacity: 0 !important;
    cursor: pointer !important;
    border: none !important;
    padding: 0 !important;
    min-height: 0 !important;
}

/* Keyboard focus: the overlay is invisible, so ring the whole card */
:is([class*="st-key-card-"], [class*="st-key-ev-"]):has(:is([class*="st-key-cardsel-"], [class*="st-key-evsel-"]) button:focus-visible),
[class*="st-key-kpi-"]:has([class*="st-key-kpisel-"] button:focus-visible) {
    outline: 3px solid var(--blue) !important;
    outline-offset: 3px;
}

/* Action pills sit above the overlay, at the bottom of the card */
:is([class*="st-key-cardact-"], [class*="st-key-evact-"]) {
    position: relative;
    z-index: 2;
    flex-wrap: wrap !important;
    gap: 6px !important;
    margin-top: auto;
}

:is([class*="st-key-cardact-"], [class*="st-key-evact-"]) button {
    border-radius: 999px !important;
    padding: 4px 12px !important;
    min-height: 0 !important;
    background: #FFFFFF !important;
    border: 1px solid var(--pill-border) !important;
    transition: background-color .15s ease, border-color .15s ease;
}

:is([class*="st-key-cardact-"], [class*="st-key-evact-"]) button p {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: var(--ink) !important;
}

:is([class*="st-key-cardact-"], [class*="st-key-evact-"]) button:hover {
    background: var(--panel) !important;
    border-color: var(--blue) !important;
}

:is([class*="st-key-cardact-"], [class*="st-key-evact-"]) button:hover p {
    color: var(--blue) !important;
}

:is(:is([class*="st-key-cardact-"], [class*="st-key-evact-"]), .st-key-rail_prev, .st-key-rail_next, .st-key-dialog-actions,
    .st-key-grid_clear) button:focus-visible {
    outline: 2px solid var(--blue) !important;
    outline-offset: 2px;
}

/* "✓ Selected" pill on the thumbnail */
.selected-pill {
    position: absolute;
    z-index: 2;
    top: 10px;
    right: 10px;
    padding: 2px 10px;
    border-radius: 999px;
    background: var(--blue);
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 700;
    box-shadow: 0 2px 6px rgba(0, 0, 0, .2);
}

/* Thumbnail hover: pattern zoom + details sliding up */
.thumb::before {
    transition: transform .35s ease;
}

:is([class*="st-key-card-"], [class*="st-key-ev-"]):hover .thumb::before {
    transform: scale(1.06);
}

.thumb-hover {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 3;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px 12px;
    background: linear-gradient(180deg, rgba(22, 24, 29, .55), rgba(22, 24, 29, .92));
    color: #FFFFFF;
    transform: translateY(100%);
    transition: transform .25s ease;
}

/* Keyboard focus also reveals it; plain :focus-within would keep it
   open on a card after a mouse click (the overlay button keeps focus). */
:is([class*="st-key-card-"], [class*="st-key-ev-"]):hover .thumb-hover,
:is([class*="st-key-card-"], [class*="st-key-ev-"]):has(button:focus-visible) .thumb-hover {
    transform: translateY(0);
}

.thumb-hover-row {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
}

.thumb-hover-cta {
    font-size: 12px;
    font-weight: 600;
}

.thumb-hover .progress {
    background: rgba(255, 255, 255, .25);
}

.thumb-hover .progress-fill {
    background: #FFFFFF;
}

/* Progress bars animate from 0 to their value */
.progress-wrap {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.progress-label {
    display: flex;
    justify-content: space-between;
    font-size: 14px;
    color: var(--muted);
}

.progress-label strong {
    color: var(--ink);
}

.progress {
    height: 6px;
    border-radius: 999px;
    background: #E6ECF5;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    width: var(--value);
    border-radius: inherit;
    background: var(--blue);
    animation: lp-grow .9s cubic-bezier(.2, .8, .2, 1) both;
}

@keyframes lp-grow {
    from { width: 0; }
    to { width: var(--value); }
}

/* Clickable KPI cards */
[class*="st-key-kpi-"] {
    position: relative !important;
    gap: 0 !important;
    transition: transform .2s ease;
}

[class*="st-key-kpi-"]:hover {
    transform: translateY(-4px);
}

[class*="st-key-kpi-"]:hover [data-testid="stMetric"] {
    box-shadow: 0 10px 24px rgba(0, 0, 0, .14);
}

/* ============================================================
   Dark rail carousel (key="rail")
   ============================================================ */
.st-key-rail {
    background: var(--dark) !important;
    border-radius: 24px !important;
    padding: 32px !important;
    color: #FFFFFF;
}

.st-key-rail-controls {
    margin-top: 4px;
}

.rail-dots {
    display: flex;
    align-items: center;
    gap: 8px;
}

.rail-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: rgba(255, 255, 255, .35);
    transition: width .2s ease, background-color .2s ease;
}

.rail-dot.is-active {
    width: 22px;
    background: #FFFFFF;
}

.st-key-rail_prev button,
.st-key-rail_next button {
    width: 44px !important;
    height: 44px !important;
    min-height: 44px !important;
    padding: 0 !important;
    border-radius: 50% !important;
    background: #FFFFFF !important;
    border: none !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, .25);
}

.st-key-rail_prev button p,
.st-key-rail_next button p {
    font-size: 24px !important;
    line-height: 1 !important;
    font-weight: 700 !important;
    color: var(--ink) !important;
    margin-top: -3px;
}

.st-key-rail_prev button:hover,
.st-key-rail_next button:hover {
    background: var(--panel) !important;
}

.st-key-rail_prev button:disabled,
.st-key-rail_next button:disabled {
    background: rgba(255, 255, 255, .16) !important;
    box-shadow: none;
}

.st-key-rail_prev button:disabled p,
.st-key-rail_next button:disabled p {
    color: rgba(255, 255, 255, .45) !important;
}

/* ============================================================
   Grid toolbar, empty state and interactive chart
   ============================================================ */
.st-key-grid_search [data-testid="stTextInputRootElement"] {
    border-radius: 999px !important;
    border: 1px solid var(--pill-border) !important;
    background: #FFFFFF !important;
}

.st-key-grid_search [data-testid="stTextInputRootElement"]:focus-within {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px rgba(0, 86, 210, .15);
}

.st-key-grid-empty {
    background: #FFFFFF !important;
    border: 1px dashed var(--pill-border) !important;
    border-radius: 12px !important;
    padding: 32px !important;
    align-items: center !important;
}

.empty-state-text {
    font-size: 16px;
    color: var(--muted);
    text-align: center;
}

/* ============================================================
   Quick-view dialog (components.topic_dialog)
   ============================================================ */
.dialog-head {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
}

.dialog-title {
    font-size: 24px;
    font-weight: 600;
    color: var(--ink);
}

.mini-kpis {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
}

.mini-kpi {
    background: var(--band);
    border-radius: 12px;
    padding: 12px 14px;
}

.mini-kpi-label {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .04em;
    color: var(--muted);
}

.mini-kpi-value {
    font-size: 24px;
    font-weight: 700;
    color: var(--ink);
}

.bar-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 12px;
}

.bar-row {
    display: grid;
    grid-template-columns: minmax(80px, 140px) minmax(0, 1fr) auto;
    align-items: center;
    gap: 10px;
    font-size: 14px;
}

.bar-value {
    font-weight: 600;
}

div[role="dialog"] .comment-row {
    background: var(--band);
}

@media (max-width: 639px) {
    .mini-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

/* ============================================================
   Scrolling: anchors clear the sticky navbar; the zero-height
   scroll helper (components.scroll_to) takes no space
   ============================================================ */
#topic-explorer,
#topic-difficulty,
#topic-grid,
#student-feedback,
#ai-assistant {
    scroll-margin-top: 96px;
}

[data-testid="stLayoutWrapper"]:has(> .st-key-scroll-helper),
.st-key-scroll-helper {
    position: absolute !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
    pointer-events: none;
}

/* ============================================================
   Evidence explorer (components.evidence_*)
   Card    = st.container(key="ev-<page>-<reference>")  (shares the
             topic-card styles above: lift, overlay, action pills)
   Row     = st.container(key="evrow-<page>-<reference>")
   ============================================================ */
.ev-card-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

/* Pinned cards: filled ★ in the chip and a blue ring */
[class*="st-key-ev-"]:has(.ev-card-body.is-pinned) {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 2px var(--blue), 0 0 0 7px rgba(0, 86, 210, .16);
}

.ev-thumb {
    height: 128px;
    align-items: flex-end;
}

.ev-icon {
    position: absolute;
    z-index: 1;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -58%);
    font-size: 44px;
    line-height: 1;
    color: #FFFFFF;
    opacity: .95;
    text-shadow: 0 2px 10px rgba(0, 0, 0, .25);
    transition: transform .25s ease;
}

[class*="st-key-ev-"]:hover .ev-icon {
    transform: translate(-50%, -58%) scale(1.15);
}

.ev-corner {
    position: absolute;
    z-index: 2;
    top: 10px;
    right: 10px;
    max-width: 60%;
    padding: 2px 10px;
    border-radius: 999px;
    background: rgba(22, 24, 29, .55);
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.ev-name {
    font-size: 15px;
    font-weight: 600;
    line-height: 1.35;
    color: var(--ink);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    overflow-wrap: anywhere;
}

/* 2-line preview that fades to "Click to read →" on hover */
.ev-preview {
    position: relative;
    min-height: 2.8em;
    font-size: 13px;
    line-height: 1.4;
}

.ev-preview-text {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    color: var(--muted);
    transition: opacity .2s ease;
}

.ev-preview-cta {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    color: var(--blue);
    font-weight: 600;
    opacity: 0;
    transition: opacity .2s ease;
}

[class*="st-key-ev-"]:hover .ev-preview-text {
    opacity: 0;
}

[class*="st-key-ev-"]:hover .ev-preview-cta {
    opacity: 1;
}

.ev-peek {
    max-width: 360px;
    font-size: 14px;
    line-height: 1.5;
    color: var(--ink);
    white-space: pre-wrap;
}

/* List view rows */
[class*="st-key-evrow-"] {
    background: #FFFFFF !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
    padding: 10px 14px !important;
    flex-wrap: nowrap !important;
    transition: box-shadow .2s ease, border-color .2s ease;
}

[class*="st-key-evrow-"]:hover {
    box-shadow: var(--shadow-hover);
    border-color: var(--pill-border) !important;
}

[class*="st-key-evrow-"]:has(.ev-row.is-pinned) {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 1px var(--blue);
}

[class*="st-key-evrow-"] > [data-testid="stElementContainer"]:first-child {
    flex: 1 1 auto;
    min-width: 0;
}

[class*="st-key-evrow-"] [data-testid="stMarkdownContainer"]:has(> .ev-row) {
    margin-bottom: 0 !important;
}

.ev-row {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
}

.ev-row-icon {
    width: 36px;
    height: 36px;
    flex: 0 0 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #FFFFFF;
    font-size: 18px;
}

.ev-row-ref {
    flex: 0 0 auto;
    min-width: 34px;
    font-weight: 700;
    color: var(--ink);
}

.ev-row-main {
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.ev-row-name,
.ev-row-preview {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.ev-row-name {
    font-size: 14px;
    font-weight: 600;
    color: var(--ink);
}

.ev-row-preview {
    font-size: 13px;
    color: var(--muted);
}

.ev-row-dot {
    flex: 0 0 10px;
    width: 10px;
    height: 10px;
    margin-left: auto;
    border-radius: 50%;
    border: 2px solid var(--pill-border);
}

.ev-row-dot.is-cited {
    background: #2BB673;
    border-color: #2BB673;
}

[class*="st-key-evrowread-"] button,
[class*="st-key-evcite-"] button {
    border-radius: 999px !important;
    padding: 4px 14px !important;
    min-height: 0 !important;
    background: #FFFFFF !important;
    border: 1px solid var(--pill-border) !important;
}

[class*="st-key-evrowread-"] button p,
[class*="st-key-evcite-"] button p {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: var(--ink) !important;
}

[class*="st-key-evrowread-"] button:hover,
[class*="st-key-evcite-"] button:hover {
    border-color: var(--blue) !important;
    background: var(--panel) !important;
}

[class*="st-key-evcites-"] {
    flex-wrap: wrap !important;
    margin-top: 4px;
}

.ev-cites-label {
    font-size: 14px;
    font-weight: 600;
    color: var(--muted);
    margin-right: 4px;
}

.st-key-evempty {
    background: #FFFFFF !important;
    border: 1px dashed var(--pill-border) !important;
    border-radius: 12px !important;
    padding: 32px !important;
    align-items: center !important;
}

:is([class*="st-key-evrowread-"], [class*="st-key-evcite-"], [class*="st-key-evdlg-actions-"],
    .st-key-ev_clear) button:focus-visible {
    outline: 2px solid var(--blue) !important;
    outline-offset: 2px;
}

/* Evidence dialog */
div[role="dialog"] [data-testid="stVerticalBlock"] {
    animation: lp-fade-in .25s ease both;
}

@keyframes lp-fade-in {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: none; }
}

.ev-dialog-head {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
}

.ev-dialog-ref {
    padding: 2px 10px;
    border-radius: 999px;
    color: #FFFFFF;
    font-weight: 700;
    font-size: 13px;
}

.ev-modality-badge {
    background: #FFFFFF;
    border: 1px solid;
}

.ev-dialog-name {
    margin-top: 6px;
    font-size: 22px;
    font-weight: 600;
    line-height: 1.3;
    color: var(--ink);
    overflow-wrap: anywhere;
}

.ev-dialog-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 18px;
    font-size: 13px;
    color: var(--muted);
    overflow-wrap: anywhere;
}

.ev-dialog-meta b {
    color: var(--ink);
    font-weight: 600;
}

.ev-label,
.ev-time {
    font-size: 13px;
    font-weight: 600;
    color: var(--muted);
    margin-bottom: 4px;
}

.ev-text {
    font-size: 15px;
    line-height: 1.6;
    color: var(--ink);
    overflow-wrap: anywhere;
}

.ev-text mark,
.ev-bubble mark {
    background: #FFF1C2;
    color: inherit;
    padding: 0 2px;
    border-radius: 3px;
}

.ev-bubble {
    position: relative;
    background: var(--band);
    border-radius: 16px 16px 16px 4px;
    padding: 16px 18px;
}

.ev-bubble-text {
    font-size: 17px;
    line-height: 1.5;
    color: var(--ink);
}

.ev-bubble-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 10px;
    font-size: 13px;
    color: var(--muted);
}

.ev-doc {
    background: #FFFFFF;
    border: 1px solid var(--line);
    border-left: 4px solid #6D28D9;
    border-radius: 8px;
    padding: 18px 22px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, .06);
}

.ev-doc-head {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: .04em;
    text-transform: uppercase;
    color: #6D28D9;
    margin-bottom: 8px;
}

.ev-position {
    font-size: 13px;
    color: var(--muted);
    white-space: nowrap;
}

/* ============================================================
   "Analyse Your Own Course" (frontend/upload_section.py)
   ============================================================ */
/* Hero actions */
.st-key-up_hero_actions {
    gap: 10px !important;
}

.st-key-up_open_wizard button {
    padding: 14px 22px !important;
    border-radius: 8px !important;
    box-shadow: 0 6px 18px rgba(0, 0, 0, .18);
}

.st-key-up_open_wizard button p {
    font-size: 17px !important;
    font-weight: 700 !important;
}

.st-key-hero-controls [data-testid="stBaseButton-tertiary"] p {
    color: #FFFFFF !important;
    font-weight: 600 !important;
    text-decoration: underline;
    text-underline-offset: 3px;
}

.st-key-hero-controls [data-testid="stBaseButton-tertiary"]:hover p {
    text-decoration-thickness: 2px;
}

.up-last-pill {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    background: rgba(255, 255, 255, .18);
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
}

/* Wizard shell and stepper */
.st-key-up_wizard {
    background: #F7F9FC !important;
    border: 1px solid var(--line) !important;
    border-radius: 24px !important;
    padding: 28px !important;
    gap: 18px !important;
}

.up-stepper {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 15px;
    font-weight: 600;
    scroll-margin-top: 96px;
}

.up-step {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: var(--muted);
}

.up-step-dot {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 2px solid var(--pill-border);
    background: #FFFFFF;
    font-size: 13px;
}

.up-step.is-active { color: var(--blue); }
.up-step.is-active .up-step-dot { border-color: var(--blue); background: var(--blue); color: #FFFFFF; }
.up-step.is-done { color: var(--ink); }
.up-step.is-done .up-step-dot { border-color: #1E6B34; background: #DFF5E6; color: #1E6B34; }

.up-step-line {
    width: 56px;
    height: 2px;
    background: var(--pill-border);
}

.up-step-line.is-done { background: #2BB673; }

/* Modality upload cards */
[class*="st-key-up_card_"] {
    background: #FFFFFF !important;
    border: 1px solid var(--line) !important;
    border-radius: 16px !important;
    padding: 18px !important;
    gap: 10px !important;
    height: 100%;
    transition: box-shadow .2s ease;
}

[class*="st-key-up_card_"]:hover {
    box-shadow: var(--shadow-hover);
}

.up-card-head {
    display: flex;
    align-items: center;
    gap: 12px;
}

.up-card-icon {
    width: 44px;
    height: 44px;
    flex: 0 0 44px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #FFFFFF;
    font-size: 22px;
}

.up-card-text {
    flex: 1 1 auto;
    min-width: 0;
}

.up-card-title {
    font-size: 17px;
    font-weight: 700;
    color: var(--ink);
}

.up-card-accept {
    font-size: 12px;
    color: var(--muted);
}

.up-files {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 13px;
}

.up-file {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    padding: 6px 10px;
    border-radius: 8px;
    background: var(--band);
    color: var(--ink);
    overflow-wrap: anywhere;
}

.up-file span:last-child {
    flex: 0 0 auto;
    color: var(--muted);
}

.up-demo-tag {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .05em;
    color: #6D28D9;
}

.up-valid {
    font-size: 13px;
    font-weight: 600;
    color: #1E6B34;
}

.up-errors {
    font-size: 13px;
    color: #A1261C;
    background: #FDECEA;
    border-radius: 8px;
    padding: 8px 12px;
}

.up-errors ul {
    margin: 4px 0 0 18px;
    padding: 0;
}

.up-demo-note {
    font-size: 14px;
    color: #5B21B6;
    background: #EFE7FF;
    border-radius: 10px;
    padding: 10px 14px;
}

.st-key-up_options {
    background: #FFFFFF !important;
    border: 1px solid var(--line) !important;
    border-radius: 16px !important;
    padding: 16px 20px !important;
}

.up-hint {
    font-size: 14px;
    color: #8A4B00;
}

.up-hint.is-ready {
    color: #1E6B34;
    font-weight: 600;
}

.st-key-up_process button {
    padding: 12px 24px !important;
}

/* Processing lines (inside st.status) */
.up-line {
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 4px 0;
    font-size: 15px;
    color: var(--ink);
}

.up-line-icon {
    width: 20px;
    text-align: center;
    font-weight: 700;
}

.up-line-detail {
    margin-left: auto;
    font-size: 13px;
    color: var(--muted);
}

.up-line.is-todo { color: var(--muted); }
.up-line.is-skipped { color: #9AA3B5; }
.up-line.is-running .up-line-label { font-weight: 700; color: var(--blue); }
.up-line.is-done .up-line-icon { color: #1E6B34; }
.up-line.is-error { color: #A1261C; font-weight: 600; }

.up-processed {
    font-size: 15px;
    color: #1E6B34;
    background: #E6F4EA;
    border-radius: 10px;
    padding: 10px 14px;
}

/* Results header */
.up-report-head {
    background: #FFFFFF;
    border: 1px solid var(--line);
    border-left: 6px solid var(--blue);
    border-radius: 16px;
    padding: 22px 26px;
    margin-top: 8px;
    scroll-margin-top: 96px;
}

.up-report-title {
    font-size: 26px;
    font-weight: 700;
    color: var(--ink);
}

.up-report-meta {
    margin-top: 2px;
    font-size: 14px;
    color: var(--muted);
}

.up-report-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;
}

.up-chip {
    padding: 4px 12px;
    border-radius: 999px;
    background: var(--band);
    border: 1px solid var(--line);
    font-size: 14px;
    font-weight: 600;
    color: var(--ink);
}

.st-key-up_reset_confirm {
    max-width: 720px;
}

.selected-topic-note {
    font-size: 14px;
    color: var(--muted);
    margin-top: -6px;
}

.selected-topic-note b {
    color: var(--blue);
}

[class*="st-key-up_evempty"] {
    background: #FFFFFF !important;
    border: 1px dashed var(--pill-border) !important;
    border-radius: 12px !important;
    padding: 32px !important;
    align-items: center !important;
}


/* Upload cards in one row share the tallest card's height */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-up_card_"]) {
    align-items: stretch !important;
}

[data-testid="stColumn"]:has(> [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-up_card_"]) {
    display: flex !important;
    flex-direction: column !important;
}

[data-testid="stColumn"] > [data-testid="stVerticalBlock"]:has(> [data-testid="stLayoutWrapper"] > [class*="st-key-up_card_"]),
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:has(> [class*="st-key-up_card_"]) {
    flex: 1 1 auto;
    display: flex !important;
    flex-direction: column !important;
}

[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-up_card_"] {
    flex: 1 1 auto;
}

/* "Download template" and similar tertiary actions read as links */
[class*="st-key-up_tpl_"] button p,
.st-key-up_clear_demo button p,
.st-key-up_close_wizard button p {
    color: var(--blue) !important;
    font-weight: 600 !important;
    font-size: 14px !important;
}

[class*="st-key-up_tpl_"] button p::before {
    content: "⬇ ";
}

[class*="st-key-up_tpl_"] button:hover p,
.st-key-up_clear_demo button:hover p {
    text-decoration: underline;
}

/* ============================================================
   Topic selection: empty state + sticky "Exploring" bar (app.py)
   ============================================================ */
.topic-empty {
    background: #FFFFFF;
    border: 1px dashed var(--pill-border);
    border-radius: 16px;
    padding: 40px 32px;
    text-align: center;
    margin-top: 16px;
    scroll-margin-top: 96px;
}

.topic-empty-icon {
    font-size: 40px;
    line-height: 1;
}

.topic-empty-title {
    margin-top: 10px;
    font-size: 22px;
    font-weight: 600;
    color: var(--ink);
}

.topic-empty-text {
    max-width: 560px;
    margin: 8px auto 0;
    font-size: 15px;
    line-height: 1.5;
    color: var(--muted);
}

[data-testid="stLayoutWrapper"]:has(> .st-key-selection-bar),
.st-key-selection-bar {
    position: sticky !important;
    top: 72px;
    z-index: 900;
}

.st-key-selection-bar {
    width: fit-content !important;
    max-width: 100%;
    margin-top: 16px;
    padding: 6px 8px 6px 16px !important;
    background: #FFFFFF !important;
    border: 1px solid var(--blue) !important;
    border-radius: 999px !important;
    box-shadow: 0 4px 14px rgba(0, 86, 210, .15);
    gap: 10px !important;
}

.selection-bar-text {
    font-size: 15px;
    color: var(--ink);
    white-space: nowrap;
}

.selection-bar-text b {
    color: var(--blue);
}

.st-key-clear_topic_selection button {
    border-radius: 999px !important;
    padding: 4px 12px !important;
    min-height: 0 !important;
    background: var(--panel) !important;
    border: 1px solid transparent !important;
}

.st-key-clear_topic_selection button p {
    color: var(--blue) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
}

.st-key-clear_topic_selection button:hover {
    border-color: var(--blue) !important;
}

.st-key-clear_topic_selection button:focus-visible {
    outline: 2px solid var(--blue) !important;
    outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
    .progress-fill { animation: none; }
    :is([class*="st-key-card-"], [class*="st-key-ev-"]),
    [class*="st-key-kpi-"],
    .thumb::before,
    .thumb-hover,
    .ev-icon,
    .ev-preview-text,
    .ev-preview-cta { transition: none; }
    div[role="dialog"] [data-testid="stVerticalBlock"] { animation: none; }
}
</style>
"""


def inject_css():
    """Inject the platform stylesheet. Call right after set_page_config()."""
    st.markdown(_CSS, unsafe_allow_html=True)
