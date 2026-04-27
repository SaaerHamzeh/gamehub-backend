from rest_framework import status
from .base import BaseAPITestCase
from api.models import Branch

class BranchViewSetTests(BaseAPITestCase):
    url = '/api/branches/'

    def test_list_branches_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_branches_staff(self):
        self.authenticate('staff')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_branch_staff(self):
        self.authenticate('staff')
        data = {"name": "New Branch", "code": "NB"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_branch_owner(self):
        self.authenticate('owner')
        data = {"name": "New Branch", "code": "NB"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Branch.objects.count(), 3)

    def test_update_branch_manager(self):
        self.authenticate('manager')
        data = {"name": "Updated Branch"}
        response = self.client.patch(f'{self.url}{self.branch1.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_branch_owner(self):
        self.authenticate('owner')
        data = {"name": "Updated Branch"}
        response = self.client.patch(f'{self.url}{self.branch1.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.branch1.refresh_from_db()
        self.assertEqual(self.branch1.name, "Updated Branch")

    def test_delete_branch_owner(self):
        self.authenticate('owner')
        response = self.client.delete(f'{self.url}{self.branch1.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Branch.objects.count(), 1)
