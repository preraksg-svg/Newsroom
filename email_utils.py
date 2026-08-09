import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()


def _send_via_resend(subject, body, recipients):
    """Send email over HTTPS via the Resend API. Returns a result dict, or None
    if Resend is not configured. Use this on hosts that block outbound SMTP
    (e.g. Render's free tier), since it goes over port 443, not 587.
    Setup: sign up at https://resend.com, create an API key, set RESEND_API_KEY.
    Set RESEND_FROM to a verified sender (defaults to onboarding@resend.dev,
    which can only deliver to your own Resend-account email).
    """
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        return None
    sender = os.getenv("RESEND_FROM", "Zapway Newsroom <onboarding@resend.dev>")
    try:
        import requests
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"from": sender, "to": recipients, "subject": subject, "text": body},
            timeout=20,
        )
        if resp.status_code in (200, 201):
            print(f"Email sent via Resend to {recipients}")
            return {"success": True, "sent_to": recipients, "via": "resend"}
        return {"success": False, "error": f"Resend API {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": f"Resend error: {e}"}

def send_alert_email(subject_or_title, body_or_id=None):
    sender_email = os.getenv("ALERT_EMAIL")
    sender_password = os.getenv("ALERT_EMAIL_APP_PASSWORD")

    # Recipients are configurable via ALERT_RECIPIENT (comma-separated). If unset,
    # the alert is sent to the sender address itself (email yourself).
    recipients_raw = os.getenv("ALERT_RECIPIENT", "") or sender_email or ""
    receiver_emails = [e.strip() for e in recipients_raw.split(",") if e.strip()]

    if not sender_email or not sender_password:
        print("Email alerts not configured. Set ALERT_EMAIL and ALERT_EMAIL_APP_PASSWORD. Skipping email.")
        return {"success": False, "error": "ALERT_EMAIL / ALERT_EMAIL_APP_PASSWORD not set on the server."}
    if not receiver_emails:
        print("No ALERT_RECIPIENT configured. Skipping email.")
        return {"success": False, "error": "No ALERT_RECIPIENT (or ALERT_EMAIL) configured."}

    # Check if this is a system alert or a new article notification
    if body_or_id and len(body_or_id) > 50:  # It's a text body (e.g. system alert)
        subject = subject_or_title
        body = body_or_id
    else:  # It's an article title & optional article_id
        article_id = body_or_id
        newsroom_url = os.getenv("NEWSROOM_URL", "").rstrip("/") or "https://your-service.onrender.com"
        if article_id:
            link_url = f"{newsroom_url}/article/{article_id}"
        else:
            link_url = f"{newsroom_url}/news"
            
        subject = f"Zapway Editorial Notification: {subject_or_title}"
        body = (
            f"Zapway Newsroom Update\n"
            f"---------------------\n\n"
            f"A new industry article has been drafted: '{subject_or_title}'\n\n"
            f"This draft is pending review in your editorial queue.\n"
            f"Please click the link below to inspect, edit, or publish it from your phone or laptop:\n"
            f"{link_url}\n\n"
            f"Regards,\n"
            f"Zapway Editorial Agent"
        )

    # Prefer the HTTP email API when configured — it works on hosts that block
    # outbound SMTP (Render free tier). Falls through to SMTP for local dev.
    resend_result = _send_via_resend(subject, body, receiver_emails)
    if resend_result is not None:
        return resend_result

    sent_to = []
    try:
        # Timeout so a blocked SMTP port (common on cloud hosts like Render free)
        # fails fast instead of hanging the request/worker.
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=20)
        server.starttls()
        server.login(sender_email, sender_password)

        for receiver in receiver_emails:
            try:
                msg = MIMEMultipart()
                msg['From'] = f"Zapway Newsroom <{sender_email}>"
                msg['To'] = receiver
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))

                # Add headers to decrease spam score
                msg['X-Priority'] = '3'
                msg['X-MSMail-Priority'] = 'Normal'

                server.send_message(msg)
                print(f"Alert email sent successfully to {receiver}!")
                sent_to.append(receiver)
            except Exception as item_err:
                print(f"Failed to send to {receiver}: {item_err}")

        server.quit()
        return {"success": len(sent_to) > 0, "sent_to": sent_to}
    except Exception as e:
        print(f"Failed to initialize SMTP server or login: {e}")
        return {"success": False, "error": f"SMTP error: {e}"}

