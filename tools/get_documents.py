import logging
from typing import Annotated

from mcp.server.fastmcp import Context
from pydantic import Field

from fhir_client import FhirClient
from fhir_utilities import get_fhir_context, get_patient_id_if_context_exists
from mcp_utilities import create_text_response

logger = logging.getLogger(__name__)


async def get_documents(
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

    logger.info("tool_get_documents patient_id=%s", patientId)

    fhir_client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)
    bundle = await fhir_client.search("DocumentReference", {"patient": patientId})

    if not bundle or not bundle.get("entry"):
        return create_text_response("No clinical documents found for this patient.")

    entries = bundle["entry"]
    lines = [f"Clinical documents for patient {patientId} ({len(entries)} found):\n"]

    for entry in entries:
        res = entry.get("resource", {})
        doc_type = res.get("type", {}).get("coding", [{}])[0].get("display", "N/A")
        author = res.get("author", [{}])[0].get("display", "N/A")
        facility = res.get("custodian", {}).get("display", "N/A")

        context = res.get("context", {})
        encounter_ref = context.get("encounter", [{}])[0].get("reference") if context.get("encounter") else None
        period_start = context.get("period", {}).get("start")

        block = [
            f"Document ID: {res.get('id', 'N/A')}",
            f"  Status: {res.get('status', 'N/A')} | Date: {res.get('date', 'N/A')}",
            f"  Type: {doc_type}",
            f"  Author: {author}",
            f"  Facility: {facility}",
        ]
        if encounter_ref:
            block.append(f"  Encounter: {encounter_ref}")
        if period_start:
            block.append(f"  Period Start: {period_start}")
        lines.append("\n".join(block))

    return create_text_response("\n\n".join(lines))