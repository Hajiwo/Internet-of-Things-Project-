(define (problem smart-garage-problem)
  (:domain smart-garage)
  (:init
    (lux-dark)
  )
  (:goal (and
    (not (fan-on))
    (light-on)
    (not (entrance-gate-open))
    (not (exit-gate-open))
  ))
)