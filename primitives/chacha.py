from primitives.primitives import Permutation
from primitives.arx import (
    add_chacha_quarter_round_layers,
    add_feedforward_final_round,
    chacha_quarter_rounds,
    copy_state_to_temp_words,
)
import variables.variables as var


# The ChaCha internal permutation
class ChaCha_permutation(Permutation):
    def __init__(self, name, s_input, s_output, nbr_rounds=None, represent_mode=0):
        """
        Initialize the ChaCha internal permutation
        :param name: Name of the permutation
        :param s_input: Input state
        :param s_output: Output state
        :param nbr_rounds: Number of rounds
        :param represent_mode: Integer specifying the mode of representation used for encoding the permutation.
        """
        
        if represent_mode==0:
            if nbr_rounds is None: nbr_rounds = 20
            nbr_layers = 12 # 1 for each of the 12 operations in 1 quarter round
            nbr_words = 16 # Words in the state of Chacha
            nbr_temp_words = 0
            word_bitsize = 32
            super().__init__(name, s_input, s_output, nbr_rounds, [nbr_layers, nbr_words, nbr_temp_words, word_bitsize])
            S = self.functions["PERMUTATION"]
        
            for i in range(1,nbr_rounds+1):  
                add_chacha_quarter_round_layers(S, i, 0, chacha_quarter_rounds(i))
        
    def gen_test_vectors(self):
        # Test vectors from https://datatracker.ietf.org/doc/html/rfc8439
        IN = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574, 0x03020100, 0x07060504, 0x0b0a0908, 0x0f0e0d0c, 0x13121110, 0x17161514, 0x1b1a1918, 0x1f1e1d1c, 0x00000001, 0x09000000, 0x4a000000, 0x00000000]
        OUT = [0x837778ab, 0xe238d763, 0xa67ae21e, 0x5950bb2f, 0xc4f2d0c7, 0xfc62bb2f, 0x8fa018fc, 0x3f5ec7b7, 0x335271c2, 0xf29489f3, 0xeabda8fc, 0x82e46ebd, 0xd19c12b4, 0xb04e16de, 0x9e83d0cb, 0x4e3c50a2]
        self.test_vectors.append([[IN], OUT])


def CHACHA_PERMUTATION(r=None, represent_mode=0, copy_operator=False): 
    my_input, my_output = [var.Variable(32,ID="in"+str(i)) for i in range(16)], [var.Variable(32,ID="out"+str(i)) for i in range(16)]
    my_permutation = ChaCha_permutation("ChaCha_PERM", my_input, my_output, nbr_rounds=r, represent_mode=represent_mode)
    my_permutation.gen_test_vectors()
    my_permutation.post_initialization(copy_operator=copy_operator)
    return my_permutation


# The ChaCha permutation to generate the key stream
class ChaCha_keypermutation(Permutation):
    def __init__(self, name, s_input, s_output, nbr_rounds=None, represent_mode=0):
        """
        Initialize the ChaCha internal permutation
        :param name: Name of the permutation
        :param s_input: Input state
        :param s_output: Output state
        :param nbr_rounds: Number of rounds
        :param represent_mode: Integer specifying the mode of representation used for encoding the permutation.
        """
        
        if represent_mode==0:
            if nbr_rounds is None: nbr_rounds = 21 # 21st round is used add the initial state to obtain the final key stream
            nbr_layers = 13 # 1 for each of the 12 operations in 1 quarter round
            nbr_words = 16 # Words in the state of Chacha
            nbr_temp_words = 16 # To retain the initial input for adding with final state to obtain the key stream
            word_bitsize = 32
            super().__init__(name, s_input, s_output, nbr_rounds, [nbr_layers, nbr_words, nbr_temp_words, word_bitsize])
            S = self.functions["PERMUTATION"]
        
            for i in range(1,nbr_rounds+1):  
                # In the first round copy the initial word to temporary words
                if i == 1:
                    copy_state_to_temp_words(S, i, 0, temp_start=16)
                else:
                    S.AddIdentityLayer("Identity", i, 0)


                if i == 21:
                    add_feedforward_final_round(S, i, 1, nbr_layers, temp_start=16)
                else:
                    add_chacha_quarter_round_layers(S, i, 1, chacha_quarter_rounds(i))

    def gen_test_vectors(self):
        # Test vectors from https://datatracker.ietf.org/doc/html/rfc8439
        IN = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574, 0x03020100, 0x07060504, 0x0b0a0908, 0x0f0e0d0c, 0x13121110, 0x17161514, 0x1b1a1918, 0x1f1e1d1c, 0x00000001, 0x09000000, 0x4a000000, 0x00000000]
        OUT = [0xe4e7f110, 0x15593bd1, 0x1fdd0f50, 0xc47120a3, 0xc7f4d1c7, 0x0368c033, 0x9aaa2204, 0x4e6cd4c3, 0x466482d2, 0x09aa9f07, 0x05d7c214, 0xa2028bd9, 0xd19c12b5, 0xb94e16de, 0xe883d0cb, 0x4e3c50a2]
        self.test_vectors.append([[IN], OUT])
    

def CHACHA_KEYPERMUTATION(r=None, represent_mode=0, copy_operator=False): 
    my_input, my_output = [var.Variable(32,ID="in"+str(i)) for i in range(16)], [var.Variable(32,ID="out"+str(i)) for i in range(16)]
    my_permutation = ChaCha_keypermutation("ChaCha_KEYPERM", my_input, my_output, nbr_rounds=r, represent_mode=represent_mode)
    my_permutation.gen_test_vectors()
    my_permutation.post_initialization(copy_operator=copy_operator)
    return my_permutation
