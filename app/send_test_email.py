import os
import sendgrid
from sendgrid.helpers.mail import Mail

# 🔹 Fill these with your real values
SG_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = "ganesanbanu1978@gmail.com"      # Must be verified in SendGrid
TO_EMAIL = "nithishkumar0303@gmail.com"              # Any email you want to receive test

def send_test_email():
    sg = sendgrid.SendGridAPIClient(api_key=SG_API_KEY)

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAIL,
        subject="SendGrid Test Email — Working!",
        html_content="""
            <h2 style='color: green;'>This is a test email from SendGrid!</h2>
            <p>If you received this, your SendGrid setup works perfectly.</p>
        """
    )

    try:
        response = sg.send(message)
        print("Status Code:", response.status_code)
        print("Body:", response.body)
        print("Headers:", response.headers)
    except Exception as e:
        print("Error:", e)

send_test_email()
