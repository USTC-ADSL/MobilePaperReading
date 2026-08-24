---
title: "Modality Plug-and-Play: Runtime Modality Adaptation in LLM-Driven
  Autonomous Mobile Systems"
conference: MobiCom'25
---
### Background & Motivation

多模态大模型面对非文本数据时的处理流程大致是：使用 Encoder 将特定模态的数据转化成向量，再使用 Aligner 将这些向量转化成符合要用到的语言模型（Decoder-Only）维度的 KV Cache，将这些 KV Cache 与语言模型接受的 query token 拼接处理。

端侧大模型（部署在 Jetson 上）有处理多种模态需求，如 RGB image、雷达点云等，然而如果将所有的模态全都同时考虑的话，则会造成计算以及内存开销太大，因此考虑将处理不同模态的 Encoder 按需加载（这个场景是本文新提出的）。比如：白天可以看 RGB image 来判断有没有车，但是晚上则最好使用雷达点云。

![MM-Plug-scenario.png](https://img.195806.xyz/file/1787561180160_MM-Plug-scenario.png)

通常来说，Decoder-Only 的大模型需要进行一定的微调才能更好地处理特定 Encoder 投影来的 tokens，所以不能直接将 Encoder 进行简单的加载/卸载，于是在使用的 Encoder 变化时进行训练。

现有的工作通常将 Encoder 投影得到的 KV Cache 拼接到 LLM 的每一层，这样做则导致在训练时即便冻结整个 LLM 的权重，也必须计算每一层激活值的梯度，带来高昂的计算开销。

### Design

将 M 个 Encoder 投影得到的 KV Cache 乘以各自可训练的权重 alpha（体现不同模态对结果的贡献），复制 N 份，注入到 LLM 的最后 N 个 Block 中，N 可变。

![MM-injection.png](https://img.195806.xyz/file/1787561817565_MM-injection.png)

离线时加载可能用到的 Encoder 和 Aligner，训练除了 Encoder 之外的所有参数。

在线时加载需要新增的 Encoder（可以是用户自行添加或者使用其他方式自动判断）和 Aligner，只训练 Aligner、alpha 以及最后 N 个块中获得 KV tensor 的 Projector，使用 LoRA 进行运行时训练。

### Evaluation

#### 实验设置

- 主要数据集：nuScenes-QA-mini（自动驾驶 QA，含 6 视角 RGB + 5D LiDAR）。论文对夜间 RGB 进行了降亮度 80% 和高斯模糊处理，以强制产生模态切换需求。
- 额外数据集：VQA-Rad、Path-VQA（医学图像 QA）、Instructional GQA（通用图像 QA），验证跨域泛化性。
- 模型：OPT（350M / 1.3B / 2.7B）、BLOOMZ-1.1B。
- 编码器：ViT-Base（RGB）、RangeViT（LiDAR）。
- 基线：Full LLM（全微调）、PromptFuse（输入层 prompt tuning）、eP-ALM（硬编码中间层连接）。
- 设备：RTX A6000（离线训练）、Nvidia Jetson AGX Orin（边缘设备在线适应）。

#### 实验结果

基本上数分钟能完成运行时训练，精度略高于基线，内存占用减少 20-30%，FLOPs 降低 3.6-3.7x。
