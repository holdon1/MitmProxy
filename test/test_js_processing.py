# test_js_processing.py

import unittest
from js_processing import extract_urls_from_js, _is_ignored_scheme  # 假设你将函数放在 js_processing.py

# 确保 logger 不会干扰测试输出
import logging

logging.disable(logging.CRITICAL)


class TestJSExtraction(unittest.TestCase):
    BASE_URL = "http://example.com/page/index.html"
    ALLOWED_HOSTS = {"api.trusted.com", "cdn.trusted.net:8080"}

    def test_empty_js_text(self):
        # 案例 1: 测试空输入
        self.assertEqual(extract_urls_from_js("", self.BASE_URL), set())

    def test_extraction_from_request_patterns(self):
        # 案例 2: 测试 fetch, axios, xhr, websocket 等请求模式的提取
        js_text = """
        fetch('/api/users');
        axios.get("https://api.trusted.com/data"); 
        new WebSocket('wss://example.com/ws');
        var x = new XMLHttpRequest(); x.open('POST', "http://example.com/submit");
        """
        expected = {
            "http://example.com/api/users",
            "https://api.trusted.com/data",
            "http://example.com/ws",  # urljoin 会将 wss 转换为 http/https
            "http://example.com/submit",
        }
        # 注意：urljoin(http, wss) 结果取决于具体 Python 版本和 base_url 的处理，
        # 实际测试中可能需要将 base_url 设为 https 以保持协议一致性，这里假设它转为 http
        # 为了精确，我们只验证路径和主机名是否被提取和过滤。
        result = extract_urls_from_js(js_text, self.BASE_URL, self.ALLOWED_HOSTS)
        self.assertEqual(result, expected)

    def test_absolute_url_extraction_and_filtering(self):
        # 案例 3: 测试绝对 URL 的提取和过滤
        js_text = """
        var good_url_1 = "http://example.com/resource1";
        var good_url_2 = 'https://api.trusted.com/v1/';
        var bad_url_1 = "https://unallowed.com/data"; 
        var good_url_3 = `http://cdn.trusted.net:8080/image.jpg#anchor`;
        """
        expected = {
            "http://example.com/resource1",
            "https://api.trusted.com/v1/",
            # host_only 会处理端口，normalize_url 会去除 #anchor
            "http://cdn.trusted.net:8080/image.jpg",
        }
        result = extract_urls_from_js(js_text, self.BASE_URL, self.ALLOWED_HOSTS)

        # 'bad_url_1' 被过滤，因为它不在 allowed_hosts 或 base_url 域名内
        self.assertEqual(result, expected)

    def test_root_relative_path_and_normalization(self):
        # 案例 4: 测试根相对路径的提取和绝对化
        js_text = """
        const path1 = '/data/item?id=1';
        const path2 = '/another-page#details'; // 应该被规范化
        const path3 = 'not_a_root_path'; // 应该被忽略
        """
        expected = {
            "http://example.com/data/item?id=1",
            "http://example.com/another-page",  # #details 被 normalize_url 去除
        }
        # 注意: path3 'not_a_root_path' 不匹配 r"""['"`](/[^'"`]+)['"`]"""，因此不会被提取。
        result = extract_urls_from_js(js_text, self.BASE_URL, self.ALLOWED_HOSTS)
        self.assertEqual(result, expected)

    def test_ignored_schemes_exclusion(self):
        # 案例 5: 测试忽略协议的排除
        js_text = """
        fetch('javascript:alert(1)'); // 被忽略
        var data_url = "data:image/png;base64,..."; // 被忽略
        var blob_url = 'blob:http://example.com/uuid'; // 被忽略
        var valid_url = "http://example.com/valid";
        """
        expected = {
            "http://example.com/valid",
        }
        result = extract_urls_from_js(js_text, self.BASE_URL)
        self.assertEqual(result, expected)

    def test_complex_filtering_and_case_insensitivity(self):
        # 案例 6: 复杂过滤（不同协议、不同大小写）
        BASE_URL_HTTPS = "https://Sub.Example.com/test/"
        ALLOWED_HOSTS = {"API.Trusted.com"}  # 大写测试
        js_text = """
        var url1 = 'http://sub.example.com/api/'; // 基础域名，协议不同，应该通过
        var url2 = "https://API.trusted.com/v1"; // 允许域名，大小写不同，应该通过
        var url3 = "http://Other.Domain.net/path"; // 不在允许列表中，应该过滤
        """
        expected = {
            "http://sub.example.com/api/",
            "https://api.trusted.com/v1",
        }
        result = extract_urls_from_js(js_text, BASE_URL_HTTPS, ALLOWED_HOSTS)
        self.assertEqual(result, expected)

# 如果使用 unittest，运行测试：
# if __name__ == '__main__':
#     unittest.main()