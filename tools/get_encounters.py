import logging
from typing import Annotated

from mcp.server.fastmcp import Context
from pydantic import Field

from fhir_client import FhirClient
from fhir_utilities import get_fhir_context, get_patient_id_if_context_exists
from mcp_utilities import create_text_response

logger = logging.getLogger(__name__)


async def get_encounters(
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

    logger.info("tool_get_encounters patient_id=%s", patientId)

    fhir_client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)
    bundle = await fhir_client.search("Encounter", {"patient": patientId, "_sort": "-date"})

    if not bundle or not bundle.get("entry"):
        return create_text_response("No encounters found for this patient.")

    entries = bundle["entry"]
    lines = [f"Encounters for patient {patientId} ({len(entries)} found, newest first):\n"]

    for entry in entries:
        res = entry.get("resource", {})
        enc_type = res.get("type", [{}])[0].get("text", "N/A")
        start = res.get("period", {}).get("start", "N/A")
        end = res.get("period", {}).get("end", "N/A")
        clinician = res.get("participant", [{}])[0].get("individual", {}).get("display", "N/A")
        facility = res.get("location", [{}])[0].get("location", {}).get("display", "N/A")
        provider = res.get("serviceProvider", {}).get("display", "N/A")

        reason_codes = res.get("reasonCode", [])
        reason = reason_codes[0].get("coding", [{}])[0].get("display") if reason_codes else None

        block = [
            f"Encounter: {enc_type}",
            f"  ID: {res.get('id')} | Status: {res.get('status', 'N/A')}",
            f"  Period: {start} → {end}",
            f"  Clinician: {clinician}",
            f"  Facility: {facility}",
            f"  Provider: {provider}",
        ]
        if reason:
            block.append(f"  Reason: {reason}")
        lines.append("\n".join(block))

    return create_text_response("\n\n".join(lines))