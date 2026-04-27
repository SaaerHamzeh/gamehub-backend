from rest_framework import status
from .base import BaseAPITestCase
from api.models import InventoryCategory, InventoryItem

class InventoryViewSetTests(BaseAPITestCase):
    cat_url = '/api/inventory-categories/'
    item_url = '/api/inventory-items/'

    def setUp(self):
        super().setUp()
        self.cat1 = InventoryCategory.objects.create(branch=self.branch1, name="Drinks", code="DRK")
        self.item1 = InventoryItem.objects.create(
            category=self.cat1, name="Cola", sale_price=2.50, quantity_in_stock=10
        )

    def test_list_unauthenticated(self):
        self.assertEqual(self.client.get(self.cat_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.item_url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_category_manager(self):
        self.authenticate('manager')
        data = {"branch": self.branch1.id, "name": "Snacks", "code": "SNK"}
        response = self.client.post(self.cat_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_item_manager(self):
        self.authenticate('manager')
        data = {
            "category": self.cat1.id,
            "name": "Chips",
            "sale_price": "1.50",
            "quantity_in_stock": 20
        }
        response = self.client.post(self.item_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
