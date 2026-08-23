---
title: "ShadowNPU: System and Algorithm Co-design for NPU-Centric On-Device LLM
  Inference"
conference: Mobisys26
---
> 北邮Xu Mengwei团队
>
> https://arxiv.org/abs/2508.16703

## Background

场景：**手机端本地运行 LLM**，利用CPU / GPU / NPU 异构 SoC

LLM中Attention 需要严格的精度要求，一般以Float32的类型计算，而NPU不支持浮点数计算，所以现有的推理框架（mllm、llama.cpp等）会将Attention算子回退到CPU/GPU进行计算，这会造成

* **性能下降**
* **能耗上升** 
* **和其他任务抢资源** 等问题

目标：LLM 推理尽量在 **NPU-centric** 的路径上完成，减少 CPU/GPU 参与

方式：Sparse Attention，NPU用于估计重要token，CPU/GPU仅计算重要token的Attention（**稀疏计算**）

## Motivation

1.NPU INT8计算，直接算Attention会掉精度

​	NPU 上做 full attention，会因为量化误差导致明显准确率下降：平均约 **18 pp** 的精度下降。所以不能简单把 Attention 直接搬到 NPU 上计算。

2.直接做 Sparse Attention性能提升有限

​	 token 重要性估计阶段（相当于$Q \times K$）开销很大，当稀疏性很大时，Attention计算少但是估计阶段成为瓶颈。同时block级别的估计会造成性能损失，需要以token为粒度：

![image-20260822232741794.png](https://img.195806.xyz/file/1787492547072_image-20260822232741794.png)

3.NPU INT8 预测正确率较高

![image-20260822232719130.png](https://img.195806.xyz/file/1787492547662_image-20260822232719130.png)

4.单个NPU 静态图不能直接做tokens重要性的估计

​	估计阶段使用INT 8 量化后的$Q \times K$，需要规定量化放缩参数scale factor，然而静态二进制图无法更改量化参数和张量形状，面对不同的prompt量化失配会导致精度下降以及性能下降。

​	不同 head 的 scale 分布明显不同

![image-20260822232650576.png](https://img.195806.xyz/file/1787492546156_image-20260822232650576.png)

每条线是一个head（所以线比较粗），不同token的Q、K向量的值不一样，为了全部映射到INT 8，需要不同的scale factor。纵轴是所有样本中低于横轴当前值的比例，突然的上升说明分布有“堆积”或“集中”的现象

![image-20260822234447524.png](https://img.195806.xyz/file/1787492552045_image-20260822234447524.png)

桶数量不宜过多，准确率不再增加；Scale factor的间隔（step size）也应该合理设置，step size太大会造成精度下降，step size过小，桶会冗余

## Design

### NPU-based estimation

​	通过离线 profiling，评估head 重要性，不同 head 设置不同的 sparsity ratio（重要的head保留更多tokens）。对于每一个head：

1. 将 Q/K 做 INT8 量化
2. 在 NPU 上计算 dense Q·K
3. 将结果传给 CPU/GPU
4. CPU/GPU 做 top-k，获得重要 token 索引
5. 只对这些 token 做 Sparse Attention计算

### NPU compute graph bucketing

* 离线生成多个 NPU 图
* 按 scale factor 和 shape 组织成 buckets
* 在线时根据输入的 Q/K scale 选择最匹配的 bucket
* 选择与当前输入 scale 误差最小的 bucket

### Head-wise NPU-CPU/GPU pipeline

把每个 head 的 Attention计算 分成三个部分：NPU estimation、CPU/GPU top-k、CPU/GPU sparse QKV

然后进行流水线调度，并行执行：

* 不同 head 间交错执行
* 贪心的减少全局运行时间
* 如果多个head估计需要同一个bucket（NPU图），合并估计任务，充分发挥NPU算力

![image-20260822233455247.png](https://img.195806.xyz/file/1787492543652_image-20260822233455247.png)

（1）为串行；（2）以 head 顺序地并行（3）合并NPU Estimation任务 （4）合并NPU计算任务同时乱序调度执行

## Evaluation

测试设备：

**小米14**

* Snapdragon 8 Gen3
* 16+6 GB DRAM

**Redmi K60 Champion Edition**

* Snapdragon 8 Gen2
* 16+3 GB DRAM

默认只用一个  CPU core，其余 LLM 计算尽量放在 NPU，用于模拟“CPU/GPU 资源受限”的手机真实场景（highly limited CPU/GPU resources）

Attention Core的延迟：

![image-20260822234124242.png](https://img.195806.xyz/file/1787492544858_image-20260822234124242.png)

端到端推理时延：

![image-20260822234156687.png](https://img.195806.xyz/file/1787492548666_image-20260822234156687.png)

SoTA对比：

![image-20260822234254352.png](https://img.195806.xyz/file/1787492549246_image-20260822234254352.png)
