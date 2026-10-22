"""申论练习题输入结构。"""
from typing import Literal
from datetime import date
from pydantic import BaseModel, Field, model_validator

QuestionType = Literal['summary', 'countermeasure', 'implementation', 'essay']
ReviewDecision = Literal['pending', 'approved', 'revision_required', 'rejected']
ReviewIssueTag = Literal['source_fidelity', 'task_fit', 'evidence_support', 'answer_coverage', 'analysis_quality', 'format_language', 'difficulty', 'other']

class ShenlunHumanReviewIn(BaseModel):
    decision: ReviewDecision = 'pending'
    issue_tags: list[ReviewIssueTag] = Field(default_factory=list, max_length=8)
    notes: str = Field(default='', max_length=2000)
    corrections_made: bool = False

    @model_validator(mode='after')
    def validate_review_note(self):
        if self.decision in ('revision_required', 'rejected') and not self.notes.strip():
            raise ValueError('退回或拒绝时请填写具体审核意见')
        return self

class ShenlunExerciseIn(BaseModel):
    question_type: QuestionType
    title: str = Field(min_length=2, max_length=256)
    source_article_id: str | None = None
    source_material_id: str | None = Field(default=None, max_length=32)
    fact_material_summary: str = Field(default='', max_length=2000)
    fact_material_limit: str = Field(default='', max_length=2000)
    fact_training: dict = Field(default_factory=dict)
    source_title: str = Field(default='', max_length=256)
    source_url: str = Field(default='', max_length=512)
    source_date: str = Field(default='', max_length=10)
    source_excerpt: str = Field(min_length=30, max_length=12000)
    prompt: str = Field(min_length=5, max_length=5000)
    requirements: str = Field(default='', max_length=3000)
    max_chars: int = Field(default=200, ge=0, le=5000)
    hint: str = Field(default='', max_length=3000)
    key_points: list[dict] = Field(default_factory=list, max_length=30)
    rubric: list[dict] = Field(default_factory=list, max_length=20)
    sample_answer: str = Field(min_length=5, max_length=12000)
    analysis: str = Field(min_length=5, max_length=12000)
    related_assets: list[dict] = Field(default_factory=list, max_length=30)
    difficulty: str = Field(default='基础', max_length=16)
    estimated_minutes: int = Field(default=8, ge=1, le=180)
    sort_order: int = 0
    is_featured: bool = False
    status: Literal['draft', 'published', 'archived'] = 'draft'
    human_review: ShenlunHumanReviewIn = Field(default_factory=ShenlunHumanReviewIn)

    @model_validator(mode='after')
    def validate_publication(self):
        if self.fact_training and not self.source_material_id:
            raise ValueError('主题训练包必须绑定主事实素材')
        if self.source_material_id:
            if self.question_type != 'essay':
                raise ValueError('事实素材论证训练仅用于申发论述题')
            if len(self.fact_material_summary.strip()) < 10:
                raise ValueError('关联事实素材后须保留事实摘要')
            if self.status == 'published' and not self.fact_training.get('themes'):
                raise ValueError('发布事实素材论证训练前，须完成人工审核的主题训练包')
            if self.status == 'published' and self.human_review.decision != 'approved':
                raise ValueError('事实素材训练包须先由教研审核通过，再发布')
        if self.status == 'published':
            if self.human_review.decision in ('revision_required', 'rejected'):
                raise ValueError('审核结论为退回或拒绝时不能发布')
            if not self.source_title.strip() or not self.source_url.startswith(('https://', 'http://')) or not self.key_points:
                raise ValueError('发布前须补齐可追溯来源链接、来源标题和参考要点')
            try:
                date.fromisoformat(self.source_date)
            except ValueError as exc:
                raise ValueError('来源日期须为 YYYY-MM-DD') from exc
            if len(self.rubric) < 2:
                raise ValueError('发布前至少设置两条评价维度')
            if any(not str(x.get('point', '')).strip() or not str(x.get('evidence', '')).strip() for x in self.key_points):
                raise ValueError('每条参考要点必须关联材料依据')
            if any(str(x.get('evidence', '')).strip() not in self.source_excerpt for x in self.key_points):
                raise ValueError('材料依据必须是材料摘录中的原文片段，便于逐字回查')
            if any(not str(x.get('name', '')).strip() or not str(x.get('description', '')).strip() for x in self.rubric):
                raise ValueError('评价维度名称和说明均不能为空')
            if any(x.get('type') not in ('quote', 'vocabulary', 'material') or not str(x.get('id','')).strip() or not str(x.get('title','')).strip() for x in self.related_assets):
                raise ValueError('关联积累需包含有效类型、记录ID和名称')
            rubric_names=' '.join(str(x.get('name','')) for x in self.rubric)
            type_checks={
                'summary': (('要点','完整'),('归纳','准确')),
                'countermeasure': (('针对','问题'),('可行','操作')),
                'implementation': (('身份','对象','受众','文种'),('格式','要素','完整')),
                'essay': (('立意','论点'),('论证','结构','逻辑')),
            }
            missing=[ '/'.join(group) for group in type_checks[self.question_type] if not any(term in rubric_names for term in group) ]
            if missing:
                raise ValueError(f"{self.question_type}题型自查维度还需覆盖：{'、'.join(missing)}")
            if self.question_type == 'implementation' and not any(term in self.requirements for term in ('身份','对象','受众','文种','格式')):
                raise ValueError('贯彻执行题的作答要求应明确身份、对象或文种格式')
            if self.question_type == 'summary' and self.max_chars == 0:
                raise ValueError('归纳概括题发布时应设置明确的字数上限')
        return self

class ShenlunExerciseAnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=12000)
    work: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode='after')
    def validate_work(self):
        allowed = {'fact', 'theme', 'theme_id', 'point', 'analysis', 'paragraph'}
        if set(self.work) - allowed:
            raise ValueError('训练过程包含未知步骤')
        if any(len(value) > 5000 for value in self.work.values()):
            raise ValueError('单步训练内容不能超过5000字')
        return self

class ShenlunExerciseRevisionIn(BaseModel):
    revision: str = Field(min_length=1, max_length=12000)
    reflection: str = Field(default='', max_length=2000)
