"""评价打标规则的单元测试：每条用例对应一个真实踩过的坑（见 docs/01 第 5 节、指标字典的口径变更记录）。"""
import pytest

from complaint_rules import QUALITY_TAGS, RULES, normalize, tag_text


def hits(text):
    t = tag_text(text)
    return {k for k, v in t.items() if k != "primary_tag" and v}


def test_normalize_lowercases_strips_accents_and_whitespace():
    assert normalize("  NÃO  Chegou\tAinda  ") == "nao chegou ainda"
    assert normalize(None) == ""
    assert normalize("") == ""


@pytest.mark.parametrize("text, expected", [
    ("Produto falsificado, não é original", {"fake"}),
    ("O produto veio com defeito", {"defect"}),
    ("Cor diferente da foto", {"mismatch"}),
    ("Recebi outro modelo", {"mismatch"}),
    ("Comprei 2 e só veio 1", {"missing"}),
    ("Faltou uma peça para montar", {"missing"}),
    ("Embalagem violada", {"package"}),
    ("Ainda não recebi o produto", {"not_received"}),
    ("A entrega atrasou muito", {"delay"}),
    ("Atendimento péssimo, ninguém responde", {"service"}),
])
def test_each_tag_fires_on_a_typical_complaint(text, expected):
    assert hits(text) == expected


@pytest.mark.parametrize("text, why", [
    ("Produto sem defeito, chegou antes do prazo", "否定式\"sem defeito\"不是缺陷；\"antes do prazo\"是提前送达"),
    ("Não veio quebrado, tudo certo", "\"não veio quebrado\"既不是缺陷也不是未收货"),
    ("A furadeira funciona muito bem", "\"furadeira（电钻）\"不能被 furad（破洞）命中"),
    ("Faltou clareza no anúncio", "\"faltou clareza\"是描述问题，不是少件"),
    ("Chegou antes do prazo, recomendo", "正向时效表述不算延迟"),
])
def test_known_false_positives_stay_fixed(text, why):
    assert hits(text) == set(), why


def test_package_damage_is_not_counted_as_product_defect():
    assert hits("A caixa veio amassada mas o produto está perfeito") == {"package"}


def test_shelf_life_is_a_defect_not_a_delay():
    assert hits("Prazo de validade curto") == {"defect"}


def test_multi_label_and_quality_first_primary_tag():
    t = tag_text("Veio quebrado e ainda atrasou")
    assert t["defect"] == 1 and t["delay"] == 1
    assert t["primary_tag"] == "defect"          # 品质问题标签优先于履约服务标签


def test_partial_delivery_is_missing_first():
    t = tag_text("Os dois potes vieram, mas o segundo ainda não chegou")
    assert t["missing"] == 1 and t["primary_tag"] == "missing"


@pytest.mark.parametrize("text", ["", None, "   "])
def test_empty_text_has_no_tags(text):
    t = tag_text(text)
    assert t["primary_tag"] is None
    assert all(t[code] == 0 for code, *_ in RULES)


def test_rule_table_is_consistent():
    codes = [r[0] for r in RULES]
    assert len(codes) == len(set(codes))
    assert sorted(r[3] for r in RULES) == list(range(1, len(RULES) + 1))   # 优先级唯一且连续
    assert QUALITY_TAGS == ["fake", "defect", "mismatch", "missing", "package"]


@pytest.mark.xfail(strict=True, reason="已知漏标：货不对板的口语化说法（标注样本中漏标的主要来源），计划在规则 v1.1 修复")
def test_known_recall_gap_mismatch_paraphrase():
    assert "mismatch" in hits("O que chegou não parece com o que comprei")
