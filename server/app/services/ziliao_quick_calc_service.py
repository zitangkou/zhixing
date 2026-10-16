"""服务端速算训练：管理发布规则、生成可校验题目并保存练习闭环数据。"""
from __future__ import annotations

import json
import random
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import ZiliaoQuickMethod, ZiliaoQuickMethodVersion, ZiliaoQuickSession, gen_id
from app.schemas.ziliao import ZiliaoQuickMethodUpsert
from app.services.activity_service import record_event
from app.timezone import now

METHODS = [
    dict(code="direct", name="分数性质", category="比较", scene="分子更大、分母更小，直接判定。", knowledgePath="资料分析 / 快速比较方法", nodeTitle="快速比较方法", nodeParent="资料分析", sortOrder=10),
    dict(code="difference", name="差分比较", category="比较", scene="分子分母同向变大且差值简单，比较差分数与原分数。", knowledgePath="资料分析 / 快速比较方法 / 差分比较", nodeTitle="差分比较", nodeParent="快速比较方法", sortOrder=20),
    dict(code="position", name="同位比较", category="比较", scene="分子和分母跨过同一倍数界线的方向相反。", knowledgePath="资料分析 / 快速比较方法 / 同位比较", nodeTitle="同位比较", nodeParent="快速比较方法", sortOrder=30),
    dict(code="split", name="分母拆分", category="比较", scene="两个正分数接近 1，转为部分与剩余后比较。", knowledgePath="资料分析 / 快速比较方法 / 分母拆分", nodeTitle="分母拆分", nodeParent="快速比较方法", sortOrder=40),
    dict(code="growth-amount", name="增长量 · n＋1", category="计算", scene="正增长率为 1/n，增长量＝现期量 / (n＋1)。", knowledgePath="资料分析 / 增长 / 增长量（X）", nodeTitle="增长量（X）", nodeParent="增长", sortOrder=50),
    dict(code="growth-rate", name="增长率", category="计算", scene="已知现期量、基期量，先求差，再除以基期量。", knowledgePath="资料分析 / 增长 / 增长率（R）", nodeTitle="增长率（R）", nodeParent="增长", sortOrder=60),
    dict(code="base", name="基期量", category="计算", scene="现期量＝基期量×(1＋增长率)，逆推基期量。", knowledgePath="资料分析 / 增长 / 基期值（A）", nodeTitle="基期值（A）", nodeParent="增长", sortOrder=70),
]


def _json(value, fallback):
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def _out(row: ZiliaoQuickMethod) -> dict:
    return {"id": row.id, "code": row.code, "name": row.name, "category": row.category,
            "scene": row.scene, "knowledgePath": row.knowledge_path, "nodeTitle": row.node_title,
            "nodeParent": row.node_parent, "config": _json(row.config_json, {}), "enabled": row.enabled,
            "status": row.status, "version": row.version, "sortOrder": row.sort_order}


def _snapshot(row: ZiliaoQuickMethod) -> dict:
    return {"code": row.code, "name": row.name, "category": row.category, "scene": row.scene,
            "knowledgePath": row.knowledge_path, "nodeTitle": row.node_title, "nodeParent": row.node_parent,
            "config": _json(row.config_json, {}), "enabled": row.enabled, "sortOrder": row.sort_order}


def ensure_seeded(db: Session) -> None:
    known = {x.code for x in db.query(ZiliaoQuickMethod.code).all()}
    # 只修复旧版默认数据中的已知路径错误；不触碰发布记录或管理员自行修改过的关联。
    legacy_paths = {
        "direct": "资料分析 / 快速比较 / 大小比较",
        "difference": "资料分析 / 快速比较 / 大小比较 / 差分比较",
        "position": "资料分析 / 快速比较 / 大小比较 / 同位比较",
        "split": "资料分析 / 快速比较 / 大小比较 / 分母拆分（分子分母接近）",
    }
    for item in METHODS:
        if item["code"] in known:
            row = db.query(ZiliaoQuickMethod).filter_by(code=item["code"], status="draft").first()
            old_path = legacy_paths.get(item["code"])
            if row and old_path and row.knowledge_path in {
                old_path, old_path.replace(" / 快速比较 / ", " / 快速比较方法 / ")
            }:
                row.knowledge_path = item["knowledgePath"]
                row.node_title = item["nodeTitle"]
                row.node_parent = item["nodeParent"]
            continue
        db.add(ZiliaoQuickMethod(
            code=item["code"], name=item["name"], category=item["category"], scene=item["scene"],
            knowledge_path=item["knowledgePath"], node_title=item["nodeTitle"], node_parent=item["nodeParent"],
            config_json=json.dumps({"min": 1000, "max": 9000, "difficulty": 2}), enabled=True,
            status="draft", version=0, sort_order=item["sortOrder"],
        ))
    db.flush()
    for row in db.query(ZiliaoQuickMethod).filter_by(status="published").all():
        version = db.query(ZiliaoQuickMethodVersion.id).filter_by(method_id=row.id, version=row.version).first()
        if not version:
            db.add(ZiliaoQuickMethodVersion(method_id=row.id, version=row.version,
                snapshot_json=json.dumps(_snapshot(row), ensure_ascii=False)))
    db.commit()


def list_methods(db: Session, *, published_only: bool = False) -> list[dict]:
    ensure_seeded(db)
    q = db.query(ZiliaoQuickMethod)
    if published_only:
        q = q.filter(ZiliaoQuickMethod.status == "published", ZiliaoQuickMethod.enabled.is_(True))
    rows = q.order_by(ZiliaoQuickMethod.sort_order, ZiliaoQuickMethod.code).all()
    return [{**_out(row), "knowledgeResolved": _knowledge_path_resolves(db, row.knowledge_path)} for row in rows]


def upsert_method(db: Session, data: ZiliaoQuickMethodUpsert, method_id: str | None = None) -> dict | None:
    if data.code not in {item["code"] for item in METHODS}:
        raise ValueError("方法编码不受支持")
    if not data.name.strip() or not data.scene.strip() or not data.knowledgePath.strip() or not data.nodeTitle.strip():
        raise ValueError("方法名称、适用场景和知识框架关联不能为空")
    try:
        minimum = int(data.config.get("min", 1000))
        maximum = int(data.config.get("max", 9000))
        difficulty = int(data.config.get("difficulty", 2))
    except (TypeError, ValueError):
        raise ValueError("出题规则参数必须是整数") from None
    if minimum < 100 or maximum > 100000 or minimum >= maximum:
        raise ValueError("数值范围须满足 100 ≤ 下限 < 上限 ≤ 100000")
    if not 1 <= difficulty <= 5:
        raise ValueError("难度级别须为 1 至 5")
    config = {"min": minimum, "max": maximum, "difficulty": difficulty}
    row = db.get(ZiliaoQuickMethod, method_id) if method_id else db.query(ZiliaoQuickMethod).filter_by(code=data.code).first()
    if method_id and not row:
        return None
    if not row:
        row = ZiliaoQuickMethod(id=gen_id("zqm"), code=data.code)
        db.add(row)
    if row.code != data.code and db.query(ZiliaoQuickMethod).filter(ZiliaoQuickMethod.code == data.code, ZiliaoQuickMethod.id != row.id).first():
        raise ValueError("方法编码已存在")
    was_published = row.status == "published"
    for attr, value in (("code", data.code), ("name", data.name), ("category", data.category),
                        ("scene", data.scene), ("knowledge_path", data.knowledgePath),
                        ("node_title", data.nodeTitle), ("node_parent", data.nodeParent),
                        ("config_json", json.dumps(config, ensure_ascii=False)),
                        ("enabled", data.enabled), ("sort_order", data.sortOrder)):
        setattr(row, attr, value)
    row.status = "draft" if was_published else (row.status or "draft")
    db.commit()
    db.refresh(row)
    return _out(row)


def publish_method(db: Session, method_id: str) -> dict | None:
    row = db.get(ZiliaoQuickMethod, method_id)
    if not row:
        return None
    if not row.enabled:
        raise ValueError("停用的方法不能发布")
    if row.status == "published":
        raise ValueError("方法已发布；请先编辑并保存为草稿，再发布新版本")
    if not _knowledge_path_resolves(db, row.knowledge_path):
        raise ValueError("关联的知识框架节点不存在或尚未发布，请修正框架路径后再发布")
    validate_method(row.code, _json(row.config_json, {}))
    row.version += 1
    row.status = "published"
    db.add(ZiliaoQuickMethodVersion(method_id=row.id, version=row.version,
        snapshot_json=json.dumps(_snapshot(row), ensure_ascii=False)))
    db.commit()
    db.refresh(row)
    return _out(row)


def list_method_versions(db: Session, method_id: str) -> list[dict] | None:
    row = db.get(ZiliaoQuickMethod, method_id)
    if not row:
        return None
    return [{"version": item.version, "publishedAt": item.published_at.isoformat(),
             "snapshot": _json(item.snapshot_json, {})}
            for item in db.query(ZiliaoQuickMethodVersion).filter_by(method_id=method_id)
            .order_by(ZiliaoQuickMethodVersion.version.desc()).all()]


def rollback_method(db: Session, method_id: str, version_number: int) -> dict | None:
    row = db.get(ZiliaoQuickMethod, method_id)
    version = db.query(ZiliaoQuickMethodVersion).filter_by(method_id=method_id, version=version_number).first()
    if not row or not version:
        return None
    snapshot = _json(version.snapshot_json, {})
    row.code = snapshot["code"]; row.name = snapshot["name"]; row.category = snapshot["category"]
    row.scene = snapshot["scene"]; row.knowledge_path = snapshot["knowledgePath"]
    row.node_title = snapshot["nodeTitle"]; row.node_parent = snapshot["nodeParent"]
    row.config_json = json.dumps(snapshot["config"], ensure_ascii=False)
    row.enabled = snapshot["enabled"]; row.sort_order = snapshot["sortOrder"]
    row.status = "draft"
    db.commit()
    return publish_method(db, method_id)


def _options(correct: str, distractors: list[str], rng: random.Random) -> tuple[list[str], int]:
    values = list(dict.fromkeys([correct, *distractors]))
    fallbacks = ["左边大于右边", "左边小于右边", "两边相等", "根据题目无法判断"]
    step = 0
    while len(values) < 4:
        candidate = fallbacks[step]
        step += 1
        if candidate not in values:
            values.append(candidate)
    values = values[:4]
    rng.shuffle(values)
    return values, values.index(correct)


def _generate(code: str, config: dict, rng: random.Random) -> dict:
    low = max(100, int(config.get("min", 1000)))
    high = max(low + 100, min(100000, int(config.get("max", 9000))))
    level = max(1, min(5, int(config.get("difficulty", 2))))
    if code in {"direct", "difference", "position", "split"}:
        if code == "direct":
            c, d = rng.randint(low, high), rng.randint(low, high)
            a, b = c + rng.randint(20, 200) * level, max(1, d - rng.randint(20, 200) * level)
            step = f"左边分子 {a} 大于 {c}，分母 {b} 小于 {d}，所以左边分数更大。"
            pitfall = "分子、分母都更大时，不能直接说分数更大。"
        elif code == "difference":
            d_min = max(500, low // 5); d_max = max(d_min + 1, min(2400, high // 3))
            d = rng.randint(d_min, d_max); k = rng.randint(3, 9); c = k * d + rng.randint(100, 400)
            delta = rng.randint(12, 40) * level; high_side = rng.choice([True, False]); da = (k + 2 if high_side else k - 1) * delta
            a, b = c + da, d + delta
            cmp = "更大" if high_side else "更小"
            step = f"差分数为 {da}/{delta}={da // delta}，右边原分数位于 {k} 与 {k + 1} 之间，左边原分数{cmp}。"
            pitfall = "差分法要求分子、分母同向作差且差分母为正。"
        elif code == "position":
            k = rng.randint(2, 4); c_min = max(500, low // 2); c_max = max(c_min + 1, min(4000, high))
            c = rng.randint(c_min, c_max); d = rng.randint(200, max(201, min(600, high // 10)))
            a, b = k * c + rng.randint(20, 100) * level, k * d - rng.randint(10, 60) * level
            step = f"分子超过 {k} 倍、分母不足 {k} 倍，因此左边大于同时放大后的右边。"
            pitfall = "分子、分母跨越倍数界线的方向相反时才能直接判定。"
        else:
            c_min = max(1500, low); c_max = max(c_min + 1, min(9000, high))
            c = rng.randint(c_min, c_max); a = c + rng.randint(400, 800)
            left_rest = rng.randint(150, 350) * level; right_rest = left_rest + rng.randint(30, 180) * level
            b, d = a + left_rest, c + right_rest
            step = f"两个分数均小于 1，改比部分/剩余：{a}/{left_rest} 与 {c}/{right_rest}，左边更大。"
            pitfall = "要求 0＜分子＜分母且剩余量为正。"
        if rng.random() < .5:
            a, b, c, d = c, d, a, b
            step = step.replace("左边", "临时侧").replace("右边", "左边").replace("临时侧", "右边")
        delta = a * d - c * b
        answer_text = "左边大于右边" if delta > 0 else "左边小于右边" if delta < 0 else "两边相等"
        options, answer = _options(answer_text, ["根据题目无法判断"], rng)
        latex = f"\\frac{{{a}}}{{{b}}}\\quad\\text{{与}}\\quad\\frac{{{c}}}{{{d}}}"
        return {"method": code, "stem": "比较下面两个分数的大小，选择正确关系。", "latex": latex,
                "plain": f"{a}/{b} 与 {c}/{d}", "options": options, "answer": answer,
                "steps": [{"text": step}], "pitfall": pitfall,
                "check": "compare", "values": [a, b, c, d], "source": {"method": code}}

    if code == "growth-amount":
        n = rng.choice([4, 5, 8, 10, 16, 20])
        base_min = max(20, low // n); base_max = max(base_min + 1, min(700, high // n))
        base = rng.randint(base_min, base_max) * n
        current = base + base // n; target = current // (n + 1)
        stem = f"现期量为 {current}，同比增长 {100 // n if 100 % n == 0 else format(100 / n, '.2f')}%，增长量最接近多少？"
        latex = f"\\frac{{{current}}}{{{n + 1}}}"
        steps = [{"text": f"增长率为 1/{n}，使用 n＋1 原则。", "latex": f"X=\\frac{{{current}}}{{{n + 1}}}={target}"}]
        pitfall = "增长量＝现期量×增长率÷（1＋增长率），不是现期量×增长率。"
        candidates = [target, current // n, current // (n - 1), current // (n + 2)]
        source = {"current": current, "n": n}
        unit = ""
    elif code == "growth-rate":
        base_min = max(15, low // 1000); base_max = max(base_min + 1, min(100, high // 1000))
        base = rng.randint(base_min, base_max) * 1000; tenths = rng.randint(40, 300); current = base + base * tenths // 1000
        target = tenths / 10; unit = "%"; stem = f"基期量为 {base}，现期量为 {current}，同比增长率是多少？（保留一位小数）"
        latex = f"\\frac{{{current}-{base}}}{{{base}}}\\times100\\%"
        steps = [{"text": f"增长量为 {current - base}，除以基期量 {base}，得到 {target:.1f}%。"}]
        pitfall = "增长率的分母是基期量；用现期量作分母会算小。"
        candidates = [target, (current - base) / current * 100, target + 5 * level, target - 3 * level]
        source = {"current": current, "base": base}
    elif code == "base":
        base_min = max(100, low // 10); base_max = max(base_min + 1, min(900, high // 10))
        base = rng.randint(base_min, base_max) * 10; rate = rng.choice([5, 10, 12.5, 20, 25]); current = base * (1 + rate / 100)
        target = float(base); unit = ""; stem = f"现期量为 {current:g}，同比增长 {rate:g}%，基期量最接近多少？"
        latex = f"\\frac{{{current:g}}}{{1+{rate:g}\\%}}"
        steps = [{"text": "用现期量除以（1＋增长率）还原基期量。", "latex": f"A=\\frac{{{current:g}}}{{1+{rate:g}\\%}}={base}"}]
        pitfall = "现期量×（1－增长率）通常不等于基期量。"
        candidates = [target, current * (1 - rate / 100), current, current / (rate / 100)]
        source = {"current": current, "rate": rate}
    else:
        raise ValueError("不支持的速算生成方法")
    precision = 1 if unit == "%" else 0
    round_to = lambda n: round(float(n) + 1e-10, precision)
    target = round_to(target); values = []
    for value in candidates:
        value = round_to(value)
        if value >= 0 and value not in values:
            values.append(value)
    increment = 0.1 if unit else max(1, round(target * .08)) * level
    offset = 1
    while len(values) < 4:
        value = round_to(target + increment * offset); offset += 1
        if value not in values:
            values.append(value)
    values = values[:4]; rng.shuffle(values)
    options = [f"{v:g}{unit}" for v in values]
    return {"method": code, "stem": stem, "latex": latex, "plain": stem, "options": options,
            "answer": values.index(target), "steps": steps, "pitfall": pitfall,
            "check": "number", "target": target, "values": values, "unit": unit, "source": source}


def _safe_question(question: dict) -> dict:
    return {k: v for k, v in question.items() if k not in {"answer", "check", "values", "target", "unit", "source", "steps", "pitfall"}}


def preview(db: Session, code: str, count: int = 5) -> dict:
    method = next((m for m in list_methods(db) if m["code"] == code), None)
    if not method:
        raise ValueError("训练方法不存在")
    rng = random.Random(20261016)
    questions = [_generate(code, method["config"], rng) for _ in range(max(1, min(20, count)))]
    _validate_questions(questions)
    knowledge_resolved = _knowledge_path_resolves(db, method["knowledgePath"])
    return {"valid": knowledge_resolved, "mathValid": True, "knowledgeResolved": knowledge_resolved,
            "validationMessage": "知识框架节点已解析" if knowledge_resolved else "知识框架节点不存在或尚未发布",
            "method": method, "questions": questions}


def _knowledge_path_resolves(db: Session, path: str) -> bool:
    parts = [part.strip() for part in path.split("/") if part.strip()]
    if len(parts) < 2:
        return False
    from app.services.knowledge_service import get_tree

    tree = get_tree(db, parts[0], visible_only=True)
    if not tree:
        return False
    siblings = tree.nodes
    for title in parts[1:]:
        node = next((item for item in siblings if item.title.strip() == title), None)
        if not node:
            return False
        siblings = node.children or []
    return True


def _validate_questions(questions: list[dict]) -> None:
    for question in questions:
        if len(question["options"]) != 4 or len(set(question["options"])) != 4:
            raise ValueError("选项必须为四个互不重复的内容")
        if question["check"] == "compare":
            a, b, c, d = question["values"]
            if min(a, b, c, d) <= 0:
                raise ValueError("分数分子、分母必须为正数")
            delta = a * d - c * b
            expected = "左边大于右边" if delta > 0 else "左边小于右边" if delta < 0 else "两边相等"
            if question["options"][question["answer"]] != expected:
                raise ValueError("分数比较答案与交叉乘积校验不一致")
            if question["method"] == "split" and not (a < b and c < d):
                raise ValueError("分母拆分题未满足正分数适用条件")
            if question["method"] == "direct" and not ((a > c and b < d) or (a < c and b > d)):
                raise ValueError("分数性质题未满足分子、分母方向相反的条件")
            if question["method"] == "difference":
                if a > c:
                    high_n, high_d, low_n, low_d = a, b, c, d
                else:
                    high_n, high_d, low_n, low_d = c, d, a, b
                if high_n <= low_n or high_d <= low_d:
                    raise ValueError("差分题的分子分母没有同向增加")
                delta_sign = (high_n - low_n) * low_d - low_n * (high_d - low_d)
                fraction_sign = high_n * low_d - low_n * high_d
                if (delta_sign > 0) != (fraction_sign > 0):
                    raise ValueError("差分题中差分数与原分数的关系不一致")
            if question["method"] == "position":
                if a > c:
                    high_n, high_d, low_n, low_d = a, b, c, d
                else:
                    high_n, high_d, low_n, low_d = c, d, a, b
                if not any(high_n > k * low_n and high_d < k * low_d for k in (2, 3, 4)):
                    raise ValueError("同位比较题未满足同一倍数界线条件")
            if question["method"] == "split":
                split_sign = a * (d - c) - c * (b - a)
                if (split_sign > 0) != (delta > 0):
                    raise ValueError("分母拆分前后大小关系不一致")
        elif question["values"][question["answer"]] != question["target"]:
            raise ValueError("数值题正确选项与精确结果不一致")
        else:
            source = question["source"]
            if question["method"] == "growth-amount":
                exact = source["current"] / (source["n"] + 1)
            elif question["method"] == "growth-rate":
                exact = round((source["current"] - source["base"]) / source["base"] * 100 + 1e-10, 1)
            else:
                exact = round(source["current"] / (1 + source["rate"] / 100) + 1e-10)
            if exact != question["target"]:
                raise ValueError("题干数据独立计算与正确答案不一致")


def validate_method(code: str, config: dict) -> None:
    rng = random.Random(731)
    questions = [_generate(code, config, rng) for _ in range(20)]
    _validate_questions(questions)


def create_session(db: Session, user_id: str, mode: str, count: int) -> dict:
    methods = list_methods(db, published_only=True)
    selected = [m for m in methods if mode == "mixed" or m["code"] == mode]
    if not selected:
        raise ValueError("没有可用的已发布训练方法")
    rng = random.SystemRandom()
    if mode == "mixed":
        rng.shuffle(selected)
    questions = []
    seen = set()
    versions = {}
    for i in range(count):
        method = selected[i % len(selected)] if mode == "mixed" else selected[0]
        versions[method["code"]] = method["version"]
        question = None
        for _ in range(100):
            candidate = _generate(method["code"], method["config"], rng)
            if candidate["latex"] not in seen:
                question = candidate
                seen.add(candidate["latex"])
                break
        if question is None:
            raise ValueError("本组题目无法去重，请调整方法或题量")
        questions.append({**question, "id": gen_id("qci")})
    if mode == "mixed":
        rng.shuffle(questions)
    row = ZiliaoQuickSession(id=gen_id("zqs"), user_id=user_id, mode=mode,
        method_versions_json=json.dumps(versions), questions_json=json.dumps(questions, ensure_ascii=False),
        answers_json="[]", status="active")
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "mode": mode, "questions": [_safe_question(q) for q in questions]}


def answer_question(db: Session, user_id: str, session_id: str, question_id: str, selected: int, seconds: int) -> dict | None:
    row = db.get(ZiliaoQuickSession, session_id)
    if not row or row.user_id != user_id or row.status != "active":
        return None
    questions = _json(row.questions_json, []); answers = _json(row.answers_json, [])
    question = next((q for q in questions if q["id"] == question_id), None)
    if not question:
        raise ValueError("题目不属于当前练习")
    existing = next((a for a in answers if a["questionId"] == question_id), None)
    if existing:
        if existing["selected"] != selected:
            raise ValueError("本题已经提交，不能修改答案")
        return {"correct": existing["correct"], "correctOption": question["options"][question["answer"]], "steps": question["steps"], "pitfall": question["pitfall"]}
    correct = selected == question["answer"]
    answers.append({"questionId": question_id, "selected": selected, "selectedText": question["options"][selected],
                    "correct": correct, "seconds": seconds, "method": question["method"],
                    "correctOption": question["answer"]})
    row.answers_json = json.dumps(answers, ensure_ascii=False)
    db.commit()
    return {"correct": correct, "correctOption": question["options"][question["answer"]], "steps": question["steps"], "pitfall": question["pitfall"]}


def complete_session(db: Session, user_id: str, session_id: str, total_seconds: int) -> dict | None:
    row = db.get(ZiliaoQuickSession, session_id)
    if not row or row.user_id != user_id:
        return None
    if row.status != "completed":
        answers = _json(row.answers_json, [])
        if not answers:
            raise ValueError("本组尚无已作答题目")
        row.status = "completed"; row.total_seconds = total_seconds; row.completed_at = now()
        db.commit()
        record_event(db, user_id, "quick_calc_done", {"sessionId": row.id, "mode": row.mode,
            "total": len(answers), "correct": sum(1 for a in answers if a["correct"])}, commit=True)
    answers = _json(row.answers_json, [])
    return {"sessionId": row.id, "total": len(answers), "correct": sum(1 for a in answers if a["correct"]),
            "seconds": row.total_seconds, "completed": row.status == "completed"}


def analytics(db: Session, days: int = 30) -> dict:
    since = now() - timedelta(days=max(1, min(365, days)))
    sessions = db.query(ZiliaoQuickSession).filter(ZiliaoQuickSession.created_at >= since,
        ZiliaoQuickSession.status == "completed").all()
    by_method: dict[str, dict] = {}
    for session in sessions:
        for answer in _json(session.answers_json, []):
            item = by_method.setdefault(answer["method"], {"method": answer["method"], "attempts": 0, "correct": 0, "seconds": 0, "wrongOptions": {}})
            item["attempts"] += 1; item["correct"] += int(answer["correct"]); item["seconds"] += answer["seconds"]
            if not answer["correct"]:
                wrong_key = str(answer.get("selectedText", answer["selected"]))
                item["wrongOptions"][wrong_key] = item["wrongOptions"].get(wrong_key, 0) + 1
    methods = {m["code"]: m["name"] for m in list_methods(db)}
    rows = []
    for code, item in by_method.items():
        item["name"] = methods.get(code, code)
        item["accuracy"] = round(item["correct"] * 100 / item["attempts"], 1) if item["attempts"] else 0
        item["averageSeconds"] = round(item["seconds"] / item["attempts"], 1) if item["attempts"] else 0
        rows.append(item)
    return {"days": days, "sessions": len(sessions), "attempts": sum(x["attempts"] for x in rows),
            "methods": sorted(rows, key=lambda x: x["method"])}


def user_history(db: Session, user_id: str, limit: int = 10) -> dict:
    rows = (db.query(ZiliaoQuickSession).filter_by(user_id=user_id, status="completed")
            .order_by(ZiliaoQuickSession.completed_at.desc()).limit(max(1, min(30, limit))).all())
    result = []; by_method: dict[str, dict[str, int]] = {}
    for row in rows:
        answers = _json(row.answers_json, [])
        result.append({"id": row.id, "mode": row.mode, "date": row.completed_at.isoformat() if row.completed_at else "",
                       "correct": sum(1 for a in answers if a["correct"]), "total": len(answers),
                       "seconds": row.total_seconds})
        for answer in answers:
            item = by_method.setdefault(answer["method"], {"attempts": 0, "correct": 0})
            item["attempts"] += 1; item["correct"] += int(answer["correct"])
    method_names = {m["code"]: m["name"] for m in list_methods(db, published_only=True)}
    recommendations = []
    for code, item in by_method.items():
        if item["attempts"] >= 5:
            accuracy = round(item["correct"] * 100 / item["attempts"], 1)
            if accuracy < 75 and code in method_names:
                recommendations.append({"code": code, "name": method_names[code], "accuracy": accuracy, "attempts": item["attempts"]})
    recommendations.sort(key=lambda x: (x["accuracy"], -x["attempts"]))
    return {"sessions": result, "recommendations": recommendations[:3]}


def retry_wrong(db: Session, user_id: str, session_id: str, question_ids: list[str]) -> dict | None:
    source = db.get(ZiliaoQuickSession, session_id)
    if not source or source.user_id != user_id or source.status != "completed":
        return None
    questions = _json(source.questions_json, [])
    answers = _json(source.answers_json, [])
    wrong_ids = {a["questionId"] for a in answers if not a["correct"]}
    requested = set(question_ids) & wrong_ids
    selected = [q for q in questions if q["id"] in requested]
    if not selected:
        raise ValueError("未找到可重练的错题")
    row = ZiliaoQuickSession(id=gen_id("zqs"), user_id=user_id, mode="retry",
        method_versions_json=source.method_versions_json, questions_json=json.dumps(selected, ensure_ascii=False),
        answers_json="[]", status="active")
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "mode": "retry", "questions": [_safe_question(q) for q in selected]}
