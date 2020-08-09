import logging
import json

from modron.interact.npc import generate_and_render_npcs


def test_npc_generator(parser, payload, caplog):
    try:
        args = parser.parse_args(['npcgen', '3'])
        with caplog.at_level(logging.INFO):
            args.interact(args, payload)
    except OSError as exc:
        assert 'wkhtmltopdf' in str(exc), "Failure for a reason other than wkhtml not being installed"
    assert '3 NPCs from default' in caplog.messages[-1]

    # Print out an example to see how it looks
    example = generate_and_render_npcs('default', 2)
    print(json.dumps(example, indent=2))

    # Test the request coming from a DM
    payload.user_id = 'UP4K437HT'  # Logan Ward's user ID
    payload.channel_id = 'GNOTREALCHID'
    try:
        args = parser.parse_args(['npcgen', '3'])
        with caplog.at_level(logging.INFO):
            args.interact(args, payload)
    except OSError as exc:
        assert 'wkhtmltopdf' in str(exc), "Failure for a reason other than wkhtml not being installed"
    assert '3 NPCs from default' in caplog.messages[-2]
    assert 'Command came from' in caplog.messages[-1]
