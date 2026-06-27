def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to +254XXXXXXXXX format
    
    Handles:
    - 0712345678 → +254712345678
    - +254712345678 → +254712345678
    - 254712345678 → +254712345678
    """
    
    if not phone:
        return ""
    
    # Remove all non-digits except +
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
    
    # Remove leading +
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    
    # Remove leading 0
    if cleaned.startswith("0"):
        cleaned = cleaned[1:]
    
    # If doesn't start with 254, assume Kenya
    if not cleaned.startswith("254"):
        cleaned = "254" + cleaned
    
    return "+" + cleaned