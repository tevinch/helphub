# Prioritize full-text feeds without moving them

For **RSS Guard 5.2.5**, use one dedicated article label as a second way to browse your existing feeds. Keep your subject folders and scoring rules. Assign this label only to feeds you have checked and know supply the article body.

The label describes your chosen feeds. It does not detect whether arbitrary articles are complete. A long stub can be longer than a complete short article, so a body-length query is not a reliable replacement for this choice.

## Set up the label and filter

1. In the account's feed tree, right-click **Labels** and create **Full-text feeds**, with a distinct color. If that account synchronizes labels and cannot create them locally, create the label in the service first, then synchronize folders and other items.
2. Open that account's **Article filters** dialog. Create a filter, copy [`full-text-label.js`](full-text-label.js) into its editor, and enable it.
3. Assign the filter to the selected full-text feeds, including feeds in different subject folders. Leave summary-only feeds unchecked. Save the filter and its feed assignments.
4. Fetch those feeds. Each accepted article that reaches this filter gets the additional label. Your other filters keep their existing order: an earlier filter that ignores an article still stops its processing.
5. Select **Full-text feeds** under **Labels** to browse the matching articles across folders. Keep using the original folders when you want the subject-based view.

The script looks up the account's label ID rather than assuming the label title is its ID. It adds that one label and returns `Msg.Accept`, allowing later filters to continue. It does not move feeds, remove existing labels, or set `msg.score`, read state, starred state or contents. Missing or misspelled labels produce a filter error; create/synchronize the label before fetching.

For articles already stored, select the filter and use **Process checked feeds** in the Article filters dialog. First use **Test** on a small sample to inspect the result; Test does not save those article changes. Processing the checked feeds applies the selected filter to their stored articles. Fetching again also labels old articles that are still present in the feed; it cannot revisit older articles the publisher has removed from that feed.

Article saving and other filters still follow your existing RSS Guard settings. This recipe does not change those settings, reserve a score range, or replace your scoring scripts. It does not require a duplicate folder hierarchy, exporting publisher categories into labels, or a database query.

## Check the offline reading result

Before disconnecting, open a representative labelled article and confirm that its saved body contains what you need. Then disconnect and open it again from the label. External images, media and linked web pages may still need a network connection; this label does not download them. Mixed feeds can contain both full articles and summaries, so check those individually rather than treating the feed label as proof of completeness.

If a publisher switches to summaries, remove this filter's assignment for that feed and unassign the dedicated label from affected stored articles. Changing a filter assignment does not retroactively remove labels.

## What was checked

The official 5.2.5 native executable fetched three local fixture feeds in two folders and ran this exact filter. Existing and new articles from the two selected full-text feeds received the label; summary-feed articles did not. Existing labels, read/star states and scores were checked separately, and another scoring filter still ran. The fixture did not preassign the full-text label.

This verifies native feed processing and persisted article data. The desktop menu sequence and visual offline article display were not exercised, and the original requester's installation has not been tested. The fixtures used a local standard-feed account; synchronized services have their own label support and synchronization behavior.

## Sources

- [Original usage question](https://github.com/martinrotter/rssguard/issues/2508)
- [5.2.5 label instructions](https://github.com/martinrotter/rssguard/blob/5.2.5/docs/source/features/labels.md)
- [5.2.5 filter instructions and API](https://github.com/martinrotter/rssguard/blob/5.2.5/docs/source/features/filters.md)
- [5.2.5 label lookup and assignment implementation](https://github.com/martinrotter/rssguard/blob/5.2.5/src/librssguard/filtering/filterobjects.cpp)

## Optional coffee

This example is free. If it saves you some time and you would like to buy me a coffee, thank you. Contributions are entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
