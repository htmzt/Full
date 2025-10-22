"""
Modified Merge Service - Uses SQL Query for FULL JOIN
Stores results in MergedData table
(Fixed: No emojis, corrected SQL query)
"""
from django.db import transaction, connection
from django.utils import timezone
from core.models import POStaging, AcceptanceStaging, MergedData, MergeHistory
import uuid
import logging
from decimal import Decimal
from datetime import date

logger = logging.getLogger(__name__)


class MergeService:
    """Service for merging PO and Acceptance staging data using SQL query"""
    
    @staticmethod
    def check_staging_data(user):
        """Check if both staging tables have data"""
        po_count = POStaging.objects.filter(user=user).count()
        acceptance_count = AcceptanceStaging.objects.filter(user=user).count()
        
        return {
            'has_po_data': po_count > 0,
            'has_acceptance_data': acceptance_count > 0,
            'po_count': po_count,
            'acceptance_count': acceptance_count,
            'ready_to_merge': po_count > 0 and acceptance_count > 0
        }
    
    @staticmethod
    @transaction.atomic
    def trigger_merge(user):
        """
        Trigger merge operation using SQL query
        
        This performs the merge using the provided SQL query and stores
        results in the MergedData table
        """
        logger.info(f"Starting merge for user: {user.email}")
        
        # Check staging data
        status_check = MergeService.check_staging_data(user)
        if not status_check['ready_to_merge']:
            raise ValueError("Both PO and Acceptance data must be uploaded first")
        
        batch_id = uuid.uuid4()
        
        try:
            # Step 1: Delete old merged data
            deleted_count, _ = MergedData.objects.filter(user=user).delete()
            logger.info(f"Deleted {deleted_count} old records")
            
            # Step 2: Execute SQL query to get merged data
            merged_records = MergeService._execute_merge_query(user)
            
            logger.info(f"Query returned {len(merged_records)} records")
            
            # Step 3: Create MergedData objects from query results
            merged_data_objects = []
            
            for record in merged_records:
                merged_data = MergedData(
                    user=user,
                    batch_id=batch_id,
                    
                    # PO Identification
                    po_id=record['po_id'],
                    po_number=record['po_no'],
                    po_line_no=record['po_line'],
                    
                    # Account & Project
                    account_name=record.get('account_name'),
                    project_name=record.get('project_name'),
                    
                    # Site
                    site_code=record.get('site_code'),
                    
                    # Category (calculated in query)
                    category=record.get('category'),
                    
                    # Item
                    item_description=record.get('item_desc'),
                    
                    # Payment Terms (parsed in query)
                    payment_terms=record.get('payment_terms'),
                    
                    # Pricing
                    unit_price=record.get('unit_price'),
                    requested_qty=record.get('req_qty'),
                    line_amount=record.get('line_amount'),
                    
                    # Dates
                    publish_date=record.get('publish_date'),
                    ac_date=record.get('ac_date'),
                    pac_date=record.get('pac_date'),
                    
                    # Calculated Amounts
                    ac_amount=record.get('ac_amount'),
                    pac_amount=record.get('pac_amount'),
                    remaining=record.get('remaining'),
                    
                    # Status (calculated in query)
                    status=record.get('status'),
                    
                    # Workflow tracking (default values)
                    is_assigned=False,
                    has_external_po=False,
                )
                
                merged_data_objects.append(merged_data)
            
            # Step 4: Bulk create
            MergedData.objects.bulk_create(merged_data_objects, batch_size=1000)
            merged_count = len(merged_data_objects)
            
            logger.info(f"Created {merged_count} merged records")
            
            # Step 5: Create merge history
            merge_history = MergeHistory.objects.create(
                batch_id=batch_id,
                merged_by=user,
                total_records=merged_count,
                po_records_count=status_check['po_count'],
                acceptance_records_count=status_check['acceptance_count'],
                status=MergeHistory.Status.COMPLETED,
                notes=f"SQL-based merge triggered by {user.full_name}",
                completed_at=timezone.now()
            )
            
            return {
                'success': True,
                'batch_id': str(batch_id),
                'merged_records': merged_count,
                'po_records': status_check['po_count'],
                'acceptance_records': status_check['acceptance_count'],
                'merged_at': merge_history.merged_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Merge failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Record failure
            MergeHistory.objects.create(
                batch_id=batch_id,
                merged_by=user,
                total_records=0,
                status=MergeHistory.Status.FAILED,
                error_message=str(e)
            )
            
            raise
    
    @staticmethod
    def _execute_merge_query(user):
        """
        Execute the SQL merge query and return results as list of dictionaries
        
        This uses the staging tables (po_staging and acceptance_staging)
        instead of the main tables (purchase_orders and acceptances)
        """
        
        # Modified query to use STAGING tables
        MERGE_QUERY = """
        SELECT 
            po.user_id,
            CONCAT(po.po_number, '-', po.po_line_no) AS po_id,
            acc.account_name,
            po.project_name,
            po.site_code,
            po.po_number AS po_no,
            po.po_line_no AS po_line,
            
            -- Category calculation
            CASE
                WHEN po.item_description ILIKE '%%Survey%%' THEN 'Survey'
                WHEN po.item_description ILIKE '%%Transportation%%' THEN 'Transportation'
                WHEN po.item_description ILIKE '%%Work Order%%' AND po.site_name ILIKE '%%Non DU%%' THEN 'Site Engineer'
                WHEN po.item_description ILIKE '%%Work Order%%' THEN 'Service'
                ELSE 'Service'
            END AS category,
            
            po.item_description AS item_desc,
            
            -- Payment terms parsing
            CASE
                WHEN po.payment_terms ILIKE '%%COD%%' THEN 'ACPAC 100%%'
                WHEN po.payment_terms ILIKE '%%AC1%%' AND po.payment_terms ILIKE '%%AC2%%' THEN 'AC1 80 | PAC 20'
                WHEN po.payment_terms ILIKE '%%AC1%%' THEN 'ACPAC 100%%'
                ELSE ''
            END AS payment_terms,
            
            po.unit_price,
            po.requested_qty AS req_qty,
            po.line_amount,
            po.publish_date,
            
            -- AC Amount (80%%)
            ROUND(CAST(COALESCE(po.line_amount, 0) AS NUMERIC) * 0.80, 2) AS ac_amount,
            a.ac_date,
            
            -- PAC Amount (20%%)
            ROUND(CAST(COALESCE(po.line_amount, 0) AS NUMERIC) * 0.20, 2) AS pac_amount,
            
            -- PAC Date logic
            CASE
                WHEN (po.payment_terms ILIKE '%%COD%%' OR (po.payment_terms ILIKE '%%AC1%%' AND po.payment_terms NOT ILIKE '%%AC2%%')) 
                     AND a.ac_date IS NOT NULL THEN a.ac_date
                ELSE a.pac_date
            END AS pac_date,
            
            -- Status calculation
            CASE
                WHEN po.payment_terms ILIKE '%%COD%%' OR (po.payment_terms ILIKE '%%AC1%%' AND po.payment_terms NOT ILIKE '%%AC2%%') THEN
                    CASE
                        WHEN COALESCE(po.requested_qty, 0) = 0 THEN 'CANCELLED'
                        WHEN a.ac_date IS NOT NULL THEN 'CLOSED'
                        WHEN a.ac_date IS NULL THEN 'Pending ACPAC'
                        ELSE 'CLOSED'
                    END
                WHEN po.payment_terms ILIKE '%%AC1%%' AND po.payment_terms ILIKE '%%AC2%%' THEN
                    CASE
                        WHEN po.po_status = 'CANCELLED' THEN 'CANCELLED'
                        WHEN po.po_status = 'CLOSED' THEN 'CLOSED'
                        WHEN a.ac_date IS NULL THEN 'Pending AC80%%'
                        WHEN a.pac_date IS NULL THEN 'Pending PAC20%%'
                        ELSE 'CLOSED'
                    END
                ELSE 'Unknown'
            END AS status,
            
            -- Remaining amount calculation
            CASE
                WHEN po.payment_terms ILIKE '%%COD%%' OR (po.payment_terms ILIKE '%%AC1%%' AND po.payment_terms NOT ILIKE '%%AC2%%') THEN
                    CASE
                        WHEN COALESCE(po.requested_qty, 0) = 0 THEN 0
                        WHEN a.ac_date IS NOT NULL THEN 0
                        WHEN a.ac_date IS NULL THEN COALESCE(po.line_amount, 0)
                        ELSE 0
                    END
                WHEN po.payment_terms ILIKE '%%AC1%%' AND po.payment_terms ILIKE '%%AC2%%' THEN
                    CASE
                        WHEN po.po_status = 'CANCELLED' THEN 0
                        WHEN po.po_status = 'CLOSED' THEN 0
                        WHEN a.ac_date IS NULL THEN COALESCE(po.line_amount, 0)
                        WHEN a.pac_date IS NULL THEN ROUND(CAST(COALESCE(po.line_amount, 0) AS NUMERIC) * 0.20, 2)
                        ELSE 0
                    END
                ELSE 0
            END AS remaining
            
        FROM po_staging po
        
        -- LEFT JOIN with Acceptance staging (grouped by milestone type)
        LEFT JOIN (
            SELECT 
                user_id,
                po_number,
                po_line_no,
                MIN(CASE WHEN milestone_type = 'AC1' THEN application_processed END) AS ac_date,
                MIN(CASE WHEN milestone_type = 'AC2' THEN application_processed END) AS pac_date
            FROM acceptance_staging
            WHERE user_id = %s
            GROUP BY user_id, po_number, po_line_no
        ) a ON po.user_id = a.user_id 
           AND po.po_number = a.po_number 
           AND po.po_line_no = a.po_line_no
        
        -- LEFT JOIN with accounts (for account_name lookup)
        LEFT JOIN accounts acc ON po.user_id = acc.user_id 
                              AND po.project_name = acc.project_name
        
        WHERE po.user_id = %s AND po.is_valid = TRUE
        
        ORDER BY po.po_number, po.po_line_no
        """
        
        # Execute query
        with connection.cursor() as cursor:
            cursor.execute(MERGE_QUERY, [user.id, user.id])
            columns = [col[0] for col in cursor.description]
            results = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
        
        return results
    
    @staticmethod
    def get_merge_history(user, limit=10):
        """Get merge history for user"""
        return MergeHistory.objects.filter(
            merged_by=user
        ).order_by('-merged_at')[:limit]