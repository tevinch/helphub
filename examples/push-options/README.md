# Push options in Lazygit

Use a custom command when you want `ci.skip` on a particular push. The normal push action keeps its usual behavior.

Add this entry to `customCommands` in your Lazygit `config.yml` (append to the existing list if you already have one):

```yaml
customCommands:
  - description: 'Push with ci.skip'
    context: 'global'
    command: 'git push --push-option=ci.skip'
    output: 'popup'
    outputTitle: 'Push with ci.skip'
```

Reopen Lazygit, press `?`, type `ci.skip` to filter the menu, and press Enter on **Push with ci.skip**. The result appears in a popup. This keyless command is available from every panel; it uses the same destination and ref selection as your normal `git push`. Set the branch's upstream first if needed. To locate your configuration directory, run `lazygit --print-config-dir`.

The [native custom-command documentation](https://github.com/jesseduffield/lazygit/blob/v0.66.2/docs/Custom_Command_Keybindings.md) describes keyless menu entries and optional keybindings. Git's long `--push-option` form works from Git 2.10 onward. [GitLab documents `ci.skip`](https://docs.gitlab.com/topics/git/commit/#push-options-for-gitlab-cicd) for branch pipelines; it does not skip merge request pipelines or external CI integrations. The receiver must support push options. If it does not, Git reports that error and the push fails.

## Try it with a local receiver

This creates a new local working repository and bare receiver. It does not contact GitLab. It requires Python 3, Git and Lazygit. Choose a directory that does not exist:

```sh
python3 setup_demo.py /tmp/push-options-demo
lazygit --path /tmp/push-options-demo/work --use-config-file "$PWD/config.yml"
```

Use `?` → type `ci.skip` → Enter. Close the result popup with Escape. Then inspect the receiver:

```sh
cat /tmp/push-options-demo/receiver.git/push-receipts.txt
git -C /tmp/push-options-demo/work rev-parse HEAD
git -C /tmp/push-options-demo/receiver.git rev-parse main
```

The receipt starts with `count=1` and `option0=ci.skip`, followed by the old commit, new commit and `refs/heads/main`. The two final commit hashes must match. You can make another commit and repeat. The local hook only records the received option; it does not implement a CI service.

Checked with Lazygit 0.66.2 and Git 2.39.3 on macOS: two custom pushes delivered `ci.skip` and updated the receiver; a subsequent normal `P` push delivered no options. The other branch and existing file stayed unchanged. Omitting the option still pushed but failed the receipt check; omitting the custom command removed it from the native menu. A receiver without push-option support displayed Git's error and kept its previous ref. These were scripted terminal checks. A live GitLab pipeline, the requester's repository and other platforms were not tested.

## Optional coffee

This example is free. If it saves you time, a coffee is entirely optional and appreciated.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
