from enum import Enum

class USER_ROLE(str, Enum):
    FA = "Facility_Admin"
    ENG = "Engineer"
    EMP = "Employee"

class ENGINEER_STATUS(str, Enum):
    AVAILABLE = "Available"
    UNAVAILABLE = "Unavailable"

# Added because making it freeform could lead to search inconsistency.
# Can always add more later.
class ENGINEER_FIELD(str, Enum):
    BUILDING = "Building"
    HARDWARE = "Hardware"
    SOFTWARE = "Software"
    ELECTRICAL = "Electrical"

class INCIDENT_TICKET_STATUS(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In-Progress"
    BLOCKED = "Blocked"
    RESOLVED = "Resolved"
    CLOSED = "Closed"

class INCIDENT_TICKET_PRIORITY(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    CRITICAL = "Critical"