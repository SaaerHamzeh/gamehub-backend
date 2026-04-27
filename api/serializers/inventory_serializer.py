from rest_framework import serializers
from api.models import InventoryCategory, InventoryItem

class InventoryCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryCategory
        fields = "__all__"

class InventoryItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    branch_id = serializers.IntegerField(source="category.branch_id", read_only=True)

    class Meta:
        model = InventoryItem
        fields = "__all__"
