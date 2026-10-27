;;; Common Lisp navigation fixture; no evaluation is needed.
(defun ordinary-example () nil)
(defthis first-example (value) value)
(define-that second-example (value) value)

;; (defthis commented-example ())
(defparameter *sample-text* "
(defthis string-example ())
")
(let ()
  (defthis nested-example ()))
