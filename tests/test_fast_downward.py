from planner.fast_downward import FastDownward


def test_build_command_includes_plan_file_and_search() -> None:
    backend = FastDownward("fast-downward.py")

    command = backend.build_command("domain.pddl", "problem.pddl", "sas_plan")

    assert command == [
        "fast-downward.py",
        "--plan-file",
        "sas_plan",
        "domain.pddl",
        "problem.pddl",
        "--search",
        "astar(lmcut())",
    ]
