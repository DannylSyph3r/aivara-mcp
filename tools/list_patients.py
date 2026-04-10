import logging
from typing import Annotated

from mcp.server.fastmcp import Context
from pydantic import Field

from fhir_client import FhirClient
from fhir_utilities import get_fhir_context
from mcp_utilities import create_text_response

logger = logging.getLogger(__name__)


async def list_patients(
    count: Annotated[
        int,
        Field(description="Maximum number of patients to return. Defaults to 20."),
    ] = 20,
    ctx: Context = None,
) -> str:
    fhir_context = get_fhir_context(ctx)
    if not fhir_context:
        raise ValueError("FHIR context could not be retrieved.")

    logger.info("tool_list_patients count=%s", count)

    fhir_client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)
    bundle = await fhir_client.search("Patient", {"_count": str(count)})

    if not bundle or not bundle.get("entry"):
        return create_text_response("No patients found in this workspace.")

    total = bundle.get("total", "unknown")
    entries = bundle["entry"]
    lines = [f"Patients in workspace (server total: {total}, returned: {len(entries)}):\n"]

    for entry in entries:
        res = entry.get("resource", {})
        name_obj = res.get("name", [{}])[0]
        given = " ".join(name_obj.get("given", []))
        family = name_obj.get("family", "")
        full_name = f"{given} {family}".strip() or "Unknown"
        lines.append(
            f"- {full_name} | ID: {res.get('id')} | DOB: {res.get('birthDate', 'N/A')} | Gender: {res.get('gender', 'N/A')}"
        )

    return create_text_response("\n".join(lines))