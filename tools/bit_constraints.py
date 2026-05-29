"""Boolean and matrix constraint helpers shared by operators."""

from itertools import combinations


def gen_xor_constraints(vin1, vin2, vout, model_type, v_dummy=None, version=0):
    # Constraint for bitwise xor: vin1 ^ vin2 = vout.
    assert (
        isinstance(vin1, str)
        and isinstance(vin2, str)
        and isinstance(vout, str)
    ), "[WARNING] Input and output variables must be strings."
    if model_type == "sat":
        if version == 0:
            return [
                f'{vin1} {vin2} -{vout}',
                f'{vin1} -{vin2} {vout}',
                f'-{vin1} {vin2} {vout}',
                f'-{vin1} -{vin2} -{vout}',
            ]
        else:
            raise ValueError(f"[WARNING] Unknown version {version} for XOR in SAT.")
    elif model_type == 'milp':
        if version == 0:
            return [f'{vin1} + {vin2} - {vout} >= 0',
                    f'{vin2} + {vout} - {vin1} >= 0',
                    f'{vin1} + {vout} - {vin2} >= 0',
                    f'{vin1} + {vin2} + {vout} <= 2',
                    'Binary\n' + ' '.join([vin1, vin2, vout])]
        elif version == 1:
            assert isinstance(v_dummy, str), "[WARNING] v_dummy must be provided as a string for XOR in MILP version 1."
            return [f'{vin1} + {vin2} + {vout} - 2 {v_dummy} >= 0',
                    f'{vin1} + {vin2} + {vout} <= 2',
                    f'{v_dummy} - {vin1} >= 0',
                    f'{v_dummy} - {vin2} >= 0',
                    f'{v_dummy} - {vout} >= 0',
                    'Binary\n' + ' '.join([vin1, vin2, vout, v_dummy])]
        elif version == 2:
            assert isinstance(v_dummy, str), "[WARNING] v_dummy must be provided as a string for XOR in MILP version 2."
            return [f'{vin1} + {vin2} + {vout} - 2 {v_dummy} = 0',
                    'Binary\n' + ' '.join([vin1, vin2, vout, v_dummy])]
        else:
            raise ValueError(f"[WARNING] Unknown version {version} for XOR in MILP.")
    else:
        raise ValueError(f"[WARNING] Unknown model type {model_type} for XOR.")


def gen_word_xor_constraints(vin1, vin2, vout, model_type, v_dummy=None, version=0):
    # Constraint for wordwise xor: vin1 ^ vin2 = vout.
    assert (
        isinstance(vin1, str)
        and isinstance(vin2, str)
        and isinstance(vout, str)
    ), "[WARNING] Input and output variables must be strings."
    if model_type == "sat":
        if version == 0:
            return [f'{vin1} {vin2} -{vout}',
                    f'{vin1} -{vin2} {vout}',
                    f'-{vin1} {vin2} {vout}']
        else:
            raise ValueError(f"[WARNING] Unknown version {version} for Word-wise XOR in SAT.")
    if model_type == 'milp':
        if version == 0:
            return [f'{vin1} + {vin2} - {vout} >= 0',
                    f'{vin2} + {vout} - {vin1} >= 0',
                    f'{vin1} + {vout} - {vin2} >= 0',
                    'Binary\n' + ' '.join([vin1, vin2, vout])]
        elif version == 1:
            assert isinstance(v_dummy, str), (
                "[WARNING] v_dummy must be provided as a string for Word-wise "
                "XOR in MILP version 1."
            )
            return [f'{vin1} + {vin2} + {vout} - 2 {v_dummy} >= 0',
                    f'{v_dummy} - {vin1} >= 0',
                    f'{v_dummy} - {vin2} >= 0',
                    f'{v_dummy} - {vout} >= 0',
                    'Binary\n' + ' '.join([vin1, vin2, vout, v_dummy])]
        else:
            raise ValueError(f"[WARNING] Unknown version {version} for Word-wise XOR in MILP.")
    else:
        raise ValueError(f"[WARNING] Unknown model type {model_type} for Word-wise XOR.")


def gen_nxor_constraints(vin, vout, model_type, v_dummy=None, version=0):
    # Constraint for n-ary bitwise nxor: vin1 ^ vin2 ^ ... ^ vinn = vout.
    assert (
        isinstance(vin, list)
        and isinstance(vout, str)
        and all(isinstance(v, str) for v in vin)
    ), "[WARNING] Input and output variables must be strings."
    constraints = []
    if model_type == "sat":
        for k in range(0, len(vin) + 1):  # All subsets (0 to n elements)
            for comb in combinations(vin, k):
                is_odd_parity = (len(comb) % 2 == 1)
                clause = [f"{vout}" if is_odd_parity else f"-{vout}"]
                clause += [f"-{v}" if v in comb else f"{v}" for v in vin]
                constraints.append(" ".join(clause))
        return constraints
    elif model_type == "milp":
        if version == 0:
            assert isinstance(v_dummy, str), "[WARNING] dummy must be provided as a string for n-XOR in MILP version 0."
            constraints += [" + ".join(v for v in (vin)) + " + " + vout + f" - 2 {v_dummy} = 0"]
            constraints += [f"{v_dummy} >= 0"]
            constraints += [f"{v_dummy} <= {int((len(vin)+1)/2)}"]
            constraints.append('Binary\n' + ' '.join(vin + [vout]))
            constraints.append('Integer\n' + v_dummy)
            return constraints
        elif version == 1: # Reference: MILP-aided cryptanalysis of the future block cipher.
            assert isinstance(v_dummy, list), (
                "[WARNING] v_dummy must be provided as a list of strings for "
                "n-XOR in MILP version 1."
            )
            s = " + ".join(vin) + f" + {vout} - {2 * len(v_dummy)} {v_dummy[0]}"
            s += (
                " - "
                + " - ".join(
                    f"{2 * (len(v_dummy) - j)} {v_dummy[j]}"
                    for j in range(1, len(v_dummy))
                )
                if len(v_dummy) > 1
                else ""
            )
            s += " = 0"
            return [s, 'Binary\n' + ' '.join(vin + [vout] + v_dummy)]
        else:
            raise ValueError(f"[WARNING] Unknown version {version} for n-XOR in MILP.")
    else:
        raise ValueError(f"[WARNING] Unknown model type {model_type} for n-XOR.")


def gen_word_nxor_constraints(vin, vout, model_type, v_dummy=None, version=0):
    constraints = []
    if model_type == "milp": # Reference: Related-Key Differential Analysis of the AES.
        constraints += [f"{' + '.join(vin)} - {vout} >= 0"]
        for k, ik in enumerate(vin):
            others = [x for j, x in enumerate(vin) if j != k]
            constraints.append(f"{' + '.join(others)} + {vout} - {ik} >= 0")
        constraints.append('Binary\n' +  ' '.join(vin + [vout]))
        return constraints
    elif model_type == "sat":
        constraints.append(" ".join([f"-{vout}"] + list(vin)))
        for k, ik in enumerate(vin):
            others = [x for j, x in enumerate(vin) if j != k]
            constraints.append(f"{' '.join(others)} {vout} -{ik}")
        return constraints
    else:
        raise ValueError(f"[WARNING] Unknown model type {model_type} for word-wise n-ary XOR.")


def gen_matrix_constraints(vin, vout, model_type, v_dummy=None):
    assert isinstance(vin, list), "Input variables should be provided as a list in matrix_constraints."
    assert isinstance(vout, str), "Output variable should be provided as a string in matrix_constraints."
    if len(vin) == 1:
        if model_type == 'milp':
            return [f"{vout} - {vin[0]} = 0", "Binary\n" + vin[0] + " " + vout]
        elif model_type == 'sat':
            return [f"{vin[0]} -{vout}", f"-{vin[0]} {vout}"]
    elif len(vin) == 2:
        return gen_xor_constraints(vin[0], vin[1], vout, model_type)
    elif len(vin) >= 3:
        if model_type == 'milp':
            assert isinstance(v_dummy, str), "Dummy variables must be provided for MILP model with more than 2 inputs."
        return gen_nxor_constraints(vin, vout, model_type, v_dummy=v_dummy)
    else:
        raise ValueError(f"[WARNING] Unknown model type {model_type} for Matrix.")


def gen_word_matrix_constraints(vin, vout, model_type, v_dummy=None):
    assert isinstance(vin, list), "Input variables should be provided as a list in word_matrix_constraints."
    assert isinstance(vout, str), "Output variable should be provided as a string in word_matrix_constraints."
    if len(vin) == 1:
        if model_type == 'milp':
            return [f"{vout} - {vin[0]} = 0", "Binary\n" + vin[0] + " " + vout]
        elif model_type == 'sat':
            return [f"{vin[0]} -{vout}", f"-{vin[0]} {vout}"]
    elif len(vin) == 2:
        return gen_word_xor_constraints(vin[0], vin[1], vout, model_type)
    elif len(vin) >= 3:
        return gen_word_nxor_constraints(vin, vout, model_type)
    else:
        raise ValueError(f"[WARNING] Unknown model type {model_type} for Matrix.")
