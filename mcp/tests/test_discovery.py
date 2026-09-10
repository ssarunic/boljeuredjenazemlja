"""F1: discovery guards - bilingual tool descriptions + routing skill.

Static checks (read source/skill as text) so they need no MCP SDK. They guard
against the descriptions or skill silently losing their Croatian trigger
vocabulary, which is what made the tools undiscoverable for HR queries.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SERVER = REPO / "mcp" / "src" / "cadastral_mcp" / "server.py"
SKILL = REPO / ".claude" / "skills" / "cadastral-lookup" / "SKILL.md"


def test_tool_descriptions_carry_croatian_vocabulary() -> None:
    text = SERVER.read_text(encoding="utf-8")
    for term in [
        "katastar",            # cadastre
        "čestica",             # parcel
        "katastarska općina",  # cadastral municipality
        "posjedovni list",     # possession sheet (cadastre)
        "vlastovnica",         # ownership sheet (land registry)
        "vlasnici",            # owners
        "zemljišn",            # land registry (zemljišne knjige / zemljišnoknjižni)
    ]:
        assert term in text, f"missing trigger vocabulary: {term!r}"


def test_routing_skill_exists_and_encodes_playbook() -> None:
    assert SKILL.exists(), "cadastral-lookup SKILL.md is missing"
    skill = SKILL.read_text(encoding="utf-8")
    # Register disambiguation and the key routing tool must be present.
    assert "cadastre" in skill and "land_registry" in skill
    assert "get_lr_unit" in skill and "get_parcel" in skill
    # Frontmatter description (the discovery surface) names the domain bilingually.
    assert "katastar" in skill and "zemljišne knjige" in skill
