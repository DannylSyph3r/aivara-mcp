import base64
import logging
from typing import Annotated

from mcp.server.fastmcp import Context
from pydantic import Field

from fhir_client import FhirClient
from fhir_utilities import get_fhir_context
from mcp_utilities import create_text_response

logger = logging.getLogger(__name__)


async def get_document_content(
    documentId: Annotated[
        str,
        Field(description="DocumentReference ID. Obtain this from GetDocuments."),
    ],
    ctx: Context = None,
) -> str:
    fhir_context = get_fhir_context(ctx)
    if not fhir_context:
        raise ValueError("FHIR context could not be retrieved.")

    logger.info("tool_get_document_content document_id=%s", documentId)

    fhir_client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)
    resource = await fhir_client.read(f"DocumentReference/{documentId}")

    if not resource:
        return create_text_response("Document not found.", is_error=True)

    try:
        data = resource["content"][0]["attachment"]["data"]
        return create_text_response(base64.b64decode(data).decode("utf-8"))
    except (KeyError, IndexError, ValueError) as exc:
        logger.error("document_decode_failed document_id=%s error=%s", documentId, exc)
        return create_text_response("Document content could not be decoded.", is_error=True)