# Align two faces along X in SolidCraft

To bring Body2's positive-X face onto Body1's positive-X face without changing Body2's Y/Z placement, use a **construction plane as the Align target**. A face target also matches the picked point; a plane target moves along the plane's normal.

Plane targets were added in [SolidCraft 0.18.3](https://github.com/tangency-labs/solidcraft/releases/tag/v0.18.3). The steps below were checked in the official browser app, build `0.25.1-39f96bbc73b76056`. If you are using 0.17, use a current release for this route. Keep a copy of your original design: newer saved formats cannot be opened by older releases.

## Use the native dialogs

These steps apply to two independent bodies with already-parallel positive-X faces.

1. Open a copy of the design and make the positive-X faces visible. The **Right** view is useful for picking them.
2. Choose **Model → Construct → Offset Plane**. Select Body1's positive-X face as **Plane**, leave **Distance** at `0 mm`, and confirm. This creates a construction plane on that face; the default name in the example is `Plane1`.
3. Open **Align** from **Model → Modify**, or find it using **Search commands**.
4. Set **Bodies** to `Body2` only. Activate **From** and select Body2's positive-X face.
5. Activate **To**, then click `Plane1` under **Construction** in the Browser. Select the plane entry, rather than clicking Body1's face again.
6. Enable **Flip** for these two positive-X normals. Check the preview and press **OK**.

Body2's selected face is now in the target plane. Its Y/Z placement stays the same. A plane target can still rotate a tilted source face, so this example deliberately uses parallel faces and Flip to retain the orientation.

**Bodies** and **From** serve different purposes. Bodies is the collection to move; From is one reference on that collection. One reference can move several selected bodies together, preserving their arrangement. The target can belong to a body that is not in the moving collection.

## Small example with measurable coordinates

The two boxes below have their long directions at right angles in the XY plane. They are also offset in Y and Z, so an unwanted shift is easy to detect. All coordinates are in millimetres.

| Body | Before: minimum → maximum | After: minimum → maximum |
|---|---|---|
| Body1 | `[0, 0, 0] → [30, 10, 8]` | `[0, 0, 0] → [30, 10, 8]` |
| Body2 | `[45, 35, 3] → [55, 65, 11]` | `[20, 35, 3] → [30, 65, 11]` |

Body2 moves `−25 mm` in X. Both positive-X faces end at `X = 30`; every Y/Z coordinate and every vertex of Body1 stays unchanged.

[axis-alignment.json](axis-alignment.json) contains the complete native command recipe: create the two boxes, create the zero-offset plane, align Body2 and measure both bodies. It is an example command script, not a saved project. Run it in an empty design. For CLI command scripts, see the [official script instructions](https://github.com/tangency-labs/solidcraft/blob/v0.25.1/docs/scripts.md); the [command reference](https://docs.solidcraft.io/reference/commands.html) describes the parameters. This script was verified through the official browser app's native command interface; a standalone CLI executable was not run.

The important distinction in the Align command is:

```json
{
  "command": "solid.align",
  "params": {
    "bodies": ["Body2"],
    "from_face": [55, 50, 7],
    "to_plane": "X face plane",
    "flip": true
  }
}
```

For a repeat check, move Body2 `7 mm` along X using **Move / Copy**, then run the same Align steps again with its current positive-X face. It returns to the bounds shown above.

## What was checked

Software-operated checks exercised the actual web dialogs, geometry selections, preview and confirmation. Native measurements, face data and all 16 box vertices confirmed the X-only move and the unchanged first body. A second Move → Align operation completed, and a JSON design was saved, closed and reopened with the same geometry. The complete command recipe was also checked in a fresh empty document.

Checks that used a face destination, left Flip off or skipped Align were required to fail the coordinate checks. This is a new two-box example; the original discussion's attached design was not loaded. Desktop releases and the 0.17 runtime were not tested.

References: [original question](https://github.com/tangency-labs/solidcraft/discussions/3597), [native plane-target implementation](https://github.com/tangency-labs/solidcraft/pull/4248), [command reference](https://docs.solidcraft.io/reference/commands.html#align), [current releases](https://github.com/tangency-labs/solidcraft/releases).

## Optional coffee

This example and guide are free. If they saved you some time, an entirely optional coffee is welcome.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
