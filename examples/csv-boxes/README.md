# Bulk inventory from CSV, including boxes

Kept 1.14.3 can import a hand-written spreadsheet and create its room paths. To create boxes too, import those paths as places, then use **Turn places into boxes…** on their parent places.

[inventory.csv](inventory.csv) is a six-item UTF-8 example. It includes quantities, tags, a comma, Unicode text and a multiline note. Try it in a test location, then replace the sample rows with your own inventory.

## Import the spreadsheet

As an owner or admin, open **Settings → Import → A spreadsheet (CSV)**. Choose an existing Kept location, then choose the CSV file.

Match these columns:

| CSV column | Kept field |
| --- | --- |
| `source_id` | Row ID (so a re-import skips it) |
| `name` | Name |
| `quantity` | Quantity |
| `place_path` | Place (a path like Garage > Shelf A) |
| `tags` | Tags |
| `notes` | Notes |

Map `source_id` manually: its header is initially guessed as **Don't import**.

Choose `>` as the place separator and enable **Make the places the file names that don't exist yet**. Choose where rows without a place should go. With the creation option off, an unknown path goes to that default place and its path is kept as text.

Select **Check the import**. In a location without these sample paths, the report should show **6 things, 6 places, 0 skipped**. Review the rows, then import and wait for completion. The check saves the import report and history; it adds no inventory, places or tags.

The paths are relative to the selected Kept location. They create rooms and spots there; create a new top-level Kept location separately when needed. You do not need exported UUIDs or a `things.csv` from Kept's readable export.

## Turn the intended places into boxes

The sample initially creates this place tree:

```text
Workshop
  Fasteners
  Carry case
    Inner tray
Office
  Paper box
```

Open each parent place. Under **MANAGE**, choose **Turn places into boxes…**:

1. On **Workshop**, select **Fasteners** and convert it.
2. On **Carry case**, select **Inner tray** and convert it.
3. On **Office**, select **Paper box** and convert it.
4. Return to **Workshop**, select **Carry case** and convert it.

A place that still contains child places cannot become a box. Work from the deepest level upwards. Each selected place becomes a box with the same ID, label code and contents. Review its existing contents before converting it: the operation converts the whole place. A batch accepts up to 200 places.

The result has Fasteners and Carry case in Workshop, Inner tray inside Carry case, and Paper box in Office. The six ordinary items keep their quantities, notes and tags. Notebook remains directly in Workshop. No separate CSV row is needed for each box.

Plain CSV has no `inside` or container-ID mapping. This sequence supplies that nesting through Kept's existing conversion operation.

## Add another batch

Keep each item's `source_id` stable and give a new item a new unique value. Re-importing an already imported ID skips that row; it does not update the item. Checking the same sample file after the box conversions skips all six rows. When every row is skipped, the UI shows a disabled **Nothing to import** button; no further import is needed. The completed repeated jobs in the application checks also added no duplicate items or recreated place paths.

Each CSV can contain up to 10,000 item rows and 8 MB. Save it as CSV UTF-8 with a header row. Quote cells containing commas or newlines, as the example does. Tags can be separated with semicolons.

## Verification

Scripted checks ran against the real Kept 1.14.3 application and PostgreSQL 18.6 with pgvector 0.8.6, using synthetic local inventory. They checked completed background imports, both path-creation settings, rejected missing-name and unsupported-container mappings, unchanged inventory during previews, conversion refusal before child places were converted, four conversions, nested contents, retained IDs and generated label codes, and an exact repeated import. Existing inventory, memberships, module settings and location settings were preserved; the location's item count increased as expected.

These checks used actual HTTP operations and independent database reads. Browser checks also followed the native column mapping, completed the first import and all four conversions, inspected nested contents, and checked the repeated file through the **Nothing to import** result. Existing content and settings were independently compared. These checks establish this synthetic sample workflow; the recipient's data and adoption remain unverified.

## References

- [Kept 1.14.3 import guide](https://github.com/keptinventory/kept/blob/v1.14.3/apps/docs/src/content/docs/users/import-export.md)
- [Kept 1.14.3 places and boxes guide](https://github.com/keptinventory/kept/blob/v1.14.3/apps/docs/src/content/docs/users/locations.md)
- [Original question](https://github.com/orgs/keptinventory/discussions/381)

## Optional coffee

If this saved you some time, a coffee is welcome, but entirely optional. The example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
