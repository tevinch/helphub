# Save a root filesystem from an OCI image with PRoot-Distro

PRoot-Distro 5.10.3 applies the layers of an OCI image and stores the merged root filesystem locally. You can save it as a PRoot-Distro backup or as a plain rootfs tarball. You can prepare either archive before starting a guest session.

## Install the OCI image

Install a local OCI image-layout archive with a fresh container name.

```sh
proot-distro install ./image.oci.tar --name oci-demo
```

For a registry image, pass its image reference in place of `./image.oci.tar`, for example `alpine:3.23`. The archive or registry image needs to include a platform matching your device. PRoot-Distro applies layer deletions and its normal install-time adjustments, including `/etc/hosts` and `/etc/resolv.conf` when the image has an `etc` directory. Both recipes below save this installed filesystem. [Install reference](https://github.com/termux/proot-distro/blob/v5.10.3/README.md#install--install-a-container)

## Save a PRoot-Distro backup

Choose this format to restore the container along with its OCI metadata.

```sh
proot-distro backup oci-demo --output ./oci-demo.backup.tar.gz
tar -tzf ./oci-demo.backup.tar.gz
```

The archive includes `oci-demo/rootfs/` and `oci-demo/manifest.json`. Backup may adjust owner permissions on unreadable files or directories before archiving. Restore replaces a container with the same name. On regular Linux, restore into a fresh data directory:

```sh
restore_data=$(mktemp -d)
XDG_DATA_HOME="$restore_data" proot-distro restore ./oci-demo.backup.tar.gz
```

On Termux, use `proot-distro restore ./oci-demo.backup.tar.gz` on a destination where `oci-demo` is free. [Backup and restore reference](https://github.com/termux/proot-distro/blob/v5.10.3/README.md#backup--archive-a-container)

## Save a plain rootfs tarball

Choose this format when you need the filesystem contents with the top level at `etc/`, `usr/`, and so on. Set `rootfs` to the path for your host.

**Termux**

```sh
rootfs="${TERMUX__PREFIX:-$PREFIX}/var/lib/proot-distro/containers/oci-demo/rootfs"
```

**Regular Linux**

```sh
rootfs="${XDG_DATA_HOME:-$HOME/.local/share}/proot-distro/containers/oci-demo/rootfs"
```

With the guest stopped, archive that directory's contents. Run this from a host directory outside the rootfs. The subshell refuses to overwrite an existing output file.

```sh
(set -C; tar -C "$rootfs" -czf - . > ./oci-demo.rootfs.tar.gz)
tar -tzf ./oci-demo.rootfs.tar.gz
proot-distro install ./oci-demo.rootfs.tar.gz --name oci-demo-plain
```

Use `install` for the plain archive. This format carries filesystem contents only. Use the native backup to carry the original OCI config and manifest. [Storage layout](https://github.com/termux/proot-distro/blob/v5.10.3/README.md#storage-layout)

## Verify the example

With `proot-distro` 5.10.3 and `proot` installed, run `python3 verify.py` on regular Linux ARM64 or x86-64. The verifier creates a small two-layer OCI image from scratch and checks layer replacement, deletion, and symlink preservation. It restores the backup in a fresh data directory, then installs the plain tarball in a separate directory and checks that plain export preserves the source content and file modes. It also checks that repeating the plain export preserves the first archive. This example was verified on Linux ARM64 without starting a container process. The Termux path follows the documented storage layout and was not tested on an Android device.

## Optional coffee

If this saved you time, a coffee is welcome and entirely optional. The example is free to use.

- **USDC / SOL · Solana** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20)** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
