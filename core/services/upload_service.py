import pandas as pd
import uuid
import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Any, Optional
from django.db import transaction
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from core.services.account_service import AccountService
from core.models import (
    POStaging, AcceptanceStaging, UploadHistory,
    PurchaseOrder, Acceptance
)

logger = logging.getLogger(__name__)

class UploadService:
    @staticmethod
    def upload_po_file(file, user):
        batch_id = uuid.uuid4()
        
        # Save file temporarily
        file_name = default_storage.save(f'temp/{batch_id}_{file.name}', ContentFile(file.read()))
        file_path = default_storage.path(file_name)
        
        # Create upload history
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
            processor = POProcessor(batch_id)
            processor.process_file(file_path)
            
            end_time = timezone.now()
            duration = int((end_time - start_time).total_seconds())
            
            # Update upload history
            upload_history.status = UploadHistory.Status.COMPLETED
            upload_history.total_rows = processor.stats['total_rows']
            upload_history.valid_rows = processor.stats['valid_rows']
            upload_history.invalid_rows = processor.stats['invalid_rows']
            upload_history.processing_duration = duration
            upload_history.processed_at = end_time
            upload_history.save()
            
            # Clean up temp file
            default_storage.delete(file_name)
            
            return {
                'success': True,
                'batch_id': str(batch_id),
                'total_rows': processor.stats['total_rows'],
                'valid_rows': processor.stats['valid_rows'],
                'invalid_rows': processor.stats['invalid_rows'],
                'processing_duration': duration
            }
            
        except Exception as e:
            logger.error(f"PO upload failed: {str(e)}", exc_info=True)
            
            # Update upload history
            upload_history.status = UploadHistory.Status.FAILED
            upload_history.error_message = str(e)
            upload_history.save()
            
            # Clean up temp file
            try:
                default_storage.delete(file_name)
            except:
                pass
            
            raise ValueError(f"Upload failed: {str(e)}")
    
    @staticmethod
    def upload_acceptance_file(file, user):
        batch_id = uuid.uuid4()
        
        # Save file temporarily
        file_name = default_storage.save(f'temp/{batch_id}_{file.name}', ContentFile(file.read()))
        file_path = default_storage.path(file_name)
        
        # Create upload history
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
            
            # Process file
            processor = AcceptanceProcessor(batch_id)
            processor.process_file(file_path)
            
            end_time = timezone.now()
            duration = int((end_time - start_time).total_seconds())
            
            # Update upload history
            upload_history.status = UploadHistory.Status.COMPLETED
            upload_history.total_rows = processor.stats['total_rows']
            upload_history.valid_rows = processor.stats['valid_rows']
            upload_history.invalid_rows = processor.stats['invalid_rows']
            upload_history.processing_duration = duration
            upload_history.processed_at = end_time
            upload_history.save()
            
            # Clean up temp file
            default_storage.delete(file_name)
            
            return {
                'success': True,
                'batch_id': str(batch_id),
                'total_rows': processor.stats['total_rows'],
                'valid_rows': processor.stats['valid_rows'],
                'invalid_rows': processor.stats['invalid_rows'],
                'processing_duration': duration
            }
            
        except Exception as e:
            logger.error(f"Acceptance upload failed: {str(e)}", exc_info=True)
            
            # Update upload history
            upload_history.status = UploadHistory.Status.FAILED
            upload_history.error_message = str(e)
            upload_history.save()
            
            # Clean up temp file
            try:
                default_storage.delete(file_name)
            except:
                pass
            
            raise ValueError(f"Upload failed: {str(e)}")

class BaseProcessor:
    """Base processor for file uploads"""
    
    def __init__(self, batch_id):
        self.batch_id = batch_id
        self.stats = {
            'total_rows': 0,
            'valid_rows': 0,
            'invalid_rows': 0,
            'validation_errors': []
        }
        self.column_mapping = {}
        self.staging_model = None
    
    def normalize_column_name(self, col_name: str) -> str:
        """Normalize column names"""
        return col_name.strip().lower().replace(' ', '_').replace('(', '_').replace(')', '_').replace('__', '_').strip('_')
    
    def map_csv_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map CSV columns to database fields"""
        df.columns = [self.normalize_column_name(col) for col in df.columns]
        mapped_data = {}
        
        for csv_col, db_field in self.column_mapping.items():
            if csv_col in df.columns:
                mapped_data[db_field] = df[csv_col]
            else:
                mapped_data[db_field] = pd.Series([None] * len(df))
        
        return pd.DataFrame(mapped_data)
    
    def parse_date(self, date_str: Any) -> Optional[date]:
        """Parse various date formats"""
        if not date_str or pd.isna(date_str) or str(date_str).strip() == '':
            return None
        
        date_formats = [
            '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y',
            '%Y/%m/%d', '%d.%m.%Y', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M'
        ]
        
        date_str = str(date_str).strip()
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None
    
    def parse_decimal(self, value: Any) -> Optional[Decimal]:
        """Parse decimal values"""
        if pd.isna(value) or value == '' or value is None:
            return None
        try:
            str_value = str(value).strip().replace(',', '').replace(' ', '').replace('%', '')
            if str_value == '':
                return None
            return Decimal(str_value)
        except (InvalidOperation, ValueError):
            logger.warning(f"Could not parse decimal: {value}")
            return None
    
    def parse_integer(self, value: Any) -> Optional[int]:
        """Parse integer values"""
        if pd.isna(value) or value == '' or value is None:
            return None
        try:
            return int(float(str(value)))
        except (ValueError, OverflowError):
            return None
    
    def safe_string_truncate(self, value: Any, max_length: int = None) -> Optional[str]:
        """Safely truncate string values"""
        if pd.isna(value) or value == '' or value is None:
            return None
        str_value = str(value).strip()
        if max_length and len(str_value) > max_length:
            return str_value[:max_length]
        return str_value if str_value else None
    
    def validate_record(self, record: Dict[str, Any], row_num: int) -> List[Dict[str, str]]:
        """Validate a single record - should be overridden"""
        return []
    
    def process_file(self, file_path: str):
        """Process uploaded file"""
        raise NotImplementedError("Must be implemented by subclass")

class POProcessor(BaseProcessor):
    def __init__(self, batch_id):
        super().__init__(batch_id)
        self.staging_model = POStaging
        self.column_mapping = {
            'po_no.': 'po_number',
            'po_line_no.': 'po_line_no',
            'project_name': 'project_name',
            'project_code': 'project_code',
            'site_name': 'site_name',
            'site_code': 'site_code',
            'item_code': 'item_code',
            'item_description': 'item_description',
            'item_description_local': 'item_description_local',
            'unit_price': 'unit_price',
            'requested_qty': 'requested_qty',
            'due_qty': 'due_qty',
            'billed_quantity': 'billed_qty',
            'quantity_cancel': 'quantity_cancel',
            'line_amount': 'line_amount',
            'unit': 'unit',
            'currency': 'currency',
            'tax_rate': 'tax_rate',
            'po_status': 'po_status',
            'payment_terms': 'payment_terms',
            'payment_method': 'payment_method',
            'customer': 'customer',
            'rep_office': 'rep_office',
            'sub_contract_no.': 'subcontract_no',
            'pr_no.': 'pr_no',
            'sales_contract_no.': 'sales_contract_no',
            'version_no.': 'version_no',
            'shipment_no.': 'shipment_no',
            'engineering_code': 'engineering_code',
            'engineering_name': 'engineering_name',
            'subproject_code': 'subproject_code',
            'category': 'category',
            'center_area': 'center_area',
            'product_category': 'product_category',
            'bidding_area': 'bidding_area',
            'bill_to': 'bill_to',
            'ship_to': 'ship_to',
            'note_to_receiver': 'note_to_receiver',
            'ff_buyer': 'ff_buyer',
            'fob_lookup_code': 'fob_lookup_code',
            'publish_date': 'publish_date',
            'start_date': 'start_date',
            'end_date': 'end_date',
            'expire_date': 'expire_date',
            'acceptance_date': 'acceptance_date',
            'acceptance_date_1': 'acceptance_date_1',
            'change_history': 'change_history',
            'pr_po_automation': 'pr_po_automation',
        }
    
    def validate_record(self, record: Dict[str, Any], row_num: int) -> List[Dict[str, str]]:
        """Validate PO record"""
        errors = []
        
        if not record.get('po_number') or str(record.get('po_number')).strip() == '':
            errors.append({
                'row': row_num,
                'field': 'po_number',
                'error': 'PO Number is required'
            })
        
        if not record.get('po_line_no') or str(record.get('po_line_no')).strip() == '':
            errors.append({
                'row': row_num,
                'field': 'po_line_no',
                'error': 'PO Line Number is required'
            })
        
        return errors
    
    @transaction.atomic
    def process_file(self, file_path: str):
        """Process PO file - COMPANY-WIDE with UPSERT logic"""
        logger.info(f"Processing PO file: {file_path}")
        
        # Read file
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
            else:
                df = pd.read_excel(file_path, dtype=str, keep_default_na=False)
        except Exception as e:
            raise ValueError(f"Failed to read file: {str(e)}")
        
        # Map columns
        df_mapped = self.map_csv_columns(df)
        self.stats['total_rows'] = len(df_mapped)
        
        # Delete ALL old staging data (staging is always replaced)
        logger.info("Deleting old PO staging data...")
        deleted_count = POStaging.objects.all().delete()
        logger.info(f"Deleted {deleted_count[0]} old PO staging records")
        
        # Process rows
        staging_records = []
        po_updates = []  # For updating existing POs
        po_inserts = []  # For inserting new POs
        
        # Track which PO numbers+lines we've seen in the new file
        new_file_po_keys = set()
        
        for idx, row in df_mapped.iterrows():
            try:
                record_data = {}
                
                # Parse all fields (keeping your existing parsing logic)
                record_data['po_number'] = self.safe_string_truncate(row.get('po_number'), 100)
                record_data['po_line_no'] = self.safe_string_truncate(row.get('po_line_no'), 50)
                record_data['project_name'] = self.safe_string_truncate(row.get('project_name'), 255)
                record_data['project_code'] = self.safe_string_truncate(row.get('project_code'), 100)
                record_data['site_name'] = self.safe_string_truncate(row.get('site_name'), 255)
                record_data['site_code'] = self.safe_string_truncate(row.get('site_code'), 100)
                record_data['item_code'] = self.safe_string_truncate(row.get('item_code'), 100)
                record_data['item_description'] = row.get('item_description')
                record_data['item_description_local'] = row.get('item_description_local')
                record_data['unit_price'] = self.parse_decimal(row.get('unit_price'))
                record_data['requested_qty'] = self.parse_integer(row.get('requested_qty'))
                record_data['due_qty'] = self.parse_integer(row.get('due_qty'))
                record_data['billed_qty'] = self.parse_integer(row.get('billed_qty'))
                record_data['quantity_cancel'] = self.parse_integer(row.get('quantity_cancel'))
                record_data['line_amount'] = self.parse_decimal(row.get('line_amount'))
                record_data['unit'] = self.safe_string_truncate(row.get('unit'), 50)
                record_data['currency'] = self.safe_string_truncate(row.get('currency'), 10)
                record_data['tax_rate'] = self.parse_decimal(row.get('tax_rate'))
                record_data['po_status'] = self.safe_string_truncate(row.get('po_status'), 50)
                record_data['payment_terms'] = self.safe_string_truncate(row.get('payment_terms'), 255)
                record_data['payment_method'] = self.safe_string_truncate(row.get('payment_method'), 100)
                record_data['customer'] = self.safe_string_truncate(row.get('customer'), 255)
                record_data['rep_office'] = self.safe_string_truncate(row.get('rep_office'), 255)
                record_data['subcontract_no'] = self.safe_string_truncate(row.get('subcontract_no'), 100)
                record_data['pr_no'] = self.safe_string_truncate(row.get('pr_no'), 100)
                record_data['sales_contract_no'] = self.safe_string_truncate(row.get('sales_contract_no'), 100)
                record_data['version_no'] = self.safe_string_truncate(row.get('version_no'), 50)
                record_data['shipment_no'] = self.safe_string_truncate(row.get('shipment_no'), 100)
                record_data['engineering_code'] = self.safe_string_truncate(row.get('engineering_code'), 100)
                record_data['engineering_name'] = self.safe_string_truncate(row.get('engineering_name'), 255)
                record_data['subproject_code'] = self.safe_string_truncate(row.get('subproject_code'), 100)
                record_data['category'] = self.safe_string_truncate(row.get('category'), 255)
                record_data['center_area'] = self.safe_string_truncate(row.get('center_area'), 255)
                record_data['product_category'] = self.safe_string_truncate(row.get('product_category'), 255)
                record_data['bidding_area'] = self.safe_string_truncate(row.get('bidding_area'), 255)
                record_data['bill_to'] = row.get('bill_to')
                record_data['ship_to'] = row.get('ship_to')
                record_data['note_to_receiver'] = row.get('note_to_receiver')
                record_data['ff_buyer'] = self.safe_string_truncate(row.get('ff_buyer'), 255)
                record_data['fob_lookup_code'] = self.safe_string_truncate(row.get('fob_lookup_code'), 100)
                record_data['publish_date'] = self.parse_date(row.get('publish_date'))
                record_data['start_date'] = self.parse_date(row.get('start_date'))
                record_data['end_date'] = self.parse_date(row.get('end_date'))
                record_data['expire_date'] = self.parse_date(row.get('expire_date'))
                record_data['acceptance_date'] = self.parse_date(row.get('acceptance_date'))
                record_data['acceptance_date_1'] = self.parse_date(row.get('acceptance_date_1'))
                record_data['change_history'] = row.get('change_history')
                record_data['pr_po_automation'] = row.get('pr_po_automation')
                
                # Validate
                validation_errors = self.validate_record(record_data, idx + 2)
                is_valid = len(validation_errors) == 0
                
                if not is_valid:
                    self.stats['invalid_rows'] += 1
                else:
                    self.stats['valid_rows'] += 1
                
                # Create staging record (always)
                staging_record = POStaging(
                    batch_id=self.batch_id,
                    row_number=idx + 2,
                    is_valid=is_valid,
                    validation_errors=validation_errors,
                    **record_data
                )
                staging_records.append(staging_record)
                
                # For permanent table: only process valid records
                if is_valid and record_data['po_number'] and record_data['po_line_no']:
                    po_key = (record_data['po_number'], record_data['po_line_no'])
                    new_file_po_keys.add(po_key)
                    
                    # Check if this PO already exists in permanent table
                    from core.models import PurchaseOrder
                    existing_po = PurchaseOrder.objects.filter(
                        po_number=record_data['po_number'],
                        po_line_no=record_data['po_line_no']
                    ).first()
                    
                    if existing_po:
                        # UPDATE: Record exists, update it
                        for field, value in record_data.items():
                            setattr(existing_po, field, value)
                        existing_po.batch_id = self.batch_id
                        po_updates.append(existing_po)
                    else:
                        # INSERT: New record
                        new_po = PurchaseOrder(
                            batch_id=self.batch_id,
                            **record_data
                        )
                        po_inserts.append(new_po)
                
            except Exception as e:
                logger.error(f"Error processing row {idx + 2}: {str(e)}")
                self.stats['invalid_rows'] += 1
        
        # Bulk create staging records (always replace)
        POStaging.objects.bulk_create(staging_records, batch_size=1000)
        logger.info(f"Created {len(staging_records)} PO staging records")
        
        # Bulk update existing POs
        from core.models import PurchaseOrder
        if po_updates:
            PurchaseOrder.objects.bulk_update(
                po_updates,
                fields=[
                    'project_name', 'project_code', 'site_name', 'site_code',
                    'item_code', 'item_description', 'item_description_local',
                    'unit_price', 'requested_qty', 'due_qty', 'billed_qty',
                    'quantity_cancel', 'line_amount', 'unit', 'currency',
                    'tax_rate', 'po_status', 'payment_terms', 'payment_method',
                    'customer', 'rep_office', 'subcontract_no', 'pr_no',
                    'sales_contract_no', 'version_no', 'shipment_no',
                    'engineering_code', 'engineering_name', 'subproject_code',
                    'category', 'center_area', 'product_category', 'bidding_area',
                    'bill_to', 'ship_to', 'note_to_receiver', 'ff_buyer',
                    'fob_lookup_code', 'publish_date', 'start_date', 'end_date',
                    'expire_date', 'acceptance_date', 'acceptance_date_1',
                    'change_history', 'pr_po_automation', 'batch_id'
                ],
                batch_size=1000
            )
            logger.info(f"Updated {len(po_updates)} existing PO records")
        
        # Bulk insert new POs
        if po_inserts:
            PurchaseOrder.objects.bulk_create(po_inserts, batch_size=1000)
            logger.info(f"Inserted {len(po_inserts)} new PO records")
        
        # Count kept records (old records not in new file)
        from core.models import PurchaseOrder
        total_in_db = PurchaseOrder.objects.count()
        kept_count = total_in_db - len(po_updates) - len(po_inserts)
        logger.info(f"Kept {kept_count} historical PO records (not in new file)")
        logger.info("Extracting accounts from processed PO data...")
        unique_projects = set()
        
        for record in po_inserts + po_updates:
            if record.project_name:
                unique_projects.add(record.project_name.strip())
        
        account_created = 0
        for project_name in unique_projects:
            if project_name:
                try:
                    AccountService.get_or_create_account(project_name)
                    account_created += 1
                except Exception as e:
                    logger.warning(f"Failed to create account for '{project_name}': {str(e)}")
        
        logger.info(f"Processed {len(unique_projects)} unique projects, created/verified {account_created} accounts")
        logger.info(f"PO Processing Summary: {len(po_updates)} updated, {len(po_inserts)} inserted, {kept_count} kept")

class AcceptanceProcessor(BaseProcessor):
    """Acceptance Upload Processor"""
    
    def __init__(self, batch_id):
        super().__init__(batch_id)
        self.staging_model = AcceptanceStaging
        self.column_mapping = {
            'acceptanceno.': 'acceptance_no',
            'pono.': 'po_number',
            'polineno.': 'po_line_no',
            'shipmentno.': 'shipment_no',
            'milestonetype': 'milestone_type',
            'projectcode': 'project_code',
            'sitename': 'site_name',
            'sitecode': 'site_code',
            'acceptancedescription': 'acceptance_description',
            'unit': 'unit',
            'currency': 'currency',
            'billamount': 'bill_amount',
            'taxamount': 'tax_amount',
            'acceptedqty': 'accepted_qty',
            'centerarea': 'center_area',
            'plannedcompletiondate': 'planned_completion_date',
            'actualcompletiondate': 'actual_completion_date',
            'approver': 'approver',
            'currenthandler': 'current_handler',
            'approvalprogress': 'approval_progress',
            'isdpproject': 'isdp_project',
            'applicationsubmitted': 'application_submitted',
            'applicationprocessed': 'application_processed',
            'headerremarks': 'header_remarks',
            'remarks': 'remarks',
            'servicecode': 'service_code',
            'payment_percentage': 'payment_percentage',
            'recordstatus': 'record_status',
        }
    
    def validate_record(self, record: Dict[str, Any], row_num: int) -> List[Dict[str, str]]:
        """Validate Acceptance record"""
        errors = []
        
        if not record.get('acceptance_no'):
            errors.append({
                'row': row_num,
                'field': 'acceptance_no',
                'error': 'Acceptance Number is required'
            })
        
        if not record.get('po_number'):
            errors.append({
                'row': row_num,
                'field': 'po_number',
                'error': 'PO Number is required'
            })
        
        if not record.get('po_line_no'):
            errors.append({
                'row': row_num,
                'field': 'po_line_no',
                'error': 'PO Line Number is required'
            })
                
        if not record.get('shipment_no'):
            errors.append({
                'row': row_num,
                'field': 'shipment_no',
                'error': 'shipment no is required'
            })
        return errors
    
    @transaction.atomic
    def process_file(self, file_path: str):
        """Process Acceptance file - COMPANY-WIDE with FULL REPLACEMENT"""
        logger.info(f"Processing Acceptance file: {file_path}")
        
        # Read file
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
            else:
                df = pd.read_excel(file_path, dtype=str, keep_default_na=False)
        except Exception as e:
            raise ValueError(f"Failed to read file: {str(e)}")
        
        # Map columns
        df_mapped = self.map_csv_columns(df)
        self.stats['total_rows'] = len(df_mapped)
        
        # Delete ALL old staging data
        logger.info("Deleting old Acceptance staging data...")
        deleted_count = AcceptanceStaging.objects.all().delete()
        logger.info(f"Deleted {deleted_count[0]} old Acceptance staging records")
        
        # Delete ALL old permanent Acceptance data (FULL REPLACEMENT)
        logger.info("Deleting ALL old Acceptance permanent data (full replacement)...")
        from core.models import Acceptance
        acc_deleted_count = Acceptance.objects.all().delete()
        logger.info(f"Deleted {acc_deleted_count[0]} old Acceptance permanent records")
        
        # Process rows
        staging_records = []
        permanent_records = []
        
        for idx, row in df_mapped.iterrows():
            try:
                record_data = {}
                
                # Parse fields (keeping your existing parsing logic)
                record_data['acceptance_no'] = self.safe_string_truncate(row.get('acceptance_no'), 100)
                record_data['po_number'] = self.safe_string_truncate(row.get('po_number'), 100)
                record_data['po_line_no'] = self.safe_string_truncate(row.get('po_line_no'), 50)
                record_data['shipment_no'] = self.safe_string_truncate(row.get('shipment_no'), 100)
                record_data['milestone_type'] = self.safe_string_truncate(row.get('milestone_type'), 100)
                record_data['project_code'] = self.safe_string_truncate(row.get('project_code'), 100)
                record_data['project_name'] = self.safe_string_truncate(row.get('project_name'), 255)
                record_data['site_name'] = self.safe_string_truncate(row.get('site_name'), 255)
                record_data['site_code'] = self.safe_string_truncate(row.get('site_code'), 100)
                record_data['site_id'] = self.safe_string_truncate(row.get('site_id'), 255)
                record_data['item_description'] = row.get('item_description')
                record_data['item_description_local'] = row.get('item_description_local')
                record_data['engineering_code'] = self.safe_string_truncate(row.get('engineering_code'), 100)
                record_data['business_type'] = row.get('business_type')
                record_data['product_category'] = row.get('product_category')
                record_data['requested_qty'] = self.parse_integer(row.get('requested_qty'))
                record_data['acceptance_qty'] = self.parse_integer(row.get('acceptance_qty'))
                record_data['unit_price'] = self.parse_decimal(row.get('unit_price'))
                record_data['acceptance_milestone'] = self.safe_string_truncate(row.get('acceptance_milestone'), 100)
                record_data['cancel_remaining_qty'] = row.get('cancel_remaining_qty')
                record_data['unit'] = self.safe_string_truncate(row.get('unit'), 50)
                record_data['bidding_area'] = self.safe_string_truncate(row.get('bidding_area'), 255)
                record_data['customer'] = row.get('customer')
                record_data['rep_office'] = self.safe_string_truncate(row.get('rep_office'), 255)
                record_data['subproject_code'] = self.safe_string_truncate(row.get('subproject_code'), 100)
                record_data['engineering_category'] = self.safe_string_truncate(row.get('engineering_category'), 255)
                record_data['center_area'] = self.safe_string_truncate(row.get('center_area'), 255)
                record_data['planned_completion_date'] = self.parse_date(row.get('planned_completion_date'))
                record_data['actual_completion_date'] = self.parse_date(row.get('actual_completion_date'))
                record_data['approver'] = self.safe_string_truncate(row.get('approver'), 255)
                record_data['current_handler'] = row.get('current_handler')
                record_data['approval_progress'] = self.safe_string_truncate(row.get('approval_progress'), 100)
                record_data['isdp_project'] = self.safe_string_truncate(row.get('isdp_project'), 100)
                record_data['application_submitted'] = self.parse_date(row.get('application_submitted'))
                record_data['application_processed'] = self.parse_date(row.get('application_processed'))
                record_data['header_remarks'] = row.get('header_remarks')
                record_data['remarks'] = row.get('remarks')
                record_data['service_code'] = self.parse_decimal(row.get('service_code'))
                record_data['payment_percentage'] = self.safe_string_truncate(row.get('payment_percentage'), 50)
                record_data['record_status'] = self.safe_string_truncate(row.get('record_status'), 50) or 'active'
                
                # Validate
                validation_errors = self.validate_record(record_data, idx + 2)
                is_valid = len(validation_errors) == 0
                
                if not is_valid:
                    self.stats['invalid_rows'] += 1
                else:
                    self.stats['valid_rows'] += 1
                
                # Create staging record
                staging_record = AcceptanceStaging(
                    batch_id=self.batch_id,
                    row_number=idx + 2,
                    is_valid=is_valid,
                    validation_errors=validation_errors,
                    **record_data
                )
                staging_records.append(staging_record)
                
                # Create permanent record (only if valid)
                if is_valid and record_data.get('acceptance_no') and record_data.get('po_number') and record_data.get('po_line_no') and record_data.get('shipment_no'):
                    permanent_record = Acceptance(
                        batch_id=self.batch_id,
                        **record_data
                    )
                    permanent_records.append(permanent_record)
                
            except Exception as e:
                logger.error(f"Error processing row {idx + 2}: {str(e)}")
                self.stats['invalid_rows'] += 1
        
        # Bulk create staging records
        AcceptanceStaging.objects.bulk_create(staging_records, batch_size=1000)
        logger.info(f"Created {len(staging_records)} Acceptance staging records")
        
        # Bulk create permanent records (all valid records, including duplicates)
        from core.models import Acceptance
        if permanent_records:
            Acceptance.objects.bulk_create(permanent_records, batch_size=1000)
            logger.info(f"Inserted {len(permanent_records)} new Acceptance records (full replacement, including duplicates)")
        else:
            logger.warning("No valid Acceptance records to insert")