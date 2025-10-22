from django.urls import path
from .views import (
    UploadPOView, UploadAcceptanceView, TriggerMergeView,
    MergeStatusView, MergedDataListView, MergedDataExportView,
    UploadHistoryView, MergeHistoryView
)

urlpatterns = [
    # Upload endpoints
    path('upload/po/', UploadPOView.as_view(), name='upload-po'),
    path('upload/acceptance/', UploadAcceptanceView.as_view(), name='upload-acceptance'),
    
    # Merge endpoints
    path('merge/trigger/', TriggerMergeView.as_view(), name='trigger-merge'),
    path('merge/status/', MergeStatusView.as_view(), name='merge-status'),
    path('merge/history/', MergeHistoryView.as_view(), name='merge-history'),
    
    # Merged data endpoints
    path('merged-data/', MergedDataListView.as_view(), name='merged-data-list'),
    path('merged-data/export/', MergedDataExportView.as_view(), name='merged-data-export'),
    
    # History
    path('upload-history/', UploadHistoryView.as_view(), name='upload-history'),
]
