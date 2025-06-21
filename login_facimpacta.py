# -*- coding: utf-8 -*-
"""
Autentica no portal Edools da Faculdade Impacta
e grava cookies de sessão em `session_cookies.json`.

USO:
    python login_facimpacta.py credenciais.json        # faz login e salva cookies
    python login_facimpacta.py credenciais.json --fresh  # força novo login

Formato de credenciais.json:
{
  "email":    "seu@email",
  "password": "*******"
}
"""
from __future__ import annotations
import argparse, json, sys, time, urllib.parse as ul
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL      = "https://faculdade-impacta.myedools.com"
SIGN_IN_URL   = f"{BASE_URL}/users/sign_in"
COOKIES_FILE  = Path("session_cookies.json")
HEADERS       = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0"
}


# -------------------------------------------------------------------------
# utilidades
# -------------------------------------------------------------------------
def salvar_sessao(sess: requests.Session, outfile: Path = COOKIES_FILE) -> None:
    data = {
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cookies":  sess.cookies.get_dict()
    }
    outfile.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def carregar_sessao(infile: Path = COOKIES_FILE) -> requests.Session | None:
    """Reconstrói a sessão com os cookies salvos (ou None, se não existir)."""
    if not infile.exists():
        return None
    data = json.loads(infile.read_text())
    s = requests.Session()
    s.headers.update(HEADERS)
    s.cookies.update(data["cookies"])
    return s


# -------------------------------------------------------------------------
# fluxo de login
# -------------------------------------------------------------------------
def login(cred_file: str | Path) -> requests.Session:
    cred = json.loads(Path(cred_file).read_text(encoding="utf-8"))
    email, password = cred["email"], cred["password"]

    sess = requests.Session()
    sess.headers.update(HEADERS)

    # --- 1) GET de /users/sign_in para obter authenticity_token ----------------
    r = sess.get(SIGN_IN_URL, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    token_tag = soup.find("meta", attrs={"name": "csrf-token"})
    authenticity_token = token_tag["content"] if token_tag else ""

    # --- 2) POST para efetuar login -------------------------------------------
    payload = {
        "authenticity_token": authenticity_token,
        "user[organization_id]": "6352",
        "user[email]":          email,
        "user[password]":       password,
    }

    resp = sess.post(SIGN_IN_URL, data=payload,
                     allow_redirects=False, timeout=20)

    if resp.status_code not in (302, 303):
        raise RuntimeError("❌  Falha no login – verifique email ou senha.")

    redirect_to = ul.urljoin(BASE_URL, resp.headers["Location"])
    # segue o redirect só para conferir:
    sess.get(redirect_to, timeout=20)

    salvar_sessao(sess)
    print(f"✅  Login bem-sucedido! Redirecionado para: {redirect_to}")
    return sess


# -------------------------------------------------------------------------
# CLI simples
# -------------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Faz login na Faculdade Impacta (Edools) e salva cookies."
    )
    ap.add_argument("credenciais", help="Arquivo JSON com email e password.")
    ap.add_argument("--fresh", action="store_true",
                    help="Ignora cookies existentes e força novo login.")
    args = ap.parse_args()

    if not args.fresh and COOKIES_FILE.exists():
        print("🔄  Cookies já salvos; use --fresh para refazer o login.")
        sys.exit(0)

    login(args.credenciais)
