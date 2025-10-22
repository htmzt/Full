from django.contrib import admin
from external_pos.models import ExternalPO


@admin.register(ExternalPO)
class ExternalPOAdmin(admin.ModelAdmin):
    list_display = [
        'internal_po_id', 'assigned_to_sbc', 'status', 'sbc_response_status',
        'estimated_total_amount', 'created_at', 'submitted_at'
    ]
    list_filter = ['status', 'sbc_response_status', 'created_at', 'submitted_at']
    search_fields = ['internal_po_id', 'assigned_to_sbc__email', 'assigned_to_sbc__sbc_company_name']
    date_hierarchy = 'created_at'
    readonly_fields = ['id', 'internal_po_id', 'created_at', 'updated_at', 'submitted_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('internal_po_id', 'po_numbers', 'po_lines_data', 'estimated_total_amount')
        }),
        ('Assignment', {
            'fields': ('created_by', 'assigned_to_sbc', 'assignment_notes', 'internal_notes')
        }),
        ('Status', {
            'fields': ('status', 'sbc_response_status')
        }),
        ('PD Approval (Level 1)', {
            'fields': ('pd_approved_by', 'pd_approved_at', 'pd_remarks'),
            'classes': ('collapse',)
        }),
        ('Admin Approval (Level 2)', {
            'fields': ('admin_approved_by', 'admin_approved_at', 'admin_remarks'),
            'classes': ('collapse',)
        }),
        ('Rejection', {
            'fields': ('rejected_by', 'rejected_at', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        ('SBC Response', {
            'fields': ('sbc_accepted_at', 'sbc_rejection_reason'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'submitted_at'),
            'classes': ('collapse',)
        }),
    )