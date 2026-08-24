# THE SIMON AND SPECK FAMILIES OF LIGHTWEIGHT BLOCK CIPHERS

Ray Beaulieu
Douglas Shors
Jason Smith
Stefan Treatman-Clark
Bryan Weeks
Louis Wingers 

National Security Agency
9800 Savage Road, Fort Meade, MD 20755, USA 

{rabeaul, djshors, jksmit3, sgtreat, beweeks, lrwinge}@tycho.ncsc.mil
19 June 2013 

## ABSTRACT

In this paper we propose two families of block ciphers, SIMON and SPECK, each of which comes in a variety of widths and key sizes. While many lightweight block ciphers exist, most were designed to perform well on a single platform and were not meant to provide high performance across a range of devices. The aim of SIMON and SPECK is to fill the need for secure, flexible, and analyzable lightweight block ciphers. Each offers excellent performance on hardware and software platforms, is flexible enough to admit a variety of implementations on a given platform, and is amenable to analysis using existing techniques. Both perform exceptionally well across the full spectrum of lightweight applications, but SIMON is tuned for optimal performance in hardware, and SPECK for optimal performance in software. 

# THE SIMON AND SPECK FAMILIES OF LIGHTWEIGHT BLOCK CIPHERS

Ray Beaulieu
Douglas Shors
Jason Smith
Stefan Treatman-Clark
Bryan Weeks
Louis Wingers 

National Security Agency
9800 Savage Road, Fort Meade, MD 20755, USA 

{rabeaul, djshors, jksmit3, sgtreat, beweeks, lrwinge}@tycho.ncsc.mil 

19 June 2013 

## 1. INTRODUCTION

Existing cryptographic algorithms were, for the most part, designed to meet the needs of the desktop computing era. Such cryptography tends not to be particularly well-suited to the emerging era of pervasive computing, in which many highly constrained hardware- and software-based devices will need to communicate wirelessly with one another. And security is important for many of these devices: a hacker should not be able to take control of your insulin pump or override the brakes in your car. 

The relatively new field of lightweight cryptography addresses security issues for highly constrained devices. A great deal of excellent work has already been done in this area, much of it aimed specifically at developing block ciphers suitable for lightweight cryptographic applications—the references at the end of this paper provide just a small sample. The algorithms we present here build upon that body of work. Our goal is that they provide the security that the cryptographic community expects, while also delivering the flexibility and performance characteristics that developers require. 

We would like to stress at this point that a block cipher does not provide security by itself! Different applications will likely have very different security requirements, and protocols must be developed in each specific instance to achieve the desired level of security. But a block cipher is an extremely versatile cryptographic primitive, and we fully expect that any lightweight protocol can be based upon an appropriately-sized block cipher. 

That being said, the obvious first question for developers of lightweight applications is “Why not build my protocols around AES?” Indeed, AES [DR02] has been suggested for lightweight use, and given its stature, we believe it should be used whenever appropriate. However, for the most constrained environments, AES is not the right choice: in hardware, for example, the emerging consensus in the academic literature is that area should not exceed 2000 gate equivalents (see [JW05]), while the smallest available implementation of AES requires 2400* [MPL+11]. 

Among the block ciphers intended for use on constrained devices, some have been designed specifically to perform well on dedicated Application-Specific Integrated Circuits (ASICs), and thus can be realized by small circuits with minimal power requirements. Others are meant to perform well on low-cost microcontrollers with limited flash, SRAM, and/or power availability. Unfortunately, design choices meant to optimize performance on one platform often adversely affect performance on another. $^{†}$ 

Here we propose two families of highly-optimized block ciphers, SIMON and SPECK, that are flexible enough to provide excellent performance in both hardware and software environments. To the best of our knowledge, each of SIMON and SPECK outperforms both the best comparable hardware algorithms (in terms of the area required to achieve a given throughput), and the best comparable software algorithms (in terms of code size and memory usage). In addition, both families consist of algorithms having a range of block and key sizes, each of which admits a variety of implementations. The impact is that users will be able to closely match their application requirements with their security needs, without having to sacrifice performance. 

<table><tr><td colspan="2"></td><td colspan="2">hardware</td><td colspan="3">software</td></tr><tr><td>size</td><td>name</td><td>area (GE)</td><td>throughput (kbps)</td><td>flash (bytes)</td><td>SRAM (bytes)</td><td>throughput (kbps)</td></tr><tr><td rowspan="3">48/96</td><td>SIMON</td><td>763</td><td>15.0</td><td>196</td><td>0</td><td>589</td></tr><tr><td>SPECK</td><td>884</td><td>12.0</td><td>134</td><td>0</td><td>943</td></tr><tr><td>EPCBC</td><td>1008</td><td>12.1</td><td>[365]</td><td>0</td><td>[93]</td></tr><tr><td rowspan="5">64/80</td><td>TWINE</td><td>1011</td><td>16.2</td><td>1304</td><td>414</td><td>472</td></tr><tr><td>PRESENT</td><td>1030</td><td>12.4</td><td>[487]</td><td>0</td><td>96</td></tr><tr><td>PICCOLO</td><td>1043</td><td>14.8</td><td>-</td><td>-</td><td>-</td></tr><tr><td>KATAN</td><td>1054</td><td>25.1</td><td>272</td><td>18</td><td>14</td></tr><tr><td>KLEIN</td><td>1478</td><td>23.6</td><td>766</td><td>18</td><td>168</td></tr><tr><td rowspan="3">64/96</td><td>SIMON</td><td>838</td><td>17.8</td><td>274</td><td>0</td><td>540</td></tr><tr><td>SPECK</td><td>984</td><td>14.5</td><td>182</td><td>0</td><td>888</td></tr><tr><td>KLEIN</td><td>1528</td><td>19.1</td><td>[766]</td><td>[18]</td><td>[134]</td></tr><tr><td rowspan="4">64/128</td><td>SIMON</td><td>1000</td><td>16.7</td><td>282</td><td>0</td><td>515</td></tr><tr><td>SPECK</td><td>1127</td><td>13.8</td><td>186</td><td>0</td><td>855</td></tr><tr><td>PICCOLO</td><td>1334</td><td>12.1</td><td>-</td><td>-</td><td>-</td></tr><tr><td>PRESENT</td><td>1339</td><td>12.1</td><td>[487]</td><td>[0]</td><td>[96]</td></tr><tr><td rowspan="3">96/96</td><td>SIMON</td><td>984</td><td>14.8</td><td>454</td><td>0</td><td>454</td></tr><tr><td>SPECK</td><td>1134</td><td>13.8</td><td>276</td><td>0</td><td>866</td></tr><tr><td>EPCBC</td><td>1333</td><td>12.1</td><td>[730]</td><td>0</td><td>[93]</td></tr><tr><td rowspan="3">128/128</td><td>SIMON</td><td>1317</td><td>22.9</td><td>732</td><td>0</td><td>342</td></tr><tr><td>SPECK</td><td>1396</td><td>12.1</td><td>396</td><td>0</td><td>768</td></tr><tr><td>AES</td><td>2400</td><td>56.6</td><td>943</td><td>33</td><td>445</td></tr></table>


Table 1.1: Performance comparisons. Size is block size/key size; hardware refers to an ASIC implementation, and software to an implementation on an 8-bit microcontroller; clock speeds are 100 kHz (hardware) and 16 MHz (software). The best performance for a given size is indicated in red, the second best in blue. Numbers in brackets are our estimates; “-” means these values were unavailable at the time of writing.


SIMON has been optimized for performance on hardware devices, and SPECK for performance in software. But we emphasize that both families perform exceptionally well in both hardware and software, offering the flexibility across platforms that will be required by future applications. 

Table 1.1 shows a few significant hardware and software performance figures for SIMON, SPECK, and some other prominent block ciphers. For readers with some background in the field, much of the table will make sense without further explanation. Far more detail can be found in Sections 5, 6, and 7. Briefly, the data shown represent minimal-area hardware implementations achieving a throughput of at least 12 kilobits per second (kbps) at 100 kHz, and for software implementations minimizing what we call the balanced performance metric (see Equation (1)). 

The organization of the paper is as follows. Section 2 discusses issues in lightweight block cipher design and introduces some of the choices we made in designing SIMON and SPECK. The algorithms are specified in Sections 3 and 4. Sections 5, 6, and 7 discuss our performance comparisons, and give fairly extensive hardware and software performance data. In the appendices, we briefly touch on performance on 64-bit processors (Appendix A) and give test vectors for SIMON (Appendix B) and SPECK (Appendix C). 

## 2. LIGHTWEIGHT BLOCK CIPHER DESIGN CONSIDERATIONS

The term lightweight is used broadly to mean that an algorithm is suitable for use on some constrained platform. But the features that make an algorithm excel on an 8-bit microcontroller, say, do not necessarily imply that it can be realized by an extremely small circuit. We would prefer to have a less platform-dependent notion of what is meant by lightweight, and so some general discussion is in order regarding our goals. 

First, we make no attempt to optimize for a specific application. We prefer to make application-independent design choices that ensure good performance on both ASICs and 8-bit microcontrollers, with the idea that good performance in these environments will carry over to other important platforms as well—FPGAs, 4- and 16-bit microcontrollers, 32-bit processors, and so on. 

The principal aim is to provide algorithms that (1) have very small hardware implementations, and at the same time (2) have software implementations on small, low-power microcontrollers, with minimal flash and SRAM usage. 

Our desire for low-area hardware designs means that we favor simple, low-complexity round functions, even if that means many rounds are required. Fortunately, for many lightweight applications, throughput is not the top priority. For the sake of comparison, however, it makes sense to set some minimal throughput requirement for low-frequency hardware implementations. There is no universal convention to be followed: based on values we've seen in the literature (see [CDK09], for instance), and as we have noted above, we have chosen to limit the direct comparisons shown in Table 1.1 to implementations of our algorithms that achieve a throughput of at least 12 kilobits per second (kbps) at 100 kHz. 

For a lightweight algorithm to be as useful as possible, it should be flexible enough not just to be implemented efficiently on a variety of platforms, but also to allow for a variety of implementations on a single platform. For hardware applications, this means that it should be possible to take advantage of the available real estate. For extremely constrained hardware environments, very low-area implementations should be achievable, but if constraints are not so tight, one should be able to take advantage of this fact with larger-area, higher-throughput implementations. For software applications, very small flash and SRAM usage should be attainable, but high-throughput, low-energy implementations should be achievable as well. 

Existing lightweight algorithms tend to use components that limit their flexibility. One important consideration is the extent to which an algorithm can be serialized in hardware. An implementation that updates a single bit at a time is said to be fully serialized, or bit-serial, while one that updates the entire block during each cycle is said to be unserialized, or iterated. Some algorithms are inherently bit-serial, making for small, though not necessarily fast, hardware implementations. But increasing the throughput of such an algorithm can be unnecessarily costly (in terms of chip area). On the other hand, many algorithms are S-box based, precluding the possibility of efficient serialization at a level below the width of the S-box. This is reflected in the AES row of Table 1.1, where we see a throughput value much higher than 12 kbps, since AES is built from 8-bit S-boxes. Algorithms that can be efficiently serialized at any level provide better optimization opportunities. 

Flexibility extends in another direction as well: since applications and devices vary, a variety of block and key sizes is useful. For instance, block sizes of 64 and 128 bits are prevalent in the world of desktop computing, but atypical block sizes of 48 or 96 bits are optimal for some electronic product code (EPC) applications. Key sizes, on the other hand, are related to the desired level of security: a very low-cost device may achieve adequate security using just 64 bits of key, while more sensitive applications (running on suitably higher-cost devices) may require as many as 256 bits of key. 

In order to provide this flexibility, we've designed SIMON and SPECK to be block cipher families: Each supports block sizes of 32, 48, 64, 96, and 128 bits, with up to three key sizes to go along with each block size. Each family provides ten algorithms in all. Table 2.1 lists the different block and key sizes, in bits, for SIMON and SPECK. 

<table><tr><td>block size</td><td>key sizes</td></tr><tr><td>32</td><td>64</td></tr><tr><td>48</td><td>72, 96</td></tr><tr><td>64</td><td>96, 128</td></tr><tr><td>96</td><td>96, 144</td></tr><tr><td>128</td><td>128, 192, 256</td></tr></table>


Table 2.1: SIMON and SPECK parameters.


We need to say a word about security, which is of course the primary goal of cryptography. In addition to meeting performance objectives, it is expected that a cryptographic algorithm have a level of security that matches its key size. Since confidence in the security of an algorithm increases as it is analyzed, a designer should strive to create algorithms that are amenable to current cryptanalytic techniques. SIMON and SPECK have been subjected to a fair amount of analysis, but nowhere near the amount brought to bear on algorithms such as DES and AES. Care must also be taken to use the appropriate block and key sizes to match the required level of security for the application. 

But the fact of the matter is that our algorithms have simple round functions that invite analysis, and we are hopeful that this will entice the cryptographic community to expend some effort studying them. 

While our intent is that SIMON and SPECK provide the advertised level of security, a large security margin is a luxury that we can't always afford when resources are scarce. Our approach has been aggressive: we have built in what we believe is a sufficient security margin, but not an excessive one, and certainly one which is tighter than might be supplied in a more traditional setting. 

This brings up an important issue, and one we would like to see discussed further: What sorts of cryptanalytic adversaries should be considered in the world of lightweight cryptography? Does it make sense to allow access to the complete set of matched inputs and outputs for an algorithm with a 128-bit block size? One might argue that the amount of data encrypted by a single lightweight device during its functional lifetime will be tiny, and data to which an adversary has access will likely remain small when this tiny quantity is summed over all devices using a common key. In addition, for devices that can't be secured physically, practical (side-channel, reverse engineering) attacks will likely take precedence over cryptanalytic ones. The point is that there is a price to be paid (with every encryption) for blocking purely theoretical weaknesses, and it makes sense to think about what price is justified. 

Since there is not yet a fully crystallized point of view on this issue, we have proceeded in a more-or-less standard fashion. SIMON and SPECK have been designed to provide security against traditional adversaries who can adaptively encrypt and decrypt large amounts of data. We concede that (as is the case with other algorithms) there will be what amount to highly optimized ways to exhaust the key that reduce the cost of a naive exhaust by a small factor. We have also made a reasonable effort to provide security against adversaries who can flip key bits, and our aim is that there should be no related-key attacks. But we have made no effort to guard against attacks in the open-key model, and SIMON and SPECK have not been evaluated for use as hashes. 

## 3. THE SIMON FAMILY OF BLOCK CIPHERS

The SIMON block cipher with an n-bit word (and hence a 2n-bit block) is denoted SIMON2n, where n is required to be 16, 24, 32, 48, or 64. SIMON2n with an m-word (mn-bit) key will be referred to as SIMON2n/mn. For example, SIMON64/128 refers to the version of SIMON acting on 64-bit plaintext blocks and using a 128-bit key. 

Each instance of SIMON uses the familiar Feistel rule of motion. The algorithm is engineered to be extremely small in hardware and easy to serialize at various levels, but care was taken so as not to sacrifice software performance. 

## 3.1. ROUND FUNCTIONS

SIMON2n encryption and decryption make use of the following operations on n-bit words: 

- bitwise XOR, ⊕, 

- bitwise AND, &, and 

- left circular shift, $S^{j}$ , by $j$ bits. 

For $k \in \mathrm{GF}(2)^{n}$ , the key-dependent SIMON2n round function is the two-stage Feistel map $R_{k} \colon \mathrm{GF}(2)^{n} \times \mathrm{GF}(2)^{n} \to \mathrm{GF}(2)^{n} \times \mathrm{GF}(2)^{n}$ defined by 

$$
R _ {k} (x, y) = (y \oplus f (x) \oplus k, x),
$$

where $f(x) = (Sx \& S^{8}x) \oplus S^{2}x$ and k is the round key. The inverse of the round function, used for decryption, is 

$$
R _ {k} ^ {- 1} (x, y) = (y, x \oplus f (y) \oplus k).
$$

The SIMON key schedules take a key and from it generate a sequence of T key words $k_{0}, \ldots, k_{T-1}$ , where T is the number of rounds. The encryption map, then, is the composition $R_{k_{T-1}} \circ \cdots \circ R_{k_{1}} \circ R_{k_{0}}$ , read from right to left. Figure 3.1 shows the effect of the round function $R_{k_{i}}$ on the two words of subcipher $(x_{i+1}, x_{i})$ at the $i^{th}$ step of this process. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-16/43c7ec9c-9665-4f1c-85f5-6aac9c3360d1/24b0b17bad03e5df749651e63b2bae5be68ff5bd3e273c7e153deb3b311ebeec.jpg)



Figure 3.1: Feistel stepping of the SIMON round function.


Table 3.1 makes explicit our parameter choices for all versions of SIMON. 

Observe that SIMON includes no plaintext and ciphertext whitening steps, as inclusion of such operations can adversely affect circuit size. Consequently the first and last rounds do nothing cryptographically, other than acting to bring in the first and last round keys. There are various other locations on Figure 3.1 where key could have been included instead, some of which don't have this issue, but none without drawbacks. Similar comments apply to SPECK. 

## 3.2. KEY SCHEDULES

Note that apart from the round key, all rounds of SIMON are exactly the same, and the operations are perfectly symmetric with respect to the circular shift map on n-bit words. The SIMON key schedules employ a sequence of 1-bit round constants specifically for the purpose of eliminating slide properties and circular shift symmetries. In fact, we provide some cryptographic separation between different versions of SIMON having the same block size by defining five such sequences: $z_{0}, \ldots, z_{4}$ . Each of these sequences is defined in terms of one of the following period 31 sequences: 

<table><tr><td>block size 2n</td><td>key size mn</td><td>word size n</td><td>key words m</td><td>const seq</td><td>rounds T</td></tr><tr><td>32</td><td>64</td><td>16</td><td>4</td><td><eq>z_0</eq></td><td>32</td></tr><tr><td rowspan="2">48</td><td>72</td><td>24</td><td>3</td><td><eq>z_0</eq></td><td>36</td></tr><tr><td>96</td><td></td><td>4</td><td><eq>z_1</eq></td><td>36</td></tr><tr><td rowspan="2">64</td><td>96</td><td>32</td><td>3</td><td><eq>z_2</eq></td><td>42</td></tr><tr><td>128</td><td></td><td>4</td><td><eq>z_3</eq></td><td>44</td></tr><tr><td rowspan="2">96</td><td>96</td><td>48</td><td>2</td><td><eq>z_2</eq></td><td>52</td></tr><tr><td>144</td><td></td><td>3</td><td><eq>z_3</eq></td><td>54</td></tr><tr><td rowspan="3">128</td><td>128</td><td>64</td><td>2</td><td><eq>z_2</eq></td><td>68</td></tr><tr><td>192</td><td></td><td>3</td><td><eq>z_3</eq></td><td>69</td></tr><tr><td>256</td><td></td><td>4</td><td><eq>z_4</eq></td><td>72</td></tr></table>


Table 3.1: SIMON parameters.


$$
u = u _ {0} u _ {1} u _ {2} \dots = 1 1 1 1 1 0 1 0 0 0 1 0 0 1 0 1 0 1 1 0 0 0 0 1 1 1 0 0 1 1 0 \dots ,
$$

$$
v = v _ {0} v _ {1} v _ {2} \dots = 1 0 0 0 1 1 1 0 1 1 1 1 1 0 0 1 0 0 1 1 0 0 0 0 1 0 1 1 0 1 0 \dots ,
$$

$$
w = w _ {0} w _ {1} w _ {2} \dots = 1 0 0 0 0 1 0 0 1 0 1 1 0 0 1 1 1 1 1 0 0 0 1 1 0 1 1 1 0 1 0 \dots
$$

The first two sequences are simply $z_{0} = u$ and $z_{1} = v$ . The remaining three, $z_{2}$ , $z_{3}$ , and $z_{4}$ , have period 62 and are formed by computing the bitwise XOR of the period 2 sequence $t = t_{0}t_{1}t_{2}\ldots = \emptyset1\emptyset1\emptyset1\emptyset1\ldots$ with u, v, and w, respectively: 

$$
\begin{array}{r l r} & z _ {2} = (z _ {2}) _ {0} (z _ {2}) _ {1} (z _ {2}) _ {2} \dots = 1 0 1 0 1 1 1 1 0 1 1 1 0 0 0 0 0 0 1 1 0 1 0 0 1 0 0 1 1 0 0 \\ & & 0 1 0 1 0 0 0 0 1 0 0 0 1 1 1 1 1 1 0 0 1 0 1 1 0 1 1 0 0 1 1 \dots , \\ & z _ {3} = (z _ {3}) _ {0} (z _ {3}) _ {1} (z _ {3}) _ {2} \dots = 1 1 0 1 1 0 1 1 1 0 1 0 1 1 0 0 0 1 1 0 0 1 0 1 1 1 1 0 0 0 0 \\ & & 0 0 1 0 0 1 0 0 0 1 0 1 0 0 1 1 1 0 0 1 1 0 1 0 0 0 0 1 1 1 1 \dots , \\ & z _ {4} = (z _ {4}) _ {0} (z _ {4}) _ {1} (z _ {4}) _ {2} \dots = 1 1 0 1 0 0 0 1 1 1 1 0 0 1 1 0 1 0 1 1 0 1 1 0 0 0 1 0 0 0 \\ & & \mathbb {O} \mathbb {O} \mathbb {O} \mathbb {O} \mathbb {O} \mathbb {O} \mathbb {O} \mathbb {O} \mathbb {O} \mathbb {O} \mathbb {O} \mathbb {O} \mathbb {O} \mathbb {O} \mathbb {O} \mathbb {O} \mathbb {O} \mathbb {\Omega}, \end{array}
$$

where $(z_{i})_{j}$ is the $j^{th}$ bit of $z_{i}$ . 

The sequences u, v, and w can be generated as follows: Define $5 \times 5$ matrices U, V, and W over GF(2) by 

$$
U = \left[ \begin{array}{c c c c c} 0 & 1 & 0 & 0 & 0 \\ 0 & 0 & 1 & 0 & 0 \\ 1 & 0 & 0 & 1 & 0 \\ 0 & 0 & 0 & 0 & 1 \\ 1 & 0 & 0 & 0 & 1 \end{array} \right], V = \left[ \begin{array}{c c c c c} 0 & 1 & 1 & 0 & 0 \\ 0 & 0 & 1 & 0 & 0 \\ 1 & 0 & 0 & 1 & 0 \\ 0 & 0 & 0 & 0 & 1 \\ 1 & 0 & 0 & 0 & 0 \end{array} \right], W = \left[ \begin{array}{c c c c c} 0 & 1 & 0 & 0 & 0 \\ 0 & 0 & 1 & 0 & 0 \\ 1 & 0 & 0 & 1 & 0 \\ 0 & 0 & 0 & 0 & 1 \\ 1 & 0 & 0 & 0 & 0 \end{array} \right].
$$

The $i^{th}$ element of each sequence is then obtained by initializing a 5-bit linear feedback shift register to 00001, stepping i times using the corresponding matrix, and extracting the right-hand bit. Thus $(u)_{i} = (0, 0, 0, 0, 1) U^{i} (0, 0, 0, 0, 1)^{t}$ . 

Let $c = 2^n - 4 = \emptyset x f f \cdots f c$ . For SIMON2n with m key words $(k_{m-1}, \ldots, k_1, k_0)$ and constant sequence $z_j$ , round keys are generated by 

$$
k _ {i + m} = \left\{ \begin{array}{l l} c \oplus (z _ {j}) _ {i} \oplus k _ {i} \oplus (I \oplus S ^ {- 1}) S ^ {- 3} k _ {i + 1}, & \mathrm{if} m = 2, \\ c \oplus (z _ {j}) _ {i} \oplus k _ {i} \oplus (I \oplus S ^ {- 1}) S ^ {- 3} k _ {i + 2}, & \mathrm{if} m = 3, \\ c \oplus (z _ {j}) _ {i} \oplus k _ {i} \oplus (I \oplus S ^ {- 1}) (S ^ {- 3} k _ {i + 3} \oplus k _ {i + 1}), & \mathrm{if} m = 4, \end{array} \right.
$$

for $0 \leq i < T - m$ . The key schedules are represented in Figure 3.2, and the version-dependent choice of constant sequence $z_{j}$ is made explicit in Table 3.1. Note that key words $k_{0}$ to $k_{m-1}$ are used as the first m round keys; they are loaded into the shift registers with $k_{0}$ on the right and $k_{m-1}$ on the left. 

Pseudocode for all versions of Simon is shown in Figure 3.3. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-16/43c7ec9c-9665-4f1c-85f5-6aac9c3360d1/ba8bec9e92b1f22c0464553b7ffa0db5dcf3cf31b041352a06e58d6f6e761bcb.jpg)



Figure 3.2: The SIMON two, three, and four-word key expansions.


```haskell
---- definitions
    n = word size (16, 24, 32, 48, or 64)
    m = number of key words (must be    4 if n = 16,
    3 or 4 if n = 24 or 32,
    2 or 3 if n = 48,
    2, 3, or 4 if n = 64)

z = [11111010001001010110000111001101111101000100101011000011100110,
    10001110111110010011000010110101000111011111001001100001011010,
    10101111011100000011010010011000101000010001111110010110110011,
    11011011101011000110010111100000010010001010011100110100001111,
    1101000111100110101101100010000001011100001100101001001110111]
(T, j) = (32, 0)    if n = 16
    = (36, 0) or (36, 1)    if n = 24, m = 3 or 4
    = (42, 2) or (44, 3)    if n = 32, m = 3 or 4
    = (52, 2) or (54, 3)    if n = 48, m = 2 or 3
    = (68, 2), (69, 3), or (72, 4)    if n = 64, m = 2, 3, or 4

x, y    = plaintext words
k[m-1]..k[∅] = key words
---- key expansion ----
for i = m..T-1
    tmp ← S⁻³k[i-1]
    if (m = 4) tmp ← tmp ⊕ k[i-3]
    tmp ← tmp ⊕ S⁻¹tmp
    k[i] ← ~k[i-m] ⊕ tmp ⊕ z[j][(i-m) mod 62] ⊕ 3
end for
---- encryption ----
for i = 0..T-1
    tmp ← x
    x ← y ⊕ (Sx & S⁸x) ⊕ S²x ⊕ k[i]
    y ← tmp
end for 
```


Figure 3.3: SIMON pseudocode.


## 4. THE SPECK FAMILY OF BLOCK CIPHERS

The ten instances of SPECK have been designed to provide excellent performance in both hardware and software, but have been optimized for performance on microcontrollers. Our notation for the different variants of SPECK is entirely analogous to that used for SIMON. For example, SPECK96/144 refers to the SPECK block cipher with block size 96 bits and key size 144 bits. 

## 4.1. ROUND FUNCTIONS

The SPECK2n encryption maps make use of the following operations on n-bit words: 

- bitwise XOR, ⊕, 

- addition modulo $2^{n}$ , +, and 

- left and right circular shifts, $S^j$ and $S^{-j}$ , respectively, by $j$ bits. 

For $k \in \text{GF}(2)^{n}$ , the key-dependent SPECK2n round function is the map $R_{k}$ : $\text{GF}(2)^{n} \times \text{GF}(2)^{n} \to \text{GF}(2)^{n} \times \text{GF}(2)^{n}$ defined by 

$$
R _ {k} (x, y) = ((S ^ {- \alpha} x + y) \oplus k, S ^ {\beta} y \oplus (S ^ {- \alpha} x + y) \oplus k),
$$

with rotation amounts $\alpha = 7$ and $\beta = 2$ if n = 16 (block size = 32) and $\alpha = 8$ and $\beta = 3$ otherwise. The SPECK round functions are similar to the mixing functions found in the THREEFISH [FLS $^{+}$ 10] block cipher.* 

The inverse of the round function, necessary for decryption, uses modular subtraction instead of modular addition, and is given by 

$$
R _ {k} ^ {- 1} (x, y) = (S ^ {\alpha} ((x \oplus k) - S ^ {- \beta} (x \oplus y)), S ^ {- \beta} (x \oplus y)).
$$

Parameters for all versions of SPECK are specified in Table 4.1. 

<table><tr><td>block size 2n</td><td>key size mn</td><td>word size n</td><td>key words m</td><td>rot α</td><td>rot β</td><td>rounds T</td></tr><tr><td>32</td><td>64</td><td>16</td><td>4</td><td>7</td><td>2</td><td>22</td></tr><tr><td rowspan="2">48</td><td>72</td><td>24</td><td>3</td><td>8</td><td>3</td><td>22</td></tr><tr><td>96</td><td></td><td>4</td><td></td><td></td><td>23</td></tr><tr><td rowspan="2">64</td><td>96</td><td>32</td><td>3</td><td>8</td><td>3</td><td>26</td></tr><tr><td>128</td><td></td><td>4</td><td></td><td></td><td>27</td></tr><tr><td rowspan="2">96</td><td>96</td><td>48</td><td>2</td><td>8</td><td>3</td><td>28</td></tr><tr><td>144</td><td></td><td>3</td><td></td><td></td><td>29</td></tr><tr><td rowspan="3">128</td><td>128</td><td>64</td><td>2</td><td>8</td><td>3</td><td>32</td></tr><tr><td>192</td><td></td><td>3</td><td></td><td></td><td>33</td></tr><tr><td>256</td><td></td><td>4</td><td></td><td></td><td>34</td></tr></table>


Table 4.1: SPECK parameters.


The SPECK key schedules take a key and from it generate a sequence of T key words $k_{0}, \ldots, k_{T-1}$ , where T is the number of rounds. The effect of the single round function $R_{k_{i}}$ is shown in Figure 4.1. Encryption is then the composition $R_{k_{T-1}} \circ \cdots \circ R_{k_{1}} \circ R_{k_{0}}$ , read from right to left. 

Note that SPECK can be realized as the composition of two Feistel-like maps with respect to two different types of addition, namely, 

$$
(x, y) \mapsto (y, (S ^ {- \alpha} x + y) \oplus k) \text { and } (x, y) \mapsto (y, S ^ {\beta} x \oplus y).
$$

This decomposition is pictured in Figure 4.2. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-16/43c7ec9c-9665-4f1c-85f5-6aac9c3360d1/0434c59419d5485d65e11e0a49aa9ca810a25271d80226883b01e072ea02044d.jpg)



Figure 4.1: SPECK round function; $(x_{2i+1}, x_{2i})$ denotes the subcipher after i steps of encryption.


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-16/43c7ec9c-9665-4f1c-85f5-6aac9c3360d1/9af81828537a9bfbf82c52f9c9985e1ffe43b150acb43564076328f03a039014.jpg)



Figure 4.2: SPECK round function decomposed into Feistel-like steps.


## 4.2. KEY SCHEDULES

The SPECK key schedules use the round function to generate round keys $k_{i}$ . Let K be a key for a SPECK2n block cipher. We can write $K = (\ell_{m-2}, \ldots, \ell_{0}, k_{0})$ , where $\ell_{i}, k_{0} \in \mathrm{GF}(2)^{n}$ , for a value of m in $\{2, 3, 4\}$ . Sequences $k_{i}$ and $\ell_{i}$ are defined by 

$$
\begin{array}{r} \ell_ {i + m - 1} = (k _ {i} + S ^ {- \alpha} \ell_ {i}) \oplus i \mathrm{and} \\ k _ {i + 1} = S ^ {\beta} k _ {i} \oplus \ell_ {i + m - 1}. \end{array}
$$

The value $k_{i}$ is the $i^{th}$ round key, for $0 \leq i < T$ . See Figure 4.3. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-16/43c7ec9c-9665-4f1c-85f5-6aac9c3360d1/f037a718c0c82bd957efe855103091a03744211dcc9ce3b7ab01922a88960e8b.jpg)



Figure 4.3: SPECK key expansion, where $R_{i}$ is the SPECK round function with i acting as round key.


Pseudocode for all versions of SPECK is shown in Figure 4.4. 

```lua
---- definitions
    n = word size (16, 24, 32, 48, or 64)
    m = number of key words (must be 4 if n = 16,
    3 or 4 if n = 24 or 32,
    2 or 3 if n = 48,
    2 or 3 or 4 if n = 64)

    T = number = 22 if n = 16
    of rounds = 22 or 23 if n = 24, m = 3 or 4
    = 26 or 27 if n = 32, m = 3 or 4
    = 28 or 29 if n = 48, m = 2 or 3
    = 32, 33, or 34 if n = 64, m = 2, 3, or 4

    (α,β) = (7,2) if n = 16
    (8,3) otherwise

    x,y = plaintext words
    ℓ[m-2]..ℓ[0],k[0] = key words

---- key expansion ----
for i = 0..T-2
    ℓ[i+m-1] ← (k[i] + S⁻α ℓ[i]) ⊕ i
    k[i+1] ← Sβk[i] ⊕ ℓ[i+m-1]
end for

---- encryption ----
for i = 0..T-1
    x ← (S⁻αx + y) ⊕ k[i]
    y ← Sβy ⊕ x
end for 
```


Figure 4.4: SPECK pseudocode.


## 5. PERFORMANCE COMPARISONS

In this section we discuss the performance of SIMON and SPECK and fill in the details regarding the comparisons made in Table 1.1 with AES [DR02], EPCBC [YKPH11], KATAN [CDK09], KLEIN [GNL11], PICCOLO $\left[\mathrm{SIH}^{+}11\right]$ , PRESENT $\left[\mathrm{BKL}^{+}07\right]$ , and TWINE [SMMK]. 

We have restricted our comparisons exclusively to block ciphers, as block ciphers are extremely flexible cryptographic primitives with a well-developed cryptanalytic theory. Consequently, we don't consider other interesting lightweight designs like HUMMINGBIRD-2 [ESS11], GRAIN [HJMM08], TRIVIUM [CP05], and SALSA20 [Ber08]. 

It is important to note the difficulties inherent in the sort of comparison we're doing. Different authors implement their algorithms under differing assumptions: various cell libraries are used for hardware implementations, and a variety of assumptions are made for software implementations. In addition, it's not always clear what a particular author means, for example, by code size (is the decryption algorithm implemented or not?) or gate count (is the key schedule included?). All of this can make attempts at a fair comparison problematic. That said, we believe the performance advantage of our algorithms cannot fully be explained by such discrepancies. 

In this paper we strive to make equitable comparisons, and to provide all the relevant details about our performance metrics and our implementation platforms. We begin by discussing the platforms a bit further. 

The principal hardware resources are circuit area and power. Area is measured in gate equivalents; a gate equivalent (GE), which depends on a particular cell library, is the physical area required for the smallest available two-input NAND gate. Our results were generated using an ARM standard cell library for the IBM 8RF (0.13 micron) ASIC process. The areas of some basic gates in this library are as follows: NOT 0.75, NAND 1.00, AND 1.25, OR 1.25, XOR 2.00, XNOR 2.00, 2-1 MUX 2.25, D flip-flop 4.25, 1-bit full adder 5.75, scan flip-flop 6.25.* 

Areas given for our algorithms are for complete implementations: we include the flip-flops to store the state and key, logic to implement the encryption algorithm and key schedule, control logic to manage the encryption, and logic to allow the plaintext to be loaded and ciphertext to be read out. We have not, however, included an implementation of the decryption algorithm in any of our area figures. This is consistent with other authors' work: for extremely lightweight applications one would want to use a block cipher in an encrypt-only mode. 

Our current hardware designs have not proceeded past the synthesis stage, so reliable power information is not available. For this reason, we report only area figures. In addition, power consumption is strongly tied to the feature size, clock speed, etc., and this makes comparisons especially difficult. However, we expect that SIMON and SPECK are very amenable to low-power and low-energy implementations. 

We now turn our attention to Table 1.1, noting first the one slight mismatch in key sizes in the data presented there: neither SIMON nor SPECK has a variant that uses an 80-bit key. In an attempt to draw the fairest comparison, we have lumped algorithms of size 64/80 together in the table with our algorithms of size 64/96. 

The hardware area and hardware throughput columns of the table compare Simon and Speck with some of the best performing block ciphers available for lightweight hardware applications. The data for PRESENT and EPCBC is found in [YKPH11], for Piccolo in $[SIH^{+}11]$ , for KATAN in [CDK09], for TWINE in [SMMK], for KLEIN in [GNL11], and for AES in $[MPL^{+}11]$ . 

Two notable omissions from the table are PRINTCIPHER [KLPR10] and KTANTAN [CDK09], lightweight block ciphers that also achieve very low-area hardware implementations. These algorithms specifically target application spaces where there is never a need to update keys, and take advantage of this fact by hard-wiring a fixed key into the circuit. Because no flip-flops are required to store key bits, these algorithms realize a significant savings in area. Our algorithms, on the other hand, are meant to fill a much broader application space. 

We now turn to software applications. In the lightweight application space, we expect our algorithms to be implemented on inexpensive microcontrollers with very limited memory resources. Atmel's ATtiny45 8-bit microcontroller, for instance, has just 4 kB of flash and 256 bytes of SRAM. In addition, these microcontrollers often run on battery power, and cryptographic components require minimal energy per bit encrypted in the interest of extending battery life. 

For the purposes of comparison, we define the balanced performance metric* for a software implementation to be 

$$
\frac {\mathrm{throughput}}{\mathrm{flash} + 1 6 \cdot \mathrm{SRAM}}.\tag{1}
$$

A balanced implementation is one which scores well amongst a variety of implementations with respect to the balanced performance metric. The table compares balanced implementations of SIMON, SPECK, and various well-known algorithms. 

For algorithms other than SIMON and SPECK, we used the implementation with maximal balanced performance metric amongst those we could find in the literature. The software data for PRESENT is derived from $[EKP^{+}07]$ ; for KLEIN, KATAN, and AES from $[EGG^{+}12]$ ; and for TWINE from $[SMMK]$ . We note that the implementations given in some of these papers include the code for both the encryption and decryption algorithms. Since our SIMON and SPECK code provides encrypt capability only (which is reasonable for lightweight applications), we have subtracted the size of the decryption code $^{\dagger}$ from the numbers reported by those authors to obtain the numbers in our table. 

Alternatively, we could have included the decryption algorithms in our implementations. For SPECK, naive implementations would have required another 100 bytes or so of flash, but by exploiting the similarity between the encryption and decryption algorithms we could reduce this number significantly. For SIMON, the cost is negligible since the decryption algorithm is the encryption algorithm, up to swaps of words and reordering of round keys. 

We note that the best balanced implementations of our algorithms were in fact those that required no SRAM. For these, code implementing the encryption algorithm is stored in flash, and the key is pre-expanded and also stored in flash; this obviates the need to include code for the key schedule and allows for high-throughput/low-energy encryption. This contrasts with the way in which some of the other algorithms handle the key: generally they include code for the key schedule, and sometimes generate round keys on the fly. 

All of our software implementations were coded in assembly on an Atmel ATmega128 8-bit microcontroller running at 16 MHz. Distinct implementations were done for high throughput (low energy), low flash usage, and low SRAM usage. Results are presented in Section 7. 

We conclude by highlighting a couple of comparisons from Table 1.1 between our algorithms and two other prominent algorithms. 

- PRESENT-80 is a leading hardware-oriented lightweight block cipher, with an implementation requiring just 1030 GE and achieving throughput of 12.4 kilobits per second at 100 kHz. SIMON64/96 and SPECK64/96 (which provide 16 added bits of security) achieve even higher throughput at areas of just 838 and 984 GE, respectively. More importantly, our algorithms also have excellent software performance, and this is something that PRESENT was not designed to offer: SIMON64/96 and SPECK64/96 have about 10 and 25 times better balanced performance, respectively, than PRESENT-80. 

- AES is one of the best existing block ciphers for applications running on 8-bit microcontrollers. This makes it a fine choice for many lightweight software applications. But for extremely constrained applications where it is no longer viable, SIMON128/128 and SPECK128/128 can fill the void. Similarly, in hardware, if AES at 2400 GE is simply not an option, SIMON128/128 and SPECK128/128 can be made to fit in about half the area (see Table 6.1). 

Perhaps most significantly, lightweight applications typically do not require a 128-bit block cipher: a 64-bit block cipher may be perfectly adequate. This consideration makes the comparison of our algorithms with 

128-bit algorithms like AES (which offers no 64-bit size) even more compelling. SIMON64/128 and SPECK64/128 have significantly higher balanced performance, and have minimal hardware requirements which fall below 1000 GE. 

## 6. HARDWARE PERFORMANCE

This section presents detailed information regarding our ASIC implementations of SIMON and SPECK. The algorithms were implemented in VHDL and synthesized using Synopsys Design Compiler 11.09-SP4 to target the ARM SAGE-X v2.0 standard cell library for IBM's 8RF 130nm (CMR8SF-LPVT) process. Typical DC supply voltages for the process are 1.2 V. All throughput values given in this section assume a clock speed of 100 kHz. 

Of particular interest are fully serialized implementations, for which nearly all of the chip area is dedicated to holding the words of subcipher and key. Table 6.1 presents our data for such area-minimizing implementations. We note that throughput for these implementations is necessarily low, and typically well below the 12 kbps threshold required for inclusion in Table 1.1. We also note that fully serial implementations don't always make a lot of sense, as the marginal cost in area to double or even quadruple the throughput is quite small.* 

Table 6.2 gives a more complete set of hardware data for SIMON and SPECK, corresponding to various levels of serialization. The smallest area obtained for each block size represents the fully serialized implementation, where a single bit of each word is updated during each clock cycle. Subsequent lines are for implementations that process larger divisors of the word size. The largest area implementation listed for each block size corresponds to an iterated implementation, which carries out a complete round in a single cycle. Though other levels of serialization are certainly possible, this table should serve to demonstrate the flexibility of our algorithms in hardware. 

<table><tr><td>size</td><td>name</td><td>area (GE)</td><td>throughput (kbps)</td></tr><tr><td rowspan="2">32/64</td><td>SIMON</td><td>523</td><td>5.6</td></tr><tr><td>SPECK</td><td>580</td><td>4.2</td></tr><tr><td rowspan="2">48/72</td><td>SIMON</td><td>631</td><td>5.1</td></tr><tr><td>SPECK</td><td>693</td><td>4.3</td></tr><tr><td rowspan="2">48/96</td><td>SIMON</td><td>739</td><td>5.0</td></tr><tr><td>SPECK</td><td>794</td><td>4.0</td></tr><tr><td rowspan="2">64/96</td><td>SIMON</td><td>809</td><td>4.4</td></tr><tr><td>SPECK</td><td>860</td><td>3.6</td></tr><tr><td rowspan="2">64/128</td><td>SIMON</td><td>958</td><td>4.2</td></tr><tr><td>SPECK</td><td>996</td><td>3.4</td></tr><tr><td rowspan="2">96/96</td><td>SIMON</td><td>955</td><td>3.7</td></tr><tr><td>SPECK</td><td>1012</td><td>3.4</td></tr><tr><td rowspan="2">96/144</td><td>SIMON</td><td>1160</td><td>3.5</td></tr><tr><td>SPECK</td><td>1217</td><td>3.3</td></tr><tr><td rowspan="2">128/128</td><td>SIMON</td><td>1234</td><td>2.9</td></tr><tr><td>SPECK</td><td>1280</td><td>3.0</td></tr><tr><td rowspan="2">128/192</td><td>SIMON</td><td>1508</td><td>2.8</td></tr><tr><td>SPECK</td><td>1566</td><td>2.9</td></tr><tr><td rowspan="2">128/256</td><td>SIMON</td><td>1782</td><td>2.6</td></tr><tr><td>SPECK</td><td>1840</td><td>2.8</td></tr></table>


Table 6.1: Hardware performance: area-minimizing implementations.


We note that in Table 6.2 it appears that SPECK peaks at a higher throughput than SIMON. This is an artifact of our choice to show the data for updating at most n bits per clock cycle for SIMON2n and SPECK2n. It's not hard to do an implementation of SIMON64 that updates, say, 40 bits at a time, or 64 bits at a time, with the associated increases in area and throughput. But we have not included a separate table for high-throughput hardware implementations like this, because these implementations have relatively large area, and, as such, fall outside the scope of this paper. In particular, if throughput per unit area is the measure of interest, then optimal implementations are not shown in the table—they would involve updating more than n bits per clock cycle. 

A further note on throughput: it's natural to count only those cycles required for the encryption process. However, we believe that the throughput values we present will be of most interest to implementers considering applications that require the encryption of only a small number of blocks. Consequently, we have included cycles for loading plaintext and key in a manner consistent with our low-area implementation. In every case it's possible to make the loading proceed more quickly, thereby raising throughput a little, at a small cost in area. We have not included any cycles for sending the resulting ciphertext off chip, since we make the assumption that this can be done more-or-less instantaneously or, at worst, simultaneously with the task of reading new data. 


Table 6.2: Hardware performance for SIMON and SPECK.


<table><tr><td>algorithm</td><td>area (GE)</td><td>throughput (kbps)</td><td>algorithm</td><td>area (GE)</td><td>throughput (kbps)</td></tr><tr><td rowspan="5">SIMON32/64</td><td>523</td><td>5.6</td><td rowspan="5">SPECK32/64</td><td>580</td><td>4.2</td></tr><tr><td>535</td><td>11.1</td><td>642</td><td>8.3</td></tr><tr><td>566</td><td>22.2</td><td>708</td><td>16.7</td></tr><tr><td>627</td><td>44.4</td><td>822</td><td>33.3</td></tr><tr><td>722</td><td>88.9</td><td>850</td><td>123.1</td></tr><tr><td rowspan="8">SIMON48/72</td><td>631</td><td>5.1</td><td rowspan="8">SPECK48/72</td><td>693</td><td>4.3</td></tr><tr><td>639</td><td>10.3</td><td>752</td><td>8.5</td></tr><tr><td>648</td><td>15.4</td><td>777</td><td>12.8</td></tr><tr><td>662</td><td>20.5</td><td>821</td><td>17.0</td></tr><tr><td>683</td><td>30.8</td><td>848</td><td>25.5</td></tr><tr><td>714</td><td>41.0</td><td>963</td><td>34.0</td></tr><tr><td>765</td><td>61.5</td><td>1040</td><td>51.1</td></tr><tr><td>918</td><td>123.1</td><td>1152</td><td>192.0</td></tr></table>


Continued on next page 


<table><tr><td>algorithm</td><td>area</td><td>throughput</td></tr><tr><td rowspan="8">SIMON48/96</td><td>739</td><td>5.0</td></tr><tr><td>750</td><td>10.0</td></tr><tr><td>763</td><td>15.0</td></tr><tr><td>781</td><td>20.0</td></tr><tr><td>804</td><td>30.0</td></tr><tr><td>839</td><td>40.0</td></tr><tr><td>898</td><td>60.0</td></tr><tr><td>1062</td><td>120.0</td></tr><tr><td rowspan="6">SIMON64/96</td><td>809</td><td>4.4</td></tr><tr><td>815</td><td>8.9</td></tr><tr><td>838</td><td>17.8</td></tr><tr><td>891</td><td>35.6</td></tr><tr><td>1004</td><td>71.1</td></tr><tr><td>1216</td><td>142.2</td></tr><tr><td rowspan="6">SIMON64/128</td><td>958</td><td>4.2</td></tr><tr><td>968</td><td>8.3</td></tr><tr><td>1000</td><td>16.7</td></tr><tr><td>1057</td><td>33.3</td></tr><tr><td>1185</td><td>66.7</td></tr><tr><td>1417</td><td>133.3</td></tr><tr><td rowspan="10">SIMON96/96</td><td>955</td><td>3.7</td></tr><tr><td>965</td><td>7.4</td></tr><tr><td>971</td><td>11.1</td></tr><tr><td>984</td><td>14.8</td></tr><tr><td>1007</td><td>22.2</td></tr><tr><td>1037</td><td>29.6</td></tr><tr><td>1088</td><td>44.4</td></tr><tr><td>1151</td><td>59.3</td></tr><tr><td>1263</td><td>88.9</td></tr><tr><td>1580</td><td>177.8</td></tr></table>

<table><tr><td>algorithm</td><td>area</td><td>throughput</td></tr><tr><td rowspan="8">SPECK48/96</td><td>794</td><td>4.0</td></tr><tr><td>857</td><td>8.0</td></tr><tr><td>884</td><td>12.0</td></tr><tr><td>932</td><td>16.0</td></tr><tr><td>961</td><td>24.0</td></tr><tr><td>1081</td><td>32.0</td></tr><tr><td>1167</td><td>48.0</td></tr><tr><td>1254</td><td>177.8</td></tr><tr><td rowspan="6">SPECK64/96</td><td>860</td><td>3.6</td></tr><tr><td>918</td><td>7.3</td></tr><tr><td>984</td><td>14.5</td></tr><tr><td>1095</td><td>29.1</td></tr><tr><td>1338</td><td>58.2</td></tr><tr><td>1522</td><td>220.7</td></tr><tr><td rowspan="6">SPECK64/128</td><td>996</td><td>3.4</td></tr><tr><td>1058</td><td>6.9</td></tr><tr><td>1127</td><td>13.8</td></tr><tr><td>1247</td><td>27.6</td></tr><tr><td>1506</td><td>55.2</td></tr><tr><td>1658</td><td>206.5</td></tr><tr><td rowspan="10">SPECK96/96</td><td>1012</td><td>3.4</td></tr><tr><td>1067</td><td>6.9</td></tr><tr><td>1089</td><td>10.3</td></tr><tr><td>1134</td><td>13.8</td></tr><tr><td>1157</td><td>20.7</td></tr><tr><td>1267</td><td>27.6</td></tr><tr><td>1328</td><td>41.4</td></tr><tr><td>1514</td><td>55.2</td></tr><tr><td>1673</td><td>82.8</td></tr><tr><td>2058</td><td>320.0</td></tr></table>


Continued on next page 


<table><tr><td>algorithm</td><td>area</td><td>throughput</td></tr><tr><td rowspan="10">SIMON96/144</td><td>1160</td><td>3.5</td></tr><tr><td>1169</td><td>7.0</td></tr><tr><td>1175</td><td>10.5</td></tr><tr><td>1189</td><td>14.0</td></tr><tr><td>1211</td><td>21.0</td></tr><tr><td>1242</td><td>28.1</td></tr><tr><td>1292</td><td>42.1</td></tr><tr><td>1354</td><td>56.1</td></tr><tr><td>1467</td><td>84.2</td></tr><tr><td>1790</td><td>168.4</td></tr><tr><td rowspan="7">SIMON128/128</td><td>1234</td><td>2.9</td></tr><tr><td>1242</td><td>5.7</td></tr><tr><td>1263</td><td>11.4</td></tr><tr><td>1317</td><td>22.9</td></tr><tr><td>1430</td><td>45.7</td></tr><tr><td>1665</td><td>91.4</td></tr><tr><td>2090</td><td>182.9</td></tr><tr><td rowspan="7">SIMON128/192</td><td>1508</td><td>2.8</td></tr><tr><td>1514</td><td>5.6</td></tr><tr><td>1536</td><td>11.1</td></tr><tr><td>1587</td><td>22.2</td></tr><tr><td>1700</td><td>44.4</td></tr><tr><td>1937</td><td>88.9</td></tr><tr><td>2378</td><td>177.8</td></tr><tr><td rowspan="7">SIMON128/256</td><td>1782</td><td>2.6</td></tr><tr><td>1792</td><td>5.3</td></tr><tr><td>1823</td><td>10.5</td></tr><tr><td>1883</td><td>21.1</td></tr><tr><td>2010</td><td>42.1</td></tr><tr><td>2272</td><td>84.2</td></tr><tr><td>2776</td><td>168.4</td></tr></table>

<table><tr><td>algorithm</td><td>area</td><td>throughput</td></tr><tr><td rowspan="10">SPECK96/144</td><td>1217</td><td>3.3</td></tr><tr><td>1269</td><td>6.6</td></tr><tr><td>1297</td><td>9.8</td></tr><tr><td>1345</td><td>13.1</td></tr><tr><td>1371</td><td>19.7</td></tr><tr><td>1485</td><td>26.2</td></tr><tr><td>1558</td><td>39.3</td></tr><tr><td>1751</td><td>52.5</td></tr><tr><td>1928</td><td>78.7</td></tr><tr><td>2262</td><td>300.0</td></tr><tr><td rowspan="7">SPECK128/128</td><td>1280</td><td>3.0</td></tr><tr><td>1338</td><td>6.1</td></tr><tr><td>1396</td><td>12.1</td></tr><tr><td>1488</td><td>24.2</td></tr><tr><td>1711</td><td>48.5</td></tr><tr><td>2179</td><td>97.0</td></tr><tr><td>2727</td><td>376.5</td></tr><tr><td rowspan="7">SPECK128/192</td><td>1566</td><td>2.9</td></tr><tr><td>1627</td><td>5.8</td></tr><tr><td>1687</td><td>11.6</td></tr><tr><td>1797</td><td>23.2</td></tr><tr><td>2038</td><td>46.4</td></tr><tr><td>2536</td><td>92.8</td></tr><tr><td>3012</td><td>355.6</td></tr><tr><td rowspan="7">SPECK128/256</td><td>1840</td><td>2.8</td></tr><tr><td>1901</td><td>5.6</td></tr><tr><td>1967</td><td>11.1</td></tr><tr><td>2087</td><td>22.2</td></tr><tr><td>2341</td><td>44.4</td></tr><tr><td>2872</td><td>88.9</td></tr><tr><td>3284</td><td>336.8</td></tr></table>

## 7. SOFTWARE PERFORMANCE: 8-BIT MICROCONTROLLERS

Generally speaking, we expect our algorithms to have exceptional performance on 4-, 8-, 16-, and 32-bit microcontrollers. For the sake of comparison, however, we have chosen to report data only for 8-bit implementations of SIMON and SPECK, since most lightweight implementations reported in the literature have been on such platforms. In particular, we implemented our algorithms on the Atmel ATmega128, a low-power device with 128K bytes of programmable flash memory, 4K bytes of SRAM, and 32 8-bit general purpose registers. 

Tables 7.1, 7.2, and 7.3 show results for high-throughput, low-SRAM, and low-flash implementations of SIMON and SPECK. In most cases we don't optimize the parameter in question, because doing so tends to have a deleterious effect on the other parameters. For example, if the cost of decreasing the code size by a few bytes is to reduce throughput by $50\%$ , then we forgo the code-size reduction. Similarly, we don't report data for an implementation that achieves $1\%$ increase in throughput if the consequence is to double the code size. 

We do not give throughput directly in these tables, as we did in Table 1.1. Instead, we show the encryption cost in cycles per byte, i.e., the number of cycles required per byte of ciphertext, as this is the common metric used in the literature for software implementations. 

We now provide a little more detail about what is shown in each of the three tables. Among the choices we have that give rise to varying implementations are the following: (1) Is the code fully or partially unrolled, or is just one round implemented? (2) Is the key schedule implemented and the code stored in flash, or are the round keys simply assumed to be present in flash? (3) Are common functions done via function calls or via in-line code? 

Table 7.1 shows results for high-throughput implementations of the algorithms. High throughput on a microcontroller equates to low energy, so such implementations are of interest when battery life is at a premium. 

Maximal throughput is attained by fully unrolling code in order to eliminate all loop overhead. This, however, can lead to very large programs, and most of the performance gains achievable by fully unrolling can be achieved by partial unrolling. Table 7.1 shows the minimal code-size results whose throughput is no more than 3% worse than the maximal throughput versions. Someone who really cares about this 2–3% can get it back, but with a significant code size penalty. 

With regard to throughput, we note that the fastest reported software implementation of AES-128 available on an Atmel 8-bit microcontroller has a cost of 125 cycles/byte, and uses 1912 bytes of flash and 432 bytes of SRAM [BOSC10]. For a slight decrease in speed, the same implementers offer a more balanced implementation with a cost of 135 cycles/byte, using 1912 bytes of flash and 176 bytes of SRAM. Our high-speed SPECK128/128 implementation has comparable throughput, at 139 cycles/byte, but uses only 388 bytes of flash and 256 bytes of SRAM. 

If one doesn't require a full 128-bit cipher, then SPECK64/128 could be considered. One implementation of SPECK64/128 encrypts at 120 cycles/byte, and when compared to the fastest implementation of AES-128 mentioned above, uses less than a sixth of the flash (284 bytes) and a quarter of the SRAM (108 bytes).* 

In addition, the SPECK implementations are straightforward, and this tends not to be the case for high-speed AES implementations. 

Table 7.2 shows results for low-SRAM implementations of the algorithms. As it always is, code for the encryption algorithm is stored in flash. But here the key schedule is not implemented; instead, key is assumed to have been pre-expanded and round keys are stored in flash. Here we must include the time to load the key from flash into registers as part of the encryption cost. 

Table 7.3 shows results for low-flash (i.e., low code-size) implementations of the algorithms. In most cases we also store the key schedule code in flash, in addition to the encryption code. $^{†}$ We then expand the key and load it into SRAM, and so the reported SRAM usage is the amount of storage required to hold all the round keys (but in some cases one or two more words are necessary). 

The encryption cost counts only the cycles required for encryption, i.e., it does not include the cycles required for the generation or storage of expanded key in SRAM. This approach makes sense for many high-speed applications, where a large amount of data may need to be encrypted. We note that the key generation for SIMON or SPECK requires about as many cycles as a single encryption. 

Small code size is achieved in part by doing function calls for common operations such as n-bit XORs. There is overhead associated with each function call, and so throughput is affected. Our low-flash implementations use this technique, but only within reason. Additional code-size savings are possible (up to 30 bytes for SPECK and 50 bytes for SIMON), but only by significantly reducing throughput. 

Finally, none of the results we report include any wrappers necessary for an actual application to interface with the external world. In particular, we have omitted the instructions and cycle counts associated with reading data in from the ports, and reading key in from wherever it resides. We also do not count any flash that may be required to store the key or plaintext. 

<table><tr><td>size</td><td>name</td><td>flash(bytes)</td><td>SRAM(bytes)</td><td>enc. cost(cycles/byte)</td></tr><tr><td rowspan="2">32/64</td><td>SIMON</td><td>384</td><td>64</td><td>168</td></tr><tr><td>SPECK</td><td>424</td><td>44</td><td>110</td></tr><tr><td rowspan="2">48/72</td><td>SIMON</td><td>430</td><td>108</td><td>187</td></tr><tr><td>SPECK</td><td>532</td><td>66</td><td>100</td></tr><tr><td rowspan="2">48/96</td><td>SIMON</td><td>442</td><td>108</td><td>187</td></tr><tr><td>SPECK</td><td>562</td><td>69</td><td>104</td></tr><tr><td rowspan="2">64/96</td><td>SIMON</td><td>530</td><td>168</td><td>205</td></tr><tr><td>SPECK</td><td>556</td><td>104</td><td>114</td></tr><tr><td rowspan="2">64/128</td><td>SIMON</td><td>404</td><td>176</td><td>217</td></tr><tr><td>SPECK</td><td>596</td><td>108</td><td>118</td></tr><tr><td rowspan="2">96/96</td><td>SIMON</td><td>544</td><td>312</td><td>249</td></tr><tr><td>SPECK</td><td>454</td><td>168</td><td>123</td></tr><tr><td rowspan="2">96/144</td><td>SIMON</td><td>444</td><td>324</td><td>260</td></tr><tr><td>SPECK</td><td>576</td><td>174</td><td>127</td></tr><tr><td rowspan="2">128/128</td><td>SIMON</td><td>446</td><td>544</td><td>333</td></tr><tr><td>SPECK</td><td>388</td><td>256</td><td>139</td></tr><tr><td rowspan="2">128/192</td><td>SIMON</td><td>582</td><td>552</td><td>335</td></tr><tr><td>SPECK</td><td>568</td><td>272</td><td>143</td></tr><tr><td rowspan="2">128/256</td><td>SIMON</td><td>458</td><td>576</td><td>353</td></tr><tr><td>SPECK</td><td>458</td><td>288</td><td>147</td></tr><tr><td rowspan="2">32/64</td><td>SIMON</td><td>130</td><td>0</td><td>205</td></tr><tr><td>SPECK</td><td>92</td><td>0</td><td>140</td></tr><tr><td rowspan="2">48/72</td><td>SIMON</td><td>196</td><td>0</td><td>220</td></tr><tr><td>SPECK</td><td>130</td><td>0</td><td>130</td></tr><tr><td rowspan="2">48/96</td><td>SIMON</td><td>196</td><td>0</td><td>220</td></tr><tr><td>SPECK</td><td>134</td><td>0</td><td>136</td></tr><tr><td rowspan="2">64/96</td><td>SIMON</td><td>274</td><td>0</td><td>239</td></tr><tr><td>SPECK</td><td>182</td><td>0</td><td>144</td></tr><tr><td rowspan="2">64/128</td><td>SIMON</td><td>282</td><td>0</td><td>250</td></tr><tr><td>SPECK</td><td>186</td><td>0</td><td>150</td></tr><tr><td rowspan="2">96/96</td><td>SIMON</td><td>454</td><td>0</td><td>284</td></tr><tr><td>SPECK</td><td>276</td><td>0</td><td>148</td></tr><tr><td rowspan="2">96/144</td><td>SIMON</td><td>466</td><td>0</td><td>295</td></tr><tr><td>SPECK</td><td>282</td><td>0</td><td>153</td></tr><tr><td rowspan="2">128/128</td><td>SIMON</td><td>732</td><td>0</td><td>376</td></tr><tr><td>SPECK</td><td>396</td><td>0</td><td>167</td></tr><tr><td rowspan="2">128/192</td><td>SIMON</td><td>740</td><td>0</td><td>381</td></tr><tr><td>SPECK</td><td>404</td><td>0</td><td>172</td></tr><tr><td rowspan="2">128/256</td><td>SIMON</td><td>764</td><td>0</td><td>398</td></tr><tr><td>SPECK</td><td>412</td><td>0</td><td>177</td></tr><tr><td rowspan="2">32/64</td><td>SIMON</td><td>136</td><td>64</td><td>189</td></tr><tr><td>SPECK</td><td>102</td><td>44</td><td>167</td></tr><tr><td rowspan="2">48/72</td><td>SIMON</td><td>166</td><td>108</td><td>202</td></tr><tr><td>SPECK</td><td>126</td><td>69</td><td>145</td></tr><tr><td rowspan="2">48/96</td><td>SIMON</td><td>178</td><td>108</td><td>202</td></tr><tr><td>SPECK</td><td>132</td><td>72</td><td>151</td></tr><tr><td rowspan="2">64/96</td><td>SIMON</td><td>198</td><td>168</td><td>218</td></tr><tr><td>SPECK</td><td>152</td><td>108</td><td>154</td></tr><tr><td rowspan="2">64/128</td><td>SIMON</td><td>208</td><td>176</td><td>228</td></tr><tr><td>SPECK</td><td>160</td><td>112</td><td>160</td></tr><tr><td rowspan="2">96/96</td><td>SIMON</td><td>256</td><td>312</td><td>258</td></tr><tr><td>SPECK</td><td>170</td><td>174</td><td>150</td></tr><tr><td rowspan="2">96/144</td><td>SIMON</td><td>256</td><td>324</td><td>268</td></tr><tr><td>SPECK</td><td>206</td><td>180</td><td>155</td></tr><tr><td rowspan="2">128/128</td><td>SIMON</td><td>328</td><td>544</td><td>342</td></tr><tr><td>SPECK</td><td>214</td><td>264</td><td>165</td></tr><tr><td rowspan="2">128/192</td><td>SIMON</td><td>328</td><td>552</td><td>347</td></tr><tr><td>SPECK</td><td>266</td><td>272</td><td>170</td></tr><tr><td rowspan="2">128/256</td><td>SIMON</td><td>340</td><td>576</td><td>362</td></tr><tr><td>SPECK</td><td>284</td><td>280</td><td>175</td></tr></table>


Table 7.1: High-throughput (low-energy) software implementations.


Table 7.2: Low-SRAM software implementations. 

Table 7.3: Low-flash software implementations. 

## REFERENCES



[Ber08] D. J. Bernstein. The Salsa20 Family of Stream Ciphers. In New Stream Cipher Designs—The eSTREAM Finalists, Lecture Notes in Compter Science, No. 4986, pages 84–97. Springer-Verlag, 2008. 19 





[BKL $^{+}$ 07] A. Bogdanov, L. R. Knudsen, G. Leander, C. Paar, A. Poschmann, M.J.B. Robshaw, Y. Seurin, and C. Vikkelsoe. PRESENT: An UltraLightweight Block Cipher. In CHES 2007, Lecture Notes in Computer Science, No. 4727, pages 450–66. Springer-Verlag, 2007. 19 





[BOSC10] J. Bos, D. Osvik, D. Stefan, and D. Canright. Fast Software AES Encryption. In Proceedings of the 17th international conference on fast software encryption, FSE 2010, pages 75–93. Springer-Verlag, 2010. 29 





[CDK09] C. D. Cannière, O. Dunkelman, and M. Knežević. KATAN and KTANTAN - A Family of Small and Efficient Hardware-Oriented Block Ciphers. In CHES 2009, Lecture Notes in Computer Science, No. 5747, pages 272–88. Springer-Verlag, 2009. 5, 19, 20 





[CP05] C. D. Canniere and B. Preneel. Trivium Specifications. In ECRYPT Stream Cipher Project Report 2005/030, 2005. 19 





[DR02] J. Daemen and V. Rijmen. The Design of Rijndael. Springer, Berlin, 2002. 2, 19 





[EGG+12] T. Eisenbarth, Z. Gong, T. Güneysu, S. Heyse, S. Indesteege, S. Kerckhof, F. Koeune, T. Nad, T. Plos, F. Regazzoni, F.-X. Standaert, and L. van Oldeneel tot Oldenzeel. Compact Implementation and Performance Evaluation of Block Ciphers in ATtiny Devices. In Africacrypt 2012, Progress in Cryptology, pages 172–87. Springer-Verlag, 2012. 21 





[EKP $^{+}$ 07] T. Eisenbarth, S. Kumar, C. Paar, A. Poschmann, and L. Uhsadel. A Survey of Lightweight-Cryptography Implementations. In IEEE Design & Test, Volume 24, Issue 6, pages 522–33, 2007. 21 





[ESS11] D. Engels, M. Saarinen, and E. Smith. The Hummingbird-2 lightweight authenticated encryption algorithm. In Cryptology ePrint Archive, Report 2011/126, 2011. 19 





[FLS $^{+}$ 10] N. Ferguson, S. Lucks, B. Schneier, D. Whiting, M. Bellare, T. Kohno, J. Callas, and J. Walker. The Skein Hash Function Family, version 1.3, 1 Oct 2010. 14 





[GNL11] Z. Gong, S. Nikova, and Y. W. Law. KLEIN: A New Family of Lightweight Block Ciphers. In RFIDsec '11 Workshop Proceedings, Cryptology and Information Security Series, No. 6, pages 1–18. IOS Press, 2011. 19, 20 





[HJMM08] M. Hell, T. Johansson, A. Maximov, and W. Meier. The Grain Family of Stream Ciphers. In New Stream Cipher Designs—The eSTREAM Finalists, Lecture Notes in Compter Science, No. 4986, pages 179–90. Springer-Verlag, 2008. 19 





[JW05] A. Juels and S. A. Weis. Authenticating Pervasive Devices with Human Protocols. In Advances in Cryptology—CRYPTO '05, Lecture Notes in Computer Science, No. 3126, pages 293–308. Springer-Verlag, 2005. 2 





[KLPR10] L. R. Knudsen, G. Leander, A. Poschmann, and M. J. B. Robshaw. PRINTCIPHER: A Block Cipher for IC Printing. In CHES 2010 Proceedings, Lecture Notes in Computer Science, No. 6225, pages 16–32. Springer-Verlag, 2010. 20 





[MPL $^{+}$ 11] A. Moradi, A. Poschmann, S. Ling, C. Paar, and H. Wang. Pushing the Limits: A Very Compact and a Threshold Implementation of AES. In Advances in Cryptology—EUROCRYPT 2011, Lecture Notes in Computer Science, No. 6632, pages 69–88. Springer-Verlag, 2011. 2, 20 





[REP07] S. Rinne, T. Eisenbarth, and C. Paar. Performance Analysis of Contemporary Lightweight Block Ciphers on 8-bit Microcontrollers. In SPEED—Software Performance Enhancement for Encryption and Decryption, 2007. 21 





[SIH $^{+}$ 11] K. Shibutani, T. Isobe, H. Hiwatari, A. Mitsuda, T. Akishita, and T. Shirai. Piccolo: An Ultra-Lightweight Blockcipher. In CHES 2011, Lecture Notes in Computer Science, No. 6917, pages 342–57. Springer-Verlag, 2011. 19, 20 





[SMMK] T. Suzuki, K. Minematsu, S. Morioka, and E. Kobayashi. TWINE: A Lightweight, Versatile Block Cipher. www.nec.co.jp/rd/media/code/research/images/twine_LC11.pdf. 19, 20, 21 





[WN95] D. Wheeler and R. Needham. TEA, a Tiny Encryption Algorithm. In B. Preneel, editor, FSE 1994, Lecture Notes in Computer Science, No. 1008, pages 363–6. Springer-Verlag, 1995. 40 





[YKPH11] H. Yap, K. Khoo, A. Poschmann, and M. Henricksen. EPCBC—A Block Cipher Suitable for Electronic Product Code Encryption. In CANS 2011, Lecture Notes in Computer Science, No. 7092, pages 76–97. Springer-Verlag, 2011. 19, 20 



## A. SIMON AND SPECK ON 64-BIT PROCESSORS

Interoperability is an important issue: We can envision scenarios where many constrained devices interact with a back-end server, and performance on that machine becomes important. RFID is an example, where low-resource tags communicate with a reader. Although a tag may only talk to a single reader, the reader may be required to interact with a large number of tags over a short time interval. 

Although it was not our primary goal, SIMON and SPECK have exceptional performance on 32- and 64-bit processors. For the remainder of this section, we focus on 64-bit performance. Table A.1 reports the encryption cost for two different C implementations on a single core of a 2.67 GHz Intel Xeon E5640 processor: a straightforward reference implementation with nothing done in parallel, and a high-speed SSE implementation. Both use a pre-expanded key, and so incur no cost for the key expansion. 

<table><tr><td>size</td><td>name</td><td>enc. cost (cycles/byte)</td><td>SSE enc. cost (cycles/byte)</td></tr><tr><td rowspan="2">64/96</td><td>SIMON</td><td>27.3</td><td>4.9</td></tr><tr><td>SPECK</td><td>9.6</td><td>2.3</td></tr><tr><td rowspan="2">64/128</td><td>SIMON</td><td>28.7</td><td>5.2</td></tr><tr><td>SPECK</td><td>10.1</td><td>2.4</td></tr><tr><td rowspan="2">128/128</td><td>SIMON</td><td>21.6</td><td>7.5</td></tr><tr><td>SPECK</td><td>5.7</td><td>2.6</td></tr><tr><td rowspan="2">128/192</td><td>SIMON</td><td>21.6</td><td>7.7</td></tr><tr><td>SPECK</td><td>5.9</td><td>2.7</td></tr><tr><td rowspan="2">128/256</td><td>SIMON</td><td>23.0</td><td>8.0</td></tr><tr><td>SPECK</td><td>6.1</td><td>2.8</td></tr></table>


Table A.1: Encryption costs on a 64-bit processor. The first encryption cost column is for the reference code given below, where a single plaintext is encrypted using precomputed round keys. The SSE encryption costs are for multiple encryptions done in parallel.


The SSE versions of SPECK64 and SPECK128 carried out sixteen and eight parallel encryptions, respectively. The SSE versions of SIMON64 and SIMON128 were bit-sliced, each performing 128 parallel encryptions. The cost to transpose data for SIMON was not included in the costs reported in Table A.1. 

In each case, our code was compiled using GCC version 4.5.1 with either the -03 flag set or the -01 flag set, whichever resulted in faster code (except for the SSE versions of SIMON 128, which performed significantly better when compiled with GCC version 4.1.2 using the -01 flag). 

For SIMON128/128 and SPECK128/128, we used the C code shown below as the basis of our reference implementations. The plaintext and ciphertext are stored in 2-dimensional arrays pt[] and ct[] of type u64. The (precomputed) round keys, also of type u64, are stored in the array k[]. The _lrotl function is provided by x86intrin.h, which needs to be included. 

```c
#define LCS _lrotl //left circular shift
#define u64 unsigned long long
#define f(x) ((LCS(x,1) & LCS(x,8)) ^ LCS(x,2))
#define R2(x,y,k1,k2) (y^=f(x), y^=k1, x^=f(y), x^=k2)

void Simon128Encrypt(u64 pt[], u64 ct[], u64 k[])
{
    u64 i;

    ct[0]=pt[0]; ct[1]=pt[1];
    for(i=0; i<68; i+=2) R2(ct[1], ct[0], k[i], k[i+1]);
}
______ SIMON 128/128 encryption ____ 
```

```c
#define LCS _lrotl //left circular shift
#define RCS _lrotr //right circular shift
#define u64 unsigned long long
#define R(x,y,k) (x=RCS(x,8), x+=y, x^=k, y=LCS(y,3), y^=x)

void Speck128Encrypt(u64 pt[], u64 ct[], u64 k[])
{
    u64 i;

    ct[0]=pt[0]; ct[1]=pt[1];
    for(i=0; i<32; i++) R(ct[1], ct[0], k[i]);
}
____ SPECK128/128 encryption 
```

SPECK128/128 encryption can be coded with on-the-fly round key generation in a very concise manner. As expected, this reduces encryption efficiency. The C routine below, in which we denote the key by $K=(K[1], K[0])$ , encrypts at a rate of 9.3 cycles/byte (or 8.0 cycles/byte if fully unrolled). 

```c
#define LCS _lrotl //left circular shift
#define RCS _lrotr //right circular shift
#define u64 unsigned long long
#define R(x,y,k) (x=RCS(x,8), x+=y, x^=k, y=LCS(y,3), y^=x)

void Speck128ExpandKeyAndEncrypt(u64 pt[], u64 ct[], u64 K[])
{
    u64 i,B=K[1],A=K[0];

    ct[0]=pt[0]; ct[1]=pt[1];
    for(i=0; i<32; i++) {R(ct[1], ct[0], A); R(B, A, i);}
}
____ SPECK128/128 encryption and key expansion 
```

For comparison, we implemented the lightweight block cipher TEA on the same processor (using the C code found in [WN95]). TEA has a trivial key schedule, so there is no additional cost associated with key expansion. Nevertheless, the resulting implementation has an encryption cost of 51.7 cycles/byte. 

## B. SIMON TEST VECTORS

## SIMON 32/64

Key: 1918 1110 0908 0100
Plaintext: 6565 6877
Ciphertext: c69b e9bb 

## SIMON 48/72

Key: 121110 0a0908 020100
Plaintext: 612067 6e696c
Ciphertext: dae5ac 292cac 

## SIMON 48/96

Key: 1a1918 121110 0a0908 020100
Plaintext: 726963 20646e
Ciphertext: 6e06a5 acf156 

## SIMON 64/96

Key: 13121110 0b0a0908 03020100
Plaintext: 6f722067 6e696c63
Ciphertext: 5ca2e27f 111a8fc8 

## SIMON 64/128

Key: 1b1a1918 13121110 0b0a0908 03020100
Plaintext: 656b696c 20646e75
Ciphertext: 44c8fc20 b9dfa07a 

## SIMON 96/96

Key: 0d0c0b0a0908 050403020100
Plaintext: 2072616c6c69 702065687420
Ciphertext: 602807a462b4 69063d8ff082 

## SIMON 96/144

Key: 151413121110 0d0c0b0a0908 050403020100
Plaintext: 746168742074 73756420666f
Ciphertext: ecad1c6c451e 3f59c5db1ae9 

## SIMON 128/128

Key: 0f0e0d0c0b0a0908 0706050403020100
Plaintext: 6373656420737265 6c6c657661727420
Ciphertext: 49681b1e1e54fe3f 65aa832af84e0bbc 

## SIMON 128/192

Key: 1716151413121110 0f0e0d0c0b0a0908 0706050403020100
Plaintext: 206572656874206e 6568772065626972
Ciphertext: c4ac61effcdc0d4f 6c9c8d6e2597b85b 

## SIMON 128/256

Key: 1f1e1d1c1b1a1918 1716151413121110 0f0e0d0c0b0a0908 0706050403020100
Plaintext: 74206e69206d6f6f 6d69732061207369
Ciphertext: 8d2b5579afc8a3a0 3bf72a87efe7b868 

## C. SPECK TEST VECTORS

## SPECK 32/64

Key: 1918 1110 0908 0100
Plaintext: 6574 694c
Ciphertext: a868 42f2 

## SPECK 48/72

Key: 121110 0a0908 020100
Plaintext: 20796c 6c6172
Ciphertext: c049a5 385adc 

## SPECK 48/96

Key: 1a1918 121110 0a0908 020100
Plaintext: 6d2073 696874
Ciphertext: 735e10 b6445d 

## SPECK 64/96

Key: 13121110 0b0a0908 03020100
Plaintext: 74614620 736e6165
Ciphertext: 9f7952ec 4175946c 

## SPECK 64/128

Key: 1b1a1918 13121110 0b0a0908 03020100
Plaintext: 3b726574 7475432d
Ciphertext: 8c6fa548 454e028b 

## SPECK 96/96

Key: 0d0c0b0a0908 050403020100
Plaintext: 65776f68202c 656761737520
Ciphertext: 9e4d09ab7178 62bdde8f79aa 

## SPECK 96/144

Key: 151413121110 0d0c0b0a0908 050403020100
Plaintext: 656d6974206e 69202c726576
Ciphertext: 2bf31072228a 7ae440252ee6 

## SPECK 128/128

Key: 0f0e0d0c0b0a0908 0706050403020100
Plaintext: 6c61766975716520 7469206564616d20
Ciphertext: a65d985179783265 7860fedf5c570d18 

## SPECK 128/192

Key: 1716151413121110 0f0e0d0c0b0a0908 0706050403020100
Plaintext: 7261482066656968 43206f7420746e65
Ciphertext: 1be4cf3a13135566 f9bc185de03c1886 

## SPECK 128/256

Key: 1f1e1d1c1b1a1918 1716151413121110 0f0e0d0c0b0a0908 0706050403020100
Plaintext: 65736f6874206e49 202e72656e6f6f70
Ciphertext: 4109010405c0f53e 4eeeb48d9c188f43 