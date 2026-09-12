from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "production"
    database_url: str = (
        "postgresql+asyncpg://mazajrituals:mazajrituals@mazajrituals_database:5432/mazajrituals"
    )
    cors_origins: str = (
        "https://mazajrituals.shop,https://www.mazajrituals.shop,http://localhost:3000"
    )

    sheet_webhook_url: str = ""
    sheet_webhook_secret: str = ""

    meta_pixel_id: str = ""
    meta_capi_access_token: str = ""
    meta_test_event_code: str = ""

    tiktok_pixel_id: str = ""
    tiktok_access_token: str = ""
    tiktok_test_event_code: str = ""

    snap_pixel_id: str = ""
    snap_capi_token: str = ""

    contact_email_to: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    catalog_version: int = 1

    maxmind_account_id: str = ""
    maxmind_license_key: str = ""
    geo_order_whitelist_phones: str = "0550603022"
    geo_check_enabled: bool = True

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
