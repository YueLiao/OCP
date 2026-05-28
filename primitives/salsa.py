from primitives.primitives import Permutation
from primitives.arx import (
    add_feedforward_final_round,
    add_salsa_quarter_round_layers,
    copy_state_to_temp_words,
    salsa_quarter_rounds,
)
import variables.variables as var


# The Salsa internal permutation
class Salsa_permutation(Permutation):
    def __init__(self, name, s_input, s_output, nbr_rounds=None, represent_mode=0):
        """
        Initialize the Salsa internal permutation
        :param name: Name of the permutation
        :param s_input: Input state
        :param s_output: Output state
        :param nbr_rounds: Number of rounds
        :param represent_mode: Integer specifying the mode of representation used for encoding the permutation.
        """
        
        if represent_mode==0:
            if nbr_rounds ==None: nbr_rounds = 20
            nbr_layers = 12 # 1 for each of the 12 operations in 1 quarter round
            nbr_words = 16 # Words in the state of Salsa
            nbr_temp_words = 4 # Temporary words to store the internal states
            word_bitsize = 32
            super().__init__(name, s_input, s_output, nbr_rounds, [nbr_layers, nbr_words, nbr_temp_words, word_bitsize])
            S = self.functions["PERMUTATION"]

            TW  = [16,17,18,19]
 
            for i in range(1,nbr_rounds+1):  
                add_salsa_quarter_round_layers(S, i, 0, salsa_quarter_rounds(i), TW)
                                     
    def gen_test_vectors(self):
        # Test vectors from https://cr.yp.to/snuffle/salsafamily-20071225.pdf
        IN = [  0x61707865, 0x04030201, 0x08070605, 0x0c0b0a09,
                0x100f0e0d, 0x3320646e, 0x01040103, 0x06020905,
                0x00000007, 0x00000000, 0x79622d32, 0x14131211,
                0x18171615, 0x1c1b1a19, 0x201f1e1d, 0x6b206574]        
        OUT = [ 0x58318d3e, 0x0292df4f, 0xa28d8215, 0xa1aca723,
                0x697a34c7, 0xf2f00ba8, 0x63e9b0a1, 0x27250e3a,
                0xb1c7f1f3, 0x62066edc, 0x66d3ccf1, 0xb0365cf3,
                0x091ad09e, 0x64f0c40f, 0xd60d95ea, 0x00be78c9]
        self.test_vectors.append([[IN], OUT])
    

def SALSA_PERMUTATION(r=None, represent_mode=0, copy_operator=False): 
    my_input, my_output = [var.Variable(32,ID="in"+str(i)) for i in range(16)], [var.Variable(32,ID="out"+str(i)) for i in range(16)]
    my_permutation = Salsa_permutation("SALSA_PERM", my_input, my_output, nbr_rounds=r, represent_mode=represent_mode)
    my_permutation.gen_test_vectors()
    my_permutation.post_initialization(copy_operator=copy_operator)
    return my_permutation    
    



# The Salsa permutation to generate the key stream
class Salsa_keypermutation(Permutation):
    def __init__(self, name, s_input, s_output, nbr_rounds=None, represent_mode=0):
        """
        Initialize the Salsa internal permutation
        :param name: Name of the permutation
        :param s_input: Input state
        :param s_output: Output state
        :param nbr_rounds: Number of rounds
        :param represent_mode: Integer specifying the mode of representation used for encoding the permutation.
        """
        
        if represent_mode==0:
            if nbr_rounds ==None: nbr_rounds = 21 # 21st round is used add the initial state to obtain the final key stream
            nbr_layers = 13 # 1 for each of the 12 operations in 1 quarter round
            nbr_words = 16 # Words in the state of Salsa
            nbr_temp_words = 20 # To retain the initial input for adding with final state to obtain the key stream
            word_bitsize = 32
            super().__init__(name, s_input, s_output, nbr_rounds, [nbr_layers, nbr_words, nbr_temp_words, word_bitsize])
            S = self.functions["PERMUTATION"]

            TW  = [16,17,18,19] # Temporary words to store the internal states
        
            for i in range(1,nbr_rounds+1):  
                # In the first round copy the initial word to temporary words
                if i == 1:
                    copy_state_to_temp_words(S, i, 0, temp_start=20)
                else:
                    S.AddIdentityLayer("Identity", i, 0)


                if i == 21:
                    add_feedforward_final_round(S, i, 1, nbr_layers, temp_start=20)
                else:
                    add_salsa_quarter_round_layers(S, i, 1, salsa_quarter_rounds(i), TW)

    def gen_test_vectors(self):
        # Test vectors from https://cr.yp.to/snuffle/salsafamily-20071225.pdf
        IN = [  0x61707865, 0x04030201, 0x08070605, 0x0c0b0a09,
                0x100f0e0d, 0x3320646e, 0x01040103, 0x06020905,
                0x00000007, 0x00000000, 0x79622d32, 0x14131211,
                0x18171615, 0x1c1b1a19, 0x201f1e1d, 0x6b206574]
        OUT = [ 0xb9a205a3, 0x0695e150, 0xaa94881a, 0xadb7b12c,
                0x798942d4, 0x26107016, 0x64edb1a4, 0x2d27173f,
                0xb1c7f1fa, 0x62066edc, 0xe035fa23, 0xc4496f04,
                0x2131e6b3, 0x810bde28, 0xf62cb407, 0x6bdede3d]
        self.test_vectors.append([[IN], OUT])
    
def SALSA_KEYPERMUTATION(r=None, represent_mode=0, copy_operator=False): 
    my_input, my_output = [var.Variable(32,ID="in"+str(i)) for i in range(16)], [var.Variable(32,ID="out"+str(i)) for i in range(16)]
    my_permutation = Salsa_keypermutation("SALSA_KEYPERM", my_input, my_output, nbr_rounds=r, represent_mode=represent_mode)
    my_permutation.gen_test_vectors()
    my_permutation.post_initialization(copy_operator=copy_operator)
    return my_permutation    

