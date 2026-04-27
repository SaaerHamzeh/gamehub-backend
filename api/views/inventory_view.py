from rest_framework import viewsets
from api.models import InventoryCategory, InventoryItem, AuditLog
from api.serializers import InventoryCategorySerializer, InventoryItemSerializer
from .permissions_view import PermissionByActionMixin, IsStaffOrOwner, IsManagerOrOwner, IsOwner

class InventoryCategoryViewSet(PermissionByActionMixin, viewsets.ModelViewSet):
    queryset = InventoryCategory.objects.all()
    serializer_class = InventoryCategorySerializer
    permission_classes = [IsManagerOrOwner]
    permission_action_map = {
        "create": [IsManagerOrOwner],
        "update": [IsManagerOrOwner],
        "partial_update": [IsManagerOrOwner],
        "destroy": [IsOwner],
    }

class InventoryItemViewSet(PermissionByActionMixin, viewsets.ModelViewSet):
    queryset = InventoryItem.objects.select_related(
        "category", "category__branch"
    ).all()
    serializer_class = InventoryItemSerializer
    permission_classes = [IsManagerOrOwner]
    permission_action_map = {
        "create": [IsManagerOrOwner],
        "update": [IsManagerOrOwner],
        "partial_update": [IsManagerOrOwner],
        "destroy": [IsOwner],
    }

    def perform_update(self, serializer):
        old_obj = self.get_object()
        new_price = serializer.validated_data.get("sale_price")
        if new_price is not None and old_obj.sale_price != new_price:
            AuditLog.objects.create(
                user=self.request.user,
                action_type=AuditLog.ACTION_UPDATE,
                resource_type="Inventory Pricing",
                resource_name=old_obj.name,
                description=f"Changed sale price from {old_obj.sale_price} to {new_price}",
            )
        serializer.save()
