"""
Management command to create sample users with proper roles and permissions
"""
from django.core.management.base import BaseCommand
from accounts.models import User, UserRole


class Command(BaseCommand):
    help = 'Create sample users for each role with proper permissions'

    def handle(self, *args, **options):
        """Create sample users with roles and permissions"""
        
        self.stdout.write(self.style.SUCCESS('Creating sample users...'))
        
        users_data = [
            {
                'email': 'admin@example.com',
                'password': 'admin123',
                'full_name': 'System Administrator',
                'role': UserRole.ADMIN,
                'phone': '+1-555-0001',
                'is_active': True,
                'is_staff': True
            },
            {
                'email': 'pd@example.com',
                'password': 'pd123456',
                'full_name': 'Procurement Director',
                'role': UserRole.PD,
                'phone': '+1-555-0002',
                'is_active': True
            },
            {
                'email': 'pm@example.com',
                'password': 'pm123456',
                'full_name': 'Project Manager',
                'role': UserRole.PM,
                'phone': '+1-555-0003',
                'is_active': True
            },
            {
                'email': 'coordinator@example.com',
                'password': 'coord123',
                'full_name': 'System Coordinator',
                'role': UserRole.COORDINATOR,
                'phone': '+1-555-0004',
                'is_active': True
            },
            {
                'email': 'pfm@example.com',
                'password': 'pfm123456',
                'full_name': 'Finance Manager',
                'role': UserRole.PFM,
                'phone': '+1-555-0005',
                'is_active': True
            },
            {
                'email': 'sbc1@example.com',
                'password': 'sbc123456',
                'full_name': 'ABC Construction',
                'role': UserRole.SBC,
                'phone': '+1-555-0006',
                'sbc_company_name': 'ABC Construction Ltd',
                'is_active': True
            },
            {
                'email': 'sbc2@example.com',
                'password': 'sbc123456',
                'full_name': 'XYZ Builders',
                'role': UserRole.SBC,
                'phone': '+1-555-0007',
                'sbc_company_name': 'XYZ Builders Inc',
                'is_active': True
            },
            {
                'email': 'it@example.com',
                'password': 'it123456',
                'full_name': 'IT Support',
                'role': UserRole.IT,
                'phone': '+1-555-0008',
                'is_active': True
            }
        ]
        
        created_count = 0
        skipped_count = 0
        updated_count = 0
        
        for user_data in users_data:
            email = user_data['email']
            
            # Check if user already exists
            existing_user = User.objects.filter(email=email).first()
            
            if existing_user:
                self.stdout.write(self.style.WARNING(f'User {email} already exists. Updating permissions...'))
                
                # Update role and trigger permission update
                existing_user.role = user_data['role']
                existing_user.full_name = user_data['full_name']
                existing_user.phone = user_data.get('phone')
                existing_user.is_active = user_data.get('is_active', True)
                
                if user_data.get('sbc_company_name'):
                    existing_user.sbc_company_name = user_data['sbc_company_name']
                
                # Manually set permissions based on role
                existing_user.set_permissions_by_role()
                
                # Save
                existing_user.save()
                
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Updated: {existing_user.full_name} ({existing_user.get_role_display()})'))
                self.stdout.write(f'    Permissions: Upload={existing_user.can_upload_files}, '
                                f'Merge={existing_user.can_trigger_merge}, '
                                f'Assign={existing_user.can_assign_pos}')
                
            else:
                try:
                    # Create new user
                    user = User.objects.create_user(
                        email=email,
                        password=user_data['password'],
                        full_name=user_data['full_name'],
                        role=user_data['role'],
                        phone=user_data.get('phone'),
                        is_active=user_data.get('is_active', True),
                        is_staff=user_data.get('is_staff', False)
                    )
                    
                    # Set SBC company name if provided
                    if user_data.get('sbc_company_name'):
                        user.sbc_company_name = user_data['sbc_company_name']
                        user.save()
                    
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {user.full_name} ({user.get_role_display()})'))
                    self.stdout.write(f'    Email: {user.email}')
                    self.stdout.write(f'    Password: {user_data["password"]}')
                    self.stdout.write(f'    Permissions: Upload={user.can_upload_files}, '
                                    f'Merge={user.can_trigger_merge}, '
                                    f'Assign={user.can_assign_pos}')
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Failed to create {email}: {str(e)}'))
                    skipped_count += 1
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('USER CREATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'Created: {created_count}')
        self.stdout.write(f'Updated: {updated_count}')
        self.stdout.write(f'Skipped: {skipped_count}')
        self.stdout.write('')
        
        # List all users with their permissions
        self.stdout.write(self.style.SUCCESS('All Users:'))
        self.stdout.write(self.style.SUCCESS('-' * 60))
        
        all_users = User.objects.all().order_by('role', 'email')
        for user in all_users:
            self.stdout.write(f'{user.email:30} | {user.get_role_display():20} | Active: {user.is_active}')
            self.stdout.write(f'  Permissions:')
            self.stdout.write(f'    - Upload Files: {user.can_upload_files}')
            self.stdout.write(f'    - Trigger Merge: {user.can_trigger_merge}')
            self.stdout.write(f'    - Assign POs: {user.can_assign_pos}')
            self.stdout.write(f'    - View All POs: {user.can_view_all_pos}')
            self.stdout.write(f'    - Create External PO (Any): {user.can_create_external_po_any}')
            self.stdout.write(f'    - Create External PO (Assigned): {user.can_create_external_po_assigned}')
            self.stdout.write(f'    - Approve Level 1 (PD): {user.can_approve_level_1}')
            self.stdout.write(f'    - Approve Level 2 (Admin): {user.can_approve_level_2}')
            self.stdout.write(f'    - Manage Users: {user.can_manage_users}')
            self.stdout.write('')