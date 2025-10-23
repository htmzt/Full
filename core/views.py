"""
Core Views - Upload, Merge, Data
"""
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.http import HttpResponse
import pandas as pd
from io import BytesIO

from .models import MergedData, UploadHistory, MergeHistory
from .serializers import (
    MergedDataSerializer, UploadHistorySerializer,
    MergeHistorySerializer, MergeStatusSerializer
)
from .services.upload_service import UploadService
from .services.merge_service import MergeService
from accounts.permissions import CanUploadFiles, CanTriggerMerge


class UploadPOView(APIView):
    """Upload PO Excel file"""
    permission_classes = [permissions.IsAuthenticated, CanUploadFiles]
    
    def post(self, request):
        """Upload PO file"""
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['file']
        
        try:
            result = UploadService.upload_po_file(file, request.user)
            return Response(result, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Upload failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UploadAcceptanceView(APIView):
    """Upload Acceptance Excel file"""
    permission_classes = [permissions.IsAuthenticated, CanUploadFiles]
    
    def post(self, request):
        """Upload Acceptance file"""
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['file']
        
        try:
            result = UploadService.upload_acceptance_file(file, request.user)
            return Response(result, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Upload failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TriggerMergeView(APIView):
    """Trigger merge operation"""
    permission_classes = [permissions.IsAuthenticated, CanTriggerMerge]
    
    def post(self, request):
        """Trigger merge"""
        try:
            result = MergeService.trigger_merge(request.user)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Merge failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MergeStatusView(APIView):
    """Check staging data status"""
    permission_classes = [permissions.IsAuthenticated, CanTriggerMerge]
    
    def get(self, request):
        """Get merge status"""
        result = MergeService.check_staging_data(request.user)
        serializer = MergeStatusSerializer(result)
        return Response(serializer.data)


class MergedDataPagination(PageNumberPagination):
    """Custom pagination for merged data"""
    page_size = 50
    page_size_query_param = 'per_page'
    max_page_size = 1000


class MergedDataListView(generics.ListAPIView):
    """List merged data with filters"""
    serializer_class = MergedDataSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MergedDataPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'category', 'project_name', 'site_code', 'is_assigned', 'has_external_po']
    search_fields = ['po_number', 'po_line_no', 'item_description', 'project_name']
    ordering_fields = ['po_number', 'po_line_no', 'line_amount', 'merged_at']
    ordering = ['po_number', 'po_line_no']
    
    def get_queryset(self):
        """Filter queryset based on user role"""
        user = self.request.user
        
        # MergedData doesn't have a user field, so everyone sees all data
        # Filter by role-specific permissions
        queryset = MergedData.objects.all()
        
        # If user is PM, only show assigned POs
        if user.role == 'PM' and not user.can_view_all_pos:
            queryset = queryset.filter(
                is_assigned=True,
                assigned_to=user
            )
        
        # If user is SBC, only show their assigned work
        elif user.role == 'SBC':
            queryset = queryset.filter(
                is_assigned=True,
                assigned_to=user
            )
        
        return queryset


class MergedDataExportView(APIView):
    """Export merged data to Excel"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Export to Excel"""
        user = request.user
        
        # Get filtered queryset based on role
        if user.role == 'PM' and not user.can_view_all_pos:
            queryset = MergedData.objects.filter(
                is_assigned=True,
                assigned_to=user
            )
        elif user.role == 'SBC':
            queryset = MergedData.objects.filter(
                is_assigned=True,
                assigned_to=user
            )
        else:
            queryset = MergedData.objects.all()
        
        # Apply filters from query params
        status_filter = request.query_params.get('status')
        category_filter = request.query_params.get('category')
        project_filter = request.query_params.get('project_name')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        if project_filter:
            queryset = queryset.filter(project_name__icontains=project_filter)
        
        # Convert to DataFrame
        data = list(queryset.values(
            'po_id', 'po_number', 'po_line_no', 'project_name', 'site_name',
            'item_description', 'category', 'unit_price', 'requested_qty',
            'line_amount', 'payment_terms', 'publish_date',
            'ac_date', 'pac_date', 'ac_amount', 'pac_amount',
            'status', 'remaining'
        ))
        
        df = pd.DataFrame(data)
        
        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Merged Data')
        
        output.seek(0)
        
        # Create response
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=merged_data.xlsx'
        
        return response


class UploadHistoryView(generics.ListAPIView):
    """List upload history"""
    serializer_class = UploadHistorySerializer
    permission_classes = [permissions.IsAuthenticated, CanUploadFiles]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['file_type', 'status']
    ordering = ['-uploaded_at']
    
    def get_queryset(self):
        return UploadHistory.objects.filter(user=self.request.user)


class MergeHistoryView(generics.ListAPIView):
    """List merge history"""
    serializer_class = MergeHistorySerializer
    permission_classes = [permissions.IsAuthenticated, CanTriggerMerge]
    ordering = ['-merged_at']
    
    def get_queryset(self):
        return MergeHistory.objects.filter(merged_by=self.request.user)