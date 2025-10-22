import pandas as pd
from django.db import transaction
from django.utils import timezone
from core.models import POStaging, AcceptanceStaging, UploadHistory
import uuid
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)
class BaseETLProcessor:
    def __init__(self):
        self.batch_id = uuid.uuid4()
        self.stats = {
            'total_rows': 0,
            'processed_rows': 0,
            'failed_rows': 0,
            'validation_errors': []
        }
        self.column_mapping = {}
    def normalize_column_name(self, col_name: str) -> str:
        normalized = str(col_name).strip().lower()
        normalized = normalized.replace(' ', '_').replace('.', '')
        normalized = normalized.replace('(', '_').replace(')', '_')
        while '__' in normalized:
            normalized = normalized.replace('__', '_')
        normalized = normalized.strip('_')
        return normalized
    def map_csv_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        original_columns = df.columns.tolist()
        df.columns = [self.normalize_column_name(col) for col in df.columns]
        normalized_columns = df.columns.tolist()
        logger.info(f"[MAPPING] Found {len(original_columns)} columns in file")
        logger.info("Column mapping (first 10):")
        for i, (orig, norm) in enumerate(zip(original_columns[:10], normalized_columns[:10])):
            logger.info(f"  '{orig}' -> '{norm}'")
        mapped_data = {}
        unmapped_columns = []
        for csv_col, db_field in self.column_mapping.items():
            if csv_col in df.columns:
                mapped_data[db_field] = df[csv_col]
            else:
                mapped_data[db_field] = pd.Series([None] * len(df))
                if csv_col not in ['id']:
                    unmapped_columns.append(csv_col)
        if unmapped_columns:
            logger.warning(f"[WARNING] Columns not found in file: {', '.join(unmapped_columns[:5])}")
        return pd.DataFrame(mapped_data)
    def parse_date(self, date_str: Any) -> Optional[str]:
        if not date_str or pd.isna(date_str) or str(date_str).strip() == '':
            return None
        date_formats = [
            '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y',
            '%Y/%m/%d', '%d.%m.%Y', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M'
        ]
        date_str = str(date_str).strip()
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt).date()
                return parsed_date.isoformat()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    def parse_decimal(self, value: Any) -> Optional[Decimal]:
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
        if pd.isna(value) or value == '' or value is None:
            return None
        try:
            return int(float(str(value)))
        except (ValueError, OverflowError):
            logger.warning(f"Could not parse integer: {value}")
            return None
    def safe_string_truncate(self, value: Any, max_length: int = None) -> Optional[str]:
        if pd.isna(value) or value == '' or value is None:
            return None
        str_value = str(value).strip()
        if max_length and len(str_value) > max_length:
            logger.warning(f"Truncating string from {len(str_value)} to {max_length} chars")
            return str_value[:max_length]
        return str_value if str_value else None
    def _is_empty_value(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ''
        if pd.isna(value):
            return True
        return False
class POProcessor(BaseETLProcessor):
    def __init__(self):
        super().__init__()
        # Column mapping: normalized CSV column → database field
        self.column_mapping = {
            'id': 'id',
            'po_no': 'po_number',
            'po_line_no': 'po_line_no',
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
            'sub_contract_no': 'subcontract_no',
            'pr_no': 'pr_no',
            'sales_contract_no': 'sales_contract_no',
            'version_no': 'version_no',
            'shipment_no': 'shipment_no',
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
            'pr_po_automation': 'pr_po_automation'
        }
    
    def validate_record(self, record: Dict[str, Any], row_num: int) -> List[Dict[str, str]]:
        """Validate a single PO record"""
        errors = []
        
        # Required fields
        if self._is_empty_value(record.get('po_number')):
            errors.append({
                'row': row_num,
                'field': 'po_number',
                'value': str(record.get('po_number')),
                'error': 'PO Number is required'
            })
        
        if self._is_empty_value(record.get('po_line_no')):
            errors.append({
                'row': row_num,
                'field': 'po_line_no',
                'value': str(record.get('po_line_no')),
                'error': 'PO Line Number is required'
            })
        
        # Numeric validations - only if value exists
        if not self._is_empty_value(record.get('unit_price')):
            price = self.parse_decimal(record['unit_price'])
            if price is not None and price < 0:
                errors.append({
                    'row': row_num,
                    'field': 'unit_price',
                    'value': str(record['unit_price']),
                    'error': 'Unit price cannot be negative'
                })
        
        if not self._is_empty_value(record.get('line_amount')):
            amount = self.parse_decimal(record['line_amount'])
            if amount is not None and amount < 0:
                errors.append({
                    'row': row_num,
                    'field': 'line_amount',
                    'value': str(record['line_amount']),
                    'error': 'Line amount cannot be negative'
                })
        
        return errors
    
    def process_file(self, file, user):
        """Process PO file and load to staging"""
        logger.info(f"[PO] Starting file processing for user: {user.email}")
        
        # Read file
        try:
            df = pd.read_excel(file, dtype=str, keep_default_na=False)
            logger.info(f"[PO] Read {len(df)} rows from Excel file")
        except Exception as e:
            logger.error(f"[PO] Failed to read Excel file: {e}")
            raise ValueError(f"Failed to read Excel file: {e}")
        
        # Map columns
        df_mapped = self.map_csv_columns(df)
        self.stats['total_rows'] = len(df_mapped)
        
        # Process rows
        po_records = []
        for idx, row in df_mapped.iterrows():
            try:
                record_data = row.to_dict()
                
                # Validate
                validation_errors = self.validate_record(record_data, idx + 1)
                is_valid = len(validation_errors) == 0
                
                if validation_errors:
                    self.stats['validation_errors'].extend(validation_errors)
                    logger.debug(f"Row {idx + 1} validation errors: {validation_errors}")
                po_recor.objects.delete()
                po_record = POStaging(
                    user=user,
                    batch_id=self.batch_id,
                    row_number=idx + 1,
                    is_valid=is_valid,
                    is_processed=False,
                    validation_errors=validation_errors if validation_errors else None,
                    # PO Data
                    po_number=self.safe_string_truncate(record_data.get('po_number'), 100),
                    po_line_no=self.safe_string_truncate(record_data.get('po_line_no'), 50),
                    project_name=self.safe_string_truncate(record_data.get('project_name'), 255),
                    project_code=self.safe_string_truncate(record_data.get('project_code'), 100),
                    site_name=self.safe_string_truncate(record_data.get('site_name'), 255),
                    site_code=self.safe_string_truncate(record_data.get('site_code'), 100),
                    item_code=self.safe_string_truncate(record_data.get('item_code'), 100),
                    item_description=record_data.get('item_description'),
                    item_description_local=record_data.get('item_description_local'),
                    unit_price=self.parse_decimal(record_data.get('unit_price')),
                    requested_qty=self.parse_integer(record_data.get('requested_qty')),
                    due_qty=self.parse_integer(record_data.get('due_qty')),
                    billed_qty=self.parse_integer(record_data.get('billed_qty')),
                    quantity_cancel=self.parse_integer(record_data.get('quantity_cancel')),
                    line_amount=self.parse_decimal(record_data.get('line_amount')),
                    unit=self.safe_string_truncate(record_data.get('unit'), 50),
                    currency=self.safe_string_truncate(record_data.get('currency'), 10),
                    tax_rate=self.parse_decimal(record_data.get('tax_rate')),
                    po_status=self.safe_string_truncate(record_data.get('po_status'), 50),
                    payment_terms=self.safe_string_truncate(record_data.get('payment_terms'), 255),
                    payment_method=self.safe_string_truncate(record_data.get('payment_method'), 100),
                    customer=self.safe_string_truncate(record_data.get('customer'), 255),
                    rep_office=self.safe_string_truncate(record_data.get('rep_office'), 255),
                    subcontract_no=self.safe_string_truncate(record_data.get('subcontract_no'), 100),
                    pr_no=self.safe_string_truncate(record_data.get('pr_no'), 100),
                    sales_contract_no=self.safe_string_truncate(record_data.get('sales_contract_no'), 100),
                    version_no=self.safe_string_truncate(record_data.get('version_no'), 50),
                    shipment_no=self.safe_string_truncate(record_data.get('shipment_no'), 100),
                    engineering_code=self.safe_string_truncate(record_data.get('engineering_code'), 100),
                    engineering_name=self.safe_string_truncate(record_data.get('engineering_name'), 255),
                    subproject_code=self.safe_string_truncate(record_data.get('subproject_code'), 100),
                    category=self.safe_string_truncate(record_data.get('category'), 255),
                    center_area=self.safe_string_truncate(record_data.get('center_area'), 255),
                    product_category=self.safe_string_truncate(record_data.get('product_category'), 255),
                    bidding_area=self.safe_string_truncate(record_data.get('bidding_area'), 255),
                    bill_to=record_data.get('bill_to'),
                    ship_to=record_data.get('ship_to'),
                    note_to_receiver=record_data.get('note_to_receiver'),
                    ff_buyer=self.safe_string_truncate(record_data.get('ff_buyer'), 255),
                    fob_lookup_code=self.safe_string_truncate(record_data.get('fob_lookup_code'), 100),
                    publish_date=self.parse_date(record_data.get('publish_date')),
                    start_date=self.parse_date(record_data.get('start_date')),
                    end_date=self.parse_date(record_data.get('end_date')),
                    expire_date=self.parse_date(record_data.get('expire_date')),
                    acceptance_date=self.parse_date(record_data.get('acceptance_date')),
                    acceptance_date_1=self.parse_date(record_data.get('acceptance_date_1')),
                    change_history=record_data.get('change_history'),
                    pr_po_automation=record_data.get('pr_po_automation')
                )
                self.stats['processed_rows'] += 1
                
            except Exception as e:
                logger.error(f"[PO] Error processing row {idx + 1}: {e}")
                self.stats['failed_rows'] += 1
                continue
        
        # Bulk create
        logger.info(f"[PO] Saving {len(po_records)} records to staging table...")
        POStaging.objects.bulk_create(po_records, batch_size=1000)
        
        valid_count = sum(1 for r in po_records if r.is_valid)
        invalid_count = len(po_records) - valid_count
        
        logger.info(f"[PO] Processing complete:")
        logger.info(f"   Total rows: {self.stats['total_rows']}")
        logger.info(f"   Processed: {self.stats['processed_rows']}")
        logger.info(f"   Valid: {valid_count}")
        logger.info(f"   Invalid: {invalid_count}")
        logger.info(f"   Failed: {self.stats['failed_rows']}")

        po_staging_records = POStaging.objects
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

class AcceptanceProcessor(BaseETLProcessor):
    """Acceptance Upload Processor"""
    
    def __init__(self):
        super().__init__()
        # Column mapping
        self.column_mapping = {
            'id': 'id',
            'acceptanceno': 'acceptance_no',
            'pono': 'po_number',
            'polineno': 'po_line_no',
            'shipmentno': 'shipment_no',
            'milestone_type': 'milestone_type',
            'project_code': 'project_code',
            'site_name': 'site_name',
            'site_code': 'site_code',
            'acceptance_description': 'acceptance_description',
            'unit': 'unit',
            'currency': 'currency',
            'bill_amount': 'bill_amount',
            'tax_amount': 'tax_amount',
            'accepted_qty': 'accepted_qty',
            'center_area': 'center_area',
            'planned_completion_date': 'planned_completion_date',
            'actual_completion_date': 'actual_completion_date',
            'application_submitted': 'application_submitted',
            'application_processed': 'application_processed',
            'approver': 'approver',
            'current_handler': 'current_handler',
            'approval_progress': 'approval_progress',
            'isdp_project': 'isdp_project',
            'header_remarks': 'header_remarks',
            'remarks': 'remarks',
            'service_code': 'service_code',
            'payment_percentage': 'payment_percentage',
            'record_status': 'record_status'
        }
    
    def validate_record(self, record: Dict[str, Any], row_num: int) -> List[Dict[str, str]]:
        """Validate Acceptance record"""
        errors = []
        
        if self._is_empty_value(record.get('acceptance_no')):
            errors.append({
                'row': row_num,
                'field': 'acceptance_no',
                'value': str(record.get('acceptance_no')),
                'error': 'Acceptance Number is required'
            })
        
        if self._is_empty_value(record.get('po_number')):
            errors.append({
                'row': row_num,
                'field': 'po_number',
                'value': str(record.get('po_number')),
                'error': 'PO Number is required'
            })
        
        if self._is_empty_value(record.get('po_line_no')):
            errors.append({
                'row': row_num,
                'field': 'po_line_no',
                'value': str(record.get('po_line_no')),
                'error': 'PO Line Number is required'
            })
        
        return errors
    
    def process_file(self, file, user):
        """Process Acceptance file and load to staging"""
        logger.info(f"[ACCEPTANCE] Starting file processing for user: {user.email}")
        
        # Read file
        try:
            df = pd.read_excel(file, dtype=str, keep_default_na=False)
            logger.info(f"[ACCEPTANCE] Read {len(df)} rows from Excel file")
        except Exception as e:
            logger.error(f"[ACCEPTANCE] Failed to read Excel file: {e}")
            raise ValueError(f"Failed to read Excel file: {e}")
        
        # Map columns
        df_mapped = self.map_csv_columns(df)
        self.stats['total_rows'] = len(df_mapped)
        
        # Process rows
        acceptance_records = []
        for idx, row in df_mapped.iterrows():
            try:
                record_data = row.to_dict()
                
                # Validate
                validation_errors = self.validate_record(record_data, idx + 1)
                is_valid = len(validation_errors) == 0
                
                if validation_errors:
                    self.stats['validation_errors'].extend(validation_errors)
                acceptance_record.object.delete()
                # Create AcceptanceStaging record
                acceptance_record = AcceptanceStaging(
                    user=user,
                    batch_id=self.batch_id,
                    row_number=idx + 1,
                    is_valid=is_valid,
                    is_processed=False,
                    validation_errors=validation_errors if validation_errors else None,
                    # Acceptance Data
                    acceptance_no=self.safe_string_truncate(record_data.get('acceptance_no'), 100),
                    po_number=self.safe_string_truncate(record_data.get('po_number'), 100),
                    po_line_no=self.safe_string_truncate(record_data.get('po_line_no'), 50),
                    shipment_no=self.safe_string_truncate(record_data.get('shipment_no'), 100),
                    milestone_type=self.safe_string_truncate(record_data.get('milestone_type'), 50),
                    project_code=self.safe_string_truncate(record_data.get('project_code'), 100),
                    site_name=self.safe_string_truncate(record_data.get('site_name'), 255),
                    site_code=self.safe_string_truncate(record_data.get('site_code'), 100),
                    acceptance_description=record_data.get('acceptance_description'),
                    unit=self.safe_string_truncate(record_data.get('unit'), 50),
                    currency=self.safe_string_truncate(record_data.get('currency'), 10),
                    bill_amount=self.parse_decimal(record_data.get('bill_amount')),
                    tax_amount=self.parse_decimal(record_data.get('tax_amount')),
                    accepted_qty=self.parse_decimal(record_data.get('accepted_qty')),
                    center_area=self.safe_string_truncate(record_data.get('center_area'), 255),
                    planned_completion_date=self.parse_date(record_data.get('planned_completion_date')),
                    actual_completion_date=self.parse_date(record_data.get('actual_completion_date')),
                    application_submitted=self.parse_date(record_data.get('application_submitted')),
                    application_processed=self.parse_date(record_data.get('application_processed')),
                    approver=self.safe_string_truncate(record_data.get('approver'), 255),
                    current_handler=record_data.get('current_handler'),
                    approval_progress=self.safe_string_truncate(record_data.get('approval_progress'), 100),
                    isdp_project=self.safe_string_truncate(record_data.get('isdp_project'), 100),
                    header_remarks=record_data.get('header_remarks'),
                    remarks=record_data.get('remarks'),
                    service_code=self.parse_decimal(record_data.get('service_code')),
                    payment_percentage=self.safe_string_truncate(record_data.get('payment_percentage'), 50),
                    record_status=self.safe_string_truncate(record_data.get('record_status'), 50)
                )
                
                self.stats['processed_rows'] += 1
                
            except Exception as e:
                logger.error(f"[ACCEPTANCE] Error processing row {idx + 1}: {e}")
                self.stats['failed_rows'] += 1
                continue
        
        # Bulk create
        logger.info(f"[ACCEPTANCE] Saving {len(acceptance_records)} records to staging table...")
        AcceptanceStaging.objects.bulk_create(acceptance_records, batch_size=1000)
        
        valid_count = sum(1 for r in acceptance_records if r.is_valid)
        invalid_count = len(acceptance_records) - valid_count
        
        logger.info(f"[ACCEPTANCE] Processing complete:")
        logger.info(f"   Total rows: {self.stats['total_rows']}")
        logger.info(f"   Processed: {self.stats['processed_rows']}")
        logger.info(f"   Valid: {valid_count}")
        logger.info(f"   Invalid: {invalid_count}")
        
        return {
            'batch_id': self.batch_id,
            'total_rows': self.stats['total_rows'],
            'valid_rows': valid_count,
            'invalid_rows': invalid_count,
            'validation_errors': self.stats['validation_errors'][:10]
        }


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
        """Upload and process PO Excel file"""
        logger.info(f"[PO] Starting upload for user: {user.email}")
        
        # Validate file
        UploadService.validate_excel_file(file)
        
        # Create upload history record
        upload_history = UploadHistory.objects.create(
            user=user,
            batch_id=uuid.uuid4(),  # Temporary, will be updated
            file_type=UploadHistory.FileType.PO,
            original_filename=file.name,
            file_size=file.size,
            status=UploadHistory.Status.PROCESSING
        )
        
        try:
            start_time = timezone.now()
            
            # Process with POProcessor
            processor = POProcessor()
            result = processor.process_file(file, user)
            
            # Calculate duration
            duration = (timezone.now() - start_time).total_seconds()
            
            # Update upload history
            upload_history.batch_id = result['batch_id']
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
        """Upload and process Acceptance Excel file"""
        logger.info(f"[ACCEPTANCE] Starting upload for user: {user.email}")
        
        # Validate file
        UploadService.validate_excel_file(file)
        
        # Create upload history record
        upload_history = UploadHistory.objects.create(
            user=user,
            batch_id=uuid.uuid4(),  # Temporary
            file_type=UploadHistory.FileType.ACCEPTANCE,
            original_filename=file.name,
            file_size=file.size,
            status=UploadHistory.Status.PROCESSING
        )
        
        try:
            start_time = timezone.now()
            
            # Process with AcceptanceProcessor
            processor = AcceptanceProcessor()
            result = processor.process_file(file, user)
            
            # Calculate duration
            duration = (timezone.now() - start_time).total_seconds()
            
            # Update upload history
            upload_history.batch_id = result['batch_id']
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