import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

def send_alert_email(new_article_title):
    sender_email = os.getenv("ALERT_EMAIL") 
    sender_password = os.getenv("ALERT_EMAIL_APP_PASSWORD") 
    
    # We send to all requested variants to ensure delivery and match requirements
    receiver_emails = [
        "prerak@cloudwebsoln.com",
        "prerak.sg@gmail.com",
        "prerak.sg@gamil.com"
    ]

    if not sender_email or not sender_password:
        print("Email alerts not configured in .env. Skipping email.")
        return

    subject = f"Zapway Editorial Notification: {new_article_title}"
    body = (
        f"Zapway Newsroom Update\n"
        f"---------------------\n\n"
        f"A new industry article has been drafted: '{new_article_title}'\n\n"
        f"This draft is pending review in your editorial queue.\n"
        f"Please log in to the Zapway Newsroom to approve or edit the article:\n"
        f"http://localhost:8000\n\n"
        f"Regards,\n"
        f"Zapway Editorial Agent"
    )

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
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
            except Exception as item_err:
                print(f"Failed to send to {receiver}: {item_err}")
                
        server.quit()
    except Exception as e:
        print(f"Failed to initialize SMTP server or login: {e}")

