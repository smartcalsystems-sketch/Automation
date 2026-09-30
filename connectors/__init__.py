from .base_connector import BaseEcosystemConnector, EmailMessage, CalendarEvent
from .google_connector import GoogleWorkspaceConnector
from .m365_connector import Microsoft365Connector
from .mock_connector import MockEcosystemConnector

__all__ = [
    "BaseEcosystemConnector",
    "EmailMessage",
    "CalendarEvent",
    "GoogleWorkspaceConnector",
    "Microsoft365Connector",
    "MockEcosystemConnector"
]
