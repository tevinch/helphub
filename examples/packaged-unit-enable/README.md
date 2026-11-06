# Enable a packaged Hjem user unit

Keep the service supplied by a package and add its enable link declaratively:

```nix
{pkgs, ...}: {
  hjem.users.alice = {config, ...}: {
    systemd.packages = [pkgs.syncthing];

    xdg.config.files."systemd/user/default.target.wants/syncthing.service".source =
      config.xdg.config.files."systemd/user/syncthing.service".source;
  };
}
```

Replace `alice` with your configured user. Keep your existing Hjem import and
other settings. Remove the attempted empty `systemd.services.syncthing`
declaration, because it replaces the package-provided service. Rebuild using
your normal NixOS configuration workflow.

The wants link and the main unit both refer to the imported package's original
service file. The link target is still an absolute store path, but Hjem manages
it and computes it again when the package changes. You do not paste a particular
generation's `/nix/store/...` path into your configuration or run `systemctl
enable` separately.

For a reusable local configuration file, [enable-unit.nix](enable-unit.nix)
contains just that wants-link declaration. Import it inside your Hjem user
module, alongside `systemd.packages = [pkgs.syncthing]`.

## Why the two earlier configurations behave differently

At Hjem revision
[`8408642`](https://github.com/feel-co/hjem/blob/8408642aa3035135fa6d70269dc93e0814e2a4f6/modules/nixos/systemd.nix),
`systemd.packages` imports unit files from the package's `etc/systemd/user`
and `lib/systemd/user` directories. It deliberately skips `.wants` directories.
The presence of `[Install] WantedBy=default.target` in a unit is also distinct
from creating its enable link.

The same module generates units declared through `systemd.services` and gives
them precedence over package-provided files. Setting only
`systemd.services.syncthing.wantedBy` therefore defines a new unit; it does not
augment the service imported through `systemd.packages`.

The solution uses Hjem's documented
[`xdg.config.files` source option](https://hjem.feel-co.org/options.html)
for the extra dependency link. It does not copy the service body or define a
replacement service.

## Check the result

After the rebuild, both paths should resolve to the same package service:

```sh
readlink ~/.config/systemd/user/syncthing.service
readlink ~/.config/systemd/user/default.target.wants/syncthing.service
systemctl --user cat syncthing.service
systemctl --user is-enabled syncthing.service
```

The next fresh user-manager startup should start the service through
`default.target`. For the already running session, reload the unit definitions
and start the service explicitly if you want it now:

```sh
systemctl --user daemon-reload
systemctl --user start syncthing.service
systemctl --user status syncthing.service
```

An enable link does not itself restart an already active target. No lingering
setting is needed for this recipe; lingering is a separate choice about running
user services while logged out.

If Hjem reports an unmanaged file conflict, inspect that existing link and your
configuration before changing it. This example leaves Hjem's overwrite behavior
at its default and does not remove existing user files for you.

## Verification scope

The [native check passed](https://github.com/tevinch/helphub/actions/runs/42282200094)
at [source `05e1396`](https://github.com/tevinch/helphub/commit/05e139628ece2ef491258053044154f57b03f39c).

The check uses Hjem `8408642`, Nixpkgs revision
`c56a87d8e41ce69bd2af57eb35dcc117a9dfca33` from the stable `nixos-26.05`
channel, and Nix 2.35.4 on Ubuntu 24.04. Hjem currently has no tagged releases;
the exact revision is pinned without calling it a stable Hjem release.

The test package contains a harmless service named `syncthing.service` that only
writes a marker. **It does not contain or run Syncthing.** The check evaluates
the real Hjem NixOS module, builds its actual activation and state-update
scripts, then runs them for a new disposable user. A fresh real systemd user
manager must start that service without an explicit service-start command.
The run preserved the user's home mode `750` and unrelated content. It read
files as their owner and used the evaluated job scripts and executable path,
including `nix-store`; the state-update garbage-collection roots were required.

All four stages passed: package version 1 startup, a changed package version 2,
repeated activation, and a package-only control with the wants line omitted.
The control retained the imported unit while leaving it inactive and producing
no marker. A change that omits the recipe cannot pass the positive startup checks.

Run only in an ephemeral Linux environment with Nix, systemd and passwordless
sudo, such as the supplied CI workflow:

```sh
bash tests/verify.sh
```

This is a software-operated module and user-manager check. It does not verify
the requester's machine, a NixOS boot or PAM login, every Hjem revision, or
Syncthing's application configuration and synchronization. The requester's
installed Hjem version was not provided. The service's own prerequisites and
configuration still apply.

References: [original question](https://github.com/feel-co/hjem/discussions/206),
[Hjem file management guide](https://hjem.feel-co.org/),
[systemd unit dependencies](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html),
[Nix downloads](https://nixos.org/download/).

## Optional coffee

This example is free. If it saves you time, a small coffee is welcome and entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
