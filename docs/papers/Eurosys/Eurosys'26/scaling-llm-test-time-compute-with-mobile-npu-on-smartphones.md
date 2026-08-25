---
title: Scaling LLM Test-Time Compute with Mobile NPU on Smartphones
conference: Eurosys26
---
围绕 Hexagon NPU 的结构、HMX/HVX 计算单元、量化布局做了详细分析，并结合 HMX 矩阵运算的特性，将推理扩展为 Test-Time Scaling。比如 Best-of-N、Beam Search，并行多个推理并选择最好的结果。

## Motivation

手机小模型能力不足，而增大参数量会显著增加内存与带宽。

作者观察到，LLM Decode 时输入通常只有一个 Token，GEMM 退化为 GEMV；但 Hexagon HMX 按大 Tile 计算，例如 FP16 基本 Tile 为 32×32，因此：

$$
[1,32]\times[32,32]
$$

实际只使用 Activation Tile 的 1/32 行，矩阵算力大量闲置。

作者因此把 Best-of-N、Beam Search 等方式作为“额外行”填入 HMX，填补算力空缺。

但难点是 QNN 的粗粒度量化（最细是 Per-Channel W4，每行量化）会大幅损失精度。所以提出了符合 HMX 结构的 Group 量化方式：每 N 个数据共享一个量化参数，粒度比一行更细。

------

## Background

### 1. NPU 架构：为什么 HMX 很快、HVX 却容易成为瓶颈

![image-20260825194823294.png](https://img.195806.xyz/file/1787658526537_image-20260825194823294.png)

Hexagon 是 **Scalar + Vector + Matrix** 架构。

#### Scalar Core

Scalar Core 负责逻辑控制调度，只有约 6–8 个 VLIW Hardware Threads，通过 4 个 VLIW Slot 发射指令。

VLIW（Very Long Instruction Word）表示一个 Cycle 内能同时发出多种不同操作（Instruction Packet）。如果没有依赖，大量指令可以同时执行，例如：

```text
vector1 multiply
vector2 shift
load vector3
...
```

#### HVX

HVX 是 SIMD Vector Core，每个 Context 有 32 个 1024-bit（128B）Vector Registers。

例如，一个线程发出一条 Vector Instruction，一个 128B 寄存器就支持同时让 64 个 FP16 加法工作。

#### HMX

HMX 是专用 Matrix Core。

#### 内存结构

内存侧有：

- 1MiB L2 Cache；
- 8MB TCM。

HVX 可以从 L2 Cache 或 TCM 读取。

HMX 以及 Vector Scatter/Gather（聚合分散，用于处理非连续内存操作）只能访问 TCM。

DDR → TCM 主要由约 60GB/s DMA 搬运，比 L2 Cache 快。

这与 GPU 的大量 SIMT Thread 不同：NPU 用少量控制线程，通过宽 SIMD、VLIW 和专用矩阵指令，以更少的逻辑、更高的并行度减小能效损耗。

实测 V75 单 HVX Thread 的 FP16 GEMM 仅 32.93 GFLOPS，而 HMX 达到 12032.54 GFLOPS，相差 300 倍以上。

所以应该：

> **防止 Dequantization、Softmax、Layout Transformation 等 HVX 工作饿死 HMX。**

------

### 2. HMX Layout

![image-20260825204948163.png](https://img.195806.xyz/file/1787662223117_image-20260825204948163.png)

HMX 的 FP16 基本单位是 32×32 矩阵，2KiB，称为 Tile。

但它在 TCM 中并不是正常的行主序。

#### Figure 4(a)：Tile 内部排布

对每相邻两行进行转置，再顺序存储。

例如逻辑上：

```text
a0 a1 a2 ... a31
b0 b1 b2 ... b31
```

先经过转置，物理内存变成：

```text
a0 b0 a1 b1 a2 b2 ... a31 b31
```

然后处理第 2、3 行，以此类推。

合理推断：

$$
2\times32\times2B=128B
$$

两行数据恰好等于一个 HVX 1024-bit Register，因此这种布局天然适合 HVX 使用。

推测转置操作需要借用 HVX 单元中的指令。

#### Figure 4(b)：Tile 之间的排布

Figure 4(b) 是从大矩阵切分成一个个 Tile 的角度来看。

大 Weight Matrix 先切成多个 32×32 Tile，再以 Tile 为粒度按**列主序**排列。

原因是 HMX 内部的累加器结构，会按照此顺序做 Tile 级乘加运算。例如：

$$
Y_0=A_0W_{00}+A_1W_{10}+A_2W_{20}
$$

因此：

```text
W00
W10
W20
```

连续存储，可依次送入 HMX Accumulator。

------

## Methods

### 1. 针对 HMX 优化的细粒度量化方式

传统的 Group 量化方式往往按行取连续 N 个 Weight。

经过上述 HMX 转置后，这 32 个值在 TCM 中被打散，因此量化时是昂贵的非连续内存运算。

作者反过来做：

```text
FP16 Weight
    ↓
离线先变成 HMX Layout
    ↓
再每连续 32 个元素量化
```

由于 HMX Memory Order 是两行交错，连续 32 个元素逻辑上正好对应一个 2×16 的矩阵，因此得到 **Tile-Group Quantization**。

作者认为 Pretrained Weights 近似零均值分布，这种 Regrouping 不明显增加量化误差；实验也显示与普通 Group Quantization 精度接近。

但是 Group=32 的 INT4 权重只有 16B，远小于 HVX 的 128B SIMD Width。

Figure 7 因此再把 8 个 Group 合并：

$$
8\times32=256\ \text{INT4}=128B
$$

正好一次填满一个 HVX Register，同时把相应量化参数保留在局部 Super-Block 中。

本质是三种粒度对齐：

```text
32-element Quant Group
        ↓
128B HVX SIMD
        ↓
32×32 HMX Tile
```

与朴素方法最大的区别不是量化公式，而是把运行时 Layout Transformation 前移到离线模型布局设计。

------

### 2. LUT 查找表计算 Softmax

Softmax 的指数运算在 HVX 上没有专用单元，传统的多项式模拟又存在串行依赖，不利于 VLIW 的 Instruction-Level Parallelism。

查找表一共占用 64KiB，只占 8MiB TCM 的约 0.8%。

运行时直接把 FP16 输入的比特表示转换成表内偏移，然后使用 `vgather` 一次并行取回多项指数结果。

具体查找原理见论文。

------

## Results

### 1. 实验平台

实验覆盖三代 Qualcomm 平台：

- OnePlus Ace3：Snapdragon 8 Gen2 / V73；
- OnePlus 12：Snapdragon 8 Gen3 / V75；
- OnePlus Ace5 Pro：Snapdragon 8 Elite / V79。

模型主要为：

- Qwen2.5-1.5B / 3B；
- Llama3.2-1B / 3B。

数学推理使用：

- MATH500；
- GSM8K。

Baseline：

- llama.cpp OpenCL 的 Adreno GPU 实现；
- QNN FP16 作为参考。

------

### 2. Figure 11：并行生成利用 HMX 空闲算力

![image-20260825210956695.png](https://img.195806.xyz/file/1787663420407_image-20260825210956695.png)

并行生成确实把 HMX 原本闲置的计算能力利用起来。

主要原因是 HMX 原本空闲的 Tile 被更多生成路径填满，HMX 核心矩阵计算时间本身基本没有随 Batch 增长。

不过吞吐没有线性增长，因为 `lm_head/logits` 仍在 CPU 上执行；Batch=16 时，这部分甚至接近或超过总计算时间的 50%。

因此 Figure 11 同时证明了本文机会成立，也暴露出新的 CPU 瓶颈。


###  Figure 15：HMX-Friendly 量化布局消融
![image-20260825210941701.png](https://img.195806.xyz/file/1787663412750_image-20260825210941701.png)

Figure 15 是验证第 5.1 节最关键的消融实验。

Baseline 使用普通 Group 布局：

```text
普通 Group Layout
      ↓
运行时反量化
      ↓
Scatter 到 HMX 所需位置
```

仅加入 **HMX-Friendly 权重布局** 后，就因为消除了大量离散写入而明显降低延迟。

进一步加入 8-Group 合并等全部优化后，相比 Baseline 获得：

$$
9.65\times\sim19.04\times加速
$$

完整方案相比“完全不做反量化、只拷贝数据”的理论性能上界平均只慢约 27%，说明剩余反量化开销已经较小。
