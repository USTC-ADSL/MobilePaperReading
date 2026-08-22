---
title: "AutoDroid: LLM-powered Task Automation in  Android"
conference: MobiCom'26
---
### Background & Motivation

基于开发者研发 API 或者是需要大量人工演示数据的构建 GUI Agent 的方法的可扩展性较差。因此采用 LLM 来帮助生成能够完成用户交付给 GUI Agent 的任务。

主要挑战有：
1. GUI 表示通常采用 GUI tree（本文面世时尚未考虑多模态大模型），这是一个高度结构化的数据结构，LLM 难以直接理解，而且其通常较长（约 40k tokens），因此需要寻找一个能够简化表示当前 UI 状态的方法；
2. LLM 通常具有丰富的世界知识，但是其对 GUI 内如何操作却并不了解，比如删除日历中的所有提醒事项需要"click Settings -> click More -> click Remove all events"；
3. 使用 GPT 等云端提供的模型费用较高。

### Design

#### Task-oriented UI Prompting

- LLM 在预训练时大量接触了 HTML 文件，因此使用 HTML 格式来简化 UI State 同时可以增强 LLM 对 UI State 的理解；
- 对于屏幕放不下需要 Scroll 的 UI State，不让 Agent 来生成 Scroll 动作而是直接把看不到的信息搜集；
- 用一些规则约束大模型的生成。

![AutoDroid-Prompt.png](https://img.195806.xyz/file/1787418923076_AutoDroid-Prompt.png)

#### Exploration-based Memory Injection

离线阶段：
- 对于每一个 App，采用随机探索器探索各个 UI element 的作用，将其变化后的 UI 与变化前的 UI 用边连起来，如此形成一个图，称为 UI 转移图；
- 针对 UI 转移图，对其中每个 UI State 的每个 UI element 都用大模型分析它的作用（称为模拟任务），构建模拟任务表，同时构建 UI 功能表；
- 对这些模拟任务进行嵌入，生成向量。

![Simulated-task-table.png](https://img.195806.xyz/file/1787419325387_Simulated-task-table.png)

在线阶段：
- 计算用户任务与模拟任务之间的相似性，选出相似度最高的一些 element；
- 如果当前的 UI State 中某个 element 匹配到了离线阶段保存的模拟任务表中某路径中某个 element，就把这条路径能最终完成的任务说明添加到 HTML 中关于这个 element 的说明中，例如：
```
<!-- 原始 -->
<button label='More options'></button>

<!-- 增强后 -->
<button label='More options' 
        onclick='navigate to GUIs that can: 
                 1. add contact holidays and anniversaries, import and export events, manage settings, 
                 2. Delete all events in the app, manage event reminders, etc.'>
</button>
```

#### Local LLM

如果不使用 GPT 等云端模型，只使用本地模型，即便加上了上述的 Prompt Engineering，效果仍比较差，因此考虑微调本地模型。

训练数据采用如下步骤生成：
1. 利用模拟任务表，生成 (question, answer)，其中问题包括：任务、历史动作、当前 UI 的 HTML 表示，同上文一样的 Prompt 模板，answer 则是当前 UI 应该采取的动作；
2. 将上述的问题、答案打包给 GPT 让其生成思维链，GPT 给出的思考过程和最终答案作为新的答案。

使用上述构造的答案可以让本地模型也具备一定的推理能力。

#### Multi-granularity Query Optimization

- Token 剪枝，删去一些没有视觉信息的背景等元素；
- 上文提到的，主动进行 Scroll；
- 上文在线阶段中查到的相似度高的模拟任务，如果相似度高出一个阈值，则不进行 LLM 生成，直接采用该任务对应的路径。

### Evaluation

| 模型                       | 动作准确率     | 任务完成率     |
| ------------------------ | --------- | --------- |
| Vicuna-7B (AutoDroid)    | 57.7%     | 41.1%     |
| GPT-3.5 (AutoDroid)      | —         | 40.3%     |
| GPT-4 (AutoDroid)        | **90.9%** | **71.3%** |
| GPT-4 基线 (LLM-framework) | 65.4%     | 31.6%     |



