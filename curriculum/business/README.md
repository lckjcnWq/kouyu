# 商务场景库

这是 Kouyu 的原创模拟商务口语材料，不是固定对话稿，也不是专业法律、财税、医疗或合规意见。当前定义覆盖 **28 类、168 个基础场景、12 个行业包**，每个场景均可选择双方角色并按英语水平调整。

## 按需读取

从安装目录运行，或把脚本替换为绝对路径：

```bash
python scripts/business.py categories
python scripts/business.py list --search 报价 --limit 6
python scripts/business.py list --category procurement
python scripts/business.py industries
python scripts/business.py show biz-negotiation-01 --role b --industry software --level intermediate --duration 20
python scripts/business.py validate
```

- `catalog.md`：供人浏览的全部目录，不含对手私有事实。
- `index.json`：轻量机器目录，含 ID、名称、角色和标签；练习时先查目录，不读取全库。
- `scenarios/<category>.json`：一个业务大类的六个完整场景；`show` 只输出选中的一个。
- `industries.json`：十二个行业的术语、常见约束、指标和问题；`show --industry` 只输出选中行业。
- `../../references/business-english.md`：角色切换、分级、预习、对练、报告及隐私边界。

检索是本地字面匹配，不调用模型或向量数据库；没有匹配时缩短关键词、换同义词或查类别，不要以为业务需求不受支持。特殊任务可以按同一结构生成自定义场景，不把它冒充为已有目录条目。

## 场景定义标准

每个场景必须有：

1. 稳定 ID 和明确的沟通任务名称；
2. 含具体条件的公开模拟背景；
3. A / B 双方各自的目标、私有信息与权限约束；
4. 至少三个推进阶段；
5. 至少两个可选且合理的变化；
6. 至少三个自然英语目标表达建议及沟通用途；
7. 双方各至少两个可观察的成功标准；
8. 用于检索的相关标签。

`a` / `b` 是目录中的角色位置，不等于学习者必须始终是销售或负责人。选择 `--role b` 时，B 的目标、边界和成功标准进入学习者简报，A 成为对手。目标表达仍需根据所选角色调整，三个种子表达不替代完整预习卡。

行业包不是复制 168 套场景。它补充术语和业务约束；与原情境冲突时，在开场前一致地改写模拟背景。不得在谈判中突然修改既定条件。

## 作者维护

修改或新增定义后执行：

```bash
python scripts/business.py build-index
python scripts/business.py validate
python -m unittest discover -s tests -v
```

`build-index` 在全库结构检查通过后，同时重建 `index.json` 和 `catalog.md`；`validate` 检查两者是否与源定义一致。当前计数约束为每类六个场景；扩展到更多场景时需同步更新校验、目录和测试，不能只加名称。`catalog.md` 内的场景 ID 必须与索引完全一致。

## 覆盖成熟度

- **已定义**：具备上述完整字段，不是标题占位。
- **结构校验**：通过全库格式、数量、身份与角色加载测试。
- **程序验收**：通过归档、混合旧记录、HTTP 与网页行为测试。
- **真实学习者验证**：需要独立的实际练习观察；自动测试不能替代。

索引中的 `content_status: defined` 与 `learner_validated: false` 如实反映内容边界。不得据此宣称全部场景已产生教学效果或获得行业认可。所有涉及组织、人名、金额、指标的材料都视为虚构练习条件。测试夹具不属于真实学习记录。
