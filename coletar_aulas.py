# -*- coding: utf-8 -*-
"""
Baixa a lista (título + URL) de todas as aulas de um curso na plataforma
Faculdade Impacta / Edools.

USO:
    python coletar_aulas.py <URL-do-curso> [saida.json]

Requerimentos extra (apenas se o fallback for acionado):
    pip install selenium webdriver-manager

Obs. 1) Assuma que você já executou:
        python login_facimpacta.py credenciais.json
      — isso deixa os cookies em session_cookies.json.

Obs. 2) Caso prefira desactivar o Selenium de propósito (ex.: CI sem X),
        basta exportar a variável de ambiente IMPACTA_NO_SELENIUM=1
"""

from __future__ import annotations
import json, os, sys, time, urllib.parse as ul
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── utilidades reaproveitadas do script de login ──────────────────────────
from login_facimpacta import (
    carregar_sessao, COOKIES_FILE, HEADERS, BASE_URL
)

# ── fallback opcional com Selenium ────────────────────────────────────────
USE_SELENIUM = not bool(os.getenv("IMPACTA_NO_SELENIUM"))
if USE_SELENIUM:
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
    except ModuleNotFoundError:       # selenium não instalado
        USE_SELENIUM = False


# -------------------------------------------------------------------------
# helpers
# -------------------------------------------------------------------------
def _get_com_redirect(sess: requests.Session, url: str, max_hops: int = 8):
    """Faz GET manual seguindo redirects mas aborta se mandarem para /sign_in."""
    for _ in range(max_hops):
        r = sess.get(url, allow_redirects=False, timeout=20)
        if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
            loc = ul.urljoin(BASE_URL, r.headers["Location"])
            if "/users/sign_in" in loc:
                raise RuntimeError(
                    "⚠️  Cookies expirados – refaça o login:\n"
                    "   python login_facimpacta.py credenciais.json --fresh"
                )
            url = loc
            continue
        return r
    raise RuntimeError(f"Excedido limite de {max_hops} redirects.")


def _raspar_com_bs4(html: str) -> list[dict]:
    """Extrai <a class='lesson-title'>…</a> do HTML bruto."""
    soup = BeautifulSoup(html, "html.parser")
    return [
        {"title": a.get_text(strip=True),
         "url":   ul.urljoin(BASE_URL, a["href"])}
        for a in soup.select("a.lesson-title[href]")
    ]


# -------------------------------------------------------------------------
#  fallback em Selenium (só usado se necessário)
# -------------------------------------------------------------------------
def _raspar_com_selenium(sess_cookies: dict, course_url: str) -> list[dict]:
    if not USE_SELENIUM:
        raise RuntimeError(
            "Nenhum link encontrado e Selenium não disponível "
            "(instale selenium + webdriver-manager ou exporte IMPACTA_NO_SELENIUM=1 "
            "para desactivar este fallback)."
        )

    chrome_opts             = Options()
    chrome_opts.headless    = True
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--window-size=1600,1000")
    chrome_opts.add_argument("--log-level=3")

    driver = webdriver.Chrome(
        ChromeDriverManager().install(),
        options=chrome_opts,
    )

    try:
        # 1) navega até o domínio raiz para poder injetar cookies
        driver.get(BASE_URL)

        # 2) injeta cada cookie salvo no requests.Session
        for name, value in sess_cookies.items():
            driver.add_cookie({
                "name":   name,
                "value":  value,
                "domain": ".myedools.com",   # cobre sub-domínios
                "path":   "/",
            })

        # 3) agora abre a página do curso já autenticado
        driver.get(course_url)

        # 4) espera o JS renderizar as aulas
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.lesson-title"))
        )

        anchors = driver.find_elements(By.CSS_SELECTOR, "a.lesson-title[href]")
        return [
            {"title": a.text.strip(),
             "url":   a.get_attribute("href")}
            for a in anchors
        ]
    finally:
        driver.quit()


# -------------------------------------------------------------------------
# função principal
# -------------------------------------------------------------------------
def coletar_aulas(course_url: str, outfile: Path | None = None) -> Path:
    sess = carregar_sessao(COOKIES_FILE)
    if sess is None:
        raise RuntimeError(
            "Primeiro faça login:\n"
            "   python login_facimpacta.py credenciais.json"
        )

    sess.headers.update(HEADERS)

    # ── tentativa 1: requests puro ────────────────────────────────────────
    r      = _get_com_redirect(sess, course_url)
    aulas  = _raspar_com_bs4(r.text)

    # ── fallback: Selenium, se necessário ─────────────────────────────────
    if not aulas:
        print("🔍  Nenhum link no HTML estático – acionando Selenium…")
        aulas = _raspar_com_selenium(sess.cookies.get_dict(), course_url)

    if not aulas:
        raise RuntimeError(
            "Nenhum link de aula encontrado nem com Selenium. "
            "A estrutura do site pode ter mudado."
        )

    # ── salva JSON --------------------------------------------------------
    if outfile is None:
        ident   = course_url.rstrip("/").split("/")[-2]  # pega ID do curso
        outfile = Path(f"course-{ident}_lessons.json")

    outfile.write_text(json.dumps({
        "coletado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(aulas),
        "aulas": aulas
    }, ensure_ascii=False, indent=2))

    print(f"💾  {len(aulas)} aulas salvas em: {outfile.resolve()}")
    return outfile


# -------------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python coletar_aulas.py <URL-do-curso> [saida.json]")
        sys.exit(1)

    url  = sys.argv[1]
    dest = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    coletar_aulas(url, dest)
