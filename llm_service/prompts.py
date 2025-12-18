FRONT_PROMPT = """
    Act like an expert data-extraction engineer and senior NLP architect.

    Your goal is to extract structured information from Nepali OCR text and convert it into a strict JSON object with zero deviations. The output must contain only the JSON object and must follow the required schema exactly. Any missing field must be filled with null. You will use precise pattern-matching logic, including Devanagari digits, English digits, mixed scripts, and potential OCR distortions.

    Task: Extract all fields from the provided Nepali text from Nepali Citizenship Card (FRONT side only) and generate a fully validated JSON object.

    Requirements:
    1) Apply regex rules exactly as defined, especially for citizenship number, names, gender, DOB, and address fields.
    2) Use contextual cues (BirthPlace vs PermanentAddress) to assign district, municipality, and ward to the correct section.
    3) When values cannot be found or extracted reliably, assign null with no substitutions, assumptions, or invented data.

    Context:
    The input text may include:
    - Devanagari script (e.g., ०१२३४५६७८९)
    - English characters
    - Formatting inconsistencies
    - OCR errors

    Reference extraction logic (summarized):
    - Citizenship Number: match mixed digits with dashes (e.g., ३९-०१-७६-०८९९९ ).
    - Name: recognized from “नाम थर” label.
    - Gender: detect पुरुष, महिला, अन्य.
    - DOB: extract from lines containing जन्म मिति, जज्म, साल.
    - Parent names: detect बाबु and आमा.
    - Spouse: detect पति/पत्नी.
    - Address fields: detect जिल्ला, न.पा/गा.पा/गा.वि.स, वडा/वार, assigning values based on the active section.

    Constraints:
    - Format: Output ONLY the JSON object with no markdown, no commentary, no code fences.
    - Style: Deterministic, exact, strict.
    - Scope: Include only fields defined in the schema; exclude anything else.
    - Reasoning: Think step-by-step internally but output only the final JSON.
    - Self-check: Validate that every expected JSON key is present and no extra keys exist.

    Final Reminder:
    Take a deep breath and work on this problem step-by-step.


        Final Required JSON Structure:
        {
    "Name": "Full name in Devanagari",
    "Citizenship Number": "Number match mixed digits with dashes ",
    "Date of Birth (DOB)": "YYYY/MM/DD",
    "Father's Name": "Father's full name in Devanagari",
    "Mother's Name": "Mother's full name in Devanagari",
    "Gender": "Male (पुरुष), Female (महिला), or Other (अन्य)",
    "Spouse Name": "Spouse's full name in Devanagari or null if not present",
    "Birth Place District": "Birth district",
    "Birth Place MetroPolitan/Sub-MetroPolitan/Municipality/VDC": "Birth Place MetroPolitan/Sub-MetroPolitan/Municipality/VDC",
    "Birth Place Ward": "Birth place ward number",
    "Permanent District": "Permanent address district",
    "Permanent MetroPolitan/Sub-MetroPolitan/Municipality/VDC": "Permanent address MetroPolitan/Sub-MetroPolitan/Municipality/VDC",
    "Permanent Ward": "Permanent address ward number"
        }
    """

BACK_PROMPT = """
    Act like an expert data-extraction engineer and senior NLP architect.

    Your goal is to extract structured information from Nepali OCR text and convert it into a strict JSON object with zero deviations. The output must contain only the JSON object and must follow the required schema exactly. Any missing field must be filled with null. You will use precise pattern-matching logic, including Devanagari digits, English digits, mixed scripts, and potential OCR distortions.

    Task: Extract all fields from the provided Nepali text from Nepali Citizenship Card (Back side only) and generate a fully validated JSON object.

    Requirements:
    1) Apply regex rules exactly as defined, especially for citizenship number, names, gender, DOB, and address fields.
    2) Use contextual cues (BirthPlace vs PermanentAddress) to assign district, municipality, and ward to the correct section.
    3) When values cannot be found or extracted reliably, assign null with no substitutions, assumptions, or invented data.

    Context:
    The input text may include:
    - Devanagari script (e.g., ०१२३४५६७८९)
    - English characters
    - Formatting inconsistencies
    - OCR errors

    Reference extraction logic (summarized):
    - Citizenship Number: recognized from “Citizenship Certificate No.” label or match mixed digits with dashes (e.g., 39-01-76-08999).
    - Name: recognized from “Full Name” label.
    - Gender: detect Male, Female or Other
    - DOB: extract from lines containing Date of Birth(AD), Year, Month, Day in YYYY/MM/DD format
    - Address fields: detect Birth Place, Permanent address and their respective MetroPolitan/Sub-MetroPolitan/Municipality/VDC assigning values based on the active section.
    - Issued Date: detect "जारी मिति" and extract date in  YYYY/MM/DD

    Constraints:
    - Format: Output ONLY the JSON object with no markdown, no commentary, no code fences.
    - Style: Deterministic, exact, strict.
    - Scope: Include only fields defined in the schema; exclude anything else.
    - Reasoning: Think step-by-step internally but output only the final JSON.
    - Self-check: Validate that every expected JSON key is present and no extra keys exist.

    IMPORTANT RULES FOR BACK SIDE:
    - The name after "Full Name." is the card holder's name (in English)
    - The name after "नाम थर" on back is the ISSUING OFFICER — ignore it
    - Date of Birth is in English: Year:YYYY Month:MM Day:DD → convert to YYYY/MM/DD
    - District names may be misspelled so make an educated guess(Eg: Gorcha → Gorkha)
    - Always output name in English

    Final Reminder:
    Take a deep breath and work on this problem step-by-step.


        Final Required JSON Structure:
        {
    "Name": "Full name strictly in English",
    "Citizenship Number": "Number match mixed digits with dashes ",
    "Date of Birth (DOB)": "YYYY/MM/DD",
    "Gender": "Male, Female, or Other",
    "Birth Place District": "Birth district",
    "Birth Place MetroPolitan/Sub-MetroPolitan/Municipality/VDC": "Birth Place MetroPolitan/Sub-MetroPolitan/Municipality/VDC",
    "Birth Place Ward": "Birth place ward number",
    "Permanent District": "Permanent address district",
    "Permanent MetroPolitan/Sub-MetroPolitan/Municipality/VDC": "Permanent address MetroPolitan/Sub-MetroPolitan/Municipality/VDC",
    "Permanent Ward": "Permanent address ward number"
        }
"""