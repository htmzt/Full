"""
Assignment Models
"""
from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
import uuid


class POAssignment(models.Model):
    """PO Assignment tracking with approval workflow"""
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Array of PO IDs (format: "po_number-po_line_no")
    po_ids = ArrayField(
        models.CharField(max_length=200),
        help_text="Array of PO IDs like ['1212121-2', '1313131-5']"
    )
    
    # Users
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_assignments'
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_assignments'
    )
    
    # Status
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    
    # Notes
    assignment_notes = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'po_assignments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['assigned_to', 'status'], name='idx_assignment_user_status'),
        ]
    
    def __str__(self):
        return f"Assignment to {self.assigned_to.email} - {len(self.po_ids)} POs - {self.status}"
    
    @property
    def po_count(self):
        """Get count of PO IDs in this assignment"""
        return len(self.po_ids) if self.po_ids else 0