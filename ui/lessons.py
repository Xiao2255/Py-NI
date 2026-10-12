"""本地教学示例；这些内容不代表 AI 回复或掌握情况评估。"""
LESSONS = [
    dict(name="初识 print", title="让 Python 说第一句话", goal="用 print 显示文字，并修改输出内容。", explanation="print() 会把括号里的内容显示出来。引号表示这里是一段文字。括号和引号要使用英文符号。", code='print("你好，世界")', task="让程序分两行显示你的名字和“我开始学 Python 了”。", hint="可以写两条 print 语句，每条语句输出一行文字。"),
    dict(name="变量", title="用变量保存信息", goal="创建变量、修改它的值，并区分变量与文字。", explanation="变量可以帮我们给一个值起名字。name 是变量名，等号右边的“小林”是保存的文字。print(name) 会读取它当前的值；如果再写 name = \"小雨\"，以后读取 name 就会得到“小雨”。注意，print(\"name\") 显示的是固定文字 name。", code='name = "小林"\nprint(name)', task="创建变量 language 保存“Python”并输出；再改成“我正在学 Python”，再次输出。", hint="先赋值，再用 print 输出变量；修改值时继续使用同一个变量名。"),
    dict(name="数据类型", title="认识文字和数字", goal="区分整数加法与字符串拼接。", explanation='不带引号的 `18` 是整数，带引号的 `"18"` 是字符串。两个整数用加号相加，两个字符串用加号拼接：`18 + 1` 是 19，`"18" + "1"` 是文字 181。\n\n整数与字符串不能直接相加。先看类型，再决定怎样处理。', code='age = 18\nprint(age + 1)\nprint("18" + "1")', task='用四条语句完成：age 保存整数 16，输出 age + 1；text 保存文字“16”，输出 text + "1"。', hint="数字不带引号，文字带引号；加号两边要用同一种类型。"),
    dict(name="条件判断", title="让程序做一个选择", goal="理解条件、分支与 >= 的边界。", explanation='`if` 后面的条件成立时，执行下方缩进的代码；否则执行 `else` 下方的代码。`>=` 表示大于或等于。\n\n`if` 和 `else` 行末要有冒号，两个分支中的语句各缩进四个空格。下面的程序只会选择一个分支。', code='age = 18\nif age >= 18:\n    print("已成年")\nelse:\n    print("未成年")', task="把 age 改为整数 16，保留 age >= 18 的判断和两个分支。成立显示“已成年”，否则显示“未成年”。", hint="16 >= 18 不成立，所以执行 else 下方的语句。注意保留缩进。"),
    dict(name="循环", title="让程序重复做一件事", goal="理解循环次数、循环变量和缩进。", explanation='`for` 会重复执行下方缩进的代码。`range(3)` 依次给出 0、1、2，变量 `i` 依次保存这些值，因此循环执行三次。\n\n缩进内的语句会重复，循环后没有缩进的语句只执行一次。下面先重复显示同一句话。', code='for i in range(3):\n    print("继续加油")', task="用 for i in range(5) 让“继续加油”显示五次。循环里只放一条缩进的 print。", hint="修改 range 括号里的次数，保留下一行开头的四个空格。"),
]

# 持久化使用稳定的标识，不依赖界面上的中文标题。
for lesson, lesson_id in zip(LESSONS, ("print", "variables", "types", "conditions", "loops")):
    lesson["id"] = lesson_id
