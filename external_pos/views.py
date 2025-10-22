"""
External PO Views
"""
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import ExternalPO
from .serializers import (
    ExternalPOCreateSerializer, ExternalPOUpdateSerializer,
    ApprovalRespondSerializer, SBCRespondSerializer,
    ExternalPOSerializer, ExternalPOListSerializer,
    AvailablePOLineSerializer
)
from .services.external_po_service import ExternalPOService
from accounts.permissions import (
    CanCreateExternalPO, CanApproveLevel1, CanApproveLevel2, IsSBC
)


class AvailablePOLinesView(APIView):
    """Get available PO lines for creating External PO"""
    permission_classes = [permissions.IsAuthenticated, CanCreateExternalPO]
    
    def get(self, request):
        """Get available lines (role-filtered)"""
        po_lines = ExternalPOService.get_available_po_lines(request.user)
        
        # Convert to dict format
        data = po_lines.values(
            'po_id', 'po_number', 'po_line_no', 'project_name',
            'item_description', 'line_amount', 'payment_terms', 'status'
        )
        
        serializer = AvailablePOLineSerializer(data, many=True)
        return Response(serializer.data)


class ExternalPOCreateView(APIView):
    """Create External PO"""
    permission_classes = [permissions.IsAuthenticated, CanCreateExternalPO]
    
    def post(self, request):
        """Create External PO"""
        serializer = ExternalPOCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            external_po = ExternalPOService.create_external_po(
                po_lines_data=serializer.validated_data['po_lines'],
                assigned_to_sbc_id=serializer.validated_data['assigned_to_sbc_id'],
                created_by_user=request.user,
                assignment_notes=serializer.validated_data.get('assignment_notes'),
                internal_notes=serializer.validated_data.get('internal_notes'),
                save_as_draft=serializer.validated_data.get('save_as_draft', True)
            )
            
            response_serializer = ExternalPOSerializer(external_po)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ExternalPOListView(generics.ListAPIView):
    """List External POs"""
    serializer_class = ExternalPOListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        
        if user.role in ['ADMIN', 'PD']:
            # Admin/PD see all
            return ExternalPO.objects.all().order_by('-created_at')
        elif user.role == 'PM':
            # PM sees only their created ones
            return ExternalPO.objects.filter(created_by=user).order_by('-created_at')
        elif user.role == 'SBC':
            # SBC sees only approved ones assigned to them
            return ExternalPO.objects.filter(
                assigned_to_sbc=user,
                status=ExternalPO.Status.APPROVED
            ).order_by('-admin_approved_at')
        else:
            return ExternalPO.objects.none()


class ExternalPODetailView(generics.RetrieveAPIView):
    """Get External PO detail"""
    serializer_class = ExternalPOSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        
        if user.role in ['ADMIN', 'PD']:
            return ExternalPO.objects.all()
        elif user.role == 'PM':
            return ExternalPO.objects.filter(created_by=user)
        elif user.role == 'SBC':
            return ExternalPO.objects.filter(
                assigned_to_sbc=user,
                status=ExternalPO.Status.APPROVED
            )
        else:
            return ExternalPO.objects.none()


class ExternalPOUpdateView(APIView):
    """Update External PO (draft only)"""
    permission_classes = [permissions.IsAuthenticated, CanCreateExternalPO]
    
    def put(self, request, pk):
        """Update draft External PO"""
        serializer = ExternalPOUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            external_po = ExternalPOService.update_external_po(
                external_po_id=pk,
                user=request.user,
                **serializer.validated_data
            )
            
            response_serializer = ExternalPOSerializer(external_po)
            return Response(response_serializer.data)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ExternalPODeleteView(APIView):
    """Delete External PO (draft only)"""
    permission_classes = [permissions.IsAuthenticated, CanCreateExternalPO]
    
    def delete(self, request, pk):
        """Delete draft External PO"""
        try:
            external_po = ExternalPO.objects.get(id=pk, created_by=request.user)
            
            if external_po.status != ExternalPO.Status.DRAFT:
                return Response(
                    {'error': 'Can only delete draft External POs'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            external_po.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except ExternalPO.DoesNotExist:
            return Response(
                {'error': 'External PO not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ExternalPOSubmitView(APIView):
    """Submit External PO for approval"""
    permission_classes = [permissions.IsAuthenticated, CanCreateExternalPO]
    
    def post(self, request, pk):
        """Submit for approval"""
        try:
            external_po = ExternalPOService.submit_external_po(pk, request.user)
            
            response_serializer = ExternalPOSerializer(external_po)
            return Response(response_serializer.data)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PDApprovalListView(generics.ListAPIView):
    """List External POs pending PD approval"""
    serializer_class = ExternalPOListSerializer
    permission_classes = [permissions.IsAuthenticated, CanApproveLevel1]
    
    def get_queryset(self):
        return ExternalPOService.get_pending_pd_approvals()


class AdminApprovalListView(generics.ListAPIView):
    """List External POs pending Admin approval"""
    serializer_class = ExternalPOListSerializer
    permission_classes = [permissions.IsAuthenticated, CanApproveLevel2]
    
    def get_queryset(self):
        return ExternalPOService.get_pending_admin_approvals()


class ApprovalRespondView(APIView):
    """PD or Admin approve/reject External PO"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        """Approve or reject"""
        serializer = ApprovalRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        try:
            # Determine if PD or Admin approval
            if user.can_approve_level_1:
                external_po = ExternalPOService.pd_respond(
                    external_po_id=pk,
                    user=user,
                    action=serializer.validated_data['action'],
                    remarks=serializer.validated_data.get('remarks'),
                    rejection_reason=serializer.validated_data.get('rejection_reason')
                )
            elif user.can_approve_level_2:
                external_po = ExternalPOService.admin_respond(
                    external_po_id=pk,
                    user=user,
                    action=serializer.validated_data['action'],
                    remarks=serializer.validated_data.get('remarks'),
                    rejection_reason=serializer.validated_data.get('rejection_reason')
                )
            else:
                return Response(
                    {'error': 'User does not have approval permission'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            response_serializer = ExternalPOSerializer(external_po)
            return Response(response_serializer.data)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class SBCWorkListView(generics.ListAPIView):
    """List approved External POs for SBC"""
    serializer_class = ExternalPOListSerializer
    permission_classes = [permissions.IsAuthenticated, IsSBC]
    
    def get_queryset(self):
        return ExternalPOService.get_sbc_work(self.request.user)


class SBCRespondView(APIView):
    """SBC accept/reject External PO"""
    permission_classes = [permissions.IsAuthenticated, IsSBC]
    
    def post(self, request, pk):
        """Accept or reject"""
        serializer = SBCRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            external_po = ExternalPOService.sbc_respond(
                external_po_id=pk,
                user=request.user,
                action=serializer.validated_data['action'],
                rejection_reason=serializer.validated_data.get('rejection_reason')
            )
            
            response_serializer = ExternalPOSerializer(external_po)
            return Response(response_serializer.data)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )