from pydantic import BaseModel
from datetime import datetime 
class NotificationCreate(BaseModel):
    type: str

    channel: str

    recipient: str

    message: str

    delivery_status: str

    sent_at: datetime