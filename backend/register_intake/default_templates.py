"""Shared/default template schemas for ANC, Delivery, and PNC (v1).

ANC v1 is entered exactly as specified in cureva-docs/03-templates-and-intake.md.
Delivery v1 and PNC v1 are built out the same way from that file's documented
key fields and the signature fields used by the register-family cross-check and
the intelligence lenses (06-metrics-and-reporting.md).

OPEN DECISION #1 (08-delivery-plan.md): the final Delivery/PNC column lists must
be confirmed against the real national registers before pilot. These are a
faithful default to build and test against in the meantime; adding a column or
alias later is a new template version, never an in-place edit (rule #2).

canonical_field names are authoritative: they must match the cross-check
signatures (REGISTER_SIGNATURE_FIELDS) and the lens field maps.
"""

ANC_V1 = {
    "register_family": "ANC",
    "version": 1,
    "effective_date": "2026-01-01",
    "columns": [
        {"canonical_field": "card_number", "label": "Card/Folder Number", "type": "string", "required": True,
         "aliases": ["Card No", "Folder No", "Unit No", "Card Number"]},
        {"canonical_field": "lmp", "label": "Last Menstrual Period", "type": "date", "required": True,
         "aliases": ["LMP", "Last Menstrual Period", "L.M.P", "LMP Date"]},
        {"canonical_field": "edd", "label": "Expected Delivery Date", "type": "date", "required": False,
         "aliases": ["EDD", "E.D.D", "Expected Delivery Date", "Due Date"]},
        {"canonical_field": "gravida", "label": "Gravida", "type": "integer", "required": True,
         "aliases": ["Gravida", "G", "Grav"]},
        {"canonical_field": "parity", "label": "Parity", "type": "integer", "required": True,
         "aliases": ["Parity", "P", "Para"]},
        {"canonical_field": "gestational_age_weeks", "label": "Gestational Age (weeks)", "type": "integer", "required": False,
         "aliases": ["GA Weeks", "Gestational Age", "GA (wks)"]},
        {"canonical_field": "blood_pressure", "label": "Blood Pressure", "type": "string", "required": False,
         "plausible_range": "systolic 70-260 / diastolic 40-160",
         "aliases": ["BP", "Blood Press.", "Blood Pressure", "B.P"]},
        {"canonical_field": "weight_kg", "label": "Weight (kg)", "type": "decimal", "required": False,
         "plausible_range": "30-160", "aliases": ["Weight", "Weight (kg)"]},
        {"canonical_field": "haemoglobin", "label": "Haemoglobin", "type": "decimal", "required": False,
         "aliases": ["Hb", "Hb g/dl", "Haemoglobin"]},
        {"canonical_field": "genotype", "label": "Genotype", "type": "enum",
         "enum_values": ["AA", "AS", "SS", "AC", "SC", "CC"], "required": False,
         "aliases": ["Genotype", "Geno"]},
        {"canonical_field": "blood_group_rhesus", "label": "Blood Group / Rhesus", "type": "enum",
         "enum_values": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"], "required": False,
         "aliases": ["Blood Group/Rh", "Blood Group", "BG/Rh"]},
        {"canonical_field": "hiv_result", "label": "HIV Test Result", "type": "string", "required": False,
         "aliases": ["HIV", "HIV Result", "HIV Status"]},
        {"canonical_field": "syphilis_result", "label": "Syphilis Test Result", "type": "string", "required": False,
         "aliases": ["VDRL", "Syphilis"]},
        {"canonical_field": "iron_folate_given", "label": "Iron & Folate Given", "type": "boolean", "required": False,
         "aliases": ["Iron/Folate", "Iron and Folate"]},
        {"canonical_field": "tetanus_given", "label": "Tetanus Vaccination", "type": "boolean", "required": False,
         "aliases": ["TT", "Tetanus", "Tetanus Vaccination"]},
        {"canonical_field": "iptp_given", "label": "IPTp (Malaria Prevention) Dose Given", "type": "boolean", "required": False,
         "aliases": ["IPTp", "IPTp Dose", "SP", "SP Dose", "Malaria Prevention", "Malaria Prophylaxis"]},
        {"canonical_field": "next_appointment", "label": "Next Appointment Date", "type": "date", "required": False,
         "aliases": ["Next Appt", "Next Appointment", "Return Date"]},
    ],
}

DELIVERY_V1 = {
    "register_family": "Delivery",
    "version": 1,
    "effective_date": "2026-01-01",
    "columns": [
        {"canonical_field": "card_number", "label": "Card/Folder Number", "type": "string", "required": True,
         "aliases": ["Card No", "Folder No", "Unit No", "Card Number"]},
        {"canonical_field": "delivery_date", "label": "Date of Delivery", "type": "date", "required": True,
         "aliases": ["Delivery Date", "Date of Delivery", "DOD", "Date Delivered"]},
        {"canonical_field": "delivery_place", "label": "Place of Delivery", "type": "enum",
         "enum_values": ["Facility", "Home", "In transit", "Other"], "required": False,
         "aliases": ["Place of Delivery", "Delivery Place", "Place"]},
        {"canonical_field": "mode_of_delivery", "label": "Mode of Delivery", "type": "enum",
         "enum_values": ["SVD", "CS", "Assisted"], "required": True,
         "aliases": ["Mode of Delivery", "Mode", "Delivery Mode", "Type of Delivery"]},
        {"canonical_field": "attendant_category", "label": "Birth Attendant", "type": "enum",
         "enum_values": ["Doctor", "Midwife", "Nurse", "CHEW", "TBA", "Other"], "required": False,
         "aliases": ["Attendant", "Birth Attendant", "Skilled Attendant", "Conducted By"]},
        {"canonical_field": "maternal_outcome", "label": "Maternal Outcome", "type": "enum",
         "enum_values": ["Alive", "Died", "Referred"], "required": False,
         "aliases": ["Maternal Outcome", "Mother Outcome", "Condition of Mother"]},
        {"canonical_field": "baby_outcome", "label": "Baby Outcome", "type": "enum",
         "enum_values": ["Live birth", "Stillbirth", "Early neonatal death"], "required": False,
         "aliases": ["Baby Outcome", "Birth Outcome", "Condition of Baby"]},
        {"canonical_field": "still_birth", "label": "Stillbirth", "type": "boolean", "required": False,
         "aliases": ["Stillbirth", "Still Birth", "SB"]},
        {"canonical_field": "baby_sex", "label": "Baby Sex", "type": "enum",
         "enum_values": ["M", "F"], "required": False,
         "aliases": ["Sex", "Baby Sex", "Sex of Baby"]},
        {"canonical_field": "birth_weight_kg", "label": "Birth Weight (kg)", "type": "decimal", "required": False,
         "plausible_range": "0.5-6.0", "aliases": ["Birth Weight", "Weight (kg)", "BW"]},
        {"canonical_field": "referral_status", "label": "Referral", "type": "string", "required": False,
         "aliases": ["Referral", "Referred", "Referral Status"]},
    ],
}

PNC_V1 = {
    "register_family": "PNC",
    "version": 1,
    "effective_date": "2026-01-01",
    "columns": [
        {"canonical_field": "card_number", "label": "Card/Folder Number", "type": "string", "required": True,
         "aliases": ["Card No", "Folder No", "Unit No", "Card Number"]},
        {"canonical_field": "visit_date", "label": "Visit Date", "type": "date", "required": True,
         "aliases": ["Visit Date", "Date of Visit", "PNC Date"]},
        {"canonical_field": "delivery_date", "label": "Date of Delivery", "type": "date", "required": False,
         "aliases": ["Delivery Date", "Date of Delivery", "DOD"]},
        {"canonical_field": "days_postpartum", "label": "Days Postpartum", "type": "integer", "required": False,
         "aliases": ["Days Postpartum", "Day PP", "Postnatal Day", "Days After Delivery"]},
        {"canonical_field": "subject", "label": "Subject (Mother/Newborn)", "type": "enum",
         "enum_values": ["mother", "newborn"], "required": True,
         "aliases": ["Subject", "Mother/Baby", "Assessed"]},
        {"canonical_field": "maternal_assessment", "label": "Maternal Assessment", "type": "string", "required": False,
         "aliases": ["Maternal Assessment", "Mother Assessment", "Condition of Mother"]},
        {"canonical_field": "newborn_assessment", "label": "Newborn Assessment", "type": "string", "required": False,
         "aliases": ["Newborn Assessment", "Baby Assessment", "Condition of Baby"]},
        {"canonical_field": "feeding_status", "label": "Feeding Status", "type": "enum",
         "enum_values": ["Exclusive breastfeeding", "Mixed", "Replacement", "Not recorded"], "required": False,
         "aliases": ["Feeding", "Feeding Status", "Breastfeeding"]},
        {"canonical_field": "danger_signs", "label": "Danger Signs", "type": "string", "required": False,
         "aliases": ["Danger Signs", "Danger Sign", "Warning Signs"]},
        {"canonical_field": "family_planning", "label": "Family Planning", "type": "string", "required": False,
         "aliases": ["Family Planning", "FP", "FP Method"]},
        {"canonical_field": "visit_outcome", "label": "Visit Outcome", "type": "string", "required": False,
         "aliases": ["Visit Outcome", "Outcome"]},
        {"canonical_field": "referral_status", "label": "Referral", "type": "string", "required": False,
         "aliases": ["Referral", "Referred", "Referral Status"]},
    ],
}

DEFAULT_TEMPLATES = [ANC_V1, DELIVERY_V1, PNC_V1]
