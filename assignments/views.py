"""
Assignment Views
"""
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import POAssignment
from .serializers import (
    AssignmentCreateSerializer, AssignmentRespondSerializer,
    AssignmentSerializer, AssignmentListSerializer
)
from .services.assignment_service import AssignmentService
from accounts.permissions import CanAssignPOs
from core.models import MergedData

from core.models import MergedData
from accounts.models import User
from django.db.models import Count, Q

class AssignmentCreateView(APIView):
    """Create PO assignment"""
    permission_classes = [permissions.IsAuthenticated, CanAssignPOs]
    
    def post(self, request):
        """Create assignment"""
        serializer = AssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            assignment = AssignmentService.create_assignment(
                po_ids=serializer.validated_data['po_ids'],
                assigned_to_user_id=serializer.validated_data['assigned_to_user_id'],
                assigned_by_user=request.user,
                notes=serializer.validated_data.get('assignment_notes')
            )
            
            response_serializer = AssignmentSerializer(assignment)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AssignmentListView(generics.ListAPIView):
    """List assignments created by current user"""
    serializer_class = AssignmentListSerializer
    permission_classes = [permissions.IsAuthenticated, CanAssignPOs]
    
    def get_queryset(self):
        status_filter = self.request.query_params.get('status')
        return AssignmentService.get_created_assignments(
            self.request.user,
            status=status_filter
        )


class AssignmentDetailView(generics.RetrieveAPIView):
    """Get assignment detail"""
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Can view if assigned to OR created by
        return POAssignment.objects.filter(
            assigned_to=user
        ) | POAssignment.objects.filter(
            assigned_by=user
        )


class AssignmentRespondView(APIView):
    """Respond to assignment (approve/reject)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        """Approve or reject assignment"""
        serializer = AssignmentRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            assignment = AssignmentService.respond_to_assignment(
                assignment_id=pk,
                action=serializer.validated_data['action'],
                user=request.user,
                rejection_reason=serializer.validated_data.get('rejection_reason')
            )
            
            response_serializer = AssignmentSerializer(assignment)
            return Response(response_serializer.data)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class MyAssignmentsView(APIView):
    """Get assignments assigned to me"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get my assignments grouped by status"""
        pending = AssignmentService.get_user_assignments(
            request.user,
            status=POAssignment.Status.PENDING
        )
        approved = AssignmentService.get_user_assignments(
            request.user,
            status=POAssignment.Status.APPROVED
        )
        rejected = AssignmentService.get_user_assignments(
            request.user,
            status=POAssignment.Status.REJECTED
        )
        
        return Response({
            'pending': AssignmentListSerializer(pending, many=True).data,
            'approved': AssignmentListSerializer(approved, many=True).data,
            'rejected': AssignmentListSerializer(rejected, many=True).data,
        })


class AvailableForAssignmentView(generics.ListAPIView):
    """
    Get all unassigned PO lines that can be assigned to users
    Access: Admin, PD only (can_assign_pos permission)
    """
    serializer_class = AvailablePOLineForAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated, CanAssignPOs]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'category', 'project_name', 'po_status', 'account_name']
    search_fields = ['po_number', 'po_line_no', 'item_description', 'project_name', 'site_name']
    ordering_fields = ['po_number', 'po_line_no', 'line_amount', 'publish_date']
    ordering = ['po_number', 'po_line_no']
    
    def get_queryset(self):
        """
        Return only unassigned PO lines
        These are available for assignment to users
        """
        return MergedData.objects.filter(
            is_assigned=False,
            has_external_po=False  # Only show lines not yet used in External POs
        )
    
    def list(self, request, *args, **kwargs):
        """Add pagination and counts"""
        queryset = self.filter_queryset(self.get_queryset())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })


class AssignableUsersView(generics.ListAPIView):
    """
    Get users who can receive PO assignments (ADMIN, PD, PM)
    Access: Admin, PD only (can_assign_pos permission)
    """
    serializer_class = AssignableUserSerializer
    permission_classes = [permissions.IsAuthenticated, CanAssignPOs]
    
    def get_queryset(self):
        """
        Return active users with assignable roles
        Annotate with count of currently assigned PO lines
        """
        return User.objects.filter(
            role__in=['ADMIN', 'PD', 'PM'],
            is_active=True
        ).annotate(
            current_assignment_count=Count(
                'assigned_pos',
                filter=Q(assigned_pos__is_assigned=True)
            )
        ).order_by('role', 'full_name')


class BulkAssignmentStatsView(APIView):
    """
    Get statistics for bulk assignment interface
    Access: Admin, PD only
    """
    permission_classes = [permissions.IsAuthenticated, CanAssignPOs]
    
    def get(self, request):
        """Return assignment statistics"""
        
        # Total unassigned PO lines
        total_unassigned = MergedData.objects.filter(
            is_assigned=False,
            has_external_po=False
        ).count()
        
        # Total assigned PO lines
        total_assigned = MergedData.objects.filter(
            is_assigned=True
        ).count()
        
        # Total PO lines with External POs
        total_with_external_po = MergedData.objects.filter(
            has_external_po=True
        ).count()
        
        # Pending assignments
        pending_assignments = POAssignment.objects.filter(
            status=POAssignment.Status.PENDING
        ).count()
        
        # Assignment distribution by user
        assignment_distribution = User.objects.filter(
            role__in=['ADMIN', 'PD', 'PM'],
            is_active=True
        ).annotate(
            assigned_count=Count(
                'assigned_pos',
                filter=Q(assigned_pos__is_assigned=True)
            )
        ).values('full_name', 'role', 'assigned_count').order_by('-assigned_count')
        
        return Response({
            'total_unassigned': total_unassigned,
            'total_assigned': total_assigned,
            'total_with_external_po': total_with_external_po,
            'pending_assignments': pending_assignments,
            'assignment_distribution': list(assignment_distribution)
        })