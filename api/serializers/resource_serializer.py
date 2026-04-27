from rest_framework import serializers
from api.models import ResourceType, ResourceUnit

class ResourceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceType
        fields = "__all__"

class ResourceUnitSerializer(serializers.ModelSerializer):
    resource_type_name = serializers.CharField(
        source="resource_type.name", read_only=True
    )
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = ResourceUnit
        fields = "__all__"
