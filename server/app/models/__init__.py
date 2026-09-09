"""ORM 模型：按域拆分后统一 re-export（保持 from app.models import X 兼容）。"""
from app.models.base import Base, gen_id, utcnow
from app.models.account import AdminUser, AppUser, Role, SystemSetting
from app.models.content import Article, Category, Question
from app.models.practice import ManualWrong, PointsLog, PracticeAnswer, QuizAttempt, SectionRead, SignRecord, StudyRecord, WrongAnswer
from app.models.plan import DailyReview, PlanTask, PlanTemplate
from app.models.knowledge import KnowledgeNode
from app.models.exam import ExamAnswer, ExamAttempt, ExamPaper, ExamQuestion
from app.models.rmrb import (
    RmrbArticle,
    ShenlunArgumentMethod,
    ShenlunDrillLog,
    ShenlunMineLog,
    ShenlunNormTerm,
    ShenlunSentenceType,
    ShenlunSkeletonTemplate,
    ShenlunTeachingExample,
    ShenlunTermCategory,
    VocabInbox,
)
from app.models.events import EventImpression
from app.models.corpus import CorpusItem
from app.models.ziliao import ZiliaoFormula, ZiliaoPracticeLog, ZiliaoQuestionType, ZiliaoTrick
from app.models.misc import ActivityEvent, ExamCountdown, Feedback
from app.models.product import DailyLearningTask, TheoryLearningEntry, UserDailyTaskProgress, UserGuestLearningRecord
from app.models.content_ops import ContentOperationTemplate, ContentPublishPackage, ContentReviewRecord, EntryAttributionEvent
from app.models.question_bank import (
    ExamPaperUnified,
    ImportBatch,
    Material,
    PaperQuestionPosition,
    PaperSection,
    QuestionItem,
    QuestionMaterialLink,
    QuestionVersion,
)
from app.models.generation import GenerationBatch, ReviewRecord
