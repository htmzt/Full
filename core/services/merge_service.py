"""
Modified Merge Service - Company-Wide Data (No User Filtering)
Uses SQL Query for FULL JOIN, stores results in MergedData table
"""
from django.db import transaction, connection
from django.utils import timezone
from core.models import PurchaseOrder, Acceptance, MergedData, MergeHistory
import uuid
import logging

logger = logging.getLogger(__name__)

class MergeService:
    """Service for merging PO and Acceptance data - COMPANY-WIDE"""
    
    @staticmethod
    def check_staging_data():
        """Check if both permanent tables have data - COMPANY-WIDE"""
        po_count = PurchaseOrder.objects.count()
        acceptance_count = Acceptance.objects.count()
        
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
        Trigger merge operation - COMPANY-WIDE DATA
        
        Args:
            user: User who triggered the merge (for tracking only)
        
        Returns:
            dict with merge results
        """
        logger.info(f"Starting COMPANY-WIDE merge triggered by: {user.email}")
        
        # Check data (NO user filtering)
        status_check = MergeService.check_staging_data()
        if not status_check['ready_to_merge']:
            raise ValueError("Both PO and Acceptance data must be uploaded first")
        
        batch_id = uuid.uuid4()
        
        try:
            # Step 1: Delete ALL old merged data (company-wide replacement)
            deleted_count, _ = MergedData.objects.all().delete()
            logger.info(f"Deleted {deleted_count} old records (company-wide)")
            
            # Step 2: Execute SQL query to get merged data
            try:
                merged_records = MergeService._execute_merge_query()
                logger.info(f"Query returned {len(merged_records)} records")
            except Exception as query_error:
                logger.error(f"Query execution failed: {str(query_error)}", exc_info=True)
                raise ValueError(f"Query execution failed: {str(query_error)}")
            
            if not merged_records:
                raise ValueError("No records returned from merge query. Check if data is valid.")
            
            # Step 3: Create MergedData objects from query results
            merged_data_objects = []
            
            for idx, record in enumerate(merged_records):
                try:
                    merged_data = MergedData(
                        batch_id=batch_id,
                        po_id=record.get('po_id', ''),
                        po_number=record.get('po_no', ''),
                        po_line_no=record.get('po_line', ''),
                        account_name=record.get('account_name'),
                        project_name=record.get('project_name'),
                        project_code=record.get('project_code'),
                        site_code=record.get('site_code'),
                        site_name=record.get('site_name'),
                        category=record.get('category'),
                        item_description=record.get('item_desc'),
                        item_code=record.get('item_code'),
                        payment_terms=record.get('payment_terms'),
                        unit_price=record.get('unit_price'),
                        requested_qty=record.get('req_qty'),
                        line_amount=record.get('line_amount'),
                        unit=record.get('unit'),
                        currency=record.get('currency'),
                        publish_date=record.get('publish_date'),
                        ac_date=record.get('ac_date'),
                        pac_date=record.get('pac_date'),
                        ac_amount=record.get('ac_amount'),
                        pac_amount=record.get('pac_amount'),
                        remaining=record.get('remaining'),
                        status=record.get('status'),
                        po_status=record.get('po_status'),
                        is_assigned=False,
                        has_external_po=False,
                    )
                    merged_data_objects.append(merged_data)
                except Exception as record_error:
                    logger.error(f"Failed to create MergedData object for record {idx}: {str(record_error)}")
                    logger.error(f"Record data: {record}")
                    continue
            
            # Step 4: Bulk create
            MergedData.objects.bulk_create(merged_data_objects, batch_size=1000)
            merged_count = len(merged_data_objects)
            
            logger.info(f"Created {merged_count} merged records (company-wide)")
            
            # Step 5: Create merge history
            merge_history = MergeHistory.objects.create(
                batch_id=batch_id,
                merged_by=user,
                total_records=merged_count,
                po_records_count=status_check['po_count'],
                acceptance_records_count=status_check['acceptance_count'],
                status=MergeHistory.Status.COMPLETED,
                notes=f"Company-wide merge triggered by {user.full_name}",
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
            logger.error(f"Merge failed: {str(e)}", exc_info=True)
            
            # Record failure
            MergeHistory.objects.create(
                batch_id=batch_id,
                merged_by=user,
                total_records=0,
                status=MergeHistory.Status.FAILED,
                error_message=str(e)
            )
            
            raise ValueError(f"Merge failed: {str(e)}")
    
    @staticmethod
    def _execute_merge_query():
        """
        Execute the SQL merge query - COMPANY-WIDE (NO USER FILTERING)
        
        Returns:
            list of dict with merged data
        """
        
        MERGE_QUERY = """
        SELECT 
            CONCAT(po.po_number, '-', po.po_line_no) AS po_id,
            po.project_name AS account_name,
            po.project_name,
            po.project_code,
            po.site_code,
            po.site_name,
            po.po_number AS po_no,
            po.po_line_no AS po_line,
            po.item_code,
            po.unit,
            po.currency,
            po.po_status,
            
            CASE
                WHEN po.item_description ILIKE %s THEN 'Survey'
                WHEN po.item_description ILIKE %s THEN 'Transportation'
                WHEN po.item_description ILIKE %s AND po.site_name ILIKE %s THEN 'Site Engineer'
                WHEN po.item_description ILIKE %s THEN 'Service'
                ELSE 'Service'
            END AS category,
            
            po.item_description AS item_desc,
            
            CASE
                WHEN po.payment_terms LIKE %s THEN 'ACPAC 100%%'
                WHEN po.payment_terms LIKE %s AND po.payment_terms LIKE %s THEN 'AC1 80 | PAC 20'
                WHEN po.payment_terms LIKE %s THEN 'ACPAC 100%%'
                ELSE COALESCE(po.payment_terms, '')
            END AS payment_terms,
            
            po.unit_price,
            po.requested_qty AS req_qty,
            po.line_amount,
            po.publish_date,
            
            ROUND(CAST(COALESCE(po.line_amount, 0) AS NUMERIC) * 0.80, 2) AS ac_amount,
            a.ac_date,
            
            ROUND(CAST(COALESCE(po.line_amount, 0) AS NUMERIC) * 0.20, 2) AS pac_amount,
            
            CASE
                WHEN (po.payment_terms LIKE %s OR (po.payment_terms LIKE %s AND po.payment_terms NOT LIKE %s)) 
                     AND a.ac_date IS NOT NULL THEN a.ac_date
                ELSE a.pac_date
            END AS pac_date,
            
            CASE
                WHEN po.payment_terms LIKE %s OR (po.payment_terms LIKE %s AND po.payment_terms NOT LIKE %s) THEN
                    CASE
                        WHEN COALESCE(po.requested_qty, 0) = 0 THEN 'CANCELLED'
                        WHEN a.ac_date IS NOT NULL THEN 'CLOSED'
                        WHEN a.ac_date IS NULL THEN 'Pending ACPAC'
                        ELSE 'CLOSED'
                    END
                WHEN po.payment_terms LIKE %s AND po.payment_terms LIKE %s THEN
                    CASE
                        WHEN po.po_status = 'CANCELLED' THEN 'CANCELLED'
                        WHEN po.po_status = 'CLOSED' THEN 'CLOSED'
                        WHEN a.ac_date IS NULL THEN 'Pending AC80%%'
                        WHEN a.pac_date IS NULL THEN 'Pending PAC20%%'
                        ELSE 'CLOSED'
                    END
                ELSE 'Unknown'
            END AS status,
            
            CASE
                WHEN po.payment_terms LIKE %s OR (po.payment_terms LIKE %s AND po.payment_terms NOT LIKE %s) THEN
                    CASE
                        WHEN COALESCE(po.requested_qty, 0) = 0 THEN 0
                        WHEN a.ac_date IS NOT NULL THEN 0
                        WHEN a.ac_date IS NULL THEN COALESCE(po.line_amount, 0)
                        ELSE 0
                    END
                WHEN po.payment_terms LIKE %s AND po.payment_terms LIKE %s THEN
                    CASE
                        WHEN po.po_status = 'CANCELLED' THEN 0
                        WHEN po.po_status = 'CLOSED' THEN 0
                        WHEN a.ac_date IS NULL THEN COALESCE(po.line_amount, 0)
                        WHEN a.pac_date IS NULL THEN ROUND(CAST(COALESCE(po.line_amount, 0) AS NUMERIC) * 0.20, 2)
                        ELSE 0
                    END
                ELSE 0
            END AS remaining
            
        FROM purchase_orders po
        
        LEFT JOIN (
            SELECT 
                po_number,
                po_line_no,
                MIN(CASE WHEN milestone_type = 'AC1' THEN application_processed END) AS ac_date,
                MIN(CASE WHEN milestone_type = 'AC2' THEN application_processed END) AS pac_date
            FROM acceptances
            GROUP BY po_number, po_line_no
        ) a ON po.po_number = a.po_number 
           AND po.po_line_no = a.po_line_no
        
        ORDER BY po.po_number, po.po_line_no
        """
        
        # CRITICAL: COLUMN MAPPING NOT CHANGED - Same parameters as before
        params = [
            '%Survey%', '%Transportation%', '%Work Order%', '%Non DU%', '%Work Order%',
            '%COD%', '%AC1%', '%AC2%', '%AC1%',
            '%COD%', '%AC1%', '%AC2%',
            '%COD%', '%AC1%', '%AC2%', '%AC1%', '%AC2%',
            '%COD%', '%AC1%', '%AC2%', '%AC1%', '%AC2%',
        ]
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(MERGE_QUERY, params)
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            logger.info(f"Query executed successfully. Returned {len(results)} records (company-wide)")
            return results
            
        except Exception as e:
            logger.error(f"SQL Query execution failed: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def get_merge_history(user, limit=10):
        """Get merge history - all merges (company-wide)"""
        return MergeHistory.objects.order_by('-merged_at')[:limit]