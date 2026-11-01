# Continued comments in Lark

Keep a continued comment as one terminal, then transform its value. Lark compiles a terminal's contents into a regular expression; `%ignore CONT` cannot remove a substring that has already been consumed inside `BMAKE_COMMENT`.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python comments.py
python check.py
```

On Windows, activate with `.venv\Scripts\activate` instead.

The grammar in [comments.py](comments.py) matches a backslash immediately followed by LF or CRLF as a continuation:

```lark
start: BMAKE_COMMENT*
BMAKE_COMMENT: /#(?:\\\r?\n|[^\r\n])*(?:\r?\n|$)/
```

The continuation alternative comes before the ordinary-character alternative. Ordinary backslashes stay in the token. A noncontinued newline ends it, so the next comment remains a separate result. EOF without a final newline is accepted.

A terminal callback can then remove just the continuation pairs:

```python
from lark import Lark, Transformer

class JoinComments(Transformer):
    def BMAKE_COMMENT(self, token):
        return str(token).replace("\\\r\n", "").replace("\\\n", "")

    def start(self, comments):
        return comments

parser = Lark(GRAMMAR, parser="lalr", transformer=JoinComments())
```

For this input:

```text
# this is a comment \
that spans multiple \
lines
# path C:\temp\notes
```

`parser.parse(...)` returns two strings:

```json
["# this is a comment that spans multiple lines\n", "# path C:\\temp\\notes\n"]
```

This preserves the final line ending and all other spaces. A backslash followed by spaces before a newline is ordinary text, because it is not immediately followed by the newline.

For **bmake-style whitespace folding**, its [manual](https://man.netbsd.org/make.1) also specifies compressing the continued newline and the next line's initial whitespace to one space. If that is the semantic value you want, replace the callback's return with this instead:

```python
import re

return re.sub(r"\\\r?\n[ \t]*", " ", str(token))
```

The supplied example implements literal pair removal from the question. It is a comment grammar fragment to incorporate into a larger grammar; it does not parse complete Makefiles or implement all make escaping rules. The original source position still belongs to the raw token, so use the untransformed parse tree when you need a lossless source view.

Seven checks run the actual Lark 1.3.1 parser and Transformer on Python 3.12.4. They cover the three-line example, adjacent comments, repeated parsing, ordinary and doubled backslashes, CRLF, EOF, Unicode, rejected unrelated lines, raw-token versus transformed values, and the complete executable example. These are scripted checks; the original application's full grammar was not provided.

Official references: [terminal regular expressions](https://lark-parser.readthedocs.io/en/stable/grammar.html#regular-expressions-ambiguity), [ignore directives](https://lark-parser.readthedocs.io/en/stable/grammar.html#ignore), [Transformer token callbacks](https://lark-parser.readthedocs.io/en/stable/visitors.html#transformer). Original [continued-comment question](https://github.com/lark-parser/lark/issues/1509).

## Optional coffee

This example is free. If it saved you time, buying me a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
