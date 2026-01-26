import smtplib
from email.mime.text import MIMEText
import os
from datetime import datetime

def send_email(to_email, subject, body):
    """
    Send email via Google Workspace (brand email)
    """
    
    from_email = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    
    if not from_email or not password:
        # Development mode: log to file instead
        return log_email_to_file(to_email, subject, body)
    
    # Production mode: send via Gmail SMTP (Google Workspace)
    return send_via_gmail(to_email, subject, body, from_email, password)


def log_email_to_file(to_email, subject, body):
    """
    Log email to file (development mode)
    """
    log_file = "emails.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(log_file, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"[{timestamp}] EMAIL LOG\n")
            f.write(f"{'='*60}\n")
            f.write(f"To: {to_email}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"Body:\n{body}\n")
        
        print(f"✅ Email logged to {log_file}")
        print(f"   To: {to_email}")
        print(f"   Subject: {subject}")
        return True
    except Exception as e:
        print(f"❌ Failed to log email: {e}")
        return False


def send_via_gmail(to_email, subject, body, from_email, password):
    """
    Send email via Gmail SMTP (Google Workspace - your brand email)
    """
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    try:
        print(f"🔗 Connecting to Gmail SMTP...")
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            print("🔒 Starting TLS...")
            server.starttls()
            print(f"🔑 Logging in as {from_email}...")
            server.login(from_email, password)
            print(f"📤 Sending email to {to_email}...")
            server.sendmail(from_email, to_email, msg.as_string())
        print(f"✅ Email sent successfully from {from_email} to {to_email}!")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed! Check your app password: {e}")
        return False
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False