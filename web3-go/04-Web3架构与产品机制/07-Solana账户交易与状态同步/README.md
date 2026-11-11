# Solana 账户交易与状态同步：核心深挖面试专题

<!-- 大白话导读开始 -->

## 先看懂：关键词大白话解释

| 关键词 | 大白话解释 | 在本文里怎么理解 |
|---|---|---|
| Solana 集群 | 一套独立运行的链网络 | 交易、余额和证据必须属于同一集群，不能跨网络拼接 |
| SPL Token Program | Solana 上管理代币的标准程序 | 主例只用传统版本，不默认支持 Token-2022 扩展 |
| M、TA、TB、A、B | 币种、两只代币账户和两方用户的代号 | A 有权从 TA 转出 M，TB 接收，B 不必为收款签名 |
| mint、decimals、原子单位 | 币种定义、显示小数位和最小整数单位 | M 的 decimals 为 6；100 M 写成 100,000,000，不能用浮点猜金额 |
| account.owner 与 authority | 前者是管理账户数据的程序，后者是业务操作权限 | TA 的所属程序是 Token Program，A 才是本例转账权限持有者 |
| PDA | 由程序和种子推导、没有普通私钥的地址 | 程序可在规定调用中为它提供签名资格，不等于任意资产归程序所有 |
| TransferChecked | 同时检查币种精度的代币转账指令 | 本例转 TA 到 TB，金额与 mint、精度和权限一起校验 |
| SOL、lamports、F | 网络原生币、其最小单位和实际手续费符号 | A 的系统账户另付 F；不从转出的 100 M 中扣 |
| I1、T1、σ1 | 业务意图、一次交易尝试及其签名标识 | 本地一个 I1 可以关联尝试，但不能阻止两份不同签名都在链上转账 |
| H1、hmax | 近期区块哈希与它对应的最后有效区块高度 | 限制原交易未来能否新执行；过期不能证明此前没成功 |
| slot 与区块高度 | 出块机会编号与实际区块进度 | slot 可能没有块，教学 slot 522 不能拿来和 hmax 比大小 |
| commitment | 对观察结果稳定程度的要求 | processed 是已处理观察，confirmed 已获较强投票确认，finalized 达到本模型最终性要求 |
| err 与 meta | 执行错误和交易执行附带资料 | finalized 也可能执行失败；成功还须 err 为空，费用读 meta.fee |
| RPC、PubSub | 节点查询接口和发布订阅通知 | 前者读证据，后者只提示该刷新；通知不保证逐笔完整历史 |
| getMultipleAccounts、context.slot | 一次多账户读取及其共同求值上下文 | 将 TA、TB、M 整组读取；context.slot 不是各账户最后写入版本 |
| minContextSlot | 限制读取不能早于某上下文的门槛 | 不能指定历史快照，也不能把多次请求锁在同一状态 |
| dirty、generation、epoch | 待刷新标志、提示代数和本地会话或来源代号 | 防止读期间新提示被清掉、旧来源结果混入；不是链上执行顺序 |
| revision、投影、stale | 本地发布版本、链上数据的查询副本和陈旧标记 | 一组余额原子发布；旧值可保留，但不能假装仍然新鲜 |
| 历史覆盖水位、checkpoint | 已证明完整处理到哪里的持久进度 | 不等于见过的最大 slot，不能跨越缺失或无法解码的范围 |
| Inbox、Outbox | 本地去重收件记录和随事务保存的待发送记录 | 帮助结果可靠交付，不让链与数据库变成一个事务 |
| ATA、WSOL、durable nonce | 关联代币账户、包装 SOL 和持久交易有效性机制 | 主例不创建 ATA、不用 WSOL 或 durable nonce；也不套用以太坊钱包的递增交易序号 |
| MVP | 只覆盖最小闭环的教学实现 | 只推演固定账户组刷新，不代表已做真实转账、历史回放或多副本测试 |

## 把整篇文章压缩成一个故事

A 想给 B 转 100 M。M 有六位小数，TA 起初有 1,000,000,000 原子单位，TB 为零。服务记录意图 I1，检查传统 Token Program、币种、账户和 A 的权限，构造 TransferChecked；用近期区块哈希 H1 和最后有效区块高度 hmax 生成尝试 T1。A 同意消息后签出 σ1，服务保存原始签名字节再发送；手续费由 A 的 SOL 系统账户另付，不挤占 B 应收的代币。

发送超时，服务继续查 σ1，必要时重发同一份字节，不能换个哈希重签就认定不会双转。超过 hmax 只排除旧交易今后凭 H1 新执行，仍需核查此前历史。教学主例中 σ1 在 slot 520 成功，服务等到 finalized 且执行无错才确认最终转账；账户通知另行触发一次 finalized 的 TA、TB、M 共同快照。本地读取期间若又来了提示，就保留下一轮刷新任务；断线、解码失败或队列溢出则标陈旧，不发布半组数据。

没有其他交易时，slot 522 的组快照显示 TA 为 900,000,000、TB 为 100,000,000，手续费 F 单列。数据库把整组余额、上下文、发布版本和待通知记录一起提交，页面分别展示最终结果与余额新鲜度，不能再按 σ1 扣一次。这个闭环证明的是所读当前态已收敛；期间逐笔历史仍需独立补齐和覆盖证据，同 slot 的通知到达顺序也不是链上写入顺序。全部数值是教学推演，不是链上实验记录。

---

<!-- 大白话导读结束 -->

本专题按 [Go / Web3 交易系统核心深挖面试提示词](../../go-web3专家提示词.md)组织，面向需要解释链上执行、Go 服务和链下状态同步边界的学习者。Solana 与链上抓取解析在[招聘要求](../../../深入/面试要求.txt)中属于加分项，不据此推断目标公司的实际产品或部署方案。

**交付状态：正文全部落盘，文档结构与本地链接检查通过。** 15 个独立母题、128 层完整问答，加本页公共内容与唯一简洁 MVP。“高频”表示优先学习的常见工程问题，没有统计频次或排名含义；这里的实现是教学设计，不是个人生产经历。文档静态检查与手工推演不等于链上实验或工程测试。

## 第一部分：文字全流程

### 1.1 讨论基线

采用**单 Solana 集群、非托管钱包、传统 SPL Token Program、普通代币转账**。不把 EVM nonce、平台托管余额、订单簿成交或 AMM 换币混入同一笔业务。

| 维度 | 全文共同前提 |
|---|---|
| 资产 | 普通 mint M，`decimals = 6`，数量使用原子整数 |
| 参与方 | A 控制源代币账户 TA，B 控制目标代币账户 TB；A 是源账户转账权限持有者 |
| 账户准备 | TA、TB 和 M 已存在；不创建 ATA，不关闭账户，不在主例引入租金变化 |
| 指令 | 传统 Token Program 的 `TransferChecked(TA, M, TB, A, amount, decimals)`；A 签名，B 无须签名 |
| 费用 | A 的系统账户另付 SOL 手续费；最终以交易 `meta.fee = F` lamports 为准，不从 M 的转账金额中扣除 |
| 资产权威 | TA、TB 的链上 Token 数据决定代币余额；本地数据库只保存意图、观察证据与投影，不拥有另一套可扣款余额 |
| 完成策略 | processed／confirmed 仅作可撤销预览；finalized 且执行成功才是本模型最终转账结果，展示同步另有进度 |
| 当前态同步 | PubSub 作为失效提示；一次 finalized `getMultipleAccounts([TA,TB,M])` 获取共同上下文的小组快照，本地原子发布 |
| 历史业务同步 | 与当前余额分开，使用具有明确覆盖范围的最终交易／区块证据；账户通知不作为逐笔交易日志 |
| 排除能力 | Token-2022 扩展、WSOL、跨链、托管充提、自定义链上幂等程序、durable nonce，不作为已实现能力 |

服务只控制自己的编排路径。用户拿到签名后仍可能通过钱包自行广播；服务端加锁不能撤销这份链上执行资格。后文比较 ATA、Token-2022、durable nonce 或自定义程序时，都会明确说明改变了前提。

### 1.2 贯穿案例

- 初始：TA 持有 **1,000 M = 1,000,000,000 原子单位**，TB 为 0。
- A 发起意图 `I1`：向 TB 转 **100 M = 100,000,000 原子单位**。
- 构造交易尝试 `T1`，使用 recent blockhash `H1`，保存对应 `lastValidBlockHeight = hmax`；签名为 `σ1`。
- 在没有其他交易的主例中，最终成功后 TA 为 **900,000,000**，TB 为 **100,000,000**；A 的系统账户减少实际手续费 **F lamports**。
- 为展示读写边界，教学上设 T1 位于 slot 520，共同余额快照的 `context.slot = 522`。这些数字只是示意，不是链上记录；**slot 522 不能拿来与区块高度 hmax 比较**。

后续余额变化、失败和并发转账都是独立变体，不与主例重复叠加。真实钱包可能存在其他转账，因此快照中的总差额不能唯一归因给 σ1。

### 1.3 从用户意图到最终结果和展示

```text
A 发起转账〔I1、集群、TA、M、TB、100,000,000 原子单位〕
    ↓
接入服务固定载荷，校验地址、程序、mint、权限、整数与请求身份
    ↓
读取必要状态，构造 TransferChecked，获取 H1 与 hmax
    ↓
模拟并展示待签消息〔金额、接收账户、程序、网络、费用边界〕
    ├─ 校验或模拟拒绝 → 不把意图记成成功；模拟无链上状态变更
    └─ A 同意并签名 → 保存 T1、完整签名字节、σ1、H1、hmax
                             ↓
服务发送已保存字节〔发送超时仍保留原尝试〕
                             ↓
RPC 接收与转发〔不代表执行，不代表最终确认〕
                             ↓
验证者验证签名、有效窗口、账户访问与执行条件
    ├─ 未收录／暂不可知 → 跟踪原 σ1，不因超时另签一份转账
    ├─ 已执行失败 → 转账状态回滚；实际落链失败仍可能收取手续费
    └─ 已执行成功 → 同一交易内 TA 减 100 M、TB 加 100 M
                             ↓
确认跟踪器保存 σ1 的执行结果、slot 与确认级别
    ├─ processed／confirmed → 仅暂态；可能撤回并重新核验
    └─ finalized 且 err = null → I1 的链上转账结果可最终确认
                             ↓
状态同步器收到提示或周期触发，读取 [TA,TB,M] 的 finalized 组快照
                             ↓
校验身份、布局、上下文与轮次，在本地事务内切换整组投影与 revision
                             ↓
查询和通知按版本呈现〔最终转账结果 + 余额快照上下文 + 同步新鲜度〕
                             ↓
主例闭合：转账已最终成功，且本地视图已反映相应或更晚的规范状态
```

跟踪器与余额同步器是并行证据链，不要求等待账户通知才能查签名，也不假设账户通知一定由 σ1 造成。若要宣称余额视图已经覆盖交易位置，必须核验相同集群和 finalized 规范上下文、快照读取 slot 不早于该交易位置；不能只比较两个未经验证来源的整数。

### 1.4 主要异常与取消边界

```text
签名前取消 → 停止本地编排，不产生新的签名资格
签名后取消／context 超时 → 只能停止服务端等待，不能撤销可广播交易
发送超时 → σ1 为未知，不等于失败；可核查并重发原字节
更新 H1 后重新签名 → 新签名、新交易；普通 transfer 没有 I1 消费屏障
```

```text
区块高度超过 hmax
    ↓
排除原交易未来再凭 H1 新执行的可能
    ↓
仍须核验此前是否已成功进入最终规范链
    ├─ 找到最终成功 → 完成 I1，禁止补转
    ├─ 证据足以确认最终失败／无成功且不可再执行 → 才能重新决策
    └─ 历史缺失、源不可靠、仍有分叉歧义 → Unknown，等待或人工核验
```

```text
订阅断线／队列溢出／账户解码未知
    ↓
标记相应视图 stale 或不可用，保留最后一次有上下文的已知值
    ↓
重新订阅 + finalized 小组全量读取 + 周期核对
    ├─ 当前余额恢复 → 只宣布当前态收敛
    └─ 期间逐笔历史不完整 → 继续独立回补，不假装历史已经补齐
```

同一交易中的多条普通指令要么整体成功，要么其普通业务状态回滚。**整笔转账成功与本地“部分处理成功”是两回事**：后者是消费和展示故障，不得补发一笔链上转账来修页面。账户创建、关闭和 durable nonce 的特殊持久变化不在主例中。

### 1.5 状态、数量与完成含义

| 阶段 | 数量与权威状态 | 允许对外表达 |
|---|---|---|
| I1 已受理 | 本地保存不可变意图，链上余额未因此改变 | 请求已记录 |
| T1 已签名／已发送 | 本地知道 σ1 和原字节；资金可能尚未改变 | 已提交或结果查询中 |
| 交易被处理且成功 | 所在分叉中 TA=900 M、TB=100 M；F 另计 | 暂时执行成功，不是最终终态 |
| 交易最终成功 | 在采用的最终性和信任假设内，σ1 的成功不可常规撤回 | 转账已最终成功 |
| 当前组快照发布 | 同一读取上下文下的 TA、TB、M 一起更新 | 余额截至该上下文；新鲜度单独声明 |
| 历史覆盖推进 | 目标范围内支持的业务证据已完整保存并应用 | 该范围的业务历史完整，不代表任意程序每次写入都被还原 |

## 第二部分：核心板块

| 核心板块 | 决定什么、为什么核心 | 状态权威与上下游交互 |
|---|---|---|
| 账户与权限模型 | 交易究竟能改变哪个账户、谁有权签名 | 运行时管理账户规则；Token Program 管理代币数据；本地只验证与投影 |
| 消息构造和执行 | 用户签了什么、并发和失败怎样裁决 | 已签消息不可悄悄改；验证者按账户访问约束和程序规则执行 |
| 确认与重试 | 什么叫成功、超时后还能不能补发 | 保存 signature、执行结果、确认级别和有效窗口，不拿客户端时间制造终态 |
| 数据源与读取 | 实时提示是否足够、怎样获得可信当前态 | RPC／PubSub 能力显式；小组快照原子发布，不能编造写序或重放游标 |
| 业务因果和本地一致性 | 一笔转账对应什么效果、如何避免重复本地记账 | 交易证据解释业务；余额快照表示当前态，两者不互相替代 |
| 恢复与运行治理 | 断线、重启、切源、升级后能否正确收敛 | 独立当前态与历史水位；Go 单所有者、有界资源、解码隔离、同口径对账 |

## 第三部分：核心 20%

| 核心机制 | 流程位置 | 为什么核心 | 不掌握的后果 | 重点深入细节 |
|---|---|---|---|---|
| 三种 owner／权限分离 | 账户校验 | 决定状态写权限和资产控制权 | 错把钱包签名当任意数据写权限 | account.owner、Token authority、PDA signer |
| 原子整数与程序身份 | 构造、解码 | 同样的字节可能有不同业务意义 | 金额精度错、伪造账户、扩展规则误用 | mint、decimals、Token Program、checked arithmetic |
| 交易原子性与账户冲突 | 执行 | 决定并发结果和回滚边界 | 认为读余额后即可安全并发支出 | signer／writable、冲突、执行时校验、费用例外 |
| 执行结果与最终性正交 | 跟踪 | 决定能否宣布最终成功 | finalized 失败被记成功 | err、confirmationStatus、slot、分叉撤回 |
| 尝试身份与未知重试 | 发送 | 普通转账没有业务恰好一次屏障 | 改 blockhash 补发导致双转 | I1／T1／σ1、原字节重发、过期与历史证据 |
| 提示流与权威读取分离 | 状态同步 | 标准 PubSub 不是持久事件日志 | 断流静默漏单、同 slot 旧值回写 | dirty、finalized 重读、context、minContextSlot |
| 当前态与逐笔历史分离 | 恢复、因果 | 两种完整性需要不同证据 | 余额对了却漏掉业务历史 | 组快照、交易 meta、最终范围覆盖、未知隔离 |
| 局部事务与可恢复发布 | 投影、交付 | 本地多账户必须同版本可见 | 半更新、重复扣款、水位越过缺口 | revision、checkpoint、Inbox／Outbox、writer epoch |

## 第四部分：设计与规则

### 4.1 不变量与证据边界

1. 主例普通 Token 转账中，`TA减少量 = TB增加量 = 100,000,000`，同币种总额不变；SOL 手续费单列，不与 M 相加。不得使用浮点承载金额判定。
2. `account.owner` 是所属程序，Token 数据中的 owner／authority 是代币支配权限；钱包签名、PDA 派生和程序所有权不能互相替代。
3. 受理、签名、发送、被处理、执行成功、最终确认、投影可见是不同事实。confirmationStatus 不能替代 err。
4. 同一已签交易重发不变成另一笔业务；重签会创建新的执行机会。本地唯一 I1 不为传统 Token Program 增加链上幂等能力。
5. `context.slot` 表示读取或通知上下文，不能普遍当作账户最后写入版本；同 slot 多次写不靠 `(pubkey, slot)` 排序。
6. 基线不直接应用账户通知负载。只有通过校验的 finalized 组快照可以替换当前权威投影；组内 TA、TB、M 与上下文、revision 同事务提交。
7. dirty generation、读取轮次、source epoch、本地 revision 都是本地控制元数据，不是 Solana 的全局执行序号。
8. 余额快照可以已经包含 σ1 和后续交易，既不能再按 σ1 扣一次，也不能只凭差额断言 σ1 成功。
9. 当前态已刷新不证明历史无缺口；历史覆盖水位不越过未确认完整、未解码或未提交的范围。
10. 正常分叉撤回只作用于暂态；可信 finalized 结果出现矛盾时按信任／最终性事故隔离，不能自动覆盖审计历史。

### 4.2 最小职责架构

```text
A 钱包〔持有签名权〕
    ↕ 不可变消息与签名
意图／发送服务 → 已签名 Attempt 存储 → RPC 发送
                                      ↓
                             Signature 确认跟踪器
                                      ↓
                               最终业务结果

PubSub 提示 + 周期时钟 → dirty 调度器 → finalized 组快照读取
                                             ↓
                                      校验／解码隔离
                                             ↓
本地数据库〔意图证据、组快照、revision、Outbox〕 → 查询／通知

历史 RPC／归档 → 最终区块覆盖扫描 → 交易解析 → 业务历史／覆盖水位
                            ↘ 与签名跟踪及当前态进行同口径核对
```

这是职责划分，不要求每个方框独立成服务。不默认引入 Kafka、Redis 或自建验证者；需要更强的写入历史时，必须另行选择并验收提供该能力的数据源。

### 4.3 核心对象和状态

| 对象 | 最小必要信息 | 不得误解为 |
|---|---|---|
| Intent | cluster、I1、A、TA、TB、M、rawAmount、载荷摘要、业务阶段 | 链上已消费的唯一键 |
| Attempt | T1、I1、原签名字节、σ1、H1、hmax、发送记录 | 未得到状态即可安全替换的临时 HTTP 请求 |
| TxObservation | 来源、σ1、slot、err、confirmationStatus、原始响应；可取得时保存区块身份 | 单一强度整数；最终成功与最终失败都可 finalized |
| AccountGroup | TA／TB／M 原始字段、解码整数、finalized context、来源 epoch、revision、freshness | 各账户最后一次写入版本或逐笔成交历史 |
| RefreshTask | 本地 dirty generation、轮次、in-flight、重试预算 | 可用作历史重放的链游标 |
| HistoryRange | 集群、规范区块身份、范围、获取／解码／应用状态、覆盖证据 | 见过的最大 slot |
| Outbox／Inbox | 稳定结果身份、revision、事件类型、投递与应用状态 | 自动覆盖链上幂等或无限去重期限 |

业务阶段允许 `Pending`、`Unknown`、`FinalizedSuccess`、`FinalizedFailure` 等明确语义；过期证据是维度之一，不把“过期”直接等价为“从未成功”。投影同步可处于 `syncing/stale/fresh-as-of-context`，不反向改写已充分证明的链上结果。

### 4.4 API 和实现取舍

- 显式设置 commitment。`getSignatureStatuses` 的状态确认级别从返回值读取，不能凭空给所有方法套同一个 commitment 参数。
- `getMultipleAccounts` 一次最多 100 个地址，本例只有 3 个；单响应共同上下文不扩展为多次请求同一 Bank。`minContextSlot` 只是最低求值上下文，不能锁定历史 slot。
- `accountSubscribe/programSubscribe` 没有本文所需的逐写历史、稳定续传或完整初始化保证。断线重订阅不代表缺口已补；周期刷新负责发现没有任何提示的变化。
- `getProgramAccounts(withContext=true)` 可用于有范围定义的当前态发现，但大范围分页、账户离开过滤集合、关闭账户以及固定切点需要单独设计，不能把固定三账户方案直接扩展成全网索引器。
- Go 中由单一 owner 管理一个快照组的调度状态；RPC 在有界 worker 中进行，结果回到 owner 串行裁决。数据库事务负责本地原子性；链与数据库之间不存在跨域原子提交。

## 第五部分：高频面试母题地图

以下 15 个母题从流程和横向故障约束确定，不以题数凑覆盖。账户权限、执行并发、最终性、数据源、顺序、快照、因果、本地一致性各有独立问题；恢复、切源、Go 和治理则检验这些保证在故障中是否仍成立。

| 编号 | 面试母题 | 文件名与相对链接 | 流程／约束 | 独立重点 | 深入层数 |
|---|---|---|---|---|---:|
| 01 | 一笔转账怎样从用户发起走到本地最终可见？ | [01-转账全流程与状态权威](01-转账全流程与状态权威.md) | 全链路 | 权威、完成点与双证据链 | 8 |
| 02 | 怎样理解账户、Program、PDA 和代币权限？ | [02-账户模型权限与PDA](02-账户模型权限与PDA.md) | 账户校验 | 所属程序、权限、地址推导 | 8 |
| 03 | 怎样构造一笔用户真正同意的 Solana 交易？ | [03-交易消息签名与构造校验](03-交易消息签名与构造校验.md) | 消息与发送 | 不可变消息、模拟、v0／ALT、资源预算 | 8 |
| 04 | 并发转账怎样执行，失败到底回滚什么？ | [04-账户锁并行执行与交易原子性](04-账户锁并行执行与交易原子性.md) | 执行 | 冲突、运行时权限、原子性及费用 | 8 |
| 05 | 怎样处理 commitment、分叉和业务最终性？ | [05-Commitment分叉与最终性](05-Commitment分叉与最终性.md) | 确认与撤回 | 暂态／稳定态、来源和事故边界 | 10 |
| 06 | 超时、过期和重新签名怎样避免重复转账？ | [06-交易确认过期与重试幂等](06-交易确认过期与重试幂等.md) | 尝试生命周期 | 原字节重发、未知结果、历史证据 | 10 |
| 07 | RPC、WebSocket 和 Geyser 各能保证什么？ | [07-RPC订阅与数据源能力边界](07-RPC订阅与数据源能力边界.md) | 数据接入 | 提示／状态／历史能力矩阵 | 8 |
| 08 | 同一账户同 slot 多次更新怎样正确处理？ | [08-同Slot更新顺序与投影版本](08-同Slot更新顺序与投影版本.md) | 顺序约束 | 不可排序输入、本地版本、同源契约 | 8 |
| 09 | 快照、订阅与断线回补怎样闭合？ | [09-快照衔接断线回补与完整性](09-快照衔接断线回补与完整性.md) | 当前态和历史完整性 | 同切点边界、重扫、独立覆盖水位 | 10 |
| 10 | 怎样从交易和账户变化解释一笔业务？ | [10-交易解析与账户变更因果](10-交易解析与账户变更因果.md) | 业务解析 | meta、CPI、账户索引与金额归因 | 8 |
| 11 | 链上成功与本地多状态怎样保持一致？ | [11-链上结果与本地业务一致性](11-链上结果与本地业务一致性.md) | 跨域一致性 | 非托管边界、局部事务、可靠交付 | 10 |
| 12 | 崩溃后怎样恢复投影和历史处理进度？ | [12-持久水位重放与故障恢复](12-持久水位重放与故障恢复.md) | 恢复 | 完整前缀、事务水位、重放和围栏 | 8 |
| 13 | 多 RPC 怎样核验与切换而不拼错状态？ | [13-多RPC核验与故障切换](13-多RPC核验与故障切换.md) | 信任与容灾 | 集群、上下文、独立性、能力迁移 | 8 |
| 14 | Go 怎样落实状态所有权和有界背压？ | [14-Go并发状态所有权与背压](14-Go并发状态所有权与背压.md) | 资源和并发 | owner、buffer、热点、过载与取消 | 8 |
| 15 | 解码升级、对账与监控怎样证明数据可信？ | [15-解码演进对账与可观测性](15-解码演进对账与可观测性.md) | 质量治理 | 隔离、同水位对账、血缘、验收 | 8 |

## 第六部分：连续面试问答阅读方式

完整双方问答位于上表的独立文件，每个文件承载同一母题的全部追问和结尾收束，不按层拆文件。建议先读 01—06 讲清业务与执行，再读 07—10 理解数据同步，最后用 11—15 检验恢复、交付与运行边界。

## 第七部分：工程实践——一个简洁 MVP

### 7.1 目标与范围

**只验证固定账户组的“通知失效 → finalized 重读 → 原子发布 → 读期间新提示不被吞掉”闭环。** 不构造真实交易，不做逐笔历史回放，不证明 PubSub 完整，不实现生产级复制、跨进程围栏或所有解码器；这些均不隐藏在一个伪造的“一致性函数”里。

前提：一个进程、一个 owner、一个读取 worker；`known` 表示已取得有效组快照。`fresh` 只表示本地没有已知待处理提示、来源连接正常且未超过刷新期限，不承诺与链上每一瞬间同步。所有事件都回到同一 owner，网络调用异步但同时最多一轮；下面的数据库事务是本地操作，不是链上事务。

### 7.2 核心伪代码

```text
saved = DB read last committed group  // 数据库不可用则暂停发布，不能当成空库
state = {dirty: 0, applied: -1, inFlight: false, connected: false,
         known: saved exists, epoch: newLocalSessionId(),
         slot: saved.slot or 0, revision: saved.revision or 0, hash: saved.hash or empty}
if state.known: DB mark saved group stale  // 保留已提交基准，强制重新读取

on dirtyHint or periodicTick or connectionChanged:
    update connected when applicable
    state.dirty += 1
    if state.known: DB set group.fresh = false
    startReadIfNeeded()

startReadIfNeeded():
    if state.inFlight or (state.known and state.dirty == state.applied): return
    state.inFlight = true
    task = {epoch: state.epoch, generation: state.dirty}
    worker read [TA, TB, M] with commitment=finalized,
        minContextSlot=state.slot; return task, response to owner

on readResult(task, response):
    if task.epoch != state.epoch: return  // 不同本地会话的结果不能发布
    state.inFlight = false
    if error or missing account or wrong program/mint/authority/layout:
        keep old values; mark unavailable/stale; schedule bounded retry; return
    decode raw integer amounts; reject overflow or incompatible decimals
    S = response.context.slot
    H = hash(canonical raw fields of [TA, TB, M])
    if S < state.slot: mark stale; schedule retry; return
    if state.known and S == state.slot and H != state.hash:
        quarantine conflicting response; alert; return
    fresh = state.connected and state.dirty == task.generation
    begin local DB transaction
        replace all three accounts and context as one group
        set revision = state.revision + 1, fresh, observationTime
        insert outbox(groupId, revision, S, H, fresh)
    commit
    if commit outcome unknown:
        pause publication; DB read committed group and matching outbox identity
        restore state.known/slot/revision/hash from committed data
        keep dirty; schedule retry only after recovery; return
    if definitely rolled back: keep old state; schedule bounded retry; return
    state.known = true; state.slot = S; state.hash = H
    state.revision += 1; state.applied = task.generation
    if state.dirty != state.applied: startReadIfNeeded()
```

启动时先载入数据库已提交的组、revision、context 和 hash，标 stale 后强制读取；只有确认数据库中没有旧组才使用零基准，数据库读取失败不能当成空库。重启保留旧组作为有上下文的陈旧视图，再从新本地会话 epoch 重读。提交结果不确定时，暂停新发布，待数据库确认事务已提交还是已回滚并恢复基准；不能复用内存里的旧 revision 猜测重试。断线期间 HTTP 读取仍可更新最后已知快照，但 `fresh=false`；连接恢复本身也产生新的 dirty。读取失败的退避、最大重试并发和刷新期限是明确的配置边界，不用无限 goroutine 自动重试。

单响应内 TA／TB／M 是共同读取上下文。查询时还必须以 observationTime 检查刷新期限，过期就显示 stale，不能永久信任存储的 fresh 布尔值。本地 hash 用于检测同 finalized 上下文的内容冲突，不用于证明 RPC 真实性；若需要跨源核验，仍必须验证集群与对应规范状态。真实系统还需要持久 writer fencing，不能照搬进程内 epoch 冒充多副本隔离。

### 7.3 输入与预期结果：手工推演

以下均为独立输入，不声称执行过网络或工程测试。

| 输入 | 预期结果 |
|---|---|
| 初次读到 slot 519：TA=1,000,000,000、TB=0 | 一组发布，revision=1；不凭余额宣告 I1 已成功 |
| σ1 已最终成功；之后读取 slot 522：TA=900,000,000、TB=100,000,000 | 组快照一次切换，revision 加 1；不再额外应用 −100 M／+100 M |
| 发起读取时 dirty=3，读取中收到新提示使 dirty=4 | 本轮可发布有上下文的已知快照，但 fresh=false，applied=3；立即安排下一轮，不能把 dirty=4 清掉 |
| 连续收到相同 slot 的两次账户通知，负载金额不同 | 只增加 dirty；不比较到达顺序、不直接覆盖账户，最终通过组读取确定当前态 |
| slot 522 已发布后，旧轮返回 slot 521 | 不回退组快照；保留旧值并重试，不把旧值包装成新 revision |
| 相同 finalized slot 522、相同配置却返回不同内容 hash | 隔离与告警，不凭最后到达者覆盖；这是需核验的矛盾 |
| 断线期间遗漏两笔相反方向转账，最终余额回到原值 | 周期重读可恢复当前余额；不能宣称发现了两笔转账，也不能推进逐笔历史完整性水位 |
| 读取 TA 成功而 TB 缺失或解码失败 | 不发布半组，不把 TB 写成零；旧组 stale，继续核验账户生命周期 |

## 技术依据与材料边界

- [Solana Accounts](https://solana.com/docs/core/accounts)、[Transactions](https://solana.com/docs/core/transactions)：账户结构、消息、签名与普通业务原子性。
- [Transfer Tokens](https://solana.com/docs/tokens/basics/transfer-tokens)：TransferChecked、mint、decimals 和权限。
- [Transaction Confirmation](https://solana.com/developers/guides/advanced/confirmation)：recent blockhash、确认、过期与 RPC 进度。
- [getSignatureStatuses](https://solana.com/docs/rpc/http/getsignaturestatuses)：执行结果、确认级别和历史查询边界。
- [accountSubscribe](https://solana.com/docs/rpc/websocket/accountsubscribe)、[programSubscribe](https://solana.com/docs/rpc/websocket/programsubscribe)：通知格式与订阅能力，不能从未说明的字段推导重放保证。
- [getMultipleAccounts](https://solana.com/docs/rpc/http/getmultipleaccounts)、[getProgramAccounts](https://solana.com/docs/rpc/http/getprogramaccounts)：当前态读取、上下文、过滤及 minContextSlot。
- [旧版 Solana 账户模型与数据同步](../../../深入/03-Web3与DEX深入/02-Solana账户模型与数据同步/README.md)：参考覆盖范围，不沿用旧版固定层数、评分锚点或“天然完整流”的假设。

官方接口、运行时和数据服务可能演进；落地时应固定目标集群、节点／SDK 版本与服务能力。本稿不承诺某商业 Geyser 服务一定具有特定排序、历史保留或重放保证。
