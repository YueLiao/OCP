from abc import ABC, abstractmethod
import sys
from tools.bit_constraints import gen_xor_constraints, gen_word_xor_constraints, gen_nxor_constraints, gen_word_nxor_constraints


def RaiseExceptionVersionNotExisting(class_name, model_version, model_type):
    raise ValueError(f"{class_name}: version {model_version} not existing for {model_type}")


def raise_unknown_model_type(class_name, model_type, context=None):
    context_message = f" for {context}" if context is not None else ""
    raise ValueError(f"{class_name}: unknown model type '{model_type}'{context_message}")


def raise_unknown_implementation_type(class_name, implementation_type):
    raise ValueError(f"{class_name}: unknown implementation type '{implementation_type}'")


def require_variable_count(class_name, variables, expected_count, side):
    if len(variables) != expected_count:
        raise ValueError(f"{class_name}: expected exactly {expected_count} {side} variable(s), got {len(variables)}")


def require_min_variable_count(class_name, variables, min_count, side):
    if len(variables) < min_count:
        raise ValueError(f"{class_name}: expected at least {min_count} {side} variable(s), got {len(variables)}")


def require_same_bitsize(class_name, left_var, right_var, message):
    if left_var.bitsize != right_var.bitsize:
        raise ValueError(f"{class_name}: {message}")


def binary_declaration(*var_groups):
    return 'Binary\n' + ' '.join(v for group in var_groups for v in group)


def sat_equivalence_constraints(var_in, var_out):
    return [clause for vin, vout in zip(var_in, var_out) for clause in (f"-{vin} {vout}", f"{vin} -{vout}")]


def milp_equivalence_constraints(var_in, var_out):
    return [f"{vin} - {vout} = 0" for vin, vout in zip(var_in, var_out)]


# ********************* OPERATORS ********************* #
# Class that represents a constraint/operator object, i.e. a type of node in our graph modeling (the other type being the variables)
# An Operator/Constraint node can only be linked to a Variable node in the graph representation
# Operators/Constraints are relationships between a group of variables

class Operator(ABC):
    def __init__(self, input_vars, output_vars, model_version=None, ID=None):
        self.input_vars = input_vars        # input variables of that operator
        self.output_vars = output_vars      # output variables of that operator
        self.model_version = model_version  # model version that will be used for that operator
        self.ID = ID                        # ID of the operator
        self.is_ghost = False               # indicates whether that operator is a ghost operator (i.e., an operator that has been marked as ghost during the dead-end removal process)

        # For this new operator created, update the connected_vars list for each input and output variables
        if self.__class__.__name__!="NoneOperator":
            for var_in in input_vars:
                for var_out in output_vars:
                    var_in.connected_vars.append((var_out,self,'in'))
                    var_out.connected_vars.append((var_in,self,'out'))

    def format_display(self):
        lines = [f"ID: {self.ID}", "Input:"]
        for input_var in self.input_vars:
            if not isinstance(input_var, list):
                lines.append(input_var.format_display())
            else:
                lines.extend(var.format_display() for var in input_var)

        lines.append("Output:")
        for output_var in self.output_vars:
            if not isinstance(output_var, list):
                lines.append(output_var.format_display())
            else:
                lines.extend(var.format_display() for var in output_var)
        return "\n".join(lines)

    def display(self, output_func=None):
        text = self.format_display()
        if output_func is None:
            sys.stdout.write(text + "\n")
        else:
            output_func(text)
        return self.__class__.__name__

    # obtain the ID of the variable located at "index" of input or output (in_out) for that operator. Compresses the ID if unroll is False
    def get_var_ID(self, in_out, index, unroll=False):
        if in_out == 'out':
            return self.output_vars[index].ID if unroll else self.output_vars[index].remove_round_from_ID()
        elif in_out == 'in':
            return self.input_vars[index].ID if unroll else self.input_vars[index].remove_round_from_ID()
        else:
            raise ValueError(f"{self.__class__.__name__}: unknown in_out type '{in_out}'")

    def get_header_ID(self):
        return [self.__class__.__name__, self.model_version]

    def generate_implementation_header(self, implementation_type='python'):    # generic method that generates the code for the header of the modeling of that operator
        return None

    # method that returns the ID of the variable located at "index" of either the input or output of the operator, with options for bitwise listing and dimension unrolling
    def get_var_model(self, in_out, index, bitwise=True, dim=1):
        if in_out == 'in':
            var = self.input_vars[index]
        elif in_out == 'out':
            var = self.output_vars[index]
        else:
            raise ValueError(f"{self.__class__.__name__}: unknown in_out type '{in_out}'")
        if bitwise and var.bitsize > 1:
            return [f"{var.ID}_{i}_{j}" for i in range(var.bitsize) for j in range(dim)] if dim > 1 else [f"{var.ID}_{i}" for i in range(var.bitsize)]
        else:
            return [f"{var.ID}_{j}" for j in range(dim)] if dim > 1 else [f"{var.ID}"]

    @abstractmethod
    def generate_implementation(self, implementation_type='python'):  # generic method (abstract) that generates the code for the implementation of that operator
        pass

    @abstractmethod
    def generate_model(self, model_type='python'):  # generic method (abstract) that generates the code for the modeling of that operator
        pass


class CastingOperator(Operator):    # Operator for casting from one type to another
    """Abstract base for future casting operators.

    Casting operators must preserve the total bit width. Concrete subclasses are
    expected to define implementation/model generation for their specific layout.
    """

    def __init__(self, input_vars, output_vars, ID = None):
        if sum(input_var.bitsize for input_var in input_vars) != sum(output_var.bitsize for output_var in output_vars):
            raise ValueError("CastingOperator: the total input size does not match the total output size")
        super().__init__(input_vars, output_vars, ID = ID)


class CastingWordtoBitVector(CastingOperator):   # Operator for casting a bit word to a vector of bits
    """Abstract base for word-to-bit-vector casting operators."""


class UnaryOperator(Operator):   # Generic operator taking one input and one output (must be of same bitsize)
    def __init__(self, input_vars, output_vars, ID = None):
        require_variable_count(self.__class__.__name__, input_vars, 1, "input")
        require_variable_count(self.__class__.__name__, output_vars, 1, "output")
        # if input_vars[0].bitsize != output_vars[0].bitsize: raise Exception(str(self.__class__.__name__) + ": your input and output sizes do not match") zcn: can be removed because the input size and output size of sbox may be different
        super().__init__(input_vars, output_vars, ID = ID)


class BinaryOperator(Operator):   # Generic operator taking two inputs and one output (must be of same bitsize)
    def __init__(self, input_vars, output_vars, ID = None):
        require_variable_count(self.__class__.__name__, input_vars, 2, "input")
        require_variable_count(self.__class__.__name__, output_vars, 1, "output")
        require_same_bitsize(self.__class__.__name__, input_vars[0], input_vars[1], "input sizes do not match")
        require_same_bitsize(self.__class__.__name__, input_vars[0], output_vars[0], "input and output sizes do not match")
        super().__init__(input_vars, output_vars, ID = ID)


class NoneOperator(Operator):  # Ghost Operator, does nothing (just a placeholder)
    def __init__(self, input_vars, output_vars, ID = None):
        super().__init__(input_vars, output_vars, ID = ID)

    def generate_implementation(self, implementation_type='python', unroll=False):
        return []

    def generate_model(self, model_type='sat'):
        return []


class CopyOperator(Operator):  # Operator that duplicates one input into multiple outputs: b_0, b_1, ..., b_n = a
    def __init__(self, input_vars, output_vars, ID = None):
        require_variable_count(self.__class__.__name__, input_vars, 1, "input")
        require_min_variable_count(self.__class__.__name__, output_vars, 2, "output")
        super().__init__(input_vars, output_vars, ID=ID)

    def generate_implementation(self, implementation_type='python', unroll=False):
        in_id = self.get_var_ID('in', 0, unroll)
        if implementation_type == 'python':
            return [f"{self.get_var_ID('out', j, unroll)} = {in_id}" for j in range(len(self.output_vars))]
        elif implementation_type == 'c':
            return [f"{self.get_var_ID('out', j, unroll)} = {in_id};" for j in range(len(self.output_vars))]
        elif implementation_type == 'verilog':
            return [f"assign {self.get_var_ID('out', j, unroll)} = {in_id};" for j in range(len(self.output_vars))]
        else:
            raise_unknown_implementation_type(self.__class__.__name__, implementation_type)

    def generate_model(self, model_type='sat'):
        model_list = []
        if model_type in ['sat', 'milp']:
            # Modeling for differential cryptanalysis
            if model_type == "sat" and self.model_version in [self.__class__.__name__ + "_XORDIFF"]:
                var_in, var_out = (self.get_var_model("in", 0), [self.get_var_model("out", i) for i in range(len(self.output_vars))])
                for i in range(self.input_vars[0].bitsize):
                    for output_vars in var_out:
                        model_list.extend(reversed(sat_equivalence_constraints([output_vars[i]], [var_in[i]])))
                return model_list
            elif model_type == "milp" and self.model_version in [self.__class__.__name__ + "_XORDIFF"]:
                var_in, var_out = (self.get_var_model("in", 0), [self.get_var_model("out", i) for i in range(len(self.output_vars))])
                for i in range(self.output_vars[0].bitsize):
                    for output_vars in var_out:
                        model_list.extend(milp_equivalence_constraints([output_vars[i]], [var_in[i]]))
                model_list.append(binary_declaration(var_in, sum(var_out, [])))
                return model_list
            # Modeling for truncated differential cryptanalysis
            elif model_type == "sat" and self.model_version == self.__class__.__name__ + "_TRUNCATEDDIFF":
                var_in, var_out = (self.get_var_model("in", 0, bitwise=False), [self.get_var_model("out", i, bitwise=False) for i in range(len(self.output_vars))])
                for output_vars in var_out:
                    model_list.extend(reversed(sat_equivalence_constraints(var_in, output_vars)))
                return model_list
            elif model_type == "milp" and self.model_version == self.__class__.__name__ + "_TRUNCATEDDIFF":
                var_in, var_out = (self.get_var_model("in", 0, bitwise=False), [self.get_var_model("out", i, bitwise=False) for i in range(len(self.output_vars))])
                for output_vars in var_out:
                    model_list.extend(milp_equivalence_constraints(output_vars, var_in))
                model_list.append(binary_declaration(var_in, sum(var_out, [])))
                return model_list
            # Modeling for linear cryptanalysis
            elif self.model_version == self.__class__.__name__ + "_LINEAR":
                var_in, var_out = (self.get_var_model("in", 0), [self.get_var_model("out", i) for i in range(len(self.output_vars))])
                if len(var_out) == 2: # Two outputs: out1, out2 = in
                    for i in range(self.input_vars[0].bitsize):
                        model_list.extend(gen_xor_constraints(var_in[i], var_out[0][i], var_out[1][i], model_type))
                elif len(var_out) >= 3: # n outputs: out1, out2, ..., outn = in
                    for i in range(self.input_vars[0].bitsize):
                        if model_type == 'milp':
                            v_dummy = f"{self.ID}_d_{i}"
                        else:
                            v_dummy = None
                        model_list.extend(gen_nxor_constraints([var_out[j][i] for j in range(len(var_out))], var_in[i], model_type=model_type, v_dummy=v_dummy))
                return model_list
            # Modeling for truncated linear cryptanalysis
            elif len(self.output_vars) == 2 and self.model_version == self.__class__.__name__ + "_TRUNCATEDLINEAR":
                var_in, var_out1, var_out2 = (self.get_var_model("in", 0, bitwise=False),  self.get_var_model("out", 0, bitwise=False), self.get_var_model("out", 1, bitwise=False))
                model_list.extend(gen_word_xor_constraints(var_out1[0], var_out2[0], var_in[0], model_type))
                return model_list
            elif len(self.output_vars) >= 3 and model_type == "milp" and self.model_version == self.__class__.__name__ + "_TRUNCATEDLINEAR":
                var_in, var_out = (self.get_var_model("in", 0, bitwise=False), [self.get_var_model("out", i, bitwise=False) for i in range(len(self.output_vars))])
                model_list.extend(gen_word_nxor_constraints([var_out[j][0] for j in range(len(var_out))], var_in[0], model_type))
                return model_list
            else: RaiseExceptionVersionNotExisting(str(self.__class__.__name__), self.model_version, model_type)
        elif model_type == 'cp': RaiseExceptionVersionNotExisting(str(self.__class__.__name__), self.model_version, model_type)
        else: raise_unknown_model_type(self.__class__.__name__, model_type)



class Equal(UnaryOperator):  # Operator assigning equality between the input variable and output variable (must be of same bitsize)
    def __init__(self, input_vars, output_vars, ID = None):
        super().__init__(input_vars, output_vars, ID = ID)

    def generate_implementation(self, implementation_type='python', unroll=False):
        if implementation_type == 'python':
            return [self.get_var_ID('out', 0, unroll) + ' = ' + self.get_var_ID('in', 0, unroll)]
        elif implementation_type == 'c':
            return [self.get_var_ID('out', 0, unroll) + ' = ' + self.get_var_ID('in', 0, unroll) + ';']
        elif implementation_type == 'verilog':
            return ["assign " + self.get_var_ID('out', 0, unroll) + ' = ' + self.get_var_ID('in', 0, unroll) + ';']
        else: raise_unknown_implementation_type(self.__class__.__name__, implementation_type)

    def generate_model(self, model_type='sat'):
        if model_type == 'sat':
            if self.model_version in [self.__class__.__name__ + "_XORDIFF", self.__class__.__name__ + "_LINEAR"]:
                var_in, var_out = (self.get_var_model("in", 0), self.get_var_model("out", 0))
                return sat_equivalence_constraints(var_in, var_out)
            elif self.model_version in [self.__class__.__name__ + "_TRUNCATEDDIFF", self.__class__.__name__ + "_TRUNCATEDLINEAR"]:
                var_in, var_out = (self.get_var_model("in", 0, bitwise=False), self.get_var_model("out", 0, bitwise=False))
                return [f"-{var_in[0]} {var_out[0]}", f"{var_in[0]} -{var_out[0]}"]
            else: RaiseExceptionVersionNotExisting(str(self.__class__.__name__), self.model_version, model_type)
        elif model_type == 'milp':
            if self.model_version in [self.__class__.__name__ + "_XORDIFF", self.__class__.__name__ + "_LINEAR"]:
                var_in, var_out = (self.get_var_model("in", 0), self.get_var_model("out", 0))
                model_list = milp_equivalence_constraints(var_in, var_out)
                model_list.append(binary_declaration(var_in, var_out))
                return model_list
            elif self.model_version in [self.__class__.__name__ + "_TRUNCATEDDIFF", self.__class__.__name__ + "_TRUNCATEDLINEAR"]:
                var_in, var_out = (self.get_var_model("in", 0, bitwise=False), self.get_var_model("out", 0, bitwise=False))
                model_list = [f"{var_in[0]} - {var_out[0]} = 0"]
                model_list.append(binary_declaration(var_in, var_out))
                return model_list
            else: RaiseExceptionVersionNotExisting(str(self.__class__.__name__), self.model_version, model_type)
        elif model_type == 'cp': RaiseExceptionVersionNotExisting(str(self.__class__.__name__), self.model_version, model_type)
        else: raise_unknown_model_type(self.__class__.__name__, model_type)


class Rot(UnaryOperator):     # Operator for the rotation function: rotation of the input variable to the output variable with "direction" ('l' or 'r') and "amount" of bits
    def __init__(self, input_vars, output_vars, direction, amount, ID = None):
        super().__init__(input_vars, output_vars, ID = ID)
        if direction not in {'l', 'r'}:
            raise ValueError(f"{self.__class__.__name__}: direction must be 'l' or 'r', got '{direction}'")
        self.direction = direction
        if amount <= 0 or amount >= input_vars[0].bitsize:
            raise ValueError(f"{self.__class__.__name__}: amount must satisfy 0 < amount < bitsize ({input_vars[0].bitsize}), got {amount}")
        self.amount = amount

    def generate_implementation(self, implementation_type='python', unroll=False):
        lhs = self.get_var_ID('out', 0, unroll)
        source = self.get_var_ID('in', 0, unroll)
        bitsize = self.input_vars[0].bitsize
        macro = "ROTR" if self.direction == 'r' else "ROTL"

        if implementation_type == 'python':
            return [f"{lhs} = {macro}({source}, {self.amount}, {bitsize})"]
        elif implementation_type == 'c':
            return [f"{lhs} = {macro}({source}, {self.amount}, {bitsize});"]
        elif implementation_type == 'verilog':
            return [f"assign {lhs} = `{macro}({source}, {self.amount}, {bitsize});"]
        else: raise_unknown_implementation_type(self.__class__.__name__, implementation_type)

    def generate_implementation_header_unique(self, implementation_type='python'):
        if implementation_type == 'python':
            return ["#Rotation Macros ", "def ROTL(n, d, bitsize): return ((n << d) | (n >> (bitsize - d))) & (2**bitsize - 1)", "def ROTR(n, d, bitsize): return ((n >> d) | (n << (bitsize - d))) & (2**bitsize - 1)"]
        elif implementation_type == 'c':
            if self.input_vars[0].bitsize < 32:
                return ["//Rotation Macros", "#define ROTL(n, d, bitsize) (((n << d) | (n >> (bitsize - d))) & ((1<<bitsize) - 1)) ", "#define ROTR(n, d, bitsize) (((n >> d) | (n << (bitsize - d))) & ((1<<bitsize) - 1))"]
            elif 32 <= self.input_vars[0].bitsize < 64:
                return ["//Rotation Macros", "#define ROTL(n, d, bitsize) (((n << d) | (n >> ((unsigned long long)(bitsize) - d))) & ((1ULL << (bitsize)) - 1))", "#define ROTR(n, d, bitsize) (((n >> d) | (n << ((unsigned long long)(bitsize) - d))) & ((1ULL << (bitsize)) - 1))"]
            else:
                return ["//Rotation Macros", "#define ROTL(n, d, bitsize) (((n << d) | (n >> ((__uint128_t)(bitsize) - d))) & (((__uint128_t)1 << (bitsize)) - 1))", "#define ROTR(n, d, bitsize) (((n >> d) | (n << ((__uint128_t)(bitsize) - d))) & (((__uint128_t)1 << (bitsize)) - 1))"]
        elif implementation_type == 'verilog':
            return ["//Rotation Macros", "`define ROTL(n, d, bitsize) {n[bitsize-1-d:0],n[bitsize-1:bitsize-d]}", "`define ROTR(n, d, bitsize) {n[d-1:0],n[bitsize-1:d]}"]
        else: return None

    def generate_model(self, model_type='sat'):
        if model_type == 'sat':
            var_in, var_out = (self.get_var_model("in", 0), self.get_var_model("out", 0))
            if (self.direction =='r' and self.model_version in [self.__class__.__name__ + "_XORDIFF", self.__class__.__name__ + "_LINEAR"]):
                return [clause for i in range(len(var_in)) for clause in (f"-{var_in[i]} {var_out[(i+self.amount)%len(var_in)]}", f"{var_in[i]} -{var_out[(i+self.amount)%len(var_in)]}")]
            elif (self.direction =='l' and self.model_version in [self.__class__.__name__ + "_XORDIFF", self.__class__.__name__ + "_LINEAR"]):
                return [clause for i in range(len(var_in)) for clause in (f"-{var_in[(i+self.amount)%len(var_in)]} {var_out[i]}", f"{var_in[(i+self.amount)%len(var_in)]} -{var_out[i]}")]
            else: RaiseExceptionVersionNotExisting(str(self.__class__.__name__), self.model_version, model_type)
        elif model_type == 'milp':
            var_in, var_out = (self.get_var_model("in", 0), self.get_var_model("out", 0))
            if (self.direction == 'r' and self.model_version in [self.__class__.__name__ + "_XORDIFF", self.__class__.__name__ + "_LINEAR"]):
                model_list = [f'{var_in[i]} - {var_out[(i + self.amount) % len(var_in)]} = 0' for i in range(len(var_in))]
                model_list.append(binary_declaration(var_in, var_out))
                return model_list
            elif (self.direction =='l' and self.model_version in [self.__class__.__name__ + "_XORDIFF", self.__class__.__name__ + "_LINEAR"]):
                model_list = [f'{var_in[(i+self.amount)%len(var_in)]} - {var_out[i]} = 0' for i in range(len(var_in))]
                model_list.append(binary_declaration(var_in, var_out))
                return  model_list
            else: RaiseExceptionVersionNotExisting(str(self.__class__.__name__), self.model_version, model_type)
        elif model_type == 'cp': RaiseExceptionVersionNotExisting(str(self.__class__.__name__), self.model_version, model_type)
        else: raise_unknown_model_type(self.__class__.__name__, model_type)


class Shift(UnaryOperator):    # Operator for the shift function: shift of the input variable to the output variable with "direction" ('l' or 'r') and "amount" of bits
    def __init__(self, input_vars, output_vars, direction, amount, ID = None):
        super().__init__(input_vars, output_vars, ID = ID)
        if direction not in {'l', 'r'}:
            raise ValueError(f"{self.__class__.__name__}: direction must be 'l' or 'r', got '{direction}'")
        self.direction = direction
        if amount <= 0 or amount >= input_vars[0].bitsize:
            raise ValueError(f"{self.__class__.__name__}: amount must satisfy 0 < amount < bitsize ({input_vars[0].bitsize}), got {amount}")
        self.amount = amount

    def generate_implementation(self, implementation_type='python', unroll=False):
        lhs = self.get_var_ID('out', 0, unroll)
        source = self.get_var_ID('in', 0, unroll)
        shift_operator = ">>" if self.direction == 'r' else "<<"
        bitsize = self.input_vars[0].bitsize

        if implementation_type == 'python':
            return [f"{lhs} = ({source} {shift_operator} {self.amount}) & (2**{bitsize} - 1)"]
        elif implementation_type == 'c':
            return [f"{lhs} = ({source} {shift_operator} {self.amount}) & ((1<<{bitsize}) - 1);"]
        elif implementation_type == 'verilog':
            return [f"assign {lhs} = ({source} {shift_operator} {self.amount}) & ((1<<{bitsize}) - 1);"]
        else: raise_unknown_implementation_type(self.__class__.__name__, implementation_type)

    def generate_model(self, model_type='sat'):
        if model_type == 'sat':
            var_in, var_out = (self.get_var_model("in", 0), self.get_var_model("out", 0))
            n = len(var_in)
            s = self.amount

            def eq_clause(a, b):
                return [f"-{a} {b}", f"{a} -{b}"]

            if self.direction == 'r' and self.model_version == self.__class__.__name__ + "_XORDIFF":
                model_list = [f"-{var_out[i]}" for i in range(s)]
                model_list += [
                    clause
                    for i in range(n - s)
                    for clause in eq_clause(var_in[i], var_out[i + s])
                ]
                model_list += [f"{var_in[i]} -{var_in[i]}" for i in range(n - s, n)]
                return model_list

            elif self.direction == 'l' and self.model_version == self.__class__.__name__ + "_XORDIFF":
                model_list = [f"{var_in[i]} -{var_in[i]}" for i in range(s)]
                model_list += [
                    clause
                    for i in range(n - s)
                    for clause in eq_clause(var_in[i + s], var_out[i])
                ]
                model_list += [f"-{var_out[i]}" for i in range(n - s, n)]
                return model_list

            elif self.direction == 'r' and self.model_version == self.__class__.__name__ + "_LINEAR":
                model_list = [f"{var_out[i]} -{var_out[i]}" for i in range(s)]
                model_list += [
                    clause
                    for i in range(n - s)
                    for clause in eq_clause(var_in[i], var_out[i + s])
                ]
                model_list += [f"-{var_in[i]}" for i in range(n - s, n)]
                return model_list

            elif self.direction == 'l' and self.model_version == self.__class__.__name__ + "_LINEAR":
                model_list = [f"-{var_in[i]}" for i in range(s)]
                model_list += [
                    clause
                    for i in range(n - s)
                    for clause in eq_clause(var_in[i + s], var_out[i])
                ]
                model_list += [f"{var_out[i]} -{var_out[i]}" for i in range(n - s, n)]
                return model_list
            else: RaiseExceptionVersionNotExisting(str(self.__class__.__name__), self.model_version, model_type)
        elif model_type == 'milp':
            var_in, var_out = (self.get_var_model("in", 0), self.get_var_model("out", 0))
            n = len(var_in)
            s = self.amount

            if self.direction == 'r' and self.model_version == self.__class__.__name__ + "_XORDIFF":
                model_list = [f'{var_out[i]} = 0' for i in range(s)]
                model_list += [f'{var_in[i]} - {var_out[i + s]} = 0' for i in range(n - s)]
                model_list.append(binary_declaration(var_in, var_out))
                return model_list

            elif self.direction == 'l' and self.model_version == self.__class__.__name__ + "_XORDIFF":
                model_list = [f'{var_in[i + s]} - {var_out[i]} = 0' for i in range(n - s)]
                model_list += [f'{var_out[i]} = 0' for i in range(n - s, n)]
                model_list.append(binary_declaration(var_in, var_out))
                return model_list

            elif self.direction == 'r' and self.model_version == self.__class__.__name__ + "_LINEAR":
                model_list = [f'{var_in[i]} - {var_out[i + s]} = 0' for i in range(n - s)]
                model_list += [f'{var_in[i]} = 0' for i in range(n - s, n)]
                model_list.append(binary_declaration(var_in, var_out))
                return model_list

            elif self.direction == 'l' and self.model_version == self.__class__.__name__ + "_LINEAR":
                model_list = [f'{var_in[i]} = 0' for i in range(s)]
                model_list += [f'{var_in[i + s]} - {var_out[i]} = 0' for i in range(n - s)]
                model_list.append(binary_declaration(var_in, var_out))
                return model_list
            else: RaiseExceptionVersionNotExisting(str(self.__class__.__name__), self.model_version, model_type)
        elif model_type == 'cp': RaiseExceptionVersionNotExisting(str(self.__class__.__name__), self.model_version, model_type)
        else: raise_unknown_model_type(self.__class__.__name__, model_type)


class CustomOP(Operator):   # generic custom operator (to be defined by the user)
    """Abstract base for user-defined operators.

    Subclasses should provide their own implementation and model generation.
    """

    def __init__(self, input_vars, output_vars, ID = None):
        super().__init__(input_vars, output_vars, ID=ID)
