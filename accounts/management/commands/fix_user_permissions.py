"""
Management command to fix permissions for existing users
Run this to update permissions for users that were created without proper permissions
"""
from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Fix permissions for all existing users based on their roles'

    def handle(self, *args, **options):
        """Fix permissions for all users"""
        
        self.stdout.write(self.style.SUCCESS('Fixing user permissions...'))
        self.stdout.write('')
        
        users = User.objects.all()
        total = users.count()
        fixed = 0
        
        for user in users:
            self.stdout.write(f'Processing: {user.email} ({user.get_role_display()})')
            
            # Store old permissions
            old_perms = {
                'upload': user.can_upload_files,
                'merge': user.can_trigger_merge,
                'assign': user.can_assign_pos,
                'view_all': user.can_view_all_pos,
                'create_ext_any': user.can_create_external_po_any,
                'create_ext_assigned': user.can_create_external_po_assigned,
                'approve_l1': user.can_approve_level_1,
                'approve_l2': user.can_approve_level_2,
                'manage_users': user.can_manage_users
            }
            
            # Set permissions based on role
            user.set_permissions_by_role()
            user.save()
            
            # Store new permissions
            new_perms = {
                'upload': user.can_upload_files,
                'merge': user.can_trigger_merge,
                'assign': user.can_assign_pos,
                'view_all': user.can_view_all_pos,
                'create_ext_any': user.can_create_external_po_any,
                'create_ext_assigned': user.can_create_external_po_assigned,
                'approve_l1': user.can_approve_level_1,
                'approve_l2': user.can_approve_level_2,
                'manage_users': user.can_manage_users
            }
            
            # Check if anything changed
            if old_perms != new_perms:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Fixed permissions for {user.email}'))
                self.stdout.write('    Changes:')
                
                for perm_name, old_val in old_perms.items():
                    new_val = new_perms[perm_name]
                    if old_val != new_val:
                        status = '✓' if new_val else '✗'
                        self.stdout.write(f'      {perm_name}: {old_val} → {new_val} {status}')
                
                fixed += 1
            else:
                self.stdout.write(f'  - No changes needed for {user.email}')
            
            self.stdout.write('')
        
        # Summary
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('PERMISSION FIX SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'Total users: {total}')
        self.stdout.write(f'Fixed: {fixed}')
        self.stdout.write(f'No changes: {total - fixed}')
        self.stdout.write('')
        
        # Display all users with their current permissions
        self.stdout.write(self.style.SUCCESS('Current User Permissions:'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        for user in User.objects.all().order_by('role', 'email'):
            self.stdout.write(self.style.SUCCESS(f'\n{user.email} ({user.get_role_display()})'))
            self.stdout.write('-' * 60)
            
            perms = [
                ('Upload Files', user.can_upload_files),
                ('Trigger Merge', user.can_trigger_merge),
                ('Assign POs', user.can_assign_pos),
                ('View All POs', user.can_view_all_pos),
                ('Create External PO (Any)', user.can_create_external_po_any),
                ('Create External PO (Assigned)', user.can_create_external_po_assigned),
                ('Approve Level 1 (PD)', user.can_approve_level_1),
                ('Approve Level 2 (Admin)', user.can_approve_level_2),
                ('Manage Users', user.can_manage_users),
                ('View Dashboard', user.can_view_dashboard),
                ('Export Data', user.can_export_data),
                ('View SBC Work', user.can_view_sbc_work)
            ]
            
            for perm_name, perm_value in perms:
                icon = '✓' if perm_value else '✗'
                color = self.style.SUCCESS if perm_value else self.style.ERROR
                self.stdout.write(color(f'  {icon} {perm_name:30} : {perm_value}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Done! All user permissions have been fixed.'))