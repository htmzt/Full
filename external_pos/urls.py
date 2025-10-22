from django.urls import path
from .views import (
    ExternalPOCreateView, ExternalPOListView, ExternalPODetailView,
    ExternalPOUpdateView, ExternalPOSubmitView, ExternalPODeleteView,
    AvailablePOLinesView, PDApprovalListView, AdminApprovalListView,
    ApprovalRespondView, SBCWorkListView, SBCRespondView
)

urlpatterns = [
    # External PO CRUD
    path('', ExternalPOListView.as_view(), name='external-po-list'),
    path('create/', ExternalPOCreateView.as_view(), name='external-po-create'),
    path('<uuid:pk>/', ExternalPODetailView.as_view(), name='external-po-detail'),
    path('<uuid:pk>/update/', ExternalPOUpdateView.as_view(), name='external-po-update'),
    path('<uuid:pk>/delete/', ExternalPODeleteView.as_view(), name='external-po-delete'),
    path('<uuid:pk>/submit/', ExternalPOSubmitView.as_view(), name='external-po-submit'),
    
    # Available PO lines
    path('available-lines/', AvailablePOLinesView.as_view(), name='available-lines'),
    
    # Approval workflows
    path('approvals/pd/', PDApprovalListView.as_view(), name='pd-approval-list'),
    path('approvals/admin/', AdminApprovalListView.as_view(), name='admin-approval-list'),
    path('approvals/<uuid:pk>/respond/', ApprovalRespondView.as_view(), name='approval-respond'),
    
    # SBC work
    path('sbc/my-work/', SBCWorkListView.as_view(), name='sbc-work-list'),
    path('sbc/<uuid:pk>/respond/', SBCRespondView.as_view(), name='sbc-respond'),
]