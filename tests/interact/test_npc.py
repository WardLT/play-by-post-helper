import logging
import json

from pytest import mark
from discord import Guild

from modron.interact.npc import generate_and_render_npcs, NPCGenerator
from modron.tests.interact.conftest import MockContext


@mark.asyncio
async def test_npc_gen(payload: MockContext, guild: Guild, caplog):
    generator = NPCGenerator()
    parser = generator.parser
    try:
        args = parser.parse_args(['3'])
        with caplog.at_level(logging.INFO):
            await generator.interact(args, payload)
    except OSError as exc:
        assert 'wkhtmltopdf' in str(exc), "Failure for a reason other than wkhtml not being installed"
    assert '3 NPCs from default' in caplog.messages[-1]

    # Print out an example to see how it looks
    example = generate_and_render_npcs('default', 2)
    print(json.dumps(example, indent=2))
