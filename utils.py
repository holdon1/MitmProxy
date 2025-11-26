# utils.py
from urllib.parse import urlparse, urljoin, urlunparse
import re


def normalize_url(u: str) -> str:
    """
    去除URL中的片段标识符
    :param u: 截取的原始URL
    :return: 格式化后的URL
    """
    # 字符串为空 或 为 'NONE'
    if not u:
        return u
    # 移除两端空白字符（空格、换行符等）
    u = u.strip()
    # 移除片段标识符以及之后的内容
    if "#" in u:
        u = u.split("#", 1)[0]

    # 解析 URL
    p = urlparse(u)
    # 检查 p.netloc 是否存在，并且确保它是一个字符串
    if p.netloc:
        # 将 netloc 字段转换为小写，并用 urlunparse 重建 URL
        # 注意：netloc 包含主机名和端口。转换为小写可以规范化主机名。
        normalized_url = urlunparse(p._replace(netloc=p.netloc.lower()))
        return normalized_url
    return u


def host_only(host: str) -> str:
    """
    从当前主机名（可能包含端口）提取纯净的主机地址
    """
    if not host:
        return ""
    # 以冒号为分割标志，提取冒号前的host，并且统一小写
    return host.split(":", 1)[0].lower()


if __name__ == '__main__':
    url = "api.domain.net:8080#####"
    print(host_only(normalize_url(url)))
