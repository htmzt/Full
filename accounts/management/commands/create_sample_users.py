"""
Management command to create sample users for testing
"""
from django.core.management.base import BaseCommand
from accounts.models import User, UserRole


class Command(BaseCommand):
    help = 'Create sample users for each role for testing'

    def handle(self, *args, **options):
        """Create sample users"""
        
        users_data = [
            {
                'email': 'admin@example.com',
                'password': 'admin123',
                'full_name': 'System Administrator',
                'role': UserRole.ADMIN,
                'phone': '+1-555-0001'
            },
            {
                'email': 'pd@example.com',
                'password': 'pd123456',
                'full_name': 'Procurement Director',
                'role': UserRole.PD,
                'phone': '+1-555-0002'
            },
            {
                'email': 'pm@example.com',
                'password': 'pm123456',
                'full_name': 'Project Manager',
                'role': UserRole.PM,
                'phone': '+1-555-0003'
            },
            {
                'email': 'coordinator@example.com',
                'password': 'coord123',
                'full_name': 'System Coordinator',
                'role': UserRole.COORDINATOR,
                'phone': '+1-555-0004'
            },
            {
                'email': 'pfm@example.com',
                'password': 'pfm123456',
                'full_name': 'Finance Manager',
                'role': UserRole.PFM,
                'phone': '+1-555-0005'
            },
            {
                'email': 'sbc1@example.com',
                'password': 'sbc123456',
                'full_name': 'ABC Construction',
                'role': UserRole.SBC,
                'phone': '+1-555-0006',
                'sbc_company_name': 'ABC Construction Ltd'
            },
            {
                'email': 'sbc2@example.com',
                'password': 'sbc123456',
                'full_name': 'XYZ Builders',
                'role': UserRole.SBC,
                'phone': '+1-555-0007',
                'sbc_company_name': 'XYZ Builders Inc'
            },
            {
                'email': 'it@example.com',
                'password': 'it123456',
                'full_name': 'IT Support',
                'role': UserRole.IT,
                'phone': '+1-555-0008'
            }
        ]
        
        created_count = 0
        skipped_count = 0
        
        for user_data in users_data:
            email = user_data['email']
            
            # Check if user already exists
            if User.objects.filter(email=email).exists():
                self.stdout.write(
                    self.style.WARNING(f'User {email} already exists - skipping')
                )
                skipped_count += 1
                continue
            
            # Create user
            try:
                user = User.objects.create_user(**user_data)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created {user.get_role_display()}: {email} (password: {user_data["password"]})'
                    )
                )
                created_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to create {email}: {str(e)}')
                )
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(
            self.style.SUCCESS(f'\nSummary: Created {created_count} users, Skipped {skipped_count} users')
        )
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.WARNING('\nIMPORTANT: Change these passwords in production!'))