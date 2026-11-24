"""
Custom HTML components for the learning-platform look.

Builders return HTML strings; show them with render(html). Rules:
- Every data value goes through _esc() (html.escape).
- HTML is emitted as one line with no leading indentation and no blank
  lines. Markdown would otherwise turn indented or blank-line-separated
  HTML into a code block.

navbar(), hero_controls(), topic_card(), clickable_metric(),
scroll_to() and topic_dialog() are the exceptions: they contain real
Streamlit widgets (HTML from st.markdown cannot send clicks back to
Python), so they render directly instead of returning HTML.
"""

import base64
import json
import re
from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path
from zlib import crc32

import streamlit as st
from PIL import Image
from streamlit.errors import StreamlitPageNotFoundError

from frontend.auth_gate import current_user, sign_out
from frontend.ui.charts import donut_chart

BRAND = "Intelligence Platform"

NAV_LINKS = (
    ("dashboard", "app.py", "Dashboard"),
    ("assistant", "pages/2_Unified_Educator_Assistant.py", "Educator Assistant"),
)

BADGE_VARIANTS = ("purple", "pink", "green", "yellow", "outline")

# Thumbnail palettes, picked deterministically from gradient_seed
THUMB_GRADIENTS = (
    "linear-gradient(135deg, #5B21D6 0%, #0056D2 100%)",
    "linear-gradient(135deg, #0056D2 0%, #00A3BF 100%)",
    "linear-gradient(135deg, #B4233C 0%, #F2994A 100%)",
    "linear-gradient(135deg, #1E6B34 0%, #2BB673 100%)",
    "linear-gradient(135deg, #3B3FE0 0%, #A855F7 100%)",
    "linear-gradient(135deg, #003A8C 0%, #3B82F6 100%)",
    "linear-gradient(135deg, #7A5B00 0%, #F5B301 100%)",
    "linear-gradient(135deg, #16181D 0%, #4B5563 100%)",
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

# Pictographic emojis (U+1F000-U+1FAFF, optional variation selector).
# Text symbols such as ★ are deliberately not matched.
_EMOJI = re.compile("([\U0001F000-\U0001FAFF]️?)")


def _esc(value):
    """
    Escape a data value for HTML; newlines become spaces. Emojis are
    wrapped in <span class="emoji"> so they render in colour: Source
    Sans 3 has monochrome glyphs for some of them (e.g. 🤖).
    """
    text = escape("" if value is None else str(value)).replace("\n", " ")
    return _EMOJI.sub(r'<span class="emoji">\1</span>', text)


def _attr(value):
    """Escape a value for use inside an HTML attribute (no markup added)."""
    return escape("" if value is None else str(value), quote=True).replace("\n", " ")


def _compact(html):
    """Strip indentation and blank lines so Markdown keeps it as HTML."""
    return "".join(line.strip() for line in html.splitlines() if line.strip())


def render(html):
    """Render a component's HTML string."""
    st.markdown(_compact(html), unsafe_allow_html=True)


def _gradient(seed):
    if isinstance(seed, int):
        index = seed
    else:
        index = crc32(str(seed).encode("utf-8"))

    return THUMB_GRADIENTS[index % len(THUMB_GRADIENTS)]


def _thumb(label, chip=None, seed=0, image_src=None):
    chip_html = f'<span class="thumb-chip">{_esc(chip)}</span>' if chip else ""
    label_html = f'<span class="thumb-label">{_esc(label)}</span>' if label else ""

    if image_src:
        # image_src comes from image_data_uri() (base64 only, no quotes)
        css_class = "thumb thumb-image"
        style = f"background:#16181D url('{image_src}') center / cover no-repeat"
    else:
        css_class = "thumb"
        style = f"background:{_gradient(seed)}"

    return f'<div class="{css_class}" style="{style}">{chip_html}{label_html}</div>'


@st.cache_data(show_spinner=False)
def image_data_uri(path, max_width=320, mtime=None):
    """
    Downscaled JPEG data URI for a local image, so HTML components can
    show it without a file server. Pass the file's mtime so the cache
    refreshes when the image changes. Returns None if unreadable.
    """
    try:
        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail((max_width, max_width * 4))
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=78)
    except (OSError, ValueError):
        return None

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


# ------------------------------------------------------------------
# Widgets-bearing components (render directly)
# ------------------------------------------------------------------

def navbar(active=None):
    """
    Sticky white top bar: brand, page links, avatar and sign-out.

    Links are real st.page_link widgets inside the keyed container
    "navbar", so navigation keeps session state. `active` is
    "dashboard" or "assistant". Links and account controls appear only
    once someone is signed in.
    """
    user = current_user()

    # Accept either the internal name or the visible label ("Dashboard")
    active = (active or "").strip().lower()
    for name, _page, label in NAV_LINKS:
        if active == label.lower():
            active = name

    with st.container(
        key="navbar",
        horizontal=True,
        vertical_alignment="center",
        gap="medium",
    ):
        render(
            '<div class="navbar-brand">'
            '<span class="navbar-logo" aria-hidden="true">🎓</span>'
            f"<span>{_esc(BRAND)}</span>"
            "</div>"
        )

        if user is not None:
            for name, page, label in NAV_LINKS:
                state = "active-" if name == active else ""

                with st.container(key=f"navlink-{state}{name}", width="content"):
                    try:
                        st.page_link(page, label=label)

                    # Paths are relative to frontend/app.py; if a page file
                    # is launched on its own, skip the link.
                    except StreamlitPageNotFoundError:
                        pass

        st.space("stretch")

        if user is not None:
            with st.container(
                key="navbar-account",
                horizontal=True,
                vertical_alignment="center",
                width="content",
                gap="small",
            ):
                tooltip = f"Signed in as {user['display_name']} ({user['role']})"

                render(
                    f'<div class="navbar-avatar" title="{_attr(tooltip)}" '
                    f'aria-label="{_attr(tooltip)}">E</div>'
                )

                st.button(
                    "Sign out",
                    key="navbar-signout",
                    on_click=sign_out,
                    type="tertiary",
                )


def hero_controls():
    """
    Gradient banner that can hold real widgets:

        with ui.hero_controls():
            left, right = st.columns([3, 2])
            with left:
                ui.render(ui.hero_heading("Title", "Text"))
            with right:
                st.selectbox(...)
    """
    return st.container(key="hero-controls")


def hero_heading(title, text=None, anchor_id=None, level=1):
    """White heading (and text) for the gradient banners. anchor_id lets
    in-page links such as info_strip(href="#...") scroll to it."""
    text_html = f'<div class="hero-banner-text">{_esc(text)}</div>' if text else ""
    id_attr = f' id="{_attr(anchor_id)}"' if anchor_id else ""

    return (
        f'<div class="hero-banner-title"{id_attr} role="heading" aria-level="{int(level)}">'
        f"{_esc(title)}</div>{text_html}"
    )


# ------------------------------------------------------------------
# HTML components (return strings)
# ------------------------------------------------------------------

def badge(text, variant="outline"):
    if variant not in BADGE_VARIANTS:
        variant = "outline"

    return f'<span class="badge badge-{variant}">{_esc(text)}</span>'


def section_title(text, anchor_id=None):
    id_attr = f' id="{_attr(anchor_id)}"' if anchor_id else ""
    return (
        f'<div class="section-title"{id_attr} role="heading" aria-level="2">'
        f"{_esc(text)}</div>"
    )


def card_title(text):
    """Heading inside a white card (smaller than section_title)."""
    return f'<div class="card-title" role="heading" aria-level="3">{_esc(text)}</div>'


def comment_row(text, meta):
    """White rounded row for one student comment."""
    return (
        '<div class="comment-row">'
        f'<div class="comment-text">{_esc(text)}</div>'
        f'<div class="comment-meta">{_esc(meta)}</div>'
        "</div>"
    )


def comment_list(rows_html):
    return f'<div class="comment-list">{"".join(rows_html)}</div>'


DECISION_BADGES = {
    "Approve": "green",
    "Request changes": "yellow",
    "Reject": "pink",
}


def decision_variant(decision):
    """Badge colour for a review decision."""
    return DECISION_BADGES.get(decision, "outline")


def format_timestamp(value):
    """'2026-11-12T14:22:27.95+00:00' -> '2026-11-12 14:22' (display only)."""
    try:
        return datetime.fromisoformat(str(value)).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


def review_summary(decision, decision_variant, lines):
    """
    Review-history card header: decision badge plus label/value lines.
    `lines` is a list of (label, value) pairs.
    """
    lines_html = "".join(
        f'<div class="review-line"><span class="review-label">{_esc(label)}</span> '
        f"{_esc(value)}</div>"
        for label, value in lines
    )

    return f'<div class="review-summary">{badge(decision, decision_variant)}{lines_html}</div>'


def feature_header(pill, title, meta):
    """Top of a feature card built from real widgets (see the video card)."""
    return (
        '<div class="feature-main">'
        f"{badge(pill, 'purple') if pill else ''}"
        f'<div class="feature-title" role="heading" aria-level="3">{_esc(title)}</div>'
        f'<div class="meta">{_esc(meta)}</div>'
        "</div>"
    )


def welcome_band(title, subtitle=None, caption=None):
    parts = [
        f'<div class="welcome-title" role="heading" aria-level="1">{_esc(title)}</div>'
    ]

    if subtitle:
        parts.append(f'<div class="welcome-subtitle">{_esc(subtitle)}</div>')

    if caption:
        parts.append(f'<div class="welcome-caption">{_esc(caption)}</div>')

    return f'<div class="welcome-band">{"".join(parts)}</div>'


def course_card(
    thumb_label,
    chip,
    title,
    provider,
    meta,
    badge_text=None,
    badge_variant="outline",
    gradient_seed=0,
    logo_text=None,
):
    """
    Course-style card. The provider row is skipped when provider is
    empty; logo_text overrides the logo box (default: provider initial).
    """
    badge_html = badge(badge_text, badge_variant) if badge_text else ""
    provider_html = ""

    if provider:
        logo = logo_text if logo_text else str(provider).strip()[:1].upper()
        provider_html = (
            '<div class="provider-row">'
            f'<span class="logo-box" aria-hidden="true">{_esc(logo)}</span>'
            f"<span>{_esc(provider)}</span>"
            "</div>"
        )

    return (
        '<div class="course-card">'
        f"{_thumb(thumb_label, chip, gradient_seed)}"
        f"{provider_html}"
        f'<div class="course-title">{_esc(title)}</div>'
        f"{badge_html}"
        f'<div class="meta">{_esc(meta)}</div>'
        "</div>"
    )


def card_grid(cards_html, columns=4):
    """Responsive grid; drops to 3/2/1 columns on narrower screens."""
    columns = max(1, int(columns))
    return f'<div class="card-grid" style="--cols:{columns}">{"".join(cards_html)}</div>'


def dark_rail(title, text, cards_html):
    return (
        '<div class="dark-rail">'
        "<div>"
        f'<div class="dark-rail-title" role="heading" aria-level="2">{_esc(title)}</div>'
        f'<div class="dark-rail-text">{_esc(text)}</div>'
        "</div>"
        f'<div class="rail-scroll">{"".join(cards_html)}</div>'
        "</div>"
    )


def trend_panel(title, inner_html):
    return (
        '<div class="trend-panel">'
        f'<div class="trend-panel-title" role="heading" aria-level="2">'
        f'{_esc(title)}<span class="arrow" aria-hidden="true">→</span></div>'
        f"{inner_html}"
        "</div>"
    )


def info_strip(bold, text, link_text=None, href=None):
    if link_text and href:
        link_html = f'<a class="link-blue" href="{_attr(href)}">{_esc(link_text)}</a>'
    elif link_text:
        link_html = f'<span class="link-blue">{_esc(link_text)}</span>'
    else:
        link_html = ""

    return (
        '<div class="info-strip">'
        f"<strong>{_esc(bold)}</strong>"
        f"<span>{_esc(text)}</span>"
        f"{link_html}"
        "</div>"
    )


def step_thumb(label, caption, gradient_seed=0, image_src=None):
    """
    Small thumbnail with a caption such as "Course 1 of 11". Pass
    image_src (from image_data_uri) to show a real image instead of a
    gradient.
    """
    return (
        '<div class="step-thumb">'
        f"{_thumb(label, None, gradient_seed, image_src)}"
        f'<div class="step-caption">{_esc(caption)}</div>'
        "</div>"
    )


def step_row(steps_html):
    return f'<div class="step-row">{"".join(steps_html)}</div>'


def feature_card(pill, logo_text, title, skills, rating, meta, right_html=""):
    """
    Large recommendation card. `skills` is a list of strings shown as
    outline pills; `right_html` is usually step_row([...step_thumb()]).
    """
    skills_html = "".join(badge(skill, "outline") for skill in (skills or []))
    rating_html = (
        f'<div class="feature-rating"><span class="star" aria-hidden="true">★</span> '
        f"{_esc(rating)}</div>"
        if rating
        else ""
    )

    return (
        '<div class="feature-card">'
        '<div class="feature-main">'
        f"{badge(pill, 'purple') if pill else ''}"
        '<div class="provider-row">'
        f'<span class="logo-box" aria-hidden="true">{_esc(str(logo_text)[:2])}</span>'
        f"<span>{_esc(logo_text)}</span>"
        "</div>"
        f'<div class="feature-title" role="heading" aria-level="3">{_esc(title)}</div>'
        f'<div class="feature-skills">{skills_html}</div>'
        f"{rating_html}"
        f'<div class="meta">{_esc(meta)}</div>'
        "</div>"
        f"<div>{right_html}</div>"
        "</div>"
    )


# ------------------------------------------------------------------
# Interactive topic cards (real widgets inside keyed containers)
# ------------------------------------------------------------------

TOPIC_STATUSES = ("Highest error rate", "Needs attention", "Moderate", "On track")

STATUS_VARIANTS = {
    "Highest error rate": "pink",
    "Needs attention": "yellow",
    "Moderate": "outline",
    "On track": "green",
}


def topic_status(rate, max_rate):
    """Status label for a topic's incorrect-answer rate."""
    if rate == max_rate:
        return "Highest error rate"

    if rate > 50:
        return "Needs attention"

    if rate >= 35:
        return "Moderate"

    return "On track"


def progress_bar(value, label=None):
    """Thin progress bar that animates from 0 to value (percent)."""
    try:
        pct = max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        pct = 0.0

    label_html = (
        f'<div class="progress-label"><span>{_esc(label)}</span>'
        f"<strong>{pct:.2f}%</strong></div>"
        if label
        else ""
    )

    return (
        f'<div class="progress-wrap">{label_html}'
        f'<div class="progress" role="progressbar" aria-valuemin="0" '
        f'aria-valuemax="100" aria-valuenow="{pct:.2f}">'
        f'<div class="progress-fill" style="--value:{pct:.2f}%"></div></div></div>'
    )


def topic_card_html(row, variant, selected, status, seed):
    """
    Body of an interactive topic card (no outer frame: the keyed
    container is the card). variant is "rail" or "grid".
    """
    rate = float(row["incorrect_rate_pct"])

    if variant == "rail":
        label, chip = row["topic_name"], row["course_id"]
    else:
        label, chip = f"{rate:.2f}% incorrect", None

    chip_html = f'<span class="thumb-chip">{_esc(chip)}</span>' if chip else ""
    selected_html = '<span class="selected-pill">✓ Selected</span>' if selected else ""
    hover_html = (
        '<div class="thumb-hover" aria-hidden="true">'
        '<div class="thumb-hover-row"><span>Incorrect rate</span>'
        f"<strong>{rate:.2f}%</strong></div>"
        f"{progress_bar(rate)}"
        '<div class="thumb-hover-cta">Click to explore →</div>'
        "</div>"
    )
    thumb_html = (
        f'<div class="thumb" style="background:{_gradient(seed)}">'
        f"{chip_html}{selected_html}"
        f'<span class="thumb-label">{_esc(label)}</span>{hover_html}</div>'
    )

    if variant == "rail":
        body = (
            f'<div class="course-title">{_esc(row["topic_name"])}</div>'
            f'<div class="meta">★ {rate:.2f}% incorrect · '
            f'{int(row["total_attempts"])} attempts</div>'
        )
    else:
        body = (
            '<div class="provider-row">'
            '<span class="logo-box" aria-hidden="true">PY</span>'
            f'<span>{_esc(row["course_id"])} · {_esc(row["video_id"])}</span></div>'
            f'<div class="course-title">{_esc(row["topic_name"])}</div>'
            f"{badge(status, STATUS_VARIANTS.get(status, 'outline'))}"
            f'<div class="meta">{int(row["incorrect_answers"])} incorrect of '
            f'{int(row["total_attempts"])} · {int(row["comment_count"])} comments</div>'
        )

    return f'<div class="topic-card-body">{thumb_html}{body}</div>'


def topic_card(
    row,
    location,
    selected,
    *,
    status,
    seed,
    on_select,
    on_quick_view,
    on_explore,
    on_ask,
):
    """
    Interactive topic card: st.container(key="card-<location>-<topic_id>")
    holding the HTML body, a transparent full-card st.button (selects the
    topic) and real action buttons (Quick view / Explore / Ask AI) that
    sit above the overlay. Callbacks receive the topic_id.
    """
    topic_id = str(row["topic_id"])
    variant = "rail" if location == "rail" else "grid"

    with st.container(key=f"card-{location}-{topic_id}"):
        render(topic_card_html(row, variant, selected, status, seed))

        st.button(
            f"Select {row['topic_name']}",
            key=f"cardsel-{location}-{topic_id}",
            on_click=on_select,
            args=(topic_id,),
        )

        with st.container(
            key=f"cardact-{location}-{topic_id}",
            horizontal=True,
            gap="small",
        ):
            st.button(
                "Quick view",
                key=f"qv-{location}-{topic_id}",
                on_click=on_quick_view,
                args=(topic_id,),
            )
            st.button(
                "Explore",
                key=f"explore-{location}-{topic_id}",
                on_click=on_explore,
                args=(topic_id,),
            )
            st.button(
                "Ask AI",
                key=f"askai-{location}-{topic_id}",
                on_click=on_ask,
                args=(topic_id,),
            )


def clickable_metric(name, label, value, on_click, args=()):
    """st.metric in a keyed container with a transparent overlay button."""
    with st.container(key=f"kpi-{name}"):
        st.metric(label, value)
        st.button(
            f"Open {label}",
            key=f"kpisel-{name}",
            on_click=on_click,
            args=args,
        )


def rail_intro(title, text, anchor_id=None):
    id_attr = f' id="{_attr(anchor_id)}"' if anchor_id else ""
    return (
        f'<div class="dark-rail-title"{id_attr} role="heading" aria-level="2">'
        f"{_esc(title)}</div>"
        f'<div class="dark-rail-text">{_esc(text)}</div>'
    )


def rail_dots(page, pages):
    dots = "".join(
        '<span class="rail-dot is-active"></span>' if index == page
        else '<span class="rail-dot"></span>'
        for index in range(pages)
    )
    return (
        f'<div class="rail-dots" role="img" '
        f'aria-label="Page {page + 1} of {pages}">{dots}</div>'
    )


def topic_empty_state(anchor_id=None):
    """Card shown instead of the topic sections while no topic is selected."""
    id_attr = f' id="{_attr(anchor_id)}"' if anchor_id else ""
    return (
        f'<div class="topic-empty"{id_attr}>'
        '<div class="topic-empty-icon" aria-hidden="true"><span class="emoji">👆</span></div>'
        '<div class="topic-empty-title" role="heading" aria-level="2">Select a topic to explore</div>'
        '<div class="topic-empty-text">Click a topic card or a bar in the chart to see its quiz '
        "results, learner feedback, video evidence and AI insights.</div>"
        "</div>"
    )


def empty_state(text):
    return f'<div class="empty-state-text">{_esc(text)}</div>'


def mini_kpis(items):
    """Row of small KPI cards from (label, value) pairs."""
    cards = "".join(
        f'<div class="mini-kpi"><div class="mini-kpi-label">{_esc(label)}</div>'
        f'<div class="mini-kpi-value">{_esc(value)}</div></div>'
        for label, value in items
    )
    return f'<div class="mini-kpis">{cards}</div>'


def bar_list(items):
    """Small horizontal bars from (label, count) pairs."""
    top = max((count for _, count in items), default=0) or 1
    rows = "".join(
        f'<div class="bar-row"><span class="bar-label">{_esc(label)}</span>'
        f'<div class="progress"><div class="progress-fill" '
        f'style="--value:{count / top * 100:.1f}%"></div></div>'
        f'<span class="bar-value">{int(count)}</span></div>'
        for label, count in items
    )
    return f'<div class="bar-list">{rows}</div>'


def scroll_to(anchor_id, nonce):
    """
    Smoothly scroll the page to the element with id=anchor_id. Uses a
    hidden st.iframe (keyed container "scroll-helper"); nonce forces a
    fresh iframe so repeated requests to the same target still scroll.
    anchor_id must be one of the app's own fixed ids, never user input.
    """
    script = (
        "<script>"
        f"/* {int(nonce)} */"
        "(function () {"
        "  var tries = 0;"
        "  function go() {"
        f"    var el = window.parent.document.getElementById({json.dumps(str(anchor_id))});"
        "    if (el) { el.scrollIntoView({behavior: 'smooth', block: 'start'}); }"
        "    else if (tries++ < 40) { setTimeout(go, 100); }"
        "  }"
        "  go();"
        "})();"
        "</script>"
    )

    with st.container(key="scroll-helper"):
        st.iframe(script, height=1)


@st.dialog("Topic details", width="large")
def topic_dialog(
    row,
    status,
    topic_comments,
    video_segment,
    video_path,
    on_explore,
    on_ask,
):
    """
    Quick view for one topic. topic_comments is that topic's comments
    DataFrame; video_segment is None or a dict with start, end and
    start_seconds; on_explore / on_ask are callbacks taking topic_id.
    """
    topic_id = str(row["topic_id"])
    correct = int(row["correct_answers"])
    incorrect = int(row["incorrect_answers"])

    render(
        '<div class="dialog-head">'
        f'<div class="dialog-title" role="heading" aria-level="2">{_esc(row["topic_name"])}</div>'
        f"{badge(status, STATUS_VARIANTS.get(status, 'outline'))}"
        "</div>"
    )

    render(mini_kpis([
        ("Attempts", int(row["total_attempts"])),
        ("Correct", correct),
        ("Incorrect", incorrect),
        ("Comments", int(row["comment_count"])),
    ]))

    render(progress_bar(row["incorrect_rate_pct"], "Incorrect rate"))

    chart_col, comments_col = st.columns([2, 3], gap="large")

    with chart_col:
        st.altair_chart(
            donut_chart(correct, incorrect),
            theme=None,
            width="stretch",
        )

    with comments_col:
        if topic_comments.empty:
            st.caption("No student comments found for this topic.")

        else:
            counts = topic_comments["comment_type"].value_counts()
            render(card_title("Comments by type"))
            render(bar_list(list(counts.items())))

            # The data has no timestamps; the highest comment IDs are
            # treated as the most recent.
            render(card_title("Recent comments"))
            recent = topic_comments.sort_values("comment_id", ascending=False).head(3)
            render(comment_list([
                comment_row(
                    comment["comment_text"],
                    f"Comment {comment['comment_id']} · Type: {comment['comment_type']}",
                )
                for _, comment in recent.iterrows()
            ]))

    if video_segment is None:
        st.info("No video segment found for this topic.")

    else:
        render(
            f'<div class="meta">Approximate start: {_esc(video_segment["start"])} · '
            f'Approximate end: {_esc(video_segment["end"])}</div>'
        )

        if video_path:
            st.video(video_path, start_time=video_segment["start_seconds"])

        else:
            st.warning("No MP4 video found in data/raw.")

    with st.container(horizontal=True, gap="small", key="dialog-actions"):
        # The callbacks change the topic before the rerun; st.rerun()
        # then closes the dialog.
        if st.button(
            "Explore this topic",
            key="dlg_explore",
            type="primary",
            on_click=on_explore,
            args=(topic_id,),
        ):
            st.rerun()

        if st.button(
            "Ask AI about this topic",
            key="dlg_ask",
            on_click=on_ask,
            args=(topic_id,),
        ):
            st.rerun()


# ------------------------------------------------------------------
# Evidence explorer (interactive evidence cards, list, timeline, dialog)
#
# Session state used (per page where noted):
#   ev_current_<page>   reference shown in the details dialog
#   ev_dialog_open      page whose dialog should open on this run
#   ev_autoplay         True when the dialog was opened with "▶ Play"
#   pinned_evidence     {"<page>:<report signature>": [references]}
#   ev_toast            message shown once as a toast
#   reviewer_notes      key of the review form's comments text_area
# Widget keys: chips, ev_view, ev_sort, ev_search, ev_timeline, ev_clear,
#   and ev-/evsel-/evact-/evread-/evpeek-/evplay-/evflag-/evpin-/
#   evrow-/evrowread-/evcite-<page>-<reference> for cards and rows.
# ------------------------------------------------------------------

# modality -> (icon, solid colour, thumbnail gradient)
EVIDENCE_STYLES = {
    "quiz_analytics": ("📊", "#B45309", "linear-gradient(135deg, #B45309 0%, #F5B301 100%)"),
    "learner_comment": ("💬", "#0F766E", "linear-gradient(135deg, #0F766E 0%, #2BB673 100%)"),
    "video_transcript": ("▶", "#C2410C", "linear-gradient(135deg, #C2410C 0%, #F87171 100%)"),
    "course_document": ("📄", "#6D28D9", "linear-gradient(135deg, #5B21D6 0%, #A855F7 100%)"),
    "video_visual_analysis": ("🖼️", "#475569", "linear-gradient(135deg, #334155 0%, #64748B 100%)"),
    "video_frame": ("🖼️", "#475569", "linear-gradient(135deg, #334155 0%, #64748B 100%)"),
}
DEFAULT_EVIDENCE_STYLE = ("🔎", "#6B7280", "linear-gradient(135deg, #4B5563 0%, #9CA3AF 100%)")

VIDEO_MODALITIES = {"video_transcript", "video_visual_analysis", "video_frame"}
FRAME_MODALITIES = {"video_visual_analysis", "video_frame"}

EVIDENCE_VIEWS = ["Cards", "List", "Timeline"]
EVIDENCE_SORTS = ["Reference", "Modality", "Timestamp"]
PINNED_CHIP = "★ Pinned"
PEEK_CHARACTERS = 300

_KEYWORD_STOPWORDS = {"and", "the", "with", "into", "from"}


def modality_label(modality):
    return str(modality or "unknown").replace("_", " ").title()


def evidence_style(modality):
    return EVIDENCE_STYLES.get(modality, DEFAULT_EVIDENCE_STYLE)


def _ref(source):
    return str(source.get("reference") or "")


def _ref_number(reference):
    match = re.search(r"(\d+)", str(reference))
    return int(match.group(1)) if match else 0


def _clock(seconds):
    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        return ""
    return f"{total // 60:02d}:{total % 60:02d}"


def _has_time(value):
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return value == value  # excludes NaN


def evidence_time_range(source):
    start, end = source.get("start_seconds"), source.get("end_seconds")

    if not _has_time(start):
        return ""

    if _has_time(end):
        return f"{_clock(start)} – {_clock(end)}"

    return _clock(start)


def evidence_display_name(source):
    """File basename of the source location (without #page anchors)."""
    location = str(source.get("source_location") or "")
    base = location.split("#")[0].replace("\\", "/").rstrip("/").split("/")[-1]
    return base or location or "Unknown source"


def evidence_page_label(source):
    match = re.search(r"#page[_=\s-]*(\d+)", str(source.get("source_location") or ""), re.IGNORECASE)
    return f"Page {match.group(1)}" if match else None


def evidence_corner(source, comment_type=None):
    """Top-right thumbnail chip: time range, page, comment type or frame time."""
    modality = source.get("modality")

    if modality == "video_transcript":
        time_range = evidence_time_range(source)
        return f"▶ {time_range}" if time_range else None

    if modality in FRAME_MODALITIES:
        return evidence_time_range(source) or None

    if modality == "course_document":
        return evidence_page_label(source) or evidence_display_name(source)

    if modality == "learner_comment":
        return comment_type

    return None


def is_cited(reference, answer):
    """True if the answer cites the reference as E3 or [E3] (not E30)."""
    if not reference:
        return False

    pattern = rf"(?<![A-Za-z0-9]){re.escape(reference)}(?!\d)"
    return re.search(pattern, str(answer or "")) is not None


def cited_references(answer, sources):
    """References cited in the answer, in order of first citation."""
    known = {_ref(source) for source in sources}
    found = []

    for match in re.finditer(r"(?<![A-Za-z0-9])(E\d+)(?!\d)", str(answer or "")):
        reference = match.group(1)

        if reference in known and reference not in found:
            found.append(reference)

    return found


def topic_keywords(topic_name):
    """Words of the topic name (plus singular forms) to highlight."""
    words = set()

    for word in re.findall(r"[A-Za-z]+", str(topic_name or "").lower()):
        if len(word) < 3 or word in _KEYWORD_STOPWORDS:
            continue

        words.add(word)

        if len(word) > 4 and word.endswith("s"):
            words.add(word[:-1])

    return sorted(words, key=len, reverse=True)


def _highlight(text, keywords):
    """Escape the text first, then wrap keywords in <mark>; keep line breaks."""
    html = escape("" if text is None else str(text))

    if keywords:
        pattern = r"\b(" + "|".join(re.escape(word) for word in keywords) + r")\b"
        html = re.sub(pattern, r"<mark>\1</mark>", html, flags=re.IGNORECASE)

    html = _EMOJI.sub(r'<span class="emoji">\1</span>', html)
    return html.replace("\r\n", "\n").replace("\n", "<br>")


def parse_quiz_text(text):
    """Numbers from quiz-analytics evidence text (missing values are None)."""
    patterns = {
        "attempts": r"quiz attempts:\s*([\d.]+)",
        "incorrect": r"incorrect answers:\s*([\d.]+)",
        "rate": r"incorrect rate:\s*([\d.]+)",
        "comments": r"comment count:\s*([\d.]+)",
    }
    values = {}

    for name, pattern in patterns.items():
        match = re.search(pattern, str(text or ""), re.IGNORECASE)
        values[name] = float(match.group(1)) if match else None

    return values


def _report_signature(answer):
    from hashlib import sha1
    return sha1(str(answer or "").encode("utf-8")).hexdigest()[:12]


def pinned_refs(page, answer):
    """The list of pinned references for this page's current report."""
    store = st.session_state.setdefault("pinned_evidence", {})
    return store.setdefault(f"{page}:{_report_signature(answer)}", [])


# Pages whose evidence widgets keep their original keys (chips, ev_view, ...)
LEGACY_EVIDENCE_PAGES = {"assistant", "dashboard"}


def _ev_key(page, base):
    """Widget key for the explorer on `page`: the original key on the two
    original pages, an "up_"-prefixed page-scoped key elsewhere so several
    explorers can share one page."""
    if page in LEGACY_EVIDENCE_PAGES:
        return base

    scoped = {
        "chips": f"up_chips_{page}",
        "ev_view": f"up_chips_view_{page}",
        "ev_sort": f"up_chips_sort_{page}",
        "ev_search": f"up_ev_search_{page}",
        "ev_timeline": f"up_ev_timeline_{page}",
        "ev_clear": f"up_ev_clear_{page}",
        "evempty": f"up_evempty_{page}",
    }
    return scoped[base]


# ---------------------------- callbacks ----------------------------

def _open_evidence(page, reference, play=False, extra=None):
    st.session_state[f"ev_current_{page}"] = reference
    st.session_state["ev_dialog_open"] = page
    st.session_state["ev_autoplay"] = bool(play)

    # e.g. switch the upload report's evidence topic before opening
    for key, value in (extra or {}).items():
        st.session_state[key] = value


def _set_current_evidence(page, reference):
    st.session_state[f"ev_current_{page}"] = reference
    st.session_state["ev_autoplay"] = False


def _toggle_pin(page, answer, reference):
    pins = pinned_refs(page, answer)

    if reference in pins:
        pins.remove(reference)
    else:
        pins.append(reference)


def _flag_evidence(reference, display_name, notes_key="reviewer_notes"):
    """Append "E3 (file): " to the reviewer comments box `notes_key`."""
    current = st.session_state.get(notes_key) or ""

    if current and not current.endswith("\n"):
        current += "\n"

    st.session_state[notes_key] = f"{current}{reference} ({display_name}): "
    st.session_state["ev_toast"] = f"Added {reference} to reviewer comments"


def _toggle_flag(key):
    st.session_state[key] = not st.session_state.get(key, False)


def _clear_evidence_filters(page):
    st.session_state[_ev_key(page, "chips")] = "All"
    st.session_state[_ev_key(page, "ev_search")] = ""


def _open_from_timeline(page):
    chart_state = st.session_state.get(_ev_key(page, "ev_timeline")) or {}
    points = chart_state.get("selection", {}).get("ev_pick", [])

    for point in points:
        if point.get("reference"):
            _open_evidence(page, point["reference"])
            break


# ---------------------------- rendering ----------------------------

def evidence_card_html(source, cited, pinned, comment_type=None):
    reference = _ref(source)
    modality = source.get("modality", "unknown")
    icon, _color, gradient = evidence_style(modality)
    corner = evidence_corner(source, comment_type)

    star = ' <span aria-label="pinned">★</span>' if pinned else ""
    corner_html = f'<span class="ev-corner">{_esc(corner)}</span>' if corner else ""
    cited_html = badge("Cited in report", "green") if cited else badge("Not cited", "outline")

    thumb = (
        f'<div class="thumb ev-thumb" style="background:{gradient}">'
        f'<span class="thumb-chip">{_esc(reference)}{star}</span>{corner_html}'
        f'<span class="ev-icon" aria-hidden="true">{_esc(icon)}</span>'
        f'<span class="thumb-label">{_esc(modality_label(modality))}</span></div>'
    )

    return (
        f'<div class="ev-card-body{" is-pinned" if pinned else ""}">{thumb}'
        f'<div class="ev-name" title="{_attr(source.get("source_location", ""))}">'
        f"{_esc(evidence_display_name(source))}</div>"
        f'<div class="meta">Source ID: {_esc(source.get("source_id", ""))}</div>'
        '<div class="ev-preview">'
        f'<span class="ev-preview-text">{_esc(source.get("text", ""))}</span>'
        '<span class="ev-preview-cta">Click to read →</span></div>'
        f"{cited_html}</div>"
    )


def evidence_card(source, page, cited, pinned, *, answer, comment_type=None,
                  notes_key="reviewer_notes"):
    """
    Interactive evidence card: st.container(key="ev-<page>-<reference>")
    with the HTML body, a transparent full-card button (opens the
    dialog) and footer actions: Read, Peek, ▶ Play (transcripts), Flag
    and Pin.
    """
    reference = _ref(source)
    name = evidence_display_name(source)
    text = str(source.get("text") or "")

    with st.container(key=f"ev-{page}-{reference}"):
        render(evidence_card_html(source, cited, pinned, comment_type))

        st.button(
            f"Read {reference}",
            key=f"evsel-{page}-{reference}",
            on_click=_open_evidence,
            args=(page, reference),
        )

        with st.container(key=f"evact-{page}-{reference}", horizontal=True, gap="small"):
            st.button(
                "Read",
                key=f"evread-{page}-{reference}",
                on_click=_open_evidence,
                args=(page, reference),
            )

            with st.popover("Peek", key=f"evpeek-{page}-{reference}"):
                snippet = text[:PEEK_CHARACTERS] + ("…" if len(text) > PEEK_CHARACTERS else "")
                render(f'<div class="ev-peek">{_esc(snippet)}</div>')

            if source.get("modality") == "video_transcript":
                st.button(
                    "▶ Play",
                    key=f"evplay-{page}-{reference}",
                    on_click=_open_evidence,
                    args=(page, reference, True),
                )

            st.button(
                "Flag",
                key=f"evflag-{page}-{reference}",
                on_click=_flag_evidence,
                args=(reference, name, notes_key),
            )

            st.button(
                "★ Pinned" if pinned else "☆ Pin",
                key=f"evpin-{page}-{reference}",
                on_click=_toggle_pin,
                args=(page, answer, reference),
            )


def evidence_row(source, page, cited, pinned):
    """Compact list row: icon, reference, name, preview and Read."""
    reference = _ref(source)
    modality = source.get("modality", "unknown")
    icon, color, _gradient = evidence_style(modality)

    row_html = (
        f'<div class="ev-row{" is-pinned" if pinned else ""}">'
        f'<span class="ev-row-icon" style="background:{color}" aria-hidden="true">{_esc(icon)}</span>'
        f'<span class="ev-row-ref">{_esc(reference)}{" ★" if pinned else ""}</span>'
        '<span class="ev-row-main">'
        f'<span class="ev-row-name" title="{_attr(source.get("source_location", ""))}">'
        f"{_esc(evidence_display_name(source))} · {_esc(modality_label(modality))}</span>"
        f'<span class="ev-row-preview">{_esc(source.get("text", ""))}</span></span>'
        f'<span class="ev-row-dot{" is-cited" if cited else ""}" '
        f'title="{"Cited in report" if cited else "Not cited"}"></span>'
        "</div>"
    )

    with st.container(
        key=f"evrow-{page}-{reference}",
        horizontal=True,
        vertical_alignment="center",
        gap="small",
    ):
        render(row_html)
        st.button(
            "Read",
            key=f"evrowread-{page}-{reference}",
            on_click=_open_evidence,
            args=(page, reference),
        )


def cited_evidence_pills(page, answer, sources, key_suffix="", extra_state=None):
    """
    'Cited evidence:' followed by one pill button per cited reference.
    key_suffix keeps keys unique when one page shows several answers;
    extra_state is written to session_state when a pill is clicked.
    """
    references = cited_references(answer, sources)

    if not references:
        return

    with st.container(
        key=f"evcites-{page}{key_suffix}",
        horizontal=True,
        vertical_alignment="center",
        gap="small",
    ):
        render('<span class="ev-cites-label">Cited evidence:</span>')

        for reference in references:
            st.button(
                reference,
                key=f"evcite-{page}{key_suffix}-{reference}",
                on_click=_open_evidence,
                args=(page, reference, False, extra_state),
            )


def evidence_toolbar(page, sources, pins):
    """
    Modality chips with counts (+ ★ Pinned), view switcher, sort and
    search. Returns (chip, view, sort, search).
    """
    counts = {}

    for source in sources:
        modality = source.get("modality", "unknown")
        counts[modality] = counts.get(modality, 0) + 1

    options = ["All", *counts.keys(), PINNED_CHIP]
    labels = {"All": f"All ({len(sources)})", PINNED_CHIP: f"{PINNED_CHIP} ({len(pins)})"}
    labels.update({modality: f"{modality_label(modality)} ({count})" for modality, count in counts.items()})

    # Defaults are set before the widgets exist (never after)
    chips_key = _ev_key(page, "chips")

    if st.session_state.get(chips_key) not in options:
        st.session_state[chips_key] = "All"

    st.session_state.setdefault(_ev_key(page, "ev_view"), EVIDENCE_VIEWS[0])
    st.session_state.setdefault(_ev_key(page, "ev_sort"), EVIDENCE_SORTS[0])
    st.session_state.setdefault(_ev_key(page, "ev_search"), "")

    chip = st.pills(
        "Supporting Evidence",
        options,
        required=True,
        format_func=lambda option: labels[option],
        key=chips_key,
        label_visibility="collapsed",
    )

    view_col, sort_col, search_col = st.columns([2, 2, 3], vertical_alignment="bottom")

    with view_col:
        view = st.segmented_control("View", EVIDENCE_VIEWS, required=True, key=_ev_key(page, "ev_view"))

    with sort_col:
        sort = st.segmented_control("Sort by", EVIDENCE_SORTS, required=True, key=_ev_key(page, "ev_sort"))

    with search_col:
        search = st.text_input(
            "Search evidence",
            placeholder="Search evidence text…",
            key=_ev_key(page, "ev_search"),
            label_visibility="collapsed",
        )

    return chip, view, sort, search


def filter_evidence(sources, chip, search, sort, pins):
    rows = list(sources)

    if chip == PINNED_CHIP:
        rows = [source for source in rows if _ref(source) in pins]
    elif chip not in (None, "All"):
        rows = [source for source in rows if source.get("modality") == chip]

    query = (search or "").strip().lower()

    if query:
        rows = [
            source for source in rows
            if query in " ".join(
                str(source.get(field) or "")
                for field in ("text", "source_id", "source_location", "reference")
            ).lower()
        ]

    if sort == "Modality":
        rows.sort(key=lambda s: (modality_label(s.get("modality")), _ref_number(_ref(s))))
    elif sort == "Timestamp":
        rows.sort(key=lambda s: (
            not _has_time(s.get("start_seconds")),
            float(s["start_seconds"]) if _has_time(s.get("start_seconds")) else 0.0,
            _ref_number(_ref(s)),
        ))
    else:
        rows.sort(key=lambda s: _ref_number(_ref(s)))

    return rows


def _frame_image(source, base_dir):
    """Resolve a frame's image file from its location or source id."""
    if base_dir is None:
        return None

    base_dir = Path(base_dir)
    location = str(source.get("source_location") or "").split("#")[0]
    frames_dir = base_dir / "data" / "processed" / "video_frames"
    candidates = [base_dir / location, frames_dir / Path(location).name]

    if _has_time(source.get("start_seconds")):
        candidates.append(frames_dir / f"PY101_V01_frame_{int(float(source['start_seconds'])):05d}.jpg")

    for candidate in candidates:
        if candidate.suffix.lower() in (".jpg", ".jpeg", ".png") and candidate.is_file():
            return candidate

    return None


@st.dialog("Evidence details", width="large")
def evidence_dialog(
    page,
    sources,
    answer,
    topic_name,
    comment_types,
    base_dir,
    video_path,
    heading_for,
    notes_key="reviewer_notes",
):
    """
    Details for one evidence record. `sources` is the currently filtered
    list; Previous/Next move through it. The current reference lives in
    st.session_state["ev_current_<page>"].
    """
    if not sources:
        return

    references = [_ref(source) for source in sources]
    current = st.session_state.get(f"ev_current_{page}")

    if current not in references:
        current = references[0]

    index = references.index(current)
    source = sources[index]
    modality = source.get("modality", "unknown")
    icon, color, _gradient = evidence_style(modality)
    cited = is_cited(current, answer)
    pins = pinned_refs(page, answer)
    keywords = topic_keywords(topic_name)
    comment_type = comment_types.get(str(source.get("source_id")), None) if comment_types else None
    name = evidence_display_name(source)

    render(
        '<div class="ev-dialog-head">'
        f'<span class="ev-dialog-ref" style="background:{color}">{_esc(current)}</span>'
        f'<span class="badge ev-modality-badge" style="color:{color};border-color:{color}">'
        f"{_esc(icon)} {_esc(modality_label(modality))}</span>"
        f"{badge('Cited in report', 'green') if cited else badge('Not cited', 'outline')}"
        f"{badge('★ Pinned', 'yellow') if current in pins else ''}"
        "</div>"
        f'<div class="ev-dialog-name" title="{_attr(source.get("source_location", ""))}">{_esc(name)}</div>'
        '<div class="ev-dialog-meta">'
        f'<span><b>Source ID:</b> {_esc(source.get("source_id", ""))}</span>'
        f'<span><b>Source location:</b> {_esc(source.get("source_location", ""))}</span>'
        f'<span><b>Topic:</b> {_esc(source.get("topic_id", ""))}</span>'
        "</div>"
    )

    if heading_for is not None:
        st.caption(heading_for(source))

    text_html = f'<div class="ev-text">{_highlight(source.get("text", ""), keywords)}</div>'

    if modality == "video_transcript":
        if video_path and _has_time(source.get("start_seconds")):
            st.video(
                video_path,
                start_time=int(float(source["start_seconds"])),
                autoplay=bool(st.session_state.get("ev_autoplay")),
            )
        elif not video_path:
            st.warning("No MP4 video found in data/raw.")

        if evidence_time_range(source):
            render(f'<div class="ev-time">Video timestamp: {_esc(evidence_time_range(source))}</div>')

        render('<div class="ev-label">Retrieved evidence:</div>' + text_html)

    elif modality == "learner_comment":
        type_html = badge(comment_type, "purple") if comment_type else ""
        render(
            f'<div class="ev-bubble"><div class="ev-bubble-text">'
            f'{_highlight(source.get("text", ""), keywords)}</div>'
            f'<div class="ev-bubble-meta">{_esc(source.get("source_id", ""))} {type_html}</div></div>'
        )

    elif modality == "quiz_analytics":
        numbers = parse_quiz_text(source.get("text"))
        kpis = [
            (label, int(numbers[key]))
            for label, key in (("Attempts", "attempts"), ("Incorrect", "incorrect"), ("Comments", "comments"))
            if numbers[key] is not None
        ]

        if kpis:
            render(mini_kpis(kpis))

        if numbers["rate"] is not None:
            render(progress_bar(numbers["rate"], "Incorrect rate"))

        render('<div class="ev-label">Retrieved evidence:</div>' + text_html)

    elif modality == "course_document":
        page_label = evidence_page_label(source)
        render(
            '<div class="ev-doc">'
            f'<div class="ev-doc-head">{_esc(name)}{" · " + _esc(page_label) if page_label else ""}</div>'
            f'<div class="ev-text">{_highlight(source.get("text", ""), keywords)}</div></div>'
        )

    elif modality in FRAME_MODALITIES:
        image_path = _frame_image(source, base_dir)

        if image_path is not None:
            st.image(str(image_path), caption=evidence_time_range(source) or None)

        render('<div class="ev-label">Retrieved evidence:</div>' + text_html)

    else:
        render('<div class="ev-label">Retrieved evidence:</div>' + text_html)

    with st.container(key=f"evdlg-actions-{page}", horizontal=True, vertical_alignment="center", gap="small"):
        st.button(
            "← Previous",
            key=f"evdlg-prev-{page}",
            disabled=index == 0,
            on_click=_set_current_evidence,
            args=(page, references[index - 1] if index > 0 else current),
        )
        st.button(
            "Next →",
            key=f"evdlg-next-{page}",
            disabled=index >= len(references) - 1,
            on_click=_set_current_evidence,
            args=(page, references[index + 1] if index < len(references) - 1 else current),
        )
        render(f'<span class="ev-position">{index + 1} of {len(references)}</span>')
        st.space("stretch")
        st.button(
            "★ Pinned" if current in pins else "☆ Pin",
            key=f"evdlg-pin-{page}",
            on_click=_toggle_pin,
            args=(page, answer, current),
        )

        if st.button(
            "Flag in review",
            key=f"evdlg-flag-{page}",
            type="primary",
            on_click=_flag_evidence,
            args=(current, name, notes_key),
        ):
            # Close the dialog so the reviewer comments box shows the text
            st.rerun()


def evidence_explorer(
    page,
    sources,
    answer,
    *,
    topic_name,
    comment_types=None,
    base_dir=None,
    video_path=None,
    heading_for=None,
    columns=3,
    initial_cards=None,
    show_all_key=None,
    notes_key="reviewer_notes",
):
    """
    Toolbar, result line, Cards / List / Timeline view, empty state,
    details dialog and Flag toast for one page's evidence. `page` makes
    the widget keys unique ("assistant", "dashboard").
    """
    comment_types = comment_types or {}
    pins = pinned_refs(page, answer)
    chip, view, sort, search = evidence_toolbar(page, sources, pins)
    shown = filter_evidence(sources, chip, search, sort, pins)

    if view == "Timeline":
        visible = [
            source for source in shown
            if source.get("modality") in VIDEO_MODALITIES and _has_time(source.get("start_seconds"))
        ]
    elif view == "Cards" and initial_cards and not st.session_state.get(show_all_key, False):
        visible = shown[:initial_cards]
    else:
        visible = shown

    st.caption(f"Showing {len(visible)} of {len(sources)} evidence records")

    if not shown:
        with st.container(key=_ev_key(page, "evempty")):
            render(empty_state("No evidence matches your filters."))
            st.button("Clear filters", key=_ev_key(page, "ev_clear"),
                      on_click=_clear_evidence_filters, args=(page,))

    elif view == "Cards":
        for row_start in range(0, len(visible), columns):
            card_columns = st.columns(columns)

            for card_column, source in zip(card_columns, visible[row_start:row_start + columns]):
                with card_column:
                    evidence_card(
                        source,
                        page,
                        is_cited(_ref(source), answer),
                        _ref(source) in pins,
                        answer=answer,
                        comment_type=comment_types.get(str(source.get("source_id"))),
                        notes_key=notes_key,
                    )

        hidden = len(shown) - (initial_cards or len(shown))

        if initial_cards and show_all_key and hidden > 0:
            show_all = st.session_state.get(show_all_key, False)
            st.button(
                "Show fewer" if show_all else f"Show {hidden} more",
                key="show-more",
                on_click=_toggle_flag,
                args=(show_all_key,),
            )

    elif view == "List":
        for source in visible:
            evidence_row(source, page, is_cited(_ref(source), answer), _ref(source) in pins)

    else:
        if not visible:
            st.info("No video evidence matches the current filters.")
        else:
            from frontend.ui.charts import evidence_timeline

            timeline_rows = []

            for source in visible:
                modality = source.get("modality", "unknown")
                timeline_rows.append({
                    "reference": _ref(source),
                    "modality": modality_label(modality),
                    "color": evidence_style(modality)[1],
                    "start": float(source["start_seconds"]),
                    "end": float(source["end_seconds"]) if _has_time(source.get("end_seconds")) else None,
                    "time": evidence_time_range(source),
                    "source_id": str(source.get("source_id", "")),
                    "preview": str(source.get("text", ""))[:90],
                })

            with st.container(border=True, key=f"lp_card_timeline_{page}"):
                st.altair_chart(
                    evidence_timeline(timeline_rows),
                    width="stretch",
                    theme=None,
                    on_select=lambda: _open_from_timeline(page),
                    key=_ev_key(page, "ev_timeline"),
                )

    if st.session_state.get("ev_dialog_open") == page:
        st.session_state.pop("ev_dialog_open")
        current = st.session_state.get(f"ev_current_{page}")
        dialog_sources = shown if current in {_ref(s) for s in shown} else filter_evidence(sources, "All", "", sort, pins)

        evidence_dialog(
            page,
            dialog_sources,
            answer,
            topic_name,
            comment_types,
            str(base_dir) if base_dir else None,
            video_path,
            heading_for,
            notes_key,
        )

    toast = st.session_state.pop("ev_toast", None)

    if toast:
        st.toast(toast, icon="🚩")
