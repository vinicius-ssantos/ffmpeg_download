#!/usr/bin/env python3
"""
Faz login na plataforma Edools / Impacta e grava os cookies em
`session_cookies.json`.  Usa apenas `requests`, então não precisa
de navegador nenhum.

$ python login_facimpacta.py credenciais.json          # usa cache
$ python login_facimpacta.py credenciais.json --fresh  # força novo login
"""
from __future__ import annotations
import argparse, pathlib, json, sys, re
import requests
from bs4 import BeautifulSoup as BS

LOGIN_URL     = "https://faculdade-impacta.myedools.com/users/sign_in"
COOKIES_FILE  = pathlib.Path("session_cookies.json")
HEADERS       = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

def _extrai_token(html: str) -> str:
    soup = BS(html, "html.parser")
    tag  = soup.find("meta", attrs={"name": "csrf-token"})
    if not tag:
        raise RuntimeError("authenticity_token não encontrado.")
    return tag["content"]

def login(sess: requests.Session, email: str, senha: str) -> str:
    """Efetua o POST no endpoint de login e devolve a URL de destino."""
    r = sess.get(LOGIN_URL, timeout=20, headers=HEADERS)
    token = _extrai_token(r.text)

    payload = {
        "user[email]"   : email,
        "user[password]": senha,
        "authenticity_token": token,
        "user[remember_me]": "0",
    }
    resp = sess.post(LOGIN_URL, data=payload,
                     allow_redirects=False, headers=HEADERS)

    if resp.status_code not in (302, 303):
        raise RuntimeError("Falha no login – verifique credenciais.")

    dest = resp.headers["Location"]
    return dest

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("credenciais", type=pathlib.Path)
    ap.add_argument("--fresh", action="store_true",
                    help="ignora cookies salvos e faz login de novo")
    args = ap.parse_args()

    sess = requests.Session()
    sess.headers.update(HEADERS)

    if COOKIES_FILE.exists() and not args.fresh:
        print("🔄  Cookies já salvos; use --fresh para refazer o login.")
        data = json.loads(COOKIES_FILE.read_text())
        sess.cookies.update(data["cookies"])
        return

    creds = json.loads(args.credenciais.read_text())
    email = creds.get("email") or creds.get("usuario")
    senha = creds.get("senha") or creds.get("password")
    if not (email and senha):
        print("Arquivo de credenciais deve ter 'email' e 'senha'",
              file=sys.stderr)
        sys.exit(1)

    destino = login(sess, email, senha)
    COOKIES_FILE.write_text(json.dumps({"cookies": sess.cookies.get_dict()},
                                       ensure_ascii=False, indent=2))
    print(f"✅  Login bem-sucedido! Redirecionado para: {destino}")

if __name__ == "__main__":
    main()
