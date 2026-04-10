import logging
from typing import Annotated

from mcp.server.fastmcp import Context
from pydantic import Field

from fhir_client import FhirClient
from fhir_utilities import get_fhir_context, get_patient_id_if_context_exists
from mcp_utilities import create_text_response

logger = logging.getLogger(__name__)


def _extract_observation_values(resource: dict) -> list[dict]:
    """Normalise the three FHIR observation value shapes into a flat list."""
    if resource.get("component"):
        return [
            {
                "name": comp.get("code", {}).get("coding", [{}])[0].get("display", "Unknown"),
                "value": comp.get("valueQuantity", {}).get("value"),
                "unit": comp.get("valueQuantity", {}).get("unit"),
            }
            for comp in resource["component"]
        ]

    name = resource.get("code", {}).get("text", "Unknown")

    if resource.get("valueQuantity"):
        return [{
            "name": name,
            "value": resource["valueQuantity"].get("value"),
            "unit": resource["valueQuantity"].get("unit"),
        }]

    if resource.get("valueCodeableConcept"):
        return [{
            "name": name,
            "value": resource["valueCodeableConcept"].get("text"),
            "unit": None,
        }]

    return [{"name": name, "value": None, "unit": None}]


async def get_observations(
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

    logger.info("tool_get_observations patient_id=%s", patientId)

    fhir_client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)
    bundle = await fhir_client.search("Observation", {"patient": patientId, "_sort": "-date"})

    if not bundle or not bundle.get("entry"):
        return create_text_response("No observations found for this patient.")

    entries = bundle["entry"]
    lines = [f"Observations for patient {patientId} ({len(entries)} found, newest first):\n"]

    for entry in entries:
        res = entry.get("resource", {})
        effective = res.get("effectiveDateTime", "N/A")
        status = res.get("status", "N/A")
        category = res.get("category", [{}])[0].get("coding", [{}])[0].get("code", "N/A")

        for obs in _extract_observation_values(res):
            value_str = f"{obs['value']} {obs['unit']}".strip() if obs["value"] is not None else "N/A"
            lines.append(
                f"- {obs['name']}: {value_str} | Date: {effective} | Category: {category} | Status: {status}"
            )

    return create_text_response("\n".join(lines))