import os
from dotenv import load_dotenv
from email_utils import send_alert_email

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
loaded = load_dotenv(dotenv_path)
print(f"Loaded .env: {loaded}")
print(f"ALERT_EMAIL: {os.getenv('ALERT_EMAIL')}")
print(f"ALERT_EMAIL_APP_PASSWORD length: {len(os.getenv('ALERT_EMAIL_APP_PASSWORD')) if os.getenv('ALERT_EMAIL_APP_PASSWORD') else 0}")

# Test sending email
print("Attempting to send alert email...")
send_alert_email("Test: Mercedes-Benz EQG Electrifies Mumbai Corridor")
print("Done.")
