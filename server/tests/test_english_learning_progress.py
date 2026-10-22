from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
import pytest
from fastapi import HTTPException

from app.models import Base, EnglishScene, EnglishStudyAttempt, EnglishStudyRecord, EnglishUnit, EnglishUnitProgress
from app.services.english_service import learner_progress, submit_study_result, unit_dict
from app.api.admin.english import _media_extension, _validate_published_media, parse_subtitles
from app.services.english_asr_service import EnglishASRError, normalize_segments
from app.schemas.english import EnglishUnitInput


def _session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return Session(engine)


def _published_unit(db: Session) -> EnglishUnit:
    scene = EnglishScene(id="scene-1", title="日常社交", is_published=True)
    db.add(scene)
    unit = EnglishUnit(id="unit-1", scene_id=scene.id, title="介绍自己", is_published=True,
                       content_json='{"transcript":[{"speaker":"A","en":"Hello","zh":"你好","internalNote":"private"}],"rightsNote":"private","media":{"type":"audio","audioUrl":"https://example.test/audio.mp3","rightsStatus":"licensed_hosting","editorNote":"private"}}')
    db.add(unit)
    db.commit()
    return unit


def test_completion_is_idempotent_and_progress_restores():
    with _session() as db:
        _published_unit(db)
        first = submit_study_result(db, "learner-1", "unit-1", "attempt-0001", "independent")
        retry = submit_study_result(db, "learner-1", "unit-1", "attempt-0001", "independent")

        assert first["duplicate"] is False
        assert retry["duplicate"] is True
        assert db.query(EnglishStudyRecord).filter_by(user_id="learner-1").count() == 1
        assert db.query(EnglishStudyAttempt).filter_by(user_id="learner-1").count() == 1
        assert db.query(EnglishUnitProgress).filter_by(user_id="learner-1").count() == 1
        assert learner_progress(db, "learner-1")["completedUnitIds"] == ["unit-1"]


def test_review_result_changes_spacing_and_public_content_filters_editor_notes():
    with _session() as db:
        unit = _published_unit(db)
        submit_study_result(db, "learner-2", unit.id, "attempt-0002", "independent")
        state = db.query(EnglishUnitProgress).filter_by(user_id="learner-2", unit_id=unit.id).one()
        initial_due = state.next_review_at

        advanced = submit_study_result(db, "learner-2", unit.id, "attempt-0003", "independent")
        assert advanced["reviewStage"] == 1
        assert state.next_review_at > initial_due

        hinted = submit_study_result(db, "learner-2", unit.id, "attempt-0004", "hinted")
        assert hinted["reviewStage"] == 1
        assert state.last_result == "hinted"

        public = unit_dict(unit, public=True)["content"]
        assert "rightsNote" not in public
        assert "editorNote" not in public["media"]
        assert "internalNote" not in public["transcript"][0]


def test_published_course_requires_practice_content_and_complete_timestamps():
    base = {"dialogue": [{"en": "Hello"}, {"en": "How are you?"}],
            "phrases": [{"en": "Hello"}, {"en": "How are you?"}], "prompt": "换成自己的信息。"}
    _validate_published_media(EnglishUnitInput(scene_id="scene-1", title="完整课程", is_published=True, content=base))

    invalid = {**base, "dialogue": [{"en": "Hello", "startSeconds": 3}, {"en": "Goodbye"}]}
    with pytest.raises(HTTPException, match="起始秒和结束秒"):
        _validate_published_media(EnglishUnitInput(scene_id="scene-1", title="时间轴缺失", is_published=True, content=invalid))


def test_subtitle_import_parses_srt_and_vtt_as_editable_cues():
    srt = b"1\r\n00:00:01,200 --> 00:00:02,500\r\nCould I have a latte?\r\n\r\n2\r\n00:00:03,000 --> 00:00:04,250\r\nThank you &amp; goodbye.\r\n"
    parsed = parse_subtitles(srt, "lesson.srt")
    assert parsed[0]["startSeconds"] == 1.2
    assert parsed[0]["endSeconds"] == 2.5
    assert parsed[1]["en"] == "Thank you & goodbye."

    vtt = b"WEBVTT\n\n00:01.000 --> 00:02.000\n<v Alex>Hello there.</v>\n"
    cue = parse_subtitles(vtt, "lesson.vtt")[0]
    assert cue["speaker"] == "Alex"
    assert cue["en"] == "Hello there."


def test_media_upload_rejects_extension_content_mismatch():
    assert _media_extension("voice.mp3", b"ID3sample") == ".mp3"
    assert _media_extension("movie.mp4", b"not a video") is None


def test_asr_segments_are_normalized_to_reviewable_caption_drafts():
    captions = normalize_segments({"segments": [
        {"start": 0.1, "end": 1.25, "text": " Hello there. "},
        {"start": 3, "end": 2, "text": "invalid timing"},
        {"start": 2, "end": 3, "text": "Goodbye."},
    ]})
    assert captions == [
        {"speaker": "Speaker", "en": "Hello there.", "zh": "", "startSeconds": 0.1, "endSeconds": 1.25},
        {"speaker": "Speaker", "en": "Goodbye.", "zh": "", "startSeconds": 2.0, "endSeconds": 3.0},
    ]
    with pytest.raises(EnglishASRError, match="未返回逐句时间轴"):
        normalize_segments({"text": "No segments"})


def test_asr_background_job_persists_draft_and_removes_temporary_media(tmp_path, monkeypatch):
    from app.models import EnglishASRJob
    import app.services.english_asr_service as asr_service

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    source = tmp_path / "sample.mp3"
    source.write_bytes(b"temporary audio")
    with Session(engine) as db:
        db.add(EnglishASRJob(id="a" * 32, status="queued", filename="sample.mp3", input_path=str(source)))
        db.commit()

    async def fake_transcribe(_raw: bytes, _filename: str):
        return [{"speaker": "Speaker", "en": "Hello.", "zh": "", "startSeconds": 0, "endSeconds": 1}]

    monkeypatch.setattr(asr_service, "SessionLocal", lambda: Session(engine))
    monkeypatch.setattr(asr_service, "transcribe_english_audio", fake_transcribe)
    asr_service.run_english_asr_job("a" * 32)

    with Session(engine) as db:
        job = db.get(EnglishASRJob, "a" * 32)
        assert job.status == "succeeded"
        assert '"en": "Hello."' in job.transcript_json
    assert not source.exists()
