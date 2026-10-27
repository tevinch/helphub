;;; check.el --- Native Treemacs navigation acceptance -*- lexical-binding: t -*-

(require 'cl-lib)
(require 'ert)
(require 'imenu)
(setq user-emacs-directory (make-temp-file "lisp-tags-profile-" t))
(require 'treemacs)
(require 'treemacs-tags)

(defconst custom-tags-check-directory
  (file-name-directory (or load-file-name buffer-file-name)))
(defvar custom-tags-check-hook-files nil)
(defun custom-tags-check-mode-hook ()
  (push buffer-file-name custom-tags-check-hook-files))
(add-hook 'emacs-lisp-mode-hook #'custom-tags-check-mode-hook)
(add-hook 'lisp-mode-hook #'custom-tags-check-mode-hook)
(setq treemacs-persist-file nil
      treemacs-last-error-persist-file nil
      treemacs-no-png-images t
      treemacs-select-when-already-in-treemacs 'stay
      treemacs-show-hidden-files t
      backup-inhibited t
      auto-save-default nil)
(when (equal (getenv "CUSTOM_TAGS_ELISP_DEFAULT") "nil")
  (setq treemacs-elisp-imenu-expression nil))

(defun custom-tags-check-button (path)
  (treemacs-select-window)
  (let ((button (treemacs-find-node path)))
    (unless button
      (princ (format "MISSING %S buffer=%s\n%s\n" path (buffer-name)
                     (buffer-string))))
    (should button)
    (goto-char (treemacs-button-start button))
    button))

(defun custom-tags-check-expand (path)
  (let ((button (custom-tags-check-button path)))
    (when (memq (treemacs-button-get button :state)
                '(root-node-closed dir-node-closed file-node-closed tag-node-closed))
      (treemacs-TAB-action))))

(defun custom-tags-check-leaves (file)
  (custom-tags-check-expand file)
  (custom-tags-check-expand (list file "Custom forms"))
  (let ((buffer (current-buffer)))
    (dolist (name '("first-example" "second-example"))
      (custom-tags-check-button (list file "Custom forms" name)))
    (dolist (name '("commented-example" "string-example" "nested-example"))
      (should-not (treemacs-find-node (list file "Custom forms" name))))
    (with-current-buffer buffer
      (princ (format "TREE %s\n%s\n" (file-name-nondirectory file)
                     (buffer-substring-no-properties (point-min) (point-max)))))))

(defun custom-tags-check-jump (file name)
  (custom-tags-check-button (list file "Custom forms" name))
  (treemacs-RET-action)
  ;; Independent post-command observations: this is the actual selected buffer.
  (should (equal (file-truename buffer-file-name) (file-truename file)))
  (should (looking-at-p (concat "(\\(?:defthis\\|define-that\\) " name "\\_>")))
  (should (= 0 (car (syntax-ppss))))
  (princ (format "JUMP %s %s line=%d\n" (file-name-nondirectory file)
                 name (line-number-at-pos))))

(ert-deftest custom-tags-native-workflow ()
  (let* ((project (file-truename (make-temp-file "lisp-tags-project-" t)))
         (files (cl-loop for extension in '("el" "lisp")
                         append (cl-loop for state in '("open" "unopened")
                                         collect (expand-file-name
                                                  (concat state "." extension) project))))
         (configuration (expand-file-name "custom-lisp-tags.el" custom-tags-check-directory)))
    (cl-loop for file in files
             do (copy-file (expand-file-name
                            (concat "sample." (file-name-extension file))
                            custom-tags-check-directory) file))
    ;; These buffers predate setup; the other two are first visited by Treemacs.
    (dolist (file files)
      (when (string-prefix-p "open." (file-name-nondirectory file))
        (find-file-noselect file)))
    (unless (equal (getenv "CUSTOM_TAGS_CONTROL") "no-config")
      (when (file-exists-p configuration)
        (load configuration nil t)
        (custom-lisp-tags-enable)
        (custom-lisp-tags-enable)
        (should (= 1 (cl-count custom-lisp-tags--pattern lisp-imenu-generic-expression
                               :test #'equal)))
        (when treemacs-elisp-imenu-expression
          (should (= 1 (cl-count custom-lisp-tags--pattern treemacs-elisp-imenu-expression
                                 :test #'equal))))))
    (when (equal (getenv "CUSTOM_TAGS_CONTROL") "opened-only")
      ;; Preserve configured existing buffers; omit the default copied into
      ;; newly visited Common Lisp buffers.  A hook-only recipe has this gap.
      (setq lisp-imenu-generic-expression
            (remove custom-lisp-tags--pattern lisp-imenu-generic-expression)))
    (should (eq 'success (car (treemacs-do-add-project-to-workspace project "Lisp sample"))))
    (treemacs-select-window)
    (custom-tags-check-expand project)
    (dolist (file files)
      (when (string-prefix-p "unopened." (file-name-nondirectory file))
        (should-not (get-file-buffer file)))
      (custom-tags-check-leaves file)
      (if (string-prefix-p "unopened." (file-name-nondirectory file))
          (progn
            (should-not (get-file-buffer file))
            (should-not (member file custom-tags-check-hook-files))
            (princ (format "UNOPENED-TAGS-WITHOUT-HOOK %s\n" (file-name-nondirectory file))))
        (should (member file custom-tags-check-hook-files)))
      ;; Real ordinary-function node must also remain visible and navigable.
      (custom-tags-check-expand (list file "Functions"))
      (custom-tags-check-button (list file "Functions" "ordinary-example"))
      (treemacs-RET-action)
      (should (equal (file-truename buffer-file-name) (file-truename file)))
      (should (looking-at-p "(defun ordinary-example"))
      (dolist (name '("first-example" "second-example"))
        (custom-tags-check-jump file name))
      ;; Repeated edit/save/refresh/navigation, including adding another entry.
      (dotimes (iteration 2)
        (with-current-buffer (find-file-noselect file)
          (goto-char (point-min))
          (search-forward (if (= iteration 0) "first-example" "renamed-example"))
          (replace-match (if (= iteration 0) "renamed-example" "final-example") t t)
          (when (= iteration 0)
            (goto-char (point-max))
            (insert "\n(defthis added-example (value) value)\n"))
          (save-buffer))
        (custom-tags-check-button file)
        (unless (equal (getenv "CUSTOM_TAGS_CONTROL") "no-refresh")
          (treemacs-refresh))
        (custom-tags-check-expand file)
        (custom-tags-check-expand (list file "Custom forms"))
        (should-not (treemacs-find-node
                     (list file "Custom forms"
                           (if (= iteration 0) "first-example" "renamed-example"))))
        (custom-tags-check-jump file (if (= iteration 0) "renamed-example" "final-example"))
        (custom-tags-check-jump file "added-example")
        (let ((expected
               (with-temp-buffer
                 (insert-file-contents
                  (expand-file-name (concat "sample." (file-name-extension file))
                                    custom-tags-check-directory))
                 (goto-char (point-min))
                 (search-forward "first-example")
                 (replace-match (if (= iteration 0) "renamed-example" "final-example") t t)
                 (goto-char (point-max))
                 (insert "\n(defthis added-example (value) value)\n")
                 (buffer-string))))
          (with-current-buffer (find-file-noselect file)
            (should (equal expected (buffer-string)))))))
    (princ (format "PASS Emacs=%s Treemacs=%s files=%d\n"
                   emacs-version treemacs-version (length files)))))

(ert-run-tests-batch-and-exit)
