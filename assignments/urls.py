from django.urls import path
from .views import (
    AssignmentCreateView, AssignmentListView, AssignmentDetailView,
    AssignmentRespondView, MyAssignmentsView
)

urlpatterns = [
    path('', AssignmentListView.as_view(), name='assignment-list'),
    path('create/', AssignmentCreateView.as_view(), name='assignment-create'),
    path('my-assignments/', MyAssignmentsView.as_view(), name='my-assignments'),
    path('<uuid:pk>/', AssignmentDetailView.as_view(), name='assignment-detail'),
    path('<uuid:pk>/respond/', AssignmentRespondView.as_view(), name='assignment-respond'),
]