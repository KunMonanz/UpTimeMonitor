from app.models.url_monitor import URLMonitor
from app.config.database_config import SessionLocal


class URLMonitorRepository:
    """Repository for URLMonitor model."""

    def __init__(self):
        self.db = SessionLocal()

    def add_url(self, url: str):
        """Add a new URLMonitor entry to the database."""
        url_monitor = URLMonitor(url=url)
        self.db.add(url_monitor)
        self.db.commit()
        self.db.refresh(url_monitor)
        return url_monitor

    def get_all_urls(self):
        """Retrieve all URLMonitor entries from the database."""
        return self.db.query(URLMonitor).all()

    def get_url_by_id(self, url_id):
        """Retrieve a specific URLMonitor entry by its ID."""
        return self.db.query(URLMonitor).filter(URLMonitor.id == url_id).first()

    def update_url_status(self, url_id, status):
        """Update the status of a specific URLMonitor entry."""
        url_monitor = self.get_url_by_id(url_id)
        if url_monitor:
            url_monitor.status = status
            self.db.commit()
            self.db.refresh(url_monitor)
            return url_monitor
        return None

    def delete_url(self, url_id):
        """Delete a specific URLMonitor entry by its ID."""
        url_monitor = self.get_url_by_id(url_id)
        if url_monitor:
            self.db.delete(url_monitor)
            self.db.commit()
            return True
        return False