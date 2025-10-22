# core/services/upload_service.py

import logging
from django.db import transaction
from django.utils import timezone
from core.models import POStaging, AcceptanceStaging, PurchaseOrder, Acceptance, UploadHistory
import uuid

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
        """Upload and process PO Excel file with UPSERT logic"""
        logger.info(f"[PO] Starting upload for user: {user.email}")
        
        # Validate file
        UploadService.validate_excel_file(file)
        
        # Create upload history record
        batch_id = uuid.uuid4()
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
            
            # Step 1: Process file → POStaging (with validation)
            processor = POProcessor()
            result = processor.process_file(file, user)
            
            # Step 2: UPSERT logic - Update existing or Insert new
            logger.info(f"[PO] Starting UPSERT operation...")
            
            po_staging_records = POStaging.objects.filter(
                user=user,
                batch_id=result['batch_id'],
                is_valid=True
            )
            
            # Track statistics
            inserted_count = 0
            updated_count = 0
            skipped_count = 0
            
            # Process each staging record
            for po_staging in po_staging_records:
                try:
                    # Check if PO already exists (match on po_number + po_line_no)
                    existing_po = PurchaseOrder.objects.filter(
                        po_number=po_staging.po_number,
                        po_line_no=po_staging.po_line_no
                    ).first()
                    
                    # Prepare data dictionary
                    po_data = {
                        'batch_id': result['batch_id'],
                        'po_number': po_staging.po_number,
                        'po_line_no': po_staging.po_line_no,
                        'project_name': po_staging.project_name,
                        'project_code': po_staging.project_code,
                        'site_name': po_staging.site_name,
                        'site_code': po_staging.site_code,
                        'item_code': po_staging.item_code,
                        'item_description': po_staging.item_description,
                        'item_description_local': po_staging.item_description_local,
                        'unit_price': po_staging.unit_price,
                        'requested_qty': po_staging.requested_qty,
                        'due_qty': po_staging.due_qty,
                        'billed_qty': po_staging.billed_qty,
                        'quantity_cancel': po_staging.quantity_cancel,
                        'line_amount': po_staging.line_amount,
                        'unit': po_staging.unit,
                        'currency': po_staging.currency,
                        'tax_rate': po_staging.tax_rate,
                        'po_status': po_staging.po_status,
                        'payment_terms': po_staging.payment_terms,
                        'payment_method': po_staging.payment_method,
                        'customer': po_staging.customer,
                        'rep_office': po_staging.rep_office,
                        'subcontract_no': po_staging.subcontract_no,
                        'pr_no': po_staging.pr_no,
                        'sales_contract_no': po_staging.sales_contract_no,
                        'version_no': po_staging.version_no,
                        'shipment_no': po_staging.shipment_no,
                        'engineering_code': po_staging.engineering_code,
                        'engineering_name': po_staging.engineering_name,
                        'subproject_code': po_staging.subproject_code,
                        'category': po_staging.category,
                        'center_area': po_staging.center_area,
                        'product_category': po_staging.product_category,
                        'bidding_area': po_staging.bidding_area,
                        'bill_to': po_staging.bill_to,
                        'ship_to': po_staging.ship_to,
                        'note_to_receiver': po_staging.note_to_receiver,
                        'ff_buyer': po_staging.ff_buyer,
                        'fob_lookup_code': po_staging.fob_lookup_code,
                        'publish_date': po_staging.publish_date,
                        'start_date': po_staging.start_date,
                        'end_date': po_staging.end_date,
                        'expire_date': po_staging.expire_date,
                        'acceptance_date': po_staging.acceptance_date,
                        'acceptance_date_1': po_staging.acceptance_date_1,
                        'change_history': po_staging.change_history,
                        'pr_po_automation': po_staging.pr_po_automation,
                    }
                    
                    if existing_po:
                        # UPDATE existing record
                        for field, value in po_data.items():
                            setattr(existing_po, field, value)
                        existing_po.save()
                        updated_count += 1
                        logger.debug(f"[PO] Updated: {po_staging.po_number}-{po_staging.po_line_no}")
                    else:
                        # INSERT new record
                        PurchaseOrder.objects.create(**po_data)
                        inserted_count += 1
                        logger.debug(f"[PO] Inserted: {po_staging.po_number}-{po_staging.po_line_no}")
                
                except Exception as e:
                    logger.error(f"[PO] Failed to upsert {po_staging.po_number}-{po_staging.po_line_no}: {e}")
                    skipped_count += 1
                    continue
            
            logger.info(f"[PO] UPSERT complete: {inserted_count} inserted, {updated_count} updated, {skipped_count} skipped")
            
            # Step 3: Clear staging table
            POStaging.objects.filter(user=user, batch_id=result['batch_id']).delete()
            logger.info(f"[PO] Cleared staging table")
            
            # Calculate duration
            duration = (timezone.now() - start_time).total_seconds()
            
            # Update upload history
            upload_history.status = UploadHistory.Status.COMPLETED
            upload_history.total_rows = result['total_rows']
            upload_history.valid_rows = result['valid_rows']
            upload_history.invalid_rows = result['invalid_rows']
            upload_history.processing_duration = int(duration)
            upload_history.processed_at = timezone.now()
            upload_history.save()
            
            logger.info(f"[PO] Upload completed. Valid: {result['valid_rows']}, Invalid: {result['invalid_rows']}")
            
            return {
                'success': True,
                'batch_id': str(result['batch_id']),
                'total_rows': result['total_rows'],
                'valid_rows': result['valid_rows'],
                'invalid_rows': result['invalid_rows'],
                'inserted_count': inserted_count,
                'updated_count': updated_count,
                'skipped_count': skipped_count,
                'processing_duration': duration,
                'upload_history_id': str(upload_history.id),
                'validation_errors': result.get('validation_errors', [])
            }
            
        except Exception as e:
            logger.error(f"[PO] Upload failed: {str(e)}", exc_info=True)
            
            # Update upload history as failed
            upload_history.status = UploadHistory.Status.FAILED
            upload_history.error_message = str(e)
            upload_history.processed_at = timezone.now()
            upload_history.save()
            
            raise
    
    @staticmethod
    @transaction.atomic
    def upload_acceptance_file(file, user):
        """Upload and process Acceptance Excel file with UPSERT logic"""
        logger.info(f"[ACCEPTANCE] Starting upload for user: {user.email}")
        
        # Validate file
        UploadService.validate_excel_file(file)
        
        # Create upload history record
        batch_id = uuid.uuid4()
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
            
            # Step 1: Process file → AcceptanceStaging
            processor = AcceptanceProcessor()
            result = processor.process_file(file, user)
            
            # Step 2: UPSERT logic
            logger.info(f"[ACCEPTANCE] Starting UPSERT operation...")
            
            acc_staging_records = AcceptanceStaging.objects.filter(
                user=user,
                batch_id=result['batch_id'],
                is_valid=True
            )
            
            # Track statistics
            inserted_count = 0
            updated_count = 0
            skipped_count = 0
            
            # Process each staging record
            for acc_staging in acc_staging_records:
                try:
                    # Check if Acceptance already exists
                    # Match on: acceptance_no + po_number + po_line_no
                    existing_acc = Acceptance.objects.filter(
                        acceptance_no=acc_staging.acceptance_no,
                        po_number=acc_staging.po_number,
                        po_line_no=acc_staging.po_line_no
                    ).first()
                    
                    # Prepare data dictionary
                    acc_data = {
                        'batch_id': result['batch_id'],
                        'acceptance_no': acc_staging.acceptance_no,
                        'po_number': acc_staging.po_number,
                        'po_line_no': acc_staging.po_line_no,
                        'shipment_no': acc_staging.shipment_no,
                        'milestone_type': acc_staging.milestone_type,
                        'project_code': acc_staging.project_code,
                        'site_name': acc_staging.site_name,
                        'site_code': acc_staging.site_code,
                        'acceptance_description': acc_staging.acceptance_description,
                        'unit': acc_staging.unit,
                        'currency': acc_staging.currency,
                        'bill_amount': acc_staging.bill_amount,
                        'tax_amount': acc_staging.tax_amount,
                        'accepted_qty': acc_staging.accepted_qty,
                        'center_area': acc_staging.center_area,
                        'planned_completion_date': acc_staging.planned_completion_date,
                        'actual_completion_date': acc_staging.actual_completion_date,
                        'application_submitted': acc_staging.application_submitted,
                        'application_processed': acc_staging.application_processed,
                        'approver': acc_staging.approver,
                        'current_handler': acc_staging.current_handler,
                        'approval_progress': acc_staging.approval_progress,
                        'isdp_project': acc_staging.isdp_project,
                        'header_remarks': acc_staging.header_remarks,
                        'remarks': acc_staging.remarks,
                        'service_code': acc_staging.service_code,
                        'payment_percentage': acc_staging.payment_percentage,
                        'record_status': acc_staging.record_status,
                    }
                    
                    if existing_acc:
                        # UPDATE existing record
                        for field, value in acc_data.items():
                            setattr(existing_acc, field, value)
                        existing_acc.save()
                        updated_count += 1
                        logger.debug(f"[ACCEPTANCE] Updated: {acc_staging.acceptance_no}")
                    else:
                        # INSERT new record
                        Acceptance.objects.create(**acc_data)
                        inserted_count += 1
                        logger.debug(f"[ACCEPTANCE] Inserted: {acc_staging.acceptance_no}")
                
                except Exception as e:
                    logger.error(f"[ACCEPTANCE] Failed to upsert {acc_staging.acceptance_no}: {e}")
                    skipped_count += 1
                    continue
            
            logger.info(f"[ACCEPTANCE] UPSERT complete: {inserted_count} inserted, {updated_count} updated, {skipped_count} skipped")
            
            # Step 3: Clear staging table
            AcceptanceStaging.objects.filter(user=user, batch_id=result['batch_id']).delete()
            logger.info(f"[ACCEPTANCE] Cleared staging table")
            
            # Calculate duration
            duration = (timezone.now() - start_time).total_seconds()
            
            # Update upload history
            upload_history.status = UploadHistory.Status.COMPLETED
            upload_history.total_rows = result['total_rows']
            upload_history.valid_rows = result['valid_rows']
            upload_history.invalid_rows = result['invalid_rows']
            upload_history.processing_duration = int(duration)
            upload_history.processed_at = timezone.now()
            upload_history.save()
            
            logger.info(f"[ACCEPTANCE] Upload completed. Valid: {result['valid_rows']}, Invalid: {result['invalid_rows']}")
            
            return {
                'success': True,
                'batch_id': str(result['batch_id']),
                'total_rows': result['total_rows'],
                'valid_rows': result['valid_rows'],
                'invalid_rows': result['invalid_rows'],
                'inserted_count': inserted_count,
                'updated_count': updated_count,
                'skipped_count': skipped_count,
                'processing_duration': duration,
                'upload_history_id': str(upload_history.id),
                'validation_errors': result.get('validation_errors', [])
            }
            
        except Exception as e:
            logger.error(f"[ACCEPTANCE] Upload failed: {str(e)}", exc_info=True)
            
            # Update upload history as failed
            upload_history.status = UploadHistory.Status.FAILED
            upload_history.error_message = str(e)
            upload_history.processed_at = timezone.now()
            upload_history.save()
            
            raise