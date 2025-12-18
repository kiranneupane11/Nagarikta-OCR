# llm_service/schema.py
from pydantic import BaseModel, Field
from typing import Optional, Literal

# Front Side Schema
class FrontSideCard(BaseModel):
    Name: Optional[str] = Field(None, description="Full name exactly in Devanagari from OCR (do not transliterate)")
    Citizenship_Number: Optional[str] = Field(None, description="Citizenship number under the label 'ना.प्र.न.' (mixed Devanagari digits with dashes)")
    Date_of_Birth_DOB: Optional[str] = Field(None, description="DOB exactly in Nepali BS format from OCR (e.g., '२०४५ महिना: ०२ गते २८'). Do not convert.")
    Fathers_Name: Optional[str] = Field(None, description="Father's name under the label 'बाबुको नाम थर' exactly in Devanagari from OCR (do not transliterate)")
    Mothers_Name: Optional[str] = Field(None, description="Mother's name exactly under the label 'आमाको नाम थर' in Devanagari from OCR (do not transliterate)")
    Gender: Optional[Literal["Male", "Female", "Other"]] = Field(None, description="Gender: Map 'पुरुष' to 'Male', 'महिला' to 'Female', 'अन्य' to 'Other'. Use null if unclear.")
    Spouse_Name: Optional[str] = Field(None, description="Spouse's name exactly in Devanagari from OCR (do not transliterate; null if not present)")
    Birth_Place_District: Optional[str] = Field(None, description="Birth district exactly in Devanagari from OCR (do not transliterate)")
    Birth_Place_MetroPolitan_Sub_MetroPolitan_Municipality_VDC: Optional[str] = Field(None, description="Birth Municipality/VDC exactly in Devanagari from OCR (do not transliterate)")
    Birth_Place_Ward: Optional[str] = Field(None, description="Birth ward number exactly as in OCR (mixed Devanagari/Latin digits)")
    Permanent_District: Optional[str] = Field(None, description="Permanent district exactly in Devanagari from OCR (do not transliterate)")
    Permanent_MetroPolitan_Sub_MetroPolitan_Municipality_VDC: Optional[str] = Field(None, description="Permanent Municipality/VDC exactly in Devanagari from OCR (do not transliterate)")
    Permanent_Ward: Optional[str] = Field(None, description="Permanent ward number exactly as in OCR (mixed Devanagari/Latin digits)")

# Back Side schema
class BackSideCard(BaseModel):
    Name: Optional[str] = Field(None, description="Full name exactly in English/Latin from OCR (do not use Devanagari)")
    Citizenship_Number: Optional[str] = Field(None, description="Citizenship number exactly as in OCR (Latin digits with dashes)")
    Date_of_Birth_DOB: Optional[str] = Field(None, description="DOB exactly in English AD format from OCR (e.g., 'YYYY/MM/DD'). Do not convert.")
    Gender: Optional[Literal["पुरुष", "महिला", "अन्य"]] = Field(None, description="Gender exactly as in OCR text")
    Birth_Place_District: Optional[str] = Field(None, description="Birth district exactly in English/Latin from OCR (do not use Devanagari)")
    Birth_Place_MetroPolitan_Sub_MetroPolitan_Municipality_VDC: Optional[str] = Field(None, description="Birth Municipality/VDC exactly in English/Latin from OCR (do not use Devanagari)")
    Birth_Place_Ward: Optional[str] = Field(None, description="Birth ward number exactly as in OCR (Latin digits)")
    Permanent_District: Optional[str] = Field(None, description="Permanent district exactly in English/Latin from OCR (do not use Devanagari)")
    Permanent_MetroPolitan_Sub_MetroPolitan_Municipality_VDC: Optional[str] = Field(None, description="Permanent Municipality/VDC exactly in English/Latin from OCR (do not use Devanagari)")
    Permanent_Ward: Optional[str] = Field(None, description="Permanent ward number exactly as in OCR (Latin digits)")
    Issued_Date: Optional[str] = Field(None, description="Issued date exactly as in OCR (e.g.,जारी मिति: (e.g., 'YYYY/MM/DD'); Do not convert)")
