"""
Account Service - Map projects to accounts
"""
from core.models import Account
import logging

logger = logging.getLogger(__name__)


class AccountService:
    """Service for managing account mappings"""
    
    @staticmethod
    def map_project_to_account_name(project_name: str) -> str:
        """
        Map project name to account name using business rules
        
        Args:
            project_name: Project name from PO
            
        Returns:
            Account name
        """
        if not project_name:
            return 'Other'
        
        project_name_lower = project_name.lower()
        
        # Business rules for account mapping
        if "iam" in project_name_lower:
            return "IAM Account"
        elif "orange" in project_name_lower:
            return "Orange Account"
        elif "inwi" in project_name_lower:
            return "INWI Account"
        else:
            return "Other"
    
    @staticmethod
    def get_or_create_account(project_name: str) -> Account:
        """
        Get existing account or create new one for project
        
        Args:
            project_name: Project name from PO
            
        Returns:
            Account object
        """
        clean_project_name = (project_name or "Unknown Project").strip()
        
        # Check if account already exists
        existing_account = Account.objects.filter(
            project_name=clean_project_name
        ).first()
        
        if existing_account:
            logger.debug(f"Found existing account for project '{clean_project_name}'")
            return existing_account
        
        # Create new account
        account_name = AccountService.map_project_to_account_name(clean_project_name)
        needs_review = (account_name == "Other")
        
        new_account = Account.objects.create(
            project_name=clean_project_name,
            account_name=account_name,
            needs_review=needs_review
        )
        
        logger.info(f"✨ Created new account '{account_name}' for project '{clean_project_name}'")
        
        return new_account
    
    @staticmethod
    def get_account_name_for_project(project_name: str) -> str:
        """
        Get account name for a project (from DB or map it)
        
        Args:
            project_name: Project name
            
        Returns:
            Account name
        """
        clean_project_name = (project_name or "Unknown Project").strip()
        
        # Try to get from database first
        account = Account.objects.filter(
            project_name=clean_project_name
        ).first()
        
        if account:
            return account.account_name
        
        # If not found, map it (but don't create)
        return AccountService.map_project_to_account_name(clean_project_name)
    
    @staticmethod
    def update_account_mapping(project_name: str, new_account_name: str, needs_review: bool = False):
        """
        Update account mapping for a project
        
        Args:
            project_name: Project name
            new_account_name: New account name
            needs_review: Whether this needs review
        """
        clean_project_name = (project_name or "Unknown Project").strip()
        
        account = Account.objects.filter(
            project_name=clean_project_name
        ).first()
        
        if account:
            account.account_name = new_account_name
            account.needs_review = needs_review
            account.save()
            logger.info(f"Updated account mapping for '{clean_project_name}' to '{new_account_name}'")
        else:
            Account.objects.create(
                project_name=clean_project_name,
                account_name=new_account_name,
                needs_review=needs_review
            )
            logger.info(f"Created new account mapping for '{clean_project_name}' to '{new_account_name}'")
    
    @staticmethod
    def get_accounts_needing_review():
        """Get all accounts that need review"""
        return Account.objects.filter(needs_review=True).order_by('created_at')
    
    @staticmethod
    def extract_accounts_from_pos():
        """
        Extract unique projects from PurchaseOrder and create Account entries
        
        Returns:
            dict with stats
        """
        from core.models import PurchaseOrder
        
        # Get all unique project names from POs
        project_names = PurchaseOrder.objects.exclude(
            project_name__isnull=True
        ).exclude(
            project_name=''
        ).values_list('project_name', flat=True).distinct()
        
        created_count = 0
        existing_count = 0
        
        for project_name in project_names:
            clean_name = project_name.strip()
            if not clean_name:
                continue
            
            # Check if exists
            if Account.objects.filter(project_name=clean_name).exists():
                existing_count += 1
            else:
                AccountService.get_or_create_account(clean_name)
                created_count += 1
        
        logger.info(f"Account extraction: {created_count} created, {existing_count} existing")
        
        return {
            'created': created_count,
            'existing': existing_count,
            'total': created_count + existing_count
        }