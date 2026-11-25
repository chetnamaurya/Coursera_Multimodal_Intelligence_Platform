
"""
Tests for backend/upload_pipeline.py using the demo course files.

Run from the project root:

    python tests/test_upload_pipeline.py

The end-to-end test needs GEMINI_API_KEY in .env (it describes the three
sample frame images with Gemini). It skips Whisper by supplying the demo
transcript JSON. Every upload it creates is deleted afterwards, and the
original "coursera_evidence" collection is checked to be unchanged.
"""

import sys
import tempfile
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend import upload_pipeline as up

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
FRAMES_DIR = PROCESSED_DIR / "video_frames"

DEMO_FRAMES = [
    "PY101_V01_frame_00120.jpg",
    "PY101_V01_frame_00360.jpg",
    "PY101_V01_frame_00380.jpg",
]

MODALITIES = [
    "quiz_analytics",
    "learner_comment",
    "video_transcript",
    "course_document",
    "video_visual_analysis",
]


def collection_names():
    return [collection.name for collection in up._chroma_client().list_collections()]


def original_count():
    import chromadb

    client = chromadb.PersistentClient(path=str(up.DATABASE_PATH))
    return client.get_collection(up.ORIGINAL_COLLECTION).count()


# ==================================================
# 1. FAST LOCAL CHECKS (no network)
# ==================================================

def test_validate_csv_reports_problems():
    good = up.read_csv(RAW_DIR / "quiz_responses.csv")
    assert up.validate_csv(good, "quiz_responses") == []

    errors = up.validate_csv(good.drop(columns=["is_correct", "topic_id"]), "quiz_responses")
    assert errors and "is_correct" in errors[0] and "topic_id" in errors[0], errors

    bad_values = good.head(5).assign(is_correct=["yes", 1, 0, 1, 0])
    assert any("is_correct" in error for error in up.validate_csv(bad_values, "quiz_responses"))

    topics = up.read_csv(RAW_DIR / "video_topics.csv")
    assert up.validate_csv(topics, "video_topics") == []

    reversed_times = topics.head(1).assign(approx_start_time="00:05:00", approx_end_time="00:01:00")
    assert any("after" in error for error in up.validate_csv(reversed_times, "video_topics"))

    assert up.validate_csv(pd.DataFrame(), "student_comments") == ["The student comments file has no rows."]
    print("OK validate_csv")


def test_learning_summary_without_topics():
    quiz = up.read_csv(RAW_DIR / "quiz_responses.csv")
    summary = up.build_learning_summary(quiz, None, None)
    assert list(summary.columns) == up.SUMMARY_COLUMNS
    assert (summary["comment_count"] == 0).all()
    assert summary.loc[summary["topic_id"] == "while_loop", "topic_name"].iloc[0] == "while loop"
    print("OK build_learning_summary without comments/topics")


def test_subtitle_and_mapping():
    srt = (
        "1\n00:06:00,000 --> 00:06:05,500\nwhile i is less than five\n\n"
        "2\n00:00:01,000 --> 00:00:03,000\n<i>hello</i> world\n"
    )

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "captions.srt"
        path.write_text(srt, encoding="utf-8")
        segments = up.load_transcript(path, "PY101_V01")

    assert [s["start_seconds"] for s in segments] == [360.0, 1.0]
    assert segments[1]["text"] == "hello world"

    topics = up.read_csv(RAW_DIR / "video_topics.csv")
    mapped = up.map_segments_to_topics(segments, topics, "PY101_V01")
    topic_ids = {m["segment_id"]: m["topic_id"] for m in mapped}
    assert topic_ids["PY101_V01_T0001"] == "while_loop", mapped
    assert up.map_segments_to_topics(segments, None)[0]["topic_id"] == "general"
    print("OK load_transcript (.srt) + map_segments_to_topics")


def test_extract_frames_and_image_matching():
    import cv2

    videos = sorted(RAW_DIR.glob("*.mp4"))

    if not videos:
        print("SKIP extract_frames (no demo video)")
        return

    with tempfile.TemporaryDirectory() as folder:
        frames = up.extract_frames(videos[0], every_seconds=60, max_frames=3,
                                   output_dir=folder, video_id="PY101_V01")
        assert len(frames) == 3 and all(Path(f["path"]).exists() for f in frames), frames
        assert frames[0]["frame_file"] == "PY101_V01_frame_00000.jpg"

    capture = cv2.VideoCapture(str(videos[0]))

    try:
        same = up._image_difference(capture, FRAMES_DIR / "PY101_V01_frame_00360.jpg", 360)
        other = up._image_difference(capture, FRAMES_DIR / "PY101_V01_frame_00360.jpg", 30)
    finally:
        capture.release()

    assert same is not None and same <= up.MAX_IMAGE_DIFFERENCE, same
    assert other is not None and other > same, (same, other)
    print(f"OK extract_frames + image matching (difference {same:.2f} at the right time, {other:.2f} elsewhere)")


def test_upload_id_is_safe():
    for bad in ("../x", "coursera_evidence", "20260101-000000-zzzzzzzz"):
        try:
            up.upload_dir(bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted unsafe upload id {bad!r}")
    print("OK upload ids are validated")


# ==================================================
# 2. END-TO-END PROCESSING OF THE DEMO FILES
# ==================================================

def test_process_upload_demo_files():
    upload_id = up.new_upload_id()
    before = original_count()
    stages = []

    files = {
        "quiz_responses": RAW_DIR / "quiz_responses.csv",
        "quiz_questions": RAW_DIR / "quiz_questions.csv",
        "student_comments": RAW_DIR / "student_comments.csv",
        "video_topics": RAW_DIR / "video_topics.csv",
        "transcript": RAW_DIR / "transcripts" / "video_transcript.json",
        "documents": sorted((RAW_DIR / "pdfs").glob("*.pdf")),
        "images": [FRAMES_DIR / name for name in DEMO_FRAMES],
    }

    try:
        manifest = up.process_upload(
            upload_id,
            files,
            options={"max_images": 3},
            progress_cb=lambda stage, fraction, message: stages.append(stage),
        )

        name = up.collection_name_for(upload_id)
        assert manifest["status"] == "complete"
        assert name in collection_names(), "upload collection was not created"
        assert (up.upload_dir(upload_id) / "manifest.json").exists()

        collection = up._chroma_client().get_collection(name)
        assert collection.metadata.get("hnsw:space") == "cosine"

        for modality in MODALITIES:
            stored = len(collection.get(where={"modality": modality}, include=[])["ids"])
            assert stored > 0, f"no {modality} records indexed"
            assert manifest["counts"].get(modality) == stored, (modality, manifest["counts"])

        # Same metadata schema as the original index
        sample = collection.get(where={"modality": "video_transcript"}, limit=1, include=["metadatas"])
        assert {"source_id", "course_id", "video_id", "topic_id", "start_seconds", "end_seconds",
                "source_location", "mapping_method"} <= set(sample["metadatas"][0])

        visual = collection.get(where={"modality": "video_visual_analysis"}, include=["metadatas"])
        statuses = {m.get("timestamp_status") for m in visual["metadatas"]}
        assert statuses == {"filename_timestamp"}, statuses  # no video uploaded to verify against

        # The learning summary matches the existing processed file
        summary = up.load_summary(upload_id)
        expected = pd.read_csv(PROCESSED_DIR / "learning_difficulty_summary.csv")
        assert list(summary.columns) == list(expected.columns)
        pd.testing.assert_frame_equal(
            summary.sort_values("topic_id").reset_index(drop=True),
            expected.sort_values("topic_id").reset_index(drop=True),
            check_dtype=False,
        )

        # Retrieval from the upload collection works through ask_course's path
        from ai.rag_pipeline import retrieve_evidence

        evidence = retrieve_evidence(
            "Why are students struggling with while loops?", "while_loop",
            top_k=3, collection_name=name,
        )
        found = {item["modality"] for item in evidence}
        assert {"quiz_analytics", "learner_comment", "video_transcript", "course_document"} <= found, found

        assert original_count() == before, "the original collection changed"
        assert "index" in stages and "done" in stages

        print("OK process_upload:", {m: manifest["counts"][m] for m in MODALITIES})
        print("   topics:", len(manifest["topics"]), "| warnings:", len(manifest["warnings"]),
              "| total seconds:", manifest["timings"]["total"])

    finally:
        up.delete_upload(upload_id)

    assert up.collection_name_for(upload_id) not in collection_names(), "collection not deleted"
    assert not up.upload_dir(upload_id).exists(), "upload folder not deleted"
    assert original_count() == before
    print("OK delete_upload removed the collection and folder; coursera_evidence unchanged")


def main():
    test_validate_csv_reports_problems()
    test_learning_summary_without_topics()
    test_subtitle_and_mapping()
    test_extract_frames_and_image_matching()
    test_upload_id_is_safe()
    test_process_upload_demo_files()
    print("\nALL UPLOAD PIPELINE TESTS PASSED")


if __name__ == "__main__":
    main()
