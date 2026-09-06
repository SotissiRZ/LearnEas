from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

class AuthRateThrottle(AnonRateThrottle):
    scope = "auth"

class PasswordResetRateThrottle(AnonRateThrottle):
    scope = "password_reset"

class RefreshRateThrottle(AnonRateThrottle):
    scope = "token_refresh"

class CheckoutRateThrottle(UserRateThrottle):
    scope = "checkout"

class MediaRateThrottle(UserRateThrottle):
    scope = "media"

class LiveRateThrottle(UserRateThrottle):
    scope = "live"

class AdminTestRateThrottle(UserRateThrottle):
    scope = "admin_test"

class WebhookRateThrottle(AnonRateThrottle):
    scope = "webhook"

class ClientTelemetryRateThrottle(AnonRateThrottle):
    scope = "client_telemetry"

class ProductAnalyticsRateThrottle(UserRateThrottle):
    scope = "product_analytics"
