"""Gerador de títulos e comentários de avaliação em português.

O texto depende da nota e do contexto do pedido (atraso, entrega antecipada,
não entregue). Variações de escrita (sem acento, minúsculas, caixa alta, erro
de digitação, emoji) imitam o que clientes reais escrevem.
"""
import unicodedata

OPEN_POS = ["", "", "", "Adorei!", "Muito bom.", "Recomendo.", "Gostei muito.", "Excelente!", "Perfeito.",
            "Tudo certo.", "Show!", "Nota 10.", "Super recomendo!", "Amei!", "Maravilhoso."]
CORE_POS = [
    "Produto de ótima qualidade", "Chegou bem embalado", "Produto conforme o anúncio",
    "O produto é exatamente o que eu esperava", "Entrega rápida e produto bem embalado",
    "Ótimo custo-benefício", "Vendedor atencioso, respondeu rápido", "Material de qualidade, bem acabado",
    "Minha mãe adorou o presente", "Meu filho adorou", "Minha esposa amou", "Meu marido gostou muito",
    "Já é a segunda vez que compro e não me arrependo", "Recebi tudo certinho", "Funcionando perfeitamente",
    "Cor e tamanho conforme a descrição", "Produto muito bonito, igual à foto", "Bem melhor do que eu esperava",
    "Fácil de montar, veio com todas as peças", "Chegou tudo em perfeito estado", "Qualidade excelente pelo preço",
    "Produto original, lacrado", "Superou minhas expectativas", "Comprei para dar de presente e fiz bonito",
]
EARLY = ["Chegou {n} dias antes do prazo", "Entrega super rápida, chegou bem antes do previsto",
         "Chegou muito antes da data prevista", "Prazo de entrega excelente, chegou em poucos dias"]
CLOSE_POS = ["", "", "Recomendo a loja.", "Comprarei novamente.", "Parabéns ao vendedor.", "Obrigada!",
             "Obrigado!", "Voltarei a comprar.", "Super indico.", "Estou satisfeita.", "Estou satisfeito.",
             "Recomendo a todos."]
CAVEAT_4 = ["Só achei a embalagem um pouco simples", "A cor é um pouco diferente da foto", "Demorou um pouco mas chegou",
            "Poderia vir com manual em português", "O tamanho é um pouco menor do que eu imaginava",
            "Bom, mas esperava um pouco mais pelo preço", "A caixa chegou um pouco amassada, mas o produto está ok",
            "Só faltou a nota fiscal", "O acabamento poderia ser melhor"]
CORE_NEU = ["Produto ok, nada demais", "Atendeu parcialmente", "O produto é razoável pelo preço", "Qualidade mediana",
            "Chegou, mas a embalagem estava amassada", "Veio sem nota fiscal", "Esperava mais pela descrição",
            "O acabamento deixa a desejar", "Entrega demorou mais do que o esperado", "Produto bom, mas a entrega atrasou",
            "É bonito mas parece frágil", "Não é igual à foto do anúncio, mas serve", "Ainda estou testando"]
CORE_LATE = ["Até agora não recebi o produto", "O produto ainda não chegou e o prazo já passou",
             "Atrasou {n} dias e ninguém dá satisfação", "Comprei para presente e chegou atrasado",
             "Prazo de entrega não foi cumprido", "Já entrei em contato várias vezes e nada",
             "Chegou com {n} dias de atraso", "Rastreamento parado há dias", "Entrega atrasada, sem nenhuma explicação"]
CORE_NOT_DELIVERED = ["Não recebi o produto", "Até hoje não recebi", "Paguei e não recebi",
                      "O pedido nunca chegou", "Comprei e não chegou, quero meu dinheiro de volta",
                      "Pedido cancelado sem explicação", "Cancelaram minha compra sem avisar"]
CORE_NEG = ["Produto veio com defeito", "Veio faltando peças", "Recebi um produto diferente do que comprei",
            "Comprei 2 unidades e só chegou 1", "Produto de péssima qualidade, não recomendo", "Veio quebrado",
            "A cor não corresponde ao anúncio", "Material muito fraco, parece falsificado",
            "Solicitei a troca e até agora nada", "O tamanho não corresponde ao anunciado",
            "Parou de funcionar depois de uma semana", "Veio usado", "Não funciona"]
CLOSE_NEG = ["", "", "Não recomendo.", "Quero meu dinheiro de volta.", "Decepcionada.", "Decepcionado.",
             "Não compro mais nessa loja.", "Péssimo atendimento.", "Aguardo uma solução.", "Vou abrir reclamação.",
             "Lamentável."]
TITLES = {
    5: ["Recomendo", "Ótimo", "Super recomendo", "Excelente", "Muito bom", "Perfeito", "Adorei", "Nota 10", "Amei"],
    4: ["Bom", "Gostei", "Bom produto", "Recomendo", "Muito bom"],
    3: ["Razoável", "Regular", "Mais ou menos", "Ok", "Mediano"],
    2: ["Ruim", "Atrasou", "Não gostei", "Decepcionante"],
    1: ["Péssimo", "Não recebi", "Não recomendo", "Horrível", "Produto com defeito", "Decepcionante", "Atraso"],
}
MINIMAL = [".", "ok", "Ok", "Bom", "Ótimo", "...", "td certo", "Recomendo", "10"]
EMOJI_POS = [" 😍", " 👏👏", " ❤️", " 👍", " 🥰", " 😊"]
EMOJI_NEG = [" 😡", " 👎", " 😤", " 😞"]


def _strip_accents(s):
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


def _typo(s, rng):
    words = s.split(" ")
    cand = [i for i, w in enumerate(words) if len(w) > 4]
    if not cand:
        return s
    i = cand[rng.integers(len(cand))]
    w = words[i]
    j = rng.integers(1, len(w) - 2)
    words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:]
    return " ".join(words)


def _style(text, score, rng):
    r = rng.random()
    if r < 0.03:
        text = text.upper()
    elif r < 0.33:
        text = text.lower()
    if rng.random() < 0.38:
        text = _strip_accents(text)
    if rng.random() < 0.08:
        text = _typo(text, rng)
    if rng.random() < 0.10:
        text = text.replace(" muito ", " mto ").replace(" que ", " q ").replace(" você ", " vc ").replace(" porque ", " pq ")
    if rng.random() < 0.15:
        text = text.rstrip(".!")
    if score <= 2 and rng.random() < 0.08:
        text = text.rstrip(".") + "!!!"
    if rng.random() < 0.045:
        text += (EMOJI_POS if score >= 4 else EMOJI_NEG)[rng.integers(len(EMOJI_POS if score >= 4 else EMOJI_NEG))]
    return text.strip()


def _pick(lst, rng):
    return lst[rng.integers(len(lst))]


def make_comment(score, late_days, delivered, rng):
    """Retorna o texto do comentário. late_days > 0 = atraso; < 0 = antecipação."""
    if rng.random() < 0.03:
        return _pick(MINIMAL, rng)
    n = int(abs(late_days)) if late_days == late_days else 0
    parts = []
    if score >= 4:
        parts.append(_pick(OPEN_POS, rng))
        if late_days == late_days and late_days < -5 and rng.random() < 0.45:
            parts.append(_pick(EARLY, rng).format(n=n) + ".")
        parts.append(_pick(CORE_POS, rng) + ".")
        if score == 4 and rng.random() < 0.55:
            parts.append(_pick(CAVEAT_4, rng) + ".")
        elif rng.random() < 0.3:
            parts.append(_pick(CORE_POS, rng) + ".")
        parts.append(_pick(CLOSE_POS, rng))
    elif score == 3:
        parts.append(_pick(CORE_NEU, rng) + ".")
        if late_days == late_days and late_days > 0 and rng.random() < 0.5:
            parts.append(_pick(CORE_LATE, rng).format(n=max(n, 1)) + ".")
    else:
        if not delivered:
            parts.append(_pick(CORE_NOT_DELIVERED, rng) + ".")
        elif late_days == late_days and late_days > 0 and rng.random() < 0.75:
            parts.append(_pick(CORE_LATE, rng).format(n=max(n, 1)) + ".")
        else:
            parts.append(_pick(CORE_NEG, rng) + ".")
        if rng.random() < 0.35:
            parts.append(_pick(CORE_NEG if delivered else CORE_LATE, rng).format(n=max(n, 1)) + ".")
        parts.append(_pick(CLOSE_NEG, rng))
    text = " ".join(p for p in parts if p)
    return _style(text, score, rng)


def make_title(score, rng):
    t = _pick(TITLES[score], rng)
    r = rng.random()
    if r < 0.3:
        t = t.lower()
    if rng.random() < 0.35:
        t = _strip_accents(t)
    return t
