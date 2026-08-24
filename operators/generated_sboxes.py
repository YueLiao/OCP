"""Agent-generated S-box classes, kept OUT of the tracked operators/Sbox.py."""
from operators.Sbox import Sbox


class SmokeSPN_Sbox(Sbox):  # auto-added by OCP-agent
    def __init__(self, input_vars, output_vars, ID=None):
        super().__init__(input_vars, output_vars, 4, 4, ID=ID)
        self.table = [12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2]


class Midori_Sbox(Sbox):  # auto-added by OCP-agent
    def __init__(self, input_vars, output_vars, ID=None):
        super().__init__(input_vars, output_vars, 4, 4, ID=ID)
        self.table = [12, 10, 13, 3, 14, 11, 15, 7, 8, 9, 1, 5, 0, 2, 4, 6]
