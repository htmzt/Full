from django.contrib import admin
from assignments.models import POAssignment


@admin.register(POAssignment)
class POAssignmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'assigned_to', 'assigned_by', 'status', 'po_count_display', 'created_at', 'responded_at']
    list_filter = ['status', 'created_at', 'responded_at']
    search_fields = ['assigned_to__email', 'assigned_by__email', 'assignment_notes']
    date_hierarchy = 'created_at'
    readonly_fields = ['id', 'created_at', 'responded_at']
    
    def po_count_display(self, obj):
        return obj.po_count
    po_count_display.short_description = 'PO Count'
    
    fieldsets = (
        ('Assignment Info', {
            'fields': ('po_ids', 'assigned_to', 'assigned_by', 'status')
        }),
        ('Notes', {
            'fields': ('assignment_notes', 'rejection_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'responded_at'),
            'classes': ('collapse',)
        }),
    )