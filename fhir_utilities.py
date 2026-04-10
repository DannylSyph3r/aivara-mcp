import logging
import os

import jwt
from mcp.server.fastmcp import Context

from fhir_context import FhirContext
from mcp_constants import FHIR_ACCESS_TOKEN_HEADER, FHIR_SERVER_URL_HEADER, PATIENT_ID_HEADER

logger = logging.getLogger(__name__)


def get_fhir_context(ctx: Context | None) -> FhirContext | None:
    url = None
    token = None

    if ctx is not None:
        headers = ctx.request_context.request.headers
        url = headers.get(FHIR_SERVER_URL_HEADER)
        token = headers.get(FHIR_ACCESS_TOKEN_HEADER)

    if not url:
        url = os.getenv("FHIR_BASE_URL")
        if url:
            logger.debug("fhir_context_url_from_env")

    if not url:
        logger.warning("fhir_context_missing no url resolved from SHARP headers or env")
        return None

    return FhirContext(url=url, token=token)


def get_patient_id_if_context_exists(ctx: Context | None) -> str | None:
    if ctx is None:
        return None

    headers = ctx.request_context.request.headers
    fhir_token = headers.get(FHIR_ACCESS_TOKEN_HEADER)

    if fhir_token:
        try:
            claims = jwt.decode(fhir_token, options={"verify_signature": False})
            patient = claims.get("patient")
            if patient:
                logger.debug("patient_id_from_jwt patient_id=%s", patient)
                return str(patient)
        except Exception:
            logger.debug("jwt_decode_failed falling through to x-patient-id header")

    patient_id = headers.get(PATIENT_ID_HEADER)
    if patient_id:
        logger.debug("patient_id_from_header patient_id=%s", patient_id)
    return patient_id