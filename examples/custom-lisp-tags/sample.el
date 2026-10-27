;;; sample.el --- Navigation fixture -*- lexical-binding: t -*-
(defun ordinary-example () "An existing function." nil)
(defthis first-example (value) value)
(define-that second-example (value) value)

;; (defthis commented-example ())
(defvar sample-text "
(defthis string-example ())
")
(let ()
  (defthis nested-example ()))
