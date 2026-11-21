"""根据明确的学习记录安排下一步；复习不替代原有课程成绩。"""

REVIEW_QUESTIONS = {
    'print': ('print("今天")\nprint("继续练习")', '今天\n继续练习',
              '两条 print 会怎样输出？', ('分别输出两行文字', '把文字拼成一行', '把引号一起输出'),
              '分别输出两行文字', '每条 print 默认输出一行，字符串两边的引号不会显示。'),
    'variables': ('word = "开始"\nword = "继续"\nprint(word)\nprint("word")', '继续\nword',
                  '变量重新赋值后，print(word) 读取什么？', ('第一次保存的内容', '最近一次保存的内容', '固定文字 word'),
                  '最近一次保存的内容', '赋值会更新变量保存的值；带引号的 "word" 只是文字。'),
    'types': ('print(3 + 5)\nprint("3" + "5")', '8\n35',
              '这里的两个加号有什么不同？', ('都做加法', '都拼接文字', '整数相加，字符串拼接'),
              '整数相加，字符串拼接', '先看引号：3 和 5 是整数，"3" 和 "5" 是字符串。'),
    'conditions': ('score = 60\nif score >= 60:\n    print("通过")\nelse:\n    print("再练练")', '通过',
                   '分数正好为 60 时，为什么执行这个分支？', ('>= 包含等于', '条件只比较大于', '两个分支都会执行'),
                   '>= 包含等于', '>= 同时包含大于和等于，条件成立只执行 if 分支。'),
    'loops': ('for step in range(2):\n    print(step)\nprint("完成")', '0\n1\n完成',
              '循环与循环后的语句各执行几次？', ('循环两次，最后一句一次', '所有语句都执行两次', '循环从 1 开始'),
              '循环两次，最后一句一次', 'range(2) 产生 0、1；最后一条 print 没有缩进，在循环结束后执行一次。'),
    'lists': ('stops = ["书店", "公园", "车站"]\nprint(stops[2])\nprint(stops[0])', '车站\n书店',
              '为什么第一行会显示第三站？', ('列表总会先读最后一项', '索引从 0 开始，第三项的索引是 2', '索引 2 表示读两项'),
              '索引从 0 开始，第三项的索引是 2', '给三个站点依次标上 0、1、2，再按两条 print 的顺序找出对应的站点。'),
    'dictionaries': ('stock = {"苹果": 4, "梨": 2}\nstock["梨"] = 5\nprint(stock["梨"])\nprint(stock["苹果"])', '5\n4',
                     '给“梨”重新赋值后，库存怎样变化？', ('两个键的值都变成 5', '字典会多出一个同名的键', '只有“梨”对应的值被更新'),
                     '只有“梨”对应的值被更新', '方括号里的文字是键。先找到赋值用的键，再看两次 print 各读取哪个键。'),
    'functions': ('def use_ticket(tickets):\n    return tickets - 1\n\nleft = use_ticket(8)\nprint(left)\nprint(use_ticket(left))', '7\n6',
                  '第二次调用时，参数 tickets 收到哪个值？', ('第一次调用时传入的 8', '第一次调用返回并保存在 left 里的 7', '第二次调用算出的 6'),
                  '第一次调用返回并保存在 left 里的 7', '先算出用掉一张票后 left 保存的数量。第二次调用用 left 作为参数，又用掉一张票。'),
}


def recommend(progress):
    """返回课程索引、行动与理由；不根据打开次数猜测掌握情况。"""
    for index, record in sorted(progress.items()):
        latest = record.get('review', {}).get('result')
        if (record['status'] == '需要复习' and latest != '独立答对') or latest == '需要再练':
            return index, 'review', '这节课标记为需要复习，先用一道新题回顾一下。'
    for index, record in sorted(progress.items()):
        if record['status'] == '练习通过，待确认理解':
            return index, 'study', '练习已检查通过，接着完成理解小测。'
    for index, record in sorted(progress.items()):
        if record['status'] not in ('独立完成', '提示下完成'):
            return index, 'study', '继续这节基础课，完成练习和理解小测。'
    for index, record in sorted(progress.items()):
        if record.get('review', {}).get('result') != '独立答对':
            return index, 'review', '基础课已完成，用不同的例子检查自己是否还能独立读懂。'
    index = min(progress, key=lambda i: (progress[i].get('review', {}).get('updated', ''), i))
    return index, 'review', '各课都有独立答对的复习记录，可以从最早复习的一课再练一次。'
