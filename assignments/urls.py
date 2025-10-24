from django.urls import path
from .views import (
    AssignmentCreateView, AssignmentListView, AssignmentDetailView,
    AssignmentRespondView, MyAssignmentsView,
    AvailableForAssignmentView, AssignableUsersView, BulkAssignmentStatsView
)

urlpatterns = [
    # Existing assignment endpoints
    path('', AssignmentListView.as_view(), name='assignment-list'),
    path('create/', AssignmentCreateView.as_view(), name='assignment-create'),
    path('my-assignments/', MyAssignmentsView.as_view(), name='my-assignments'),
    path('<uuid:pk>/', AssignmentDetailView.as_view(), name='assignment-detail'),
    path('<uuid:pk>/respond/', AssignmentRespondView.as_view(), name='assignment-respond'),
    
    # NEW: Bulk assignment interface endpoints
    path('available-for-assignment/', AvailableForAssignmentView.as_view(), 
         name='available-for-assignment'),
    path('assignable-users/', AssignableUsersView.as_view(), 
         name='assignable-users'),
    path('assignment-stats/', BulkAssignmentStatsView.as_view(), 
         name='assignment-stats'),
]