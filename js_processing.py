# js_processing.py
from urllib.parse import urlparse, urljoin
import re
from typing import Set
from utils import normalize_url, host_only
import logging

"""
当前文件功能：
① 从HTML中提取内联JavaScript代码（extract_inline_js_from_html）
② 通过正则表达式从JavaScript文本中猜测和提取URL（extract_urls_from_js）
"""
logger = logging.getLogger(__name__)

HTML_SCRIPT_RE = re.compile(r"<script\b([^>]*)>(?P<code>[\s\S]*?)</script>", re.IGNORECASE)

IGNORED_SCHEMES = ("data:", "blob:", "javascript:")


def _is_ignored_scheme(u: str) -> bool:
    """
    判断一个 URL 是否以特定的、不应被爬取或处理的**协议（Scheme）**开头。
    :param u: 给定的URL
    :return: 需要忽略的URL
    """
    return any(u.lower().startswith(s) for s in IGNORED_SCHEMES)

def extract_urls_from_js(js_text: str, base_url: str, allowed_hosts: set = None, debug: bool = False) -> Set[str]:
    """
    Return set of absolute URLs (strings) that belong to allowed_hosts (if provided)
    or to the base host or configured TARGET_DOMAINS.


    :param js_text: 待分析的 JavaScript 代码文本。
    :param base_url: 用于将相对路径转换为绝对 URL 的基础 URL。
    :param allowed_hosts: 可选，一个包含允许域名的集合。
    :returns 一个包含符合要求且已规范化的绝对 URL 的集合。



    1.链接猜测：使用三组正则表达式寻找JS代码中用单引号，双引号以及反引号括起来的字符串
    ① Ajax/WebSocket模式（Request Patterns）
        查找涉及网络请求或连接的函数调用：fetch(...), axios(...), xhr.open(...), new WebSocket(...)。
    ② 绝对URL模式（Absolute HTTP/HTTPS）
        查找所有包含 http:// 或 https:// 的带引号字符串。
    ③ 根相对路径模式（Root Relative Paths）
        查找所有以 / 开头（即根相对路径）的带引号字符串。
    2.主机过滤设置，构建一个允许的主机列表
    ① 将参数allow_hosts中的所有主机进行host_only规范化
    ② 解析base_url 将主机名添加到allow_hosts中
    """
    urls = set()
    # js代码列表为空，直接返回当前urls列表（空）
    if not js_text:
        return urls

    txt = js_text

    # fetch/axios/xhr/websocket patterns
    try:
        # 1.匹配网络请求/连接模式
        matches = re.findall(
            r"(?:fetch|axios(?:\.(?:get|post|put))?)\s*\(\s*['\"`]([^'\"`]+)['\"`]"
            r"|xhr\.open\s*\(\s*['\"`][A-Z]+['\"`]\s*,\s*['\"`]([^'\"`]+)['\"`]"
            r"|new\s+WebSocket\s*\(\s*['\"`]([^'\"`]+)['\"`]",
            txt
        )
        # matches 返回的是一个三元组的列表
        for triple in matches:
            for candidate in triple:
                if candidate:
                    candidate = candidate.strip()
                    if not _is_ignored_scheme(candidate):
                        urls.add(candidate)
    except Exception:
        logger.exception("pattern extract fail (fetch/xhr/ws)")

    # absolute http(s)
    # 2. 匹配绝对 HTTP/HTTPS URL
    # 查找用引号括起来的、以 http:// 或 https:// 开头的字符串
    for m in re.findall(r"""['"`](https?://[^'"`]+)['"`]""", txt):
        if not _is_ignored_scheme(m):
            urls.add(m)

    # paths starting with /
    # 3. 匹配根相对路径
    # 查找用引号括起来的、以 / 开头（但不是 //）的字符串（例如：/api/users）
    for m in re.findall(r"""['"`](/[^'"`]+)['"`]""", txt):
        if not _is_ignored_scheme(m):
            urls.add(m)

    # normalize & filter to allowed_hosts
    result = set()
    # 1. 构建允许的主机集合 (allowed)
    # 对传入的 allowed_hosts 进行 host_only 处理（去除端口）并转换为小写
    allowed = {host_only(h) for h in (allowed_hosts or set()) if h}
    # 2. 将 base_url 的主机名也添加到允许列表中
    base = urlparse(base_url)
    if base.hostname:
        allowed.add(base.hostname.lower())
    # 3. 遍历提取到的所有候选 URL，进行绝对化、过滤和规范化
    for u in urls:
        try:
            # 处理已经是 绝对URL 的情况
            if u.startswith("http://") or u.startswith("https://"):

                p = urlparse(u)
                # 检查主机名（去除端口后）是否在允许列表内
                if p.hostname and host_only(p.hostname) in allowed:
                    # 规范化 URL (例如去除片段标识符 #) 并加入结果集
                    result.add(normalize_url(u))
            else:
                abs_u = urljoin(base_url, u)
                p = urlparse(abs_u)
                if p.hostname and host_only(p.hostname) in allowed:
                    result.add(normalize_url(abs_u))
        except Exception:
            continue

    if debug:
        logger.debug("extracted urls: %s", list(result)[:20])
    return result


if __name__ == '__main__':
    js_text = """
            var url1 = 'http://sub.example.com/api/'; // 基础域名，协议不同，应该通过
            var url2 = "https://API.trusted.com/v1"; // 允许域名，大小写不同，应该通过
            var url3 = "http://Other.Domain.net/path"; // 不在允许列表中，应该过滤
            """
    BASE_URL_HTTPS = "https://Sub.Example.com/test/"
    ALLOWED_HOSTS = {"API.Trusted.com"}  # 大写测试
    result = extract_urls_from_js(js_text, BASE_URL_HTTPS, ALLOWED_HOSTS)
    print(f"result: {result}")