"""Parsers dos exports da Shopee (pedidos .xlsx e relatórios de ADS .csv).

Funções puras: recebem bytes, devolvem dicts normalizados. A persistência (upsert,
resolução de SKU) fica na camada de API. Colunas de PII do comprador (nome, CPF,
telefone, endereço) são IGNORADAS por completo.

Fatos verificados nos exports reais:
- Order.all: 1 linha por ITEM; taxas e totais são do PEDIDO e repetem em cada linha
  (agregamos da primeira linha). Cancelado vem zerado.
- ADS: preâmbulo de ~7 linhas (título, loja, período dd/mm/aaaa - dd/mm/aaaa) e depois
  a tabela. Números com ponto decimal; percentuais com '%'; campos vazios como '-'.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Any

import openpyxl

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def norm_key(*parts: str | None) -> str:
    """Chave de match normalizada: minúscula, espaços colapsados, partes unidas por '||'."""
    cleaned = []
    for p in parts:
        s = " ".join(str(p or "").split()).strip().lower()
        cleaned.append(s)
    return "||".join(cleaned).strip("|")


def _num(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    s = str(v).strip().replace("R$", "").replace("%", "").strip()
    if s in ("", "-"):
        return default
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return default


def _int(v: Any, default: int = 0) -> int:
    return int(_num(v, float(default)))


def _dt(v: Any) -> datetime | None:
    if v is None or str(v).strip() in ("", "-"):
        return None
    if isinstance(v, datetime):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _date_br(s: str) -> date | None:
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Pedidos (Order.all*.xlsx)
# ---------------------------------------------------------------------------
STATUS_MAP = {
    "não pago": "nao_pago",
    "a enviar": "a_enviar",
    "enviado": "enviado",
    "entregue": "entregue",
    "concluído": "concluido",
    "concluido": "concluido",
    "cancelado": "cancelado",
}


def normalize_status(raw: str) -> str:
    s = (raw or "").strip().lower()
    if s in STATUS_MAP:
        return STATUS_MAP[s]
    # "O comprador pode pedir uma devolução até <data>" => entregue (dentro da janela)
    if "devolução até" in s or "devolucao até" in s or "devolução ate" in s:
        return "entregue"
    if "devolu" in s or "reembolso" in s:
        return "devolucao"
    return "enviado"  # fallback conservador


# Colunas usadas (por rótulo). PII fica FORA desta lista de propósito.
_ORDER_COLS = [
    "ID do pedido",
    "Status do pedido",
    "Data de criação do pedido",
    "Hora do pagamento do pedido",
    "Nº de referência do SKU principal",
    "Nome do Produto",
    "Número de referência SKU",
    "Nome da variação",
    "Preço acordado",
    "Quantidade",
    "Subtotal do produto",
    "Desconto do vendedor",
    "Valor Total",
    "Taxa de transação",
    "Taxa de comissão líquida",
    "Taxa de serviço líquida",
    "Total global",
]


def parse_orders_xlsx(content: bytes, source_file: str = "") -> dict:
    """Lê o Order.all*.xlsx e agrega linhas-item em pedidos.

    Retorna {"orders": [...], "errors": [...]} onde cada order tem os campos
    financeiros do pedido + items:[{sku_main, sku_var, product_name, variation_name,
    qty, unit_price, subtotal}].
    """
    # Nota: read_only=True trunca o header nos xlsx gerados pela Shopee (XML fora do
    # padrão). O arquivo é pequeno, então carregamos em modo normal.
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    ws = wb.worksheets[0]

    rows = ws.iter_rows(values_only=True)
    try:
        header = [str(h).strip() if h is not None else "" for h in next(rows)]
    except StopIteration:
        return {"orders": [], "errors": [{"linha": 0, "erro": "Arquivo vazio"}]}

    idx: dict[str, int] = {}
    for name in _ORDER_COLS:
        if name in header:
            idx[name] = header.index(name)
    missing = [n for n in ("ID do pedido", "Status do pedido", "Quantidade") if n not in idx]
    if missing:
        return {
            "orders": [],
            "errors": [{"linha": 1, "erro": f"Colunas não encontradas: {', '.join(missing)} — é o export de pedidos da Shopee?"}],
        }

    def get(row: tuple, name: str):
        i = idx.get(name)
        return row[i] if i is not None and i < len(row) else None

    orders: dict[str, dict] = {}
    errors: list[dict] = []
    for line_no, row in enumerate(rows, start=2):
        sn = str(get(row, "ID do pedido") or "").strip()
        if not sn:
            continue
        status_raw = str(get(row, "Status do pedido") or "").strip()
        o = orders.get(sn)
        if o is None:
            o = orders[sn] = {
                "order_sn": sn,
                "status_raw": status_raw,
                "status": normalize_status(status_raw),
                "created_at_channel": _dt(get(row, "Data de criação do pedido")),
                "paid_at": _dt(get(row, "Hora do pagamento do pedido")),
                # valores do PEDIDO (repetem em todas as linhas -> pegamos da primeira)
                "valor_bruto": _num(get(row, "Valor Total")),
                "taxa_comissao": _num(get(row, "Taxa de comissão líquida")),
                "taxa_servico": _num(get(row, "Taxa de serviço líquida")),
                "taxa_transacao": _num(get(row, "Taxa de transação")),
                "valor_liquido": _num(get(row, "Total global")),
                "desconto_vendedor": 0.0,
                "source_file": source_file,
                "items": [],
            }
        qty = _int(get(row, "Quantidade"), 0)
        if qty <= 0:
            errors.append({"linha": line_no, "erro": f"Pedido {sn}: quantidade inválida"})
            continue
        # desconto do vendedor é por item -> soma
        o["desconto_vendedor"] += _num(get(row, "Desconto do vendedor"))
        o["items"].append(
            {
                "sku_main": (str(get(row, "Nº de referência do SKU principal") or "").strip() or None),
                "sku_var": (str(get(row, "Número de referência SKU") or "").strip() or None),
                "product_name": (str(get(row, "Nome do Produto") or "").strip() or None),
                "variation_name": (str(get(row, "Nome da variação") or "").strip() or None),
                "qty": qty,
                "unit_price": _num(get(row, "Preço acordado")),
                "subtotal": _num(get(row, "Subtotal do produto")),
            }
        )
    wb.close()
    return {"orders": list(orders.values()), "errors": errors}


# ---------------------------------------------------------------------------
# ADS (4 relatórios .csv da mesma família)
# ---------------------------------------------------------------------------
_ADS_TYPES = (
    # (assinatura no título ou cabeçalho, report_type)
    ("grupo de anúncio", "adgroup"),
    ("gmv max", "gmvmax"),
    ("palavra-chave", "keyword"),
)

_ADS_METRICS = {
    "Impressões": ("impressions", _int),
    "Cliques": ("clicks", _int),
    "Conversões": ("conversions", _int),
    "Itens Vendidos": ("items_sold", _int),
    "GMV": ("gmv", _num),
    "Despesas": ("spend", _num),
    "ROAS": ("roas", _num),
    "ACOS": ("acos", _num),
}


def parse_ads_csv(content: bytes, source_file: str = "") -> dict:
    """Lê qualquer um dos 4 relatórios de ADS. Detecta o tipo e o período no preâmbulo.

    Retorna {"report_type", "period_start", "period_end", "rows": [...], "errors": [...]}
    com rows contendo listing_ref, ad_name, detail_key e as métricas canônicas.
    """
    text = content.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    reader = list(csv.reader(io.StringIO(text)))

    # tipo: título (1ª linha) + presença da coluna de palavra-chave
    title = (lines[0] if lines else "").lower()
    report_type = "geral"
    for sig, rtype in _ADS_TYPES:
        if sig in title:
            report_type = rtype
            break

    # período no preâmbulo: "Período,01/08/2026 - 13/08/2026"
    period_start = period_end = None
    header_i = None
    for i, row in enumerate(reader[:12]):
        if row and row[0].strip().lower() in ("período", "periodo") and len(row) > 1:
            parts = row[1].split("-")
            if len(parts) == 2:
                period_start, period_end = _date_br(parts[0]), _date_br(parts[1])
        if row and row[0].strip() == "#":
            header_i = i
            break
    if header_i is None:
        return {"report_type": report_type, "rows": [], "errors": [{"linha": 0, "erro": "Cabeçalho da tabela não encontrado — é um relatório de ADS da Shopee?"}]}
    if not period_start or not period_end:
        return {"report_type": report_type, "rows": [], "errors": [{"linha": 0, "erro": "Período não encontrado no preâmbulo do relatório"}]}

    header = [h.strip() for h in reader[header_i]]
    if "Palavra-chave/Localização" in header:
        report_type = "keyword"

    def col(row: list, name: str):
        try:
            i = header.index(name)
        except ValueError:
            return None
        return row[i] if i < len(row) else None

    name_col = "Nome do Anúncio" if "Nome do Anúncio" in header else (
        "Anúncio / Nome do Produto" if "Anúncio / Nome do Produto" in header else "Nome do Produto"
    )

    rows_out: list[dict] = []
    errors: list[dict] = []
    for line_no, row in enumerate(reader[header_i + 1 :], start=header_i + 2):
        if not row or not any(c.strip() for c in row):
            continue
        name = str(col(row, name_col) or "").strip()
        if not name:
            errors.append({"linha": line_no, "erro": "Linha sem nome de anúncio/produto"})
            continue
        listing = str(col(row, "ID do produto") or "-").strip() or "-"
        detail = "-"
        if report_type == "keyword":
            detail = str(col(row, "Palavra-chave/Localização") or "-").strip() or "-"
        out = {
            "listing_ref": listing,
            "ad_name": name,
            "detail_key": detail,
        }
        for label, (field, conv) in _ADS_METRICS.items():
            out[field] = conv(col(row, label))
        rows_out.append(out)

    return {
        "report_type": report_type,
        "period_start": period_start,
        "period_end": period_end,
        "rows": rows_out,
        "errors": errors,
    }
