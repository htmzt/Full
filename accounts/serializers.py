"""
User Serializers - COMPLETE
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, UserRole


class UserSerializer(serializers.ModelSerializer):
    """User detail serializer"""
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'phone', 'role',
            'can_upload_files', 'can_trigger_merge', 'can_assign_pos',
            'can_view_all_pos', 'can_create_external_po_any',
            'can_create_external_po_assigned', 'can_approve_level_1',
            'can_approve_level_2', 'can_manage_users', 'can_view_dashboard',
            'can_export_data', 'can_view_sbc_work',
            'sbc_code', 'sbc_company_name',
            'is_active', 'is_locked', 'email_verified',
            'created_at', 'last_login'
        ]
        read_only_fields = ['id', 'created_at', 'last_login', 'sbc_code']


class UserListSerializer(serializers.ModelSerializer):
    """User list serializer (simplified for listing)"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'role', 'role_display',
            'is_active', 'is_locked', 'created_at', 'last_login'
        ]
        read_only_fields = ['id', 'created_at', 'last_login']


class UserCreateSerializer(serializers.ModelSerializer):
    """User creation serializer"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm', 'full_name', 
            'phone', 'role', 'sbc_company_name'
        ]
    
    def validate(self, attrs):
        """Validate passwords match"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords don't match"})
        
        # Validate SBC fields
        if attrs.get('role') == UserRole.SBC and not attrs.get('sbc_company_name'):
            raise serializers.ValidationError(
                {"sbc_company_name": "Company name is required for SBC role"}
            )
        
        return attrs
    
    def create(self, validated_data):
        """Create user with hashed password"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Login serializer"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Validate credentials"""
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )
            
            if not user:
                raise serializers.ValidationError('Invalid email or password')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            
            if user.is_locked:
                raise serializers.ValidationError('User account is locked')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Email and password are required')


class ChangePasswordSerializer(serializers.Serializer):
    """Change password serializer"""
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, required=True, min_length=8)
    
    def validate(self, attrs):
        """Validate new passwords match"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError(
                {"new_password": "New passwords don't match"}
            )
        
        # Ensure new password is different from old
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                {"new_password": "New password must be different from old password"}
            )
        
        return attrs