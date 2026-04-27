from django.db import models
from .core_model import Branch

class InventoryCategory(models.Model):
    branch = models.ForeignKey(
        Branch, related_name="inventory_categories", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)

    class Meta:
        unique_together = ("branch", "code")
        ordering = ["branch__name", "name"]

    def __str__(self):
        return f"{self.branch.code} - {self.name}"

class InventoryItem(models.Model):
    category = models.ForeignKey(
        InventoryCategory, related_name="items", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=50, blank=True)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_in_stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["category__branch__name", "category__name", "name"]

    def __str__(self):
        return self.name
