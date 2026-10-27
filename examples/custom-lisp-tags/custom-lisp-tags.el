;;; custom-lisp-tags.el --- Custom top-level Lisp entries -*- lexical-binding: t -*-

;; This example is free to use under the MIT license; see LICENSE.

(require 'imenu)
(require 'lisp-mode)
(defvar treemacs-elisp-imenu-expression)

(defvar custom-lisp-tags-heads '("defthis" "define-that")
  "Declaration heads whose first argument is an unquoted symbol name.
Change this list to the actual macro names used in your source files.")

(defun custom-lisp-tags--search-backward ()
  "Find the previous chosen declaration at syntactic top level.
Set match group 1 to its unquoted symbol name, as required by Imenu.
This only reads source text; it does not evaluate any form."
  (let ((regexp (concat "^[ \t]*(" (regexp-opt custom-lisp-tags-heads)
                        "\\_>[ \t]+\\(\\(?:\\sw\\|\\s_\\)+\\)")))
    (catch 'found
      (while (re-search-backward regexp nil t)
        (let ((state (save-excursion
                       (save-match-data (syntax-ppss (match-beginning 0))))))
          (when (and (= 0 (car state)) (not (nth 8 state)))
            (throw 'found t))))
      nil)))

(defconst custom-lisp-tags--pattern
  '("Custom forms" custom-lisp-tags--search-backward 1))

(defun custom-lisp-tags-enable ()
  "Add custom declarations to Lisp Imenu and Treemacs file tags.
Keep the existing expressions.  Update already-open Lisp buffers too.
Enable Imenu rescanning, as recommended by Treemacs for changing files."
  ;; `lisp-mode-variables' copies this into new Common Lisp / Elisp buffers.
  ;; Unlike a mode hook, that initialization also runs when Treemacs first
  ;; opens an unvisited file while temporarily suppressing mode hooks.
  (add-to-list 'lisp-imenu-generic-expression custom-lisp-tags--pattern t)
  (setq-default imenu-auto-rescan t)
  ;; Treemacs uses a separate, more detailed expression for Emacs Lisp.
  ;; Leave nil alone: nil explicitly tells it to use the buffer's expression.
  (with-eval-after-load 'treemacs
    (when treemacs-elisp-imenu-expression
      (add-to-list 'treemacs-elisp-imenu-expression custom-lisp-tags--pattern t)))
  (dolist (buffer (buffer-list))
    (with-current-buffer buffer
      (when (derived-mode-p 'emacs-lisp-mode 'lisp-mode)
        (setq-local imenu-generic-expression
                    (if (member custom-lisp-tags--pattern imenu-generic-expression)
                        imenu-generic-expression
                      (append imenu-generic-expression
                              (list custom-lisp-tags--pattern))))
        (setq-local imenu-auto-rescan t)))))

(provide 'custom-lisp-tags)
;;; custom-lisp-tags.el ends here
