# Larger WhiteSur GTK3 window controls

**Native verification is pending.** This draft has not yet passed the real Gedit/xfwm4 checks described below.

Gedit draws its GTK3 headerbar controls itself. The WhiteSur **xfwm4** normal, hdpi and xhdpi variants change window-manager decorations, so selecting a larger xfwm4 variant does not resize these Gedit controls.

For GTK3 applications using WhiteSur's native headerbar controls, [controls.css](controls.css) increases both the clickable allocation and the painted artwork from 16 to 24 logical pixels. It keeps WhiteSur's own close, minimize, maximize and restore images and their state rules. Ordinary buttons, text and window-manager decorations are outside the selector.

## Apply the setting

Keep the base **WhiteSur-Dark-orange** GTK application theme selected in Xfce Appearance. Your preferred **WhiteSur-Dark-orange-hdpi** window-manager theme can stay selected in Window Manager. The hdpi directory contains xfwm4 assets; it is not the GTK application theme.

Open `~/.config/gtk-3.0/gtk.css` in a text editor, or `$XDG_CONFIG_HOME/gtk-3.0/gtk.css` if you set that variable. Create the directory/file if needed, keep a backup of an existing file, and **append** this block:

```css
/* Larger WhiteSur GTK3 headerbar controls: begin */
headerbar button.titlebutton.close,
headerbar button.titlebutton.minimize,
headerbar button.titlebutton.maximize {
  min-width: 24px;
  min-height: 24px;
  padding: 0;
  background-size: 24px 24px;
}
/* Larger WhiteSur GTK3 headerbar controls: end */
```

Save your work and fully close and reopen Gedit. A new window in an already running process may keep the previous CSS. Use the same value in the four size fields if you prefer another size.

Changing only `min-width`/`min-height` enlarges the target while leaving the theme's painted control at 16px. Changing only `background-size` can clip the larger artwork inside the old target. Both parts are needed.

This setting applies to native **GTK3** headerbar titlebuttons for this theme. GTK4/libadwaita, browser-drawn controls and sandboxed applications with their own configuration are separate cases. It does not change display scaling or replace application-specific accessibility settings.

## Undo

Remove only the block between the two comments, save the file, and fully close and reopen the application. Keep any other CSS rules you already had. The controls return to the theme's original size.

## Preview and native checks

On a GTK3 Linux desktop with PyGObject installed, `python3 preview.py` opens a small native headerbar/text preview. `python3 preview.py --ssd` uses the window manager's titlebar for comparison. Both windows are ordinary throwaway examples.

[CHECKS.md](CHECKS.md) describes the native Gedit/xfwm4 check and its limits. Its runner changes window-manager settings in an isolated D-Bus/X11 session; use the accompanying disposable workflow rather than running that checker against your everyday desktop.

The official [WhiteSur installer](https://github.com/vinceliuice/WhiteSur-gtk-theme/blob/99247ecd219bdc1c7409baff062b4aafcf1102a7/libs/lib-install.sh) installs the xfwm4 variants separately. Its [GTK3 control rules](https://github.com/vinceliuice/WhiteSur-gtk-theme/blob/99247ecd219bdc1c7409baff062b4aafcf1102a7/src/sass/gtk/_common-3.0.scss#L4417) set the original 16px dimensions. GTK documents [user CSS loading](https://docs.gtk.org/gtk3/class.CssProvider.html) and [GtkHeaderBar controls](https://docs.gtk.org/gtk3/class.HeaderBar.html); Xfce documents [window-manager decoration settings](https://docs.xfce.org/xfce/xfwm4/preferences#style).

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
