from typing import Dict
import africastalking
from core.config import settings

class SmsService:
    def __init__(self):
        """Initialize Africa's Talking client"""

        self.api_key = settings.AFRICASTALKING_API_KEY
        self.username = settings.AFRICASTALKING_USERNAME or "sandbox"

        if not self.api_key or not self.username:
            raise RuntimeError("Africa's Talking credentials missing in settings")

        africastalking.initialize(self.username, self.api_key)
        self.sms = africastalking.SMS   # ✅ directly from SDK
    
    def send_sms(self, phone: str, message: str, session_id: str = None) -> Dict:
        try:
            response = self.sms.send(message, [phone])
            if response["SMSMessageData"]["Recipients"]:
                recipient = response["SMSMessageData"]["Recipients"][0]
                return {
                    "sms_id": recipient.get("messageId"),
                    "phone": phone,
                    "status": recipient.get("status"),
                    "cost": recipient.get("cost"),
                    "message": message,
                    "session_id": session_id
                }
            else:
                raise Exception("SMS send failed")
        except Exception as e:
            raise Exception(f"SMS send error: {str(e)}")
