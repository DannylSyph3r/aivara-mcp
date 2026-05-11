import logging

from mcp.server.fastmcp import Context

from fhir_client import FhirClient
from fhir_utilities import get_fhir_context
from mcp_utilities import create_text_response

logger = logging.getLogger(__name__)

_DALY_URL = "http://synthetichealth.github.io/synthea/disability-adjusted-life-years"
_QALY_URL = "http://synthetichealth.github.io/synthea/quality-adjusted-life-years"


async def get_workspace_risk_summary(
    ctx: Context = None,
) -> str:
    # Workspace-scoped — ranks all patients by DALY score with limitations caveat. No patient ID required.
    fhir_context = get_fhir_context(ctx)
    if not fhir_context:
        return create_text_response(
            "FHIR context could not be retrieved. Ensure this tool is invoked "
            "from the PO launchpad with a valid workspace session.",
            is_error=True,
        )

    fhir_client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)

    bundle = await fhir_client.search("Patient", {"_count": "50"})
    if not bundle:
        return create_text_response("No patients found in this workspace.", is_error=True)

    entries = bundle.get("entry", [])
    if not entries:
        return create_text_response("No patients found in this workspace.", is_error=True)

    patients = []
    for entry in entries:
        try:
            resource = entry.get("resource", {})
            patient_id = resource.get("id", "")

            name_obj = resource.get("name", [{}])[0]
            given = " ".join(name_obj.get("given", []))
            family = name_obj.get("family", "")
            full_name = f"{given} {family}".strip() or "Unknown"

            birth_date = resource.get("birthDate", "Unknown")
            gender = resource.get("gender", "Unknown")

            extensions = resource.get("extension", [])
            daly = next(
                (e["valueDecimal"] for e in extensions if e.get("url") == _DALY_URL),
                None,
            )
            qaly = next(
                (e["valueDecimal"] for e in extensions if e.get("url") == _QALY_URL),
                None,
            )

            patients.append({
                "patient_id": patient_id,
                "name":       full_name,
                "birth_date": birth_date,
                "gender":     gender,
                "daly":       daly,
                "qaly":       qaly,
            })
        except Exception as exc:
            logger.warning("get_workspace_risk_summary_patient_parse_error error=%s", exc)
            continue

    scored   = sorted(
        [p for p in patients if p["daly"] is not None],
        key=lambda p: p["daly"],
        reverse=True,
    )
    unscored = [p for p in patients if p["daly"] is None]

    logger.info(
        "tool_get_workspace_risk_summary total_patients=%d scored=%d unscored=%d",
        len(patients), len(scored), len(unscored),
    )

    lines = [
        f"WORKSPACE RISK SUMMARY — {len(patients)} patients total",
        "Ranked by DALY score (highest disease burden first)\n",
        "RANKED PATIENTS (by disease burden):",
    ]

    if not scored:
        lines.append("No patients with DALY scores found in this workspace.")
    else:
        for i, p in enumerate(scored, start=1):
            qaly_str = f"{p['qaly']:.3f}" if p["qaly"] is not None else "N/A"
            lines.append(
                f"{i}. {p['name']} | DOB: {p['birth_date']} | {p['gender']} | "
                f"DALY: {p['daly']:.3f} | QALY: {qaly_str} | ID: {p['patient_id']}"
            )

    if unscored:
        lines.append(f"\nPATIENTS WITHOUT DALY SCORE ({len(unscored)}):")
        for p in unscored:
            lines.append(
                f"- {p['name']} | DOB: {p['birth_date']} | {p['gender']} | ID: {p['patient_id']}"
            )

    lines.extend([
        "\nRANKING BASIS:",
        (
            "DALY (Disability-Adjusted Life Years) measures physiological disease burden — "
            "the number of years of healthy life lost to illness, disability, or premature death. "
            "Higher DALY = higher burden. Lower DALY = better health status."
        ),
        "\nIMPORTANT LIMITATIONS — THIS RANKING DOES NOT CAPTURE:",
        (
            "1. Psychosocial risk: intimate partner abuse, social isolation, limited social contact\n"
            "2. Behavioural health: depression screening history, substance use, anxiety assessments\n"
            "3. Paediatric growth concerns: BMI percentile outliers, weight-for-length deviations\n"
            "4. Safeguarding risks: domestic abuse flags, compound SDOH vulnerability\n"
            "A high DALY rank does not mean highest clinical urgency. A patient ranked low on DALY "
            "may carry significant psychosocial or safeguarding risk. Consult Aivara Behavioural Health, "
            "Aivara Safeguarding, or Aivara Paediatric Growth for domain-specific risk assessment."
        ),
    ])

    return create_text_response("\n".join(lines))