def create_text_response(text: str, is_error: bool = False) -> str:
    # is_error is semantically meaningful at call sites — signals intent clearly.
    # It is inert at the MCP protocol level: FastMCP surfaces errors via raised
    # exceptions, not return values. Retained for future extension.
    return text