import logging
from typing import Annotated

from mcp.server.fastmcp import Context
from pydantic import Field

from fhir_client import FhirClient
from fhir_utilities import get_fhir_context, get_patient_id_if_context_exists
from mcp_utilities import create_text_response

logger = logging.getLogger(__name__)


async def get_medications(
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

    logger.info("tool_get_medications patient_id=%s", patientId)

    fhir_client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)
    bundle = await fhir_client.search("MedicationRequest", {"patient": patientId})

    if not bundle or not bundle.get("entry"):
        return create_text_response("No medications found for this patient.")

    entries = bundle["entry"]
    lines = [f"Medications for patient {patientId} ({len(entries)} found):\n"]

    for entry in entries:
        res = entry.get("resource", {})

        med_ref = res.get("medicationReference", {}).get("reference", "")
        med_id = med_ref.replace("Medication/", "") if med_ref else ""
        medication = await fhir_client.read(f"Medication/{med_id}") if med_id else None
        drug_name = medication["code"]["text"] if medication else "Unknown"

        status = res.get("status", "N/A")
        intent = res.get("intent", "N/A")
        authored = res.get("authoredOn", "N/A")
        requester = res.get("requester", {}).get("display", "N/A")
        reason_codes = res.get("reasonCode", [])
        reason = reason_codes[0].get("text") if reason_codes else None

        block = [
            f"Medication: {drug_name}",
            f"  Status: {status} | Intent: {intent}",
            f"  Authored: {authored}",
            f"  Requester: {requester}",
        ]
        if reason:
            block.append(f"  Reason: {reason}")
        lines.append("\n".join(block))

    return create_text_response("\n\n".join(lines))