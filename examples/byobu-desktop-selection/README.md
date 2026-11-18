# Copy from Byobu into another desktop program

For Byobu's **tmux backend**, turn mouse capture off to let Xfce Terminal handle normal text selection. Then use the terminal's **Copy** command before pasting into another program. Byobu's own copy buffer and the desktop clipboard serve different operations.

This recipe addresses the [Xfce/X11 selection question](https://github.com/dustinkirkland/byobu/issues/182). The question does not specify a backend or version; it is not a confirmed diagnosis of that particular machine.

## Apply the setting

Run these inside a shell in your Byobu session. First check that `TMUX` is set:

```sh
test -n "${TMUX:-}" && printf 'tmux backend\n'
```

If that prints nothing, check the backend before using this recipe. On the tmux backend:

```sh
tmux set-option -g mouse off
tmux show-options -gqv mouse
```

The second command should print `off`. This changes the current tmux server immediately and affects its other sessions too. Mouse actions such as tmux pane selection and mouse-driven copy mode are disabled.

1. Print or locate a short line of text in the pane.
2. Drag across it normally in Xfce Terminal.
3. Choose **Edit → Copy**, normally **Ctrl+Shift+C**.
4. Switch to another program and choose **Paste**. In a second Xfce Terminal, use **Edit → Paste**, normally **Ctrl+Shift+V**.
5. Repeat with a different line to check that a fresh selection replaces the previous one.

X11 also has a separate selection used by middle-click. Explicit **Copy**, followed by ordinary **Paste**, checks the clipboard used by desktop applications.

## Keep it for future sessions

From inside Byobu, locate its actual configuration directory:

```sh
printf '%s\n' "$BYOBU_CONFIG_DIR/.tmux.conf"
```

Open that file, retain its existing contents, and add this final line:

```tmux
set -g mouse off
```

Byobu loads this file after its supplied profile and key bindings. The location may be `~/.byobu/.tmux.conf` or an XDG configuration directory, so use the exported path. The immediate command above handles the running server; the file handles fresh Byobu server startup. Keep ongoing work running.

**Alt+F12** is Byobu's mouse toggle. Using it later can change the mouse setting again. Check the actual value with `tmux show-options -gqv mouse` if selection changes unexpectedly.

If mouse is already `off` and selection still fails, include `byobu --version`, `xfce4-terminal --version`, the backend, and whether normal selection works outside Byobu when asking for further help. An application inside a pane may have its own mouse handling.

## Check status

**Complete native desktop validation is pending.** The [recorded run](https://github.com/tevinch/helphub/actions/runs/44365282918) completed first and repeated clipboard transfers into a second terminal program. Its fresh-server check stopped before the persistence transfer, which has not passed yet. No original-requester confirmation is claimed.

The inspectable [verification script](verify.py) supports only the accompanying fresh GitHub-hosted Ubuntu 24.04 workflow. Before starting D-Bus, Xvfb, the window manager or Python, that workflow clears inherited session pointers and creates private HOME and XDG directories. The script checks the hosted-runner context, profile paths, owned Xvfb process and private D-Bus process ancestry before importing AT-SPI or sending desktop input. These are checks against accidental use of an existing session, not a security boundary against a deliberately altered environment. It uses distribution packages, records their actual versions and targets an explicit private tmux socket; Ubuntu's Byobu package differs from the current upstream release.

The check requires real mouse dragging in Xfce Terminal, explicit clipboard copy, and paste into a second terminal program that records its received input. It also requires a mouse-on negative control, a different second selection, retained source and recipient content, an unchanged separate file, and a fresh Byobu server loading the persistent override. The separate file is checked before teardown and after the fresh-server transfer. It never inserts the expected source text directly into the clipboard or recipient. A config-only check does not establish clipboard success.

Sources: [Byobu 7.23 profile load order](https://github.com/dustinkirkland/byobu/blob/7.23/usr/share/byobu/profiles/tmuxrc), [Byobu mouse key binding](https://github.com/dustinkirkland/byobu/blob/7.23/usr/share/doc/byobu/help.tmux.txt), [Ubuntu Byobu packages](https://packages.ubuntu.com/byobu), [Xfce Terminal selection and paste](https://docs.xfce.org/apps/xfce4-terminal/4.20/usage#working_with_the_contents_of_terminal_windows).

## Optional coffee

If this example saved you some time, an entirely optional coffee is appreciated. The guide and checks are free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
