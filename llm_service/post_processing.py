# post_processing.py
import json
from thefuzz import process, fuzz
from config import MUNI_JSON, VDC_JSON, EN_MUNI_JSON, EN_VDC_JSON

class NepalAddressValidator:
    def __init__(self):
        with open(MUNI_JSON, 'r', encoding='utf-8') as f:
            self.muni = json.load(f)
        with open(VDC_JSON, 'r', encoding='utf-8') as f:
            self.vdc = json.load(f)

        with open(EN_MUNI_JSON, 'r', encoding='utf-8') as f:
            self.en_muni = json.load(f)
        with open(EN_VDC_JSON, 'r', encoding='utf-8') as f:
            self.en_vdc = json.load(f)

        self.ne_district_list = []
        self.ne_hierarchy = {}  
        self.ne_global_map = {} 

        suffixes_ne = [" गाउँपालिका", " नगरपालिका", " उपमहानगरपालिका", " महानगरपालिका"]

        for provinces, districts in self.muni.items():
            for dist, munis in districts.items():

                if dist not in self.ne_district_list:
                    self.ne_district_list.append(dist)
                
                if dist not in self.ne_hierarchy:
                    self.ne_hierarchy[dist] = []

                for full_muni_name, wards in munis.items():
                    base = full_muni_name
                    for s in suffixes_ne:
                        if full_muni_name.endswith(s):
                            base = full_muni_name[:-len(s)].strip()
                            break
                    
                    entry = {
                        "base": base,
                        "full": full_muni_name,
                        "district": dist,
                        "type": "modern",
                        "wards": wards 
                    }
                    
                    self.ne_hierarchy[dist].append(entry)
                    self.ne_global_map[base] = entry


        
        # --- ENGLISH SETUP ---
        self.en_district_list = [] 
        self.en_hierarchy = {} 
        self.en_global_map = {} 

        # Suffixes to strip so we can match "Lalitpur" against "Lalitpur Metropolitan City"
        suffixes_en = [" Metropolitan City", " Sub-Metropolitan City", " Municipality", " Rural Municipality"]

        # 1. Build Municipality Hierarchy
        for provinces,districts in self.en_muni.items():
            for raw_dist_name, munis_dict in districts.items():
                dist_norm = raw_dist_name.strip().title()

                if dist_norm not in self.en_district_list:
                    self.en_district_list.append(dist_norm)

                if dist_norm not in self.en_hierarchy:
                    self.en_hierarchy[dist_norm] = {"munis": [], "vdcs": []}

                for raw_muni_key in munis_dict.keys():
                    full_name = raw_muni_key.strip() 
                    
                    # Extract Base Name
                    base = full_name
                    for suffix in suffixes_en:
                        if full_name.endswith(suffix):
                            base = full_name[:-len(suffix)].strip()
                            break
                    
                    entry = {
                        "base": base,       
                        "full": full_name,  
                        "district": dist_norm,
                        "type": "muni"
                    }

                    self.en_hierarchy[dist_norm]["munis"].append(entry)
                    # Add to global map for fallback search
                    self.en_global_map[base] = entry

        # Build VDC Hierarchy
        for dist, vdc_list in self.en_vdc.items():
            dist_norm = dist.strip().title()

            if dist_norm not in self.en_district_list:
                self.en_district_list.append(dist_norm)

            if dist_norm not in self.en_hierarchy:
                self.en_hierarchy[dist_norm] = {"munis": [], "vdcs": []}

            for vdc_raw in vdc_list:
                base = vdc_raw.strip()
                full_name = f"{base} VDC"

                entry = {
                    "base": base,      
                    "full": full_name, 
                    "district": dist_norm,
                    "type": "vdc"
                }
                self.en_hierarchy[dist_norm]["vdcs"].append(entry)

                if base not in self.en_global_map:
                    self.en_global_map[base] = entry

        # B. Process VDCs
        for dist, vdcs in self.vdc.items():
            if dist not in self.ne_district_list:
                self.ne_district_list.append(dist)
            
            if dist not in self.ne_hierarchy:
                self.ne_hierarchy[dist] = []

            for vdc_name in vdcs:
                full_name = f"{vdc_name} गा.वि.स."
                
                entry = {
                    "base": vdc_name,
                    "full": full_name,
                    "district": dist,
                    "type": "vdc",
                    "wards": None 
                }
                
                self.ne_hierarchy[dist].append(entry)
                if vdc_name not in self.ne_global_map:
                    self.ne_global_map[vdc_name] = entry


    def get_nepali_place(self, raw_district, raw_muni, raw_ward):
        raw_district = (raw_district or "").strip()
        raw_muni = (raw_muni or "").strip()

        # Output defaults
        result = {
            "district": raw_district,
            "municipality": raw_muni,
            "ward": raw_ward,
            "ward_valid": None,
            "type": "unmatched",
            "confidence": 0
        }

        if not raw_muni:
            return result
        
        # --- STEP 1: Resolve District ---
        clean_district = None
        if raw_district:
            # Check exact match
            if raw_district in self.ne_district_list:
                clean_district = raw_district
            else:
                # Fuzzy match District
                best_dist, score = process.extractOne(raw_district, self.ne_district_list, scorer=fuzz.ratio)
                if score >= 70:
                    clean_district = best_dist
                    result["district"] = clean_district

        # --- STEP 2: Scoped Search (Within District) ---
        found_place = None
        match_score = 0

        if clean_district and clean_district in self.ne_hierarchy:
            # Get all Munis/VDCs for this district
            candidates = self.ne_hierarchy[clean_district] # List of dicts
            candidate_names = [x["base"] for x in candidates]

            # Fuzzy match the base name
            best_base, score = process.extractOne(raw_muni, candidate_names, scorer=fuzz.ratio)
            
            if score >= 70:
                match_score = score
                # Find the full object corresponding to the name
                for x in candidates:
                    if x["base"] == best_base:
                        found_place = x
                        break

            # --- STEP 3: Global Fallback (If Step 2 Failed) ---
        if not found_place:
            return result
        
        if not found_place and not clean_district:
            all_bases = list(self.ne_global_map.keys())
            best_base, score = process.extractOne(raw_muni, all_bases, scorer=fuzz.ratio)
            
            # Require higher confidence for global search to avoid false positives
            if score >= 90: 
                match_score = score
                found_place = self.ne_global_map[best_base]
                # Update district since the original was likely wrong
                result["district"] = found_place["district"]


        # --- STEP 4: Finalize & Validate Ward ---
        if found_place:
            result["municipality"] = found_place["full"]
            result["type"] = found_place["type"]
            result["confidence"] = match_score
            
            # Check Ward validity (Only possible if we have a ward list, i.e., Modern Muni)
            if raw_ward and found_place["wards"]:
                if str(raw_ward) in [str(w) for w in found_place["wards"]]:
                    result["ward_valid"] = True
                else:
                    result["ward_valid"] = False
            else:
                # VDCs don't have ward data in JSON, or ward was missing
                result["ward_valid"] = None 

        return result
        

    def get_english_place(self, raw_muni, raw_district, raw_ward):
        
        raw_muni = raw_muni.strip()
        raw_district = raw_district.strip() if raw_district else ""
        
        # Output defaults
        result = {
            "district": raw_district,
            "municipality": raw_muni,
            "ward": raw_ward,
            "ward_valid": None,
            "type": "unmatched",
            "confidence": 0
        }

        if not raw_muni:
            return raw_district, None

        # Step 1: Resolve District
        clean_district = None
        if raw_district:
            # Check exact match
            if raw_district.title() in self.en_district_list:
                clean_district = raw_district.title()
            else:
                # Fuzzy match District
                best_dist, score = process.extractOne(raw_district, self.en_district_list, scorer=fuzz.ratio)
                if score >= 75:
                    clean_district = best_dist
        
        # Step 2: Search within District (High Confidence)
        if clean_district and clean_district in self.en_hierarchy:
            local_data = self.en_hierarchy[clean_district]
            
            # Combine Munis and VDCs for search (Munis are usually preferred)
            candidates = local_data["munis"] + local_data["vdcs"]
            candidate_names = [x["base"] for x in candidates]

            # Fuzzy match against base names
            best_muni_base, score = process.extractOne(raw_muni, candidate_names, scorer=fuzz.ratio)

            # If we found a good match inside the district
            if score >= 75:
                # Retrieve full object
                for x in candidates:
                    if x["base"] == best_muni_base:
                        return clean_district, x["full"]
        
            return clean_district, raw_muni

        if not clean_district and raw_muni:
            all_bases = list(self.en_global_map.keys())
            best_base, score = process.extractOne(raw_muni, all_bases, scorer=fuzz.ratio)

            # Very high threshold for global search to prevent false positives
            if score >= 90: 
                match = self.en_global_map[best_base]
                return match["district"], match["full"]

        # Step 4: No match found, return raw data
        return clean_district or raw_district, raw_muni


    def post_process(self, raw_data: dict, side:str) -> dict:
        MUNI_KEY = "Birth_Place_MetroPolitan_Sub_MetroPolitan_Municipality_VDC"
        PERM_MUNI_KEY = "Permanent_MetroPolitan_Sub_MetroPolitan_Municipality_VDC"

        if side == "front":
            birth = self.get_nepali_place(
                raw_data.get("Birth_Place_District"),
                raw_data.get(MUNI_KEY), 
                raw_data.get("Birth_Place_Ward"),
            )
            perm = self.get_nepali_place(
            raw_data.get("Permanent_District"),
            raw_data.get(PERM_MUNI_KEY), 
            raw_data.get("Permanent_Ward")
        )

            return {
            "extracted_raw": raw_data,
            "validated": {
                "birth_place": birth,
                "permanent_address": perm
            },
            "final_clean": {
                "Name": raw_data.get("Name"),
                "Citizenship Number": raw_data.get("Citizenship_Number"),
                "Date of Birth (DOB)": raw_data.get("Date_of_Birth_DOB"),
                "Father's Name": raw_data.get("Fathers_Name"),
                "Mother's Name": raw_data.get("Mothers_Name"),
                "Gender": raw_data.get("Gender"),
                "Spouse Name": raw_data.get("Spouse_Name"),
                "Birth Place": {
                    "District": birth["district"] or raw_data.get("Birth_Place_District"),
                    "Municipality/VDC": birth["municipality"] or raw_data.get("Birth_Place_MetroPolitan_Sub_MetroPolitan_Municipality_VDC"),
                    "Ward": birth["ward"] or raw_data.get("Birth_Place_Ward")
                },
                "Permanent Address": {
                    "District": perm["district"] or raw_data.get("Permanent_District"),
                    "Municipality/VDC": perm["municipality"] or raw_data.get("Permanent_MetroPolitan_Sub_MetroPolitan_Municipality_VDC"),
                    "Ward": perm["ward"] or raw_data.get("Permanent_Ward")
                }
            },
            "validation_notes": {
                "birth_place_type": birth["type"],
                "permanent_address_type": perm["type"],
                "ward_valid_birth": birth.get("ward_valid", None),
                "ward_valid_permanent": perm.get("ward_valid", None),
            }
        }
        else:
            birth_dist, birth_muni = self.get_english_place(
                raw_data.get(MUNI_KEY), 
                raw_data.get("Birth_Place_District"),
                raw_data.get("Birth_Place_Ward")
            )
            perm_dist, perm_muni = self.get_english_place(
                raw_data.get(PERM_MUNI_KEY),
                raw_data.get("Permanent_District"),
                raw_data.get("Permanent_Ward")
            )

            return {
                "Name": raw_data.get("Name", ""),
                "Citizenship Number": raw_data.get("Citizenship_Number"),
                "Date of Birth (DOB)": raw_data.get("Date_of_Birth_DOB"),
                "Gender": raw_data.get("Gender", "").split("(")[0].strip() if raw_data.get("Gender") else "",
                "Birth Place District": birth_dist or raw_data.get("Permanent_District"),
                "Birth Place MetroPolitan/Sub-MetroPolitan/Municipality/VDC": birth_muni or raw_data.get("Permanent_MetroPolitan_Sub_MetroPolitan_Municipality_VDC"),
                "Birth Place Ward": raw_data.get("Birth_Place_Ward"),
                "Permanent District": perm_dist or raw_data.get("Permanent_District"),
                "Permanent MetroPolitan/Sub-MetroPolitan/Municipality/VDC": perm_muni or raw_data.get("Permanent_MetroPolitan_Sub_MetroPolitan_Municipality_VDC"),
                "Permanent Ward": raw_data.get("Permanent_Ward"),
                "Issued Date": raw_data.get("Issued Date", "")
            }
            