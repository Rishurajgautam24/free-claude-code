"""Centralized configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .nim import NimSettings

# OpenAI-compatible cloud APIs that only need an API key: name -> (base URL, key page)
OPENAI_COMPATIBLE_PRESETS = {
    "groq": ("https://api.groq.com/openai/v1", "https://console.groq.com/keys"),
    "cerebras": ("https://api.cerebras.ai/v1", "https://cloud.cerebras.ai"),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "https://aistudio.google.com/apikey",
    ),
    "mistral": ("https://api.mistral.ai/v1", "https://console.mistral.ai/api-keys"),
    "deepseek": (
        "https://api.deepseek.com/v1",
        "https://platform.deepseek.com/api_keys",
    ),
    "together": (
        "https://api.together.xyz/v1",
        "https://api.together.ai/settings/api-keys",
    ),
}

# /v1/models lists configured models as "<prefix><provider/model>". Claude Code's
# model picker only keeps IDs containing "claude"; picking one routes to that model.
MODEL_ID_PREFIX = "claude-fcc/"

VALID_PROVIDERS = (
    "nvidia_nim",
    "open_router",
    "lmstudio",
    "ollama",
    "custom",
    *OPENAI_COMPATIBLE_PRESETS,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ==================== OpenRouter Config ====================
    open_router_api_key: str = Field(default="", validation_alias="OPENROUTER_API_KEY")

    # ==================== Messaging Platform Selection ====================
    # Valid: "telegram" | "discord"
    messaging_platform: str = Field(
        default="discord", validation_alias="MESSAGING_PLATFORM"
    )

    # ==================== NVIDIA NIM Config ====================
    nvidia_nim_api_key: str = ""

    # ==================== LM Studio Config ====================
    lm_studio_base_url: str = Field(
        default="http://localhost:1234/v1",
        validation_alias="LM_STUDIO_BASE_URL",
    )

    # ==================== OpenAI-compatible providers ====================
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")
    cerebras_api_key: str = Field(default="", validation_alias="CEREBRAS_API_KEY")
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    mistral_api_key: str = Field(default="", validation_alias="MISTRAL_API_KEY")
    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    together_api_key: str = Field(default="", validation_alias="TOGETHER_API_KEY")
    ollama_base_url: str = Field(
        default="http://localhost:11434/v1", validation_alias="OLLAMA_BASE_URL"
    )
    # Any other OpenAI-compatible endpoint, used as MODEL="custom/<model>"
    custom_base_url: str = Field(default="", validation_alias="CUSTOM_BASE_URL")
    custom_api_key: str = Field(default="", validation_alias="CUSTOM_API_KEY")

    # ==================== Model ====================
    # All Claude model requests are mapped to this single model (fallback)
    # Format: provider_type/model/name
    model: str = "nvidia_nim/meta/llama3-70b-instruct"

    # Per-model overrides (optional, falls back to MODEL)
    # Each can use a different provider
    model_opus: str | None = Field(default=None, validation_alias="MODEL_OPUS")
    model_sonnet: str | None = Field(default=None, validation_alias="MODEL_SONNET")
    model_haiku: str | None = Field(default=None, validation_alias="MODEL_HAIKU")

    # ==================== Provider Rate Limiting ====================
    provider_rate_limit: int = Field(default=40, validation_alias="PROVIDER_RATE_LIMIT")
    provider_rate_window: int = Field(
        default=60, validation_alias="PROVIDER_RATE_WINDOW"
    )
    provider_max_concurrency: int = Field(
        default=5, validation_alias="PROVIDER_MAX_CONCURRENCY"
    )

    # ==================== HTTP Client Timeouts ====================
    http_read_timeout: float = Field(
        default=300.0, validation_alias="HTTP_READ_TIMEOUT"
    )
    http_write_timeout: float = Field(
        default=10.0, validation_alias="HTTP_WRITE_TIMEOUT"
    )
    http_connect_timeout: float = Field(
        default=2.0, validation_alias="HTTP_CONNECT_TIMEOUT"
    )

    # ==================== Fast Prefix Detection ====================
    fast_prefix_detection: bool = True

    # ==================== Optimizations ====================
    enable_network_probe_mock: bool = True
    enable_title_generation_skip: bool = True
    enable_suggestion_mode_skip: bool = True
    enable_filepath_extraction_mock: bool = True

    # ==================== NIM Settings ====================
    nim: NimSettings = Field(default_factory=NimSettings)

    # ==================== Voice Note Transcription ====================
    voice_note_enabled: bool = Field(
        default=True, validation_alias="VOICE_NOTE_ENABLED"
    )
    # Device: "cpu" | "cuda" | "nvidia_nim"
    # - "cpu"/"cuda": local Whisper (requires voice_local extra: uv sync --extra voice_local)
    # - "nvidia_nim": NVIDIA NIM Whisper API (requires voice extra: uv sync --extra voice)
    whisper_device: str = Field(default="cpu", validation_alias="WHISPER_DEVICE")
    # Whisper model ID or short name (for local Whisper) or NVIDIA NIM model (for nvidia_nim)
    # Local Whisper: "tiny", "base", "small", "medium", "large-v2", "large-v3", "large-v3-turbo"
    # NVIDIA NIM: "nvidia/parakeet-ctc-1.1b-asr", "openai/whisper-large-v3", etc.
    whisper_model: str = Field(default="base", validation_alias="WHISPER_MODEL")
    # Hugging Face token for faster model downloads (optional, for local Whisper)
    hf_token: str = Field(default="", validation_alias="HF_TOKEN")

    # ==================== Bot Wrapper Config ====================
    telegram_bot_token: str | None = None
    allowed_telegram_user_id: str | None = None
    discord_bot_token: str | None = Field(
        default=None, validation_alias="DISCORD_BOT_TOKEN"
    )
    allowed_discord_channels: str | None = Field(
        default=None, validation_alias="ALLOWED_DISCORD_CHANNELS"
    )
    claude_workspace: str = "./agent_workspace"
    # Claude Code processes the bot runs at once; more tasks wait for a free slot
    max_concurrent_cli: int = Field(
        default=4, ge=1, validation_alias="MAX_CONCURRENT_CLI"
    )
    allowed_dir: str = ""

    # ==================== Server ====================
    host: str = "127.0.0.1"
    port: int = 8082
    log_file: str = "server.log"
    # DEBUG also logs full request payloads (prompts, file contents) to log_file
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    # Empty = no auth check. Clients send it as ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY.
    proxy_auth_token: str = Field(default="", validation_alias="PROXY_AUTH_TOKEN")

    # Handle empty strings for optional string fields
    @field_validator(
        "telegram_bot_token",
        "allowed_telegram_user_id",
        "discord_bot_token",
        "allowed_discord_channels",
        mode="before",
    )
    @classmethod
    def parse_optional_str(cls, v):
        if v == "":
            return None
        return v

    @field_validator("whisper_device")
    @classmethod
    def validate_whisper_device(cls, v: str) -> str:
        if v not in ("cpu", "cuda", "nvidia_nim"):
            raise ValueError(
                f"whisper_device must be 'cpu', 'cuda', or 'nvidia_nim', got {v!r}"
            )
        return v

    @field_validator("model", "model_opus", "model_sonnet", "model_haiku")
    @classmethod
    def validate_model_format(cls, v: str | None) -> str | None:
        """Validate `provider/model`, or a comma-separated fallback chain of them."""
        if v is None:
            return None
        models = [m.strip() for m in v.split(",")]
        for model in models:
            if "/" not in model:
                raise ValueError(
                    f"Model must be prefixed with provider type. "
                    f"Valid providers: {', '.join(VALID_PROVIDERS)}. "
                    f"Format: provider_type/model/name"
                )
            provider = model.split("/", 1)[0]
            if provider not in VALID_PROVIDERS:
                raise ValueError(
                    f"Invalid provider: '{provider}'. "
                    f"Supported: {', '.join(VALID_PROVIDERS)}"
                )
        return ",".join(models)

    @model_validator(mode="after")
    def check_nvidia_nim_api_key(self) -> Settings:
        if (
            self.voice_note_enabled
            and self.whisper_device == "nvidia_nim"
            and not self.nvidia_nim_api_key.strip()
        ):
            raise ValueError(
                "NVIDIA_NIM_API_KEY is required when WHISPER_DEVICE is 'nvidia_nim'. "
                "Set it in your .env file."
            )
        return self

    @property
    def provider_type(self) -> str:
        """Extract provider type from the default model string."""
        return self.model.split("/", 1)[0]

    @property
    def model_name(self) -> str:
        """Extract the actual model name from the default model string."""
        return self.model.split("/", 1)[1]

    def resolve_model(self, claude_model_name: str) -> str:
        """Resolve a Claude model name to the configured provider/model string.

        Classifies the incoming Claude model (opus/sonnet/haiku) and
        returns the model-specific override if configured, otherwise the fallback MODEL.
        """
        picked = claude_model_name.removeprefix(MODEL_ID_PREFIX)
        if picked != claude_model_name and picked.split("/", 1)[0] in VALID_PROVIDERS:
            return picked  # chosen in Claude Code's /model picker
        name_lower = claude_model_name.lower()
        if "opus" in name_lower and self.model_opus is not None:
            return self.model_opus
        if "haiku" in name_lower and self.model_haiku is not None:
            return self.model_haiku
        if "sonnet" in name_lower and self.model_sonnet is not None:
            return self.model_sonnet
        return self.model

    def configured_models(self) -> dict[str, list[str]]:
        """Every model in MODEL/MODEL_* (chains included) -> the settings using it."""
        models: dict[str, list[str]] = {}
        for setting, value in (
            ("MODEL_OPUS", self.model_opus),
            ("MODEL_SONNET", self.model_sonnet),
            ("MODEL_HAIKU", self.model_haiku),
            ("MODEL", self.model),
        ):
            for i, model in enumerate((value or "").split(",") if value else []):
                models.setdefault(model, []).append(
                    setting if i == 0 else f"{setting} fallback {i}"
                )
        return models

    @staticmethod
    def parse_provider_type(model_string: str) -> str:
        """Extract provider type from any 'provider/model' string."""
        return model_string.split("/", 1)[0]

    @staticmethod
    def parse_model_name(model_string: str) -> str:
        """Extract model name from any 'provider/model' string."""
        return model_string.split("/", 1)[1]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
