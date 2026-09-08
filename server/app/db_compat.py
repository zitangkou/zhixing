"""SQLite 旧库兼容迁移：启动时补列，避免手动 ALTER。

模型仍在演进期，先用轻量补列；表结构稳定后可迁移到正式迁移工具（Alembic）。
"""
from __future__ import annotations

from app.database import engine

def _ensure_article_columns():
    """SQLite 旧库补列"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("articles"):
        return
    cols = [c["name"] for c in insp.get_columns("articles")]
    alters: list[str] = []
    if "sections" not in cols:
        alters.append("ALTER TABLE articles ADD COLUMN sections TEXT DEFAULT '[]'")
    if "is_featured" not in cols:
        alters.append("ALTER TABLE articles ADD COLUMN is_featured BOOLEAN DEFAULT 0")
    if "category_id" not in cols:
        alters.append("ALTER TABLE articles ADD COLUMN category_id VARCHAR(32)")
    if "category_path" not in cols:
        alters.append("ALTER TABLE articles ADD COLUMN category_path TEXT DEFAULT '[]'")
    if "importance" not in cols:
        alters.append("ALTER TABLE articles ADD COLUMN importance INTEGER DEFAULT 3")
    if "status" not in cols:
        alters.append("ALTER TABLE articles ADD COLUMN status VARCHAR(16) DEFAULT 'published'")
    if "allow_quiz" not in cols:
        alters.append("ALTER TABLE articles ADD COLUMN allow_quiz BOOLEAN DEFAULT 1")
    if not alters:
        return
    with engine.begin() as conn:
        for sql in alters:
            conn.execute(text(sql))


def _ensure_app_user_columns():
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("app_users"):
        return
    cols = [c["name"] for c in insp.get_columns("app_users")]
    alters: list[str] = []
    if "username" not in cols:
        alters.append("ALTER TABLE app_users ADD COLUMN username VARCHAR(64)")
    if "password_hash" not in cols:
        alters.append("ALTER TABLE app_users ADD COLUMN password_hash VARCHAR(255)")
    if "email" not in cols:
        alters.append("ALTER TABLE app_users ADD COLUMN email VARCHAR(128) DEFAULT ''")
    if "phone" not in cols:
        alters.append("ALTER TABLE app_users ADD COLUMN phone VARCHAR(20) DEFAULT ''")
    if not alters:
        return
    with engine.begin() as conn:
        for sql in alters:
            conn.execute(text(sql))


def _ensure_manual_wrong_images_column():
    """兼容旧 manual_wrongs 表"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("manual_wrongs"):
        return
    cols = [c["name"] for c in insp.get_columns("manual_wrongs")]
    # SQLAlchemy 会自动 create_all 新表，这里只处理已存在旧表
    needed = {
        "images": "ALTER TABLE manual_wrongs ADD COLUMN images TEXT DEFAULT '[]'",
        "source": "ALTER TABLE manual_wrongs ADD COLUMN source VARCHAR(32) DEFAULT 'manual'",
        "review_count": "ALTER TABLE manual_wrongs ADD COLUMN review_count INTEGER DEFAULT 0",
        "review_stage": "ALTER TABLE manual_wrongs ADD COLUMN review_stage INTEGER DEFAULT 0",
        "next_review_at": "ALTER TABLE manual_wrongs ADD COLUMN next_review_at DATETIME",
        "mastered": "ALTER TABLE manual_wrongs ADD COLUMN mastered BOOLEAN DEFAULT 0",
        "wrong_reason": "ALTER TABLE manual_wrongs ADD COLUMN wrong_reason VARCHAR(64) DEFAULT ''",
        "question_type": "ALTER TABLE manual_wrongs ADD COLUMN question_type VARCHAR(64) DEFAULT ''",
        "note": "ALTER TABLE manual_wrongs ADD COLUMN note TEXT DEFAULT ''",
        "knowledge_node_id": "ALTER TABLE manual_wrongs ADD COLUMN knowledge_node_id VARCHAR(32)",
        "knowledge_tree_key": "ALTER TABLE manual_wrongs ADD COLUMN knowledge_tree_key VARCHAR(32) DEFAULT ''",
        "knowledge_path": "ALTER TABLE manual_wrongs ADD COLUMN knowledge_path TEXT DEFAULT ''",
    }
    alters = [sql for col, sql in needed.items() if col not in cols]
    with engine.begin() as conn:
        for sql in alters:
            conn.execute(text(sql))
        if "next_review_at" in cols or "next_review_at" in needed:
            conn.execute(
                text(
                    "UPDATE manual_wrongs SET next_review_at = CURRENT_TIMESTAMP "
                    "WHERE next_review_at IS NULL AND (mastered = 0 OR mastered IS NULL)"
                )
            )


def _ensure_knowledge_node_columns():
    """兼容旧 knowledge_nodes 表：补 my_note / is_starred / 掌握度字段"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("knowledge_nodes"):
        return
    cols = [c["name"] for c in insp.get_columns("knowledge_nodes")]
    alters: list[str] = []
    if "my_note" not in cols:
        alters.append("ALTER TABLE knowledge_nodes ADD COLUMN my_note TEXT DEFAULT ''")
    if "is_starred" not in cols:
        alters.append("ALTER TABLE knowledge_nodes ADD COLUMN is_starred BOOLEAN DEFAULT 0")
    if "mastery_level" not in cols:
        alters.append("ALTER TABLE knowledge_nodes ADD COLUMN mastery_level VARCHAR(16) DEFAULT 'new'")
    if "next_review_at" not in cols:
        alters.append("ALTER TABLE knowledge_nodes ADD COLUMN next_review_at DATETIME")
    if "review_count" not in cols:
        alters.append("ALTER TABLE knowledge_nodes ADD COLUMN review_count INTEGER DEFAULT 0")
    if "last_reviewed_at" not in cols:
        alters.append("ALTER TABLE knowledge_nodes ADD COLUMN last_reviewed_at DATETIME")
    if not alters:
        return
    with engine.begin() as conn:
        for sql in alters:
            conn.execute(text(sql))


def _ensure_exam_question_knowledge_columns():
    """真题题目关联知识框架字段"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("exam_questions"):
        return
    cols = [c["name"] for c in insp.get_columns("exam_questions")]
    needed = {
        "knowledge_node_id": "ALTER TABLE exam_questions ADD COLUMN knowledge_node_id VARCHAR(32)",
        "knowledge_tree_key": "ALTER TABLE exam_questions ADD COLUMN knowledge_tree_key VARCHAR(32) DEFAULT ''",
        "knowledge_path": "ALTER TABLE exam_questions ADD COLUMN knowledge_path TEXT DEFAULT ''",
    }
    alters = [sql for col, sql in needed.items() if col not in cols]
    if not alters:
        return
    with engine.begin() as conn:
        for sql in alters:
            conn.execute(text(sql))


def _ensure_corpus_knowledge_columns():
    """语料本挂知识框架字段"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("corpus_items"):
        return
    cols = [c["name"] for c in insp.get_columns("corpus_items")]
    needed = {
        "knowledge_node_id": "ALTER TABLE corpus_items ADD COLUMN knowledge_node_id VARCHAR(32)",
        "knowledge_tree_key": "ALTER TABLE corpus_items ADD COLUMN knowledge_tree_key VARCHAR(64) DEFAULT ''",
        "knowledge_path": "ALTER TABLE corpus_items ADD COLUMN knowledge_path TEXT DEFAULT ''",
    }
    alters = [sql for col, sql in needed.items() if col not in cols]
    if not alters:
        return
    with engine.begin() as conn:
        for sql in alters:
            conn.execute(text(sql))


def _ensure_plan_task_priority_column():
    """兼容旧 plan_tasks 表：补 priority"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("plan_tasks"):
        return
    cols = [c["name"] for c in insp.get_columns("plan_tasks")]
    if "priority" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE plan_tasks ADD COLUMN priority INTEGER DEFAULT 3"))


def _ensure_shenlun_columns():
    """开采本结构化字段 + 规范词分类（兼容已有表）"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if insp.has_table("shenlun_mine_logs"):
        cols = {c["name"] for c in insp.get_columns("shenlun_mine_logs")}
        alters = []
        if "argument_json" not in cols:
            alters.append("ALTER TABLE shenlun_mine_logs ADD COLUMN argument_json TEXT DEFAULT '{}'")
        if "templates_json" not in cols:
            alters.append("ALTER TABLE shenlun_mine_logs ADD COLUMN templates_json TEXT DEFAULT '[]'")
        if "quotes_json" not in cols:
            alters.append("ALTER TABLE shenlun_mine_logs ADD COLUMN quotes_json TEXT DEFAULT '[]'")
        if "verbs_json" not in cols:
            alters.append("ALTER TABLE shenlun_mine_logs ADD COLUMN verbs_json TEXT DEFAULT '[]'")
        if alters:
            with engine.begin() as conn:
                for sql in alters:
                    conn.execute(text(sql))
    if insp.has_table("shenlun_norm_terms"):
        cols = {c["name"] for c in insp.get_columns("shenlun_norm_terms")}
        if "category" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE shenlun_norm_terms ADD COLUMN category VARCHAR(32) DEFAULT '其他'"))
    if insp.has_table("shenlun_term_categories"):
        cols = {c["name"] for c in insp.get_columns("shenlun_term_categories")}
        if "kind" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE shenlun_term_categories ADD COLUMN kind VARCHAR(16) DEFAULT 'term'")
                )
    if insp.has_table("shenlun_teaching_examples"):
        cols = {c["name"] for c in insp.get_columns("shenlun_teaching_examples")}
        if "display_html" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE shenlun_teaching_examples ADD COLUMN display_html TEXT DEFAULT ''"))


def _ensure_wrong_answer_columns():
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("wrong_answers"):
        return
    cols = [c["name"] for c in insp.get_columns("wrong_answers")]
    alters: list[str] = []
    if "user_answer" not in cols:
        alters.append("ALTER TABLE wrong_answers ADD COLUMN user_answer TEXT DEFAULT ''")
    if "review_stage" not in cols:
        alters.append("ALTER TABLE wrong_answers ADD COLUMN review_stage INTEGER DEFAULT 0")
    if "next_review_at" not in cols:
        alters.append("ALTER TABLE wrong_answers ADD COLUMN next_review_at DATETIME")
    with engine.begin() as conn:
        for sql in alters:
            conn.execute(text(sql))
        # 旧错题先全部标为今日到期，进入记忆曲线
        conn.execute(
            text(
                "UPDATE wrong_answers SET next_review_at = CURRENT_TIMESTAMP "
                "WHERE next_review_at IS NULL"
            )
        )


def _ensure_question_columns():
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("questions"):
        return
    cols = [c["name"] for c in insp.get_columns("questions")]
    alters: list[str] = []
    if "status" not in cols:
        alters.append("ALTER TABLE questions ADD COLUMN status VARCHAR(16) DEFAULT 'approved'")
    if "origin" not in cols:
        alters.append("ALTER TABLE questions ADD COLUMN origin VARCHAR(16) DEFAULT 'manual'")
    if not alters:
        return
    with engine.begin() as conn:
        for sql in alters:
            conn.execute(text(sql))


def _ensure_rmrb_article_columns():
    """兼容旧 rmrb_articles：补主题标签与原文链接。"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("rmrb_articles"):
        return
    cols = {c["name"] for c in insp.get_columns("rmrb_articles")}
    with engine.begin() as conn:
        if "tags" not in cols:
            conn.execute(text("ALTER TABLE rmrb_articles ADD COLUMN tags TEXT DEFAULT '[]'"))
        if "source_url" not in cols:
            conn.execute(text("ALTER TABLE rmrb_articles ADD COLUMN source_url VARCHAR(512) DEFAULT ''"))
        if "is_daily" not in cols:
            conn.execute(text("ALTER TABLE rmrb_articles ADD COLUMN is_daily BOOLEAN DEFAULT 0"))


def _ensure_ziliao_formula_plain_column():
    """资料分析公式：补 formula_plain（中文可读式，配合 latex 渲染）"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("ziliao_formulas"):
        return
    cols = [c["name"] for c in insp.get_columns("ziliao_formulas")]
    if "formula_plain" in cols:
        return
    with engine.begin() as conn:
            conn.execute(text("ALTER TABLE ziliao_formulas ADD COLUMN formula_plain TEXT DEFAULT ''"))


def _ensure_content_ops_columns():
    """兼容早期内容发布包：补结构化栏目与学习入口字段。"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("content_publish_packages"):
        return
    cols = {c["name"] for c in insp.get_columns("content_publish_packages")}
    alters = []
    if "slot_values_json" not in cols:
        alters.append("ALTER TABLE content_publish_packages ADD COLUMN slot_values_json TEXT DEFAULT '{}'")
    if "entry_target_json" not in cols:
        alters.append("ALTER TABLE content_publish_packages ADD COLUMN entry_target_json TEXT DEFAULT '{}'")
    if alters:
        with engine.begin() as conn:
            for statement in alters:
                conn.execute(text(statement))


def run_compat_migrations() -> None:
    """执行全部旧库兼容补列（幂等，可重复调用）。"""
    _ensure_article_columns()
    _ensure_app_user_columns()
    _ensure_question_columns()
    _ensure_wrong_answer_columns()
    _ensure_manual_wrong_images_column()
    _ensure_knowledge_node_columns()
    _ensure_exam_question_knowledge_columns()
    _ensure_corpus_knowledge_columns()
    _ensure_plan_task_priority_column()
    _ensure_shenlun_columns()
    _ensure_rmrb_article_columns()
    _ensure_ziliao_formula_plain_column()
    _ensure_content_ops_columns()
