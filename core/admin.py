from django.contrib import admin
from .models import POStaging, AcceptanceStaging, MergedData, UploadHistory, MergeHistory, PurchaseOrder, Acceptance


@admin.register(MergedData)
class MergedDataAdmin(admin.ModelAdmin):
    list_display = ['po_id', 'project_name', 'status', 'line_amount', 'is_assigned', 'has_external_po', 'merged_at']
    list_filter = ['status', 'category', 'is_assigned', 'has_external_po', 'merged_at']
    search_fields = ['po_number', 'po_line_no', 'project_name', 'item_description']
    date_hierarchy = 'merged_at'
    readonly_fields = ['id', 'batch_id', 'merged_at']


@admin.register(UploadHistory)
class UploadHistoryAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'file_type', 'user', 'status', 'total_rows', 'valid_rows', 'uploaded_at']
    list_filter = ['file_type', 'status', 'uploaded_at']
    search_fields = ['original_filename', 'user__email']
    date_hierarchy = 'uploaded_at'
    readonly_fields = ['id', 'batch_id', 'uploaded_at', 'processed_at']


@admin.register(MergeHistory)
class MergeHistoryAdmin(admin.ModelAdmin):
    list_display = ['batch_id', 'merged_by', 'total_records', 'status', 'merged_at']
    list_filter = ['status', 'merged_at']
    search_fields = ['batch_id', 'merged_by__email']
    date_hierarchy = 'merged_at'
    readonly_fields = ['id', 'batch_id', 'merged_at', 'completed_at']


@admin.register(POStaging)
class POStagingAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'po_line_no', 'batch_id', 'is_valid', 'is_processed', 'created_at']
    list_filter = ['is_processed', 'is_valid', 'created_at']
    search_fields = ['po_number', 'po_line_no']
    date_hierarchy = 'created_at'
    readonly_fields = ['batch_id', 'created_at']


@admin.register(AcceptanceStaging)
class AcceptanceStagingAdmin(admin.ModelAdmin):
    list_display = ['acceptance_no', 'po_number', 'po_line_no', 'batch_id', 'is_valid', 'is_processed', 'created_at']
    list_filter = ['is_processed', 'is_valid', 'created_at']
    search_fields = ['acceptance_no', 'po_number', 'po_line_no']
    date_hierarchy = 'created_at'
    readonly_fields = ['batch_id', 'created_at']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'po_line_no', 'batch_id', 'created_at']
    list_filter = ['created_at']
    search_fields = ['po_number', 'po_line_no']
    date_hierarchy = 'created_at'
    readonly_fields = ['id', 'batch_id', 'created_at', 'updated_at']


@admin.register(Acceptance)
class AcceptanceAdmin(admin.ModelAdmin):
    list_display = ['acceptance_no', 'po_number', 'po_line_no', 'batch_id', 'created_at']
    list_filter = ['created_at']
    search_fields = ['acceptance_no', 'po_number', 'po_line_no']
    date_hierarchy = 'created_at'
    readonly_fields = ['id', 'batch_id', 'created_at', 'updated_at']