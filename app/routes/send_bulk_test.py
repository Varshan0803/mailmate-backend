from fastapi import APIRouter
from app.services.sendgrid_client import SendGridClient
from app.config import settings

router = APIRouter(prefix="/dev", tags=["Dev Email Testing"])

@router.post("/test-email")
async def test_email():
    sg = SendGridClient(api_key=settings.SENDGRID_API_KEY)

    payload = {
        "personalizations": [{
            "to": [{"email": "nithishkumar0303@gmail.com"}],
            "subject": "Test Email From SendGrid"
        }],
        "from": {"email": settings.SENDER_EMAIL},
        "content": [{
            "type": "text/html",
            "value": "<h1>Hello from MailMate!</h1><p>This is a test email.</p>"
        }],
        "categories": ["test-campaign-id"],
        "custom_args": {"campaign_id": "test-campaign-id"}
    }

    result = await sg.send(payload)

    return {
        "message": "Email attempted",
        "result": result
    }
