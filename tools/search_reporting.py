"""Small reporting helpers for model search modules."""


def is_verbose(config_model=None, config_solver=None):
    """Return whether search functions should print progress messages."""

    config_model = config_model or {}
    config_solver = config_solver or {}
    return bool(config_model.get("verbose", config_solver.get("verbose", True)))


def log(message, config_model=None, config_solver=None):
    """Print a message unless verbose output is disabled."""

    if is_verbose(config_model, config_solver):
        print(message)


def log_search_summary(title, solutions, config_model, config_solver, hidden_keys=None):
    """Print a common model/solver summary."""

    hidden_keys = set(hidden_keys or ())
    log(f"====== {title} ======", config_model, config_solver)
    log(f"--- Found {len(solutions)} solution(s) ---", config_model, config_solver)
    for key, value in {**config_model, **config_solver}.items():
        if key not in hidden_keys:
            log(f"--- {key} ---: {value}", config_model, config_solver)
