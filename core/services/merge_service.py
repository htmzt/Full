"""
Merge Service - Handle PO + Acceptance merge with complex SQL logic
"""
from django.db import transaction, connection
from django.utils import timezone
from core.models import (
    MergedData, MergeHistory, UploadHistory, 
    PurchaseOrder, Acceptance
)
from core.services.account_service import AccountService
import uuid
import logging

logger = logging.getLogger(__name__)


class MergeService:
    """Service for merging PO and Acceptance data"""
    
    # SQL query for merging data
    MERGED_DATA_QUERY = """
    SELECT 
        concat(po.po_number, '-', po.po_line_no) AS po_id,
        acc.account_name,
        po.project_name,
        po.site_code,
        po.project_code,
        po.po_number AS po_no,
        po.po_line_no AS po_line,
        CASE
            WHEN po.item_description ILIKE '%Survey%' THEN 'Survey'
            WHEN po.item_description ILIKE '%Transportation%' THEN 'Transportation'
            WHEN po.item_description ILIKE '%Work Order%' AND po.site_name ILIKE '%Non DU%' THEN 'Site Engineer'
            WHEN po.item_description ILIKE '%Work Order%' THEN 'Service'
            ELSE 'Service'
        END AS category,
        po.item_description AS item_desc,
        CASE
            WHEN po.payment_terms::text LIKE '%COD%' THEN 'ACPAC 100%'
            WHEN po.payment_terms::text LIKE '%AC1%' AND po.payment_terms::text LIKE '%AC2%' THEN 'AC1 80 | PAC 20'
            WHEN po.payment_terms::text LIKE '%AC1%' THEN 'ACPAC 100%'
            ELSE ''
        END AS payment_terms,
        po.unit_price,
        po.requested_qty AS req_qty,
        po.line_amount,
        po.publish_date,
        ROUND(po.line_amount * 0.80, 2) AS ac_amount,
        a.ac_date,
        ROUND(po.line_amount * 0.20, 2) AS pac_amount,
        CASE
            WHEN (po.payment_terms::text LIKE '%COD%' OR (po.payment_terms::text LIKE '%AC1%' AND po.payment_terms::text NOT LIKE '%AC2%')) AND a.ac_date IS NOT NULL THEN a.ac_date
            ELSE a.pac_date
        END AS pac_date,
        CASE
            WHEN po.payment_terms::text LIKE '%COD%' OR (po.payment_terms::text LIKE '%AC1%' AND po.payment_terms::text NOT LIKE '%AC2%') THEN
            CASE
                WHEN po.requested_qty = 0 THEN 'CANCELLED'
                WHEN a.ac_date IS NOT NULL THEN 'CLOSED'
                WHEN a.ac_date IS NULL THEN 'Pending ACPAC'
                ELSE 'CLOSED'
            END
            WHEN po.payment_terms::text LIKE '%AC1%' AND po.payment_terms::text LIKE '%AC2%' THEN
            CASE
                WHEN po.po_status::text = 'CANCELLED' THEN 'CANCELLED'
                WHEN po.po_status::text = 'CLOSED' THEN 'CLOSED'
                WHEN a.ac_date IS NULL THEN 'Pending AC80%'
                WHEN a.pac_date IS NULL THEN 'Pending PAC20%'
                ELSE 'CLOSED'
            END
            ELSE 'Unknown'
        END AS status,
        CASE
            WHEN po.payment_terms::text LIKE '%COD%' OR (po.payment_terms::text LIKE '%AC1%' AND po.payment_terms::text NOT LIKE '%AC2%') THEN
            CASE
                WHEN po.requested_qty = 0 THEN 0
                WHEN a.ac_date IS NOT NULL THEN 0
                WHEN a.ac_date IS NULL THEN po.line_amount
                ELSE 0
            END
            WHEN po.payment_terms::text LIKE '%AC1%' AND po.payment_terms::text LIKE '%AC2%' THEN
            CASE
                WHEN po.po_status::text = 'CANCELLED' THEN 0
                WHEN po.po_status::text = 'CLOSED' THEN 0
                WHEN a.ac_date IS NULL THEN po.line_amount
                WHEN a.pac_date IS NULL THEN ROUND(po.line_amount * 0.20, 2)
                ELSE 0
            END
            ELSE 0
        END AS remaining,
        po.unit,
        po.currency,
        po.po_status,
        po.site_name,
        po.item_code
    FROM purchase_orders po
    LEFT JOIN (
        SELECT 
            acceptances.po_number,
            acceptances.po_line_no,
            MIN(CASE WHEN acceptances.milestone_type::text = 'AC1' THEN acceptances.application_processed END) AS ac_date,
            MIN(CASE WHEN acceptances.milestone_type::text = 'AC2' THEN acceptances.application_processed END) AS pac_date
        FROM acceptances
        GROUP BY acceptances.po_number, acceptances.po_line_no
    ) a ON po.po_number::text = a.po_number::text AND po.po_line_no::text = a.po_line_no::text
    LEFT JOIN accounts acc ON po.project_name::text = acc.project_name::text
    WHERE {base_filter}
    """
    
    @staticmethod
    def check_staging_data():
        """
        Check if staging data is ready for merge
        
        Returns:
            dict with status information
        """
        po_count = PurchaseOrder.objects.count()
        acceptance_count = Acceptance.objects.count()
        
        has_po_data = po_count > 0
        has_acceptance_data = acceptance_count > 0
        
        return {
            'has_po_data': has_po_data,
            'has_acceptance_data': has_acceptance_data,
            'po_count': po_count,
            'acceptance_count': acceptance_count,
            'ready_to_merge': has_po_data  # Can merge with just PO data
        }
    
    @staticmethod
    @transaction.atomic
    def trigger_merge(user):
        """
        Trigger merge operation using complex SQL query
        
        Args:
            user: User triggering the merge
            
        Returns:
            dict with merge results
            
        Raises:
            ValueError: If no data available to merge
        """
        logger.info(f"Starting merge operation by user: {user.email}")
        
        # Check if data is ready
        status = MergeService.check_staging_data()
        if not status['ready_to_merge']:
            raise ValueError("No PO data available to merge")
        
        # Generate batch ID
        batch_id = uuid.uuid4()
        
        # Get latest upload files
        latest_po_upload = UploadHistory.objects.filter(
            file_type=UploadHistory.FileType.PO,
            status=UploadHistory.Status.COMPLETED
        ).order_by('-uploaded_at').first()
        
        latest_acceptance_upload = UploadHistory.objects.filter(
            file_type=UploadHistory.FileType.ACCEPTANCE,
            status=UploadHistory.Status.COMPLETED
        ).order_by('-uploaded_at').first()
        
        # Create merge history
        merge_history = MergeHistory.objects.create(
            batch_id=batch_id,
            merged_by=user,
            po_file=latest_po_upload,
            acceptance_file=latest_acceptance_upload,
            status=MergeHistory.Status.IN_PROGRESS,
            po_records_count=status['po_count'],
            acceptance_records_count=status['acceptance_count']
        )
        
        try:
            # Ensure accounts are extracted
            logger.info("Extracting accounts from PO data...")
            AccountService.extract_accounts_from_pos()
            
            # Delete old merged data
            logger.info("Deleting old merged data...")
            deleted_count = MergedData.objects.all().delete()
            logger.info(f"Deleted {deleted_count[0]} old merged records")
            
            # Execute merge query
            logger.info("Executing merge query...")
            base_filter = "1=1"  # No filter, get all records
            
            merge_query = MergeService.MERGED_DATA_QUERY.format(base_filter=base_filter)
            
            with connection.cursor() as cursor:
                cursor.execute(merge_query)
                columns = [col[0] for col in cursor.description]
                results = cursor.fetchall()
            
            logger.info(f"Query returned {len(results)} records")
            
            # Convert results to MergedData objects
            merged_records = []
            for row in results:
                row_dict = dict(zip(columns, row))
                
                merged_record = MergedData(
                    batch_id=batch_id,
                    po_id=row_dict['po_id'],
                    po_number=row_dict['po_no'],
                    po_line_no=row_dict['po_line'],
                    project_name=row_dict['project_name'],
                    project_code=row_dict['project_code'],
                    account_name=row_dict['account_name'],
                    site_name=row_dict.get('site_name'),
                    site_code=row_dict['site_code'],
                    item_code=row_dict.get('item_code'),
                    item_description=row_dict['item_desc'],
                    category=row_dict['category'],
                    unit_price=row_dict['unit_price'],
                    requested_qty=row_dict['req_qty'],
                    line_amount=row_dict['line_amount'],
                    unit=row_dict.get('unit'),
                    currency=row_dict.get('currency'),
                    payment_terms=row_dict['payment_terms'],
                    publish_date=row_dict['publish_date'],
                    ac_date=row_dict['ac_date'],
                    pac_date=row_dict['pac_date'],
                    ac_amount=row_dict['ac_amount'],
                    pac_amount=row_dict['pac_amount'],
                    remaining=row_dict['remaining'],
                    status=row_dict['status'],
                    po_status=row_dict.get('po_status'),
                    is_assigned=False,
                    has_external_po=False
                )
                merged_records.append(merged_record)
            
            # Bulk create merged records
            if merged_records:
                MergedData.objects.bulk_create(merged_records, batch_size=1000)
                logger.info(f"Created {len(merged_records)} merged records")
            
            # Update merge history
            merge_history.total_records = len(merged_records)
            merge_history.status = MergeHistory.Status.COMPLETED
            merge_history.completed_at = timezone.now()
            merge_history.save()
            
            logger.info(f"Merge completed successfully: {len(merged_records)} records")
            
            return {
                'success': True,
                'batch_id': str(batch_id),
                'merged_records': len(merged_records),
                'po_records': status['po_count'],
                'acceptance_records': status['acceptance_count'],
                'merged_at': merge_history.merged_at
            }
            
        except Exception as e:
            logger.error(f"Merge failed: {str(e)}", exc_info=True)
            
            # Update merge history as failed
            merge_history.status = MergeHistory.Status.FAILED
            merge_history.error_message = str(e)
            merge_history.save()
            
            raise ValueError(f"Merge operation failed: {str(e)}")
    
    @staticmethod
    def get_merge_summary(batch_id):
        """
        Get summary statistics for a merge batch
        
        Args:
            batch_id: Batch UUID
            
        Returns:
            dict with summary statistics
        """
        from django.db.models import Count, Sum, Q
        
        merged_data = MergedData.objects.filter(batch_id=batch_id)
        
        summary = {
            'total_records': merged_data.count(),
            'by_status': merged_data.values('status').annotate(count=Count('id')),
            'by_category': merged_data.values('category').annotate(count=Count('id')),
            'total_amount': merged_data.aggregate(total=Sum('line_amount'))['total'],
            'total_remaining': merged_data.aggregate(total=Sum('remaining'))['total'],
            'assigned_count': merged_data.filter(is_assigned=True).count(),
            'external_po_count': merged_data.filter(has_external_po=True).count(),
        }
        
        return summary