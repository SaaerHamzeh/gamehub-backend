from django.db import models

class Branch(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=20, unique=True)
    address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class FeatureFlag(models.Model):
    branch = models.ForeignKey(
        Branch, related_name="feature_flags", on_delete=models.CASCADE
    )
    key = models.CharField(max_length=100)
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("branch", "key")
        ordering = ["branch__name", "key"]

    def __str__(self):
        return f"{self.branch.code}::{self.key}"

class DailyReport(models.Model):
    branch = models.ForeignKey(Branch, related_name="daily_reports", on_delete=models.CASCADE)
    date = models.DateField()
    
    revenue_sessions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    revenue_standalone = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    orders_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    standalone_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    net_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    active_sessions_at_close = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("branch", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"Report {self.branch.code} - {self.date}"
