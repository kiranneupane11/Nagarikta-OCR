
from typing import Dict
import re

def regex_extract(text: str) -> Dict:
    """Fallback regex extraction"""
    ocr_lines = [line.strip() for line in text.split('\n') if line.strip()]
    structured_data = {
        "Name": None,
        "Citizenship Number": None,
        "Date of Birth (DOB)": None,
        "Father's Name": None,
        "Mother's Name": None,
        "Gender": None,
        "Spouse Name": None,
        "Birth Place District": None,
        "Birth Place Municipality": None,
        "Birth Place Ward": None,
        "Permanent District": None,
        "Permanent Municipality": None,
        "Permanent Ward": None
    }
    current_section = "General"
    
    def clean_extraction(text, label_pattern):
        text = re.sub(label_pattern, '', text).strip()
        text = re.sub(r'^[:\-\.=\s]+', '', text).strip()
        return text
    
    for i, line in enumerate(ocr_lines):
        line_clean = line.replace('o', '०').replace('O', '०')
        if re.search(r'जन्म\s*स्थान', line):
            current_section = "BirthPlace"
            continue
        if re.search(r'(स्थायी|बोसस्थान|बासस्थान)', line):
            current_section = "PermanentAddress"
            continue
        cit_match = re.search(r'[०-९0-9]+[\-\/][०-९0-9\-\/]+', line)
        if cit_match and not structured_data["Citizenship Number"]:
            structured_data["Citizenship Number"] = cit_match.group()
        if re.search(r'नाम\s*थर', line) and "बाबु" not in line and "आमा" not in line and "पति" not in line:
            val = clean_extraction(line, r'नाम\s*थर[:ः]?')
            if not val and i + 1 < len(ocr_lines):
                structured_data["Name"] = ocr_lines[i+1]
            elif val:
                structured_data["Name"] = val
        if re.search(r'(लिङ्ग|लिड़ग|लिंग)', line):
            if "पुरुष" in line: structured_data["Gender"] = "Male (पुरुष)"
            elif "महिला" in line: structured_data["Gender"] = "Female (महिला)"
            elif "अन्य" in line: structured_data["Gender"] = "Other (अन्य)"
        if re.search(r'(जन्म\s*मिति|जज्म|साल[:\s])', line):
            val = clean_extraction(line, r'(जन्म\s*मिति|जज्म|मिति)[:ः]?')
            if "साल" in val or re.search(r'[०-९0-9]', val):
                structured_data["Date of Birth (DOB)"] = val
            elif i + 1 < len(ocr_lines):
                structured_data["Date of Birth (DOB)"] = ocr_lines[i+1]
        if re.search(r'(बाबु|बाहु|पिता).*?(नाम|थर)', line):
            val = clean_extraction(line, r'(बाबु|बाहु|पिता).*?(नाम|थर)[:ः]?')
            if not val and i + 1 < len(ocr_lines):
                structured_data["Father's Name"] = ocr_lines[i+1]
        if re.search(r'(आमा).*?(नाम|थर)', line):
            val = clean_extraction(line, r'(आमा).*?(नाम|थर)[:ः]?')
            if not val and i + 1 < len(ocr_lines):
                structured_data["Mother's Name"] = ocr_lines[i+1]
        if re.search(r'(पति|पत्नी).*?(नाम|थर)', line):
            val = clean_extraction(line, r'(पति|पत्नी).*?(नाम|थर)[:ः]?')
            if not val and i + 1 < len(ocr_lines):
                structured_data["Spouse Name"] = ocr_lines[i+1]
        if "जिल्ला" in line:
            val = clean_extraction(line, r'जिल्ला[:ः]?')
            if current_section == "BirthPlace": structured_data["Birth Place District"] = val
            elif current_section == "PermanentAddress": structured_data["Permanent District"] = val
        if re.search(r'(न\.?पा|गा\.?पा|गा\.?वि|महानगर|उपमहानगर)', line):
            val = clean_extraction(line, r'(न\.?पा\.?|उ\.?म\.?न\.?पा\.?|गा\.?वि\.?\s*स\.?|गा\.?पा\.?)[:ः]?')
            if current_section == "BirthPlace": structured_data["Birth Place Municipality"] = val
            elif current_section == "PermanentAddress": structured_data["Permanent Municipality"] = val
        if re.search(r'([वब]डा|वार).*?(नं|न)', line) or re.search(r'([वब]डान)', line):
            ward_num = re.sub(r'[^\d०-९]', '', line)
            if current_section == "BirthPlace": structured_data["Birth Place Ward"] = ward_num
            elif current_section == "PermanentAddress": structured_data["Permanent Ward"] = ward_num
    
    return structured_data