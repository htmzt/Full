"""
User Model - Single table for all roles
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import uuid


class UserRole(models.TextChoices):
    """User role choices"""
    ADMIN = 'ADMIN', 'Administrator'
    PD = 'PD', 'Procurement Director'
    PM = 'PM', 'Project Manager'
    COORDINATOR = 'COORDINATOR', 'Coordinator'
    PFM = 'PFM', 'Finance Manager'
    SBC = 'SBC', 'Subcontractor'
    IT = 'IT', 'IT Support'


class UserManager(BaseUserManager):
    """Custom user manager"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user"""
        if not email:
            raise ValueError('Email is required')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', UserRole.ADMIN)
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for all roles
    
    Roles:
    - ADMIN: Full system control, Level 2 approver
    - PD: Procurement Director, Level 1 approver
    - PM: Project Manager, creates External POs from assigned POs
    - COORDINATOR: View-only access
    - PFM: Finance Manager, view-only
    - SBC: Subcontractor, sees only assigned work
    - IT: IT Support (optional)
    """
    
    # ========== PRIMARY KEY ==========
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # ========== AUTHENTICATION ==========
    email = models.EmailField(unique=True, max_length=255)
    password = models.CharField(max_length=255)  # Handled by AbstractBaseUser
    
    # ========== PROFILE ==========
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True, null=True)
    
    # ========== ROLE ==========
    role = models.CharField(
        max_length=50,
        choices=UserRole.choices,
        default=UserRole.PM,
        db_index=True
    )
    
    # ========== PERMISSIONS (Auto-set based on role) ==========
    can_upload_files = models.BooleanField(default=False)
    can_trigger_merge = models.BooleanField(default=False)
    can_assign_pos = models.BooleanField(default=False)
    can_view_all_pos = models.BooleanField(default=False)
    can_create_external_po_any = models.BooleanField(default=False)
    can_create_external_po_assigned = models.BooleanField(default=False)
    can_approve_level_1 = models.BooleanField(default=False)  # PD
    can_approve_level_2 = models.BooleanField(default=False)  # Admin
    can_manage_users = models.BooleanField(default=False)
    can_view_dashboard = models.BooleanField(default=False)
    can_export_data = models.BooleanField(default=False)
    can_view_sbc_work = models.BooleanField(default=False)
    
    # ========== SBC SPECIFIC FIELDS ==========
    sbc_code = models.CharField(max_length=50, blank=True, null=True, unique=True)
    sbc_company_name = models.CharField(max_length=255, blank=True, null=True)
    
    # ========== STATUS ==========
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # For Django admin access
    is_locked = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    
    # ========== TIMESTAMPS ==========
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    # ========== MANAGER ==========
    objects = UserManager()
    
    # ========== SETTINGS ==========
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['role', 'is_active'], name='idx_user_role_active'),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
        """Auto-set permissions based on role before saving"""
        if not self.pk:  # Only on creation
            self.set_permissions_by_role()
        
        # Generate SBC code if SBC and no code exists
        if self.role == UserRole.SBC and not self.sbc_code:
            self.sbc_code = self.generate_sbc_code()
        
        super().save(*args, **kwargs)
    
    def set_permissions_by_role(self):
        """Set permissions based on role"""
        # Reset all permissions
        self.can_upload_files = False
        self.can_trigger_merge = False
        self.can_assign_pos = False
        self.can_view_all_pos = False
        self.can_create_external_po_any = False
        self.can_create_external_po_assigned = False
        self.can_approve_level_1 = False
        self.can_approve_level_2 = False
        self.can_manage_users = False
        self.can_view_dashboard = False
        self.can_export_data = False
        self.can_view_sbc_work = False
        
        # Set permissions by role
        if self.role == UserRole.ADMIN:
            self.can_upload_files = True
            self.can_trigger_merge = True
            self.can_assign_pos = True
            self.can_view_all_pos = True
            self.can_create_external_po_any = True
            self.can_approve_level_2 = True
            self.can_manage_users = True
            self.can_view_dashboard = True
            self.can_export_data = True
            self.is_staff = True
        
        elif self.role == UserRole.PD:
            self.can_upload_files = True
            self.can_trigger_merge = True
            self.can_assign_pos = True
            self.can_view_all_pos = True
            self.can_create_external_po_any = True
            self.can_approve_level_1 = True
            self.can_view_dashboard = True
            self.can_export_data = True
        
        elif self.role == UserRole.PM:
            self.can_create_external_po_assigned = True
            self.can_view_dashboard = True
            self.can_export_data = True
        
        elif self.role in [UserRole.COORDINATOR, UserRole.PFM]:
            self.can_view_dashboard = True
            self.can_export_data = True
        
        elif self.role == UserRole.SBC:
            self.can_view_sbc_work = True
        
        elif self.role == UserRole.IT:
            self.can_view_dashboard = True
    
    def generate_sbc_code(self):
        """Generate unique SBC code"""
        last_sbc = User.objects.filter(
            role=UserRole.SBC,
            sbc_code__isnull=False
        ).order_by('-sbc_code').first()
        
        if last_sbc and last_sbc.sbc_code:
            try:
                last_num = int(last_sbc.sbc_code.split('-')[1])
                new_num = last_num + 1
            except (IndexError, ValueError):
                new_num = 1
        else:
            new_num = 1
        
        return f"SBC-{new_num:04d}"