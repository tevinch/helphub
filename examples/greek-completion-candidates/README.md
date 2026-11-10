# Keep accented Greek candidates while typing in Neovim

For the Greek prefix `λογι`, the native completion-item field `equal = 1` keeps a returned candidate such as `λογία` selectable while typing narrows a cached list from `λογ` to `λογι`.

Add it to the `convert` option passed to `vim.lsp.completion.enable()` for the affected client. Inside your existing `LspAttach` callback:

```lua
local client = vim.lsp.get_client_by_id(client_id)
local options = {
  autotrigger = true,
  -- Retain your existing cmp and convert fields here, if any.
}

if client and client.name == 'dialogos-lua' then
  local previous_convert = options.convert
  options.convert = function(item)
    local converted = previous_convert and previous_convert(item) or {}
    return vim.tbl_extend('force', converted, { equal = 1 })
  end
end

vim.lsp.completion.enable(true, client_id, event.buf, options)
```

Use your current client's name in the condition. Retain your current `autotrigger` value and other options. This composes with an existing converter and leaves its display fields, the original LSP item and your comparator intact. Register the changed callback before attachment, or restart the language server afterward. It does not change `completeopt`.

This targets native filtering of an existing completion list. It does not force another server request while a complete list remains open, so candidates can stay visible as you keep typing. The server's `isIncomplete` flag still determines whether continued typing requests updated results. Your existing completion ordering still applies; response array order is not guaranteed.

This is not a universal accent-matching switch. On 0.12.6 an earlier Lua filter can discard items before `convert` runs when the prefix contains ASCII letters or digits. For example, this configuration does not make `cafe` match a returned `café` item. Other completion plugins can also apply their own matching.

The [0.12.6 completion-item documentation](https://github.com/neovim/neovim/blob/v0.12.6/runtime/doc/insert.txt#L1228-L1230) defines `equal = 1`; the [LSP documentation](https://github.com/neovim/neovim/blob/v0.12.6/runtime/doc/lsp.txt#L2185-L2196) describes `convert`.

The included check uses real Neovim 0.12.6 and a local stdio language server. It verifies fresh and cached results, actual matching popup items, Unicode acceptance, repeated editing, save/reopen, callback preservation and the ASCII limitation. A fresh request at `λογι` already worked without this option in the fixture; the omission check fails specifically during cached narrowing.

From this example directory:

```sh
python -m pip install pynvim==0.6.0
python tests/verify.py /path/to/nvim
python tests/verify.py /path/to/nvim --omit-conversion
```

The first check should pass. The omission check should exit with failure when `λογία` disappears from the matching popup items after typing `ι`.


## Optional coffee

This example is free. If it helped, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
