"""Shared synthetic CSV fixtures for e2e tests."""

CUSTOMERS_CSV = b"""\
customer_id,name,date_of_birth,phone,email,address,identity_number,onboarded_at,source_system,account_id,product,opened_at,status
C001,Alice Kumar,1985-03-15,9876543210,alice@test.com,12 Main St Chennai TN,IDTST001,2023-01-01T00:00:00+05:30,CORE,ACC001,savings,2023-01-01T00:00:00+05:30,active
C002,Bob Singh,1990-07-22,9876543211,bob@test.com,45 Park Ave Mumbai MH,IDTST002,2023-02-01T00:00:00+05:30,CORE,ACC002,current,2023-02-01T00:00:00+05:30,active
"""

# T004 is 80x the avg of T001-T003 (1000 each) → R1-SUSPICIOUS-TRANSFER (High)
TRANSACTIONS_CSV = b"""\
transaction_id,timestamp,sender_account_id,beneficiary_account_id,beneficiary_name,amount_inr,channel,status,device_id,note
T001,2024-01-01T10:00:00+05:30,ACC001,ACC002,Bob Singh,1000.00,online,success,DEV001,
T002,2024-01-02T10:00:00+05:30,ACC001,ACC002,Bob Singh,1000.00,online,success,DEV001,
T003,2024-01-03T10:00:00+05:30,ACC001,ACC002,Bob Singh,1000.00,online,success,DEV001,
T004,2024-01-10T10:00:00+05:30,ACC001,ACC099,Unknown Payee,80000.00,online,success,DEV001,suspicious large
"""

# EV001-EV003: 3 failures for C001 in <30 min
# EV004:       success from DEV002 (NEW device) within 30 min of EV003 → R3-ATO
# EV005:       C002 uses DEV001 → shared with C001 → R2-SHARED-DEVICE
LOGINS_CSV = b"""\
event_id,customer_id,timestamp,device_id,ip_address,location,outcome,event_type
EV001,C001,2024-01-05T09:00:00+05:30,DEV001,1.2.3.4,Chennai,failure,login
EV002,C001,2024-01-05T09:05:00+05:30,DEV001,1.2.3.4,Chennai,failure,login
EV003,C001,2024-01-05T09:10:00+05:30,DEV001,1.2.3.4,Chennai,failure,login
EV004,C001,2024-01-05T09:20:00+05:30,DEV002,5.6.7.8,Mumbai,success,login
EV005,C002,2024-01-06T10:00:00+05:30,DEV001,1.2.3.4,Chennai,success,login
"""

# L001 + L002 both use DEV003 → R4-LOAN-RING
LOANS_CSV = b"""\
application_id,customer_id,applied_at,amount_inr,device_id,ip_address,phone,address,disbursement_account_id,status
L001,C001,2024-01-15T10:00:00+05:30,500000.00,DEV003,1.2.3.4,9876543210,12 Main St Chennai TN,ACC001,pending
L002,C002,2024-01-16T10:00:00+05:30,600000.00,DEV003,5.6.7.8,9876543211,45 Park Ave Mumbai MH,ACC002,pending
"""

# IC001 + IC002: same type + amount within 90 days → R5-DUP-CLAIM
CLAIMS_CSV = b"""\
claim_id,policy_id,customer_id,incident_date,claim_date,claim_type,amount_inr,description,payout_account_id
IC001,POL001,C001,2024-01-01,2024-01-10,medical,50000.00,Hospital visit,ACC001
IC002,POL001,C001,2024-01-20,2024-01-25,medical,50000.00,Repeat medical claim,ACC001
"""

# Bad CSV: missing mandatory field amount_inr
BAD_TRANSACTIONS_CSV = b"""\
transaction_id,timestamp,sender_account_id,channel,status
TBAD,2024-01-01T10:00:00+05:30,ACC001,online,completed
"""
