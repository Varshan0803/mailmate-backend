# app/contacts/utils.py
from typing import List, Dict
from app.contacts.schemas import ContactCreate
from pydantic import ValidationError

def normalize_email(email: str) -> str:
    if not email:
        return ""
    # remove invisible unicode characters:
    email = email.replace("\ufeff", "")       # BOM
    email = email.replace("\u200e", "")       # LTR mark
    email = email.replace("\u200f", "")       # RTL mark
    email = email.replace("\u202a", "")       # LRE
    email = email.replace("\u202b", "")       # RLE
    email = email.replace("\u202c", "")       # PDF

    # strip ALL whitespace (left, right, and inside)
    email = email.strip()
    email = "".join(email.split())  # remove weird spaces

    # lower-case
    return email.lower()


def validate_row(row: Dict) -> ContactCreate:
    # row: dict with 'name','email','segment' keys
    # will raise pydantic ValidationError if invalid
    data = {
        "name": row.get("name", "").strip(),
        "email": normalize_email(row.get("email", "")),
        "segment": row.get("segment", None)
    }
    return ContactCreate.model_validate(data)  # pydantic v2
