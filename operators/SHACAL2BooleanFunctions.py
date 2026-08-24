# Not ready for use, still in development.
import copy
from operators.operators import (
    Operator,
    Rot,
    Shift,
    RaiseExceptionVersionNotExisting,
    raise_unknown_implementation_type,
    raise_unknown_model_type,
)
from operators.boolean_operators import NOT, AND, N_XOR, XOR


_SIGMA_SUM_SPECS = {
    "sigma0": {
        512: ((7, 18), 3),
        1024: ((1, 8), 7),
    },
    "sigma1": {
        512: ((17, 19), 10),
        1024: ((19, 61), 6),
    },
    "sum0": {
        512: (2, 13, 22),
        1024: (28, 34, 39),
    },
    "sum1": {
        512: (6, 11, 25),
        1024: (14, 18, 41),
    },
}


def _get_sigma_sum_spec(name, keysize):
    try:
        return _SIGMA_SUM_SPECS[name][keysize]
    except KeyError as exc:
        raise ValueError(f"Unsupported SHACAL2 keysize {keysize!r}; expected 512 or 1024") from exc


def _generate_layered_header(layers, implementation_type):
    seen_class_names = set()
    code_list = []
    for layer in layers:
        for cons in layer:
            class_name = cons.__class__.__name__
            if class_name in seen_class_names:
                continue
            seen_class_names.add(class_name)
            header = cons.generate_implementation_header(implementation_type)
            if header is not None:
                code_list += header
            if class_name == 'Rot':
                code_list += cons.generate_implementation_header_unique(implementation_type)
    return code_list


def _generate_layered_implementation(owner, implementation_type, unroll):
    if implementation_type not in ['python', 'c']:
        raise_unknown_implementation_type(str(owner.__class__.__name__), implementation_type)

    code_list = []
    if implementation_type == 'c':
        var_ids = [
            var.ID if unroll else var.remove_round_from_ID()
            for i in range(1, len(owner.vars) - 1)
            for var in owner.vars[i]
        ]
        code_list.append("uint8_t " + ", ".join(var_ids) + ";")

    for layer in owner.layers:
        for cons in layer:
            code_list += cons.generate_implementation(implementation_type, unroll=unroll)
    return code_list


def _generate_layered_model(owner, model_type, unroll):
    if model_type in ['sat', 'milp']:
        model_list = []
        for layer in owner.layers:
            for cons in layer:
                cons.model_version = owner.model_version.replace(owner.__class__.__name__, cons.__class__.__name__)
                model_list += cons.generate_model(model_type)
        return model_list
    elif model_type == 'cp':
        RaiseExceptionVersionNotExisting(str(owner.__class__.__name__), owner.model_version, model_type)
    else:
        raise_unknown_model_type(str(owner.__class__.__name__), model_type)


class SHACAL2_Sigma0(Operator):
    def __init__(self, input_vars, output_vars, keysize=512, ID = None):
        super().__init__(input_vars, output_vars, ID = ID)
        self.layers = []
        self.vars = []

        self.vars.append(input_vars)

        temp_vars = copy.deepcopy(input_vars) + copy.deepcopy(input_vars) + copy.deepcopy(input_vars)
        for i in range(3):
            temp_vars[i].ID += '_' + str(i)
        self.vars.append(temp_vars)

        self.vars.append(output_vars)

        rotation_offsets, shift_offset = _get_sigma_sum_spec("sigma0", keysize)
        rotations = [
            [self.vars[0][0], self.vars[1][0], 'r', rotation_offsets[0], "SIGMA0_ROT_1"],
            [self.vars[0][0], self.vars[1][1], 'r', rotation_offsets[1], "SIGMA0_ROT_2"],
        ]
        shift = [self.vars[0][0], self.vars[1][2], 'r', shift_offset, "SIGMA0_SHR_1"]
        
        self.layers.append([Rot([rotation[0]], [rotation[1]], rotation[2], rotation[3], rotation[4]) for rotation in rotations] + [Shift([shift[0]], [shift[1]], shift[2], shift[3], shift[4])])
        self.layers.append([N_XOR([self.vars[1][0], self.vars[1][1], self.vars[1][2]], [self.vars[2][0]], "SUM0_NXOR1")])

    def generate_implementation_header(self, implementation_type='python'):
        return _generate_layered_header(self.layers, implementation_type)
    
    def generate_implementation(self, implementation_type='python', unroll=False):
        return _generate_layered_implementation(self, implementation_type, unroll)
        
    def generate_model(self, model_type='sat', unroll=True):
        return _generate_layered_model(self, model_type, unroll)


class SHACAL2_Sigma1(Operator):
    def __init__(self, input_vars, output_vars, keysize=512, ID = None):
        super().__init__(input_vars, output_vars, ID = ID)
        self.layers = []
        self.vars = []

        self.vars.append(input_vars)

        temp_vars = copy.deepcopy(input_vars) + copy.deepcopy(input_vars) + copy.deepcopy(input_vars)
        for i in range(3):
            temp_vars[i].ID += '_' + str(i)
        self.vars.append(temp_vars)

        self.vars.append(output_vars)

        rotation_offsets, shift_offset = _get_sigma_sum_spec("sigma1", keysize)
        rotations = [
            [self.vars[0][0], self.vars[1][0], 'r', rotation_offsets[0], "SIGMA1_ROT_1"],
            [self.vars[0][0], self.vars[1][1], 'r', rotation_offsets[1], "SIGMA1_ROT_2"],
        ]
        shift = [self.vars[0][0], self.vars[1][2], 'r', shift_offset, "SIGMA1_SHR_1"]
        
        self.layers.append([Rot([rotation[0]], [rotation[1]], rotation[2], rotation[3], rotation[4]) for rotation in rotations] + [Shift([shift[0]], [shift[1]], shift[2], shift[3], shift[4])])
        self.layers.append([N_XOR([self.vars[1][0], self.vars[1][1], self.vars[1][2]], [self.vars[2][0]], "SUM0_NXOR1")])

    def generate_implementation_header(self, implementation_type='python'):
        return _generate_layered_header(self.layers, implementation_type)
    
    def generate_implementation(self, implementation_type='python', unroll=False):
        return _generate_layered_implementation(self, implementation_type, unroll)
        
    def generate_model(self, model_type='sat', unroll=True):
        return _generate_layered_model(self, model_type, unroll)



class SHACAL2_Sum0(Operator):
    def __init__(self, input_vars, output_vars, keysize=512, ID = None):
        super().__init__(input_vars, output_vars, ID = ID)
        self.layers = []
        self.vars = []

        self.vars.append(input_vars)

        temp_vars = copy.deepcopy(input_vars) + copy.deepcopy(input_vars) + copy.deepcopy(input_vars)
        for i in range(3):
            temp_vars[i].ID += '_' + str(i)
        self.vars.append(temp_vars)

        self.vars.append(output_vars)

        rotation_offsets = _get_sigma_sum_spec("sum0", keysize)
        rotations = [
            [self.vars[0][0], self.vars[1][0], 'r', rotation_offsets[0], "SUM0_ROT_1"],
            [self.vars[0][0], self.vars[1][1], 'r', rotation_offsets[1], "SUM0_ROT_2"],
            [self.vars[0][0], self.vars[1][2], 'r', rotation_offsets[2], "SUM0_ROT_3"],
        ]
        
        self.layers.append([Rot([rotation[0]], [rotation[1]], rotation[2], rotation[3], rotation[4]) for rotation in rotations])
        self.layers.append([N_XOR([self.vars[1][0], self.vars[1][1], self.vars[1][2]], [self.vars[2][0]], "SUM0_NXOR1")])

        
    def generate_implementation_header(self, implementation_type='python'):
        return _generate_layered_header(self.layers, implementation_type)
    
    def generate_implementation(self, implementation_type='python', unroll=False):
        return _generate_layered_implementation(self, implementation_type, unroll)
        
    def generate_model(self, model_type='sat', unroll=True):
        return _generate_layered_model(self, model_type, unroll)


class SHACAL2_Sum1(Operator):
    def __init__(self, input_vars, output_vars, keysize=512, ID = None):
        super().__init__(input_vars, output_vars, ID = ID)
        self.layers = []
        self.vars = []

        self.vars.append(input_vars)

        temp_vars = copy.deepcopy(input_vars) + copy.deepcopy(input_vars) + copy.deepcopy(input_vars)
        for i in range(3):
            temp_vars[i].ID += '_' + str(i)
        self.vars.append(temp_vars)

        self.vars.append(output_vars)

        rotation_offsets = _get_sigma_sum_spec("sum1", keysize)
        rotations = [
            [self.vars[0][0], self.vars[1][0], 'r', rotation_offsets[0], "SUM1_ROT_1"],
            [self.vars[0][0], self.vars[1][1], 'r', rotation_offsets[1], "SUM1_ROT_2"],
            [self.vars[0][0], self.vars[1][2], 'r', rotation_offsets[2], "SUM1_ROT_3"],
        ]
        
        self.layers.append([Rot([rotation[0]], [rotation[1]], rotation[2], rotation[3], rotation[4]) for rotation in rotations])
        self.layers.append([N_XOR([self.vars[1][0], self.vars[1][1], self.vars[1][2]], [self.vars[2][0]], "SUM0_NXOR1")])

        
    def generate_implementation_header(self, implementation_type='python'):
        return _generate_layered_header(self.layers, implementation_type)
    
    def generate_implementation(self, implementation_type='python', unroll=False):
        return _generate_layered_implementation(self, implementation_type, unroll)
        
    def generate_model(self, model_type='sat', unroll=True):
        return _generate_layered_model(self, model_type, unroll)




class SHACAL2_Maj(Operator):
    def __init__(self, input_vars, output_vars, keysize=512, ID = None):
        super().__init__(input_vars, output_vars, ID = ID)
        self.layers = []
        self.vars = []

        self.vars.append(input_vars)

        temp_vars = copy.deepcopy(input_vars)
        for i in range(3):
            temp_vars[i].ID += '_' + str(i)
        self.vars.append(temp_vars)

        self.vars.append(output_vars)

        ANDOperations = [[self.vars[0][0], self.vars[0][1], self.vars[1][0], "Maj_AND_1"], [self.vars[0][0], self.vars[0][2], self.vars[1][1], "Maj_AND_2"], [self.vars[0][1], self.vars[0][2], self.vars[1][2], "Maj_AND_3"]]

        self.layers.append([AND([ANDOperation[0], ANDOperation[1]], [ANDOperation[2]], ANDOperation[3]) for ANDOperation in ANDOperations])
        self.layers.append([N_XOR([self.vars[1][0], self.vars[1][1], self.vars[1][2]], [self.vars[2][0]], "Maj_NXOR1")])
        
        
    def generate_implementation_header(self, implementation_type='python'):
        return _generate_layered_header(self.layers, implementation_type)
    
    def generate_implementation(self, implementation_type='python', unroll=False):
        return _generate_layered_implementation(self, implementation_type, unroll)
        
    def generate_model(self, model_type='sat', unroll=True):
        return _generate_layered_model(self, model_type, unroll)


class SHACAL2_Ch(Operator):
    def __init__(self, input_vars, output_vars, keysize=512, ID = None):
        super().__init__(input_vars, output_vars, ID = ID)
        self.layers = []
        self.vars = []

        self.vars.append(input_vars)

        temp_var = [copy.deepcopy(input_vars[0])]
        temp_var[0].ID += '_0_0'
        self.vars.append(temp_var)

        
        temp_vars = [copy.deepcopy(input_vars[0])] + [copy.deepcopy(input_vars[1])]
        for i in range(2):
            temp_vars[i].ID += '_1_' + str(i) # 0: e ^ f; 1: NOT e ^ g
        self.vars.append(temp_vars)

        self.vars.append(output_vars)

        NOTOperation = [self.vars[0][0], self.vars[1][0], "Ch_NOT_1"]
        ANDOperations = [[self.vars[0][0], self.vars[0][1], self.vars[2][0], "Ch_AND_1"], 
                         [self.vars[1][0], self.vars[0][2], self.vars[2][1], "Ch_AND_2"]]

        self.layers.append([NOT([NOTOperation[0]], [NOTOperation[1]], NOTOperation[2])])
        self.layers.append([AND([ANDOperation[0], ANDOperation[1]], [ANDOperation[2]], ANDOperation[3]) for ANDOperation in ANDOperations])
        self.layers.append([XOR([self.vars[2][0], self.vars[2][1]], [self.vars[3][0]], "Ch_XOR1")])
      

        
    def generate_implementation_header(self, implementation_type='python'):
        return _generate_layered_header(self.layers, implementation_type)
    
    def generate_implementation(self, implementation_type='python', unroll=False):
        return _generate_layered_implementation(self, implementation_type, unroll)
        
    def generate_model(self, model_type='sat', unroll=True):
        return _generate_layered_model(self, model_type, unroll)
