#!/usr/bin/env python3
"""P3 学习反馈 — 演示练习数据生成脚本。

基于 Q2/Q3 生成题的 distractors 错误路径，模拟用户作答：
- 正确项选择率 60~80%（按难度调整：简单 80%、中等 70%、较难 60%）
- 各干扰项按错误路径常见程度分配选择率
- 数据明确标注 source="demo"，不与真实数据混淆

用法:
    cd server && source .venv/bin/activate
    PYTHONPATH=. python3 ../scripts/xingce/gen_demo_practice_data.py [--users 20] [--per-question 15]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 确保能 import app
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SERVER_DIR = _REPO_ROOT / "server"
sys.path.insert(0, str(_SERVER_DIR))

from app.database import SessionLocal, engine  # noqa: E402
from app.models import Base, PracticeAnswer  # noqa: E402

_QUESTION_BANK_PATH = _REPO_ROOT / "xingce-structured-data" / "generated" / "qa_data_analysis_v2.json"

# 错误路径常见程度权重（模拟真实用户犯错分布）
ERROR_PATH_WEIGHTS = {
    "基期现期颠倒": 1.5,
    "百分数未转换": 1.2,
    "直接用现期量": 1.0,
    "公式记错": 1.3,
    "计算错误": 1.8,
    "审题错误": 1.4,
    "单位换算错误": 0.8,
    "百分点与百分数混淆": 1.1,
    "其他错误": 0.5,
}


def load_questions() -> list[dict]:
    with open(_QUESTION_BANK_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["questions"]


def simulate_answer(question: dict, rng: random.Random) -> tuple[str, int]:
    """模拟单题作答，返回 (user_answer, time_spent_ms)。"""
    correct = question["answer"].strip().upper()
    options = question.get("options", {})
    distractors = question.get("distractors", {})
    difficulty = question.get("difficulty", 2)

    # 正确率按难度：简单 80%、中等 70%、较难 60%
    correct_rate = {1: 0.80, 2: 0.70, 3: 0.60}.get(difficulty, 0.70)

    # 用时：简单 20-40s，中等 30-60s，较难 40-90s
    time_base = {1: (20000, 40000), 2: (30000, 60000), 3: (40000, 90000)}.get(difficulty, (30000, 60000))
    time_spent = rng.randint(*time_base)

    if rng.random() < correct_rate:
        return correct, time_spent

    # 选错：从干扰项中按错误路径权重选择
    wrong_options = [opt for opt in options.keys() if opt != correct]
    if not wrong_options:
        return correct, time_spent

    weights = []
    for opt in wrong_options:
        dist = distractors.get(opt, {})
        ep_type = dist.get("type", "其他错误")
        w = ERROR_PATH_WEIGHTS.get(ep_type, 1.0)
        weights.append(w)

    chosen = rng.choices(wrong_options, weights=weights, k=1)[0]
    return chosen, time_spent


def generate_demo_data(num_users: int = 20, per_question_min: int = 10, per_question_max: int = 25):
    """生成演示练习数据。"""
    questions = load_questions()
    print(f"题库题目数: {len(questions)}")

    db = SessionLocal()
    try:
        # 确保表存在（脚本独立运行时不会走 lifespan 的 create_all）
        Base.metadata.create_all(bind=engine)

        # 清除已有 demo 数据（幂等）
        deleted = db.query(PracticeAnswer).filter(PracticeAnswer.source == "demo").delete()
        if deleted:
            print(f"清除旧 demo 数据: {deleted} 条")
            db.commit()

        rng = random.Random(42)
        total_inserted = 0
        now = datetime.now()

        for user_idx in range(num_users):
            user_id = f"demo-user-{user_idx + 1:03d}"
            # 每个用户在过去 14 天内随机分布作答时间
            for question in questions:
                # 每个用户不一定做所有题，80% 概率做
                if rng.random() > 0.80:
                    continue

                num_attempts = rng.randint(1, 3)  # 每题最多尝试 3 次
                for attempt in range(num_attempts):
                    user_answer, time_spent = simulate_answer(question, rng)

                    # 作答时间：过去 14 天内随机
                    days_ago = rng.randint(0, 13)
                    hours_ago = rng.randint(8, 22)
                    created_at = now - timedelta(days=days_ago, hours=hours_ago - now.hour)
                    created_at = created_at.replace(minute=rng.randint(0, 59), second=rng.randint(0, 59))

                    record = PracticeAnswer(
                        user_id=user_id,
                        question_id=question["question_id"],
                        daily_id=f"practice-demo-{days_ago:02d}",
                        user_answer=user_answer,
                        correct_answer=question["answer"].strip().upper(),
                        is_correct=(user_answer == question["answer"].strip().upper()),
                        time_spent_ms=time_spent,
                        source="demo",
                    )
                    # 手动设置 created_at
                    record.created_at = created_at
                    db.add(record)
                    total_inserted += 1

        db.commit()

        # 统计
        total = db.query(PracticeAnswer).filter(PracticeAnswer.source == "demo").count()
        correct = db.query(PracticeAnswer).filter(
            PracticeAnswer.source == "demo",
            PracticeAnswer.is_correct == True,  # noqa: E712
        ).count()
        print(f"生成完成: {total_inserted} 条作答记录")
        print(f"  总练习人次: {total}")
        print(f"  正确数: {correct}")
        print(f"  总正确率: {correct / total * 100:.1f}%" if total else "  无数据")
        print(f"  涉及题目数: {db.query(PracticeAnswer.question_id).filter(PracticeAnswer.source == 'demo').distinct().count()}")
        print(f"  涉及用户数: {db.query(PracticeAnswer.user_id).filter(PracticeAnswer.source == 'demo').distinct().count()}")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成演示练习数据")
    parser.add_argument("--users", type=int, default=20, help="模拟用户数")
    parser.add_argument("--per-question-min", type=int, default=10, help="每题最少作答次数（参考）")
    parser.add_argument("--per-question-max", type=int, default=25, help="每题最多作答次数（参考）")
    args = parser.parse_args()

    generate_demo_data(args.users, args.per_question_min, args.per_question_max)
