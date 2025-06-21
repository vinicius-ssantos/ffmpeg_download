#!/usr/bin/env python3
"""
Autentica no portal Faculdade Impacta (Edools)
e devolve uma sessão pronta para uso.

Uso:
    python login_facimpacta.py credenciais.json
"""

import json
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup


LOGIN_URL = "https://faculdade-impacta.myedools.com/users/sign_in"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}


def carregar_credenciais(json_path: Path) -> tuple[str, str]:
    with json_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data["email"], data["password"]


def extrair_tokens(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    csrf = soup.find("input", {"name": "authenticity_token"})
    org_id = soup.find("input", {"name": "user[organization_id]"})

    if not csrf or not org_id:
        raise RuntimeError(
            "Não foi possível localizar authenticity_token ou organization_id. "
            "O HTML pode ter mudado ou o site pediu reCAPTCHA."
        )

    return csrf["value"], org_id["value"]


def login(email: str, password: str) -> requests.Session | None:
    sess = requests.Session()

    # 1) GET da página para capturar cookies + tokens ocultos
    resp = sess.get(LOGIN_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    authenticity_token, organization_id = extrair_tokens(resp.text)

    # 2) POST de autenticação
    payload = {
        "authenticity_token": authenticity_token,
        "user[organization_id]": organization_id,
        "user[email]": email,
        "user[password]": password,
    }

    post = sess.post(LOGIN_URL, data=payload, headers=HEADERS, timeout=15, allow_redirects=True)

    # 3) Heurísticas simples de sucesso
    if "Email e/ou senha inválidos" in post.text:
        print("❌  Credenciais rejeitadas.")
        return None

    if post.url.endswith("/users/sign_in"):
        print("⚠️  Ainda na tela de login — provavelmente o site exigiu reCAPTCHA.")
        return None

    print("✅  Login bem-sucedido! Redirecionado para:", post.url)
    return sess


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python login_facimpacta.py credenciais.json")
        sys.exit(1)

    json_file = Path(sys.argv[1])
    email, pwd = carregar_credenciais(json_file)
    session = login(email, pwd)

    # Exemplo: acessar a home autenticada, caso o login tenha dado certo
    if session:
        r = session.get("https://faculdade-impacta.myedools.com/", headers=HEADERS, timeout=15)
        print("Título da página inicial:", BeautifulSoup(r.text, "html.parser").title.string)
