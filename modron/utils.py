
# Colors based on the Material design scheme
colors = {
    'red': '#B71C1C',
    'green': '#2E7D32',
    'gray': '#263238'
}


def escape_slack_characters(raw: str) -> str:
    """Escape the special characters that are used by Slack
    in their messaging API.

    See `Slack API docs <https://api.slack.com/reference/surfaces/formatting#escaping>`_.

    Args:
        raw (str): String to be escaped
    Returns:
        (str) String with problematic escape strings
    """

    # Escape &
    out = raw.replace("&", "&amp;")

    # Escape < and >
    return out.replace("<", "&lt;").replace(">", "&gt;")
