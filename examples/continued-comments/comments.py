"""Parse comment continuations using a native Lark terminal."""

import json

from lark import Lark, Token, Transformer


GRAMMAR = r"""
start: BMAKE_COMMENT*
BMAKE_COMMENT: /#(?:\\\r?\n|[^\r\n])*(?:\r?\n|$)/
"""

class JoinComments(Transformer):
    """Turn one complete comment token into its logical text value."""

    def BMAKE_COMMENT(self, token: Token) -> str:
        """Remove only backslashes immediately followed by LF or CRLF."""
        return str(token).replace("\\\r\n", "").replace("\\\n", "")

    def start(self, comments: list[str]) -> list[str]:
        """Return the comments in their original order."""
        return comments


parser = Lark(GRAMMAR, parser="lalr", transformer=JoinComments())


if __name__ == "__main__":
    source = (
        "# this is a comment \\\nthat spans multiple \\\nlines\n"
        "# path C:\\temp\\notes\n"
    )
    print(json.dumps(parser.parse(source), ensure_ascii=False))
