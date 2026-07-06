(define (domain smart-garage)

    (:requirements
        :strips
        :negative-preconditions
    )

    (:predicates

        ;; Environment
        (temperature-high)
        (lux-dark)

        ;; Actuator States
        (fan-on)
        (light-on)

        ;; Garage State
        (garage-full)

        ;; Vehicle Events
        (vehicle-waiting-to-enter)
        (vehicle-waiting-to-leave)

        ;; Gate States
        (entrance-gate-open)
        (exit-gate-open)

    )

    ;; ==========================================================
    ;; Fan
    ;; ==========================================================

    (:action turn-on-fan

        :precondition
            (and
                (temperature-high)
                (not (fan-on))
            )

        :effect
            (and
                (fan-on)
            )
    )

    (:action turn-off-fan

        :precondition
            (and
                (fan-on)
                (not (temperature-high))
            )

        :effect
            (and
                (not (fan-on))
            )
    )

    ;; ==========================================================
    ;; Light
    ;; ==========================================================

    (:action turn-on-light

        :precondition
            (and
                (lux-dark)
                (not (light-on))
            )

        :effect
            (and
                (light-on)
            )
    )

    (:action turn-off-light

        :precondition
            (and
                (light-on)
                (not (lux-dark))
            )

        :effect
            (and
                (not (light-on))
            )
    )

    ;; ==========================================================
    ;; Entrance Gate
    ;; ==========================================================

    (:action open-entrance-gate

        :precondition
            (and
                (vehicle-waiting-to-enter)
                (not (garage-full))
                (not (entrance-gate-open))
            )

        :effect
            (and
                (entrance-gate-open)
            )
    )

    (:action close-entrance-gate

        :precondition
            (and
                (entrance-gate-open)
                (not (vehicle-waiting-to-enter))
            )

        :effect
            (and
                (not (entrance-gate-open))
            )
    )

    ;; ==========================================================
    ;; Exit Gate
    ;; ==========================================================

    (:action open-exit-gate

        :precondition
            (and
                (vehicle-waiting-to-leave)
                (not (exit-gate-open))
            )

        :effect
            (and
                (exit-gate-open)
            )
    )

    (:action close-exit-gate

        :precondition
            (and
                (exit-gate-open)
                (not (vehicle-waiting-to-leave))
            )

        :effect
            (and
                (not (exit-gate-open))
            )
    )

)
