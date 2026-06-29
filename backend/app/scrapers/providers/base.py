from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession


class BaseScraper(ABC):
    """Base class for all scrapers."""
    
    @abstractmethod
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute scraping based on config.
        
        Args:
            config: Provider-specific configuration
            project_id: ID of the project to save data to
            db: Database session
            job_id: Optional ID of the job (for tracking which job created the items)
            
        Returns:
            List of scraped items
        """
        pass
    
    @abstractmethod
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate the configuration."""
        pass

