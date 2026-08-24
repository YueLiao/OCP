import subprocess
from pathlib import Path
import warnings
from tools.paths import get_files_dir

try:
    import pyeda
except (ImportError, OSError):
    pyeda = None


def _pyeda_raw_patterns(ttable, variables):
    """Minimize the truth table's ON-set with PyEDA's built-in Espresso and
    return cube patterns in the SAME column convention the external espresso
    binary emits, so the downstream ``espresso_pattern_to_ineq`` parser is reused
    unchanged.

    The ON-set is the set of minterms with ``ttable[k] == '0'`` (identical to the
    PLA that the external path writes, where such minterms get output bit '1').
    Each returned pattern has one character per variable, in ``variables`` order
    (position 0 == variables[0] == most-significant input bit):
        '0' -> the variable must be 0 in the cube (complemented literal)
        '1' -> the variable must be 1 in the cube (uncomplemented literal)
        '-' -> the variable is absent from the cube

    Correctness is exact: a point violates at least one derived inequality iff it
    lies in the ON-set (verified exhaustively). PyEDA's Espresso always returns a
    minimized ON-set cover, so the ``mode`` presets used by the external binary
    have no analogue here and are not needed.
    """
    from pyeda.boolalg.table import truthtable
    from pyeda.boolalg.bfarray import ttvars
    from pyeda.boolalg.minimization import espresso_tts
    from pyeda.boolalg.expr import Complement, Variable

    num_vars = len(variables)
    onset_str = "".join('1' if ttable[k] == '0' else '0' for k in range(2 ** num_vars))
    minimized = espresso_tts(truthtable(ttvars('x', num_vars), onset_str))[0]

    if minimized.is_zero():
        return []                      # empty ON-set: nothing to forbid
    if minimized.is_one():
        return ['-' * num_vars]        # full ON-set: forbid every point

    cubes = list(minimized.xs) if minimized.__class__.__name__ == 'OrOp' else [minimized]
    patterns = []
    for cube in cubes:
        literals = list(cube.xs) if cube.__class__.__name__ == 'AndOp' else [cube]
        pattern = ['-'] * num_vars
        for literal in literals:
            if isinstance(literal, Complement):
                bit_index, char = (~literal).indices[0], '0'   # variable must be 0
            elif isinstance(literal, Variable):
                bit_index, char = literal.indices[0], '1'       # variable must be 1
            else:
                raise TypeError(f"unexpected PyEDA literal {literal!r}")
            # PyEDA's x[bit_index] is minterm bit `bit_index` (LSB = 0); the PLA /
            # espresso column order is most-significant first, so variables[i]
            # maps to minterm bit (num_vars - 1 - i).
            pattern[num_vars - 1 - bit_index] = char
        patterns.append("".join(pattern))
    return patterns


def espresso_pattern_to_ineq(pattern): # Convert the Espresso output into a list of integer coefficients representing a linear inequality of the form: sum_i (coeff_i * x_i) >= rhs
    """
    Parameters:
        pattern (str): A string consisting of characters '0', '1', or '-'. Each character corresponds to one variable:
                         '0' → +1 coefficient (positive)
                         '1' → -1 coefficient (negative)
                         '-' → 0 coefficient (ignored)

    Returns:
        List[int]: Coefficients followed by the right-hand side (RHS) constant.

    Example:
        pattern = '01-1'  # Suppose variables = ['x1', 'x2', 'x3', 'x4']
        Then:
            x1 → '0' → +1
            x2 → '1' → -1
            x3 → '-' →  0
            x4 → '1' → -1
            Coefficients = [1, -1, 0, -1], RHS = -2 (from two '1's) + 1 = -1
            Inequality becomes: x1 - x2 - x4 >= -1
        Return: [1, -1, 0, -1, -1]
    """
    coeffs = []
    rhs = 0
    for ch in pattern:
        if ch == '0':
            coeffs.append(1)
        elif ch == '1':
            coeffs.append(-1)
            rhs -= 1
        else:
            coeffs.append(0)  # don't care
    return coeffs + [rhs + 1]


def ttb_to_ineq_logic(ttable, variables, mode=0, tool_type="espresso_pyeda", timeout=720000): # Convert a truth table to CNF or MILP constraints using the Espresso logic minimization tool via PyEDA.
    # Prepare truth table in PLA (Programmable Logic Array) format
    """
    Convert a truth table in PLA (Programmable Logic Array) format to inequalities using logic minimization.

    Args:
        ttable:
            Truth table values.
            ttable[n] == '0' means output bit 1 in PLA; otherwise output bit 0.
        variables (list[str]):
            Variable names in the truth table order.
        mode (int):
            Option preset for the external espresso binary.
        backend (str):
            "espresso_pyeda": Use the PyEDA library to call espresso internally.
            "espresso": Use the external espresso software.
        timeout (int):
            Timeout in seconds for espresso.

    Returns:
        list:
            A list of inequalities.
    """
    num_vars = len(variables)
    pla_rows = []
    for n in range(2**num_vars):
        bit = '1' if ttable[n] == '0' else '0'
        pla_rows.append(f'{bin(n)[2:].zfill(num_vars)} {bit}')
    file_contents = f".i {num_vars}\n"
    file_contents += ".o 1\n"
    file_contents += f".p {2**(num_vars)}\n"
    file_contents += ".ilb " + " ".join(variables) + "\n"
    file_contents += ".ob F\n"
    file_contents += ".type fr\n"
    file_contents += "\n".join(pla_rows) + "\n"

    # Setup paths
    files_dir = get_files_dir("sbox_modeling")
    pla_file = str(files_dir / 'ttable.txt')
    result_file = str(files_dir / 'sttable.txt')

    # Write input PLA file
    with open(pla_file, "w") as fw:
        fw.write(file_contents)

    # Define espresso command-line options based on mode. Refer to Espresso documentation for details on these options.
    espresso_options =  [['-estrong', '-eonset'], [], ['-eonset']] # Espresso Script of Pyeda provides the parameters: "-e {fast,ness,nirr,nunwrap,onset,strong}"

    if tool_type == "minimize_logic": # Generate inequalities from the truth table using PyEDA's built-in Espresso (no external binary required)
        if pyeda is None:
            raise ImportError(
                "PyEDA is required for tool_type='minimize_logic'. "
                "Install it with: pip install pyeda"
            )
        backend_name = "espresso_pyeda"
        backend_version = getattr(pyeda, "__version__", "unknown")
        raw_patterns = _pyeda_raw_patterns(ttable, variables)
        inequalities = [espresso_pattern_to_ineq(p[:len(variables)]) for p in raw_patterns]
        information = {"Backend": backend_name, "Backend version": backend_version, "Mode": espresso_options[mode]}
        return inequalities, information

    elif tool_type == "minimize_logic_espresso": # Generate inequalities from the truth table using external Espresso software
        backend_name = "espresso"
        espresso_path = Path.home() / "espresso-logic" / "bin" / "espresso" # Adjust this path to where espresso is installed on your system
        if not espresso_path.exists():
            warnings.warn(
                "Cannot find external Espresso at ~/espresso-logic/bin/espresso.",
                RuntimeWarning,
            )
        backend_version = "unknown"
        try:
            result = subprocess.run([espresso_path, "-v"], capture_output=True, text=True, check=False)
            version_text = (result.stdout + result.stderr).strip()
            if version_text:
                backend_version = version_text.splitlines()[0]
        except (OSError, subprocess.SubprocessError):
            pass
        espresso_command = [espresso_path, *espresso_options[mode], pla_file]
    else:
        raise ValueError(f"unknown tool type {tool_type}")

    try:
        result = subprocess.run(espresso_command, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"Espresso execution failed:\n{result.stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Espresso execution exceeded the timeout of {timeout} seconds.")

    # Save output and parse
    with open(result_file, 'w') as fw:
        fw.write(result.stdout)
    espresso_output = result.stdout.splitlines()
    raw_patterns = [line.strip() for line in espresso_output if line.strip() and not line.startswith('.')]

    # Convert logic lines to target constraints
    inequalities = [espresso_pattern_to_ineq(p[:len(variables)]) for p in raw_patterns]
    information = {"Backend": backend_name, "Backend version": backend_version, "Mode": espresso_options[mode]}
    return inequalities, information
