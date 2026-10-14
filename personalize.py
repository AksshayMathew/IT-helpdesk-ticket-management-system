import hashlib
import random


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


if __name__ == "__main__":
    employee_id = input("Employee ID: ").strip()
    parameters = get_my_parameters(employee_id)
    print(f"Parameters for employee {employee_id}:")
    print(f"  Categories    : {', '.join(parameters['categories'])}")
    print(f"  SLA hours     : {parameters['sla_hours']}")
    print(f"  Ticket prefix : {parameters['ticket_prefix']}")
