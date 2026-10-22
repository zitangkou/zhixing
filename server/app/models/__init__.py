"""ORM 模型：按域拆分后统一 re-export（保持 from app.models import X 兼容）。"""
from app.models.base import Base, gen_id, utcnow
from app.models.account import AdminUser, AppUser, Role, SystemSetting
from app.models.content import Article, Category, Question, TheoryPoint
from app.models.practice import ArticleQuizProgress, ManualWrong, PointsLog, PracticeAnswer, QuizAttempt, SectionRead, SignRecord, StudyRecord, WrongAnswer
from app.models.plan import DailyReview, PlanTask, PlanTemplate
from app.models.knowledge import KnowledgeNode, KnowledgeTree, KnowledgeTreeVersion, UserKnowledgeState
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
    ShenlunExercise,
    ShenlunExerciseAttempt,
    ShenlunTermCategory,
    VocabInbox,
)
from app.models.events import EventImpression
from app.models.corpus import CorpusItem
from app.models.ziliao import (
    ZiliaoFormula, ZiliaoPracticeLog, ZiliaoQuestionType, ZiliaoTrick,
    ZiliaoQuickMethod, ZiliaoQuickSession, ZiliaoQuickMethodVersion,
)
from app.models.misc import ActivityEvent, ExamCountdown, Feedback
from app.models.product import DailyLearningTask, TheoryLearningEntry, UserDailyTaskProgress, UserGuestLearningRecord
from app.models.content_ops import ContentOperationTemplate, ContentPublishPackage, ContentReviewRecord, EntryAttributionEvent
from app.models.wechat_reply import WechatReplyConfiguration, WechatReplyRelease
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
from app.models.library_document import LibraryDocument
from app.models.image_generation import ImageGenerationJob
from app.models.rmrb_archive import RmrbArchiveArticle, RmrbArchiveBatch, RmrbArchiveIssue, RmrbArchivePage, RmrbArchiveRevision, RmrbArchiveSource, RmrbCommentArticle, RmrbArticleEvaluation, RmrbCommentQuote, RmrbCommentExclusionRule, RmrbQuoteOpsPackage, RmrbQuoteOpsPackageItem
from app.models.english import EnglishASRJob, EnglishScene, EnglishStudyAttempt, EnglishStudyRecord, EnglishUnit, EnglishUnitProgress
from app.models.photography import PhotographyCase, PhotographyLesson, PhotographyStage
from app.models.daily_quote import DailyQuote, DailyQuoteSelection, DailyQuoteFeedback, DailyQuoteJob
from app.models.shenlun_material import ShenlunMaterial

from app.models.rmrb_vocabulary import RmrbVocabulary, RmrbVocabularyJob
from app.models.shenlun_exercises import ShenlunExerciseJob
from app.models.llm_usage import LlmUsageLog
from app.models.theory_workflow import TheorySourceReview, TheoryQuizPaper
from app.models.rmrb_daily_pool import RmrbDailyPoolIssue, RmrbDailyPoolArticle
from app.models.creative import CreativeIdea, CreativeTag, CreativeIdeaTag, CreativeMaterial, CreativeIdeaMaterial, CreativeIdeaRelation, CreativePractice, CreativeEvent
from app.models.creative import CreativeCaptureRequest, CreativeAttachment
