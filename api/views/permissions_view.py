from rest_framework.permissions import BasePermission
from api.models import User


class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role == User.ROLE_OWNER or request.user.is_superuser)
        )


class IsManagerOrOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.role in [User.ROLE_OWNER, User.ROLE_MANAGER]
                or request.user.is_superuser
            )
        )


class IsCashierManagerOrOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.role
                in [User.ROLE_OWNER, User.ROLE_MANAGER, User.ROLE_CASHIER]
                or request.user.is_superuser
            )
        )


class IsStaffOrOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class PermissionByActionMixin:
    permission_action_map = {}

    def get_permissions(self):
        classes = self.permission_action_map.get(self.action, self.permission_classes)
        return [permission() for permission in classes]
