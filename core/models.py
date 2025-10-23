"""
Core Models - Upload staging, Merged Data, History
"""
from django.db import models
from django.conf import settings
import uuid


# ============================================================================
# STAGING TABLES
# ============================================================================

class POStaging(models.Model):
    """Temporary staging for uploaded PO data"""
    
    staging_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    batch_id = models.UUIDField(db_index=True)
    
    # Processing status
    row_number = models.IntegerField(null=True, blank=True)
    is_processed = models.BooleanField(default=False)
    is_valid = models.BooleanField(default=True)
    validation_errors = models.JSONField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # PO Data
    po_number = models.CharField(max_length=100)
    po_line_no = models.CharField(max_length=50)
    project_name = models.CharField(max_length=255, blank=True, null=True)
    project_code = models.CharField(max_length=100, blank=True, null=True)
    site_name = models.CharField(max_length=255, blank=True, null=True)
    site_code = models.CharField(max_length=100, blank=True, null=True)
    item_code = models.CharField(max_length=100, blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    item_description_local = models.TextField(blank=True, null=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    requested_qty = models.IntegerField(null=True, blank=True)
    due_qty = models.IntegerField(null=True, blank=True)
    billed_qty = models.IntegerField(null=True, blank=True)
    quantity_cancel = models.IntegerField(null=True, blank=True)
    line_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    po_status = models.CharField(max_length=50, blank=True, null=True)
    payment_terms = models.CharField(max_length=255, blank=True, null=True)
    payment_method = models.CharField(max_length=100, blank=True, null=True)
    customer = models.CharField(max_length=255, blank=True, null=True)
    rep_office = models.CharField(max_length=255, blank=True, null=True)
    subcontract_no = models.CharField(max_length=100, blank=True, null=True)
    pr_no = models.CharField(max_length=100, blank=True, null=True)
    sales_contract_no = models.CharField(max_length=100, blank=True, null=True)
    version_no = models.CharField(max_length=50, blank=True, null=True)
    shipment_no = models.CharField(max_length=100, blank=True, null=True)
    engineering_code = models.CharField(max_length=100, blank=True, null=True)
    engineering_name = models.CharField(max_length=255, blank=True, null=True)
    subproject_code = models.CharField(max_length=100, blank=True, null=True)
    category = models.CharField(max_length=255, blank=True, null=True)
    center_area = models.CharField(max_length=255, blank=True, null=True)
    product_category = models.CharField(max_length=255, blank=True, null=True)
    bidding_area = models.CharField(max_length=255, blank=True, null=True)
    bill_to = models.TextField(blank=True, null=True)
    ship_to = models.TextField(blank=True, null=True)
    note_to_receiver = models.TextField(blank=True, null=True)
    ff_buyer = models.CharField(max_length=255, blank=True, null=True)
    fob_lookup_code = models.CharField(max_length=100, blank=True, null=True)
    publish_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    expire_date = models.DateField(null=True, blank=True)
    acceptance_date = models.DateField(null=True, blank=True)
    acceptance_date_1 = models.DateField(null=True, blank=True)
    change_history = models.TextField(blank=True, null=True)
    pr_po_automation = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'po_staging'
        indexes = [
            models.Index(fields=['user', 'batch_id'], name='idx_po_staging_user_batch'),
            models.Index(fields=['user', 'po_number', 'po_line_no'], name='idx_po_staging_lookup'),
        ]
    
    def __str__(self):
        return f"PO {self.po_number}-{self.po_line_no}"


class AcceptanceStaging(models.Model):
    """Temporary staging for uploaded Acceptance data"""
    
    staging_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    batch_id = models.UUIDField(db_index=True)
    
    # Processing status
    row_number = models.IntegerField(null=True, blank=True)
    is_processed = models.BooleanField(default=False)
    is_valid = models.BooleanField(default=True)
    validation_errors = models.JSONField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Acceptance Data
    acceptance_no = models.CharField(max_length=100)
    po_number = models.CharField(max_length=100)
    po_line_no = models.CharField(max_length=50)
    shipment_no = models.CharField(max_length=100, blank=True, null=True)
    milestone_type = models.CharField(max_length=50, blank=True, null=True)  # AC1 or AC2
    project_code = models.CharField(max_length=100, blank=True, null=True)
    site_name = models.CharField(max_length=255, blank=True, null=True)
    site_code = models.CharField(max_length=100, blank=True, null=True)
    acceptance_description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    bill_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    accepted_qty = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    center_area = models.CharField(max_length=255, blank=True, null=True)
    planned_completion_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField(null=True, blank=True)
    approver = models.CharField(max_length=255, blank=True, null=True)
    current_handler = models.TextField(blank=True, null=True)
    approval_progress = models.CharField(max_length=100, blank=True, null=True)
    isdp_project = models.CharField(max_length=100, blank=True, null=True)
    application_submitted = models.DateField(null=True, blank=True)
    application_processed = models.DateField(null=True, blank=True)
    header_remarks = models.TextField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    service_code = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    payment_percentage = models.CharField(max_length=50, blank=True, null=True)
    record_status = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        db_table = 'acceptance_staging'
        indexes = [
            models.Index(fields=['user', 'batch_id'], name='idx_acc_staging_user_batch'),
            models.Index(fields=['user', 'po_number', 'po_line_no'], name='idx_acc_staging_lookup'),
        ]
    
    def __str__(self):
        return f"Acceptance {self.acceptance_no}"


# ============================================================================
# MERGED DATA (Physical Table)
# ============================================================================

class MergedData(models.Model):
    """Physical table storing merged PO + Acceptance data"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)    
    # PO Identifier
    po_id = models.CharField(max_length=200, db_index=True)  # Format: "po_number-po_line_no"
    po_number = models.CharField(max_length=100, db_index=True)
    po_line_no = models.CharField(max_length=50)
    
    # Project info
    project_name = models.CharField(max_length=255, blank=True, null=True)
    project_code = models.CharField(max_length=100, blank=True, null=True)
    account_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Site info
    site_name = models.CharField(max_length=255, blank=True, null=True)
    site_code = models.CharField(max_length=100, blank=True, null=True)
    
    # Item info
    item_code = models.CharField(max_length=100, blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=255, blank=True, null=True)
    
    # Pricing
    unit_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    requested_qty = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    line_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    
    # Payment terms
    payment_terms = models.CharField(max_length=255, blank=True, null=True)
    
    # Dates
    publish_date = models.DateField(null=True, blank=True)
    
    # Acceptance data (from LEFT JOIN)
    ac_date = models.DateField(null=True, blank=True)  # AC1 (80%)
    pac_date = models.DateField(null=True, blank=True)  # AC2/PAC (20%)
    
    # Calculated amounts
    ac_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pac_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    remaining = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=50, blank=True, null=True)
    po_status = models.CharField(max_length=50, blank=True, null=True)
    
    # Assignment tracking
    is_assigned = models.BooleanField(default=False, db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_pos'
    )
    
    # External PO tracking
    has_external_po = models.BooleanField(default=False, db_index=True)
    external_po_id = models.UUIDField(null=True, blank=True)
    
    # Merge tracking
    batch_id = models.UUIDField(db_index=True)
    merged_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'merged_data'
        indexes = [
            models.Index(fields=['po_number', 'po_line_no'], name='idx_merged_po'),
            models.Index(fields=['is_assigned'], name='idx_merged_assigned'),
            models.Index(fields=['has_external_po'], name='idx_merged_external'),
            models.Index(fields=['batch_id'], name='idx_merged_batch'),
            models.Index(fields=['status'], name='idx_merged_status'),
        ]
    
    def __str__(self):
        return f"{self.po_id} - {self.project_name}"


# ============================================================================
# UPLOAD & MERGE HISTORY
# ============================================================================

class UploadHistory(models.Model):
    """Tracks file uploads"""
    
    class FileType(models.TextChoices):
        PO = 'PO', 'Purchase Order'
        ACCEPTANCE = 'ACCEPTANCE', 'Acceptance'
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    batch_id = models.UUIDField(unique=True, db_index=True)
    
    file_type = models.CharField(max_length=50, choices=FileType.choices)
    original_filename = models.CharField(max_length=500)
    file_size = models.BigIntegerField(null=True, blank=True)  # bytes
    
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    total_rows = models.IntegerField(default=0)
    valid_rows = models.IntegerField(default=0)
    invalid_rows = models.IntegerField(default=0)
    
    error_message = models.TextField(blank=True, null=True)
    processing_duration = models.IntegerField(null=True, blank=True)  # seconds
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'upload_history'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['user', 'file_type'], name='idx_upload_user_type'),
        ]
    
    def __str__(self):
        return f"{self.file_type} - {self.original_filename}"


class MergeHistory(models.Model):
    """Tracks merge operations"""
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch_id = models.UUIDField(unique=True, db_index=True)
    
    merged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    total_records = models.IntegerField(default=0)
    po_records_count = models.IntegerField(null=True, blank=True)
    acceptance_records_count = models.IntegerField(null=True, blank=True)
    
    po_file = models.ForeignKey(
        UploadHistory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_merges'
    )
    acceptance_file = models.ForeignKey(
        UploadHistory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acceptance_merges'
    )
    
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.COMPLETED)
    error_message = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    merged_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'merge_history'
        ordering = ['-merged_at']
    
    def __str__(self):
        return f"Merge {self.batch_id} - {self.total_records} records"


# ============================================================================
# PERMANENT PO & ACCEPTANCE TABLES
# ============================================================================

class PurchaseOrder(models.Model):
    """Permanent PO data storage"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch_id = models.UUIDField(db_index=True)
    
    # PO Identifier
    po_number = models.CharField(max_length=100, db_index=True)
    po_line_no = models.CharField(max_length=50)
    
    # Project info
    project_name = models.CharField(max_length=255, blank=True, null=True)
    project_code = models.CharField(max_length=100, blank=True, null=True)
    site_name = models.CharField(max_length=255, blank=True, null=True)
    site_code = models.CharField(max_length=100, blank=True, null=True)
    
    # Item info
    item_code = models.CharField(max_length=100, blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    item_description_local = models.TextField(blank=True, null=True)
    
    # Pricing
    unit_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    requested_qty = models.IntegerField(null=True, blank=True)
    due_qty = models.IntegerField(null=True, blank=True)
    billed_qty = models.IntegerField(null=True, blank=True)
    quantity_cancel = models.IntegerField(null=True, blank=True)
    line_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Status & terms
    po_status = models.CharField(max_length=50, blank=True, null=True)
    payment_terms = models.CharField(max_length=255, blank=True, null=True)
    payment_method = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional info
    customer = models.CharField(max_length=255, blank=True, null=True)
    rep_office = models.CharField(max_length=255, blank=True, null=True)
    subcontract_no = models.CharField(max_length=100, blank=True, null=True)
    pr_no = models.CharField(max_length=100, blank=True, null=True)
    sales_contract_no = models.CharField(max_length=100, blank=True, null=True)
    version_no = models.CharField(max_length=50, blank=True, null=True)
    shipment_no = models.CharField(max_length=100, blank=True, null=True)
    
    # Engineering
    engineering_code = models.CharField(max_length=100, blank=True, null=True)
    engineering_name = models.CharField(max_length=255, blank=True, null=True)
    subproject_code = models.CharField(max_length=100, blank=True, null=True)
    
    # Categories
    category = models.CharField(max_length=255, blank=True, null=True)
    center_area = models.CharField(max_length=255, blank=True, null=True)
    product_category = models.CharField(max_length=255, blank=True, null=True)
    bidding_area = models.CharField(max_length=255, blank=True, null=True)
    
    # Text fields
    bill_to = models.TextField(blank=True, null=True)
    ship_to = models.TextField(blank=True, null=True)
    note_to_receiver = models.TextField(blank=True, null=True)
    ff_buyer = models.CharField(max_length=255, blank=True, null=True)
    fob_lookup_code = models.CharField(max_length=100, blank=True, null=True)
    
    # Dates
    publish_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    expire_date = models.DateField(null=True, blank=True)
    acceptance_date = models.DateField(null=True, blank=True)
    acceptance_date_1 = models.DateField(null=True, blank=True)
    
    # Additional
    change_history = models.TextField(blank=True, null=True)
    pr_po_automation = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'purchase_orders'
        unique_together = [['po_number', 'po_line_no', 'batch_id']]
        indexes = [
            models.Index(fields=['batch_id']),
            models.Index(fields=['po_number', 'po_line_no']),
        ]
    
    def __str__(self):
        return f"PO {self.po_number}-{self.po_line_no}"


class Acceptance(models.Model):
    """Permanent Acceptance data storage"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch_id = models.UUIDField(db_index=True)
    
    # Acceptance identifiers
    acceptance_no = models.CharField(max_length=100)
    po_number = models.CharField(max_length=100, db_index=True)
    po_line_no = models.CharField(max_length=50)
    shipment_no = models.CharField(max_length=100, blank=True, null=True)
    milestone_type = models.CharField(max_length=50, blank=True, null=True)  # AC1 or AC2
    
    # Project info
    project_code = models.CharField(max_length=100, blank=True, null=True)
    site_name = models.CharField(max_length=255, blank=True, null=True)
    site_code = models.CharField(max_length=100, blank=True, null=True)
    
    # Description
    acceptance_description = models.TextField(blank=True, null=True)
    
    # Financial
    unit = models.CharField(max_length=50, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    bill_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    accepted_qty = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Area
    center_area = models.CharField(max_length=255, blank=True, null=True)
    
    # Dates
    planned_completion_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField(null=True, blank=True)
    application_submitted = models.DateField(null=True, blank=True)
    application_processed = models.DateField(null=True, blank=True)
    
    # Approval
    approver = models.CharField(max_length=255, blank=True, null=True)
    current_handler = models.TextField(blank=True, null=True)
    approval_progress = models.CharField(max_length=100, blank=True, null=True)
    
    # Project type
    isdp_project = models.CharField(max_length=100, blank=True, null=True)
    
    # Notes
    header_remarks = models.TextField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    
    # Additional
    service_code = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    payment_percentage = models.CharField(max_length=50, blank=True, null=True)
    record_status = models.CharField(max_length=50, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'acceptances'
        unique_together = [['acceptance_no', 'po_number', 'po_line_no', 'batch_id']]
        indexes = [
            models.Index(fields=['batch_id']),
            models.Index(fields=['po_number', 'po_line_no']),
        ]
    
    def __str__(self):
        return f"Acceptance {self.acceptance_no}"

class Account(models.Model):
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account_name = models.CharField(max_length=100)
    project_name = models.CharField(max_length=100)
    needs_review = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

