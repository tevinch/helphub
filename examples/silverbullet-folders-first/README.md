# Browse SilverBullet with folders first

Open a separate SilverBullet sidebar that puts folders before pages and documents. It uses the native tree, so the arrow keys follow the same order that you see.

1. Put [Folders First.md](Folders%20First.md) under `Library/` in your SilverBullet space. You can also create `Library/Folders First` in SilverBullet and paste the file's Markdown into the editor.
2. Once the library page is visible in your space, run **System: Reload**, then run **Navigate: Folders First** from the command palette.
3. Use **Up** and **Down** to move through the rows, **Right** and **Left** to expand or collapse folders, and **Enter** to open a page or document. When a folder also has a page, use **Right** to browse its children and **Enter** to open the page itself.

The unfiltered sidebar can browse past 200 rows. The sample allows up to 500 matches when you type a filter. Change `presentation.limit` if you need a larger filtered set. Typing uses SilverBullet's fuzzy matcher, with results shown in tree order.

This sidebar shows your content pages and documents and follows the open page. Keep using **Navigate: Tree** for Library files, manual ordering, and file-management actions. The sample reads hide settings from page decorations and the existing Space Tree Outline. It leaves the outline untouched.

Verified in SilverBullet 3.0.1 using the keyboard to open pages beyond row 200, with and without a filter. The same check opened a folder’s own page and a text document and compared the space files before and after browsing.

[SilverBullet view API](https://github.com/silverbulletmd/silverbullet/blob/3.0.1/docs/Reference/API/view.md) · [SilverBullet widget API](https://github.com/silverbulletmd/silverbullet/blob/3.0.1/docs/Reference/API/widget.md)

## Optional coffee

If this saved you some time, you're welcome to buy me a coffee. It's entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
