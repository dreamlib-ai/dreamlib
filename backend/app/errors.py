"""Errors the client sees as {"error": Turkish message, "code": machine code} with an HTTP status.

The message is for people and may change; the code is the contract (docs/api.md, S2). A code is either given
where the client must tell cases apart, or follows from the status."""

CODES = {
    "invalid_request": "İstek eksik ya da geçersiz",
    "auth_required": "Giriş gerekli",
    "auth_invalid": "Oturum geçersiz ya da süresi dolmuş",
    "not_found": "Kayıt ya da yol yok (başkasının kaydı da)",
    "conflict": "İstek mevcut durumla çelişiyor",
    "revision_conflict": "Kayıt başka yerde değişti; güncelini açıp yeniden dene",
    "job_busy": "Önceki çizim işi sürüyor",
    "too_large": "Gövde çok büyük",
    "unsupported_media": "Ses biçimi desteklenmiyor",
    "unreadable": "Kayıtta konuşma anlaşılamadı",
    "daily_limit": "Bugünkü hak doldu",
    "rate_limited": "Çok sık istek; biraz bekle",
    "upstream_failed": "Sağlayıcı ya da veritabanı yanıt vermedi; tekrar denenebilir",
    "service_off": "Bu servis kurulu değil",
    "internal": "Beklenmeyen hata",
}
BY_STATUS = {400: "invalid_request", 401: "auth_required", 403: "auth_invalid", 404: "not_found", 409: "conflict",
             413: "too_large", 415: "unsupported_media", 422: "unreadable", 429: "rate_limited", 500: "internal",
             502: "upstream_failed", 503: "service_off"}


def code_for(status: int) -> str:
    return BY_STATUS.get(status, "internal" if status >= 500 else "invalid_request")


class ApiError(Exception):
    """An error the client sees as {"error": message, "code": code} with this status."""

    def __init__(self, status: int, message: str, code: str = ""):
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code or code_for(status)
        if self.code not in CODES:
            raise ValueError(f"unknown error code {self.code!r}")


class NotFound(Exception):
    """A dream that does not exist for this user."""


class Conflict(Exception):
    """A dream that changed while it was being edited."""
