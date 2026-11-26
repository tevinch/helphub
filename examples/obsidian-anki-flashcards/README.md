# Sync an Obsidian flashcard to Anki

Flashcards by reuseman supports Obsidian Desktop 1.13.0 and up. Write a question and answer in Markdown, then update the corresponding note in Anki after editing it in Obsidian. [Flashcards in the Obsidian community directory](https://community.obsidian.md/plugins/flashcards-obsidian).

## Set up the local connection

1. In Obsidian, open **Settings → Community plugins**. Search for **Flashcards** by **reuseman**, then install and enable it in your vault.
2. In Anki Desktop, open **Tools → Add-ons → Get Add-ons**, enter `2055492159`, then restart Anki. [AnkiConnect on AnkiWeb](https://ankiweb.net/shared/info/2055492159).
3. Keep Anki open on the profile you want to use. Flashcards uses AnkiConnect's default local address, `http://127.0.0.1:8765`.

## Create a card and update it

1. Copy [Desk-note.md](Desk-note.md) into your vault and open it in Obsidian. You can also paste this line into a new note.

   ```markdown
   What is the name of the shelf for incoming paperwork?::Intake tray
   ```

2. Open Obsidian's command palette and run **Flashcards: Update Anki from current note**. Open **Browse** in Anki and search for `incoming paperwork`. The result has `Intake tray` as its answer.
3. In Obsidian, change `Intake tray` to `Receiving tray`. Leave the `flashcards` property and the `^q-…` anchor that the plugin added. Run the same command again.
4. Search for `incoming paperwork` in Anki again. The same card now answers `Receiving tray`.

Flashcards treats the Markdown note as the source for the card content. This example starts with a new card in Flashcards v2 syntax. The [Flashcards documentation](https://github.com/reuseman/flashcards-obsidian/tree/2.2.0#readme) shows additional card types and syntax.

## Verification

A local check used Obsidian 1.15.1 on macOS, Flashcards 2.2.0, Anki 26.09.4 on Debian ARM64, and AnkiConnect 26.11.22.0. The first update created one card. The second changed its answer and kept the same note and card IDs. An unrelated card in the test collection retained its original fields.

## Optional coffee

If this example saved you time and you’d like to buy me a coffee, thank you. Contributions are entirely optional.

- **USDC / SOL · Solana** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20)** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
