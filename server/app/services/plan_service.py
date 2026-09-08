"""每日学习清单 + 复盘 service

模板从 plan_templates 表读取（后台维护）；支持周一到周日 7 套独立配置。
首次启动 seed 默认模板（周一到周五用工作日模板，周六周日用周末模板）。
生成某天任务时，按当天星期选模板，展开成 PlanTask。

day_type 取值：mon / tue / wed / thu / fri / sat / sun
旧数据 weekday/weekend 会在启动时自动迁移为 mon-fri / sat-sun。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import AppUser, DailyReview, PlanTask, PlanTemplate, gen_id
from app.schemas import (
    DailyReviewOut,
    DailyReviewUpsert,
    DayPlanOut,
    PlanTaskCreate,
    PlanTaskOut,
    PlanTaskUpdate,
    PlanTemplateCreate,
    PlanTemplateOut,
    PlanTemplateUpdate,
)
from app.timezone import now, today as today_str

# 星期 0-6（Python weekday()）-> day_key
WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEKDAY_LABELS = {
    "mon": "周一",
    "tue": "周二",
    "wed": "周三",
    "thu": "周四",
    "fri": "周五",
    "sat": "周六",
    "sun": "周日",
}

# ===== 默认模板（个人学习与成长计划 · 每周执行清单，2026-07-17） =====
# priority: 5=⭐⭐⭐⭐⭐ 必须 / 3=⭐⭐⭐ 选做 / 2=⭐⭐ 弹性
def _t(time_slot: str, subject: str, content: str, minutes: int, priority: int) -> dict:
    return {
        "time_slot": time_slot,
        "subject": subject,
        "content": content,
        "expected_minutes": minutes,
        "priority": priority,
    }


DEFAULT_BY_DAY: dict[str, list[dict]] = {
    "mon": [
        _t("07:00-07:10", "行测", "行测·资料分析 10题｜华图限时，每题≤1分钟，速算估算", 10, 5),
        _t("07:10-07:15", "行测", "错题看解析｜只看不誊抄；反复错的截图周末回看", 5, 5),
        _t("07:15-07:25", "时政", "时政·人民日报精读｜精读复述，摘录规范词", 10, 3),
        _t("12:30-13:00", "时政", "时政·素材阅读｜评论/半月谈任意篇，摘 3 条金句", 30, 2),
        _t("13:00-13:30", "休息", "午睡｜必须躺下闭眼，不看手机", 30, 5),
        _t("18:20-20:00", "行测", "考公·行测弱项专练｜20题限时25分钟+35分钟复盘，错因≤10字", 100, 5),
        _t("20:00-22:00", "申论", "晚间深度补强｜申论小题专项60min + 自由补弱60min", 120, 5),
        _t("22:00-22:30", "休息", "洗漱放松｜不碰学习，准备入睡", 30, 5),
    ],
    "tue": [
        _t("07:00-07:08", "行测", "行测·判断推理 8题｜图形/定义/类比/逻辑各2；图形10秒无思路蒙", 8, 5),
        _t("07:08-07:13", "行测", "错题看解析｜重点图形推理规律总结", 5, 5),
        _t("07:15-07:25", "时政", "时政·人民日报精读｜精读复述，摘录规范词", 10, 3),
        _t("12:30-13:00", "时政", "时政·素材阅读｜评论/半月谈任意篇，摘 3 条金句", 30, 2),
        _t("13:00-13:30", "休息", "午睡｜固定生物钟", 30, 5),
        _t("18:20-20:00", "申论", "考公·申论积累｜人民日报精读+150字概括+200字短论证", 100, 5),
        _t("20:00-22:00", "行测", "晚间深度补强｜行测mini套卷30题+人民日报论证导图", 120, 5),
        _t("22:00-22:30", "休息", "洗漱放松", 30, 5),
    ],
    "wed": [
        _t("07:00-07:10", "行测", "行测·资料分析 10题｜增长率/基期公式即时反应", 10, 5),
        _t("07:10-07:15", "行测", "错题看解析｜默念正确公式", 5, 5),
        _t("07:15-07:25", "时政", "时政·人民日报精读｜精读复述，摘录规范词", 10, 3),
        _t("12:30-13:00", "时政", "时政·素材阅读｜评论/半月谈任意篇，摘 3 条金句", 30, 2),
        _t("13:00-13:30", "休息", "午睡", 30, 5),
        _t("18:20-20:00", "行测", "考公·行测弱项专练｜对照此前正确率", 100, 5),
        _t("20:00-20:15", "行测", "行测·速算热身｜三位数乘除口算，保持手感", 15, 2),
        _t("20:15-22:00", "申论", "晚间深度补强｜申论小题专项 + 自由补弱", 105, 5),
        _t("22:00-22:30", "休息", "洗漱放松", 30, 5),
    ],
    "thu": [
        _t("07:00-07:08", "行测", "行测·判断推理 8题｜重点削弱加强", 8, 5),
        _t("07:08-07:13", "行测", "错题看解析｜理清前提→结论→削弱/加强点", 5, 5),
        _t("07:15-07:25", "时政", "时政·人民日报精读｜精读复述，摘录规范词", 10, 3),
        _t("12:30-13:00", "时政", "时政·素材阅读｜评论/半月谈任意篇，摘 3 条金句", 30, 2),
        _t("13:00-13:30", "休息", "午睡", 30, 5),
        _t("18:20-20:00", "申论", "考公·申论积累｜精读+概括+模仿写作", 100, 5),
        _t("20:00-22:00", "行测", "晚间深度补强｜行测mini套卷+人民日报思维导图", 120, 5),
        _t("22:00-22:30", "休息", "洗漱放松", 30, 5),
    ],
    "fri": [
        _t("07:00-07:10", "行测", "行测·资料分析 10题｜关注本周正确率变化", 10, 5),
        _t("07:10-07:15", "行测", "错题看解析｜正确率稳定可缩至3分钟", 5, 5),
        _t("07:15-07:25", "时政", "时政·人民日报精读｜精读复述，摘录规范词", 10, 3),
        _t("12:30-13:00", "时政", "时政·素材阅读｜评论/半月谈任意篇，摘 3 条金句", 30, 2),
        _t("13:00-13:30", "休息", "午睡", 30, 5),
        _t("18:20-20:00", "行测", "考公·行测弱项专练｜汇总本周错因成易错清单", 100, 5),
        _t("20:00-22:00", "申论", "晚间深度补强｜申论小题/自由补弱/整理周末复习", 120, 5),
        _t("22:00-22:30", "休息", "洗漱放松", 30, 5),
    ],
    "sat": [
        _t("07:00-07:08", "行测", "行测·言语理解 10题｜关注转折词后内容", 8, 5),
        _t("07:08-07:13", "行测", "错题看解析｜每道错题在原文找依据", 5, 5),
        _t("07:15-07:25", "时政", "时政·人民日报精读｜精读复述，摘录规范词", 10, 3),
        _t("09:00-11:00", "行测", "行测全真模考｜严格110分钟+涂卡，完全模拟考场", 110, 5),
        _t("11:00-12:00", "行测", "模考初步复盘｜只看错题不看解析，按模块统计", 60, 5),
        _t("13:00起", "休息", "完全自由时间｜出去玩/见朋友/看电影，不许有负罪感", 0, 2),
    ],
    "sun": [
        _t("07:00-07:05", "行测", "行测·数量关系 5题｜只挑最简题型，练习取舍", 5, 5),
        _t("07:05-07:10", "行测", "错题看解析｜公式默念三遍", 5, 5),
        _t("07:15-07:25", "时政", "时政·人民日报精读｜精读复述，摘录规范词", 10, 3),
        _t("09:00-09:40", "申论", "申论范文拆解｜划论点+规范词/论证方法+口述主旨录音", 40, 5),
        _t("09:40-09:50", "申论", "申论·规范词衔接复述｜用规范词复述范文主旨并录音", 10, 3),
        _t("10:00-11:00", "行测", "行测模考深度复盘｜逐题看解析，记录高频错因", 60, 5),
        _t("14:00-14:20", "申论", "申论·范文精听｜关字幕听 2 遍，开字幕跟读 2 遍", 20, 3),
        _t("14:20-15:00", "申论", "申论·范文模仿 3 句｜模仿论证语气，录音到满意", 40, 3),
        _t("15:00-15:30", "行测", "行测·数量关系专项｜公式默写 + 5 题限时", 30, 2),
        _t("16:00-16:20", "休息", "自由时间｜散步/听播客，恢复精力", 20, 2),
        _t("20:00-20:30", "复盘", "每周复盘｜完成率统计→三问反思→清理归档→写下微调", 30, 5),
    ],
}

# 兼容旧引用：工作日/周末取 mon / sat 作为代表
DEFAULT_WEEKDAY: list[dict] = DEFAULT_BY_DAY["mon"]
DEFAULT_WEEKEND: list[dict] = DEFAULT_BY_DAY["sat"]


def _today_str() -> str:
    return today_str()


def _weekday_key(date_str: str) -> str:
    """YYYY-MM-DD -> mon/tue/.../sun"""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return "mon"
    return WEEKDAY_KEYS[d.weekday()]


def _is_weekend(date_str: str) -> bool:
    return _weekday_key(date_str) in ("sat", "sun")


def _insert_default_templates(db: Session) -> int:
    """按 DEFAULT_BY_DAY 写入全部模板，返回条数"""
    count = 0
    for day_key in WEEKDAY_KEYS:
        for idx, item in enumerate(DEFAULT_BY_DAY.get(day_key, [])):
            db.add(
                PlanTemplate(
                    id=gen_id("plt"),
                    day_type=day_key,
                    time_slot=item["time_slot"],
                    subject=item["subject"],
                    content=item["content"],
                    priority=item.get("priority", 3),
                    expected_minutes=item["expected_minutes"],
                    sort_order=idx,
                    is_active=True,
                )
            )
            count += 1
    return count


def seed_default_templates(db: Session) -> None:
    """首次启动时把默认模板写入 plan_templates 表

    周一到周日各一套（DEFAULT_BY_DAY）。
    若已有 7 套 day_key 数据则跳过；若有老 weekday/weekend 数据则先迁移。
    """
    _migrate_legacy_day_type(db)

    # 已经有 mon 等新 key 数据，不重复 seed
    has_new = db.query(PlanTemplate).filter(PlanTemplate.day_type.in_(WEEKDAY_KEYS)).first()
    if has_new:
        return

    _insert_default_templates(db)
    db.commit()


def _calendar_week_range(anchor: datetime | None = None) -> tuple[str, str]:
    """以 anchor（默认今天）所在自然周 Mon-Sun 的起止日期 YYYY-MM-DD"""
    d = (anchor or now()).date()
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


def replace_default_templates(
    db: Session,
    *,
    reset_week_tasks: bool = True,
) -> dict:
    """用内置 DEFAULT_BY_DAY 覆盖全部计划模板

    reset_week_tasks=True 时：删除本自然周（周一~周日）所有用户的 plan_tasks，
    下次打开「今日/本周」会按新模板重新生成。
    """
    _migrate_legacy_day_type(db)
    deleted_tpl = db.query(PlanTemplate).delete()
    inserted = _insert_default_templates(db)

    deleted_tasks = 0
    week_start, week_end = _calendar_week_range()
    if reset_week_tasks:
        deleted_tasks = (
            db.query(PlanTask)
            .filter(PlanTask.plan_date >= week_start, PlanTask.plan_date <= week_end)
            .delete(synchronize_session=False)
        )
    db.commit()
    return {
        "ok": True,
        "deletedTemplates": deleted_tpl,
        "insertedTemplates": inserted,
        "deletedWeekTasks": deleted_tasks,
        "weekStart": week_start,
        "weekEnd": week_end,
    }


def _migrate_legacy_day_type(db: Session) -> None:
    """把老 weekday/weekend 数据迁移成 mon-fri/sat-sun

    weekday -> 复制到 mon/tue/wed/thu/fri（每条复制5份）
    weekend -> 复制到 sat/sun（每条复制2份）
    迁移后删除老的 weekday/weekend 行。
    """
    legacy = db.query(PlanTemplate).filter(PlanTemplate.day_type.in_(["weekday", "weekend"])).all()
    if not legacy:
        return

    # 检查是否已有新 key 数据（避免重复迁移）
    has_new = db.query(PlanTemplate).filter(PlanTemplate.day_type.in_(WEEKDAY_KEYS)).first()
    if has_new:
        # 仅删老数据
        for row in legacy:
            db.delete(row)
        db.commit()
        return

    for row in legacy:
        if row.day_type == "weekday":
            target_keys = ["mon", "tue", "wed", "thu", "fri"]
        else:
            target_keys = ["sat", "sun"]
        for key in target_keys:
            db.add(
                PlanTemplate(
                    id=gen_id("plt"),
                    day_type=key,
                    time_slot=row.time_slot,
                    subject=row.subject,
                    content=row.content,
                    priority=row.priority,
                    expected_minutes=row.expected_minutes,
                    sort_order=row.sort_order,
                    is_active=row.is_active,
                )
            )
    for row in legacy:
        db.delete(row)
    db.commit()


# ===== 模板 CRUD =====


def _template_to_out(t: PlanTemplate) -> PlanTemplateOut:
    return PlanTemplateOut(
        id=t.id,
        dayType=t.day_type,
        timeSlot=t.time_slot or "",
        subject=t.subject or "",
        content=t.content,
        priority=t.priority,
        expectedMinutes=t.expected_minutes,
        sortOrder=t.sort_order,
        isActive=bool(t.is_active),
    )


def list_templates(db: Session, day_type: str | None = None) -> list[PlanTemplateOut]:
    q = db.query(PlanTemplate)
    if day_type:
        q = q.filter(PlanTemplate.day_type == day_type)
    rows = q.order_by(PlanTemplate.day_type, PlanTemplate.sort_order, PlanTemplate.id).all()
    return [_template_to_out(t) for t in rows]


def sync_templates_to_pending_tasks(
    db: Session,
    day_type: str | None = None,
    *,
    from_date: str | None = None,
    horizon_days: int = 14,
) -> dict:
    """把模板变更同步到「今天起、尚未开始」的用户日清单。

    规则：对 [from_date, +horizon] 内、星期匹配 day_type（None=全部）的日期，
    若该用户当天任务全部仍为 pending（无任何 done），则删除后下次打开会按新模板重生。
    已有完成记录的日期跳过，避免冲掉进度。
    """
    start = datetime.strptime(from_date or _today_str(), "%Y-%m-%d").date()
    end = start + timedelta(days=max(0, horizon_days))
    target_days = set(WEEKDAY_KEYS) if not day_type else {day_type}
    if day_type and day_type not in WEEKDAY_KEYS:
        raise ValueError("day_type 必须是 mon~sun")

    deleted = 0
    skipped_done = 0
    touched_dates: set[str] = set()
    d = start
    while d <= end:
        key = WEEKDAY_KEYS[d.weekday()]
        if key in target_days:
            date_str = d.strftime("%Y-%m-%d")
            # 按用户分组：有 done 则整日跳过
            rows = (
                db.query(PlanTask)
                .filter(PlanTask.plan_date == date_str)
                .all()
            )
            by_user: dict[str, list[PlanTask]] = {}
            for t in rows:
                by_user.setdefault(t.user_id, []).append(t)
            for _uid, tasks in by_user.items():
                if any(t.status == "done" for t in tasks):
                    skipped_done += 1
                    continue
                for t in tasks:
                    db.delete(t)
                    deleted += 1
                touched_dates.add(date_str)
        d += timedelta(days=1)
    db.commit()
    return {
        "ok": True,
        "dayType": day_type or "all",
        "fromDate": start.strftime("%Y-%m-%d"),
        "toDate": end.strftime("%Y-%m-%d"),
        "deletedTasks": deleted,
        "skippedDaysWithDone": skipped_done,
        "datesTouched": sorted(touched_dates),
    }


def create_template(db: Session, body: PlanTemplateCreate, *, sync_pending: bool = True) -> PlanTemplateOut:
    max_order = (
        db.query(PlanTemplate)
        .filter(PlanTemplate.day_type == body.dayType)
        .count()
    )
    t = PlanTemplate(
        id=gen_id("plt"),
        day_type=body.dayType,
        time_slot=body.timeSlot,
        subject=body.subject,
        content=body.content,
        priority=body.priority,
        expected_minutes=body.expectedMinutes,
        sort_order=body.sortOrder if body.sortOrder else max_order,
        is_active=True,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    if sync_pending:
        sync_templates_to_pending_tasks(db, body.dayType)
    return _template_to_out(t)


def update_template(
    db: Session, template_id: str, body: PlanTemplateUpdate, *, sync_pending: bool = True
) -> PlanTemplateOut | None:
    t = db.get(PlanTemplate, template_id)
    if not t:
        return None
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        key = {
            "dayType": "day_type",
            "timeSlot": "time_slot",
            "expectedMinutes": "expected_minutes",
            "sortOrder": "sort_order",
            "isActive": "is_active",
        }.get(k, k)
        setattr(t, key, v)
    day_key = t.day_type
    db.commit()
    db.refresh(t)
    if sync_pending:
        sync_templates_to_pending_tasks(db, day_key)
    return _template_to_out(t)


def delete_template(db: Session, template_id: str, *, sync_pending: bool = True) -> bool:
    t = db.get(PlanTemplate, template_id)
    if not t:
        return False
    day_key = t.day_type
    db.delete(t)
    db.commit()
    if sync_pending:
        sync_templates_to_pending_tasks(db, day_key)
    return True


def copy_day_templates(
    db: Session,
    *,
    from_day: str,
    to_day: str,
    replace: bool = True,
) -> dict:
    """将某一天的计划模板复制到另一天。

    replace=True 时先清空目标日已有模板再写入。
    """
    if from_day not in WEEKDAY_KEYS or to_day not in WEEKDAY_KEYS:
        raise ValueError("from_day / to_day 必须是 mon~sun")
    if from_day == to_day:
        raise ValueError("源日与目标日不能相同")

    source = (
        db.query(PlanTemplate)
        .filter(PlanTemplate.day_type == from_day)
        .order_by(PlanTemplate.sort_order, PlanTemplate.id)
        .all()
    )
    if not source:
        raise ValueError("源日没有可复制的计划")

    deleted = 0
    if replace:
        old = db.query(PlanTemplate).filter(PlanTemplate.day_type == to_day).all()
        deleted = len(old)
        for row in old:
            db.delete(row)
        db.flush()

    base_order = 0
    if not replace:
        base_order = db.query(PlanTemplate).filter(PlanTemplate.day_type == to_day).count()

    inserted = 0
    for i, src in enumerate(source):
        db.add(
            PlanTemplate(
                id=gen_id("plt"),
                day_type=to_day,
                time_slot=src.time_slot or "",
                subject=src.subject or "",
                content=src.content,
                priority=src.priority,
                expected_minutes=src.expected_minutes,
                sort_order=base_order + i,
                is_active=bool(src.is_active),
            )
        )
        inserted += 1
    db.commit()
    sync = sync_templates_to_pending_tasks(db, to_day)
    return {
        "ok": True,
        "fromDay": from_day,
        "toDay": to_day,
        "deleted": deleted,
        "inserted": inserted,
        "syncedPending": sync,
    }


# ===== 每日任务 =====


def _task_to_out(t: PlanTask) -> PlanTaskOut:
    return PlanTaskOut(
        id=t.id,
        planDate=t.plan_date,
        timeSlot=t.time_slot,
        subject=t.subject,
        content=t.content,
        priority=t.priority or 3,
        expectedMinutes=t.expected_minutes,
        actualMinutes=t.actual_minutes,
        status=t.status,
        sortOrder=t.sort_order,
        note=t.note or "",
    )


def _ensure_day_tasks(db: Session, user: AppUser, date_str: str) -> list[PlanTask]:
    """确保某天的任务已生成（首次访问时按模板生成）"""
    existing = (
        db.query(PlanTask)
        .filter(PlanTask.user_id == user.id, PlanTask.plan_date == date_str)
        .order_by(PlanTask.sort_order, PlanTask.id)
        .all()
    )
    if existing:
        return existing

    day_key = _weekday_key(date_str)
    templates = (
        db.query(PlanTemplate)
        .filter(PlanTemplate.day_type == day_key, PlanTemplate.is_active.is_(True))
        .order_by(PlanTemplate.sort_order, PlanTemplate.id)
        .all()
    )
    # 如果该星期没模板（管理员删空了），尝试用同类型 fallback
    if not templates:
        # 周一到周五互相 fallback，周六周日互相 fallback
        fallback_keys = ["mon", "tue", "wed", "thu", "fri"] if day_key in ("mon", "tue", "wed", "thu", "fri") else ["sat", "sun"]
        for k in fallback_keys:
            if k == day_key:
                continue
            templates = (
                db.query(PlanTemplate)
                .filter(PlanTemplate.day_type == k, PlanTemplate.is_active.is_(True))
                .order_by(PlanTemplate.sort_order, PlanTemplate.id)
                .all()
            )
            if templates:
                break
    # 实在没模板，用内置默认
    if not templates:
        defaults = DEFAULT_BY_DAY.get(day_key) or DEFAULT_WEEKDAY
        for idx, item in enumerate(defaults):
            db.add(
                PlanTask(
                    id=gen_id("pt"),
                    user_id=user.id,
                    plan_date=date_str,
                    time_slot=item["time_slot"],
                    subject=item["subject"],
                    content=item["content"],
                    priority=item.get("priority", 3),
                    expected_minutes=item["expected_minutes"],
                    sort_order=idx,
                )
            )
    else:
        for idx, tpl in enumerate(templates):
            db.add(
                PlanTask(
                    id=gen_id("pt"),
                    user_id=user.id,
                    plan_date=date_str,
                    time_slot=tpl.time_slot,
                    subject=tpl.subject,
                    content=tpl.content,
                    priority=tpl.priority,
                    expected_minutes=tpl.expected_minutes,
                    sort_order=idx,
                )
            )
    db.commit()
    return (
        db.query(PlanTask)
        .filter(PlanTask.user_id == user.id, PlanTask.plan_date == date_str)
        .order_by(PlanTask.sort_order, PlanTask.id)
        .all()
    )


def _get_review(db: Session, user_id: str, date_str: str) -> DailyReview | None:
    return (
        db.query(DailyReview)
        .filter(DailyReview.user_id == user_id, DailyReview.review_date == date_str)
        .first()
    )


def get_day_plan(db: Session, user: AppUser, date_str: str) -> DayPlanOut:
    tasks = _ensure_day_tasks(db, user, date_str)
    total = len(tasks)
    done = sum(1 for t in tasks if t.status == "done")
    completion = int(done / total * 100) if total else 0
    expected = sum(t.expected_minutes for t in tasks)
    actual = sum(t.actual_minutes for t in tasks)
    review = _get_review(db, user.id, date_str)
    return DayPlanOut(
        date=date_str,
        isWeekend=_is_weekend(date_str),
        tasks=[_task_to_out(t) for t in tasks],
        completion=completion,
        doneCount=done,
        totalCount=total,
        expectedMinutes=expected,
        actualMinutes=actual,
        review=DailyReviewOut(
            reviewDate=review.review_date,
            completion=review.completion,
            totalMinutes=review.total_minutes,
            weakPoint=review.weak_point or "",
            tomorrowFocus=review.tomorrow_focus or "",
            mood=review.mood or "",
            note=review.note or "",
        )
        if review
        else None,
    )


def update_task(
    db: Session, user: AppUser, task_id: str, body: PlanTaskUpdate
) -> PlanTaskOut | None:
    t = db.get(PlanTask, task_id)
    if not t or t.user_id != user.id:
        return None
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        key = {"actualMinutes": "actual_minutes"}.get(k, k)
        setattr(t, key, v)
    db.commit()
    db.refresh(t)
    return _task_to_out(t)


def add_task(db: Session, user: AppUser, body: PlanTaskCreate) -> PlanTaskOut:
    max_order = (
        db.query(PlanTask)
        .filter(PlanTask.user_id == user.id, PlanTask.plan_date == body.planDate)
        .count()
    )
    t = PlanTask(
        id=gen_id("pt"),
        user_id=user.id,
        plan_date=body.planDate,
        time_slot=body.timeSlot,
        subject=body.subject,
        content=body.content,
        priority=body.priority,
        expected_minutes=body.expectedMinutes,
        sort_order=max_order,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _task_to_out(t)


def delete_task(db: Session, user: AppUser, task_id: str) -> bool:
    t = db.get(PlanTask, task_id)
    if not t or t.user_id != user.id:
        return False
    db.delete(t)
    db.commit()
    return True


def upsert_review(db: Session, user: AppUser, body: DailyReviewUpsert) -> DailyReviewOut:
    review_date = (body.reviewDate or "").strip()
    if not review_date:
        raise ValueError("请填写复盘日期")
    r = _get_review(db, user.id, review_date)
    data = body.model_dump(exclude_unset=True)
    if r:
        for k, v in data.items():
            key = {
                "reviewDate": "review_date",
                "totalMinutes": "total_minutes",
                "weakPoint": "weak_point",
                "tomorrowFocus": "tomorrow_focus",
            }.get(k, k)
            setattr(r, key, v)
    else:
        r = DailyReview(
            id=gen_id("dr"),
            user_id=user.id,
            review_date=review_date,
            completion=data.get("completion", 0),
            total_minutes=data.get("totalMinutes", 0),
            weak_point=data.get("weakPoint", ""),
            tomorrow_focus=data.get("tomorrowFocus", ""),
            mood=data.get("mood", ""),
            note=data.get("note", ""),
        )
        db.add(r)
    db.commit()
    db.refresh(r)
    return DailyReviewOut(
        reviewDate=r.review_date,
        completion=r.completion,
        totalMinutes=r.total_minutes,
        weakPoint=r.weak_point or "",
        tomorrowFocus=r.tomorrow_focus or "",
        mood=r.mood or "",
        note=r.note or "",
    )


def list_recent_days(db: Session, user: AppUser, days: int = 7) -> list[DayPlanOut]:
    """最近 N 天的概览（用于周计划页）"""
    today = now().date()
    out: list[DayPlanOut] = []
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        date_str = d.strftime("%Y-%m-%d")
        existing = (
            db.query(PlanTask)
            .filter(PlanTask.user_id == user.id, PlanTask.plan_date == date_str)
            .all()
        )
        if not existing and d > today:
            out.append(
                DayPlanOut(
                    date=date_str,
                    isWeekend=_is_weekend(date_str),
                    tasks=[],
                    completion=0,
                    doneCount=0,
                    totalCount=0,
                    expectedMinutes=0,
                    actualMinutes=0,
                    review=None,
                )
            )
            continue
        out.append(get_day_plan(db, user, date_str))
    return out
