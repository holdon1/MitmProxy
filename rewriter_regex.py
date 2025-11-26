import re
# 假设的常量，用于查找各种 HTML/CSS/JS 属性中的 URL
# 这个正则必须足够强大，才能覆盖所有需要替换的场景。
# 示例：匹配 href, src, url() 中的值，以及 JS 字符串中的 URL
# --- 定义三个独立、清晰的正则表达式 ---
# 1. 匹配 JS 字符串和模板字面量中的 URL
# 捕获组 1: 定界符 (', ", `)
# 捕获组 2: URL/路径 (http://..., //..., 或 /...)
# JS_URL_RE = re.compile(
#     r'(["\'`])((?:https?://|//|/)(?:\\.|(?!\1).)*?)\1',  # 非贪婪匹配
#     re.IGNORECASE
# )
JS_URL_RE = re.compile(
    r'(["\'`])\s*'                     # 开引号 + 可选空格
    r'((?:https?://|//|/)[^\s\\]+?)'   # URL: 以 http/https/ // 或 / 开头, 中间不能有空白或反斜杠
    r'\s*\\?\1',
    re.IGNORECASE
)
# 2. 匹配 HTML/JS 属性 (src="...", href='...')
# 捕获组 1: 属性名 (href|src|url)
# 捕获组 2: 引号 (', ")
# 捕获组 3: URL 值
HTML_ATTR_RE = re.compile(r"""(href|src|url)\s*=\s*(['"])([^'"]+)\2""", re.IGNORECASE)

# 3. 匹配 CSS url()
# 捕获组 1: 引号?
# 捕获组 2: URL 值
CSS_URL_RE = re.compile(r"""url\s*\(\s*(['"]?)([^'"]+?)\1\s*\)""", re.IGNORECASE)

# --- 4. 专门匹配 JS 变量赋值语句右侧的 URL/路径 ---
# 捕获组 1: 变量赋值部分 (var/const/let/assignment = )
# 捕获组 2: 引号或反引号 (', ", `)
# 捕获组 3: URL/路径 (/dev-api 或 http://...)
JS_VAR_ASSIGN_RE = re.compile(
# 匹配属性名或键名 (例如 uploadUrl:)
    r'\\"\\/?dev-api\\"'
    , re.IGNORECASE)


if __name__ == '__main__':
    text = r'''
    baseUrl: \" /dev-api\",\n
    uploadImgUrl: \" /dev-api\" + this.action,\n
    quill.insertEmbed(length, \" image\", \" /dev-api\" + res.fileName);\n
    '''

    for m in JS_URL_RE.finditer(text):
        quote = m.group(1)
        url = m.group(2)
        print("quote:", quote, "url:", url)