# Read the first prompt in a resumed MCode session

When MCode shows `earlier turns omitted from live projection`, you can read the earlier saved prompts by exporting the open session.

1. Resume the session you want to read.
2. Enter this in the main MCode input, replacing the path with a private location on your Mac.

   ```text
   /export "/Users/yourname/Documents/Private Exports/mcode-history.md"
   ```

3. Open the file named in the **Exported Markdown** message. Find **Turn 1**, then **User**. You can return to the same MCode session and keep working.

For a session with two saved turns, the relevant parts look like this.

```markdown
## Turn 1

### User

Fixture prompt 001

### Assistant

Fixture reply 001

## Turn 2

### User

Fixture prompt 002
```

The export reads saved history and keeps its original order. A second export to the same path creates a numbered filename, such as `mcode-history-1.md`. Keep the file private if the conversation contains sensitive text. [MCode export documentation](https://github.com/MiniMax-AI/minimax-code/blob/v0.7.2/packages/tui/CHANGELOG.md#L1082-L1088)

If you want to look inside MCode first, enter `/transcript`, press `/`, and search for words you remember. This can find turns loaded into the transcript panel. Use `/export` if the result is missing or you want to read from the first saved turn.

## Verified

On macOS arm64, `/export` recovered the first prompt after reopening a 31-turn session in 0.7.2 and a 101-turn session in 0.7.9. Both sessions accepted another prompt afterward. Searching in `/transcript` also found the first prompt in the 31-turn session in 0.7.2.

## Optional coffee

If this saved you time and you'd like to buy me a coffee, thank you. It's entirely optional.

- **USDC / SOL · Solana** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20)** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
