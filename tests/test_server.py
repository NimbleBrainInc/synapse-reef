"""The server answers over the current MCP protocol with FastMCP 4.

Everything here runs on the bundled data in data/; nothing reaches NDBC.
"""

import json

from fastmcp import Client

from mcp_reef.server import mcp


async def test_instructions_reach_the_client():
    async with Client(mcp) as client:
        # client.instructions reads whichever negotiation result the protocol era
        # produced; client.initialize() raises on the modern (server/discover) era.
        assert client.instructions is not None
        assert "find_buoys" in client.instructions


async def test_tools_are_read_only_and_link_the_card():
    async with Client(mcp) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
    assert {"find_buoys", "get_conditions"} <= set(tools)
    for tool in tools.values():
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
    meta = json.dumps(tools["get_conditions"].meta or {})
    assert "ui://reef/main" in meta


async def test_find_buoys_by_place_uses_the_bundled_catalog():
    async with Client(mcp) as client:
        found = await client.call_tool("find_buoys", {"place": "Half Moon Bay"})
        unknown = await client.call_tool("find_buoys", {"place": "Nowhereville Xyz"})
    assert "error" not in found.structured_content
    assert found.structured_content["matches"]
    assert {"lat", "lng"} <= set(found.structured_content["search"])
    # An unknown place answers with an error and no matches, so the first
    # assertions above can only pass on a real resolution.
    assert unknown.structured_content["matches"] == []
    assert "error" in unknown.structured_content


async def test_ui_resource_is_an_mcp_app():
    async with Client(mcp) as client:
        resources = {str(r.uri): r for r in await client.list_resources()}
        contents = await client.read_resource("ui://reef/main")
    assert resources["ui://reef/main"].mime_type == "text/html;profile=mcp-app"
    assert "<html" in contents[0].text.lower()
