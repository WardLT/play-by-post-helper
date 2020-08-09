import logging


def test_delay_status(parser, payload):
    args = parser.parse_args(['reminder', 'status'])
    args.interact(args, payload)


def test_delay_pause(parser, payload, caplog):
    args = parser.parse_args(['reminder', 'break', 'PT1S'])
    with caplog.at_level(logging.INFO):
        args.interact(args, payload)
    assert 'failed' not in caplog.messages[-1]
