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
