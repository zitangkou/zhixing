"""导入纲要专项 T0c JSON（20 题，选项 A–D 对象，含出处与干扰）。"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import Article, Question, TheoryLearningEntry, gen_id
from app.services.question_service import delete_questions_for_article
from app.services.serializers import encode_correct_answer
from app.services.theory_learning_entry_service import save_entry


def _option_list(options: object) -> list[str]:
    if isinstance(options, dict):
        return [str(options[k]).strip() for k in ("A", "B", "C", "D") if str(options.get(k) or "").strip()]
    if isinstance(options, list):
        return [str(x).strip() for x in options if str(x).strip()]
    return []


def _analysis(item: dict) -> str:
    explanation = str(item.get("explanation") or "").strip()
    lines = [explanation] if explanation else []
    distractors = item.get("distractors")
    if isinstance(distractors, list) and distractors:
        lines.append("【干扰项】")
        for d in distractors:
            if not isinstance(d, dict):
                continue
            letter = str(d.get("option") or "").strip()
            kind = str(d.get("type") or "").strip()
            path = str(d.get("error_path") or "").strip()
            content = str(d.get("content") or "").strip()
            bit = " ".join(x for x in (letter, kind) if x)
            detail = path or content
            if bit and detail:
                lines.append(f"{bit}：{detail}")
            elif detail:
                lines.append(detail)
    return "\n".join(lines).strip()


def questions_from_t0c(payload: dict) -> list[dict]:
    rows = payload.get("questions")
    if not isinstance(rows, list) or not rows:
        raise ValueError("JSON 中没有 questions")
    out = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        options = _option_list(item.get("options"))
        if len(options) < 2:
            raise ValueError("题目选项不足")
        letter = str(item.get("answer") or "").strip().upper()
        idx = ord(letter) - 65 if len(letter) == 1 and "A" <= letter <= "D" else -1
        if idx < 0 or idx >= len(options):
            raise ValueError(f"无法解析答案：{item.get('question_id')}")
        source = str(item.get("source_ref") or payload.get("source_ref") or "").strip()
        analysis = _analysis(item)
        if not analysis:
            raise ValueError(f"缺少解析：{item.get('question_id')}")
        if not source:
            raise ValueError(f"缺少出处：{item.get('question_id')}")
        subtype = str(item.get("subtype") or "").strip()
        stem = str(item.get("stem") or "").strip()
        if subtype:
            stem = f"【{subtype}】{stem}"
        out.append({
            "type": "single",
            "stem": stem,
            "options": options,
            "correct_answer": options[idx],
            "analysis": analysis,
            "source_sentence": source,
        })
    if len(out) != 20:
        raise ValueError(f"应为 20 题，实际 {len(out)}")
    return out


def import_t0c_pack(db: Session, payload: dict, *, pending: bool = False) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload 必须是对象")
    title = str(payload.get("article_section") or payload.get("article_title") or "").strip()
    if not title:
        raise ValueError("缺少卷标题")
    questions = questions_from_t0c(payload)
    summary = str(payload.get("source_ref") or payload.get("value_label") or title)[:500]
    source_url = str(payload.get("material_anchor") or "")[:512]
    article = db.query(Article).filter(Article.title == title).first()
    if not article:
        article = Article(
            id=gen_id("art"),
            title=title,
            source=str(payload.get("source") or "纲要专项")[:64],
            source_url=source_url,
            publish_date=str(payload.get("date") or "")[:10],
            summary=summary,
            content=summary,
            sections="[]",
            tags=json.dumps(["纲要专项", "时政刷题"], ensure_ascii=False),
            mind_map="{}",
            status="published",
            allow_quiz=True,
            is_published=True,
            is_daily="卷02" in title,
            is_featured=False,
        )
        db.add(article)
        db.flush()
    else:
        article.summary = summary
        article.content = summary
        article.source_url = source_url or article.source_url
        article.allow_quiz = True
        article.is_published = True
        article.status = "published"
        article.is_daily = article.is_daily or ("卷02" in title)

    delete_questions_for_article(db, article.id)
    status = "pending" if pending else "approved"
    created: list[Question] = []
    for qdata in questions:
        row = Question(
            id=gen_id("q"),
            article_id=article.id,
            type=qdata["type"],
            stem=qdata["stem"],
            options=json.dumps(qdata["options"], ensure_ascii=False),
            correct_answer=encode_correct_answer(qdata["correct_answer"]),
            analysis=qdata["analysis"],
            source_sentence=qdata["source_sentence"],
            status=status,
            origin="import",
            is_active=not pending,
        )
        db.add(row)
        created.append(row)
    db.flush()
    parts = []
    for i in range(4):
        chunk = created[i * 5 : (i + 1) * 5]
        parts.append({
            "title": f"第 {i + 1} 辑",
            "questionIds": [q.id for q in chunk],
        })
    entry = save_entry(
        db,
        article.id,
        {
            "title": title,
            "description": summary,
            "isDaily": "卷02" in title,
            "isEvergreen": True,
            "parts": parts,
            "collectionEnabled": True,
            "status": "draft" if pending else "published",
            "publishStart": "",
            "publishEnd": "",
            "sortOrder": 0,
        },
    )
    return {
        "articleId": article.id,
        "title": title,
        "questionCount": len(created),
        "entry": entry,
    }
