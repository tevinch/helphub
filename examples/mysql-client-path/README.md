# Use Homebrew's MySQL client from your shell

`mysql-client` is keg-only: installing it does not add `mysql` to Homebrew's usual `bin` directory. On Apple Silicon, Homebrew normally uses `/opt/homebrew`; an example using `/usr/local` targets the Intel default instead.

First check the installed client and run it by its actual location:

```sh
mysql_client_prefix="$(brew --prefix --installed mysql-client)" &&
  "$mysql_client_prefix/bin/mysql" --version
```

If the formula is not installed, inspect the output of `brew install mysql-client` first. A prefix returned without `--installed` is not proof that installation completed. If the direct executable fails too, keep that error: changing `PATH` cannot repair a failed installation.

When the direct command succeeds, make the client available in the current zsh session:

```sh
export PATH="$(brew --prefix mysql-client)/bin:$PATH"
rehash
command -v mysql
mysql --version
```

For an installation under `/opt/homebrew`, `command -v mysql` should show `/opt/homebrew/opt/mysql-client/bin/mysql`. `mysql --version` prints the client version without connecting to a database.

To keep this in new interactive zsh sessions, add this line once to your existing `~/.zshrc`, preserving the rest of the file, then open a new terminal:

```sh
export PATH="$(brew --prefix mysql-client)/bin:$PATH"
```

`brew info mysql-client` also displays the formula's local PATH instructions. The client package can be used without installing or starting a MySQL server. This PATH entry makes this client take precedence over another `mysql` already on your PATH.

[Original question](https://github.com/orgs/Homebrew/discussions/7178), [keg-only explanation](https://docs.brew.sh/FAQ#what-does-keg-only-mean), [prefix and installed checks](https://docs.brew.sh/Manpage#--prefix---unbrewed---installed-formula-), [client formula](https://formulae.brew.sh/formula/mysql-client).

## Check the shell behavior

With the real Homebrew client already installed, run:

```sh
bash verify.sh
```

The check runs the installed binary directly, verifies missing-command behavior in a clean child shell, adds the native prefix to PATH, and invokes the client twice. It then checks a new interactive zsh with a disposable startup directory. All temporary startup files stay in that directory; your shell profiles are not edited. It also checks a missing formula fails the installed-prefix test. The script neither installs packages nor starts a server.

These are scripted checks. They do not establish a connection to a database or confirmation from the original requester.

## Optional coffee

If this saved you time, a small coffee is welcome and entirely optional. The guide and checks are free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
