from enum import Enum

class USER_ROLE(str, Enum):
    FA = "Facility_Admin"
    ENG = "Engineer"
    EMP = "Employee"