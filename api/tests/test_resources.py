from rest_framework import status
from .base import BaseAPITestCase
from api.models import ResourceType, ResourceUnit

class ResourceViewSetTests(BaseAPITestCase):
    rt_url = '/api/resource-types/'
    ru_url = '/api/resource-units/'

    def setUp(self):
        super().setUp()
        self.rt1 = ResourceType.objects.create(name="PC", code="PC_TYPE", prefix="PC", base_price=10.00)
        self.ru1 = ResourceUnit.objects.create(branch=self.branch1, resource_type=self.rt1, code="PC-01")

    def test_list_unauthenticated(self):
        self.assertEqual(self.client.get(self.rt_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.ru_url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_resource_type_staff(self):
        self.authenticate('staff')
        data = {"name": "Console", "code": "CONS", "prefix": "CN"}
        self.assertEqual(self.client.post(self.rt_url, data).status_code, status.HTTP_403_FORBIDDEN)

    def test_create_resource_type_manager(self):
        self.authenticate('manager')
        data = {"name": "Console", "code": "CONS", "prefix": "CN"}
        response = self.client.post(self.rt_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ResourceType.objects.count(), 2)

    def test_create_resource_unit_manager(self):
        self.authenticate('manager')
        data = {
            "branch": self.branch1.id,
            "resource_type": self.rt1.id,
            "code": "PC-02"
        }
        response = self.client.post(self.ru_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ResourceUnit.objects.count(), 2)

    def test_delete_resource_unit_manager(self):
        self.authenticate('manager')
        response = self.client.delete(f'{self.ru_url}{self.ru1.id}/')
        # Only OWNER can delete
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_resource_unit_owner(self):
        self.authenticate('owner')
        response = self.client.delete(f'{self.ru_url}{self.ru1.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
