from rest_framework import viewsets
from api.models import ResourceType, ResourceUnit
from api.serializers import ResourceTypeSerializer, ResourceUnitSerializer
from .permissions_view import PermissionByActionMixin, IsStaffOrOwner, IsOwner, IsManagerOrOwner

class ResourceTypeViewSet(PermissionByActionMixin, viewsets.ModelViewSet):
    queryset = ResourceType.objects.all()
    serializer_class = ResourceTypeSerializer
    permission_classes = [IsManagerOrOwner]
    permission_action_map = {
        "create": [IsOwner],
        "update": [IsOwner],
        "partial_update": [IsOwner],
        "destroy": [IsOwner],
    }

class ResourceUnitViewSet(PermissionByActionMixin, viewsets.ModelViewSet):
    queryset = ResourceUnit.objects.select_related("branch", "resource_type").all()
    serializer_class = ResourceUnitSerializer
    permission_classes = [IsManagerOrOwner]
    permission_action_map = {
        "create": [IsManagerOrOwner],
        "update": [IsManagerOrOwner],
        "partial_update": [IsManagerOrOwner],
        "destroy": [IsOwner],
    }
