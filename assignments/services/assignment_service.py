"""
Assignment Service - Handle PO assignment workflow
"""
from django.db import transaction
from django.utils import timezone
from assignments.models import POAssignment
from core.models import MergedData
from accounts.models import User
import logging

logger = logging.getLogger(__name__)


class AssignmentService:
    """Service for PO assignments"""
    
    @staticmethod
    @transaction.atomic
    def create_assignment(po_ids, assigned_to_user_id, assigned_by_user, notes=None):
        """
        Create PO assignment
        
        Args:
            po_ids: List of PO IDs to assign
            assigned_to_user_id: UUID of user to assign to
            assigned_by_user: User object who is creating assignment
            notes: Optional assignment notes
            
        Returns:
            POAssignment object
            
        Raises:
            ValueError: If PO IDs are invalid or already assigned
        """
        logger.info(f"Creating assignment: {len(po_ids)} POs to user {assigned_to_user_id}")
        
        # Get assigned_to user
        try:
            assigned_to_user = User.objects.get(id=assigned_to_user_id)
        except User.DoesNotExist:
            raise ValueError("Assigned user not found")
        
        # Validate PO IDs exist and are not assigned
        merged_data_records = MergedData.objects.filter(
            user=assigned_by_user,
            po_id__in=po_ids
        )
        
        if merged_data_records.count() != len(po_ids):
            raise ValueError("Some PO IDs not found in merged data")
        
        # Check if any are already assigned
        already_assigned = merged_data_records.filter(is_assigned=True)
        if already_assigned.exists():
            assigned_ids = list(already_assigned.values_list('po_id', flat=True))
            raise ValueError(f"Some POs are already assigned: {assigned_ids}")
        
        # Create assignment
        assignment = POAssignment.objects.create(
            po_ids=po_ids,
            assigned_to=assigned_to_user,
            assigned_by=assigned_by_user,
            status=POAssignment.Status.PENDING,
            assignment_notes=notes or ''
        )
        
        logger.info(f"Assignment created: {assignment.id}")
        
        return assignment
    
    @staticmethod
    @transaction.atomic
    def respond_to_assignment(assignment_id, action, user, rejection_reason=None):
        """
        Respond to assignment (approve/reject)
        
        Args:
            assignment_id: Assignment UUID
            action: 'APPROVE' or 'REJECT'
            user: User responding
            rejection_reason: Required if rejecting
            
        Returns:
            Updated POAssignment object
            
        Raises:
            ValueError: If invalid action or assignment
        """
        logger.info(f"User {user.email} responding to assignment {assignment_id}: {action}")
        
        # Get assignment
        try:
            assignment = POAssignment.objects.select_for_update().get(id=assignment_id)
        except POAssignment.DoesNotExist:
            raise ValueError("Assignment not found")
        
        # Check user is the assigned user
        if assignment.assigned_to != user:
            raise ValueError("You are not the assigned user for this assignment")
        
        # Check status is PENDING
        if assignment.status != POAssignment.Status.PENDING:
            raise ValueError(f"Assignment already responded to: {assignment.status}")
        
        if action == 'APPROVE':
            # Update assignment status
            assignment.status = POAssignment.Status.APPROVED
            assignment.responded_at = timezone.now()
            assignment.save()
            
            # Mark PO lines as assigned in merged_data
            MergedData.objects.filter(
                user=assignment.assigned_by,
                po_id__in=assignment.po_ids
            ).update(
                is_assigned=True,
                assigned_to=user
            )
            
            logger.info(f"Assignment approved: {assignment.id}")
            
        elif action == 'REJECT':
            if not rejection_reason:
                raise ValueError("Rejection reason is required")
            
            # Update assignment status
            assignment.status = POAssignment.Status.REJECTED
            assignment.rejection_reason = rejection_reason
            assignment.responded_at = timezone.now()
            assignment.save()
            
            logger.info(f"Assignment rejected: {assignment.id}")
        
        else:
            raise ValueError("Invalid action. Must be APPROVE or REJECT")
        
        return assignment
    
    @staticmethod
    def get_user_assignments(user, status=None):
        """
        Get assignments for a user
        
        Args:
            user: User object
            status: Optional status filter (PENDING, APPROVED, REJECTED)
            
        Returns:
            QuerySet of POAssignment
        """
        queryset = POAssignment.objects.filter(assigned_to=user)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_created_assignments(user, status=None):
        """
        Get assignments created by a user
        
        Args:
            user: User object
            status: Optional status filter
            
        Returns:
            QuerySet of POAssignment
        """
        queryset = POAssignment.objects.filter(assigned_by=user)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')