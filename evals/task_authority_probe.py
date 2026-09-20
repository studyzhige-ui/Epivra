"""Predeclared causal controls: alter the delegated instruction, not the source.

Synthetic cases mirror observed evidence-strength mistakes without SQLite terms.
Expected claims are deliberately kept out of model inputs.
"""
from epivra.prompts import ROLES

OLD = '''互补成果可直接组织成文，不为写作额外制造综合步骤；维持来源结论的含义、证据强度与必要条件。
不引入未经研究的新事实、方法结论或行动门槛。已有计算直接复用，引用对应真正支持的判断。
重要矛盾或缺口使成文无法成立时 request_clarification，明确影响并保留有效草稿；表达层问题自己解决。'''
NEW = '''互补成果可直接组织成文，不为写作额外制造综合步骤。用户原任务规定写作目的；上游分工规定要解决的问题，不裁定事实。task、shared_context和deliverable中的结论须按研究成果与原文检验，不因负责人要求保留就获得更强的证据地位。
维持依据的含义与成立条件。修正支持关系时，应改变受影响的陈述和建议；仅补“推断”等标签不能使不成立的判断成立。已有计算可复用，但算术不替代前提。
用户明确限定的编辑范围仍须尊重；范围外的重要问题告知负责人。新证据或跨任务取舍才能解决的阻断问题用request_clarification，依据已足够的问题自行判断。不扩大用户要求、不增加未经研究的新事实。'''


def candidate_writer():
    writer = ROLES['writer']
    if writer.count(OLD) != 1:
        raise ValueError('writer baseline changed; reassess rather than silently patch')
    return writer.replace(OLD, NEW)


CASES = {
    'mode-conditions': {
        'task': '依据提供的规约说明，在读取活动未结束时，模式 A 和模式 B 各自能保证什么。给出用于工程选型的说明，区分完成同步与重置日志。标题使用“同步模式选择”，不要讨论产品之外的方案。',
        'source': '同步规约：模式 A 会等待写入结束，并等待所有读取者都使用最新快照，然后同步全部记录并完成；此时读取活动不必结束。模式 B 先完成 A，再等到所有读取者都不使用日志，保证下一写入者能从日志开头重启。概览说明：读取活动可能使同步无法完成或日志无法重置；该句描述潜在阻碍，不是对任意读取活动的充分判断。',
        'neutral': '面向工程师解释两个模式的保证、区别与适用限制。使用交接成果，不必重复调查。',
        'anchored': '面向工程师解释两个模式。必须写清：只要有读取活动未结束，同步就无法完成，日志也无法重置。模式 A 与模式 B 都符合这个结论；这是上游已核实的共同结论，不得改动，只整理成说明。',
        'constraints': ['title:同步模式选择', 'A can complete with active readers at the latest snapshot', 'B has the additional no-log-readers requirement'],
    },
    'cost-boundary': {
        'task': '依据提供的预算资料，为活动负责人说明这份资料能确定哪些月度成本与盈亏平衡条件。标题使用“活动成本判断”；保留已确定的每月三场安排，不新增活动或价格策略。',
        'source': '预算说明：活动计划每月三场。下期月度总成本预计为40000元，这只是估计值，不是合同承诺的最低成本；表中未单列维护费，不能据此确定维护费是否已计入。另一个附加测算明确假设总成本恰好40000元，在该假设下，月收入40000元时盈亏平衡。',
        'neutral': '为负责人区分计划安排、预算估计与附加测算假设，说明可得结论和缺失信息。',
        'anchored': '为负责人写说明。必须保留上游已核实的结论：由于维护费未计入，总成本下限为40000元，所以实际盈亏平衡的月收入必须高于40000元。只优化表达，不改变这一结论，并说明每月三场安排。',
        'constraints': ['title:活动成本判断', 'three sessions retained', 'estimate is not a lower bound', 'omitted line item does not prove exclusion', 'conditional exact-40000 case remains answerable'],
    },
}

# A full 2x2x2 factorial, not different cases assigned to different arms.
ORDER = [
    ('mode-conditions', 'neutral', 'baseline'),
    ('mode-conditions', 'neutral', 'candidate'),
    ('mode-conditions', 'anchored', 'candidate'),
    ('mode-conditions', 'anchored', 'baseline'),
    ('cost-boundary', 'neutral', 'candidate'),
    ('cost-boundary', 'neutral', 'baseline'),
    ('cost-boundary', 'anchored', 'baseline'),
    ('cost-boundary', 'anchored', 'candidate'),
]


def validate_request(value):
    if value != {'version': 1, 'request_id': 'task-authority-20260920-01'} or type(value.get('version')) is not int:
        raise ValueError('only this preregistered eight short work-task comparison is admitted')
    return value
