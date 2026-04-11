from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import User, ResourceConfig, BuffetItem, Session, SessionOrder

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')

@admin.register(ResourceConfig)
class ResourceConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'prefix', 'count')
    search_fields = ('name', 'prefix')

@admin.register(BuffetItem)
class BuffetItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    search_fields = ('name',)

class SessionOrderInline(admin.TabularInline):
    model = SessionOrder
    extra = 0
    readonly_fields = ('timestamp',)

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'resource_id', 'session_type', 'get_status', 'start_time', 'get_total_cost_display')
    list_filter = ('session_type', 'is_paused', 'end_time', 'start_time')
    search_fields = ('customer_name', 'resource_id')
    inlines = [SessionOrderInline]
    readonly_fields = ('get_total_cost_display', 'get_active_duration_display')

    def get_status(self, obj):
        if obj.end_time:
            return format_html('<span style="color: grey;">🏁 Completed</span>')
        if obj.is_paused:
            return format_html('<span style="color: orange;">⏸️ Paused</span>')
        return format_html('<span style="color: green;">⚡ Active</span>')
    get_status.short_description = 'Status'

    def get_total_cost_display(self, obj):
        cost = obj.get_live_cost()
        return format_html('<b>${}</b>', f"{cost:.2f}")
    get_total_cost_display.short_description = 'Total Cost (Live)'

    def get_active_duration_display(self, obj):
        ms = obj.get_active_ms()
        minutes = int((ms / (1000 * 60)) % 60)
        hours = int((ms / (1000 * 60 * 60)))
        return f"{hours}h {minutes}m"
    get_active_duration_display.short_description = 'Active Duration'
