---
title: Benchmarking and Characterization of Large Language Model Inference on
  Apple Silicon
conference: SIGMETRICS 2026
---
>链接：https://arxiv.org/abs/2508.08531
>
>对比Apple M系列芯片和Nivida A6000在端侧推理时的端到端延时、细粒度耗时以及每百万token花费等指标

### Motivation

Apple Silicon芯片的统一内存架构可提供高达192 GB的共享内存池，为承载超大规模LLM（如 Llama 405B）提供了可能。目前普遍认为Apple GPU的运算能力较Nivida GPU更低，不适合LLM推理，但其统一内存是否能在成本和实用性上弥补算力短板，尚无定论。本文通过基准测试和细粒度性能测试，回答三个问题：1. Apple Silicon端到端推理效果如何？2. 相比 CUDA 是否具备成本效益？3. 性能瓶颈究竟是计算能力、内存带宽还是反量化开销？

![M系列共享内存架构](https://img.195806.xyz/file/1787219505861_Apple_Silicon_pic1.png)

### Design

实验用到的硬件平台如下：

![Backend](https://img.195806.xyz/file/1787219666699_Apple_Silicon_pic2.png)

实验用到的模型如下：

![Models](https://img.195806.xyz/file/1787219785260_Apple_Silicon_pic3.png)

实验室用Apple Instruments和Xcode捕获GPU性能计数器（ALU利用率、缓冲区负载、缓存命中率等），对比端到端延迟、吞吐量、每百万token成本，并进行Roofline模型分析。

整体流程：加载量化后模型->执行推理->记录各阶段耗时与硬件计数器->比较不同后端结果

### Method

实验测量了下列指标：

- 吞吐量与延迟

>分别测量Prefill和Decode阶段的每token延迟，以及GEMM/GEMV内核的TFLOPS吞吐量。
>固定上下文长度2048，生成长度4096，对比26种量化方案的端到端速度。考察上下文长度（128~2048）和KV缓存大小对延迟的影响。

- 反量化与算子级开销

>通过内核性能计数，分析与矩阵相关的一系列量化矩阵内核的归一化执行时间占比，区分标量运算、反量化、矩阵乘等子操作。
>比较不同比特宽度下指令数、吞吐量差异，并量化位不对齐导致的额外开销。

- 成本效益

>按硬件购买价格在两年内摊销，反算每小时成本，再结合TPS计算每百万token的美元成本。
>对比三种场景（单卡模型，VRAM足够大；双卡模型，VRAM足够大；模型超过CUDA VRAM大小但未超过Apple芯片VRAM大小）下的每token美元成本。

- 内存与缓存行为

>测量缓冲区加载利用率、缓冲区读取限制器、TLB未命中率、末级缓存利用率。
>分析不同量化方案下，codebook-based量化方式下查表带来的额外内存流量和缓存压力。

- ALU利用率

>分别测量ALU利用率、ALU Stall、FP32和INT利用率，以及Occupancy。
>结合roofline模型，判断每个Transformer子层（FFN、Attention、Softmax）处于计算受限还是内存受限区域。

![roofline model](https://img.195806.xyz/file/1787233161508_roofline.png)

### Findings

- 不同量化方式和推理速度并不是单一单调关系，反量化开销与硬件架构之间的协调也会产生较大影响
- Apple芯片的统一内存架构再超大模型推理上相较于Nivida CUDA具有显著成本优势
- codebook-based IQ-quants量化方式在M系列芯片上表现较差；K-quants表现优异
- 反量化是显著瓶颈，尤其是在低比特下，反量化算术强度高，使解码转向计算受限，而非传统认为的内存受限
- 奇数字宽效率低下
- Apple GPU无类似Tensor Core的低比特矩阵乘单元，难以隐藏反量化开销，与Nvida的差距在低比特下尤为突出

### Inspirations

文章所述实验流程完整，从实验测量框架到实验设备和测量指标均有详细说明。今后从事测量相关实验时可以参考其流程，先有一个完善的测量工作流和明确的测量指标，再开展测量。同时，对实验现象，文章给出了详实的分析，启示今后在做测量实验时要对数据的理解到位。文章也提供了一些很有启发性的测量指标，比如每token耗费美元数、不同算子的资源受限类型等等，今后可以学习借鉴。
