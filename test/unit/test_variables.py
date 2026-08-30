import pytest

from variables.variables import Variable


# ----------------------------- constructor -----------------------------
def test_constructor_sets_attributes_and_defaults():
    v = Variable(8, value=10, ID="v_1_0_3")
    assert v.bitsize == 8
    assert v.value == 10
    assert v.ID == "v_1_0_3"
    assert v.connected_vars == []
    assert v.copied_vars == []
    assert v.copyorigin is None

    w = Variable(4, copyorigin=v)
    assert w.copyorigin is v
    assert w.value is None and w.ID is None


def test_constructor_rejects_invalid_bitsize():
    for bad in (0, -1, 2.5, "8", None):
        with pytest.raises(ValueError, match="bitsize"):
            Variable(bad)


def test_constructor_rejects_non_string_id():
    with pytest.raises(ValueError, match="ID"):
        Variable(8, ID=123)


def test_constructor_rejects_out_of_range_value():
    with pytest.raises(ValueError, match="value"):
        Variable(8, value=256)  # 256 == 2**8, just out of range
    with pytest.raises(ValueError, match="value"):
        Variable(8, value=-1)
    # boundaries that are valid:
    assert Variable(8, value=255).value == 255
    assert Variable(8, value=0).value == 0


# ----------------------------- display_value -----------------------------
def test_display_value_representations():
    v = Variable(8, value=10)
    assert v.display_value("binary") == "00001010"
    assert v.display_value("hexadecimal") == "0a"
    assert v.display_value("integer") == "10"
    assert v.display_value("nonsense") == "Invalid representation"
    assert v.display_value() == "00001010"  # default is binary


def test_display_value_none_and_widths():
    assert Variable(8).display_value("binary") == "None"  # value unset
    assert Variable(4, value=10).display_value("binary") == "1010"
    assert Variable(4, value=10).display_value("hexadecimal") == "a"
    assert Variable(12, value=0xABC).display_value("hexadecimal") == "abc"


# ----------------------------- format_display / display -----------------------------
def test_format_display():
    assert (
        Variable(8, value=10, ID="v_1_0_3").format_display("binary")
        == "ID: v_1_0_3 / bitsize: 8 / value: 00001010"
    )
    # a None ID renders as empty
    assert (
        Variable(4, value=1, ID=None).format_display("integer")
        == "ID:  / bitsize: 4 / value: 1"
    )


def test_display_prints_and_returns(capsys):
    v = Variable(8, value=10, ID="v_1_0_3")
    line = "ID: v_1_0_3 / bitsize: 8 / value: 10"
    returned = v.display("integer")
    assert returned == line
    assert line in capsys.readouterr().out


def test_display_uses_output_func_instead_of_print(capsys):
    v = Variable(8, value=10, ID="v_1_0_3")
    sink = []
    returned = v.display("integer", output_func=sink.append)
    assert sink == [returned]
    assert capsys.readouterr().out == ""  # nothing went to stdout


# ----------------------------- remove_round_from_ID -----------------------------
def test_remove_round_from_ID():
    assert Variable(8, ID="v_1_0_3").remove_round_from_ID() == "v_0_3"
    assert Variable(8, ID="Add1_2_1_12").remove_round_from_ID() == "Add1_1_12"
    # None ID -> ""
    assert Variable(8, ID=None).remove_round_from_ID() == ""
    # round field is not a digit -> unchanged
    assert Variable(8, ID="v_x_0_3").remove_round_from_ID() == "v_x_0_3"
    # fewer than 4 fields -> unchanged
    assert Variable(8, ID="v_1").remove_round_from_ID() == "v_1"
