"""
app/compliance/
───────────────
RBI (Reserve Bank of India) mandate compliance rules.
Business logic for validating retry attempts against regulatory constraints:
  - Max retry attempts per mandate type
  - Cooling-off periods between retries
  - Notification requirements (SMS/email before debit)
"""
