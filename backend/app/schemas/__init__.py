from .user import (
    User_Create,
    User_Read,
    User_Update,
    User_Permissions_Read,
    Role_Permissions_Read,
    Permission_Read,
    Token,
    Refresh_Token_Request,
)
from .building import Building_Create, Building_Read, Building_Update
from .engineer import Engineer_Create, Engineer_Read, Engineer_Update
from .floor import Floor_Create, Floor_Read, Floor_Update
from .incident_ticket import (
    Incident_Ticket_Create,
    Incident_Ticket_Read,
    Incident_Ticket_Update,
)
from .seat import Seat_Bulk_Create, Seat_Create, Seat_Read, Seat_Update
from .ticket_note import (
    Ticket_Note_Attachment_Create,
    Ticket_Note_Attachment_Read,
    Ticket_Note_Attachment_Update,
    Ticket_Note_Create,
    Ticket_Note_Read,
    Ticket_Note_Update,
)

# Attach all schemas here so they are easily callable.
__all__ = [
    "User_Create", "User_Read", "User_Update", "User_Permissions_Read", "Role_Permissions_Read", "Permission_Read",
    "Token", "Refresh_Token_Request",
    "Building_Create", "Building_Read", "Building_Update",
    "Engineer_Create", "Engineer_Read", "Engineer_Update",
    "Floor_Create", "Floor_Read", "Floor_Update",
    "Incident_Ticket_Create", "Incident_Ticket_Read", "Incident_Ticket_Update",
    "Seat_Bulk_Create", "Seat_Create", "Seat_Read", "Seat_Update",
    "Ticket_Note_Attachment_Create", "Ticket_Note_Attachment_Read",
    "Ticket_Note_Attachment_Update",
    "Ticket_Note_Create", "Ticket_Note_Read", "Ticket_Note_Update",
]