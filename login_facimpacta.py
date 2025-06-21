#!/usr/bin/env python3
"""
Faz login no portal myedools/Faculdade Impacta e salva os
cookies de sessão num arquivo JSON (`session_cookies.json`).

Exemplos
--------
# usa cookies em cache (se existirem)
python login_facimpacta.py credenciais.json

# força login novamente
python login_facimpacta.py credenciais.json --fresh
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://faculdade-impacta.myedools.com"
LOGIN_URL = f"{BASE_URL}/users/sign_in"
COOKIES_FILE = pathlib.Path("session_cookies.json")


# ───────── helpers ────────────────────────────────────────────────────────────
def _carregar_credenciais(path: pathlib.Path) -> tuple[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        email = data["email"]
        senha = data.get("senha") or data["password"]  # aceita ambos
    except KeyError as exc:
        raise KeyError(
            "Arquivo de credenciais deve conter as chaves "
            '"email" e "password" (ou "senha").'
        ) from exc
    return email, senha


def _salvar_cookies(sess: requests.Session) -> None:
    payload = {
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cookies": requests.utils.dict_from_cookiejar(sess.cookies),
    }
    COOKIES_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def _carregar_cookies(sess: requests.Session) -> None:
    raw = json.loads(COOKIES_FILE.read_text(encoding="utf-8"))
    cookies_dict = raw.get("cookies", raw)  # lida com os dois formatos
    sess.cookies = requests.utils.cookiejar_from_dict(cookies_dict)


def _login(sess: requests.Session, email: str, senha: str) -> str:
    """Efetua login e devolve a URL final (enrollments)."""
    # 1) token CSRF
    r = sess.get(LOGIN_URL, timeout=15)
    r.raise_for_status()
    csrf = BeautifulSoup(r.text, "html.parser").find(
        "meta", attrs={"name": "csrf-token"}
    )["content"]

    # 2) submit
    payload = {
        "authenticity_token": csrf,
        "user[email]": email,
        "user[password]": senha,
        "user[organization_id]": "6352",
    }
    r = sess.post(LOGIN_URL, data=payload, timeout=15, allow_redirects=False)
    r.raise_for_status()

    # 3) segue redirecionamento manualmente
    destino = r.headers.get("location")
    if not destino:
        raise RuntimeError("Login falhou – verifique e-mail e senha.")

    sess.get(destino, timeout=15)
    return destino


# ───────── main ───────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("credenciais_json", type=pathlib.Path)
    ap.add_argument("--fresh", action="store_true",
                    help="ignora cache de cookies e faz login novamente")
    args = ap.parse_args()

    email, senha = _carregar_credenciais(args.credenciais_json)

    with requests.Session() as sess:
        if COOKIES_FILE.exists() and not args.fresh:
            _carregar_cookies(sess)
            print("🔄  Cookies já salvos; use --fresh para refazer o login.")
        else:
            destino = _login(sess, email, senha)
            _salvar_cookies(sess)
            print(f"✅  Login bem-sucedido! Redirecionado para: {destino}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Uso: python login_facimpacta.py credenciais.json")
        sys.exit(1)
    main()
