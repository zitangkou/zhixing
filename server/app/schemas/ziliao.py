"""Pydantic schema · 域模块

按业务域拆分，统一由 app/schemas/__init__.py re-export，保持 from app.schemas import X 兼容。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
class ZiliaoFormulaOut(BaseModel):
    id: str
    code: str
    name: str
    category: str
    definition: str
    latex: str
    formulaPlain: str = ""
    scenarios: str
    pitfalls: str
    relatedTypeCodes: list[str] = []
    relatedTrickCodes: list[str] = []
    keywords: list[str] = []
    examFreq: int = 3
    sortOrder: int = 0
    isPublished: bool = True


class ZiliaoFormulaCreate(BaseModel):
    code: str
    name: str
    category: str = ""
    definition: str = ""
    latex: str = ""
    formulaPlain: str = ""
    scenarios: str = ""
    pitfalls: str = ""
    relatedTypeCodes: list[str] = []
    relatedTrickCodes: list[str] = []
    keywords: list[str] = []
    examFreq: int = 3
    sortOrder: int = 0
    isPublished: bool = True


class ZiliaoFormulaUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    category: str | None = None
    definition: str | None = None
    latex: str | None = None
    formulaPlain: str | None = None
    scenarios: str | None = None
    pitfalls: str | None = None
    relatedTypeCodes: list[str] | None = None
    relatedTrickCodes: list[str] | None = None
    keywords: list[str] | None = None
    examFreq: int | None = None
    sortOrder: int | None = None
    isPublished: bool | None = None


class ZiliaoFormulaImportBody(BaseModel):
    content: str
    overwrite: bool = True
    publishDefault: bool = True


class ZiliaoFormulaImportResult(BaseModel):
    total: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = []


class ZiliaoQuestionTypeOut(BaseModel):
    id: str
    code: str
    name: str
    category: str
    description: str
    ability: str
    difficulty: int = 3
    examFreq: int = 3
    formulaCodes: list[str] = []
    trickCodes: list[str] = []
    keywords: list[str] = []
    sortOrder: int = 0
    isPublished: bool = True


class ZiliaoQuestionTypeCreate(BaseModel):
    code: str
    name: str
    category: str = ""
    description: str = ""
    ability: str = ""
    difficulty: int = 3
    examFreq: int = 3
    formulaCodes: list[str] = []
    trickCodes: list[str] = []
    keywords: list[str] = []
    sortOrder: int = 0
    isPublished: bool = True


class ZiliaoQuestionTypeUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    category: str | None = None
    description: str | None = None
    ability: str | None = None
    difficulty: int | None = None
    examFreq: int | None = None
    formulaCodes: list[str] | None = None
    trickCodes: list[str] | None = None
    keywords: list[str] | None = None
    sortOrder: int | None = None
    isPublished: bool | None = None


class ZiliaoTrickOut(BaseModel):
    id: str
    code: str
    name: str
    category: str
    principle: str
    whenToUse: str
    whenNot: str
    errorNote: str
    formulaCodes: list[str] = []
    example: str
    sortOrder: int = 0
    isPublished: bool = True


class ZiliaoTrickCreate(BaseModel):
    code: str
    name: str
    category: str = ""
    principle: str = ""
    whenToUse: str = ""
    whenNot: str = ""
    errorNote: str = ""
    formulaCodes: list[str] = []
    example: str = ""
    sortOrder: int = 0
    isPublished: bool = True


class ZiliaoTrickUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    category: str | None = None
    principle: str | None = None
    whenToUse: str | None = None
    whenNot: str | None = None
    errorNote: str | None = None
    formulaCodes: list[str] | None = None
    example: str | None = None
    sortOrder: int | None = None
    isPublished: bool | None = None


class ZiliaoOverviewOut(BaseModel):
    formulaCount: int = 0
    typeCount: int = 0
    trickCount: int = 0
    drillSetCount: int = 0
    todaySets: int = 0
    todayCorrect: int = 0
    todayTotal: int = 0
    weekSets: int = 0
    hasRealDrill: bool = False
    usingSampleOnly: bool = False
    weakTypes: list["ZiliaoWeakTypeOut"] = []


class ZiliaoWeakTypeOut(BaseModel):
    id: str
    code: str
    name: str
    category: str = ""
    attemptCount: int = 0
    correctCount: int = 0
    totalCount: int = 0
    accuracy: float | None = None
    reason: str = ""


class ZiliaoDrillSetOut(BaseModel):
    setId: str
    paperId: str
    paperTitle: str
    materialPreview: str
    questionCount: int
    section: str = "资料分析"
    typeHints: list[str] = []
    isSample: bool = False


class ZiliaoDrillQuestionOut(BaseModel):
    id: str
    section: str
    sortOrder: int
    type: str
    material: str
    stem: str
    options: list[str]
    difficulty: int = 3


class ZiliaoDrillSetDetailOut(BaseModel):
    setId: str
    paperId: str
    paperTitle: str
    material: str
    questions: list[ZiliaoDrillQuestionOut]


class ZiliaoDrillAnswerItem(BaseModel):
    questionId: str
    userAnswer: str | list[str] = ""


class ZiliaoDrillSubmitIn(BaseModel):
    setId: str
    answers: list[ZiliaoDrillAnswerItem]
    timeUsedSec: int = 0
    typeCode: str = ""
    saveWrongs: bool = True


class ZiliaoDrillWrongItem(BaseModel):
    questionId: str
    stem: str
    material: str = ""
    options: list[str] = []
    userAnswer: str | list[str] = ""
    correctAnswer: str | list[str] = ""
    analysis: str = ""


class ZiliaoDrillSubmitOut(BaseModel):
    setId: str
    totalCount: int
    correctCount: int
    timeUsedSec: int
    wrongs: list[ZiliaoDrillWrongItem] = []
    savedWrongCount: int = 0


# ===== 考试倒计时 =====

