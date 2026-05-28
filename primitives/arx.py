"""Shared ARX primitive layer builders.

These helpers centralize repeated ChaCha/Salsa/Forro layer construction while
preserving each primitive's existing round and layer layout.
"""

from operators.boolean_operators import XOR
from operators.modular_operators import ModAdd
from operators.operators import Equal


CHACHA_COLUMN_ROUNDS = (
    (0, 4, 8, 12),
    (1, 5, 9, 13),
    (2, 6, 10, 14),
    (3, 7, 11, 15),
)
CHACHA_DIAGONAL_ROUNDS = (
    (0, 5, 10, 15),
    (1, 6, 11, 12),
    (2, 7, 8, 13),
    (3, 4, 9, 14),
)
SALSA_COLUMN_ROUNDS = (
    (0, 4, 8, 12),
    (5, 9, 13, 1),
    (10, 14, 2, 6),
    (15, 3, 7, 11),
)
SALSA_ROW_ROUNDS = (
    (0, 1, 2, 3),
    (5, 6, 7, 4),
    (10, 11, 8, 9),
    (15, 12, 13, 14),
)


def chacha_quarter_rounds(round_number):
    return CHACHA_DIAGONAL_ROUNDS if round_number % 2 == 0 else CHACHA_COLUMN_ROUNDS


def salsa_quarter_rounds(round_number):
    return SALSA_ROW_ROUNDS if round_number % 2 == 0 else SALSA_COLUMN_ROUNDS


def _pairs(quarters, left_index, right_index):
    return [[quarter[left_index], quarter[right_index]] for quarter in quarters]


def _outputs(quarters, word_index):
    return [quarter[word_index] for quarter in quarters]


def _rotations(amount, quarters, word_index):
    return [['l', amount, quarter[word_index], quarter[word_index]] for quarter in quarters]


def add_chacha_quarter_round_layers(function, round_number, first_layer, quarters):
    function.SingleOperatorLayer("Add1", round_number, first_layer, ModAdd, _pairs(quarters, 0, 1), _outputs(quarters, 0))
    function.SingleOperatorLayer("XOR1", round_number, first_layer + 1, XOR, _pairs(quarters, 0, 3), _outputs(quarters, 3))
    function.RotationLayer("Rot1", round_number, first_layer + 2, _rotations(16, quarters, 3))
    function.SingleOperatorLayer("Add2", round_number, first_layer + 3, ModAdd, _pairs(quarters, 2, 3), _outputs(quarters, 2))
    function.SingleOperatorLayer("XOR2", round_number, first_layer + 4, XOR, _pairs(quarters, 1, 2), _outputs(quarters, 1))
    function.RotationLayer("Rot2", round_number, first_layer + 5, _rotations(12, quarters, 1))

    function.SingleOperatorLayer("Add3", round_number, first_layer + 6, ModAdd, _pairs(quarters, 0, 1), _outputs(quarters, 0))
    function.SingleOperatorLayer("XOR3", round_number, first_layer + 7, XOR, _pairs(quarters, 0, 3), _outputs(quarters, 3))
    function.RotationLayer("Rot3", round_number, first_layer + 8, _rotations(8, quarters, 3))
    function.SingleOperatorLayer("Add4", round_number, first_layer + 9, ModAdd, _pairs(quarters, 2, 3), _outputs(quarters, 2))
    function.SingleOperatorLayer("XOR4", round_number, first_layer + 10, XOR, _pairs(quarters, 1, 2), _outputs(quarters, 1))
    function.RotationLayer("Rot4", round_number, first_layer + 11, _rotations(7, quarters, 1))


def _temp_rotations(amount, temp_words):
    return [['l', amount, temp_word, temp_word] for temp_word in temp_words]


def add_salsa_quarter_round_layers(function, round_number, first_layer, quarters, temp_words):
    function.SingleOperatorLayer("Add1", round_number, first_layer, ModAdd, _pairs(quarters, 0, 3), temp_words)
    function.RotationLayer("Rot1", round_number, first_layer + 1, _temp_rotations(7, temp_words))
    function.SingleOperatorLayer("XOR1", round_number, first_layer + 2, XOR, [[temp_words[i], quarters[i][1]] for i in range(4)], _outputs(quarters, 1))

    function.SingleOperatorLayer("Add2", round_number, first_layer + 3, ModAdd, _pairs(quarters, 0, 1), temp_words)
    function.RotationLayer("Rot2", round_number, first_layer + 4, _temp_rotations(9, temp_words))
    function.SingleOperatorLayer("XOR2", round_number, first_layer + 5, XOR, [[temp_words[i], quarters[i][2]] for i in range(4)], _outputs(quarters, 2))

    function.SingleOperatorLayer("Add3", round_number, first_layer + 6, ModAdd, _pairs(quarters, 1, 2), temp_words)
    function.RotationLayer("Rot3", round_number, first_layer + 7, _temp_rotations(13, temp_words))
    function.SingleOperatorLayer("XOR3", round_number, first_layer + 8, XOR, [[temp_words[i], quarters[i][3]] for i in range(4)], _outputs(quarters, 3))

    function.SingleOperatorLayer("Add4", round_number, first_layer + 9, ModAdd, _pairs(quarters, 2, 3), temp_words)
    function.RotationLayer("Rot4", round_number, first_layer + 10, _temp_rotations(18, temp_words))
    function.SingleOperatorLayer("XOR4", round_number, first_layer + 11, XOR, [[temp_words[i], quarters[i][0]] for i in range(4)], _outputs(quarters, 0))


def copy_state_to_temp_words(function, round_number, layer, state_size=16, temp_start=16):
    function.SingleOperatorLayer(
        "Equal",
        round_number,
        layer,
        Equal,
        [[index] for index in range(state_size)],
        list(range(temp_start, temp_start + state_size)),
    )


def add_feedforward_final_round(function, round_number, first_layer, nbr_layers, state_size=16, temp_start=16):
    function.SingleOperatorLayer(
        "Add1",
        round_number,
        first_layer,
        ModAdd,
        [[index, temp_start + index] for index in range(state_size)],
        list(range(state_size)),
    )
    for layer in range(first_layer + 1, nbr_layers):
        function.AddIdentityLayer("Identity" + str(layer), round_number, layer)
