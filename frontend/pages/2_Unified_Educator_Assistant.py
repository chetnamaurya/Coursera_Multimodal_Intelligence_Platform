
from pathlib import Path
import sys

import pandas as pd
import streamlit as st


# ==================================================
# 1. PROJECT SETUP
# ==================================================

BASE_DIR = Path(__file__).resolve().parents[2]

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ai.rag_pipeline import ask_course

from backend.review_store import (
    initialize_review_database,
    save_review,
    get_review_history
)

from frontend.auth_gate import can_review, require_login
from frontend.ui import components as ui
from frontend.ui.theme import inject_css


# ==================================================
# 2. FILE PATHS
# ==================================================

ANALYTICS_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "learning_difficulty_summary.csv"
)

RAW_DIR = BASE_DIR / "data" / "raw"
COMMENTS_PATH = RAW_DIR / "student_comments.csv"

# Evidence cards shown before "Show N more"
INITIAL_EVIDENCE_CARDS = 8
SHOW_ALL_EVIDENCE_KEY = "show_all_evidence_cards"


# ==================================================
# 3. STREAMLIT PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="Educator Intelligence Platform",
    page_icon="🎓",
    layout="wide"
)
inject_css()
ui.navbar(active="Educator Assistant")

# Nothing below renders until the visitor signs in
user = require_login()
user_can_review = can_review(user)

ui.render(ui.welcome_band(
    "🎓 Unified Educator Intelligence Platform",
    subtitle=(
        "Analyse learning difficulties, inspect supporting "
        "evidence, generate AI recommendations and "
        "review reports before accepting them."
    )
))


@st.cache_data
def load_comment_types():
    """comment_id -> comment_type, for labelling learner-comment evidence."""
    if not COMMENTS_PATH.exists():
        return {}

    comment_table = pd.read_csv(COMMENTS_PATH)

    return dict(zip(
        comment_table["comment_id"].astype(str),
        comment_table["comment_type"].astype(str)
    ))


def evidence_heading(source):
    """The evidence heading this page has always used."""
    reference = source.get(
        "reference", "Unknown"
    )

    modality = source.get(
        "modality", "unknown"
    )

    location = source.get(
        "source_location", "Unknown source"
    )

    return (
        f"{reference} | "
        f"{modality.replace('_', ' ').title()} | "
        f"{location}"
    )


# ==================================================
# 4. INITIALIZE SQLITE DATABASE
# ==================================================

try:
    initialize_review_database()

except Exception as error:
    st.error(
        f"Unable to initialize review database: {error}"
    )
    st.stop()


# ==================================================
# 5. LOAD LEARNING ANALYTICS
# ==================================================

@st.cache_data
def load_analytics():

    if not ANALYTICS_PATH.exists():
        raise FileNotFoundError(
            "Learning analytics summary is missing."
        )

    return pd.read_csv(ANALYTICS_PATH)


try:
    analytics = load_analytics()

except Exception as error:
    st.error(str(error))
    st.stop()


# ==================================================
# 6. SELECT EDUCATIONAL TOPIC (gradient banner)
# ==================================================

topic_ids = (
    analytics["topic_id"]
    .dropna()
    .unique()
    .tolist()
)

if not topic_ids:
    st.warning("No learning topics are available.")
    st.stop()


topic_names = {}

for _, row in analytics.iterrows():

    topic_id = str(row["topic_id"])

    topic_names[topic_id] = str(
        row.get("topic_name", topic_id)
    )


with ui.hero_controls():
    heading_col, control_col = st.columns(
        [3, 2], gap="large", vertical_alignment="center"
    )

    with heading_col:
        ui.render(ui.hero_heading("Educator Controls"))

    with control_col:
        selected_topic = st.selectbox(
            "Select learning topic",
            options=topic_ids,
            format_func=lambda topic: (
                f"{topic_names.get(topic, topic)} ({topic})"
            )
        )


# ==================================================
# 7. DISPLAY LEARNING ANALYTICS
# ==================================================

ui.render(ui.section_title("1. Learning Performance"))

selected_data = analytics[
    analytics["topic_id"] == selected_topic
]

performance = selected_data.iloc[0]

kpi_columns = st.columns(5)

kpis = [
    ("Total attempts", int(performance["total_attempts"])),
    ("Correct answers", int(performance["correct_answers"])),
    ("Incorrect answers", int(performance["incorrect_answers"])),
    ("Incorrect rate", f"{performance['incorrect_rate_pct']:.2f}%"),
    ("Comments", int(performance["comment_count"]))
]

for kpi_column, (label, value) in zip(kpi_columns, kpis):
    with kpi_column:
        st.metric(label, value)

with st.expander("View as table"):
    st.dataframe(
        selected_data,
        width="stretch",
        hide_index=True
    )


# ==================================================
# 8. EDUCATOR QUESTION
# ==================================================

ui.render(ui.section_title("2. Generate AI Learning Insights"))

with st.container(key="feature-generate"):
    default_question = (
        f"Why are students struggling with "
        f"{topic_names[selected_topic]}? "
        f"Use quiz analytics, student comments, "
        f"video transcripts and course documents. "
        f"Recommend practical teaching improvements."
    )

    question = st.text_area(
        "Ask a question",
        value=default_question,
        height=120,
        key=f"educator_question_{selected_topic}"
    )

    if not user_can_review:
        st.info(
            "Your account has view-only access. Generating insights "
            "and saving reviews requires the educator or admin role."
        )

    generate_clicked = st.button(
        "Generate Learning Insights",
        type="primary",
        disabled=not user_can_review
    )


    # ==================================================
    # 9. GENERATE AI REPORT
    # ==================================================

    if generate_clicked:

        if not question.strip():

            st.warning(
                "Please enter a question."
            )

        else:

            with st.spinner(
                "Retrieving evidence and generating report..."
            ):

                try:

                    result = ask_course(
                        question=question.strip(),
                        topic_id=selected_topic
                    )

                    st.session_state[
                        "educator_review_report"
                    ] = {
                        "topic_id": selected_topic,
                        "question": result["question"],
                        "answer": result["answer"],
                        "sources": result["sources"]
                    }

                    st.session_state[
                        "educator_review_saved"
                    ] = False

                    st.success(
                        "AI report generated. "
                        "Citation IDs were validated."
                    )

                except Exception as error:

                    st.error(
                        "Unable to generate AI report."
                    )

                    st.caption(str(error))


# ==================================================
# 10. DISPLAY GENERATED REPORT
# ==================================================

report = st.session_state.get(
    "educator_review_report"
)

report_is_current = (
    report is not None
    and report["topic_id"] == selected_topic
)

if report_is_current:

    ui.render(ui.section_title("3. AI Learning Insights"))

    ui.render(ui.info_strip(
        "This report was generated by AI.",
        "Citation IDs have been checked, but "
        "the accuracy of each claim still "
        "requires educator review."
    ))

    with st.container(border=True, key="lp_card_insights"):
        st.markdown(
            report["answer"]
        )

        ui.cited_evidence_pills(
            "assistant", report["answer"], report["sources"]
        )


    # ==============================================
    # 11. SUPPORTING EVIDENCE
    # ==============================================

    ui.render(ui.section_title("4. Supporting Evidence"))

    sources = report["sources"]

    st.caption(
        f"{len(sources)} evidence records retrieved"
    )

    video_files = list(RAW_DIR.glob("*.mp4"))

    # Interactive evidence: chips, view switcher, sort, search, cards /
    # list / timeline and the details dialog (frontend/ui/components.py)
    ui.evidence_explorer(
        "assistant",
        sources,
        report["answer"],
        topic_name=topic_names[selected_topic],
        comment_types=load_comment_types(),
        base_dir=BASE_DIR,
        video_path=str(video_files[0]) if video_files else None,
        heading_for=evidence_heading,
        columns=4,
        initial_cards=INITIAL_EVIDENCE_CARDS,
        show_all_key=SHOW_ALL_EVIDENCE_KEY
    )


    # ==============================================
    # 12. EDUCATOR REVIEW FORM
    # ==============================================

    ui.render(ui.section_title("5. Educator Review and Approval"))

    with st.container(key="feature-review"):
        st.write(
            "Review the AI report and supporting evidence "
            "before saving your decision."
        )

        already_saved = st.session_state.get(
            "educator_review_saved",
            False
        )

        if already_saved:

            st.success(
                "Your decision for this generated report "
                "has already been saved."
            )

        else:

            with st.form(
                "educator_approval_form",
                clear_on_submit=False
            ):

                decision = st.segmented_control(
                    "Select your review decision",
                    options=[
                        "Approve",
                        "Request changes",
                        "Reject"
                    ],
                    default="Approve",
                    required=True,
                    key="chips_review_decision"
                )

                reviewer_notes = st.text_area(
                    "Reviewer comments",
                    placeholder=(
                        "Explain your decision. "
                        "Mention any improvements needed."
                    ),
                    height=120,
                    key="reviewer_notes"
                )

                submitted = st.form_submit_button(
                    "Save Review Decision",
                    type="primary"
                )

            if submitted:

                if not user_can_review:

                    st.error(
                        "Your account cannot save review decisions."
                    )

                elif (
                    decision != "Approve"
                    and not reviewer_notes.strip()
                ):

                    st.warning(
                        "Please explain why the report "
                        "requires changes or was rejected."
                    )

                else:

                    try:

                        save_review(
                            topic_id=report["topic_id"],
                            question=report["question"],
                            answer=report["answer"],
                            sources=report["sources"],
                            decision=decision,
                            notes=reviewer_notes.strip(),
                            reviewer=user["username"]
                        )

                        st.session_state[
                            "educator_review_saved"
                        ] = True

                        st.success(
                            "Review decision saved "
                            "successfully to SQLite."
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            "Unable to save review decision."
                        )

                        st.caption(str(error))


# ==================================================
# 13. REVIEW HISTORY
# ==================================================

ui.render(ui.section_title("6. Educator Review History"))

try:

    history = get_review_history()

    if isinstance(history, pd.DataFrame):
        history_df = history.copy()

    elif isinstance(history, list):
        history_df = pd.DataFrame(history)

    elif isinstance(history, dict):
        history_df = pd.DataFrame(
            history.get("reviews", [])
        )

    else:
        history_df = pd.DataFrame()

    if history_df.empty:

        st.info(
            "No educator review decisions "
            "have been saved yet."
        )

    else:

        if "topic_id" in history_df.columns:

            filtered_history = history_df[
                history_df["topic_id"]
                == selected_topic
            ]

        else:
            filtered_history = history_df

        total_column, _ = st.columns([1, 3])

        with total_column:
            st.metric(
                "Total saved reviews",
                len(history_df)
            )

        st.write(
            "Review decisions for the selected topic:"
        )

        if filtered_history.empty:

            st.info(
                "No reviews found for this topic."
            )

        else:

            history_rows = filtered_history.to_dict("records")

            for row_start in range(0, len(history_rows), 3):
                history_columns = st.columns(3)

                for history_column, review in zip(
                    history_columns, history_rows[row_start:row_start + 3]
                ):
                    with history_column:
                        with st.container(
                            border=True,
                            key=f"lp_card_history_{review.get('review_id', row_start)}"
                        ):
                            ui.render(ui.review_summary(
                                review.get("decision", ""),
                                ui.decision_variant(review.get("decision")),
                                [
                                    ("Topic:", review.get("topic_id", "")),
                                    (
                                        "Reviewed at (UTC):",
                                        ui.format_timestamp(review.get("reviewed_at", ""))
                                    ),
                                    (
                                        "Reviewer notes:",
                                        review.get("reviewer_notes") or "None"
                                    )
                                ]
                            ))

            with st.expander("View as table"):
                st.dataframe(
                    filtered_history,
                    width="stretch",
                    hide_index=True
                )

except Exception as error:

    st.error(
        "Unable to load review history."
    )

    st.caption(str(error))


# ==================================================
# 14. FOOTER
# ==================================================

st.caption(
    "Coursera Multimodal Intelligence Platform | "
    "AI Insights and Human Review"
)
