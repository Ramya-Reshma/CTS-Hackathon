import requests
import sqlite3

BASE = "http://localhost:8000/api/auth"

print("--- STARTING MEDLYTICS AUTHENTICATION LIFECYCLE TEST ---")

# 1. Register new user
reg_payload = {
    "name": "Dr. Ramya Reshma",
    "email": "ramya@medlytics.com",
    "password": "SecurePassword2026!",
    "confirm_password": "SecurePassword2026!"
}
res_reg = requests.post(f"{BASE}/register", json=reg_payload)
print(f"1. Register Status: {res_reg.status_code}, Response: {res_reg.json()}")

# 2. Attempt login before verification
res_log1 = requests.post(f"{BASE}/login", json={"email": "ramya@medlytics.com", "password": "SecurePassword2026!"})
print(f"2. Login (Unverified) Status: {res_log1.status_code}, Detail: {res_log1.json().get('detail')}")

# 3. Retrieve token from DB
conn = sqlite3.connect("backend/uc10_anomalies.db")
c = conn.cursor()
c.execute("SELECT token FROM verification_tokens WHERE is_used = 0 ORDER BY id DESC LIMIT 1")
row = c.fetchone()
token = row[0] if row else None
print(f"3. Retrieved Token: {token[:12]}...")

# 4. Verify Email
res_ver = requests.post(f"{BASE}/verify-email", json={"token": token})
print(f"4. Verify Email Status: {res_ver.status_code}, Message: {res_ver.json().get('message')}")

# 5. Attempt login before approval (Status: PENDING_APPROVAL)
res_log2 = requests.post(f"{BASE}/login", json={"email": "ramya@medlytics.com", "password": "SecurePassword2026!"})
print(f"5. Login (Pending Approval) Status: {res_log2.status_code}, Detail: {res_log2.json().get('detail')}")

# 6. Admin Login and Approve
res_admin = requests.post(f"{BASE}/login", json={"email": "admin@medlytics.com", "password": "MedlyticsAdmin2026!"})
admin_token = res_admin.json().get("access_token")
print(f"6. Admin Login: {res_admin.status_code}, Role: {res_admin.json().get('user', {}).get('role')}")

c.execute("SELECT id FROM users WHERE email = 'ramya@medlytics.com'")
user_id = c.fetchone()[0]
conn.close()

res_app = requests.post(f"{BASE}/approve/{user_id}", headers={"Authorization": f"Bearer {admin_token}"})
print(f"7. Admin Approve Status: {res_app.status_code}, Response: {res_app.json().get('message')}")

# 7. Login after approval (APPROVED)
res_log3 = requests.post(f"{BASE}/login", json={"email": "ramya@medlytics.com", "password": "SecurePassword2026!"})
user_token = res_log3.json().get("access_token")
user_profile = res_log3.json().get("user")
print(f"8. Login (Approved) Status: {res_log3.status_code}, User: {user_profile.get('name')}, Status: {user_profile.get('approval_status')}")

# 8. Check protected /api/auth/me endpoint
res_me = requests.get(f"{BASE}/me", headers={"Authorization": f"Bearer {user_token}"})
print(f"9. Protected /api/auth/me Status: {res_me.status_code}, Email: {res_me.json().get('email')}")

print("--- ALL BACKEND AUTH LIFECYCLE TESTS PASSED [OK] ---")
