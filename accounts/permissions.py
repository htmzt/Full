"""
Custom Permissions
"""
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Check if user is Admin"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'


class IsPD(permissions.BasePermission):
    """Check if user is PD"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'PD'


class IsAdminOrPD(permissions.BasePermission):
    """Check if user is Admin or PD"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['ADMIN', 'PD']


class CanUploadFiles(permissions.BasePermission):
    """Check if user can upload files"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.can_upload_files


class CanTriggerMerge(permissions.BasePermission):
    """Check if user can trigger merge"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.can_trigger_merge


class CanAssignPOs(permissions.BasePermission):
    """Check if user can assign POs"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.can_assign_pos


class CanViewAllPOs(permissions.BasePermission):
    """Check if user can view all POs"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.can_view_all_pos


class CanCreateExternalPO(permissions.BasePermission):
    """Check if user can create External POs"""
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and 
                (request.user.can_create_external_po_any or request.user.can_create_external_po_assigned))


class CanApproveLevel1(permissions.BasePermission):
    """Check if user can approve Level 1 (PD)"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.can_approve_level_1


class CanApproveLevel2(permissions.BasePermission):
    """Check if user can approve Level 2 (Admin)"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.can_approve_level_2


class IsSBC(permissions.BasePermission):
    """Check if user is SBC"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'SBC'