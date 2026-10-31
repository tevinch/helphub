# Sans 12 with CopperSpice 2.1.0 on Linux

Use a per-application stylesheet to request `Sans` at 12 points while leaving the family name available for Linux Fontconfig to resolve.

Save [sans12.qss](sans12.qss):

```css
* {
    font-family: "Sans";
    font-size: 12pt;
}
```

Start the application with one final equals-form argument:

```sh
"/path/to/application" -stylesheet="/absolute/path/to/sans12.qss"
```

Keep this as the application's **only argument**, in the final position shown. Do not append it to a command with other application options or filenames. In the CopperSpice 2.1.0 Linux inspection application, the separate `-stylesheet path` form was ignored. The final equals form shown above passed the included native check.

Use a quoted absolute stylesheet path, particularly in a launcher or when the path contains spaces. `12pt` means twelve points; `12px` requests pixels. Keep `Sans` symbolic and retain your existing Fontconfig configuration.

The application must pass this argument to `QApplication`, and its own styling can override rules. This is a per-application setting. The unnamed original application, additional startup arguments, Gentoo, global qtct configuration and Qt/Kvantum plugin compatibility have not been verified. If the application requires other launch arguments, identify the application and version before adapting this command. CopperSpice also documents limitations with custom `QStyle` subclasses.

See the [QApplication command-line options](https://www.copperspice.com/docs/cs_api/class_qapplication.html), [stylesheet properties and units](https://www.copperspice.com/docs/cs_api/stylesheet-reference.html) and [stylesheet overview](https://www.copperspice.com/docs/cs_api/stylesheet-c.html).

## Optional reproducibility check

Using the stylesheet in an existing application does not require this check, a compiler or the SDK download below.

The small consumer forwards its arguments unchanged and reports six ordinary widgets after they are shown and polished. It does not set their fonts in C++.

Use Ubuntu 24.04 x86_64 with a C++20 compiler, CMake 3.20+, Python 3.11+, curl, `sha256sum`, Xvfb, xauth, Fontconfig tools and the SDK's native dependencies, with at least 1 GiB free. This diagnostic matrix requires installed DejaVu Sans and Liberation Sans, and a default `Sans` match different from Liberation Sans so its omitted-configuration control is meaningful. The reference CI environment includes 20 additional official Ubuntu dependency packages. The check does not install packages; missing prerequisites stop it. See CopperSpice's [Unix requirements](https://www.copperspice.com/docs/cs_overview/unix-requirements.html).

From this example directory, obtain the pinned official 46,307,026-byte SDK archive:

```sh
curl --disable --fail --location --proto '=https' --proto-redir '=https' \
  --output copperspice-2.1.0-ubuntu24.04-x64.tar.bz2 \
  https://github.com/copperspice/copperspice/releases/download/cs-2.1.0/copperspice-2.1.0-ubuntu24.04-x64.tar.bz2
printf '%s  %s\n' \
  c138fbc4bc2c21de5aa5ce63d2ced40661373ed3d857f4605a315981f23d5641 \
  copperspice-2.1.0-ubuntu24.04-x64.tar.bz2 | sha256sum --check -
mkdir check-work
python3 verify.py \
  --sdk-archive "$PWD/copperspice-2.1.0-ubuntu24.04-x64.tar.bz2" \
  --work-parent "$PWD/check-work"
```

**Verified:** [this Ubuntu 24.04/XCB run](https://github.com/tevinch/helphub/actions/runs/41195643253) passed all thirteen cases using CopperSpice 2.1.0 and [these exact source files](https://github.com/tevinch/helphub/tree/6a8d648fe02bb942a0b0c89969a01e80cdaf9daf/.github/checks/application-fonts). One unchanged executable reported six visible, polished widgets requesting symbolic `Sans` at 12pt, with pixel-size unset and contents preserved. Independent Fontconfig A/B/A checks and the widgets' matched families followed DejaVu Sans → Liberation Sans → DejaVu Sans. The matched point size was 12.24 after whole-pixel rounding; the requested size remained exactly 12pt.

The omitted, separated, nonfinal, removed-file, missing-file and 12px controls were rejected as expected. A process-local `QT_STYLE_OVERRIDE=Windows` launch independently reported the available Windows style; the same setting with the final stylesheet argument passed the font checks.

Example source is available under the [MIT license](LICENSE).

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
