"""Constraint template generation, caching, and instantiation helpers."""

import ast
from functools import lru_cache
import os
import platform
import re
import sys
import time

from tools.minimize_logic import ttb_to_ineq_logic
from tools.polyhedron import ttb_to_ineq_convex_hull


def generate_and_save_constraints(
    model_type,
    tool_type,
    mode,
    ttable,
    input_variables,
    output_variables,
    weight_variables=None,
    objective_fun=None,
    model_filename=None,
):
    """
    Generate template constraints/objective function and save them to self.model_filename.

    Returns:
        tuple[list[str], str]: (constraints, objective_fun)
    """
    variables = (
        input_variables + output_variables + weight_variables
        if weight_variables
        else input_variables + output_variables
    )
    time_start = time.time()
    if model_type == "milp":
        if tool_type not in [
            "minimize_logic",
            "minimize_logic_espresso",
            "polyhedron",
        ]:
            raise ValueError(f"Unsupported tool type {tool_type} for MILP model.")
    elif model_type == "sat":
        if tool_type not in [
            "minimize_logic",
            "minimize_logic_espresso",
        ]:
            raise ValueError(f"Unsupported tool type {tool_type} for SAT model.")
    else:
        raise ValueError(f"unknown model type {model_type}")

    if tool_type == "minimize_logic" or tool_type == "minimize_logic_espresso":
        inequalities, information = ttb_to_ineq_logic(
            ttable,
            variables,
            mode=mode,
            tool_type=tool_type,
        )

    elif tool_type == "polyhedron": # Generate inequalities from the truth table using Convex Hull
        inequalities, information = ttb_to_ineq_convex_hull(ttable, variables)
    else:
        raise ValueError(f"unknown tool type {tool_type}")

    if model_type == 'milp': # Generate MILP constraints from inequalities
        constraints = [inequality_to_constraint_milp(ineq, variables) for ineq in inequalities]
        num_cons = len(constraints)
        constraints.append('Binary\n' + ' '.join(variables))
    elif model_type == 'sat':  # Generate SAT constraints from inequalities
        constraints = [inequality_to_constraint_sat(ineq, variables) for ineq in inequalities]
        num_cons = len(constraints)
    else:
        raise ValueError(f"unknown model type {model_type}")

    time_used = time.time() - time_start
    if model_filename is not None:
        with open(model_filename, "w", encoding="utf-8") as file:
            file.write(f"Input: {'||'.join(input_variables)}; msb: {input_variables[0]}\n")
            file.write(f"Output: {'||'.join(output_variables)}; msb: {output_variables[0]}\n")
            file.write(f"Time used to simplify the constraints: {time_used:.4f} s\n")
            file.write(f"Number of constraints: {num_cons}\n")
            file.write(f"Constraints: {constraints}\n")
            if objective_fun:
                file.write(f"Weight: {objective_fun}\n")
            file.write(f"\n\nInformation\n")
            for key, value in information.items():
                file.write(f"{key}: {value}\n")
            file.write(f"Model type: {model_type}\n")
            file.write(f"Tool type: {tool_type}\n")
            file.write(f"Python version: {sys.version.split()[0]}\n")
            file.write(f"Platform: {platform.platform()}\n")
    return constraints, objective_fun


@lru_cache(maxsize=128)
def load_constraints_template_cached(filename, mtime_ns):
    constraints, objective_fun = None, None
    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line.startswith("Constraints:"):
                constraints_str = line.split(":", 1)[1].strip()
                try:
                    constraints = ast.literal_eval(constraints_str)
                except (SyntaxError, ValueError) as e:
                    raise ValueError(f"Failed to parse constraints from {filename}: {constraints_str}") from e
            elif line.startswith("Weight:"):
                objective_fun = line.split(":", 1)[1].strip()
    return tuple(constraints) if constraints is not None else None, objective_fun


def load_constraints_template(filename):
    """
    Load template constraints/objective function from file.

    Returns:
        tuple[list[str] | None, str | None]: (constraints, objective_fun)
    """
    if not os.path.exists(filename):
        return None, None
    constraints, objective_fun = load_constraints_template_cached(
        filename,
        os.stat(filename).st_mtime_ns,
    )
    return list(constraints) if constraints is not None else None, objective_fun


def build_template_replacer(*template_var_groups):
    replacements = {}
    for prefix, variables in template_var_groups:
        if variables is None:
            continue
        replacements.update(
            (f"{prefix}{index}", str(variable))
            for index, variable in enumerate(variables)
        )

    if not replacements:
        return lambda expr: expr

    token_pattern = "|".join(
        re.escape(token)
        for token in sorted(replacements, key=len, reverse=True)
    )
    pattern = re.compile(rf"\b(?:{token_pattern})\b")

    def replace(expr):
        if expr is None:
            return None
        return pattern.sub(lambda match: replacements[match.group(0)], expr)

    return replace


def instantiate_constraints_template(constraints, objective_fun, var_in, var_out, var_p=None):
    """
    Instantiate template constraints/objective function by replacing template variables:
        a0, a1, ... -> var_in[i]
        b0, b1, ... -> var_out[i]
        p0, p1, ... -> var_p[i] (optional)

    Returns:
        tuple[list[str], str]: (mapped_constraints, mapped_objective_fun)
    """
    replace_constraint_vars = build_template_replacer(
        ("a", var_in),
        ("b", var_out),
        ("p", var_p),
    )
    replace_objective_vars = build_template_replacer(("p", var_p))

    return (
        [replace_constraint_vars(con) for con in constraints],
        replace_objective_vars(objective_fun),
    )


def gen_constraints_obj_func_from_template(filename, var_in, var_out, var_p=None):
    """
    Load template constraints/objective function from file, then instantiate them.

    Returns:
        tuple[list[str], str]: (mapped_constraints, mapped_objective_fun)
    """
    constraints, objective_fun = load_constraints_template(filename)

    if constraints is None:
        raise ValueError(f"Failed to load constraints or objective function from {filename}.")

    return instantiate_constraints_template(constraints, objective_fun, var_in, var_out, var_p)


def inequality_to_constraint_sat(inequality, variables):
    # Convert coefficients plus RHS into SAT clause format.
    """
    Example:
        inequality = [1, -1, 0, -1, -1], variables = ['x1', 'x2', 'x3', 'x4']
        Return: 'x1 -x2 -x4'
    """
    terms = []
    for coeff, var in zip(inequality[:-1], variables):
        if coeff == 1:
            terms.append(f"{var}")
        elif coeff == -1:
            terms.append(f"-{var}")
        # coeff == 0 -> variable not used
    return " ".join(terms).strip()


def inequality_to_constraint_milp(inequality, variables):
    # Convert coefficients plus RHS into MILP inequality format.
    """
    Example:
        ineq = [1, -1, 0, -1, -1], variables = ['x1', 'x2', 'x3', 'x4']
        Return: 'x1 - x2 - x4 >= -1'
    """
    terms = []
    rhs = inequality[-1]
    for coeff, var in zip(inequality[:-1], variables):
        sign = '+' if coeff > 0 else '-'
        abs_coeff = abs(coeff)
        if abs_coeff == 1:
            terms.append(f"{sign} {var}")
        elif abs_coeff > 0:
            terms.append(f"{sign} {abs_coeff} {var}")
        # coeff == 0 -> variable not used
    return " ".join(terms).lstrip('+ ').strip() + f" >= {rhs}"
