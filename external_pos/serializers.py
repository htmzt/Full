"""
External PO Serializers
"""
from rest_framework import serializers
from .models import ExternalPO
from accounts.models import User


class POLineInputSerializer(serializers.Serializer):
    """Single PO line input"""
    po_id = serializers.CharField(max_length=200)
    po_number = serializers.CharField(max_length=100)
    po_line = serializers.CharField(max_length=50)
    
    def validate_po_id(self, value):
        """Validate PO ID format"""
        if '-' not in value:
            raise serializers.ValidationError(f"Invalid PO ID format: {value}")
        return value


class ExternalPOCreateSerializer(serializers.Serializer):
    """Create External PO serializer"""
    po_lines = POLineInputSerializer(many=True, min_length=1)
    assigned_to_sbc_id = serializers.UUIDField()
    assignment_notes = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    internal_notes = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    save_as_draft = serializers.BooleanField(default=True)
    
    def validate_assigned_to_sbc_id(self, value):
        """Validate SBC user exists"""
        try:
            user = User.objects.get(id=value)
            if user.role != 'SBC':
                raise serializers.ValidationError("Assigned user must be SBC role")
        except User.DoesNotExist:
            raise serializers.ValidationError("SBC user not found")
        return value


class ExternalPOUpdateSerializer(serializers.Serializer):
    """Update External PO (draft only)"""
    po_lines = POLineInputSerializer(many=True, required=False)
    assigned_to_sbc_id = serializers.UUIDField(required=False)
    assignment_notes = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    internal_notes = serializers.CharField(max_length=5000, required=False, allow_blank=True)


class ApprovalRespondSerializer(serializers.Serializer):
    """Approve/reject External PO"""
    action = serializers.ChoiceField(choices=['APPROVE', 'REJECT'])
    remarks = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    rejection_reason = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    
    def validate(self, attrs):
        """Validate rejection reason if rejecting"""
        if attrs['action'] == 'REJECT' and not attrs.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': 'Rejection reason is required when rejecting'
            })
        return attrs


class SBCRespondSerializer(serializers.Serializer):
    """SBC accept/reject External PO"""
    action = serializers.ChoiceField(choices=['ACCEPT', 'REJECT'])
    rejection_reason = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    
    def validate(self, attrs):
        """Validate rejection reason if rejecting"""
        if attrs['action'] == 'REJECT' and not attrs.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': 'Rejection reason is required when rejecting'
            })
        return attrs


class ExternalPOSerializer(serializers.ModelSerializer):
    """External PO detail serializer"""
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    assigned_to_sbc_email = serializers.EmailField(source='assigned_to_sbc.email', read_only=True)
    assigned_to_sbc_name = serializers.CharField(source='assigned_to_sbc.full_name', read_only=True)
    assigned_to_sbc_company = serializers.CharField(source='assigned_to_sbc.sbc_company_name', read_only=True)
    
    pd_approved_by_email = serializers.EmailField(source='pd_approved_by.email', read_only=True)
    pd_approved_by_name = serializers.CharField(source='pd_approved_by.full_name', read_only=True)
    
    admin_approved_by_email = serializers.EmailField(source='admin_approved_by.email', read_only=True)
    admin_approved_by_name = serializers.CharField(source='admin_approved_by.full_name', read_only=True)
    
    rejected_by_email = serializers.EmailField(source='rejected_by.email', read_only=True)
    rejected_by_name = serializers.CharField(source='rejected_by.full_name', read_only=True)
    
    po_line_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ExternalPO
        fields = [
            'id', 'internal_po_id', 'po_numbers', 'po_lines_data', 'po_line_count',
            'created_by', 'created_by_email', 'created_by_name',
            'assigned_to_sbc', 'assigned_to_sbc_email', 'assigned_to_sbc_name', 'assigned_to_sbc_company',
            'status', 'assignment_notes', 'internal_notes', 'estimated_total_amount',
            'pd_approved_by', 'pd_approved_by_email', 'pd_approved_by_name', 'pd_approved_at', 'pd_remarks',
            'admin_approved_by', 'admin_approved_by_email', 'admin_approved_by_name', 'admin_approved_at', 'admin_remarks',
            'rejected_by', 'rejected_by_email', 'rejected_by_name', 'rejected_at', 'rejection_reason',
            'sbc_response_status', 'sbc_accepted_at', 'sbc_rejection_reason',
            'created_at', 'updated_at', 'submitted_at'
        ]
        read_only_fields = ['id', 'internal_po_id', 'created_at', 'updated_at']


class ExternalPOListSerializer(serializers.ModelSerializer):
    """Simplified External PO list serializer"""
    assigned_to_sbc_name = serializers.CharField(source='assigned_to_sbc.full_name', read_only=True)
    po_line_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ExternalPO
        fields = [
            'id', 'internal_po_id', 'po_line_count',
            'assigned_to_sbc_name', 'status',
            'estimated_total_amount', 'created_at', 'submitted_at'
        ]


class AvailablePOLineSerializer(serializers.Serializer):
    """Available PO line serializer"""
    po_id = serializers.CharField()
    po_number = serializers.CharField()
    po_line_no = serializers.CharField()
    project_name = serializers.CharField()
    item_description = serializers.CharField()
    line_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    payment_terms = serializers.CharField()
    status = serializers.CharField()