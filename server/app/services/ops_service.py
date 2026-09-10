"""内容生产流程：种子目录、手动执行步骤。第一期不跑 cron、不自动导入学员内容。"""
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.ops import OpsPipeline, OpsPipelineStep, OpsRun, OpsRunStep, OpsStep
from app.timezone import today as today_str, now as now_bj

REPO_ROOT = Path(__file__).resolve().parents[3]
OPS_ROOT = REPO_ROOT / "ops"

_STEPS: list[dict] = [
    {
        "key": "shenlun.crawl",
        "name": "抓取人民日报评论",
        "product": "shenlun",
        "step_type": "script",
        "command": "python3 -c \"print('抓取步骤探活，生产请改为 工作流/抓取.py --date')\"",
        "cwd_rel": "shenlun",
        "sort_hint": 10,
        "notes": "现网：工作流/抓取.py --date <日期>。第一期点跑为 --help 探活。",
    },
    {
        "key": "shenlun.screen",
        "name": "五维筛选（人工/模型）",
        "product": "shenlun",
        "step_type": "manual",
        "command": "",
        "cwd_rel": "shenlun",
        "sort_hint": 20,
        "notes": "写 物料/<日期>/筛选/候选清单.md。后台点跑仅记完成，不调模型。",
    },
    {
        "key": "shenlun.recommend",
        "name": "选文推荐",
        "product": "shenlun",
        "step_type": "manual",
        "command": "",
        "cwd_rel": "shenlun",
        "sort_hint": 30,
        "notes": "写确认结果.md，等待运营在后台点确认。",
    },
    {
        "key": "shenlun.wait_confirm",
        "name": "待后台确认选文",
        "product": "shenlun",
        "step_type": "wait_confirm",
        "command": "",
        "cwd_rel": "shenlun",
        "sort_hint": 40,
        "notes": "流程停在此步，点「确认继续」后再跑出品流程。",
    },
    {
        "key": "shenlun.mkdir",
        "name": "建文章目录",
        "product": "shenlun",
        "step_type": "manual",
        "command": "",
        "cwd_rel": "shenlun",
        "sort_hint": 50,
        "notes": "物料/<日期>/<标题>/{原文,解剖,公众号}",
    },
    {
        "key": "shenlun.anatomy_md",
        "name": "三刀解剖 MD",
        "product": "shenlun",
        "step_type": "manual",
        "command": "",
        "cwd_rel": "shenlun",
        "sort_hint": 60,
        "notes": "模板 物料模板/三刀解剖模版_v2.18.md。需模型，第一期只记账。",
    },
    {
        "key": "shenlun.origin_html",
        "name": "原文 HTML 生成",
        "product": "shenlun",
        "step_type": "script",
        "command": "python3 工作流/原文HTML生成.py --help",
        "cwd_rel": "shenlun",
        "sort_hint": 70,
        "notes": "生产命令：python3 工作流/原文HTML生成.py --date <日期> --into-articles",
    },
    {
        "key": "shenlun.anatomy_html",
        "name": "解剖 HTML 归位",
        "product": "shenlun",
        "step_type": "manual",
        "command": "",
        "cwd_rel": "shenlun",
        "sort_hint": 80,
        "notes": "公众号 A 套复制为 解剖/<标题>_三刀解剖.html",
    },
    {
        "key": "shenlun.lint",
        "name": "规则自检",
        "product": "shenlun",
        "step_type": "script",
        "command": "python3 工作流/规则自检.py --help",
        "cwd_rel": "shenlun",
        "sort_hint": 90,
        "notes": "生产：python3 工作流/规则自检.py 物料/<日期>",
    },
    {
        "key": "theory.structure_html",
        "name": "结构化 HTML",
        "product": "theory",
        "step_type": "script",
        "command": "python3 工作流/gen_structure_html.py --help",
        "cwd_rel": "theory",
        "sort_hint": 10,
        "notes": "生产需 --md --title --source --date --link",
    },
    {
        "key": "theory.questions_json",
        "name": "出题 JSON",
        "product": "theory",
        "step_type": "manual",
        "command": "",
        "cwd_rel": "theory",
        "sort_hint": 20,
        "notes": "人工/模型出 20 题 JSON，不自动跑。",
    },
    {
        "key": "theory.paper_md",
        "name": "套题导入 MD",
        "product": "theory",
        "step_type": "script",
        "command": "python3 工作流/gen_paper_md.py --help",
        "cwd_rel": "theory",
        "sort_hint": 30,
        "notes": "生产：--date --title",
    },
]

_PIPELINES: list[dict] = [
    {
        "key": "shenlun.daily_screen",
        "name": "申论·每日筛选推荐",
        "product": "shenlun",
        "cron": "40 6 * * 1-5",
        "notes": "对应现网定时段。cron 已保存，第一期不会自动触发。",
        "steps": ["shenlun.crawl", "shenlun.screen", "shenlun.recommend", "shenlun.wait_confirm"],
    },
    {
        "key": "shenlun.after_confirm",
        "name": "申论·确认后出品",
        "product": "shenlun",
        "cron": "",
        "notes": "确认选文后手动跑。产物落磁盘，不自动导入时评后台。",
        "steps": [
            "shenlun.mkdir",
            "shenlun.anatomy_md",
            "shenlun.origin_html",
            "shenlun.anatomy_html",
            "shenlun.lint",
        ],
    },
    {
        "key": "theory.daily",
        "name": "理论·每日出品",
        "product": "theory",
        "cron": "",
        "notes": "结构化 HTML 等。不自动导入文章管理。",
        "steps": ["theory.structure_html", "theory.questions_json", "theory.paper_md"],
    },
]


def material_root() -> Path:
    settings = get_settings()
    raw = (settings.ops_material_root or "").strip()
    path = Path(raw) if raw else Path("data/ops-materials")
    if not path.is_absolute():
        path = (REPO_ROOT / "server" / path).resolve() if str(path).startswith("data/") else (Path.cwd() / path).resolve()
    return path


def seed_ops_catalog(db: Session) -> None:
    by_key: dict[str, OpsStep] = {}
    for item in _STEPS:
        row = db.query(OpsStep).filter(OpsStep.key == item["key"]).one_or_none()
        if not row:
            row = OpsStep(
                key=item["key"],
                name=item["name"],
                product=item["product"],
                step_type=item["step_type"],
                command=item["command"],
                cwd_rel=item["cwd_rel"],
                enabled=True,
                sort_hint=item["sort_hint"],
                notes=item["notes"],
            )
            db.add(row)
            db.flush()
        by_key[item["key"]] = row
    for pipe in _PIPELINES:
        prow = db.query(OpsPipeline).filter(OpsPipeline.key == pipe["key"]).one_or_none()
        if not prow:
            prow = OpsPipeline(
                key=pipe["key"],
                name=pipe["name"],
                product=pipe["product"],
                enabled=True,
                cron=pipe["cron"],
                timezone="Asia/Shanghai",
                notes=pipe["notes"],
            )
            db.add(prow)
            db.flush()
        existing = {l.step_id: l for l in db.query(OpsPipelineStep).filter(OpsPipelineStep.pipeline_id == prow.id)}
        for i, step_key in enumerate(pipe["steps"]):
            step = by_key[step_key]
            link = existing.pop(step.id, None)
            if not link:
                link = OpsPipelineStep(pipeline_id=prow.id, step_id=step.id, enabled=True)
                db.add(link)
            link.sort_order = i
        db.flush()
    db.commit()


def _step_out(s: OpsStep) -> dict:
    return {
        "id": s.id,
        "key": s.key,
        "name": s.name,
        "product": s.product,
        "stepType": s.step_type,
        "command": s.command,
        "cwdRel": s.cwd_rel,
        "enabled": bool(s.enabled),
        "sortHint": s.sort_hint,
        "notes": s.notes,
    }


def _pipeline_out(db: Session, p: OpsPipeline) -> dict:
    links = (
        db.query(OpsPipelineStep)
        .filter(OpsPipelineStep.pipeline_id == p.id)
        .order_by(OpsPipelineStep.sort_order)
        .all()
    )
    steps = []
    for link in links:
        step = db.get(OpsStep, link.step_id)
        if not step:
            continue
        item = _step_out(step)
        item["inPipelineEnabled"] = bool(link.enabled)
        item["sortOrder"] = link.sort_order
        item["linkId"] = link.id
        steps.append(item)
    return {
        "id": p.id,
        "key": p.key,
        "name": p.name,
        "product": p.product,
        "enabled": bool(p.enabled),
        "cron": p.cron or "",
        "timezone": p.timezone,
        "notes": p.notes,
        "cronNote": "第一期只保存 cron，不会按点自动执行。",
        "steps": steps,
    }


def list_steps(db: Session) -> list[dict]:
    rows = db.query(OpsStep).order_by(OpsStep.product, OpsStep.sort_hint, OpsStep.key).all()
    return [_step_out(s) for s in rows]


def list_pipelines(db: Session) -> list[dict]:
    rows = db.query(OpsPipeline).order_by(OpsPipeline.product, OpsPipeline.key).all()
    return [_pipeline_out(db, p) for p in rows]


def update_step(db: Session, step_id: str, data: dict) -> dict | None:
    row = db.get(OpsStep, step_id)
    if not row:
        return None
    if "enabled" in data and data["enabled"] is not None:
        row.enabled = bool(data["enabled"])
    if "command" in data and data["command"] is not None:
        row.command = str(data["command"])
    if "notes" in data and data["notes"] is not None:
        row.notes = str(data["notes"])
    if "name" in data and data["name"]:
        row.name = str(data["name"])
    db.commit()
    db.refresh(row)
    return _step_out(row)


def update_pipeline(db: Session, pipeline_id: str, data: dict) -> dict | None:
    row = db.get(OpsPipeline, pipeline_id)
    if not row:
        return None
    if "enabled" in data and data["enabled"] is not None:
        row.enabled = bool(data["enabled"])
    if "cron" in data and data["cron"] is not None:
        row.cron = str(data["cron"])
    if "notes" in data and data["notes"] is not None:
        row.notes = str(data["notes"])
    if "name" in data and data["name"]:
        row.name = str(data["name"])
    links = data.get("steps")
    if isinstance(links, list):
        for item in links:
            link = db.get(OpsPipelineStep, item.get("linkId") or "")
            if not link or link.pipeline_id != row.id:
                continue
            if "enabled" in item:
                link.enabled = bool(item["enabled"])
            if "sortOrder" in item:
                link.sort_order = int(item["sortOrder"])
    db.commit()
    db.refresh(row)
    return _pipeline_out(db, row)


def _env() -> dict[str, str]:
    env = os.environ.copy()
    root = material_root()
    root.mkdir(parents=True, exist_ok=True)
    env["OPS_MATERIAL_ROOT"] = str(root)
    return env


def run_step(db: Session, step: OpsStep) -> tuple[int, str]:
    if not step.enabled:
        return 1, "步骤已关闭"
    if step.step_type == "wait_confirm":
        return 0, "wait_confirm"
    if step.step_type == "manual" or not (step.command or "").strip():
        return 0, "manual：已记完成，未执行命令"
    cwd = OPS_ROOT / (step.cwd_rel or "")
    if not cwd.is_dir():
        return 1, f"工作目录不存在: {cwd}"
    cmd = step.command.replace("{date}", today_str())
    try:
        proc = subprocess.run(
            shlex.split(cmd),
            cwd=str(cwd),
            env=_env(),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return 1, "执行超时（120s）"
    except OSError as e:
        return 1, str(e)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out[-8000:]


def start_pipeline_run(db: Session, pipeline_id: str) -> dict:
    pipe = db.get(OpsPipeline, pipeline_id)
    if not pipe:
        raise ValueError("流程不存在")
    if not pipe.enabled:
        raise ValueError("流程已关闭")
    busy = (
        db.query(OpsRun)
        .filter(OpsRun.pipeline_id == pipeline_id, OpsRun.status.in_(["running", "waiting_confirm"]))
        .first()
    )
    if busy:
        raise ValueError("该流程已有未完成的运行")
    run = OpsRun(pipeline_id=pipe.id, status="running", current_index=0, log="")
    db.add(run)
    db.commit()
    db.refresh(run)
    return continue_run(db, run.id, from_start=True)


def continue_run(db: Session, run_id: str, *, from_start: bool = False, skip_confirm: bool = False) -> dict:
    run = db.get(OpsRun, run_id)
    if not run:
        raise ValueError("运行不存在")
    pipe = db.get(OpsPipeline, run.pipeline_id)
    links = (
        db.query(OpsPipelineStep)
        .filter(OpsPipelineStep.pipeline_id == run.pipeline_id, OpsPipelineStep.enabled.is_(True))
        .order_by(OpsPipelineStep.sort_order)
        .all()
    )
    start = 0 if from_start else run.current_index
    for i in range(start, len(links)):
        link = links[i]
        step = db.get(OpsStep, link.step_id)
        if not step or not step.enabled:
            continue
        run.current_index = i
        rec = OpsRunStep(run_id=run.id, step_id=step.id, step_name=step.name, status="running")
        db.add(rec)
        db.commit()
        if step.step_type == "wait_confirm" and not skip_confirm:
            rec.status = "waiting_confirm"
            rec.output = "等待后台确认"
            rec.finished_at = now_bj()
            run.status = "waiting_confirm"
            run.log = (run.log or "") + f"\n[{step.name}] waiting_confirm"
            db.commit()
            return _run_out(db, run)
        code, output = run_step(db, step)
        rec.exit_code = code
        rec.output = output
        rec.finished_at = now_bj()
        rec.status = "done" if code == 0 else "failed"
        run.log = (run.log or "") + f"\n[{step.name}] exit={code}\n{output[-500:]}"
        db.commit()
        if code != 0:
            run.status = "failed"
            run.finished_at = now_bj()
            db.commit()
            return _run_out(db, run)
        skip_confirm = False
    run.status = "done"
    run.finished_at = now_bj()
    run.current_index = max(len(links) - 1, 0)
    db.commit()
    return _run_out(db, run)


def confirm_run(db: Session, run_id: str) -> dict:
    run = db.get(OpsRun, run_id)
    if not run or run.status != "waiting_confirm":
        raise ValueError("没有待确认的运行")
    run.current_index = run.current_index + 1
    run.status = "running"
    db.commit()
    return continue_run(db, run.id, from_start=False, skip_confirm=True)


def run_one_step(db: Session, step_id: str) -> dict:
    step = db.get(OpsStep, step_id)
    if not step:
        raise ValueError("步骤不存在")
    code, output = run_step(db, step)
    return {"stepId": step.id, "name": step.name, "exitCode": code, "output": output, "ok": code == 0}


def list_runs(db: Session, pipeline_id: str | None = None, limit: int = 20) -> list[dict]:
    q = db.query(OpsRun).order_by(OpsRun.started_at.desc())
    if pipeline_id:
        q = q.filter(OpsRun.pipeline_id == pipeline_id)
    rows = q.limit(limit).all()
    return [_run_out(db, r) for r in rows]


def _run_out(db: Session, run: OpsRun) -> dict:
    steps = db.query(OpsRunStep).filter(OpsRunStep.run_id == run.id).order_by(OpsRunStep.started_at).all()
    pipe = db.get(OpsPipeline, run.pipeline_id)
    return {
        "id": run.id,
        "pipelineId": run.pipeline_id,
        "pipelineName": pipe.name if pipe else "",
        "status": run.status,
        "currentIndex": run.current_index,
        "log": run.log or "",
        "startedAt": run.started_at.isoformat() if run.started_at else "",
        "finishedAt": run.finished_at.isoformat() if run.finished_at else "",
        "materialRoot": str(material_root()),
        "steps": [
            {
                "id": s.id,
                "stepName": s.step_name,
                "status": s.status,
                "exitCode": s.exit_code,
                "output": s.output[-2000:] if s.output else "",
            }
            for s in steps
        ],
    }
