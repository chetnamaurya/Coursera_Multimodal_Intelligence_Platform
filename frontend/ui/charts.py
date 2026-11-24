"""Altair charts in the platform style."""

import altair as alt
import pandas as pd

BLUE = "#0056D2"
BLUE_SOFT = "#9DB8E8"

# Name of the point selection in topic_difficulty_chart(); the page's
# on_select callback reads st.session_state[key].selection[TOPIC_PICK].
TOPIC_PICK = "topic_pick"
TEXT = "#1F1F1F"
MUTED = "#5B6780"
GRID = "#DAE1ED"
FONT = '"Source Sans 3", "Source Sans", sans-serif'


def horizontal_bar_chart(data, category, value, height=380):
    """
    Horizontal bar chart: blue rounded bars, highest value first,
    x gridlines only, transparent background. Axis and tooltip titles
    are the column names. Render with
    st.altair_chart(chart, width="stretch", theme=None).
    """
    chart = (
        alt.Chart(data)
        .mark_bar(color=BLUE, cornerRadiusEnd=4, height={"band": 0.7})
        .encode(
            x=alt.X(
                f"{value}:Q",
                axis=alt.Axis(
                    grid=True,
                    gridColor=GRID,
                    domain=False,
                    ticks=False,
                    labelColor=MUTED,
                    titleColor=MUTED,
                    titleFontWeight=600,
                    labelPadding=6,
                ),
            ),
            y=alt.Y(
                f"{category}:N",
                sort="-x",
                axis=alt.Axis(
                    grid=False,
                    domain=False,
                    ticks=False,
                    labelColor=TEXT,
                    labelFontSize=13,
                    labelLimit=240,
                    labelPadding=8,
                    titleColor=MUTED,
                    titleFontWeight=600,
                ),
            ),
            tooltip=[
                alt.Tooltip(f"{category}:N"),
                alt.Tooltip(f"{value}:Q", format=".2f"),
            ],
        )
        .properties(height=height, background="transparent")
    )

    return chart.configure(font=FONT).configure_view(stroke=None)


def topic_difficulty_chart(data, selected_topic_id=None, height=380):
    """
    Clickable difficulty chart. `data` needs topic_id, topic_name,
    incorrect_rate_pct, total_attempts and comment_count.

    - Nothing selected (selected_topic_id is None): every bar uses one
      neutral blue.
    - A topic selected: that bar is BLUE, the others BLUE_SOFT.
    The point selection always starts EMPTY (no initial value): Streamlit
    only reports a selection that differs from the last one it saw, so the
    page gives the chart a new key whenever the topic changes; a click on
    a bar is then always reported, and the page's callback treats a click
    on the already-selected bar as "clear".
    Render with st.altair_chart(..., on_select=callback, key=...).
    """
    data = data.copy()
    data["label"] = data["incorrect_rate_pct"].map(lambda value: f"{value:.1f}%")
    selected = None if selected_topic_id is None else str(selected_topic_id)
    data["hint"] = [
        "Click again to clear" if topic_id == selected else "Click to explore"
        for topic_id in data["topic_id"].astype(str)
    ]

    # 0 .. max rounded up to 10, with room for the value labels
    top = float(data["incorrect_rate_pct"].max() or 0)
    domain_max = int(min(100, max(10, ((top + 8) // 10 + 1) * 10)))

    pick = alt.selection_point(name=TOPIC_PICK, fields=["topic_id"], on="click")

    x = alt.X(
        "incorrect_rate_pct:Q",
        title="Incorrect answer rate (%)",
        scale=alt.Scale(domain=[0, domain_max], nice=False),
        axis=alt.Axis(
            values=list(range(0, domain_max + 1, 10)),
            grid=True,
            gridColor="#EEF2F7",
            domain=False,
            ticks=False,
            labelColor=MUTED,
            titleColor=MUTED,
            titleFontWeight=600,
            labelPadding=6,
        ),
    )
    y = alt.Y(
        "topic_name:N",
        sort="-x",
        title=None,
        axis=alt.Axis(
            grid=False,
            domain=False,
            ticks=False,
            labelColor=TEXT,
            labelFontSize=13,
            labelLimit=240,
            labelPadding=8,
        ),
    )
    tooltip = [
        alt.Tooltip("topic_name:N", title="Topic"),
        alt.Tooltip("incorrect_rate_pct:Q", title="Incorrect %", format=".2f"),
        alt.Tooltip("total_attempts:Q", title="Attempts"),
        alt.Tooltip("comment_count:Q", title="Comments"),
        alt.Tooltip("hint:N", title=" "),
    ]

    if selected is None:
        bar_color, bar_opacity = alt.value(BLUE), alt.value(0.85)
        label_color = alt.value(MUTED)
    else:
        is_selected = alt.datum.topic_id == selected
        bar_color = alt.condition(is_selected, alt.value(BLUE), alt.value(BLUE_SOFT))
        bar_opacity = alt.value(1)
        label_color = alt.condition(is_selected, alt.value(BLUE), alt.value(MUTED))

    base = alt.Chart(data)

    bars = (
        base.mark_bar(cornerRadiusEnd=4, height={"band": 0.7}, cursor="pointer")
        .encode(x=x, y=y, color=bar_color, opacity=bar_opacity, tooltip=tooltip)
        .add_params(pick)
    )

    values = (
        base.mark_text(align="left", baseline="middle", dx=6, fontSize=12, fontWeight=600)
        .encode(x=x, y=y, text="label:N", color=label_color, tooltip=tooltip)
    )

    return (
        alt.layer(bars, values)
        .properties(height=height, background="transparent")
        .configure(font=FONT)
        .configure_view(stroke=None)
    )


def donut_chart(correct, incorrect, height=240):
    """Donut of correct vs incorrect answers."""
    data = pd.DataFrame({
        "answer": ["Correct", "Incorrect"],
        "count": [int(correct), int(incorrect)],
    })

    chart = (
        alt.Chart(data)
        .mark_arc(innerRadius=58, outerRadius=92, cornerRadius=4, padAngle=0.02)
        .encode(
            theta=alt.Theta("count:Q"),
            color=alt.Color(
                "answer:N",
                scale=alt.Scale(domain=["Correct", "Incorrect"], range=[BLUE_SOFT, BLUE]),
                legend=alt.Legend(orient="bottom", title=None, labelColor=TEXT),
            ),
            tooltip=[
                alt.Tooltip("answer:N", title="Answer"),
                alt.Tooltip("count:Q", title="Count"),
            ],
        )
        .properties(height=height, background="transparent")
    )

    return chart.configure(font=FONT).configure_view(stroke=None)


# Name of the point selection in evidence_timeline(); the evidence
# explorer reads st.session_state["ev_timeline"].selection[EVIDENCE_PICK].
EVIDENCE_PICK = "ev_pick"


def evidence_timeline(rows):
    """
    Horizontal video timeline: one row per modality, a marker per
    evidence record at its start time (transcripts also show their span),
    coloured by modality. Clicking a marker fills the EVIDENCE_PICK point
    selection with its reference.

    rows: dicts with reference, modality, color, start, end (or None),
    time, source_id, preview.
    """
    data = pd.DataFrame(rows)
    starts = data["start"].astype(float)
    ends = data["end"].dropna().astype(float) if data["end"].notna().any() else starts
    domain = [max(0.0, starts.min() - 20), max(starts.max(), ends.max()) + 20]

    colors = data.drop_duplicates("modality")
    color = alt.Color(
        "modality:N",
        scale=alt.Scale(domain=list(colors["modality"]), range=list(colors["color"])),
        legend=None,
    )
    x = alt.X(
        "start:Q",
        scale=alt.Scale(domain=domain, nice=False),
        axis=alt.Axis(
            title="Video time",
            # utcFormat: timeFormat would shift the labels by the viewer's
            # timezone offset (e.g. +05:30 turns 05:40 into 35:40)
            labelExpr="utcFormat(datum.value * 1000, '%M:%S')",
            tickCount=8,
            labelOverlap=True,
            grid=True,
            gridColor=GRID,
            domain=False,
            ticks=False,
            labelColor=MUTED,
            titleColor=MUTED,
            titleFontWeight=600,
        ),
    )
    y = alt.Y(
        "modality:N",
        axis=alt.Axis(title=None, domain=False, ticks=False, labelColor=TEXT, labelFontSize=13, labelPadding=10),
    )
    pick = alt.selection_point(name=EVIDENCE_PICK, fields=["reference"], on="click")

    base = alt.Chart(data)

    spans = (
        base.transform_filter("isValid(datum.end)")
        .mark_rule(strokeWidth=8, opacity=0.35, strokeCap="round")
        .encode(x=x, x2="end:Q", y=y, color=color)
    )

    markers = (
        base.mark_circle(size=320, opacity=0.95, stroke="#FFFFFF", strokeWidth=2, cursor="pointer")
        .encode(
            x=x,
            y=y,
            color=color,
            tooltip=[
                alt.Tooltip("reference:N", title="Reference"),
                alt.Tooltip("modality:N", title="Modality"),
                alt.Tooltip("time:N", title="Time"),
                alt.Tooltip("source_id:N", title="Source ID"),
                alt.Tooltip("preview:N", title="Evidence"),
            ],
        )
        .add_params(pick)
    )

    labels = base.mark_text(dy=-18, fontSize=12, fontWeight=600, color=TEXT).encode(
        x=x, y=y, text="reference:N"
    )

    rows_count = data["modality"].nunique()

    return (
        alt.layer(spans, markers, labels)
        .properties(height=70 + 60 * rows_count, background="transparent")
        .configure(font=FONT)
        .configure_view(stroke=None)
    )
