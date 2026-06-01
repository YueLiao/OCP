"""Search-strategy SAT/MILP constraints used by trail search helpers."""


def gen_sequential_encoding_sat(hw_list, weight, dummy_variables=None):
    """Generate SAT clauses for a sequential counter cardinality encoding."""
    if not hasattr(gen_sequential_encoding_sat, "_counter"):
        gen_sequential_encoding_sat._counter = 0
    n = len(hw_list)
    if not isinstance(weight, int) or weight < 0 or weight > n:
        raise ValueError(f"weight should be an integer: 0 <= weight <= n (n={n}), got {weight}")
    if weight == 0:
        return [f'-{var}' for var in hw_list]
    if weight >= n:
        return []
    if dummy_variables is None:
        gen_sequential_encoding_sat._counter += 1
        prefix = f'dummy_seq_{gen_sequential_encoding_sat._counter}'
        dummy_variables = [[f'{prefix}_{i}_{j}' for j in range(weight)] for i in range(n - 1)]
    constraints = [f'-{hw_list[0]} {dummy_variables[0][0]}']
    constraints.extend([f'-{dummy_variables[0][j]}' for j in range(1, weight)])
    for i in range(1, n - 1):
        constraints.append(f'-{hw_list[i]} {dummy_variables[i][0]}')
        constraints.append(f'-{dummy_variables[i - 1][0]} {dummy_variables[i][0]}')
        constraints.extend([f'-{hw_list[i]} -{dummy_variables[i - 1][j - 1]} {dummy_variables[i][j]}'
                            for j in range(1, weight)])
        constraints.extend([f'-{dummy_variables[i - 1][j]} {dummy_variables[i][j]}'
                            for j in range(1, weight)])
        constraints.append(f'-{hw_list[i]} -{dummy_variables[i - 1][weight - 1]}')
    constraints.append(f'-{hw_list[n - 1]} -{dummy_variables[n - 2][weight - 1]}')
    return constraints


def _default_milp_at_most(model_type, cons_type, cons_vars, cons_value, **_kwargs):
    if model_type != "milp" or cons_type != "AT_MOST":
        raise ValueError("Default Matsui factory only supports MILP AT_MOST constraints.")
    return [f"{cons_var} <= {cons_value}" for cons_var in cons_vars]


def gen_matsui_constraints_milp(
    Round,
    best_obj,
    obj_fun,
    cons_type="ALL",
    predefined_constraint_factory=_default_milp_at_most,
):
    """Generate Matsui branch-and-bound constraints for MILP models."""
    if Round < 2:
        raise ValueError(f"Round = {Round} must be at least 2.")
    if len(best_obj) != Round - 1:
        raise ValueError(f"best_obj = {best_obj} length must be Round-1 = {Round - 1}.")
    while obj_fun and obj_fun[-1] == []: # Remove empty lists at the end of obj_fun
        obj_fun.pop()
    if obj_fun is None or len(obj_fun) != Round or not all(isinstance(obj, list) for obj in obj_fun):
        raise ValueError(f"obj_fun = {obj_fun} must be a list of lists, and with length equal to Round = {Round}.")
    if cons_type not in ["ALL", "UPPER", "LOWER"]:
        raise ValueError(f"cons_type = {cons_type} must be one of ['ALL', 'UPPER', 'LOWER'].")

    add_cons = []
    for i in range(1, Round):
        if best_obj[i-1] > 0:
            if cons_type == "ALL" or cons_type == "UPPER":
                w_vars = [var for r in range(i + 1, Round + 1) for var in obj_fun[r - 1]]
                all_vars = [" + ".join(w_vars) + " - obj"]
                add_cons += predefined_constraint_factory(
                    model_type="milp",
                    cons_type="AT_MOST",
                    cons_vars=all_vars,
                    cons_value=-best_obj[i-1],
                )
            if cons_type == "ALL" or cons_type == "LOWER":
                w_vars = [var for r in range(1, Round - i + 1) for var in obj_fun[r - 1]]
                all_vars = [" + ".join(w_vars) + " - obj"]
                add_cons += predefined_constraint_factory(
                    model_type="milp",
                    cons_type="AT_MOST",
                    cons_vars=all_vars,
                    cons_value=-best_obj[i-1],
                )
    return add_cons


def gen_matsui_constraints_sat(
    Round,
    best_obj,
    obj_sat,
    obj_var,
    GroupConstraintChoice=1,
    GroupNumForChoice=1,
):
    """Generate Matsui branch-and-bound constraints for SAT models."""
    if Round < 2:
        raise ValueError(f"Round = {Round} must be at least 2.")
    if len(best_obj) != Round - 1:
        raise ValueError(f"best_obj length = {len(best_obj)} must be (Round-1) = {Round - 1}.")
    if not isinstance(obj_sat, int) or obj_sat <= 0:
        raise ValueError(f"obj_sat = {obj_sat} must be a positive integer.")
    while obj_var and obj_var[-1] == []: # Remove empty lists at the end of obj_var
        obj_var.pop()
    if obj_var is None or len(obj_var) != Round or not all(isinstance(row, list) for row in obj_var):
        obj_var_len = "None" if obj_var is None else len(obj_var)
        raise ValueError(f"obj_var must be a list of lists, and with length = {obj_var_len} equal to Round = {Round}.")
    if GroupConstraintChoice != 1:
        raise ValueError(f"Currently only support GroupConstraintChoice = 1, but got {GroupConstraintChoice}.")
    if GroupNumForChoice < 1:
        raise ValueError(f"GroupNumForChoice = {GroupNumForChoice} must be at least 1.")

    if not hasattr(gen_matsui_constraints_sat, "_counter"): # Use function attribute to set global counter
        gen_matsui_constraints_sat._counter = 0
    if len(best_obj) == Round-1:
        best_obj = [0] + best_obj
    Main_Vars = list([])
    for r in range(Round):
        for i in range(len(obj_var[Round - 1 - r])):
            Main_Vars += [obj_var[Round - 1 - r][i]]
    gen_matsui_constraints_sat._counter += 1
    dummy_var = [
        [
            f'dummy_matsui_{gen_matsui_constraints_sat._counter}_{i}_{j}'
            for j in range(obj_sat)
        ]
        for i in range(len(Main_Vars) - 1)
    ]
    constraints = gen_sequential_encoding_sat(hw_list=Main_Vars, weight=obj_sat, dummy_variables=dummy_var)

    MatsuiRoundIndex = []
    if GroupConstraintChoice == 1:
        for group in range(GroupNumForChoice):
            for round_offset in range(1, Round - group + 1):
                MatsuiRoundIndex.append([group, group + round_offset])

    for matsui_count in range(0, len(MatsuiRoundIndex)):
        StartingRound = MatsuiRoundIndex[matsui_count][0]
        EndingRound = MatsuiRoundIndex[matsui_count][1]
        PartialCardinalityCons = obj_sat - best_obj[StartingRound] - best_obj[Round-EndingRound]
        left = 0
        for i in range(StartingRound):
            left += len(obj_var[i])
        right = 0
        for i in range(EndingRound):
            right += len(obj_var[i])
        right -= 1
        constraints += gen_matsui_partial_cardinality_sat(
            Main_Vars,
            dummy_var,
            obj_sat,
            left,
            right,
            PartialCardinalityCons,
        )
    return constraints


def gen_matsui_partial_cardinality_sat(obj_var, dummy_var, k, left, right, m):
    """Generate partial cardinality SAT clauses for Matsui constraints."""
    if not isinstance(obj_var, list) or len(obj_var) == 0:
        raise ValueError("obj_var must be a non-empty list.")
    if not isinstance(dummy_var, list) or len(dummy_var) != len(obj_var) - 1:
        raise ValueError("dummy_var must be a list with length equal to len(obj_var) - 1.")
    if not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a positive integer.")
    if not isinstance(left, int) or left < 0:
        raise ValueError("left index must be a non-negative integer.")
    if not isinstance(right, int) or right >= len(obj_var):
        raise ValueError(f"right index = {right} out of range of obj_var = {len(obj_var)}.")
    if not isinstance(m, int) or m < 0:
        raise ValueError(f"m={m} must be a non-negative integer.")

    n = len(obj_var)
    add_cons = []

    if m > 0:
        if left == 0 and right < n - 1:
            for i in range(1, right + 1):
                add_cons.append(f"-{obj_var[i]} -{dummy_var[i - 1][m - 1]}")

        if left > 0 and right == n - 1:
            for i in range(0, k - m):
                add_cons.append(f"{dummy_var[left - 1][i]} -{dummy_var[right - 1][i + m]}")
            for i in range(0, k - m + 1):
                add_cons.append(f"{dummy_var[left - 1][i]} -{obj_var[right]} -{dummy_var[right - 1][i + m - 1]}")

        if left > 0 and right < n - 1:
            for i in range(0, k - m):
                add_cons.append(f"{dummy_var[left - 1][i]} -{dummy_var[right][i + m]}")

    elif m == 0:
        for i in range(left, right + 1):
            add_cons.append(f"-{obj_var[i]}")

    return add_cons
