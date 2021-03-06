(define (test value expected)
  (cond ((not (equal? value expected))
	 (begin (display "Failed!") (newline)
		(display "expected ")
		(display expected)
		(display " but got ")
		(display value) (newline)))
	(else (display "ok")
	      (newline))))

(define a 1)
(define b 2)
(define c 3)
(define p1 (cons a b))
(define p2 (cons a a))
(define p3 (list a b c))
(define p4 (append '(a b c) p3))

;;(test (eq? p1)