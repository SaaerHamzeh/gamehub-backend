from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from api.models import Session, InventoryItem, SessionOrder
from api.serializers import SessionSerializer
from api.serializers.gaming_serializer import SessionCreateSerializer
from .permissions_view import IsCashierManagerOrOwner

class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSerializer
    permission_classes = [IsCashierManagerOrOwner]

    def get_queryset(self):
        return Session.objects.all().select_related(
            "branch", "resource_unit", "resource_unit__resource_type"
        ).prefetch_related("orders")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = SessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Determine customer name – may be overridden below after ID is known
        provided_name = (data.get("name") or "").strip()

        session = Session.objects.create(
            customer_name=provided_name or "__TEMP__",
            branch_id=data["branchId"],
            resource_unit=data["resource_unit"],
            session_type=data["sessionType"],
            custom_price_per_hour=data.get("pricePerHour"),
            fixed_price=data.get("fixedPrice"),
            duration_hours=data.get("durationHours"),
            planned_end_time=data.get("planned_end_time"),
            discount=data.get("discount", 0),
            metadata=data.get("metadata") or {},
        )

        # Auto-assign session number as customer name when left blank
        if not provided_name:
            session.customer_name = f"زبون #{session.id}"
            session.save(update_fields=["customer_name"])

        out = self.get_serializer(session)
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def toggle_pause(self, request, pk=None):
        session = self.get_object()
        if session.end_time:
            return Response(
                {"error": "Cannot pause an ended session."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        session.is_paused = not session.is_paused
        if session.is_paused:
            session.last_pause_time = timezone.now()
        else:
            if session.last_pause_time:
                session.total_paused_ms += int(
                    (timezone.now() - session.last_pause_time).total_seconds() * 1000
                )
            session.last_pause_time = None
        session.save()
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        session = self.get_object()
        session.end_session()
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def add_order(self, request, pk=None):
        session = self.get_object()
        if session.end_time:
            return Response(
                {"error": "Cannot add orders to completed sessions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quantity = int(request.data.get("quantity", 1))
        inventory_item_id = request.data.get("inventoryItemId")
        item_name = request.data.get("name")
        unit_price = request.data.get("price")

        inventory_item = None
        if inventory_item_id:
            inventory_item = (
                InventoryItem.objects.select_for_update()
                .filter(id=inventory_item_id, is_active=True)
                .first()
            )
            if not inventory_item:
                return Response(
                    {"error": "Inventory item not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if inventory_item.quantity_in_stock < quantity:
                return Response(
                    {"error": f"Insufficient stock for {inventory_item.name}."}, status=status.HTTP_400_BAD_REQUEST
                )
            inventory_item.quantity_in_stock -= quantity
            inventory_item.save(update_fields=["quantity_in_stock"])
            item_name = inventory_item.name
            unit_price = inventory_item.sale_price
            unit_cost = inventory_item.cost_price
        else:
            unit_cost = Decimal("0.00")

        if not item_name or unit_price is None:
            return Response(
                {"error": "Missing item name or price."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        SessionOrder.objects.create(
            session=session,
            inventory_item=inventory_item,
            item_name=item_name,
            quantity=quantity,
            unit_price=unit_price,
            unit_cost=unit_cost,
            total_price=Decimal("0.00"),
        )
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def remove_order(self, request, pk=None):
        session = self.get_object()
        if session.end_time:
            return Response(
                {"error": "Cannot remove orders from completed sessions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_id = request.data.get("orderId")
        try:
            order = session.orders.get(id=order_id)
        except SessionOrder.DoesNotExist:
            return Response(
                {"error": "Order not found in this session."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Restore stock if linked to an inventory item
        if order.inventory_item:
            inventory_item = InventoryItem.objects.select_for_update().get(id=order.inventory_item.id)
            inventory_item.quantity_in_stock += order.quantity
            inventory_item.save(update_fields=["quantity_in_stock"])

        order.delete()
        return Response(self.get_serializer(session).data)
