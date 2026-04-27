from rest_framework import viewsets
from api.models import Branch, FeatureFlag
from api.serializers import BranchSerializer, FeatureFlagSerializer
from .permissions_view import PermissionByActionMixin, IsStaffOrOwner, IsOwner, IsManagerOrOwner

class BranchViewSet(PermissionByActionMixin, viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [IsManagerOrOwner]
    permission_action_map = {
        "create": [IsOwner],
        "update": [IsOwner],
        "partial_update": [IsOwner],
        "destroy": [IsOwner],
    }

class FeatureFlagViewSet(viewsets.ModelViewSet):
    queryset = FeatureFlag.objects.all()
    serializer_class = FeatureFlagSerializer
    permission_classes = [IsManagerOrOwner]
    permission_action_map = {
        "create": [IsManagerOrOwner],
        "update": [IsManagerOrOwner],
        "partial_update": [IsManagerOrOwner],
        "destroy": [IsOwner],
    }
