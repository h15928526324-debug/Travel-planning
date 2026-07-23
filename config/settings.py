"""
全局配置管理 — 多来源加载 + 用户级 API 配置隔离

加载优先级 (LLM 配置):
  用户自己的 API Key (线程隔离) > Streamlit Secrets > .env > 系统环境变量

线程安全: 每个用户会话对应一个线程，threading.local() 保证互不干扰。
"""

import os
import threading
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent

# 加载 .env 文件: .env → .env.example → 跳过
env_file = PROJECT_ROOT / ".env"
env_example = PROJECT_ROOT / ".env.example"

if env_file.exists():
    load_dotenv(env_file, override=False)
elif env_example.exists():
    print(f"⚠️  未找到 .env，使用 .env.example 回退。建议: cp .env.example .env")
    load_dotenv(env_example, override=False)
else:
    print("⚠️  未找到 .env 或 .env.example，依赖环境变量")


# ═══════════════════════════════════════════
# 用户级 API 配置 (线程隔离)
# ═══════════════════════════════════════════

_user_api_config = threading.local()


def set_user_api_config(api_key: str = "", base_url: str = "", model: str = ""):
    """
    设置当前用户会话的 API 配置。
    由 Streamlit 前端在每个用户会话中调用。
    线程安全: 每个线程（用户会话）独立存储。
    """
    _user_api_config.api_key = api_key
    _user_api_config.base_url = base_url
    _user_api_config.model = model


def get_user_api_config() -> dict:
    """获取当前用户会话的 API 配置"""
    return {
        "api_key": getattr(_user_api_config, "api_key", None),
        "base_url": getattr(_user_api_config, "base_url", None),
        "model": getattr(_user_api_config, "model", None),
    }


def has_user_api_config() -> bool:
    """当前用户是否已配置自己的 API Key"""
    cfg = get_user_api_config()
    return bool(cfg["api_key"])


def clear_user_api_config():
    """清除当前用户的 API 配置"""
    _user_api_config.api_key = None
    _user_api_config.base_url = None
    _user_api_config.model = None


def get_effective_llm_config() -> dict:
    """
    获取最终生效的 LLM 配置。
    优先级: 用户自己的 Key > 全局 .env Key
    """
    user = get_user_api_config()
    s = get_settings()
    return {
        "api_key": user["api_key"] or s.openai_api_key,
        "base_url": user["base_url"] or s.openai_base_url,
        "model": user["model"] or s.openai_model,
    }


def _get_config_value(key: str, default: str = "") -> str:
    """
    多来源读取配置值。

    优先级:
      1. 系统环境变量 (Streamlit Cloud 会将 secrets 注入到环境变量)
      2. .env 文件 (通过 load_dotenv 加载)
      3. 默认值
    """
    return os.getenv(key, default)


def _get_config_int(key: str, default: int = 0) -> int:
    try:
        return int(_get_config_value(key, str(default)))
    except (ValueError, TypeError):
        return default


def _get_config_bool(key: str, default: bool = False) -> bool:
    val = _get_config_value(key, str(default).lower())
    return val.lower() in ("true", "1", "yes")


@dataclass
class Settings:
    """应用配置单例"""

    # --- LLM ---
    openai_api_key: str = field(default_factory=lambda: _get_config_value("OPENAI_API_KEY", ""))
    openai_base_url: str = field(default_factory=lambda: _get_config_value("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    openai_model: str = field(default_factory=lambda: _get_config_value("OPENAI_MODEL", "gpt-4o"))

    # --- 天气 API (uapis.cn 免费接口，无需 Key) ---

    # --- 地图 API ---
    map_api_key: str = field(default_factory=lambda: _get_config_value("MAP_API_KEY", ""))
    map_api_type: str = field(default_factory=lambda: _get_config_value("MAP_API_TYPE", "amap"))

    # --- 数据库 ---
    db_host: str = field(default_factory=lambda: _get_config_value("DB_HOST", "localhost"))
    db_port: int = field(default_factory=lambda: _get_config_int("DB_PORT", 3306))
    db_user: str = field(default_factory=lambda: _get_config_value("DB_USER", "root"))
    db_password: str = field(default_factory=lambda: _get_config_value("DB_PASSWORD", ""))
    db_name: str = field(default_factory=lambda: _get_config_value("DB_NAME", "travel_planner"))

    # --- 应用 ---
    log_level: str = field(default_factory=lambda: _get_config_value("LOG_LEVEL", "INFO"))
    output_dir: str = field(default_factory=lambda: _get_config_value("OUTPUT_DIR", "./output"))
    debug: bool = field(default_factory=lambda: _get_config_bool("DEBUG", False))

    @property
    def llm_config(self) -> dict:
        return {
            "model": self.openai_model,
            "api_key": self.openai_api_key,
            "base_url": self.openai_base_url,
        }


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
