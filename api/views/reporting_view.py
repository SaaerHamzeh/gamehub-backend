from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, F
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from api.models.core_model import DailyReport, Branch
from api.models.gaming_model import Session, SessionOrder
from api.models.sales_model import Sale
from api.serializers.reporting_serializer import DailyReportSerializer
from .permissions_view import IsManagerOrOwner

class DailyReportViewSet(viewsets.ModelViewSet):
    queryset = DailyReport.objects.all()
    serializer_class = DailyReportSerializer
    permission_classes = [IsManagerOrOwner]

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def close_day(self, request):
        branch_id = request.data.get("branchId")
        if not branch_id:
            return Response({"error": "branchId is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            branch = Branch.objects.get(id=branch_id)
        except Branch.DoesNotExist:
            return Response({"error": "Branch not found"}, status=status.HTTP_404_NOT_FOUND)

        target_date = timezone.now().date()
        
        # 1. Sessions Revenue & Cost
        completed_sessions = Session.objects.filter(
            branch=branch, 
            end_time__date=target_date
        )
        revenue_sessions = completed_sessions.aggregate(total=Sum("final_cost"))["total"] or 0
        
        orders_cost = SessionOrder.objects.filter(
            session__in=completed_sessions
        ).aggregate(
            total=Sum(F("quantity") * F("unit_cost"))
        )["total"] or 0

        # 2. Standalone Sales Revenue & Cost
        standalone_sales = Sale.objects.filter(
            branch=branch, 
            timestamp__date=target_date
        )
        revenue_standalone = standalone_sales.aggregate(total=Sum("total_price"))["total"] or 0
        standalone_cost = standalone_sales.aggregate(total=Sum("total_cost"))["total"] or 0

        total_revenue = float(revenue_sessions) + float(revenue_standalone)
        total_cost = float(orders_cost) + float(standalone_cost)
        net_profit = total_revenue - total_cost
        
        active_sessions = Session.objects.filter(
            branch=branch, 
            end_time__isnull=True
        ).count()

        report, created = DailyReport.objects.update_or_create(
            branch=branch,
            date=target_date,
            defaults={
                "revenue_sessions": revenue_sessions,
                "revenue_standalone": revenue_standalone,
                "total_revenue": total_revenue,
                "orders_cost": orders_cost,
                "standalone_cost": standalone_cost,
                "total_cost": total_cost,
                "net_profit": net_profit,
                "active_sessions_at_close": active_sessions,
                "metadata": {
                    "generated_by": request.user.username,
                    "timestamp": timezone.now().isoformat()
                }
            }
        )

        return Response(DailyReportSerializer(report).data)
