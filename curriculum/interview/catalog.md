# Go / Web3 专业面试场景

> 六条主线 · 18 个自包含模拟场景。已定义不等于真实学习者效果验证。

招聘面试下的专业方向；英语水平、技术深度和帮助模式独立。先 list 检索，再 show 单场景，教师资料需显式 --coach。

参见 [使用说明](README.md) 和 [技术面试协议](../../references/technical-interview.md)。

## 架构与业务全景 / Architecture

Explain lifecycle, state authority, completion semantics and explicit architectural trade-offs in simulated trading systems.

| 场景 ID | 任务 |
|---|---|
| `int-architecture-architecture-tradeoffs` | 托管订单簿与非托管AMM / Compare trading architectures |
| `int-architecture-project-explanation` | 讲清项目与证据边界 / Explain a simulated project |
| `int-architecture-trade-lifecycle` | 从订单到资产交割 / Explain a trade lifecycle |

## 交易与账本 / Trading

Reason about order races, reservations and idempotent settlement under stated custodial spot assumptions.

| 场景 ID | 任务 |
|---|---|
| `int-trading-ledger-reservation` | 预留到释放的资金闭环 / Close a reservation safely |
| `int-trading-order-race` | 部分成交与撤单竞争 / A fill races a cancel |
| `int-trading-settlement-idempotency` | 确认丢失后的重复结算 / Settle a replayed trade once |

## 衍生品与风险 / Risk

Distinguish margin boundaries, risk valuation, liquidation authority and price quality in fictional linear perpetual systems.

| 场景 ID | 任务 |
|---|---|
| `int-risk-liquidation` | 强平接管与旧执行者 / Hand over liquidation authority |
| `int-risk-margin-isolation` | 逐仓与全仓的边界 / Isolated versus cross margin |
| `int-risk-mark-price` | 标记价不等于可成交价 / Explain price semantics |

## 行情与流动性 / Liquidity

Explain order-book recovery, enforceable swap constraints and RFQ execution without treating quotes as guarantees.

| 场景 ID | 任务 |
|---|---|
| `int-liquidity-orderbook-recovery` | 盘口缺口恢复 / Recover an order-book feed gap |
| `int-liquidity-rfq-execution` | RFQ从报价到履约 / Finish an RFQ exchange |
| `int-liquidity-slippage-protection` | 报价到执行的滑点保护 / Protect swap execution |

## 链上后端与信任边界 / Web3

Practice unknown transaction outcomes, bounded signature authority and reorganization-aware indexing on an explicit EVM baseline.

| 场景 ID | 任务 |
|---|---|
| `int-web3-broadcast-timeout` | 广播超时后恢复付款 / Recovering an unknown broadcast |
| `int-web3-reorg-indexing` | 重组中的撤销与重放 / Recover a reorged projection |
| `int-web3-signature-boundaries` | 结构化签名的执行边界 / Bind a signed intent |

## Go 与可靠工程 / Go

Explain mutable-state ownership, reliable effects and deterministic recovery separately from language fluency or performance claims.

| 场景 ID | 任务 |
|---|---|
| `int-go-recovery-replay` | 确定性回放与完整快照 / Replay a complete state machine |
| `int-go-reliable-events` | 消费者重启与业务效果 / Make a consumer recoverable |
| `int-go-state-ownership` | Go订单簿状态所有权 / Who may mutate the book? |

Solana 与预测市场不属于本版必修覆盖。题卡是基于本地用户资料的原创英语改编，不是生产系统认证答案。
