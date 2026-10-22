from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.response import ApiResponse
from app.core.security import decode_token
from app.database import get_db
from app.models import AppUser, EnglishStudyAttempt, EnglishUnit, gen_id
from app.schemas.english import EnglishStudySubmission
from app.services.english_service import learner_progress, list_public_scenes, submit_study_result, unit_dict
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

router = APIRouter(prefix="/english", tags=["英语口语"])
optional_bearer = HTTPBearer(auto_error=False)


def get_learning_user(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    db: Session = Depends(get_db),
) -> str:
    if credentials:
        user_id = decode_token(credentials.credentials)
        user = db.get(AppUser, user_id) if user_id else None
        if not user or not user.is_active or (not user.username and not user.openid):
            raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
        return user.id
    return x_user_id or "guest-local"


@router.get("/home")
def home(db: Session = Depends(get_db), user_id: str = Depends(get_learning_user)):
    progress = learner_progress(db, user_id)
    return ApiResponse.ok({"completedUnits": progress["completedUnits"], "completedUnitIds": progress["completedUnitIds"],
                           "dueReviews": len(progress["dueReviews"]), "dueReviewCount": len(progress["dueReviews"]),
                           "dueReviewItems": progress["dueReviews"], "dailyTargetMin": 10,
                           "scenes": list_public_scenes(db)})


@router.get("/progress")
def progress(db: Session = Depends(get_db), user_id: str = Depends(get_learning_user)):
    return ApiResponse.ok(learner_progress(db, user_id))


@router.get("/scenes")
def scenes(db: Session = Depends(get_db)):
    return ApiResponse.ok(list_public_scenes(db))


@router.get("/units/{unit_id}")
def unit_detail(unit_id: str, db: Session = Depends(get_db)):
    row = db.query(EnglishUnit).filter(EnglishUnit.id == unit_id, EnglishUnit.is_published.is_(True)).first()
    if not row:
        raise HTTPException(status_code=404, detail="课程不存在或尚未发布")
    return ApiResponse.ok(unit_dict(row, public=True))


@router.post("/units/{unit_id}/complete")
def complete(unit_id: str, body: EnglishStudySubmission | None = None, db: Session = Depends(get_db), user_id: str = Depends(get_learning_user)):
    unit = db.query(EnglishUnit).filter(EnglishUnit.id == unit_id, EnglishUnit.is_published.is_(True)).first()
    if not unit:
        raise HTTPException(status_code=404, detail="课程不存在或尚未发布")
    submission = body or EnglishStudySubmission(attempt_id=gen_id("ena"), result="independent")
    previous = db.query(EnglishStudyAttempt).filter_by(user_id=user_id, attempt_id=submission.attempt_id).first()
    if previous and previous.unit_id != unit_id:
        raise HTTPException(status_code=409, detail="本次提交编号已用于其他课程")
    return ApiResponse.ok(submit_study_result(db, user_id, unit_id, submission.attempt_id, submission.result))
