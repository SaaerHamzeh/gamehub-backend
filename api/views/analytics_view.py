from django.db.models import Count, Sum, F
from rest_framework.views import APIView
from rest_framework.response import Response
from api.models import Session, Sale, SessionOrder
from .permissions_view import IsManagerOrOwner

class AnalyticsView(APIView):
    permission_classes = [IsManagerOrOwner]

    def get(self, request):
        branch_id = request.query_params.get("branch_id")
        sessions = Session.objects.all()
        standalone_sales = Sale.objects.all()
        if branch_id:
            sessions = sessions.filter(branch_id=branch_id)
            standalone_sales = standalone_sales.filter(branch_id=branch_id)

        completed = sessions.filter(end_time__isnull=False)
        
        # Calculate Revenue
        sess_revenue = completed.aggregate(total=Sum("final_cost"))["total"] or 0
        standalone_revenue = standalone_sales.aggregate(total=Sum("total_price"))["total"] or 0
        total_revenue = float(sess_revenue) + float(standalone_revenue)

        # Calculate Costs (Inventory COGS)
        # 1. From Session Orders
        sess_order_cost = SessionOrder.objects.filter(session__in=completed).aggregate(
            total=Sum(F("quantity") * F("unit_cost"))
        )["total"] or 0
        
        # 2. From Standalone Sales
        standalone_cost = standalone_sales.aggregate(total=Sum("total_cost"))["total"] or 0
        
        total_cost = float(sess_order_cost) + float(standalone_cost)
        net_profit = total_revenue - total_cost

        most_used = (
            sessions.values("resource_unit__code", "resource_unit__resource_type__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )
        active_count = sessions.filter(end_time__isnull=True).count()

        return Response(
            {
                "activeSessions": active_count,
                "completedRevenue": total_revenue,
                "totalCost": total_cost,
                "netProfit": net_profit,
                "mostUsedResources": list(most_used),
            }
        )
