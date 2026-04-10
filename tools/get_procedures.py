import logging
from typing import Annotated

from mcp.server.fastmcp import Context
from pydantic import Field

from fhir_client import FhirClient
from fhir_utilities import get_fhir_context, get_patient_id_if_context_exists
from mcp_utilities import create_text_response

logger = logging.getLogger(__name__)


async def get_procedures(
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

    logger.info("tool_get_procedures patient_id=%s", patientId)

    fhir_client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)
    bundle = await fhir_client.search("Procedure", {"patient": patientId})

    if not bundle or not bundle.get("entry"):
        return create_text_response("No procedures found for this patient.")

    entries = bundle["entry"]
    lines = [f"Procedures for patient {patientId} ({len(entries)} found):\n"]

    for entry in entries:
        res = entry.get("resource", {})
        name = res.get("code", {}).get("text", "Unknown")
        start = res.get("performedPeriod", {}).get("start", "N/A")
        end = res.get("performedPeriod", {}).get("end")
        facility = res.get("location", {}).get("display")
        encounter_ref = res.get("encounter", {}).get("reference")

        reason_refs = res.get("reasonReference", [])
        reason = reason_refs[0].get("display") if reason_refs else None

        block = [
            f"Procedure: {name}",
            f"  ID: {res.get('id')} | Status: {res.get('status', 'N/A')}",
            f"  Start: {start}",
        ]
        if end:
            block.append(f"  End: {end}")
        if facility:
            block.append(f"  Facility: {facility}")
        if encounter_ref:
            block.append(f"  Encounter: {encounter_ref}")
        if reason:
            block.append(f"  Reason: {reason}")
        lines.append("\n".join(block))

    return create_text_response("\n\n".join(lines))