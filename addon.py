# mitmproxy_token_proxy/addon.py
from mitmproxy import http
import json
import logging
from threading import Lock
from logger_setup import setup_logging
from config import *
from replacer import rewrite_url_func, process_and_rewrite_response

setup_logging()
logger = logging.getLogger(__name__)

# Shared in-memory store for discovered JS URLs
JS_URLS = {}  # key: source_url -> set(found_urls)
JS_URLS_LOCK = Lock()


# helper
def host_matches_any(host: str, domain_list):
    if not host:
        return False
    h = host.lower()
    return any(d.lower() in h for d in domain_list)


class TokenProxyAddon:

    # ---------- request hook ----------
    def request(self, flow: http.HTTPFlow):

        logger.info(f"[HOOK-REQUEST] {flow.request.method} {flow.request.pretty_url}")

    def match_domain(self, host: str):
        # 假设 host_matches_any 函数已在顶部定义或导入
        return host_matches_any(host, TARGET_DOMAINS)

    # ---------- response hook ----------
    def response(self, flow: http.HTTPFlow):
        logger.info("=================== response begin ===================")
        resp = flow.response
        host = flow.request.host or ""
        path = flow.request.path or ""
        port = flow.request.port or ""
        scheme = flow.request.scheme or ""
        content_type = resp.headers.get("Content-Type", "")
        logger.info(f"[RESP] scheme={scheme} host={host}, path={path}, status={resp.status_code}, ct={content_type},port={port}")

        # --- 核心：确保处理压缩头部 ---
        if "content-encoding" in resp.headers:
            # 移除编码头部，强制浏览器将内容视为未压缩的普通文本
            del resp.headers["Content-Encoding"]
        if "content-length" in resp.headers:
            del resp.headers["Content-Length"]
        # 1. 检查是否为目标域
        # if not self.match_domain(host):
        #     logger.debug("非目标域，拦截")
        #     return

        # 2. 检查是否为文本内容 (Content-Type starts with 'text/')
        ct = content_type.lower().strip()
        is_text_type = False
        if ct.startswith("text/"):
            is_text_type = True
        elif ct.startswith("application/json"):
            is_text_type = True
        elif ct.startswith("application/javascript") or ct.startswith("application/x-javascript"):
            is_text_type = True
        elif ct.startswith("text/javascript"):
            is_text_type = True
        elif ct.startswith("application/xml") or ct.startswith("application/xhtml+xml"):
            is_text_type = True
        if not is_text_type:
            logger.info("[RESP] 非文本类型响应，跳过")
            return
        # 3.动态计算替换目标
        DYNAMIC_NETLOC = f"{host}:{port}"
        DYNAMIC_SCHEME = f"{scheme}"
        try:
            # 获取原始文本内容。Mitmproxy 会自动处理编码问题。
            original_content_bytes = resp.content or b""
            if not original_content_bytes:
                logger.info("[RESP] 空响应体，跳过")
                return
            # --- 核心替换逻辑调用 ---

            # 假设 rewrite_response_content 是一个函数，
            # 它接收字节内容、Content-Type 和 Base URL，并返回替换后的字节内容。
            rewritten_content_bytes = process_and_rewrite_response(
                content=original_content_bytes,
                content_type=content_type,
                new_target_netloc=DYNAMIC_NETLOC,
                new_target_scheme=DYNAMIC_SCHEME,
            )

            # 3. 将修改后的内容写回响应
            if rewritten_content_bytes != original_content_bytes:
                resp.set_content(rewritten_content_bytes)
                logger.info(f"[REWRITE] Successfully rewrote URLs in response from {flow.request.pretty_url}")
            else:
                logger.info(f"[REWRITE] No change for {flow.request.pretty_url}")
        except Exception:
            # 捕获并记录处理过程中的任何异常
            logger.exception("[REWRITE-ERR] Failed to process and rewrite response content")


# Export addon for mitmproxy
addons = [TokenProxyAddon()]
