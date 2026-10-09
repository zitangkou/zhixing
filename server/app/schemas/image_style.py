"""AI image style preset configuration contract."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ImageStylePreset(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=64)
    category: str = Field(default="image-to-image", max_length=64)
    productKey: str = Field(default="general", max_length=32)
    modelId: str = Field(default="", max_length=64)
    description: str = Field(default="", max_length=240)
    status: Literal["draft", "active", "archived"] = "draft"
    version: str = Field(default="1.0.0", max_length=32)
    sortOrder: int = Field(default=100, ge=-10000, le=10000)
    promptTemplate: str = Field(default="", max_length=12000)
    negativePrompt: str = Field(default="", max_length=6000)
    rules: dict[str, Any] = Field(default_factory=dict)
    controls: dict[str, Any] = Field(default_factory=dict)
    providerParameters: dict[str, Any] = Field(default_factory=dict)
    maintainerNotes: str = Field(default="", max_length=2000)


class ImageStyleConfigOut(BaseModel):
    schemaVersion: int = 1
    items: list[ImageStylePreset] = Field(default_factory=list)


class ImageStyleMarkdownImportBody(BaseModel):
    markdown: str = Field(min_length=1, max_length=64000)


class ImageModelConfig(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=80)
    provider: Literal["dashscope", "volcengine", "openai-compatible"]
    model: str = Field(min_length=1, max_length=128)
    baseUrl: str = Field(min_length=1, max_length=500)
    credentialEnv: str = Field(default="", max_length=80, pattern=r"^$|^[A-Z][A-Z0-9_]{2,79}$")
    enabled: bool = False
    isDefault: bool = False
    supportsImageEdit: bool = True
    timeoutSeconds: int = Field(default=180, ge=10, le=600)
    parameters: dict[str, Any] = Field(default_factory=dict)
    credentialConfigured: bool = False


class ImageModelConfigOut(BaseModel):
    schemaVersion: int = 1
    defaultModelId: str = ""
    items: list[ImageModelConfig] = Field(default_factory=list)


class ImageModelConfigUpdate(BaseModel):
    items: list[ImageModelConfig] = Field(default_factory=list, max_length=50)
