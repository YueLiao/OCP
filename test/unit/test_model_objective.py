from tools.model_objective import (
    cal_round_obj_fun_values_from_solution,
    gen_obj_fun_variables,
    parse_objective_term,
)


def test_parse_objective_term_supports_common_forms():
    assert parse_objective_term("x") == (1.0, "x")
    assert parse_objective_term("2 x") == (2.0, "x")
    assert parse_objective_term("0.5000 p0") == (0.5, "p0")
    assert parse_objective_term("2x") == (2.0, "x")
    assert parse_objective_term("not valid!") is None


def test_gen_obj_fun_variables_separates_integer_and_decimal_terms():
    obj_fun = [
        ["p0 + 2 p1 + 0.5000 p2"],
        ["p3 + 0.2500 p4 + 0.5000 p5"],
    ]

    int_vars, decimal_vars = gen_obj_fun_variables(obj_fun, obj_fun_decimal=True)

    assert int_vars == [["p0", "p1"], ["p3"]]
    assert decimal_vars == [
        [["p2"], ["p5"]],
        [[], ["p4"]],
    ]


def test_cal_round_obj_fun_values_from_solution_uses_coefficients():
    obj_fun = [["x + 2 y + 0.5 z"], ["missing + 3 w"]]
    solution = {"x": 1, "y": 0, "z": 1, "w": 2}

    assert cal_round_obj_fun_values_from_solution(obj_fun, solution) == [1.5, 6.0]


def test_cal_round_obj_fun_values_warns_for_unparseable_terms(recwarn):
    assert cal_round_obj_fun_values_from_solution([["not valid!"]], {}) == [0]

    warning = recwarn.pop(RuntimeWarning)
    assert "Unable to parse objective term" in str(warning.message)
