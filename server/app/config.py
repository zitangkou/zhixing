from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/zhixing.db"
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 1440
    cors_origins: str = "http://localhost:10087"
    admin_username: str = "admin"
    admin_password: str = "admin123"
    # 是否开放移动端自助注册；生产建议 false，由管理员开通账号
    allow_register: bool = True
    # 多产品：旧客户端不传 Header 时继续使用综合版。
    default_product_key: str = "general"
    enabled_product_keys: str = "general"
    # 知识框架本地目录（开发可用 Obsidian；生产留空则走 data/knowledge + 管理端上传）
    knowledge_kb_dir: str = ""

    # 杜衡阁公众号基础回调。密钥只允许通过服务器环境变量注入。
    wechat_official_enabled: bool = False
    wechat_official_token: str = ""
    wechat_official_app_id: str = ""
    wechat_official_public_base_url: str = ""

    llm_enabled: bool = False
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-v4-flash"
    llm_timeout_seconds: int = 120

    # 语音识别：默认 none → 前端用免费 Web Speech；可设 aliyun / tencent
    asr_provider: str = "none"
    asr_prefer_cloud: bool = False
    aliyun_asr_appkey: str = ""
    aliyun_asr_token: str = ""
    tencent_asr_secret_id: str = ""
    tencent_asr_secret_key: str = ""
    tencent_asr_app_id: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def cors_allow_credentials(self) -> bool:
        return "*" not in self.cors_origin_list

    @property
    def enabled_product_key_set(self) -> set[str]:
        return {key.strip().lower() for key in self.enabled_product_keys.split(",") if key.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
