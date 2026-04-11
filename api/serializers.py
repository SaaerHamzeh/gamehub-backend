from rest_framework import serializers
from django.utils import timezone
from .models import User, ResourceConfig, BuffetItem, Session, SessionOrder
from decimal import Decimal

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'role']

class ResourceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceConfig
        fields = '__all__'
        
    def to_representation(self, instance):
        """
        Adapt response to perfectly match React expected device object shape:
        { id: "PC", name: "PC", prefix: "PC-", count: 10 }
        """
        data = super().to_representation(instance)
        # Re-mapping internal PK to the expected frontend `id` standard if needed
        # Or expose the `id` as the front-end string
        return {
            "id": data["metadata"].get("frontend_id", data["name"].upper().replace(" ", "")), # Persist UI ID
            "db_id": data["id"],
            "name": data["name"],
            "prefix": data["prefix"],
            "count": data["count"],
            "metadata": data["metadata"]
        }

class BuffetItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuffetItem
        fields = '__all__'

class SessionOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionOrder
        fields = ['item_name', 'price', 'timestamp']
        
    def to_representation(self, instance):
        """
        React shape: { name: itemName, price: itemPrice, time: isoString }
        """
        return {
            "name": instance.item_name,
            "price": instance.price,
            "time": instance.timestamp.isoformat()
        }

class SessionSerializer(serializers.ModelSerializer):
    orders = SessionOrderSerializer(many=True, read_only=True)
    
    # Virtual fields to replace frontend getters
    durationMinutes = serializers.SerializerMethodField()
    totalCost = serializers.SerializerMethodField()
    ordersCost = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id', 'customer_name', 'resource_id', 'session_type', 'price_per_hour',
            'duration_hours', 'start_time', 'planned_end_time', 'end_time',
            'is_paused', 'last_pause_time', 'total_paused_ms', 'discount',
            'orders', 'durationMinutes', 'totalCost', 'ordersCost'
        ]

    def get_durationMinutes(self, obj):
        # Prevent React from showing skewed final duration by retrieving our hardcoded final value
        if obj.final_duration_minutes is not None:
            return round(float(obj.final_duration_minutes), 2)
            
        active_ms = obj.get_active_ms()
        return round(active_ms / 60000, 2)

    def get_totalCost(self, obj):
        # Strict server-side cost calculation that cannot be overwritten by client patch requests
        if obj.final_cost is not None:
            return float(obj.final_cost)
            
        return float(obj.get_live_cost())
        
    def get_ordersCost(self, obj):
        # Aggegating the strict server-side records rather than trusting the React JS sum
        return float(sum(order.price for order in obj.orders.all()))

    def to_representation(self, instance):
        """
        Deep key mapping to ensure absolute parity with React state expectation.
        React expected:
        { name, deviceType, stationId, sessionType, pricePerHour, durationHours, ... }
        """
        data = super().to_representation(instance)
        # Rename keys to expected camelCase since React codebase uses camelCase.
        # This allows 1-to-1 sync without changing the React app heavily.
        # Extract the prefix dynamically (assuming format Prefix-Number, e.g. PC-01)
        device_type = data["resource_id"].split('-')[0] if '-' in data["resource_id"] else 'Unknown'

        return {
            "id": data["id"],
            "name": data["customer_name"],
            "deviceType": device_type,
            "stationId": data["resource_id"],
            "sessionType": data["session_type"],
            "pricePerHour": float(data["price_per_hour"]),
            "durationHours": float(data["duration_hours"]) if data["duration_hours"] else 0,
            "startTime": data["start_time"],
            "plannedEndTime": data["planned_end_time"],
            "endTime": data["end_time"],
            "durationMinutes": data["durationMinutes"],
            "totalCost": data["totalCost"],
            "orders": data["orders"],
            "ordersCost": data["ordersCost"],
            "isPaused": data["is_paused"],
            "lastPauseTime": data["last_pause_time"],
            "totalPausedMs": data["total_paused_ms"],
            "discount": float(data["discount"]),
            "alerted10min": False # Logic handled in frontend, or could be passed from backend based on time bounds
        }
