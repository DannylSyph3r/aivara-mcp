import logging
from typing import Annotated

from mcp.server.fastmcp import Context
from pydantic import Field

from fhir_client import FhirClient
from fhir_utilities import get_fhir_context
from mcp_utilities import create_text_response

logger = logging.getLogger(__name__)


async def search_patients(
    name: Annotated[
        str | None,
        Field(description="General name search string. Use when you have a partial or full name."),
    ] = None,
    firstName: Annotated[
        str | None,
        Field(description="Patient first (given) name."),
    ] = None,
    lastName: Annotated[
        str | None,
        Field(description="Patient last (family) name."),
    ] = None,
    ctx: Context = None,
) -> str:
    if not any([name, firstName, lastName]):
        raise ValueError("At least one search parameter is required: name, firstName, or lastName.")

    fhir_context = get_fhir_context(ctx)
    if not fhir_context:
        raise ValueError("FHIR context could not be retrieved.")

    if name:
        params = {"name": name}
    elif firstName and lastName:
        params = {"given": firstName, "family": lastName}
    elif firstName:
        params = {"given": firstName}
    else:
        params = {"family": lastName}

    logger.info("tool_search_patients params=%s", params)

    fhir_client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)
    bundle = await fhir_client.search("Patient", params)

    if not bundle or not bundle.get("entry"):
        return create_text_response("No patients found matching the search criteria.")

    entries = bundle["entry"]
    lines = [f"Found {len(entries)} patient(s):\n"]

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