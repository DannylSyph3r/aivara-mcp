import logging
from typing import Annotated

from mcp.server.fastmcp import Context
from pydantic import Field

from fhir_client import FhirClient
from fhir_utilities import get_fhir_context, get_patient_id_if_context_exists
from mcp_utilities import create_text_response

logger = logging.getLogger(__name__)


async def get_allergies(
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

    logger.info("tool_get_allergies patient_id=%s", patientId)

    fhir_client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)
    bundle = await fhir_client.search("AllergyIntolerance", {"patient": patientId})

    if not bundle or not bundle.get("entry"):
        return create_text_response("No known allergies found for this patient.")

    entries = bundle["entry"]
    lines = [f"Allergies for patient {patientId} ({len(entries)} found):\n"]

    for entry in entries:
        res = entry.get("resource", {})
        code = res.get("code", {})
        substance = code.get("text") or code.get("coding", [{}])[0].get("display", "Unknown")
        clinical_status = res.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "N/A")
        allergy_type = res.get("type", "N/A")
        criticality = res.get("criticality", "N/A")

        reactions = res.get("reaction", [])
        reaction = reactions[0].get("manifestation", [{}])[0].get("text") if reactions else None

        block = [
            f"Substance: {substance}",
            f"  Status: {clinical_status} | Type: {allergy_type} | Criticality: {criticality}",
        ]
        if reaction:
            block.append(f"  Reaction: {reaction}")
        lines.append("\n".join(block))

    return create_text_response("\n\n".join(lines))