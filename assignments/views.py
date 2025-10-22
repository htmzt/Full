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