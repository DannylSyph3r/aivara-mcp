import logging
from typing import Annotated

from mcp.server.fastmcp import Context
from pydantic import Field

from fhir_client import FhirClient
from fhir_utilities import get_fhir_context, get_patient_id_if_context_exists
from mcp_utilities import create_text_response

logger = logging.getLogger(__name__)


async def get_conditions(
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

    logger.info("tool_get_conditions patient_id=%s", patientId)

    fhir_client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)
    bundle = await fhir_client.search("Condition", {"patient": patientId})

    if not bundle or not bundle.get("entry"):
        return create_text_response("No conditions found for this patient.")

    entries = bundle["entry"]
    lines = [f"Conditions for patient {patientId} ({len(entries)} found):\n"]

    for entry in entries:
        res = entry.get("resource", {})
        name = res.get("code", {}).get("text", "Unknown")
        clinical_status = res.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "N/A")
        verification_status = res.get("verificationStatus", {}).get("coding", [{}])[0].get("code", "N/A")
        onset = res.get("onsetDateTime", "N/A")
        abatement = res.get("abatementDateTime")
        encounter_ref = res.get("encounter", {}).get("reference", "N/A")

        block = [
            f"Condition: {name}",
            f"  Status: {clinical_status} | Verification: {verification_status}",
            f"  Onset: {onset}",
        ]
        if abatement:
            block.append(f"  Resolved: {abatement}")
        block.append(f"  Encounter: {encounter_ref}")
        lines.append("\n".join(block))

    return create_text_response("\n\n".join(lines))