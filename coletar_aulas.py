#!/usr/bin/env python3
"""
Extrai todos os links das aulas de um curso da Faculdade Impacta
(Edools/HeroSpark).

Fluxo:
1) tenta raspar o HTML estático;
2) se não achar, usa Selenium (headless) reutilizando os cookies salvos.

Requisitos:
pip install requests beautifulsoup4 selenium webdriver-manager
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import time

import requests
from bs4 import BeautifulSoup

# ───────── Selenium ──────────────────────────────────────────────────────────
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL = "https://faculdade-impacta.myedools.com"
COOKIES_FILE = pathlib.Path("session_cookies.json")
REGEX_AULA = re.compile(r"/enrollments/\d+/courses/\d+/course_contents/\d+")


# ───────── helpers ────────────────────────────────────────────────────────────
def _sessao() -> requests.Session:
    if not COOKIES_FILE.exists():
        raise FileNotFoundError(
            "session_cookies.json não encontrado. Execute login_facimpacta.py --fresh."
        )
    raw = json.loads(COOKIES_FILE.read_text(encoding="utf-8"))
    sess = requests.Session()
    sess.cookies = requests.utils.cookiejar_from_dict(raw.get("cookies", raw))
    return sess


def _extrair_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = {a["href"] for a in soup.find_all("a", href=True)
             if REGEX_AULA.fullmatch(a["href"])}
    return sorted(f"{BASE_URL}{href}" for href in links)


def _raspar_com_selenium(cookies: dict, url: str) -> list[str]:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")

    # 1) tenta usar driver fornecido pelo usuário
    driver_path = os.getenv("CHROMEDRIVER")               # caminho manual
    if driver_path and not pathlib.Path(driver_path).exists():
        raise FileNotFoundError(f"CHROMEDRIVER='{driver_path}' não existe.")

    try:
        if not driver_path:
            driver_path = ChromeDriverManager().install()

        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=opts)
    except (OSError, WebDriverException) as exc:
        raise RuntimeError(
            "Falha ao iniciar o ChromeDriver — normalmente é sinal de "
            "incompatibilidade de arquitetura ou versão. "
            "Baixe manualmente o executável adequado ao seu Chrome "
            "e defina a variável de ambiente CHROMEDRIVER com o caminho completo."
        ) from exc

    try:
        driver.get("about:blank")
        for k, v in cookies.items():
            driver.add_cookie({"name": k, "value": v,
                               "domain": "faculdade-impacta.myedools.com",
                               "path": "/"})
        driver.get(url)
        time.sleep(3)                                     # aguarda JS
        return _extrair_links(driver.page_source)
    finally:
        driver.quit()


# ───────── fluxo principal ───────────────────────────────────────────────────
def coletar_aulas(course_url: str, destino: pathlib.Path) -> None:
    sess = _sessao()

    # 1) HTML estático
    r = sess.get(course_url, timeout=20)
    if r.is_redirect:
        raise RuntimeError("Sessão expirada – refaça o login com --fresh.")

    r.raise_for_status()
    aulas = _extrair_links(r.text)

    if aulas:
        print(f"✅  {len(aulas)} links encontrados no HTML estático.")
    else:
        print("🔍  Nenhum link encontrado – usando Selenium…")
        aulas = _raspar_com_selenium(sess.cookies.get_dict(), course_url)
        print(f"✅  {len(aulas)} links coletados via Selenium.")

    if not aulas:
        raise RuntimeError("Nenhum link detectado. O layout do site pode ter mudado.")

    destino.write_text(json.dumps(aulas, indent=2, ensure_ascii=False))
    print(f"💾  Links salvos em: {destino.resolve()}")


# ───────── CLI ───────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("course_url", help="URL completa do curso (/courses/ID).")
    ap.add_argument("--out", default="lessons.json",
                    help="Arquivo JSON de saída (padrão: lessons.json)")
    args = ap.parse_args()

    coletar_aulas(args.course_url, pathlib.Path(args.out))


if __name__ == "__main__":
    main()
