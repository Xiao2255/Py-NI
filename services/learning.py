"""基础课程的本地检查：只分析语法树，不执行用户代码。"""
import ast

STATUSES = ("尚未开始", "看过示例", "正在练习", "练习通过，待确认理解", "提示下完成", "独立完成", "需要复习")
PRINT_HINTS = (
    "想一想：一条 print 会显示一行。如果要显示两行，可以写几条呢？",
    "可以写两条 print。第一条放你的名字，第二条放“我开始学 Python 了”。记得让引号和括号成对出现。",
    '这里有个可参考的写法，把第一行的名字换成你自己的：\n\n```python\nprint("小林")\nprint("我开始学 Python 了")\n```',
)


def new_progress():
    return {"status": "尚未开始", "hints": 0, "assisted": False,
            "checked_code": None, "evidence": "还没有练习记录。", "source": "学习过程", "note": ""}


def check_print_exercise(code):
    if len(code) > 24000:
        return False, "代码有点长，先留下这次练习需要的两条 print 吧。"
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError) as exc:
        line = getattr(exc, "lineno", None)
        location = f"第 {line} 行附近" if line else "代码里"
        return False, f"{location}还有个语法问题。先看看括号、引号有没有配对，行首是否多了空格，再试一次。"
    if len(tree.body) != 2:
        return False, "这次我们练习两条 print：第一条显示名字，第二条显示“我开始学 Python 了”。再对照一下任务吧。"
    texts = []
    for node in tree.body:
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
            return False, "本课的小检查只识别两条 print(文字)。其他写法可以请 Py妮解释，这次先用刚学的写法练习吧。"
        call = node.value
        if not (isinstance(call.func, ast.Name) and call.func.id == "print" and len(call.args) == 1 and not call.keywords
                and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str)):
            return False, "每条 print 里先放一段带引号的文字就好。本课检查不运行代码，也暂不判断其他写法。"
        texts.append(call.args[0].value)
    if not texts[0].strip() or "\n" in texts[0] or "\r" in texts[0]:
        return False, "第一条 print 里写上你的名字或昵称，让它显示在一行里。"
    if "".join(texts[1].split()) != "我开始学Python了" or "\n" in texts[1] or "\r" in texts[1]:
        return False, "第一行有名字啦。再把第二行的文字改成“我开始学 Python 了”。"
    return True, "两条 print 的写法符合这次任务啦。这是代码阅读检查，还没有运行程序。接着做一个小判断，看看你是不是读懂了。"


def check_variables_exercise(code):
    if len(code) > 24000:
        return False, "先留下这次练习需要的四个步骤：赋值、输出、修改值、再次输出。"
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError) as exc:
        line = getattr(exc, "lineno", None)
        location = f"第 {line} 行附近" if line else "代码里"
        return False, f"{location}还有个语法问题。检查一下等号、引号和括号，也留意行首有没有多余空格。"
    if len(tree.body) != 4:
        return False, "这次有四个小步骤：让 language 保存“Python”，输出它；再把它改成“我正在学 Python”，再次输出。试着每个步骤写一行。"
    for offset, expected in ((0, "Python"), (2, "我正在学Python")):
        assignment, output = tree.body[offset:offset + 2]
        if not (isinstance(assignment, ast.Assign) and len(assignment.targets) == 1
                and isinstance(assignment.targets[0], ast.Name) and assignment.targets[0].id == "language"):
            return False, "本课练习用 language 作为变量名。用一个等号把右边的文字赋给它；之后再用同一个变量名修改值。"
        if not (isinstance(assignment.value, ast.Constant) and isinstance(assignment.value.value, str)):
            return False, "等号右边先放带引号的文字。这里检查的是最基础的赋值写法，其他表达式可以通过“代码求助”一起看。"
        value = assignment.value.value
        if (value if offset == 0 else "".join(value.split())) != expected or "\n" in value or "\r" in value:
            return False, "第一次让 language 保存“Python”，第二次改成“我正在学 Python”。注意 Python 的大小写。"
        if not (isinstance(output, ast.Expr) and isinstance(output.value, ast.Call)):
            return False, "每次赋值之后，都用一条 print 显示 language 当前保存的值。"
        call = output.value
        if not (isinstance(call.func, ast.Name) and call.func.id == "print"
                and len(call.args) == 1 and not call.keywords):
            return False, "本课只检查 print(language) 这样的基本输出。先把额外参数留到后面学吧。"
        if isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
            return False, "这里要显示变量里保存的内容，所以 print 括号里放 language，不要给它加引号。加了引号就成了一段固定文字。"
        if not (isinstance(call.args[0], ast.Name) and call.args[0].id == "language"):
            return False, "输出时也要使用 language，和前面赋值时的名字保持一致；Python 会区分大小写。"
    return True, "你已经按顺序创建变量、输出、修改值，再次输出了。这里检查了代码写法，还没有运行程序。接着用一个小判断看看你是否理解了“变量”和“文字”的区别吧。"


def _parse_exercise(code):
    if len(code) > 24000:
        return "代码有点长，先留下这次任务需要的语句吧。"
    try:
        return ast.parse(code)
    except (SyntaxError, ValueError, RecursionError) as exc:
        line = getattr(exc, "lineno", None)
        location = f"第 {line} 行附近" if line else "代码里"
        return f"{location}还有个语法问题。看看引号、括号、冒号和缩进，再改一改。"


def _name(node, name):
    return isinstance(node, ast.Name) and node.id == name


def _literal(node, value):
    return isinstance(node, ast.Constant) and type(node.value) is type(value) and node.value == value


def _assignment(node, name, value):
    return (isinstance(node, ast.Assign) and len(node.targets) == 1
            and _name(node.targets[0], name) and _literal(node.value, value))


def _print_argument(node):
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        call = node.value
        if _name(call.func, "print") and len(call.args) == 1 and not call.keywords:
            return call.args[0]
    return None


def check_types_exercise(code):
    tree = _parse_exercise(code)
    if isinstance(tree, str):
        return False, tree
    if len(tree.body) != 4:
        return False, "这次写四条语句：给 age 赋值、输出 age + 1，再给 text 赋值、输出 text + \"1\"。对比数字相加和文字拼接。"
    if not _assignment(tree.body[0], "age", 16):
        return False, "先让 age 保存整数 16，不要加引号。带引号的“16”是一段文字，不能直接和整数 1 相加。"
    integer_sum = _print_argument(tree.body[1])
    if not (isinstance(integer_sum, ast.BinOp) and isinstance(integer_sum.op, ast.Add)
            and _name(integer_sum.left, "age") and _literal(integer_sum.right, 1)):
        return False, "第二条语句用 print(age + 1)，让两个整数相加。先别直接写结果，我们要练习表达式。"
    if not _assignment(tree.body[2], "text", "16"):
        return False, "接着让 text 保存带引号的“16”。这样它和前面的整数 16 才能形成对比。"
    string_sum = _print_argument(tree.body[3])
    if not (isinstance(string_sum, ast.BinOp) and isinstance(string_sum.op, ast.Add)
            and _name(string_sum.left, "text") and _literal(string_sum.right, "1")):
        return False, "最后用 print(text + \"1\")。这里两边都是文字，加号会把它们接起来；不要把右边写成整数 1。"
    return True, "整数相加和字符串拼接的写法都符合任务啦。这是静态检查，没有运行程序。接着换一组数字，看看你能否预测两种加法的结果。"


def check_conditions_exercise(code):
    tree = _parse_exercise(code)
    if isinstance(tree, str):
        return False, tree
    if len(tree.body) != 2 or not _assignment(tree.body[0], "age", 16):
        return False, "这次先把 age 改成整数 16，再保留一个 if / else 判断。条件判断之外先不添加其他语句。"
    branch = tree.body[1]
    if not isinstance(branch, ast.If):
        return False, "用 if 判断 age 是否达到 18，再用 else 处理没达到的情况。两个分支里的输出要缩进。"
    comparison = branch.test
    if not (isinstance(comparison, ast.Compare) and _name(comparison.left, "age")
            and len(comparison.ops) == 1 and isinstance(comparison.ops[0], ast.GtE)
            and len(comparison.comparators) == 1 and _literal(comparison.comparators[0], 18)):
        return False, "本课练习写 age >= 18，表示大于或等于 18。注意 >= 包含刚好 18 岁，单独的 > 不包含；其他等价写法可在代码求助里讨论。"
    if len(branch.body) != 1 or not _literal(_print_argument(branch.body[0]), "已成年"):
        return False, "条件成立的 if 分支里，缩进写一条 print，显示“已成年”。注意不要把两个分支写反。"
    if len(branch.orelse) != 1 or not _literal(_print_argument(branch.orelse[0]), "未成年"):
        return False, "else 分支里缩进写一条 print，显示“未成年”。每次判断会选择其中一个分支。"
    return True, "条件、两个分支和输出文字都符合任务啦。我们没有运行代码；接下来的小测会看看“刚好达到条件”时该走哪个分支。"


def check_loops_exercise(code):
    tree = _parse_exercise(code)
    if isinstance(tree, str):
        return False, tree
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.For):
        return False, "这次用一个 for 循环完成重复输出，不要把 print 复制五遍。输出语句要放在循环内并缩进。"
    loop = tree.body[0]
    iterator = loop.iter
    if not (_name(loop.target, "i") and isinstance(iterator, ast.Call)
            and _name(iterator.func, "range") and len(iterator.args) == 1
            and _literal(iterator.args[0], 5) and not iterator.keywords):
        return False, "本课练习用 for i in range(5):。5 表示重复五次，i 依次取 0 到 4；这次先使用 range 的单参数写法。"
    if loop.orelse or len(loop.body) != 1 or not _literal(_print_argument(loop.body[0]), "继续加油"):
        return False, "在 for 下面缩进写一条 print(\"继续加油\")。循环会重复执行这条语句，暂时不加入 break 或其他语句。"
    return True, "循环次数和缩进里的输出都符合任务啦。这里没有运行程序；做个小判断，看看循环里的 i 怎样变化，以及循环外的语句会执行几次。"


CHECKPOINTS = {
    "print": {
        "checker": check_print_exercise,
        "hints": PRINT_HINTS,
        "quiz_code": 'print("你好")\nprint("Python")',
        "quiz_question": "代码里的引号有什么作用？",
        "quiz_options": ("引号也会显示在输出里", "引号表示这是一段文字", "引号用来把文字变成数字"),
        "quiz_output": ("你好", "Python"),
        "quiz_reason": "引号表示这是一段文字",
        "quiz_feedback": "再想想：每条 print 显示一行，引号告诉 Python 里面是文字，输出时不会带上这些引号。可以改一改再确认。",
        "exercise_evidence": "两条 print 的静态结构符合任务；未执行，理解小测尚未完成。",
        "completion_evidence": "两条 print 符合任务；预测输出和引号含义答对。未执行代码，不能据此断言全面掌握。",
        "recap": "今天练习了输出文字、修改文字和分行输出。下一课我们试试用变量保存信息，也可以留在这里再练一练。",
    },
    "variables": {
        "checker": check_variables_exercise,
        "hints": (
            "先想想示例里的 name：等号右边是要保存的文字，左边是变量名。把这个思路用到 language 上，再想想怎样修改它。",
            "把任务拆成四步：给 language 赋值、print(language)、给同一个变量重新赋值、再次 print(language)。输出变量时不要给 language 加引号。",
            '可以参考这个结构。对照每一行，想想变量在那一刻保存了什么：\n\n```python\nlanguage = "Python"\nprint(language)\nlanguage = "我正在学 Python"\nprint(language)\n```',
        ),
        "quiz_code": 'animal = "猫"\nanimal = "狗"\nprint(animal)\nprint("animal")',
        "quiz_question": "为什么两条 print 会显示不同的内容？",
        "quiz_options": ("修改值以后，变量名也自动变成了狗", "变量读取新的值；引号里是固定文字", "两条语句都会显示第一次保存的猫"),
        "quiz_output": ("狗", "animal"),
        "quiz_reason": "变量读取新的值；引号里是固定文字",
        "quiz_feedback": "顺着代码往下看：第二次赋值让 animal 保存“狗”。print(animal) 读取这个值，而 print(" + '"animal"' + ") 显示引号里的文字 animal。试着把两行输出分开写。",
        "exercise_evidence": "language 的两次字符串赋值与两次变量输出符合任务；未执行，理解小测尚未完成。",
        "completion_evidence": "创建和修改变量的写法符合任务；预测重新赋值后的输出，并区分变量名与字符串。未执行代码，不能据此断言全面掌握。",
        "recap": "今天练习了创建变量、修改它保存的值，也分清了 language 和带引号的文字。下一课我们一起认识文字和数字，看看为什么它们的计算方式不一样。",
    },
    "types": {
        "checker": check_types_exercise,
        "hints": (
            "先看看有没有引号：16 是整数，“16”是文字。想想加号两边都是数字时，与两边都是文字时，有什么不同。",
            "前两行让 age 保存整数 16，再输出 age + 1。后两行让 text 保存字符串“16”，再输出 text + \"1\"。",
            '可以参考这个对照。先自己预测输出，再做小测：\n\n```python\nage = 16\nprint(age + 1)\ntext = "16"\nprint(text + "1")\n```',
        ),
        "quiz_code": 'count = 4\nprint(count + 2)\nprint("4" + "2")',
        "quiz_question": "为什么两个加号会得到不同的结果？",
        "quiz_options": ("加号总是做数字加法", "数字相加，字符串拼接", "带引号的数字会自动变成整数"),
        "quiz_output": ("6", "42"),
        "quiz_reason": "数字相加，字符串拼接",
        "quiz_feedback": "第一条 print 计算整数 4 加 2；第二条把文字“4”和“2”接在一起。把两种结果分行写出来，再想想引号的作用。",
        "exercise_evidence": "整数与字符串的赋值、加法和拼接写法符合任务；未执行，理解小测尚未完成。",
        "completion_evidence": "练习符合任务；能预测整数加法与字符串拼接的不同结果。未执行代码，不能据此断言全面掌握。",
        "recap": "今天分清了整数和字符串，也看到了加号在两种类型上的不同作用。下一课让程序根据条件作出选择。",
    },
    "conditions": {
        "checker": check_conditions_exercise,
        "hints": (
            "先把 age 改成 16，想一想：16 >= 18 成立吗？顺着条件找对应的分支，不需要把两个分支都输出。",
            "保留 if age >= 18: 和 else:，两行后面都有冒号。分支里的 print 各缩进四个空格，else 与 if 对齐。",
            '对照缩进和分支里的文字，先在心里走一遍：\n\n```python\nage = 16\nif age >= 18:\n    print("已成年")\nelse:\n    print("未成年")\n```',
        ),
        "quiz_code": 'age = 18\nif age >= 18:\n    print("可以报名")\nelse:\n    print("再等等")',
        "quiz_question": "刚好 18 时，为什么会选择这个分支？",
        "quiz_options": ("两个分支都会执行", ">= 包含等于，条件成立", "只有大于 18，条件才成立"),
        "quiz_output": ("可以报名",),
        "quiz_reason": ">= 包含等于，条件成立",
        "quiz_feedback": "再看 >= 中的等号：18 >= 18 成立，所以只执行 if 分支里的 print，跳过 else 分支。",
        "exercise_evidence": "age=16、>=18 条件和两个分支符合任务；未执行，理解小测尚未完成。",
        "completion_evidence": "条件分支练习符合任务；能判断等于阈值时 >= 成立且只执行对应分支。未执行代码，不能据此断言全面掌握。",
        "recap": "今天练习了条件、缩进和 if / else 分支，也留意了 >= 的等号。下一课用循环，让程序帮你重复做一件事。",
    },
    "loops": {
        "checker": check_loops_exercise,
        "hints": (
            "不用把 print 复制五遍。先看看 range 括号里的数字，它决定这个例子重复多少次。",
            "把 range(3) 改成 range(5)，保留变量 i。下一行的 print 需要缩进，表示它属于循环。",
            '这两行就能表达重复五次。读一读，想想为什么输出语句要缩进：\n\n```python\nfor i in range(5):\n    print("继续加油")\n```',
        ),
        "quiz_code": 'for i in range(3):\n    print(i)\nprint("结束")',
        "quiz_question": "循环里的 i 怎样变化，最后一条 print 执行几次？",
        "quiz_options": ("i 是 1、2、3，结束显示三次", "i 是 0、1、2，循环外的结束显示一次", "i 只取 3，结束不会显示"),
        "quiz_output": ("0", "1", "2", "结束"),
        "quiz_reason": "i 是 0、1、2，循环外的结束显示一次",
        "quiz_feedback": "range(3) 从 0 开始，依次给出 0、1、2。最后一条 print 没有缩进，位于循环外，会在循环结束后执行一次。",
        "exercise_evidence": "range(5) 循环与内部输出符合任务；未执行，理解小测尚未完成。",
        "completion_evidence": "循环练习符合任务；能预测 range 的起点、结束位置以及循环内外输出次数。未执行代码，不能据此断言全面掌握。",
        "recap": "今天练习了重复次数、循环变量和缩进。五节入门课已经走到这里啦！可以打开学习记录，挑一节还不熟的重新练习，再准备把这些知识用到一个小程序中。",
    },
}


def check_understanding(output, reason, lesson_id="print"):
    lines = [line.strip() for line in output.strip().splitlines()]
    checkpoint = CHECKPOINTS[lesson_id]
    return tuple(lines) == checkpoint["quiz_output"] and reason == checkpoint["quiz_reason"]
