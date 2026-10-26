"""The CLI's user-facing error type.

Deliberately free of third-party imports. `factory ids` runs before every push
that adds artifacts, so it must work on a bare Python; importing this from
`project` would drag in the adapter and model chain, and with it PyYAML.
"""

from __future__ import annotations


class FactoryError(Exception):
    """User-facing CLI error."""
