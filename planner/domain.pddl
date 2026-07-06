(define (domain smart-garage)
  (:requirements :strips :negative-preconditions)

  (:predicates
    (temperature-high)
    (lux-dark)
    (fan-on)
    (light-on)
    (garage-full)
    (vehicle-waiting-to-enter)
    (vehicle-waiting-to-leave)
    (entrance-gate-open)
    (exit-gate-open)
  )

  (:action turn-on-fan
    :precondition (and
      (temperature-high)
      (not (fan-on))
    )
    :effect (and
      (fan-on)
    )
  )

  (:action turn-off-fan
    :precondition (and
      (fan-on)
      (not (temperature-high))
    )
    :effect (and
      (not (fan-on))
    )
  )

  (:action turn-on-light
    :precondition (and
      (lux-dark)
      (not (light-on))
    )
    :effect (and
      (light-on)
    )
  )

  (:action turn-off-light
    :precondition (and
      (light-on)
      (not (lux-dark))
    )
    :effect (and
      (not (light-on))
    )
  )

  (:action open-entrance-gate
    :precondition (and
      (vehicle-waiting-to-enter)
      (not (garage-full))
      (not (entrance-gate-open))
    )
    :effect (and
      (entrance-gate-open)
    )
  )

  (:action close-entrance-gate
    :precondition (and
      (entrance-gate-open)
      (not (vehicle-waiting-to-enter))
    )
    :effect (and
      (not (entrance-gate-open))
    )
  )

  (:action open-exit-gate
    :precondition (and
      (vehicle-waiting-to-leave)
      (not (exit-gate-open))
    )
    :effect (and
      (exit-gate-open)
    )
  )

  (:action close-exit-gate
    :precondition (and
      (exit-gate-open)
      (not (vehicle-waiting-to-leave))
    )
    :effect (and
      (not (exit-gate-open))
    )
  )
)

