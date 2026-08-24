# The SPEEDY Family of Block Ciphers Engineering an Ultra Low-Latency Cipher from Gate Level for Secure Processor Architectures

Gregor Leander<sup>1</sup> , Thorben Moos<sup>1</sup> , Amir Moradi<sup>1</sup> and Shahram Rasoolzadeh<sup>∗2</sup> 

1 Ruhr University Bochum, Horst Görtz Institute for IT Security, Bochum, Germany firstname.lastname@rub.de <sup>2</sup> Radboud University, Nijmegen, The Netherlands firstname.lastname@ru.nl 

Abstract. We introduce SPEEDY, a family of ultra low-latency block ciphers. We mix engineering expertise into each step of the cipher’s design process in order to create a secure encryption primitive with an extremely low latency in CMOS hardware. The centerpiece of our constructions is a high-speed 6-bit substitution box whose coordinate functions are realized as two-level NAND trees. In contrast to other low-latency block ciphers such as PRINCE, PRINCEv2, MANTIS and QARMA, we neither constrain ourselves by demanding decryption at low overhead, nor by requiring a super low area or energy. This freedom together with our gate- and transistor-level considerations allows us to create an ultra low-latency cipher which outperforms all known solutions in single-cycle encryption speed. Our main result, SPEEDY-6-192, is a 6-round 192-bit block and 192-bit key cipher which can be executed faster in hardware than any other known encryption primitive (including Gimli in Even-Mansour scheme and the Orthros pseudorandom function) and ofers 128-bit security. One round more, i.e., SPEEDY-7-192, provides full 192-bit security. SPEEDY primarily targets hardware security solutions embedded in high-end CPUs, where area and energy restrictions are secondary while high performance is the number one priority. 

Keywords: Low-Latency Cryptography, High-Speed Encryption, Block Cipher 

## 1 Introduction

In this paper we revisit the following fundamental problem: How do we design a secure encryption algorithm whose hardware implementation is fast? Specifically, we care about the entire latency of the hardware circuit from the point where the inputs are provided to the point where the final outputs are ready and stable, i.e., the latency of a fully-unrolled hardware implementation entirely made from combinatorial logic. Previous approaches, which led to the design of established low-latency constructions like PRINCE [BCG<sup>+</sup>12], PRINCEv2 [BEK<sup>+</sup>20], MANTIS [BJK<sup>+</sup>16] and QARMA [Ava17], considered a low number of rounds and, to some extent, a small gate depth as design criteria. While both are obviously important factors to achieve a low latency, there are further aspects which have been ignored at the design level in the past – first and foremost the latency characteristics of the underly ing hardware. At first sight it may appear to be of limited interest to tailor a cryptographic primitive towards one specific device technology due to the potential loss of generality. However, in the hardware world there has been only one de-facto standard for integrated circuit fabrication since the 1980s, namely Complementary Metal–Oxide–Semiconductor (CMOS) technology. The construction of CMOS logic gates, i.e., the arrangement of pand n-channel MOSFETs (Metal–Oxide–Semiconductor Field-Efect Transistors) to create a certain functionality, has remained largely unchanged since its original proposal in 1963. In other words, CMOS logic gates – the essential building blocks for the vast majority of our computing technology today – have not experienced any fundamental redesign in almost 6 decades. Merely their size has seen a progressive decrease according to Moore’s famous law [Moo65]. 

Notably, there are some operations which can be constructed more naturally from complementary logic. In particular, complementary gates in silicon hardware are naturally inverting and non-inverting Boolean functions cannot be realized in a single stage (i.e., they require more than one pull-up and pull-down network) [RCN04]. Among the naturally inverting logic gates some can be realized using only the minimum (lower bound) of 2n transistors, where n is the number of inputs the gate receives. These 2n transistors are then arranged in the classical layout of one pull-up network, built from p-channel MOSFETs (PMOS), and one pull-down network, built from n-channel MOSFETs (NMOS). The simple Boolean functions NAND, NOR and INV/NOT are constructed this way, but also the compound or complex logic gates AND-OR-INV (AOI) and OR-AND-INV (OAI). We argue that logic cells with these properties are immensely beneficial for low-latency constructions as they produce outputs much faster than their counterparts, independent of the particular specifications or the minimum feature size of the fabrication process. 

When diving deeper into the physical characteristics of hardware circuits built from silicon, it is possible to make even further distinctions. In particular, we point out that cell layouts which require PMOS transistors to be connected in series (stacked) sufer from the lower mobility of PMOS compared to NMOS transistors more significantly. In consequence, a noticeable negative impact on the latency of such gates can be observed and larger transistor widths are required to partially ofset this performance loss at the price of an increased area [RCN04]. Among the previously listed cells, only NAND and INV/NOT gates do not classically require PMOS transistors to be stacked. NOR gates with more than two inputs sufer most severely from the mobility mismatch due to the larger PMOS stacks. To clarify the impact of such observations on the performance of gates in common standard cell libraries, we present latency figures for individual logic gates exemplarily for NanGate 45 nm and 15 nm Open Cell Libraries (OCLs) in Section 2. 

All gate- and transistor-level considerations described above are universally applicable to CMOS standard cells, independent of the particular foundry, manufacturing process and minimum feature size. Hence, it makes sense to take such characteristics into account when attempting to implement a certain function, like an encryption algorithm, as a hardware circuit with minimum latency. When revisiting previous latency-driven constructions in cryptography, it is clear that such low-level observations have not been considered in the past. We provide first contributions towards hardware-aware low-latency design and construct a family of ultra low-latency block ciphers based on the underlying principles. 

## 1.1 Motivation

Approaches to secure the internals of modern Central Processing Units (CPUs) have received significant attention in the last few years as microarchitectural attacks, notably Meltdown [LSG<sup>+</sup>18] and Spectre [KHF<sup>+</sup>19], revealed serious shortcomings in the security architectures of widely deployed high-end processors. Hardware-based mitigations for such attacks are proposed "en masse". Many of them call for a higher level of encrypted communication inside of CPUs as well as between CPUs and their surrounding hardware components. Among the former are proposals for secure caches such as ScatterCache [WUG<sup>+</sup>19] and CEASER [Qur18]. Both of them are compared to a number of further cache architectures in [DXS19]. To implement new features of this kind in the next generations of mainstream processors without causing a large performance penalty, high-speed encryption primitives are among the most important building blocks. 

Secure caches are only one example of security applications in CPU environments that require high-speed encryption. Dedicated hardware instructions, memory encryption, pointer authentication (as renownedly implemented using QARMA in ARM processors) and similar hardware-assisted mechanisms against software exploitation fall into this category as well. We expect to see a lot more of such features implemented in future generations of secure processor architectures, especially when more highly-optimized cryptographic primitives become available. SPEEDY is meant as a general purpose high-speed encryption primitive for all these applications and not limited or tailored to a subset of them. 

Most low-latency ciphers published in the literature so far, such as PRINCE $\mathrm { [ B C G ^ { + } 1 2 ] }$ PR.TNCEv2 $[ \mathrm { B E K ^ { + } 2 0 } ]$ ], MANTIS $[ \mathrm { B J K ^ { + } 1 6 } ]$ and QARMA [Ava17], try to meet tight area and energy requirements in addition to low latency. These properties make them particularly suitable for highly-constrained microcontrollers in the Internet of Things (IoT). However, keeping the primitives suited for battery-powered devices requires sacrifices with respect to maximum performance. High-end CPUs do not impose the same kind of restrictions on area and energy, yet they require even higher performance in terms of latency and throughput. SPEEDY is able to outperform the state of the art by focusing on maximum encryption speed and high security only. 

## 1.2 Related Work

Designing cryptographic primitives with minimum execution time in hardware is still a young and emergent research discipline. At CHES 2012 the authors of [KNR12] delivered first results in that area by comparing the latency properties of multiple (lightweight) block ciphers. It was concluded that, among other factors, the use of cryptographically-strong 4- bit (or even 3-bit) S-boxes should be favored over larger substitutions and that a low number of rounds should be maintained even at the price of a heavier linear layer when designing a low-latency primitive. These demands were immediately met by the first dedicated low-latency block cipher called PRINCE which has been presented at ASIACRYPT 2012. PRINCE is a 64-bit block cipher with a 128-bit key and 12 cipher rounds which features an innovative reflection property that allows to encrypt and decrypt data with essentially the same circuit. Recently, an updated version called PRINCEv2 has been proposed which claims to increase the security level of PRINCE by making small modifications to the key schedule and the middle rounds $[ \mathrm { B E K ^ { + } 2 0 } ]$ . This work also provides a comparison of multiple low-latency block ciphers which confirms that PRINCE and PRINCEv2 are still the fastest such primitives in public literature $[ \mathrm { B E K ^ { + } 2 0 } ]$ . The comparison also includes the tweakable block ciphers MANTIS $[ \mathrm { B J K ^ { + } 1 6 } ]$ and QARMA [Ava17] as well as the low-energy block cipher Midori $[ \mathrm { B B I ^ { + } 1 5 } ]$ and demonstrates that all three of them come at a latency overhead between 22 % and 42 % (considering the encryption-only variants) compared to PRINCE in open-source NanGate libraries. This result may not come as a surprise, since tweakable block ciphers such as MANTIS and QARMA are expected to require a larger circuit depth due to the additional tweak input and since Midori has not been designed with low latency being the primary design goal, although its substitution layer has been chosen particularly to ofer a small delay. However, two recent works claim that cryptographic primitives aside from traditional block ciphers are able to outperform PRINCE in terms of latency. First, the high performance cross-platform permutation Gimli introduced in $[ \mathrm { B K L ^ { + } 1 7 } ]$ is claimed to enable encryption with a 1.7 times smaller latency than PRINCE in [GKD20], while the low-latency pseudorandom function (PRF) Orthros introduced in [BIL<sup>+</sup>21] claims to achieve a latency about 7 % below PRINCE’s. We analyze both claims in our comparison in Section 7 and conclude that the latter is consistent with our results, while the former is clearly not. Orthros is able to achieve a lower latency than PRINCE by computing the sum of two keyed permutations [BIL<sup>+</sup>21] which makes the resulting primitive non-invertible (in contrast to block ciphers like SPEEDY). 

Apart from the full cryptographic primitives discussed above, there are also some works focusing on particular cryptographic building blocks only. For instance, in [LSL<sup>+</sup>19] it is shown how to construct involutory low-latency Maximal Distance Separable (MDS) matrices. The authors of [BFP19] present techniques for finding small low-depth circuits for cryptographic functions. In [BMD<sup>+</sup>20] the main goal is to construct S-boxes whose masked variants (i.e., their side-channel protected versions) have a low latency in hardware which conceptually requires a low AND depth and AND gate complexity. Low-latency hardware masking in general, used to protect cryptographic primitives against sidechannel attacks, has received significant attention in the last few years, as demonstrated in [MS16, GIB18, ABP<sup>+</sup>18, BKN19, SBHM20]. However, this field is not directly related to the development of low-latency symmetric primitives in general, as the requirements are vastly diferent and sometimes even direct opposites.<sup>1</sup> 

## 1.3 Our Contribution

We introduce SPEEDY, a family of ultra low-latency block ciphers dedicated to semi-custom, i.e., standard-cell-based, integrated circuit design. In order to tailor this cryptographic primitive towards maximum execution speed in hardware we first analyze which type of logic gates and circuit topologies are particularly suited for ultra low-latency encryption. Our considerations in this regard are novel and have, to the best of our knowledge, not been applied in previous designs of symmetric cryptographic primitives. 

SPEEDY can be instantiated with diferent block and key sizes and varying numbers of rounds. However, due to our S-box width of 6 bits and our main target application of 64-bit high-end CPUs we decided to use the least common multiple of 6 and 64, namely 192 as the default block and key size and call this instance SPEEDY-r-192. We claim that SPEEDY-r-192 achieves 128-bit security when iterated over r = 6 rounds and full 192-bit security when iterated over r = 7 rounds, while the r = 5 round variant already provides a decent security level that is suficient for many practical applications. Our extensive evaluation of hardware implementations in 6 diferent standard cell libraries shows that both SPEEDY-5-192 and SPEEDY-6-192 achieve a lower latency in hardware than any other known encryption primitive, while SPEEDY-7-192 is only marginally slower than PRINCE. Considering the provided security levels this is a significant improvement over the state of the art in the area of (ultra) low-latency cryptography. 

## 2 Background

In this section we revisit the necessary concepts which build the foundation for SPEEDY and analyze the primary traits that make certain CMOS standard cells and circuit topologies particularly useful for high-speed cryptography. 

## 2.1 Natural CMOS Gates (NCGs)

A static CMOS gate is constructed by combining a pull-up with a pull-down network. The pull-up network, as the name suggests, is responsible for pulling the output of the gate up to VDD whenever the Boolean function should result in a logical ’1’. The pull down network, analogously, is responsible for pulling the output down to GND whenever the Boolean function should output a logical ’0’. The networks are built in a mutually exclusive manner such that only one of them is conductive for each combination of input signals [RCN04]. While the pull-up networks are exclusively built from PMOS devices, the pull-down networks are built from NMOS devices. PMOS devices can be understood as switches that conduct current between their drain and source terminals whenever their gate voltage is low, NMOS devices conduct current between the terminals whenever their gate voltage is high. For the opposite gate voltages the transistors are in a high-resistance state. The assignment of PMOS transistors to pull-up networks and NMOS to pull-down networks originates from the fact that PMOS devices cannot produce so-called strong zeros, while NMOS devices cannot produce strong ones [RCN04]. In consequence, static CMOS gates with a single stage are naturally inverting by design. Non-inverting Boolean functions require at least two stages of pull-up and pull-down networks. Thus, as already discussed in Section 1, certain logic functions are a more natural fit for technologies that are based on complementary metal–oxide–semiconductor logic. Inverting Boolean functions include for instance the common logic gates INV/NOT, NAND, NOR, XNOR, AOI and OAI. Most of them (all except XNOR) can be realized as static gates by using only the lower bound of 2n devices, namely n PMOS and n NMOS transistors. We call all inverting logic gates which require only one stage and 2n transistors for their implementation Natural CMOS Gates (NCGs). All NCGs commonly found in standard cell libraries with $1 \leq n \leq 4$ inputs are depicted in Figure 1. Such logic cells are not only interesting from a hardware design perspective because they require a lower number of transistors and therefore have a smaller area footprint, they are also faster than their opposition and therefore beneficial for low-latency constructions. 

## 2.2 Latency of CMOS Logic Gates

The time that a physical instance of a logic gate requires to respond to a change in its input signals by updating its output signal is called the delay or the latency of a cell. Considering CMOS hardware, the latency of a physical instance of a logic cell depends on a number of factors. Besides environmental influences like the temperature and the supply voltage, also the transition time of the input signals and the capacitance that needs to be driven at its output play a significant role. In this subsection, however, we want to compare the base latencies of static CMOS gates when all outside factors are equal. Tables 1 and 2 list the latencies of common logic gates in two open-source standard cell libraries, namely NanGate 45 nm and 15 nm Open Cell Libraries (OCLs), respectively. The latency values are given in picoseconds and have been obtained by analyzing a netlist containing only the individual logic gate enclosed between standard D-flip-flop cells for typical operating conditions $( 2 5 ^ { \circ } \mathrm { C }$ , nominal voltage) with the Electronic Design Automation (EDA) software Synopsys Design Compiler Version O-2018.06-SP4 using Composite Current Source (CCS) models of the standard cells. Please note that for simplicity only the logic gates with the minimum drive strength (denoted by the sufix "_X1" in NanGate libraries) are shown here. However, the following arguments and considerations also apply to the higher drive strength variants. As expected, the natural CMOS gates, defined in the previous subsection, produce their outputs significantly faster than the competition. Interestingly, though, some significant diferences between analogous natural gates such as NAND and NOR can be observed. In NanGate 45 nm technology for example, the NAND4_X1 cell is more than twice as fast as the NOR4_X1 cell. This is due to the diferent physical behavior of p-type and n-type MOSFETs realized in silicon as semiconductor material. In n-type MOSFETs the majority carriers are electrons which are negatively charged. In p-type MOSFETs on the other hand, the majority carriers are positively charged holes [RCN04]. Holes are less mobile than electrons, which means they move slower. Therefore, simply speaking, PMOS transistors operate slower than NMOS transistors of the same size. This situation is even amplified when connecting PMOS devices in series (stacking) and leads to a significant performance degradation and an increased area demand due to the larger widths required to partially ofset the performance penalty and achieve balanced rise and fall times. Classic CMOS NOR gates require stacks of n PMOS transistors and are therefore among the logic functions which sufer the most from the lower mobility of holes as majority carriers. Since 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/efa7cc25cd22530594a679019f592342ff87964c327b64e50491592890f8c66b.jpg)



(a) INV


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/43fc6d4c784d874ffdf75e7a30715553ad5c1cddf4b3b324d53f2547aa241d6a.jpg)



(b) NAND2


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/bc6f81d53cc7f43071e10f10df64f029ee8cd673003d18e62a77f041c0a788da.jpg)



(c) NOR2


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/f4c540f15c512c796c7ba11b8997587adfd126e343158f2de1059e1ffff3acba.jpg)



(d) NAND3


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/9166f1a35ea9a76ba738ae7cd1c3cbedc8c0d3f045c7acba6c6ea95cdb14294c.jpg)



(e) NOR3


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/4463ad2ac9d11dc6afe3e9037f364362d7d4b8f05bcfc4cf06ce1de4ccf319b7.jpg)



(f) OAI21


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/8260ac3b3a238f828e50d7c13e838fa8e18f55a14bdd5fa56632d06aa5eec401.jpg)



(g) AOI21


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/2faaafff30b47d2618de6dcfeb2d3467950ba2283c637387d6c80e34824c2251.jpg)



(h) NAND4


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/b2226ac480ee85e31ba0fccce90890d0c256ffff021f1a526a64abe5e4f61cc7.jpg)



(i) NOR4


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/f3a4e81debbfd778fd9cdeabef7f0105eaabb0c792624c8a74859ca81843bb66.jpg)



(j) OAI22


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/1830ff2dea23a5599babf5da5c9438452e129ad612a541e5c84456bf3b668089.jpg)



(k) AOI22


Figure 1: Natural CMOS Gates (NCGs): Inverting logic cells realizable in only one stage of 2n MOSFETs as static CMOS gates, where n is the number of inputs. 

both types of complex gates, AOI and OAI, require stacked PMOS transistors in their layouts as well, we can make similar arguments here, although the efect is less striking since the stacks are smaller. OAI gates are typically faster than AOI gates in common standard cell libraries since the internal capacitances in the pull-up networks of AOI gates are larger. NAND and INV/NOT gates are the only NCGs that do not require PMOS stacks in their classical layout. As a result, INV/NOT and NAND2 gates are almost exclusively the fastest CMOS gates for $n = 1$ and $n = 2$ in any CMOS gate library. For $n = 3$ and $n = 4$ the situation depends on the exact sizing of the transistors chosen by the cell designer for each particular gate. This choice determines the trade-of between area and latency of the logic cells. Typically, either NAND3 and NAND4 or OAI21 and OAI22 are the fastest gates for $n = 3$ and $n = 4$ , respectively. In NanGate 45 nm technology OAI21 $( n = 3 )$ and NAND4 $( n = 4 )$ are the fastest cells for their respective number of inputs while in 15 nm technology NAND3 $( n = 3 )$ and OAI22 $( n = 4 )$ cells are the fastest, as apparent in Tables 1 and 2. 


Table 1: Fan-In, Latency, Fan-In-to-Latency-Ratio and Linearity of logic gates in NanGate 45nm Open Cell Library (OCL) for typical operating conditions.


<table><tr><td>Cell Name</td><td>Fan-In</td><td>Latency [ps]</td><td>FLR</td><td>Linearity</td></tr><tr><td>INV_X1</td><td>1</td><td>22.047900</td><td>0.045356</td><td>2</td></tr><tr><td>BUF_X1</td><td>1</td><td>33.556521</td><td>0.029800</td><td>2</td></tr><tr><td>AND2_X1</td><td>2</td><td>40.170699</td><td>0.049788</td><td>2</td></tr><tr><td>NAND2_X1</td><td>2</td><td>27.885556</td><td>0.071722</td><td>2</td></tr><tr><td>NOR2_X1</td><td>2</td><td>40.649809</td><td>0.049201</td><td>2</td></tr><tr><td>OR2_X1</td><td>2</td><td>56.413554</td><td>0.035452</td><td>2</td></tr><tr><td>XNOR2_X1</td><td>2</td><td>57.604454</td><td>0.034720</td><td>4</td></tr><tr><td>XOR2_X1</td><td>2</td><td>73.018849</td><td>0.027390</td><td>4</td></tr><tr><td>AND3_X1</td><td>3</td><td>51.869132</td><td>0.057838</td><td>6</td></tr><tr><td>AOI21_X1</td><td>3</td><td>51.618919</td><td>0.058118</td><td>6</td></tr><tr><td>MUX2_X1</td><td>3</td><td>75.174913</td><td>0.039907</td><td>4</td></tr><tr><td>NAND3_X1</td><td>3</td><td>34.766912</td><td>0.086289</td><td>6</td></tr><tr><td>NOR3_X1</td><td>3</td><td>61.542571</td><td>0.048747</td><td>6</td></tr><tr><td>OAI21_X1</td><td>3</td><td>32.650799</td><td>0.091881</td><td>6</td></tr><tr><td>OR3_X1</td><td>3</td><td>85.839920</td><td>0.034949</td><td>6</td></tr><tr><td>AND4_X1</td><td>4</td><td>65.491892</td><td>0.061076</td><td>14</td></tr><tr><td>AOI22_X1</td><td>4</td><td>57.255469</td><td>0.069862</td><td>6</td></tr><tr><td>NAND4_X1</td><td>4</td><td>44.487149</td><td>0.089914</td><td>14</td></tr><tr><td>NOR4_X1</td><td>4</td><td>91.312885</td><td>0.043805</td><td>14</td></tr><tr><td>OAI22_X1</td><td>4</td><td>54.596245</td><td>0.073265</td><td>6</td></tr><tr><td>OR4_X1</td><td>4</td><td>118.592046</td><td>0.033729</td><td>14</td></tr></table>

## 2.2.1 Suitability for High-Speed Encryption

There are several factors to be considered when determining which cells in a standard gate library are most suitable for low-latency encryption. Building a low-latency encryption primitive in hardware is essentially the task of creating a circuit that, as quickly as possible, establishes an, as highly as possible, non-linear relationship between the plaintext and, as many as possible, independent key bits. Of course, this is an extreme oversimplification of the large number of requirements that symmetric cryptographic primitives need to fulfill in order parry all known attacks. Yet, when following this simplified idea, the design process for an ultra low-latency cipher should start at the gate level. In particular, we are interested in logic gates that are capable of establishing a Boolean relationship between as many inputs as possible in a short period of time. In that regard, we introduce a new metric, which we call the Fan-in-to-Latency Ratio (FLR). Essentially, we divide the fan-in n of each gate $( { \mathrm { i . e . } }$ , the number of inputs it receives) by its latency. Let $f : \mathbb { F } _ { 2 } ^ { n } \to \mathbb { F } _ { 2 }$ be the Boolean function of a logic gate and n the number of inputs it receives (i.e., the fan-in), then the Fan-in-to-Latency Ratio (FLR) of $f$ can be expressed as Equation 1. 


Table 2: Fan-In, Latency, Fan-In-to-Latency-Ratio and Linearity of logic gates in NanGate 15nm Open Cell Library (OCL) for typical operating conditions.


<table><tr><td>Cell Name</td><td>Fan-In</td><td>Latency [ps]</td><td>FLR</td><td>Linearity</td></tr><tr><td>INV_X1</td><td>1</td><td>1.580082</td><td>0.632879</td><td>2</td></tr><tr><td>BUF_X1</td><td>1</td><td>3.068201</td><td>0.325924</td><td>2</td></tr><tr><td>AND2_X1</td><td>2</td><td>3.579786</td><td>0.558692</td><td>2</td></tr><tr><td>NAND2_X1</td><td>2</td><td>2.030621</td><td>0.984920</td><td>2</td></tr><tr><td>NOR2_X1</td><td>2</td><td>2.554366</td><td>0.782973</td><td>2</td></tr><tr><td>OR2_X1</td><td>2</td><td>3.643867</td><td>0.548867</td><td>2</td></tr><tr><td>XNOR2_X1</td><td>2</td><td>6.788322</td><td>0.294624</td><td>4</td></tr><tr><td>XOR2_X1</td><td>2</td><td>5.268465</td><td>0.379617</td><td>4</td></tr><tr><td>AND3_X1</td><td>3</td><td>5.496015</td><td>0.545850</td><td>6</td></tr><tr><td>AOI21_X1</td><td>3</td><td>3.394032</td><td>0.883904</td><td>6</td></tr><tr><td>MUX2_X1</td><td>3</td><td>6.133133</td><td>0.489146</td><td>4</td></tr><tr><td>NAND3_X1</td><td>3</td><td>2.360978</td><td>1.270660</td><td>6</td></tr><tr><td>NOR3_X1</td><td>3</td><td>3.787567</td><td>0.792065</td><td>6</td></tr><tr><td>OAI21_X1</td><td>3</td><td>2.830147</td><td>1.060016</td><td>6</td></tr><tr><td>OR3_X1</td><td>3</td><td>5.862194</td><td>0.511754</td><td>6</td></tr><tr><td>AND4_X1</td><td>4</td><td>7.125210</td><td>0.561387</td><td>14</td></tr><tr><td>AOI22_X1</td><td>4</td><td>4.070343</td><td>0.982718</td><td>6</td></tr><tr><td>NAND4_X1</td><td>4</td><td>4.659015</td><td>0.858551</td><td>14</td></tr><tr><td>NOR4_X1</td><td>4</td><td>5.250172</td><td>0.761880</td><td>14</td></tr><tr><td>OAI22_X1</td><td>4</td><td>3.775570</td><td>1.059443</td><td>6</td></tr><tr><td>OR4_X1</td><td>4</td><td>7.682688</td><td>0.520651</td><td>14</td></tr></table>

$$
\operatorname{FLR} (f) = \frac {n}{\operatorname{latency} (f)}\tag{1}
$$

By calculating the FLR for each logic gate in a standard cell library one can rank the gates by their suitability for ultra low-latency encryption. Tables 1 and 2 list the FLR scores for all standard logic gates with n inputs for $1 \leq n \leq 4$ . The FLR score reflects the ability of a logic gate to rapidly evaluate a Boolean function on multiple inputs. Hence, the higher the value in the FLR-column for a logic gate, the higher is its potential to be suitable for ultra low-latency encryption. NAND and OAI gates are among the logic cells with the highest FLR scores, while XOR and XNOR gates are among the worst performers. Thus, despite the importance of XOR (and XNOR) gates in symmetric cryptography (mostly for key addition and strong linear layers) it is prudent to limit their occurrence to a minimum. Obviously, the kind of Boolean logic function that is evaluated plays a significant role in determining its suitability for high-speed encryption as well. In that regard, a further important aspect is the linearity of a function. Lin(f) denotes the linearity of the Boolean function $f ,$ defined by Equation 2, where $\widehat { f } : \mathbb { F } _ { 2 } ^ { n } \to \mathbb { Z }$ is the Fourier transform of f given by Equation 3. 

$$
\operatorname{Lin} (f) := \max _ {\alpha \in \mathbb {F} _ {2} ^ {n}} \left| \widehat {f} (\alpha) \right|\tag{2}
$$

$$
\widehat {f} (\alpha) = \sum_ {x \in \mathbb {F} _ {2} ^ {n}} (- 1) ^ {f (x) + \langle \alpha , x \rangle}\tag{3}
$$

Tables 1 and 2 provide the linearity of all listed logic gates. The linearity of a Boolean function $f : \mathbb { F } _ { 2 } ^ { n } \to \mathbb { F } _ { 2 }$ is lower bounded by 2<sup>n</sup>2 and upper bounded by $2 ^ { n }$ . Whenever 

Lin $( f ) = 2 ^ { n }$ , f is an afine function, i.e., Equation 4 holds with $\alpha \in \mathbb { F } _ { 2 } ^ { n } , c \in \mathbb { F } _ { 2 }$ 

$$
f (x) = \langle \alpha , x \rangle + c\tag{4}
$$

In our tables, the logic functions INV/NOT, BUF, XOR, XNOR have maximum linearity (2<sup>n</sup>) and can be expressed as constant or afine functions, while the logic gates AND2, NAND2, NOR2 and OR2 reach the lower bound for the linearity of 2<sup>n</sup>2 . 

While both, linear and non-linear functions, are useful for the construction of secure encryption algorithms, they are typically used in diferent layers or round operations. The non-linear layer in block cipher design is typically the substitution layer while all other operations tend to be linear. Often the substitution boxes, in short S-boxes, are among the most resource consuming elements in terms of area, energy and latency. Therefore, it is particularly interesting to optimize this building block towards the desired design goal when developing and implementing a cipher. In that regard, non-linear gates with a high FLR score, like NAND and OAI, are the prime candidates for building strong and fast S-boxes. 

## 2.3 Latency of Logic Circuits

It is insuficient to consider only the latencies of individual logic elements in order to determine the resulting total latency of a combinatorial circuit or path. When connecting logic gates to logic circuits, the individual propagation delays of the gates depend significantly on their direct electrical environment. Merely summing up the base latencies of the gates in a path (e.g., the values given in Tables 1 and 2) may give a very incorrect idea about the path’s total latency. Despite the fact that some obvious correlation between these quantities can be observed, the gate depth of a path is not always directly proportional to its latency. Therefore, it is important to also consider adequate circuit topologies which minimize the latency of combinatorial circuits when designing a low-latency cipher. In this regard, we first want to dispel two common myths about the latency of CMOS circuits: 

• Myth 1: Each CMOS standard cell has a fixed delay and each instantiation of the same exact standard cell adds (approximately) the same latency to a path. 

Truth: This is false. The propagation delay of a CMOS cell is always a function of the transition time of its input signals, which is influenced by the drive strength of preceding cells and the capacitance of the nets they need to drive, as well as the capacitive load that the CMOS cell itself needs to drive at its output. The variations of the delay of a cell instance depending on its electrical environment can easily be in the range of 200-300%. Therefore, it is not uncommon that two instances of the same cell in diferent positions of a logic circuit have delays associated with them (e.g., in a timing report) that difer by a factor of 3 or 4. 

• Myth 2: Adding a gate to a path of a circuit and not making any other changes to the path will always increase the path’s latency. 

Truth: This is also false. Often, adding a well-placed bufer or inverter (where logically applicable) to a path in order to charge a significant capacitive load faster can decrease the overall latency of the path. Hence, the mere gate depth is not always indicative of the latency of a circuit. Generally, the topology of a circuit, primarily the fan-out of the logic cells, is similarly important as the number and type of gates in its critical path when determining the maximum latency. 

In the following we provide an example which demonstrates the incorrectness of the two myths. We consider a simple circuit in Figure 2(a) where the output signal of a single XOR logic gate in NanGate 15 nm technology (XOR2_X1) is the input to 8 further XOR cells. The respective maximum latencies for each of the two circuit stages are denoted below the gates in Figure 2. While the base latency of a simple XOR logic gate in this technology is 5.268465 ps according to Table 2, it is obvious that the actual latencies of the gates in this circuit are significantly larger. The first XOR gate in particular which feeds the other 8 gates requires a latency which is more than 4 times as large as its base latency due to the significant capacitive load it needs to drive. The XOR gates in the second stage do not drive any large loads but their latency is increased because their input signals have a large transition time. It is noteworthy that this is a synthesis result, which means that the actual capacitances and resistances of the routing (i.e., wiring) are not even considered yet. After placing and routing this circuit in a chip design the latencies would likely be even larger. Figure 2(b) shows a circuit with the same logic functionality and the same 9 total XOR gates, but here the output of the first stage XOR is bufered by a drive strength bufer (BUF_X4). Although this change increases the gate depth of the circuit, it decreases its overall latency. The first stage XOR now only needs to drive a small load and the last stage XORs are driven by input signals with a short transition time. As a result, the bufered circuit has a total latency of 18.675571 ps (Fig. 2(b)) while the circuit without a bufer has a total latency of 29.169073 ps (Fig. 2(a)). Hence, the bufered circuit is more than 35% faster. Please note that the NanGate 15 nm library does not provide XOR gates with a higher drive strength, thus up-sizing the first stage XOR itself is not an option here and bufering the high fan-out net is inevitable when the latency should be reduced. Of course, this is done automatically by the synthesis tool. Our point here is simply that, regardless of how the large fan-out is addressed by the tool or the designer, e.g., up-sizing the gate or inserting a bufer, it assuredly causes an increased latency compared to a circuit with the same depth and the same gates in both levels, but with smaller fan-outs. Thus, we conclude that dedicated low-latency circuits should use topologies where the fan-outs of the logic gates are as small as possible (e.g. tree-based). 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/45d439b0bc6ec8c03e92f70e2bdc6a07ae6d5afa6dc444908ed59d6206f2a490.jpg)



(a) without bufering


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/4596c0788d49807d2f7196741baff1dc132d1c6db98e2e72af8f0bee62527002.jpg)



(b) with bufering



Figure 2: Impact on the latency of the circuit in NanGate 15 nm technology when bufering the high fan-out net. Total latency is 29.169073 ps without the bufer (left) and 18.675571 ps with the bufer (right), despite the larger gate depth on the right.


## 2.3.1 Finding Circuits with Minimum Latency

We would like to caution against the common perception that professional synthesis tools can readily be used to find and generate a netlist with minimum achievable latency for a simple Boolean function like an S-box coordinate function. First of all, the complexity of checking any possible circuit representation composed of a finite (but usually large) set of standard cells for a Boolean function is often remarkably high and market-leading EDA tools are built for time eficiency (especially the synthesis routines). Furthermore, the proprietary synthesis algorithms may not be suficiently configurable to consider latency as the only or primary design goal. The tools may rather take area and energy into account as well and not consider latency optimizations that come at a harsh penalty for the other two optimization goals. In our own experience, the thresholds for such decisions cannot be adjusted suficiently by the designer. Thus, we have found that constructing optimal building blocks for ultra low-latency cryptography needs to be done from scratch (by hand or via heuristics) instead of analyzing many diferent variants with a synthesis tool and selecting the ones that delivered the best performance. In our evaluations, the synthesis algorithms usually produced the best results with respect to low latency, when the underlying gate structure was already given and only incremental performance optimizations were required. 

## 3 Ultra Low-Latency 6-bit S-box

In this section, we describe the technique we have used to build an ultra low-latency S-box from gate level. In order to design an S-box which is extremely fast in CMOS hardware while at the same time provides good cryptographic properties, we used the following criteria: 

• Ultra low-latency: As explained in Subsection 2.2, NAND and OAI gates are among the best-suited logic gates for low-latency S-box design. Thus, we search for S-boxes that can be realized with as few as possible levels of only NAND and OAI gates. Furthermore, as discussed in Subsection 2.3, we try to make sure that in as many stages as possible the logic gates have a minimum fan-out. 

• Bijective mapping with fully-dependent outputs: Since we aim for an SPN cipher, we need the S-box to be a bijective mapping. Moreover, we restrict the search to the S-boxes with fully-dependent outputs. In more detail, this means that all input bits are involved in the computation of each output bit. 

• Small linearity and uniformity: To provide strong resistance against diferential and linear attacks, we are only interested in S-boxes with small uniformity u and linearity l defined as 

$$
\begin{array}{l}u = \operatorname{Uni}(S):= \max_{\substack{\alpha ,\beta \in \mathbb{F}_{2}^{n}\\ \alpha \neq 0}}\big|\{x\in \mathbb{F}_{2}^{n}|S(x)\oplus S(x\oplus \alpha) = \beta \} \big|,\\ l = \operatorname{Lin}(S):= \max_{\substack{\alpha ,\beta \in \mathbb{F}_{2}^{n}\\ \beta \neq 0}}\Big|\sum_{x\in \mathbb{F}_{2}^{n}}(-1)^{\langle \alpha ,x\rangle \oplus \langle \beta ,S(x)\rangle}\Big|. \end{array}
$$

By definition, the latency of a vectorial Boolean function, e.g., an S-box, is the maximum of the latencies of its coordinate Boolean functions. Besides, to have a bijective fullydependent S-box with a small linearity, all of its coordinate functions must be balanced, fully-dependent and have a small linearity. Hence, our strategy was to first find low-latency Boolean functions and in a second step try to combine those into an S-box. 

It is noteworthy that the S-boxes within the same class of extended bit-permutation equivalence have roughly the same latency cost (with a small margin of tolerance). Moreover, those functions will have the same uniformity and linearity. We recall from [LP07] that two n-bit to m-bit vectorial Boolean functions $F$ and G of the form $\mathbb { F } _ { 2 } ^ { n } \mapsto \mathbb { F } _ { 2 } ^ { m }$ are called extended bit-permutation equivalent, if there exist $a \in \mathbb { F } _ { 2 } ^ { n } , b \in \mathbb { F } _ { 2 } ^ { m } , P _ { i n } \mathrm { ~ a ~ }$ bit permutation function of n bits and $P _ { o u t }$ a bit permutation function of m bits such that 

$$
G (x) = P _ {o u t} \circ F \circ P _ {i n} (x \oplus a) \oplus b \quad \forall x \in \mathbb {F} _ {2} ^ {n}.
$$

Therefore, it is suficient to consider S-boxes only up to this equivalence. 

## 3.1 Suitable Boolean Functions

To achieve a minimal latency, we searched for coordinate functions that can be realized in only two levels of NAND and OAI gates, or more specifically NAND2, NAND3, NAND4, OAI21 and OAI22 gates, while the larger and slower NAND4 and OAI22 gates should only be used in one of both levels. Additionally the first stage of NAND and OAI gates should have a fan-out of 1 for each gate. With this restriction, we are able to find Boolean functions with an extremely low latency in CMOS hardware. 

We empirically found that Boolean functions based on NAND gates exclusively achieve the best cryptographic properties and latencies with only two levels at a higher quantity; therefore, in the following we limit ourselves to S-boxes which are possible to be built only from NAND gates. However, using the same process described in the following we have created S-boxes based on OAI gates exclusively (functions based on a mix between NAND and OAI have shown to be less promising) and compare them to the NAND-based boxes at the end of this section. 

By considering all the possibilities for the inputs of the NAND gates at the first level, we aim at building all the n-bit Boolean functions $f ( x _ { 0 } , \ldots , x _ { n - 1 } ) ; { \mathrm { i . e . } }$ , for each input for NAND gates we test 2n possible inputs: either $x _ { i }$ or its inverted value $\neg x _ { i }$ with $0 \leq i < n$ We then filter the Boolean functions with respect to the aforementioned criteria, that is balancedness and low-linearity. Please note that selecting the inverted inputs requires additional inverter gates before the first stage of NAND gates. ${ \mathrm { Y e t , } }$ since each of the S-box inputs feeds multiple coordinate Boolean functions at the same time it is prudent to instantiate bufers to drive those nets anyway and an inverter can serve the same purpose. Following this argument, the inverted inputs do not cause any significant extra cost. 

The first step is to find all the Boolean functions $f : \mathbb { F } _ { 2 } ^ { n } \mapsto \mathbb { F } _ { 2 }$ which are: 1) possible to be built by using two levels of NAND gates as explained previously, 2) balanced, 3) fully-dependent on all the input bits, and 4) with linearity at most l. It is important to mention that the order of checking these features is quite important for reducing the computational cost. 

We save all those Boolean functions in a set, named ${ \mathcal F } .$ Note that if there is a function $f \in { \mathcal { F } }$ , then all of its extended bit-permutation equivalent functions such as $g ( \cdot ) = f \circ P ( \cdot \oplus a ) \oplus b$ with $a \in \mathbb { F } _ { 2 } ^ { n } , b \in \mathbb { F } _ { 2 }$ and $P \mathrm { \ a }$ bit permutation function of $n$ bits, are included in $\mathcal { F }$ . Next, we reduce the Boolean functions within $\mathcal { F }$ by the extended bit-permutation equivalence, and only keep one representative of each equivalence class in another set $\mathcal { F } ^ { * }$ . Note that if there are $N _ { f } ^ { \ast }$ Boolean functions in ${ \mathcal { F } } ^ { * }$ , then there are about $N _ { f } = N _ { f } ^ { * } \cdot ( n ! \cdot 2 ^ { n + 1 } )$ functions in ${ \mathcal F } .$ . This reduction corresponds to the n! permutations of the input bits, the $2 ^ { n }$ constants we can add to the input and the single bit we can add to the output. 

## 3.2 Building Sboxes

To find all the bijective S-boxes $S = ( f _ { 0 } , \dotsc , f _ { n - 1 } )$ such that each coordinate function is in ${ \mathcal F } ,$ we can simply choose n of those $N _ { f }$ functions and then check for the necessary criteria, but this requires about $( N _ { f } ) ^ { n }$ steps of checking all the criteria which for $n > 4$ is a large computation cost. The two main options to reduce this cost is (i) considering permutation equivalence and (ii) to select the coordinate function step-by-step and filter after each additional choice. 

Since it is suficient to find the bijective S-boxes up-to the extended bit-permutation equivalence, we can restrict the first coordinate function $f _ { 0 }$ to be chosen from ${ \mathcal { F } } ^ { * }$ that is due to the freedom on choosing the constant and the bit-permutation in the input of the S-box. Besides, for all the other coordinate functions $f _ { 1 } , \ldots , f _ { n - 1 }$ , we can fix an input’s output to a constant, e.g., $f _ { i } ( 0 ) = 0$ and this is because of the freedom in the output constant of the S-box. Note that since $f _ { 0 }$ is chosen from ${ \mathcal { F } } ^ { * }$ and it is a representative function, we already considered that $f _ { 0 } ( 0 ) = 0$ . Moreover, since we are still left with the freedom on the output bit-permutation of the S-box, we can fix the order of the coordinate functions of the S-box. In other words, if we consider that the elements of $\mathcal { F }$ are indexed, then we can fix the index of $f _ { 1 }$ to be smaller than the index of $f _ { 2 }$ and both are smaller than the index of $f _ { 3 }$ and so on. This way, we reduce the number of choices to build an S-box to about ${ \cal N } _ { t } ^ { \dot { n } } / ( n ! \cdot 2 ^ { n } ) ^ { 2 } \approx ( N _ { t } ^ { * } ) ^ { n } \cdot ( \dot { n } ! ) ^ { n - 2 } \cdot 2 ^ { n ^ { 2 } - n }$ . In case of $n = 5$ , this number is about $( N _ { f } ^ { \ast } ) ^ { 5 } \cdot 2 ^ { 4 1 }$ which is still not feasible to search. 

The other main technique to reduce the computation cost of this search is that instead of choosing all the coordinate functions at once and then check for the criteria, we choose them one by one and in each step of choosing a coordinate function, we check for the probable possible criteria. In more details, in step one, we choose $f _ { 0 } \in { \mathcal { F } } ^ { * }$ , then in step 2, we choose $f _ { 1 } \in \mathcal { F }$ . Before, going to step 3, we can check for balancedness and linearity of the component function $f _ { 0 } \oplus f _ { 1 }$ . We go to the next step, if the criteria for $f _ { 0 } \oplus f _ { 1 }$ have met, otherwise, we stay in step 2 and choose another function as $f _ { 1 }$ . In step 3, after choosing $f _ { 2 } \in \mathcal { F }$ , we again can check for balancedness and linearity of the component functions f<sub>0</sub> $\oplus f _ { 2 } , f _ { 1 } \oplus f _ { 2 } , f _ { 0 } \oplus f _ { 1 } \oplus f _ { 2 } .$ . We go to step 4, if all these criteria have met. In this way, we choose all the n coordinate functions to build the S-box, and then we can check for the uniformity criterion. 

This technique, together with several other low-level techniques for speeding up the search, reduces the computation cost of this search significantly. Our search algorithm is written in C++ code and we run it on an Intel Core i7 CPU with 8 threads for about 10 days to exhaustively search all the possible 6-bit S-boxes. Finding all 5-bit S-boxes only requires about two hours. 

We also constructed 7- and 8-bit S-boxes, but due to the larger linearity or uniformity value, they would not have been beneficial over the 6-bit S-box. 

## 3.3 Results

In case of 6-bit S-boxes, the minimum linearity and the minimum uniformity of all S-boxes possible to built, is 24 and 8, respectively. For these properties, up to the extended bit-permutation equivalence, there are only two class of such S-boxes. We choose the S-box class equivalent to the one shown in Figure 3 and given in Table 3, because of the higher algebraic degree. 

For the chosen S-box class, we have the freedom to choose the input/output constants a and b and also $P _ { i n }$ and $P _ { o u t }$ bit-permutation functions. We choose the output constant b in such a way that there is no need to insert an inverter in the output of the NAND gates of the second gate level. Even though it is a tiny improvement, the input constant a is chosen in a way to minimize the latency of the whole structure. 

Finally, we choose the bit-permutations in such a way that it improves the cryptographic properties of the round function for SPEEDY which is explained in more detail in Section 6. Note that the optimum choice of these bit-permutations can be diferent for round functions of diferent primitives. Altogether, we end up with the S-box presented in Table 3. Its corresponding implementation is depicted in Figure 3. Furthermore, the disjunctive normal form (DNF) of the S-box is presented below, which is equivalent to the representation by 


Table 3: The 6-bit S-box of SPEEDY.


<table><tr><td><eq>x_0x_1</eq></td><td colspan="16"><eq>x_2x_3x_4x_5</eq></td></tr><tr><td></td><td>.0</td><td>.1</td><td>.2</td><td>.3</td><td>.4</td><td>.5</td><td>.6</td><td>.7</td><td>.8</td><td>.9</td><td>.a</td><td>.b</td><td>.c</td><td>.d</td><td>.e</td><td>.f</td></tr><tr><td>0.</td><td>08</td><td>00</td><td>09</td><td>03</td><td>38</td><td>10</td><td>29</td><td>13</td><td>0c</td><td>0d</td><td>04</td><td>07</td><td>30</td><td>01</td><td>20</td><td>23</td></tr><tr><td>1.</td><td>1a</td><td>12</td><td>18</td><td>32</td><td>3e</td><td>16</td><td>2c</td><td>36</td><td>1c</td><td>1d</td><td>14</td><td>37</td><td>34</td><td>05</td><td>24</td><td>27</td></tr><tr><td>2.</td><td>02</td><td>06</td><td>0b</td><td>0f</td><td>33</td><td>17</td><td>21</td><td>15</td><td>0a</td><td>1b</td><td>0e</td><td>1f</td><td>31</td><td>11</td><td>25</td><td>35</td></tr><tr><td>3.</td><td>22</td><td>26</td><td>2a</td><td>2e</td><td>3a</td><td>1e</td><td>28</td><td>3c</td><td>2b</td><td>3b</td><td>2f</td><td>3f</td><td>39</td><td>19</td><td>2d</td><td>3d</td></tr></table>

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/b9b3ae40a9087b5a3f0e13123b94c04673c98c8aea8ee1c37bb42e9251c136a6.jpg)



Figure 3: Implementation of the 6-bit S-box of SPEEDY based on two-level NAND trees.


the 2-level NAND gates. 

$$
\begin{array}{l} y _ {0} = \left( \begin{array}{c c c c} x _ {3} \wedge \neg x _ {5} & & \end{array} \right) \vee \left( \begin{array}{c c c c} x _ {3} \wedge x _ {4} \wedge x _ {2} \end{array} \right) \vee \left(\neg x _ {3} \wedge x _ {1} \wedge x _ {0}\right) \vee \left( \begin{array}{c c c c} x _ {5} \wedge x _ {4} \wedge x _ {1} \end{array} \right), \\ y _ {1} = \left( \begin{array}{c c c c} x _ {5} \wedge x _ {3} \wedge \neg x _ {2} \end{array} \right) \vee \left(\neg x _ {5} \wedge x _ {3} \wedge \neg x _ {4}\right) \vee \left( \begin{array}{c c c c} x _ {5} \wedge x _ {2} \wedge x _ {0} \end{array} \right) \vee \left(\neg x _ {3} \wedge \neg x _ {0} \wedge x _ {1}\right), \\ y _ {2} = \left(\neg x _ {3} \wedge x _ {0} \wedge x _ {4}\right) \vee \left( \begin{array}{c c c c} x _ {3} \wedge x _ {0} \wedge x _ {1} \end{array} \right) \vee \left(\neg x _ {3} \wedge \neg x _ {4} \wedge x _ {2}\right) \vee \left(\neg x _ {0} \wedge \neg x _ {2} \wedge \neg x _ {5}\right), \\ y _ {3} = \left(\neg x _ {0} \wedge x _ {2} \wedge \neg x _ {3}\right) \vee \left( \begin{array}{c c c c} x _ {0} \wedge x _ {2} \wedge x _ {4} \end{array} \right) \vee \left( \begin{array}{c c c c} x _ {0} \wedge \neg x _ {2} \wedge x _ {5} \end{array} \right) \vee \left(\neg x _ {0} \wedge x _ {3} \wedge x _ {1}\right), \\ y _ {4} = \left( \begin{array}{c c c c} x _ {0} \wedge \neg x _ {3} & & \end{array} \right) \vee \left( \begin{array}{c c c c} x _ {0} \wedge \neg x _ {4} \wedge \neg x _ {2} \end{array} \right) \vee \left(\neg x _ {0} \wedge x _ {4} \wedge x _ {5}\right) \vee \left(\neg x _ {4} \wedge \neg x _ {2} \wedge x _ {1}\right), \\ y _ {5} = \left( \begin{array}{c c c c} x _ {2} \wedge x _ {5} & & \end{array} \right) \vee \left(\neg x _ {2} \wedge \neg x _ {1} \wedge x _ {4}\right) \vee \left( \begin{array}{c c c c} x _ {2} \wedge x _ {1} \wedge x _ {0} \end{array} \right) \vee (\neg x _ {1} \wedge x _ {0} \wedge x _ {3}). \end{array}
$$

## 3.4 S-box Latency Comparison

We benchmark our chosen S-box with respect to minimum latency in hardware and compare it to a number of other S-boxes from literature in Table 4. Details about the synthesis tools and process are given in Section 7. Please note that up to now only 4-bit S-boxes have been proposed for low-latency constructions in literature, namely (in alphabetical order) the Midori S-boxes [BBI<sup>+</sup>15], the Orthros S-box [BIL<sup>+</sup>21], the PRINCE S-box [BCG<sup>+</sup>12] and the QARMA S-boxes [Ava17]. Yet, in order to compare the SPEEDY S-box also to larger substitution boxes we chose the ASCON 5-bit S-box [DEMS19], the Data Encryption Standard (DES) S 6-to-4-bit box (as a representative of the 8 diferent DES S-boxes) [oST79], the Q2263 6-bit S-box [BMD<sup>+</sup>20] and the Advanced Encryption 


Table 4: Latency comparison of diferent S-boxes with varying numbers of input bits (#ib). If not stated otherwise, each S-box is implemented as a lookup table (using with/select in VHDL).


<table><tr><td rowspan="3">#ib</td><td rowspan="3">S-box</td><td colspan="6">Minimum Latency [ns]</td></tr><tr><td colspan="4">Commercial Foundry</td><td colspan="2">NanGate OCL</td></tr><tr><td>90 nm LP</td><td>65 nm LP</td><td>40 nm LP</td><td>28 nm HPC</td><td>45 nm</td><td>15 nm</td></tr><tr><td>4</td><td>Midori <eq>Sb_0</eq></td><td>0.089098</td><td>0.070579</td><td>0.055577</td><td>0.021051</td><td>0.111156</td><td>0.010619</td></tr><tr><td>4</td><td>Midori <eq>Sb_1</eq></td><td>0.132489</td><td>0.095724</td><td>0.080657</td><td>0.026898</td><td>0.119637</td><td>0.009058</td></tr><tr><td>4</td><td>Orthros</td><td>0.075344</td><td>0.051435</td><td>0.055908</td><td>0.021003</td><td>0.133932</td><td>0.008821</td></tr><tr><td>4</td><td>PRINCE</td><td>0.087938</td><td>0.066545</td><td>0.052826</td><td>0.031010</td><td>0.126588</td><td>0.010176</td></tr><tr><td>4</td><td>QARMA <eq>σ_0</eq></td><td>0.090568</td><td>0.057602</td><td>0.051993</td><td>0.022180</td><td>0.128350</td><td>0.009409</td></tr><tr><td>4</td><td>QARMA <eq>σ_1</eq></td><td>0.144465</td><td>0.101487</td><td>0.077186</td><td>0.031306</td><td>0.156462</td><td>0.011272</td></tr><tr><td>4</td><td>QARMA <eq>σ_2</eq></td><td>0.100530</td><td>0.075846</td><td>0.081528</td><td>0.036485</td><td>0.154379</td><td>0.013354</td></tr><tr><td>5</td><td>ASCON</td><td>0.197794</td><td>0.151025</td><td>0.123356</td><td>0.057595</td><td>0.210599</td><td>0.019854</td></tr><tr><td>6</td><td>DES <eq>S_1</eq></td><td>0.260286</td><td>0.190725</td><td>0.153514</td><td>0.069299</td><td>0.309009</td><td>0.030846</td></tr><tr><td>6</td><td>OAIU8L24</td><td>0.138926</td><td>0.111734</td><td>0.088775</td><td>0.046295</td><td>0.215628</td><td>0.017971</td></tr><tr><td>6</td><td>Q2263</td><td>0.233256</td><td>0.171537</td><td>0.157194</td><td>0.068870</td><td>0.246198</td><td>0.028648</td></tr><tr><td>6</td><td>min(RU8L24)</td><td>0.220168</td><td>0.144777</td><td>0.126819</td><td>0.060535</td><td>0.240982</td><td>0.026696</td></tr><tr><td>6</td><td>SPEEDY</td><td>0.106872</td><td>0.081330</td><td>0.065966</td><td>0.029890</td><td>0.161653</td><td>0.016124</td></tr><tr><td>6</td><td>SPEEDY *</td><td>0.096468</td><td>0.073253</td><td>0.064215</td><td>0.029470</td><td>0.138825</td><td>0.012799</td></tr><tr><td>6</td><td>SPEEDY_INV</td><td>0.207746</td><td>0.152161</td><td>0.129433</td><td>0.071523</td><td>0.278395</td><td>0.025665</td></tr><tr><td>8</td><td>AES</td><td>0.407332</td><td>0.304098</td><td>0.248914</td><td>0.130490</td><td>0.491570</td><td>0.048258</td></tr></table>


木 = Optimized HDL code with direct instantiation of library cells based on Figure 3.


Standard (AES) 8-bit S-box [oST01] for the comparison. Under the abbreviation OAIU8L24 we have listed a 6-bit S-box built from two levels of OAI22 gates with uniformity 8 and linearity 24 (same properties as the SPEEDY S-box). By min(RU8L24) we denote the minimum latency achieved among 10 randomly generated 6-bit S-boxes with uniformity 8 and linearity 24 (without focusing on a particularly eficient implementation). Finally, the inverse of the SPEEDY S-box is included. However, this inverse is not required for the SPEEDY encryption and therefore only relevant for the latency of its decryption. Minimizing the decryption’s latency is not a focus of this work. 

From the comparison it becomes clear that the SPEEDY S-box is impressively fast in hardware. It is much faster than any other S-box with more than 4 input bits (#ib), especially when considering the optimized version with direct instantiation of standard cells in the code based on Figure 3. Additionally, it even outperforms multiple of the 4-bit low-latency S-boxes (including Midori Sb , QARMA σ and QARMA σ ). This is a great result, since the SPEEDY S-box not only provides better difusion in general but also ofers stronger protection against linear and diferential attacks than any 4-bit S-box possibly could. Thus, we are confident in our S-box choice as the centerpiece for an ultra low-latency cipher. 

## 4 Specification of SPEEDY

SPEEDY is a family of ultra low-latency block ciphers with diferent block and key sizes, and varying numbers of rounds. Precisely, SPEEDY-r-6ℓ is an instance of this family with block and key size 6ℓ bits and it iterates over r rounds. 

The internal state is viewed as an ℓ × 6 rectangle array of bits. We use the notation x to denote the bit located at row i and column j of the state x with 0 ≤ i < ℓ and 0 ≤ j < 6. It is important to emphasize that in the remainder of this paper, all the indices start from zero and the zero-th bit or word is always considered the most significant one. Besides, note that if there is an addition or a subtraction in the indices of the state, it is always in modulo ℓ for the first (row) index and in modulo 6 for the second (column) index. 

Initialization: The cipher receives a 6ℓ-bit plaintext and initializes the internal state with it using the same order used for indexing bits, i.e. it first fills $x _ { [ 0 , 0 ] }$ , then $x _ { [ 0 , 1 ] }$ and so on. Then, r round functions, $\mathcal { R } _ { r }$ (with $0 \leq r < \mathbf { r } )$ , are applied on the internal state, the first $\mathbf { r } - 1$ ones of which (up to the round keys and round constants) are identical. Each round function is composed of the following four diferent operations: $( 2 \times )$ SubBox, $( 2 \times )$ ShiftColumns, MixColumns, AddRoundConstant and AddRoundKey. Considering $x \in \dot { \mathbb { F } } _ { 2 } ^ { \ell \times 6 }$ as the input, $y \in \mathbb { F } _ { 2 } ^ { \ell \times 6 }$ as the output of operations, $0 \leq i < \ell$ and $0 \le j < 6$ , the round operations are defined as follows: 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/58b34f77ae6b7fbf77a83ef03536ab561d0ecc382297818fa217b3f6fecb22aa.jpg)


• SubBox (SB): The 6-bit S-box S is applied to each row of the state. 

$$
(y _ {[ i, 0 ]}, y _ {[ i, 1 ]}, y _ {[ i, 2 ]}, y _ {[ i, 3 ]}, y _ {[ i, 4 ]}, y _ {[ i, 5 ]}) = S (x _ {[ i, 0 ]}, x _ {[ i, 1 ]}, x _ {[ i, 2 ]}, x _ {[ i, 3 ]}, x _ {[ i, 4 ]}, x _ {[ i, 5 ]}), \quad \forall   i  .
$$

The table for the S-box (in hexadecimal notation) is given in Table 3 and its implementation based on two-level NAND trees is shown in Figure 3. 

• ShiftColumns (SC): The j-th column of the state is rotated upside by $j$ bits. 

$$
y _ {[ i, j ]} = x _ {[ i + j, j ]}, \quad \forall i, j.
$$

• MixColumns (MC): A cyclic binary matrix is multiplied to each column of the state. 

$$
y _ {[ i, j ]} = x _ {i, j} \oplus x _ {[ i + \alpha_ {1}, j ]} \oplus x _ {[ i + \alpha_ {2}, j ]} \oplus x _ {[ i + \alpha_ {3}, j ]} \oplus x _ {[ i + \alpha_ {4}, j ]} \oplus x _ {[ i + \alpha_ {5}, j ]} \oplus x _ {[ i + \alpha_ {6}, j ]}, \quad \forall   i, j  .
$$

For simplicity, we identify the applied matrix with $\alpha = ( \alpha _ { 1 } , \ldots , \alpha _ { 6 } )$ that is parameterized for each version of the cipher with diferent ℓ value. 

• AddRoundKey $\left( \mathsf { A } _ { k _ { r } } \right)$ : The 6ℓ-bit round key $k _ { r }$ is XORed to the whole of the state. 

$$
y _ {[ i, j ]} = x _ {[ i, j ]} \oplus k _ {r [ i, j ]}, \quad \forall i, j.
$$

• AddRoundConstant $\left( \mathsf { A } _ { c _ { r } } \right)$ : The 6ℓ-bit constant $c _ { r }$ is XORed to the whole of the state. 

$$
y _ {[ i, j ]} = x _ {[ i, j ]} \oplus c _ {r [ i, j ]}, \quad \forall i, j.
$$

Similar to PRINCE, the round constants are chosen as the binary digits of the number $\pi - 3 = 0 . 1 4 1 5 \dots$ . Table 5 presents the first $1 0 0 \times 6 4$ bits of this constant. We use the first 6ℓ bits as $c _ { 0 }$ , the second 6ℓ bits as $c _ { 1 }$ and so on. 

Round Function: Using the above mentioned round operations, the first $\mathbf { r } - 1$ round functions (with $0 \leq r \leq \mathbf { r } - 2 )$ are defined as 

$$
\mathcal {R} _ {r} = \mathrm{A} _ {c _ {r}} \circ \mathrm{MC} \circ \mathrm{SC} \circ \mathrm{SB} \circ \mathrm{SC} \circ \mathrm{SB} \circ \mathrm{A} _ {k _ {r}},
$$

while in the last round, the linear layer and constant addition are omitted, and instead an extra key addition is applied, i.e., 

$$
\mathcal {R} _ {\mathrm{r-1}} = \mathsf {A} _ {k _ {\mathrm{r}}} \circ \mathsf {S B} \circ \mathsf {S C} \circ \mathsf {S B} \circ \mathsf {A} _ {k _ {\mathrm{r-1}}}.
$$


Table 5: The first $1 0 0 \times 6 4$ bits of the constant used in the round constants of SPEEDY.


<table><tr><td>0</td><td>243f6a8885a308d3</td><td>13198a2e03707344</td><td>a4093822299f31d0</td><td>082efa98ec4e6c89</td></tr><tr><td>1</td><td>452821e638d01377</td><td>be5466cf34e90c6c</td><td>c0ac29b7c97c50dd</td><td>3f84d5b5b5470917</td></tr><tr><td>2</td><td>9216d5d98979fb1b</td><td>d1310ba698dfb5ac</td><td>2ffd72dbd01adfb7</td><td>b8e1afed6a267e96</td></tr><tr><td>3</td><td>ba7c9045f12c7f99</td><td>24a19947b3916cf7</td><td>0801f2e2858efc16</td><td>636920d871574e69</td></tr><tr><td>4</td><td>a458fea3f4933d7e</td><td>0d95748f728eb658</td><td>718bcd5882154aee</td><td>7b54a41dc25a59b5</td></tr><tr><td>5</td><td>9c30d5392af26013</td><td>c5d1b023286085f0</td><td>ca417918b8db38ef</td><td>8e79dcb0603a180e</td></tr><tr><td>6</td><td>6c9e0e8bb01e8a3e</td><td>d71577c1bd314b27</td><td>78af2fda55605c60</td><td>e65525f3aa55ab94</td></tr><tr><td>7</td><td>5748986263e81440</td><td>55ca396a2aab10b6</td><td>b4cc5c341141e8ce</td><td>a15486af7c72e993</td></tr><tr><td>8</td><td>b3ee1411636fbc2a</td><td>2ba9c55d741831f6</td><td>ce5c3e169b87931e</td><td>afd6ba336c24cf5c</td></tr><tr><td>9</td><td>7a32538128958677</td><td>3b8f48986b4bb9af</td><td>c4bfe81b66282193</td><td>61d809ccfb21a991</td></tr><tr><td>10</td><td>487cac605dec8032</td><td>ef845d5de98575b1</td><td>dc262302eb651b88</td><td>23893e81d396acc5</td></tr><tr><td>11</td><td>0f6d6ff383f44239</td><td>2e0b4482a4842004</td><td>69c8f04a9e1f9b5e</td><td>21c66842f6e96c9a</td></tr><tr><td>12</td><td>670c9c61abd388f0</td><td>6a51a0d2d8542f68</td><td>960fa728ab5133a3</td><td>6eef0b6c137a3be4</td></tr><tr><td>13</td><td>ba3bf0507efb2a98</td><td>a1f1651d39af0176</td><td>66ca593e82430e88</td><td>8cee8619456f9fb4</td></tr><tr><td>14</td><td>7d84a5c33b8b5ebe</td><td>e06f75d885c12073</td><td>401a449f56c16aa6</td><td>4ed3aa62363f7706</td></tr><tr><td>15</td><td>1bfedf72429b023d</td><td>37d0d724d00a1248</td><td>db0fead349f1c09b</td><td>075372c980991b7b</td></tr><tr><td>16</td><td>25d479d8f6e8def7</td><td>e3fe501ab6794c3b</td><td>976ce0bd04c006ba</td><td>c1a94fb6409f60c4</td></tr><tr><td>17</td><td>5e5c9ec2196a2463</td><td>68fb6faf3e6c53b5</td><td>1339b2eb3b52ec6f</td><td>6dfc511f9b30952c</td></tr><tr><td>18</td><td>cc814544af5ebd09</td><td>bee3d004de334afd</td><td>660f2807192e4bb3</td><td>c0cba85745c8740f</td></tr><tr><td>19</td><td>d20b5f39b9d3fbdb</td><td>5579c0bd1a60320a</td><td>d6a100c6402c7279</td><td>679f25fefb1fa3cc</td></tr><tr><td>20</td><td>8ea5e9f8db3222f8</td><td>3c7516dffd616b15</td><td>2f501ec8ad0552ab</td><td>323db5fafd238760</td></tr><tr><td>21</td><td>53317b483e00df82</td><td>9e5c57bbca6f8ca0</td><td>1a87562edf1769db</td><td>d542a8f6287effc3</td></tr><tr><td>22</td><td>ac6732c68c4f5573</td><td>695b27b0bbca58c8</td><td>e1ffa35db8f011a0</td><td>10fa3d98fd2183b8</td></tr><tr><td>23</td><td>4afcb56c2dd1d35b</td><td>9a53e479b6f84565</td><td>d28e49bc4bfb9790</td><td>e1ddf2daa4cb7e33</td></tr><tr><td>24</td><td>62fb1341cee4c6e8</td><td>ef20cada36774c01</td><td>d07e9efe2bf11fb4</td><td>95dbda4dae909198</td></tr></table>

Key Schedule: The cipher receives a 6ℓ-bit master key and initializes it to the state of the zero-th round key $\left( k _ { 0 } \right)$ . Then, it applies the bit permutation PB to compute the next round key, i.e., using the following permutation $P ,$ , the positions of the bits are changed. That is 

$$
k _ {r + 1} = \mathrm{PB} (k _ {r}) \text {with} k _ {r + 1 [ i ^ {\prime}, j ^ {\prime} ]} = k _ {r [ i, j ]},
$$

such that 

$$
(i ^ {\prime}, j ^ {\prime}) := P (i, j) \text {with} (6 i ^ {\prime} + j ^ {\prime}) \equiv (\beta \cdot (6 i + j) + \gamma) \bmod 6 \ell ,
$$

i.e., $i ^ { \prime }$ and $j ^ { \prime }$ are the quotient and remainder of dividing $\left( \beta \cdot ( 6 i + j ) + \gamma \right)$ mod $6 \ell$ to $^ { 6 , }$ respectively. The parameters $\beta$ and $\gamma$ are dependent on the block length of the cipher with the condition of $\operatorname* { g c d } ( \beta , 6 \ell ) = 1$ 

Instantiation: As already mentioned, SPEEDY is a family of block ciphers that allows instantiations of a wide range of block sizes and security levels. One may choose the block size of the encryption (6ℓ) by to the type of data blocks that need to be encrypted, and select the number of rounds (r) based on the necessary security level. By applying an appropriate $\alpha = ( \alpha _ { 1 } , \ldots , \alpha _ { 6 } )$ value with regards to the rationale explained in Section 5, SPEEDY-r-6ℓ is ready to use. 

To provide encryption of 64-bit blocks, which is the common instruction and data width in modern CPUs, we suggest to instantiate SPEEDY-r-192 with $\alpha = ( 1 , 5 , 9 , 1 5 , 2 1 , 2 6 )$ as the linear layer’s parameter. We leave the number of rounds to be chosen based on the required security level. That is, for 128- and 192-bit security levels, we recommend using $\mathbf { r } \geq 6$ and $\mathbf { r } \geq 7$ rounds, respectively. More details about our security claims are provided below. The security analysis and the implementation of this instance are discussed in Section 6 and Section 7, respectively. Furthermore, for this instance we suggest to use $\beta = 7 \ \mathrm { a n d } \ \gamma = 1$ for the key schedule parameters that the corresponding permutation P (given in Table 6) receives. 


Table 6: P bit-permutation for SPEEDY-r-192 with ℓ = 32, $\beta = 7$ and $\gamma = 1$


<table><tr><td>i</td><td>0</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td><td>7</td><td>8</td><td>9</td><td>10</td><td>11</td><td>12</td><td>13</td><td>14</td><td>15</td><td>16</td><td>17</td><td>18</td><td>19</td><td>20</td><td>21</td><td>22</td><td>23</td></tr><tr><td>P(i)</td><td>1</td><td>8</td><td>15</td><td>22</td><td>29</td><td>36</td><td>43</td><td>50</td><td>57</td><td>64</td><td>71</td><td>78</td><td>85</td><td>92</td><td>99</td><td>106</td><td>113</td><td>120</td><td>127</td><td>134</td><td>141</td><td>148</td><td>155</td><td>162</td></tr><tr><td>i</td><td>24</td><td>25</td><td>26</td><td>27</td><td>28</td><td>29</td><td>30</td><td>31</td><td>32</td><td>33</td><td>34</td><td>35</td><td>36</td><td>37</td><td>38</td><td>39</td><td>40</td><td>41</td><td>42</td><td>43</td><td>44</td><td>45</td><td>46</td><td>47</td></tr><tr><td>P(i)</td><td>169</td><td>176</td><td>183</td><td>190</td><td>5</td><td>12</td><td>19</td><td>26</td><td>33</td><td>40</td><td>47</td><td>54</td><td>61</td><td>68</td><td>75</td><td>82</td><td>89</td><td>96</td><td>103</td><td>110</td><td>117</td><td>124</td><td>131</td><td>138</td></tr><tr><td>i</td><td>48</td><td>49</td><td>50</td><td>51</td><td>52</td><td>53</td><td>54</td><td>55</td><td>56</td><td>57</td><td>58</td><td>59</td><td>60</td><td>61</td><td>62</td><td>63</td><td>64</td><td>65</td><td>66</td><td>67</td><td>68</td><td>69</td><td>70</td><td>71</td></tr><tr><td>P(i)</td><td>145</td><td>152</td><td>159</td><td>166</td><td>173</td><td>180</td><td>187</td><td>2</td><td>9</td><td>16</td><td>23</td><td>30</td><td>37</td><td>44</td><td>51</td><td>58</td><td>65</td><td>72</td><td>79</td><td>86</td><td>93</td><td>100</td><td>107</td><td>114</td></tr><tr><td>i</td><td>72</td><td>73</td><td>74</td><td>75</td><td>76</td><td>77</td><td>78</td><td>79</td><td>80</td><td>81</td><td>82</td><td>83</td><td>84</td><td>85</td><td>86</td><td>87</td><td>88</td><td>89</td><td>90</td><td>91</td><td>92</td><td>93</td><td>94</td><td>95</td></tr><tr><td>P(i)</td><td>121</td><td>128</td><td>135</td><td>142</td><td>149</td><td>156</td><td>163</td><td>170</td><td>177</td><td>184</td><td>191</td><td>6</td><td>13</td><td>20</td><td>27</td><td>34</td><td>41</td><td>48</td><td>55</td><td>62</td><td>69</td><td>76</td><td>83</td><td>90</td></tr><tr><td>i</td><td>96</td><td>97</td><td>98</td><td>99</td><td>100</td><td>101</td><td>102</td><td>103</td><td>104</td><td>105</td><td>106</td><td>107</td><td>108</td><td>109</td><td>110</td><td>111</td><td>112</td><td>113</td><td>114</td><td>115</td><td>116</td><td>117</td><td>118</td><td>119</td></tr><tr><td>P(i)</td><td>97</td><td>104</td><td>111</td><td>118</td><td>125</td><td>132</td><td>139</td><td>146</td><td>153</td><td>160</td><td>167</td><td>174</td><td>181</td><td>188</td><td>3</td><td>10</td><td>17</td><td>24</td><td>31</td><td>38</td><td>45</td><td>52</td><td>59</td><td>66</td></tr><tr><td>i</td><td>120</td><td>121</td><td>122</td><td>123</td><td>124</td><td>125</td><td>126</td><td>127</td><td>128</td><td>129</td><td>130</td><td>131</td><td>132</td><td>133</td><td>134</td><td>135</td><td>136</td><td>137</td><td>138</td><td>139</td><td>140</td><td>141</td><td>142</td><td>143</td></tr><tr><td>P(i)</td><td>73</td><td>80</td><td>87</td><td>94</td><td>101</td><td>108</td><td>115</td><td>122</td><td>129</td><td>136</td><td>143</td><td>150</td><td>157</td><td>164</td><td>171</td><td>178</td><td>185</td><td>0</td><td>7</td><td>14</td><td>21</td><td>28</td><td>35</td><td>42</td></tr><tr><td>i</td><td>144</td><td>145</td><td>146</td><td>147</td><td>148</td><td>149</td><td>150</td><td>151</td><td>152</td><td>153</td><td>154</td><td>155</td><td>156</td><td>157</td><td>158</td><td>159</td><td>160</td><td>161</td><td>162</td><td>163</td><td>164</td><td>165</td><td>166</td><td>167</td></tr><tr><td>P(i)</td><td>49</td><td>56</td><td>63</td><td>70</td><td>77</td><td>84</td><td>91</td><td>98</td><td>105</td><td>112</td><td>119</td><td>126</td><td>133</td><td>140</td><td>147</td><td>154</td><td>161</td><td>168</td><td>175</td><td>182</td><td>189</td><td>4</td><td>11</td><td>18</td></tr><tr><td>i</td><td>168</td><td>169</td><td>170</td><td>171</td><td>172</td><td>173</td><td>174</td><td>175</td><td>176</td><td>177</td><td>178</td><td>179</td><td>180</td><td>181</td><td>182</td><td>183</td><td>184</td><td>185</td><td>186</td><td>187</td><td>188</td><td>189</td><td>190</td><td>191</td></tr><tr><td>P(i)</td><td>25</td><td>32</td><td>39</td><td>46</td><td>53</td><td>60</td><td>67</td><td>74</td><td>81</td><td>88</td><td>95</td><td>102</td><td>109</td><td>116</td><td>123</td><td>130</td><td>137</td><td>144</td><td>151</td><td>158</td><td>165</td><td>172</td><td>179</td><td>186</td></tr></table>

We provide several test vectors for SPEEDY-r-192 encryption in Appendix C. 

Security Claim While SPEEDY can be instantiated with diferent block and key sizes, the default is 192 bit as it constitutes the least common multiple of 6 (our S-box width) and 64 (the instruction width in high-end CPUs). We expect that SPEEDY-r-192 achieves 128-bit security when iterated over $\mathbf { r } = 6$ rounds and full 192-bit security when iterated over $\mathbf { r } = 7$ rounds, while the $x = 5$ round variant already provides a decent security level that is suficient for many practical applications $\left( \geq 2 ^ { 1 2 8 } \right.$ time complexity when data complexity is limited to $\leq 2 ^ { 6 \overset { . } { 4 } } )$ ). Compared to the security claims made for example for PRINCE $( \geq 2 ^ { 1 2 7 - n }$ time complexity when data complexity is limited $\tan \leq 2 ^ { n } )$ or PRINCEv2 $( \geq 2 ^ { 1 1 2 }$ time complexity when data complexity is limited to $\leq 2 ^ { 5 0 } )$ the security level claimed by SPEEDY-5-192 is already superior. 

## 5 Design Rationale

The primary criterion for the design of SPEEDY is to use round operations with a low latency that still provide good enough cryptographic properties to provide a secure encryption with a small number of rounds. To achieve this goal, we applied the ultra low-latency S-box found in Section 3. While the design approach for the S-box is described in Section 3, all details regarding the design choices for the other round operations are explained in the following. 

MixColumns: It is clear that the latency cost (in terms of XOR gate depth) of XORing n bits, $\mathrm { i . e . , } x _ { 0 } \oplus . . . \oplus x _ { n - 1 }$ is equal to $d = \left\lfloor \log _ { 2 } n \right\rfloor$ . This means that XORing n bits with $2 ^ { d - 1 } < n \leq 2 ^ { d }$ , has the same cost for all n values with respect to the latency of the circuit (considering identical topology). Therefore, to use the maximum capacity of the given latency, it is prudent to choose $n = 2 ^ { d }$ 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-19/817dee3f-a0b5-4f3e-bc0f-da403bef3baa/ea33e38cdaa449bc684a661e5ebdc56c3c3354072919181f123e6c475baa7b1d.jpg)



Figure 4: Implementation of each output bit of the merged function $\mathtt { A } _ { k _ { r + 1 } } \circ \mathtt { A } _ { c _ { r } } \circ$ MC of the SPEEDY design.


In the design of SPEEDY, since the $\mathsf { A } _ { k _ { r + 1 } }$ operation from round $r + 1$ occurs right after the $\mathtt { A } _ { c _ { \tau } }$ and MC operations from the r-th round, it is possible to merge all three operations. Considering that x and y from $\mathbb { F } _ { 2 } ^ { \ell \times 6 }$ are the input and output of the merged $\mathtt { A } _ { k _ { r + 1 } } \circ \mathtt { A } _ { c _ { r } } \circ$ MC operation, respectively, then each output bit can be calculated as 

$$
y _ {[ i, j ]} = x _ {[ i, j ]} \oplus x _ {[ i + \alpha_ {1}, j ]} \oplus x _ {[ i + \alpha_ {2}, j ]} \oplus x _ {[ i + \alpha_ {3}, j ]} \oplus x _ {[ i + \alpha_ {4}, j ]} \oplus x _ {[ i + \alpha_ {5}, j ]} \oplus x _ {[ i + \alpha_ {6}, j ]} \oplus (k _ {r + 1 [ i, j ]} \oplus c _ {r [ i, j ]}).
$$

Hence, it is possible to implement the whole $\mathtt { A } _ { k _ { r + 1 } } \circ \mathtt { A } _ { c _ { r } } \circ \mathtt { M C }$ as a merged function within three XOR gate levels. Note that since the input $k _ { r + 1 [ i , j ] }$ is not in the critical path of the circuit, $k _ { r + 1 [ i , j ] }$ and $c _ { r \left[ i , j \right] }$ can be combined with each other beforehand. Depending on the value of the round constant bit, we actually only need to use $k _ { r + 1 [ i , j ] }$ itself or its inverted value $\neg k _ { r + 1 [ i , j ] }$ . Figure 4 depicts the corresponding circuit to implement each output bit of the merged function. Please note that the fan-out of each XOR gate in this circuit is 1. It is important to consider that for CMOS technologies where the XNOR gate is significantly faster than the XOR gate (such as NanGate 45 nm), it is easily possible to implement this linear layer with only XNOR gates instead of XORs and simply exchange the bufers and inverters of the next S-box stage to revert its inverted output. 

For the MC operation, we decided to use the same binary cyclic matrix with polynomial representation of $1 + z ^ { \alpha _ { 1 } } + \ldots + z ^ { \alpha _ { w - 1 } }$ and multiply it with each column of the state. Therefore, each output bit of the MC operation is the XOR of w input bits. As explained above, the optimal choices for w are 3, 7, 15 and so on, so that it is possible to implement the above mentioned merged function with 2, 3, 4 XOR gate levels, respectively. While in PRINCE, MIDORI and QARMA block ciphers, this technique of merging is used by applying cyclic matrices of $w = 3$ and repeated after each S-box layer, we found that it is a good trade-of to use cyclic matrices with $w = 7$ , but only after each second S-box layer, which is efectively cheaper from a latency cost perspective. 

For each SPEEDY-r-6ℓ version of the cipher, we need to find a bijective $\ell \times \ell$ binary cyclic matrix M with polynomial representation of $1 + z ^ { \alpha _ { 1 } } + \ldots + z ^ { \alpha _ { 6 } }$ . Finding an appropriate bijective cyclic matrix with $w = 7$ being an odd integer, is quite possible for wide range of ℓ. But, since the value of $\alpha = ( \alpha _ { 1 } , \ldots , \alpha _ { 6 } )$ is always dependent on the value of $\ell ,$ we leave it as a parameter of the cipher’s instantiation. 

Since, the probability of M being a non-singular matrix is high, we can add extra criteria regarding the choice of the α parameter. 

• All values for $\alpha _ { 1 } , ~ \alpha _ { 2 } - \alpha _ { 1 } , ~ \alpha _ { 3 } - \alpha _ { 2 } , ~ \alpha _ { 4 } - \alpha _ { 3 } , ~ \alpha _ { 5 } - \alpha _ { 4 } , ~ \alpha _ { 6 } - \alpha _ { 5 }$ and $\ell - \alpha _ { 6 }$ need to be smaller or equal to 6. The reason for this criterion is explained later, in the corresponding paragraph for ShiftColumns. Note that this criterion is only possible for $\ell \leq 4 2$ 

• Maximum branch number: Branch number of a matrix is defined as 

$$
b n := \min _ {x \in \mathbb {F} _ {2} ^ {\ell} \setminus \{0 \}} \mathrm{hw} (x) + \mathrm{hw} (M \times x ^ {T}),
$$

where hw denotes the Hamming weight of a binary array. In case of a bijective $\ell \times \ell$ binary cyclic matrix M with polynomial representation of $1 + z ^ { \alpha _ { 1 } } + \ldots + z ^ { \alpha _ { w - 1 } }$ , the branch number cannot be higher than $w + 1$ . In our case, we restrict the choice of the α parameter to the ones which provide maximum branch number, i.e., 8. 

• For the corresponding matrix M of parameter $\alpha = ( \alpha _ { 1 } , \ldots , \alpha _ { 6 } )$ , we build a binary table H such that the element in the position $( i , j )$ is 1, if and only if there is an $x \in \mathbb { F } _ { 2 } ^ { \ell } \setminus \{ 0 \}$ with $\operatorname { h w } ( x ) = i$ and hw $( M \times x ^ { T } ) = j$ . Then, we compute the following three numbers: 

$$
\begin{array}{l}b n_{3} = \min_{\substack{i_{1},i_{2},i_{3}\\ H[i_{1}][i_{2}] = H[i_{2}][i_{3}] = 1}}i_{1} + i_{2} + i_{3}  ,\\ bn_{4} = \min_{\substack{i_{1},i_{2},i_{3},i_{4}\\ H[i_{1}][i_{2}] = H[i_{2}][i_{3}] = H[i_{3}][i_{4}] = 1}}i_{1} + i_{2} + i_{3} + i_{4}  ,\\ bn_{5} = \min_{\substack{i_{1},i_{2},i_{3},i_{4},i_{5}\\ H[i_{1}][i_{2}] = H[i_{2}][i_{3}] = H[i_{3}][i_{4}] = H[i_{4}][i_{5}] = 1}}i_{1} + i_{2} + i_{3} + i_{4} + i_{5}  . \end{array}\tag{5}
$$

As explained later in Section 6, larger values for $b n _ { \tau }$ lead to a stronger resistance of the r-round SPEEDY against diferential and linear attacks. Therefore, for all the possible choices of α which are meeting the first two criteria, we compute the above $b n _ { r }$ numbers and choose one of the corresponding α values which leads to the maximum bn values. 

It is noteworthy that the branch number bn is the same as $b n _ { 2 }$ defined as 

$$
bn_{2} = \min_{\substack{i_{1},i_{2}\\ H[i_{1}][i_{2}] = 1}}i_{1} + i_{2}  .
$$

Besides, $b n _ { r }$ with $r > 2$ can be considered as an extension for the definition of branch number, and hereafter, we will call it a higher-order branch number. 

In the case of SPEEDY-r-192, with $\ell \ = \ 3 2$ , we applied the above criteria and end up with 30 choices from which we choose the first one that is $\alpha = ( 1 , 5 , 9 , 1 5 , 2 1 , 2 6 )$ with $b n _ { 3 } = 1 3 , \ b n _ { 4 } = 2 0$ , and $b n _ { 5 } = 2 5$ . It is important to mention that the corresponding matrix for inverse of the MC operation is a cyclic matrix with $w = 1 9$ and $\boldsymbol { \alpha } ^ { - 1 } = ( \bar { 4 } , 5 , 6 , 7 , 1 0 , 1 2 , 1 4 , 1 5 , 1 6 , 1 8 , 1 9 , 2 0 , 2 1 , 2 2 , 2 3 , 2 4 , 2 5 , 2 8 )$ 

ShiftColumns: The existence of the first SC operation, right after the first SB makes it possible that input bits of each S-box in the second SB operation are all from the outputs of diferent S-boxes of the first SB operation. Therefore, since the applied S-box has the full difusion property (in both straight and inverse direction), each output bit of $\mathtt { S B } \circ \mathtt { S C }$ ◦ SB is a function of 36 consecutive input bits. Namely, for $\mathbf { S B } \circ \mathbf { S C } \circ \mathbf { S B }$ , the output bit in the position $[ i , j ]$ is a function of all input bits in the position of the form $[ i + p , q ]$ with $0 \leq p , q < 6 $ while for $( \mathtt { S B } \circ \mathtt { S C } \circ \mathtt { S B } ) ^ { - 1 }$ , the output bit $[ i , j ]$ is a function of all input bits of the form $[ i - p , q ]$ 

By considering the first criterion for MixColumns, namely that $\alpha _ { 1 } , \alpha _ { 2 } - \alpha _ { 1 } , \alpha _ { 3 } - \alpha _ { 2 } , \alpha _ { 4 } - \alpha _ { 3 } ,$ $\alpha _ { 5 } - \alpha _ { 4 } , \alpha _ { 6 } - \alpha _ { 5 }$ and $\ell - \alpha _ { 6 }$ are all smaller or equal to $6 ,$ it means that the output bit of $\mathtt { M C } \circ \mathtt { S B } \circ \mathtt { S C } \circ \mathtt { S B }$ and equivalently, output of one key-less round function $\mathtt { M C } \circ \mathbf { S C } \circ \mathbf { S B } \circ \mathbf { S C } \circ \mathbf { S B }$ is dependent on the whole $6 \ell$ input bits. The same holds for $( \mathsf { M C } \circ \mathsf { S B } \circ \mathsf { S C } \circ \mathsf { S B } ) ^ { - 1 }$ in the decryption side, hence, the input of one key-less round function is dependent on the whole 6ℓ output bits. 

Moreover, the same arguments hold for inserting the second SC, right after the second SB operation, which means that each output bit of SB◦MC◦SC◦SB depends on the whole 6ℓ input bits which equivalently holds for the rotated key-less round function SC ◦ SB ◦ MC ◦ SC ◦ SB. Altogether, one key-less round function or rotated round function, in both encryption and decryption directions, provides full difusion. In other words, in a key recovery attack, to compute one output bit of those functions, the attacker needs to know the value of the whole input state. Note that knowing the value for the whole input state of these functions requires knowing the whole state of the round key. This means, if the attacker wants to extend a distinguisher by appending one complete round (or rotated round) function, to do a key recovery attack, he needs to guess the whole 6ℓ bits of the key. 

It is important to mention that since existence of any key-independent linear operation right before the ciphertext does not add any security to the encryption, we exclude the MC and the second SC operations from the last round. 

Key Schedule: Since the main target of our design is to provide a low-latency encryption routine, and since other cost factors of the implementation such as area or energy consumption of the circuits are only secondary priorities, one can apply a key schedule built from costly operations. Yet, since we do not aim for related-key security, and since the round function has a strong difusion, we found that using a linear key schedule is suficient for our purposes. Besides, updating round keys by a bit-permutation function in an unrolled implementation has no latency, area or energy costs, thus we decided to use such a key schedule. Furthermore, we wanted to use a bit-permutation such that it is easy to generalize for all SPEEDY-r-6ℓ members. To do so, we chose the general afine mapping in the finite integer field of $\{ 0 , \ldots , 6 \ell - 1 \}$ , that the permutation P maps x, an element of this field, to $P ( x ) = \beta x + \gamma$ mod 6ℓ. The only requirement for P being a bijection is that β and 6ℓ need to be co-prime, i.e., gcd $( \beta , 6 \ell ) = 1$ 

## 6 Security Analysis

In this section, we provide details about the cryptographic properties of the SPEEDY family of block ciphers. We start with diferential, linear and algebraic properties of the S-box S and expand them over a round function of the cipher. By applying properties for the round function, we discuss the security of an r round structure of SPEEDY. 

Cryptographic Properties of the S-box: The S-box S, presented in Section 3, is the heart of the SPEEDY design and it needs to be studied in detail. As described before the uniformity and linearity of S is equal to 8 and 24, respectively. This means that the maximum probability of diferentials over S is $8 \cdot 2 ^ { - 6 } = { \overline { { 2 ^ { - 3 } } } }$ and the maximum absolute correlation of linear approximations is $2 4 \cdot 2 ^ { - 6 } = 3 \cdot 2 ^ { - 3 }$ (equally means that the maximum potential of linear approximations is $( 3 \cdot 2 ^ { - 3 } ) ^ { 2 } = 9 \cdot 2 ^ { - 6 } \approx 2 ^ { - 2 \cdot 8 3 } )$ . As one important part of the Diferential Distribution Table (DDT) and Linear Approximation Table (LAT), we present the 1-bit to 1-bit diferentials and linear approximations in Table 7. In more detail, entry $( i , j )$ of the 1-bit to 1-bit DDT denotes the probability that having only one active bit in the position i of the S-box inputs leads to only one active bit in the position $j$ of the S-box output. In case of 1-bit to 1-bit LAT, entry $( i , j )$ of the table denotes the absolute correlation value for the $x _ { i } = y _ { j }$ linear approximation. 

Even though, one of the criteria for building the low-latency S-box was to provide full dependency of the output bits on the input bits, this is not suficient to provide all information about algebraic properties of the function. We provide the algebraic normal form (ANF) representation of both S and $S ^ { - 1 }$ below. As shown, not only all the input/output variables are non-linearly involved in all the output/input coordinates $( { \mathrm { i . e . } }$ , the S-box provides full difusion in both straight and inverse directions), each coordinate function is quite dense with respect to the number of involved terms. Another interesting information is that the ANF degree for coordinates of S is 5, 3, 3, 3, 4 and 5, respectively, while in the case of S<sup>−1</sup>, these numbers are 5, 4, 5, 4, 5 and 5, respectively. 

$\begin{array}{rl} & y_0 = x_3\oplus x_5x_3\oplus x_5x_4x_3x_2\oplus x_5x_4x_1\oplus x_5x_4x_3x_2x_1\oplus x_1x_0\oplus x_5x_4x_1x_0\oplus x_3x_1x_0\oplus \\ & \qquad x_5x_4x_3x_1x_0\\ & y_1 = x_3\oplus x_4x_3\oplus x_5x_4x_3\oplus x_5x_3x_2\oplus x_1\oplus x_3x_1\oplus x_5x_2x_0\oplus x_1x_0\oplus x_3x_1x_0\\ & y_2 = 1\oplus x_5\oplus x_5x_2\oplus x_4x_2\oplus x_3x_2\oplus x_4x_3x_2\oplus x_0\oplus x_5x_0\oplus x_4x_0\oplus x_4x_3x_0\oplus x_2x_0\oplus \\ & \qquad x_5x_2x_0\oplus x_3x_1x_0,\\ & y_3 = x_2\oplus x_3x_2\oplus x_3x_1\oplus x_5x_0\oplus x_2x_0\oplus x_5x_2x_0\oplus x_4x_2x_0\oplus x_3x_2x_0\oplus x_3x_1x_0\\ & y_4 = x_5x_4\oplus x_1\oplus x_4x_1\oplus x_2x_1\oplus x_4x_2x_1\oplus x_0\oplus x_5x_4x_0\oplus x_4x_3x_0\oplus x_3x_2x_0\oplus x_4x_3x_2x_0\oplus \\ & \qquad x_1x_0\oplus x_4x_1x_0\oplus x_2x_1x_0\oplus x_4x_2x_1x_0,\\ & y_5 = x_4\oplus x_5x_2\oplus x_4x_2\oplus x_4x_1\oplus x_4x_2x_1\oplus x_3x_0\oplus x_4x_3x_0\oplus x_5x_3x_2x_0\oplus x_4x_3x_2x_0\oplus \\ & \qquad x_3x_{1}x_{0}\oplus x_{4}x_{3}x_{1}x_{0}\oplus x_{2}x_{1}x_{0}\oplus x_{5}x_{2}x_{1}x_{0}\oplus x_{5}x_{3}x_{2}x_{1}x_{0}\oplus x_{4}x_{3}x_{2}x_{1}x_{0}. \end{array}$ 

$x_0 = y_4 \oplus y_5y_4 \oplus y_5y_4y_2 \oplus y_5y_1 \oplus y_4y_1 \oplus y_5y_4y_3y_1 \oplus y_5y_3y_2y_1 \oplus y_4y_3y_2y_1 \oplus y_5y_4y_3y_2y_1 \oplus y_5y_0 \oplus y_5y_4y_0 \oplus y_2y_0 \oplus y_4y_2y_0 \oplus y_3y_2y_0 \oplus y_4y_3y_2y_0 \oplus y_5y_1y_0 \oplus y_2y_1y_0$ 

$x_{1} = y_{5}y_{3}\oplus y_{5}y_{4}y_{3}\oplus y_{5}y_{3}y_{2}\oplus y_{5}y_{4}y_{3}y_{2}\oplus y_{4}y_{1}\oplus y_{5}y_{4}y_{1}\oplus y_{3}y_{1}\oplus y_{4}y_{3}y_{1}\oplus y_{2}y_{1}\oplus$ $y_{4}y_{2}y_{1}\oplus y_{3}y_{2}y_{1}\oplus y_{4}y_{3}y_{2}y_{1}\oplus y_{4}y_{0}\oplus y_{5}y_{4}y_{0}\oplus y_{3}y_{0}\oplus y_{4}y_{3}y_{0}\oplus y_{5}y_{4}y_{3}y_{0}\oplus y_{2}y_{0}\oplus$ $y_{5}y_{2}y_{0}\oplus y_{4}y_{2}y_{0}\oplus y_{3}y_{2}y_{0}\oplus y_{5}y_{3}y_{2}y_{0}\oplus y_{4}y_{3}y_{2}y_{0}\oplus y_{4}y_{1}y_{0}\oplus y_{5}y_{4}y_{1}y_{0}\oplus y_{3}y_{1}y_{0}\oplus$ $y_{4}y_{3}y_{1}y_{0},$ 

$x_{2} = y_{5}\oplus y_{5}y_{4}\oplus y_{3}\oplus y_{5}y_{3}\oplus y_{4}y_{3}\oplus y_{5}y_{2}\oplus y_{4}y_{2}\oplus y_{5}y_{3}y_{2}\oplus y_{5}y_{3}y_{1}\oplus y_{5}y_{2}y_{1}\oplus y_{4}y_{2}y_{1}\oplus$ $y_{5}y_{4}y_{2}y_{1}\oplus y_{5}y_{4}y_{3}y_{2}y_{1}\oplus y_{0}\oplus y_{4}y_{0}\oplus y_{5}y_{4}y_{0}\oplus y_{3}y_{0}\oplus y_{4}y_{3}y_{0}\oplus y_{5}y_{4}y_{3}y_{0}\oplus y_{2}y_{0}\oplus$ $y_{5}y_{4}y_{2}y_{0}\oplus y_{5}y_{3}y_{2}y_{0}\oplus y_{5}y_{1}y_{0}\oplus y_{5}y_{2}y_{1}y_{0}\oplus y_{4}y_{2}y_{1}y_{0},$ 

$x_{3} = y_{5}\oplus y_{5}y_{4}\oplus y_{5}y_{2}\oplus y_{5}y_{4}y_{2}\oplus y_{1}\oplus y_{5}y_{1}\oplus y_{4}y_{1}\oplus y_{3}y_{1}\oplus y_{5}y_{3}y_{1}\oplus y_{2}y_{1}\oplus y_{4}y_{2}y_{1}\oplus$ $y_{5}y_{4}y_{2}y_{1}\oplus y_{3}y_{2}y_{1}\oplus y_{4}y_{3}y_{2}y_{1}\oplus y_{0}\oplus y_{5}y_{0}\oplus y_{4}y_{0}\oplus y_{5}y_{2}y_{0}\oplus y_{1}y_{0}\oplus y_{5}y_{1}y_{0}\oplus$ $y_{4}y_{1}y_{0}\oplus y_{3}y_{1}y_{0}\oplus y_{5}y_{3}y_{1}y_{0}\oplus y_{4}y_{3}y_{1}y_{0}\oplus y_{2}y_{1}y_{0}\oplus y_{3}y_{2}y_{1}y_{0},$ 

$x_{4} = y_{5}y_{4}\oplus y_{3}\oplus y_{5}y_{3}\oplus y_{4}y_{3}\oplus y_{5}y_{4}y_{3}\oplus y_{5}y_{2}\oplus y_{5}y_{4}y_{2}\oplus y_{3}y_{2}\oplus y_{5}y_{4}y_{3}y_{2}\oplus y_{5}y_{3}y_{1}\oplus$ $y_{2}y_{1}\oplus y_{4}y_{2}y_{1}\oplus y_{5}y_{4}y_{2}y_{1}\oplus y_{3}y_{2}y_{1}\oplus y_{5}y_{3}y_{2}y_{1}\oplus y_{0}\oplus y_{4}y_{0}\oplus y_{3}y_{0}\oplus y_{5}y_{3}y_{0}\oplus$ $y_{4}y_{3}y_{0}\oplus y_{5}y_{4}y_{3}y_{0}\oplus y_{5}y_{2}y_{0}\oplus y_{4}y_{2}y_{0}\oplus y_{5}y_{4}y_{2}y_{0}\oplus y_{3}y_{2}y_{0}\oplus y_{1}y_{0}\oplus y_{2}y_{1}y_{0}\oplus$ $y_{4}y_{2}y_{1}y_{0}\oplus y_{4}y_{3}y_{2}y_{1}y_{0},$ 

$x_{5} = 1\oplus y_{4}\oplus y_{5}y_{4}\oplus y_{3}\oplus y_{5}y_{3}\oplus y_{2}\oplus y_{4}y_{2}\oplus y_{5}y_{4}y_{2}\oplus y_{3}y_{2}\oplus y_{4}y_{1}\oplus y_{5}y_{4}y_{1}\oplus y_{4}y_{3}y_{1}\oplus$ $y_{5}y_{4}y_{3}y_{1}\oplus y_{5}y_{2}y_{1}\oplus y_{4}y_{2}y_{1}\oplus y_{5}y_{4}y_{2}y_{1}\oplus y_{5}y_{3}y_{2}y_{1}\oplus y_{0}\oplus y_{4}y_{0}\oplus y_{3}y_{0}\oplus y_{5}y_{3}y_{0}\oplus$ $y_{4}y_{3}y_{0}\oplus y_{5}y_{4}y_{3}y_{0}\oplus y_{2}y_{0}\oplus y_{4}y_{2}y_{0}\oplus y_{3}y_{2}y_{0}\oplus y_{5}y_{4}y_{1}y_{0}\oplus y_{5}y_{3}y_{1}y_{0}\oplus y_{5}y_{2}y_{1}y_{0}\oplus$ $y_{3}y_{2}y_{1}y_{0}\oplus y_{4}y_{3}y_{2}y_{1}y_{0}$ 

Cryptographic Properties of SB ◦ SC ◦ SB: Since in the round function of SPEEDY, two SB operations are connected through the SC operation which is a simple bit permutation, it is necessary to look at the properties of this combination. We first investigate the 1-bit to 1-bit diferentials and linear approximations of $\mathbf { S B } \circ \mathbf { S C } \circ \mathbf { S B }$ . Since each input bit of the second SB operation comes from a diferent first-stage S-box, 1-bit to 1-bit transitions over SB ◦ SC ◦ SB are possible if and only if the transitions over the first and second SB operations, both are 1-bit to 1-bit transitions. Besides, without any extra assumption (such as independency between the state bits), it can be proven that probability or correlation of this 1-bit to 1-bit transitions over $\mathrm { S B } \circ \mathsf { S C } \circ \mathsf { S B }$ is the multiplication of probabilities or correlations over two active S-boxes (one from the first SB and another from the second SB operation). 


Table 7: 1-bit to 1-bit diferential probabilities and linear correlations of the SPEEDY S-box.



diferential (×2<sup>−5</sup>)


<table><tr><td>i\j</td><td>0</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td></tr><tr><td>0</td><td>-</td><td>1</td><td>3</td><td>2</td><td>1</td><td>1</td></tr><tr><td>1</td><td>4</td><td>3</td><td>4</td><td>4</td><td>-</td><td>-</td></tr><tr><td>2</td><td>1</td><td>1</td><td>3</td><td>3</td><td>1</td><td>1</td></tr><tr><td>3</td><td>1</td><td>3</td><td>-</td><td>2</td><td>3</td><td>-</td></tr><tr><td>4</td><td>2</td><td>2</td><td>4</td><td>4</td><td>2</td><td>1</td></tr><tr><td>5</td><td>2</td><td>4</td><td>2</td><td>4</td><td>-</td><td>2</td></tr></table>


linear (×2<sup>−4</sup>)


<table><tr><td><eq>i\backslash j</eq></td><td>0</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td></tr><tr><td>0</td><td>3</td><td>-</td><td>4</td><td>-</td><td>4</td><td>4</td></tr><tr><td>1</td><td>6</td><td>4</td><td>4</td><td>4</td><td>2</td><td>4</td></tr><tr><td>2</td><td>1</td><td>-</td><td>-</td><td>4</td><td>4</td><td>6</td></tr><tr><td>3</td><td>6</td><td>4</td><td>4</td><td>-</td><td>6</td><td>2</td></tr><tr><td>4</td><td>4</td><td>4</td><td>-</td><td>4</td><td>-</td><td>3</td></tr><tr><td>5</td><td>4</td><td>4</td><td>4</td><td>4</td><td>4</td><td>5</td></tr></table>

Since SC does not change the column position of active bits, it is easily possible to compute these probabilities. Table 8 presents the 1-bit to 1-bit diferential probabilities and linear correlations over SB◦SC◦SB such that entry [i, j] denotes the maximum possible probabilities or linear correlations that an active input bit in the column i transits to an active output bit in the column j. To compute these values, we used the following equation which $T _ { 1 }$ and $T _ { 2 }$ denote the Table 7 and Table 8, respectively. 

$$
T _ {2} [ i, j ] = \max _ {k} T _ {1} [ i, k ] \cdot T _ {1} [ k, j ].
$$

Note that the maximum entry for diferential transitions is $2 ^ { - 6 }$ and for linear transitions it is $1 5 \cdot 2 ^ { - 7 } \approx 2 ^ { - 3 }$ . We are only interested in 1-bit to 1-bit transitions, because the probability or the correlation of such transitions are among the highest ones and also because based on such transitions, we can build diferential or linear characteristics with a high diferential probability or linear correlation. 

Again due to the fact that SC does not change the column position of the bits and each input bit of the second SB is the output of a diferent S-box, it is possible to compute the algebraic degree of SB ◦ SC ◦ SB. The degree of any output bit in the columns $0 , 1 , \ldots$ . and 5 is equal to 19, 15, 13, 13, 13 and 20, respectively. 

It is important to mention that replacing the current S-box with another bit-permutation equivalent S-box will change diferential, linear and algebraic properties of SB ◦ SC ◦ SB. While in Section 3, we ended up with a bit-permutation equivalency class of S-boxes, we tried all the S-boxes of this class to find an S-box such that the maximum entry in Table 8 and also the number of entries with maximum value are as small as possible. Moreover, we want the minimum algebraic degree over SB ◦ SC ◦ SB coordinates to be as large as possible. Note that due to the structure of the round function, since encryption with S-box $P _ { o u t } \circ$ $S \circ P _ { i n }$ is identical to encryption with S-box $P _ { i n } \circ P _ { o u t } \circ S$ (up to a column permutation in the state of plaintext, ciphertext, round key and round constants), we can consider one of them to be the identity bit-permutation and only need to choose the other one. 

Diferential and Linear Attacks Since there are 1-bit to 1-bit diferential and linear approximations over SB ◦ SC ◦ SB and the corresponding probability or correlation of those transitions are quite significant, it is necessary to choose a strong MC operation. The criterion of having branch number bn = 8 ensures that the maximum expected diferential probability (EDP) of diferential trails and the maximum expected linear potential (ELP) of linear trails over two rounds of SPEEDY is equal to $( 2 ^ { - 6 } ) ^ { 8 } = 2 ^ { - 4 8 } .$ 


Table 8: 1-bit to 1-bit diferential probabilities and linear correlations over $\mathrm { S B } \circ \mathsf { S C } \circ \mathsf { S B }$



diferential $( \times 2 ^ { - 1 0 } )$


<table><tr><td>i\j</td><td>0</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td></tr><tr><td>0</td><td>4</td><td>6</td><td>9</td><td>9</td><td>6</td><td>3</td></tr><tr><td>1</td><td>12</td><td>12</td><td>12</td><td>12</td><td>12</td><td>4</td></tr><tr><td>2</td><td>4</td><td>9</td><td>9</td><td>9</td><td>9</td><td>3</td></tr><tr><td>3</td><td>12</td><td>9</td><td>12</td><td>12</td><td>6</td><td>3</td></tr><tr><td>4</td><td>8</td><td>12</td><td>12</td><td>12</td><td>12</td><td>4</td></tr><tr><td>5</td><td>16</td><td>12</td><td>16</td><td>16</td><td>12</td><td>4</td></tr></table>

<table><tr><td colspan="7">linear (<eq>\times 2^{-8}</eq>)</td></tr><tr><td><eq>i\backslash j</eq></td><td>0</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td></tr><tr><td>0</td><td>16</td><td>16</td><td>16</td><td>16</td><td>16</td><td>24</td></tr><tr><td>1</td><td>24</td><td>16</td><td>24</td><td>16</td><td>24</td><td>24</td></tr><tr><td>2</td><td>24</td><td>24</td><td>24</td><td>24</td><td>24</td><td>30</td></tr><tr><td>3</td><td>24</td><td>24</td><td>24</td><td>24</td><td>24</td><td>24</td></tr><tr><td>4</td><td>24</td><td>16</td><td>16</td><td>16</td><td>24</td><td>16</td></tr><tr><td>5</td><td>24</td><td>20</td><td>20</td><td>20</td><td>24</td><td>25</td></tr></table>

To discuss the resistance of r-round SPEEDY, we use the $h i g h e r – o r d e r$ branch number $b n _ { r }$ defined in Equation 5 to have an overview about the minimum number of active S-boxes in diferential or linear trails. Therefore, using this estimation the maximum EDP of diferentials and the ELP of linear trails over r-round SPEEDY is estimated by $2 ^ { - 6 \cdot b n _ { r } }$ In case of SPEEDY-r-192, with the recommended α parameter, we have 

$$
b n _ {3} = 1 3, \quad b n _ {4} = 2 0, \quad b n _ {5} = 2 5, \quad b n _ {6} = 3 2.
$$

Hence, we estimate that EDP (resp. ELP) of any diferential (resp. linear) trails over $^ { 3 , }$ 4, 5 and 6 rounds is smaller than $\bar { 2 } ^ { - 7 8 } , 2 ^ { - 1 2 0 } , 2 ^ { - 1 5 0 } \mathrm { a n d 2 ^ { - 1 9 2 } }$ . Actually, assuming that all the 1-bit to 1-bit diferential or linear transitions through the S-box are possible, and by considering that there are at most 8 active words (of 6-bit) per state of operations, we searched for the minimum number of active S-boxes. We found that this number is 13, 23 and 35 for 2, 3 and 4 rounds. Assuming that all these 1-bit to 1-bit transitions occur with diferential probability (or linear potential) of $2 ^ { - 3 }$ , the EDP (resp. ELP) of any diferential (resp. linear) trails over 2, 3 and 4 rounds is smaller than $\dot { 2 } ^ { - 3 \bar { 9 } } , 2 ^ { - 6 9 }$ and $2 ^ { - 1 0 5 }$ . We emphasize that these values are an upper bound, which means that a trail with such EDP or ELP must not necessarily exist. 

Higher-Order Diferential, Integral and Cube Attacks SPEEDY’s round function has a strong difusion and high algebraic degree. While, we investigate these properties for one complete round precisely, for a larger number of rounds, we expect that the ANF representation would be dense with respect to the number of involved terms. Therefore, we believe that these attacks are weaker than diferential and linear attacks and less of a concern. 

Number of Rounds For a low-latency block cipher, a large security margin is not reasonable and is usually considered as wasteful. Since the attacker cannot add more than one round to extend a distinguisher and therefore to use the distinguisher in a key recovery attack, we believe a security margin of one round is suficient. Therefore, we recommend to choose the number of rounds with respect to the required security level of the block cipher’s application. For example, in case of the SPEEDY-r-192 instance, we recommend to use SPEEDY-6-192 and SPEEDY-7-192 for 128-bit and 192-bit security levels, respectively, while for more practical applications, such as a security level of $2 ^ { 1 2 8 }$ time and $\overline { { 2 ^ { 6 4 } } }$ data complexity, we recommend to use S 192. 

Impossible Diferential and Zero-Correlation Linear-Hull Attacks One active bit, with respect to both diferentials and linear correlations, and in both forward and backward directions can propagate to all the state bits over one (rotated) key-less SPEEDY round function and more importantly, none of this activeness is deterministic. But, it should be noted that the activeness of these bits can be related to each other if the last operation is MC. Therefore, by combining one round propagation in the forward direction and one round propagation in the backward direction, it might be possible to find impossible diferentials or zero-correlation linear-hulls over two (rotated) key-less round functions. But, if we add one SB operation in the middle, we ensure that there are no such distinguishers; in other words, there are no impossible diferentials or zero-correlation linear-hulls over 

$$
\left(\mathrm{SB} \circ \mathrm{SC} \circ \mathrm{SB} \circ \mathrm{SC} \circ \mathrm{MC}\right) \circ \mathrm{SB} \circ \left(\mathrm{SC} \circ \mathrm{SB} \circ \mathrm{SC} \circ \mathrm{MC} \circ \mathrm{SB}\right)
$$

$$
(\mathrm{SB} \circ \mathrm{SC} \circ \mathrm{MC} \circ \mathrm{SB} \circ \mathrm{SC}) \circ \mathrm{SB} \circ (\mathrm{SC} \circ \mathrm{MC} \circ \mathrm{SB} \circ \mathrm{SC} \circ \mathrm{SB}).
$$

Therefore, by applying the 2-round distinguisher and extending by one round for key recovery, it might be possible to have a successful attack on 3-round SPEEDY, but we expect that more than 3 rounds are secure against those attacks. 

Meet-in-the-Middle Attack The maximum number of attacked rounds using meet-inthe-middle technique can be evaluated considering the maximum length of three features: partial-matching, initial structure and splice-and-cut. For partial-matching, the number of rounds in both forward and backward directions cannot reach the full difusion rounds which for SPEEDY in both directions is smaller than one round. The condition for the initial structure is that the key diferential trails in both forward and backward directions do not share active non-linear components. As any key diferential in SPEEDY afects the whole state after one complete round in both directions, there is no such diferential which shares active S-box(es) in more than one round. Therefore, it only works up to one round. Splice-and-cut may extend the number of attacked rounds up to the number of full difusion rounds, i.e., again one round. Thus, it is not possible for the attacker to mount a successful meet-in-the-middle attack on a (2+1+1) = 4-round SPEEDY. 

Implementation Attacks The protection of SPEEDY against implementation attacks like timing, power analysis or fault injection attacks is not a focus of this work. Clearly, a straightforward and unprotected implementation of SPEEDY will be susceptible to adversaries who are capable of observing the characteristics of the implementation during its execution. Although this attacker model traditionally requires physical access to the executing device and therefore is typically considered to be less of a concern for desktop and server CPUs (the targeted application area for SPEEDY) there have been more and more successful remote power analysis attacks on such devices recently, most notably the PLATYPUS attack [LKO<sup>+</sup>21]. Thus, even in such contexts, physical adversaries can no longer be ignored and protecting SPEEDY against said attacks is a great direction for future research. 

In that regard, a recent work has pointed out that, although it is hardly feasible to apply hardware masking to unrolled low-latency cryptography without sacrificing a large portion of its performance due to the necessary inclusion of register stages, simple reset methods (i.e., randomly pre-charging the combinatorial circuit) deliver very promising results against passive side-channel attacks if applied properly [Moo20]. The parallelism, speed and asynchronicity of SPEEDY are assumed to be even higher than for the investigated PRINCE instance. Thus, we believe that this kind of protection mechanism can most reasonably be applied to unrolled SPEEDY in hardware without causing a large performance penalty. According to [Moo20], the cost of this countermeasure is either that the throughput is halved, or that the area is doubled when instantiating the unrolled cipher twice and alternating between pre-charging or encrypting with each circuit. Additionally, the cost for the Random Number Generator (RNG) has to be considered. 

## 7 Hardware Implementation

In this section, we analyze the minimum achievable latency of fully-unrolled SPEEDY hardware implementations as well as the area required for the time-constrained circuits and compare them to a number of other cryptographic primitives that have been suggested for high-speed single-cycle encryption in literature. Implementing SPEEDY in hardware is rather straightforward since almost all round operations which require any logic and may not be realized through wiring alone are already chosen as circuit representations. In detail, Figure 3 shows the hardware circuitry for the 6-bit high-speed S-box while Figure 4 depicts the logic circuit that implements the combined $\mathtt { A } _ { k _ { r + 1 } } \circ \mathtt { A } _ { c _ { r } } \circ \mathtt { M } \mathtt { C }$ function. The ShiftColumns operation does not require any logic, which means that only the initial and the final AddRoundKey functions remain. Obviously these are implemented with a single stage of regular XOR gates. 


Table 9: Minimum latency of fully-unrolled encryption-only circuits of diferent cryptographic primitives.


<table><tr><td rowspan="3">Cipher</td><td colspan="6">Minimum Latency [ns]</td></tr><tr><td colspan="4">Commercial Foundry</td><td colspan="2">NanGate OCL</td></tr><tr><td>90 nm LP</td><td>65 nm LP</td><td>40 nm LP</td><td>28 nm HPC</td><td>45 nm</td><td>15 nm</td></tr><tr><td>Gimli E-M</td><td>4.532467</td><td>3.330192</td><td>2.794736</td><td>1.178424</td><td>4.537304</td><td>0.435069</td></tr><tr><td>MANTIS6</td><td>4.625529</td><td>3.405490</td><td>2.891383</td><td>1.278725</td><td>4.479773</td><td>0.437595</td></tr><tr><td>MANTIS7</td><td>5.201681</td><td>3.722473</td><td>3.234409</td><td>1.421365</td><td>5.074452</td><td>0.492703</td></tr><tr><td>MANTIS8</td><td>5.823127</td><td>4.233543</td><td>3.631438</td><td>1.594997</td><td>5.739020</td><td>0.552384</td></tr><tr><td>Midori</td><td>5.061255</td><td>3.582221</td><td>3.142355</td><td>1.362237</td><td>4.934847</td><td>0.481522</td></tr><tr><td>Orthros</td><td>3.862139</td><td>2.678637</td><td>2.401275</td><td>1.087139</td><td>3.774836</td><td>0.369497</td></tr><tr><td>PRINCE</td><td>4.101177</td><td>2.866749</td><td>2.521302</td><td>1.108886</td><td>4.059997</td><td>0.389144</td></tr><tr><td>PRINCEv2</td><td>4.047311</td><td>2.944367</td><td>2.509131</td><td>1.103273</td><td>4.077636</td><td>0.387146</td></tr><tr><td>QARMA5-64-σ0</td><td>4.075846</td><td>2.920377</td><td>2.498908</td><td>1.134901</td><td>4.014516</td><td>0.385281</td></tr><tr><td>QARMA6-64-σ0</td><td>4.770325</td><td>3.418600</td><td>2.951308</td><td>1.308331</td><td>4.554445</td><td>0.448931</td></tr><tr><td>QARMA7-64-σ0</td><td>5.449707</td><td>3.909138</td><td>3.389576</td><td>1.538606</td><td>5.336362</td><td>0.517093</td></tr><tr><td>QARMA8-64-σ0</td><td>6.103768</td><td>4.396543</td><td>3.814078</td><td>1.697027</td><td>5.966323</td><td>0.575525</td></tr><tr><td>QARMA5-64-σ1</td><td>4.515514</td><td>3.284252</td><td>2.815788</td><td>1.219624</td><td>4.367899</td><td>0.408580</td></tr><tr><td>QARMA6-64-σ1</td><td>5.297867</td><td>3.808675</td><td>3.271455</td><td>1.388353</td><td>4.944635</td><td>0.472798</td></tr><tr><td>QARMA7-64-σ1</td><td>6.014477</td><td>4.371963</td><td>3.745959</td><td>1.601572</td><td>5.800633</td><td>0.542712</td></tr><tr><td>QARMA8-64-σ1</td><td>6.720944</td><td>4.904521</td><td>4.202632</td><td>1.797539</td><td>6.498429</td><td>0.608985</td></tr><tr><td>SPEEDY-5-192</td><td>2.994643</td><td>2.178075</td><td>1.867064</td><td>0.847761</td><td>3.187368</td><td>0.300466</td></tr><tr><td>SPEEDY-6-192</td><td>3.637978</td><td>2.639186</td><td>2.277422</td><td>1.032206</td><td>3.848132</td><td>0.366762</td></tr><tr><td>SPEEDY-7-192</td><td>4.261928</td><td>3.087257</td><td>2.663004</td><td>1.217946</td><td>4.515505</td><td>0.431032</td></tr><tr><td>SPEEDY-5-192 *</td><td>2.941130</td><td>2.121748</td><td>1.820950</td><td>0.826217</td><td>2.817971</td><td>0.290961</td></tr><tr><td>SPEEDY-6-192 *</td><td>3.559981</td><td>2.573561</td><td>2.223863</td><td>1.011173</td><td>3.382270</td><td>0.353391</td></tr><tr><td>SPEEDY-7-192 *</td><td>4.174183</td><td>3.029217</td><td>2.620612</td><td>1.186598</td><td>3.995325</td><td>0.413950</td></tr></table>


* = Optimized HDL code with direct instantiation of library cells based on Figures 3 and 4.


Table 9 presents the minimum latency results achieved for diferent instances of Gimli, MANTIS, Midori, Orthros, PRINCE, PRINCEv2, QARMA, and SPEEDY (in alphabetical order). All results have been obtained by synthesizing the fully-unrolled cipher circuits between two register stages for minimum clock period using the Synopsys Design Compiler Version O-2018.06-SP4 software while executing four stages of the compi $\mathsf { l e \_ u l }$ tra command (three incremental). We have repeated the analysis with 6 diferent standard cell libraries, 4 of which are manufacturable cell libraries from a commercial foundry, while the remaining 2 are open-source libraries which are not manufacturable but can be used for producing uni versally comparable and reproducible synthesis results. Please note that Gimli is a key-less permutation. Therefore, in order to create an encryption circuit from the primitive we have realized it in Even-Mansour scheme [EM97] with two diferent keys at the beginning and end. With respect to our SPEEDY implementations we distinguish between results that are achieved when giving the regular behavioral (or dataflow) description of the cipher to the synthesis tool and those results we have obtained by optimizing the code and instantiating the desired standard cells directly in the HDL code (according to the gate-level descriptions shown in Figures 3 and 4). It is obvious that this optimization has a significant impact on the performance in NanGate libraries, but less of an impact in the commercial technologies. In order to force the synthesizer to use our suggested gate-level structures for MC and SB we set a size-only attribute on the relevant cells in Synopsys Design Compiler before the first compile_ultra command. The synthesizer then only scales the drive strengths of these cells. In a next step three compile_ultra -incremental commands are executed without size-only attribute, so that all optimizations are allowed again. With that technique the highest quality of results is achieved and the majority of manually-instantiated cells still remain unchanged. 


Table 10: Area consumption of fully-unrolled encryption-only circuits of diferent cryptographic primitives when synthesized for minimum latency.


<table><tr><td rowspan="3">Cipher</td><td colspan="6">Area [GE]</td></tr><tr><td colspan="4">Commercial Foundry</td><td colspan="2">NanGate OCL</td></tr><tr><td>90 nm LP</td><td>65 nm LP</td><td>40 nm LP</td><td>28 nm HPC</td><td>45 nm</td><td>15 nm</td></tr><tr><td>Gimli E-M</td><td>72644.00</td><td>82781.00</td><td>63100.50</td><td>144036.33</td><td>52038.67</td><td>57551.25</td></tr><tr><td>MANTIS<eq>_{6}</eq></td><td>21045.75</td><td>23264.50</td><td>20448.25</td><td>36073.33</td><td>12660.67</td><td>15954.00</td></tr><tr><td>MANTIS<eq>_{7}</eq></td><td>23229.25</td><td>26385.75</td><td>23192.50</td><td>43220.33</td><td>14225.67</td><td>17522.50</td></tr><tr><td>MANTIS<eq>_{8}</eq></td><td>26365.75</td><td>30316.75</td><td>25429.75</td><td>50793.00</td><td>15663.33</td><td>19707.50</td></tr><tr><td>Midori</td><td>18678.50</td><td>21964.00</td><td>17562.25</td><td>41450.67</td><td>10675.33</td><td>13927.25</td></tr><tr><td>Orthros</td><td>49639.75</td><td>61657.00</td><td>44715.75</td><td>74384.67</td><td>31317.33</td><td>39165.00</td></tr><tr><td>PRINCE</td><td>16244.25</td><td>19877.75</td><td>17177.00</td><td>38145.33</td><td>9873.33</td><td>13291.00</td></tr><tr><td>PRINCEv2</td><td>17661.25</td><td>18798.25</td><td>16556.50</td><td>33470.33</td><td>10332.00</td><td>13069.50</td></tr><tr><td>QARMA<eq>_{5}</eq>-64-<eq>\sigma_{0}</eq></td><td>19590.75</td><td>21706.75</td><td>20255.00</td><td>31703.00</td><td>11824.67</td><td>14880.75</td></tr><tr><td>QARMA<eq>_{6}</eq>-64-<eq>\sigma_{0}</eq></td><td>22624.25</td><td>25349.50</td><td>22689.00</td><td>38813.67</td><td>14165.67</td><td>17621.75</td></tr><tr><td>QARMA<eq>_{7}</eq>-64-<eq>\sigma_{0}</eq></td><td>25614.00</td><td>29323.00</td><td>24656.25</td><td>40494.33</td><td>15769.33</td><td>19770.25</td></tr><tr><td>QARMA<eq>_{8}</eq>-64-<eq>\sigma_{0}</eq></td><td>28813.75</td><td>32780.75</td><td>28262.75</td><td>47952.33</td><td>17908.00</td><td>22074.00</td></tr><tr><td>QARMA<eq>_{5}</eq>-64-<eq>\sigma_{1}</eq></td><td>20264.75</td><td>23753.00</td><td>20202.25</td><td>34302.00</td><td>12350.33</td><td>15588.75</td></tr><tr><td>QARMA<eq>_{6}</eq>-64-<eq>\sigma_{1}</eq></td><td>23162.25</td><td>26941.25</td><td>23333.75</td><td>45419.00</td><td>15066.00</td><td>18164.00</td></tr><tr><td>QARMA<eq>_{7}</eq>-64-<eq>\sigma_{1}</eq></td><td>26563.75</td><td>31495.00</td><td>27059.50</td><td>52108.00</td><td>16641.00</td><td>20670.25</td></tr><tr><td>QARMA<eq>_{8}</eq>-64-<eq>\sigma_{1}</eq></td><td>30534.50</td><td>35787.75</td><td>29116.50</td><td>54967.00</td><td>18963.67</td><td>22761.75</td></tr><tr><td>SPEEDY-5-192</td><td>47364.00</td><td>53856.00</td><td>47528.50</td><td>74467.00</td><td>27903.33</td><td>34649.00</td></tr><tr><td>SPEEDY-6-192</td><td>57322.00</td><td>64438.25</td><td>56816.00</td><td>88932.00</td><td>34085.00</td><td>41443.25</td></tr><tr><td>SPEEDY-7-192</td><td>68370.00</td><td>75273.00</td><td>65422.00</td><td>95235.67</td><td>39853.33</td><td>48727.75</td></tr><tr><td>SPEEDY-5-192 *</td><td>49902.00</td><td>58796.25</td><td>55846.75</td><td>80313.33</td><td>29839.00</td><td>38075.25</td></tr><tr><td>SPEEDY-6-192 *</td><td>59688.00</td><td>70653.00</td><td>66553.00</td><td>98950.00</td><td>36523.33</td><td>46266.50</td></tr><tr><td>SPEEDY-7-192 *</td><td>73397.75</td><td>84745.00</td><td>77519.75</td><td>111754.33</td><td>42813.33</td><td>54193.25</td></tr></table>


* = Optimized HDL code with direct instantiation of library cells based on Figures 3 and 4. 


It is obvious from Table 9 that SPEEDY-5-192 and SPEEDY-6-192 produce the smallest latencies among all implementations. The next fastest primitives are Orthros and PRINCE/PRINCEv2. Gimli, performs respectably well given its large state (384 bit) and number of rounds (24). Yet, the claim that it outperforms PRINCE by a significant margin, made in [GKD20], is very doubtful considering our results. Please note that for all ciphers except Midori we have used hardware implementations written by the original authors of the corresponding papers (Qameleon authors for QARMA). 

Table 10 shows the corresponding area consumption for the fully-unrolled and highly latency constrained circuits. Clearly, SPEEDY requires a larger circuit area compared to all other ciphers except Gimli. However, this is mainly caused by its 192-bit state (which is larger than for all other ciphers in the table except Gimli). In more detail, when multiplying the area of the 64-bit ciphers by 3 (to encrypt 192 bit at once) many of them require a larger area than SPEEDY-5-192 and all MANTIS and QARMA instances even exceed the area of SPEEDY-6-192. Thus, we believe that for their block widths and the high security and performance levels that the SPEEDY instances provide, their area consumption is acceptable. Power consumption figures for all circuits are given in Appendix A, Table 12. 


Table 11: Comparison of pre-layout and post-layout latencies in a commercial 65 nm CMOS technology.


<table><tr><td rowspan="3">Cipher</td><td colspan="3">Minimum Latency [ns]</td></tr><tr><td colspan="3">65 nm LP</td></tr><tr><td>Pre-Layout</td><td>Post-Layout</td><td>Overhead</td></tr><tr><td>Gimli E-M</td><td>3.330192</td><td>3.902397</td><td>17.18 %</td></tr><tr><td>MANTIS6</td><td>3.405490</td><td>3.810253</td><td>11.89 %</td></tr><tr><td>MANTIS7</td><td>3.722473</td><td>4.225445</td><td>13.51 %</td></tr><tr><td>MANTIS8</td><td>4.233543</td><td>4.785156</td><td>13.03 %</td></tr><tr><td>Midori</td><td>3.582221</td><td>4.005088</td><td>11.80 %</td></tr><tr><td>Orthros</td><td>2.678637</td><td>3.166256</td><td>18.20 %</td></tr><tr><td>PRINCE</td><td>2.866749</td><td>3.236980</td><td>12.91 %</td></tr><tr><td>PRINCEv2</td><td>2.944367</td><td>3.324928</td><td>12.93 %</td></tr><tr><td>QARMA5-64-σ0</td><td>2.920377</td><td>3.302898</td><td>13.10 %</td></tr><tr><td>QARMA6-64-σ0</td><td>3.418600</td><td>3.869228</td><td>13.18 %</td></tr><tr><td>QARMA7-64-σ0</td><td>3.909138</td><td>4.432907</td><td>13.40 %</td></tr><tr><td>QARMA8-64-σ0</td><td>4.396543</td><td>5.078354</td><td>15.51 %</td></tr><tr><td>QARMA5-64-σ1</td><td>3.284252</td><td>3.696785</td><td>12.56 %</td></tr><tr><td>QARMA6-64-σ1</td><td>3.808675</td><td>4.294109</td><td>12.75 %</td></tr><tr><td>QARMA7-64-σ1</td><td>4.371963</td><td>4.929371</td><td>12.75 %</td></tr><tr><td>QARMA8-64-σ1</td><td>4.904521</td><td>5.519027</td><td>12.53 %</td></tr><tr><td>SPEEDY-5-192</td><td>2.178075</td><td>2.612023</td><td>19.92 %</td></tr><tr><td>SPEEDY-6-192</td><td>2.639186</td><td>3.142331</td><td>19.06 %</td></tr><tr><td>SPEEDY-7-192</td><td>3.087257</td><td>3.717537</td><td>20.42 %</td></tr><tr><td>SPEEDY-5-192 *</td><td>2.121748</td><td>2.572030</td><td>21.22 %</td></tr><tr><td>SPEEDY-6-192 *</td><td>2.573561</td><td>3.136378</td><td>21.87 %</td></tr><tr><td>SPEEDY-7-192 *</td><td>3.029217</td><td>3.696695</td><td>22.03 %</td></tr></table>


木 = Optimized HDL code with direct instantiation of library cells based on Figures 3 and 4.


Because synthesis results disregard the impact of wire capacitances on the latency of hardware circuits, we have exemplarily taken all netlists generated for the 65 nm technology through a Place and Route (PnR) process in order to estimate the post-layout latencies. These are given in comparison to the pre-layout values in Table 11. Naturally, the overhead introduced by the physical layout is greater for the circuits that have a larger area footprint, e.g., Gimli, Orthros and SPEEDY, because connected cells might be wider apart from each other and longer wire lengths are required to connect them (also because metal utilization increases and wires have to be routed on higher, thicker metal layers). However, despite the slightly larger overhead SPEEDY-5-192 and SPEEDY-6-192 are still the fastest encryption primitives after PnR. 

## 7.1 Decryption

For the most part of this work we have ignored the SPEEDY decryption. SPEEDY is primarily designed to ofer ultra fast encryption of data with a high level of security. As discussed by the authors of the Orthros low-latency PRF, it is suficient for many use cases to have a one directional primitive [BIL<sup>+</sup>21]. Among these use cases are several popular block cipher modes of operation, such as CTR, CMAC and GCM, which all require no decryption routine, as well as applications such as pointer authentication and memory encryption schemes based on Merkle trees [BIL<sup>+</sup>21]. According to [BIL<sup>+</sup>21] even a memory encryption scheme applied inside Intel’s Software Guard Extensions (SGX) uses adapted variants of GMAC and GCM without requiring the underlying primitive to be invertible. However, since SPEEDY does not lack invertibility like Orthros does, it can also be used in application scenarios where invertibility and decryption are indeed required, but where it is acceptable that only one direction is extremely eficient. In Appendix B, Table 13 implementation results (latency, area, power) are presented for the SPEEDY decryption. Although it is not nearly as eficient as the encryption, the SPEEDY-5-192 decryption is faster than the Midori encryption and many others (cf. Table 9) and the SPEEDY-6-192 decryption is still faster than the $\mathsf { Q A R M A _ { 7 }  – 6 4 – \sigma _ { 1 } }$ encryption and a few more (cf. Table 9). 

## 7.2 Code and Reproducibility

A reference software implementation in C and hardware implementations of SPEEDY-r-192 encryption and decryption in VHDL, along with synthesized netlists in NanGate libraries and associated synthesis scripts, are all available in our GitHub repository found here: https://github.com/Chair-for-Security-Engineering/SPEEDY. 

## 8 Conclusion

In this work we have introduced SPEEDY, a family of ultra low-latency block ciphers developed for extremely high execution speed in CMOS hardware and dedicated to semi-custom, i.e., standard-cell-based, integrated circuit design. The primary targets for SPEEDY are security architectures in high-end CPUs which require ultra low-latency encryption, such as secure caches, dedicated hardware extensions, memory encryption, pointer authentication and many more. SPEEDY achieves higher performance than any competitor because of hardware-specific gate- and transistor-level observations that have been exploited in its design to make it extremely performant in CMOS hardware. While SPEEDY can be instantiated with diferent block and key sizes, the default is 192 bit. Based on our analysis, we are confident that 7 rounds provide full security, while 5 rounds already provide a higher security level than PRINCE or PRINCEv2 for example. Our extensive evaluation of hardware implementations demonstrates that both SPEEDY-5-192 and SPEEDY-6-192 are faster than any proposed version of PRINCE, PRINCEv2, MANTIS, QARMA, Midori, Gimli and Orthros. Thus, SPEEDY is a significant upgrade over the state of the art for any application where area and energy are secondary design goals while high performance is the number one priority. 

## Acknowledgments

The work described in this paper has been supported in part by the Deutsche Forschungsgemeinschaft (DFG, German Research Foundation) under Germany’s Excellence Strategy - EXC 2092 CASA - 390781972 and through the project 406956718 “SymmetriC CiphEr design with inherent phySical Security (SuCCESS)”. Besides, S. Rasoolzadeh is supported by the Netherlands Organisation for Scientific Research (NWO) under TOP grant TOP1.18.002 SCALAR. 

## References



[ABP<sup>+</sup>18] Victor Arribas, Begül Bilgin, George Petrides, Svetla Nikova, and Vincent Rijmen. Rhythmic keccak: SCA security and low latency in HW. IACR Trans. Cryptogr. Hardw. Embed. Syst., 2018(1):269–290, 2018. 





[Ava17] Roberto Avanzi. The QARMA block cipher family. almost MDS matrices over rings with zero divisors, nearly symmetric even-mansour constructions with non-involutory central rounds, and search heuristics for low-latency s-boxes. IACR Trans. Symmetric Cryptol., 2017(1):4–44, 2017. 





[BBI<sup>+</sup>15] Subhadeep Banik, Andrey Bogdanov, Takanori Isobe, Kyoji Shibutani, Harunaga Hiwatari, Toru Akishita, and Francesco Regazzoni. Midori: A block cipher for low energy. In Tetsu Iwata and Jung Hee Cheon, editors, Advances in Cryptology - ASIACRYPT 2015 - 21st International Conference on the Theory and Application of Cryptology and Information Security, Auckland, New Zealand, November 29 - December 3, 2015, Proceedings, Part II, volume 9453 of Lecture Notes in Computer Science, pages 411–436. Springer, 2015. 





[BCG<sup>+</sup>12] Julia Borghof, Anne Canteaut, Tim Güneysu, Elif Bilge Kavun, Miroslav Knezevic, Lars R. Knudsen, Gregor Leander, Ventzislav Nikov, Christof Paar, Christian Rechberger, Peter Rombouts, Søren S. Thomsen, and Tolga Yalçin. PRINCE - A low-latency block cipher for pervasive computing applications - extended abstract. In Xiaoyun Wang and Kazue Sako, editors, Advances in Cryptology - ASIACRYPT 2012 - 18th International Conference on the Theory and Application of Cryptology and Information Security, Beijing, China, December 2-6, 2012. Proceedings, volume 7658 of Lecture Notes in Computer Science, pages 208–225. Springer, 2012. 





[BEK<sup>+</sup>20] Dušan Božilov, Maria Eichlseder, Miroslav Knezevic, Baptiste Lambin, Gregor Leander, Thorben Moos, Ventzislav Nikov, Shahram Rasoolzadeh, Yosuke Todo, and Friedrich Wiemer. Princev2 - more security for (almost) no overhead. In Selected Areas in Cryptography - SAC 2020, Lecture Notes in Computer Science, 2020. 





[BFP19] Joan Boyar, Magnus Gausdal Find, and René Peralta. Small low-depth circuits for cryptographic applications. Cryptogr. Commun., 11(1):109–127, 2019. 





[BIL<sup>+</sup>21] Subhadeep Banik, Takanori Isobe, Fukang Liu, Kazuhiko Minematsu, and Kosei Sakamoto. Orthros: A low-latency PRF. IACR Trans. Symmetric Cryptol., 2021(1):37–77, 2021. 





[BJK<sup>+</sup>16] Christof Beierle, Jérémy Jean, Stefan Kölbl, Gregor Leander, Amir Moradi, Thomas Peyrin, Yu Sasaki, Pascal Sasdrich, and Siang Meng Sim. The SKINNY family of block ciphers and its low-latency variant MANTIS. In Matthew Robshaw and Jonathan Katz, editors, Advances in Cryptology - CRYPTO 2016 - 36th Annual International Cryptology Conference, Santa Barbara, CA, USA, August 14-18, 2016, Proceedings, Part II, volume 9815 of Lecture Notes in Computer Science, pages 123–153. Springer, 2016. 





[BKL<sup>+</sup>17] Daniel J. Bernstein, Stefan Kölbl, Stefan Lucks, Pedro Maat Costa Massolino, Florian Mendel, Kashif Nawaz, Tobias Schneider, Peter Schwabe, François-Xavier Standaert, Yosuke Todo, and Benoît Viguier. Gimli : A cross-platform permutation. In Wieland Fischer and Naofumi Homma, editors, Cryptographic Hardware and Embedded Systems - CHES 2017 - 19th International Conference, Taipei, Taiwan, September 25-28, 2017, Proceedings, volume 10529 of Lecture Notes in Computer Science, pages 299–320. Springer, 2017. 





[BKN19] Dusan Bozilov, Miroslav Knezevic, and Ventzislav Nikov. Optimized threshold implementations: Minimizing the latency of secure cryptographic accelerators. In Sonia Belaïd and Tim Güneysu, editors, Smart Card Research and Advanced Applications - 18th International Conference, CARDIS 2019, Prague, Czech Republic, November 11-13, 2019, Revised Selected Papers, volume 11833 of Lecture Notes in Computer Science, pages 20–39. Springer, 2019. 





[BMD<sup>+</sup>20] Begül Bilgin, Lauren De Meyer, Sébastien Duval, Itamar Levi, and François-Xavier Standaert. Low AND depth and eficient inverses: a guide on s-boxes 





for low-latency masking. IACR Trans. Symmetric Cryptol., 2020(1):144–184, 2020. 





[DEMS19] Christoph Dobraunig, Maria Eichlseder, Florian Mendel, and Martin Schläfer. Ascon v1.2 submission to nist. https://csrc.nist.gov/ CSRC/media/Projects/lightweight-cryptography/documents/round-2/ spec-doc-rnd2/ascon-spec-round2.pdf, 2019. Accessed: 2021-07-02. 





[DXS19] Shuwen Deng, Wenjie Xiong, and Jakub Szefer. Analysis of secure caches using a three-step model for timing-based attacks. J. Hardware and Systems Security, 3(4):397–425, 2019. 





[EM97] Shimon Even and Yishay Mansour. A construction of a cipher from a single pseudorandom permutation. J. Cryptol., 10(3):151–162, 1997. 





[GIB18] Hannes Groß, Rinat Iusupov, and Roderick Bloem. Generic low-latency masking in hardware. IACR Trans. Cryptogr. Hardw. Embed. Syst., 2018(2):1– 21, 2018. 





[GKD20] Santosh Ghosh, Michael E. Kounavis, and Sergej Deutsch. Gimli encryption in 715.9 psec. IACR Cryptol. ePrint Arch., 2020:336, 2020. 





[KHF<sup>+</sup>19] Paul Kocher, Jann Horn, Anders Fogh, Daniel Genkin, Daniel Gruss, Werner Haas, Mike Hamburg, Moritz Lipp, Stefan Mangard, Thomas Prescher, Michael Schwarz, and Yuval Yarom. Spectre attacks: Exploiting speculative execution. In 2019 IEEE Symposium on Security and Privacy, SP 2019, San Francisco, CA, USA, May 19-23, 2019, pages 1–19. IEEE, 2019. 





[KNR12] Miroslav Knezevic, Ventzislav Nikov, and Peter Rombouts. Low-latency encryption - is "lightweight = light + wait"? In Emmanuel Prouf and Patrick Schaumont, editors, Cryptographic Hardware and Embedded Systems - CHES 2012 - 14th International Workshop, Leuven, Belgium, September 9-12, 2012. Proceedings, volume 7428 of Lecture Notes in Computer Science, pages 426–446. Springer, 2012. 





[LKO<sup>+</sup>21] Moritz Lipp, Andreas Kogler, David Oswald, Michael Schwarz, Catherine Easdon, Claudio Canella, and Daniel Gruss. PLATYPUS: Software-based Power Side-Channel Attacks on x86. In 2021 IEEE Symposium on Security and Privacy (SP). IEEE, 2021. 





[LP07] Gregor Leander and Axel Poschmann. On the classification of 4 bit s-boxes. In Claude Carlet and Berk Sunar, editors, Arithmetic of Finite Fields, First International Workshop, WAIFI 2007, Madrid, Spain, June 21-22, 2007, Proceedings, volume 4547 of Lecture Notes in Computer Science, pages 159– 176. Springer, 2007. 





[LSG<sup>+</sup>18] Moritz Lipp, Michael Schwarz, Daniel Gruss, Thomas Prescher, Werner Haas, Anders Fogh, Jann Horn, Stefan Mangard, Paul Kocher, Daniel Genkin, Yuval Yarom, and Mike Hamburg. Meltdown: Reading kernel memory from user space. In William Enck and Adrienne Porter Felt, editors, 27th USENIX Security Symposium, USENIX Security 2018, Baltimore, MD, USA, August 15-17, 2018, pages 973–990. USENIX Association, 2018. 





[LSL<sup>+</sup>19] Shun Li, Siwei Sun, Chaoyun Li, Zihao Wei, and Lei Hu. Constructing low-latency involutory MDS matrices with lightweight circuits. IACR Trans. Symmetric Cryptol., 2019(1):84–117, 2019. 





[Moo65] Gordon E. Moore. Cramming more components onto integrated circuits. Electronics, 38(8), April 1965. 





[Moo20] Thorben Moos. Unrolled cryptography on silicon A physical security analysis. IACR Trans. Cryptogr. Hardw. Embed. Syst., 2020(4):416–442, 2020. 





[MS16] Amir Moradi and Tobias Schneider. Side-channel analysis protection and lowlatency in action - - case study of PRINCE and midori -. In Jung Hee Cheon and Tsuyoshi Takagi, editors, Advances in Cryptology - ASIACRYPT 2016 - 22nd International Conference on the Theory and Application of Cryptology and Information Security, Hanoi, Vietnam, December 4-8, 2016, Proceedings, Part I, volume 10031 of Lecture Notes in Computer Science, pages 517–547, 2016. 





[oST79] National Institute of Standards and Technology. Fips-46: Data encryption standard (des). http://csrc.nist.gov/publications/fips/fips46-3/ fips46-3.pdf, 1979. Accessed: 2021-07-02. 





[oST01] National Institute of Standards and Technology. Fips-197: Advanced encryption standard (aes). https://nvlpubs.nist.gov/nistpubs/FIPS/NIST. FIPS.197.pdf, 2001. Accessed: 2021-07-02. 





[Qur18] Moinuddin K. Qureshi. CEASER: mitigating conflict-based cache attacks via encrypted-address and remapping. In 51st Annual IEEE/ACM International Symposium on Microarchitecture, MICRO 2018, Fukuoka, Japan, October 20-24, 2018, pages 775–787. IEEE Computer Society, 2018. 





[RCN04] Jan M. Rabaey, Anantha Chandrakasan, and Borivoje Nikolic. Digital integrated circuits- A design perspective. Prentice Hall, 2ed edition, 2004. 





[SBHM20] Pascal Sasdrich, Begül Bilgin, Michael Hutter, and Mark E. Marson. Lowlatency hardware masking with application to AES. IACR Trans. Cryptogr. Hardw. Embed. Syst., 2020(2):300–326, 2020. 





[WUG<sup>+</sup>19] Mario Werner, Thomas Unterluggauer, Lukas Giner, Michael Schwarz, Daniel Gruss, and Stefan Mangard. Scattercache: Thwarting cache attacks via cache set randomization. In Nadia Heninger and Patrick Traynor, editors, 28th USENIX Security Symposium, USENIX Security 2019, Santa Clara, CA, USA, August 14-16, 2019, pages 675–692. USENIX Association, 2019. 



## A Power Consumption


Table 12: Estimated power consumption of fully-unrolled encryption-only circuits of diferent cryptographic primitives when synthesized for minimum latency. Estimated for 100 MHz operation.


<table><tr><td rowspan="3">Cipher</td><td colspan="6">Power [mW]</td></tr><tr><td colspan="4">Commercial Foundry</td><td colspan="2">NanGate OCL</td></tr><tr><td>90 nm LP</td><td>65 nm LP</td><td>40 nm LP</td><td>28 nm HPC</td><td>45 nm</td><td>15 nm</td></tr><tr><td>Gimli E-M</td><td>16.3489</td><td>12.4244</td><td>4.1035</td><td>8.5614</td><td>9.4797</td><td>2.7762</td></tr><tr><td>MANTIS6</td><td>0.2848</td><td>0.2108</td><td>0.0889</td><td>0.3755</td><td>0.3680</td><td>0.2101</td></tr><tr><td>MANTIS7</td><td>0.3140</td><td>0.2409</td><td>0.0986</td><td>0.4509</td><td>0.4107</td><td>0.2318</td></tr><tr><td>MANTIS8</td><td>0.3503</td><td>0.2806</td><td>0.1072</td><td>0.5269</td><td>0.4479</td><td>0.2605</td></tr><tr><td>Midori</td><td>0.2652</td><td>0.2104</td><td>0.0798</td><td>0.4512</td><td>0.3131</td><td>0.1848</td></tr><tr><td>Orthros</td><td>0.6626</td><td>0.5814</td><td>0.1935</td><td>0.7978</td><td>0.8711</td><td>0.4959</td></tr><tr><td>PRINCE</td><td>0.2162</td><td>0.1856</td><td>0.0756</td><td>0.4079</td><td>0.2930</td><td>0.1759</td></tr><tr><td>PRINCEv2</td><td>0.2390</td><td>0.1827</td><td>0.0721</td><td>0.3629</td><td>0.3041</td><td>0.1708</td></tr><tr><td>QARMA5-64-σ0</td><td>0.2652</td><td>0.2044</td><td>0.0867</td><td>0.3285</td><td>0.3448</td><td>0.1997</td></tr><tr><td>QARMA6-64-σ0</td><td>0.2993</td><td>0.2364</td><td>0.0973</td><td>0.3973</td><td>0.4099</td><td>0.2332</td></tr><tr><td>QARMA7-64-σ0</td><td>0.3367</td><td>0.2640</td><td>0.1054</td><td>0.4087</td><td>0.4529</td><td>0.2614</td></tr><tr><td>QARMA8-64-σ0</td><td>0.3846</td><td>0.2964</td><td>0.1205</td><td>0.4935</td><td>0.5121</td><td>0.2896</td></tr><tr><td>QARMA5-64-σ1</td><td>0.2669</td><td>0.2187</td><td>0.0872</td><td>0.3672</td><td>0.3607</td><td>0.2059</td></tr><tr><td>QARMA6-64-σ1</td><td>0.3052</td><td>0.2443</td><td>0.1004</td><td>0.4879</td><td>0.4350</td><td>0.2385</td></tr><tr><td>QARMA7-64-σ1</td><td>0.3544</td><td>0.2795</td><td>0.1161</td><td>0.5599</td><td>0.4769</td><td>0.2700</td></tr><tr><td>QARMA8-64-σ1</td><td>0.3903</td><td>0.3246</td><td>0.1263</td><td>0.5906</td><td>0.5418</td><td>0.2946</td></tr><tr><td>SPEEDY-5-192</td><td>11.6227</td><td>7.9766</td><td>3.0922</td><td>3.9246</td><td>4.9508</td><td>1.7998</td></tr><tr><td>SPEEDY-6-192</td><td>14.2678</td><td>9.7228</td><td>3.7569</td><td>4.7595</td><td>6.1494</td><td>2.1764</td></tr><tr><td>SPEEDY-7-192</td><td>17.2552</td><td>11.5149</td><td>4.4061</td><td>5.1270</td><td>7.2578</td><td>2.5978</td></tr><tr><td>SPEEDY-5-192 *</td><td>11.7005</td><td>8.6807</td><td>3.6014</td><td>5.8412</td><td>5.3485</td><td>2.0160</td></tr><tr><td>SPEEDY-6-192 *</td><td>14.2010</td><td>10.6287</td><td>4.3671</td><td>5.1269</td><td>6.6413</td><td>2.4959</td></tr><tr><td>SPEEDY-7-192 *</td><td>17.8889</td><td>12.9823</td><td>5.1331</td><td>5.8412</td><td>7.8866</td><td>2.9508</td></tr></table>


= Optimized HDL code with direct instantiation of library cells based on Figures 3 and 4. 


## B SPEEDY Decryption Implementation Results


Table 13: Estimated latency, area, and power consumption of the SPEEDY decryption routine.


<table><tr><td colspan="7">Minimum Latency [ns]</td></tr><tr><td rowspan="2">Cipher</td><td colspan="4">Commercial Foundry</td><td colspan="2">NanGate OCL</td></tr><tr><td>90 nm LP</td><td>65 nm LP</td><td>40 nm LP</td><td>28 nm HPC</td><td>45 nm</td><td>15 nm</td></tr><tr><td>SPEEDY-5-192</td><td>4.827471</td><td>3.469787</td><td>2.953934</td><td>1.387975</td><td>5.088359</td><td>0.471568</td></tr><tr><td>SPEEDY-6-192</td><td>5.845453</td><td>4.197634</td><td>3.586378</td><td>1.680402</td><td>6.174353</td><td>0.572912</td></tr><tr><td>SPEEDY-7-192</td><td>6.887968</td><td>4.937893</td><td>4.240692</td><td>1.987920</td><td>7.259925</td><td>0.672681</td></tr><tr><td colspan="7">Area [GE]</td></tr><tr><td>SPEEDY-5-192</td><td>101401.50</td><td>118295.50</td><td>107298.50</td><td>123458.67</td><td>70771.33</td><td>86302.50</td></tr><tr><td>SPEEDY-6-192</td><td>120336.75</td><td>138823.50</td><td>127010.00</td><td>146688.00</td><td>83632.67</td><td>102160.50</td></tr><tr><td>SPEEDY-7-192</td><td>138292.50</td><td>161802.50</td><td>142642.25</td><td>163059.67</td><td>97923.33</td><td>117827.25</td></tr><tr><td colspan="7">Power [mW]</td></tr><tr><td>SPEEDY-5-192</td><td>21.6051</td><td>15.7708</td><td>6.4204</td><td>5.7405</td><td>11.6600</td><td>4.1493</td></tr><tr><td>SPEEDY-6-192</td><td>26.2426</td><td>18.7986</td><td>7.7360</td><td>6.9424</td><td>14.0370</td><td>4.9956</td></tr><tr><td>SPEEDY-7-192</td><td>30.3541</td><td>22.0906</td><td>8.6553</td><td>7.7193</td><td>16.5390</td><td>5.8020</td></tr></table>


C Test Vectors for SPEEDY-r-192


<table><tr><td colspan="24">SPEEDY-5-192</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>K</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>P</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>C</td><td>E0</td><td>D5</td><td>6F</td><td>BD</td><td>95</td><td>56</td><td>A8</td><td>71</td><td>CA</td><td>49</td><td>35</td><td>7A</td><td>82</td><td>2D</td><td>04</td><td>81</td><td>A8</td><td>50</td><td>2D</td><td>DD</td><td>16</td><td>FE</td><td>CE</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>K</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>P</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td>EF</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td>EF</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>C</td><td>12</td><td>3A</td><td>5D</td><td>7A</td><td>D4</td><td>5D</td><td>E4</td><td>4A</td><td>27</td><td>64</td><td>OB</td><td>EF</td><td>01</td><td>F4</td><td>8D</td><td>42</td><td>01</td><td>7C</td><td>FA</td><td>D0</td><td>F2</td><td>22</td><td>3C</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>K</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td>EF</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td>EF</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>P</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>C</td><td>FC</td><td>FB</td><td>8E</td><td>9C</td><td>23</td><td>OA</td><td>07</td><td>81</td><td>B0</td><td>63</td><td>30</td><td>76</td><td>FD</td><td>62</td><td>BF</td><td>7D</td><td>CE</td><td>F4</td><td>98</td><td>BA</td><td>2C</td><td>2B</td><td>29</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>K</td><td>76</td><td>4C</td><td>4F</td><td>62</td><td>54</td><td>E1</td><td>BF</td><td>F2</td><td>08</td><td>E9</td><td>58</td><td>62</td><td>42</td><td>8F</td><td>AE</td><td>D0</td><td>15</td><td>84</td><td>F4</td><td>20</td><td>7A</td><td>7E</td><td>84</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>P</td><td>A1</td><td>3A</td><td>63</td><td>24</td><td>51</td><td>07</td><td>OE</td><td>43</td><td>82</td><td>A2</td><td>7F</td><td>26</td><td>A4</td><td>06</td><td>82</td><td>F3</td><td>FE</td><td>9F</td><td>F6</td><td>80</td><td>28</td><td>D2</td><td>4F</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>C</td><td>01</td><td>DA</td><td>25</td><td>A9</td><td>3D</td><td>1C</td><td>FC</td><td>5E</td><td>4C</td><td>OB</td><td>74</td><td>F6</td><td>77</td><td>EB</td><td>74</td><td>6C</td><td>28</td><td>1A</td><td>26</td><td>01</td><td>93</td><td>B7</td><td>75</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td colspan="24">SPEEDY-6-192</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>K</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>0</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>P</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>0</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>C</td><td>A6</td><td>D5</td><td>18</td><td>A2</td><td>E5</td><td>73</td><td>75</td><td>15</td><td>15</td><td>93</td><td>11</td><td>OA</td><td>16</td><td>1E</td><td>D7</td><td>C6</td><td>27</td><td>8A</td><td>BC</td><td>D0</td><td>31</td><td>CB</td><td>E8</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>K</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>0</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>P</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td>EF</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td>EF</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>C</td><td>CB</td><td>44</td><td>11</td><td>34</td><td>1F</td><td>FF</td><td>B3</td><td>00</td><td>03</td><td>00</td><td>1A</td><td>8C</td><td>1F</td><td>06</td><td>FE</td><td>D8</td><td>7F</td><td>F6</td><td>89</td><td>C5</td><td>2D</td><td>1E</td><td>AB</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>K</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td>EF</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td>EF</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>P</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>0</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>C</td><td>4B</td><td>F4</td><td>3B</td><td>6A</td><td>64</td><td>8E</td><td>81</td><td>6A</td><td>EF</td><td>4F</td><td>C9</td><td>88</td><td>A9</td><td>4C</td><td>76</td><td>7F</td><td>A8</td><td>36</td><td>BA</td><td>25</td><td>A8</td><td>D2</td><td>A3</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>K</td><td>76</td><td>4C</td><td>4F</td><td>62</td><td>54</td><td>E1</td><td>BF</td><td>F2</td><td>08</td><td>E9</td><td>58</td><td>62</td><td>42</td><td>8F</td><td>AE</td><td>D0</td><td>15</td><td>84</td><td>F4</td><td>20</td><td>7A</td><td>7E</td><td>84</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>P</td><td>A1</td><td>3A</td><td>63</td><td>24</td><td>51</td><td>07</td><td>OE</td><td>43</td><td>B2</td><td>A2</td><td>7F</td><td>26</td><td>A4</td><td>06</td><td>82</td><td>F3</td><td>FE</td><td>9F</td><td>F6</td><td>80</td><td>28</td><td>D2</td><td>4F</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>C</td><td>88</td><td>BF</td><td>D3</td><td>DC</td><td>14</td><td>OF</td><td>38</td><td>BC</td><td>53</td><td>A6</td><td>66</td><td>87</td><td>F5</td><td>30</td><td>78</td><td>60</td><td>56</td><td>OE</td><td>BE</td><td>C4</td><td>11</td><td>00</td><td>66</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td colspan="24">SPEEDY-7-192</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>K</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00.00</td><td>00 00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>P</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00. 00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00 0</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>C</td><td>24</td><td>7D</td><td>30</td><td>80</td><td>D2</td><td>63</td><td>F7</td><td>4C</td><td>B0</td><td>3D</td><td>DE</td><td>6E</td><td>57</td><td>5C</td><td>68</td><td>EE</td><td>68</td><td>EE</td><td>E9</td><td>57</td><td>E1</td><td>C2</td><td>9C</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>K</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00</td><td>00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00.00 0</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>P</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td>EF</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td>EF</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>C</td><td>B4</td><td>8F</td><td>32</td><td>16</td><td>AB</td><td>33</td><td>AE</td><td colspan="16">01.99.14.2F6A0743E8481BFC37625CBBDC4F</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td>K</td><td>01</td><td>23</td><td>45</td><td>67</td><td>89</td><td>AB</td><td>CD</td><td>EF</td><td>01.23.45.67.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89 .89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89. 89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.89.</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr></table>