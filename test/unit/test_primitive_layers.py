from operators.boolean_operators import XOR
from operators.matrix import Matrix
from operators.operators import Equal, Rot
from primitives.primitives import Layered_Function


def _constraint_ids(function, round_number=1, layer_number=0):
    return [constraint.ID for constraint in function.constraints[round_number][layer_number]]


def test_add_identity_layer_creates_equal_constraints_for_all_words():
    function = Layered_Function("F", "", 1, 1, 2, 1, 4)

    function.AddIdentityLayer("ID", 1, 0)

    constraints = function.constraints[1][0]
    assert _constraint_ids(function) == ["ID_EQ_1_1_0", "ID_EQ_1_1_1", "ID_EQ_1_1_2"]
    assert all(isinstance(constraint, Equal) for constraint in constraints)
    assert [constraint.input_vars[0].ID for constraint in constraints] == ["v_1_0_0", "v_1_0_1", "v_1_0_2"]
    assert [constraint.output_vars[0].ID for constraint in constraints] == ["v_1_1_0", "v_1_1_1", "v_1_1_2"]


def test_permutation_layer_extends_missing_positions_as_identity():
    function = Layered_Function("F", "", 1, 1, 3, 1, 4)

    function.PermutationLayer("P", 1, 0, [2, 0])

    constraints = function.constraints[1][0]
    assert _constraint_ids(function) == ["P_EQ_1_1_0", "P_EQ_1_1_1", "P_EQ_1_1_2", "P_EQ_1_1_3"]
    assert [constraint.input_vars[0].ID for constraint in constraints] == ["v_1_0_2", "v_1_0_0", "v_1_0_2", "v_1_0_3"]
    assert [constraint.output_vars[0].ID for constraint in constraints] == ["v_1_1_0", "v_1_1_1", "v_1_1_2", "v_1_1_3"]


def test_rotation_layer_mixes_rotations_and_identity_constraints():
    function = Layered_Function("F", "", 1, 1, 3, 0, 8)

    function.RotationLayer("R", 1, 0, [["l", 1, 0, 2]])

    constraints = function.constraints[1][0]
    assert _constraint_ids(function) == ["R_EQ_1_1_0", "R_EQ_1_1_1", "R_1_1_2"]
    assert isinstance(constraints[0], Equal)
    assert isinstance(constraints[1], Equal)
    assert isinstance(constraints[2], Rot)
    assert constraints[2].direction == "l"
    assert constraints[2].amount == 1
    assert constraints[2].input_vars[0].ID == "v_1_0_0"
    assert constraints[2].output_vars[0].ID == "v_1_1_2"


def test_single_operator_layer_uses_set_membership_without_changing_constraints():
    function = Layered_Function("F", "", 1, 1, 4, 0, 1)

    function.SingleOperatorLayer("X", 1, 0, XOR, [[0, 1]], [2])

    constraints = function.constraints[1][0]
    assert _constraint_ids(function) == ["X_EQ_1_1_0", "X_EQ_1_1_1", "X_1_1_2", "X_EQ_1_1_3"]
    assert [constraint.__class__.__name__ for constraint in constraints] == ["Equal", "Equal", "XOR", "Equal"]
    assert [variable.ID for variable in constraints[2].input_vars] == ["v_1_0_0", "v_1_0_1"]
    assert [variable.ID for variable in constraints[2].output_vars] == ["v_1_1_2"]


def test_matrix_layer_adds_identity_constraints_outside_matrix_groups():
    function = Layered_Function("F", "", 1, 1, 3, 0, 4)

    function.MatrixLayer("M", 1, 0, [[1, 0], [0, 1]], [[0, 1]])

    constraints = function.constraints[1][0]
    assert _constraint_ids(function) == ["M_EQ_1_1_2", "M_1_1_0"]
    assert isinstance(constraints[0], Equal)
    assert isinstance(constraints[1], Matrix)
