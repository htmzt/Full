"""
Django Admin Configuration for Users
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin"""
    
    list_display = ['email', 'full_name', 'role', 'is_active', 'created_at', 'last_login']
    list_filter = ['role', 'is_active', 'is_locked', 'created_at']
    search_fields = ['email', 'full_name', 'sbc_code', 'sbc_company_name']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'password')
        }),
        ('Personal Info', {
            'fields': ('full_name', 'phone')
        }),
        ('Role & Permissions', {
            'fields': (
                'role',
                'can_upload_files',
                'can_trigger_merge',
                'can_assign_pos',
                'can_view_all_pos',
                'can_create_external_po_any',
                'can_create_external_po_assigned',
                'can_approve_level_1',
                'can_approve_level_2',
                'can_manage_users',
                'can_view_dashboard',
                'can_export_data',
                'can_view_sbc_work',
            )
        }),
        ('SBC Info', {
            'fields': ('sbc_code', 'sbc_company_name'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_staff', 'is_locked', 'email_verified')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'full_name', 'role'),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_login']
    
    def save_model(self, request, obj, form, change):
        """Auto-set permissions when role changes"""
        if not change or 'role' in form.changed_data:
            obj.set_permissions_by_role()
        super().save_model(request, obj, form, change)