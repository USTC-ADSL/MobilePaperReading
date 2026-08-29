---
title: "PuzzleMoE: Efficient Compression of Large Mixture-of-Experts Models via
  Fine-Grained Expert Merging and Bit-packed Inference"
conference: ICML 26
---
## Motivation
为了降低内存开销，先前的研究多聚焦于剪枝-专家丢弃（Expert Dropping）或专家合并（Expert Merging）。然而，现有的合并方法（如 HC-SMoE、Sub-MoE）存在一个致命缺陷：操作粒度过粗。它们在整个专家或张量级别进行聚类，将相似的专家直接取平均合并；和或者低秩近似，但这无法区分“共享通用特征”和“专家特异性特征”，这使得模型在较高的压缩率（如 50%）下性能变差。

PuzzleMoE 考虑了专家的特殊权重更细粒度的进行合并。并通过软硬件协同设计解决了细粒度稀疏带来的元数据存储难题，同时创建GPU的专用算子，加快计算。

## Methods
### 一、元素相似度
首先建模元素级相似，理论按照专家权重近似服从零均值高斯分布 $w \sim \mathcal{N}(0, \sigma^2)$，再计算相似度。实际经验直接从权重得出：

  $$\Delta_{i,j} = \frac{\vert{}\vert{}W_i\vert{} - \vert{}W_j\vert{}\vert{}}{\vert{}W_i\vert{} + \vert{}W_j\vert{}}$$

理论预测曲线与 Qwen1.5-MoE 等真实模型的经验数据高度吻合，说明权重是具有数值相关性的。

![puzzle-theory.png](https://img.195806.xyz/file/1787976363362_puzzle-theory.png)

实验表明，将相似度阈值\tau_{sim}$ 设为 0.4 时，表现最好。

### 二、相似度掩码和特殊值掩码
- 相似度掩码 ($M^{sim}$)：当 $\Delta_{i,j} < \tau_{sim}$ 时为 1，此时两个权重是相似的，取二者平均值。  
- 显著性掩码 ($M^{sal}$)：针对差异极大的特殊权重，保留二个专家中更为特殊的权值，并作出标记记录选择了哪个专家。
计算显著性得分： 先用校准数据集，得到一个平均激活值（同一维度上做L2范数计算），再用此激活值和权重的绝对值逐元素相乘，得到显著性得分。

得分高者在 $M^{sal}$ 中记为 1（无损保留原值），低者记为 0（强制截断为 0）。  
### 三、Bit-packing 与 Decode-GEMM
细粒度合并会产生海量的二值掩码和符号位，若单独存储会占用大量内存。PuzzleMoE 观察到 Float16 格式在 MoE 权重中存在严重的指数位（Exponent）冗余，其数值高度集中在 112 到 128 之间。所以可以省去几位的空间用于存储编码信息  

- 编码机制：通过平移操作，算法腾出了 3 个比特位，直接将两个专家的掩码和符号无缝嵌入到 Float16 张量的内部。加上原来fp16的符号位，有四位的空间：
  - 两位符号位，分别是两个专家的符号
  - 两位标志位：11表示相似，10、01 表示谁更特殊。

- 实时重构：在推理时，按照符号位、标志位还原专家 

$W_i = (-1)^{S_i} \odot M_i \odot W_{merged}$ 

GPU 内核专为恢复专家并计算所用。

## Result
PuzzleMoE 能够将常识推理的性能损失控制在 0.5% 到 1.5% 左右

![puzzlemoe-perf.png](https://img.195806.xyz/file/1787976322372_puzzlemoe-perf.png)

PuzzleMoE 由于采用 Bit-packing，算子仅需对合并后的张量发起一次访存，即可在寄存器级别解码并重构出两个独立的权重参与计算。这大幅降低了IO开销
