"""wco-ge-skills over MCP — the same skill functions the hive agents use, for any MCP host.

    pip install "mcp>=1.10"
    HIVE_PROJECT=<project> python -m agenthive.mcp_server            # stdio (Claude Code, Gemini CLI, IDEs)
    HIVE_PROJECT=<project> python -m agenthive.mcp_server --http 8080  # streamable HTTP (e.g. Cloud Run, IAM-auth)

ADK agents can consume it remotely with MCPToolset(StreamableHTTPConnectionParams(url=...)); inside the hive they
call the functions in-process for latency and cost.
"""
from __future__ import annotations

import sys

from .catalog import load_catalog
from .tools import REGISTRY


def build_server():
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("wco-ge-skills", instructions="Wursta foundational skills: meeting risk, structured extraction, "
                     "video-to-knowledge, Drive organisation, partner content grading, OCR and email routing.")
    for skill in load_catalog().skills:
        fn = REGISTRY[skill["tool"]]
        server.tool(name=skill["id"], description=skill["description"] + "\n\n" + (fn.__doc__ or ""))(fn)
    return server


if __name__ == "__main__":
    srv = build_server()
    if "--http" in sys.argv:
        port = int(sys.argv[sys.argv.index("--http") + 1])
        srv.settings.host, srv.settings.port = "0.0.0.0", port
        srv.run(transport="streamable-http")
    else:
        srv.run()
