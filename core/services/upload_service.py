import pandas as pd
from django.db import transaction
from django.utils import timezone
from core.models import (
    POStaging, AcceptanceStaging, UploadHistory, 
    PurchaseOrder, Acceptance
)
import uuid
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)

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
        self.staging_model = None
        self.main_model = None
    
    def normalize_column_name(self, col_name: str) -> str:
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

    
    def parse_date(self, date_str: str) -> Optional[date]:
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
        """Parse integer values with error handling"""
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
        """Validate a single record - should be overridden by child classes"""
        return []
        
    def serialize_for_json(self, obj):
        """Serialize objects for JSON storage"""
        if isinstance(obj, dict):
            return {k: self.serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self.serialize_for_json(item) for item in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        else:
            return obj
    def load_csv(self, file_path: str, user_id: str) -> bool:
        """Load CSV file into staging table"""
        try:
            logger.info(f"Loading CSV file for user {user_id}: {file_path}")
            
            # Determine file type and read accordingly
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension == '.csv':
                df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
            elif file_extension in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path, dtype=str, keep_default_na=False)
            else:
                raise ValueError("Unsupported file format")
            
            logger.info(f"Found {len(df)} rows in file")
            
            # Map columns to database fields
            df_mapped = self.map_csv_columns(df)
            self.stats['total_rows'] = len(df_mapped)
            
            # Process in chunks
            staging_records = []
            for idx, row in df_mapped.iterrows():
                try:
                    record_data = row.to_dict()
                    
                    # Get valid fields for staging table
                    valid_fields = [column.name for column in self.staging_model.__table__.columns]
                    filtered_data = {k: v for k, v in record_data.items() if k in valid_fields}
                    
                    # Validate record
                    validation_errors = self.validate_record(filtered_data, idx + 1)
                    is_valid = len(validation_errors) == 0
                    
                    if validation_errors:
                        self.stats['validation_errors'].extend(validation_errors)
                    
                    # Create staging record
                    staging_record = self.staging_model(
                        user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
                        batch_id=self.batch_id,
                        row_number=idx + 1,
                        is_valid=is_valid,
                        validation_errors=validation_errors,
                        **filtered_data
                    )
                    
                    staging_records.append(staging_record)
                    self.stats['processed_rows'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing row {idx + 1}: {e}")
                    self.stats['failed_rows'] += 1
            
            # Bulk insert staging records
            self.db.bulk_save_objects(staging_records)
            self.db.commit()
            
            logger.info(f"✅ Loaded {self.stats['processed_rows']} rows into staging for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading CSV: {e}")
            self.db.rollback()
            return False
    
    def get_stats(self) -> Dict:
        """Get processing statistics"""
        return self.stats
    
    def print_summary(self):
        """Print processing summary"""
        print("\n" + "=" * 60)
        print("ETL PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Batch ID: {self.batch_id}")
        print(f"Total rows: {self.stats['total_rows']}")
        print(f"Processed rows: {self.stats['processed_rows']}")
        print(f"Failed rows: {self.stats['failed_rows']}")
        print(f"New records: {self.stats['new_records']}")
        print(f"Updated records: {self.stats['updated_records']}")
        print(f"Validation errors: {len(self.stats['validation_errors'])}")
        print("=" * 60)

class POProcessor(BaseETLProcessor):
    def __init__(self):
        super().__init__()
        self.staging_model = POStaging
        self.main_model = PurchaseOrder
        self.column_mapping = {
            'id': 'id',
            'change_history': 'change_history',
            'rep_office': 'rep_office',
            'project_name': 'project_name',
            'tax_rate': 'tax_rate',
            'site_name': 'site_name',
            'item_description': 'item_description',
            'note_to_receiver': 'note_to_receiver',
            'unit_price': 'unit_price',
            'due_qty': 'due_qty',
            'po_status': 'po_status',
            'po_no.': 'po_number',
            'po_line_no.': 'po_line_no',
            'item_code': 'item_code',
            'billed_quantity': 'billed_qty',
            'requested_qty': 'requested_qty',
            'publish_date': 'publish_date',
            'project_code': 'project_code',
            'payment_terms': 'payment_terms',
            'customer': 'customer',
            'site_code': 'site_code',
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
            'ff_buyer': 'ff_buyer',
            'fob_lookup_code': 'fob_lookup_code',
            'start_date': 'start_date',
            'end_date': 'end_date',
            'expire_date': 'expire_date',
            'acceptance_date': 'acceptance_date',
            'acceptance_date_1': 'acceptance_date_1',
            'pr_po_automation': 'pr_po_automation',
            'currency': 'currency',
            'unit': 'unit',
            'line_amount': 'line_amount',
            'quantity_cancel': 'quantity_cancel',
            'item_description_local': 'item_description_local',
            'payment_method': 'payment_method'
        }
    
    def validate_record(self, record: Dict[str, Any], row_num: int) -> List[Dict[str, str]]:
        """Validate a single PO record"""
                errors = []
        
        # Required fields validation
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
        
        # Numeric field validations
        if record.get('unit_price'):
            try:
                price = self.parse_decimal(record['unit_price'])
                if price and price < 0:
                    errors.append({
                        'row': row_num,
                        'field': 'unit_price',
                        'error': 'Unit price cannot be negative'
                    })
            except:
                errors.append({
                    'row': row_num,
                    'field': 'unit_price',
                    'error': 'Invalid unit price format'
                })
        
        if record.get('line_amount'):
            try:
                amount = self.parse_decimal(record['line_amount'])
                if amount and amount < 0:
                    errors.append({
                        'row': row_num,
                        'field': 'line_amount',
                        'error': 'Line amount cannot be negative'
                    })
            except:
                errors.append({
                    'row': row_num,
                    'field': 'line_amount',
                    'error': 'Invalid line amount format'
                })
        
        # Quantity validations
        for qty_field in ['requested_qty', 'due_qty', 'billed_qty']:
            if record.get(qty_field):
                try:
                    qty = self.parse_integer(record[qty_field])
                    if qty and qty < 0:
                        errors.append({
                            'row': row_num,
                            'field': qty_field,
                            'error': f'{qty_field} cannot be negative'
                        })
                except:
                    errors.append({
                        'row': row_num,
                        'field': qty_field,
                        'error': f'Invalid {qty_field} format'
                    })
        
        return errors
    def transform_and_load(self) -> bool:
        try:
            staging_records = self.db.query(POStaging).filter(
                POStaging.user_id == user_uuid,
                POStaging.batch_id == self.batch_id,
                POStaging.is_valid == True,
                POStaging.is_processed == False
            ).all()

            logger.info(f"📦 Transforming {len(staging_records)} valid staging records...")
                for staging_record in staging_records:
                try:
                    po_number = self.safe_string_truncate(staging_record.po_number, 100)
                    po_line_no = self.safe_string_truncate(staging_record.po_line_no, 50)
                    
                    # Create or update account mapping
                    if staging_record.project_name:
                        self._get_or_create_account(user_uuid, staging_record.project_name)
                    
                    # Check if PO already exists (upsert logic)
                    existing_po = self.db.query(PurchaseOrder).filter(
                        PurchaseOrder.po_number == po_number,
                        PurchaseOrder.po_line_no == po_line_no
                    ).first()
                    
                    if existing_po:
                        # UPDATE existing PO
                        self._update_po_from_staging(existing_po, staging_record)
                        self.stats['updated_records'] += 1
                        logger.debug(f"✏️ Updated PO: {po_number}-{po_line_no}")
                    else:
                        # INSERT new PO
                        new_po = self._create_po_from_staging(staging_record)
                        self.db.add(new_po)
                        self.stats['new_records'] += 1
                        logger.debug(f"➕ Inserted PO: {po_number}-{po_line_no}")
                    
                    # Mark staging record as processed
                    staging_record.is_processed = True
                    staging_record.processed_at = datetime.utcnow()
                    
                except Exception as e:
                    logger.error(f"❌ Error processing staging record {staging_record.staging_id}: {e}")
                    self.db.rollback()
                    
                    # Mark as processed but invalid
                    staging_record.is_processed = True
                    staging_record.is_valid = False
                    staging_record.validation_errors = [{'error': str(e)}]
                    self.db.add(staging_record)
                    self.db.commit()
            
            # Commit all changes
            self.db.commit()
            
            logger.info(
                f"✅ Processing complete: "
                f"{self.stats['new_records']} new, "
                f"{self.stats['updated_records']} updated PO records"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in PO transformation: {e}")
            self.db.rollback()
            return False
    
    def _map_project_to_account_name(self, project_name: str) -> str:
    
        if not project_name:
            return 'Other'
        
        project_name_lower = project_name.lower()
        
        if "iam" in project_name_lower:
            return "IAM Account"
        elif "orange" in project_name_lower:
            return "Orange Account"
        elif "inwi" in project_name_lower:
            return "INWI Account"
        else:
            return "Other"


    def _get_or_create_account(self, project_name: str) -> None:
        clean_project_name = (project_name or "Unknown Project").strip()
        
        # Check if account already exists
        existing_account = self.db.query(Account).filter(
            Account.project_name == clean_project_name
        ).first()
        
        if existing_account:
            return
        
        # Create new account
        account_name = self._map_project_to_account_name(clean_project_name)
        needs_review = (account_name == "Other")
        
        new_account = Account(
            project_name=clean_project_name,
            account_name=account_name,
            needs_review=needs_review
        )
        
        self.db.add(new_account)
        self.db.flush()
        
        logger.info(f"✨ Created new account '{account_name}' for project '{clean_project_name}'")
    
    def load_to_staging(self, file_path: str, user_id: str) -> bool:

        try:
            logger.info(f"Loading CSV file to staging for user {user_id}: {file_path}")
            success = self.load_csv(file_path, user_id)
            
            if success:
                logger.info(f"✅ Successfully loaded {self.stats['processed_rows']} rows to PO staging")
            else:
                logger.error(f"❌ Failed to load CSV to PO staging")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error in load_to_staging: {e}")
            return False
    def _create_po_from_staging(self, staging: POStaging) -> PurchaseOrder:
        return PurchaseOrder(
            po_number=self.safe_string_truncate(staging.po_number, 100),
            po_line_no=self.safe_string_truncate(staging.po_line_no, 50),
            project_name=self.safe_string_truncate(staging.project_name, 255),
            project_code=self.safe_string_truncate(staging.project_code, 100),
            site_name=self.safe_string_truncate(staging.site_name, 255),
            site_code=self.safe_string_truncate(staging.site_code, 100),
            item_code=self.safe_string_truncate(staging.item_code, 100),
            item_description=staging.item_description,
            item_description_local=staging.item_description_local,
            unit_price=self.parse_decimal(staging.unit_price),
            requested_qty=self.parse_integer(staging.requested_qty),
            due_qty=self.parse_integer(staging.due_qty),
            billed_qty=self.parse_integer(staging.billed_qty),
            quantity_cancel=self.parse_integer(staging.quantity_cancel),
            line_amount=self.parse_decimal(staging.line_amount),
            unit=self.safe_string_truncate(staging.unit, 50),
            currency=self.safe_string_truncate(staging.currency, 10),
            tax_rate=self.parse_decimal(staging.tax_rate),
            po_status=self.safe_string_truncate(staging.po_status, 50),
            payment_terms=self.safe_string_truncate(staging.payment_terms, 255),
            payment_method=self.safe_string_truncate(staging.payment_method, 100),
            customer=self.safe_string_truncate(staging.customer, 255),
            rep_office=self.safe_string_truncate(staging.rep_office, 255),
            subcontract_no=self.safe_string_truncate(staging.subcontract_no, 100),
            pr_no=self.safe_string_truncate(staging.pr_no, 100),
            sales_contract_no=self.safe_string_truncate(staging.sales_contract_no, 100),
            version_no=self.safe_string_truncate(staging.version_no, 50),
            shipment_no=self.safe_string_truncate(staging.shipment_no, 100),
            engineering_code=self.safe_string_truncate(staging.engineering_code, 100),
            engineering_name=self.safe_string_truncate(staging.engineering_name, 255),
            subproject_code=self.safe_string_truncate(staging.subproject_code, 100),
            category=self.safe_string_truncate(staging.category, 255),
            center_area=self.safe_string_truncate(staging.center_area, 255),
            product_category=self.safe_string_truncate(staging.product_category, 255),
            bidding_area=self.safe_string_truncate(staging.bidding_area, 255),
            bill_to=staging.bill_to,
            ship_to=staging.ship_to,
            note_to_receiver=staging.note_to_receiver,
            ff_buyer=self.safe_string_truncate(staging.ff_buyer, 255),
            fob_lookup_code=self.safe_string_truncate(staging.fob_lookup_code, 100),
            publish_date=self.parse_date(staging.publish_date),
            start_date=self.parse_date(staging.start_date),
            end_date=self.parse_date(staging.end_date),
            expire_date=self.parse_date(staging.expire_date),
            acceptance_date=self.parse_date(staging.acceptance_date),
            acceptance_date_1=self.parse_date(getattr(staging, 'acceptance_date_1', None)),
            change_history=staging.change_history,
            pr_po_automation=staging.pr_po_automation
        )
    
    
    def _update_po_from_staging(self, po: PurchaseOrder, staging: POStaging):
         new_values = self._create_po_from_staging(staging)
        
        for key, value in new_values.__dict__.items():
            if not key.startswith('_'):
                setattr(po, key, value)
        
        # Update timestamp
        po.updated_at = datetime.utcnow()


def process_user_csv(file_path: str, user_id: str, file_name: str = None) -> Dict:

    upload_record = None
    
    try:
        # Extract filename if not provided
        if not file_name:
            file_name = os.path.basename(file_path)
        
        logger.info(f"🚀 Starting PO CSV processing: {file_name} for user {user_id}")
        
        upload_record = UploadHistory(
            user_id=uuid.UUID(user_id),
            file_name=file_name,
            file_type='PO',
            uploaded_at=datetime.utcnow(),
            status='processing'
        )
        db.add(upload_record)
        db.commit()
        db.refresh(upload_record)
        
        # Initialize processor
        processor = POProcessor(db)
        
        # Step 1: Load CSV to staging
        logger.info("📥 Step 1/3: Loading CSV to staging table...")
        if not processor.load_to_staging(file_path, user_id):
            raise Exception("Failed to load CSV to staging")
        
        # Step 2: Transform and upsert to main table
        logger.info("⚙️ Step 2/3: Transforming and upserting to main table...")
        if not processor.transform_and_load():
            raise Exception("Failed to transform and load data")
        
        # Step 3: Get statistics
        stats = processor.get_stats()
        logger.info("📊 Step 3/3: Processing statistics collected")
        
        # Update upload history with success
        upload_record.status = 'success'
        upload_record.total_rows = stats.get('processed_rows', 0)
        db.commit()
        
        # Print summary
        processor.print_summary()
        
        logger.info(f"✅ PO CSV processing completed successfully: {file_name}")
        
        return {
            'success': True,
            'upload_id': str(upload_record.id),
            'stats': stats,
            'message': f'Successfully processed {stats.get("processed_rows", 0)} rows'
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing PO CSV: {str(e)}")
        
        # Update upload history with failure
        if upload_record:
            upload_record.status = 'failed'
            db.commit()
        
        db.rollback()
        
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to process CSV: {str(e)}'
        }
        
    finally:
        db.close()

class AcceptanceProcessor(BaseETLProcessor):
    """Acceptance Upload Processor"""
    
    def __init__(self):
        super().__init__()
        self.staging_model = AcceptanceStaging
        self.main_model = Acceptance
        # Column mapping
        self.column_mapping = {
            'id': 'id',
            'acceptanceno.': 'acceptance_no',
            'status': 'status',
            'rejected_reason': 'rejected_reason',
            'pono.': 'po_number',
            'polineno.': 'po_line_no',
            'shipmentno.': 'shipment_no',
            'item_description': 'item_description',
            'item_description(local)': 'item_description_local',
            'projectcode': 'project_code',
            'projectname': 'project_name',
            'sitecode': 'site_code',
            'sitename': 'site_name',
            'siteid': 'site_id',
            'engineeringcode': 'engineering_code',
            'businesstype': 'business_type',
            'productcategory': 'product_category',
            'requestedqty': 'requested_qty',
            'acceptanceqty': 'acceptance_qty',
            'unitprice': 'unit_price',
            'milestonetype': 'milestone_type',
            'acceptancemilestone': 'acceptance_milestone',
            'cancelremainingqty': 'cancel_remaining_qty',
            'biddingarea': 'bidding_area',
            'customer': 'customer',
            'repoffice': 'rep_office',
            'unit': 'unit',
            'subprojectcode': 'subproject_code',
            'engineeringcategory': 'engineering_category',
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
            'payment_percentage': 'payment_percentage'
        }
    
    
    def validate_record(self, record: Dict[str, Any], row_num: int) -> List[Dict[str, str]]:
        """Validate Acceptance record"""
        errors = []
        
        if not record.get('acceptance_no'):
            errors.append({
                'row': row_num,
                'field': 'acceptance_no',
                'value': record.get('acceptance_no'),
                'error': 'Acceptance Number is required'
            })
        
        if not record.get('po_number'):
            errors.append({
                'row': row_num,
                'field': 'po_number',
                'value': record.get('po_number'),
                'error': 'PO Number is required'
            })
        
        if not record.get('po_line_no'):
            errors.append({
                'row': row_num,
                'field': 'po_line_no',
                'value': record.get('po_line_no'),
                'error': 'PO Line Number is required'
            })
            
        if not record.get('shipment_no'):
            errors.append({
                'row': row_num,
                'field': 'shipment_no',
                'value': record.get('shipment_no'),
                'error': 'Shipment Number is required'
            })
        
        return errors
    
    def transform_and_load(self) -> bool:
        """Transform staging data and load into main Acceptance table"""
        try:
            
            logger.info(f"Transforming and loading Acceptance data ...")
            
            logger.info(f"🧹 Deleting all existing acceptances for user")
            deleted_count = self.db.query(Acceptance).delete(synchronize_session=False)
            self.db.commit()
            logger.info(f"🗑️ Deleted {deleted_count} existing acceptances")
            
            # Get valid staging records
            valid_records = self.db.query(AcceptanceStaging).filter(
                AcceptanceStaging.batch_id == self.batch_id,
                AcceptanceStaging.is_valid == True,
                AcceptanceStaging.is_processed == False
            ).all()
            
            logger.info(f"Processing {len(valid_records)} valid Acceptance records for user {user_id}")
            
            for staging_record in valid_records:
                try:
                    # Create new acceptance
                    new_acceptance = self._create_acceptance_from_staging(staging_record)
                    self.db.add(new_acceptance)
                    logger.info(f"  ➕ Created new Acceptance: {staging_record.acceptance_no}-{staging_record.po_number}-{staging_record.po_line_no}-{staging_record.shipment_no}")
                    self.stats['new_records'] += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error processing acceptance record: {e}")
                    continue
            
            self.db.commit()
            logger.info(f"✅ Successfully processed {self.stats['new_records']} new Acceptance records for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in Acceptance transformation: {e}")
            self.db.rollback()
            return False
    
    def _create_acceptance_from_staging(self,staging_record: AcceptanceStaging) -> Acceptance:
        """Create Acceptance from staging record"""
        return Acceptance(
            acceptance_no=self.safe_string_truncate(staging_record.acceptance_no, 100),
            status=self.safe_string_truncate(staging_record.status, 50),
            rejected_reason=staging_record.rejected_reason,
            po_number=self.safe_string_truncate(staging_record.po_number, 100),
            po_line_no=self.safe_string_truncate(staging_record.po_line_no, 50),
            shipment_no=self.parse_integer(staging_record.shipment_no),
            item_description=staging_record.item_description,
            item_description_local=staging_record.item_description_local,
            project_code=self.safe_string_truncate(staging_record.project_code, 100),
            project_name=self.safe_string_truncate(staging_record.project_name, 255),
            site_code=self.safe_string_truncate(staging_record.site_code, 100),
            site_name=self.safe_string_truncate(staging_record.site_name, 255),
            site_id=self.safe_string_truncate(staging_record.site_id, 255),
            engineering_code=self.safe_string_truncate(staging_record.engineering_code, 100),
            business_type=staging_record.business_type,
            product_category=staging_record.product_category,
            requested_qty=self.parse_integer(staging_record.requested_qty),
            acceptance_qty=self.parse_integer(staging_record.acceptance_qty),
            unit_price=self.parse_decimal(staging_record.unit_price),
            milestone_type=self.safe_string_truncate(staging_record.milestone_type, 100),
            acceptance_milestone=self.safe_string_truncate(staging_record.acceptance_milestone, 100),
            cancel_remaining_qty=staging_record.cancel_remaining_qty,
            bidding_area=self.safe_string_truncate(staging_record.bidding_area, 255),
            customer=staging_record.customer,
            rep_office=self.safe_string_truncate(staging_record.rep_office, 255),
            unit=self.safe_string_truncate(staging_record.unit, 50),
            subproject_code=self.safe_string_truncate(staging_record.subproject_code, 100),
            engineering_category=self.safe_string_truncate(staging_record.engineering_category, 255),
            center_area=self.safe_string_truncate(staging_record.center_area, 255),
            planned_completion_date=self.parse_date(staging_record.planned_completion_date),
            actual_completion_date=self.parse_date(staging_record.actual_completion_date),
            approver=self.safe_string_truncate(staging_record.approver, 255),
            current_handler=staging_record.current_handler,
            approval_progress=self.safe_string_truncate(staging_record.approval_progress, 100),
            isdp_project=self.safe_string_truncate(staging_record.isdp_project, 100),
            application_submitted=self.parse_date(staging_record.application_submitted),
            application_processed=self.parse_date(staging_record.application_processed),
            header_remarks=staging_record.header_remarks,
            remarks=staging_record.remarks,
            service_code=self.parse_decimal(staging_record.service_code),
            payment_percentage=self.safe_string_truncate(staging_record.payment_percentage, 50),
            record_status='active'
        )


def process_user_acceptance_csv(file_path: str,file_name: str = None) -> Dict:
    """Process user Acceptance CSV file - main function called by FileService"""
    from app.database import SessionLocal
    
    db = SessionLocal()
    upload_record = None
    
    try:
        # Extract filename if not provided
        if not file_name:
            file_name = os.path.basename(file_path)
        
        processor = AcceptanceProcessor(db)
        
        logger.info(f"📄 Starting Acceptance CSV processing for user: {user_id}")
        
        # Load CSV into staging
        load_success = processor.load_csv(file_path, user_id)
        
        # Transform and load into main table
        transform_success = False
        if load_success:
            transform_success = processor.transform_and_load(user_id)
        
        # Get processing stats
        stats = processor.get_stats()
        
        # Determine upload status
        if load_success and transform_success:
            status = 'success'
        elif stats.get('processed_rows', 0) > 0:
            status = 'partial'
        else:
            status = 'failed'
        
        # Create upload history record
        upload_record = UploadHistory(
            user_id=user_id,
            file_name=file_name,
            file_type='Acceptance',
            total_rows=stats.get('total_rows', 0),
            status=status
        )
        db.add(upload_record)
        db.commit()
        db.refresh(upload_record)
        
        processor.print_summary()
        
        return {
            'success': load_success and transform_success,
            'stats': stats,
            'batch_id': str(processor.batch_id),
            'upload_id': str(upload_record.id)
        }
        
    except Exception as e:
        logger.error(f"Critical error in process_user_acceptance_csv: {e}")
        
        # Create failed upload record
        try:
            if not file_name:
                file_name = os.path.basename(file_path)
            
            upload_record = UploadHistory(
                user_id=user_id,
                file_name=file_name,
                file_type='Acceptance',
                total_rows=0,
       
                status='failed'
            )
            db.add(upload_record)
            db.commit()
        except Exception as db_error:
            logger.error(f"Failed to create upload history: {db_error}")
        
        return {
            'success': False,
            'error': str(e),
            'stats': {}
        }
    finally:
        db.close()

