import time
from decimal import Decimal
from rest_framework import status
from .base import BaseAPITestCase
from api.models import Session, ResourceType, ResourceUnit, InventoryCategory, InventoryItem

class SessionViewSetTests(BaseAPITestCase):
    url = '/api/sessions/'

    def setUp(self):
        super().setUp()
        self.rt1 = ResourceType.objects.create(name="PC", code="PC_TYPE", prefix="PC", base_price=10.00)
        self.ru1 = ResourceUnit.objects.create(branch=self.branch1, resource_type=self.rt1, code="PC-01")
        self.cat1 = InventoryCategory.objects.create(branch=self.branch1, name="Drinks", code="DRK")
        self.item1 = InventoryItem.objects.create(category=self.cat1, name="Cola", sale_price=2.50, quantity_in_stock=1)

    def test_create_session(self):
        self.authenticate('staff')
        data = {
            "name": "John Doe",
            "branchId": self.branch1.id,
            "stationId": "PC-01",
            "sessionType": Session.SESSION_POSTPAID
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Session.objects.count(), 1)
        self.assertEqual(response.data["name"], "John Doe")

    def test_create_session_occupied(self):
        self.authenticate('staff')
        # Create first session
        Session.objects.create(
            customer_name="John", branch=self.branch1, resource_unit=self.ru1, session_type=Session.SESSION_POSTPAID
        )
        
        data = {
            "name": "Jane",
            "branchId": self.branch1.id,
            "stationId": "PC-01",
            "sessionType": Session.SESSION_POSTPAID
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stationId", response.data)

    def test_pause_resume_session(self):
        self.authenticate('staff')
        session = Session.objects.create(
            customer_name="John", branch=self.branch1, resource_unit=self.ru1, session_type=Session.SESSION_POSTPAID
        )
        
        pause_url = f'{self.url}{session.id}/pause/'
        # Pause
        response = self.client.post(pause_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertTrue(session.is_paused)
        self.assertIsNotNone(session.last_pause_time)

        # Resume
        response = self.client.post(pause_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertFalse(session.is_paused)
        self.assertIsNone(session.last_pause_time)

    def test_add_order(self):
        self.authenticate('staff')
        session = Session.objects.create(
            customer_name="John", branch=self.branch1, resource_unit=self.ru1, session_type=Session.SESSION_POSTPAID
        )
        
        add_order_url = f'{self.url}{session.id}/add_order/'
        data = {
            "inventoryItemId": self.item1.id,
            "quantity": 1
        }
        response = self.client.post(add_order_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.item1.refresh_from_db()
        self.assertEqual(self.item1.quantity_in_stock, 0)
        self.assertEqual(session.orders.count(), 1)
        
        # Test insufficient stock
        response2 = self.client.post(add_order_url, data)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response2.data)

    def test_end_session(self):
        self.authenticate('staff')
        session = Session.objects.create(
            customer_name="John", branch=self.branch1, resource_unit=self.ru1, session_type=Session.SESSION_POSTPAID
        )
        
        end_url = f'{self.url}{session.id}/end/'
        response = self.client.post(end_url, {"discount": "1.00"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        session.refresh_from_db()
        self.assertIsNotNone(session.end_time)
        self.assertEqual(session.discount, Decimal("1.00"))
        # Price is $10/hr. If active for a very short time, rental cost is ~0. Total cost = 0 - 1.00 (but floored to 0.00).
        self.assertEqual(session.final_cost, Decimal("0.00"))
