---
title: " D²MoE: Dual Routing and Dynamic Scheduling for Efficient On-Device
  MoE-based LLM Serving"
conference: PPoPP
---
> 作者为 SongGuo (HKUST)
>
> 链接：https://dl.acm.org/doi/pdf/10.1145/3680207.3723493
>
> 对于每个 token，不仅动态决定“走哪个 expert”，还动态决定“这个 expert 用多少 bit 运行”；然后利用嵌套量化和 I/O-compute 调度，把 expert 权重加载的开销藏起来。



### Motivation



1. MoE 虽然每个 token 只激活少量 expert，但\*\*所有 expert 参数非常大\*\*。以 Mixtral 8×7B 为例，FP16 权重超过 90GB，而 RTX 3060 Laptop GPU 只有 6GB，因此大量 expert 必须放在 CPU/SSD，需要时再搬到 GPU。计算时常常是 \*\*I/O-bound\*\*：论文测得 RTX 3060 上一个 LLaMA-MoE expert 计算约 3.1ms，而加载大约 20ms，所以 GPU 经常在等 expert。

2. 已有 mixed-precision MoE 通常是离线决定：\(E_1\rightarrow INT4,\quad E_2\rightarrow INT2,\quad E_3\rightarrow INT3\)，然后在推理时精度固定，但作者观察到，\*\*同一个 expert 对不同 token 的重要性并不相同\*\*，所以固定 bit-width 不够灵活，可能会导致不同程度的精度下降



### Design



- Token-Adaptive Bit-Width Selection



  **Dual Routing: ** 普通 MoE 只有一个 Expert Router： \[ x\rightarrow \text{Expert Gate}\rightarrow E_i \]

  D²MoE 在此基础上增加一个 Bit-width Router：\\[ x\rightarrow \begin{cases} \text{Expert Gate} &\rightarrow E_i\\ \text{Bit Gate} &\rightarrow b_i \end{cases} \]

  也就是说，一个 token 的专家路由的结果可能是：\\[ (E_2, INT2) \]，这个是基于 expert 对 token 的重要程度来得到的，作者对 Bit-width Router 也进行了微调（思想来源于：Mixture-of-Depths: Dynamically allocating compute in transformer-based language models.）

  注意量化不是 on-the-fly 的，是offline 阶段已经做好的



- MWQ（Matryoshka Weight Quantization）

  如果直接支持动态 bit-width，一个朴素办法是给每个 expert 保存：\\[ W_2, W_3, W_4 \]也就是三份独立的 INT2 / INT3 / INT4 权重。这会把节省下来的内存又吃回去。论文举例，LLaMA-MoE 单独 INT4 expert 权重约 3.81GB，但同时存 INT2/3/4 会达到 9.62GB。

  D²MoE 用了一种“套娃式”权重表示： \\[ W^{(2)} = Q_2 \]\\[ W^{(3)} = Q_2+\Delta_3 \]\\[ W^{(4)} = Q_2+\Delta_3+\Delta_4 \]

  其中 \(Q_2\) 是基础 INT2 权重，\(\Delta_3,\Delta_4\) 是逐 bit 的 binary residual quantization。也就是说： \\[ INT2 \subset INT3 \subset INT4 \]

  高精度权重并不是另一份独立 copy，而是在低精度权重基础上\*\*增量补残差\*\*。这不仅减少存储，更重要的是给后面的 scheduling 创造了条件。

- Bit-width-aware I/O-Compute Pipeline

  因为 expert 放不进 GPU，它们实际上是： \\[ SSD/CPU \xrightarrow{\text{I/O}} GPU \xrightarrow{\text{dequant}} FP16 \xrightarrow{\text{GEMM}} output \]

  作者希望形成： \\[ \text{Load }E_2 \parallel\text{Compute }E_1 \] 来隐藏权重加载。

  这个工作在原先的流水线粒度上多了一个量化的粒度，所以 pipeline 机会更多，并且可以和原来的顺序加载计算有所区别

  调度算法叫 \*\*HEBF（Hottest-Expert-Bit-First）\*\*，也就是先选择最 hottest 的 expert 加载计算，注意 bit 顺序，为了最高程度的 overlap
