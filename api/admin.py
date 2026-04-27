from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Branch,
    FeatureFlag,
    InventoryCategory,
    InventoryItem,
    ResourceType,
    ResourceUnit,
    Session,
    SessionOrder,
    User,
)


@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "is_staff")
    list_filter = ("role", "is_staff", "is_superuser")
    search_fields = ("username", "email")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at")
    search_fields = ("name", "code")
    list_filter = ("is_active",)


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ("branch", "key", "enabled")
    list_filter = ("enabled", "branch")
    search_fields = ("key", "branch__name")


@admin.register(ResourceType)
class ResourceTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "prefix",
        "pricing_strategy",
        "base_price",
        "is_active",
    )
    list_filter = ("pricing_strategy", "is_active")
    search_fields = ("name", "code", "prefix")


@admin.register(ResourceUnit)
class ResourceUnitAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "display_name",
        "branch",
        "resource_type",
        "status",
        "is_active",
    )
    list_filter = ("branch", "resource_type", "status", "is_active")
    search_fields = ("code", "display_name")


@admin.register(InventoryCategory)
class InventoryCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "branch")
    list_filter = ("branch",)
    search_fields = ("name", "code")


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "sale_price", "quantity_in_stock", "is_active")
    list_filter = ("category__branch", "category", "is_active")
    search_fields = ("name", "sku")


class SessionOrderInline(admin.TabularInline):
    model = SessionOrder
    extra = 0
    readonly_fields = ("timestamp", "total_price")


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = (
        "customer_name",
        "branch",
        "resource_unit",
        "session_type",
        "get_status",
        "start_time",
        "get_total_cost_display",
    )
    list_filter = ("branch", "session_type", "is_paused", "end_time", "start_time")
    search_fields = ("customer_name", "resource_unit__code", "branch__name")
    inlines = [SessionOrderInline]
    readonly_fields = ("get_total_cost_display", "get_active_duration_display")

    def get_status(self, obj):
        if obj.end_time:
            return format_html('<span style="color: grey;">🏁 Completed</span>')
        if obj.is_paused:
            return format_html('<span style="color: orange;">⏸️ Paused</span>')
        return format_html('<span style="color: green;">⚡ Active</span>')

    get_status.short_description = "Status"

    def get_total_cost_display(self, obj):
        return format_html("<b>${}</b>", f"{obj.get_live_cost():.2f}")

    get_total_cost_display.short_description = "Total Cost (Live)"

    def get_active_duration_display(self, obj):
        minutes = int((obj.get_active_ms() / (1000 * 60)) % 60)
        hours = int(obj.get_active_ms() / (1000 * 60 * 60))
        return f"{hours}h {minutes}m"

    get_active_duration_display.short_description = "Active Duration"
