from pydantic import BaseModel

from app.api.admin._deps import *
from app.services.ops_service import (
    confirm_run,
    list_pipelines,
    list_runs,
    list_steps,
    run_one_step,
    start_pipeline_run,
    update_pipeline,
    update_step,
)

router = APIRouter()


class OpsStepPatch(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    command: str | None = None
    notes: str | None = None


class OpsPipelineStepPatch(BaseModel):
    linkId: str
    enabled: bool | None = None
    sortOrder: int | None = None


class OpsPipelinePatch(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    cron: str | None = None
    notes: str | None = None
    steps: list[OpsPipelineStepPatch] | None = None


@router.get("/ops/steps")
def admin_ops_steps(_admin=Depends(require_permission("ops:read")), db: Session = Depends(get_db)):
    return ApiResponse.ok(list_steps(db))


@router.patch("/ops/steps/{step_id}")
def admin_ops_patch_step(
    step_id: str,
    body: OpsStepPatch,
    _admin=Depends(require_permission("ops:write")),
    db: Session = Depends(get_db),
):
    out = update_step(db, step_id, body.model_dump(exclude_unset=True))
    if not out:
        return ApiResponse.fail("步骤不存在", code=404)
    return ApiResponse.ok(out)


@router.post("/ops/steps/{step_id}/run")
def admin_ops_run_step(
    step_id: str,
    _admin=Depends(require_permission("ops:write")),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(run_one_step(db, step_id))
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)


@router.get("/ops/pipelines")
def admin_ops_pipelines(_admin=Depends(require_permission("ops:read")), db: Session = Depends(get_db)):
    return ApiResponse.ok(list_pipelines(db))


@router.patch("/ops/pipelines/{pipeline_id}")
def admin_ops_patch_pipeline(
    pipeline_id: str,
    body: OpsPipelinePatch,
    _admin=Depends(require_permission("ops:write")),
    db: Session = Depends(get_db),
):
    data = body.model_dump(exclude_unset=True)
    if data.get("steps"):
        data["steps"] = [s.model_dump() for s in body.steps or []]
    out = update_pipeline(db, pipeline_id, data)
    if not out:
        return ApiResponse.fail("流程不存在", code=404)
    return ApiResponse.ok(out)


@router.post("/ops/pipelines/{pipeline_id}/run")
def admin_ops_run_pipeline(
    pipeline_id: str,
    _admin=Depends(require_permission("ops:write")),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(start_pipeline_run(db, pipeline_id))
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)


@router.get("/ops/runs")
def admin_ops_runs(
    pipeline_id: str | None = None,
    _admin=Depends(require_permission("ops:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(list_runs(db, pipeline_id))


@router.post("/ops/runs/{run_id}/confirm")
def admin_ops_confirm_run(
    run_id: str,
    _admin=Depends(require_permission("ops:write")),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(confirm_run(db, run_id))
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
