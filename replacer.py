import re
import sys
from typing import Optional, Callable, Dict
from urllib.parse import urlparse, urlunparse

from config import *
from logger_setup import setup_logging
import logging
import os
from rewriter_regex import JS_URL_RE,HTML_ATTR_RE,CSS_URL_RE,JS_VAR_ASSIGN_RE


setup_logging()
logger = logging.getLogger(__name__)


# --- 自定义 URL 替换规则 ---
# 您需要根据您的需求定义这个函数
def rewrite_url_func(original_url: str,
                     NEW_TARGET_SCHEME: str,  # 动态参数,协议
                     NEW_TARGET_NETLOC: str  # 动态参数，域名+ 端口
                     ) -> str:
    """
    根据用户定义的规则替换 URL：
    1. 绝对 URL (http/https)：替换主机和端口。
    2. 根相对路径 (/)：添加新的主机和端口前缀。
    """

    # --- 规则 ②: 根相对路径 (/api/tasks) ---
    if original_url.startswith('/'):
        # 结果: http://192.168.0.16:3007/api/tasks
        target_base = f"{NEW_TARGET_SCHEME}://{NEW_TARGET_NETLOC}"
        return f"{target_base}{original_url}"

    # --- 规则 ①: 绝对 URL (http://...) ---
    # 如果是绝对路径的api，那么直接返回原始的url，不去做替换
    elif original_url.lower().startswith(('http://', 'https://')):
        # try:
        #     # 解析原始 URL
        #     parsed_original = urlparse(original_url)
        #
        #     # 创建一个新的 URL 元组，替换掉 scheme 和 netloc
        #     new_url_parts = parsed_original._replace(
        #         scheme=NEW_TARGET_SCHEME,  # 使用新目标的协议 (e.g., 'http')
        #         netloc=NEW_TARGET_NETLOC  # 使用新目标的 主机:端口 (e.g., '192.168.0.16:3007')
        #     )
        #
        #     # 重构新的 URL 字符串
        #     return str(urlunparse(new_url_parts))
        #
        # except Exception:
        # 如果解析失败，返回原始内容


        return original_url

    # --- 其他情况 (例如: 相对路径 'styles.css' 或非标准链接) ---
    # 保持不变，让浏览器处理
    return original_url


# --- 核心处理函数 ---

def process_and_rewrite_response(
        content: bytes,
        content_type: Optional[str],
        new_target_netloc: str,
        new_target_scheme: str = "https",
        rewriter: Callable[[str], str] = rewrite_url_func
) -> bytes:
    """
    根据内容类型筛选响应内容，并替换其中的 URL。

    Args:
        content: HTTP 响应的原始字节内容。
        content_type: 响应的 Content-Type 头部值。
        base_url: 响应对应的原始请求 URL (用于处理相对路径，尽管替换逻辑可能更复杂)。
        rewriter: 用于执行 URL 替换的函数。

    Returns:
        处理后的（可能被修改）的字节内容。
    """



    # 1. 内容类型筛选
    if not content_type or not content_type.lower().startswith('application/javascript' or 'text/javascript'):
        # 如果不是文本类型（如图片, zip 等），直接返回原始内容
        return content

    try:
        # 尝试解码为文本。假设使用 UTF-8，实际应用中应从 Content-Type 中提取编码
        text_content = content.decode('utf-8')
    except UnicodeDecodeError:
        # 如果解码失败，返回原始内容
        return content

    # 2. URL 替换逻辑
    # --- A. 替换 JS 字符串和模板字面量 (绝对 URL 和根相对路径) ---
    logger.info("---------------js_replacer-----------------")
    def js_replacer(match: re.Match) -> str:
        delimiter = match.group(1)  # 引号或反引号
        # logger.info(f"delimiter: {delimiter}")
        original_url = match.group(2)
        # logger.info(f"original_url: {original_url}")
        new_url = rewriter(original_url, new_target_scheme, new_target_netloc)
        # logger.info(f"new_url: {new_url}")
        return f'{delimiter}{new_url}{delimiter}'

    logger.info("--------------------------------------------")
    rewritten_content = JS_URL_RE.sub(js_replacer, text_content)

    # --- B. 替换 HTML 属性 ---
    def html_replacer(match: re.Match) -> str:
        attribute = match.group(1)  # href/src/url
        delimiter = match.group(2)  # 引号
        original_url = match.group(3)
        new_url = rewriter(original_url, new_target_scheme, new_target_netloc)
        return f'{attribute}={delimiter}{new_url}{delimiter}'

    rewritten_content = HTML_ATTR_RE.sub(html_replacer, rewritten_content)

    # --- C. 替换 CSS url() ---
    def css_replacer(match: re.Match) -> str:
        delimiter = match.group(1)  # 引号?
        original_url = match.group(2)
        new_url = rewriter(original_url, new_target_scheme, new_target_netloc)
        # 结果：url("new_url")
        return f'url({delimiter}{new_url}{delimiter})'

    rewritten_content = CSS_URL_RE.sub(css_replacer, rewritten_content)


    # 3. 返回修改后的内容
    return rewritten_content.encode('utf-8')


if __name__ == '__main__':
    TEST_TEXT = """
        // 1. 绝对 URL (您遇到的问题格式)
        const API_URL_ABS = 'http://192.168.0.18:8088/api/fake-api01';

        // 2. 模板字面量中的根相对路径 (您遇到的问题格式)
        const API_PATH_TPL = `/api/tasks`;

        // 3. HTML 属性 (会被替换)
        const HTML_LINK = '<a href="http://old.cdn.com/style.css">Link</a>';

        // 4. CSS url() (会被替换)
        const CSS_BG = "background-image: url('http://old.cdn.com/bg.png');";

        // 5. 纯相对路径 (应该被忽略 by rewriter)
        const REL_PATH = './data.json';
        """

    new_target_netloc = "api.mitmproxy.com"
    new_target_scheme = "http"
    original_bytes = TEST_TEXT.encode('utf-8')
    Test_JS_FILE_PATH = r"C:\Users\NBKJ2509\Desktop\work\testJS.js"
    MOCK_CONTENT_TYPE = "application/javascript; charset=utf-8"
    MOCK_BASE_URL = "https://192.168.0.162:3007"
    if not os.path.exists(Test_JS_FILE_PATH):
        logger.error(f"文件未找到：请确保当前目录下存在 {Test_JS_FILE_PATH}")
        sys.exit(1)
    try:
        # 1. 读取原始文件内容 (以字节形式读取，模拟 HTTP 响应)
        with open(Test_JS_FILE_PATH, 'rb') as f:
            original_content_bytes = f.read()

        logger.info(f"成功读取文件: {Test_JS_FILE_PATH} ({len(original_content_bytes)} 字节)")
        logger.info(f"模拟 Content-Type: {MOCK_CONTENT_TYPE}")

        # 2. 调用核心替换函数
        # rewrite_response_content 负责解码、替换、然后重新编码。
        rewritten_content_bytes = process_and_rewrite_response(
            content=original_content_bytes,
            content_type=MOCK_CONTENT_TYPE,
            new_target_netloc=new_target_netloc,
            new_target_scheme=new_target_scheme,
        )

        # 3. 结果判断与输出
        if rewritten_content_bytes == original_bytes:
            print("\n" + "=" * 50)
            logger.warning("替换前后内容相同。请检查您的 test.js 是否包含可替换的 URL 或替换逻辑是否正确。")
            print("=" * 50 + "\n")

        else:
            logger.info("内容已成功修改。")

        # 将修改后的字节内容解码并打印出来
        try:
            rewritten_text = rewritten_content_bytes.decode('utf-8')
            print("\n" + "#" * 50)
            print("         修改后的 JS 文件内容：")
            print("#" * 50)
            print(rewritten_text)
            print("#" * 50)

        except UnicodeDecodeError:
            logger.error("无法将修改后的字节内容解码为 UTF-8 文本。")

    except Exception as e:
        logger.exception(f"处理文件时发生错误: {e}")
        sys.exit(1)

    text = 'uploadUrl: \\"\\/dev-api\\" + \\"\\/common/upload\\",'
    pattern = r'\\"\\/dev-api\\"'

    match = re.search(pattern, text)
    if match:
        print("Matched:", match.group())


