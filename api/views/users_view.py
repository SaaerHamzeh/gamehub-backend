from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token

from api.models import User, FeatureFlag, Branch
from api.serializers import UserSerializer
from .permissions_view import IsOwner


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all().order_by("id")
    permission_classes = [IsOwner]


class CustomObtainAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user_id": user.pk,
                "username": user.username,
                "role": user.role,
                "is_superuser": user.is_superuser,
            }
        )


def build_permissions(user):
    if user.is_superuser or user.role == User.ROLE_OWNER:
        return {
            "manage_users": True,
            "manage_settings": True,
            "manage_feature_flags": True,
            "view_audit_logs": True,
            "manage_inventory": True,
            "manage_sessions": True,
            "view_analytics": True,
        }

    if user.role == User.ROLE_MANAGER:
        return {
            "manage_users": False,
            "manage_settings": True,
            "manage_feature_flags": True,
            "view_audit_logs": True,
            "manage_inventory": True,
            "manage_sessions": True,
            "view_analytics": True,
        }

    if user.role == User.ROLE_CASHIER:
        return {
            "manage_users": False,
            "manage_settings": False,
            "manage_feature_flags": False,
            "view_audit_logs": False,
            "manage_inventory": False,
            "manage_sessions": True,
            "view_analytics": False,
        }

    return {
        "manage_users": False,
        "manage_settings": False,
        "manage_feature_flags": False,
        "view_audit_logs": False,
        "manage_inventory": False,
        "manage_sessions": False,
        "view_analytics": False,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user_profile(request):
    user = request.user
    permissions = build_permissions(user)

    branch = Branch.objects.filter(is_active=True).order_by("id").first()
    feature_flags = {}
    if branch:
        flags = FeatureFlag.objects.filter(branch=branch)
        feature_flags = {flag.key: flag.enabled for flag in flags}

    return Response(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_superuser": user.is_superuser,
            "permissions": permissions,
            "features": feature_flags,
        }
    )
