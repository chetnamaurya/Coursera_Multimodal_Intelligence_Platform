
import sys
from functools import partial
from math import ceil
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ai.rag_pipeline import ask_course
from backend.review_store import (
    save_review,
    get_review_history
)
from frontend.auth_gate import can_review, require_login
from frontend.ui import components as ui
from frontend.ui.charts import TOPIC_PICK, topic_difficulty_chart
from frontend.ui.theme import inject_css
from frontend import upload_section

# 1. Configure the application
st.set_page_config(
    page_title="Coursera Intelligence Platform",
    page_icon="🎓",
    layout="wide"
)
inject_css()
ui.navbar(active="Dashboard")

# Nothing below renders until the visitor signs in
user = require_login()
user_can_review = can_review(user)

# 2. Locate the project folders
PROCESSED_DIR = BASE_DIR / "data" / "processed"
RAW_DIR = BASE_DIR / "data" / "raw"
FRAMES_DIR = PROCESSED_DIR / "video_frames"

# Topic cards shown before "Show N more"
INITIAL_TOPIC_CARDS = 8
SHOW_ALL_TOPICS_KEY = "show_all_topic_cards"

# Dark rail carousel and grid toolbar
RAIL_CARDS_PER_PAGE = 3
GRID_SORTS = ["Highest error", "Most comments", "A–Z"]

# 3. Load our processed analytics
learning_data = pd.read_csv(
    PROCESSED_DIR / "learning_difficulty_summary.csv"
)

comments = pd.read_csv(
    RAW_DIR / "student_comments.csv"
)

# Loaded up front: the Quick view dialog needs it even when no topic is selected
video_topics = pd.read_csv(
    RAW_DIR / "video_topics.csv"
)


@st.cache_data(show_spinner=False)
def load_topic_frames(topic_id, video_id):
    """(timestamp_seconds, path) of extracted frames mapped to a topic."""
    mapping_path = FRAMES_DIR / "frame_topic_mapping.csv"

    if not mapping_path.exists():
        return []

    mapping = pd.read_csv(mapping_path)

    rows = mapping[
        (mapping["topic_id"] == topic_id)
        & (mapping["video_id"] == video_id)
    ].sort_values("timestamp_seconds")

    frames = []

    for _, row in rows.iterrows():
        frame_path = FRAMES_DIR / str(row["frame_file"])

        if frame_path.exists():
            frames.append((int(row["timestamp_seconds"]), str(frame_path)))

    return frames


def segment_start_seconds(time_text):
    """HH:MM:SS -> seconds (used by the quick-view dialog)."""
    hours, minutes, seconds = map(int, str(time_text).split(":"))
    return hours * 3600 + minutes * 60 + seconds


# ------------------------------------------------------------------
# Callbacks. st.session_state["topic_select"] (None = no topic) is only
# ever changed here, in on_click / on_select callbacks.
# ------------------------------------------------------------------

def select_topic(topic_id):
    st.session_state["topic_select"] = topic_id


def explore_topic(topic_id):
    select_topic(topic_id)
    st.session_state["scroll_to"] = "student-feedback"


def ask_ai_about_topic(topic_id):
    select_topic(topic_id)
    st.session_state["scroll_to"] = "ai-assistant"


def open_quick_view(topic_id):
    st.session_state["quick_view_topic"] = topic_id


def scroll_to_section(anchor_id):
    st.session_state["scroll_to"] = anchor_id


def change_rail_page(step):
    st.session_state["rail_page"] = st.session_state.get("rail_page", 0) + step


def toggle_topic_cards():
    st.session_state[SHOW_ALL_TOPICS_KEY] = not st.session_state.get(
        SHOW_ALL_TOPICS_KEY, False
    )


def clear_grid_filters():
    st.session_state["grid_filter"] = "All"
    st.session_state["grid_search"] = ""


def on_chart_select(chart_key):
    """
    Bar clicks. The chart gets a fresh key (empty selection) whenever the
    topic changes, so every bar click is reported here:
    - a different bar  -> select that topic
    - the selected bar -> clear the selection
    - nothing valid    -> clear the selection (never an empty/invalid id)
    """
    chart_state = st.session_state.get(chart_key) or {}
    points = (chart_state.get("selection") or {}).get(TOPIC_PICK) or []
    valid = set(learning_data["topic_id"])
    picked = [
        point.get("topic_id") for point in points
        if isinstance(point, dict) and point.get("topic_id") in valid
    ]
    current = st.session_state.get("topic_select")
    newly_picked = [topic_id for topic_id in picked if topic_id != current]

    if newly_picked:
        select_topic(newly_picked[-1])
    else:
        st.session_state["topic_select"] = None


def clear_topic_selection():
    """'✕ Clear selection': no topic, and a fresh (empty) chart selection."""
    st.session_state["topic_select"] = None
    st.session_state["chart_gen"] = st.session_state.get("chart_gen", 0) + 1


# Widget defaults (set before the widgets exist, never after)
st.session_state.setdefault("grid_filter", "All")
st.session_state.setdefault("grid_sort", GRID_SORTS[0])
st.session_state.setdefault("grid_search", "")

# Per-topic status and a stable thumbnail colour per topic
max_rate = learning_data["incorrect_rate_pct"].max()

topic_statuses = {
    row.topic_id: ui.topic_status(row.incorrect_rate_pct, max_rate)
    for row in learning_data.itertuples(index=False)
}

topic_seeds = {
    topic_id: index
    for index, topic_id in enumerate(learning_data["topic_id"])
}

# 4. Application heading
ui.render(ui.welcome_band(
    "🎓 Coursera Multimodal Intelligence Platform",
    subtitle="Learning Analytics Dashboard",
    caption="Demonstration using synthetic learner data"
))

# 5. Selected topic + "Analyse Your Own Course" (gradient banner)
# Create a mapping between topic IDs and readable names
topic_options = dict(
    zip(
        learning_data["topic_id"],
        learning_data["topic_name"]
    )
)

# No topic is selected until the educator picks one (topic card, Explore /
# Quick view / Ask AI, or a chart bar). None = nothing selected.
# A fresh session may restore an explicit choice from ?topic= in the URL;
# without the parameter nothing is selected.
if "topic_select" not in st.session_state:
    url_topic = st.query_params.get("topic")
    st.session_state["topic_select"] = url_topic if url_topic in topic_options else None

if st.session_state["topic_select"] not in topic_options:
    st.session_state["topic_select"] = None  # unknown or stale id: no selection

selected_topic = st.session_state["topic_select"]

# Keep the URL in step so a refresh keeps the selection
if selected_topic is not None:
    st.query_params["topic"] = selected_topic
elif "topic" in st.query_params:
    del st.query_params["topic"]

upload_section.render_hero()
upload_section.render_wizard()
upload_section.render_results(user, user_can_review)

selected_data = None
selected_comments = None

if selected_topic is not None:
    # Find the selected topic's analytics
    selected_data = learning_data[
        learning_data["topic_id"] == selected_topic
    ].iloc[0]

    # Find the student comments for that topic
    selected_comments = comments[
        comments["topic_id"] == selected_topic
    ]

# Shared callbacks for every topic card
card_callbacks = {
    "on_select": select_topic,
    "on_quick_view": open_quick_view,
    "on_explore": explore_topic,
    "on_ask": ask_ai_about_topic
}

# 6. Display summary metrics (clickable KPI cards)
col1, col2, col3 = st.columns(3)

with col1:
    ui.clickable_metric(
        "quiz_attempts",
        "Quiz Attempts",
        int(learning_data["total_attempts"].sum()),
        on_click=scroll_to_section,
        args=("topic-difficulty",)
    )

with col2:
    ui.clickable_metric(
        "student_comments",
        "Student Comments",
        len(comments),
        on_click=scroll_to_section,
        args=("student-feedback",)
    )

with col3:
    ui.clickable_metric(
        "topics_analysed",
        "Topics Analysed",
        len(learning_data),
        on_click=scroll_to_section,
        args=("topic-grid",)
    )

# 7. Topics students struggle with (dark rail carousel + chart)
most_difficult = learning_data.loc[
    learning_data["incorrect_rate_pct"].idxmax()
]

highest_error_text = (
    f"Highest quiz error rate: "
    f"{most_difficult['topic_name']} "
    f"({most_difficult['incorrect_rate_pct']:.2f}%)"
)

rail_topics = learning_data.sort_values(
    "incorrect_rate_pct", ascending=False
)

rail_pages = max(1, ceil(len(rail_topics) / RAIL_CARDS_PER_PAGE))
rail_page = min(max(st.session_state.get("rail_page", 0), 0), rail_pages - 1)
st.session_state["rail_page"] = rail_page

rail_slice = rail_topics.iloc[
    rail_page * RAIL_CARDS_PER_PAGE:(rail_page + 1) * RAIL_CARDS_PER_PAGE
]

with st.container(key="rail"):
    intro_col, cards_col = st.columns(
        [1, 3], gap="large", vertical_alignment="center"
    )

    with intro_col:
        ui.render(ui.rail_intro(
            "Topics Students Struggle With Most",
            highest_error_text,
            anchor_id="topic-difficulty"
        ))

    with cards_col:
        rail_columns = st.columns(RAIL_CARDS_PER_PAGE)

        for rail_column, (_, row) in zip(rail_columns, rail_slice.iterrows()):
            with rail_column:
                ui.topic_card(
                    row,
                    "rail",
                    row["topic_id"] == selected_topic,
                    status=topic_statuses[row["topic_id"]],
                    seed=0,
                    **card_callbacks
                )

        with st.container(
            key="rail-controls",
            horizontal=True,
            vertical_alignment="center",
            gap="small"
        ):
            ui.render(ui.rail_dots(rail_page, rail_pages))
            st.space("stretch")
            st.button(
                "‹",
                key="rail_prev",
                help="Previous topics",
                on_click=change_rail_page,
                args=(-1,),
                disabled=rail_page == 0
            )
            st.button(
                "›",
                key="rail_next",
                help="Next topics",
                on_click=change_rail_page,
                args=(1,),
                disabled=rail_page >= rail_pages - 1
            )

chart_data = learning_data[
    [
        "topic_id",
        "topic_name",
        "incorrect_rate_pct",
        "total_attempts",
        "comment_count"
    ]
]

chart_key = (
    f"difficulty_chart_{selected_topic or 'none'}_"
    f"{st.session_state.get('chart_gen', 0)}"
)

with st.container(border=True, key="lp_card_chart"):
    st.altair_chart(
        topic_difficulty_chart(chart_data, selected_topic),
        width="stretch",
        theme=None,
        on_select=partial(on_chart_select, chart_key),
        key=chart_key
    )

# 8. Detailed learning analytics (filterable card grid)
ui.render(ui.section_title(
    "Detailed Learning Analytics",
    anchor_id="topic-grid"
))

filter_counts = {"All": len(learning_data)}

for status in ui.TOPIC_STATUSES:
    filter_counts[status] = sum(
        1 for value in topic_statuses.values() if value == status
    )

grid_filter = st.pills(
    "Filter topics",
    ["All", *ui.TOPIC_STATUSES],
    required=True,
    format_func=lambda option: f"{option} ({filter_counts[option]})",
    key="grid_filter",
    label_visibility="collapsed"
)

sort_col, search_col = st.columns([3, 2], vertical_alignment="center")

with sort_col:
    grid_sort = st.segmented_control(
        "Sort topics",
        GRID_SORTS,
        required=True,
        key="grid_sort",
        label_visibility="collapsed"
    )

with search_col:
    grid_search = st.text_input(
        "Search topics",
        placeholder="Search topics…",
        key="grid_search",
        label_visibility="collapsed"
    )

grid_rows = learning_data.assign(
    status=learning_data["topic_id"].map(topic_statuses)
)

if grid_filter not in (None, "All"):
    grid_rows = grid_rows[grid_rows["status"] == grid_filter]

search_text = (grid_search or "").strip().lower()

if search_text:
    grid_rows = grid_rows[
        grid_rows["topic_name"].str.lower().str.contains(search_text, regex=False)
    ]

if grid_sort == "Most comments":
    grid_rows = grid_rows.sort_values(
        ["comment_count", "incorrect_rate_pct"], ascending=[False, False]
    )
elif grid_sort == "A–Z":
    grid_rows = grid_rows.sort_values(
        "topic_name", key=lambda names: names.str.lower()
    )
else:
    grid_rows = grid_rows.sort_values("incorrect_rate_pct", ascending=False)

show_all_topics = st.session_state.get(SHOW_ALL_TOPICS_KEY, False)
matching_topics = len(grid_rows)

visible_rows = (
    grid_rows if show_all_topics
    else grid_rows.head(INITIAL_TOPIC_CARDS)
)

st.caption(f"Showing {len(visible_rows)} of {matching_topics} topics")

if matching_topics == 0:
    with st.container(key="grid-empty"):
        ui.render(ui.empty_state("No topics match your filters."))
        st.button(
            "Clear filters",
            key="grid_clear",
            on_click=clear_grid_filters
        )

else:
    for row_start in range(0, len(visible_rows), 4):
        grid_columns = st.columns(4)

        for grid_column, (_, row) in zip(
            grid_columns, visible_rows.iloc[row_start:row_start + 4].iterrows()
        ):
            with grid_column:
                ui.topic_card(
                    row,
                    "grid",
                    row["topic_id"] == selected_topic,
                    status=row["status"],
                    seed=topic_seeds[row["topic_id"]],
                    **card_callbacks
                )

hidden_cards = matching_topics - INITIAL_TOPIC_CARDS

if hidden_cards > 0:
    st.button(
        "Show fewer" if show_all_topics else f"Show {hidden_cards} more",
        key="show-more",
        on_click=toggle_topic_cards
    )

with st.expander("View as table"):
    st.dataframe(
        learning_data[
            [
                "topic_name",
                "total_attempts",
                "incorrect_answers",
                "incorrect_rate_pct",
                "comment_count"
            ]
        ],
        hide_index=True,
        width="stretch"
    )

# Show the highest error-rate topic
ui.render(ui.info_strip(
    "Highest quiz error rate:",
    f"{most_difficult['topic_name']} "
    f"({most_difficult['incorrect_rate_pct']:.2f}%)",
    "Explore topic",
    href="#topic-grid"
))

# 9-12. Sections for the selected topic. Nothing is pre-selected: until
# the educator picks a topic, one empty-state card stands in for the
# topic metrics, Student Feedback, Related Video Evidence and the AI
# Educator Assistant. Everything after (review history, footer) still runs.
if selected_topic is None:
    ui.render(ui.topic_empty_state(anchor_id="student-feedback"))

else:
    # Sticky "Exploring: <topic>" bar with a way back to no selection
    with st.container(
        key="selection-bar",
        horizontal=True,
        vertical_alignment="center",
        gap="small"
    ):
        ui.render(
            '<div class="selection-bar-text">Exploring: '
            f'<b>{ui._esc(topic_options[selected_topic])}</b></div>'
        )
        st.button(
            "✕ Clear selection",
            key="clear_topic_selection",
            on_click=clear_topic_selection
        )

    # 9. Student feedback for the selected topic
    ui.render(ui.section_title("Student Feedback", anchor_id="student-feedback"))

    # Display topic metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Incorrect Answer Rate",
            f"{selected_data['incorrect_rate_pct']:.2f}%"
        )

    with col2:
        st.metric(
            "Quiz Attempts",
            int(selected_data["total_attempts"])
        )

    with col3:
        st.metric(
            "Student Comments",
            len(selected_comments)
        )

    # Display student comments, one light-blue panel per comment type
    if selected_comments.empty:
        st.info("No student comments found for this topic.")

    else:
        comment_groups = []

        for comment_type, group in selected_comments.groupby(
            "comment_type", sort=False
        ):
            rows = [
                ui.comment_row(
                    comment["comment_text"],
                    f"Comment {comment['comment_id']} · "
                    f"Type: {comment['comment_type']}"
                )
                for _, comment in group.iterrows()
            ]

            comment_groups.append((comment_type, rows))

        if len(comment_groups) == 1:
            comment_type, rows = comment_groups[0]
            ui.render(ui.trend_panel(
                comment_type,
                ui.card_grid(rows, columns=3)
            ))

        else:
            ui.render(ui.card_grid(
                [
                    ui.trend_panel(comment_type, ui.comment_list(rows))
                    for comment_type, rows in comment_groups
                ],
                columns=min(3, len(comment_groups))
            ))


    # 10. Connect learning difficulties to video lessons
    ui.render(ui.section_title("Related Video Evidence"))

    # Find selected topic's video metadata
    matching_video = video_topics[
        (video_topics["topic_id"] == selected_topic)
        & (video_topics["course_id"] == selected_data["course_id"])
        & (video_topics["video_id"] == selected_data["video_id"])
    ]

    with st.container(key="feature-video"):
        if matching_video.empty:
            st.info("No video segment found for this topic.")

        else:
            video_info = matching_video.iloc[0]

            start_time = video_info["approx_start_time"]
            end_time = video_info["approx_end_time"]

            # Convert HH:MM:SS into seconds
            def time_to_seconds(time_text):
                hours, minutes, seconds = map(
                    int,
                    str(time_text).split(":")
                )

                return hours * 3600 + minutes * 60 + seconds

            start_seconds = time_to_seconds(start_time)

            # Find the MP4 video
            video_files = list(RAW_DIR.glob("*.mp4"))

            video_col, frames_col = st.columns(
                [3, 2], gap="large", vertical_alignment="center"
            )

            with video_col:
                ui.render(ui.feature_header(
                    "Video evidence",
                    video_info["topic_name"],
                    f"Approximate start: {start_time} · "
                    f"Approximate end: {end_time}"
                ))

                if video_files:
                    video_path = video_files[0]

                    st.video(
                        str(video_path),
                        start_time=start_seconds
                    )

                else:
                    st.warning("No MP4 video found in data/raw.")

                st.caption(
                    "Video timestamps are approximate and aligned "
                    "using the generated lesson transcript."
                )

            with frames_col:
                frames = load_topic_frames(
                    selected_topic,
                    selected_data["video_id"]
                )

                frame_thumbs = []

                for number, (seconds, frame_path) in enumerate(frames, start=1):
                    image_src = ui.image_data_uri(
                        frame_path,
                        mtime=Path(frame_path).stat().st_mtime
                    )

                    if image_src:
                        frame_thumbs.append(ui.step_thumb(
                            f"{seconds // 60:02d}:{seconds % 60:02d}",
                            f"Frame {number} of {len(frames)}",
                            image_src=image_src
                        ))

                if frame_thumbs:
                    ui.render(ui.step_row(frame_thumbs))

    # 11. AI EDUCATOR ASSISTANT (gradient section)
    with st.container(key="ai-section"):
        intro_col, form_col = st.columns(
            [2, 3], gap="large", vertical_alignment="center"
        )

        with intro_col:
            ui.render(ui.hero_heading(
                "🤖 AI Educator Assistant",
                "Ask questions about learner difficulties, "
                "quiz performance and course evidence.",
                anchor_id="ai-assistant",
                level=2
            ))

        with form_col:
            with st.container(key="ai-card"):
                question = st.text_area(
                    "Your question",
                    value=(
                        f"Why are students struggling with "
                        f"{topic_options[selected_topic]}? "
                        f"Use quiz results, student feedback and "
                        f"video transcript evidence."
                    ),
                    height=120,
                    key=f"educator_question_{selected_topic}"
                )

                if not user_can_review:
                    st.info(
                        "Your account has view-only access. Generating insights "
                        "and saving reviews requires the educator or admin role."
                    )

                # Generate a new report
                if st.button(
                    "Generate Learning Insights",
                    type="primary",
                    disabled=not user_can_review
                ):

                    if not question.strip():
                        st.warning("Please enter a question.")

                    else:
                        with st.spinner("Retrieving and analyzing evidence..."):
                            try:
                                result = ask_course(                            ###---USER INPUT question---###
                                    question,
                                    topic_id=selected_topic
                                )

                                # Preserve the report across Streamlit reruns
                                st.session_state["rag_report"] = {
                                    "topic_id": selected_topic,
                                    "result": result
                                }

                            except Exception as error:
                                st.error(f"Unable to generate insights: {error}")

    # Retrieve the last generated report
    saved_report = st.session_state.get("rag_report")

    # Only show a report for the currently selected topic
    if (
        saved_report is not None
        and saved_report["topic_id"] == selected_topic
    ):
        result = saved_report["result"]

        with st.container(border=True, key="lp_card_insights"):
            ui.render(ui.card_title("Learning Insights"))
            st.markdown(result["answer"])                               # Display the Gemini answer

            ui.cited_evidence_pills(
                "dashboard", result["answer"], result.get("sources", [])
            )

        ui.render(ui.section_title("Supporting Evidence"))

        sources = result.get("sources", [])

        if not sources:
            st.info("No supporting evidence was found.")

        else:
            video_files = list(RAW_DIR.glob("*.mp4"))

            # Interactive evidence: chips, view switcher, sort, search, cards /
            # list / timeline and the details dialog (frontend/ui/components.py)
            ui.evidence_explorer(
                "dashboard",
                sources,
                result["answer"],
                topic_name=topic_options[selected_topic],
                comment_types=dict(zip(
                    comments["comment_id"].astype(str),
                    comments["comment_type"].astype(str)
                )),
                base_dir=BASE_DIR,
                video_path=str(video_files[0]) if video_files else None,
                heading_for=lambda source: (
                    f"{source['reference']} — "
                    f"{source['modality']} — "
                    f"{source['source_id']}"
                ),
                columns=3
            )

        # 12. EDUCATOR REVIEW
        with st.container(border=True, key="lp_card_review"):
            ui.render(ui.card_title("Educator Review"))

            st.write(
                "Review the AI-generated insights and "
                "record your decision."
            )

            with st.form("educator_review_form"):

                decision = st.segmented_control(
                    "Review decision",
                    [
                        "Approve",
                        "Request changes",
                        "Reject"
                    ],
                    default="Approve",
                    required=True,
                    key="chips_review_decision"
                )

                notes = st.text_area(
                    "Reviewer comments",
                    placeholder="Explain your decision...",
                    key="reviewer_notes"
                )

                submitted = st.form_submit_button(
                    "Save Review Decision",
                    type="primary"
                )

                if submitted:

                    if not user_can_review:
                        st.error("Your account cannot save review decisions.")

                    elif decision != "Approve" and not notes.strip():
                        st.warning(
                            "Please explain why changes are needed "
                            "or why the report was rejected."
                        )

                    elif not sources:
                        st.warning(
                            "Cannot review a report without evidence."
                        )

                    else:
                        review_id = save_review(
                            topic_id=selected_topic,
                            question=result["question"],
                            answer=result["answer"],
                            sources=sources,
                            decision=decision,
                            notes=notes,
                            reviewer=user["username"]
                        )

                        st.success(
                            f"Review #{review_id} saved successfully."
                        )

# 13. REVIEW HISTORY
ui.render(ui.section_title("Educator Review History"))

history = get_review_history()

if not history:
    st.info("No educator reviews have been saved yet.")

else:
    for row_start in range(0, len(history), 3):
        history_cols = st.columns(3)

        for history_col, review in zip(
            history_cols, history[row_start:row_start + 3]
        ):
            with history_col:
                with st.container(
                    border=True,
                    key=f"lp_card_history_{review['review_id']}"
                ):
                    ui.render(ui.review_summary(
                        review["decision"],
                        ui.decision_variant(review["decision"]),
                        [
                            ("Topic:", review["topic_id"]),
                            ("Reviewed at (UTC):", ui.format_timestamp(review["reviewed_at"])),
                            ("Reviewer notes:", review["reviewer_notes"] or "None")
                        ]
                    ))

                    with st.expander(
                        f"Review #{review['review_id']} — "
                        f"{review['topic_id']} — "
                        f"{review['decision']}"
                    ):
                        st.write("**Decision:**", review["decision"])
                        st.write(
                            "**Reviewer:**",
                            review.get("reviewer") or "Unknown (before sign-in)"
                        )
                        st.write("**Topic:**", review["topic_id"])

                        st.write(
                            "**Reviewed at (UTC):**",
                            review["reviewed_at"]
                        )

                        st.write(
                            "**Reviewer notes:**",
                            review["reviewer_notes"] or "None"
                        )

                        st.write(
                            "**Evidence IDs:**",
                            review["evidence_ids"]
                        )

                        st.write("**Original question:**")
                        st.write(review["question"])

                        st.write("**Saved AI answer:**")
                        st.markdown(review["ai_answer"])

st.caption(
    "Prototype using synthetic learner data. "
    "Review decisions are stored locally with the "
    "signed-in reviewer's username."
)

# ------------------------------------------------------------------
# Quick view dialog (opened once per click; closing it needs no state)
# ------------------------------------------------------------------
quick_view_topic = st.session_state.pop("quick_view_topic", None)

if quick_view_topic in topic_options:
    quick_row = learning_data[
        learning_data["topic_id"] == quick_view_topic
    ].iloc[0]

    quick_video = video_topics[
        (video_topics["topic_id"] == quick_view_topic)
        & (video_topics["course_id"] == quick_row["course_id"])
        & (video_topics["video_id"] == quick_row["video_id"])
    ]

    quick_segment = None

    if not quick_video.empty:
        quick_segment = {
            "start": quick_video.iloc[0]["approx_start_time"],
            "end": quick_video.iloc[0]["approx_end_time"],
            "start_seconds": segment_start_seconds(
                quick_video.iloc[0]["approx_start_time"]
            )
        }

    quick_video_files = list(RAW_DIR.glob("*.mp4"))

    ui.topic_dialog(
        quick_row,
        topic_statuses[quick_view_topic],
        comments[comments["topic_id"] == quick_view_topic],
        quick_segment,
        str(quick_video_files[0]) if quick_video_files else None,
        select_topic,
        ask_ai_about_topic
    )

# Scroll requested by a card, KPI or dialog button (then cleared)
scroll_target = st.session_state.pop("scroll_to", None)

if scroll_target:
    st.session_state["scroll_nonce"] = st.session_state.get("scroll_nonce", 0) + 1
    ui.scroll_to(scroll_target, st.session_state["scroll_nonce"])
