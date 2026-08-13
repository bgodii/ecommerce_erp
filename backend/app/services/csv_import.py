"""Parser de CSV de vendas (ERP-030).

Tolerante a cabeçalhos em PT-BR / rótulos comuns de exportação da Shopee, ao
delimitador (`,` ou `;`) e a números no formato brasileiro (1.234,56 / 22,99).
Retorna (linhas_normalizadas, erros). A resolução de SKU -> produto/kit e a
inserção ficam na camada de API.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime

# canônico -> sinônimos aceitos (comparados em minúsculas)
CANON: dict[str, list[str]] = {
    "data": [
        "data", "data da venda", "data venda", "data do pedido",
        "data de criacao do pedido", "data de criação do pedido",
        "order date", "order creation date", "created time",
    ],
    "pedido": [
        "pedido", "numero do pedido", "número do pedido", "no do pedido",
        "nº do pedido", "n do pedido", "id do pedido", "order id", "order sn",
        "order number",
    ],
    "sku": [
        "sku", "sku produto/kit", "sku do produto", "numero de referencia sku",
        "número de referência sku", "referencia sku", "referência sku",
        "seller sku", "codigo", "código", "sku de referencia",
    ],
    "qty": ["qtd", "quantidade", "quantity", "qty", "quantidade total"],
    "preco_unitario": [
        "preco unitario", "preço unitário", "preco", "preço", "preco acordado",
        "preço acordado", "preco original", "preço original", "valor unitario",
        "valor unitário", "unit price", "preco de venda", "preço de venda",
    ],
    "taxa_shopee_pct": [
        "taxa shopee %", "taxa shopee", "comissao %", "comissão %", "comissao", "comissão",
    ],
    "taxa_fixa": ["taxa fixa", "taxa fixa r$", "taxa fixa por pedido"],
    "taxa_afiliado_pct": ["taxa afiliado %", "afiliado %", "taxa afiliado", "comissao afiliado %"],
    "outras_taxas": ["outras taxas", "outras taxas r$", "outras", "outros custos"],
}

REQUIRED = ("data", "sku", "qty", "preco_unitario")


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _map_headers(headers: list[str]) -> dict[str, int]:
    normed = [_norm(h) for h in headers]
    result: dict[str, int] = {}
    for canon, syns in CANON.items():
        idx = next((i for i, h in enumerate(normed) if h in syns), None)
        if idx is None:
            idx = next((i for i, h in enumerate(normed) if any(s in h for s in syns)), None)
        if idx is not None:
            result[canon] = idx
    return result


def _parse_num(v) -> float | None:
    if v is None:
        return None
    s = str(v).strip().replace("R$", "").replace("%", "").strip()
    if s == "":
        return None
    if "," in s and "." in s:  # 1.234,56 -> 1234.56
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:  # 22,99 -> 22.99
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_date(v) -> str | None:
    s = str(v or "").strip().split(" ")[0].split("T")[0]
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _pct(v) -> float | None:
    n = _parse_num(v)
    if n is None:
        return None
    return n / 100 if n > 1 else n  # aceita "20", "20%" e "0.2"


def parse_sales_csv(content: bytes) -> tuple[list[dict], list[dict]]:
    text = content.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    if not lines:
        return [], [{"linha": 0, "erro": "Arquivo vazio"}]

    delim = ";" if lines[0].count(";") > lines[0].count(",") else ","
    rows_raw = list(csv.reader(io.StringIO(text), delimiter=delim))
    headers = rows_raw[0]
    hmap = _map_headers(headers)
    missing = [k for k in REQUIRED if k not in hmap]
    if missing:
        return [], [
            {"linha": 1, "erro": f"Colunas obrigatórias não encontradas: {', '.join(missing)}"}
        ]

    parsed: list[dict] = []
    errors: list[dict] = []
    for i, row in enumerate(rows_raw[1:], start=2):
        if not any((c or "").strip() for c in row):
            continue

        def get(key: str, _row=row):
            idx = hmap.get(key)
            return _row[idx] if idx is not None and idx < len(_row) else None

        d = _parse_date(get("data"))
        sku = (get("sku") or "").strip()
        qty = _parse_num(get("qty"))
        preco = _parse_num(get("preco_unitario"))
        if d is None or not sku or not qty or preco is None:
            errors.append({"linha": i, "erro": "Data, SKU, quantidade ou preço inválido/ausente"})
            continue

        parsed.append(
            {
                "data_venda": d,
                "pedido": (get("pedido") or "").strip() or None,
                "sku": sku,
                "qty": int(qty),
                "preco_unitario": preco,
                "taxa_shopee_pct": _pct(get("taxa_shopee_pct")),
                "taxa_fixa": _parse_num(get("taxa_fixa")),
                "taxa_afiliado_pct": _pct(get("taxa_afiliado_pct")),
                "outras_taxas": _parse_num(get("outras_taxas")),
            }
        )
    return parsed, errors
