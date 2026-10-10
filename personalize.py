import hashlib
import random

EMPLOYEE_ID = "56040183"


def get_my_parameters(employee_id: str) -> dict:
    """Deterministic, unique parameters derived from the employee ID.
    Every joiner gets a different set of ticket categories, SLA
    thresholds, and a ticket-ID prefix -- so no two submissions can
    look the same."""
    seed = int(hashlib.sha256(employee_id.encode()).hexdigest(), 16) % (2**31)
    rng = random.Random(seed)
    all_categories = ['Hardware', 'Software', 'Network', 'Access Request',
                      'Email', 'Printer', 'VPN', 'Application Bug',
                      'Account Lockout', 'Data Backup']
    return {
        'categories': rng.sample(all_categories, 5),
        'sla_hours': {
            'Critical': rng.randint(2, 4),
            'High': rng.randint(6, 12),
            'Medium': rng.randint(24, 48),
            'Low': rng.randint(72, 120),
        },
        'ticket_prefix': rng.choice(['TCK', 'INC', 'REQ', 'SR']),
    }


PARAMETERS = get_my_parameters(EMPLOYEE_ID)
CATEGORIES = PARAMETERS['categories']
SLA_HOURS = PARAMETERS['sla_hours']
TICKET_PREFIX = PARAMETERS['ticket_prefix']


if __name__ == "__main__":
    print(f"Parameters for employee {EMPLOYEE_ID}:")
    print(f"  Categories    : {', '.join(CATEGORIES)}")
    print(f"  SLA hours     : {SLA_HOURS}")
    print(f"  Ticket prefix : {TICKET_PREFIX}")
