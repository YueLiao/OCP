# Midori: A Block Cipher for Low Energy (Extended Version)

Subhadeep Banik<sup>1</sup>, Andrey Bogdanov<sup>1</sup>, Takanori Isobe<sup>2</sup>, Kyoji Shibutani<sup>2</sup>, Harunaga Hiwatari<sup>2</sup>, Toru Akishita<sup>2</sup>, and Francesco Regazzoni<sup>3</sup> 

<sup>1</sup> Technical University of Denmark, Denmark. {subb,anbog}@dtu.dk 

<sup>2</sup> Sony Corporation, Japan. {Takanori.Isobe,Kyoji.Shibutani,Harunaga. Hiwatari,Toru.Akishita}@jp.sony.com 

<sup>3</sup> University of Lugano, Switzerland. regazzoni@alari.ch 

Abstract. In the past few years, lightweight cryptography has become a popular research discipline with a number of ciphers and hash functions proposed. The designers’ focus has been predominantly to minimize the hardware area, while other goals such as low latency have been addressed rather recently only. However, the optimization goal of low energy for block cipher design has not been explicitly addressed so far. At the same time, it is a crucial measure of goodness for an algorithm. Indeed, a cipher optimized with respect to energy has wide applications, especially in constrained environments running on a tight power/energy budget such as medical implants. 

This paper presents the block cipher Midori <sup>4</sup> that is optimized with respect to the energy consumed by the circuit per bit in encryption or decryption operation. We deliberate on the design choices that lead to low energy consumption in an electrical circuit, and try to optimize each component of the circuit as well as its entire architecture for energy. An added motivation is to make both encryption and decryption functionalities available by small tweak in the circuit that would not incur significant area or energy overheads. We propose two energy-eficient block ciphers Midori128 and Midori64 with block sizes equal to 128 and 64 bits respectively. These ciphers have the added property that a circuit that provides both the functionalities of encryption and decryption can be designed with very little overhead in terms of area and energy. We compare our results with other ciphers with similar characteristics: it was found that the energy consumptions of Midori64 and Midori128 are by far better when compared ciphers like PRINCE and NOEKEON. 

Keywords: AES, lightweight block cipher, low energy circuits 

## 1 Introduction

The field of lightweight cryptography has gone into overdrive as evident from the number of cipher proposals that have emerged in the past few years, like 

CLEFIA [33], KATAN [14], KLEIN [19], LED [20], PRESENT [12], Piccolo [32], PRINCE [13], SIMON/SPECK [6] to name a few. However, the Advanced Encryption Standard (AES) [17] still remains the de-facto standard when it comes to practical lightweight encryption. The past few years have seen several low-power/area architectures for AES being reported in literature [28,31,18]. However, there has been little work that goes on to determine the design choices that lead to the most energy-eficient architecture. There are many parameters that contribute to the eficiency of a given lightweight design, with area, power, throughput and energy being the foremost among them. Power and energy, are correlated parameters, as energy is essentially the time integral of power, and power is equivalent to the energy consumed per unit time or simply the rate of energy consumption. Energy consumption, thus, is a measure of the total work done by voltage source during the execution of an operation. Hence, in many ways, energy rather than power may be a more relevant parameter to measure the eficiency of a design. Serial architectures of any block cipher that reduce the width of the datapath and reuse components, have a smaller power footprint than round based implementations in which the data path is equal to the block length of the cipher. However, serial implementations usually have high latency, that is, they take much longer to compute the result of an encryption operation than their round based counterparts, and as a result may end up consuming more energy. Therefore, there is no guarantee that low power architectures would necessarily lead to low energy architectures and vice versa. 

In [22,5], an evaluation of several lightweight block ciphers with respect to various hardware performance metrics, with a particular focus on the energy cost was done. A formal model for energy consumption in any r-round unrolled block cipher architecture was proposed in [3]. However these papers do not specifically outline design choices that lead to energy-eficient designs. 

## 1.1 Our contributions

In this paper, we at first try to identify design choices that are energy-eficient and the related tradeofs that are involved as a result of it. We throw some light at the design considerations that govern low energy circuits, and look at several factors like clock frequency, architecture, loop unrolling and lay down some general thumb rules that help in optimizing for energy. Then, we choose components specifically tailored to meet the requirements of low energy design. In particular, we develp energy-eficient linear layers and non-linear layers. 

We use 4 4 almost MDS binary matrices which are more eficient than 4 4 MDS matrices in the terms of area and signal-delay. Note that the branch numbers (the smallest nonzero sum of active inputs and outputs of the matrix) of MDS and almost MDS matrices areare 5 and 4, respectively. However, due to a smaller branch number, ciphers employing almost MDS matrices are likely to require the more number of rounds to guarantee its security against several attacks. To address this issue, we propose optimal cell-permutation layers which are aimed at improving difusion speed and increasing the numbers of active 

S-boxes in each round with low implementation overheads. Our optimal cellpermutations drastically improve the minimum number of diferentially/linearly active S-boxes in each round, and achieve faster difusion compared to ShiftRowtype permutation. We construct a lightweight and small-delay 4-bit S-box by focusing on the dependency of the computation in S-boxes. The signal delay in our S-boxes is 1.5 times and twice faster than those of PRINCE and PRESENT, respectively. Since the S-box layer is one of the most critical and expensive operations of the cipher, our new S-boxes suficiently contribute to low energy consumptions. 

Combining those new constructions, we design a family of low energy block ciphers Midori which is composed of two variants: Midori64 and Midori128. These provide the functionality for both encryption and decryption with minimal area and energy overhead. The two variants support a 128-bit secret key and a 64/128- bit block, respectively. Security wise, Midori64 and Midori128 do not claim related, known and chosen-key security as it is not relevant in our target application. Using the STM 90nm standard cell library, both these ciphers consume less than 1.89 pJ/bit encrypted, which is by far better when compared ciphers like PRINCE and NOEKEON. These ciphers are particularly useful for applications that run on tight energy budget, e.g. active RFID tags, sensor nodes, medical implants and battery operated portable devices. 

## 1.2 Organization of the Paper

In Section 2, we look at some design considerations that help to minimize energy consumption in block cipher circuits. In Section 3, we outline the algorithmic specifications of the Midori128 and Midori64 ciphers. In Section 4, we explain our design decisions vis-a-vis the observations of Section 2. In Section 5, we outline the security analysis of the ciphers. Section 6 contains implementation results of our cipher in hardware using the standard cell library of the STM 90nm logic process. Section 7 concludes the paper. 

## 2 Design Considerations for Low Energy

For any given block cipher, three factors are likely to play a dominant role in determining the quantity of energy dissipated in the circuit: 

(a) Frequency of the Clock used to drive the circuit, 

(b) Architecture of the individual components, 

(c) Unrolling round functions in the circuit. 

We will try to understand the significance of each of these parameters in the context of energy consumption. Let us start with clock frequency. Two components characterize the amount of energy dissipated in a CMOS circuit : 

– Dynamic dissipation due to the charging and discharging of load capacitances and the short-circuit current, 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-13/7a7c4e6c-6b0d-4dd7-8818-5ac0725cd68b/665b53ba6fda3d05055f19124cb64978bc65dd34bc05b14116086f475a414b7f.jpg)



Fig. 1: S-boxes placed sequentially


– Static dissipation due to leakage current and other current drawn continuously from the power supply. 

The total energy dissipation for a CMOS gate can be written as 

$$
E _ {g a t e} = E _ {l o a d} + E _ {s c} + E _ {l e a k a g e}
$$

The quantity $E _ { l o a d }$ is the energy dissipated for charging and discharging the capacitive load $C _ { L }$ of a gate when output transitions occur. The energy dissipated per $0  1 / 1  0$ transition is given as 

$$
E = \int_ {0} ^ {t} v i d t = \int_ {0} ^ {t} v C _ {L} \frac {d v}{d t} d t = C _ {L} \int_ {0} ^ {V _ {D D}} v d v = \frac {1}{2} C _ {L} V _ {D D} ^ {2}.
$$

The energy due to the short-circuit current, $E _ { s c }$ is dissipated in a CMOS gate, when during a transition both the n and the p-transistors are on for a short period of time. The energy due to leakage currents $E _ { l e a k a g e }$ is rather small, and is mainly caused due to the sub-threshold leakage current, which is the drain-source current in a CMOS gate when the transistor is OFF. This figure is becoming increasingly important as the technology is scaling down making the sub-threshold leakage more significant. However as pointed out in [3,22], the efect of the leakage energy at high clock frequencies is minimal. As such, energy becomes a metric which is a measure of the total switching activity of a circuit during the process. For suficiently high frequencies, the energy consumption required to compute an encryption/decryption operation is essentially independent of frequency of operation. In our experiments, for circuits implemented using the standard cell library based on the STM 90nm low leakage process, at frequencies higher than 1 MHz, leakage energy is usually less than 1% of the the total energy dissipated in the circuit. 

To understand the significance of the other parameters we performed the following experiments. Consider a case in which two Rijndael S-boxes are placed one after the other in a circuit as shown in Fig. 1. The signals to the input of the first S-box, the second S-box, and the output of the 2nd S-box are named S1xD, S2xD and S3xD respectively. Note that, analyzing this situation is particularly useful for understanding the energy consumption trends of unrolled designs where logic blocks are placed sequentially one after the other. 

Let us assume that the signal S1xD comes from an 8-bit register, so that it “cleanly” switches between successive byte values, i.e. all the bits of S1xD make logic transitions at the same point of time which is usually the rising clock edge for synchronous circuits. The signal S2xD will switch between various values in a given time interval $0  \tau _ { d } .$ before settling down to a stable value. The value $\tau _ { d }$ which is the delay experienced by the signal S1xD usually depends on the cell library and the architecture adopted to implement the S-boxes. Another parameter dependent on the logic process and architecture of the S-box is the switching activity of S2xD which can be informally defined as the number of logic transitions made by this signal in the period $0  \tau _ { d }$ 

<table><tr><td colspan="5">Total Time Range: 199742 - 204426 Page 1 of 1</td></tr><tr><td>#</td><td>Desig.</td><td>Signal</td><td>Value</td><td>Time: 199742 - 204426 X 1PS (C1: 2017812REF)</td></tr><tr><td>SG</td><td></td><td>Group 1</td><td></td><td>200000 201000 202000 203000 204000</td></tr><tr><td>001</td><td>Sim</td><td>S1xD [7:0]</td><td>8&#x27;hbb</td><td>70 bb</td></tr><tr><td>002</td><td>Sim</td><td>S2xD [7:0]</td><td>8&#x27;hea</td><td>51 ea</td></tr><tr><td>003</td><td>Sim</td><td>S3xD [7:0]</td><td>8&#x27;h87</td><td>d1 6d be 87</td></tr></table>


Fig. 2: The signals S1xD, S2xD, S3xD


The second S-box $S _ { 2 } .$ , sees this signal S2xD, which is switching between various values in the time interval $0  \tau _ { d }$ . Therefore, the switching activity of $S _ { 2 }$ is actually at least double that of $S _ { 1 }$ , as it would continue switching for another $\tau _ { d }$ before producing a stable signal. Figure 2 provides an example in which, the three signals for the pair of Rijndael S-boxes (implemented using the Canright [15] architecture in the standard cell library of the STM 90nm logic process, at 10 MHz) are shown. The synthesis for each S-box was done separately, so that the synthesis tool would not group together gates from the first and the second S-box in order to save area. Since the energy consumption of a logic block depends on the switching activity of all its nodes, the S-box $S _ { 2 }$ should naturally consume more energy than $S _ { 1 }$ . Again the exact energy consumed by $S _ { 2 }$ relative to $S _ { 1 }$ depends on factors like 

(a) the logic process and hence the value of $\tau _ { d } ,$ 

(b) the architecture of the S-box and hence the amount of “extra” switching experienced by $S _ { 2 }$ and 

(c) the algebraic structure of the S-box, i.e. its component Boolean functions. 

The extra switching activity would be proportional to the average number of gates that undergo a $0  1 / 1  0$ transition during the period $\tau _ { d }  2 \tau _ { d }$ (the average is typically taken over all possible transitions of the signal $\mathrm { S 1 x D } )$ Similarly if a third S-box $S _ { 3 }$ were placed after $S _ { 2 }$ , then too it would experience an increase in switching activity relative to $S _ { 2 }$ that would depend on the average number of gates switched in the period $2 \tau _ { d } \to 3 \tau _ { d }$ . The increase in switching activity of $S _ { 3 }$ over $S _ { 2 }$ is likely to be roughly the same as that of $S _ { 2 }$ over $S _ { 1 }$ 2 since the number of gates in $S _ { 2 }$ that switch in $\tau _ { d }  2 \tau _ { d }$ and those in $S _ { 3 }$ between $2 \tau _ { d } \to 3 \tau _ { d }$ when averaged over $\binom { 2 5 6 } { 2 }$ transitions of S1xD, is likely to be same. And so if it so happens that $S _ { 1 } , S _ { 2 }$ and $S _ { 3 }$ drive the same amount of capacitive load, the diference between the energy consumed between $S _ { 2 }$ and $S _ { 1 }$ is likely to be the same as between $S _ { 3 }$ and $S _ { 2 }$ 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-13/7a7c4e6c-6b0d-4dd7-8818-5ac0725cd68b/55318956fd54ac0638cb12410835e44c820b0f1e4ec8b3fd1b67a4be4a2b54db.jpg)



Fig. 3: Energy per cycle $E _ { i }$ in $i ^ { t h } \mathrm { ~ S - ~ }$ box $S _ { i }$


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-13/7a7c4e6c-6b0d-4dd7-8818-5ac0725cd68b/bc310f0ad38f297721e1264b2c57bda0ce6e4bc988fa2f7e9f64ff9e8550d398.jpg)



Fig. 4: Energy $\varOmega _ { n }$ required to compute $S ^ { 1 0 } ( x )$ using n S-boxes


Taking these ideas forward, if we connect a series of n S-boxes sequentially, the energy consumed by each S-box in a given period of time is likely to be more than the previous S-box, as the switching activity of the S-boxes are likely to increase from the first to the last. We tested three diferent architectures for the Rijndael S-box. The first is the Canright [15] architecture which is acknowledged to be smallest known implementation in terms of gate area. The second is the Look-up Table (LUT) based architecture as synthesized by the Synopsys Design Compiler. The LUT architecture, while larger than the Canright architecture in terms of area, is much faster in terms of signal delay from the input to output port. The third is a Decoder-Switch-Encoder (DSE) based architecture [8], which is optimal in terms of power/energy consumption. Over the years there has been much research on low power Rijndael S-boxes [29,36], but the DSE based architecture is widely believed to be most power/energy-eficient on account of its unique architecture. The 8-bit input is first decoded to a set of 256 wires. The S-box functionality is achieved by a shufling of wires after which the output is produced by an encoding of the 256 shufled wires (i.e. the inverse of the decoding process). The entire circuit can be constructed by AND/NAND gates, which have very low switching probability and since the S-box functionality is provided by wire shufling, all 8-bit S-boxes can be constructed in this manner. The architecture ofers very low switching per change of input bit: a maximum of 25% of the gates switch when one of the input bits is flipped. 

We connected 10 instances of the S-box constructed using the Canright architecture (using the standard cell library of the STM 90nm logic process) sequentially and used the Synopsys Power Compiler to estimate the energy consumed per clock cycle $E _ { i }$ in each of the successive S-boxes $S _ { i }$ at a clock frequency of 10 MHz. We repeated the same experiment for the LUT and DSE based S-boxes. The results can be seen in Fig. 3. It can be seen that the successive instances of the LUT based S-box which has a delay of around 2.1 ns consumes much less energy as compared to the Canright S-box which has a delay of around 2.9 ns. In both the LUT and Canright architectures, the switching activity in the circuit is roughly proportional to the signal delay across the input and output ports. This is however not the case for DSE S-box, which although has a delay of around 2.3 ns, experiences much lower increase in successive values of $E _ { i }$ because the total switching activity in the delay period is much lower. 

The above analysis is particularly relevant due to two reasons. The first pertains to the structure of especially SPN based ciphers, in which each round typically consists of a substitution, a linear layer and a key addition placed sequentially. A substitution layer with low switching activity and signal delay ensures that the linear layer consumes less energy. Similarly a linear layer with similar characteristics ensures that any circuit placed after it consumes less energy. The second pertains to the consideration of round unrolled circuits. An r-round unrolled circuit for a block cipher is one in which, the circuit computes the results of r successive round functions in a single clock cycle. So if the block cipher specification calls for N executions of the round function, an r-round unrolled circuit will compute the result of the encryption operation in $\left\lceil { \frac { N } { r } } \right\rceil$ cycles. An r-round unrolled architecture is constructed by placing the circuits for r round functions sequentially, followed by a register. The above analysis suggests that any multiple round unrolled circuit is unlikely to be eficient in terms of energy consumption. In the above example, using the LUT based S-box, computing the result of two S-box operations $( \mathrm { i . e . } \ S ( S ( x ) ) )$ over 2 cycles costs $2 * 1 . 8 8 = 3 . 7 6$ $p J .$ Computing the same over one cycle by sequential placement of 2 S-boxes will cost $1 . 8 8 + 3 . 9 1 \ : = \ : 5 . 7 9 \ : p J$ . Similarly computing three S-box operations over three cycles takes 5.64 pJ, whereas the same over one cycle would take $1 . 8 8 + 3 . 9 1 + 6 . 4 0 = 1 2 . 3 9 p J$ . Figure 4 shows the cumulative energy cost $\varOmega _ { n }$ of computing $S ^ { 1 0 } ( x )$ using a sequence of n S-boxes (i.e. in $\textstyle { \frac { 1 0 } { n } }$ cycles), for diferent values of n. It can be seen that, irrespective of the architecture of the S-box, the energy consumption is optimal for $n = 1$ , i.e. computing the operation over 10 cycles using a single S-box, even if this involves updating the register 10 times in the process. 

## 2.1 M-S vs S-M based round functions

An interesting analysis would be to consider circuits in which the linear layer (i.e. the MixColumn logic) is placed before the substitution layer (see Figure 5). We will denote this configuration as M-S based round function, as opposed to S-M based functions in which the substitution layer precedes the linear layer. The block cipher Noekeon is an example of an M-S configuration, whereas Prince uses both S-M and M-S based functions in diferent rounds. To put things in perspective, we did the energy evaluation for the M-S and S-M configurations for AES (with the DSE architecture for S-box), Prince and Noekeon. The results are given in Table 1. The results suggest that there is not a very significant diference in M-S and S-M configurations, any advantage gained by one configuration over the other would depend on the respective designs. However our experiments suggest that placing the logic block with larger signal delay in the later part of the circuit would be more energy eficient. For example, in AES the substitution layer constitutes a bulk of the critical path, for which the M-S configuration is more eficient. The Noekeon linear layer has nine levels of logic and hence a larger delay, than the Substitution layer which uses 4-bit S-boxes. For this cipher, the S-M configuration is found to be slightly better. For a cipher like Prince, in which both the linear layer and the substitution layer have very little signal delays the result of the S-M and M-S configurations are almost equally energy eficient. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-13/7a7c4e6c-6b0d-4dd7-8818-5ac0725cd68b/622970c33b1299130be7fefd222091e8d6f9b0765bbfab2044c10c65fd7071bb.jpg)



Fig. 5: The M-S and S-M architectures


<table><tr><td rowspan="2">Design</td><td rowspan="2">Delay in M (ns)</td><td rowspan="2">Delay in S (ns)</td><td colspan="2">Energy per cycle (pJ)</td></tr><tr><td>M-S</td><td>S-M</td></tr><tr><td>AES</td><td>0.56</td><td>2.25</td><td>12.09</td><td>14.00</td></tr><tr><td>Noekeon</td><td>1.56</td><td>0.38</td><td>12.37</td><td>11.88</td></tr><tr><td>Prince</td><td>0.31</td><td>0.36</td><td>2.30</td><td>2.18</td></tr></table>


Table 1: A comparison of Energy per cycle of M-S/S-M configurations


## 2.2 S-box: 4-bit vs 8-bit

In light of the above analysis, it is clear that a design using a 4-bit S-box is more eficient in terms of energy consumed per cycle than a design using an 8-bit S-box. This is primarily due to the fact that a 4-bit S-box will typically have a lower signal delay as compared to an 8-bit S-box. However 8-bit S-boxes ofer higher non-linearity and lower values of the DP/LP co-eficient, and so in order to sustain similar security margins, a design using a 4-bit S-box will typically need more executions of the round function. To put things, in perspective we performed the energy evaluation of the circuit of the SPN round function (with blocksize equal to 128 bits) in which we experimented with two diferent substitution layers, one having sixteen 8-bit S-boxes and the other having thirty two 4-bit S-boxes. The Rijndael MixColumn was used in both cases, and the STM 90nm cell library was used to synthesize the circuits. For this purpose four diferent 8-bit S-boxes were chosen. Apart from the LUT and DSE based Rijndael S-boxes, we chose the S-boxes used in mCrypton [25] and Whirlpool [4]. Unlike AES, these S-boxes can be functionally defined in terms of smaller 4-bit S-boxes, and so can be implemented eficiently in hardware. Additionally we chose three 4-bit S-boxes: the generic DSE based S-box (note that since the S-box functionality is provided by a wire shufle, all DSE S-boxes will have same energy consumption), and the S-boxes used in PRINCE [13] and PRESENT [12]. 


Table 2: A comparison of energy per cycle for round functions constructed with (A) 16 8-bit S-boxes, (B) 32 4-bit S-boxes.


<table><tr><td></td><td>S-box</td><td>Delay in S (ns)</td><td>Energy per cycle (pJ)</td></tr><tr><td rowspan="4">A</td><td>DSE (8-bit)</td><td>2.25</td><td>14.00</td></tr><tr><td>Rijndael(LUT)</td><td>2.10</td><td>38.88</td></tr><tr><td>mCrypton</td><td>1.59</td><td>13.20</td></tr><tr><td>Whirlpool</td><td>1.33</td><td>16.38</td></tr><tr><td rowspan="3">B</td><td>DSE (4-bit)</td><td>0.81</td><td>7.92</td></tr><tr><td>PRINCE</td><td>0.36</td><td>4.87</td></tr><tr><td>PRESENT</td><td>0.45</td><td>6.18</td></tr></table>

Table 2 reports the energy per cycle figures at a frequency of 10 MHz. It can be seen that the DSE architecture is not as efective as energy saving measure for 4-bit S-boxes. It is also interesting to note that from the point of view of energy 4-bit S-boxes out performs their 8-bit counterparts by a ratio of around 2:1. Thus, the use of 4-bit S-boxes seems to be an eficient configuration even if the number of rounds in the encryption algorithm has to be increased in order to maintain security margins. 

## 2.3 Feistel vs SPN and Complex vs Simple Round Function

As far as designing lightweight ciphers is concerned, both SPN and Feistel architectures have their respective advantages and disadvantages. Feistel structures (e.g. TWINE [34], Piccolo [32], SIMON [6]) usually apply a round function to only one half of the state and as such structures can be implemented in hardware with low average power. Also, implementing the inverse of Feistel constructions is not very dificult and hence a circuit that provides functionalities for both encryption and decryption can be designed with minimal overhead. However, given the fact that Feistel structures introduce non-linearity in only one half of the state in every round and hence, to maintain security margins, such constructions usually require more executions of the round functions as compared to SPN structures. As such Feistel, constructions are not suited for low latency implementations. Most SPN constructions, on the other hand, usually apply its transformation function to the entire state and so can be implemented using fewer rounds. In principle, if n rounds of SPN function and m rounds of Feistel function (where m > n) have the same security margin and similar energy expenditure, then using the n round SPN function makes more sense since lesser energy is consumed to update the state and key register for n rounds. A similar argument can be used to resolve the choice between (a) Simple round functions with more rounds (e.g. PRESENT [12]) and (b) Complex round functions with lesser rounds. 

## 2.4 Efect of Key Schedule

Generating separate round keys in each round by means of a key schedule operation can eat into the energy budget as it incurs the added cost of updating the key register in every round. For example using the STM 90nm standard cell library, in AES (with DSE S-box), the key schedule consumes a total of 25% of the total energy consumed. For PRESENT, the key schedule consumes close to 32% of the total energy. So designs meant primarily for low energy consumption, designers should look to avoid the key schedule operation. This would also be eficient in terms of area as it would not be necessary to include a key register in the design. 

## 2.5 Main Conclusion: Low-Energy Design Choices

We can now state some conclusions that will serve as pointers for a good low energy block cipher design. From the point of view of energy, we know that a round based architecture is usually optimal. Thus we concentrate on an eficient round based construction that would with minimal overhead provide both the functionalities of encryption and decryption. A cipher like PRINCE, although provides both encryption/decryption functionalities with minimal tweak in the circuit, does not have an equally energy-eficient round based construction [13], as it needs to accommodate 3 diferent round functions in the same circuit. We have also seen that components with low switching and delay tend to perform better energy wise. So another requirement is choosing components with low area and delay. In this context, it makes sense to choose 4-bit S-boxes over 8-bit S-boxes. We choose SPN architecture over Feistel to minimize the number of rounds in the design. And since providing the functionalities of both encryption and decryption is an added motivation, we try to include components which in addition to having low area/delay, are also involutions. Having such components would minimize any additional overhead required for providing the functionalities of both encryption and decryption. We will now present the specifications for the proposed block cipher and in Section 4 we will explain the design decisions in the context of the observations made in this Section. 

## 3 Specification

Midori is a family of two block ciphers: Midori64 and Midori128. Both ciphers accept 128-bit keys, and have a diferent block size n $( n = 6 4$ for Midori64 and $n = 1 2 8$ for Midori128). The basic parameters of Midori64 and Midori128 are shown in Table 3. 

Midori is a variant of a Substitution Permutation Network (SPN), which consists of the S-layer and the P-layer, and uses the following 4  4 array called 


Table 3: Parameters for Midori64 and Midori128


<table><tr><td></td><td>block size(n)</td><td colspan="2">key size cell size(m)</td><td>number of rounds</td></tr><tr><td>Midori64</td><td>64</td><td>128</td><td>4</td><td>16</td></tr><tr><td>Midori128</td><td>128</td><td>128</td><td>8</td><td>20</td></tr></table>


Table 4: 4-bit bijective S-boxes $\mathsf { S b } _ { 0 }$ and $\mathsf { S b } _ { 1 }$ in hexadecimal form


<table><tr><td><eq>x</eq></td><td>0</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td><td>7</td><td>8</td><td>9</td><td>a</td><td>b</td><td>c</td><td>d</td><td>e</td><td>f</td></tr><tr><td><eq>\text{Sb}_{0}[x]</eq></td><td>c</td><td>a</td><td>d</td><td>3</td><td>e</td><td>b</td><td>f</td><td>7</td><td>8</td><td>9</td><td>1</td><td>5</td><td>0</td><td>2</td><td>4</td><td>6</td></tr><tr><td><eq>\text{Sb}_{1}[x]</eq></td><td>1</td><td>0</td><td>5</td><td>3</td><td>e</td><td>2</td><td>f</td><td>7</td><td>d</td><td>a</td><td>9</td><td>b</td><td>c</td><td>8</td><td>4</td><td>6</td></tr></table>

state as a data expression: 

$$
S = \left[ \begin{array}{l l l l} s _ {0} & s _ {4} & s _ {8} & s _ {1 2} \\ s _ {1} & s _ {5} & s _ {9} & s _ {1 3} \\ s _ {2} & s _ {6} & s _ {1 0} & s _ {1 4} \\ s _ {3} & s _ {7} & s _ {1 1} & s _ {1 5} \end{array} \right],
$$

where the sizes of each cell m are 4 and 8 bits for Midori64 and Midori128, respectively, i.e., $s _ { i } \in \{ 0 , 1 \} ^ { m } , m = 4$ for Midori64 and $m = 8$ for Midori128. A 64-bit or a 128-bit plaintext $P$ is loaded into the state, and the i-th round output state is defined as $S _ { i }$ , namely $S _ { 0 } = P$ 

## 3.1 S-boxes and Matrices

S-box: Midori utilizes two types of bijective 4-bit S-boxes, $\mathsf { S b } _ { 0 }$ and ${ \mathsf { S b } } _ { 1 } ,$ where $\mathsf { S b } _ { 0 } , \mathsf { S b } _ { 1 } : \{ 0 , 1 \} ^ { 4 } \to \{ 0 , 1 \} ^ { 4 }$ (see Table 4). $\mathsf { S b } _ { 0 }$ and $\mathsf { S b } _ { 1 }$ are used in Midori64 and Midori128, respectively. Note that $\mathsf { S b } _ { 0 }$ and $\mathsf { S b } _ { 1 }$ both have the involution property. 

Midori128 utilizes four diferent 8-bit S-boxes $\mathsf { S S b } _ { 0 } , \mathsf { S S b } _ { 1 } , \mathsf { S S b } _ { 2 }$ and ${ \mathsf { S S b } } _ { 3 } ,$ where $\mathsf { S S b } _ { 0 } , \mathsf { S S b } _ { 1 } , \mathsf { S S b } _ { 2 } , \mathsf { S S b } _ { 3 } : \{ 0 , 1 \} ^ { 8 } \to \{ 0 , 1 \} ^ { 8 }$ Mathematically, each SSb consists of input and output bit permutations and two Sb<sub>1</sub>’s as shown in Fig. 6. Each output bit permutation is taken as the inverse of the corresponding input bit permutation to keep the involution property. Let the input bit permutation of each ${ \mathsf { S S b } } _ { i }$ be referred to as ${ \mathsf { p } } _ { i }$ . Let $x _ { [ i ] }$ denote the i-th bit of $x ,$ where x<sub>[0]</sub> is the most significant bit (MSB). Then denoting $\mathsf { p } _ { i } ( x ) = y ^ { ( i ) }$ , we have 

$$
y _ {[ 0, 1, 2, 3, 4, 5, 6, 7 ]} ^ {(0)} = x _ {[ 4, 1, 6, 3, 0, 5, 2, 7 ]}, y _ {[ 0, 1, 2, 3, 4, 5, 6, 7 ]} ^ {(1)} = x _ {[ 1, 6, 7, 0, 5, 2, 3, 4 ]}
$$

$$
y _ {[ 0, 1, 2, 3, 4, 5, 6, 7 ]} ^ {(2)} = x _ {[ 2, 3, 4, 1, 6, 7, 0, 5 ]}, y _ {[ 0, 1, 2, 3, 4, 5, 6, 7 ]} ^ {(3)} = x _ {[ 7, 4, 1, 2, 3, 0, 5, 6 ]}
$$

The output permutation used in each ${ \mathsf { S S b } } _ { i }$ is simply the inverse of the map ${ \mathsf { p } } _ { i } .$ 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-13/7a7c4e6c-6b0d-4dd7-8818-5ac0725cd68b/12393a7ea013b17f8c384aa81c3f37cdab08b88befd74ffe94c5d63878acb7f2.jpg)



Fig. 6: SSb<sub>0</sub>, SSb<sub>1</sub>, SSb<sub>2</sub> and $\mathsf { S S b _ { 3 } }$


Matrix: Midori utilizes an involutive binary matrix M defined as follows: 

$$
M = \left( \begin{array}{c c c c} 0 & 1 & 1 & 1 \\ 1 & 0 & 1 & 1 \\ 1 & 1 & 0 & 1 \\ 1 & 1 & 1 & 0 \end{array} \right).
$$

The matrix M updates four m-bit values $( x _ { 0 } , x _ { 1 } , x _ { 2 } , x _ { 3 } )$ as follows: 

$$
{ } ^ { t } ( x _ { 0 } , x _ { 1 } , x _ { 2 } , x _ { 3 } ) \leftarrow M \cdot { } ^ { t } ( x _ { 0 } , x _ { 1 } , x _ { 2 } , x _ { 3 } ) ,
$$

where the operations between a matrix and a vector are performed over $\operatorname { G F } ( 2 ^ { m } )$ ). 

## 3.2 Round Function

The round function of Midori consists of an S-layer SubCell: $\{ 0 , 1 \} ^ { n } \to \{ 0 , 1 \} ^ { n }$ 2 a P-layer ShufleCell and MixColumn: $\{ 0 , 1 \} ^ { n } \to \{ 0 , 1 \} ^ { n }$ and a key-addition layer KeyAdd: $\{ 0 , 1 \} ^ { n } \times \{ 0 , 1 \} ^ { n } \to \{ 0 , 1 \} ^ { n }$ . Each layer updates an n-bit state $S$ as follows. 

SubCell $( S ) \colon \mathsf { S b } _ { 0 }$ and ${ \mathsf { S S b } } _ { i }$ are applied to every 4 and 8-bit cell of the state $S$ of Midori64 and Midori128 in parallel, respectively. Namely, $s _ { i } \gets \mathsf { S b } _ { 0 } [ s _ { i } ]$ for Midori64 and $s _ { i } \gets \mathsf { S S b } _ { ( i \mod 4 ) } \big [ s _ { i } \big ]$ for Midori128, where $0 \leq i \leq 1 5$ ShufleCell (S): Each cell of the state is permuted as follows: 

$$
\left(s _ {0}, s _ {1}, \dots , s _ {1 5}\right) \leftarrow \left(s _ {0}, s _ {1 0}, s _ {5}, s _ {1 5}, s _ {1 4}, s _ {4}, s _ {1 1}, s _ {1}, s _ {9}, s _ {3}, s _ {1 2}, s _ {6}, s _ {7}, s _ {1 3}, s _ {2}, s _ {8}\right).
$$

MixColumn (S): M is applied to every 4m-bit column of the state $S , { \mathrm { i . e . } }$ 

$$
{ } ^ { t } ( s _ { i } , s _ { i + 1 } , s _ { i + 2 } , s _ { i + 3 } ) \leftarrow M ^ { t } ( s _ { i } , s _ { i + 1 } , s _ { i + 2 } , s _ { i + 3 } ) \text {~   and~   } i = 0 , 4 , 8 , 1 2 .
$$

KeyAdd(S, RK<sub>i</sub>): The i-th n-bit round key $R K _ { i }$ is XORed to a state $S .$ 

## 3.3 Data Processing Part

The data processing part of Midori for encryption MidoriCo $\mathsf { r e } _ { ( R ) }$ performs as follows: 

$$
\operatorname{MidoriCore} _ {(R)}: \left\{ \begin{array}{l} \{0, 1 \} ^ {1 6 m} \times \{0, 1 \} ^ {1 6 m} \times \{\{0, 1 \} ^ {1 6 m} \} ^ {R - 1} \to \{0, 1 \} ^ {1 6 m} \\ (X, W K, R K _ {0},..., R K _ {R - 2}) \mapsto Y \end{array} \right.
$$

Algorithm MidoriCore $_{(R)}(X, WK, RK_0, ..., RK_{R-2})$ : $S \leftarrow \text{KeyAdd}(X, WK)$ for $i = 0$ to $R - 2$ do $S \leftarrow \text{SubCell}(S)$ $S \leftarrow \text{ShuffleCell}(S)$ $S \leftarrow \text{MixColumn}(S)$ $S \leftarrow \text{KeyAdd}(S, RK_i)$ $S \leftarrow \text{SubCell}(S)$ $Y \leftarrow \text{KeyAdd}(S, WK)$ 

where $R = 1 6$ for Midori64 and $R = 2 0$ for Midori128. Similarly, the inverse data processing part Midori $\mathsf { \bar { c o r e } } _ { ( R ) } ^ { - 1 }$ operates as follows: 

```txt
MidoriCore\(_{(R)}^{-1}:\left\{\begin{array}{l}\{0,1\}^{16m}\times\{0,1\}^{16m}\times\{\{0,1\}^{16m}\}^{R-1}\to\{0,1\}^{16m}\\(Y,WK,RK_{R-2},...,RK_{0})\mapsto X\end{array}\right.\) Algorithm MidoriCore\(_{(R)}^{-1}(Y,WK,RK_{R-2},...,RK_{0})\) : \(S \leftarrow \text{KeyAdd}(Y,WK)\) for \(i=(R-2)\) to 0 do \(S \leftarrow \text{SubCell}(S)\) \(S \leftarrow \text{MixColumn}(S)\) \(S \leftarrow \text{InvShuffleCell}(S)\) \(S \leftarrow \text{KeyAdd}(S,L^{-1}(RK_i))\) \(S \leftarrow \text{SubCell}(S)\) \(X \leftarrow \text{KeyAdd}(S,WK)\) 
```

where $L ^ { - 1 }$ (inverse of the linear layer) denotes the composition of the operations InvShufleCell MixColumn, and InvShufleCell permutes each cell of the state as follows. 

$$
\left(s _ {0}, s _ {1}, \dots , s _ {1 5}\right) \leftarrow \left(s _ {0}, s _ {7}, s _ {1 4}, s _ {9}, s _ {5}, s _ {2}, s _ {1 1}, s _ {1 2}, s _ {1 5}, s _ {8}, s _ {1}, s _ {6}, s _ {1 0}, s _ {1 3}, s _ {4}, s _ {3}\right).
$$

## 3.4 Round Key Generation

For Midori64, a 128-bit secret key K is denoted as two 64-bit keys $K _ { 0 }$ and $K _ { 1 }$ as $K = K _ { 0 } | | K _ { 1 }$ . Then, $W K = K _ { 0 } \oplus K _ { 1 }$ and $R K _ { i } = K _ { ( i }$ mod $_ { 2 ) } \oplus \alpha _ { i }$ , where $0 \leq i \leq 1 4$ . For Midori128, WK = K and $R K _ { i } = K \oplus \beta _ { i }$ , where $0 \leq i \leq 1 8$ . The constants $\beta _ { i }$ are defined in Table 5. It can be seen that the constants are in the form of $4 \times 4$ binary matrices. They are added bitwise to the LSB of every round key byte in Midori128 and round key nibble in Midori64 respectively. Note that $\alpha _ { i } = \beta _ { i }$ for $0 \leq i \leq 1 4$ 

## 3.5 Midori Ciphers

Midori block ciphers are composed of two variants: Midori64 and Midori128 consisting of Midori $\mathsf { \tilde { \Gamma } } _ { \mathsf { O r e } _ { \left( 1 6 \right) } }$ with $m = 4$ and MidoriCore<sub>(20)</sub> with $m = 8$ , respectively. Midori $\mathsf { \tilde { \Gamma } } _ { \mathsf { O r e } _ { \left( 1 6 \right) } }$ is depicted in Fig. 7 as an example. 


Table 5: The Round Constants β<sub>i</sub>


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-13/7a7c4e6c-6b0d-4dd7-8818-5ac0725cd68b/939b38f79cc53d87b0370f61a64babc2bb3cd650c8a7b22ef9d69b1f7fcc6431.jpg)



Fig. 7: Overview of Midori64


## 4 Design Decision

Here, we explain our design decisions vis-a-vis the observations of Section 2. 

## 4.1 Linear Layer

Linear layers of the each variant consist of a cell-permutation (ShufleCell) and four 4 4 matrix operations (MixColumn). Those operations are performed over $G F ( 2 ^ { 4 } )$ and $G F ( 2 ^ { 8 } )$ for the 64 and 128-bit variants, respectively. 

MDS vs Almost MDS. Using the NanGate 45nm open cell library, Table 6 compares three types of $4 \times 4$ matrices, involutive MDS $( M _ { A } )$ , non-involutive MDS $( M _ { B } )$ and involutive almost MDS matrices $( M _ { C } )$ from implementation aspects. These matrices are considered lightweight in each of the three aforementioned criteria [27,32]. 

$$
\boldsymbol {M} _ {A} = \left( \begin{array}{c c c c} 1 & 2 & 6 & 4 \\ 2 & 1 & 4 & 6 \\ 6 & 4 & 1 & 2 \\ 4 & 6 & 2 & 1 \end{array} \right), \boldsymbol {M} _ {B} = \left( \begin{array}{c c c c} 2 & 3 & 1 & 1 \\ 1 & 2 & 3 & 1 \\ 1 & 1 & 2 & 3 \\ 3 & 1 & 1 & 2 \end{array} \right), \boldsymbol {M} _ {C} = \left( \begin{array}{c c c c} 0 & 1 & 1 & 1 \\ 1 & 0 & 1 & 1 \\ 1 & 1 & 0 & 1 \\ 1 & 1 & 1 & 0 \end{array} \right).
$$

From Table 6, $M _ { C }$ is obviously preferable over the others in terms of the gate size and the path delay. In fact, circulant-type almost MDS matrices are adopted in PRINCE [13], PRIDE [1], FIDES [9] and CLOC [21]. Moreover, Khoo et al. showed that, for a 64-bit block size employing the AES-like structure, the combination of 4 4 almost MDS matrices $( M _ { C } )$ with ShiftRow and 16 4-bit S-boxes is the most eficient in both a round-based and a serialized implementation by proposing a new comparison metric FOAM (figure of adversarial merit), which combines the inherent security provided by cryptographic structures and components along with their implementation properties [23]. 


Table 6: Comparison of three matrices


<table><tr><td></td><td><eq>M_A</eq></td><td><eq>M_B</eq></td><td><eq>M_C</eq></td></tr><tr><td>Area [GE]</td><td>108</td><td>104</td><td>48</td></tr><tr><td>Delay [ns]</td><td>0.93</td><td>0.68</td><td>0.37</td></tr><tr><td>Diffusion</td><td>MDS</td><td>MDS</td><td>Almost MDS</td></tr><tr><td>Involution</td><td>yes</td><td>no</td><td>yes</td></tr></table>


Table 7: Comparison of S-boxes


<table><tr><td></td><td>PRESENT</td><td>PRINCE</td><td><eq>Sb_0</eq></td><td><eq>Sb_1</eq></td></tr><tr><td>Area [GE]</td><td>24.33</td><td>16</td><td>13.3</td><td>15.33</td></tr><tr><td>Delay [ns]</td><td>0.47</td><td>0.36</td><td>0.24</td><td>0.32</td></tr><tr><td>Involution</td><td>No</td><td>No</td><td>Yes</td><td>Yes</td></tr></table>

While $M _ { C }$ has eficient implementation properties, its difusion speed is slower and the minimum number of active S-boxes in each round is smaller than those of ciphers employing MDS matrices due to its lower branch number. It has been known that those properties are directly related to the immunity against several attacks including impossible diferential, saturation, diferential and linear attacks. To improve security of the almost MDS with low implementation overheads, we adopt optimal cell-permutation layers which are aimed at improving difusion speed and increasing the number of active S-boxes in each round. The difusion speed is measured by the number of rounds taken to attain full difusion, which is the property that all output cells are afected by all input cells. Importantly, changing cell-permutation patterns generally does not require additional implementation costs in a round-based and an unrolled hardware implementation. 

Approach to Find Optimal Cell-Permutation Layers for Almost MDS. Since it is computationally hard to exhaustively count the minimum number of active S-boxes for all possible permutations $( = \ 1 6 ! \ \approx \ 2 ^ { 4 4 . 2 5 } )$ by Matsui’s search approach [26,10], we take the following two-step approach to reduce the search space. In the fist step, we restrict the cell-permutations to row-based cellpermutations which permute four cells in each row, $\mathrm { e . g . }$ ShiftRow in AES. The number of possible row-based cell-permutations is estimated as $2 ^ { 1 8 . 3 } ~ ( = ( 4 ! ) ^ { 4 } )$ This step is based on the fact that the full difusion property relies on only rowbased property of the cell-permutation. As a result of our searches, we find that a class of row-based cell-permutations achieves full difusion in 3 rounds and its necessary and suficient condition is as follows. 

Condition 1 (3-round full difusion) For a $4 \times 4$ cell-array, after applying a cell-permutation once and twice, each input cell in a column is mapped into a cell in the diferent column. 

From our search, 576 row-based cell-permutations satisfy Condition 1. Interestingly, ShiftRow-type permutation is not included in this class, i.e. it requires 4 rounds for full difusion. 

In the second step, we add a column-based cell-permutation, which permutes four cells in each column, after applying the class of permutations satisfying Condition 1. The target cell permutation consists of the combination of the row-based and column-based permutations. Note that adding a column-based cell-permutation to the row-based permutations satisfying Condition 1 does not afect the full difusion property. The number of all possible cell-permutations of this class is estimated as $2 ^ { 2 7 . 5 1 } ~ ( = ~ 5 7 6 ~ \times ~ ( 4 ! ) ^ { 4 } )$ . Consequently, we find a class of cell-permutation achieving the largest number of active S-boxes in each round and the smallest number of rounds to attain full difusion when satisfying Condition 1 and the following Condition 2 or 3. 

Condition 2 (The number of active S-box) For a $4 \times 4$ cell-array, after applying a cell-permutation twice and twice inversely, each input cell in a column is mapped into a cell in the same row. 

Condition 3 (The number of active S-box) For a $4 \times 4$ cell-array, after applying a cell-permutation once and three times inversely, each input cell in a column is mapped into a cell in the same row. 

The numbers of cell-permutations satisfying Condition 2 and Condition 3 are both 576. We define such 1152 cell-permutation as optimal cell-permutations. Table 8 shows the minimum numbers of diferentially/linearly active S-boxes of the optimal cell-permutations and the ShiftRow-type permutation. Our optimal cell-permutations drastically improve the minimum number of diferentially/linearly active S-boxes in each round while keeping the 3-round full difusion property as shown in Fig. 8. Thus, our optimal permutations achieve security against several attacks such as diferential/linear and impossible attacks in the same number of rounds compared to ShiftRow-type permutation. Midori128 and Midori64 adopt one of optimal cell permutations satisfying both Conditions 1 and 2 as follows. 

$$
\left(s _ {0}, s _ {1},..., s _ {1 5}\right) \leftarrow \left(s _ {0}, s _ {1 0}, s _ {5}, s _ {1 5}, s _ {1 4}, s _ {4}, s _ {1 1}, s _ {1}, s _ {9}, s _ {3}, s _ {1 2}, s _ {6}, s _ {7}, s _ {1 3}, s _ {2}, s _ {8}\right).
$$

Starting from the state $S _ { 0 }$ , each cell of $S _ { 0 }$ is mapped to $S _ { 1 } , S _ { 2 } , S _ { 1 } ^ { - 1 }$ and $S _ { 2 } ^ { - 1 }$ after applying the above cell-permutation once, twice, once inversely and twice inversely, respectively, as follows. 

$$
S _ {0} = \left[ \begin{array}{l l l l} s _ {0} & s _ {4} & s _ {8} & s _ {1 2} \\ s _ {1} & s _ {5} & s _ {9} & s _ {1 3} \\ s _ {2} & s _ {6} & s _ {1 0} & s _ {1 4} \\ s _ {3} & s _ {7} & s _ {1 1} & s _ {1 5} \end{array} \right], S _ {1} = \left[ \begin{array}{l l l l} s _ {0} & s _ {1 4} & s _ {9} & s _ {7} \\ s _ {1 0} & s _ {4} & s _ {3} & s _ {1 3} \\ s _ {5} & s _ {1 1} & s _ {1 2} & s _ {2} \\ s _ {1 5} & s _ {1} & s _ {6} & s _ {8} \end{array} \right], S _ {2} = \left[ \begin{array}{l l l l} s _ {0} & s _ {2} & s _ {3} & s _ {1} \\ s _ {1 2} & s _ {1 4} & s _ {1 5} & s _ {1 3} \\ s _ {4} & s _ {6} & s _ {7} & s _ {5} \\ s _ {8} & s _ {1 0} & s _ {1 1} & s _ {9} \end{array} \right],
$$

$$
S _ {1} ^ {- 1} = \left[ \begin{array}{c c c c} s _ {0} & s _ {5} & s _ {1 5} & s _ {1 0} \\ s _ {7} & s _ {2} & s _ {8} & s _ {1 3} \\ s _ {1 4} & s _ {1 1} & s _ {1} & s _ {4} \\ s _ {9} & s _ {1 2} & s _ {6} & s _ {3} \end{array} \right], S _ {2} ^ {- 1} = \left[ \begin{array}{c c c c} s _ {0} & s _ {2} & s _ {3} & s _ {1} \\ s _ {1 2} & s _ {1 4} & s _ {1 5} & s _ {1 3} \\ s _ {4} & s _ {6} & s _ {7} & s _ {5} \\ s _ {8} & s _ {1 0} & s _ {1 1} & s _ {9} \end{array} \right].
$$


Table 8: The number of minimum number of diferentially/linearly active S-boxes (AS) of Midori64 and Midori128


<table><tr><td>Round Number</td><td>4</td><td>5</td><td>6</td><td>7</td><td>8</td><td>9</td><td>10</td><td>11</td><td>12</td><td>13</td><td>14</td><td>15</td><td>16</td></tr><tr><td>Min. # of AS (Optimal Cell-Permutation)</td><td>16</td><td>23</td><td>30</td><td>35</td><td>38</td><td>41</td><td>50</td><td>57</td><td>62</td><td>67</td><td>72</td><td>75</td><td>84</td></tr><tr><td>Min. # of AS (ShiftRow-type Permutation)</td><td>16</td><td>18</td><td>20</td><td>26</td><td>32</td><td>34</td><td>36</td><td>42</td><td>48</td><td>50</td><td>52</td><td>58</td><td>64</td></tr></table>

From those mappings, it is clear that the relation among $S _ { 2 } ^ { - 1 } , S _ { 0 }$ and $S _ { 2 }$ satisfies Condition 2. Similarly, all of the pairs $( S _ { 2 } ^ { - 1 } , S _ { 1 } ^ { - 1 } ) , ( S _ { 1 } ^ { - 1 } , \mathsf { \bar { S } } _ { 0 } ) , ( S _ { 0 } , S _ { 1 } ) , ( S _ { 1 } , S _ { 2 } )$ satisfy Condition 1. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-13/7a7c4e6c-6b0d-4dd7-8818-5ac0725cd68b/c3fc1325933c627865f890dffc6fa8096430be2daf14b89a165a536dc5e399d0.jpg)



Fig. 8: Comparison of the minimum numbers of diferentially/linearly active $\mathrm { S } -$ boxes (AS)


## 4.2 S-box Layer

According to analysis of Section 2.2, 4-bit S-boxes are usually more eficient than 8-bit S-boxes in terms of energy consumption per cycle. Also, the small path delay and the small gate area lead to low-energy implementation. To optimize S-layer regarding energy consumption, we aim to develop a small-delay and lightweight 4-bit S-box which fulfill the following requirements: (1) the maximal probability of a diferential is $2 ^ { - 2 }$ , (2) the maximal absolute bias of a linear approximation is $2 ^ { - 2 }$ and (3) involution. The requirement (3) enables us to reduce the number of possible S-boxes from $2 ^ { 4 4 . 2 5 } \ \overset { \cdot } { _ { \mathrm { t o } } } \ 2 ^ { 2 5 . 5 }$ 

Approach to Find Small-Delay and Lightweight 4-bit S-box. Our approach starts with a key observation that the path delay is highly related to $t h e$ dependency of the computation. We introduce a metric depth to estimate the path delay of S-boxes. 

Definition 1 (depth): The depth is defined as the sum ofsequential path delays of basic operations AND, OR, NAND, NOR and NOT. 

Example. The depth of the computation of $( x \oplus y ) \cdot z$ is estimated as the sum of path delays of XOR and AND, because $^ { 6 , } \cdot z ^ { 5 }$ operation is feasible only after the computation of $( x \oplus y )$ 2 

In our search, we assume that depths of XOR, AND/OR, NAND/NOR and NOT are weighted as 2, 1.5, 1 and 0.5, respectively, based on the number of the transistors to be sequentially proceeded in the operation. The required gates of NOT, NAND/NOR, AND/OR and XOR/XNOR are estimated as 0.5, 1, 1.5 and 2 [GEs], respectively. We search all S-boxes whose depth is 1, 1.5, 2, . . . , and check whether the S-boxes satisfy our security requirements. As a result, we can find $\mathsf { S b } _ { 0 }$ (see Table 4) whose depth and gate size are the lowest and the smallest ones in our search. $\mathsf { S b } _ { 0 }$ can be expressed as follows, where inputs and outputs are defined as $\{ a , b , c , d \}$ and $\{ a ^ { \prime } , \bar { b ^ { \prime } } , c ^ { \prime } , d ^ { \prime } \}$ , and a and $a ^ { \prime }$ are the most significant bits. 

$$
\begin{array}{l} a ^ {\prime} = \left(\overline {{c}} \text {NAND} (a \text {NAND} b)\right) \text {NAND} (a \text {OR} d) \\ b ^ {\prime} = \left((a \text {NOR} d) \text {NOR} (b \text {AND} c)\right) \text {NAND} ((a \text {AND} c) \text {NAND} d) \\ c ^ {\prime} = (b \text {NAND} d) \text {NAND} ((b \text {NOR} d) \text {OR} a) \\ d ^ {\prime} = \left(a \text {NOR} (b \text {OR} c)\right) \text {NOR} ((a \text {NAND} b) \text {NAND} (c \text {OR} d)) \end{array}
$$

For instance, let us consider the computation of $c ^ { \prime } .$ In this computation, (b NAND d) and (b NOR $d )$ can be done at first. After that, the computation of (b NOR d) OR a is done. Then, the last operation of NAND is executable. Thus, the depth of $c ^ { \prime }$ is estimated as $3 . 5 \ : ( = 1 + 1 . 5 + 1 )$ . The depths of the remaining $a ^ { \prime } , b ^ { \prime }$ and $d ^ { \prime }$ are also estimated as 3.0 or 3.5. 

Considering additional requirement full difusion property, we find $\mathsf { S b } _ { 1 }$ which has the lowest depth and the smallest gate area among 4-bit bijective S-boxes satisfying the requirements (1), (2), (3) and the full difusion property. $\mathsf { S b } _ { 1 }$ is expressed as follows : 

$$
\begin{array}{l} a ^ {\prime} = \left((b \text {   NAND   } c) \text {   NAND   } a\right) \text {   NAND   } \left((a \text {   NOR   } d) \text {   NAND   } b\right) \\ b ^ {\prime} = \left((a \text {   XOR   } c) \text {   NOR   } b\right) \text {   NOR   } \left((b \text {   NAND   } c) \text {   AND   } d\right) \\ c ^ {\prime} = (c \text {   NAND   } d) \text {   NAND   } \left((a \text {   XOR   } b) \text {   NAND   } (b \text {   OR   } d)\right) \\ d ^ {\prime} = \left((a \text {   NAND   } b) \text {   NAND   } c\right) \text {   NAND   } (b \text {   OR   } d) \end{array}
$$

Note that an S-box satisfies the full difusion property if and only if any inputs $\{ a , b , c , d \}$ of the S-box non-linearly afect all outputs $\{ a ^ { \prime } , b ^ { \prime } , c ^ { \prime } , d ^ { \prime } \}$ . This full difusion property enables us to ensure a 3-round property regarding the difusion in Midori128 (we will explain it in the end of this section). 

Evaluation. Table 7 shows the comparison of S-boxes of PRESENT, PRINCE, Sb and $\mathsf { S b } _ { 1 }$ using NanGate 45nm open cell library. The path delay of $\mathsf { S b } _ { 0 }$ is 1.5 times and twice smaller than PRINCE and PRESENT, respectively, and the gate size is also smaller than the others. Those of $\mathsf { S b } _ { 1 }$ are comparable to PRINCE’s S-box. Additionally $\mathsf { S b } _ { 0 }$ and $\mathsf { S b } _ { 1 }$ have the involution property. 


Table 9: Input-output bit relations of each S-box


<table><tr><td></td><td><eq>SSb_0</eq></td><td><eq>SSb_1</eq></td><td><eq>SSb_2</eq></td><td><eq>SSb_3</eq></td></tr><tr><td>A</td><td>(1, 3, 4, 6)</td><td>(0, 1, 6, 7)</td><td>(1, 2, 3, 4)</td><td>(1, 2, 4, 7)</td></tr><tr><td>B</td><td>(0, 2, 5, 7)</td><td>(2, 3, 4, 5)</td><td>(0, 5, 6, 7)</td><td>(0, 3, 5, 6)</td></tr></table>

8-bit S-boxes based on 4-bit S-boxes. From the observation in Section 2.2, we adopt 8-bit S-boxes consisting of two 4-bit S-boxes processed in parallel to minimize the path delay in the round-based implementation. Moreover, in order to avoid having the unfavorable independent property exploited in the full-round attack on KLEIN [24], we add properly-chosen bit-permutations to the begin and the end of 8-bit S-boxes as shown in Fig. 6. As described in Section 3.1, each output bit-permutation is the inverse of the corresponding input bit-permutation to keep the involution property. With a property of our P-layer and those bitpermutations, we claim that no independent property is found after 3 rounds in Midori128. Since $\mathsf { S b } _ { 1 }$ has the full difusion property, any input bit of SSb afects the corresponding 4 bits output as shown in Table 9. For example, in SSb<sub>1</sub>, any of the i-th input bit afects all of the i-th output bits, where $i \in \{ 0 , 1 , 6 , 7 \}$ . We choose bit-permutations for ${ \mathsf { S S b } } _ { 0 }$ , SSb<sub>1</sub>, $\mathsf { S S b _ { 2 } }$ and $\mathsf { S S b _ { 3 } }$ so that those satisfy the following property. 

Property 1 Afected 4-bit positions of outputs of an S-box are included in both of two diferent input groups of the other three S-boxes. 

For example, the group A of $\mathsf { S S b } _ { 1 }$ is $\{ 0 , 1 , 6 , 7 \}$ . Then, those bit positions are found in the groups A and B of ${ \mathsf { S S b } } _ { 0 }$ . This implies that the $\{ 0 , 1 , 6 , 7 \}$ -th input bits of ${ \mathsf { S S b } } _ { 0 }$ afect all 8 bits output. For the matrix operation $^ t ( y _ { 0 } , y _ { 1 } , y _ { 2 } , y _ { 3 } ) $ $M ^ { t } ( x _ { 0 } , x _ { 1 } , x _ { 2 } , x _ { 3 } )$ , we have the following property. 

Property 2 Each input cell afects three cells in the diferent cell positions from the input. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-13/7a7c4e6c-6b0d-4dd7-8818-5ac0725cd68b/7a1bc3d2d7a37d1455185801a571e9f47a68a7d84133330d4ea54bd31a5dd23c.jpg)



Fig. 9: Theorem 1 : 3-round full difusion property


For instance, $x _ { 0 }$ deterministically afects $y _ { 1 } , \ y _ { 2 }$ and $y _ { 3 }$ , and does not afect $y _ { 0 }$ From Properties 1 and 2, we obtain the following theorem. 

Theorem 1 $I n$ Midori128, any input bit nonlinearly afect all 128 bits of the state after 3 rounds. 

Proof. An input bit afects 4 bits in the corresponding cell after the first S-layer due to the full difusion property of $\mathsf { S b } _ { 1 }$ . From Property 2, the afected 4 bits in the cell are difused to three cells in the same column but the diferent cell position after MixColumn. Note that, in the afected three cells, the afected bit positions are the same. From Property 1, in each afected three cells, the afected 4 bits are spreads over all 8 bits in the cell after the 2nd S-layer. Therefore, all bits are afected by any input after 3 rounds (see Fig. 9). □ 

## 4.3 Key Scheduling Function

To save energy, Midori128 does not employ any key scheduling function. The same 128 bit key is used as the whitening key and to generate the round key. To make an eficient circuit for decryption, the i-th round key is defined as $L ^ { - 1 } ( K ) \mathbb { \oplus }$ $L ^ { - 1 } ( \beta _ { 1 8 - i } )$ , where $L ^ { - 1 }$ denotes the inverse of the linear layer. Computation of $L ^ { - 1 } ( K )$ involves a one-time computation with the key at the beginning at the decryption function and so does not consume any significant energy. The round key generation of Midori64, is slightly more complicated, as it involves selecting $K _ { 0 }$ and $K _ { 1 }$ , i.e. the most significant and least significant halves of the 128 bit key in alternate rounds. This can be achieved by the use of a single multiplexer. For eficient decryption, a one-time computation of $L ^ { - 1 } ( K _ { 0 } )$ and $L ^ { - 1 } ( K _ { 1 } )$ can be done at the beginning of the algorithm, which again does not consume any significant energy. 

## 4.4 Round Constant

Both Midori128 and Midori64 use $4 \times 4$ binary matrices as round constants. The constants have been derived from the hexadecimal encoding of the fractional part of π = 3.243f 6a88 85a3    . For example, the 1st, 2nd, 3rd, 4th rows of $\beta _ { 0 }$ when read as a 4-bit binary constant, are the encoding of the hex values 

2,4,3,f respectively. Similarly for the other $\beta _ { i } ^ { \prime } \mathrm { s } .$ . These are added bitwise to the LSB of each round key byte in Midori128 and round key nibble in Midori64. The round constants were chosen in this manner with a view to have an energyeficient decryption circuit. Both $\beta _ { i }$ and $L ^ { - 1 } ( \beta _ { i } )$ are $4 \times 4$ binary matrices, and so in both Midori128 and Midori64, the round constant addition requires a total of 16 XOR gates only. The constants $\beta _ { i }$ and $L ^ { - 1 } ( \beta _ { i } )$ can be stored in lookup tables and filtered accordingly in each round. 

## 5 Security Evaluation

## 5.1 Diferential/Linear Cryptanalysis

The minimum number of diferentially and linearly active S-boxes of each round is estimated as shown in Table 8. The maximum diferential and linear probabilities of $\mathsf { S b } _ { 0 } , \mathsf { S S b } _ { 0 } , \mathsf { S S b } _ { 1 } , \mathsf { S S b } _ { 2 }$ and $\mathsf { S S b _ { 3 } }$ are $2 ^ { - 2 }$ , respectively. Midori64 and Midori128 have more than 32 and 64 active S-boxes after 7 and 13 rounds. Thus, we expect that variants of Midori64 and Midori128 reduced to 7 rounds and 13 rounds do not have any diferential and linear trails whose probabilities are higher than $2 ^ { - 6 4 }$ and $2 ^ { - 1 2 8 }$ 

## 5.2 Boomerang-Type Attack

The boomerang-type attacks first divide the cipher into two sub-ciphers, then find a boomerang quartet with high probability. The probability of constructing a boomerang quartet is denoted as $\hat { p } ^ { 2 } \hat { q } ^ { 2 }$ , where $\begin{array} { r } { \hat { p } = \sqrt { \sum _ { \beta } \mathrm { P r } ^ { 2 } [ \alpha  \beta ] } } \end{array}$ , and α and $\beta$ are input and output diferences for the first sub-cipher, and ˆq for the second sub-cipher. $\hat { p } ^ { 2 }$ is bounded by the maximum diferential trail probability, i.e., $\hat { p } ^ { 2 } \leq \operatorname* { m a x } _ { \beta } \operatorname* { P r } [ \alpha  \beta ]$ , and $\hat { q } ^ { 2 }$ as well. Let $p , q$ be the maximum diferential trail probability for the first and the second sub-ciphers. Then, p, q are bounded by multiplying the minimum number of active S-boxes in each sub-cipher. From Table 8, any combination of two sub-ciphers for consisting of Midori64 and Midori128 after 8 and 14 rounds has at least 32 and 64 active S-boxes in total. Note that these bounds of boomerang attacks are very conservative ones, i.e., it requires unrealistic assumptions of $\hat { p } ^ { 2 } = p$ and $\hat { q } ^ { 2 } = q .$ . Actually, in our active S-box search, we did not find such special events. Thus, we expect that much smaller rounds than 8 and 14 rounds are secure against boomerang-type attacks. 

## 5.3 Impossible Diferential Attacks

Midori64 and Midori128 achieve the 3-round full difusion property. Thus, differences of all cells in a state becomes unknown after SubCell of 4 rounds, i.e., there is no any probability-one (truncated) diferential characteristic. Following the miss-in-the-middle approach, the maximum number of rounds of impossible diferential characteristics is estimated as 7 rounds. 

In order to obtain the lower bound of rounds of impossible diferential, we try to find actual impossible diferential characteristics. We utilize several deterministic properties of four binary matrices M. This approach was also adopted in the security evaluation of FIDES [9]. As a result, we find 6-round impossible diferentials such that if only one active cell is input, 6-rounds of Midori64 and Midori128 never produces only one active cell. We believe that full rounds of Midori64 and Midori128 have suficient number of rounds as the security margin. 

## 5.4 Meet-in-the-Middle Attacks

The 3-round full difusion property with our S-boxes enable us to claim that any inserted key bit of $\{ K _ { 0 } , K _ { 1 } \}$ or K non-linearly afects all bits of the state after 3 rounds in the forward and the backward directions in Midori64 and Midori128, respectively. Thus, the number of rounds used for the partial matching (PM) [2] is upper bounded by $5 ~ ( = ( 3 - 1 ) + ( 3 - 1 ) + 1 )$ ). The condition for the initial structure (IS) [30], also called independent biclique [11], is that key diferential trails in the forward direction and those in the backward direction do not share active non-linear components. For Midori64 and Midori128, since any key diferential afects all 16 S-boxes after at least 4 rounds in the forward and the backward directions, there is no such diferential which shares active S-box in more than 4 rounds. Thus, the number of rounds used for IS is upper bounded by 3. Assuming that the splice-and-cut technique allows an attacker to add more 3 rounds in the worst case, at most 11-round $( 3 \ : + \ : 3 \ : + \ : 5 )$ MitM attack may be feasible. However, because of white keys in the begin and the end and the actual constraint of key orders, we consider that it is dificult to construct 11-round attacks on Midori64 and Midori128. 

## Integral Attacks

Integral attacks are likely to be eficient for the SPN ciphers. We define four states for a set of 2<sup>n</sup> n-bit cell: A: if $\forall i , j \ i \neq j \Leftrightarrow x _ { i } \neq x _ { j }$ , C: if $\forall i , j \ i \ne j$ $\Leftrightarrow x _ { i } = x _ { j } , \mathbf { B } \colon \textstyle \bigoplus _ { i } ^ { 2 ^ { n } - 1 } x _ { i } ,$ and U: Other. In order to estimate upper bounds of integral characteristics, we utilize an evaluation method in [35]. At first, we obtain the required number of rounds $N _ { A }$ for the event of $( \alpha  \beta )$ , α is a state consisting of one A and 15 C, and $\beta$ is a state consisting of all 16 U. After that, we estimate the required number of rounds $N _ { B }$ for the event of $( \alpha ^ { \prime } \to \alpha )$ , where $\alpha ^ { \prime }$ is a state consisting of all 16 A. Then, the round number of integral characteristic is bounded by the sum of $N _ { A }$ and $N _ { B }$ . Since $N _ { A }$ and $N _ { B }$ of Midori64 and Midori128 are 4 and 2, respectively, we expected that the maximum number of round of integral characteristics is 7 rounds To obtain lower bounds, we try to find actual integral characteristics, and obtain a 3.5-round one. By exploiting several techniques used in the integral attack on Prince, we can construct 7-round key recovery attacks based on the distinguisher but more round seems to be infeasible. Thus, full versions of Midori64 and Midori128 are expected to be enough secure against integral attacks. 

## Slide Attacks

Slide attacks exploit self similarities of round functions. Each round of Midori64 and Midori128 accept 16-bit round-dependent constants, and each bit is XORed to all 16 cells. These 16-bit constants make a suficient diference in each round function. Actually, diferences coming from these 16-bit constants are expanded into more than the half of a state after S-layer, and it can eficiently break self similarities to be utilized for slide attacks. Thus, we believe that any slide attacks can not be constructed in Midori64 and Midori128. 

## Reflection Attacks

Reflection attacks rely on the structure of the Prince-like block cipher, described as $F _ { K } ^ { - 1 } \circ M \circ \dot { F } _ { K }$ , and exploits the similarity of $F _ { K }$ and $F _ { K } ^ { - 1 }$ , where $F _ { K }$ and $F _ { K } ^ { - 1 }$ are keyed permutation and its inverse function, respectively, and M is an involutive function, namely $M = M ^ { - 1 }$ . Although Midori64 and Midori128 utilize involutive components of S-boxes and Matrixes, the cell-permutation is not involution. Thus, Midori64 and Midori128 are not expressed as a function of $F _ { K } ^ { - 1 } \circ M \circ F _ { K }$ . In addition, 16-bit round-dependent constants break these similarities of the first half and the inverse of last half functions. Thus, we believe that any reflection attacks is not applicable to Midori64 and Midori128. 

## 6 Implementation

The main design objectives of Midori were first to achieve eficiency in energy consumption and second to provide both the encryption and decryption (ED) functionalities with minimal overhead. In this context, it is essential to have a round based design optimal in terms of energy consumption, since unrolled designs are unlikely to be eficient in terms of energy consumption. The S-box and the MixColumn layer were specifically chosen for their energy-eficiency and their involutive property. Both these layers have very small logic depth which makes the energy consumption per round figure as small as possible. Structurally MidoriCore and $\mathsf { M i d o r i c o r e ^ { - 1 } }$ difer only in the order of application of ShufleCell, MixColumn and InvShufleCell operations. And so, the circuit for the round based implementation of the cipher, that accommodates both encryption and decryption can be realized in Fig. 10. 

Since the ShufleCell operation (Sh) and MixColumn (MC) do not commute, the linear layer which is basically the composition of MC Sh $( = L { \mathrm { ~ s a y } } )$ , must be inverted during the decryption by $L ^ { - 1 } = \ \mathrm { S h ^ { - 1 } o M C }$ . In hardware, this can be achieved in two ways. The first involves filtering the outputs of the L and $L ^ { - 1 }$ operations through a single multiplexer. This requires two instances of the MixColumn logic in the circuit, and since this layer is the most expensive in terms of area and energy consumed, it is not the most eficient way to achieve this functionality. The second method which is better in terms of both area and energy is the one shown in Fig. 10. This involves using two multiplexers for filtering the outputs of the Sh and $\mathrm { S h ^ { - 1 } }$ operations and a single instance of the MixColumn logic. To perform the decryption operation using this circuit, the round key needs to be changed to $L ^ { - 1 } ( K )$ , and correspondingly the $i ^ { t h }$ round constant to $L ^ { - 1 } ( \beta _ { 1 8 - i } )$ . The first involves a cheap one-time change to the master key, while keeping the whitening key constant. The round constant functionality can be achieved by employing two lookup tables, one each for encryption and decryption and filtering the appropriate round constant through a multiplexer. The round constants have been chosen in a manner so that both $\beta _ { i }$ and $L ^ { - 1 } ( \beta _ { i } )$ are 4 4 binary matrices, and so this layer requires a total of 16 XOR gates only. The circuit for the 64-bit variant is the same as in Fig. 10, except that it requires an extra filtering between between $K _ { 0 }$ and $K _ { 1 }$ (the most and least significant halves of the secret key) in alternate rounds. Additionally one can also design an encryption only (E) variant of the circuit as shown in Figure 11. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-13/7a7c4e6c-6b0d-4dd7-8818-5ac0725cd68b/b9a0a12e2be21eda12f03d56a47d0ef41456957de930e34da39123ddc6ccdfe0.jpg)



Fig. 10: The round based encryption/decryption (ED) architecture


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-13/7a7c4e6c-6b0d-4dd7-8818-5ac0725cd68b/e215fd04462f2f894adc0650c56686c15b25ac7b1990829839e59cd957e5151a.jpg)



Fig. 11: The round based encryption only (E) architecture


## 6.1 Evaluation

All the designs were initially implemented in VHDL and the functional verification was done using Mentor Graphics ModelSim SE software. The designs were then synthesized using the Synopsys Design Compiler for the Standard Cell library of the STM 90nm Logic Process: CORE90GPHVT v 2.1.a. 


Table 10: A comparison of energy consumption of Midori with selected ciphers for the STM 90nm Logic Process. (Average Power reported at 10 MHz)


<table><tr><td>#</td><td>Cipher</td><td colspan="2">Block Size Architecture</td><td>Area (in GE)</td><td>Energy pJ</td><td>Energy/bit pJ</td><td>Average Power (μW)</td><td>Critical Path (ns)</td></tr><tr><td rowspan="2">1</td><td rowspan="2">AES</td><td rowspan="2">128</td><td>ED</td><td>21274</td><td>769.0</td><td>6.01</td><td>699.1</td><td>4.08</td></tr><tr><td>E</td><td>12459</td><td>350.7</td><td>2.74</td><td>318.8</td><td>3.32</td></tr><tr><td rowspan="2">2</td><td rowspan="2">NOEKEON</td><td rowspan="2">128</td><td>ED</td><td>3439</td><td>331.5</td><td>2.59</td><td>184.2</td><td>3.79</td></tr><tr><td>E</td><td>2284</td><td>338.0</td><td>2.64</td><td>187.8</td><td>3.38</td></tr><tr><td rowspan="2">3</td><td rowspan="2">SIMON 128/128</td><td rowspan="2">128</td><td>ED</td><td>3480</td><td>855.6</td><td>6.68</td><td>124.0</td><td>2.67</td></tr><tr><td>E</td><td>2420</td><td>664.1</td><td>5.19</td><td>96.2</td><td>2.66</td></tr><tr><td rowspan="2">4</td><td rowspan="2">Midori128</td><td rowspan="2">128</td><td>ED</td><td>3661</td><td>228.3</td><td>1.78</td><td>108.7</td><td>2.44</td></tr><tr><td>E</td><td>2522</td><td>187.3</td><td>1.46</td><td>89.2</td><td>2.25</td></tr><tr><td rowspan="2">5</td><td rowspan="2">PRESENT</td><td rowspan="2">64</td><td>ED</td><td>2186</td><td>250.2</td><td>3.91</td><td>75.8</td><td>2.32</td></tr><tr><td>E</td><td>1440</td><td>172.3</td><td>2.69</td><td>52.2</td><td>2.09</td></tr><tr><td rowspan="2">6</td><td rowspan="2">PRINCE</td><td rowspan="2">64</td><td>ED</td><td>2650</td><td>146.3</td><td>2.29</td><td>112.5</td><td>4.09</td></tr><tr><td>E</td><td>2286</td><td>144.7</td><td>2.26</td><td>111.3</td><td>4.06</td></tr><tr><td rowspan="2">7</td><td rowspan="2">Midori64</td><td rowspan="2">64</td><td>ED</td><td>2450</td><td>121.0</td><td>1.89</td><td>71.2</td><td>2.12</td></tr><tr><td>E</td><td>1542</td><td>103.0</td><td>1.61</td><td>60.6</td><td>2.06</td></tr></table>

The switching activity file was then generated by performing a timing simulation on the synthesized netlist using the Synopsys VCS Software. The energy was then estimated with the Synopsys Power Compiler by using the switching activity file. An operating frequency of 10 MHz was used in all the simulations since the efect of the leakage power is minimal at this frequency, and so the energy consumed is more or less independent of the clock frequency. The results of the simulation for the 90nm logic process are presented in Table 10 along with similar evaluations for AES, NOEKEON, SIMON 128/128, PRESENT, PRINCE. It can be seen that Midori128/Midori64 performs better than NOEKEON/PRINCE which were also designed to make the combined functionalities of encryption and decryption easily available. In Fig. 12 we compare the energy/bit consumption of the ED architectures all the seven ciphers along with the cumulative latency figure (calculated as critical path  number of rounds). It can be seen that Midori128 and Midori64 fare optimally with respect to both parameters. 

## 6.2 Simulations with the STM 65 nm logic process

The design flow was repeated with the standard cell library based on the STM 65 nm logic process: CORE65LPHVT v 5.1. The simulation results are tabulated in Table 11. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-13/7a7c4e6c-6b0d-4dd7-8818-5ac0725cd68b/026131c347364fb4d8ebcdece0b96acd1918ac67578cc43aa0d1837f9dcf1e8a.jpg)



Fig. 12: Cumulative Latency vs Energy/bit figures



Table 11: A comparison of energy consumption of Midori with selcted ciphers for the STM 65nm Logic Process. (Average Power reported at 10 MHz)


<table><tr><td>#</td><td>Cipher</td><td colspan="2">Block Size Architecture</td><td>Area (in GE)</td><td>Energy pJ</td><td>Energy/bit pJ</td><td>Average Power (μW)</td><td>Critical Path (ns)</td></tr><tr><td rowspan="2">1</td><td rowspan="2">AES</td><td rowspan="2">128</td><td>ED</td><td>24722</td><td>449.5</td><td>3.51</td><td>408.6</td><td>7.93</td></tr><tr><td>E</td><td>14483</td><td>225.6</td><td>1.76</td><td>205.1</td><td>5.27</td></tr><tr><td rowspan="2">2</td><td rowspan="2">Noekeon</td><td rowspan="2">128</td><td>ED</td><td>3640</td><td>183.2</td><td>1.43</td><td>101.8</td><td>6.64</td></tr><tr><td>E</td><td>2448</td><td>229.3</td><td>1.79</td><td>127.4</td><td>5.68</td></tr><tr><td rowspan="2">3</td><td rowspan="2">Simon 128/128</td><td rowspan="2">128</td><td>ED</td><td>3603</td><td>564.0</td><td>4.40</td><td>81.7</td><td>3.13</td></tr><tr><td>E</td><td>2612</td><td>443.1</td><td>3.46</td><td>64.2</td><td>3.17</td></tr><tr><td rowspan="2">4</td><td rowspan="2">Midori128</td><td rowspan="2">128</td><td>ED</td><td>3959</td><td>127.8</td><td>1.00</td><td>60.9</td><td>3.51</td></tr><tr><td>E</td><td>2714</td><td>105.8</td><td>0.83</td><td>50.4</td><td>3.87</td></tr><tr><td rowspan="2">5</td><td rowspan="2">Present</td><td rowspan="2">64</td><td>ED</td><td>2499</td><td>171.3</td><td>2.68</td><td>51.9</td><td>4.27</td></tr><tr><td>E</td><td>1679</td><td>114.5</td><td>1.79</td><td>34.7</td><td>3.70</td></tr><tr><td rowspan="2">6</td><td rowspan="2">Prince</td><td rowspan="2">64</td><td>ED</td><td>3199</td><td>83.6</td><td>1.31</td><td>64.3</td><td>6.43</td></tr><tr><td>E</td><td>2780</td><td>81.0</td><td>1.27</td><td>62.3</td><td>6.26</td></tr><tr><td rowspan="2">7</td><td rowspan="2">Midori64</td><td rowspan="2">64</td><td>ED</td><td>2620</td><td>68.5</td><td>1.07</td><td>40.3</td><td>4.09</td></tr><tr><td>E</td><td>1638</td><td>58.5</td><td>0.91</td><td>34.4</td><td>3.92</td></tr></table>

## 7 Conclusion

In this paper we present the block ciphers Midori128 and Midori64, optimized with respect to energy consumption. We first identify design choices that make a given algorithm eficient in terms of energy. Thereafter we propose two design components i.e. MixColumn matrix and S-box, that help us achieve the objectives of low energy design. These components are additionally involutive, that makes it easier to design a circuit with functionalities for both encryption and decryption. The energy of the proposed design was then found to be optimal in comparison with state of the art block ciphers available in literature. 

## References



1. M. Albrecht, B. Driessen, E. Kavun, G. Leander, C. Paar, and T. Yal¸cin. Block ciphers - focus on the linear layer (feat. PRIDE). In CRYPTO 2014, LNCS, Vol. 8616, pp. 57–76. 





2. K. Aoki and Y. Sasaki. Preimage attacks on One-block MD4, 63-step MD5 and more. In SAC 2008, LNCS, Vol. 5381, pp. 103–119. 





3. S. Banik, A. Bogdanov and F. Regazzoni. Exploring Energy Eficiency of Lightweight Block Ciphers. To appear in proceedings of SAC 2015. 





4. P. Barreto and V. Rijmen. The WHIRLPOOL Hash Function. Available at http: //www.larc.usp.br/<sub>~</sub>pbarreto/WhirlpoolPage.html 





5. L. Batina, A. Das, B. Ege, E. B. Kavun, N. Mentens, C. Paar, I. Verbauwhede, T. Yal¸cin. Dietary Recommendations for Lightweight Block Ciphers: Power, Energy and Area Analysis of Recently Developed Architectures. In RFIDSec 2013, LNCS, vol. 8262, pp. 103-112. 





6. R. Beaulieu, D. Shors, J. Smith, S. Treatman-Clark, B. Weeks, L. Wingers. The SI-MON and SPECK Families of Lightweight Block Ciphers. In IACR eprint archive. Available at https://eprint.iacr.org/2013/404.pdf. 





7. G. Bertoni, J. Daemen, M. Peeters, G. V. Assche. The Keccak Reference. Available at http://keccak.noekeon.org/Keccak-reference-3.0.pdf. 





8. G. Bertoni, M. Macchetti, L. Negri, P. Fragneto. Power-eficient ASIC synthesis of cryptographic S-boxes. In 14th ACM Great Lakes Symposium on VLSI, pp. 277-281. ACM (2004). 





9. B. Bilgin, A. Bogdanov, M. Knezevic, F. Mendel, and Q. Wang. FIDES: Lightweight authenticated cipher with side-channel resistance for constrained hardware. In CHES 2013, LNCS, Vol. 8086, pp. 142–158. 





10. A. Biryukov and I. Nikolic. Automatic Search for Related-Key Diferential Characteristics in Byte-Oriented Block Ciphers: Application to AES, Camellia, Khazad and Others. In EUROCRYPT 2010, LNCS, Vol. 6110, pp. 322–344. 





11. A. Bogdanov, D. Khovratovich, and C. Rechberger. Biclique Cryptanalysis of the full AES. In ASIACRYPT 2011, LNCS, Vol. 7073, pp. 344–371. 





12. A. Bogdanov, L. Knudsen, G. Leander, C. Paar, A. Poschmann, M. Robshaw, Y. Seurin, C. Vikkelsoe. PRESENT: An Ultra-Lightweight Block Cipher. In CHES 2007, LNCS, vol. 4727, pp. 450-466. 





13. J. Borghof, A. Canteaut, T. G¨uneysu, E. B. Kavun, M. Kneˇzevi´c, L. R. Knudsen, G. Leander, V. Nikov, C. Paar, C. Rechberger, P. Rombouts, S. S. Thomsen, T. Yal¸cin. PRINCE - A Low-Latency Block Cipher for Pervasive Computing Applications - Extended Abstract. In Asiacrypt 2012, LNCS, vol. 7658, pages 208-225. 





14. C. De Canni`ere, O. Dunkelman, M. Kneˇzevi´c. KATAN and KTANTAN - a family of small and eficient hardware-oriented block ciphers. In CHES 2009, LNCS, vol. 5747, pp. 272-288. 





15. D. Canright. A very compact S-Box for AES. In CHES 2005, LNCS, vol. 3659, pp. 441-455. 





16. J. Daemen, M. Peeters, G. V. Assche, V. Rijmen. Nessie Proposal: NOEKEON. Available at http://gro.noekeon.org/Noekeon-spec.pdf. 





17. J. Daemen, V. Rijmen. The design of Rijndael: AES - the Advanced Encryption Standard. Springer-Verlag. 





18. M. Feldhofer, J. Wolkerstorfer, V. Rijmen. AES Implementation on a Grain of Sand. In IEEE Proceedings of Information Security, vol. 152(1), pages 13-20, 2005. 





19. Z. Gong, S. Nikova, Y.W. Law. KLEIN: a new family of lightweight block ciphers. In RFIDSec 2011, LNCS, vol. 7055, pp. 1-18. 





20. J. Guo, T. Peyrin, A. Poschmann, M. J. B. Robshaw. The LED Block Cipher. In CHES 2011, LNCS, vol. 6917, pp. 326-341. 





21. T. Iwata, K. Minematsu, J. Guo, and S. Morioka. CLOC: Authenticated Encryption for Short Input. In FSE 2014, LNCS, vol. 8540, pp. 149–167. 





22. S. Kerckhof, F. Durvaux, C. Hocquet, D. Bol, F. X. Standaert. Towards Green Cryptography: a Comparison of Lightweight Ciphers from the Energy Viewpoint. In CHES 2012, LNCS, vol. 7428, pp. 390-407. 





23. K. Khoo, T. Peyrin, A. Poschmann, and H. Yap. FOAM: Searching for Hardware-Optimal SPN Structures and Components with a Fair Comparison. In CHES 2014, LNCS, Vol. 8731, pp. 433–450. 





24. V. Lallemand and M. Naya-Plasencia. Cryptanalysis of KLEIN. In FSE 2014, LNCS, vol. 8540, pp. 451–470. 





25. C.H. Lim and T. Korishhko. mCrypton - A Lightweight Block Cipher for Security of Low-Cost RFID Tags and Sensors. In WISA 2006, LNCS, vol. 3786, pp 243-258. 





26. M. Matsui. On Correlation Between the Order of S-boxes and the Strength of DES. In EUROCRYPT 1994, LNCS, vol. 950, pp. 366–375. 





27. S. Meng Sim, K. Khoo, F. Oggier, and T. Peyrin. Lightweight MDS Involution Matrices. To appear in FSE 2015. 





28. A. Moradi, A. Poschmann, S. Ling, C. Paar, H. Wang. Pushing the Limits: A Very Compact and a Threshold Implementation of AES. In Eurocrypt 2011, LNCS, vol. 6632, pp. 69-88. 





29. S. Morioka, A. Satoh. An Optimized S-Box Circuit Architecture for Low Power AES Design. In CHES 2002, LNCS, vol. 2523, pp. 172-186. 





30. Y. Sasaki and K. Aoki. Finding Preimages in Full MD5 Faster Than Exhaustive Search. In EUROCRYPT 2009, LNCS, vol. 5479, pp. 134-152. 





31. A. Satoh, S. Morioka, K. Takano, S. Munetoh. A Compact Rijndael Hardware Architecture with S-Box Optimization. In Asiacrypt 2001, LNCS, vol. 2248, pp. 239-254. 





32. K. Shibutani, T. Isobe, H. Hiwatari, A. Mitsuda, T. Akishita, T. Shirai. Piccolo: An Ultra-Lightweight Blockcipher. In CHES 2011, LNCS, vol. 6917, pp. 342-357. 





33. T. Shirai, K. Shibutani, T. Akishita, S. Moriai, T. Iwata. The 128-bit Block-cipher CLEFIA (Extended Abstract). In FSE 2007, LNCS, vol. 4593, pp. 181-195. 





34. T. Suzaki, K. Minematsu, S. Morioka, E. Kobayashi. TWINE: A Lightweight Block Cipher for Multiple Platforms. In SAC 2012, LNCS, vol. 7707, pp. 339-354. 





35. T. Suzaki, K. Minematsu. Improving the Generalized Feistel. In FSE 2010, LNCS, vol. 6147, pp. 19-39. 



36. S. Tillich, M. Feldhofer, and J. Großsch¨adl. Area, Delay, and Power Characteristics of Standard-Cell Implementations of the AES S-Box. In SAMOS 2006, LNCS, vol. 4017, pp. 457-466. 

## Appendix A: Test Vectors

A. Midori128 

Plaintext : 00000000000000000000000000000000 

1. Key : 00000000000000000000000000000000 

Ciphertext : c055cbb95996d14902b60574d5e728d6 

Plaintext : 51084ce6e73a5ca2ec87d7babc297543 

2. Key : 687ded3b3c85b3f35b1009863e2a8cbf Ciphertext : 1e0ac4fddff71b4c1801b73ee4afc83d 

B. Midori64 

Plaintext : 0000000000000000 

1. Key : 00000000000000000000000000000000 Ciphertext : 3c9cceda2bbd449a 

Plaintext : 42c20fd3b586879e 

2. Key : 687ded3b3c85b3f35b1009863e2a8cbf Ciphertext : 66bcdc6270d901cd 