"""
External PO Models
"""
from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
import uuid


class ExternalPO(models.Model):
    """External PO with 2-level approval workflow"""
    
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING_PD_APPROVAL = 'PENDING_PD_APPROVAL', 'Pending PD Approval'
        PENDING_ADMIN_APPROVAL = 'PENDING_ADMIN_APPROVAL', 'Pending Admin Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
    
    class SBCResponseStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
    
    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Internal PO ID (auto-generated, e.g., EPO-2024-0001)
    internal_po_id = models.CharField(max_length=50, unique=True, db_index=True)
    
    # PO Numbers (array of original PO numbers)
    po_numbers = ArrayField(
        models.CharField(max_length=100),
        help_text="Array of PO numbers"
    )
    
    # PO Lines data (JSON array)
    po_lines_data = models.JSONField(
        help_text="Array of objects: [{po_id, po_number, po_line}, ...]"
    )
    
    # Creator
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_external_pos'
    )
    
    # Assigned SBC
    assigned_to_sbc = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_external_pos'
    )
    
    # Status
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    
    # Notes
    assignment_notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)
    
    # Financial
    estimated_total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # PD Approval (Level 1)
    pd_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pd_approved_external_pos'
    )
    pd_approved_at = models.DateTimeField(null=True, blank=True)
    pd_remarks = models.TextField(blank=True, null=True)
    
    # Admin Approval (Level 2)
    admin_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_approved_external_pos'
    )
    admin_approved_at = models.DateTimeField(null=True, blank=True)
    admin_remarks = models.TextField(blank=True, null=True)
    
    # Rejection
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_external_pos'
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # SBC Response
    sbc_response_status = models.CharField(
        max_length=50,
        choices=SBCResponseStatus.choices,
        default=SBCResponseStatus.PENDING
    )
    sbc_accepted_at = models.DateTimeField(null=True, blank=True)
    sbc_rejection_reason = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'external_pos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at'], name='idx_ext_po_status'),
            models.Index(fields=['assigned_to_sbc', 'status'], name='idx_ext_po_sbc'),
        ]
    
    def __str__(self):
        return f"{self.internal_po_id} - {self.assigned_to_sbc.email if self.assigned_to_sbc else 'Unassigned'}"
    
    def save(self, *args, **kwargs):
        """Generate internal_po_id if not exists"""
        if not self.internal_po_id:
            self.internal_po_id = self.generate_internal_po_id()
        super().save(*args, **kwargs)
    
    def generate_internal_po_id(self):
        """Generate unique internal PO ID: EPO-YYYY-NNNN"""
        from django.utils import timezone
        year = timezone.now().year
        
        # Get last External PO for this year
        last_po = ExternalPO.objects.filter(
            internal_po_id__startswith=f'EPO-{year}-'
        ).order_by('-internal_po_id').first()
        
        if last_po:
            try:
                last_num = int(last_po.internal_po_id.split('-')[-1])
                new_num = last_num + 1
            except (IndexError, ValueError):
                new_num = 1
        else:
            new_num = 1
        
        return f"EPO-{year}-{new_num:04d}"
    
    @property
    def po_line_count(self):
        """Get count of PO lines"""
        return len(self.po_lines_data) if self.po_lines_data else 0