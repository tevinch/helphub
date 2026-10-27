# Custom Lisp definitions in Treemacs

Treemacs gets the entries beneath a file from Emacs' Imenu index. This example adds a **Custom forms** group for named top-level forms such as `(defthis first-example ...)` and `(define-that second-example ...)`, while retaining the existing function and variable groups.

It supports the stock `emacs-lisp-mode` and Common Lisp `lisp-mode`. The source forms are indexed as text and are never evaluated. There is no need to implement or load the example macros.

## Set up

Install Treemacs normally through your Emacs package manager. Save [custom-lisp-tags.el](custom-lisp-tags.el) in your Emacs configuration directory, then add:

```elisp
(load (expand-file-name "custom-lisp-tags.el" user-emacs-directory))
(setq custom-lisp-tags-heads '("defthis" "define-that"))
(custom-lisp-tags-enable)
```

Replace the two strings with the macro names you use. Each supported form starts on its own line, optionally indented, with its head and unquoted symbol name on the same line. The name is the first argument. Comments, strings and forms nested inside another expression are excluded. Quoted names, list-shaped names, reader-escaped names and a name on a separate line need a different matcher.

The setup extends both `lisp-imenu-generic-expression` and Treemacs' separate `treemacs-elisp-imenu-expression`. That second setting matters: Treemacs normally uses its own expression for Elisp rather than the buffer's generic expression. If you already set the Treemacs expression to `nil`, this example keeps that choice and extends the ordinary Lisp expression instead.

The Lisp default is also needed for files you have not opened yet. Treemacs temporarily suppresses major-mode hooks when it first indexes those files, so putting the entire configuration in a mode hook can miss them. Already-open Lisp buffers are updated when you call `custom-lisp-tags-enable`. Calling it again does not add duplicate patterns.

This enables `imenu-auto-rescan` by default, following Treemacs' recommendation for changing source files. Rebuilding an index can take longer in large buffers. Other packages that replace `imenu-create-index-function`, such as a semantic indexer, may require their own configuration; this example does not replace those indexers.

## Use it

1. Open a project containing [sample.el](sample.el) or [sample.lisp](sample.lisp), or your own source file. In Treemacs, add the directory as a project if necessary.
2. Select the filename and press `TAB`. Expand **Custom forms** with `TAB`.
3. Select `first-example` or `second-example` and press `RET` to visit that declaration. The ordinary function still appears under **Functions**.
4. Rename a declaration or add another one, then save the file. In Treemacs, run `M-x treemacs-refresh` and expand the file and **Custom forms** again as needed. Select the new name and press `RET`.

The configuration can run before or after Treemacs loads. It also handles files first indexed directly from Treemacs, without first opening them in an editing buffer.

## Check the complete flow

With Treemacs and its dependencies on your Emacs load path, run from this directory:

```sh
emacs --batch -Q -l check.el
```

`-Q` skips your package initialization. Supply the package directories with `-L`, or use a separate test configuration that adds them to `load-path`; for example:

```sh
emacs --batch -Q -L /path/to/treemacs -L /path/to/dash \
  -L /path/to/s -L /path/to/ace-window -L /path/to/avy \
  -L /path/to/pfuture -L /path/to/hydra -L /path/to/lv \
  -L /path/to/ht -L /path/to/cfrs -L /path/to/posframe -l check.el
```

The check uses temporary source copies and a separate Emacs profile directory. It expands real Treemacs nodes, invokes its `RET` action, checks the selected source buffer and position, then repeats edit/save/refresh/navigation twice. It covers Elisp and Common Lisp, already-open and previously unopened files, excluded comments/strings/nested calls, duplicate setup and exact preservation of the remaining source content.

Verified with Emacs 31.1 and stable Treemacs 3.2 on macOS arm64. These are native scripted Emacs checks; no graphical desktop session or original user's configuration was tested. The same acceptance check fails if the custom configuration is omitted, if the required refresh is omitted, or if the Lisp default for unopened files is omitted. To exercise those controls locally, set `CUSTOM_TAGS_CONTROL` to `no-config`, `no-refresh`, or `opened-only` before running the check. Setting `CUSTOM_TAGS_ELISP_DEFAULT=nil` checks the supported nil-expression setting.

References: [Treemacs tag view](https://github.com/Alexander-Miller/treemacs#tag-view), [Treemacs Elisp expression](https://github.com/Alexander-Miller/treemacs/blob/3.2/src/elisp/treemacs-customization.el), [Emacs Imenu configuration](https://www.gnu.org/software/emacs/manual/html_node/elisp/Imenu.html), [original question](https://github.com/Alexander-Miller/treemacs/issues/1199).

## Optional coffee

This example is free. If it saves you time, a small coffee is welcome and entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
