from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ResourceConfigViewSet, BuffetItemViewSet, SessionViewSet, BulkSyncView

router = DefaultRouter()
router.register(r'settings/devices', ResourceConfigViewSet, basename='device')
router.register(r'settings/cafe-items', BuffetItemViewSet, basename='cafeitem')
router.register(r'sessions', SessionViewSet, basename='session')

urlpatterns = [
    path('settings/bulk-sync/', BulkSyncView.as_view(), name='bulk-sync'),
    path('', include(router.urls)),
]
