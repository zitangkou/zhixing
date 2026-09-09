import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, require_permission
from app.core.permissions import PERMISSIONS, ROLE_PERMISSIONS
from app.core.response import ApiResponse
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import AdminUser, AppUser, Article, Category, Question, Role, SystemSetting, gen_id
from app.models import CorpusItem, EventImpression
from app.schemas import (
    AdminLogin,
    AdminPasswordChange,
    AdminToken,
    AdminUserOut,
    AppUserOut,
    AppUserUpdate,
    ArticleCreate,
    ArticleInferMetadataBody,
    ArticleUpdate,
    ArticleBatchCategory,
    ArticleBatchIds,
    ArticleBatchPublish,
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    KnowledgeNodeCreate,
    KnowledgeNodeOut,
    KnowledgeNodeUpdate,
    KnowledgeTreeOut,
    ExamPaperCreate,
    ExamPaperOut,
    ExamPaperUpdate,
    ExamQuestionCreate,
    ExamQuestionOut,
    ExamQuestionUpdate,
    PlanTemplateCreate,
    PlanTemplateOut,
    PlanTemplateUpdate,
    QuestionBatchApprove,
    QuestionBatchDelete,
    QuestionCreate,
    QuestionUpdate,
    AiGenerateQuestionsBody,
    ImportArticleHtmlBody,
    ImportArticleMarkdownBody,
    ImportQuestionsBody,
    RoleOut,
    SettingOut,
    SettingUpdate,
    RmrbArticleCreate,
    RmrbArticleUpdate,
    ShenlunArgumentMethodCreate,
    ShenlunArgumentMethodUpdate,
    ShenlunSentenceTypeCreate,
    ShenlunSentenceTypeUpdate,
    ShenlunSkeletonTemplateCreate,
    ShenlunSkeletonTemplateUpdate,
    ShenlunTermCategoryCreate,
    ShenlunTermCategoryUpdate,
    ZiliaoFormulaCreate,
    ZiliaoFormulaImportBody,
    ZiliaoFormulaUpdate,
    ZiliaoQuestionTypeCreate,
    ZiliaoQuestionTypeUpdate,
    ZiliaoTrickCreate,
    ZiliaoTrickUpdate,
)
from app.services.category_service import build_category_tree, sync_article_category
from app.services.ai.llm_client import LlmError
from app.services.ai.question_generator import run_ai_question_generation
from app.services.question_factory import add_generated_questions, add_imported_questions
from app.services.question_import import parse_questions_markdown
from app.services.article_import import parse_article_html, parse_article_markdown
from app.services.article_metadata import infer_article_metadata, merge_article_fields
from app.services.article_service import delete_article_record
from app.services.question_service import delete_question_record, delete_questions_for_article
from app.services.section_parser import build_sections_from_content, sections_to_content
from app.services.serializers import article_to_out, build_mind_map, question_to_out
from app.services.serializers import parse_json
from app.services.knowledge_service import (
    create_node as create_knowledge_node,
    delete_node as delete_knowledge_node,
    get_tree as get_knowledge_tree,
    list_trees as list_knowledge_trees,
    save_uploaded_md,
    sync_knowledge,
    sync_status as knowledge_sync_status,
    update_node as update_knowledge_node,
)
from app.services.plan_service import (
    copy_day_templates as copy_plan_day_templates,
    create_template as create_plan_template,
    delete_template as delete_plan_template,
    list_templates as list_plan_templates,
    replace_default_templates,
    seed_default_templates,
    sync_templates_to_pending_tasks,
    update_template as update_plan_template,
)
from app.services.exam_service import (
    batch_create_questions as batch_create_exam_questions,
    create_paper as create_exam_paper,
    create_question as create_exam_question,
    delete_paper as delete_exam_paper,
    delete_question as delete_exam_question,
    get_paper as get_exam_paper,
    list_papers as list_exam_papers,
    update_paper as update_exam_paper,
    update_question as update_exam_question,
)
from app.services.exam_import import parse_import as parse_exam_import
from app.services.ziliao_service import (
    create_formula as create_ziliao_formula,
    create_trick as create_ziliao_trick,
    create_type as create_ziliao_type,
    delete_formula as delete_ziliao_formula,
    delete_trick as delete_ziliao_trick,
    delete_type as delete_ziliao_type,
    import_formulas_from_json as import_ziliao_formulas_from_json,
    list_formulas as list_ziliao_formulas_admin,
    list_tricks as list_ziliao_tricks_admin,
    list_types as list_ziliao_types_admin,
    seed_sample_drill_paper,
    seed_ziliao_resources,
    update_formula as update_ziliao_formula,
    update_trick as update_ziliao_trick,
    update_type as update_ziliao_type,
)
from app.services.rmrb_service import (
    create_article as create_rmrb_article,
    delete_article as delete_rmrb_article,
    list_articles as list_rmrb_articles_admin,
    update_article as update_rmrb_article,
)
from app.services.rmrb_meta_service import (
    create_argument_method as create_rmrb_argument_method,
    create_sentence_type as create_rmrb_sentence_type,
    create_skeleton_template as create_rmrb_skeleton,
    create_term_category as create_rmrb_term_category,
    delete_argument_method as delete_rmrb_argument_method,
    delete_sentence_type as delete_rmrb_sentence_type,
    delete_skeleton_template as delete_rmrb_skeleton,
    delete_term_category as delete_rmrb_term_category,
    get_meta as get_rmrb_meta,
    list_argument_methods as list_rmrb_argument_methods,
    list_sentence_types as list_rmrb_sentence_types,
    list_skeleton_templates as list_rmrb_skeletons,
    list_term_categories as list_rmrb_term_categories,
    update_argument_method as update_rmrb_argument_method,
    update_sentence_type as update_rmrb_sentence_type,
    update_skeleton_template as update_rmrb_skeleton,
    update_term_category as update_rmrb_term_category,
)

