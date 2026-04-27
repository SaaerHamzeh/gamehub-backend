from decimal import Decimal
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from api.models import (
    Branch,
    FeatureFlag,
    ResourceType,
    ResourceUnit,
    InventoryCategory,
    InventoryItem,
    AuditLog,
)
from .permissions_view import IsOwner

class BulkSetupView(APIView):
    permission_classes = [IsOwner]

    @transaction.atomic
    def post(self, request):
        branch_data = request.data.get("branch") or {
            "name": "Main Branch",
            "code": "MAIN",
        }
        feature_flags = request.data.get("feature_flags", [])
        resource_types = request.data.get("resource_types", [])
        resource_units = request.data.get("resource_units", [])
        inventory_categories = request.data.get("inventory_categories", [])
        inventory_items = request.data.get("inventory_items", [])

        branch, _ = Branch.objects.update_or_create(
            code=branch_data["code"],
            defaults={
                "name": branch_data.get("name", branch_data["code"]),
                "address": branch_data.get("address", ""),
                "metadata": branch_data.get("metadata", {}),
                "is_active": branch_data.get("is_active", True),
            },
        )

        FeatureFlag.objects.filter(branch=branch).delete()
        for item in feature_flags:
            FeatureFlag.objects.create(
                branch=branch,
                key=item["key"],
                enabled=item.get("enabled", True),
                config=item.get("config", {}),
            )

        # ResourceUnit.objects.filter(branch=branch).delete() # We don't delete to preserve sessions
        type_map = {}
        for item in resource_types:
            obj, created = ResourceType.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item.get("name", item["code"]),
                    "prefix": item.get("prefix", item["code"][:3].upper()),
                    "pricing_strategy": item.get(
                        "pricing_strategy", ResourceType.PRICING_HOURLY
                    ),
                    "base_price": item.get("base_price", 0),
                    "metadata": item.get("metadata", {}),
                    "is_active": item.get("is_active", True),
                },
            )
            if not created and "base_price" in item:
                old_p = Decimal(str(obj.base_price))
                new_p = Decimal(str(item["base_price"]))
                if old_p != new_p:
                    AuditLog.objects.create(
                        user=request.user,
                        action_type=AuditLog.ACTION_UPDATE,
                        resource_type="Device Pricing",
                        resource_name=obj.name,
                        description=f"System update: Base price changed from {old_p} to {new_p}"
                    )
            type_map[obj.code] = obj

        for item in resource_units:
            resource_type = type_map[item["resource_type_code"]]
            ResourceUnit.objects.update_or_create(
                branch=branch,
                code=item["code"],
                defaults={
                    "resource_type": resource_type,
                    "display_name": item.get("display_name", ""),
                    "status": item.get("status", ResourceUnit.STATUS_AVAILABLE),
                    "metadata": item.get("metadata", {}),
                    "is_active": item.get("is_active", True),
                }
            )

        # ─── Inventory ───────────────────────────────────────────────────────
        category_map = {}
        for item in inventory_categories:
            category, _ = InventoryCategory.objects.update_or_create(
                branch=branch,
                code=item["code"],
                defaults={"name": item["name"]}
            )
            category_map[category.code] = category

        incoming_item_names = [item["name"] for item in inventory_items]
        for item in inventory_items:
            category = category_map[item["category_code"]]
            obj, created = InventoryItem.objects.update_or_create(
                category=category,
                name=item["name"],
                defaults={
                    "sku": item.get("sku", ""),
                    "sale_price": item.get("sale_price", 0),
                    "cost_price": item.get("cost_price", 0),
                    "quantity_in_stock": item.get("quantity_in_stock", 0),
                    "is_active": item.get("is_active", True),
                    "metadata": item.get("metadata", {}),
                }
            )
            if not created and "sale_price" in item:
                old_p = Decimal(str(obj.sale_price))
                new_p = Decimal(str(item["sale_price"]))
                if old_p != new_p:
                    AuditLog.objects.create(
                        user=request.user,
                        action_type=AuditLog.ACTION_UPDATE,
                        resource_type="Inventory Pricing",
                        resource_name=obj.name,
                        description=f"System update: Price changed from {old_p} to {new_p}"
                    )

        return Response(
            {"message": "Bulk setup synced successfully", "branch_id": branch.id}
        )
