# LEA: A 128-Bit Block Cipher for Fast Encryption on Common Processors

Deukjo Hong<sup>1(B)</sup>, Jung-Keun Lee<sup>1</sup>, Dong-Chan Kim<sup>1</sup>, Daesung Kwon<sup>1</sup>, Kwon Ho Ryu<sup>1</sup>, and Dong-Geon Lee<sup>2</sup> 

<sup>1</sup> Attached Institute of ETRI, Seoul, Korea Attached Institute of ETRI, Seoul, Korea 

hongdj,jklee,dongchan,ds kwon,jude @ensec.re.kr Information Security & IoT Laboratory, Pusan National University, Busan, South Korea guneez@pusan.ac.kr 

Abstract. We propose a new block cipher LEA, which has 128-bit block size and 128, 192, or 256-bit key size. It provides a high-speed software encryption on general-purpose processors. Our experiments show that LEA is faster than AES on Intel, AMD, ARM, and ColdFire platforms. LEA can be also implemented to have tiny code size. Its hardware implementation has a competitive throughput per area. It is secure against all the existing attacks on block ciphers. 

Keywords: LEA Block cipher Fast encryption 

## 1 Introduction

CPUs and operating systems are continuously developing, and many computing devices work much better than before, with such powerful resources. For example, smart portable devices like smart phones and tablet PCs do not only replace mobile phones but also allow to enjoy various cloud computing and social network services. With those applications, the amount of the private data which people create for their business and life will be significantly increasing. Another example is a smart meter, which is a basic unit of an advanced metering infrastructure in a smart grid, recording consumption of electric energy, gathering data for remote reporting, and communicating with the utility for monitoring and billing purpose. For the convenience of management, smart meters are often implemented to perform tasks in software with small CPUs [18]. 

Those data mentioned in the above examples are usually important information which must be protected from various threats in networks. It implies that the wide use of software applications significantly causes the necessity of cryptographic systems on software platforms. With this consideration, we have been interested in a software encryption. Software encryptions are easier to deploy and more cost-efective than hardware ones in many cases. In particular, when a new encryption service is required for already deployed computing environments, a software encryption is more suitable than a hardware one. 

A block cipher is one of the most widely used cryptographic primitives. It is applied to data encryption, message authentication, random bit generation, message hashing and so on. Presumably, the most widely used block cipher in the world is AES [27] which has been established as various international standards. AES shows good performance figures on most software and hardware platforms and is generally considered to be secure after surviving about 15 years of comprehensive cryptanalysis though some weaknesses have been found. Since AES, many block ciphers have been designed for hardware lightweight implementation. Some of them were standardized as ISO lightweight cryptography (ISO/IEC 29192-2). The main feature of the lightweight block ciphers is the eficient hardware implementation with low resource. In order to achieve that goal, most of them use simple structures with small block sizes and large number of rounds. However, those design approaches usually lead to low performance, and is far from our consideration for software encryption. Consequently, we have designed a new block cipher providing a fast encryption on common software platforms. 

## 1.1 Contribution

We propose a new block cipher LEA. It has the block size of 128 bits and the key size of 128, 192, or 256 bits. We denote the algorithms with 128-bit, 192-bit, and 256-bit keys by LEA-128, LEA-192, and LEA-256, respectively. The structure of LEA has the following features. 

1. LEA consists of only ARX (modular Addition, bitwise Rotation, and bitwise XOR) operations for 32-bit words. Those operations are well-supported and fast in many 32-bit and 64-bit platforms. Moreover, we suppose that the usage of 32-bit and 64-bit processors will grow rapidly compared to 8-bit or 16-bit ones. 

2. The ARX operations contribute to the encryption and key schedule procedures in eficient and parallel way. Our arrangement of operations does not only lead to fast software encryption and small size code, but also strong resistance against the attacks using the properties of a particular operation. 

3. The last round function of LEA is the same as other round functions, while many block cipher including DES and AES have special last round functions which are somewhat diferent from other round functions. This is for the encryption speed in both software and hardware because we think the block cipher encryption is more frequently used than decryption. 

4. The key schedule of LEA has a simple structure without any interleaving between 32-bit key words. It is good for the eficiency, and does not cause any weakness. 

Security. Our goal for the security of LEA is to get the resistance against all the existing attacks for block ciphers and to provide enough security margin. To achieve this goal, we firstly found the minimum number R of rounds for LEA to resist against all the known cryptanalytic techniques for each key size. Then we determined the number of rounds of LEA as around $3 R / 2$ to prepare for the unknown attacks to appear in future. 

Eficiency. LEA provides a fast encryption on many platforms. Our experiments measuring the speed for one-block encryption on the platforms of Intel, AMD, ARM and ColdFire show that even a C level implementation of LEA is very fast. It implies that the evaluation of LEA encryption requires the light overhead to CPUs. Note that the light overhead can lead to the low power consumption which is useful for the devices based on batteries. The optimized implementation of LEA-128 for one-block encryption is faster than those of AES-128 publicly reported [25,47], on our test platforms. To objectivity, we used the announced facts for comparison instead of implementing AES. 

LEA can be implemented with SIMD operations supported by Intel and AMD CPUs such that it encrypts 4 blocks simultaneously. It is useful for the highly fast encryption with ECB or CTR modes under a powerful environment like a server-based computing. Our experiments on Intel Core 2 Quad Q6600 and Intel Core i7-800 show that the speed of the 4-block SIMD implementation of LEA-128 is about 2 times and 1.7 times faster than the best records of the multi-block encryption codes of AES-128 [35], respectively. 

We also found that LEA is implemented with a small code-size. The small-size implementation is useful in a memory-limited environment. LEA-128 is implemented with less than 600 and 750 bytes on the platforms of ARM926EJ-S and ColdFire MCF5213, respectively, while AES-128 is known to be implemented with around 2,400 and 960 bytes on the platforms of ARM7TDMI and ColdFire v2, respectively. 

Comparison with Other Ciphers. We compare LEA to other ciphers in order to explain why it is meaningful to propose this new block cipher. 

AES. AES was designed based on design and analysis techniques by 2000, and cryptanalysis of block ciphers has been continuously researched and developed. Recent several attacks have pointed out some weaknesses for AES. In [11], Biryukov et al. presented a chosen-key distinguisher for full 14-round AES-256 and converted it to a key-recovery attack for a weak key class with the complexities of $2 ^ { 1 3 1 }$ time and $\dot { 2 } ^ { 6 5 }$ memory. In [10], Biryukov and Khovratovich presented related-key boomerang attacks on full 14-round AES-256 with $2 ^ { 9 9 . 5 }$ time and data complexities and AES-192 with $2 ^ { 1 7 6 }$ time and $2 ^ { 1 2 3 }$ data complexities. In [14], Bogdanov et al. used biclique techniques to make key recovery attacks on full AES-128, AES-192, and AES-256 with time complexities $2 ^ { 1 \mathrm { \check { 2 } 6 . 1 } } , 2 ^ { 1 8 9 . 7 }$ , and $2 ^ { 2 5 4 . 4 }$ , respectively. LEA is designed based on the latest design and analysis techniques and we checked that LEA is secure and has suficient security margin against all the existing attacks. 

Furthermore, as we already mentioned, LEA provides better software encryptions in speed and size on many platforms than AES. 

Block ciphers with ARX structure. TEA [56] and XTEA [46] are Feistel block ciphers with simple round function and key schedule. Their encryption speeds are not fast because they have the block length of 64 bits shorter than LEA and 64 rounds more than LEA. Additionally, there are full-round attacks [37,58] on TEA and XXTEA [57], which is the third algorithm of TEA family. 

At the AES competition, RC6 [49] was regarded as faster than Rijndael [21], which is the AES winner, on many software platforms. However, parallelism ofered by modern CPUs is not exploited well with RC6, and the performance of recent implementation of AES exceeds that of RC6. 

HIGHT [31] is a lightweight block cipher based on 8-bit ARX operations. So, it is not suitable for fast encryption on 32-bit CPUs. Recently, full-round attacks on HIGHT have been published [32,41]. 

Hash functions often adopt the ARX structure for the high performance on various platforms, similarly to our design goal [2,26]. Most of them have block ciphers as a component for building compression and hash functions. They are even secure against attacks for block ciphers. However, hash functions and block ciphers are diferent in the usage. In particular, most block ciphers in the hash functions have much larger block and key sizes than those usually required for the security and application of block ciphers. 

Recently, NSA published two block cipher families SPECK and SIMON [3]. SPECK is a typical ARX cipher and SIMON consists of ANDs, rotations, and XORs. They have various parameters. The algorithms with 128-bit block are comparable with LEA. The Performance of LEA is faster than SIMON in both 32- and 64-bit processors. Since SPECK uses 64-bit addition with 128-bit block, its performance exceeds that of LEA only in 64-bit processors but LEA is more suitable for most 32-bit processors. 

Lightweight block ciphers. Many lightweight block ciphers like HIGHT [31], PRESENT [13], LED [30], and Piccolo [51] have short block size and large number of rounds and their software encryptions are usually not fast. Although [43] provides fast bitslice implementation of PRESENT and Piccolo, SIMD implementation of LEA is faster than them. Furthermore, a short block size is not proper for encrypting huge data because some modes of operation can allow security leakage like a ciphertext-matching attack. 

KLEIN [28] is designed to be faster than AES on 8-bit and 16-bit platforms, while our targets are 32-bit and 64-bit platforms. CLEFIA [52] has the same block and key size as AES and the performance of its software encryption is close to that of AES on AMD Athlon TM Processor 4000+. However, as far as we know, it does not claim higher software performance than AES. Recently, PRINCE [16] was proposed as a low-latency block cipher which has good performance in software and hardware implementations, but its security goal is somewhat diferent from that for the general-purpose block ciphers. 

Stream ciphers. Several stream ciphers such as Salsa20 [4] are based on ARX operations, but we think the block cipher is not totally comparable to the stream cipher because they do not always have the same applications. 

## 1.2 Organization

The remaining part is organized as follows. Section 2 describes the specification of LEA. In Sect. 3, we introduce design principles. In Sect. 4, we present the security analysis results for existing cryptanalytic techniques. In Sect. 5, we explain the implementation results. Section 6 is the conclusion of our paper. 

## 2 Specification of LEA

LEA is a block cipher with 128-bit block. Key size is 128-bit, 192-bit, and 256- bit. The number of rounds is 24 for 128-bit keys, 28 for 192-bit keys, and 32 for 256-bit keys. In Sect. 2.1, we introduce notations which are often used in this paper. We explain how the key schedule generates round keys from the master key in Sect. 2.3. We explain how the encryption procedure converts a plaintext to a ciphertext in Sect. 2.4. We omit the description of the decryption procedure because it is simply considered as the inverse of the encryption procedure. 

## 2.1 Notations

– P: a 128-bit plaintext, consisting of four 32-bit words $P = ( P [ 0 ] , P [ 1 ] , P [ 2 ]$ $P [ 3 ] )$ 

– C: a 128-bit ciphertext, consisting of four 32-bit words $C = ( C [ 0 ] , C [ 1 ] , C [ 2 ]$ • $C [ 3 ] )$ 

$- \ X _ { i } \colon$ a 128-bit intermediate value (an input of i-th round in the encryption function), consisting of four 32-bit words $X _ { i } = ( X _ { i } [ 0 ] , X _ { i } [ 1 ] , X _ { i } [ 2 ] , X _ { i } [ 3 ] )$ 

$- { \mathrm { ~ \mathop { L e n } } } ( x )$ : the bit-length of a string x 

– K: a master key. It is denoted as a concatenation of 32-bit words. $K =$ $( K [ 0 ] , K [ 1 ] , K [ 2 ] , K [ 3 ] )$ when $\operatorname { L e n } ( K ) = 1 2 8 ; K = ( K [ 0 ] , K [ 1 ] , . . . , K [ 5 ] )$ when $\operatorname { L e n } ( K ) = 1 9 2 ; K = ( K [ 0 ] , K [ 1 ] , . . . , K [ 7 ] )$ when $\mathrm { L e n } ( K ) = 2 5 6$ 

– r: the number of rounds. $r = 2 4$ when $\operatorname { L e n } ( K ) = 1 2 8 ; r = 2 8$ when $\operatorname { L e n } ( K ) =$ $1 9 2 ; r = 3 2$ when $\operatorname { L e n } ( K ) = 2 5 6$ 

$- ~ R K$ : the concatenation of all round keys, defined by $R K = ( R K _ { 0 } , R K _ { 1 }$ $. . . , R K _ { r - 1 } )$ where $R K _ { i }$ is the 192-bit round key for the i-th round. Each $R K _ { i }$ consists of six 32-bit words $R K _ { i } = ( R K _ { i } [ 0 ] , R K _ { i } [ 1 ] , . . . , R K _ { i } [ 5 ] )$ 

– x y: XOR (eXclusive OR) of bit strings x and y with same length 

– x - y: Addition modulo $2 ^ { 3 2 }$ of 32-bit strings x and y 

$\operatorname { R O L } _ { i } ( x )$ : the i-bit left rotation on a 32-bit value x 

$- \ \mathrm { R O R } _ { i } ( x )$ : the i-bit right rotation on a 32-bit value x 

## 2.2 State Representation

Let $a [ 0 ] , a [ 1 ] , . . . ,$ be representation of arrays of bytes. The bytes and the bit ordering within bytes are derived from the 128-bit input sequence input , input , ... as follows: 

$$
a [ i ] = \{i n p u t _ {8 i}, i n p u t _ {8 i + 1},..., i n p u t _ {8 i + 7} \}.
$$

All the operations in the LEA algorithm are 32-bit-word-oriented. The 128-bit plaintext P of LEA is represented as an array of four 32-bit words $P [ 0 ] , P [ 1 ] , P [ 2 ]$ , $P [ 3 ]$ . Each $P [ i ]$ is taken for the input bytes $a [ 0 ] , a [ 1 ] , . . . , a [ 1 5 ]$ as follows: 

$$
P [ i ] = a [ 4 i + 3 ] \| a [ 4 i + 2 ] \| a [ 4 i + 1 ] \| a [ 4 i ] \text { for } 0 \leq i \leq 3.
$$

The key K of LEA is also represented as an array of 32-bit words $K [ 0 ] , K [ 1 ] , . . . ,$ and taken for the input bytes in the same way. Table 1 shows how bits and bytes in the word indexed by 0 are numbered. 


Table 1. Representations for words, bytes, and bits


<table><tr><td>Input bit sequence</td><td>24</td><td><eq>\cdots</eq></td><td>31</td><td>16</td><td><eq>\cdots</eq></td><td>23</td><td>8</td><td><eq>\cdots</eq></td><td>15</td><td>0</td><td><eq>\cdots</eq></td><td>7</td></tr><tr><td>Word number</td><td colspan="12">0</td></tr><tr><td>Byte number</td><td colspan="3">3</td><td colspan="3">2</td><td colspan="3">1</td><td colspan="3">0</td></tr><tr><td>Bit numbers in word</td><td>31</td><td colspan="10"><eq>\cdots</eq></td><td>0</td></tr></table>

## 2.3 Key Schedule

The key schedule generates a sequence of 192-bit round keys $R K _ { i }$ as follows. 

Constants. The key schedule uses several constants for generating round keys, which are defined as 

$$
\delta [ 0 ] = 0 x c 3 e f e 9 d b, \quad \delta [ 1 ] = 0 x 4 4 6 2 6 b 0 2,
$$

$$
\delta [ 2 ] = 0 x 7 9 e 2 7 c 8 a, \qquad \delta [ 3 ] = 0 x 7 8 d f 3 0 e c,
$$

$$
\delta [ 4 ] = 0 x 7 1 5 e a 4 9 e, \qquad \delta [ 5 ] = 0 x c 7 8 5 d a 0 a,
$$

$$
\delta [ 6 ] = 0 x e 0 4 e f 2 2 a,
$$

$$
\delta [ 7 ] = 0 x e 5 c 4 0 9 5 7.
$$

They are obtained from hexadecimal expression of $\sqrt { 7 6 6 9 9 5 }$ , where 76, 69, and 95 are ASCII codes of ${ } ^ { 6 } \mathrm { L } , { } ^ { 5 } \mathrm { E } ,$ ’ and $\mathrm { \cdot A . \mathrm { \cdot } }$ 

Key Schedule with a 128-Bit Key. Let $K = ( K [ 0 ] , K [ 1 ] , K [ 2 ] , K [ 3 ] )$ be a 128-bit key. We set $T [ i ] = K [ i ]$ for $0 \leq i < 4$ . Round key $R K _ { i } = ( R K _ { i } [ 0 ] , R K _ { i } [ 1 ] , . . . , R K _ { i }$ [5]) for $0 \leq i < 2 4$ are produced through the following relations: 

$$
T [ 0 ] \leftarrow \operatorname{ROL} _ {1} (T [ 0 ] \boxplus \operatorname{ROL} _ {i} (\delta [ i \bmod 4 ])),
$$

$$
T [ 1 ] \leftarrow \operatorname{ROL} _ {3} (T [ 1 ] \boxplus \operatorname{ROL} _ {i + 1} (\delta [ i \bmod 4 ])),
$$

$$
T [ 2 ] \leftarrow \mathrm{ROL} _ {6} (T [ 2 ] \boxplus \mathrm{ROL} _ {i + 2} (\delta [ i \bmod 4 ])),
$$

$$
T [ 3 ] \leftarrow \mathrm{ROL} _ {1 1} (T [ 3 ] \boxplus \mathrm{ROL} _ {i + 3} (\delta [ i \bmod 4 ])),
$$

$$
R K _ {i} \leftarrow (T [ 0 ], T [ 1 ], T [ 2 ], T [ 1 ], T [ 3 ], T [ 1 ]).
$$

Key Schedule with a 192-Bit Key. Let $K = ( K [ 0 ] , K [ 1 ] , . . . , K [ 5 ] )$ be a 192-bit key. We set $T [ i ] = K [ i ]$ for $0 \leq i < 6$ . Round key $R K _ { i } = ( R K _ { i } [ 0 ] , R K _ { i } [ 1 ] , . . . , R K _ { i } [ 5 ] )$ for $0 \leq i < 2 8$ are produced through the following relations: 

$$
T [ 0 ] \leftarrow \mathrm{ROL} _ {1} (T [ 0 ] \boxplus \mathrm{ROL} _ {i} (\delta [ i \bmod 6 ])),
$$

$$
T [ 1 ] \leftarrow \operatorname{ROL} _ {3} (T [ 1 ] \boxplus \operatorname{ROL} _ {i + 1} (\delta [ i \bmod 6 ])),
$$

$$
T [ 2 ] \leftarrow \operatorname{ROL} _ {6} (T [ 2 ] \boxplus \operatorname{ROL} _ {i + 2} (\delta [ i \bmod 6 ])),
$$

$$
T [ 3 ] \leftarrow \mathrm{ROL} _ {1 1} (T [ 3 ] \boxplus \mathrm{ROL} _ {i + 3} (\delta [ i \bmod 6 ])),
$$

$$
T [ 4 ] \leftarrow \operatorname{ROL} _ {1 3} (T [ 4 ] \boxplus \operatorname{ROL} _ {i + 4} (\delta [ i \bmod 6 ])),
$$

$$
T [ 5 ] \leftarrow \operatorname{ROL} _ {1 7} (T [ 5 ] \boxplus \operatorname{ROL} _ {i + 5} (\delta [ i \bmod 6 ])),
$$

$$
R K _ {i} \leftarrow (T [ 0 ], T [ 1 ], T [ 2 ], T [ 3 ], T [ 4 ], T [ 5 ]).
$$

Key Schedule with a 256-Bit Key. Let $K = ( K [ 0 ] , K [ 1 ] , . . . , K [ 7 ] )$ be a 256-bit key. We set $T [ i ] = K [ i ]$ for $0 \leq i < 8$ . Round key $R K _ { i } = ( R K _ { i } [ 0 ] , R K _ { i } [ 1 ] , . . . , R K _ { i } [ 5 ] )$ for $0 \leq i < 3 2$ are produced through the following relations: 

$$
T [ 6 i \bmod 8 ] \leftarrow \mathrm{ROL} _ {1} (T [ 6 i \bmod 8 ] \boxplus \mathrm{ROL} _ {i} (\delta [ i \bmod 8 ])),
$$

$$
T [ 6 i + 1 \bmod 8 ] \leftarrow \mathrm{ROL} _ {3} (T [ 6 i + 1 \bmod 8 ] \boxplus \mathrm{ROL} _ {i + 1} (\delta [ i \bmod 8 ])),
$$

$$
T [ 6 i + 2 \bmod 8 ] \leftarrow \mathrm{ROL} _ {6} (T [ 6 i + 2 \bmod 8 ] \boxplus \mathrm{ROL} _ {i + 2} (\delta [ i \bmod 8 ])),
$$

$$
T [ 6 i + 3 \bmod 8 ] \leftarrow \mathrm{ROL} _ {1 1} (T [ 6 i + 3 \bmod 8 ] \boxplus \mathrm{ROL} _ {i + 3} (\delta [ i \bmod 8 ])),
$$

$$
T [ 6 i + 4 \bmod 8 ] \leftarrow \mathrm{ROL} _ {1 3} (T [ 6 i + 4 \bmod 8 ] \boxplus \mathrm{ROL} _ {i + 4} (\delta [ i \bmod 8 ])),
$$

$$
T [ 6 i + 5 \bmod 8 ] \leftarrow \mathrm{ROL} _ {1 7} (T [ 6 i + 5 \bmod 8 ] \boxplus \mathrm{ROL} _ {i + 5} (\delta [ i \bmod 8 ])),
$$

$$
R K _ {i} \leftarrow (T [ 6 i \bmod 8 ], T [ 6 i + 1 \bmod 8 ], T [ 6 i + 2 \bmod 8 ],
$$

$$
T [ 6 i + 3 \bmod 8 ], T [ 6 i + 4 \bmod 8 ], T [ 6 i + 5 \bmod 8 ]).
$$

## 2.4 Encryption Procedure

The encryption procedure of LEA consists of 24 rounds for 128-bit keys, 28 rounds for 192-bit keys, and 32 rounds for 256-bit keys. For r rounds, it encrypts a 128-bit plaintext $P = ( P [ 0 ] , P [ 1 ] , P [ 2 ] , P [ 3 ] )$ to a 128-bit ciphertext $C =$ $( C [ 0 ] , C [ 1 ] , C [ 2 ] , C [ 3 ] )$ 

Initialization. Set the 128-bit intermediate value $X _ { 0 }$ to the plaintext P. Run the key schedule to generate r round keys. 

Iterating Rounds. The 128-bit output $X _ { i + 1 } = ( X _ { i + 1 } [ 0 ] , . . . , X _ { i + 1 } [ 3 ] )$ of the ith round for $0 \leq i \leq r - 1$ is computed as 

$$
X _ {i + 1} [ 0 ] \leftarrow \operatorname{ROL} _ {9} ((X _ {i} [ 0 ] \oplus R K _ {i} [ 0 ]) \boxplus (X _ {i} [ 1 ] \oplus R K _ {i} [ 1 ])),
$$

$$
X _ {i + 1} [ 1 ] \leftarrow \mathrm{ROR} _ {5} ((X _ {i} [ 1 ] \oplus R K _ {i} [ 2 ]) \boxplus (X _ {i} [ 2 ] \oplus R K _ {i} [ 3 ])),
$$

$$
X _ {i + 1} [ 2 ] \leftarrow \mathrm{ROR} _ {3} ((X _ {i} [ 2 ] \oplus R K _ {i} [ 4 ]) \boxplus (X _ {i} [ 3 ] \oplus R K _ {i} [ 5 ])),
$$

$$
X _ {i + 1} [ 3 ] \leftarrow X _ {i} [ 0 ].
$$

Finalization. The ciphertext C is produced from the finally obtained $X _ { r }$ after round iteration in the following way: 

$$
C [ 0 ] \leftarrow X _ {r} [ 0 ], C [ 1 ] \leftarrow X _ {r} [ 1 ], C [ 2 ] \leftarrow X _ {r} [ 2 ], \text { and } C [ 3 ] \leftarrow X _ {r} [ 3 ].
$$

## 3 Design Principles

We explain the design principles for LEA (Fig. 1). 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-17/655ba2f2-9a4c-4edf-887e-58839717d721/eef2aa86e458c23ea2ce8597ee7483a23ccb0cccbba64293fb0302ea38e75ca9.jpg)



Fig. 1. ith round function


Eficient round structure with 32-bit ARX operations. The round function of LEA consists of ARX operations. Especially, we used 32-bit ARX operations instead of 8-bit ones because 32-bit operations are more popular than 8-bit ones and we think that most processors will be developed to support 32-bit operations even in resource-constrained devices. It has just three internal computation modules including two key XORs, one addition, and one bitwise rotation. We adopt the addition modulo $\mathrm { \dot { 2 } ^ { 3 2 } }$ as a nonlinear function with two 32-bit inputs and one 32-bit output<sup>1</sup>. Round key XORs are used for randomizing the inputs of the nonlinear functions, the bitwise rotations and the word-wise swap are used for difusion. The simple and eficient structure of LEA provides both tiny-size code and highspeed code. In spite of its simplicity, it has nice nonlinearity and difusion efect to give a proper number of rounds for good performance. 

Encryption is more useful than decryption. Unexpectedly, there are not many modes of operation which need the decryption function. For example, ISO/IEC 9797-1, ISO/IEC 10116, and ISO/IEC 19772 specify 6 message authentication modes, 5 encryption modes, and 6 authenticated-encryption modes of block ciphers, respectively. However, only ECB, CBC, and OCB modes need both encryption and decryption functions<sup>2</sup>. It implies that the block cipher encryption is more widely and frequently used than the block cipher decryption. With this consideration, we did not care for the balance of the speed between encryption and decryption. Note that most block ciphers usually have the special last round diferent from other rounds for eficiency in the implementation of decryption, while the last round of LEA is not special but has the same structure as the other rounds for eficiency of the encryption-only modes. Nevertheless, the decryption speed of LEA is still competitive with most block ciphers. 

Choice of rotations. We chose the rotations in encryption procedure such that it has the strong difusion property. Firstly, for the parameters $( a , b , c )$ , we set the round function with input $X _ { i }$ , output $X _ { i + 1 }$ , and round key $R K _ { i }$ as follows. 

$$
\begin{array}{l} X _ {i + 1} [ 0 ] \leftarrow \mathrm{ROL} _ {a} ((X _ {i} [ 0 ] \oplus R K _ {i} [ 0 ]) \boxplus (X _ {i} [ 1 ] \oplus R K _ {i} [ 1 ])), \\ X _ {i + 1} [ 1 ] \leftarrow \mathrm{ROL} _ {b} ((X _ {i} [ 1 ] \oplus R K _ {i} [ 2 ]) \boxplus (X _ {i} [ 2 ] \oplus R K _ {i} [ 3 ])), \\ X _ {i + 1} [ 2 ] \leftarrow \mathrm{ROL} _ {c} ((X _ {i} [ 2 ] \oplus R K _ {i} [ 4 ]) \boxplus (X _ {i} [ 3 ] \oplus R K _ {i} [ 5 ])), \\ X _ {i + 1} [ 3 ] \leftarrow X _ {i} [ 0 ]. \end{array}
$$

Then, we linearized the LEA encryption algorithm by replacing the additions with XORs, and searched the XOR diferential characteristics (XDCs) of the linearized structure for all possible $\binom { 3 2 } { 3 }$ candidates of $( a , b , c )$ . Note that $\mathrm { R O L } _ { b } =$ $\mathrm { R O R } _ { 3 2 - b }$ and $\mathrm { R O L } _ { c } = \mathrm { R O R } _ { 3 2 - c } .$ . One of our searching strategies is to start from a middle round with low Hamming weight of diferences. As a result, we found that for each candidate of $( a , b , c )$ there exists a 11-round XDC whose probability is not lower than $2 ^ { - 1 2 8 }$ . The probability is estimated under the assumption that every addition is independent. Note that this assumption is not stronger than any other block ciphers because each addition can be regarded as a nonlinear function with two 32-bit inputs and a 32-bit output and because XORing subkeys with the inputs of nonlinear functions is the most popular way to combine key materials to encryption body. We found 32 candidates of $( a , b , c )$ which have 12- round XDCs with the probability of $2 ^ { - 1 2 8 } \ \mathrm { o r \ 2 ^ { - 1 2 9 } }$ as best ones. We optimized these characteristics such that both of the first and last rounds are not linearized. We chose (9, 27, 29) because it made only diferential characteristics with the probability $2 ^ { - 1 2 8 }$ as best ones, and because the number of such characteristics is fewer than any other candidates. 

Additionally, we considered short characteristics for the boomerang attack, and found that the maximum number of rounds having diferential characteristic with the probability greater than $2 ^ { - 3 2 }$ is $7$ over all $( a , b , c )$ , and so does it for the case $( a , b , c ) = ( 9 , 2 7 , 2 9 )$ 

As a diferent approach for the same goal, we can also regard the linearized rounds as a linear code. So, we tried to get good diferential characteristics by applying Canteaut-Chabaud method [17] to search code words with minimum weight code words, but we could not find better diferential characteristics than the first approach. 

Simple key schedule. We adopt a very simple structure for the key schedule. It does not mix the words of the key and has no avalanche efect in key bits at all. Nevertheless, our security analysis show that it protects LEA from the attacks such as slide attack [12], related-key attack [5], related-key boomerang attack [10,11], biclique attack [14], rotational attack [38] and so on. The simplicity of the key schedule provides eficiency in small-size hardware and software implementations. 

## 4 Security Analysis

We analyzed the security of LEA for existing cryptanalytic techniques by searching, constructing, or exploiting various characteristics such as diferential and linear trails. For each attack, firstly, we found the maximum number N of rounds where there exists an available characteristic, and then constructed the best Nround characteristic. We determined the number of rounds making the algorithm secure against each attack, considering the diference propagation of the round function and the arrangement of the round key words, as follows. 

1. If the characteristic is N-round and holds with the probability between 0 and 1, then the secure number of rounds is $N + 3$ for 128-bit keys, $N + 4$ for 192-bit keys, and $N + 5$ for 256-bit keys. 

2. If the characteristic is N-round and holds with the probability 0 or 1, then the secure number of rounds is $N + 4$ for 128-bit keys, N + 5 for 192-bit keys, and $N + 6$ for 256-bit keys. 

COSIC made an evaluation report for LEA, too, independently of us [20]. We will explain some of their security analysis results. The whole main analysis results are summarized at Table 2. We also discuss other attacks not listed in Table 2. 


Table 2. Security of LEA against several main attacks


<table><tr><td rowspan="2">Attack type</td><td rowspan="2">Round # of Characteristic</td><td rowspan="2">Probability of Characteristic</td><td colspan="3">Secure # of rounds</td></tr><tr><td>LEA-128</td><td>LEA-192</td><td>LEA-256</td></tr><tr><td>Differential [9]</td><td>11</td><td><eq>p = 2^{-98}</eq></td><td>14</td><td>15</td><td>16</td></tr><tr><td>Truncated Differential [39]</td><td>11</td><td><eq>p = 2^{-91.9}</eq></td><td>14</td><td>15</td><td>16</td></tr><tr><td>Linear [44]</td><td>11</td><td><eq>|p - 1/2| = 2^{-62}</eq></td><td>14</td><td>15</td><td>16</td></tr><tr><td>Zero Correlation [15]</td><td>7</td><td><eq>|p - 1/2| = 0</eq></td><td>11</td><td>12</td><td>13</td></tr><tr><td>Boomerang [54]</td><td>14</td><td><eq>p^{2}q^{2} = 2^{-108}</eq></td><td>17</td><td>18</td><td>19</td></tr><tr><td>Impossible Differential [6]</td><td>10</td><td><eq>p = 0</eq></td><td>14</td><td>15</td><td>16</td></tr><tr><td>Integral [40]</td><td>6</td><td><eq>p = 1</eq></td><td>10</td><td>11</td><td>12</td></tr><tr><td>Differential-Linear [8]</td><td>14</td><td><eq>|p - 1/2| &lt; 2^{-57}</eq></td><td>17</td><td>18</td><td>19</td></tr></table>

## 4.1 Diferential Attack

As we mentioned in Sect. 3, the probability of the best 12-round diferential characteristic which we have found is estimated at most as $2 ^ { - 1 2 8 }$ . Since it is not available for the attack, we searched 11-round diferential characteristic with the same way; firstly find the XOR-linearized diferential characteristics with high probabilities and then optimize it by removing the linearity in the diferential paths of the first and the last rounds. As a result, the best found ones of 11-round diferential characteristics have the probability $2 ^ { - 9 8 }$ and the following form: 

– Input diference: 80000234 α0402214 β0401205 γ0400281, where $\alpha \in \{ 4 , \mathsf { c } \}$ , $\beta \in \{ 4 , \mathsf { c } \}$ , and $\gamma = \beta \oplus 1$ , 

– Output diference: η800000a 88aaa00a 220202ζ0 00200050, where $\eta \in$ $\{ 4 , \mathsf { c } \}$ and $\zeta \in \{ 2 , 6 \}$ 

We can apply one of these characteristics to 11 rounds from Round 0 to Round 10, and attack 12 rounds for 128-bit keys. This attack recovers 96 bits of the round key $R K _ { 1 1 }$ in the last round, Round 11 with very high signal-to-noise ratio, and requires around $2 ^ { 1 0 0 }$ plaintexts, $2 ^ { 8 4 }$ encryptions, and the memory for $2 ^ { 7 6 }$ bytes. Extending it to 13-round attack is not successful because 

– If one applies the 11-round characteristic to the first 11 rounds from Round 0 to Round 10 and tries to recover partial bits of $R K _ { 1 2 }$ , the round key of Round 12, he will be in trouble with the poor filtering and it leads to the bad signal-to-noise ratio. 

– If one applies the 11-round characteristic to Round 1 to Round 11 and tries to recover partial bits of $R K _ { 0 }$ , the round key of Round 0 and $R K _ { 1 2 }$ , the round key of Round 12, he will face too much guessed key bits or too weak filtering to attack. 

We consider the possibility of 13-round attack for 192-bit keys and 14-round attack for 256-bit keys, respectively. 

Using a set of many diferential characteristics with relatively high probabilities instead of a best one, we can increase the probability from $2 ^ { - 5 8 } \ \mathrm { {  t o } \ 2 ^ { - 9 1 . 9 } }$ This is a kind of truncated diferential characteristic [39], which can be used for reducing some of complexities for the above diferential attack, but not be helpful for increasing the number of the attacked rounds. Analyses with other types of diferences [20] have been tried but not found any critical weaknesses. 

## 4.2 Linear Attack

A linear approximation has the following form: 

$$
\Gamma_ {P} \cdot P \oplus \Gamma_ {C} \cdot C = \Gamma_ {R K} \cdot R K,\tag{1}
$$

where RK is a vector composed of all round keys. We denote the probability that (1) is satisfied, by $p ,$ and let $\varepsilon = p - 1 / 2 . \varepsilon$ is called the bias of (1). A linear attack using a linear approximation has the data complexity of $O ( \varepsilon ^ { - 2 } )$ 

It is not easy to find a good linear approximation for long rounds of LEA. Wall´en’s work [55] shows that in the masks of a linear approximation for modular additions the absolute value of the bias tends to decrease as the highest nonzero bit of the masks is close to the most significant. The combination of the bitwise rotations in LEA encryption significantly disturbs the appearance of linear approximations with good biases. We searched the linear approximations in such a way that the propagation of linear masks is suppressed as strong as possible. Consequently, we found 10-round linear approximation with $\varepsilon = \hat { 2 } ^ { - 4 6 }$ and 11-round linear approximation with $\varepsilon = 2 ^ { - 6 3 }$ . We can use Matsui’s algorithm 1 and the 11-round linear approximation to get 1-bit information about round keys for 11 rounds with $O ( 2 ^ { 1 2 6 } )$ known plaintexts, and we can use Matsui’s algorithm 2 and the 10-round linear approximation to make a 11-round key recovery attack with $O ( 2 ^ { 9 2 } )$ known plaintexts. 

## 4.3 Zero Correlation Attack

Recently, the attacks using zero correlation approximations have been introduced [15], which is a counter part of the impossible diferential attack in linear cryptanalysis. The best key recovery attacks in single-key setting based on zero correlation approximations have been made for TEA and XTEA. Since LEA has the use of ARX operations in common with TEA and XTEA, one may suspect the vulnerability of LEA against zero correlation attack. However, we found that a 7-round zero correlation approximation is constructed from 3-round forward and 4-round backward approximations, and it is dificult to construct much longer zero correlation approximations than $7$ rounds. Based on the $7 -$ round zero correlation approximations, we consider the possibility of 9-round attack for 128-bit keys, 10-round attack for 192-bit keys, and 11-round attack for 256-bit keys, respectively. 

## 4.4 Boomerang Attack

The best diferential probability for 7 rounds is $2 ^ { - 2 7 }$ . The best 7-round one has the following diferences of input and output. 

– Input diference: 80000014 80400014 80400004 80400080, 

– Output diference: 00001200 28000200 80800800 00000008. 

We construct a 14-round boomerang characteristic from the best 7-round differential characteristic. There are some round-skip techniques maximizing the number of rounds of the boomerang characteristic [10,24], but they do not work for LEA. It is the best one which we have found ever. For 128-bit keys, we can use it to make an attack on at most 15 rounds with $2 ^ { 1 1 6 . 3 }$ plaintexts. We could not find a proper attack on 16 rounds due to increased data complexity and worsened filtering. The amplified boomerang [36] or rectangle attacks [7] do not seem to improve our attacks significantly. We consider the possibility of 16-round attack for 192-bit keys and 17-round attack for 256-bit keys, respectively. 

## 4.5 Impossible Diferential Attack

Impossible diferential attack [6] uses diferential characteristics with probability of 0. They are usually constructed from miss-in-the-middle combination with forward and backward truncated diferential characteristics with probability of 1. For LEA, the best impossible diferential characteristics are 10 rounds, constructed with 6-round forward and 4-round backward truncated diferential characteristics with probability of 1, which is reported in [20]. 

For 128-bit keys, we can use the 10-round impossible diferential characteristics to make a 11-round attack to derive a partial information of the last round key. one may make a 12-round attack by using a set of specially chosen plaintexts or constructing a key-recovering process. We consider the possibility of 13-round attack for 192-bit keys, and 14-round attack for 256-bit keys, respectively. 

## 4.6 Integral Attack

Integral attack [40] for LEA uses a 6-round integral characteristic, which is reported at [20]. A 6-round integral characteristic of LEA is reported at [20]. It shows that if the 3-th word $P [ 3 ]$ of the plaintext P is active, which takes all 32-bit values for one time, and other words of P are constants, then the least significant bit of the 1-th word X[1] of the output X after 6 rounds is ADD-balanced. For 128-bit keys, we can use the 6-round integral characteristic to make a 9-round attack to derive a partial information of round keys. Adding rounds to the characteristic at top is impossible because it requires a code book of all plaintexts. We consider the possibility of 10-round attack for 192-bit keys, and 11-round attack for 256-bit keys, respectively. We suppose higher order differential characteristic [39] is also constructed for 6 rounds at most. 

## 4.7 Diferential-Linear Attack

Diferential-linear attack [8] uses a combined characteristic from short-round differential characteristics and linear approximations. A $( r _ { 1 } + r _ { 2 } )$ -round diferentiallinear characteristic based on one $r _ { \mathrm { 1 } } \mathrm { - r o u n d }$ diferential characteristic with the probability $p _ { d }$ and two r -round linear approximations with same masks and the probability $p _ { l } = 1 / 2 + \varepsilon$ holds with the probability $p = 1 / 2 + 2 p _ { d } \varepsilon ^ { 2 }$ . Our analysis for diferential and linear attacks on LEA implies that the available diferentiallinear characteristics for LEA can be constructed up to 14 rounds and that the biasour searching program can find 14-round diferential-linear characteristics with the bias at most $\bar { 2 } ^ { - 5 7 }$ . However, this reasoning is based on the best results which we can find for diferential and linear trails, and so we suppose that the actually found diferential-linear characteristics be much shorter than 14 rounds or have the bias whose absolute value is significantly smaller than $2 ^ { - 5 7 }$ 

## 4.8 Attacks Using Weakness of Key Schedule

Slide attack [12] uses a self-similarity in the block cipher. The key schedule of LEA obstructs it by adding the rotated constants to the key materials. 

For instance, when the key size is 128 bits, $\mathrm { R O L } _ { i } ( \delta [ i$ mod 4]) is added for the leftmost 32 bits of the i-th round key $R K _ { i } [ 0 ]$ . Although only several 32-bit constants are used, rotations depending on i make the efects of adding diferent round constants for every round. Therefore, there is no self-similarity which can be exploited for any attacks on LEA. 

Related-key diferential attack [34] and related-key boomerang attack [10,11] is the most popular ones among the attacks using related keys [5]. In the similar way to diferential cryptanalysis, we searched how many rounds there exists a key diference having diferential characteristics with the probability $> 2 ^ { - 1 2 8 }$ up to. The best related-key diferential characteristics which we found ever are 11- round one for 128-bit keys, and 12-round one for 192 and 256-bit keys. However, those characteristics cannot be used straightforwardly for any attacks because they hold with only small part of the key space. 

Bogdanov et al. [14] has introduced the key recovery attacks in single-key setting, based on biclique techniques with two attack approaches. The first approach is to use the bicliques constructed from independent related-key diferentials and to search the right key with partial computations based on precomputation. We checked that it is hard to construct such bicliques for more than one round of LEA for the key sizes of 128 and 192 bits and for more than two round for the key size of 256 bits, because LEA uses 192-bit round keys and all key materials are wasted in one round for 128 and 192-bit keys and in two rounds for 256-bit keys, and because all additions in the same round are active within two rounds in backward direction for any key diference. Therefore, the time complexity of the key recovery attacks based on the first approach would have a negligible diference with that of exhaustive search. The second approach is to use the bicliques constructed from interleaving related-key diferential trails and to apply a basic meet-in-the-middle technique for key recovery. Such bicliques would not be constructed for more than 8 rounds because the propagation of the diference inserted at key is fast in the encryption of LEA in spite of its simple structure. Furthermore, the basic meet-in-the-middle technique of the second approach is applicable to only short rounds. So, the attack based on second approach can work for only small reduced variants with much less rounds than recommended. 

## 4.9 Other Attacks

Recently, some kinds of meet-in-the-middle attacks have made impressive cryptanalytic results for block ciphers and hash functions. We checked that meetin-the-middle attack techniques are not applicable to LEA very well. A basic meet-in-the-middle attack [23] is disturbed since there is no separation of long rounds. The meet-in-the-middle pseudo-preimage attack [1,50] does not work for even half rounds. The partial-matching and initial-structure techniques are not eficient in LEA. 

Rotational cryptanalysis [38] is attractively available on ARX-based structures. We examined the resistance of LEA against rotational cryptanalysis for the single-key model and the related-key model in which two keys form a rotational pair. We found that key XORs in the encryption procedure and constant XORs in the key schedule prevent rotational characteristics from being constructed for long rounds. 

Algebraic attack [19] forms an overdefined system of equations derived from the block cipher. Several algorithms are proposed for solving it, but they fail to find a right solution for existing block ciphers. We think they hardly work for LEA, too. 

## 4.10 Security Margin

We have studied various existing cryptanalytic techniques for block ciphers in order to analyze the security of LEA. Although some characteristics we mentioned can be somewhat upgraded by new technologies, it is unlikely to find a new attack to improve significantly the results in Table 2, as long as we did not miss critical weakness of LEA. We determined the number of rounds for LEA-128 based on the above security analysis such that the security margin to the whole rounds ratio is greater than 30 %. For LEA-192 and LEA-256, we added 4 and 8 rounds, respectively to the rounds of LEA-128, considering the diference of key schedules and security criteria. 

## 5 Implementation

## 5.1 Software Implementation

We have implemented LEA on various 32-bit and 64-bit software platforms. We have focused on LEA-128 since the speed decreases almost in proportion to the number of rounds. 

On ARM platforms, we can implement LEA without register-spilling and most of the bit rotations can be processed without costing any clock cycle thanks to the barrel shifter. Thus we get remarkably high throughput compared to other block ciphers both in encryption and decryption. 

On Intel/AMD platforms, we can also implement LEA without registerspilling and, due to the highly parallel structure of LEA round function, we also get high encryption speed. Moreover, by utilizing SIMD(Single Instruction Multiple Data) instructions inherent in most of recent Intel/AMD platforms, we can get even higher throughput for parallel modes of LEA. 

On ARM and ColdFire platforms, we have measured the compactness of LEA. Since the round function of LEA consists of a small number ARX operations without S-box, the code size of LEA on these platforms is quite smal compared to other block ciphers with the same block size. 

We have also estimated the eficiency of LEA on some 8-bit platforms and confirmed that LEA has sound performance on these platforms. 

ARM platforms. ARM processors are the most widely used 32-bit embedded processors. They support rotate, multiple load/store instructions as well as most arithmetic and logical ones. Comparison with the speed-optimized implementation of AES on comparable platforms is given in Table 3. 

Table 4 shows the comparison with the code-size-optimized implementation of AES. 

Intel and AMD Platforms. Most of recent Intel/AMD CPUs have 3 pipelines. Since LEA consists of 24 rounds and each round can be expressed as a sequence of 16 instructions, the minimal cycle cost of LEA encryption is expected to be around 128. Comparison with 32-bit implementation of AES is given in Table 5. 


Table 3. Speed of LEA-128 and AES-128 on ARM platform


<table><tr><td>Algorithm</td><td>Speed (cycles/byte)</td><td>Platform</td></tr><tr><td>LEA-128</td><td>20.06</td><td>ARM926EJ-S</td></tr><tr><td>AES-128 [47]</td><td>34.00</td><td>StrongARM SA-1110</td></tr></table>


Table 4. Code size of LEA-128 and AES-128 on ARM platform


<table><tr><td>Algorithm</td><td>ROM size (bytes)</td><td>RAM size (bytes)</td><td>Speed (cycles/byte)</td><td>Platform</td></tr><tr><td>LEA-128</td><td>590</td><td>32</td><td>326.94</td><td>ARM926EJ-S</td></tr><tr><td>AES-128 [22]</td><td>2,164</td><td>304</td><td>460.50</td><td>ARM7TDMI</td></tr></table>

Decryption is slower than encryption since decryption is processed rather serially. We note that AES is faster than all other well-known block ciphers with similar block and key size on these platforms. 

Most of recent Intel/AMD processors support SIMD extensions at least up to SSE2. Thus, basic 32-bit operations like XOR, ADD, SHIFT can be performed very eficiently in parallel. Moreover, the latency and throughput of SIMD instructions are close to those of corresponding 32-bit-wise instructions on recent processors. Since LEA is described as a combination of XOR, ADD, and ROTATE, it is straightforward to implement parallel modes of LEA using SSE2 to process 4 or 8 blocks simultaneously. 

Comparison with SIMD implementations of AES (not using AES instruction set) is given in Table 6. 

ColdFire platforms. ColdFire processors are 32-bit microprocessors targeted towards embedded systems. LEA shows lower performance here than on ARM platforms since load/store and rotate operation are performed less eficiently: They do not support rotate, multiple load/store instructions and the shift instruc tion can shift only by up to 8 bits. We have implemented speed-optimized and size-optimized LEA on MCF5213. Comparison with implementation of AES on comparable platform is given in Table 7. We note that LEA runs faster than hardware-accelerated AES. 

8-bit and 16-bit Platforms. Though LEA is designed to achieve high performance in 32-bit platforms. We have also analyzed the performance of LEA on Advanced 


Table 5. Speed (cycles/byte) of LEA-128 and AES-128 on 32-bit Intel/AMD platforms


<table><tr><td rowspan="2">Platform</td><td colspan="2">LEA-128</td><td>AES-128</td></tr><tr><td>Encryption</td><td>Decryption</td><td>Encryption</td></tr><tr><td>Intel Core 2 Quad Q6600</td><td>9.29</td><td>14.83</td><td>12.20 [25]</td></tr><tr><td>Intel Core i5-2500</td><td>9.29</td><td>14.52</td><td>11.35 [25]</td></tr><tr><td>AMD Phenom II X4 965</td><td>8.85</td><td>14.50</td><td>10.35 [25]</td></tr><tr><td>AMD Opteron 6176 SE</td><td>8.55</td><td>14.05</td><td>N/A</td></tr></table>


Table 6. SIMD implementations of LEA-128 and AES-128


<table><tr><td>Platform</td><td>LEA CTR</td><td>AES CTR</td></tr><tr><td>Intel Core 2 Quad Q6600</td><td>4.51</td><td>9.32 [35]</td></tr><tr><td>Intel Core i7-860</td><td>4.19</td><td>6.92 [35]</td></tr><tr><td>AMD Opteron 6176SE</td><td>4.50</td><td>N/A</td></tr></table>

Virtual RISC(AVR), which are among the most favorable 8-bit platforms. LEA is estimated to run at around 3,040 cycles for encryption on AVR AT90USB82/162 where AES best record is 1,993 cycles [47]. We suppose that the performance of LEA is comparable to that of AES on low-end 8-bit or 16-bit platforms, both in speed and code size. 

## 5.2 Hardware Implementation

We have implemented LEA-128 with Verilog HDL and synthesized to ASIC with fully verifying the correctness of front-end and back-end design. For HDL implementation and verification of our design, we have used Mentor Modelsim 6.5f for RTL simulation and Synopsys Design Compiler Ver. B-2008.09-SP5 for its synthesis. Our RTL level design result of LEA is synthesized to ASIC with the UMC 0.13µm standard cell library and 100 MHz operating frequency. 

Since the LEA consists of the small number of simple operations such as bit XOR, rotation and 32-bit adder without complex operations such as S-box, it can be implemented with low hardware resources. The LEA can also achieve high performance for its short critical path characteristics. The operational blocks for the round function and key scheduling are so regular that we can achieve these operations with low hardware resources by using its basic operational blocks repetitively. 


Table 7. Implementations of LEA-128 and AES-128 on ColdFire Platform


<table><tr><td>Algorithm</td><td>ROM size (bytes)</td><td>RAM size (bytes)</td><td>Speed (cycles/byte)</td><td>Platform</td></tr><tr><td>LEA-128</td><td>9,674</td><td>832</td><td>103.59</td><td>MCF5213</td></tr><tr><td>LEA-128</td><td>704</td><td>32</td><td>829.25</td><td>MCF5213</td></tr><tr><td>AES-128 [48]</td><td>7,996</td><td></td><td>1,403.51</td><td>ColdFire v2</td></tr><tr><td>AES-128 [48]</td><td>960</td><td></td><td>160.00</td><td>ColdFire v2 with <eq>CAU^†</eq></td></tr></table>


†Cryptographic Acceleration Unit 


Table 8 shows the hardware complexity of two diferent implementations of LEA-128 encryption module: One is the area-optimized and the other is the FOM-optimized (throughput/area). The area-optimized implementation of LEA has 3,826 GE and 168 clock cycles, and the FOM-optimized has 5,426 GE and 24 clock cycles. We can see that the LEA encryption algorithm has relatively lightweight key scheduling and encryption block (Round Function) from this table. 

Table 9 compares our hardware implementation results of LEA-128 encryption to other 128-bit key block ciphers with view point of FOM. 


Table 8. Hardware feature of LEA-128 encryption module


<table><tr><td rowspan="2">Block</td><td colspan="2">Area(GE)</td></tr><tr><td>Area-optimized</td><td>FOM-optimized</td></tr><tr><td>Constants generation</td><td>970</td><td>964</td></tr><tr><td>Control unit</td><td>75</td><td>54</td></tr><tr><td>Key scheduling</td><td>400</td><td>695</td></tr><tr><td>State register</td><td>920</td><td>1,037</td></tr><tr><td>Key register</td><td>998</td><td>1,037</td></tr><tr><td>Round function</td><td>450</td><td>1,080</td></tr><tr><td>Others</td><td>23</td><td>559</td></tr><tr><td>Total block</td><td>3,826</td><td>5,426</td></tr></table>


Table 9. Hardware implementation of LEA-128 encryption algorithm and its comparison to that of other 128-bit key block ciphers


<table><tr><td rowspan="2">Algorithm</td><td colspan="2">Size(bits)</td><td rowspan="2">Cycles /block</td><td rowspan="2">T.put<eq>^{\dagger}</eq></td><td rowspan="2">Tech. (μm)</td><td rowspan="2">Area (GE)</td><td rowspan="2">FOM<eq>^{\ddagger}</eq></td></tr><tr><td>Key</td><td>block</td></tr><tr><td>LED [30]</td><td>128</td><td>64</td><td>1,872</td><td>3.42</td><td>0.18</td><td>1,265</td><td>0.26</td></tr><tr><td>CLEFIA [52]</td><td>128</td><td>128</td><td>328</td><td>39</td><td>0.09</td><td>2,488</td><td>1.56</td></tr><tr><td>PICCOLO [51]</td><td>128</td><td>64</td><td>528</td><td>12.12</td><td>0.13</td><td>758</td><td>1.59</td></tr><tr><td>LEA-128<eq>^{1}</eq></td><td>128</td><td>128</td><td>168</td><td>76.19</td><td>0.13</td><td>3,826</td><td>1.9</td></tr><tr><td>AES [45]</td><td>128</td><td>128</td><td>226</td><td>56.64</td><td>0.13</td><td>2,400</td><td>2.35</td></tr><tr><td>HIGHT [31]</td><td>128</td><td>64</td><td>34</td><td>188.24</td><td>0.25</td><td>3,048</td><td>6.17</td></tr><tr><td>TWINE [53]</td><td>128</td><td>64</td><td>36</td><td>178</td><td>0.09</td><td>1,866</td><td>9.53</td></tr><tr><td>LEA-128<eq>^{2}</eq></td><td>128</td><td>128</td><td>24</td><td>533.33</td><td>0.13</td><td>5,426</td><td>9.82</td></tr><tr><td>PRESENT [13]</td><td>128</td><td>64</td><td>32</td><td>200</td><td>0.18</td><td>1,570</td><td>12.73</td></tr></table>


†Throughtput@100KHz (Kbps), ‡FOM : (Throughput/Area) 10<sup>2</sup> 



<sup>1</sup> : Area-optimized implementation of LEA-128 



<sup>2</sup> : FOM-optimized implementation of LEA-128 


## 6 Conclusion

We have proposed a new block cipher LEA, which has 128-bit block size and 128, 192, or 256-bit key size. LEA provides a high-speed software encryption on general-purpose processors. It can be also implemented to have tiny code size. Its hardware implementation has a competitive throughput per area. It is secure against all the existing attacks. In spite of the remarkable implementation results presented in this paper, we believe that the they have room for further optimizations. 

## A Diferential Characteristic

Let $\varDelta X _ { i }$ be the XOR diference of $X _ { i }$ , and let $p _ { i }$ be the probability of $\varDelta X _ { i } $ $\varDelta X _ { i + 1 }$ . The probability $p$ of an r-round diferential characteristic is computed as $\begin{array} { r } { p = \prod _ { i = 0 } ^ { r - 1 } p _ { i } } \end{array}$ 

Table 10 shows the 11-round diferential characteristic with the probability of $2 ^ { - 9 8 }$ . The diferences in the table are denoted in hexadecimal. 


Table 10. 11-round diferential characteristic with the probability of $2 ^ { - 9 8 }$


<table><tr><td>i</td><td><eq>\Delta X_i</eq></td><td></td><td></td><td></td><td>pi</td></tr><tr><td>0</td><td>80000234</td><td>α0402214</td><td>β0401205</td><td>γ0400281</td><td><eq>2^{-22}</eq></td></tr><tr><td>1</td><td>80400080</td><td>8a000080</td><td>82000210</td><td>80000234</td><td><eq>2^{-14}</eq></td></tr><tr><td>2</td><td>80000014</td><td>80400014</td><td>80400004</td><td>80400080</td><td><eq>2^{-9}</eq></td></tr><tr><td>3</td><td>80000000</td><td>80000000</td><td>80000010</td><td>80000014</td><td><eq>2^{-3}</eq></td></tr><tr><td>4</td><td>00000000</td><td>80000000</td><td>80000000</td><td>80000000</td><td>1</td></tr><tr><td>5</td><td>00000100</td><td>00000000</td><td>00000000</td><td>00000000</td><td><eq>2^{-1}</eq></td></tr><tr><td>6</td><td>00020000</td><td>00000000</td><td>00000000</td><td>00000100</td><td><eq>2^{-2}</eq></td></tr><tr><td>7</td><td>04000000</td><td>00000000</td><td>00000020</td><td>00020000</td><td><eq>2^{-4}</eq></td></tr><tr><td>8</td><td>00000008</td><td>00000001</td><td>00004004</td><td>04000000</td><td><eq>2^{-8}</eq></td></tr><tr><td>9</td><td>00001200</td><td>28000200</td><td>80800800</td><td>00000008</td><td><eq>2^{-12}</eq></td></tr><tr><td>10</td><td>00200050</td><td>05440050</td><td>10100101</td><td>00001200</td><td><eq>2^{-23}</eq></td></tr><tr><td>11</td><td>η800000a</td><td>88aaa00a</td><td>220202ζ0</td><td>00200050</td><td></td></tr></table>

The 7-round diferential characteristic with the probability of $2 ^ { - 2 7 }$ , discarding the first two rounds and the last two rounds is used for constructing a 14-round boomerang characteristic. 

## B Linear Approximation

Let $\boldsymbol { \Gamma } \boldsymbol { X _ { i } }$ be the mask of $X _ { i }$ , and let $\varepsilon _ { i } = p _ { i } - 1 / 2$ be the bias of the linear approximation 

$$
\Gamma X _ {i} \cdot X _ {i} \oplus \Gamma X _ {i + 1} \cdot X _ {i + 1} = \Gamma K _ {i} \cdot R K.\tag{2}
$$


Table 11. 11-round linear approximation with the bias $\varepsilon = 2 ^ { - 6 2 }$


```latex
\( \Gamma X_{0} = 0aff33f0\ 470032b0\ 735801c0 \)  15f00080
\( (\alpha_{0}^{0}, \alpha_{1}^{0}, \alpha_{2}^{0}) = (0a0033f0, 0f0033b0, 0a0033b0) \)   \( \varepsilon_{\alpha^{0}} = 2^{-7} \) 
\( (\beta_{0}^{0}, \beta_{1}^{0}, \beta_{2}^{0}) = (48000100, 6c000100, 48000180) \)   \( \varepsilon_{\beta^{0}} = -2^{-4} \) 
\( (\gamma_{0}^{0}, \gamma_{1}^{0}, \gamma_{2}^{0}) = (1f5800c0, 15f00080, 15500080) \)   \( \varepsilon_{\gamma^{0}} = 2^{-7} \) 
\( \Gamma X_{1} = 00676014\ 024000c\ 02aa0010 \)  00ff0000
\( (\alpha_{0}^{1}, \alpha_{1}^{1}, \alpha_{2}^{1}) = (00600014, 00400014, 0040001e) \)   \( \varepsilon_{\alpha^{1}} = 2^{-4} \) 
\( (\beta_{0}^{1}, \beta_{1}^{1}, \beta_{2}^{1}) = (02000018, 02000010, 03000010) \)   \( \varepsilon_{\beta^{1}} = -2^{-3} \) 
\( (\gamma_{0}^{1}, \gamma_{1}^{1}, \gamma_{2}^{1}) = (00aa0000, 0ff000, 00aa000) \)   \( \varepsilon_{\gamma^{1}} = 2^{-5} \) 
\( \Gamma X_{2} = 8003c00\ 8018000\ 0015400\ ) \)  0007600\ 
\( (\alpha_{0}^{2}, \alpha_{1}^{2}, \alpha_{2}^{2}) = (80000\ 8, 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ 8\ ) \) 
\( (\beta_{0}^{2}, \beta_{1}^{2}, \beta_{2}^{2}) = (9189999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999.7)
\( (\gamma_{2}^{2}, \gamma_{1}^{2}, \gamma_{2}^{2}) = (11111111111111111111111111111111111111111111.7)
\( \Gamma X_{3} = 6666666666666666666666666666666666666666666666666666666666666666666666666666666666666666666.7)
\( (\alpha_{2}^{3}, \alpha_{2}^{3}, \alpha_{2}^{3}) = (8555555555555555555555555555555555555555555555555555555555.7)
\( (\beta_{2}^{3}, \beta_{2}^{3}, \beta_{2}^{3}) = (855555555555555555555555555555555555.7)
\( (\gamma_{2}^{3}, \gamma_{2}^{3}, \gamma_{2}^{3}) = (855555555555555547777777777777777777777777777777777777777777777.7)
\( \Gamma X_{4} = 333333333333333333333333333333333333333333333333333333333333333333333333333333333333.7)
\( (\alpha_{4}^{4}, \alpha_{4}^{4}, \alpha_{4}^{4}) = (8888888888888888888888888888888888888888888888.7)
\( (\beta_{4}^{4}, \beta_{4}^{4}, \beta_{4}^{4}) = (888888888888888888888888888888.7)
\( (\gamma_{4}^{4}, \gamma_{4}^{4}, \gamma_{4}^{4}) = (1222222222222222222222222222222222222.7)
\( \Gamma X_{5} = 4444444444444444444444444444444444.7)
(\alpha_{5}^{6}, \alpha_{5}^{6}, \alpha_{5}^{6}) = (12222222222222222222222222222222222.7)
\( (\beta_{5}^{6}, \beta_{5}^{6}, \beta_{5}^{6}) = (122222222222222222222222222.7)
\( (\gamma_{5}^{6}, \gamma_{5}^{6}, \gamma_{5}^{6}) = (122222222222222222222<fcel>\( \varepsilon_{\alpha^{4}} = -1^{\frac{d}{d}} -1^{\frac{d}{d}} -1^{\frac{d}{d}} -1^{\frac{d}{d}} -1^{\frac{d}{d}} -1^{\frac{d}{d}} -1^{\frac{d}{d}} -1^{\frac{d}{d}} -1^{\frac{d}{d}} -1^{\frac{d}{d}} -1^{\frac{d}{d}}, \\v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= - v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= -v= - v= -v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = v = .7)
(α_{o}^{i+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+j+ j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j- j> 
```


Table 12. 10-round impossible diferential characteristic


<table><tr><td></td><td>i</td><td><eq>\Delta X_i</eq> in forward direction</td><td><eq>\Delta X_i</eq> in backward direction</td><td>i</td><td></td><td></td></tr><tr><td>X[0]</td><td>0</td><td>10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000</td><td>000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000</td><td></td><td></td><td></td></tr><tr><td>X[1]</td><td></td><td>10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000</td><td></td><td></td><td></td><td></td></tr><tr><td rowspan="2">X[2]</td><td rowspan="2"></td><td rowspan="2">100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000</td><td rowspan="2"></td><td rowspan="2"></td><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td>X[3]</td><td></td><td>100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000</td><td>10</td><td></td><td></td><td></td></tr><tr><td>X[0]</td><td>1</td><td>00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000</td><td>10</td><td></td><td></td><td></td></tr><tr><td>X[1]</td><td></td><td>00010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000</td><td>10</td><td></td><td></td><td></td></tr><tr><td>X[2]</td><td></td><td>0001000000000000000000000000000000000000000000000000000000000000000000</td><td>10</td><td></td><td></td><td></td></tr><tr><td>X[3]</td><td></td><td>0001000000000000000000000000000000000000000000000000</td><td>10</td><td></td><td></td><td></td></tr><tr><td>X[0]</td><td>3</td><td>0001000000000000000000000000000000000000000000000000000000</td><td>9</td><td></td><td></td><td></td></tr><tr><td>X[1]</td><td></td><td>001111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111</td><td>8</td><td></td><td></td><td></td></tr><tr><td>X[2]</td><td></td><td>111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111</td><td></td><td></td><td></td><td></td></tr><tr><td>X[3]</td><td></td><td>111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111</td><td></td><td></td><td></td><td></td></tr><tr><td>X[0]</td><td>4</td><td>11111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111</td><td></td><td>8</td><td></td><td></td></tr><tr><td>X[1]</td><td></td><td>1111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111112</td><td></td><td></td><td></td><td></td></tr><tr><td>X[2]</td><td></td><td>111111111111111111111111111111111111111111111111111111111111111111111111111111111111111</td><td></td><td></td><td></td><td></td></tr><tr><td>X[3]</td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>X[0]</td><td>5</td><td>xxxxxxxxxxxxxxxxxxxxxxxxx1xxxxxxxxxx</td><td>7</td><td></td><td></td><td></td></tr><tr><td>X[1]</td><td></td><td>xxxxxxxxxxxxxxxxx100000000000</td><td>xxxxxxxxxx100000000000</td><td>xxxxxxxxxx100</td><td></td><td></td></tr><tr><td>X[2]</td><td></td><td>xxxxxxxxxx10000000000</td><td>xxxxxxxxxxxxxxxxxxxxxxxxxx</td><td>xxxxxxxxxx</td><td></td><td></td></tr><tr><td>X[3]</td><td></td><td>xxxxxxxxxx1</td><td>xxxxxxxxxxxxxxxxxxxxxxxxxx</td><td>xxxxxxxxxx</td><td></td><td></td></tr><tr><td>X[0]</td><td>6</td><td>xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx</td><td>xxxxxxxxxxxxxxxxxxxxxxxxxxx</td><td>xxxxxxxxxxxxxxxxxxxxxxxxxx</td><td></td><td></td></tr><tr><td>X[1]</td><td></td><td>xxxxxxxxxxxxxxxxxxxxxx</td><td>xxxxxxxxxxxxxxxxxxxxxxxxxx</td><td>xxxxxxxxxxxxxxxxxxxxxxxxxx</td><td></td><td></td></tr><tr><td>X[2]</td><td></td><td>xxxxxxxxxxxxxxxxxxxxxxxxxx</td><td>xxxxxxxxxxxxxxxxxxxxxxxxxx</td><td>xxxxxxxxxxxxxxxxxxxxxxxxxx</td><td></td><td></td></tr><tr><td>X[3]</td><td></td><td>xxxxxxxxxxxxxxxxxxxxxxxxxx</td><td>xxxxxxxxxxxxxxxxxxxxxxxxxx</td><td>xxxxxxxxxxxxxxxxxxxxxxxxxx</td><td></td><td></td></tr></table>

Equation (2) is XOR-sum of the following approximations: 

$$
\alpha_ {0} ^ {i} \cdot (X _ {i} [ 0 ] \oplus R K _ {i} [ 0 ]) \oplus \alpha_ {1} ^ {i} \cdot (X _ {i} [ 1 ] \oplus R K _ {i} [ 1 ]) = \alpha_ {2} ^ {i} \cdot R O R _ {9} (X _ {i + 1} [ 0 ]),
$$

$$
p _ {\alpha^ {i}} = 1 / 2 + \varepsilon_ {\alpha_ {i}},\tag{3}
$$

$$
\beta_ {0} ^ {i} \cdot (X _ {i} [ 1 ] \oplus R K _ {i} [ 2 ]) \oplus \beta_ {1} ^ {i} \cdot (X _ {i} [ 2 ] \oplus R K _ {i} [ 3 ]) = \beta_ {2} ^ {i} \cdot R O L _ {5} (X _ {i + 1} [ 1 ]),
$$

$$
p _ {\beta^ {i}} = 1 / 2 + \varepsilon_ {\beta_ {i}},\tag{4}
$$

$$
\gamma_ {0} ^ {i} \cdot (X _ {i} [ 2 ] \oplus R K _ {i} [ 4 ]) \oplus \gamma_ {1} ^ {i} \cdot (X _ {i} [ 3 ] \oplus R K _ {i} [ 5 ]) = \gamma_ {2} ^ {i} \cdot R O L _ {3} (X _ {i + 1} [ 2 ]),
$$

$$
p _ {\gamma^ {i}} = 1 / 2 + \varepsilon_ {\gamma_ {i}}.\tag{5}
$$

Let $\varepsilon$ be the bias of an r-round linear approximation. Note that $\varepsilon _ { i } = 4 \varepsilon _ { \alpha ^ { i } } \varepsilon _ { \beta _ { i } } \varepsilon _ { \gamma ^ { i } }$ and $\begin{array} { r } { \varepsilon = 2 ^ { r - 1 } \prod _ { i = 0 } ^ { r - 1 } \varepsilon _ { i } } \end{array}$ by Piling-Up Lemma [44]. 

Table 11 shows the 11-round linear approximation with the biases of $2 ^ { - 6 2 }$ The masks in the table are denoted in hexadecimal. 

## C Impossible Diferential Characteristic

Table 12 shows one of three 10-round impossible diferential characteristic reported in [20]. ‘1’ and ‘0’ mean the single bits 1 and 0 in the XOR diference. $\cdot _ { \mathbf { X } } ^ { } \rangle$ means an unknown bit. 

## References



1. Aoki, K., Sasaki, Y.: Meet-in-the-middle preimage attacks against reduced SHA-0 and SHA-1. In: Halevi, S. (ed.) CRYPTO 2009. LNCS, vol. 5677, pp. 70–89. Springer, Heidelberg (2009) 





2. Aumasson, J.P., Henzen, L., Meier, W., Phan, R.C.W.: SHA-3 proposal BLAKE. Submission to NIST (Round 3) (2010) 





3. Beaulieu, R., Shors, D., Smith, J., Treatman-Clar, S., Weeks, B., Wingers, L.: The SIMON and SPECK families of lightweight block ciphers. IACR Cryptology ePrint Archive. Report 2013/404 (2013) 





4. Bernstein, D.J.: The salsa20 stream cipher. In: SKEW 2005 — Symmetric Key Encryption Workshop (2005) 





5. Biham, E.: New types of cryptanalytic attacks using related keys. In: Helleseth, T. (ed.) EUROCRYPT 1993. LNCS, vol. 765, pp. 398–409. Springer, Heidelberg (1994) 





6. Biham, E., Biryukov, A., Shamir, A.: Cryptanalysis of skipjack reduced to 31 rounds using impossible diferentials. In: Stern, J. (ed.) EUROCRYPT 1999. LNCS, vol. 1592, pp. 12–23. Springer, Heidelberg (1999) 





7. Biham, E., Dunkelman, O., Keller, N.: The rectangle attack - rectangling the serpent. In: Pfitzmann, B. (ed.) EUROCRYPT 2001. LNCS, vol. 2045, pp. 340–357. Springer, Heidelberg (2001) 





8. Biham, E., Dunkelman, O., Keller, N.: Enhancing diferential-linear cryptanalysis. In: Zheng, Y. (ed.) ASIACRYPT 2002. LNCS, vol. 2501, pp. 254–266. Springer, Heidelberg (2002) 





9. Biham, E., Shamir, A.: Diferential Cryptanalysis of the Data Encryption Standard. Springer, Heidelberg (1993) 





10. Biryukov, A., Khovratovich, D.: Related-key cryptanalysis of the full AES-192 and AES-256. In: Matsui, M. (ed.) ASIACRYPT 2009. LNCS, vol. 5912, pp. 1–18. Springer, Heidelberg (2009) 





11. Biryukov, A., Khovratovich, D., Nikoli´c, I.: Distinguisher and related-key attack on the full AES-256. In: Halevi, S. (ed.) CRYPTO 2009. LNCS, vol. 5677, pp. 231–249. Springer, Heidelberg (2009) 





12. Biryukov, A., Wagner, D.: Slide attacks. In: Knudsen, L.R. (ed.) FSE 1999. LNCS, vol. 1636, pp. 245–259. Springer, Heidelberg (1999) 





13. Bogdanov, A.A., Knudsen, L.R., Leander, G., Paar, Ch., Poschmann, A., Robshaw, M., Seurin, Y., Vikkelsoe, C.: PRESENT: An ultra-lightweight block cipher. In: Paillier, P., Verbauwhede, I. (eds.) CHES 2007. LNCS, vol. 4727, pp. 450–466. Springer, Heidelberg (2007) 





14. Bogdanov, A., Khovratovich, D., Rechberger, Ch.: Biclique cryptanalysis of the full AES. In: Lee, D.H., Wang, X. (eds.) ASIACRYPT 2011. LNCS, vol. 7073, pp. 344–371. Springer, Heidelberg (2011) 





15. Bogdanov, A., Wang, M.: Zero correlation linear cryptanalysis with reduced data complexity. In: Canteaut, A. (ed.) FSE 2012. LNCS, vol. 7549, pp. 29–48. Springer, Heidelberg (2012) 





16. Borghof, J., Canteaut, A., G¨uneysu, T., Kavun, E.B., Knezevic, M., Knudsen, L.R., Leander, G., Nikov, V., Paar, C., Rechberger, C., Rombouts, P., Thomsen, S., Yal¸cın, T.: PRINCE - A low-latency block cipher for pervasive computing applications. In: Wang, X., Sako, K. (eds.) ASIACRYPT 2012. LNCS, vol. 7658, pp. 208–225. Springer, Heidelberg (2012) 





17. Canteaut, A., Chabaud, F.: A new algorithm for finding minimum-weight words in a linear code: application to McEliece’s cryptosystem and to narrow-sense BCH codes of length 511. IEEE Trans. Inf. Theory 44(1), 367–378 (1998) 





18. Certicom White Paper Series. Critical infrastructure protection for AMI using a comprehensive security platform, Februrary 2009 





19. Courtois, N.T., Pieprzyk, J.: Cryptanalysis of block ciphers with overdefined systems of equations. In: Zheng, Y. (ed.) ASIACRYPT 2002. LNCS, vol. 2501, pp. 267–287. Springer, Heidelberg (2002) 





20. COSIC. Final Report: Security Evaluation of the Block Cipher LEA (2011) 





21. Daemen, J., Rijmen, V.: The Design of Rijndael: AES. In: The Advanced Encryption Standard. Springer (2002) 





22. Darnall, M., Kuhlman, D.: AES software implementations on ARM7TDMI. In: Barua, R., Lange, T. (eds.) INDOCRYPT 2006. LNCS, vol. 4329, pp. 424–435. Springer, Heidelberg (2006) 





23. Difie, W., Hellman, M.: Exhaustive cryptanalysis of the NBS data encryption standard. Computer 10(6), 74–84 (1977) 





24. Dunkelman, O., Keller, N., Shamir, A.: A practical-time related-key attack on the KASUMI cryptosystem used in GSM and 3G telephony. In: Rabin, T. (ed.) CRYPTO 2010. LNCS, vol. 6223, pp. 393–410. Springer, Heidelberg (2010) 





25. eBACS: ECRYPT Benchmarking of Cryptographic Systems, bench.cr.yp.to. 





26. Ferguson, N., Lucks, S., Schneier, B., DougWhiting, Bellare, M., Tadayoshi Kohno, Callas, J., Jesse Walker, : The skein hash function family, Submission to NIST (Round 3) (2010) 





27. ADVANCED ENCRYPTION STANDARD, (AES), Federal Information Processing Standards, Publication 197, 26 November 2001) 





28. Gong, Z., Nikova, S., Law, Y.W.: KLEIN: A new family of lightweight block ciphers. In: Juels, A., Paar, Ch. (eds.) RFIDSec 2011. LNCS, vol. 7055, pp. 1–18. Springer, Heidelberg (2012) 





29. Mukhopadhyay, D.: An improved fault based attack of the advanced encryption standard. In: Preneel, B. (ed.) AFRICACRYPT 2009. LNCS, vol. 5580, pp. 421– 434. Springer, Heidelberg (2009) 





30. Guo, J., Peyrin, T., Poschmann, A., Robshaw, M.: The LED block cipher. In: Preneel, B., Takagi, T. (eds.) CHES 2011. LNCS, vol. 6917, pp. 326–341. Springer, Heidelberg (2011) 





31. Hong, D., Sung, J., Hong, S.H., Lim, J.-I., Lee, S.-J., Koo, B.-S., Lee, C.-H., Chang, D., Lee, J., Jeong, K., Kim, H., Kim, J.-S., Chee, S.: HIGHT: A new block cipher suitable for low-resource device. In: Goubin, L., Matsui, M. (eds.) CHES 2006. LNCS, vol. 4249, pp. 46–59. Springer, Heidelberg (2006) 





32. Hong, D., Koo, B., Kwon, D.: Biclique attack on the full HIGHT. In: Kim, H. (ed.) ICISC 2011. LNCS, vol. 7259, pp. 365–374. Springer, Heidelberg (2012) 





33. ISO/IEC 19772, Information technology — Security techniques — Authenticated encryption (2009) 





34. Jakimoski, G., Desmedt, Y.: Related-key diferential cryptanalysis of 192-bit key AES variants. In: Matsui, M., Zuccherato, R. (eds.) SAC 2004. LNCS, vol. 3006, pp. 208–221. Springer, Heidelberg (2004) 





35. K¨asper, E., Schwabe, P.: Faster and timing-attack resistant AES-GCM. In: Clavier, C., Gaj, K. (eds.) CHES 2009. LNCS, vol. 5747, pp. 1–27. Springer, Heidelberg (2009) 





36. Kelsey, J., Kohno, T., Schneier, B.: Amplified boomerang attacks against reducedround MARS and serpent. In: Schneier, B. (ed.) FSE 2000. LNCS, vol. 1978, pp. 75–93. Springer, Heidelberg (2001) 





37. Kelsey, J., Schneier, B., Wagner, D.: Related-key cryptanalysis of 3-WAY, biham-DES, CAST, DES-X, newDES, RC2, and TEA. In: Han, Y., Quing, S. (eds.) ICICS 1997. LNCS, vol. 1334, pp. 233–246. Springer, Heidelberg (1997) 





38. Khovratovich, D., Nikoli´c, I.: Rotational cryptanalysis of ARX. In: Hong, S., Iwata, T. (eds.) FSE 2010. LNCS, vol. 6147, pp. 333–346. Springer, Heidelberg (2010) 





39. Knudsen, L.R.: Truncated and higher order diferentials. In: Preneel, B. (ed.) FSE 1994. LNCS, vol. 1008, pp. 196–211. Springer, Heidelberg (1995) 





40. Knudsen, L.R., Wagner, D.: Integral cryptanalysis. In: Daemen, J., Rijmen, V. (eds.) FSE 2002. LNCS, vol. 2365, pp. 112–127. Springer, Heidelberg (2002) 





41. Koo, B., Hong, D., Kwon, D.: Related-key attack on the full HIGHT. In: Rhee, K.-H., Nyang, D.H. (eds.) ICISC 2010. LNCS, vol. 6829, pp. 49–67. Springer, Heidelberg (2011) 





42. Lipmaa, H., Moriai, S.: Eficient algorithms for computing diferential properties of addition. In: Matsui, M. (ed.) FSE 2001. LNCS, vol. 2355, pp. 336–350. Springer, Heidelberg (2002) 





43. Matsuda, S., Moriai, S.: Lightweight cryptography for the cloud: exploit the power of bitslice implementation. In: Prouf, E., Schaumont, P. (eds.) CHES 2012. LNCS, vol. 7428, pp. 408–425. Springer, Heidelberg (2012) 





44. Matsui, M.: Linear cryptanalysis method for DES cipher. In: Helleseth, T. (ed.) EUROCRYPT 1993. LNCS, vol. 765, pp. 386–397. Springer, Heidelberg (1994) 





45. Moradi, A., Poschmann, A., Ling, S., Paar, Ch., Wang, H.: Pushing the limits: a very compact and a threshold implementation of AES. In: Paterson, K.G. (ed.) EUROCRYPT 2011. LNCS, vol. 6632, pp. 69–88. Springer, Heidelberg (2011) 





46. Needham, R.M., Wheeler, D.J.: TEA extensions. computer laboratory, University of Cambridge, Technical report, October 1997 





47. Osvik, D.A., Bos, J.W., Stefan, D., Canright, D.: Fast software AES encryption. In: Hong, S., Iwata, T. (eds.) FSE 2010. LNCS, vol. 6147, pp. 75–93. Springer, Heidelberg (2010) 





48. https://realtimelogic.com/products/sharkssl/Coldfire-80Mhz/ 





49. Rivest, R.L., Robshaw, M.J.B., Sidney, R., Yin, Y.L.: Thr RC6 block cipher (1998) 





50. Sasaki, Y., Aoki, K.: Finding preimages in full MD5 faster than exhaustive search. In: Joux, A. (ed.) EUROCRYPT 2009. LNCS, vol. 5479, pp. 282–296. Springer, Heidelberg (2009) 





51. Shibutani, K., Isobe, T., Hiwatari, H., Mitsuda, A., Akishita, T., Shirai, T.: Piccolo: an ultra-lightweight blockcipher. In: Preneel, B., Takagi, T. (eds.) CHES 2011. LNCS, vol. 6917, pp. 342–357. Springer, Heidelberg (2011) 





52. Shirai, T., Shibutani, K., Akishita, T., Moriai, S., Iwata, T.: The 128-bit blockci pher CLEFIA (Extended abstract). In: Biryukov, A. (ed.) FSE 2007. LNCS, vol. 4593, pp. 181–195. Springer, Heidelberg (2007) 





53. Suzaki, T., Minematsu, K., Morioka, S., Kobayasi, E.: Twine: A lightweight, versatile block cipher. In: Proceedings of ECRYPT Workshop on Lightweight Cryptography (2011) 





54. Wagner, D.: The boomerang attack. In: Knudsen, L.R. (ed.) FSE 1999. LNCS, vol. 1636, pp. 156–170. Springer, Heidelberg (1999) 





55. Wall´en, J.: On the diferential and linear properties of addition, Master’s thesis, Helsinki University of Technology, Laboratory for Theoretical Computer Science, November 2003 





56. Wheeler, D.J., Needham, R.M.: TEA, a tiny encryption algorithm. In: Preneel, B. (ed.) FSE 1994. LNCS, vol. 1008, pp. 363–366. Springer, Heidelberg (1995) 





57. Wheeler, D.J., Needham, R.M.: Correction of XTEA. Computer Laborarory, University of Cambridge, Technical report (October 1998) 





58. Yarrkov, E.: Cryptanalysis of XXTEA, IACR Cryptology ePrint Archive 2010/254 (2010) 





## Appendix A: Test Vectors

Known-answer test vectors for LEA-128 / LEA-192 / LEA-256, from
https://en.wikipedia.org/wiki/LEA_(cipher) . The 128-bit block is four 32-bit
words; the key is 4/6/8 words for the 128/192/256-bit variants (24/28/32 rounds).
Values are given first as the source's byte sequence, then as 32-bit word lists
(bytes grouped left-to-right, byte 0 = most significant) in the agent's
[[plaintext], [key]], [ciphertext] form (word_bitsize = 32).

Endianness note: LEA's reference implementation loads the byte string into 32-bit
words in LITTLE-endian order. The word lists here use the direct big-endian reading
of the bytes. If a Build/KAT does not match, byte-reverse each 32-bit word (e.g.
0x10111213 -> 0x13121110) so the word convention matches the LEA model.

### LEA-128

Plaintext  (bytes): 10 11 12 13 14 15 16 17 18 19 1a 1b 1c 1d 1e 1f
Key        (bytes): 0f 1e 2d 3c 4b 5a 69 78 87 96 a5 b4 c3 d2 e1 f0
Ciphertext (bytes): 9f c8 4e 35 28 c6 c6 18 55 32 c7 a7 04 64 8b fd

Plaintext  = [0x10111213, 0x14151617, 0x18191a1b, 0x1c1d1e1f]
Key        = [0x0f1e2d3c, 0x4b5a6978, 0x8796a5b4, 0xc3d2e1f0]
Ciphertext = [0x9fc84e35, 0x28c6c618, 0x5532c7a7, 0x04648bfd]

### LEA-192

Plaintext  (bytes): 20 21 22 23 24 25 26 27 28 29 2a 2b 2c 2d 2e 2f
Key        (bytes): 0f 1e 2d 3c 4b 5a 69 78 87 96 a5 b4 c3 d2 e1 f0 f0 e1 d2 c3 b4 a5 96 87
Ciphertext (bytes): 6f b9 5e 32 5a ad 1b 87 8c dc f5 35 76 74 c6 f2

Plaintext  = [0x20212223, 0x24252627, 0x28292a2b, 0x2c2d2e2f]
Key        = [0x0f1e2d3c, 0x4b5a6978, 0x8796a5b4, 0xc3d2e1f0, 0xf0e1d2c3, 0xb4a59687]
Ciphertext = [0x6fb95e32, 0x5aad1b87, 0x8cdcf535, 0x7674c6f2]

### LEA-256

Plaintext  (bytes): 30 31 32 33 34 35 36 37 38 39 3a 3b 3c 3d 3e 3f
Key        (bytes): 0f 1e 2d 3c 4b 5a 69 78 87 96 a5 b4 c3 d2 e1 f0 f0 e1 d2 c3 b4 a5 96 87 78 69 5a 4b 3c 2d 1e 0f
Ciphertext (bytes): d6 51 af f6 47 b1 89 c1 3a 89 00 ca 27 f9 e1 97

Plaintext  = [0x30313233, 0x34353637, 0x38393a3b, 0x3c3d3e3f]
Key        = [0x0f1e2d3c, 0x4b5a6978, 0x8796a5b4, 0xc3d2e1f0, 0xf0e1d2c3, 0xb4a59687, 0x78695a4b, 0x3c2d1e0f]
Ciphertext = [0xd651aff6, 0x47b189c1, 0x3a8900ca, 0x27f9e197]
