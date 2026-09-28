"""AgentCore Platform v1.0 — CMN-C1-171 template-catalog KB service.

Deterministic-core retrieval over a MOCK SAMPLE catalog (industry x pattern x
template_id). The entries below are illustrative placeholders, not real
templates: replace `_CATALOG` with your own template catalog before use. A
full catalog + embedding model is deferred and NOT a hard blocker:
retrieval here is a keyword/intent match against the curated fixture, which is
reproducible and testable offline. When the embedding dependency is approved,
swap the matcher for dense retrieval behind the same `retrieve_candidates`
signature — no node change.

S-3 relies on `is_valid_template_id()` for deterministic membership validation:
every routed template_id MUST be a member of this catalog.

No credentials, no os.environ, no external calls.
"""

from __future__ import annotations

from typing import Any

# Catalog schema version — surfaced in every routing recommendation so callers
# know coverage; bump on each catalog refresh (stale-catalog awareness).
CATALOG_KB_VERSION = "sample-catalog-v1"

# MOCK SAMPLE catalog — placeholder entries that illustrate the schema; replace
# them with your own catalog. Each entry: template_id, industry, pattern, description, keyword triggers.
_CATALOG: list[dict[str, Any]] = [
    {
        "template_id": "SAMPLE-RAG-01",
        "industry": "CMN",
        "pattern": "VectorRAG",
        "description": "Sample entry: retrieve and answer questions over a knowledge base.",
        "keywords": [
            "q&a",
            "question",
            "knowledge base",
            "kb",
            "faq",
            "rag",
            "retrieve",
            "answer",
            "vector",
            "semantic search",
            "search",
            "lookup",
            "cite",
            "source",
        ],
        "keywords_ja": [
            "質問",
            "問い合わせ",
            "回答",
            "ナレッジ",
            "知識",
            "社内文書",
            "検索",
            "参照",
            "根拠",
            "よくある質問",
        ],
    },
    {
        "template_id": "SAMPLE-DOCGEN-01",
        "industry": "CMN",
        "pattern": "DocGeneration",
        "description": "Sample entry: generate a structured document or report from inputs.",
        "keywords": ["generate", "document", "report", "draft", "compose", "write", "summar", "summary"],
        "keywords_ja": ["生成", "作成", "文書", "資料", "報告", "レポート", "下書き", "要約", "作文"],
    },
    {
        "template_id": "SAMPLE-CHAT-01",
        "industry": "CMN",
        "pattern": "Chat",
        "description": "Sample entry: multi-turn conversational assistant.",
        "keywords": ["chat", "conversation", "assistant", "talk", "dialogue", "dialog", "support desk", "helpdesk"],
        "keywords_ja": ["会話", "対話", "チャット", "相談", "アシスタント", "窓口"],
    },
    {
        "template_id": "SAMPLE-FIN-01",
        "industry": "FIN",
        "pattern": "DocGeneration",
        "description": "Sample entry: financial report / disclosure generation.",
        "keywords": ["financial", "finance", "disclosure", "earnings", "bank", "loan"],
        "keywords_ja": ["金融", "財務", "決算", "開示", "銀行", "融資", "与信"],
    },
    {
        "template_id": "SAMPLE-RET-01",
        "industry": "RET",
        "pattern": "VectorRAG",
        "description": "Sample entry: retail demand-forecast Q&A over sales data.",
        "keywords": ["retail", "demand", "forecast", "inventory", "sales", "store"],
        "keywords_ja": ["小売", "需要", "予測", "在庫", "売上", "店舗", "販売"],
    },
    {
        "template_id": "SAMPLE-INS-01",
        "industry": "INS",
        "pattern": "VectorRAG",
        "description": "Sample entry: insurance compliance monitoring and audit.",
        "keywords": ["insurance", "compliance", "solicitation", "policy", "claim", "audit"],
        "keywords_ja": ["保険", "募集", "コンプライアンス", "約款", "保険金", "監査"],
    },
    {
        "template_id": "SAMPLE-HCR-01",
        "industry": "HCR",
        "pattern": "VectorRAG",
        "description": "Sample entry: healthcare clinical-guideline Q&A.",
        "keywords": ["healthcare", "clinical", "patient", "medical", "diagnosis", "guideline"],
        "keywords_ja": ["医療", "診療", "患者", "臨床", "診断", "ガイドライン"],
    },
    {
        "template_id": "SAMPLE-LOG-01",
        "industry": "LOG",
        "pattern": "VectorRAG",
        "description": "Sample entry: logistics shipment-status Q&A.",
        "keywords": ["logistics", "shipment", "delivery", "supply chain", "warehouse", "freight"],
        "keywords_ja": ["物流", "配送", "出荷", "輸送", "倉庫", "サプライチェーン"],
    },
    {
        "template_id": "SAMPLE-TEL-01",
        "industry": "TEL",
        "pattern": "VectorRAG",
        "description": "Sample entry: telecom service-plan and outage support.",
        "keywords": ["telecom", "network", "outage", "plan", "subscriber", "billing"],
        "keywords_ja": ["通信", "回線", "障害", "料金プラン", "契約者", "請求"],
    },
    {
        "template_id": "SAMPLE-EDU-01",
        "industry": "EDU",
        "pattern": "VectorRAG",
        "description": "Sample entry: education curriculum and policy Q&A.",
        "keywords": ["education", "curriculum", "student", "course", "school", "learning"],
        "keywords_ja": ["教育", "カリキュラム", "学生", "授業", "学校", "学習"],
    },
]

# Fast membership index (S-3 deterministic check).
_VALID_IDS = frozenset(e["template_id"] for e in _CATALOG)


def catalog_size() -> int:
    """Number of entries in the sample catalog."""
    return len(_CATALOG)


def is_valid_template_id(template_id: str) -> bool:
    """S-3 membership check: True iff template_id is a member of the catalog."""
    return template_id in _VALID_IDS


def retrieve_candidates(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Return up to top_k catalog entries ranked by keyword overlap with the query.

    Deterministic: score = count of keyword hits + industry/pattern token hits.
    Japanese triggers are matched against the original text, not the lowercased
    copy — casefolding is meaningless there and the request usually arrives in
    Japanese.

    An empty list means nothing matched. The caller reports that as no match;
    it must not be filled with arbitrary entries, which would read as a
    recommendation the catalog never supported.
    """
    q = query.lower()
    scored: list[dict[str, Any]] = []
    for e in _CATALOG:
        score = sum(1 for kw in e["keywords"] if kw in q)
        score += sum(1 for kw in e.get("keywords_ja", ()) if kw in query)
        if e["industry"].lower() in q:
            score += 1
        if e["pattern"].lower() in q:
            score += 1
        if score > 0:
            scored.append(
                {
                    "template_id": e["template_id"],
                    "industry": e["industry"],
                    "pattern": e["pattern"],
                    "description": e["description"],
                    "score": score,
                }
            )
    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored[:top_k]
