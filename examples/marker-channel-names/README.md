# Backsub marker names across acquisition cycles

Use a unique `marker_name` for every input row, and keep the rows in the same order as the image planes. This follows [Backsub's documented input contract](https://github.com/SchapiroLabor/Background_subtraction#inputs).

In Backsub 0.5.2, repeated `DAPI` labels with an empty `background` do **not** merge those planes. The command reads each retained plane by its original row position. Name lookup happens when a row has a nonempty `background`: if several rows have that name, Backsub warns and uses the first occurrence. It does not choose a background by `cycle_number`.

This example answers [the repeated-DAPI question](https://github.com/SchapiroLabor/Background_subtraction/issues/32) with a small generated TIFF, the unmodified released CLI, and checks of the resulting pixels, CSV and OME metadata.

## Try the recommended layout

Use Python 3.12 and install the tested dependency versions:

```sh
python -m venv .venv
# Activate .venv with the command for your shell.
python -m pip install --index-url https://pypi.org/simple -r requirements.txt

python make_fixture.py --out example
python -m backsub --input example/input.tif \
  --output example/output.ome.tif --markers example/markers.csv \
  --marker-output example/output.csv --pixel-size 1 \
  --tile-size 16 --compression none
```

The fixture has two cycles, each containing two background planes, a DAPI reference and a signal plane. Background rows have `remove=TRUE`: they remain available for subtraction, but are excluded from the output. The four retained planes are:

| Output plane | Name | Pixel value |
|---|---|---:|
| 1 | DAPI_001 | 10, unchanged |
| 2 | Signal_001 | 20 − 3 × (20 / 10) = 14 |
| 3 | DAPI_002 | 80, unchanged |
| 4 | Signal_002 | 100 − 9 × (30 / 10) = 73 |

These are constant synthetic planes, not microscopy measurements. The output contains four full resolution 32×32 planes and a 16×16 pyramid level. The CSV rows and OME channel names have the same order.

## Check the two different duplicate cases

```sh
python -m unittest -v
```

The five tests run the actual Backsub command for three layouts:

- **Unique names:** the recommended input; both cycles use their explicitly named background.
- **Repeated DAPI names:** both DAPI rows have an empty `background`. The two DAPI planes stay distinct, and all output pixels equal the unique-name run. This demonstrates 0.5.2 behavior; use unique labels for normal input.
- **Repeated background target:** both signal rows reference the same duplicated `bg_signal` name. The command prints its first-occurrence warning twice. The second signal becomes 91, because it uses the first background's value 3 instead of the second background's value 9.

Tests also check output dtype, pyramid dimensions, exposure values, CSV channel numbers, OME channel count and distinct OME channel IDs. The dependency versions are pinned in `requirements.txt`.

## Apply this to an existing table

1. Preserve every CSV row's position relative to its image plane. The input `channel_number` is not a selector that reorders the image.
2. For repeated DAPI reference rows that are not referenced by another row's `background`, give each a unique label, such as `DAPI_001` and `DAPI_002`. Leave their empty `background` fields empty.
3. If a duplicated name is used as a background target, first identify the intended source row. Give the source rows unique names and update each affected `background` reference explicitly. Renaming the targets alone leaves invalid references.
4. Keep the background rows in the input table even when `remove=TRUE`. Check the output table and OME channel order after processing.

Do not infer an intended background from a duplicate label. This example verifies indexing and exposure-scaled arithmetic on synthetic data; it does not validate acquisition metadata or a particular dataset.

The relevant native behavior is in [`process_markers` and `write_pyramid`](https://github.com/SchapiroLabor/Background_subtraction/blob/main/backsub/background_sub.py). MACSima's staging tool also [leaves the reference marker's background empty and names signal backgrounds by cycle](https://github.com/SchapiroLabor/macsima2mc/blob/main/src/macsima2mc/mc_tools.py).

## Optional coffee

This example is free. If it helped, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`

