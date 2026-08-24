# FUTURE: A Lightweight Block Cipher Using An Optimal Difusion Matrix

Kishan Chand Gupta<sup>1</sup>, Sumit Kumar Pandey<sup>2</sup>, and Susanta Samanta<sup>3</sup> 

<sup>1</sup> Applied Statistics Unit, Indian Statistical Institute, 203, B.T. Road, Kolkata-700108, INDIA. kishan@isical.ac.in 

2 Computer Science and Engineering, Indian Institute of Technology Jammu, Jagti, PO Nagrota, Jammu-181221, INDIA. 

emailpandey@gmail.com 

Applied Statistics Unit, Indian Statistical Institute, 203, B.T. Road, Kolkata-700108, INDIA. susantas_r@isical.ac.in 

Abstract. In this work, we present FUTURE, a new 64-bit lightweight SPN-based block cipher. FUTURE encrypts data in a single clock cycle with a very low implementation cost compared to other block ciphers in unrolled fashion. The advantage of an unrolled implementation is that there are no sequential elements, such as registers, in the implementation and hence no clock. While designing FUTURE in a completely unrolled fashion, the goal was to keep the implementation costs low along with minimal latency. Security is the most essential aspect of a cryptographic primitive. However, in addition to security, an essential secondary criterion for a lightweight cryptographic primitive is eficient implementation in hardware and software. Most lightweight block ciphers refrain from the use of MDS matrices in the round function, and as a result, they need more rounds for full encryption. Using MDS matrices in a lightweight block cipher is a challenging task due to its high implementation cost. The lightweight block cipher FUTURE overcomes this challenge by judiciously choosing a very lightweight MDS matrix, which is a composition of 4 sparse matrices. We also use a lightweight cryptographically significant Sbox which is a composition of 4 Sboxes. 

Keywords: Lightweight cryptography· Block cipher· Substitution-permutation network· MDS matrix. 

## 1 Introduction

AES [21], SHA-256 [31] and RSA [33] are some of the most widely used cryptography methods, and they work well on systems with reasonable processing power and memory capabilities. But these primitives are not suitable in constrained environments such as RFID tags, sensor networks, contactless smart cards, medical services gadgets, etc. For this purpose in the recent decade, a large number of lightweight cryptographic primitives have been suggested and deployed on resource-constrained devices. While there is no precise meaning of the term lightweight cryptography, it is normally perceived as cryptography with a solid spotlight on eficiency. Here eficiency can be assessed by diferent models like hardware cost, power utilization, latency, etc., and their blends. 

A block cipher converts plaintext blocks of a fixed length n (for the most part n= 64 or 128) to ciphertext blocks with the length n under the influence of a secret key k. More precisely, a block cipher is a set of Boolean permutations working on n-bit vectors. This set contains a Boolean permutation for each value of the secret key k. Also, block ciphers are fundamentally arranged into two sorts: Feistel structure and substitution-permutation network (SPN) structure. Feistel structures (e.g. TWINE [42], Piccolo [39]) generally apply a round function to just one half of the block due to which they may be implemented in hardware with minimal cost. However as Feistel structures inject non-linearity in just one half of the block in every round, such designs require more executions of round functions than SPN structures in order to preserve the security margins. 

Due to the large deployment of low-resource devices and expanding need to provide security among such devices, lightweight cryptography has become a popular topic. Thus, research on designing and analyzing lightweight block ciphers has got a great deal of attention. Initial lightweight block ciphers such as PRESENT [10] and KATAN [22] focused mainly on the chip area and employed simple round functions as their primary building blocks. With the advent of lightweight block ciphers, this field expanded dramatically in terms of possibilities. At this point, we have specialized ciphers that are optimized for code size, latency, energy and power. For example we have SIMON and SPECK [6] for code-size, PRINCE [11] and MANTIS [7] for latency and MIDORI [3] and GIFT [4] for energy. Furthermore, the cost of implementing decryption with encryption has been optimized for some block ciphers. Such as in MIDORI all the components are involutory and PRINCE has α-reflection property. 

Also, many lightweight block cipher such as LED [24], MIDORI and SKINNY [7] adopt the general structure of AES round function and tweak its components to improve their performances. 

There have also been attempts to create lightweight tweakable block ciphers, a block cipher with an extra input called tweak. This primitive supports better encryption modes and eficient constructions of authenticated encryption. SKINNY, MANTIS, CRAFT [8], QARMA [2] are some examples of such primitives. Also for CRAFT, design considerations were made to ensure that its implementations were resistant to Diferential Fault Analysis (DFA) attacks. 

Also, it is worth mentioning that MDS matrices provide maximum difusion in block ciphers. Whereas most of the lightweight block ciphers do not employ MDS matrices in a round function due to their high cost. As a consequence, they need more rounds to achieve security against some well-known attacks like diferential, impossible diferential, and linear. So it is challenging to use MDS matrices in a lightweight block cipher. Our proposed lightweight block cipher FUTURE overcomes this challenge by choosing a suitable MDS matrix. 

## 2 Definition and Preliminaries

Let $\mathbb { F } _ { 2 } = \{ 0 , 1 \}$ be the finite field of two elements, $\mathbb { F } _ { 2 ^ { r } }$ be the finite field of $2 ^ { r }$ elements and $\mathbb { F } _ { 2 ^ { r } } ^ { n }$ be the set of vectors of length n with entries from the finite field $\mathbb { F } _ { 2 ^ { r } }$ . Elements of $\mathbb { F } _ { 2 ^ { r } }$ can be represented as polynomials of degree less than $r$ over $\mathbb { F } _ { 2 }$ . For example, let $\beta \in \mathbb { F } _ { 2 ^ { r } }$ , then $\beta$ can be represented as $\textstyle \sum _ { i = 0 } ^ { r - 1 } b _ { i } \alpha ^ { i }$ ， where $b _ { i } \in \mathbb { F } _ { 2 }$ and α is the root of the constructing polynomial of $\mathbb { F } _ { 2 ^ { r } }$ 

$\mathbb { F } _ { 2 ^ { r } }$ and $\mathbb { F } _ { 2 } ^ { r }$ are isomorphic when both of them are regarded as vector spaces over $\mathbb { F } _ { 2 }$ . The isomorphism is given by $x \ = \ ( x _ { 1 } \alpha _ { 1 } + x _ { 2 } \alpha _ { 2 } + \cdot \cdot \cdot + x _ { r } \alpha _ { r } ) \ $ $( x _ { 1 } , x _ { 2 } , \cdots , x _ { r } )$ , where $\{ \alpha _ { 1 } , \alpha _ { 2 } , \ldots , \alpha _ { r } \}$ is a basis of $\mathbb { F } _ { 2 ^ { r } }$ 

A square matrix is a matrix with the same number of rows and columns. An $n \times n$ matrix is known as a matrix of order n. 

In the following section, we will discuss some fundamental definitions and properties of MDS matrices. For a comprehensive overview of various theories on the construction of MDS matrices, readers may look at [25]. 

## 2.1 MDS matrix

The difusion properties of an MDS matrix make it useful in cryptography. The concept originates from coding theory, specifically from maximum distance separable (MDS) codes. 

Theorem 1. (The Singleton bound)[29, page 33] Let C be an $[ n , k , d ]$ code. Then 0 $l \leq n - k + 1$ 

Definition 1. A code with $d = n - k + 1$ is called maximum distance separable code or MDS code in short. 

Theorem 2. [29, page 321] An $[ n , k , d ]$ code C with generator matrix $G =$ $[ I \mid A ]$ , where A is a $k \times ( n - k )$ matrix, is MDS if and only if every square submatrix (formed from any i rows and any i columns, for any $i = 1 , 2 , \ldots , m i n \{ k , n -$ k}) of A is nonsingular. 

The following fact is another way to characterize an MDS matrix. 

Fact 1 A square matrix A is an MDS matrix if and only if every square submatrices $o f A$ are nonsingular. 

The difusion power of a linear transformation (specified by a matrix) is measured by its branch numbers [21, pages 130–132]. 

Definition 2. [21, page 132] The Diferential branch number $\beta _ { d } ( M )$ ofa matrix M of order n over finite field $\mathbb { F } _ { 2 ^ { r } }$ is defined as the minimum number of nonzero components in the input vector x and the output vector Mx as we range over all nonzero $x \in ( \mathbb { F } _ { 2 ^ { r } } ) ^ { n }$ i.e. 

$$
\beta_ {d} (M) = \min _ {x \neq \boldsymbol {0}} (w (x) + w (M x))
$$

where $w ( x )$ denotes the weight of the vector x i.e. number of nonzero components of the vector x. 

Note that the diferential branch number of a matrix M is exactly the distance of the linear code generated by the matrix $[ I \ | \ M ]$ 

Definition 3. $I ^ { \mathcal { Q } 1 , }$ page 132] The Linear branch number $\beta _ { l } ( M )$ of a matrix M $o f$ order n over finite field $\mathbb { F } _ { 2 } ,$ r is defined as the minimum number of nonzero components in the input vector x and the output vector $M ^ { T } { _ { \lambda } }$ x as we range over all nonzero $x \in ( \mathbb { F } _ { 2 ^ { r } } ) ^ { n }$ i.e. 

$$
\beta_ {l} (M) = \min _ {x \neq \boldsymbol {0}} (w (x) + w (M ^ {T} x))
$$

where $w ( x )$ denotes the weight of the vector x i.e. number of nonzero components of the vector x. 

Remark 1. [21, page 132] Note that the maximal value of $\beta _ { d } ( M )$ and $\beta _ { l } ( M )$ are $n + 1$ . In general $\beta _ { d } ( M ) \neq \beta _ { l } ( M )$ but if a matrix has the maximum possible diferential or linear branch number, then both branch numbers are equal. 

Therefore the following fact is another characterization of MDS matrix. 

Fact 2 [21] A square matrix A of order n is MDS if and only $i f \beta _ { d } ( A ) = \beta _ { l } ( A ) =$ $n + 1$ 

For simplicity, in this paper, we will consider the diferential branch number only and we will call this simply the branch number. 

Some definitions and properties of Boolean functions and Sboxes are revisited in the following section. For a comprehensive overview of Boolean functions, we recommend [12,20]. 

## 2.2 Boolean Function and Sbox

An n-variable Boolean function is a map $g : \mathbb { F } _ { 2 } ^ { n } \to \mathbb { F } _ { 2 }$ . The support of a Boolean function $g$ is denoted by $S u p ( g )$ and is defined to be $S u p ( g ) = \{ x : g ( x ) = 1 \}$ The weight of $g$ is denoted by $w ( g )$ and is defined to be $w ( g ) = | S u p ( g ) |$ . A function $g$ is said to be balanced if $\overset { \cdot } { w } ( g ) = 2 ^ { n - 1 }$ 

A Boolean function can be represented by its binary output vector containing $2 ^ { n }$ elements, referred to as the truth table. Another way of representing $g$ is by its algebraic normal form: 

$$
g (x) = \bigoplus_ {(\alpha_ {n - 1}, \alpha_ {n - 2}, \ldots , \alpha_ {1}, \alpha_ {0}) \in \mathbb {F} _ {2} ^ {n}} A _ {g} (\alpha_ {n - 1}, \alpha_ {n - 2}, \ldots , \alpha_ {1}, \alpha_ {0}) x _ {n - 1} ^ {\alpha_ {n - 1}} x _ {n - 2} ^ {\alpha_ {n - 2}} \ldots x _ {1} ^ {\alpha_ {1}} x _ {0} ^ {\alpha_ {0}}
$$

where $x \ = \ ( x _ { n - 1 } , x _ { n - 2 } , \ldots , x _ { 1 } , x _ { 0 } ) \in \mathbb { F } _ { 2 } ^ { n }$ and $A _ { g } ( x _ { n - 1 } , x _ { n - 2 } , \ldots , x _ { 1 } , x _ { 0 } )$ is a Boolean function. 

The nonlinearity of a Boolean function is a key parameter in cryptography. This quantity measures the Hamming distance<sup>4</sup> of a Boolean function from the set of all afine functions. If $A _ { n }$ be the set of all n-variable afine functions, the nonlinearity $n l ( g )$ of an n-variable Boolean function is defined as $n l ( g ) =$ min $d ( g , l )$ $l \in A _ { r }$ 2 

The maximum nonlinearity achievable by an n-variable Boolean function is $2 ^ { n - 1 } - 2 ^ { ( n - 2 ) / 2 }$ . Functions achieving this value of nonlinearity are called bent and can exist only when n is even [34]. 

Definition 4. An $n \times m$ Sbox is a mapping $S : \mathbb { F } _ { 2 } ^ { n }  \mathbb { F } _ { 2 } ^ { m }$ 

Then, to each $x = ( x _ { n - 1 } , x _ { n - 2 } , \ldots , x _ { 1 } , x _ { 0 } ) \in \mathbb { F } _ { 2 } ^ { n }$ some $y = ( y _ { m - 1 } , \textrm { } y _ { m - 2 } )$ 2 $y _ { 1 } , \ y _ { 0 } ) \in \mathbb { F } _ { 2 } ^ { m }$ is assigned by $S ( x ) = y$ . The $n \times m$ Sbox S can be considered as a vectorial Boolean function comprising m individual Boolean functions $f _ { m - 1 } , f _ { m - 2 } , \ldots , f _ { 1 } , f _ { 0 } : \mathbb { F } _ { 2 } ^ { n } \to \mathbb { F } _ { 2 }$ , where $f _ { i } ( x ) = y _ { i }$ for $i = 0 , 1 , 2 , \ldots , m - 1$ These functions are referred to as the coordinate Boolean functions of the Sbox. Thus we can write $S ( x ) = ( f _ { m - 1 } ( x ) , f _ { m - 2 } ( x ) , \ldots , f _ { 1 } ( x ) , f _ { 0 } ( x ) )$ . 

It is well known that most of desirable cryptographic properties of the Sbox can be defined also in terms of all non-trivial linear combinations of the coordinate functions, referred to as the Sbox component Boolean functions $g _ { c } : \mathbb { F } _ { 2 } ^ { n } \to$ $\mathbb { F } _ { 2 } .$ , where $g _ { c } = c _ { m - 1 } f _ { m - 1 } \oplus . . . \oplus c _ { 1 } f _ { 1 } \oplus c _ { 0 } f _ { 0 }$ and $c = ( c _ { m - 1 } , \hdots , c _ { 1 } , c _ { 0 } ) \in \mathbb { F } _ { 2 } ^ { m } \backslash \{ 0 \}$ To avoid trivial statistical attacks, an Sbox should be regular (balanced). An $n \times m$ Sbox S with $n \geq m$ is said to be regular if, for each its output $y \in \mathbb { F } _ { 2 } ^ { m }$ 2 there are exactly $2 ^ { n - m }$ inputs that are mapped to $y .$ . Clearly, each bijective n×n Sbox S is always regular since it represents a permutation. It is well known that an $n \times m$ Sbox with n ≥ m is regular if and only if all its component Boolean functions are balanced [38]. 

The nonlinearity of an Sbox is a fundamental parameter in cryptography. The nonlinearity of $S ,$ denoted by $n l ( S )$ , is given by the minimal nonlinearity among the nonlinearities of the component Boolean functions: 

$$
n l (S) = \min _ {c \in \mathbb {F} _ {2} ^ {m} \backslash \{0 \}} n l (g _ {c}).
$$

The best known nonlinearity of a 4-variable balanced Boolean function is 4 [12, Table 3.2]. Thus the maximum nonlinearity of an $4 \times 4$ bijective Sbox is 4. In this paper, we are discussing about $n \times n$ bijective Sboxes and we will call these as n-bit Sboxes. 

Definition 5. For an n-bit Sbox, the diference distribution table (DDT) of S is the table of size $2 ^ { n } \times 2 ^ { n }$ of integers $\delta _ { S } ( a , b )$ defined by 

$$
\delta_ {S} (a, b) = \# \left\{x \in \mathbb {F} _ {2} ^ {n}: S (x \oplus a) \oplus S (x) = b \right\}
$$

The diferential uniformity of $S ,$ denoted by $\delta _ { S }$ , is the highest value in the DDT, i.e. $\delta _ { S } = \operatorname* { m a x } _ { a , b \in \mathbb { F } _ { 2 } ^ { n } , a \neq 0 } \delta _ { S } ( a , b )$ and $\frac { \delta _ { S } } { 2 ^ { n } }$ is called the maximal probability of a diferential of the Sbox S. 

An Sbox should have low diferential uniformity to increase block cipher immunity to diferential cryptanalysis [9]. 

Definition 6. For an n-bit Sbox, the linear approximation table (LAT) of S is the table of size $2 ^ { n } \times 2 ^ { n }$ of integers $L _ { S } ( a , b )$ defined by 

$$
L _ {S} (a, b) = \# \left\{x \in \mathbb {F} _ {2} ^ {n}: x \cdot a \oplus S (x) \cdot b = 0 \right\} - 2 ^ {n - 1},
$$

where $\ddots \mathit { \Pi } ^ { \prime }$ denotes the bitwise logical AND. 

The maximal absolute bias of a linear approximation of an Sbox is given by $\textstyle { \frac { L _ { S } } { 2 ^ { n } } }$ , where $L _ { S } = \operatorname* { m a x } _ { a , b \in \mathbb { F } _ { 2 } ^ { n } , a \neq 0 } | L _ { S } ( a , b ) |$ . 

As with the diferential uniformity, the lower value of $L _ { S }$ is required to increase the block cipher’s resistance to linear cryptanalysis [30]. 

Now we will discuss the design specification of the block cipher FUTURE. 

## 3 Structure of FUTURE

FUTURE is a new SPN-based block cipher and consists of 10 rounds in a fully unrolled fashion. It accepts 128-bit keys and has a block size of 64-bit. 

## 3.1 Round Function

Each encryption round of FUTURE is composed of four diferent transformations in the following order: SubCell, MixColumn, ShiftRow and AddRoundKey (see illustration in Figure 1). The final round of the block cipher is slightly diferent, MixColumn operation is removed here. The cipher receives a 64-bit plaintext $P = b _ { 0 } b _ { 1 } b _ { 2 } \dots b _ { 6 2 } b _ { 6 3 }$ as the cipher state I, where $b _ { 0 }$ is the most significant bit. The cipher state can also be expressed as 16 4-bit cells as follows: 

$$
I = \left[ \begin{array}{c c c c} s _ {0} & s _ {4} & s _ {8} & s _ {1 2} \\ s _ {1} & s _ {5} & s _ {9} & s _ {1 3} \\ s _ {2} & s _ {6} & s _ {1 0} & s _ {1 4} \\ s _ {3} & s _ {7} & s _ {1 1} & s _ {1 5} \end{array} \right],
$$

i.e. $s _ { i } \in \{ 0 , 1 \} ^ { 4 }$ . The i-th round input state is defined as $I _ { i }$ , namely $I _ { 0 } = P$ 

<table><tr><td rowspan="4"></td><td rowspan="4">SC</td><td rowspan="4">MC</td><td>ShiftRow</td><td rowspan="4">ARK</td></tr><tr><td>&gt;&gt;&gt; 1</td></tr><tr><td>&gt;&gt;&gt; 2</td></tr><tr><td>&gt;&gt;&gt; 3</td></tr></table>


Fig. 1. The round function applies four diferent transformations: SubCells (SC), Mix-Columns (MC), ShiftRows (SR) and AddRoundKey (ARK).


Nonlinear Transformation SubCell. SubCell is a nonlinear transformation in which 4-bit Sbox S is applied to every cell of the cipher internal state. 

$$
s _ {i} \leftarrow S (s _ {i}) \quad \text { for } i = 0, 1, \dots , 1 5.
$$

where S is a 4-bit Sbox applied to every cell of the cipher internal state. The Sbox S is a composition of four low hardware cost Sboxes $S _ { 1 } , S _ { 2 } , S _ { 3 }$ and $S _ { 4 }$ i.e. $S ( s _ { j } ) = S _ { 1 } \circ S _ { 2 } \circ S _ { 3 } \circ S _ { 4 } ( s _ { j } )$ for $j = 0 , 1 , \ldots , 1 5$ 

The Sboxes in hexadecimal notation are given by the following Table 1. 

<table><tr><td>x</td><td>0</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td><td>7</td><td>8</td><td>9</td><td>a</td><td>b</td><td>c</td><td>d</td><td>e</td><td>f</td></tr><tr><td><eq>S_4(x)</eq></td><td>0</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td><td>7</td><td>8</td><td>9</td><td>e</td><td>f</td><td>c</td><td>d</td><td>a</td><td>b</td></tr><tr><td><eq>S_3(x)</eq></td><td>0</td><td>1</td><td>2</td><td>3</td><td>4</td><td>d</td><td>6</td><td>f</td><td>8</td><td>9</td><td>a</td><td>b</td><td>c</td><td>5</td><td>e</td><td>7</td></tr><tr><td><eq>S_2(x)</eq></td><td>1</td><td>3</td><td>0</td><td>2</td><td>5</td><td>7</td><td>4</td><td>6</td><td>9</td><td>a</td><td>8</td><td>b</td><td>d</td><td>e</td><td>c</td><td>f</td></tr><tr><td><eq>S_1(x)</eq></td><td>0</td><td>1</td><td>2</td><td>3</td><td>4</td><td>7</td><td>6</td><td>5</td><td>8</td><td>9</td><td>a</td><td>b</td><td>c</td><td>f</td><td>e</td><td>d</td></tr><tr><td><eq>S(x)</eq></td><td>1</td><td>3</td><td>0</td><td>2</td><td>7</td><td>e</td><td>4</td><td>d</td><td>9</td><td>a</td><td>c</td><td>6</td><td>f</td><td>5</td><td>8</td><td>b</td></tr></table>


Table 1. Specifications of FUTURE Sbox


Linear Transformation MixColumn. The MixColumn is a linear operation that operates separately on each of the four columns of the state. FUTURE uses an MDS matrix M for the MixColumns operation. We have 

$$
\left(s _ {i}, s _ {i + 1}, s _ {i + 2}, s _ {i + 3}\right) \leftarrow M \cdot \left(s _ {i}, s _ {i + 1}, s _ {i + 2}, s _ {i + 3}\right) ^ {t}
$$

for $i = { 0 , 4 , 8 , 1 2 }$ 

Here M is an MDS matrix given by 

$$
M = \left[ \begin{array}{c c c c} \alpha^ {3} & \alpha^ {3} + 1 & 1 & \alpha^ {3} \\ \alpha + 1 & \alpha & \alpha^ {3} + 1 & \alpha^ {3} + 1 \\ \alpha & \alpha + 1 & \alpha^ {3} & \alpha^ {3} + 1 \\ \alpha^ {3} + 1 & \alpha^ {3} + 1 & \alpha^ {3} & 1 \end{array} \right]
$$

which is constructed by composition of 4 sparse matrices $M _ { 1 } , M _ { 2 } , M _ { 3 }$ and $M _ { 4 }$ of order 4 i.e. $M = M _ { 1 } M _ { 2 } M _ { 3 } M _ { 4 }$ , where 

$$
M _ {1} = \left[ \begin{array}{c c c c} 0 & 0 & 1 & 1 \\ 1 & 0 & 0 & 0 \\ 1 & 1 & 0 & 0 \\ 0 & 0 & 1 & 0 \end{array} \right], M _ {2} = \left[ \begin{array}{c c c c} 0 & 0 & 1 & \alpha \\ 1 & 0 & 0 & 0 \\ \alpha^ {3} + 1 & 1 & 0 & 0 \\ 0 & 0 & 1 & 0 \end{array} \right], M _ {3} = \left[ \begin{array}{c c c c} 0 & 0 & 1 & 1 \\ 1 & 0 & 0 & 0 \\ \alpha^ {3} + 1 & 1 & 0 & 0 \\ 0 & 0 & 1 & 0 \end{array} \right] \text {and} M _ {4} = M _ {1}.\tag{1}
$$

The multiplications between matrices and vectors are performed over $\mathbb { F } _ { 2 ^ { 4 } }$ defined by the primitive polynomial $x ^ { 4 } + x + 1$ and α is a primitive element which is a root of $x ^ { 4 } + x + 1$ 

Cell Permutation ShiftRow. ShiftRow rotates row i of the array state i cell positions to the right for $i = { 0 , 1 , 2 , 3 }$ . We have, 

$$
\left[ \begin{array}{c c c c} s _ {0} & s _ {4} & s _ {8} & s _ {1 2} \\ s _ {1} & s _ {5} & s _ {9} & s _ {1 3} \\ s _ {2} & s _ {6} & s _ {1 0} & s _ {1 4} \\ s _ {3} & s _ {7} & s _ {1 1} & s _ {1 5} \end{array} \right] \leftarrow \left[ \begin{array}{c c c c} s _ {0} & s _ {4} & s _ {8} & s _ {1 2} \\ s _ {1 3} & s _ {1} & s _ {5} & s _ {9} \\ s _ {1 0} & s _ {1 4} & s _ {2} & s _ {6} \\ s _ {7} & s _ {1 1} & s _ {1 5} & s _ {3} \end{array} \right].
$$

i.e. $s _ { i } \gets 1 3 \cdot s _ { i }$ (mod 16) for $i = 0 , 1 , \ldots , 1 5$ 

Note that in the ShiftRow operation of AES [21] and LED [24], the row i of the array state is rotated i cell positions to the left, for $i = { 0 , 1 , 2 , 3 }$ 

AddRoundKey. Given round key $R K _ { i }$ for $1 \leq i \leq 1 0$ , the i-th 64-bit round key $R K _ { i }$ is XORed to the state $S .$ 

Data Processing The data processing part of FUTURE for encryption consisting of 10 rounds. The encryption function F takes a 64-bit data $\dot { X ^ { \epsilon } } \in \left\{ 0 , 1 \right\} ^ { 6 4 } ,$ whitening keys $W K \in \{ 0 , 1 \} ^ { \bar { 6 } \bar { 4 } }$ and 10 round keys $R K _ { i } \in \left\{ 0 , 1 \right\} ^ { 6 4 } ( 1 \leq i \leq 1 0 )$ as the inputs and outputs a 64-bit data $Y \in \{ 0 , 1 \} ^ { 6 4 }$ . F is defined as follows: 

$$
F = \left\{ \begin{array}{l} \{0, 1 \} ^ {6 4} \times \{0, 1 \} ^ {6 4} \times \left\{\{0, 1 \} ^ {6 4} \right\} ^ {1 0} \to \{0, 1 \} ^ {6 4} \\ (X, W K, R K _ {1}, R K _ {2}, \ldots , R K _ {1 0}) \to Y. \end{array} \right.
$$

Input: X and WK, $RK_{1}$ , $RK_{2}$ , $\ldots$ , $RK_{10}$ Initialization: $S \leftarrow \text{KeyAdd}(X, WK)$ ;

for $i \leftarrow 1$ to 9 do $S \leftarrow \text{SubCell}(S)$ ; $S \leftarrow \text{MixColumn}(S)$ ; $S \leftarrow \text{ShiftRows}(S)$ ; $S \leftarrow \text{AddRoundKey}(S, RK_{i})$ ;

end $S \leftarrow \text{SubCell}(S)$ ; $S \leftarrow \text{ShiftRows}(S)$ ; $Y \leftarrow \text{AddRoundKey}(S, RK_{10})$ ;

Output: Y 


Algorithm 1: Encryption Function of FUTURE


The Round Key Evolution and round constants. FUTURE uses a 128- bit secret key $K = k _ { 0 } k _ { 1 } \ldots k _ { 1 2 7 }$ . It splits K in two equal parts $K _ { 0 }$ and $K _ { 1 }$ for the round key and whitening key generation i.e. $K = K _ { 0 } | | K _ { 1 }$ , where $K _ { 0 } =$ $k _ { 0 } k _ { 1 } \ldots k _ { 6 3 }$ and $K _ { 1 } = k _ { 6 4 } k _ { 6 5 } \ldots k _ { 1 2 7 }$ are two 64-bit keys. It uses $K _ { 0 }$ as whitening key and the round key $R K _ { i } \ ( 1 \leq i \leq 1 0 )$ ) generation is as follows (see Figure 2): 

$$
R K _ {i} = \left\{ \begin{array}{l l} K _ {0} \leftarrow K _ {0} \ll (5 \cdot \frac {i}{2}) & \text {if 2\mid i} \\ K _ {1} \leftarrow K _ {1} \ll (5 \cdot \lfloor \frac {i}{2} \rfloor) & \text {if 2\nmid i} \end{array} \right.
$$

where $K _ { i } \ \ll \ j$ means the 64-bit word obtained by a j-bit left rotation (left cyclic shift) of $K _ { i }$ 

For FUTURE a single bit $^ { 6 6 } 1 ^ { \mathfrak { s } }$ is XORed into each 4-bit cell (in diferent positions) of every round except the 5th and 10th round. We define the round constants below: 

<table><tr><td>Rounds (N)</td><td>Round constant</td></tr><tr><td>1, 6</td><td>0x1248248148128124</td></tr><tr><td>2, 7</td><td>0x2481481281241248</td></tr><tr><td>3, 8</td><td>0x4812812412482481</td></tr><tr><td>4, 9</td><td>0x8124124824814812</td></tr><tr><td>5, 10</td><td>0x0000000000000000</td></tr></table>


Table 2. The round constants for the N-th round of FUTURE


More specifically, we are adding a NOT gate in each cell except 5th and 10th round. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-16/2504093b-aa4d-4726-b49a-8e7453d44b3b/7a285ed0b36dad4f387f4b671b0149d46b3e3238bcf6cfe364dd433180ec8b33.jpg)



Fig. 2. Round Key Generation


In the following section we justify the decisions we took during the design of FUTURE. 

## 4 Design Decision

The design choice of round function for FUTURE has been inspired by the existing block ciphers, however all the components of FUTURE are new. Sometimes it is preferred to use an SPN-based block cipher over a Feistel-based one, as Feistel-based block ciphers operate on just half of the state, which results in more rounds for encryption. So we have chosen FUTURE to be SPN-based. 

Also an unrolled implementation ofers the best performance due to the computation of full encryption within one clock cycle. It has the disadvantage of extending the critical path since the encryption or decryption operation is implemented as a combinatorial circuit in its entirety. However, in this implementation, there is no requirement for registers to hold the intermediate states. This means a low implementation cost with a small delay for the block ciphers with a small number of rounds. Since FUTURE needs only 10 rounds for the full encryption we have considered the unrolled implementation for it. 

## 4.1 SubCell

As the only nonlinear operation in the FUTURE, Sbox plays a significant role against various attacks. To increase the cipher’s resistance to linear cryptanalysis [30] and diferential cryptanalysis [9], any n-bit Sbox should have small magnitude entries in the linear approximation table LAT and diference distribution table DDT respectively, not counting the first entry in the first row. In other words, the maximal absolute bias of a linear approximation and the maximal probability of a diferential of an Sbox should be low. One other criteria is the absence of fixed points for increasing resistance against statistical attacks. Also, the cost of the Sbox, i.e., its area and critical path, is a significant portion of the entire cost. As a result, selecting an Sbox that optimizes such expenses is important for the design of a lightweight block cipher. 

For the SubCell operation, we use a 4-bit Sbox that is extremely eficient in terms of hardware and also meets the following criteria: 

1. Nonlinearity of the Sbox is 4 (which is optimal). 

2. The maximal probability of a diferential is $2 ^ { - 2 }$ and there are exactly 24 diferentials with probability $2 ^ { - 2 }$ 

3. The maximal absolute bias of a linear approximation is $2 ^ { - 2 }$ and there are exactly 36 linear approximations with absolute bias $2 ^ { - 2 }$ 

4. There is no fixed point. 

FUTURE Sbox S is a composition of four Sboxes $S _ { 1 } , S _ { 2 } , S _ { 3 }$ and $S _ { 4 }$ (See Table 1). The algebraic normal form of the coordinate Boolean functions of S is given by 

$$
\begin{array}{l} l _ {3} (x) = x _ {0} x _ {1} x _ {3} \oplus x _ {0} x _ {2} \oplus x _ {3} \\ l _ {2} (x) = x _ {1} x _ {3} \oplus x _ {2} \\ l _ {1} (x) = x _ {0} x _ {2} x _ {3} \oplus x _ {0} x _ {2} \oplus x _ {0} \oplus x _ {1} x _ {2} \oplus x _ {2} \\ l _ {0} (x) = x _ {0} x _ {1} x _ {3} \oplus x _ {0} x _ {2} \oplus x _ {0} x _ {3} \oplus x _ {1} \oplus 1. \end{array}
$$

Thus we can see that the maximal and minimal algebraic degree of $S$ are 3 and 2 respectively. 

To find lightweight 4-bit Sboxes, we chose to explore circuits systematically from the bottom-up approach, starting with the identity function’s circuit (or by bit wiring of the circuit) and adding gates sequentially. We have decided to choose only NAND, XOR, and XNOR gates as some popular block ciphers like SKINNY [7] and Piccolo [39] use lightweight 4-bit Sboxes that can be implemented by a minimum number of these logic gates. First, we have searched for the circuits representing a 4-bit Sbox that can be implemented by (i) one XOR/XNOR gate or by (ii) one NAND gate followed by one XOR/XNOR gate. As a result, we have the two sets of 4-bit Sboxes, $T _ { 1 }$ and $T _ { 2 } ^ { 5 }$ , where $T _ { 1 }$ contains the Sboxes implemented by one XOR/XNOR gate and $T _ { 2 }$ contains the Sboxes implemented by one NAND and one XOR/XNOR gate. Next, we search for the Sboxes with low hardware cost and good cryptographic properties by composition of 2, 3 or 4 diferent Sboxes from the set $T _ { 1 } \cup T _ { 2 }$ . We obtain the FUTURE Sbox which is a composition of 4 Sboxes with 4 NAND, 3 XNOR and 1 XOR gates with is the lowest hardware cost for our search of 4-bit Sboxes with the optimal nonlinearity of 4. 

During the search of an Sbox for FUTURE with this composition method, we only concentrate on the nonlinearity of the resulting Sbox. The nonlinearity of the Sboxes $S _ { 1 } , S _ { 2 } , S _ { 3 }$ and $S _ { 4 }$ are zero, whereas the resulting Sbox S has $^ { 4 , }$ which is the maximum value for a balanced 4-bit Sbox. The main concern for choosing such a composition method was to reduce implementation cost for the Sbox S. The hardware cost for $S _ { 1 } , S _ { 2 } , S _ { 3 }$ and $S _ { 4 }$ are very low. More specifically, they can be implemented with 4 NAND, 3 XNOR, and 1 XOR gates only (see Figure: 4,5,6 and $7 )$ , resulting in a low hardware cost (12 GE in UMC 180nm 1.8 V [1]) for the Sbox S. 

With this method, the implementation cost of an Sbox with the standard Sbox criteria (like balancedness, maximum nonlinearity, small value of $\delta _ { S }$ and $L _ { S } { \mathrm { ~ e t c . ) } }$ may be reduced significantly. We believe that this is the first time to use this composition type Sbox with maximum nonlinearity and some useful cryptographic properties. 

Also, it is worth mentioning that the 4-bit Sboxes used in SKINNY and Piccolo have the same nonlinearity and hardware cost as the FUTURE Sbox. But FUTURE Sbox is the new one and it is constructed by the composition of four lightweight Sboxes with zero nonlinearity. Also, it is not always trivial to get an Sbox with good cryptographic properties by the composition of four such lightweight Sboxes. We decided to use the newly constructed Sbox. 

## 4.2 MixColumn

Almost MDS matrix (or binary matrix with slightly lower branch number) has eficient implementation features. But its difusion speed is slower and the minimum number of active Sboxes in each round is lower than the ciphers that employ the MDS matrix as part of MixColumn. The difusion speed is measured by the number of rounds taken to achieve full difusion, i.e. all output cells are afected by all input cells. FUTURE requires only 2 rounds for the full difusion (See Figure 3). 

For hardware eficiency, most of the lightweight block ciphers in the literature use almost MDS matrix or binary matrix with a much lower branch number, which results in more rounds for achieving security against various attacks, including diferential, impossible diferential, and linear. Whereas FUTURE needs only 10 rounds for resisting such attacks by using an MDS matrix. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-16/2504093b-aa4d-4726-b49a-8e7453d44b3b/059a79fa1d082421bb16955b5b6898114970510b40cc3084e7c42c4d289f6623.jpg)



Fig. 3. Full difusion of FUTURE.


MDS matrices are not sparse. But they can be constructed from sparse matrices by recursive method i.e. using a sparse matrix several times resulting in a very low hardware cost. 

The MDS matrix in FUTURE is a composition of 4 diferent lightweight sparse matrices $M _ { 1 } , M _ { 2 } , M _ { 3 }$ and $M _ { 4 }$ (see Equation 1 of Section 3.1). These matrices are of the form 

$$
\left[ \begin{array}{c c c c} 0 & 0 & m _ {1} & m _ {2} \\ m _ {3} & 0 & 0 & 0 \\ m _ {4} & m _ {5} & 0 & 0 \\ 0 & 0 & m _ {6} & 0 \end{array} \right],
$$

where $m _ { i } \in \mathbb { F } _ { 2 ^ { 4 } }$ for $i = 1 , 2 , \dots , 6$ 

The idea of constructing MDS matrices in such a fashion was first introduced in [35] and we are the first to take advantage of this method in the design of FUTURE. More specifically, we have fixed $m _ { 1 } = m _ { 3 } = m _ { 6 } = 1$ and perform an exhaustive search $\bar { ( 5 ^ { 1 2 } \approx 2 ^ { 2 8 } }$ choices) over the set $\left\{ 1 , \alpha , \alpha ^ { 2 } , \alpha ^ { - 1 } , \alpha ^ { - 2 } \right\}$ to obtain $M = M _ { 1 } M _ { 2 } M _ { 3 } M _ { 4 }$ as an MDS matrix. 

The implementation cost for the MDS matrix M is minimized due to the low implementation cost of $M _ { 1 } , M _ { 2 } , M _ { 3 }$ and $M _ { 4 }$ . Note that to construct an MDS matrix in this method, the implementation cost is calculated by the sum of the implementation costs of $M _ { 1 } , M _ { 2 } , M _ { 3 }$ , and $M _ { 4 }$ 

We will now demonstrate how selecting specific elements from a finite field constructed by a specific irreducible polynomial improves multiplication eficiency. 

The Primitive Polynomial $\pmb { x } ^ { 4 } + \pmb { x } + \pmb { 1 }$ . The multiplications between the matrices $M _ { 1 } , \ M _ { 2 } , \ M _ { 3 }$ and $M _ { 4 }$ and vectors are performed over the field $\mathbb { F } _ { 2 ^ { 4 } }$ constructed by the primitive polynomial $x ^ { 4 } + x + 1$ . The entries of these matrices are from the set $\left\{ 0 , 1 , \alpha , \alpha ^ { 3 } + 1 = \alpha ^ { - 1 } \right\}$ , where α is a primitive element of $\mathbb { F } _ { 2 ^ { 4 } }$ and is a root of $x ^ { 4 } + x + 1$ i.e. $\alpha ^ { 4 } + \alpha + 1 = 0$ 

Any element b in $\mathbb { F } _ { 2 ^ { 4 } }$ can be written as $b = \ b _ { 0 } + b _ { 1 } \cdot \alpha + b _ { 2 } \cdot \alpha ^ { 2 } + b _ { 3 } \cdot \alpha ^ { 3 }$ Then by the multiplication of b by $\alpha ^ { 3 } + 1$ we have 

$$
(b _ {0} + b _ {1} \cdot \alpha + b _ {2} \cdot \alpha^ {2} + b _ {3} \cdot \alpha^ {3}) \cdot (\alpha^ {3} + 1) = (b _ {0} + b _ {1}) + b _ {2} \cdot \alpha + b _ {3} \cdot \alpha^ {2} + b _ {0} \cdot \alpha^ {3}.
$$

Thus in vector form the above product looks like $( b _ { 0 } \oplus b _ { 1 } , \ b _ { 2 } , \ b _ { 3 } , \ b _ { 0 } )$ , in which there is 1 XOR. Therefore the XOR count of $\alpha ^ { 3 } + 1 \mathrm { i . e . }$ the XORs required to implement the multiplication of $\alpha ^ { 3 } + 1$ with an arbitrary element $b \in \mathbb { F } _ { 2 ^ { 4 } }$ is 1. Similarly we have $b \cdot \alpha = \ ( b _ { 3 } , \ b _ { 0 } \oplus b _ { 3 } , \ b _ { 1 } , \ b _ { 2 } )$ . Hence the XOR count of α is 1. Also, the XOR count of 1 is 0 and there is no other nonzero element in the field with an XOR count of $\leq 1$ 

Thus for the suitable choice of the constructing polynomial and entries of the matrices, the implementation cost of the MDS matrix M is reduced significantly. More specifically, FUTURE requires 35 XORs for the implementation of the MDS matrix (See Section 6.2). 

The following table provides a comparison of the cost of the FUTURE MDS matrix with the matrices <sup>6</sup> used in the linear layer of some popular block ciphers. 

<table><tr><td>Block Cipher</td><td>Linear Layer</td><td>Cost</td></tr><tr><td>AES</td><td>MDS matrix</td><td>108 XORs</td></tr><tr><td>LED</td><td>Recursive MDS matrix</td><td>14 XORs</td></tr><tr><td>FUTURE</td><td>MDS matrix</td><td>35 XORs</td></tr><tr><td>Piccolo</td><td>MDS matrix</td><td>52 XORs</td></tr><tr><td>PRINCE</td><td><eq>(M^{(0)}, M^{(1)})</eq> Almost MDS matrix</td><td>24 XORs</td></tr><tr><td>MIDORI</td><td>Almost MDS matrix</td><td>24 XORs</td></tr><tr><td>SKINNY</td><td>Binary matrix with branch number 2</td><td>12 XORs</td></tr><tr><td>CRAFT</td><td>Binary matrix with branch number 2</td><td>12 XORs</td></tr><tr><td>PRESENT</td><td>Bit permutation</td><td>0</td></tr><tr><td>GIFT</td><td>Bit permutation</td><td>0</td></tr></table>


Table 3. Comparison of cost of the Linear layers.


From Table 3, we can see that PRINCE and MIDORI use an Almost MDS matrix with a low implementational cost of 24 XORs. But for achieving security against various attacks they need more rounds than FUTURE. The linear layers in PRESENT and GIFT are a bit permutation of the state. As a result, the linear layer is created with simple wire shufling and requires no hardware. But for resisting some fundamental attacks like linear cryptanalysis, diferential cryptanalysis etc., they need a large number of rounds than MIDORI and PRINCE. For the case of SKINNY and CRAFT, the binary matrix is of branch number 2 and needs only 12 XORs for implementation. For this, they attain full difusion after 6th and 7th rounds respectively, which is 2 for FUTURE. Also, the cost of implementing the MDS matrix of LED is low. However, the companion matrix in LED needs to be applied 4 times in the serialized implementation of the diffusion layer to get the MDS matrix, i.e., if we implement the MDS matrix in a single clock cycle, its cost will be $4 \times 1 4 = 5 6 ~ \mathrm { X O R s }$ . The FUTURE MDS matrix M is implemented in a single clock cycle with 35 XOR gates. Since FUTURE is implemented in a fully unrolled fashion, M is preferred over the others in terms of XOR gates and security parameters. 

## 4.3 Round Key

For the key scheduling, we are mainly concerned about reducing hardware costs. Note that the key scheduling function in FUTURE is implemented as a bit permutation of the master key. It is, therefore, possible to create this module through simple wire shufling and it takes up no hardware cost. 

## 5 Security Analysis

The security of FUTURE against various cryptanalysis techniques is discussed in this section. 

## 5.1 Diferential and Linear Cryptanalysis

The most frequent and fundamental security analysis of a block cipher is to determine a cipher’s resistance to diferential and linear cryptanalysis. We computed the lower limits on the minimum number of active Sboxes involved in a diferential or linear characteristic to measure the resistance against diferential and linear attacks. 

Mixed Integer Linear Programming (MILP) is used in this study to derive lower limits for the minimum number of active Sboxes in both Diferential and Linear Cryptanalysis for various numbers of rounds. The outcomes <sup>7</sup> are outlined in Table 4. Also, the MILP solution gives us the actual diferential or linear characteristics, which permits us to find out the actual diferential probability and correlation potential from the DDT (Table 9) and LAT (Table 10) of FUTURE Sbox respectively. 

Diferential cryptanalysis. If $2 ^ { - \delta }$ be the maximum probability of the differential propagation in a single Sbox and $N _ { s }$ be the number of active Sboxes in a diferential characteristic, then attack with the diferential characteristic of a block cipher becomes infeasible if $N _ { s }$ satisfies the following condition [36, Section 4.2.12]: 

<table><tr><td>Rounds (N)</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td></tr><tr><td>Differential cryptanalysis</td><td>1</td><td>5</td><td>9</td><td>25</td><td>26</td></tr><tr><td>Linear cryptanalysis</td><td>1</td><td>5</td><td>9</td><td>25</td><td>26</td></tr></table>


Table 4. The minimum number of active Sbox for N rounds of FUTURE


$$
2 ^ {\delta \cdot N _ {s}} > 2 ^ {b} \implies \delta \cdot N _ {s} > b,
$$

where b is the bit-length of the block size of the block cipher. For FUTURE, $b = 6 4$ and $\delta = 2$ and hence we must have $N _ { s } > 3 2$ . This is obtained by at most 7 rounds<sup>8</sup> for FUTURE. 

However for the 4-round FUTURE, we have searched 50 diferent single characteristics with the minimum number of active Sboxes (which is 25) with no Sbox activity pattern. Here we have observed that among these 50 characteristics the highest probability is $2 ^ { - 6 2 }$ . Next we have fixed the input and output diferences of the characteristic with highest probability and search for diferent single characteristics with the same Sbox activity pattern. Here we have found that only 2 characteristics are possible and the highest probability is also $2 ^ { - 6 2 }$ . Also, from Table 9, we can observe that there are only 24 diferentials with probability $2 ^ { - 2 }$ and whereas there are 72 diferentials with probability $2 ^ { - 3 }$ . Hence we expect that the probability of any possible diferential characteristic will be lower than $2 ^ { - 6 3 }$ when we have 5 rounds. Therefore, we believe that full rounds of FUTURE are strong enough to resist diferential cryptanalysis. 

Linear cryptanalysis. Given a linear characteristic with a bias $\epsilon , \ 4 \epsilon ^ { 2 }$ is defined as the correlation potential. For an adversary to perform linear cryptanalysis on an n-bit block cipher, the correlation potential must be more than $2 ^ { - n }$ 

Similar to the diferential, for the 4th round of FUTURE, we have searched 50 diferent single linear characteristics with the minimum number of active Sboxes with no Sbox activity pattern. Among which, the highest correlation potential is $2 ^ { - 7 4 }$ . Next, with the same input and output masking of the highest correlation potential, we search for 10 more diferent single characteristics which follow the same Sbox activity pattern. We observe that it has a linear hull efect (average correlation potential) of $2 ^ { - 7 3 . 6 6 }$ . Also, from Table 10, we can observe that there are exactly 36 linear approximations with absolute bias $2 ^ { - 2 }$ and whereas there are 96 linear approximations with absolute bias $2 ^ { - 3 }$ . So we expect that for 5- round FUTURE, the correlation potential will be lower than $2 ^ { - 6 4 }$ . Hence, we believe that 10-round FUTURE is suficient to resist linear cryptanalysis. 

## 5.2 Impossible Diferential Attacks

A diferential $( \varDelta x , \varDelta y )$ is supposed to be an impossible diferential on an encryption function F if, for all plaintexts x, $F ( x ) + F ( x + \varDelta x ) \neq \varDelta y .$ . Such a diference over a reduced round version of the cipher can be used for a key-recovery attack on the cipher in some more rounds and this is done by eliminating all the keys that produce intermediate state values with diferences ∆x and $\varDelta y$ i.e. intermediate state values that match the impossible diferential. Note that for the resistance of FUTURE against impossible diferential attack, we have used the similar approach as in GIFT [4]. We looked for impossible diferentials in the reduced-round versions of FUTURE using the Mixed-Integer Linear Programming method [19,37]. We thoroughly test input and output diferences that meet the following conditions. 

1. The input diference activates just one of the first 4 Sboxes. 

2. The output diference activates only one of the 16 Sboxes. 

There are $4 \times 1 5 = 6 0$ such input diferences in the first case and for the second case, there are $1 6 \times 1 5 = 2 4 0$ such output diferences. We thus examined the 14, 400 set of pairs of input and output diferences. 

Our search results show that for 4-round FUTURE, there are only 267 impossible diferentials out of the 14, 400 choices. We then extend this search procedure to $5$ rounds and found that there does not exist any impossible diferential from the 14, 400 pairs. So full rounds of FUTURE are strong enough to resist the impossible diferential attack. 

## 5.3 Boomerang Attack

The boomerang attack [44] is a type of diferential attack in which the attacker does not attempt to cover the entire block cipher with a single diferential characteristic with high probability. Instead, the attacker first divides the cipher into two sub-ciphers, then finds a boomerang quartet with high probability. The probability of constructing a boomerang quartet is denoted as $\hat { p } ^ { 2 } \hat { q } ^ { 2 }$ , where 

$$
\hat {p} = \sqrt {\sum_ {\beta} \mathrm{Pr} ^ {2} [ \alpha \rightarrow \beta ]},
$$

and α and $\beta$ are input and output diferences for the first sub-cipher and $\hat { q }$ for the second sub-cipher. This attack is efective when an n-bit cipher satisfies $\hat { p } ^ { 2 } \hat { q } ^ { 2 } \leq 2 ^ { - n }$ 

The value of $\hat { p } ^ { 2 }$ is bounded by the maximum diferential characteristic probability, i.e., $\hat { p } ^ { 2 } \leq \operatorname* { m a x } _ { \alpha } \operatorname* { P r } [ \alpha  \beta ]$ and $\hat { q } ^ { 2 }$ as well. Let $p , \ q$ be the maximum dif-β ferential trail probability for the first and the second sub-ciphers. Then, p, q are bounded by $2 ^ { - 2 \cdot N _ { s } }$ , where $N _ { s }$ is the minimum number of active Sboxes in each sub-cipher. From Table $^ { 4 , }$ we can see that any combination of two sub-ciphers for FUTURE consisting of 8 rounds has at least 32 active Sboxes in total. Hence, we conclude that the full round of FUTURE is secure against boomerang attacks. 

## 5.4 Integral Attack

We first search for integral distinguishers for the round reduced versions of FU-TURE by using the (bit-based) division property [43] and using the Mixed-Integer Linear Programming approach described in [41,45]. We first evaluate the propagation of the division property for the Sbox. The algebraic normal form of FUTURE Sbox is given by 

$y_{3} = x_{0}x_{1}x_{3}\oplus x_{0}x_{2}\oplus x_{3}$ $y_{2} = x_{1}x_{3}\oplus x_{2}$ $y_{1} = x_{0}x_{2}x_{3}\oplus x_{0}x_{2}\oplus x_{0}\oplus x_{1}x_{2}\oplus x_{2}$ $y_0 = x_0x_1x_3\oplus x_0x_2\oplus x_0x_3\oplus x_1\oplus 1.$ 

and the propagation of the division property is summarized as Table 5. 

<table><tr><td colspan="17">v</td></tr><tr><td>u</td><td>0</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td><td>7</td><td>8</td><td>9</td><td>a</td><td>b</td><td>c</td><td>d</td><td>e</td><td>f</td></tr><tr><td>0</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td></tr><tr><td>1</td><td></td><td>×</td><td>×</td><td>×</td><td></td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td></tr><tr><td>2</td><td></td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td></tr><tr><td>3</td><td></td><td>×</td><td></td><td>×</td><td></td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td></tr><tr><td>4</td><td></td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td></tr><tr><td>5</td><td></td><td>×</td><td>×</td><td>×</td><td></td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td></tr><tr><td>6</td><td></td><td></td><td>×</td><td>×</td><td></td><td>×</td><td>×</td><td>×</td><td></td><td>×</td><td>×</td><td>×</td><td></td><td>×</td><td>×</td><td>×</td></tr><tr><td>7</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td>×</td><td></td><td>×</td><td>×</td><td>×</td><td></td><td>×</td><td>×</td><td>×</td></tr><tr><td>8</td><td></td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td></tr><tr><td>9</td><td></td><td>×</td><td>×</td><td>×</td><td></td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td></tr><tr><td>a</td><td></td><td>×</td><td></td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td></tr><tr><td>b</td><td></td><td>×</td><td></td><td>×</td><td></td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td></tr><tr><td>c</td><td></td><td></td><td>×</td><td>×</td><td></td><td>×</td><td>×</td><td>×</td><td></td><td></td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td><td>×</td></tr><tr><td>d</td><td></td><td></td><td>×</td><td>×</td><td></td><td>×</td><td>×</td><td>×</td><td></td><td></td><td>×</td><td>×</td><td></td><td>×</td><td>×</td><td>×</td></tr><tr><td>e</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td>×</td><td>×</td><td></td><td>×</td><td>×</td><td>×</td></tr><tr><td>f</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td>×</td></tr></table>


Table 5. The possible propagation of the division property for FUTURE Sbox


Here, let u and v be the input and output division property, respectively. The propagation from u to v labeled × is possible. Otherwise, the propagation is impossible. 

Taking into account the efect of MixColumn, we evaluated the propagation of the division property on the reduced-round FUTURE. To search for the longest integral distinguisher, we choose only one bit in plaintext as constant and the others are active. For example, in the 6th round we have a distinguisher $A C A ^ { 6 2 }  B ^ { 6 4 }$ . But we could not find any distinguisher for the 7th round by MILP model due to its long running time. So we can not conclude whether there is an integral distinguisher in the 7th round or not. We also checked that there is no distinguisher from the 8th round <sup>9</sup>. So we are expecting that full rounds of FUTURE is secure against integral attack. 

<sup>9</sup> For finding an r round division trail $( a _ { 0 } ^ { 0 } , a _ { 1 } ^ { 0 } , \ldots , a _ { 6 3 } ^ { 0 } ) \to \ldots \to ( a _ { 0 } ^ { r } , a _ { 1 } ^ { r } , \ldots , a _ { 6 3 } ^ { r } )$ by the MILP technique, we fixed the output $( a _ { 0 } ^ { r } , a _ { 1 } ^ { r } , \ldots , a _ { 6 3 } ^ { r } )$ of the rth round by the unit vectors (64 cases) and check whether the MILP model is feasible or not. 

## 5.5 Invariant Subspace Attacks

The invariant subspace attack [26,27] exploits a subspace A and constants $u ,$ v such that $F ( u \oplus A ) = v \oplus A$ , where F is a round transformation of a block cipher. For the round key $r _ { k } \in A \oplus u \oplus v , F \oplus r _ { k }$ maps the subspace u ⊕ A onto itself, because $F ( u \oplus A ) \oplus r _ { k } = v \oplus A \oplus r _ { k } = u \oplus A$ . However, we can avoid this invariant subspace by using appropriate round constants. 

By Section 3.3 of [28], if RC be the constants on a single cell over all rounds, then the designer can choose RC such that there is no 2-dimensional subspace V of $\mathbb { F } _ { 2 ^ { 4 } }$ satisfying $R C \subseteq V$ for the resistance of invariant subspace attack on AES-like ciphers with MDS MixColumn layer. 

Recall that FUTURE is an AES-like ciphers with MDS MixColumn layer which uses round constants 0, 1, 2, 4, 8 in each output of a cell. Also, there is no 2-dimensional subspace V such $\{ 0 , 1 , 2 , 4 , 8 \} \subseteq V .$ Hence in FUTURE, the invariant subspace attack cannot be found for an arbitrary number of rounds. 

## 5.6 Meet-in-the-Middle Attacks

This section shows the security of FUTURE against the meet-in-the-middle attacks. We have used an approach which is similar to the methods used in the block ciphers MIDORI [3] and SKINNY [7]. The maximum number of rounds that can be attacked can be evaluated by considering the maximum length of three features: partial-matching, initial structure, and splice-and-cut. 

a. Partial-matching: Partial-matching can not work if the number of rounds reaches full difusion in each of the forward and backward directions. In FU-TURE, full difusion is achieved after 2 rounds forwards and backwards. Thus, the number of rounds used for partial-matching is upper bounded by $( 2 - 1 ) + ( 2 - 1 ) + 1 = 3$ 

b. Initial structure: The condition for the initial structure is that key diferential trails in the forward direction and those in the backward direction do not share active Sboxes. For FUTURE, since any key diferential afects all 16 Sboxes after at least 4 rounds in the forward and the backward directions, there is no such diferential which shares active Sbox in more than 4 rounds. Thus, the number of rounds used for the initial structure is upper bounded by $( 4 - 1 ) = 3$ 

c. Splice-and-cut: Splice-and-cut may extend the number of attack rounds up to the smaller number of full difusion rounds minus one, which is $( 2 - 1 ) = 1$ 

Therefore we can conclude that the meet-in-the-middle attack may work up to $3 + 3 + 1 = 7$ rounds. Hence full round FUTURE is suficient to resist meet-in-the-middle attacks. 

## 5.7 Algebraic Attacks

FUTURE Sbox has algebraic degree 3 and from Table 4 we see that for 4-round diferential characteristic, there are at least 25 active Sboxes. So we have $3 \times$ 

$2 5 \times \lfloor { \frac { 1 0 } { 4 } } \rfloor = 1 5 0 > 6 4$ , where 64 is the block size and 10 is the number of rounds in FUTURE. Also, the FUTURE Sbox is described by 21 quadratic equations in the 8 input/output-bit variables over $\mathbb { F } _ { 2 }$ . The key schedule of FUTURE does not need any Sbox. Thus the 10-round cipher is described by $1 0 \times 1 6 \times 2 1 = 3 3 6 0$ quadratic equations in $1 0 \times 1 6 \times 8 = 1 2 8 0$ variables. 

The general problem of solving a system of multivariate quadratic equations is NP-hard. However the systems derived for block ciphers are very sparse since they are composed of a small number of nonlinear systems connected by linear layers. Nevertheless, it is unclear whether this fact can be exploited in a so-called algebraic attack. Some specialized techniques such as XL [16] and XSL [17] have been proposed, though flaws in both techniques have been discovered [13,23]. Instead the practical results on the algebraic cryptanalysis of block ciphers have been obtained by applying the Buchberger and F4 algorithms within Magma. Also, recently there are some practical results [46] on algebraic cryptanalysis by using ElimLin [15,18] and SAT solver techniques [5,40]. 

Now note that the entire system for a fixed-key AES permutation consists of 6400 equations in 2560 variables and whereas in FUTURE these numbers are roughly half of that in AES. Simulations on small-scale variants of the AES showed that except for very small versions, one quickly encounters dificulties with time and memory complexity [14]. So we believe that algebraic attacks do not threaten FUTURE. 

## 6 Hardware Implementations, Performance and Comparison

In this section, we will discuss the hardware implementation cost of FUTURE in both FPGA and ASIC design. 

## 6.1 FPGA Implementation

Nowadays, FPGAs are used more and more for high-performance applications, even in the field of security and cryptographic applications. Since there are a wealth of diferent FPGA vendors available, we decided to implement our designs on various FPGA boards provided by Xilinx. The hardware implementation of FUTURE is written in VHDL and is implemented on both Virtex-6 and Virtex-7. More specifically, the FPGA results are obtained after place-and-route (PAR) on the Xilinx Virtex-6 (xc6vlx240t-2f1156) and Virtex-7 (xc7vx415t-2fg1157) in Xilinx ISE. In Table 6 the implementation results are given. Note that for the comparison of FUTURE with other block ciphers (in fully unrolled implementations), we used the VHDL codes available at https://github.com KULeuven-COSIC/UnrolledBlockCiphers. 

## 6.2 ASIC implementation

In order to estimate the hardware cost for an ASIC platform, we will consider the use of the Synopsys Design Compiler using the UMCL18G212T3 [1] ASIC standard cell library, i.e. UMC 0.18µm. In Table 7 we describe the area requirements and corresponding gate count in this library (for details, check [32]). Also, note that Gate equivalent (GE) is a measure of the area requirements of integrated circuits (IC). It is derived by dividing the area of the IC by the area of a two-input NAND gate with the lowest driving strength. 

<table><tr><td rowspan="2">Cipher</td><td colspan="3">Virtex-6</td><td colspan="3">Virtex-7</td></tr><tr><td>Size (Slices)</td><td>Critical Path (ns)</td><td>Throughput (Gbit/s)</td><td>Size (Slices)</td><td>Critical Path (ns)</td><td>Throughput (Gbit/s)</td></tr><tr><td>KATAN 64/80</td><td>2550</td><td>47.33</td><td>1.35</td><td>2550</td><td>42.11</td><td>1.52</td></tr><tr><td>PRESENT 64/80</td><td>2089</td><td>29.21</td><td>2.19</td><td>2089</td><td>26.27</td><td>2.44</td></tr><tr><td>PRESENT 64/128</td><td>2203</td><td>32.55</td><td>1.97</td><td>2203</td><td>29.03</td><td>2.20</td></tr><tr><td>SIMON 64/128</td><td>2688</td><td>27.31</td><td>2.34</td><td>2688</td><td>25.30</td><td>2.53</td></tr><tr><td>SPECK 64/128</td><td>3594</td><td>50.29</td><td>1.27</td><td>3594</td><td>48.31</td><td>1.32</td></tr><tr><td>PRINCE</td><td>1244</td><td>16.38</td><td>3.91</td><td>1244</td><td>14.79</td><td>4.33</td></tr><tr><td>FUTURE</td><td>1240</td><td>15.94</td><td>4.01</td><td>1241</td><td>14.53</td><td>4.40</td></tr></table>


Table 6. Comparison of size, critical path and throughput on FPGA.


<table><tr><td>Standard cell</td><td>Area in <eq>\mu m^{2}</eq></td><td>GE</td></tr><tr><td>NAND</td><td>9.677</td><td>1</td></tr><tr><td>NOR</td><td>9.677</td><td>1</td></tr><tr><td>AND/OR</td><td>12.902</td><td>1.33</td></tr><tr><td>XOR/XNOR</td><td>25.805</td><td>2.67</td></tr><tr><td>NOT</td><td>6.451</td><td>0.67</td></tr></table>


Table 7. Area requirements and corresponding gate count


But as discussed in [39], some libraries provide special gates that further save the area. Namely, in this library, the 4-input AND-NOR and 4-input OR-NAND gates with two inputs inverted can be used to directly compute an XOR or an XNOR. Since both cells cost 2 GE instead of 2.67 GE required for XOR or XNOR, we can save 0.67 GE per XOR or XNOR gate. Now we will discuss the cost for each module of a single round FUTURE using the above mentioned implementation techniques. 

Cost of FUTURE Sbox Recall that FUTURE Sbox S is a composition of four Sboxes $S _ { 1 } , S _ { 2 } , S _ { 3 }$ and $S _ { 4 }$ i.e. $S ( x ) = S _ { 1 } \circ S _ { 2 } \circ S _ { 3 } \circ S _ { 4 } ( x )$ . The algebraic normal form of these Sboxes are given by 

$$
\begin{array}{r l} & y _ {3} = x _ {3} \\ S _ {4}: & y _ {2} = x _ {1} x _ {3} \oplus x _ {2} \\ & y _ {1} = x _ {1} \\ & y _ {0} = x _ {0} \end{array}
$$

$$
\begin{array}{r l} & y _ {3} = x _ {0} x _ {2} \oplus x _ {3} \\ S _ {3}: & y _ {2} = x _ {2} \\ & y _ {1} = x _ {1} \\ & y _ {0} = x _ {0} \end{array}
$$

$$
\begin{array}{r l} & y _ {3} = x _ {3} \\ S _ {2}: & y _ {2} = x _ {2} \\ & y _ {1} = x _ {0} \\ & y _ {0} = x _ {0} x _ {3} \oplus x _ {1} \oplus 1 \end{array}
$$

$$
\begin{array}{r l} & y _ {3} = x _ {3} \\ S _ {1}: & y _ {2} = x _ {2} \\ & y _ {1} = x _ {0} x _ {2} \oplus x _ {1} \\ & y _ {0} = x _ {0} \end{array}
$$

Here y<sub>3</sub>y<sub>2</sub>y<sub>1</sub>y<sub>0</sub> and x<sub>3</sub>x<sub>2</sub>x<sub>1</sub>x<sub>0</sub> denotes the 4-bit output and input respectively of the Sboxes. They can be implemented as follows: 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-16/2504093b-aa4d-4726-b49a-8e7453d44b3b/ad815535030ec56501875276b925e404984ecb12b56997479520f5bb5da6f088.jpg)



Fig. 4. Sbox $S _ { 4 }$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-16/2504093b-aa4d-4726-b49a-8e7453d44b3b/59998a14515b00509081a44ac294415d59803c9e9acf3fc88eb06e53789bfb49.jpg)



Fig. 5. Sbox $S _ { 3 }$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-16/2504093b-aa4d-4726-b49a-8e7453d44b3b/446c4a90d57ffa283db74d34b81892ad3dd5765a92c01a97ad89a7d9cacc388e.jpg)



Fig. 6. Sbox $S _ { 2 }$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-16/2504093b-aa4d-4726-b49a-8e7453d44b3b/3f03b9ea223b46052a34e594cc0e76768a029d1e63008acc8190187277d0d808.jpg)



Fig. 7. Sbox S<sub>1</sub>


Thus to implement the Sbox of FUTURE, we need 4 NAND, 3 XNOR and 1 XOR gates only. Therefore FUTURE Sbox can be implemented with $( 4 \times 1 +$ $3 \times 2 + 1 \times 2 ) = 1 2$ GE. 

Therefore SubCell operation for a single round FUTURE takes 16×12 = 192 GE for implementation. 

Cost of FUTURE MDS matrix The MDS matrix in FUTURE is a composition of 4 diferent lightweight sparse matrices $M _ { 1 } , M _ { 2 } , M _ { 3 }$ and $M _ { 4 }$ (see Equation 1 of Section 3.1). 

These matrices are of the form 

$$
\left[ \begin{array}{c c c c} 0 & 0 & m _ {1} & m _ {2} \\ m _ {3} & 0 & 0 & 0 \\ m _ {4} & m _ {5} & 0 & 0 \\ 0 & 0 & m _ {6} & 0 \end{array} \right],
$$

where $m _ { i } \in \mathbb { F } _ { 2 ^ { 4 } }$ for $i = 1 , 2 , \dots , 6$ . Therefore for any vector $( s _ { j } , s _ { j + 1 } , s _ { j + 2 } , s _ { j + 3 } )$ $\in \mathbb { F } _ { 2 ^ { 4 } } ^ { 4 }$ we have, 

$$
\left[ \begin{array}{c c c c} 0 & 0 & m _ {1} & m _ {2} \\ m _ {3} & 0 & 0 & 0 \\ m _ {4} & m _ {5} & 0 & 0 \\ 0 & 0 & m _ {6} & 0 \end{array} \right] \cdot \left[ \begin{array}{c} s _ {j} \\ s _ {j + 1} \\ s _ {j + 2} \\ s _ {j + 3} \end{array} \right] = \left[ \begin{array}{c} m _ {1} \cdot s _ {j + 2} \oplus_ {4} m _ {2} \cdot s _ {j + 3} \\ m _ {3} \cdot s _ {j} \\ m _ {4} \cdot s _ {j} \oplus_ {4} m _ {5} \cdot s _ {j + 1} \\ m _ {6} \cdot s _ {j + 2} \end{array} \right],
$$

where $\oplus _ { 4 }$ denotes the XOR between two elements of $\mathbb { F } _ { 2 ^ { 4 } }$ . Since any element of $b \in \mathbb { F } _ { 2 ^ { 4 } }$ , can be viewed as $\boldsymbol { b } = ( b _ { 0 } , b _ { 1 } , b _ { 2 } , b _ { 3 } )$ , where $b _ { i } \in \mathbb { F } _ { 2 }$ for $i = { 1 , 2 , 3 , 4 }$ . So for $b , c \in  { \mathbb { F } } _ { 2 ^ { 4 } }$ , we have 

$$
b \oplus_ {4} c = (b _ {0}, b _ {1}, b _ {2}, b _ {3}) \oplus_ {4} (c _ {0}, c _ {1}, c _ {2}, c _ {3}) = (b _ {0} \oplus c _ {0}, b _ {1} \oplus c _ {1}, b _ {2} \oplus c _ {2}, b _ {3} \oplus c _ {3}).
$$

Therefore for $\oplus _ { 4 } .$ we need 4 bit wise XOR. Also, the multiplication cost for each $m _ { i }$ is required to get the full implementation cost of each matrix. Thus the cost for implementation of the matrices are given below: 

(a) cost for implementing $M _ { 4 } = 8 ~ \mathrm { X O R s }$ 

(b) cost for implementing $M _ { 3 } = 8 + 1 = 9 ~ \mathrm { X O R s }$ (the multiplication cost of $\alpha ^ { 3 } + 1 \ \mathrm { i s } \ 1 \ \mathrm { X O R } )$ 

(c) cost for implementing $M _ { 2 } = 8 + 1 + 1 = 1 0 ~ \mathrm { X O R s }$ (the multiplication cost of $\alpha ^ { 3 } + 1$ and α is 1 XOR). 

(d) cost for implementing $M _ { 1 } = 8 ~ \mathrm { X O R s }$ 

Therefore MDS matrix for FUTURE needs 35 XOR gates. As a result, it can be implemented with $3 5 \times 2 = 7 0$ GE and MixColumn operation for a single round FUTURE takes $4 \times 7 0 = 2 8 0$ GE for implementation. 

Cost of ShiftRow Since ShiftRow is nothing but a permutation of the whole state, this module is constructed by a simple wire shufle and takes no area at all. 

Cost of Key schedule and round constants Since the round keys are obtained by only bit wiring of the master key, it needs no cost in hardware. Whereas, for the full encryption FUTURE uses 128 NOT gates for the round constants. Therefore it takes $1 2 8 \times 0 . 6 7 = 8 5 . 7 6$ GE. Also the 64-bit round key is xored with the entire state in each round (also for whitening key) resulting in a $6 4 \times 2 = 1 2 8 ~ \mathrm { G E }$ cost for this operation in each single round. 

Cost for the full encryption of FUTURE Since FUTURE is implemented in a fully unrolled fashion, it does not need any extra logic and state register. Therefore we have the details cost estimations of FUTURE below: 

(i) cost for one single round= 192 + 280 + 128 = 600 GE. So for 9 full rounds, it will cost 9 × 600 = 5400 GE. 

(ii) cost for the last round= 192 + 128 = 320 GE. 

(iii) cost for round constant= 85.76 GE and key whitening needs 128 GE. 

Thus FUTURE can be implemented with $5 4 0 0 + 3 2 0 + 8 5 . 7 6 + 1 2 8 = 5 9 3 3 . 7 6$ GE only. Of course, these numbers depend on the library used, but we expect that it will take less area than our estimations. 

In Table 8, we list the hardware cost of unrolled implementations for FU-TURE and compare it to other block ciphers taken from the literature. 

<table><tr><td>Ciphers</td><td>Area (GE)</td></tr><tr><td>LED-64-128</td><td>111496</td></tr><tr><td>PRESENT-64-128</td><td>56722</td></tr><tr><td>PICCOLO-64-128</td><td>25668</td></tr><tr><td>SKINNY-64-128</td><td>17454</td></tr><tr><td>MANTIS<eq>_{5}</eq></td><td>8544</td></tr><tr><td>PRINCE</td><td>8512</td></tr><tr><td>FUTURE</td><td>5934</td></tr></table>


Table 8. Comparison of the hardware cost of unrolled implementations for FUTURE and other 64-bit block ciphers with 128 bit key on ASIC platform


The above table contains the cost estimations of FUTURE along with the cost of other ciphers obtained from Table 12 and Table 24 of [7]. It should be pointed out that SKINNY and MANTIS are tweakable block ciphers, whereas the others are not. 

It will be inappropriate to compare the hardware cost of the unrolled version of a rolled block cipher with a large number of rounds because the hardware cost of making the rolled version into the unrolled version will be very high. That’s why we are not comparing the hardware cost of FUTURE with the recent block ciphers like GIFT [4] and CRAFT [8]. 

In Table 6, we compare FUTURE with some block ciphers in the FPGA platform and Table 8 compares its hardware cost with some block ciphers in the ASIC platform. A better approach would be to compare our block cipher with other block ciphers in both FPGA and ASIC implementations. But we are comparing some block ciphers in FPGA and other block ciphers in ASIC because of the unavailability of their hardware codes in the literature. 

## 7 Conclusions

One of the fundamental primitives for cryptographic applications is block ciphers. In this work, we have proposed a new SPN-based lightweight block cipher, FUTURE, that is designed for minimal latency with low hardware implementation cost. For the perfect difusion, it employs an MDS matrix in the round function. Whereas, due to the high cost of MDS matrices, most lightweight block ciphers do not use such matrices in their round function. But FUTURE optimizes the cost of the MDS matrix by taking advantage of a particular type of MDS matrix construction. By judiciously choosing the FUTURE Sbox as a composition of four lightweight Sboxes, we have reduced the implementation cost significantly. Also, FUTURE shows its resistance to fundamental attacks. We believe that FUTURE will be a secure lightweight block cipher. 

## References



1. Virtual Silicon Inc. 0.18 µm VIP Standard Cell Library Tape Out Ready, Part Number: UMCL18G212T3, Process: UMC Logic 0.18 µm Generic II Technology: 0.18µm, July 2004. 





2. Roberto Avanzi. The QARMA Block Cipher Family. Almost MDS Matrices Over Rings With Zero Divisors, Nearly Symmetric Even-Mansour Constructions With Non-Involutory Central Rounds, and Search Heuristics for Low-Latency S-Boxes. IACR Transactions on Symmetric Cryptology, 2017(1):4–44, Mar. 2017. 





3. Subhadeep Banik, Andrey Bogdanov, Takanori Isobe, Kyoji Shibutani, Harunaga Hiwatari, Toru Akishita, and Francesco Regazzoni. Midori: A Block Cipher for Low Energy. In Tetsu Iwata and Jung Hee Cheon, editors, Advances in Cryptology – ASIACRYPT 2015, pages 411–436, Berlin, Heidelberg, 2015. Springer Berlin Heidelberg. 





4. Subhadeep Banik, Sumit Kumar Pandey, Thomas Peyrin, Yu Sasaki, Siang Meng Sim, and Yosuke Todo. GIFT: A Small Present - Towards Reaching the Limit of Lightweight Encryption. In Wieland Fischer and Naofumi Homma, editors, Cryptographic Hardware and Embedded Systems – CHES 2017, pages 321–345. Springer International Publishing, 2017. 





5. Gregory V. Bard, Nicolas T. Courtois, and Chris Jeferson. Eficient Methods for Conversion and Solution of Sparse Systems of Low-Degree Multivariate Polynomials over GF(2) via SAT-Solvers. Cryptology ePrint Archive, Report 2007/024, 2007. https://ia.cr/2007/024. 





6. Ray Beaulieu, Douglas Shors, Jason Smith, Stefan Treatman-Clark, Bryan Weeks, and Louis Wingers. The SIMON and SPECK Lightweight Block Ciphers. In Proceedings of the 52nd Annual Design Automation Conference, DAC ’15, pages 1–6, 2015. 





7. Christof Beierle, Jérémy Jean, Stefan Kölbl, Gregor Leander, Amir Moradi, Thomas Peyrin, Yu Sasaki, Pascal Sasdrich, and Siang Meng Sim. The SKINNY Family of Block Ciphers and Its Low-Latency Variant MANTIS. In Matthew Robshaw and Jonathan Katz, editors, Advances in Cryptology – CRYPTO 2016, pages 123–153, Berlin, Heidelberg, 2016. Springer Berlin Heidelberg. 





8. Christof Beierle, Gregor Leander, Amir Moradi, and Shahram Rasoolzadeh. CRAFT: Lightweight Tweakable Block Cipher with Eficient Protection Against 





DFA Attacks. IACR Transactions on Symmetric Cryptology, 2019(1):5–45, Mar. 2019. 





9. Eli Biham and Adi Shamir. Diferential cryptanalysis of DES-like cryptosystems. Journal of Cryptology, 4:3–72, 1991. https://doi.org/10.1007/BF00630563. 





10. Andrey Bogdanov, Lars R. Knudsen, Gregor Leander, Christof Paar, Axel Poschmann, Matthew J. B. Robshaw, Yannick Seurin, and C. Vikkelsoe. PRESENT: An Ultra-Lightweight Block Cipher. In Pascal Paillier and Ingrid Verbauwhede, editors, Cryptographic Hardware and Embedded Systems - CHES 2007, pages 450–466, Berlin, Heidelberg, 2007. Springer Berlin Heidelberg. 





11. Julia Borghof, Anne Canteaut, Tim Güneysu, Elif Bilge Kavun, Miroslav Knezevic, Lars R. Knudsen, Gregor Leander, Ventzislav Nikov, Christof Paar, Christian Rechberger, Peter Rombouts, Søren S. Thomsen, and Tolga Yalçın. PRINCE – A Low-Latency Block Cipher for Pervasive Computing Applications. In Xiaoyun Wang and Kazue Sako, editors, Advances in Cryptology – ASIACRYPT 2012, pages 208–225, Berlin, Heidelberg, 2012. Springer Berlin Heidelberg. 





12. Claude Carlet. Boolean Functions for Cryptography and Coding Theory. Cambridge University Press, 2021. 





13. Carlos Cid and Gaëtan Leurent. An Analysis of the XSL Algorithm. In Bimal Roy, editor, Advances in Cryptology - ASIACRYPT 2005, pages 333–352, Berlin, Heidelberg, 2005. Springer Berlin Heidelberg. 





14. Carlos Cid, Sean Murphy, and Matthew J. B. Robshaw. Small Scale Variants of the AES. In Henri Gilbert and Helena Handschuh, editors, Fast Software Encryption, pages 145–162, Berlin, Heidelberg, 2005. Springer Berlin Heidelberg. 





15. Nicolas T. Courtois and Gregory V. Bard. Algebraic Cryptanalysis of the Data Encryption Standard. In Steven D. Galbraith, editor, Cryptography and Coding, pages 152–169, Berlin, Heidelberg, 2007. Springer Berlin Heidelberg. 





16. Nicolas T. Courtois, Alexander Klimov, Jacques Patarin, and Adi Shamir. Eficient Algorithms for Solving Overdefined Systems of Multivariate Polynomial Equations. In Bart Preneel, editor, Advances in Cryptology — EUROCRYPT 2000, pages 392– 407, Berlin, Heidelberg, 2000. Springer Berlin Heidelberg. 





17. Nicolas T. Courtois and Josef Pieprzyk. Cryptanalysis of Block Ciphers with Overdefined Systems of Equations. In Yuliang Zheng, editor, Advances in Cryptology — ASIACRYPT 2002, pages 267–287, Berlin, Heidelberg, 2002. Springer Berlin Heidelberg. 





18. Nicolas T. Courtois, Pouyan Sepehrdad, Petr Sušil, and Serge Vaudenay. Elimlin Algorithm Revisited. In Anne Canteaut, editor, Fast Software Encryption, pages 306–325, Berlin, Heidelberg, 2012. Springer Berlin Heidelberg. 





19. Tingting Cui, Shiyao Chen, Keting Jia, Kai Fu, and Meiqin Wang. New automatic search tool for impossible diferentials and zero-correlation linear approximations. Cryptology ePrint Archive, Report 2016/689, 2016. https://ia.cr/2016/689. 





20. Thomas W. Cusick and Pantelimon Stanica. Cryptographic Boolean Functions and Applications (Second Edition). Academic Press, 2017. 





21. Joan Daemen and Vincent Rijmen. The Design of Rijndael: AES - The Advanced Encryption Standard. Information Security and Cryptography. Springer, 2002. 





22. Christophe De Cannière, Orr Dunkelman, and Miroslav Knežević. KATAN and KTANTAN — A Family of Small and Eficient Hardware-Oriented Block Ciphers. In Christophe Clavier and Kris Gaj, editors, Cryptographic Hardware and Embedded Systems - CHES 2009, pages 272–288, Berlin, Heidelberg, 2009. Springer Berlin Heidelberg. 





23. Claus Diem. The XL-Algorithm and a Conjecture from Commutative Algebra. In Pil Joong Lee, editor, Advances in Cryptology - ASIACRYPT 2004, pages 323–337, Berlin, Heidelberg, 2004. Springer Berlin Heidelberg. 





24. Jian Guo, Thomas Peyrin, Axel Poschmann, and Matt Robshaw. The LED Block Cipher. In Bart Preneel and Tsuyoshi Takagi, editors, Cryptographic Hardware and Embedded Systems – CHES 2011, pages 326–341, Berlin, Heidelberg, 2011. Springer Berlin Heidelberg. 





25. Kishan Chand Gupta, Sumit Kumar Pandey, Indranil Ghosh Ray, and Susanta Samanta. Cryptographically significant MDS matrices over finite fields: A brief survey and some generalized results. Advances in Mathematics of Communications, 13(4):779–843, 2019. 





26. Gregor Leander, Mohamed Ahmed Abdelraheem, Hoda AlKhzaimi, and Erik Zenner. A Cryptanalysis of PRINTcipher: The Invariant Subspace Attack. In Phillip Rogaway, editor, Advances in Cryptology – CRYPTO 2011, pages 206–221, Berlin, Heidelberg, 2011. Springer Berlin Heidelberg. 





27. Gregor Leander, Brice Minaud, and Sondre Rønjom. A Generic Approach to Invariant Subspace Attacks: Cryptanalysis of Robin, iSCREAM and Zorro. In Elisabeth Oswald and Marc Fischlin, editors, Advances in Cryptology – EUROCRYPT 2015, pages 254–283, Berlin, Heidelberg, 2015. Springer Berlin Heidelberg. 





28. Yunwen Liu and Vincent Rijmen. New observations on invariant subspace attack. Information Processing Letters, 138:27–30, 2018. 





29. F.J. MacWilliams and N.J.A. Sloane. The Theory of Error Correcting Codes. North-Holland Publishing Co., Amsterdam-New York-Oxford, 1977. 





30. Mitsuru Matsui. Linear Cryptanalysis Method for DES Cipher. In Tor Helleseth, editor, Advances in Cryptology — EUROCRYPT ’93, pages 386–397, Berlin, Heidelberg, 1994. Springer Berlin Heidelberg. 





31. U.S. Department of Commerce, National Institute of Standards, and Technology. Secure Hash Standard - SHS: Federal Information Processing Standards Publication 180-4. CreateSpace Independent Publishing Platform, North Charleston, SC, USA, 2012. http://csrc.nist.gov/publications/fips/fips180-4/fips-180-4.pdf. 





32. Axel Poschmann. Lightweight cryptography - cryptographic engineering for a pervasive world. Cryptology ePrint Archive, Report 2009/516, 2009. https: //ia.cr/2009/516. 





33. R. L. Rivest, A. Shamir, and L. Adleman. A method for obtaining digital signatures and public-key cryptosystems. Communications of the ACM, 21(2):120–126, 1978. 





34. O.S Rothaus. On “bent” functions. Journal of Combinatorial Theory, Series A, 20(3):300–305, 1976. 





35. Mahdi Sajadieh and Mohsen Mousavi. Construction of MDS matrices from generalized feistel structures. Designs, Codes and Cryptography, 89:1433–1452, 2021. 





36. Kazuo Sakiyama, Yu Sasaki, and Yang Li. Security of Block Ciphers: From Algorithm Design to Hardware Implementation. Wiley Publishing, 1st edition, 2015. 





37. Yu Sasaki and Yosuke Todo. New Impossible Diferential Search Tool from Design and Cryptanalysis Aspects. In Jean-Sébastien Coron and Jesper Buus Nielsen, editors, Advances in Cryptology – EUROCRYPT 2017, pages 185–215. Springer International Publishing, 2017. 





38. Jennifer Seberry, Xian-Mo Zhang, and Yuliang Zheng. Relationships Among Nonlinear Criteria (Extended Abstract). In Advances in Cryptology - EUROCRYPT ’94, Workshop on the Theory and Application of Cryptographic Techniques, Perugia, Italy, May 9-12, 1994, Proceedings, pages 376–388, 1994. 





39. Kyoji Shibutani, Takanori Isobe, Harunaga Hiwatari, Atsushi Mitsuda, Toru Akishita, and Taizo Shirai. Piccolo: An Ultra-Lightweight Blockcipher. In Bart Preneel and Tsuyoshi Takagi, editors, Cryptographic Hardware and Embedded Systems – CHES 2011, pages 342–357, Berlin, Heidelberg, 2011. Springer Berlin Heidelberg. 





40. Mate Soos, Karsten Nohl, and Claude Castelluccia. Extending SAT Solvers to Cryptographic Problems. In Oliver Kullmann, editor, Theory and Applications of Satisfiability Testing - SAT 2009, pages 244–257, Berlin, Heidelberg, 2009. Springer Berlin Heidelberg. 





41. Ling Sun, Wei Wang, and Meiqin Q. Wang. MILP-aided bit-based division property for primitives with non-bit-permutation linear layers. IET Information Security, 14(1):12–20, 2020. 





42. Tomoyasu Suzaki, Kazuhiko Minematsu, Sumio Morioka, and Eita Kobayashi. TWINE: A Lightweight Block Cipher for Multiple Platforms. In Lars R. Knudsen and Huapeng Wu, editors, Selected Areas in Cryptography, pages 339–354, Berlin, Heidelberg, 2013. Springer Berlin Heidelberg. 





43. Yosuke Todo and Masakatu Morii. Bit-Based Division Property and Application to Simon Family. In Thomas Peyrin, editor, Fast Software Encryption, pages 357–377, Berlin, Heidelberg, 2016. Springer Berlin Heidelberg. 





44. David Wagner. The boomerang attack. In Lars Knudsen, editor, Fast Software Encryption, pages 156–170, Berlin, Heidelberg, 1999. Springer Berlin Heidelberg. 





45. Zejun Xiang, Wentao Zhang, Zhenzhen Bao, and Dongdai Lin. Applying Milp Method to Searching Integral Distinguishers Based on Division Property for 6 Lightweight Block Ciphers. In Jung Hee Cheon and Tsuyoshi Takagi, editors, Advances in Cryptology – ASIACRYPT 2016, pages 648–678, Berlin, Heidelberg, 2016. Springer Berlin Heidelberg. 





46. Sze Ling Yeo, Duc-Phong Le, and Khoongming Khoo. Improved algebraic attacks on lightweight block ciphers. Journal of Cryptographic Engineering, 11:1–19, 2021. https://doi.org/10.1007/s13389-020-00237-4. 



## A Test Vectors

<table><tr><td>Plaintext</td><td>Key (<eq>K = K_0 || K_1</eq>)</td><td>Ciphertext</td></tr><tr><td>0x00000000000000000</td><td>0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000</td><td>0x298650c13199cdec</td></tr><tr><td>0x000000000000000000</td><td>0x0000000000000000001111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111</td><td>0x4aa41b330751b83d</td></tr><tr><td>0xffffffffffffff</td><td>0x00102030405060708090a0b0c0d0e0f</td><td>0x68e030733fe73b8a</td></tr><tr><td>0xffffffffffffff</td><td>0xffffffffFFFFFFFFFFFFFFFFFFFFFFFF</td><td>0x333ba4b7646e09f2</td></tr><tr><td>0x6162636465666768</td><td>0x000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000</td><td>0xcc5ba5e52038b6df</td></tr><tr><td>0x5353414d414e5441</td><td>0x05192832010913645029387763948871</td><td>0x5ce1b8d8d01a9310</td></tr></table>

## B Diferential Distribution Table of FUTURE Sbox

<table><tr><td colspan="16"><eq>\Delta O</eq></td><td></td></tr><tr><td><eq>\Delta I</eq></td><td>0</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td><td>7</td><td>8</td><td>9</td><td>a</td><td>b</td><td>c</td><td>d</td><td>e</td><td>f</td></tr><tr><td>0</td><td>16</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td></tr><tr><td>1</td><td>0</td><td>0</td><td>4</td><td>4</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>4</td><td>4</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td></tr><tr><td>2</td><td>0</td><td>4</td><td>0</td><td>4</td><td>0</td><td>2</td><td>0</td><td>2</td><td>0</td><td>0</td><td>0</td><td>0</td><td>2</td><td>0</td><td>2</td><td>0</td></tr><tr><td>3</td><td>0</td><td>0</td><td>0</td><td>4</td><td>2</td><td>0</td><td>2</td><td>0</td><td>0</td><td>0</td><td>4</td><td>0</td><td>0</td><td>2</td><td>0</td><td>2</td></tr><tr><td>4</td><td>0</td><td>0</td><td>0</td><td>0</td><td>4</td><td>0</td><td>4</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>4</td><td>0</td><td>4</td></tr><tr><td>5</td><td>0</td><td>0</td><td>0</td><td>0</td><td>2</td><td>2</td><td>2</td><td>2</td><td>0</td><td>0</td><td>0</td><td>0</td><td>2</td><td>2</td><td>2</td><td>2</td></tr><tr><td>6</td><td>0</td><td>4</td><td>0</td><td>4</td><td>0</td><td>2</td><td>0</td><td>2</td><td>0</td><td>0</td><td>0</td><td>0</td><td>2</td><td>0</td><td>2</td><td>0</td></tr><tr><td>7</td><td>0</td><td>0</td><td>4</td><td>0</td><td>0</td><td>2</td><td>0</td><td>2</td><td>0</td><td>4</td><td>0</td><td>0</td><td>2</td><td>0</td><td>2</td><td>0</td></tr><tr><td>8</td><td>0</td><td>0</td><td>0</td><td>0</td><td>2</td><td>0</td><td>2</td><td>0</td><td>4</td><td>2</td><td>0</td><td>2</td><td>4</td><td>0</td><td>0</td><td>0</td></tr><tr><td>9</td><td>0</td><td>2</td><td>2</td><td>0</td><td>0</td><td>2</td><td>2</td><td>0</td><td>0</td><td>0</td><td>2</td><td>2</td><td>0</td><td>0</td><td>2</td><td>2</td></tr><tr><td>a</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>4</td><td>0</td><td>0</td><td>4</td><td>2</td><td>0</td><td>2</td><td>0</td><td>2</td><td>0</td><td>2</td></tr><tr><td>b</td><td>0</td><td>2</td><td>2</td><td>0</td><td>0</td><td>0</td><td>2</td><td>2</td><td>0</td><td>0</td><td>2</td><td>2</td><td>2</td><td>0</td><td>0</td><td>2</td></tr><tr><td>c</td><td>0</td><td>0</td><td>0</td><td>0</td><td>2</td><td>0</td><td>2</td><td>0</td><td>4</td><td>2</td><td>0</td><td>2</td><td>0</td><td>0</td><td>4</td><td>0</td></tr><tr><td>d</td><td>0</td><td>2</td><td>2</td><td>0</td><td>2</td><td>0</td><td>0</td><td>2</td><td>0</td><td>0</td><td>2</td><td>2</td><td>2</td><td>2</td><td>0</td><td>0</td></tr><tr><td>e</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>4</td><td>4</td><td>2</td><td>0</td><td>2</td><td>0</td><td>2</td><td>0</td><td>2</td></tr><tr><td>f</td><td>0</td><td>2</td><td>2</td><td>0</td><td>2</td><td>2</td><td>0</td><td>0</td><td>0</td><td>0</td><td>2</td><td>2</td><td>0</td><td>2</td><td>2</td><td>0</td></tr></table>


Table 9. Diferential Distribution Table (DDT) of FUTURE Sbox


## C Linear approximation table of FUTURE Sbox

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-16/2504093b-aa4d-4726-b49a-8e7453d44b3b/7aa638dd28f3469409586eafb99cfd76e4c7a1018360e8b4814a878254eb512b.jpg)



Table 10. Linear approximation table (LAT) of FUTURE Sbox. Each entry represents $\# \{ x \in \mathbb { F } _ { 2 ^ { 4 } } : x \cdot \alpha \oplus S ( x ) \cdot \beta = 0 \} - 8 .$


## D $\mathbf { T _ { 1 } }$ : 4-bit Sboxes implemented by 1 XOR/XNOR gates

<table><tr><td>Sbox</td><td>ANF</td></tr><tr><td>0123456798badcfe</td><td><eq>y_3 = x_3, \ y_2 = x_2, \ y_1 = x_1, \ y_0 = x_0 \oplus x_3</eq></td></tr><tr><td>0123547689abdcfe</td><td><eq>y_3 = x_3, \ y_2 = x_2, \ y_1 = x_1, \ y_0 = x_0 \oplus x_2</eq></td></tr><tr><td>0132457689bacdfe</td><td><eq>y_3 = x_3, \ y_2 = x_2, \ y_1 = x_1, \ y_0 = x_0 \oplus x_1</eq></td></tr><tr><td>1023546798abdcef</td><td><eq>y_3 = x_3, \ y_2 = x_2, \ y_1 = x_1, \ y_0 = x_0 \oplus x_1 \oplus 1</eq></td></tr><tr><td>1032456798bacdef</td><td><eq>y_3 = x_3, \ y_2 = x_2, \ y_1 = x_1, \ y_0 = x_0 \oplus x_2 \oplus 1</eq></td></tr><tr><td>1032547689abcdef</td><td><eq>y_3 = x_3, \ y_2 = x_2, \ y_1 = x_1, \ y_0 = x_0 \oplus x_3 \oplus 1</eq></td></tr><tr><td>01234567ab89efcd</td><td><eq>y_3 = x_3, \ y_2 = x_2, \ y_1 = x_1 \oplus x_3, \ y_0 = x_0</eq></td></tr><tr><td>0123674589abefcd</td><td><eq>y_3 = x_3, \ y_2 = x_2, \ y_1 = x_1 \oplus x_2, \ y_0 = x_0</eq></td></tr><tr><td>031247568b9acfde</td><td><eq>y_3 = x_3, \ y_2 = x_2, \ y_1 = x_0, \ y_0 = x_0 \oplus x_1</eq></td></tr><tr><td>120356479a8bdecf</td><td><eq>y_3 = x_3, \ y_2 = x_2, \ y_1 = x_0, \ y_0 = x_0 \oplus x_1 \oplus 1</eq></td></tr><tr><td>130246579b8acedf</td><td><eq>y_3 = x_3, \ y_2 = x_2, \ y_1 = x_0, \ y_0 = x_1 \oplus x_2 \oplus 1</eq></td></tr><tr><td>130257468a9bcdf</td><td><eq>y_3 = x_3, \ y_2 = x_2, \ y_1 = x_0, \ y_0 = x_1 \oplus x_3 \oplus 1</eq></td></tr><tr><td>01234567cdef89ab</td><td><eq>y_3 = x_3, \ y_2 = x_2 \oplus x_3, \ y_1 = x_1, \ y_0 = x_0</eq></td></tr><tr><td>0167234589efabcd</td><td><eq>y_3 = x_3, y_2 = x_1, y_1 = x_1 \oplus x_2, y_0 = x_0</eq></td></tr><tr><td>034712568bcf9ade</td><td><eq>y_3 = x_3, y_2 = x_1, y_1 = x_0, y_0 = x_0 \oplus x_2</eq></td></tr><tr><td>125603479ade8bcf</td><td><eq>y_3 = x_3, y_2 = x_1, y_1 = x_0, y_0 = x_0 \oplus x_2 \oplus 1</eq></td></tr><tr><td>134602579bce8adf</td><td><eq>y_3 = x_3, y_2 = x_1, y_1 = x_0, y_0 = x_1 \oplus x_2 \oplus 1</eq></td></tr><tr><td>135702468ace9bdf</td><td><eq>y_3 = x_3, y_2 = x_1, y_1 = x_0, y_0 = x_2 \oplus x_3 \oplus 1</eq></td></tr><tr><td>0123cdef456789ab</td><td><eq>y_3 = x_2, y_2 = x_2 \oplus x_3, y_1 = x_1, y_0 = x_0</eq></td></tr><tr><td>016789ef2345abcd</td><td><eq>y_3 = x_2, y_2 = x_1, y_1 = x_1 \oplus x_3, y_0 = x_0</eq></td></tr><tr><td>03478bcf12569ade</td><td><eq>y_3 = x_2, y_2 = x_1, y_1 = x_0, y_0 = x_0 \oplus x_3</eq></td></tr><tr><td>12569ade03478bcf</td><td><eq>y_3 = x_2, y_2 = x_1, y_1 = x_0, y_0 = x_0 \oplus x_3 \oplus 1</eq></td></tr><tr><td>13469bce02578adf</td><td><eq>y_3 = x_2, y_2 = x_1, y_1 = x_0, y_0 = x_1 \oplus x_3 \oplus 1</eq></td></tr><tr><td>13578ace02469bdf</td><td><eq>y_3 = x_2, y_2 = x_1, y_1 = x_0, y_0 = x_2 \oplus x_3 \oplus 1</eq></td></tr></table>

Table 11: 4-bit Sboxes implemented by 1 XOR/XNOR gates (Here y<sub>3</sub>y<sub>2</sub>y<sub>1</sub>y<sub>0</sub> and $x _ { 3 } x _ { 2 } x _ { 1 } x _ { 0 }$ denotes the 4-bit output and input respectively of the Sboxes). 

## E $\mathbf { T _ { 2 } }$ : 4-bit Sboxes implemented by 1 NAND and 1 XOR/XNOR gates

<table><tr><td>Sbox</td><td>ANF</td></tr><tr><td>0123456789abdcfe</td><td><eq>y_3 = x_3, y_2 = x_2, y_1 = x_1, y_0 = x_0 \oplus x_2x_3</eq><eq>[x_0 \oplus x_2x_3 = \text{XNOR}((x_0, \text{NAND}(x_2, x_3)))]</eq></td></tr><tr><td>0123456789bacdfe</td><td><eq>y_3 = x_3, y_2 = x_2, y_1 = x_1, y_0 = x_0 \oplus x_1x_3</eq></td></tr><tr><td>0123457689abcdfe</td><td><eq>y_3 = x_3, y_2 = x_2, y_1 = x_1, y_0 = x_0 \oplus x_1x_2</eq></td></tr><tr><td>1032546798badcef</td><td><eq>y_3 = x_3, y_2 = x_2, y_1 = x_1, y_0 = x_0 \oplus x_1x_2 \oplus 1</eq></td></tr><tr><td>1032547698abdcef</td><td><eq>y_3 = x_3, y_2 = x_2, y_1 = x_1, y_0 = x_0 \oplus x_1x_3 \oplus 1</eq><eq>[x_0 \oplus x_1x_3 \oplus 1 = \text{XOR}((x_0, \text{NAND}(x_1, x_3)))]</eq></td></tr><tr><td>1032547698bacdef</td><td><eq>y_3 = x_3, y_2 = x_2, y_1 = x_1, y_0 = x_0 \oplus x_2x_3 \oplus 1</eq></td></tr><tr><td>0123456789abefcd</td><td><eq>y_3 = x_3, y_2 = x_2, y_1 = x_1 \oplus x_2x_3, y_0 = x_0</eq></td></tr><tr><td>012345678ba9cfed</td><td><eq>y_3 = x_3, y_2 = x_2, y_1 = x_0x_3 \oplus x_1, y_0 = x_0</eq></td></tr><tr><td>0123476589abcfed</td><td><eq>y_3 = x_3, y_2 = x_2, y_1 = x_0x_2 \oplus x_1, y_0 = x_0</eq></td></tr><tr><td>130256479b8adecf</td><td><eq>y_3 = x_3, y_2 = x_2, y_1 = x_0, y_0 = x_0x_2 \oplus x_1 \oplus 1</eq></td></tr><tr><td>130257469a8bdecf</td><td><eq>y_3 = x_3, y_2 = x_2, y_1 = x_0, y_0 = x_0x_3 \oplus x_1 \oplus 1</eq></td></tr><tr><td>130257469b8acedf</td><td><eq>y_3 = x_3, y_2 = x_2, y_1 = x_0, y_0 = x_1 \oplus x_2x_3 \oplus 1</eq></td></tr><tr><td>0123456789efcdab</td><td><eq>y_3 = x_3, y_2 = x_1x_3 \oplus x_2, y_1 = x_1, y_0 = x_0</eq></td></tr><tr><td>012345678dafc9eb</td><td><eq>y_3 = x_3, y_2 = x_0x_3 \oplus x_2, y_1 = x_1, y_0 = x_0</eq></td></tr><tr><td>0127456389afcdeb</td><td><eq>y_3 = x_3, y_2 = x_0x_1 \oplus x_2, y_1 = x_1, y_0 = x_0</eq></td></tr><tr><td>135602479bde8acf</td><td><eq>y_3 = x_3, y_2 = x_1, y_1 = x_0, y_0 = x_0x_1 \oplus x_2 \oplus 1</eq></td></tr><tr><td>135702469ade8bcf</td><td><eq>y_3 = x_3, y_2 = x_1, y_1 = x_0, y_0 = x_0x_3 \oplus x_2 \oplus 1</eq></td></tr><tr><td>135702469bce8adf</td><td><eq>y_3 = x_3, y_2 = x_1, y_1 = x_0, y_0 = x_1x_3 \oplus x_2 \oplus 1</eq></td></tr><tr><td>012345ef89abcd67</td><td><eq>y_3 = x_1x_2 \oplus x_3, y_2 = x_2, y_1 = x_1, y_0 = x_0</eq></td></tr><tr><td>01234d6f89abc5e7</td><td><eq>y_3 = x_0x_2 \oplus x_3, y_2 = x_2, y_1 = x_1, y_0 = x_0</eq></td></tr><tr><td>012789af4563cdeb</td><td><eq>y_3 = x_2, y_2 = x_0x_1 \oplus x_3, y_1 = x_1, y_0 = x_0</eq></td></tr><tr><td>13569bde02478acf</td><td><eq>y_3 = x_2, y_2 = x_1, y_1 = x_0, y_0 = x_0x_1 \oplus x_3 \oplus 1</eq></td></tr><tr><td>13579ade02468bcf</td><td><eq>y_3 = x_2, y_2 = x_1, y_1 = x_0, y_0 = x_0x_2 \oplus x_3 \oplus 1</eq></td></tr><tr><td>13579bce02468adf</td><td><eq>y_3 = x_2, y_2 = x_1, y_1 = x_0, y_0 = x_1x_2 \oplus x_3 \oplus 1</eq></td></tr></table>

Table 12: 4-bit Sboxes implemented by 1 NAND and 1 XOR/XNOR gates (Here y<sub>3</sub>y<sub>2</sub>y<sub>1</sub>y<sub>0</sub> and x<sub>3</sub>x<sub>2</sub>x<sub>1</sub>x<sub>0</sub> denotes the 4- bit output and input respectively of the Sboxes). 