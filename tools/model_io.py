"""MILP/SAT model file serialization helpers."""

import os


def write_milp_model(constraints, obj_fun=None, filename="milp.lp"):
    """Generate and write a standard LP-format MILP model."""
    dir_path = os.path.dirname(filename)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    with open(filename, "w") as f:
        if obj_fun:
            f.write("Minimize\n obj\nSubject To\n")
        else:
            f.write("Minimize\n 0\nSubject To\n")

        bin_vars, in_vars = set(), set()
        for constraint in constraints:
            if "Binary" in constraint:
                parts = constraint.split('Binary\n')
                if parts[0].strip():
                    f.write(parts[0].strip() + "\n")
                for segment in parts[1:]:
                    seg = segment.strip()
                    if seg:
                        bin_vars.update(seg.split())
            elif "Integer" in constraint:
                parts = constraint.split('Integer\n')
                if parts[0].strip():
                    f.write(parts[0].strip() + "\n")
                for segment in parts[1:]:
                    seg = segment.strip()
                    if seg:
                        in_vars.update(seg.split())
            else:
                f.write(constraint if constraint.endswith('\n') else constraint + '\n')

        if obj_fun:
            if isinstance(obj_fun[0], list):
                obj_terms = [obj for row in obj_fun for obj in row]
            else:
                obj_terms = obj_fun
            f.write(" + ".join(obj_terms) + " - obj = 0" + "\n")

        if bin_vars:
            f.write("Binary\n" + " ".join(sorted(bin_vars)) + "\n")
        if in_vars:
            f.write("Integer\n" + " ".join(sorted(in_vars)) + "\n")

        f.write("End\n")
    return None


def create_numerical_cnf(cnf):
    """Convert symbolic CNF clauses to DIMACS-style integer clauses."""
    variables = sorted({literal.lstrip("-") for clause in cnf for literal in clause.split()})
    variable2number = {variable: i + 1 for (i, variable) in enumerate(variables)}

    numerical_cnf = []
    for clause in cnf:
        literals = clause.split()
        numerical_literals = (
            f'{"-" if literal.startswith("-") else ""}{variable2number[literal.lstrip("-")]}'
            for literal in literals
        )
        numerical_cnf.append(' '.join(numerical_literals))
    return len(variables), variable2number, numerical_cnf


def write_sat_model(constraints=None, filename="sat.cnf"):
    """Generate and write a DIMACS CNF SAT model."""
    constraints = constraints or []
    dir_path = os.path.dirname(filename)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    num_var, variable_map, numerical_cnf = create_numerical_cnf(constraints)
    num_clause = len(constraints)

    with open(filename, "w") as f:
        f.write(f"p cnf {num_var} {num_clause}\n")
        for constraint in numerical_cnf:
            f.write(f"{constraint} 0\n")

    return {"variable_map": variable_map}
