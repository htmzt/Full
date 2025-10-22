"""
Assignment Serializers
"""
from rest_framework import serializers
from .models import POAssignment
from accounts.models import User


class AssignmentCreateSerializer(serializers.Serializer):
    """Create assignment serializer"""
    po_ids = serializers.ListField(
        child=serializers.CharField(max_length=200),
        min_length=1,
        help_text="List of PO IDs (format: po_number-po_line)"
    )
    assigned_to_user_id = serializers.UUIDField()
    assignment_notes = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    
    def validate_po_ids(self, value):
        """Validate PO ID format"""
        for po_id in value:
            if '-' not in po_id:
                raise serializers.ValidationError(
                    f"Invalid PO ID format: {po_id}. Expected format: 'po_number-po_line'"
                )
        return value
    
    def validate_assigned_to_user_id(self, value):
        """Validate user exists"""
        try:
            user = User.objects.get(id=value)
            if user.role not in ['ADMIN', 'PD', 'PM']:
                raise serializers.ValidationError("Can only assign to ADMIN, PD, or PM roles")
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value


class AssignmentRespondSerializer(serializers.Serializer):
    """Respond to assignment serializer"""
    action = serializers.ChoiceField(choices=['APPROVE', 'REJECT'])
    rejection_reason = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    
    def validate(self, attrs):
        """Validate rejection reason if rejecting"""
        if attrs['action'] == 'REJECT' and not attrs.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': 'Rejection reason is required when rejecting'
            })
        return attrs


class AssignmentSerializer(serializers.ModelSerializer):
    """Assignment detail serializer"""
    assigned_to_email = serializers.EmailField(source='assigned_to.email', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    assigned_by_email = serializers.EmailField(source='assigned_by.email', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.full_name', read_only=True)
    po_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = POAssignment
        fields = [
            'id', 'po_ids', 'po_count',
            'assigned_to', 'assigned_to_email', 'assigned_to_name',
            'assigned_by', 'assigned_by_email', 'assigned_by_name',
            'status', 'assignment_notes', 'rejection_reason',
            'created_at', 'responded_at'
        ]
        read_only_fields = ['id', 'created_at']


class AssignmentListSerializer(serializers.ModelSerializer):
    """Simplified assignment list serializer"""
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.full_name', read_only=True)
    po_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = POAssignment
        fields = [
            'id', 'po_count', 'assigned_to_name', 'assigned_by_name',
            'status', 'created_at', 'responded_at'
        ]