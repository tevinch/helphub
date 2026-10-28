# Write Markdown flashcards for Qard

Qard detects **`[!qard]` callouts** in ordinary Markdown notes. A question followed by an answer in plain text is not enough. The callout title is the question; its quoted body is the answer.

This example follows Qard **0.6.2** and its [official Markdown cards guide](https://github.com/kylianmarceau/qard-obsidian/blob/0.6.2/docs/GUIDE.md#markdown-cards).

## Start with one card

Create a normal note in your vault and paste this into its Markdown source:

```markdown
---
qard-deck: Network basics
---

# Transport

> [!qard]- What does TCP provide?
> TCP provides **reliable, ordered delivery** of data.
```

Keep the card outside any code fence: do not paste the surrounding triple backticks into your note. Prefix every answer line, including blank lines, with `>`. Both the question and answer must have content. The `-` collapses the callout in the note; `[!qard]` and `[!qard]+` also work.

Save the note as a `.md` file in an ordinary, visible vault folder. With Qard enabled, run **Qard: Open study workspace** from Obsidian’s command palette. The expected result is the **Network basics** deck, with the question under **Transport**.

## Try the complete note

Open [network-basics.md](network-basics.md), choose its **Raw** view, and copy the Markdown source into one new vault note, once. It contains three cards:

| Deck | Topic | Question |
| --- | --- | --- |
| Network basics | Transport | What does TCP provide? |
| Network basics | Transport | Does UDP guarantee delivery? |
| Network basics | Addresses | What does the destination IP address identify? |

`qard-deck` sets the deck name. Notes with exactly the same deck name join that deck; names are case-sensitive. The closest preceding heading supplies the topic. Without `qard-deck`, Qard uses the note name by default; before any heading, the topic is `General`. A `qard-topic` frontmatter value overrides headings for the whole note.

The complete note includes explicit `qard-id` comments. They are optional for detection and keep a card’s identity when its wording changes. Each card ID must be unique across the vault. When making another card by copying one, remove its copied ID comment or give it a new unique ID. Keep an existing card’s ID when editing that card.

## If nothing appears

Check that you saved a `.md` note, the folder and filename are not hidden, and the marker is exactly `[!qard]`. Ensure the answer lines are quoted and the card is outside a fenced code example. Installing the plugin does not add sample notes automatically.

The exact 0.6.2 parser and card index detected all three complete cards and grouped them into the deck/topics above. Checks also covered fenced examples, wording edits with stable IDs, same-deck notes and duplicate IDs. These were scripted parser/index checks; the Obsidian interface was not exercised. See the [upstream guide](https://github.com/kylianmarceau/qard-obsidian/blob/0.6.2/docs/GUIDE.md#markdown-cards) for other card formats and study controls.

## Optional coffee

If this saved you some time, you can optionally buy me a coffee. The example and guide are free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
