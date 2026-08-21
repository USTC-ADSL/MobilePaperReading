---
title: "V-Droid: Advancing Mobile GUI Agent Through  Generative Verifiers"
conference: MobiCom'26
---
### Background & Motivation

现有的 GUI Agent 常把 LLM 当作 action generator，首先对于每个 UI state，其候选动作是诸多的，因此直接生成一个动作极易产生幻觉，这导致任务成功率低，其次 decode 时延较高。

![VDroid-Performance.png](https://img.195806.xyz/file/1787311899325_VDroid-Performance.png)

作者观察到一个 UI state 中的可交互的 elements 数量大部分在 20 以下，因此，本文的核心思想是，将 LLM 的角色从 action generator 转化为 action verifier，对每个候选 action，agent 将其连同一些信息（如任务目标、历史动作、规则约束等）输入到 LLM，仅生成一个 Yes/No token（这是一个 Prefill Only 的任务），再将这个 token 连到一层 MLP，输出最终该 action 的分数。

![LLM-as-verifier.png](https://img.195806.xyz/file/1787312259717_LLM-as-verifier.png)

### Design

#### Workflow

本文展示的 GUI Agent 的工作流为：
1. 构建 action space，除了显式的可交互的 element 之外，还包括：返回 Home、返回上一级、等待、标志任务完成、打开应用等动作，将当前 UI state 的所有有效动作分类，可分为 click、press、scroll、type text、clear text等类型；
2. 将候选动作适配 prompt template，使用 LLM 为其打分（Prefill 过程，使用 Prefix Cache 以及 Batch Processing 可以加速）；
3. 对于一些需要额外动作的过程，比如在框内输入“123456789”，采用 Android 提供的 API 而不是在屏幕上一个个输入，这需要提供参数，使用一个 LLM 额外进行此生成任务。

![VDroid-workflow.png](https://img.195806.xyz/file/1787312827079_VDroid-workflow.png)

#### Pairwise Process Preference Training

没有针对性微调的 LLM 使用 verifier 方法效果极差，任务成功率为 0，原因在于打分区分率极低。训练思想：假设每步有 N 个动作，将成功动作与任意一个失败动作作为样本对，以此生成 N - 1 个样本，损失函数定为正确动作与失败动作的打分差距。

在实际任务中，Agent 难免走错一步，则将回退动作作为当前已经错了的 UI State 时的正确动作继续生成样本对，作为自我纠错样本对进行训练，这样可以让 Agent 在走错之后察觉到并回退。

![P3-training.png](https://img.195806.xyz/file/1787313704605_P3-training.png)

#### Human-Agent Joint Annotation

现有的数据集没有像上文构建的那样的精细的每步动作正反样本对，因此本文需要自行构建数据集，本文观察到：如果本轮动作的得分差异较大（熵较大），则 Agent 给出的最高分动作大概率是对的。因此，本文采取的 Human-Agent Joint Annotation 方法采用先用人工标注第一轮数据，然后用第一轮数据训练 Agent，再用这个 Agent 去标注扩展数据，如果某数据的得分差异（熵）小于阈值，则使用人工标注，如此迭代。

### Evaluation

- 设备：2 张 4090，运行 Agent
- 模型：LLaMA-3.1-8B
- 测试 Bench：AndroidWorld、AndroidLab、MobileAgentBench

#### 成功率与时延

在三个 Bench 上均超过之前表现最佳模型，分别达 59.5%、38.3%、49.0%，单步延迟约4.3s，对比成功率 SOTA 模型，快 6.1x。

