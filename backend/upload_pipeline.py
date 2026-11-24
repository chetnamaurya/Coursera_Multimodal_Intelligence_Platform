"""
Processing pipeline for educator-uploaded course materials.

Pure functions (no Streamlit) that turn uploaded files in five
modalities into a searchable Chroma collection and AI reports:

    quiz CSVs        -> learning summary -> "quiz_analytics" evidence
    comment CSV      -> "learner_comment" evidence
    video/transcript -> segments -> topics -> "video_transcript" evidence
    video/images     -> frames -> Gemini descriptions
                                      -> "video_visual_analysis" evidence
    PDF/PPTX         -> pages/slides -> chunks -> "course_document" evidence

Everything for one upload lives in data/uploads/<upload_id>/ and in the
Chroma collection "upload_<upload_id>". The original "coursera_evidence"
collection is never written to.

The logic mirrors the original one-off scripts, which run at import time
and therefore cannot be imported:
    pipelines/analyze_learning.py        -> build_learning_summary()
    pipelines/transcribe_video.py        -> transcribe_video()
    pipelines/map_transcript_topics.py   -> map_segments_to_topics()
    pipelines/extract_video_frames.py    -> extract_frames()
    pipelines/ingest_documents.py        -> extract_documents()
    ai/index_documents.py (split_text)   -> split_text()
    ai/build_evidence_index.py,
    ai/index_transcripts.py,
    ai/index_documents.py,
    ai/index_visual_analysis.py,
    ai/align_visual_evidence.py          -> the metadata schemas below
"""

import hashlib
import json
import os
import re
import shutil
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "data" / "uploads"
DATABASE_PATH = BASE_DIR / "vector_database"

ORIGINAL_COLLECTION = "coursera_evidence"
COLLECTION_PREFIX = "upload_"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
WHISPER_MODEL = "base.en"

# Same value as ai/align_visual_evidence.py
MAX_IMAGE_DIFFERENCE = 14.0

UPLOAD_ID_PATTERN = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{8}$")

REQUIRED_COLUMNS = {
    "quiz_responses": [
        "course_id", "video_id", "student_id", "attempt_id", "question_id",
        "topic_id", "selected_option", "correct_option", "is_correct",
        "attempt_number",
    ],
    "quiz_questions": [
        "course_id", "video_id", "question_id", "topic_id", "question_text",
        "option_a", "option_b", "option_c", "option_d", "correct_option",
    ],
    "student_comments": [
        "comment_id", "course_id", "video_id", "student_id", "topic_id",
        "comment_text", "comment_type",
    ],
    "video_topics": [
        "course_id", "video_id", "topic_id", "topic_name",
        "approx_start_time", "approx_end_time",
    ],
}

SUMMARY_COLUMNS = [
    "course_id", "video_id", "topic_id", "total_attempts", "correct_answers",
    "incorrect_answers", "incorrect_rate_pct", "comment_count", "topic_name",
]

DOCUMENT_SUFFIXES = {".pdf", ".pptx"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
TRANSCRIPT_SUFFIXES = {".json", ".srt", ".vtt"}


class UploadValidationError(ValueError):
    """Raised when uploaded files cannot be processed; .errors lists why."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


# ==================================================
# 1. UPLOAD FOLDERS
# ==================================================

def new_upload_id():
    """Short sortable id: YYYYMMDD-HHMMSS-<8 hex chars>."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def _check_upload_id(upload_id):
    # Guards the folder path and collection name against injection
    if not UPLOAD_ID_PATTERN.match(str(upload_id)):
        raise ValueError(f"Invalid upload id: {upload_id!r}")
    return str(upload_id)


def collection_name_for(upload_id):
    return f"{COLLECTION_PREFIX}{_check_upload_id(upload_id)}"


def upload_dir(upload_id):
    return UPLOADS_DIR / _check_upload_id(upload_id)


def save_uploaded_file(upload_id, file_name, data, subfolder="raw"):
    """
    Write uploaded bytes into data/uploads/<id>/<subfolder>/ under a safe
    file name and return the path. (Helper for the upload UI.)
    """
    safe_name = re.sub(r"[^A-Za-z0-9._ ()-]+", "_", Path(str(file_name)).name).strip() or "file"
    folder = upload_dir(upload_id) / subfolder
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / safe_name
    path.write_bytes(data)
    return path


def _relative(path):
    """Project-relative posix path (used as source_file, like the originals)."""
    path = Path(path).resolve()
    try:
        return path.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def _report(progress_cb, stage, fraction, message=""):
    if progress_cb is not None:
        progress_cb(stage, max(0.0, min(1.0, float(fraction))), message)


# ==================================================
# 2. CSV VALIDATION
# ==================================================

def read_csv(path):
    """Read an uploaded CSV (the demo files start with a UTF-8 BOM)."""
    frame = pd.read_csv(path, encoding="utf-8-sig", skip_blank_lines=True)
    frame.columns = [str(column).strip() for column in frame.columns]
    return frame


def _to_seconds(value):
    """HH:MM:SS or MM:SS -> seconds (as in ai/align_visual_evidence.py)."""
    parts = str(value).strip().split(":")
    numbers = [float(part) for part in parts]

    if len(numbers) == 2:
        return numbers[0] * 60 + numbers[1]

    if len(numbers) == 3:
        return numbers[0] * 3600 + numbers[1] * 60 + numbers[2]

    raise ValueError(f"Invalid timestamp: {value}")


def validate_csv(df, kind):
    """Human-readable problems with an uploaded CSV ([] means valid)."""
    if kind not in REQUIRED_COLUMNS:
        return [f"Unknown CSV type: {kind}"]

    label = kind.replace("_", " ")

    if df is None or df.empty:
        return [f"The {label} file has no rows."]

    errors = []
    missing = [column for column in REQUIRED_COLUMNS[kind] if column not in df.columns]

    if missing:
        errors.append(f"The {label} file is missing columns: {', '.join(missing)}.")
        return errors

    for column in ("course_id", "video_id", "topic_id"):
        if df[column].isna().any() or (df[column].astype(str).str.strip() == "").any():
            errors.append(f"The {label} file has empty values in '{column}'.")

    if kind == "quiz_responses":
        values = set(df["is_correct"].dropna().astype(str).str.strip().str.lower())
        allowed = {"0", "1", "true", "false", "0.0", "1.0"}

        if not values <= allowed:
            bad = sorted(values - allowed)[:5]
            errors.append(f"'is_correct' must be 0/1 or true/false; found {bad}.")

        if df["is_correct"].isna().any():
            errors.append("'is_correct' has empty values.")

    if kind == "student_comments":
        if df["comment_id"].duplicated().any():
            errors.append("'comment_id' values must be unique.")

        if df["comment_text"].isna().all():
            errors.append("All 'comment_text' values are empty.")

    if kind == "video_topics":
        duplicated = df.duplicated(["course_id", "video_id", "topic_id"])

        if duplicated.any():
            errors.append("Duplicate topic identifiers found (course_id, video_id, topic_id).")

        for index, row in df.iterrows():
            try:
                start = _to_seconds(row["approx_start_time"])
                end = _to_seconds(row["approx_end_time"])
            except ValueError:
                errors.append(f"Row {index + 2}: times must look like HH:MM:SS.")
                continue

            if end <= start:
                errors.append(f"Row {index + 2}: approx_end_time must be after approx_start_time.")

    return errors


def _bool_series(series):
    mapping = {"1": 1, "0": 0, "true": 1, "false": 0, "1.0": 1, "0.0": 0}
    return series.astype(str).str.strip().str.lower().map(mapping).astype(int)


# ==================================================
# 3. LEARNING SUMMARY (pipelines/analyze_learning.py)
# ==================================================

def build_learning_summary(quiz_df, comments_df=None, topics_df=None):
    """
    Same calculations and columns as data/processed/
    learning_difficulty_summary.csv. Without video topics, topic_name is
    derived from topic_id.
    """
    keys = ["course_id", "video_id", "topic_id"]
    quiz = quiz_df.copy()
    quiz["is_correct"] = _bool_series(quiz["is_correct"])

    for key in keys:
        quiz[key] = quiz[key].astype(str).str.strip()

    quiz_summary = (
        quiz.groupby(keys)
        .agg(
            total_attempts=("is_correct", "size"),
            correct_answers=("is_correct", "sum"),
        )
        .reset_index()
    )

    quiz_summary["incorrect_answers"] = (
        quiz_summary["total_attempts"] - quiz_summary["correct_answers"]
    )

    quiz_summary["incorrect_rate_pct"] = (
        quiz_summary["incorrect_answers"] / quiz_summary["total_attempts"] * 100
    ).round(2)

    if comments_df is not None and not comments_df.empty:
        comments = comments_df.copy()

        for key in keys:
            comments[key] = comments[key].astype(str).str.strip()

        comment_summary = comments.groupby(keys).size().reset_index(name="comment_count")

        summary = quiz_summary.merge(
            comment_summary, on=keys, how="left", validate="one_to_one"
        )
    else:
        summary = quiz_summary.assign(comment_count=0)

    summary["comment_count"] = summary["comment_count"].fillna(0).astype(int)

    if topics_df is not None and not topics_df.empty:
        topic_lookup = topics_df[keys + ["topic_name"]].copy()

        for key in keys:
            topic_lookup[key] = topic_lookup[key].astype(str).str.strip()

        topic_lookup = topic_lookup.drop_duplicates()

        if topic_lookup.duplicated(keys).any():
            raise ValueError("Duplicate topic identifiers found.")

        summary = summary.merge(topic_lookup, on=keys, how="left", validate="many_to_one")
    else:
        summary["topic_name"] = None

    # Topics missing from video_topics (or no topics file at all)
    missing_names = summary["topic_name"].isna()
    summary.loc[missing_names, "topic_name"] = (
        summary.loc[missing_names, "topic_id"].str.replace("_", " ")
    )

    summary = summary.sort_values(by="incorrect_rate_pct", ascending=False)

    return summary[SUMMARY_COLUMNS].reset_index(drop=True)


# ==================================================
# 4. TRANSCRIPTS (pipelines/transcribe_video.py)
# ==================================================

@lru_cache(maxsize=1)
def _whisper_model():
    from faster_whisper import WhisperModel

    # Same settings as pipelines/transcribe_video.py
    return WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")


def transcribe_video(video_path, progress_cb=None, video_id="VIDEO"):
    """
    Speech-to-text with faster-whisper base.en (cpu, int8, VAD filter):
    [{segment_id, start_seconds, end_seconds, text}, ...].
    """
    video_path = Path(video_path)
    _report(progress_cb, "transcribe", 0.0, "Loading the speech model")

    segments, info = _whisper_model().transcribe(
        str(video_path), language="en", beam_size=5, vad_filter=True
    )

    duration = float(getattr(info, "duration", 0) or 0)
    records = []

    for index, segment in enumerate(segments, start=1):
        text = segment.text.strip()

        if text:
            records.append({
                "segment_id": f"{video_id}_T{index:04d}",
                "start_seconds": round(segment.start, 2),
                "end_seconds": round(segment.end, 2),
                "text": text,
            })

        if duration:
            _report(progress_cb, "transcribe", segment.end / duration,
                    f"Transcribed {segment.end:.0f}s of {duration:.0f}s")

    _report(progress_cb, "transcribe", 1.0, f"{len(records)} segments")
    return records


_SUBTITLE_TIME = re.compile(
    r"(\d{1,2}:)?(\d{1,2}):(\d{2})[.,](\d{1,3})\s*-->\s*(\d{1,2}:)?(\d{1,2}):(\d{2})[.,](\d{1,3})"
)


def _subtitle_seconds(hours, minutes, seconds, fraction):
    hours = int(hours.rstrip(":")) if hours else 0
    return hours * 3600 + int(minutes) * 60 + int(seconds) + int(fraction.ljust(3, "0")) / 1000


def load_transcript(path, video_id="VIDEO"):
    """
    Read an uploaded transcript instead of transcribing: .json in the
    format of data/raw/transcripts/video_transcript.json, or .srt / .vtt.
    """
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))

        if isinstance(data, dict):
            data = data.get("segments", [])

        records = []

        for index, item in enumerate(data, start=1):
            text = str(item.get("text", "")).strip()

            if not text:
                continue

            records.append({
                "segment_id": str(item.get("segment_id") or f"{video_id}_T{index:04d}"),
                "start_seconds": float(item["start_seconds"]),
                "end_seconds": float(item["end_seconds"]),
                "text": text,
            })

        return records

    if suffix in (".srt", ".vtt"):
        blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").replace("\r\n", "\n"))
        records = []

        for block in blocks:
            lines = [line.strip() for line in block.strip().split("\n") if line.strip()]
            time_index = next((i for i, line in enumerate(lines) if "-->" in line), None)

            if time_index is None:
                continue

            match = _SUBTITLE_TIME.search(lines[time_index])

            if not match:
                continue

            text = " ".join(
                re.sub(r"<[^>]+>", "", line) for line in lines[time_index + 1:]
            ).strip()

            if text:
                groups = match.groups()
                records.append({
                    "segment_id": f"{video_id}_T{len(records) + 1:04d}",
                    "start_seconds": round(_subtitle_seconds(*groups[:4]), 2),
                    "end_seconds": round(_subtitle_seconds(*groups[4:]), 2),
                    "text": text,
                })

        return records

    raise ValueError(f"Unsupported transcript format: {path.name} (use .json, .srt or .vtt)")


def _topic_ranges(topics_df, video_id=None):
    """Topic time ranges in seconds, optionally for one video only."""
    if topics_df is None or topics_df.empty:
        return []

    ranges = []

    for _, row in topics_df.iterrows():
        if video_id is not None and str(row["video_id"]).strip() != str(video_id):
            continue

        try:
            start = _to_seconds(row["approx_start_time"])
            end = _to_seconds(row["approx_end_time"])
        except ValueError:
            continue

        if end <= start:
            continue

        ranges.append({
            "course_id": str(row["course_id"]).strip(),
            "video_id": str(row["video_id"]).strip(),
            "topic_id": str(row["topic_id"]).strip(),
            "topic_name": str(row["topic_name"]),
            "start": start,
            "end": end,
        })

    return ranges


def map_segments_to_topics(segments, topics_df=None, video_id=None):
    """
    Attach topics by time overlap (pipelines/map_transcript_topics.py):
    one row per overlapping (segment, topic). Segments with no overlap,
    or every segment when there are no topics, get topic_id "general".
    """
    ranges = _topic_ranges(topics_df, video_id)
    mapped = []

    for segment in segments:
        start, end = float(segment["start_seconds"]), float(segment["end_seconds"])
        matches = [topic for topic in ranges if start < topic["end"] and end > topic["start"]]

        for topic in matches:
            mapped.append({
                **segment,
                "topic_id": topic["topic_id"],
                "topic_name": topic["topic_name"],
                "mapping_method": "approximate_time_overlap",
            })

        if not matches:
            mapped.append({
                **segment,
                "topic_id": "general",
                "topic_name": "general",
                "mapping_method": "no_topic_ranges" if not ranges else "no_matching_range",
            })

    return mapped


# ==================================================
# 5. VIDEO FRAMES (pipelines/extract_video_frames.py)
# ==================================================

def _evenly_spaced(items, limit):
    """Pick `limit` items spread across the list (analyze_video_frames.py)."""
    if len(items) <= limit:
        return list(items)

    if limit <= 1:
        return [items[0]]

    indices = [round(i * (len(items) - 1) / (limit - 1)) for i in range(limit)]
    return [items[index] for index in indices]


def extract_frames(video_path, every_seconds=10, max_frames=60, output_dir=None, video_id="VIDEO"):
    """
    Save one JPEG every `every_seconds` (at most `max_frames`, spread over
    the whole video) as <video_id>_frame_<seconds>.jpg. Returns
    [{video_id, timestamp_seconds, frame_file, path, source_video}].
    """
    import cv2

    video_path = Path(video_path)
    output_dir = Path(output_dir or video_path.parent / "frames")
    output_dir.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(video_path))

    if not capture.isOpened():
        raise RuntimeError(f"Unable to open the video file: {video_path.name}")

    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        total_frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)

        if fps <= 0 or total_frames <= 0:
            raise RuntimeError("Invalid video FPS or frame count.")

        duration = total_frames / fps
        seconds_list = _evenly_spaced(
            list(range(0, int(duration) + 1, max(1, int(every_seconds)))), max_frames
        )
        records = []

        for second in seconds_list:
            capture.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
            success, frame = capture.read()

            if not success:
                continue

            frame_name = f"{video_id}_frame_{second:05d}.jpg"
            frame_path = output_dir / frame_name

            if not cv2.imwrite(str(frame_path), frame):
                continue

            records.append({
                "video_id": video_id,
                "timestamp_seconds": second,
                "frame_file": frame_name,
                "path": str(frame_path),
                "source_video": video_path.name,
            })
    finally:
        capture.release()

    return records


def _frame_timestamp(image_path):
    """Timestamp candidate from a *_frame_<seconds>.jpg name (align_visual_evidence.py)."""
    match = re.search(r"_frame_(\d+)\.(jpg|jpeg|png)$", Path(image_path).name, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _image_difference(capture, image_path, seconds):
    """Mean pixel difference to the video frame at `seconds` (align_visual_evidence.py)."""
    import cv2

    saved = cv2.imread(str(image_path))

    if saved is None:
        return None

    capture.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
    success, video_image = capture.read()

    if not success:
        return None

    size = (320, 180)
    return float(cv2.absdiff(cv2.resize(saved, size), cv2.resize(video_image, size)).mean())


# ==================================================
# 6. DOCUMENTS (pipelines/ingest_documents.py + split_text)
# ==================================================

def split_text(text, chunk_size=900, overlap=150):
    """Copied from ai/index_documents.py."""
    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks


def _pdf_pages(path):
    import pymupdf

    with pymupdf.open(path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()

            if text:
                yield "pdf", f"page_{page_number}", text


def _pptx_slides(path):
    from pptx import Presentation

    presentation = Presentation(str(path))

    for slide_number, slide in enumerate(presentation.slides, start=1):
        parts = []

        for shape in slide.shapes:
            if shape.has_text_frame and shape.text.strip():
                parts.append(shape.text.strip())

            if getattr(shape, "has_table", False) and shape.has_table:
                for row in shape.table.rows:
                    parts.append(" | ".join(cell.text.strip() for cell in row.cells))

        text = "\n".join(parts).strip()

        if text:
            yield "powerpoint", f"slide_{slide_number}", text


def extract_documents(paths, course_id="UPLOAD"):
    """
    Text chunks from PDFs (per page) and PowerPoints (per slide), split
    like ai/index_documents.py. Returns (chunks, warnings).
    """
    chunks, warnings = [], []

    for path in paths:
        path = Path(path)
        suffix = path.suffix.lower()

        try:
            if suffix == ".pdf":
                pages = list(_pdf_pages(path))
            elif suffix == ".pptx":
                pages = list(_pptx_slides(path))
            else:
                warnings.append(f"{path.name}: unsupported document type (use PDF or PPTX).")
                continue
        except Exception as error:
            warnings.append(f"{path.name}: could not be read ({error}).")
            continue

        if not pages:
            warnings.append(f"{path.name}: no selectable text found (scanned documents need OCR).")
            continue

        source_file = _relative(path)

        for source_type, location, text in pages:
            for chunk_number, chunk in enumerate(split_text(text), start=1):
                chunks.append({
                    "course_id": course_id,
                    "source_type": source_type,
                    "source_file": source_file,
                    "location": location,
                    "chunk_number": chunk_number,
                    "text": chunk,
                    "data_provenance": "user_supplied_document",
                })

    return chunks, warnings


# ==================================================
# 7. IMAGE DESCRIPTIONS (pipelines/analyze_video_frames.py)
# ==================================================

# Gemini sometimes answers 503 "high demand, try again": retry briefly
GEMINI_RETRY_WAITS = (4, 10)


def _gemini_busy(error):
    """True for Gemini's temporary 'unavailable / high demand' failures."""
    for item in (error, getattr(error, "__cause__", None)):
        if item is None:
            continue
        if getattr(item, "code", None) == 503:
            return True
        text = str(item).lower()
        if "503" in text or "unavailable" in text or "could not analyse" in text or "could not generate" in text:
            return True
    return False


def _with_gemini_retry(call, progress_cb=None, stage="describe", label=""):
    """Run call(); on a temporary Gemini failure wait and try again."""
    for attempt, wait in enumerate((*GEMINI_RETRY_WAITS, None), start=1):
        try:
            return call()
        except Exception as error:
            if wait is None or not _gemini_busy(error):
                raise
            _report(progress_cb, stage, 0.0, f"Gemini is busy; retrying {label} in {wait}s")
            time.sleep(wait)


def describe_images(image_paths, max_images=12, progress_cb=None):
    """
    Gemini descriptions of up to `max_images` images (spread evenly),
    using analyse_frame() from pipelines/analyze_video_frames.py (same
    prompt and model fallback). Returns (results, warnings) where results
    are {path, description, model}.
    """
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")

    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError(
            "GEMINI_API_KEY is missing from .env, so images cannot be described. "
            "Add the key or upload without images."
        )

    from google import genai
    from pipelines.analyze_video_frames import analyse_frame

    selected = _evenly_spaced([Path(path) for path in image_paths], max_images)
    results, warnings = [], []
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    try:
        for number, path in enumerate(selected, start=1):
            _report(progress_cb, "describe", (number - 1) / max(1, len(selected)),
                    f"Describing image {number} of {len(selected)}")

            try:
                description, model = _with_gemini_retry(
                    lambda: analyse_frame(client, path), progress_cb, "describe", path.name
                )
                results.append({"path": str(path), "description": description, "model": model})
            except Exception as error:
                reason = (
                    "Gemini was busy and still unavailable after retrying"
                    if _gemini_busy(error) else str(error)
                )
                warnings.append(f"{path.name}: image description failed ({reason}).")
    finally:
        client.close()

    _report(progress_cb, "describe", 1.0, f"{len(results)} images described")
    return results, warnings


# ==================================================
# 8. EVIDENCE RECORDS (same schemas as the original index)
# ==================================================

def _clean_metadata(metadata):
    # Chroma rejects None values; the original scripts omit such keys
    return {key: value for key, value in metadata.items() if value is not None}


def quiz_records(summary_df):
    """ai/build_evidence_index.py: one quiz_analytics record per topic."""
    records = []

    for _, row in summary_df.iterrows():
        text = (
            f"Topic: {row['topic_name']}. "
            f"Quiz attempts: {row['total_attempts']}. "
            f"Incorrect answers: {row['incorrect_answers']}. "
            f"Incorrect rate: {row['incorrect_rate_pct']} percent. "
            f"Student comment count: {row['comment_count']}."
        )

        records.append({
            "id": f"analytics_{row['course_id']}_{row['video_id']}_{row['topic_id']}",
            "text": text,
            "metadata": {
                "modality": "quiz_analytics",
                "source_id": str(row["topic_id"]),
                "course_id": str(row["course_id"]),
                "video_id": str(row["video_id"]),
                "topic_id": str(row["topic_id"]),
                "source_location": "learning_difficulty_summary.csv",
            },
        })

    return records


def comment_records(comments_df, source_name="student_comments.csv"):
    """ai/build_evidence_index.py: one learner_comment record per comment."""
    records = []

    for _, row in comments_df.iterrows():
        text = row["comment_text"]

        if not isinstance(text, str) or not text.strip():
            continue

        records.append({
            "id": f"comment_{row['comment_id']}",
            "text": text.strip(),
            "metadata": {
                "modality": "learner_comment",
                "source_id": str(row["comment_id"]),
                "course_id": str(row["course_id"]),
                "video_id": str(row["video_id"]),
                "topic_id": str(row["topic_id"]),
                "source_location": source_name,
            },
        })

    return records


def transcript_records(mapped_segments, course_id, video_id, source_video):
    """ai/index_transcripts.py: one video_transcript record per (segment, topic)."""
    records = []

    for segment in mapped_segments:
        text = str(segment["text"]).strip()

        if not text:
            continue

        records.append({
            "id": f"transcript_{segment['segment_id']}_{segment['topic_id']}",
            "text": text,
            "metadata": {
                "modality": "video_transcript",
                "source_id": str(segment["segment_id"]),
                "course_id": str(course_id),
                "video_id": str(video_id),
                "topic_id": str(segment["topic_id"]),
                "topic_name": str(segment["topic_name"]),
                "start_seconds": float(segment["start_seconds"]),
                "end_seconds": float(segment["end_seconds"]),
                "source_location": str(source_video),
                "mapping_method": str(segment["mapping_method"]),
            },
        })

    return records


def document_records(chunks):
    """ai/index_documents.py: one course_document record per chunk."""
    records = []

    for chunk in chunks:
        unique_value = f"{chunk['source_file']}:{chunk['location']}:{chunk['chunk_number']}"
        record_id = hashlib.sha256(unique_value.encode("utf-8")).hexdigest()[:24]

        records.append({
            "id": f"course_doc_{record_id}",
            "text": chunk["text"],
            "metadata": {
                "modality": "course_document",
                "course_id": chunk["course_id"],
                "topic_id": "unassigned",
                "source_id": record_id,
                "source_type": chunk["source_type"],
                "source_file": chunk["source_file"],
                "source_location": f"{chunk['source_file']}#{chunk['location']}",
                "location": chunk["location"],
                "chunk_number": chunk["chunk_number"],
                "provenance": chunk["data_provenance"],
            },
        })

    return records


def visual_records(described, course_id, video_id, topics_df=None, timing=None):
    """
    ai/index_visual_analysis.py + ai/align_visual_evidence.py: one
    video_visual_analysis record per described image. `timing` maps an
    image path to (start_seconds, timestamp_status, image_difference).
    Topics are assigned only when exactly one topic range contains the
    timestamp ("unique_range_match"), as in align_visual_evidence.py.
    """
    ranges = _topic_ranges(topics_df, video_id)
    timing = timing or {}
    records = []

    for item in described:
        description = str(item.get("description") or "").strip()

        if not description:
            continue

        source_file = _relative(item["path"])
        record_id = f"visual_analysis_{hashlib.sha256(source_file.encode('utf-8')).hexdigest()[:24]}"
        start, timestamp_status, difference = timing.get(item["path"], (None, None, None))

        metadata = {
            "modality": "video_visual_analysis",
            "course_id": str(course_id),
            "video_id": str(video_id),
            "topic_id": "unassigned",
            "source_id": record_id,
            "source_file": source_file,
            "source_location": source_file,
            "source_type": "video_frame",
            "analysis_model": str(item.get("model", "unknown")),
            "provenance": "gemini_visual_analysis",
        }

        if start is not None:
            matches = [topic["topic_id"] for topic in ranges if topic["start"] <= start < topic["end"]]

            if len(matches) == 1:
                topic_id, topic_status = matches[0], "unique_range_match"
            elif len(matches) > 1:
                topic_id, topic_status = "unassigned", "overlapping_ranges"
            else:
                topic_id, topic_status = "unassigned", "no_matching_range"

            metadata.update({
                "start_seconds": float(start),
                "topic_id": topic_id,
                "topic_candidates": ",".join(matches),
                "timestamp_status": timestamp_status,
                "topic_mapping_status": topic_status,
                "image_difference": difference,
            })

        records.append({"id": record_id, "text": description, "metadata": metadata})

    return records


# ==================================================
# 9. INDEXING
# ==================================================

@lru_cache(maxsize=1)
def _embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def _chroma_client():
    import chromadb

    return chromadb.PersistentClient(path=str(DATABASE_PATH))


def index_upload(upload_id, records, progress_cb=None, batch_size=256):
    """
    Embed the records and store them in a NEW collection "upload_<id>"
    (cosine space, all-MiniLM-L6-v2) using the original metadata schema.
    Never touches "coursera_evidence". Returns the collection name.
    """
    name = collection_name_for(upload_id)

    if name == ORIGINAL_COLLECTION or not name.startswith(COLLECTION_PREFIX):
        raise RuntimeError("Refusing to write outside an upload collection.")

    # Unique ids (a transcript segment can map to the same topic once only)
    unique = {}

    for record in records:
        unique.setdefault(record["id"], record)

    records = list(unique.values())

    if not records:
        raise ValueError("There is no evidence to index.")

    collection = _chroma_client().get_or_create_collection(
        name=name, metadata={"hnsw:space": "cosine"}
    )
    model = _embedding_model()

    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]
        embeddings = model.encode(
            [record["text"] for record in batch], normalize_embeddings=True
        ).tolist()

        collection.upsert(
            ids=[record["id"] for record in batch],
            documents=[record["text"] for record in batch],
            embeddings=embeddings,
            metadatas=[_clean_metadata(record["metadata"]) for record in batch],
        )

        _report(progress_cb, "index", (start + len(batch)) / len(records),
                f"Indexed {start + len(batch)} of {len(records)} records")

    return name


def delete_upload(upload_id):
    """Drop the upload's collection and delete its folder."""
    name = collection_name_for(upload_id)
    client = _chroma_client()

    if name in [collection.name for collection in client.list_collections()]:
        client.delete_collection(name)

    try:
        from ai.rag_pipeline import get_collection

        get_collection.cache_clear()  # forget the deleted collection handle
    except ImportError:
        pass

    folder = upload_dir(upload_id)

    if folder.exists():
        shutil.rmtree(folder)


# ==================================================
# 10. END-TO-END PROCESSING
# ==================================================

def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [item for item in value if item]
    return [value]


def _copy_into(folder, path):
    folder.mkdir(parents=True, exist_ok=True)
    source = Path(path)
    target = folder / source.name

    if source.resolve() != target.resolve():
        shutil.copy2(source, target)

    return target


def process_upload(upload_id, files, options=None, progress_cb=None):
    """
    Run every processing step that has input and index the result.

    files: {"quiz_responses": csv, "quiz_questions": csv,
            "student_comments": csv, "video_topics": csv,
            "video": mp4, "transcript": json/srt/vtt,
            "documents": [pdf/pptx, ...], "images": [jpg/png, ...]}
    options: course_id, video_id, frame_every_seconds (10),
             max_frames (60), max_images (12), describe_images (True),
             transcribe (True)
    progress_cb(stage, fraction, message) is optional.

    Returns the manifest (also saved as data/uploads/<id>/manifest.json).
    Raises UploadValidationError for unusable input.
    """
    options = dict(options or {})
    folder = upload_dir(upload_id)
    raw_dir = folder / "raw"
    processed_dir = folder / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "upload_id": upload_id,
        "collection": collection_name_for(upload_id),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": {},
        "counts": {},
        "topics": [],
        "warnings": [],
        "timings": {},
        "status": "processing",
    }
    warnings = manifest["warnings"]
    records = []
    started = time.perf_counter()

    def timed(step, began):
        manifest["timings"][step] = round(time.perf_counter() - began, 2)

    # ---- CSVs: copy, read and validate ---------------------------------
    began = time.perf_counter()
    frames, errors = {}, []

    for kind in REQUIRED_COLUMNS:
        path = files.get(kind)

        if not path:
            continue

        copied = _copy_into(raw_dir, path)
        manifest["files"][kind] = _relative(copied)

        try:
            frame = read_csv(copied)
        except Exception as error:
            problem = f"{Path(path).name}: could not be read as CSV ({error})."
            (errors if kind in ("quiz_responses", "student_comments") else warnings).append(problem)
            continue

        problems = validate_csv(frame, kind)

        if problems and kind in ("quiz_responses", "student_comments"):
            errors.extend(problems)
        elif problems:
            warnings.extend(f"{kind.replace('_', ' ')} ignored: {problem}" for problem in problems)
        else:
            frames[kind] = frame

    if errors:
        raise UploadValidationError(errors)

    topics_df = frames.get("video_topics")
    course_id = options.get("course_id")
    video_id = options.get("video_id")

    for source in ("video_topics", "quiz_responses", "student_comments"):
        if source in frames:
            course_id = course_id or str(frames[source]["course_id"].iloc[0]).strip()
            video_id = video_id or str(frames[source]["video_id"].iloc[0]).strip()

    course_id = course_id or "UPLOAD"
    video_id = video_id or "VIDEO"
    manifest["course_id"], manifest["video_id"] = course_id, video_id

    if topics_df is not None and topics_df["video_id"].astype(str).nunique() > 1:
        warnings.append(
            f"video topics cover several videos; timestamps are mapped for video_id {video_id}."
        )

    timed("validate", began)
    _report(progress_cb, "validate", 1.0, "Files checked")

    # ---- Quiz analytics + comments ---------------------------------------
    summary = None

    if "quiz_responses" in frames:
        began = time.perf_counter()
        _report(progress_cb, "quiz_analytics", 0.0, "Summarising quiz results")
        summary = build_learning_summary(
            frames["quiz_responses"], frames.get("student_comments"), topics_df
        )
        summary.to_csv(processed_dir / "learning_difficulty_summary.csv", index=False)
        records.extend(quiz_records(summary))

        if topics_df is not None:
            known = set(topics_df["topic_id"].astype(str).str.strip())
            unnamed = sorted(set(summary["topic_id"]) - known)

            if unnamed:
                warnings.append(f"Topics without a name in video topics: {', '.join(unnamed)}.")

        timed("quiz_analytics", began)
        _report(progress_cb, "quiz_analytics", 1.0, f"{len(summary)} topics")

    if "student_comments" in frames:
        began = time.perf_counter()
        _report(progress_cb, "learner_comment", 0.0, "Reading learner comments")
        records.extend(comment_records(
            frames["student_comments"], Path(files["student_comments"]).name
        ))
        timed("learner_comment", began)
        _report(progress_cb, "learner_comment", 1.0, f"{len(frames['student_comments'])} comments")

    # ---- Video: transcript and frames ------------------------------------
    video_path = files.get("video")
    transcript_path = files.get("transcript")
    source_video = Path(video_path).name if video_path else None

    if video_path:
        video_path = _copy_into(raw_dir, video_path)
        manifest["files"]["video"] = _relative(video_path)

    segments = None

    if transcript_path:
        began = time.perf_counter()
        _report(progress_cb, "transcript", 0.0, "Reading the uploaded transcript")
        copied = _copy_into(raw_dir, transcript_path)
        manifest["files"]["transcript"] = _relative(copied)

        try:
            segments = load_transcript(copied, video_id)

            if copied.suffix.lower() == ".json" and not source_video:
                data = json.loads(copied.read_text(encoding="utf-8-sig"))
                first = data[0] if isinstance(data, list) and data else {}
                source_video = first.get("source_video") or copied.name
        except Exception as error:
            warnings.append(f"Transcript ignored: {error}")

        timed("transcript_load", began)
        _report(progress_cb, "transcript", 1.0, f"{len(segments or [])} segments from the transcript")

    elif video_path and options.get("transcribe", True):
        began = time.perf_counter()

        try:
            segments = transcribe_video(video_path, progress_cb, video_id)
        except Exception as error:
            warnings.append(f"Transcription failed: {error}")

        timed("transcribe", began)

    if segments:
        mapped = map_segments_to_topics(segments, topics_df, video_id)
        (processed_dir / "transcript_segments.json").write_text(
            json.dumps(mapped, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        records.extend(transcript_records(mapped, course_id, video_id, source_video or "transcript"))

        if topics_df is None:
            warnings.append("No video topics uploaded: transcript segments use topic 'general'.")

    # ---- Images: extracted frames + uploaded images ----------------------
    image_paths, timing = [], {}

    if video_path and options.get("extract_frames", True):
        began = time.perf_counter()
        _report(progress_cb, "extract_frames", 0.0, "Extracting frames from the video")

        try:
            extracted = extract_frames(
                video_path,
                every_seconds=options.get("frame_every_seconds", 10),
                max_frames=options.get("max_frames", 60),
                output_dir=folder / "frames",
                video_id=video_id,
            )
            manifest["counts"]["frames_extracted"] = len(extracted)

            for frame in extracted:
                image_paths.append(frame["path"])
                # Extracted directly from the video at this time: the
                # image matches the video at the timestamp by construction.
                timing[frame["path"]] = (frame["timestamp_seconds"], "candidate_image_match", 0.0)
        except Exception as error:
            warnings.append(f"Frame extraction failed: {error}")

        timed("extract_frames", began)
        _report(progress_cb, "extract_frames", 1.0, f"{manifest['counts'].get('frames_extracted', 0)} frames")

    uploaded_images = [_copy_into(folder / "images", path) for path in _as_list(files.get("images"))]

    if uploaded_images:
        manifest["files"]["images"] = [_relative(path) for path in uploaded_images]
        capture = None

        if video_path:
            import cv2

            capture = cv2.VideoCapture(str(video_path))

        try:
            for path in uploaded_images:
                image_paths.append(str(path))
                seconds = _frame_timestamp(path)

                if seconds is None:
                    continue

                if capture is not None and capture.isOpened():
                    difference = _image_difference(capture, path, seconds)

                    if difference is not None and difference <= MAX_IMAGE_DIFFERENCE:
                        timing[str(path)] = (seconds, "candidate_image_match", difference)
                    else:
                        timing[str(path)] = (seconds, "image_match_failed", difference)
                else:
                    timing[str(path)] = (seconds, "filename_timestamp", None)
        finally:
            if capture is not None:
                capture.release()

        unverified = [p for p, (_, status, _d) in timing.items() if status == "filename_timestamp"]

        if unverified:
            warnings.append(
                f"{len(unverified)} uploaded image(s) have a timestamp in their file name but no "
                "video to verify it against; they are searchable but not used as topic visual "
                "evidence in reports (that needs status candidate_image_match)."
            )

    if image_paths and options.get("describe_images", True):
        began = time.perf_counter()

        try:
            described, image_warnings = describe_images(
                image_paths, options.get("max_images", 12), progress_cb
            )
            warnings.extend(image_warnings)
            (processed_dir / "image_descriptions.json").write_text(
                json.dumps(described, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            records.extend(visual_records(described, course_id, video_id, topics_df, timing))
        except Exception as error:
            warnings.append(f"Images were not described: {error}")

        timed("describe_images", began)

    # ---- Documents -------------------------------------------------------
    documents = _as_list(files.get("documents"))

    if documents:
        began = time.perf_counter()
        _report(progress_cb, "documents", 0.0, "Reading course documents")
        copied = [_copy_into(folder / "documents", path) for path in documents]
        manifest["files"]["documents"] = [_relative(path) for path in copied]
        chunks, document_warnings = extract_documents(copied, course_id)
        warnings.extend(document_warnings)
        (processed_dir / "document_chunks.json").write_text(
            json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        records.extend(document_records(chunks))
        timed("documents", began)
        _report(progress_cb, "documents", 1.0, f"{len(chunks)} text chunks")

    # ---- Index -------------------------------------------------------------
    if not records:
        raise UploadValidationError(["Nothing could be extracted from the uploaded files."])

    began = time.perf_counter()
    _report(progress_cb, "index", 0.0, f"Embedding {len(records)} evidence records")
    index_upload(upload_id, records, progress_cb)
    timed("index", began)

    for record in {record["id"]: record for record in records}.values():
        modality = record["metadata"]["modality"]
        manifest["counts"][modality] = manifest["counts"].get(modality, 0) + 1

    topic_ids = set()

    if summary is not None:
        topic_ids |= set(summary["topic_id"])
    if topics_df is not None:
        topic_ids |= set(topics_df["topic_id"].astype(str).str.strip())

    manifest["topics"] = sorted(topic_ids)
    manifest["has_summary"] = summary is not None
    manifest["timings"]["total"] = round(time.perf_counter() - started, 2)
    manifest["status"] = "complete"

    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _report(progress_cb, "done", 1.0, "Upload processed")
    return manifest


def load_manifest(upload_id):
    path = upload_dir(upload_id) / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def load_summary(upload_id):
    path = upload_dir(upload_id) / "processed" / "learning_difficulty_summary.csv"
    return pd.read_csv(path) if path.exists() else None


# ==================================================
# 11. AI REPORTS FROM AN UPLOAD
# ==================================================

def default_question(topic_name):
    """Same default question wording as the dashboard (frontend/app.py)."""
    return (
        f"Why are students struggling with "
        f"{topic_name}? "
        f"Use quiz results, student feedback and "
        f"video transcript evidence."
    )


def generate_upload_report(upload_id, summary_df, scope, topic_id=None, top_n=3, question=None):
    """
    scope="topic":    ask_course for one topic, using the upload's collection.
    scope="overview": ask_course for the top_n topics by incorrect_rate_pct;
                      returns {"topics": [...], "summary_df": ...}. A topic
                      that fails is reported with its error and the rest
                      continue.
    """
    from ai.rag_pipeline import ask_course

    collection_name = collection_name_for(upload_id)

    if summary_df is None or summary_df.empty:
        raise ValueError("Reports need quiz results (quiz responses) in the upload.")

    names = dict(zip(summary_df["topic_id"].astype(str), summary_df["topic_name"].astype(str)))

    if scope == "topic":
        if not topic_id or str(topic_id) not in names:
            raise ValueError(f"Unknown topic for this upload: {topic_id!r}")

        result = _with_gemini_retry(lambda: ask_course(
            question or default_question(names[str(topic_id)]),
            str(topic_id),
            collection_name=collection_name,
        ), stage="report", label=names[str(topic_id)])
        return {**result, "topic_id": str(topic_id), "topic_name": names[str(topic_id)]}

    if scope == "overview":
        ranked = summary_df.sort_values("incorrect_rate_pct", ascending=False).head(int(top_n))
        topics = []

        for _, row in ranked.iterrows():
            entry = {
                "topic_id": str(row["topic_id"]),
                "topic_name": str(row["topic_name"]),
                "incorrect_rate_pct": float(row["incorrect_rate_pct"]),
            }

            try:
                entry["result"] = _with_gemini_retry(lambda: ask_course(
                    default_question(row["topic_name"]),
                    str(row["topic_id"]),
                    collection_name=collection_name,
                ), stage="report", label=str(row["topic_name"]))
            except Exception as error:
                entry["error"] = str(error)

            topics.append(entry)

        return {"topics": topics, "summary_df": ranked.reset_index(drop=True)}

    raise ValueError("scope must be 'topic' or 'overview'.")
