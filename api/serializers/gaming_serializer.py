from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers
from api.models import Session, SessionOrder, ResourceUnit

class SessionOrderSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="item_name", read_only=True)
    price = serializers.DecimalField(
        source="total_price", max_digits=10, decimal_places=2, read_only=True
    )
    time = serializers.DateTimeField(source="timestamp", read_only=True)

    class Meta:
        model = SessionOrder
        fields = [
            "id",
            "inventory_item",
            "item_name",
            "quantity",
            "unit_price",
            "total_price",
            "timestamp",
            "name",
            "price",
            "time",
        ]

class SessionSerializer(serializers.ModelSerializer):
    orders = SessionOrderSerializer(many=True, read_only=True)
    durationMinutes = serializers.SerializerMethodField()
    totalCost = serializers.SerializerMethodField()
    ordersCost = serializers.SerializerMethodField()
    branchName = serializers.CharField(source="branch.name", read_only=True)
    resourceType = serializers.CharField(
        source="resource_unit.resource_type.code", read_only=True
    )
    stationId = serializers.CharField(source="resource_unit.code", read_only=True)

    class Meta:
        model = Session
        fields = [
            "id",
            "customer_name",
            "branch",
            "branchName",
            "resource_unit",
            "resourceType",
            "stationId",
            "session_type",
            "custom_price_per_hour",
            "fixed_price",
            "duration_hours",
            "start_time",
            "planned_end_time",
            "end_time",
            "is_paused",
            "last_pause_time",
            "total_paused_ms",
            "discount",
            "metadata",
            "orders",
            "durationMinutes",
            "totalCost",
            "ordersCost",
        ]

    def get_durationMinutes(self, obj):
        if obj.final_duration_minutes is not None:
            return float(obj.final_duration_minutes)
        return round(obj.get_active_ms() / 60000, 2)

    def get_totalCost(self, obj):
        if obj.final_cost is not None:
            return float(obj.final_cost)
        return float(obj.get_live_cost())

    def get_ordersCost(self, obj):
        return float(obj.get_orders_cost())

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            "id": data["id"],
            "name": data["customer_name"],
            "branchId": data["branch"],
            "branchName": data["branchName"],
            "deviceType": data["resourceType"],
            "stationId": data["stationId"],
            "resourceUnitId": data["resource_unit"],
            "sessionType": data["session_type"],
            "pricePerHour": (
                float(data["custom_price_per_hour"])
                if data["custom_price_per_hour"] is not None
                else None
            ),
            "fixedPrice": (
                float(data["fixed_price"]) if data["fixed_price"] is not None else None
            ),
            "durationHours": (
                float(data["duration_hours"])
                if data["duration_hours"] is not None
                else 0
            ),
            "startTime": data["start_time"],
            "plannedEndTime": data["planned_end_time"],
            "endTime": data["end_time"],
            "isPaused": data["is_paused"],
            "lastPauseTime": data["last_pause_time"],
            "totalPausedMs": data["total_paused_ms"],
            "discount": float(data["discount"]),
            "orders": data["orders"],
            "durationMinutes": data["durationMinutes"],
            "ordersCost": data["ordersCost"],
            "totalCost": data["totalCost"],
            "metadata": data["metadata"],
            "alerted10min": False,
        }

class SessionCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    branchId = serializers.IntegerField()
    resourceUnitId = serializers.IntegerField(required=False)
    stationId = serializers.CharField(required=False)
    sessionType = serializers.ChoiceField(
        choices=[Session.SESSION_PREPAID, Session.SESSION_POSTPAID],
        default=Session.SESSION_POSTPAID,
    )
    pricePerHour = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    fixedPrice = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    durationHours = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    metadata = serializers.JSONField(required=False, allow_null=True)

    def validate(self, attrs):
        branch_id = attrs["branchId"]
        unit = None
        if attrs.get("resourceUnitId"):
            unit = (
                ResourceUnit.objects.filter(
                    id=attrs["resourceUnitId"], branch_id=branch_id, is_active=True
                )
                .select_related("resource_type")
                .first()
            )
        elif attrs.get("stationId"):
            unit = (
                ResourceUnit.objects.filter(
                    code=attrs["stationId"], branch_id=branch_id, is_active=True
                )
                .select_related("resource_type")
                .first()
            )

        if not unit:
            raise serializers.ValidationError(
                {"resourceUnitId": "Valid resource unit is required."}
            )

        if Session.objects.filter(resource_unit=unit, end_time__isnull=True).exists():
            raise serializers.ValidationError(
                {"stationId": f"Station {unit.code} is already occupied."}
            )

        attrs["resource_unit"] = unit

        if attrs["sessionType"] == Session.SESSION_PREPAID and attrs.get(
            "durationHours"
        ):
            attrs["planned_end_time"] = timezone.now() + timedelta(
                hours=float(attrs["durationHours"])
            )
        else:
            attrs["planned_end_time"] = None
        return attrs
