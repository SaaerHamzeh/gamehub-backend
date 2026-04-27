from decimal import Decimal
from django.db import transaction
from rest_framework import viewsets, serializers
from rest_framework.response import Response
from api.models import Sale, InventoryItem, SaleItem
from api.serializers import SaleSerializer
from .permissions_view import IsCashierManagerOrOwner

class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleSerializer
    permission_classes = [IsCashierManagerOrOwner]
    queryset = Sale.objects.all()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        branch_id = request.data.get("branchId")
        items_data = request.data.get("items", [])
        
        if not branch_id:
            raise serializers.ValidationError({"branchId": "This field is required."})
        if not items_data:
            raise serializers.ValidationError({"items": "At least one item is required."})

        total_price = Decimal("0.00")
        total_cost = Decimal("0.00")
        
        sale = Sale.objects.create(
            branch_id=branch_id,
            user=request.user,
        )
        
        for item in items_data:
            item_id = item.get("id")
            qty = int(item.get("quantity", 1))
            
            try:
                inventory_item = InventoryItem.objects.select_for_update().get(id=item_id)
            except InventoryItem.DoesNotExist:
                raise serializers.ValidationError({"items": f"Inventory item with ID {item_id} does not exist."})

            if qty <= 0:
                raise serializers.ValidationError({"items": f"Quantity for {inventory_item.name} must be greater than zero."})
            
            if inventory_item.quantity_in_stock < qty:
                raise serializers.ValidationError({"items": f"Insufficient stock for {inventory_item.name} (Available: {inventory_item.quantity_in_stock}, Requested: {qty})"})
            
            inventory_item.quantity_in_stock -= qty
            inventory_item.save()
            
            item_price = inventory_item.sale_price * qty
            item_cost = inventory_item.cost_price * qty
            
            SaleItem.objects.create(
                sale=sale,
                inventory_item=inventory_item,
                item_name=inventory_item.name,
                quantity=qty,
                unit_price=inventory_item.sale_price,
                unit_cost=inventory_item.cost_price,
                total_price=item_price
            )
            total_price += item_price
            total_cost += item_cost
            
        sale.total_price = total_price
        sale.total_cost = total_cost
        sale.save()
        
        return Response(self.get_serializer(sale).data)
