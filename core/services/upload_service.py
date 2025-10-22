"""
Upload Service - Handle Excel file uploads
"""
import pandas as pd
from django.db import transaction
from django.utils import timezone
from core.models import POStaging, AcceptanceStaging, UploadHistory
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class UploadService:
    """Service for uploading and processing Excel files"""
    
    @staticmethod
    def validate_excel_file(file):
        """Validate uploaded file is Excel"""
        valid_extensions = ['.xlsx', '.xls']
        file_name = file.name.lower()
        
        if not any(file_name.endswith(ext) for ext in valid_extensions):
            raise ValueError("File must be Excel format (.xlsx or .xls)")
        
        if file.size > 10 * 1024 * 1024:  # 10MB limit
            raise ValueError("File size must be less than 10MB")
        
        return True
    
    @staticmethod
    @transaction.atomic
    def upload_po_file(file, user):
        """
        Upload and process PO Excel file
        
        Args:
            file: Uploaded Excel file
            user: User object
            
        Returns:
            dict with upload results
        """
        logger.info(f"Starting PO upload for user: {user.email}")
        
        # Validate file
        UploadService.validate_excel_file(file)
        
        # Generate batch ID
        batch_id = uuid.uuid4()
        
        # Create upload history record
        upload_history = UploadHistory.objects.create(
            user=user,
            batch_id=batch_id,
            file_type=UploadHistory.FileType.PO,
            original_filename=file.name,
            file_size=file.size,
            status=UploadHistory.Status.PROCESSING
        )
        
        try:
            start_time = timezone.now()
            
            # Read Excel file
            df = pd.read_excel(file)
            
            logger.info(f"Excel file read successfully. Rows: {len(df)}")
            
            # Clean column names (strip whitespace, lowercase)
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            # Expected columns (adjust based on your actual Excel structure)
            expected_columns = [
                'po_number', 'po_line_no', 'project_name', 'site_name',
                'item_description', 'unit_price', 'requested_qty', 'line_amount',
                'payment_terms', 'po_status'
            ]
            
            # Replace NaN with None
            df = df.where(pd.notnull(df), None)
            
            # Convert dates
            date_columns = ['publish_date', 'start_date', 'end_date', 'expire_date']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Process rows
            valid_rows = 0
            invalid_rows = 0
            po_records = []
            
            for idx, row in df.iterrows():
                try:
                    # Validate required fields
                    if pd.isna(row.get('po_number')) or pd.isna(row.get('po_line_no')):
                        invalid_rows += 1
                        continue
                    
                    # Create POStaging record
                    po_record = POStaging(
                        user=user,
                        batch_id=batch_id,
                        row_number=idx + 1,
                        is_valid=True,
                        
                        # Required fields
                        po_number=str(row.get('po_number', '')),
                        po_line_no=str(row.get('po_line_no', '')),
                        
                        # Project info
                        project_name=row.get('project_name'),
                        project_code=row.get('project_code'),
                        site_name=row.get('site_name'),
                        site_code=row.get('site_code'),
                        
                        # Item info
                        item_code=row.get('item_code'),
                        item_description=row.get('item_description'),
                        item_description_local=row.get('item_description_local'),
                        
                        # Pricing
                        unit_price=row.get('unit_price'),
                        requested_qty=row.get('requested_qty'),
                        due_qty=row.get('due_qty'),
                        billed_qty=row.get('billed_qty'),
                        quantity_cancel=row.get('quantity_cancel'),
                        line_amount=row.get('line_amount'),
                        unit=row.get('unit'),
                        currency=row.get('currency'),
                        tax_rate=row.get('tax_rate'),
                        
                        # Status & terms
                        po_status=row.get('po_status'),
                        payment_terms=row.get('payment_terms'),
                        payment_method=row.get('payment_method'),
                        
                        # Additional info
                        customer=row.get('customer'),
                        rep_office=row.get('rep_office'),
                        subcontract_no=row.get('subcontract_no'),
                        pr_no=row.get('pr_no'),
                        sales_contract_no=row.get('sales_contract_no'),
                        version_no=row.get('version_no'),
                        shipment_no=row.get('shipment_no'),
                        
                        # Engineering
                        engineering_code=row.get('engineering_code'),
                        engineering_name=row.get('engineering_name'),
                        subproject_code=row.get('subproject_code'),
                        
                        # Categories
                        category=row.get('category'),
                        center_area=row.get('center_area'),
                        product_category=row.get('product_category'),
                        bidding_area=row.get('bidding_area'),
                        
                        # Text fields
                        bill_to=row.get('bill_to'),
                        ship_to=row.get('ship_to'),
                        note_to_receiver=row.get('note_to_receiver'),
                        ff_buyer=row.get('ff_buyer'),
                        fob_lookup_code=row.get('fob_lookup_code'),
                        
                        # Dates
                        publish_date=row.get('publish_date'),
                        start_date=row.get('start_date'),
                        end_date=row.get('end_date'),
                        expire_date=row.get('expire_date'),
                        acceptance_date=row.get('acceptance_date'),
                        acceptance_date_1=row.get('acceptance_date_1'),
                        
                        # Additional
                        change_history=row.get('change_history'),
                        pr_po_automation=row.get('pr_po_automation'),
                    )
                    
                    po_records.append(po_record)
                    valid_rows += 1
                    
                except Exception as e:
                    logger.error(f"Error processing row {idx}: {str(e)}")
                    invalid_rows += 1
                    continue
            
            # Bulk create
            POStaging.objects.bulk_create(po_records, batch_size=1000)
            
            # Calculate duration
            duration = (timezone.now() - start_time).total_seconds()
            
            # Update upload history
            upload_history.status = UploadHistory.Status.COMPLETED
            upload_history.total_rows = len(df)
            upload_history.valid_rows = valid_rows
            upload_history.invalid_rows = invalid_rows
            upload_history.processing_duration = int(duration)
            upload_history.processed_at = timezone.now()
            upload_history.save()
            
            logger.info(f"PO upload completed. Valid: {valid_rows}, Invalid: {invalid_rows}")
            
            return {
                'success': True,
                'batch_id': str(batch_id),
                'total_rows': len(df),
                'valid_rows': valid_rows,
                'invalid_rows': invalid_rows,
                'processing_duration': duration,
                'upload_history_id': str(upload_history.id)
            }
            
        except Exception as e:
            logger.error(f"PO upload failed: {str(e)}")
            
            # Update upload history as failed
            upload_history.status = UploadHistory.Status.FAILED
            upload_history.error_message = str(e)
            upload_history.processed_at = timezone.now()
            upload_history.save()
            
            raise
    
    @staticmethod
    @transaction.atomic
    def upload_acceptance_file(file, user):
        """
        Upload and process Acceptance Excel file
        
        Args:
            file: Uploaded Excel file
            user: User object
            
        Returns:
            dict with upload results
        """
        logger.info(f"Starting Acceptance upload for user: {user.email}")
        
        # Validate file
        UploadService.validate_excel_file(file)
        
        # Generate batch ID
        batch_id = uuid.uuid4()
        
        # Create upload history record
        upload_history = UploadHistory.objects.create(
            user=user,
            batch_id=batch_id,
            file_type=UploadHistory.FileType.ACCEPTANCE,
            original_filename=file.name,
            file_size=file.size,
            status=UploadHistory.Status.PROCESSING
        )
        
        try:
            start_time = timezone.now()
            
            # Read Excel file
            df = pd.read_excel(file)
            
            logger.info(f"Excel file read successfully. Rows: {len(df)}")
            
            # Clean column names
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            # Replace NaN with None
            df = df.where(pd.notnull(df), None)
            
            # Convert dates
            date_columns = ['planned_completion_date', 'actual_completion_date', 
                          'application_submitted', 'application_processed']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Process rows
            valid_rows = 0
            invalid_rows = 0
            acceptance_records = []
            
            for idx, row in df.iterrows():
                try:
                    # Validate required fields
                    if pd.isna(row.get('po_number')) or pd.isna(row.get('po_line_no')):
                        invalid_rows += 1
                        continue
                    
                    # Create AcceptanceStaging record
                    acceptance_record = AcceptanceStaging(
                        user=user,
                        batch_id=batch_id,
                        row_number=idx + 1,
                        is_valid=True,
                        
                        # Required fields
                        acceptance_no=str(row.get('acceptance_no', '')),
                        po_number=str(row.get('po_number', '')),
                        po_line_no=str(row.get('po_line_no', '')),
                        
                        # Milestone
                        milestone_type=row.get('milestone_type'),  # AC1 or AC2
                        shipment_no=row.get('shipment_no'),
                        
                        # Project info
                        project_code=row.get('project_code'),
                        site_name=row.get('site_name'),
                        site_code=row.get('site_code'),
                        
                        # Description
                        acceptance_description=row.get('acceptance_description'),
                        
                        # Financial
                        unit=row.get('unit'),
                        currency=row.get('currency'),
                        bill_amount=row.get('bill_amount'),
                        tax_amount=row.get('tax_amount'),
                        accepted_qty=row.get('accepted_qty'),
                        
                        # Area
                        center_area=row.get('center_area'),
                        
                        # Dates
                        planned_completion_date=row.get('planned_completion_date'),
                        actual_completion_date=row.get('actual_completion_date'),
                        application_submitted=row.get('application_submitted'),
                        application_processed=row.get('application_processed'),
                        
                        # Approval
                        approver=row.get('approver'),
                        current_handler=row.get('current_handler'),
                        approval_progress=row.get('approval_progress'),
                        
                        # Project type
                        isdp_project=row.get('isdp_project'),
                        
                        # Notes
                        header_remarks=row.get('header_remarks'),
                        remarks=row.get('remarks'),
                        
                        # Additional
                        service_code=row.get('service_code'),
                        payment_percentage=row.get('payment_percentage'),
                        record_status=row.get('record_status'),
                    )
                    
                    acceptance_records.append(acceptance_record)
                    valid_rows += 1
                    
                except Exception as e:
                    logger.error(f"Error processing row {idx}: {str(e)}")
                    invalid_rows += 1
                    continue
            
            # Bulk create
            AcceptanceStaging.objects.bulk_create(acceptance_records, batch_size=1000)
            
            # Calculate duration
            duration = (timezone.now() - start_time).total_seconds()
            
            # Update upload history
            upload_history.status = UploadHistory.Status.COMPLETED
            upload_history.total_rows = len(df)
            upload_history.valid_rows = valid_rows
            upload_history.invalid_rows = invalid_rows
            upload_history.processing_duration = int(duration)
            upload_history.processed_at = timezone.now()
            upload_history.save()
            
            logger.info(f"Acceptance upload completed. Valid: {valid_rows}, Invalid: {invalid_rows}")
            
            return {
                'success': True,
                'batch_id': str(batch_id),
                'total_rows': len(df),
                'valid_rows': valid_rows,
                'invalid_rows': invalid_rows,
                'processing_duration': duration,
                'upload_history_id': str(upload_history.id)
            }
            
        except Exception as e:
            logger.error(f"Acceptance upload failed: {str(e)}")
            
            # Update upload history as failed
            upload_history.status = UploadHistory.Status.FAILED
            upload_history.error_message = str(e)
            upload_history.processed_at = timezone.now()
            upload_history.save()
            
            raise