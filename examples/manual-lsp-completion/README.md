# Request LSP completion manually in Neovim 0.12

On Neovim 0.12.6, use `vim.lsp.completion.get()`. `vim.lsp.completion.trigger()` is unavailable.

Register this before starting your language servers, or replace your existing `LspAttach` completion callback:

```lua
vim.api.nvim_create_autocmd('LspAttach', {
  callback = function(event)
    local client = vim.lsp.get_client_by_id(event.data.client_id)
    if not client or not client:supports_method('textDocument/completion') then
      return
    end

    vim.lsp.completion.enable(true, client.id, event.buf, { autotrigger = false })
    vim.keymap.set('i', '<C-e>', function()
      vim.lsp.completion.get()
    end, { buffer = event.buf, desc = 'Request LSP completion' })
  end,
})
```

In an attached buffer, enter Insert mode, type a prefix, then press Ctrl-E. Use Ctrl-N/Ctrl-P to select a candidate and Ctrl-Y to accept it. This mapping replaces Insert-mode Ctrl-E in that buffer. Typing alone does not request completions through this configuration.

The language server must advertise `textDocument/completion`. Existing completion plugins can add their own automatic behavior; this snippet does not disable them. Restart the language server after changing the callback so `LspAttach` runs again.

The built-in alternative is Ctrl-X followed by Ctrl-O when `omnifunc` is `v:lua.vim.lsp.omnifunc`. See the [pinned 0.12.6 documentation](https://github.com/neovim/neovim/blob/v0.12.6/runtime/doc/lsp.txt#L2198-L2211) and `:help vim.lsp.completion.get()`.

The included check runs real Neovim 0.12.6 through its embedded interface with an attached UI and a small local stdio language server. It exercises keypresses, popup selection, repeated completion, continued editing, save/reopen, and buffers without completion support.

From this example directory:

```sh
python -m pip install pynvim==0.6.0
python tests/verify.py /path/to/nvim
```

`--variant old` checks the removed `trigger()` call; `--variant disabled` omits completion registration. Both are expected to exit with failure because the completion operation cannot finish.


## Optional coffee

This example is free. If it helped, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
