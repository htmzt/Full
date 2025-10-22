"""
Core Serializers
"""
from rest_framework import serializers
from .models import MergedData, UploadHistory, MergeHistory


class MergedDataSerializer(serializers.ModelSerializer):
    """Merged data serializer"""
    
    class Meta:
        model = MergedData
        fields = [
            'id', 'po_id', 'po_number', 'po_line_no',
            'project_name', 'project_code', 'account_name',
            'site_name', 'site_code',
            'item_code', 'item_description', 'category',
            'unit_price', 'requested_qty', 'line_amount', 'unit', 'currency',
            'payment_terms', 'publish_date',
            'ac_date', 'pac_date', 'ac_amount', 'pac_amount',
            'status', 'po_status', 'remaining',
            'is_assigned', 'assigned_to', 'has_external_po',
            'batch_id', 'merged_at'
        ]
        read_only_fields = ['id', 'batch_id', 'merged_at']


class UploadHistorySerializer(serializers.ModelSerializer):
    """Upload history serializer"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = UploadHistory
        fields = [
            'id', 'user', 'user_email', 'user_name', 'batch_id',
            'file_type', 'original_filename', 'file_size',
            'status', 'total_rows', 'valid_rows', 'invalid_rows',
            'error_message', 'processing_duration',
            'uploaded_at', 'processed_at'
        ]
        read_only_fields = ['id', 'batch_id', 'uploaded_at']


class MergeHistorySerializer(serializers.ModelSerializer):
    """Merge history serializer"""
    merged_by_email = serializers.EmailField(source='merged_by.email', read_only=True)
    merged_by_name = serializers.CharField(source='merged_by.full_name', read_only=True)
    
    class Meta:
        model = MergeHistory
        fields = [
            'id', 'batch_id', 'merged_by', 'merged_by_email', 'merged_by_name',
            'total_records', 'po_records_count', 'acceptance_records_count',
            'po_file', 'acceptance_file',
            'status', 'error_message', 'notes',
            'merged_at', 'completed_at'
        ]
        read_only_fields = ['id', 'batch_id', 'merged_at']


class MergeStatusSerializer(serializers.Serializer):
    """Merge status check serializer"""
    has_po_data = serializers.BooleanField()
    has_acceptance_data = serializers.BooleanField()
    po_count = serializers.IntegerField()
    acceptance_count = serializers.IntegerField()
    ready_to_merge = serializers.BooleanField()