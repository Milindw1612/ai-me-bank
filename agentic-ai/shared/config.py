from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str

    # Database
    database_url: str
    database_sync_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Langfuse
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # Core Banking System (CBS)
    cbs_base_url: str = ""
    cbs_client_id: str = ""
    cbs_client_secret: str = ""

    # Credit Bureau (CIBIL / Experian)
    bureau_api_url: str = "https://api.cibil.com/v1"
    bureau_api_key: str = ""

    # Account Aggregator (Sahamati / Setu / Finvu)
    aa_base_url: str = ""
    aa_client_id: str = ""
    aa_client_secret: str = ""

    # GST / Tax
    gst_api_url: str = "https://api.gst.gov.in/v1"
    gst_api_key: str = ""

    # OCR (financial document extraction)
    ocr_api_url: str = ""
    ocr_api_key: str = ""

    # AML / Watchlist screening
    aml_watchlist_api_url: str = ""
    aml_watchlist_api_key: str = ""

    # Card / UPI / IMPS transaction feed
    txn_feed_api_url: str = ""
    txn_feed_api_key: str = ""

    # WhatsApp
    whatsapp_api_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_webhook_verify_token: str = ""

    # SMS Gateway
    sms_gateway_url: str = ""
    sms_gateway_key: str = ""

    # IVR / Voice
    ivr_api_url: str = ""
    ivr_api_key: str = ""

    # Slack (internal ops escalation)
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_credit_channel_id: str = ""
    slack_fraud_channel_id: str = ""
    slack_collections_channel_id: str = ""

    # Security
    pii_encryption_key: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # App
    app_env: str = "development"
    app_port: int = 8000
    log_level: str = "INFO"
    bank_name: str = "Ai-ME BANK"

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
