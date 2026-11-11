# 大问题 6：用户已经签了兑换意图，为什么还要 approve，permit 又改变了哪一层授权？

<!-- 大白话导读开始 -->

## 先看懂：关键词大白话解释

| 关键词 | 大白话解释 | 在本文里怎么理解 |
|---|---|---|
| Token / allowance | 代币合约、它保存的可代扣余额上限。 | 权威在 Token，不在 Go；足够额度不说明某次兑换已获业务授权。 |
| approve / spender | 设置使用额度的交易、获准使用额度的合约。 | 基线是 A 单独确认给 X 恰好 1000 USDC，不是把钱锁进 X。 |
| transferFrom | 依已有额度从 owner 转出代币。 | X 仍须满足余额与 allowance，不能让 Token 自动理解 SwapIntent。 |
| SwapIntent / recipient | 兑换条款签名、输出收款人。 | 固定花多少、换什么、路线及最低到账，收款人 A 不由 R 自选。 |
| EIP-2612 / permit | 特定 Token 授权签名标准、提交该签名修改 allowance 的入口。 | 仅是明确扩展，不能因代币名为 USDC 就认定实际部署支持它。 |
| owner / spender / value | 授权人、用额度者、授权额度。 | 扩展中 permit 明确给 X_p 本次 1000 USDC，而非给任意调用者。 |
| X / X_p / 域 | 原执行合约、新扩展实例、签名适用环境。 | X 不可升级；新组合入口部署为 X_p，意图与 spender 都要绑定新实例。 |
| permit nonce / 意图 nonce | Token 授权消息序号、兑换业务一次性编号。 | 各自消费各自状态，不能用前者代替 A/7/42。 |
| permit deadline | Token 最迟接受这份授权签名的时间。 | 及时建立的 allowance 不会在该时间到来后自动清零。 |
| 意图 deadline / `<=` | 合约最迟执行兑换的时间、允许相等。 | T0+120 秒时仍可执行；超过才拒绝，不逆转已经成功的兑换。 |
| 抢先提交 | 别人先把同一份有效签名交给 Token。 | 会先消费 permit nonce 并建立指定额度，不能改 spender，不等于必然盗款。 |
| try/catch / 后置条件 | 捕获调用错误、错误后仍须满足的实际状态要求。 | 不能无条件继续；须查当前 allowance 足够，再完整验证并执行意图。 |
| 组合事务 / 独立事务 | 一次调用内共同回滚、此前另一次已提交操作。 | 本次首次 permit 可随兑换回滚，先前单独提交的 permit 或 approve 不会。 |
| minAmountOut / 最小单位 | 最低实际输出、整数计量。 | 下限 490000000000000000 WETH 最小单位，实际 0.48 WETH 就整笔失败。 |
| used / epoch / 余额预检 | 一次性权限状态、权限代次、读取时的资金条件。 | 即使 permit 或预检成功，X 执行时仍要重新验权、查资金并校验输出。 |
| big.Int / uint256 | 精确大整数及其协议范围。 | 金额受限解析且避免共享可变值，不用 float64 把签名额度舍入。 |

## 把整篇文章压缩成一个故事

**起因：** 小林的 A 有 1500 USDC，基线中已单独 approve X 使用 1000 USDC，然后签下一笔至少收 0.49 WETH 的兑换。额度只让 X 有能力拉币，意图才限定这次怎么换、输出给谁；两者都不是冻结资金。成功样例实际收 0.50 WETH 后，小林有 500 USDC、0.50 WETH，本教学消耗模型下 allowance 为 0。

**处理及异常：** 现在明确换到支持所选 EIP-2612 的扩展，另部署带组合入口的 X_p，初始 allowance 为 0；小林另签 spender=X_p、value=1000 USDC 的 permit，兑换意图域也改为 X_p。若别人先独立提交这份 permit，额度已建立、Token nonce 已前进，组合调用再次提交它可能失败。X_p 只有在严格核对参数、重新查到当前额度足够，并继续完整验意图、期限、nonce 和路线时，才可容忍这一步失败；不能把“permit 出错”一律吞掉。

**结果及边界：** 若组合兑换只得到 0.48 WETH，就整体 revert。首次 permit 若属于同一事务，其额度与 nonce 增量一起退回事务前；若 permit 之前已独立提交，组合失败撤不掉那笔历史授权，正如基线失败也撤不掉旧 approve。permit 的两分钟期限只限制签名提交，不令已建立额度自动到期；取消意图不清额度，清额度也不永久取消仍有效的意图。Go 记录两套身份与区块快照，不能据此承诺未来一定成交。

---

<!-- 大白话导读结束 -->

[返回专题总览](README.md)

**流程位置与核心机制：** 本题定位“Token 允许执行合约扣款”和“执行合约允许某笔兑换”之间的交界，重点解释 allowance、permit nonce、意图 nonce 的权威归属，以及抢先提交和失败回滚的范围，不展开 Relayer 广播系统。

**沿用基线：** 教学 EVM 链 `chainId=1`，普通 EOA A 自持私钥，域为 `OneTrade / 1 / X`；X 不可升级，地址为教学占位值。A 初始持有 1500 USDC、0 WETH，已经通过独立且确认的 `approve` 授权 X 恰好 1000 USDC。`SwapIntent` 固定为 `owner、tokenIn、tokenOut、amountIn、minAmountOut、recipient、nonce、epoch、deadline、routeHash`，其中 `recipient=A、nonce=42、epoch=7、deadline=T0+120秒`，当前 epoch 为 7。兑换花 1000 USDC，至少得 0.49 WETH，示例实际得 0.50 WETH；不部分成交、业务费为 0。permit 仅在明确标注的扩展中讨论，不能因为代币叫 USDC 就假定其支持 EIP-2612。

## 第 1 层：两种授权为什么不能互相代替

**面试官：** A 已经签了“花 1000 USDC 换至少 0.49 WETH”的意图，为什么 X 还不能仅凭这份签名从 A 扣款？

**面试者：** 因为这份签名是 X 自定义兑换协议的权限证明，Token 合约不会自动理解它。X 验证意图后调用 `transferFrom(A, …, 1000 USDC)`，Token 仍然独立检查 A 的余额和 `allowance[A][X]`。基线中的独立 approve 解决“X 最多可以扣多少”，意图签名解决“X 这一次可以按什么路线、向谁交付多少资产”。两者缺一不可：只有签名而 allowance 不足，兑换失败；只有 allowance 而没有有效意图，X 必须拒绝执行。approve 不证明用户同意任意兑换，签名也不会冻结余额或替 Token 改写授权。

## 第 2 层：授权额度足够以后，如何限制实际扣款

**面试官：** 你说 approve 只给出了扣款能力。那 X 已经拥有 1000 USDC 的能力，怎样保证它不会按别的路线扣款，或者兑换失败却留下扣款结果？

**面试者：** 限制必须在不可升级的 X 的执行逻辑里成立，而不是靠 Relayer 自觉。X 校验 EIP-712 域、签名、当前 epoch、期限及一次性 nonce，核对规范路线的 `routeHash`，并要求路线目标、selector、资产和池都在内置白名单内，不能开放任意 call 或 delegatecall。入口有重入保护，used 在外部资金调用前标记，随后精确拉取 `1_000_000_000` 个 USDC 最小单位，执行受控兑换并向 A 交付至少 `490_000_000_000_000_000` 个 WETH 最小单位。used、扣款、兑换和输出检查属于同一 EVM 事务，后续失败全部回滚；此前已经确认的 approve 不在这次回滚范围内。

## 第 3 层：引入 permit 到底替换了什么

**面试官：** 上一答仍要求用户先单独发送 approve。若希望用 permit 减少这一步，能不能直接拿原来的 SwapIntent 当作 permit？

**面试者：** 不能。现在明确进入扩展：代币必须确实实现所选 EIP-2612 接口，permit 有 Token 自己的域和 `owner、spender、value、nonce、deadline`，与 X 的 SwapIntent 是两个不同消息。permit 修改 allowance，不包含兑换路线、输出下限和收款人，因此不能替代意图签名。普通 permit 可以先单独提交给 Token，再调用原 X；若要设计一次调用中的 permit 加兑换，而原 X 没有该入口，就必须另部署扩展执行合约，不能给不可升级的 X 热加功能。这里把新实例记为 X_p：其意图域绑定 X_p，permit 的 spender 也必须是 X_p，扩展示例初始 allowance 为 0，不能挪用基线对 X 的授权。

## 第 4 层：permit 的 deadline 为什么不是授权到期时间

**面试官：** 你把 permit 和兑换拆成两份签名了。那么给它们都设置两分钟 deadline，是不是两分钟之后 allowance 和兑换权限都会一起失效？

**面试者：** 不是。permit 的 deadline 只约束这份 permit 最晚何时被 Token 接受；只要及时提交成功，写入的 allowance 不会因该 deadline 到来自动归零。SwapIntent 的 deadline 则由执行合约在实际兑换时检查，基线是 `block.timestamp<=deadline`，相等仍允许。两者的 nonce 也不同：Token 的 permit nonce 防止重复使用该 Token 授权消息，意图的 42 由执行合约按 owner、epoch 等域隔离消费。要撤销扣款能力，A 应修改对应 allowance；要废止意图，应取消 nonce 或提高 epoch。仅把 allowance 降为 0 也不等于永久取消意图，未来重新授权后，未取消且未过期的意图仍可能执行。

## 第 5 层：别人抢先提交 permit 会发生什么

**面试官：** 既然 permit 只是写入 allowance，任何人拿到签名都能提交。如果别人抢先把它上链，随后我们的 permit 加兑换调用会怎样？

**面试者：** EIP-2612 允许任何提交者转交有效 permit。别人先提交相同 permit 后，Token 的授权 nonce 已递增，allowance 已按签名写给指定 spender；后来再提交原 permit 通常会因 nonce 不匹配失败。若组合入口强制 permit 成功，攻击者就可能让本来有足够 allowance 的兑换被拒绝，这是可用性问题，不能描述成 permit 被抢走后资产必然被盗。签名中的 spender 不能被改成攻击者，兑换的 recipient 和路线也不能被改写。不过基线没有 executor 字段，别人持有完整有效兑换意图时也可以抢先转发，改变执行时机；若要限制提交者，必须另改签名 schema，不能把这种限制说成现有能力。

## 第 6 层：为什么不能简单 catch 后继续

**面试官：** 抢先提交只会让重复 permit 失败，那扩展入口写一个 try/catch，把 permit 的错误吞掉后继续兑换，不就解决了吗？

**面试者：** 只有建立完整后置条件才可以容忍 permit 失败，不能无条件继续。以 X_p 为例，入口先校验代币能力和参数，要求 permit 的 owner 对应意图 owner、spender 是 X_p，扩展方案的 value 为本次 1000 USDC，不能接受攻击者指定另一个授权目标。尝试 permit 后，无论成功还是捕获失败，都重新以 Token 的权威状态检查 `allowance[owner][X_p]>=amountIn`，再走完整的意图验签、期限、epoch、nonce、路线和余额执行约束；不足就回滚。足够 allowance 不证明“肯定是同一 permit 被抢先消费”，它只证明当前具备扣款前提。兑换合法性仍来自有效意图，绝不能用 permit 成功或当前 allowance 足够替代兑换授权。

## 第 7 层：组合调用的原子性覆盖不了哪些状态

**面试官：** 你说重新检查 allowance 后继续完整执行。假设 permit 成功了，但兑换只能拿到 0.48 WETH，失败以后 permit nonce 和 allowance 一定会恢复成 0 吗？

**面试者：** 需要区分状态来自哪笔事务。如果 permit 首次成功就在 X_p 的这笔组合事务里，后来因低于 0.49 WETH 而整体 revert，这笔事务产生的 Token 授权、permit nonce 增量、资金变化和意图 used 都回滚到事务前，不是无条件回到某个固定数值。如果 permit 已被别人提前独立提交，组合事务中的重复 permit 被捕获，那么它随后回滚也撤销不了前一笔已经确认的授权。回到普通 EOA 基线，失败后 A 仍有 1500 USDC、0 WETH，先前对 X 的 1000 USDC 授权仍在；成功时 A 为 500 USDC、0.50 WETH，按基线普通消耗模型 allowance 为 0。不能把这个减法推广成所有 Token 的通则。

## 第 8 层：Go 预检怎样表达这些独立状态

**面试官：** 前一答说明状态可能来自不同事务。Go 服务如果读到余额和 allowance 都足够，就向用户显示“这单保证成功”，还缺了哪一层判断？

**面试者：** 缺了“读取时成立”和“实际执行时成立”的区别。Go 可以按指定区块记录余额、allowance、permit nonce、意图 used、epoch 和模拟结果，但这些只是带区块引用的快照，不是资金预留。A 后续转走资产、修改授权，或其他意图先消费 allowance，都能让执行失败。金额应使用有 uint256 范围检查的 `big.Int`，不能经 float64，也不能共享可变指针误改签名数值。任务记录应分别保存 Token 授权消息身份和执行域内的意图身份，不能用 permit nonce 代替意图 42。对“permit 已被抢先提交但 allowance 足够”和“deadline 已过但 allowance 仍在”进行手工推演，才能说明容错边界；这里没有把推演冒称为已运行测试。

## 本题收束

- **讲透的机制：** Token 的余额与 allowance、Token 的 permit nonce、X 的意图 nonce 与 epoch 属于不同权威状态；permit 解决资产授权传递，不解决兑换授权。
- **最易答错的边界：** permit 抢先提交会消费授权 nonce，但不改变签名指定的 spender；permit deadline 不会撤销已经建立的 allowance；catch 后必须检查当前扣款前提并执行全部意图约束。
- **检验反例：** 别人先独立提交有效 permit，组合交易后来因输出只有 0.48 WETH 而失败。组合事务的意图 used 和资金变化回滚，但先前 allowance 与 permit nonce 不会倒退。若答案声称“两分钟后自动归零”或“失败后所有历史授权都回滚”，就混淆了期限与事务边界。

## 规范参考

- [EIP-2612：permit、授权 nonce 与 deadline 语义](https://eips.ethereum.org/EIPS/eip-2612)
- [EIP-712：结构化数据签名与域分离](https://eips.ethereum.org/EIPS/eip-712)

以上用于核对协议语义，不表示本文的教学合约、Token 能力或组合入口已经部署、审计或实测。
