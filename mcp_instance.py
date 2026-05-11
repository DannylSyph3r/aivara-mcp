import logging

from mcp.server.fastmcp import FastMCP

from tools.get_allergies import get_allergies
from tools.get_conditions import get_conditions
from tools.get_document_content import get_document_content
from tools.get_documents import get_documents
from tools.get_encounters import get_encounters
from tools.get_medications import get_medications
from tools.get_observations import get_observations
from tools.get_patient import get_patient
from tools.get_procedures import get_procedures
from tools.list_patients import list_patients
from tools.search_patients import search_patients
from tools.get_workspace_risk_summary import get_workspace_risk_summary

logger = logging.getLogger(__name__)

mcp = FastMCP("Aivara MCP", stateless_http=True, host="0.0.0.0")

# Patch capabilities to advertise FHIR context support — triggers SHARP header injection by PO.
_original_get_capabilities = mcp._mcp_server.get_capabilities


def _patched_get_capabilities(notification_options, experimental_capabilities):
    caps = _original_get_capabilities(notification_options, experimental_capabilities)
    caps.model_extra["extensions"] = {"ai.promptopinion/fhir-context": {}}
    return caps


mcp._mcp_server.get_capabilities = _patched_get_capabilities
logger.info("capabilities_patch_applied key=ai.promptopinion/fhir-context")

mcp.tool(
    name="GetPatient",
    description="Gets full patient demographics including DALY and QALY health burden scores.",
)(get_patient)

mcp.tool(
    name="ListPatients",
    description="Lists all patients in the workspace. Returns id, name, date of birth, and gender. Use count to control page size (default 20).",
)(list_patients)

mcp.tool(
    name="SearchPatients",
    description="Searches for patients by name. Accepts firstName, lastName, or a general name string. At least one must be provided.",
)(search_patients)

mcp.tool(
    name="GetConditions",
    description="Gets all conditions for a patient including clinical diagnoses and social determinants of health (SDOH). Both appear as Condition resources.",
)(get_conditions)

mcp.tool(
    name="GetObservations",
    description="Gets observations (vitals, labs, social history) for a patient, newest first. Values are normalised — blood pressure returns as two separate entries.",
)(get_observations)

mcp.tool(
    name="GetEncounters",
    description="Gets visit history for a patient, newest first. Includes encounter type, date, facility, and clinician.",
)(get_encounters)

mcp.tool(
    name="GetMedications",
    description="Gets medication requests for a patient with drug names resolved. Returns graceful empty if no medications on record.",
)(get_medications)

mcp.tool(
    name="GetAllergies",
    description="Gets known allergies for a patient. Returns a graceful no-allergy message if none recorded — this is expected for most patients in this workspace.",
)(get_allergies)

mcp.tool(
    name="GetDocuments",
    description="Lists all clinical notes for a patient with metadata. Returns status (current/superseded), date, author, and document ID for use with GetDocumentContent.",
)(get_documents)

mcp.tool(
    name="GetDocumentContent",
    description="Fetches and decodes the full text of a specific clinical note by DocumentReference ID. Returns structured plaintext with sections: Chief Complaint, HPI, Social History, Allergies, Medications, Assessment and Plan.",
)(get_document_content)

mcp.tool(
    name="GetProcedures",
    description="Gets procedures performed for a patient including procedure name, status, date, and the condition that triggered it.",
)(get_procedures)

mcp.tool(
    name="GetWorkspaceRiskSummary",
    description=(
        "Returns all patients in the workspace ranked by DALY score (highest disease burden first). "
        "Includes patient name, date of birth, gender, DALY, QALY, and patient ID for each entry. "
        "Always includes ranking basis explanation and explicit limitations caveat. "
        "Use for workspace-level triage queries only — invoke without a patient selected in the launchpad. "
        "Does not capture psychosocial risk, behavioural health history, safeguarding concerns, "
        "or paediatric growth status."
    ),
)(get_workspace_risk_summary)