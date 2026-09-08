from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_app_user
from app.core.response import ApiResponse
from app.database import get_db
from app.models import AppUser, Article, PointsLog, Question, SignRecord
from app.services.activity_service import record_event
from app.product import get_product_context
from app.schemas import (
    AnswerResult,
    AnswerSubmit,
    AppAuthToken,
    AppLoginBody,
    AppRegisterBody,
    AppUserPasswordChange,
    AppUserProfileUpdate,
    DailyReviewUpsert,
    DayPlanOut,
    ExamAnswerSubmit,
    ExamCountdownOut,
    ExamCountdownUpsert,
    ExamPaperCreate,
    ExamPaperOut,
    ExamPaperUpdate,
    ExamQuestionCreate,
    ExamQuestionOut,
    ExamQuestionUpdate,
    KnowledgeNodeUpdate,
    KnowledgeReviewAnswerBody,
    KnowledgeReviewSessionBody,
    KnowledgeTreeOut,
    ManualWrongCreate,
    ManualWrongOut,
    ManualWrongUpdate,
    ShenlunMineLogUpdate,
    ShenlunMineLogUpsert,
    ShenlunNormTermAdd,
    ShenlunNormTermUpdate,
    ShenlunDrillCreate,
    ShenlunSkeletonTemplateCreate,
    ShenlunTermCategoryCreate,
    CorpusItemCreate,
    CorpusItemUpdate,
    EventImpressionCreate,
    EventImpressionUpdate,
    PlanTaskCreate,
    PlanTaskOut,
    PlanTaskUpdate,
    PointsLogOut,
    QuizCompleteBody,
    QuizCompleteResult,
    QuizRankItemOut,
    QuizStatsOut,
    RankItemOut,
    ReviewCompleteBody,
    SectionReadBody,
    StudyRecordOut,
    UserMeOut,
    WrongRedoBody,
    ZiliaoDrillSubmitIn,
)
from app.services.auth_service import (
    authenticate_user,
    change_user_password,
    issue_app_token,
    register_user,
    update_user_profile,
)
from app.services.category_service import build_category_tree
from app.services.countdown_service import delete_countdown, get_countdown, upsert_countdown
from app.services.knowledge_service import (
    get_tree as get_knowledge_tree,
    list_trees as list_knowledge_trees,
    save_uploaded_md,
    sync_knowledge,
    sync_status as knowledge_sync_status,
    update_node as update_knowledge_node,
)
from app.services.knowledge_review_service import (
    answer_review as answer_knowledge_review,
    create_session as create_knowledge_review_session,
    get_due as get_knowledge_review_due,
)
from app.services.review_hub_service import get_review_hub
from app.services.manual_wrong_service import (
    create_wrong,
    delete_wrong,
    list_wrongs,
    review_wrong as review_manual_wrong,
    update_wrong,
)
from app.services.exam_service import (
    finish_attempt as finish_exam_attempt,
    get_attempt_detail as get_exam_attempt_detail,
    get_paper_detail as get_exam_paper_detail,
    list_papers as list_exam_papers,
    list_user_attempts as list_exam_attempts,
    start_attempt as start_exam_attempt,
    submit_answer as submit_exam_answer,
)
from app.services.ziliao_service import (
    get_drill_set as get_ziliao_drill_set,
    get_formula as get_ziliao_formula,
    get_overview as get_ziliao_overview,
    get_trick as get_ziliao_trick,
    get_type as get_ziliao_type,
    list_drill_sets as list_ziliao_drill_sets,
    list_formulas as list_ziliao_formulas,
    list_tricks as list_ziliao_tricks,
    list_types as list_ziliao_types,
    submit_drill as submit_ziliao_drill,
)
from app.services.rmrb_service import (
    get_article as get_rmrb_article,
    list_articles as list_rmrb_articles,
)
from app.services.rmrb_meta_service import (
    create_skeleton_template as create_rmrb_skeleton,
    create_term_category as create_rmrb_term_category,
    get_meta as get_rmrb_meta,
)
from app.services.growth_service import get_growth_overview
from app.services.corpus_service import (
    create_item as create_corpus_item,
    delete_item as delete_corpus_item,
    get_item as get_corpus_item,
    get_stats as get_corpus_stats,
    list_items as list_corpus_items,
    promote_to_term as promote_corpus_to_term,
    update_item as update_corpus_item,
)
from app.services.event_impression_service import (
    create_event as create_event_impression,
    delete_event as delete_event_impression,
    get_event as get_event_impression,
    get_hub as get_event_hub,
    list_events as list_event_impressions,
    update_event as update_event_impression,
)
from app.services.shenlun_service import (
    add_drill as add_shenlun_drill,
    add_term as add_shenlun_term,
    delete_mine as delete_shenlun_mine,
    delete_term as delete_shenlun_term,
    get_mine as get_shenlun_mine,
    get_mine_by_date as get_shenlun_mine_by_date,
    get_stats as get_shenlun_stats,
    list_drills as list_shenlun_drills,
    list_mines as list_shenlun_mines,
    list_terms as list_shenlun_terms,
    update_mine as update_shenlun_mine,
    update_term as update_shenlun_term,
    upsert_mine as upsert_shenlun_mine,
)
from app.services.plan_service import (
    add_task,
    delete_task,
    get_day_plan,
    list_recent_days,
    update_task,
    upsert_review,
)
from app.services.category_service import build_category_tree
from app.services.quiz_service import pick_questions, pick_timeline_questions
from app.services.serializers import article_to_out, parse_correct_answer, question_to_out
from app.services.study_service import (
    complete_review,
    generate_review_tasks,
    get_section_read_map,
    list_study_records,
    mark_section_read,
    upsert_study_record,
)
from app.services.user_service import add_points_log, build_user_me_out, calc_sign_streak, check_answer, record_wrong
from app.services.wrong_service import (
    apply_wrong_redo_result,
    list_wrong_questions,
    remove_wrong,
)


class FeedbackBody(BaseModel):
    content: str = ""
