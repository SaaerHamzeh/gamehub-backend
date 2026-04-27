from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AnalyticsView,
    AuditLogViewSet,
    BranchViewSet,
    BulkSetupView,
    FeatureFlagViewSet,
    InventoryCategoryViewSet,
    InventoryItemViewSet,
    ResourceTypeViewSet,
    ResourceUnitViewSet,
    SaleViewSet,
    SessionViewSet,
    UserViewSet,
    DailyReportViewSet,
    CustomObtainAuthToken,
    current_user_profile,
)

router = DefaultRouter()
router.register(r"branches", BranchViewSet, basename="branch")
router.register(r"feature-flags", FeatureFlagViewSet, basename="feature-flag")
router.register(r"resource-types", ResourceTypeViewSet, basename="resource-type")
router.register(r"resource-units", ResourceUnitViewSet, basename="resource-unit")
router.register(
    r"inventory-categories", InventoryCategoryViewSet, basename="inventory-category"
)
router.register(r"inventory-items", InventoryItemViewSet, basename="inventory-item")
router.register(r"sessions", SessionViewSet, basename="session")
router.register(r"sales", SaleViewSet, basename="sale")
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")
router.register(r"users", UserViewSet, basename="user")
router.register(r"daily-reports", DailyReportViewSet, basename="daily-report")

urlpatterns = [
    path("auth/login/", CustomObtainAuthToken.as_view(), name="auth-login"),
    path("auth/me/", current_user_profile, name="auth-me"),
    path("setup/bulk/", BulkSetupView.as_view(), name="bulk-setup"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
    path("", include(router.urls)),
]
