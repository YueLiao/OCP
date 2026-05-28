"""
This module provides tools for solving MILP/SAT models. Supports multiple solvers and configurations.
    - MILP solvers: Gurobi, SCIP, OR-Tools
    - SAT solvers: PySAT, OR-Tools
"""
from importlib import import_module
from importlib.util import find_spec
import time

from tools.resource_monitor import RuntimeResourceMonitor
from tools.search_reporting import log


gurobipy_import = find_spec("gurobipy") is not None
scip_import = find_spec("pyscipopt") is not None
ortools_import = (
    find_spec("ortools") is not None and find_spec("ortoolslpparser") is not None
)
pysat_import = find_spec("pysat") is not None


def _load_gurobi():
    try:
        return import_module("gurobipy")
    except ImportError:
        return None


def _load_scip_model():
    try:
        return import_module("pyscipopt").Model
    except ImportError:
        return None


def _load_pysat():
    try:
        return import_module("pysat.formula").CNF, import_module("pysat.solvers").Solver
    except ImportError:
        return None, None


def solve_milp(filename, config_solver=None):
    """
    Solve a MILP model.

    Parameters:
        filename (str): Path to the MILP model file.
        config_solver (dict):
            - solver: solver name (e.g, "GUROBI", "SCIP").
            - solution_number: The number of solutions to find (default: 1).

    Returns:
            A list of solutions. Each solution is represented as a dictionary mapping variable names to their values.
    """

    config_solver = config_solver or {}
    solver = config_solver.get("solver", "DEFAULT")
    log(f"[INFO] Solving MILP model with settings: {config_solver}", config_solver=config_solver)
    monitor = RuntimeResourceMonitor(interval=0.2)
    monitor.start()
    time_start = time.time()
    try:
        if solver.upper() in ["GUROBI", "DEFAULT"]:
            return solve_milp_gurobi(filename, config_solver)
        elif solver.upper() == "SCIP":
            return solve_milp_scip(filename, config_solver)
        else:
            raise ValueError(f"[ERROR] Unsupported solver: '{solver}'. Supported: 'GUROBI' (DEFAULT), 'SCIP'.")
    finally:
        config_solver["resource_usage"] = monitor.stop()
        config_solver["solving_time(s)"] = round(time.time() - time_start, 2)


def solve_milp_gurobi(filename, config_solver): # Solve a MILP model using Gurobi.
    gp = _load_gurobi()
    if gp is None:
        log("[WARNING] gurobipy module can't be loaded ... skipping test", config_solver=config_solver)
        return []

    try:
        model = gp.read(filename) # Load the model from file.
        # Set Parameters provided by Gurobi. Example: TimeLimit, SolutionLimit, PoolSearchMode, PoolSolutions, MIPFocus, etc.
        for key, val in config_solver.items():
            if hasattr(model.Params, key):
                setattr(model.Params, key, val)
        solution_number = config_solver.get("solution_number", 1)
        if isinstance(solution_number, int) and solution_number > 1:
            model.Params.PoolSearchMode = 2
            model.Params.PoolSolutions = solution_number
        # Solve the model
        model.optimize()
        sol_count = getattr(model, "SolCount", 0)
    except gp.GurobiError:
        log("[ERROR] Check your Gurobi license, visit https://gurobi.com/unrestricted for more information", config_solver=config_solver)
        return []

    # Return a list of solutions
    # Case 1: No solution found
    if sol_count == 0:
        log("[INFO] Found no solution from Gurobi.", config_solver=config_solver)
        return []

    # Case 2: Single optimal solution found
    elif solution_number == 1 and getattr(model.Params, "PoolSearchMode", 0) == 0:
        sol = {v.VarName: v.X for v in model.getVars()}
        sol["obj_fun_value"] = model.ObjVal
        log("[INFO] Found 1 solution from Gurobi.", config_solver=config_solver)
        return [sol]

    # Case 3: Multiple solutions found
    elif solution_number > 1 or getattr(model.Params, "PoolSearchMode", 0) > 0:
        sol_list = []
        for i in range(model.SolCount):
            model.Params.SolutionNumber = i
            sol = {v.VarName: v.Xn for v in model.getVars()}
            sol.update({"obj_fun_value": model.PoolObjVal})
            sol_list.append(sol)
        log(f"[INFO] Found {len(sol_list)} solution(s) from Gurobi.", config_solver=config_solver)
        return sol_list


def solve_milp_scip(filename, config_solver): # Solve a MILP model using SCIP.
    Model = _load_scip_model()
    if Model is None:
        log("[WARNING] PySCIPOpt module can't be loaded ... skipping SCIP test", config_solver=config_solver)
        return []

    try:
        model = Model()
        model.readProblem(filename)
        # Set Parameters provided by SCIP. TO DO MORE
        if "time_limit" in config_solver:
            model.setRealParam("limits/time", config_solver["time_limit"])
        solution_number = config_solver.get("solution_number", 1)
        if isinstance(solution_number, int) and solution_number > 1: # TO DO: support multiple solutions
            log("[WARNING] It currently does not support finding multiple solutions ... returning only one solution", config_solver=config_solver)
            model.setIntParam("limits/solutions", solution_number)
        # Solve the model
        model.optimize()
        sol_count = model.getNSols()
    except Exception as e:
        log(f"[WARNING] SCIP solver error: {e} ... skipping test", config_solver=config_solver)
        return []

    # Return a list of solutions
    if sol_count == 0:
        log("[INFO] Found no solution from SCIP.", config_solver=config_solver)
        return []

    else:
        sol = model.getBestSol()
        sol_dic = {v.name: model.getSolVal(sol, v) for v in model.getVars()}
        sol_dic["obj_fun_value"] = model.getSolObjVal(sol)
        log("[INFO] Found 1 solution from SCIP.", config_solver=config_solver)
        return [sol_dic]


def solve_sat(filename, variable_map, config_solver=None):
    """
    Solve a SAT problem

    Args:
        filename (str): Path to the CNF file.
        config_solver (dict):
            - target: The optimization target:
                - "SATISFIABLE": Find a feasible solution.
                - "All": Find all feasible solutions.
            - solver: solver name (e.g, "ORTools", "Cadical103")

    Returns:
        - If target is "SATISFIABLE", returns a dict of variable assignments (a solution).
        - If target is "ALL", returns a list of such dicts (all solutions).
        - None if no feasible solution is found or solver fails.
    """

    config_solver = config_solver or {}
    solver = config_solver.get("solver", "DEFAULT")
    log(f"[INFO] Solving SAT model with settings: {config_solver}", config_solver=config_solver)
    monitor = RuntimeResourceMonitor(interval=0.2)
    monitor.start()
    time_start = time.time()
    try:
        if solver in ["DEFAULT", "Cadical103", "Cadical153", "Cadical195", "CryptoMinisat", "Gluecard3", "Gluecard4", "Glucose3", "Glucose4", "Lingeling", "MapleChrono", "MapleCM", "Maplesat", "Mergesat3", "Minicard", "Minisat22", "MinisatGH"]:
            return solve_sat_pysat(filename, variable_map, config_solver)
        elif solver == "ORTools":
            return solve_sat_ortools(filename, variable_map, config_solver)
        else:
            raise ValueError(f"[ERROR] Unsupported solver: '{solver}'. Supported: ORTools, DEFAULT, Cadical103, Cadical153, Cadical195, CryptoMinisat, Gluecard3, Gluecard4, Glucose3, Glucose4, Lingeling, MapleChrono, MapleCM, Maplesat, Mergesat3, Minicard, Minisat22, MinisatGH'.")
    finally:
        config_solver["resource_usage"] = monitor.stop()
        config_solver["solving_time(s)"] = round(time.time() - time_start, 2)


def solve_sat_pysat(filename, variable_map, config_solver):
    CNF, Solver = _load_pysat()
    if CNF is None or Solver is None:
        log("[WARNING] pysat module can't be loaded ... skipping test", config_solver=config_solver)
        return None

    solver = config_solver.get("solver", "DEFAULT")
    solution_number = config_solver.get("solution_number", 1)
    cnf = CNF(filename)
    if solver == "DEFAULT":
        solver = Solver()
    else:
        solver = Solver(name=solver)

    solver.append_formula(cnf.clauses)

    sol_count = 0
    sol_list = []
    while sol_count < solution_number and solver.solve():
        model = solver.get_model()
        sol = {}
        for var, value in variable_map.items():
            if value in model:
                sol[var] = 1
            elif -value in model:
                sol[var] = 0
        sol_list.append(sol)
        block_clause = [-l for l in model] # TO DO: optimaize: if abs(l) in main_vars
        solver.add_clause(block_clause)
        sol_count += 1
    solver.delete()
    log(f"[INFO] Found {len(sol_list)} solution(s) from PySAT.", config_solver=config_solver)
    return sol_list


def solve_sat_ortools(filename, variable_map, config_solver): # TO DO
    return None
