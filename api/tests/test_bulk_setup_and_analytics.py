from rest_framework import status
from .base import BaseAPITestCase
from api.models import Branch, FeatureFlag, ResourceType, ResourceUnit, InventoryCategory, InventoryItem, Session
from django.utils import timezone
from datetime import timedelta

class BulkSetupAndAnalyticsTests(BaseAPITestCase):
    setup_url = '/api/setup/bulk/'
    analytics_url = '/api/analytics/'

    def test_bulk_setup_unauthorized(self):
        self.authenticate('staff')
        response = self.client.post(self.setup_url, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_bulk_setup_owner(self):
        self.authenticate('owner')
        data = {
            "branch": {"code": "BULK1", "name": "Bulk Branch"},
            "feature_flags": [{"key": "NEW_UI", "enabled": True}],
            "resource_types": [{"code": "PS5", "name": "Playstation 5", "pricing_strategy": "HOURLY", "base_price": "15"}],
            "resource_units": [{"code": "PS5-01", "resource_type_code": "PS5", "status": "AVAILABLE"}],
            "inventory_categories": [{"name": "Food", "code": "FOOD"}],
            "inventory_items": [{"category_code": "FOOD", "name": "Burger", "sale_price": "5.00", "quantity_in_stock": 10}]
        }
        response = self.client.post(self.setup_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify db logic
        branch = Branch.objects.get(code="BULK1")
        self.assertEqual(FeatureFlag.objects.filter(branch=branch).count(), 1)
        self.assertEqual(ResourceType.objects.filter(code="PS5").count(), 1)
        self.assertEqual(ResourceUnit.objects.filter(branch=branch, code="PS5-01").count(), 1)
        self.assertEqual(InventoryCategory.objects.filter(branch=branch, code="FOOD").count(), 1)
        self.assertEqual(InventoryItem.objects.filter(category__branch=branch, name="Burger").count(), 1)

    def test_analytics_manager(self):
        self.authenticate('manager')
        
        # Creating Session data
        rt = ResourceType.objects.create(name="PC", code="PC_TYPE", prefix="PC", base_price=10.00)
        ru = ResourceUnit.objects.create(branch=self.branch1, resource_type=rt, code="PC-01")
        
        # Active session
        Session.objects.create(customer_name="Active", branch=self.branch1, resource_unit=ru)
        
        # Completed session
        completed = Session.objects.create(customer_name="Done", branch=self.branch1, resource_unit=ru)
        completed.end_time = timezone.now()
        completed.final_cost = 25.50
        completed.save()

        response = self.client.get(self.analytics_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["activeSessions"], 1)
        self.assertEqual(response.data["completedRevenue"], 25.50)
        
        # Must have PC-01 as most used
        self.assertTrue(len(response.data["mostUsedResources"]) > 0)
        self.assertEqual(response.data["mostUsedResources"][0]["resource_unit__code"], "PC-01")
