#!/usr/bin/env python3
"""
Coleta todos os links das aulas de um curso Edools/Impacta usando Playwright.

Pré-requisitos (uma única vez):
    pip install playwright==1.*
    python -m playwright install    # baixa o Chromium headless

Uso:
    python coletar_aulas.py https://.../enrollments/1234/courses/5678 \
           --out lessons.json
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys
import requests
from playwright.sync_api import sync_playwright

BASE = "https://faculdade-impacta.myedools.com"
RX_PATH = re.compile(r'/enrollments/\d+/courses/\d+/course_contents/\d+')

COOKIES_FILE = pathlib.Path("session_cookies.json")
HEADERS      = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}


def _add_cookies_to_context(ctx, cookies_dict: dict[str, str]) -> None:
    """Injeta cookies de sessão já autenticada no contexto Playwright."""
    cookies = [{
        "name"   : k,
        "value"  : v,
        "domain" : "faculdade-impacta.myedools.com",
        "path"   : "/",
        "httpOnly": False,
        "secure"  : True,
        "sameSite": "Lax"
    } for k, v in cookies_dict.items()]
    ctx.add_cookies(cookies)


def coleta_links(course_url: str) -> list[str]:
    """Abre a página via Playwright e extrai os paths das aulas."""
    if not COOKIES_FILE.exists():
        sys.exit("⚠️  Você precisa fazer login primeiro (session_cookies.json).")

    cookies = json.loads(COOKIES_FILE.read_text())["cookies"]

    with sync_playwright() as p:
        browser  = p.chromium.launch(headless=True)
        context  = browser.new_context()
        _add_cookies_to_context(context, cookies)

        page = context.new_page()
        page.goto(course_url, wait_until="networkidle")
        html = page.content()

        paths = {m.group(0) for m in RX_PATH.finditer(html)}
        if not paths:
            raise RuntimeError("Nenhum link encontrado – verifique a URL ou o curso.")

        return [f"{BASE}{path}" for path in sorted(paths)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("course_url")
    ap.add_argument("--out", "-o", default="lessons.json",
                    help="arquivo de saída (padrão: lessons.json)")
    args = ap.parse_args()

    links = coleta_links(args.course_url)
    pathlib.Path(args.out).write_text(
        json.dumps(links, indent=2, ensure_ascii=False)
    )
    print(f"✅  {len(links)} links salvos em {args.out}")


if __name__ == "__main__":
    main()
