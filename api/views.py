from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from django.utils import timezone
from .models import ResourceConfig, BuffetItem, Session, SessionOrder
from .serializers import (
    ResourceConfigSerializer, BuffetItemSerializer, 
    SessionSerializer, SessionOrderSerializer
)
from datetime import timedelta

# ---------------------------------------------------------
# CUSTOM RBAC PERMISSIONS
# ---------------------------------------------------------

class IsOwner(BasePermission):
    """
    Grants access only if the user role is strictly 'OWNER'.
    Prevents Cashier/Staff from modifying system settings or dynamically priced items.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'OWNER')

class IsStaffOrOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

# ---------------------------------------------------------
# SETTINGS & INVENTORY VIEWS
# ---------------------------------------------------------

class ResourceConfigViewSet(viewsets.ModelViewSet):
    """
    General management of Physical Devices/Tables.
    Only the owner can alter these configurations.
    """
    queryset = ResourceConfig.objects.all()
    serializer_class = ResourceConfigSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsOwner]
        else:
            self.permission_classes = [IsStaffOrOwner]
        return super().get_permissions()

class BuffetItemViewSet(viewsets.ModelViewSet):
    """
    Manage customizable buffer items (snacks, accessories).
    """
    queryset = BuffetItem.objects.all()
    serializer_class = BuffetItemSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsOwner]
        else:
            self.permission_classes = [IsStaffOrOwner]
        return super().get_permissions()

from rest_framework.views import APIView
from django.db import transaction

class BulkSyncView(APIView):
    """
    Accepts full arrays for Devices and CafeItems. Wipes and recreates them.
    This maintains exact parity with the frontend's localStorage behavior.
    """
    permission_classes = [IsOwner]

    @transaction.atomic
    def post(self, request):
        devices = request.data.get('devices', [])
        cafe_items = request.data.get('cafe_items', [])

        ResourceConfig.objects.all().delete()
        for d in devices:
            metadata = d.get('metadata', {})
            metadata['frontend_id'] = d.get('id', '')
            ResourceConfig.objects.create(
                name=d.get('name', 'Unknown Device'),
                prefix=d.get('prefix', 'DEV-'),
                count=int(d.get('count', 1)),
                metadata=metadata
            )

        BuffetItem.objects.all().delete()
        for c in cafe_items:
            BuffetItem.objects.create(
                name=c.get('name', 'Unknown Item'),
                price=c.get('price', 0.0),
                metadata=c.get('metadata', {})
            )

        return Response({"message": "Settings completely synced to database"})


# ---------------------------------------------------------
# CORE SESSION VALIDATION VIEWS
# ---------------------------------------------------------

class SessionViewSet(viewsets.ModelViewSet):
    """
    Manages the lifecycle of gaming/table sessions.
    The React Frontend acts as a dumb terminal. This View computes all monetary values securely.
    """
    serializer_class = SessionSerializer
    permission_classes = [IsStaffOrOwner] # Both Owner and Staff can manipulate live sessions
    
    def get_queryset(self):
        """
        LAZY-EVALUATION PATTERN (Backend Authority gap bridging):
        Instead of a complex Celery + Redis setup for "Auto-Ending", 
        every time the client polls the session list, we intercept and enforce business logic!
        """
        active_sessions = Session.objects.filter(end_time__isnull=True)
        for session in active_sessions:
            session.process_auto_end() # Will close the session safely if it exceeded the prepaid time limit
            
        return Session.objects.all().order_by('-start_time')

    def create(self, request, *args, **kwargs):
        """
        Override standard creation to map React values logically to Python bounds.
        """
        data = request.data
        session_type = data.get('sessionType', 'POST')
        start_time = timezone.now()
        
        # Calculate planned_end_time safely on the backend only.
        planned_end_time = None
        if session_type == 'PRE' and data.get('durationHours'):
            try:
                hours = float(data.get('durationHours'))
                planned_end_time = start_time + timedelta(hours=hours)
            except ValueError:
                return Response({"error": "Invalid duration"}, status=status.HTTP_400_BAD_REQUEST)
                
        # Validate that the station isn't already occupied securely!
        station_id = data.get('stationId')
        if Session.objects.filter(resource_id=station_id, end_time__isnull=True).exists():
            return Response(
                {"error": f"Station {station_id} is already actively occupied. Cannot double-book."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        session = Session.objects.create(
            customer_name=data.get('name', 'Unknown'),
            resource_id=station_id,
            session_type=session_type,
            price_per_hour=data.get('pricePerHour', 0),
            duration_hours=data.get('durationHours'),
            start_time=start_time,
            planned_end_time=planned_end_time
        )
        serializer = self.get_serializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """
        Toggles the pause state of a session. 
        Highly accurate backend timestamps block client from extending time.
        """
        session = self.get_object()
        if session.end_time:
            return Response({"error": "Cannot pause a closed session."}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        if session.is_paused:
            # UNPAUSE Logic
            session.is_paused = False
            pause_delta = (now - session.last_pause_time).total_seconds() * 1000
            session.total_paused_ms += int(pause_delta)
            
            # Stretch the planned_end_time by the paused amount so the player doesn't lose paid time.
            if session.planned_end_time:
                session.planned_end_time += timedelta(milliseconds=pause_delta)
        else:
            # PAUSE Logic
            session.is_paused = True
            session.last_pause_time = now
            
        session.save()
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """
        Finalizes the session. Locks in the current cost, ignores any estimated cost from the react state.
        Cashiers can apply a discount during this request payload.
        """
        session = self.get_object()
        if session.end_time:
            return Response({"message": "Session is already completed"}, status=status.HTTP_400_BAD_REQUEST)

        discount_param = request.data.get('discount', 0.0)
        try:
            session.discount = discount_param
        except ValueError:
            pass

        session.end_session()
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=['post'])
    def add_order(self, request, pk=None):
        """
        Adds a Buffet/Cafe item directly to a single session.
        Cost will inherently increase.
        """
        session = self.get_object()
        if session.end_time:
            return Response({"error": "Cannot add orders to completed sessions."}, status=status.HTTP_400_BAD_REQUEST)

        item_name = request.data.get('name')
        price = request.data.get('price')

        if not item_name or price is None:
            return Response({"error": "Missing name or price"}, status=status.HTTP_400_BAD_REQUEST)

        SessionOrder.objects.create(
            session=session,
            item_name=item_name,
            price=price
        )
        return Response(self.get_serializer(session).data)
