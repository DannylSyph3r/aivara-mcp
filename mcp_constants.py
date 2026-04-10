# Single source of truth for SHARP header names.
# Every module that reads SHARP headers imports from here — no hardcoded strings elsewhere.
FHIR_SERVER_URL_HEADER = "x-fhir-server-url"
FHIR_ACCESS_TOKEN_HEADER = "x-fhir-access-token"
PATIENT_ID_HEADER = "x-patient-id"