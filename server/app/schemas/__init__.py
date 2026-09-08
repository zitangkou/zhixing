"""Pydantic schema：按域拆分后统一 re-export（保持 from app.schemas import X 兼容）。"""
from app.schemas.common import ArticleSection, MindMapNode
from app.schemas.content import (
    AiGenerateQuestionsBody,
    ArticleBatchCategory, ArticleBatchIds, ArticleBatchPublish, ArticleCreate, ArticleInferMetadataBody,
    ArticleInferMetadataOut, ArticleOut, ArticleUpdate, CategoryCreate, CategoryOut, CategoryUpdate,
    ImportArticleMarkdownBody, ImportQuestionsBody, QuestionBatchApprove, QuestionBatchDelete,
    QuestionCreate, QuestionOut, QuestionUpdate,
)
from app.schemas.quiz import AnswerResult, AnswerSubmit, PointsLogOut, QuizCompleteBody, QuizCompleteResult, QuizRankItemOut, QuizStatsOut, RankItemOut
from app.schemas.user import AppAuthToken, AppLoginBody, AppRegisterBody, AppUserPasswordChange, AppUserProfileUpdate, FeedbackHandleBody, FeedbackOut, UserMeOut
from app.schemas.study import ReviewCompleteBody, SectionReadBody, StudyRecordOut, WrongRedoBody
from app.schemas.admin import AdminLogin, AdminPasswordChange, AdminToken, AdminUserOut, AppUserOut, AppUserUpdate, RoleOut, SettingOut, SettingUpdate
from app.schemas.plan import DailyReviewOut, DailyReviewUpsert, DayPlanOut, PlanTaskCreate, PlanTaskOut, PlanTaskUpdate, PlanTemplateCreate, PlanTemplateOut, PlanTemplateUpdate
from app.schemas.knowledge import KnowledgeNodeCreate, KnowledgeNodeOut, KnowledgeNodeUpdate, KnowledgeReviewAnswerBody, KnowledgeReviewAnswerOut, KnowledgeReviewCardOut, KnowledgeReviewDueOut, KnowledgeReviewSessionBody, KnowledgeReviewSessionOut, KnowledgeTreeOut
from app.schemas.review import ManualWrongCreate, ManualWrongOut, ManualWrongUpdate, ReviewHubOut
from app.schemas.exam import ExamAnswerSubmit, ExamAttemptDetailOut, ExamAttemptOut, ExamPaperCreate, ExamPaperDetailOut, ExamPaperOut, ExamPaperUpdate, ExamQuestionCreate, ExamQuestionOut, ExamQuestionUpdate
from app.schemas.rmrb import (
    RMRB_THEME_TAG_PRESETS,
    RmrbArticleCreate, RmrbArticleOut, RmrbArticleUpdate,
    ShenlunArgumentFieldValue, ShenlunArgumentMethodCreate, ShenlunArgumentMethodOut, ShenlunArgumentMethodUpdate,
    ShenlunArgumentPoint, ShenlunArgumentSkeleton, ShenlunDrillCreate, ShenlunDrillLogOut,
    ShenlunMetaOut, ShenlunMineLogOut, ShenlunMineLogUpsert, ShenlunMineLogUpdate, ShenlunMineTermItem,
    ShenlunNormTermAdd, ShenlunNormTermOut, ShenlunNormTermUpdate, ShenlunQuoteItem, ShenlunSentenceTypeCreate,
    ShenlunSentenceTypeOut, ShenlunSentenceTypeUpdate, ShenlunSkeletonFieldDef, ShenlunSkeletonStructure,
    ShenlunSkeletonTemplateCreate, ShenlunSkeletonTemplateOut, ShenlunSkeletonTemplateUpdate, ShenlunStatsOut,
    ShenlunTemplateItem, ShenlunTermCategoryCreate, ShenlunTermCategoryOut, ShenlunTermCategoryUpdate, ShenlunVerbItem,
)
from app.schemas.growth import GrowthDayBar, GrowthDomainProgress, GrowthOverviewOut
from app.schemas.corpus import (
    CORPUS_KINDS,
    CORPUS_SOURCE_TYPES,
    CORPUS_STATUSES,
    CORPUS_TAG_PRESETS,
    CORPUS_TERM_KINDS,
    CorpusItemCreate,
    CorpusItemOut,
    CorpusItemUpdate,
    CorpusStatsOut,
)
from app.schemas.events import EventFrameworkGroup, EventHubOut, EventImpressionCreate, EventImpressionOut, EventImpressionUpdate
from app.schemas.ziliao import (
    ZiliaoDrillAnswerItem, ZiliaoDrillQuestionOut, ZiliaoDrillSetDetailOut, ZiliaoDrillSetOut, ZiliaoDrillSubmitIn,
    ZiliaoDrillSubmitOut, ZiliaoDrillWrongItem, ZiliaoFormulaCreate, ZiliaoFormulaImportBody, ZiliaoFormulaImportResult,
    ZiliaoFormulaOut, ZiliaoFormulaUpdate, ZiliaoOverviewOut, ZiliaoQuestionTypeCreate,
    ZiliaoQuestionTypeOut, ZiliaoQuestionTypeUpdate, ZiliaoTrickCreate, ZiliaoTrickOut, ZiliaoTrickUpdate, ZiliaoWeakTypeOut,
)
from app.schemas.countdown import ExamCountdownOut, ExamCountdownUpsert
from app.schemas.data import DataImportIn
from app.schemas.product import DailyTaskListOut, DailyTaskProgressBody, DailyTaskProgressOut, DailyLearningTaskOut, TopicItem, TopicListOut
from app.schemas.content_ops import ContentPackageGenerateFromArticle, ContentPublishPackageCreate, ContentPublishPackageUpdate, ContentPublishStatusBody, EntryAttributionEventCreate
from app.schemas.question_bank import (
    ExamPaperUnifiedOut,
    ImportBatchOut,
    MaterialOut,
    PaperQuestionPositionOut,
    PaperSectionOut,
    QuestionItemOut,
    QuestionMaterialLinkOut,
    QuestionVersionOut,
    ReconciliationReport,
)
