#!/usr/bin/env python3
"""
Generate mock police test data: interviews, mediation reports, financial
transaction records, and call detail records -- 100 files each.

All files are plain .txt and ready for the ingest pipeline.
"""
import os
import random
from datetime import datetime, timedelta

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_data")

# ── Random pools ──────────────────────────────────────────────

SURNAMES = [
    "张", "李", "王", "刘", "陈", "杨", "赵", "黄", "周", "吴",
    "徐", "孙", "马", "朱", "胡", "郭", "林", "何", "高", "梁",
    "郑", "罗", "宋", "谢", "唐", "韩", "曹", "许", "邓", "冯",
    "肖", "程", "蔡", "潘", "袁", "于", "董", "余", "苏", "叶",
    "吕", "魏", "蒋", "田", "杜", "丁", "沈", "姜", "范", "江",
]
GIVEN_NAMES_MALE = [
    "伟", "强", "磊", "洋", "勇", "军", "杰", "涛", "明", "超",
    "华", "建国", "志强", "文博", "宇轩", "浩然", "天宇", "睿", "皓", "鹏",
]
GIVEN_NAMES_FEMALE = [
    "芳", "敏", "静", "丽", "婷", "雪", "琳", "玲", "云", "娜",
    "欣怡", "梓涵", "雨桐", "一诺", "诗涵", "思雨", "梦洁", "紫萱", "语嫣", "晓婷",
]
DISTRICTS = ["城东区", "城西区", "城南区", "城北区", "开发区", "高新区", "滨江区", "龙湖区"]
STREETS = [
    "中山路", "人民路", "建设路", "解放路", "和平街", "新华街",
    "朝阳路", "文化路", "工业大道", "滨河路", "学府路", "光明路",
    "长安街", "学院路", "花园路", "五一路", "青年路",
]
COMMUNITIES = [
    "阳光小区", "翠苑新村", "金域华府", "碧水湾", "锦绣花园",
    "紫荆花园", "世纪新城", "恒大名都", "万科城", "翡翠湾",
    "星河湾", "龙湖天街", "凤凰城", "东方明珠", "绿地新都", "保利花园",
]
CASE_TYPES = [
    "盗窃", "诈骗", "抢劫", "故意伤害", "寻衅滋事", "赌博", "吸毒",
    "网络诈骗", "电信诈骗", "入室盗窃", "扒窃", "抢夺", "聚众斗殴",
    "故意毁坏财物", "敲诈勒索", "侵犯公民个人信息",
    "帮助信息网络犯罪", "掩饰隐瞒犯罪所得", "伪造证件",
]
EVIDENCE_TYPES = [
    "监控视频", "现场照片", "指纹", "DNA样本", "证人证言",
    "转账记录", "聊天记录", "通话记录", "银行流水",
]
GOODS = [
    "电动车", "手机", "笔记本电脑", "现金", "金银首饰",
    "名贵烟酒", "电缆线", "高档手表", "品牌包包", "数码相机",
    "平板电脑", "茅台酒", "钻戒", "金项链",
]
LAW_ARTICLES = [
    "（《中华人民共和国治安管理处罚法》第四十九条）盗窃、诈骗、哄抢、抢夺、敲诈勒索或者故意损毁公私财物的",
    "（《中华人民共和国治安管理处罚法》第四十三条）殴打他人的，或者故意伤害他人身体的",
    "（《中华人民共和国治安管理处罚法》第七十条）赌博",
    "（《中华人民共和国刑法》第二百六十四条）盗窃罪",
    "（《中华人民共和国刑法》第二百六十六条）诈骗罪",
    "（《中华人民共和国刑法》第二百三十四条）故意伤害罪",
    "（《中华人民共和国刑法》第二百六十三条）抢劫罪",
    "（《中华人民共和国刑法》第二百八十七条之二）帮助信息网络犯罪活动罪",
    "（《中华人民共和国刑法》第三百一十二条）掩饰隐瞒犯罪所得罪",
]

FREQUENT_SUSPECTS = [
    {"name": "张建国", "tags": ["盗窃前科", "吸毒人员"]},
    {"name": "李强", "tags": ["诈骗前科"]},
    {"name": "王伟", "tags": ["抢劫前科", "涉黑"]},
    {"name": "刘芳", "tags": ["电信诈骗", "网络赌博"]},
    {"name": "陈磊", "tags": ["盗窃", "吸毒"]},
    {"name": "杨勇", "tags": ["故意伤害前科"]},
    {"name": "赵敏", "tags": ["诈骗", "伪造证件"]},
    {"name": "黄超", "tags": ["盗窃", "销赃"]},
    {"name": "周军", "tags": ["寻衅滋事", "聚众斗殴"]},
    {"name": "吴斌", "tags": ["盗窃", "抢夺"]},
    {"name": "孙静", "tags": ["组织卖淫"]},
    {"name": "马杰", "tags": ["网络诈骗"]},
    {"name": "朱涛", "tags": ["故意伤害", "涉黑"]},
    {"name": "胡琳", "tags": ["吸毒"]},
    {"name": "林飞", "tags": ["盗窃", "入室盗窃"]},
]
FREQUENT_LOCATIONS = [
    {"name": "阳光小区", "address": "城东区中山路168号"},
    {"name": "翠苑新村", "address": "城东区建设路56号"},
    {"name": "金域华府", "address": "城南区人民路288号"},
    {"name": "碧水湾", "address": "城西区滨河路99号"},
    {"name": "大柳树村", "address": "城北区工业大道北段"},
    {"name": "锦绣花园", "address": "高新区学府路128号"},
    {"name": "世纪新城", "address": "开发区长安街66号"},
    {"name": "火车站广场", "address": "城东区站前路1号"},
    {"name": "万达广场", "address": "城南区朝阳路200号"},
    {"name": "恒大名都", "address": "高新区花园路88号"},
    {"name": "紫荆花园", "address": "城西区五一路33号"},
    {"name": "小河村", "address": "城北区北环路外"},
]


def random_name():
    return random.choice(SURNAMES) + random.choice(GIVEN_NAMES_MALE + GIVEN_NAMES_FEMALE)


def random_date(start_year=2024, end_year=2026):
    start = datetime(start_year, 1, 1)
    end = min(datetime(end_year, 4, 28), datetime.now())
    delta = end - start
    return start + timedelta(days=random.randint(0, max(0, delta.days)))


def random_phone():
    prefixes = ["138", "139", "150", "151", "158", "159", "186", "187", "188", "177", "136", "155", "185"]
    return random.choice(prefixes) + "".join([str(random.randint(0, 9)) for _ in range(8)])


def random_id_card():
    area = random.choice(["320102", "320103", "320104", "320105", "320106", "320111", "320201"])
    birth = random_date(1970, 2004).strftime("%Y%m%d")
    return area + birth + "".join([str(random.randint(0, 9)) for _ in range(4)])


def random_suspect():
    return random.choice(FREQUENT_SUSPECTS)


def random_location():
    return random.choice(FREQUENT_LOCATIONS)


def random_police_station():
    return f"{random.choice(DISTRICTS)}{random.choice(STREETS)}派出所"


# ═══════════════════════════════════════════════════════════════
# 1. 笔录 (Interviews)
# ═══════════════════════════════════════════════════════════════

def gen_interview(idx):
    case_type = random.choice(CASE_TYPES)
    suspect = random_suspect()
    location = random_location()
    station = random_police_station()
    date = random_date()
    ds = date.strftime("%Y年%m月%d日")
    ts = date.strftime("%Y年%m月%d日%H时%M分")

    interviewee = random_name()
    officer1 = random_name()
    officer2 = random_name()
    addr = f"{location['address']}{random.randint(1, 30)}栋{random.randint(101, 2502)}室"

    if case_type in ["盗窃", "入室盗窃", "扒窃", "抢夺"]:
        description = (
            f"{ds}下午，我在{location['name']}附近发现自己的物品被盗。"
            f"被偷走了一部手机和钱包，钱包里还有身份证和银行卡。"
            f"当时周围人很多，没注意到是谁干的。"
        )
        loss = f"手机一部（价值约{random.choice([2000, 3000, 5000, 8000])}元），现金{random.choice([500, 1000, 2000, 3000])}元"
    elif case_type in ["诈骗", "网络诈骗", "电信诈骗"]:
        description = (
            f"{ds}我接到一个陌生电话，对方自称是公检法工作人员，"
            f"说我涉嫌洗钱，要求我把资金转到安全账户进行核查。"
            f"我按照对方指示通过手机银行转了账。"
        )
        loss = f"共计被骗人民币{random.choice([10000, 30000, 50000, 80000, 150000])}元"
    elif case_type in ["故意伤害", "寻衅滋事", "聚众斗殴"]:
        description = (
            f"{ds}晚上，我在{location['name']}附近吃饭时，"
            f"和邻桌的几个人发生口角，对方先动手打了我。"
            f"我的头部和手臂都受伤了。"
        )
        loss = f"头部受伤、手臂挫伤，医药费约{random.choice([1000, 3000, 5000, 8000])}元"
    elif case_type in ["吸毒", "赌博"]:
        description = (
            f"{ds}接到群众举报，{location['name']}有人{case_type}。"
            f"我们到达现场后发现{random.randint(3, 8)}名可疑人员。"
            f"经初步盘查，现场发现有相关工具和证据。"
        )
        loss = "暂无财产损失"
    elif case_type in ["敲诈勒索"]:
        description = (
            f"{ds}我收到一条匿名短信，对方称掌握我的个人隐私，"
            f"要求我转账{random.randint(5000, 50000)}元到指定账户，否则就把照片发到网上。"
        )
        loss = f"被勒索人民币{random.choice([5000, 10000, 20000, 30000])}元"
    elif case_type in ["侵犯公民个人信息"]:
        description = (
            f"{ds}我发现自己的个人信息被泄露，"
            f"经常收到骚扰电话和诈骗短信，怀疑是某中介公司泄露的。"
        )
        loss = "暂无直接经济损失，但个人信息安全受到严重侵害"
    elif case_type in ["帮助信息网络犯罪"]:
        description = (
            f"{ds}在{location['name']}抓获一可疑人员，"
            f"其名下多张银行卡交易频繁且金额巨大，与多起电信诈骗案件有关联。"
        )
        loss = "涉案银行卡流水共计约" + f"{random.choice([50, 100, 200, 500])}万元"
    else:
        description = (
            f"{ds}在{location['name']}发生一起{case_type}案件，"
            f"当事人已到{station}报案，具体情况正在调查中。"
        )
        loss = "损失情况正在进一步核实中"

    content = f"""询问笔录——{case_type}案——{interviewee}

询问时间：{ts}
询问地点：{station}
询问人：{officer1}、{officer2}
记录人：{officer1}
被询问人：{interviewee}
身份证号：{random_id_card()}
联系电话：{random_phone()}
住址：{addr}

问：我们是{station}的民警（出示证件），现依法对你进行询问，请你如实回答。你听清楚了吗？
答：听清楚了。

问：请你把事发经过详细讲一下。
答：{description}

问：你有什么损失？
答：{loss}

问：你认识嫌疑人吗？
答：{random.choice(['不认识', f'见过{suspect["name"]}几次，但不熟', '认识，是邻居'])}。

问：还有什么需要补充的吗？
答：{random.choice(['希望警方尽快破案', '暂时没有了', '想起什么再联系你们'])}

以上笔录我看过，与我所说相符。

被询问人签名：{interviewee}
询问人签名：{officer1}、{officer2}
{ts}
"""
    return content


# ═══════════════════════════════════════════════════════════════
# 2. 调解报告 (Mediation Reports)
# ═══════════════════════════════════════════════════════════════

MEDIATION_TYPES = [
    "邻里纠纷", "家庭矛盾", "消费纠纷", "劳资纠纷",
    "物业纠纷", "交通事故赔偿", "婚恋纠纷", "治安调解",
]

MEDIATION_REASONS = [
    ("漏水纠纷", [
        "楼上水管破裂导致楼下天花板和墙面受损，双方因赔偿金额分歧较大",
        "楼上租户用水不当导致楼下住户家中积水，家具受损",
        "空调排水管安装不当，长期滴水影响楼下正常生活",
    ]),
    ("噪音纠纷", [
        "楼上租户经常深夜聚会、打牌，噪音影响楼下休息，多次沟通无效",
        "隔壁住户家的小孩每天练琴到很晚，影响邻居正常作息",
        "楼下商铺夜间营业噪音过大，住户多次投诉未果",
    ]),
    ("停车纠纷", [
        "因小区停车位紧张，双方因争抢车位发生口角并产生肢体冲突",
        "业主车辆被邻居车辆堵住无法出行，沟通时发生激烈争吵",
        "外来车辆占用固定车位引发业主不满，双方发生争执",
    ]),
    ("家庭矛盾", [
        "夫妻因经济问题和子女教育方式产生分歧，发生剧烈争吵",
        "父子因工作选择问题产生矛盾，关系紧张",
        "婆媳因家务分配和孩子抚养问题长期不和，发生争执",
    ]),
    ("消费纠纷", [
        "消费者购买商品后发现存在质量问题，要求退货退款被拒",
        "服务项目收费不透明，消费者认为存在价格欺诈",
        "网购商品与描述严重不符，买家要求退货赔偿",
    ]),
    ("劳资纠纷", [
        "劳动者被拖欠工资{months}个月，多次讨要未果",
        "企业单方面解除劳动合同且未支付经济补偿金",
        "离职后最后一个月的工资被以各种理由扣罚",
    ]),
    ("物业纠纷", [
        "业主因房屋质量问题长期未解决而拒缴物业费",
        "小区电动车充电桩不足，业主私拉电线存在安全隐患",
        "小区门禁系统损坏长期未维修，业主安全受影响",
    ]),
    ("邻里纠纷", [
        "养宠物影响邻居生活，狗吠声扰民且楼道有异味",
        "楼道堆放杂物占用公共空间，影响通行和消防安全",
        "装修施工时间过长且节假日施工，影响邻居正常休息",
    ]),
]


def gen_mediation(idx):
    med_type = random.choice(MEDIATION_TYPES)
    reason_templates = MEDIATION_REASONS[random.randint(0, len(MEDIATION_REASONS) - 1)]
    reason_type = reason_templates[0]
    reason_detail = random.choice(reason_templates[1])
    months = random.choice(["三", "六", "两"])

    date = random_date()
    ts = date.strftime("%Y年%m月%d日%H时%M分")
    ds = date.strftime("%Y年%m月%d日")
    station = random_police_station()
    location = random_location()

    party_a = random_name()
    party_b = random_name()
    officer = random_name()
    mediator1 = random_name()
    mediator2 = random_name()

    content = f"""治安调解报告——{med_type}——{ds}

调解编号：TJ-{date.strftime('%Y%m%d')}-{idx:04d}
调解时间：{ts}
调解地点：{station}调解室
主持人：{officer}
调解员：{mediator1}、{mediator2}
记录人：{officer}

当事人甲方：{party_a}，男，{random.randint(22, 65)}岁
身份证号：{random_id_card()}
联系电话：{random_phone()}
住址：{location['address']}{random.randint(1, 30)}栋{random.randint(101, 2502)}室

当事人乙方：{party_b}，男，{random.randint(22, 65)}岁
身份证号：{random_id_card()}
联系电话：{random_phone()}
住址：{location['address']}{random.randint(1, 30)}栋{random.randint(101, 2502)}室

纠纷事由：
{ds}，{reason_detail.format(months=months)}。

调解过程：
主持人首先听取了双方当事人的陈述。甲方{party_a}要求对方赔偿损失并赔礼道歉。
乙方{party_b}承认有一定责任，但认为对方要求过高。

调解员依据相关法律法规，对双方进行了耐心细致的调解工作。
{random.choice([
    '经调解员反复沟通，双方态度逐渐缓和，愿意协商解决。',
    '调解员从邻里关系、社会和谐的角度进行劝导，双方同意各让一步。',
    '调解员指出双方均有过错，引导换位思考，最终达成一致意见。',
    '经多次调解和单独沟通，双方最终达成和解协议。',
])}

调解结果：
经调解，双方自愿达成如下协议：
1. {random.choice([
    f'乙方{party_b}向甲方{party_a}赔礼道歉',
    f'甲方{party_a}向乙方{party_b}赔偿人民币{random.choice([500, 1000, 2000, 3000, 5000])}元',
    '双方当面向对方赔礼道歉，握手言和',
    f'乙方{party_b}承诺在{random.choice([3, 7, 15])}天内修复/整改存在的问题',
])}
2. {random.choice([
    '双方不得因此事再次发生纠纷或打击报复',
    '各自承担自己的医疗费用，互不追究',
    '今后互相体谅，和睦相处，共同维护良好的邻里关系',
    '双方自愿和解，不再追究对方的任何法律责任',
    f'支付方式为现金支付/微信转账，当场履行',
])}
3. {random.choice([
    '本调解协议自双方签字之日起生效，具有法律约束力',
    '如一方不履行协议，另一方可依法向人民法院提起诉讼',
])}

甲方签名：{party_a}
乙方签名：{party_b}
调解员签名：{mediator1}、{mediator2}
主持人签名：{officer}
{ts}

备注：{random.choice(['调解全程录音录像', '双方对调解结果表示满意', '已告知双方相关法律权利和义务'])}
"""
    return content


# ═══════════════════════════════════════════════════════════════
# 3. 资金交易记录 (Financial Transaction Records)
# ═══════════════════════════════════════════════════════════════

def gen_transaction(idx):
    suspect = random_suspect()
    date_start = random_date(2024, 2025)
    date_end = date_start + timedelta(days=random.randint(30, 180))
    officer = random_name()
    station = random_police_station()

    count = random.randint(20, 50)
    tx_lines = []
    total_in = 0
    total_out = 0
    counterparties = [random_name() for _ in range(6)]

    for i in range(1, count + 1):
        d = date_start + timedelta(days=random.randint(0, (date_end - date_start).days))
        dt = d.strftime("%Y-%m-%d") + f" {random.randint(8, 22):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}"
        tp = random.choice(["转入", "转出", "转入", "转出", "消费", "取现", "转入"])
        amt = random.choice([500, 1000, 2000, 3000, 5000, 8000, 10000, 20000, 30000, 50000, 80000, 100000, 200000])
        cp = random.choice(counterparties)
        if tp == "转入":
            total_in += amt
        elif tp == "转出":
            total_out += amt
        elif tp in ("取现", "消费"):
            total_out += amt

        summary = random.choice([
            "货款", "借款", "还款", "工资", "劳务费", "投资款",
            "项目款", "工程款", "服务费", "佣金", "返利",
        ]) if tp in ("转入", "转出") else random.choice(["取现", "消费", "购物"])

        tx_lines.append(
            f"{i:3d} | {dt} | {tp:4s} | {amt:>10,} | {cp:6s} | {summary}"
        )

    content = f"""资金交易记录查询——{suspect["name"]}

涉案人员：{suspect["name"]}
身份证号：{random_id_card()}
联系电话：{random_phone()}
主卡号：{random.choice(['6222', '6228', '6217', '6212'])}********{random.randint(1000, 9999)}

查询范围：{date_start.strftime('%Y年%m月%d日')} 至 {date_end.strftime('%Y年%m月%d日')}
查询单位：{station}经侦大队
查询人：{officer}
查询时间：{datetime.now().strftime('%Y年%m月%d日%H时%M分')}

{'='*80}
序号 | 交易时间               | 类型 | 金额(元)      | 对方     | 摘要
{'='*80}
{chr(10).join(tx_lines)}
{'='*80}

统计：
  总笔数：{count} 笔
  收入合计：{total_in:,} 元
  支出合计：{total_out:,} 元
  净额：{total_in - total_out:,} 元

异常交易提示：
{random.choice([
    '存在多笔大额资金快进快出特征，符合洗钱交易模式',
    '交易对手涉及多个已知涉案账户',
    '有{0}笔交易在凌晨时段发生，行为异常',
    '短期内与多个不同对手发生大额交易',
]).format(random.randint(3, 8))}

分析意见：
经初步分析，该账户交易模式异常，涉及多笔可疑交易。
建议进一步调取交易对手信息，核实资金来源和去向，并视情采取冻结措施。

查询人：{officer}
"""
    return content


# ═══════════════════════════════════════════════════════════════
# 4. 话单记录 (Call Detail Records)
# ═══════════════════════════════════════════════════════════════

def gen_cdr(idx):
    suspect = random_suspect()
    date_start = random_date(2024, 2025)
    date_end = date_start + timedelta(days=random.randint(30, 90))
    officer = random_name()
    station = random_police_station() + "刑侦大队"

    count = random.randint(40, 80)
    records = []
    contact_counter = {}
    outer_total_sec = 0
    outer_night = 0

    # generate some frequent contacts
    hot_numbers = [random_phone() for _ in range(8)]

    for i in range(1, count + 1):
        d = date_start + timedelta(days=random.randint(0, (date_end - date_start).days))
        h = random.randint(0, 23)
        m = random.randint(0, 59)
        dt = d.strftime("%Y-%m-%d") + f" {h:02d}:{m:02d}"
        tp = random.choice(["主叫", "被叫", "主叫", "被叫", "主叫"])

        if random.random() < 0.6:
            num = random.choice(hot_numbers)
        else:
            num = random_phone()

        dur = random.choice([5, 10, 20, 30, 45, 60, 120, 180, 240, 300, 600, 900, 1200])
        outer_total_sec += dur
        if 0 <= h <= 5:
            outer_night += 1
            if random.random() < 0.08:
                dur = random.choice([2, 3, 5])  # very short calls at night

        contact_counter[num] = contact_counter.get(num, 0) + 1
        loc = random.choice(DISTRICTS + ["本市"])

        dur_str = f"{dur // 60}:{dur % 60:02d}" if dur >= 60 else f"0:{dur:02d}"
        records.append(
            f"{i:3d} | {dt} | {tp:4s} | {num} | {loc:8s} | {dur_str:>6s}"
        )

    top5 = sorted(contact_counter.items(), key=lambda x: x[1], reverse=True)[:5]
    top5_lines = [f"  {i+1}. {num} —— {cnt}次" for i, (num, cnt) in enumerate(top5)]

    content = f"""话单记录查询——{suspect["name"]}

涉案人员：{suspect["name"]}
手机号码：{random_phone()}
运营商：{random.choice(['中国移动', '中国联通', '中国电信'])}

查询范围：{date_start.strftime('%Y年%m月%d日')} 至 {date_end.strftime('%Y年%m月%d日')}
查询单位：{station}
查询人：{officer}
查询时间：{datetime.now().strftime('%Y年%m月%d日%H时%M分')}

{'='*80}
序号 | 时间                | 类型 | 对方号码       | 归属地   | 时长
{'='*80}
{chr(10).join(records)}
{'='*80}

通话统计：
  总通话次数：{count} 次
  总通话时长：{outer_total_sec // 60} 分钟
  涉及号码数：{len(contact_counter)} 个

频繁联系人 TOP5：
{chr(10).join(top5_lines)}

异常分析：
{random.choice([
    f'凌晨时段（00:00-06:00）通话{outer_night}次，不符合正常作息规律',
    '通话记录显示与多个已知涉案人员存在密切联系',
    f'案发前后与{suspect["name"]}的通话频率明显增加',
    '存在多个短时通话（不足5秒），疑似暗号或通风报信',
])}

分析意见：
建议结合案件进一步研判，制作通信关系图谱。
必要时可调取重点时段的通话内容进行分析。

查询人：{officer}
"""
    return content


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════


def main():
    dirs = {
        "interviews":    (OUTPUT_DIR + "/interviews", 100, gen_interview),
        "mediations":    (OUTPUT_DIR + "/mediations", 100, gen_mediation),
        "transactions":  (OUTPUT_DIR + "/transactions", 100, gen_transaction),
        "call_records":  (OUTPUT_DIR + "/call_records", 100, gen_cdr),
    }

    for key, (path, n, gen) in dirs.items():
        os.makedirs(path, exist_ok=True)
        for i in range(1, n + 1):
            filepath = os.path.join(path, f"{key}_{i:04d}.txt")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(gen(i))
        print(f"[OK] {key}: {n} files -> {path}")

    print(f"\nDone. 400 mock data files saved in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
