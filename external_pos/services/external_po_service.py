"""
External PO Service - Handle External PO workflow with 2-level approval
"""
from django.db import transaction
from django.utils import timezone
from external_pos.models import ExternalPO
from core.models import MergedData
from accounts.models import User
from decimal import Decimal
import logging
from django.db import models

logger = logging.getLogger(__name__)


class ExternalPOService:
    """Service for External PO management"""
    
    @staticmethod
    def get_available_po_lines(user):
        """
        Get available PO lines for creating External PO
        
        For PM: Only assigned & approved PO lines
        For Admin/PD: All assigned PO lines (or optionally all available)
        
        Args:
            user: User object
            
        Returns:
            QuerySet of MergedData
        """
        base_query = MergedData.objects.filter(
            has_external_po=False  # Not yet used in External PO
        )
        
        if user.role == 'PM':
            # PM sees only their assigned POs
            return base_query.filter(
                is_assigned=True,
                assigned_to=user
            )
        elif user.role in ['ADMIN', 'PD']:
            # Admin/PD can create External PO from any assigned PO
            # Or optionally: show ALL available POs (even unassigned)
            # Option 1: Only assigned POs
            return base_query.filter(is_assigned=True)
            
            # Option 2: All available POs (uncomment if needed)
            # return base_query
        else:
            # Others cannot create External POs
            return MergedData.objects.none()
        
    @staticmethod
    @transaction.atomic
    def create_external_po(po_lines_data, assigned_to_sbc_id, created_by_user, 
                          assignment_notes=None, internal_notes=None, save_as_draft=True):
        """
        Create External PO
        
        Args:
            po_lines_data: List of dicts with po_id, po_number, po_line
            assigned_to_sbc_id: UUID of SBC user
            created_by_user: User creating the External PO
            assignment_notes: Notes for SBC
            internal_notes: Internal notes (SBC cannot see)
            save_as_draft: If True, save as DRAFT; if False, submit immediately
            
        Returns:
            ExternalPO object
            
        Raises:
            ValueError: If validation fails
        """
        logger.info(f"Creating External PO: {len(po_lines_data)} lines by {created_by_user.email}")
        
        # Get SBC user
        try:
            sbc_user = User.objects.get(id=assigned_to_sbc_id, role='SBC')
        except User.DoesNotExist:
            raise ValueError("SBC user not found")
        
        # Extract PO IDs
        po_ids = [line['po_id'] for line in po_lines_data]
        
        # Validate PO lines are available
        merged_data_records = MergedData.objects.filter(
            user=created_by_user,
            po_id__in=po_ids
        )
        
        if merged_data_records.count() != len(po_ids):
            raise ValueError("Some PO IDs not found")
        
        # Check if PM, validate they're assigned
        if created_by_user.role == 'PM':
            not_assigned = merged_data_records.filter(
                is_assigned=False
            )
            if not_assigned.exists():
                raise ValueError("PM can only create External POs from assigned PO lines")
        
        # Check if already used
        already_used = merged_data_records.filter(has_external_po=True)
        if already_used.exists():
            used_ids = list(already_used.values_list('po_id', flat=True))
            raise ValueError(f"Some PO lines already used in External PO: {used_ids}")
        
        # Extract unique PO numbers
        po_numbers = list(set([line['po_number'] for line in po_lines_data]))
        
        # Calculate estimated total amount
        total_amount = merged_data_records.aggregate(
            total=models.Sum('line_amount')
        )['total'] or Decimal('0.00')
        
        # Create External PO
        external_po = ExternalPO.objects.create(
            po_numbers=po_numbers,
            po_lines_data=po_lines_data,
            created_by=created_by_user,
            assigned_to_sbc=sbc_user,
            status=ExternalPO.Status.DRAFT,
            assignment_notes=assignment_notes or '',
            internal_notes=internal_notes or '',
            estimated_total_amount=total_amount
        )
        
        logger.info(f"External PO created: {external_po.internal_po_id}")
        
        # If not draft, submit immediately
        if not save_as_draft:
            return ExternalPOService.submit_external_po(external_po.id, created_by_user)
        
        return external_po
    
    @staticmethod
    @transaction.atomic
    def update_external_po(external_po_id, user, **update_data):
        """
        Update External PO (draft only)
        
        Args:
            external_po_id: External PO UUID
            user: User updating
            update_data: Fields to update
            
        Returns:
            Updated ExternalPO object
            
        Raises:
            ValueError: If not draft or validation fails
        """
        try:
            external_po = ExternalPO.objects.select_for_update().get(id=external_po_id)
        except ExternalPO.DoesNotExist:
            raise ValueError("External PO not found")
        
        # Check user created it
        if external_po.created_by != user:
            raise ValueError("You can only update External POs you created")
        
        # Check status is DRAFT
        if external_po.status != ExternalPO.Status.DRAFT:
            raise ValueError("Can only update draft External POs")
        
        # Update fields
        for field, value in update_data.items():
            if hasattr(external_po, field):
                setattr(external_po, field, value)
        
        external_po.save()
        
        logger.info(f"External PO updated: {external_po.internal_po_id}")
        
        return external_po
    
    @staticmethod
    @transaction.atomic
    def submit_external_po(external_po_id, user):
        """
        Submit External PO for approval
        
        Args:
            external_po_id: External PO UUID
            user: User submitting
            
        Returns:
            Updated ExternalPO object
            
        Raises:
            ValueError: If validation fails
        """
        try:
            external_po = ExternalPO.objects.select_for_update().get(id=external_po_id)
        except ExternalPO.DoesNotExist:
            raise ValueError("External PO not found")
        
        # Check user created it
        if external_po.created_by != user:
            raise ValueError("You can only submit External POs you created")
        
        # Check status is DRAFT
        if external_po.status != ExternalPO.Status.DRAFT:
            raise ValueError(f"Cannot submit External PO with status: {external_po.status}")
        
        # Mark PO lines as used
        po_ids = [line['po_id'] for line in external_po.po_lines_data]
        MergedData.objects.filter(
            po_id__in=po_ids
        ).update(
            has_external_po=True,
            external_po_id=external_po.id
        )
        
        # Update status
        external_po.status = ExternalPO.Status.PENDING_PD_APPROVAL
        external_po.submitted_at = timezone.now()
        external_po.save()
        
        logger.info(f"External PO submitted: {external_po.internal_po_id}")
        
        return external_po
    
    @staticmethod
    @transaction.atomic
    def pd_respond(external_po_id, user, action, remarks=None, rejection_reason=None):
        """
        PD approve or reject External PO (Level 1)
        
        Args:
            external_po_id: External PO UUID
            user: PD user
            action: 'APPROVE' or 'REJECT'
            remarks: Optional remarks
            rejection_reason: Required if rejecting
            
        Returns:
            Updated ExternalPO object
            
        Raises:
            ValueError: If validation fails
        """
        logger.info(f"PD {user.email} responding to External PO {external_po_id}: {action}")
        
        try:
            external_po = ExternalPO.objects.select_for_update().get(id=external_po_id)
        except ExternalPO.DoesNotExist:
            raise ValueError("External PO not found")
        
        # Check user is PD
        if not user.can_approve_level_1:
            raise ValueError("User does not have PD approval permission")
        
        # Check status
        if external_po.status != ExternalPO.Status.PENDING_PD_APPROVAL:
            raise ValueError(f"External PO is not pending PD approval: {external_po.status}")
        
        if action == 'APPROVE':
            external_po.status = ExternalPO.Status.REJECTED
            external_po.rejected_by = user
            external_po.rejected_at = timezone.now()
            external_po.rejection_reason = rejection_reason
            external_po.save()
            
            logger.info(f"PD rejected: {external_po.internal_po_id}")
        
        else:
            raise ValueError("Invalid action")
        
        return external_po
    
    @staticmethod
    @transaction.atomic
    def admin_respond(external_po_id, user, action, remarks=None, rejection_reason=None):
        """
        Admin approve or reject External PO (Level 2 - Final)
        
        Args:
            external_po_id: External PO UUID
            user: Admin user
            action: 'APPROVE' or 'REJECT'
            remarks: Optional remarks
            rejection_reason: Required if rejecting
            
        Returns:
            Updated ExternalPO object
            
        Raises:
            ValueError: If validation fails
        """
        logger.info(f"Admin {user.email} responding to External PO {external_po_id}: {action}")
        
        try:
            external_po = ExternalPO.objects.select_for_update().get(id=external_po_id)
        except ExternalPO.DoesNotExist:
            raise ValueError("External PO not found")
        
        # Check user is Admin
        if not user.can_approve_level_2:
            raise ValueError("User does not have Admin approval permission")
        
        # Check status
        if external_po.status != ExternalPO.Status.PENDING_ADMIN_APPROVAL:
            raise ValueError(f"External PO is not pending Admin approval: {external_po.status}")
        
        if action == 'APPROVE':
            external_po.status = ExternalPO.Status.APPROVED
            external_po.admin_approved_by = user
            external_po.admin_approved_at = timezone.now()
            external_po.admin_remarks = remarks or ''
            external_po.save()
            
            logger.info(f"Admin approved: {external_po.internal_po_id}")
            
        elif action == 'REJECT':
            if not rejection_reason:
                raise ValueError("Rejection reason required")
            
            # Un-mark PO lines
            po_ids = [line['po_id'] for line in external_po.po_lines_data]
            MergedData.objects.filter(
                po_id__in=po_ids
            ).update(
                has_external_po=False,
                external_po_id=None
            )
            
            external_po.status = ExternalPO.Status.REJECTED
            external_po.rejected_by = user
            external_po.rejected_at = timezone.now()
            external_po.rejection_reason = rejection_reason
            external_po.save()
            
            logger.info(f"Admin rejected: {external_po.internal_po_id}")
        
        else:
            raise ValueError("Invalid action")
        
        return external_po
    
    @staticmethod
    @transaction.atomic
    def sbc_respond(external_po_id, user, action, rejection_reason=None):
        """
        SBC accept or reject External PO
        
        Args:
            external_po_id: External PO UUID
            user: SBC user
            action: 'ACCEPT' or 'REJECT'
            rejection_reason: Required if rejecting
            
        Returns:
            Updated ExternalPO object
            
        Raises:
            ValueError: If validation fails
        """
        logger.info(f"SBC {user.email} responding to External PO {external_po_id}: {action}")
        
        try:
            external_po = ExternalPO.objects.select_for_update().get(id=external_po_id)
        except ExternalPO.DoesNotExist:
            raise ValueError("External PO not found")
        
        # Check user is the assigned SBC
        if external_po.assigned_to_sbc != user:
            raise ValueError("You are not the assigned SBC for this External PO")
        
        # Check status is APPROVED
        if external_po.status != ExternalPO.Status.APPROVED:
            raise ValueError(f"External PO must be approved before SBC response: {external_po.status}")
        
        if action == 'ACCEPT':
            external_po.sbc_response_status = ExternalPO.SBCResponseStatus.ACCEPTED
            external_po.sbc_accepted_at = timezone.now()
            external_po.save()
            
            logger.info(f"SBC accepted: {external_po.internal_po_id}")
            
        elif action == 'REJECT':
            if not rejection_reason:
                raise ValueError("Rejection reason required")
            
            # Un-mark PO lines
            po_ids = [line['po_id'] for line in external_po.po_lines_data]
            MergedData.objects.filter(
                po_id__in=po_ids
            ).update(
                has_external_po=False,
                external_po_id=None
            )
            
            # Send back to PD approval
            external_po.status = ExternalPO.Status.PENDING_PD_APPROVAL
            external_po.sbc_response_status = ExternalPO.SBCResponseStatus.REJECTED
            external_po.sbc_rejection_reason = rejection_reason
            external_po.save()
            
            logger.info(f"SBC rejected: {external_po.internal_po_id}")
        
        else:
            raise ValueError("Invalid action")
        
        return external_po
    
    @staticmethod
    def get_pending_pd_approvals():
        """Get External POs pending PD approval"""
        return ExternalPO.objects.filter(
            status=ExternalPO.Status.PENDING_PD_APPROVAL
        ).order_by('-submitted_at')
    
    @staticmethod
    def get_pending_admin_approvals():
        """Get External POs pending Admin approval"""
        return ExternalPO.objects.filter(
            status=ExternalPO.Status.PENDING_ADMIN_APPROVAL
        ).order_by('-pd_approved_at')
    
    @staticmethod
    def get_sbc_work(sbc_user):
        """Get approved External POs for SBC"""
        return ExternalPO.objects.filter(
            assigned_to_sbc=sbc_user,
            status=ExternalPO.Status.APPROVED
        ).order_by('-admin_approved_at')
