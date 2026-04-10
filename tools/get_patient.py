import logging
from typing import Annotated

from mcp.server.fastmcp import Context
from pydantic import Field

from fhir_client import FhirClient
from fhir_utilities import get_fhir_context, get_patient_id_if_context_exists
from mcp_utilities import create_text_response

logger = logging.getLogger(__name__)

_DALY_URL = "http://synthetichealth.github.io/synthea/disability-adjusted-life-years"
_QALY_URL = "http://synthetichealth.github.io/synthea/quality-adjusted-life-years"


async def get_patient(
    patientId: Annotated[
        str | None,
        Field(description="Patient ID. Optional if patient context exists from PO launchpad."),
    ] = None,
    ctx: Context = None,
) -> str:
    if not patientId:
        patientId = get_patient_id_if_context_exists(ctx)
        if not patientId:
            raise ValueError("No patient context found. Provide a patientId or invoke from PO launchpad.")

    fhir_context = get_fhir_context(ctx)
    if not fhir_context:
        raise ValueError("FHIR context could not be retrieved.")

    logger.info("tool_get_patient patient_id=%s", patientId)

    fhir_client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)
    patient = await fhir_client.read(f"Patient/{patientId}")

    if not patient:
        return create_text_response("Patient not found.", is_error=True)

    name_obj = patient.get("name", [{}])[0]
    given = " ".join(name_obj.get("given", []))
    family = name_obj.get("family", "")
    prefix_list = name_obj.get("prefix", [])
    prefix = prefix_list[0] if prefix_list else ""
    full_name = f"{prefix} {given} {family}".strip() if prefix else f"{given} {family}".strip()

    addr = patient.get("address", [{}])[0]
    address_parts = [
        (addr.get("line") or [""])[0],
        addr.get("city", ""),
        addr.get("state", ""),
        addr.get("postalCode", ""),
    ]
    address = ", ".join(p for p in address_parts if p) or "Not recorded"

    phone = (patient.get("telecom") or [{}])[0].get("value", "Not recorded")
    marital_status = patient.get("maritalStatus", {}).get("text", "Not recorded")

    extensions = patient.get("extension", [])
    daly = next((e["valueDecimal"] for e in extensions if e.get("url") == _DALY_URL), None)
    qaly = next((e["valueDecimal"] for e in extensions if e.get("url") == _QALY_URL), None)

    lines = [
        f"Patient: {full_name}",
        f"ID: {patient['id']}",
        f"Gender: {patient.get('gender', 'Not recorded')}",
        f"Date of Birth: {patient.get('birthDate', 'Not recorded')}",
        f"Address: {address}",
        f"Phone: {phone}",
        f"Marital Status: {marital_status}",
        f"DALY: {daly if daly is not None else 'Not recorded'}",
        f"QALY: {qaly if qaly is not None else 'Not recorded'}",
    ]

    return create_text_response("\n".join(lines))