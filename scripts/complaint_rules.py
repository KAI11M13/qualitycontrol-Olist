"""评价文字 → 标签 的识别规则（葡语关键词正则）。

标签分两组（docs/00_术语与口径.md 4.2 节）：品质问题标签 5 类、履约服务标签 3 类。

设计原则
1. 先归一化：小写 + 去重音（não→nao）+ 压缩空白，规避拼写变体。
2. 多标签：一条评价可同时命中多个标签（flag 各自独立）。
3. 主标签：按 priority 从小到大取第一个命中的标签，用于需要互斥的结构统计。
   品质问题标签排在履约服务标签前面 —— 用户既说"晚到"又说"坏了"，品控口径先认"坏了"。
4. 品质客诉订单只认 1-3 星评价（4-5 星里的"sem defeito/没有瑕疵"等否定表述易误判），
   该过滤在 SQL 宽表层（04_dwd_qc_wide.sql）实现。
5. 规则需要持续迭代：每次调整后用标注样本复核标签精确率与标签召回率（见 docs/01_数据说明与清洗规则.md、scripts/14_tag_gold_eval.py）。
"""
import re
import unicodedata

# (tag_code, 标签名, 标签分组, priority, 正则)
RULES = [
    ("fake", "假货", "品质问题", 1,
     r"falsificad|nao (e|eh|era|sao|parece) (um |uma )?(produto )?original|nao original|nao e legitim"
     r"|replica|pirata|\bcopia\b(?! d[ao] (nota|nf))|nao e da marca|produto paralelo"),

    ("defect", "质量缺陷", "品质问题", 2,
     # 外观/物理损坏
     r"defeit|quebrad|quebrou|danificad|avariad|estragad|rasgad|trincad|rachad|riscad|amassad|furad[oa]s?\b"
     r"|manchad|descascou|descascando|enferruj|mofad|vazand|vazou|desfiou|desfiando|entortad|marca de queda"
     r"|descolou|desbotou|encolheu"
     # 功能故障
     r"|nao funciona|nao funcionou|parou de funcionar|deixou de funcionar|nao liga\b|nao ligou|nao carrega"
     r"|nao acende|funciona mal|apresentou (um )?problema|com problema|com falha|falhando"
     # 质量/做工差评
     r"|mal acabad|acabamento (ruim|pessimo|horrivel)|qualidade (ruim|pessima|baixa|inferior|horrivel|duvidosa)"
     r"|qualidade (deixou|deixa) a desejar|qualidade .{0,20}(muito )?(ruim|pessima|horrivel|inferior)"
     r"|pessima qualidade|baixa qualidade|ma qualidade|material (ruim|fraco|fragil|pessimo)|fragil"
     r"|fajut|vagabund|porcaria|nao presta|nao prestou|cheira (muito )?mal|mal cheiro|cheiro (ruim|forte|horrivel)"
     # 临期/过期
     r"|validade vencid|produto vencid|fora da validade|prazo de validade (vencid|curt|proxim)"
     r"|validade (para vencimento|curta|proxima)|perto de vencer|proximo do vencimento"),

    ("mismatch", "货不对板", "品质问题", 3,
     r"diferente d[aoe]s? (foto|imagem|anuncio|anunciad|pedid|descri|site|original|que (comprei|pedi|foi|esta|estava|mostra|eu))"
     r"|(veio|chegou|recebi|entregue|enviad[oa]|mandaram|e|era|produto|cor|modelo|tamanho|totalmente|completamente"
     r"|bem|muito|um|uma|outro|outra) diferente"
     r"|(?<!endereco )(?<!acho )(?<!achei )errad|nao (e|era) o (que|mesmo)|nao (condiz|corresponde|confere)(?! com a (entrega|data))"
     r"|outra cor|outro modelo|outra marca|(?<!por )(?<!o )outro produto|outro tamanho|veio outr|mandaram outr|enviaram outr"
     r"|(me )?(entregaram|recebi|entregue) (um |uma )?outr[oa]|entregue na cor|produto trocado|voltagem errada"
     r"|(achei|pensei) q(ue)? (fosse|era|seria|viria)"
     r"|ficou (muito )?(pequen|grande|apertad|curt)|(pequen[oa]|grande) demais|menor (do )?que|maior (do )?que"
     r"|muito pequen|muito grande|tamanho (errado|incorreto|menor|maior)|nao e compativel|incompativel|nao serve"
     r"|propaganda enganosa|anuncio enganoso|enganos|nao (e|esta|veio|chegou) conforme|nao e (igual|como) (a|na) foto"),

    ("missing", "少件漏发", "品质问题", 4,
     r"faltand|faltou(?! (clareza|informac|atencao|respeito|comunicac|cuidado|educacao|compromisso|profissionalismo|so\b))"
     r"|falta (de )?(uma|um|a|o|as|os|peca|pecas|item|itens|parte|acessorio|produto)\b"
     r"|so (recebi|veio|chegou|chegaram|entregaram) (um|uma|1|metade|parte)"
     r"|(so|apenas|somente) (veio|vieram|chegou|chegaram|recebi|entregaram) \d"
     r"|(apenas|somente) (um|uma|1|metade|parte)\b|(recebi|veio|chegou) (apenas|so|somente)"
     r"|(mandaram|enviaram|entregaram) (apenas|so|somente)|quantidade (errada|incorreta|menor)"
     r"|a quantidade (que|certa|comprada|adquirida)|(?<!nome )incomplet|(veio|chegou) sem(?! (a |o )?(respectiva )?(nota|nf))"
     r"|nao vieram|metade do pedido|parte do pedido|um dos (itens|produtos)|parcialmente|entrega parcial"
     r"|(o|a) (outr[oa]|segund[oa])( \w+)? (nao|ainda nao) (veio|chegou)|nao recebi (o|a) (outr[oa]|segund[oa]|restante)"
     r"|nada d[oa] (outr[oa]|segund[oa])\b"),

    ("package", "包装破损", "品质问题", 5,
     r"(embalagem|caixa|pacote)( \w+){0,3} (violad|danificad|rasgad|aberta|amassad|molhad|detonad|estourad)"
     r"|embalagem (ruim|pessima|horrivel|precaria|fraca|simples)|mal embalad|pessimamente embalad|sem embalagem"),

    ("not_received", "未收到货", "履约服务", 6,
     r"nao (recebi|recebemos|chegou|chegaram|foi entregue|foram entregues|entregaram|entregou"
     r"|veio\b(?! (quebrad|danificad|amassad|riscad|com |errad|faltand|diferente|do jeito|conforme|como)))"
     r"|ainda nao (recebi|chegou)|nunca (chegou|recebi)|nao (me )?entreg|nao me foi entregue|nao foi recebid|nao recebido"
     r"|(esperando|aguardando) (o |a |meu |minha )?(produto|pedido|entrega|mercadoria)|aguardando (ainda )?o recebimento"
     r"|(ainda aguardo|continuo aguardando|estou aguardando) (o |a |meu |minha )?(produto|pedido|entrega|mercadoria|chegada)"
     r"|nada de chegar|ate (agora|hoje|o momento) nada|sem previsao|\bcade\b|extraviad|devolvid[oa] ao remetente|sem receber"),

    ("delay", "物流延迟", "履约服务", 7,
     r"atras|demor|prazo|lent[oa]\b|muito tempo|chegou tarde|entrega tardia"),

    ("service", "服务售后", "履约服务", 8,
     r"atendimento|nao respond|sem resposta|nenhuma resposta|nao (tive|obtive|recebi) (retorno|resposta)"
     r"|sem retorno|nenhum retorno|nao consigo (falar|contato|contatar|resolver)|contato|\bsac\b"
     r"|reclame aqui|procon|reembols|estorno|dinheiro de volta|devolu|troca|cancel"),
]

# 物流延迟规则前先剔除"准时/提前"的正向表述，否则"chegou antes do prazo"会被误判为延迟
_POSITIVE_TIME = re.compile(
    r"(no|dentro do|antes do|bem antes do|conforme o|dentro) prazo|prazo de validade"
    r"|prazo (bom|otimo|curto|razoavel|excelente|rapido|certo)"
)
# 否定式的"无瑕疵"表述（sem defeito / nenhum problema / não veio quebrado），打标前剔除
_NEGATED_QUALITY = re.compile(
    r"(sem|nenhum|nenhuma|zero|nao (veio|chegou|tem|tinha|teve|apresentou|apresenta|estava|esta|foi))"
    r" (nenhum |nenhuma |qualquer |algum |nada )?(defeito|avaria|avariad[oa]|problema|dano|danificad[oa]|arranhao|risco|quebrad[oa])s?"
)

# "箱子/外包装 压扁、破了"属于包装问题，判定"质量缺陷"前剔除，避免重复计入
_PACKAGE_DAMAGE = re.compile(
    r"(embalagem|caixa|pacote)( \w+){0,3} (violad|danificad|rasgad|aberta|amassad|molhad|detonad|estourad)\w*"
)

_COMPILED = [(code, re.compile(pat)) for code, _, _, _, pat in RULES]
QUALITY_TAGS = [code for code, _, grp, _, _ in RULES if grp == "品质问题"]
TAG_NAME = {code: name for code, name, _, _, _ in RULES}


def normalize(text: str | None) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", str(text).lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip()


def tag_text(raw: str | None) -> dict:
    """返回 {tag_code: 0/1, ..., 'primary_tag': code 或 None}"""
    text = normalize(raw)
    out = {}
    for code, pat in _COMPILED:
        if code == "delay":
            target = _POSITIVE_TIME.sub(" ", text)
        elif code == "defect":
            target = _PACKAGE_DAMAGE.sub(" ", _NEGATED_QUALITY.sub(" ", text))
        elif code in QUALITY_TAGS:
            target = _NEGATED_QUALITY.sub(" ", text)
        else:
            target = text
        out[code] = 1 if (text and pat.search(target)) else 0
    out["primary_tag"] = next((code for code, _ in _COMPILED if out[code]), None)
    return out
