from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

class AuthRateThrottle(AnonRateThrottle):
    scope = "auth"

class PasswordResetRateThrottle(AnonRateThrottle):
    scope = "password_reset"

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
