"""本地教学示例；这些内容不代表 AI 回复或掌握情况评估。"""
LESSONS = [
    dict(name="初识 print", title="让 Python 说第一句话", goal="用 print 显示文字，并修改输出内容。", explanation="print() 会把括号里的内容显示出来。引号表示这里是一段文字。括号和引号要使用英文符号。", code='print("你好，世界")', task="让程序分两行显示你的名字和“我开始学 Python 了”。", hint="可以写两条 print 语句，每条语句输出一行文字。"),
    dict(name="变量", title="用变量保存信息", goal="创建变量、修改它的值，并区分变量与文字。", explanation="变量可以帮我们给一个值起名字。name 是变量名，等号右边的“小林”是保存的文字。print(name) 会读取它当前的值；如果再写 name = \"小雨\"，以后读取 name 就会得到“小雨”。注意，print(\"name\") 显示的是固定文字 name。", code='name = "小林"\nprint(name)', task="创建变量 language 保存“Python”并输出；再改成“我正在学 Python”，再次输出。", hint="先赋值，再用 print 输出变量；修改值时继续使用同一个变量名。"),
    dict(name="数据类型", title="认识文字和数字", goal="区分整数加法与字符串拼接。", explanation='不带引号的 `18` 是整数，带引号的 `"18"` 是字符串。两个整数用加号相加，两个字符串用加号拼接：`18 + 1` 是 19，`"18" + "1"` 是文字 181。\n\n整数与字符串不能直接相加。先看类型，再决定怎样处理。', code='age = 18\nprint(age + 1)\nprint("18" + "1")', task='用四条语句完成：age 保存整数 16，输出 age + 1；text 保存文字“16”，输出 text + "1"。', hint="数字不带引号，文字带引号；加号两边要用同一种类型。"),
    dict(name="条件判断", title="让程序做一个选择", goal="理解条件、分支与 >= 的边界。", explanation='`if` 后面的条件成立时，执行下方缩进的代码；否则执行 `else` 下方的代码。`>=` 表示大于或等于。\n\n`if` 和 `else` 行末要有冒号，两个分支中的语句各缩进四个空格。下面的程序只会选择一个分支。', code='age = 18\nif age >= 18:\n    print("已成年")\nelse:\n    print("未成年")', task="把 age 改为整数 16，保留 age >= 18 的判断和两个分支。成立显示“已成年”，否则显示“未成年”。", hint="16 >= 18 不成立，所以执行 else 下方的语句。注意保留缩进。"),
    dict(name="循环", title="让程序重复做一件事", goal="理解循环次数、循环变量和缩进。", explanation='`for` 会重复执行下方缩进的代码。`range(3)` 依次给出 0、1、2，变量 `i` 依次保存这些值，因此循环执行三次。\n\n缩进内的语句会重复，循环后没有缩进的语句只执行一次。下面先重复显示同一句话。', code='for i in range(3):\n    print("继续加油")', task="用 for i in range(5) 让“继续加油”显示五次。循环里只放一条缩进的 print。", hint="修改 range 括号里的次数，保留下一行开头的四个空格。"),
    dict(
        name="列表", title="整理今天的任务清单", goal="创建列表，用索引取出一项，再把新任务加到末尾。",
        explanation='用方括号把几项内容放在一起，就得到了一个列表。索引从 0 开始：第一项用 [0]，第二项用 [1]。\n\n示例先显示“散步”，再用 append 把“看书”放到清单末尾。原来的两项位置不变，新的一项可以用 [2] 读出来。',
        code='plans = ["画画", "散步"]\nprint(plans[1])\nplans.append("看书")\nprint(plans[2])',
        task='让 tasks 保存列表 ["阅读", "练习"]，用 append 加入“复习”，再用两条 print 按索引依次显示第二项和第三项。',
        hint="把第一项、第二项、第三项的索引写在纸上。加到末尾的新任务排第几？",
    ),
    dict(
        name="字典", title="给每位同学记积分", goal="按名字读取积分，更新已有记录，添加一条新记录。",
        explanation='字典把键和值配成对。示例里的“蓝队”是键，2 是对应的积分。方括号里写队名就能取到它的分数。\n\n给 team["蓝队"] 重新赋值，会更新已有的积分。给一个新的键“红队”赋值，则会多出一条记录。',
        code='team = {"蓝队": 2}\nteam["蓝队"] = 4\nteam["红队"] = 1\nprint(team["蓝队"])\nprint(team["红队"])',
        task='创建 scores = {"小林": 3}。用方括号把小林的积分改为 5，再添加小雨的积分 2。最后按名字分别输出小林和小雨的积分。',
        hint='读取积分时，在 scores 的方括号里放同学的名字。更新时在同样的写法后面加上等号和新分数。',
    ),
    dict(
        name="函数", title="把加分规则写成函数", goal="定义带一个参数的函数，用 return 返回结果，再用不同的分数调用它。",
        explanation='def double(number): 定义了一个函数。调用 double(3) 时，参数 number 这一次的值是 3。缩进里的 return 把计算出的 6 交回调用处，所以外面的 print 能显示 6。\n\n下一次调用 double(5) 时，number 的值会变为 5。同一段计算可以反复使用。',
        code='def double(number):\n    return number * 2\n\nprint(double(3))\nprint(double(5))',
        task='定义 add_point(score)，在函数里用 return 返回 score + 1。在函数外分别用 print 显示 add_point(4) 和 add_point(9) 的结果。',
        hint="函数体里的 return 要缩进。调用时把已有分数放进括号，把整次调用放到 print 里。",
    ),
]

# 持久化使用稳定的标识，不依赖界面上的中文标题。
for lesson, lesson_id in zip(LESSONS, ("print", "variables", "types", "conditions", "loops", "lists",
                                       "dictionaries", "functions"), strict=True):
    lesson["id"] = lesson_id
