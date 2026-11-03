from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformServer(BaseModel):
    name: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    url: str
    # Explicit operator grant. Other tools always require an action-specific approval.
    read_only_tools: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", validate_assignment=True, populate_by_name=True
    )
    socket_path: str = Field("/run/clifford/api.sock", validation_alias="CLIFFORD_SOCKET_PATH")
    clifford_user_id: str = "owner"
    assistant_name: str = "Clifford"
    wake_phrase: str = "Clifford"
    database_url: str = "sqlite:///./data/clifford.db"
    default_llm_provider: str = "ollama"
    default_llm_model: str = "gemma3:12b"
    ollama_base_url: str = "http://127.0.0.1:11434"
    provider_timeout: float = Field(180, gt=0, le=600)
    provider_retries: int = Field(1, ge=0, le=3)
    ollama_num_ctx: int = Field(2048, ge=512, le=32768)
    max_output_tokens: int = Field(512, ge=64, le=16384)
    context_char_budget: int = Field(4000, ge=1000, le=200000)
    files_root: str = "./data/files"
    requests_per_minute: int = Field(60, ge=1)
    vosk_model_path: str = "./data/models/vosk-model-small-en-us-0.15"
    web_root: str | None = None
    platform_servers: list[PlatformServer] = Field(default_factory=list)

    @field_validator("socket_path")
    @classmethod
    def valid_socket_path(cls, value):
        if not value.startswith("/") or "\x00" in value or value.endswith("/"):
            raise ValueError("Socket path must be an absolute file path")
        return value
