"""
Merge Service - Merge PO and Acceptance data
"""
from django.db import transaction
from django.utils import timezone
from core.models import POStaging, AcceptanceStaging, MergedData, MergeHistory
import uuid
import logging

logger = logging.getLogger(__name__)


class MergeService:
    """Service for merging PO and Acceptance staging data"""
    
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
        Trigger merge operation
        
        This performs LEFT JOIN of PO + Acceptance staging
        and saves to merged_data table
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
            
            # Step 2: Get staging data
            po_staging = POStaging.objects.filter(user=user).select_related()
            acceptance_staging = AcceptanceStaging.objects.filter(user=user)
            
            # Build acceptance lookup dict for LEFT JOIN
            acceptance_lookup = {}
            for acc in acceptance_staging:
                key = f"{acc.po_number}-{acc.po_line_no}"
                if key not in acceptance_lookup:
                    acceptance_lookup[key] = {'ac_date': None, 'pac_date': None}
                
                if acc.milestone_type == 'AC1' and acc.application_processed:
                    acceptance_lookup[key]['ac_date'] = acc.application_processed
                elif acc.milestone_type == 'AC2' and acc.application_processed:
                    acceptance_lookup[key]['pac_date'] = acc.application_processed
            
            # Step 3: Create merged records
            merged_records = []
            for po in po_staging:
                po_id = f"{po.po_number}-{po.po_line_no}"
                acc_data = acceptance_lookup.get(po_id, {})
                
                # Calculate category
                category = 'Service'  # default
                if po.item_description:
                    desc_lower = po.item_description.lower()
                    if 'survey' in desc_lower:
                        category = 'Survey'
                    elif 'transportation' in desc_lower:
                        category = 'Transportation'
                    elif 'work order' in desc_lower:
                        if po.site_name and 'non du' in po.site_name.lower():
                            category = 'Site Engineer'
                        else:
                            category = 'Service'
                
                # Calculate payment terms
                payment_terms = ''
                if po.payment_terms:
                    pt = po.payment_terms.lower()
                    if 'cod' in pt:
                        payment_terms = 'ACPAC 100%'
                    elif 'ac1' in pt and 'ac2' in pt:
                        payment_terms = 'AC1 80 | PAC 20'
                    elif 'ac1' in pt:
                        payment_terms = 'ACPAC 100%'
                
                # Calculate amounts
                ac_amount = None
                pac_amount = None
                if po.line_amount:
                    ac_amount = round(po.line_amount * 0.80, 2)
                    pac_amount = round(po.line_amount * 0.20, 2)
                
                # Calculate status
                ac_date = acc_data.get('ac_date')
                pac_date = acc_data.get('pac_date')
                
                if 'cod' in (po.payment_terms or '').lower() or ('ac1' in (po.payment_terms or '').lower() and 'ac2' not in (po.payment_terms or '').lower()):
                    if po.requested_qty == 0:
                        status = 'CANCELLED'
                    elif ac_date:
                        status = 'CLOSED'
                    else:
                        status = 'Pending ACPAC'
                elif 'ac1' in (po.payment_terms or '').lower() and 'ac2' in (po.payment_terms or '').lower():
                    if po.po_status == 'CANCELLED':
                        status = 'CANCELLED'
                    elif po.po_status == 'CLOSED':
                        status = 'CLOSED'
                    elif not ac_date:
                        status = 'Pending AC80%'
                    elif not pac_date:
                        status = 'Pending PAC20%'
                    else:
                        status = 'CLOSED'
                else:
                    status = 'Unknown'
                
                # Calculate remaining
                remaining = 0
                if po.line_amount:
                    if 'cod' in (po.payment_terms or '').lower() or ('ac1' in (po.payment_terms or '').lower() and 'ac2' not in (po.payment_terms or '').lower()):
                        if po.requested_qty == 0:
                            remaining = 0
                        elif ac_date:
                            remaining = 0
                        else:
                            remaining = po.line_amount
                    elif 'ac1' in (po.payment_terms or '').lower() and 'ac2' in (po.payment_terms or '').lower():
                        if po.po_status in ['CANCELLED', 'CLOSED']:
                            remaining = 0
                        elif not ac_date:
                            remaining = po.line_amount
                        elif not pac_date:
                            remaining = pac_amount or 0
                        else:
                            remaining = 0
                
                # Create merged data record
                merged_record = MergedData(
                    user=user,
                    po_id=po_id,
                    po_number=po.po_number,
                    po_line_no=po.po_line_no,
                    project_name=po.project_name,
                    project_code=po.project_code,
                    site_name=po.site_name,
                    site_code=po.site_code,
                    item_code=po.item_code,
                    item_description=po.item_description,
                    category=category,
                    unit_price=po.unit_price,
                    requested_qty=po.requested_qty,
                    line_amount=po.line_amount,
                    unit=po.unit,
                    currency=po.currency,
                    payment_terms=payment_terms,
                    publish_date=po.publish_date,
                    ac_date=ac_date,
                    pac_date=pac_date,
                    ac_amount=ac_amount,
                    pac_amount=pac_amount,
                    status=status,
                    po_status=po.po_status,
                    remaining=remaining,
                    is_assigned=False,
                    has_external_po=False,
                    batch_id=batch_id
                )
                merged_records.append(merged_record)
            
            # Bulk create
            MergedData.objects.bulk_create(merged_records, batch_size=1000)
            merged_count = len(merged_records)
            
            logger.info(f"Created {merged_count} merged records")
            
            # Step 4: Create merge history
            merge_history = MergeHistory.objects.create(
                batch_id=batch_id,
                merged_by=user,
                total_records=merged_count,
                po_records_count=status_check['po_count'],
                acceptance_records_count=status_check['acceptance_count'],
                status=MergeHistory.Status.COMPLETED,
                notes=f"Merge triggered by {user.full_name}",
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
            
            # Record failure
            MergeHistory.objects.create(
                batch_id=batch_id,
                merged_by=user,
                total_records=0,
                status=MergeHistory.Status.FAILED,
                error_message=str(e)
            )
            
            raise