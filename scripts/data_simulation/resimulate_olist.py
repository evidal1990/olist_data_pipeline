"""Ressimulação dos dados Olist (ADR-0003).

Lê os CSVs atuais, preserva datas e status dos ~99 mil pedidos do Olist
público (até ago/2018) e regera o resto com regras de negócio coerentes:
frete e prazo por distância, vendedores concentrados, recompra baixa,
parcelas por forma de pagamento, nota como consequência do atraso e
comentários em português. Planta sujeira rara e registra cada caso em
_gabarito/planted_issues.csv.

Uso:
    python scripts/data_simulation/resimulate_olist.py \
        --src ~/Downloads/output --out ~/Downloads/output_v2
"""
import argparse
import os
import shutil
import time

import numpy as np
import pandas as pd

import comments
from config import *  # noqa: F401,F403

DAY = 86400.0
T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ---------------------------------------------------------------------------
# utilitários
# ---------------------------------------------------------------------------
class IdFactory:
    def __init__(self, rng, taken):
        self.rng, self.taken = rng, set(taken)

    def make(self, n):
        out = []
        while len(out) < n:
            k = n - len(out)
            raw = self.rng.bytes(16 * k)
            for i in range(k):
                h = raw[i * 16:(i + 1) * 16].hex()
                if h not in self.taken:
                    self.taken.add(h)
                    out.append(h)
        return np.array(out, dtype=object)


def to_days(series):
    """string de data -> dias desde 1970 (float); vazio -> NaN."""
    dt = pd.to_datetime(series.replace("", None), errors="coerce")
    return (dt - pd.Timestamp("1970-01-01")).dt.total_seconds().to_numpy() / DAY


def fmt_ts(days, date_only=False, midnight=False):
    s = pd.Series(pd.to_datetime(np.round(np.asarray(days, dtype=float) * DAY), unit="s", errors="coerce"))
    if date_only:
        out = s.dt.strftime("%Y-%m-%d")
    elif midnight:
        out = s.dt.strftime("%Y-%m-%d 00:00:00")
    else:
        out = s.dt.strftime("%Y-%m-%d %H:%M:%S")
    return out.fillna("").to_numpy()


def ts_days(ts):
    return (pd.Timestamp(ts) - pd.Timestamp("1970-01-01")).total_seconds() / DAY


def haversine_km(lat1, lng1, lat2, lng2):
    r = np.pi / 180
    a = np.sin((lat2 - lat1) * r / 2) ** 2 + np.cos(lat1 * r) * np.cos(lat2 * r) * np.sin((lng2 - lng1) * r / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a))


def year_of(days):
    return pd.to_datetime(np.asarray(days) * DAY, unit="s").year.to_numpy()


def black_friday(y):
    d = pd.Timestamp(f"{y}-11-01")
    first_fri = d + pd.Timedelta(days=(4 - d.weekday()) % 7)
    return first_fri + pd.Timedelta(days=21)


class Gabarito:
    def __init__(self):
        self.rows = []

    def add(self, table, keys, issue, column, value, kind="plantada"):
        for k, v in zip(keys, value if isinstance(value, (list, np.ndarray, pd.Series)) else [value] * len(keys)):
            self.rows.append((table, k, issue, column, v, kind))

    def frame(self):
        return pd.DataFrame(self.rows, columns=["tabela", "chave", "problema", "coluna", "valor_plantado", "origem"])


# ---------------------------------------------------------------------------
# etapas
# ---------------------------------------------------------------------------
def load(src):
    read = lambda n: pd.read_csv(f"{src}/olist_{n}_dataset.csv", dtype=str, keep_default_na=False)
    t = {n: read(n) for n in ["customers", "sellers", "products", "orders", "order_items",
                              "order_payments", "order_reviews"]}
    geo = pd.read_csv(f"{src}/olist_geolocation_dataset_clean.csv", dtype={"geolocation_zip_code_prefix": str})
    t["geo_zip"] = geo.groupby("geolocation_zip_code_prefix")[["geolocation_lat", "geolocation_lng"]].mean()
    t["geo_state"] = geo.groupby("geolocation_state")[["geolocation_lat", "geolocation_lng"]].median()
    return t


def coords(zips, states, t):
    gz, gs = t["geo_zip"], t["geo_state"]
    lat = pd.Series(zips).map(gz.geolocation_lat).to_numpy()
    lng = pd.Series(zips).map(gz.geolocation_lng).to_numpy()
    miss = np.isnan(lat)
    lat[miss] = pd.Series(states[miss]).map(gs.geolocation_lat).to_numpy()
    lng[miss] = pd.Series(states[miss]).map(gs.geolocation_lng).to_numpy()
    return lat, lng


def build_timeline(rng, orig_orders):
    """Datas de compra do período simulado: tendência anual, sazonalidade, datas comerciais."""
    days = pd.date_range(SYNTH_START, DATA_CUTOFF.normalize(), freq="D")
    w = np.array([MONTH_FACTOR[d.month] * WEEKDAY_FACTOR[d.weekday()] for d in days])
    w *= 1 + 0.12 * (days.dayofyear.to_numpy() / 365)
    for i, d in enumerate(days):
        if d.year == 2020:
            w[i] *= 0.85 if d.month <= 2 else (0.95 if d.month == 3 else 1.12)
        if d.year == 2021 and d.month <= 6:
            w[i] *= 1.08
        if d.month == 12 and d.day >= 21:
            w[i] *= 0.6 if d.day not in (24, 25) else 0.35
        if d.month == 1 and d.day == 1:
            w[i] *= 0.4
        if d.month == 3 and d.day == 15:
            w[i] *= 1.5  # dia do consumidor
    for y in range(2018, 2026):
        bf = black_friday(y)
        boost = {-7: 1.3, -6: 1.3, -5: 1.3, -4: 1.4, -3: 1.5, -2: 1.7, -1: 2.0, 0: 5.0, 1: 2.2, 2: 1.8, 3: 2.0}
        for off, b in boost.items():
            idx = days.get_indexer([bf + pd.Timedelta(days=off)])[0]
            if idx >= 0:
                w[idx] *= b
        md = pd.Timestamp(f"{y}-05-01")
        mothers = md + pd.Timedelta(days=(6 - md.weekday()) % 7 + 7)
        for off in range(-8, 0):
            idx = days.get_indexer([mothers + pd.Timedelta(days=off)])[0]
            if idx >= 0:
                w[idx] *= 1.25
    counts = np.zeros(len(days), dtype=int)
    for y, target in YEARLY_ORDERS.items():
        m = days.year == y
        counts[m] = rng.multinomial(target, w[m] / w[m].sum())
    day_vals = (days - pd.Timestamp("1970-01-01")).total_seconds().to_numpy() / DAY
    base = np.repeat(day_vals, counts)
    # hora do dia com o perfil empírico dos pedidos originais
    hours = pd.to_datetime(orig_orders.order_purchase_timestamp).dt.hour.value_counts().sort_index()
    hour_p = hours.reindex(range(24), fill_value=0).to_numpy(float)
    hour_p /= hour_p.sum()
    h = rng.choice(24, size=len(base), p=hour_p)
    secs = h * 3600 + rng.integers(0, 3600, size=len(base))
    return np.sort(base + secs / DAY)


def assign_customers(rng, t, orders, ids):
    """Um customer_id por pedido; recompra via customer_unique_id."""
    cust = t["customers"].copy()
    rows = cust.set_index("customer_id")
    r_uid = rows.customer_unique_id.to_dict()
    r_loc = dict(zip(cust.customer_id, zip(cust.customer_zip_code_prefix, cust.customer_city, cust.customer_state)))
    order_ord = np.argsort(orders.purchase.to_numpy(), kind="stable")
    n = len(orders)
    is_orig = orders.is_orig.to_numpy()
    old_cid = orders.customer_id.to_numpy()
    years = orders.year.to_numpy()

    orig_cids = set(old_cid[is_orig])
    synth_cids = set(old_cid[~is_orig]) - orig_cids
    pool = [c for c in cust.customer_id if c in synth_cids]
    rng.shuffle(pool)

    # localização de clientes novos: amostra das linhas existentes, com deriva regional por ano
    loc = cust[["customer_zip_code_prefix", "customer_city", "customer_state"]].to_numpy()
    reg = cust.customer_state.map(REGION).to_numpy()
    loc_samples = {}
    for y in range(2016, 2026):
        wy = np.maximum(0.4, 1 + pd.Series(reg).map(REGION_CUSTOMER_DRIFT).to_numpy() * max(0, y - 2018))
        k = int((years == y).sum()) + 10
        loc_samples[y] = list(rng.choice(len(loc), size=k, p=wy / wy.sum()))

    fresh = list(ids.make(2 * n))  # ids novos para customer_id e customer_unique_id
    out_cid = np.empty(n, dtype=object)
    new_rows = []
    uid_fix = {}
    used_unique = {r_uid[c] for c in orig_cids}
    buyers = []  # (unique, zip, city, state)
    seen_orig = set()
    r_rep, r_pick, r_recent = rng.random(n), rng.random(n), rng.random(n)
    for i in order_ord:
        c = old_cid[i]
        if is_orig[i] and c not in seen_orig:
            seen_orig.add(c)
            out_cid[i] = c
            buyers.append((r_uid[c],) + r_loc[c])
            continue
        if buyers and r_rep[i] < REPEAT_RATE.get(years[i], 0.03):
            nb = len(buyers)
            j = int(r_pick[i] * nb) if r_recent[i] < 0.6 else nb - 1 - int(r_pick[i] * nb * 0.2)
            b = buyers[j]
            cid = fresh.pop()
            new_rows.append((cid,) + b)
            out_cid[i] = cid
            continue
        if not is_orig[i] and pool:
            pc = pool.pop()
            u = r_uid[pc]
            if u in used_unique:
                u = fresh.pop()
                uid_fix[pc] = u
            used_unique.add(u)
            out_cid[i] = pc
            buyers.append((u,) + r_loc[pc])
            continue
        z, ci, st = loc[loc_samples[years[i]].pop()]
        cid, u = fresh.pop(), fresh.pop()
        new_rows.append((cid, u, z, ci, st))
        out_cid[i] = cid
        buyers.append((u, z, ci, st))

    cust.loc[cust.customer_id.isin(uid_fix), "customer_unique_id"] = cust.customer_id.map(uid_fix)
    add = pd.DataFrame(new_rows, columns=["customer_id", "customer_unique_id", "customer_zip_code_prefix",
                                          "customer_city", "customer_state"])
    add["is_active"] = "0"
    cust = pd.concat([cust, add[cust.columns]], ignore_index=True)
    return out_cid, cust


def setup_sellers_products(rng, t, cat_share):
    s = t["sellers"].copy()
    p = t["products"].copy()
    ns = len(s)
    s["pop"] = rng.lognormal(0, SELLER_POP_SIGMA, ns)
    yrs = np.array(list(SELLER_START_YEAR))
    s["start"] = rng.choice(yrs, size=ns, p=np.array(list(SELLER_START_YEAR.values())) / sum(SELLER_START_YEAR.values()))
    churn = rng.random(ns) < SELLER_CHURN_RATE
    end = s.start + rng.integers(1, 6, ns)
    s["end"] = np.where(churn & (end <= 2025), end, 9999)
    # categorias por vendedor
    cats = np.array(cat_share.index)
    cp = cat_share.to_numpy() / cat_share.sum()
    seller_cats = [set([c]) for c in rng.choice(cats, size=ns, p=cp)]
    for k in range(ns):
        if rng.random() < 0.35:
            seller_cats[k].add(rng.choice(cats, p=cp))
        if rng.random() < 0.12:
            seller_cats[k].add(rng.choice(cats, p=cp))
    by_cat = {}
    for k, cs in enumerate(seller_cats):
        for c in cs:
            by_cat.setdefault(c, []).append(k)
    p["cat"] = p.product_category_name
    owner = np.empty(len(p), dtype=int)
    for c, idx in p.groupby("cat").indices.items():
        cand = np.array(by_cat.get(c) or rng.choice(ns, 5, replace=False))
        wp = s["pop"].to_numpy()[cand] ** 0.6
        owner[idx] = rng.choice(cand, size=len(idx), p=wp / wp.sum())
    p["owner"] = owner
    p["pw"] = s["pop"].to_numpy()[owner] * rng.lognormal(0, PRODUCT_POP_SIGMA, len(p))
    # preço base (R$ 2017)
    w = pd.to_numeric(p.product_weight_g, errors="coerce")
    wmed = w.groupby(p.cat).transform("median")
    wf = np.clip((w / wmed).fillna(1.0), 0.2, 5) ** 0.15
    med = p.cat.map(lambda c: CATEGORY_PRICE.get(c, DEFAULT_PRICE)[0]).to_numpy(float)
    sig = p.cat.map(lambda c: CATEGORY_PRICE.get(c, DEFAULT_PRICE)[1]).to_numpy(float)
    p["base_price"] = np.maximum(4.9, med * np.exp(rng.normal(0, 1, len(p)) * sig) * wf)
    L = pd.to_numeric(p.product_length_cm, errors="coerce")
    H = pd.to_numeric(p.product_height_cm, errors="coerce")
    W = pd.to_numeric(p.product_width_cm, errors="coerce")
    kg = (w / 1000).fillna(w.median() / 1000)
    vol = (L * H * W / 6000).fillna(0)
    p["bill_kg"] = np.maximum(kg, vol)
    return s, p


def sample_products(rng, items, p, s, cust_state_of_item):
    """Escolhe produto (e vendedor) por categoria, UF do cliente e ano."""
    sstate = s.seller_state.to_numpy()[p.owner.to_numpy()]
    sreg = pd.Series(sstate).map(REGION).to_numpy()
    sstart = s.start.to_numpy()[p.owner.to_numpy()]
    send = s.end.to_numpy()[p.owner.to_numpy()]
    pw = p.pw.to_numpy()
    cat_idx = p.groupby("cat").indices
    out = np.empty(len(items), dtype=int)
    keys = pd.DataFrame({"c": items.cat.to_numpy(), "st": cust_state_of_item, "y": items.year.to_numpy()})
    for (c, st, y), idx in keys.groupby(["c", "st", "y"]).indices.items():
        cand = cat_idx[c]
        act = (sstart[cand] <= y) & (send[cand] >= y)
        if act.sum() < 3:
            act = np.ones(len(cand), bool)
        cc = cand[act]
        aff = np.where(sstate[cc] == st, AFFINITY_SAME_STATE,
                       np.where(sreg[cc] == REGION[st], AFFINITY_SAME_REGION, 1.0))
        ww = pw[cc] * aff
        out[idx] = rng.choice(cc, size=len(idx), p=ww / ww.sum())
    return out


def main(src, out):
    rng = np.random.default_rng(SEED)
    gab = Gabarito()
    log("lendo CSVs")
    t = load(src)
    o = t["orders"]
    ids = IdFactory(rng, set(o.order_id) | set(t["customers"].customer_id) | set(t["customers"].customer_unique_id)
                    | set(t["order_reviews"].review_id))

    ts = o.order_purchase_timestamp
    is_orig = (ts.str.len() > 10) & (ts < str(ORIGINAL_END)) & ~ts.str.endswith("00:00:00")
    orig = o[is_orig].copy()
    log(f"pedidos originais preservados: {len(orig):,}")

    # --- linha do tempo e ids de pedidos -----------------------------------
    synth_days = build_timeline(rng, orig)
    old_synth = o.loc[~is_orig, ["order_id", "customer_id"]].to_numpy()
    n_syn = len(synth_days)
    n_new = n_syn - len(old_synth)
    if n_new < 0:
        raise SystemExit("YEARLY_ORDERS menor que os pedidos simulados existentes")
    slot = rng.permutation(n_syn)
    syn_oid = np.empty(n_syn, dtype=object)
    syn_cid = np.empty(n_syn, dtype=object)
    syn_oid[slot[:len(old_synth)]] = old_synth[:, 0]
    syn_cid[slot[:len(old_synth)]] = old_synth[:, 1]
    syn_oid[slot[len(old_synth):]] = ids.make(n_new)
    syn_cid[slot[len(old_synth):]] = "__none__"
    log(f"pedidos simulados: {n_syn:,} ({len(old_synth):,} ids existentes + {n_new:,} novos)")

    O = pd.DataFrame({
        "order_id": np.concatenate([orig.order_id.to_numpy(), syn_oid]),
        "customer_id": np.concatenate([orig.customer_id.to_numpy(), syn_cid]),
        "purchase": np.concatenate([to_days(orig.order_purchase_timestamp), synth_days]),
        "is_orig": np.r_[np.ones(len(orig), bool), np.zeros(n_syn, bool)],
    })
    O["year"] = year_of(O.purchase)
    for col in ["order_status", "order_approved_at", "order_delivered_carrier_date",
                "order_delivered_customer_date", "order_estimated_delivery_date"]:
        O[col] = np.concatenate([orig[col].to_numpy(), np.full(n_syn, "", dtype=object)])
    N = len(O)

    # --- clientes ----------------------------------------------------------
    log("clientes e recompra")
    O["customer_id"], customers = assign_customers(rng, t, O, ids)
    cinfo = customers.set_index("customer_id")
    O["cust_state"] = O.customer_id.map(cinfo.customer_state).to_numpy()
    O["cust_zip"] = O.customer_id.map(cinfo.customer_zip_code_prefix).to_numpy()
    O["cust_reg"] = O.cust_state.map(REGION).to_numpy()

    # --- vendedores e produtos --------------------------------------------
    log("vendedores e produtos")
    it_old = t["order_items"].merge(t["products"][["product_id", "product_category_name"]], how="left")
    cat_share = it_old.product_category_name.value_counts()
    sellers, products = setup_sellers_products(rng, t, cat_share)

    # --- itens -------------------------------------------------------------
    log("itens")
    kv = np.array(list(ITEMS_PER_ORDER))
    kp = np.array(list(ITEMS_PER_ORDER.values()))
    k = rng.choice(kv, size=N, p=kp / kp.sum())
    cats = np.array(cat_share.index)
    base_cp = cat_share.to_numpy(float)
    order_cat = np.empty(N, dtype=object)
    for y in np.unique(O.year):
        m = np.where(O.year.to_numpy() == y)[0]
        cp = base_cp * np.array([CATEGORY_DRIFT.get(c, {}).get(y, 1.0) for c in cats])
        order_cat[m] = rng.choice(cats, size=len(m), p=cp / cp.sum())

    oi = np.repeat(np.arange(N), k)
    seq = np.concatenate([np.arange(1, x + 1) for x in k]) if N else np.array([])
    I = pd.DataFrame({"oi": oi, "seq": seq})
    I["year"] = O.year.to_numpy()[oi]
    r = rng.random(len(I))
    I["kind"] = np.where(I.seq == 1, "first",
                         np.where(r < EXTRA_ITEM_SAME_PRODUCT, "same_product",
                                  np.where(r < EXTRA_ITEM_SAME_PRODUCT + EXTRA_ITEM_SAME_SELLER, "same_seller", "indep")))
    I["cat"] = order_cat[oi]
    indep = I.kind == "indep"
    I.loc[indep, "cat"] = rng.choice(cats, size=int(indep.sum()), p=base_cp / base_cp.sum())
    samp = I.kind.isin(["first", "indep"]).to_numpy()
    prod = np.full(len(I), -1)
    prod[samp] = sample_products(rng, I[samp], products, sellers, O.cust_state.to_numpy()[oi[samp]])
    # itens extras: mesmo produto / outro produto do mesmo vendedor
    first_pos = np.r_[0, np.cumsum(k)[:-1]]
    first_prod = prod[first_pos]
    sp = (I.kind == "same_product").to_numpy()
    prod[sp] = first_prod[oi[sp]]
    owner = products.owner.to_numpy()
    by_seller = products.groupby("owner").indices
    pw = products.pw.to_numpy()
    for j in np.where((I.kind == "same_seller").to_numpy())[0]:
        cand = by_seller[owner[first_prod[oi[j]]]]
        ww = pw[cand]
        prod[j] = cand[rng.choice(len(cand), p=ww / ww.sum())] if len(cand) > 1 else cand[0]
    I["prod"] = prod
    I["seller"] = owner[prod]

    # preço
    infl = pd.Series(INFLATION)
    yfac = I.year.map(infl).to_numpy()
    price = products.base_price.to_numpy()[prod] * yfac * np.exp(rng.normal(0, 0.035, len(I)))
    pdays = O.purchase.to_numpy()[oi]
    bf_week = np.zeros(len(I), bool)
    for y in range(2016, 2026):
        b = ts_days(black_friday(y))
        bf_week |= (pdays >= b - 3) & (pdays < b + 4)
    price = np.where(bf_week & (rng.random(len(I)) < 0.35), price * rng.uniform(0.75, 0.92, len(I)), price)
    psych = rng.random(len(I))
    cents = np.select([psych < 0.35, psych < 0.6, psych < 0.68], [0.90, 0.99, 0.50], np.round(price % 1, 2))
    price = np.maximum(2.99, np.floor(price) + cents)
    # mesmo produto no mesmo pedido = mesmo preço
    price[sp] = price[first_pos[oi[sp]]]

    # frete
    log("frete por distância")
    s_zip = sellers.seller_zip_code_prefix.to_numpy()[I.seller]
    s_st = sellers.seller_state.to_numpy()[I.seller]
    slat, slng = coords(s_zip, s_st, t)
    c_zip = O.cust_zip.to_numpy()[oi]
    c_st = O.cust_state.to_numpy()[oi]
    clat, clng = coords(c_zip, c_st, t)
    km = np.maximum(5, haversine_km(slat, slng, clat, clng) * FREIGHT["road_factor"])
    kg = products.bill_kg.to_numpy()[prod]
    f = FREIGHT
    freight = (f["base"] + f["per_km"] * km + kg * (f["per_kg"] + f["per_kg_km"] * km))
    freight *= pd.Series(c_st).map(REGION).map(FREIGHT_REMOTE).to_numpy() * yfac
    freight *= np.exp(rng.normal(0, f["noise_sigma"], len(I)))
    dup_seller = pd.DataFrame({"oi": oi, "s": I.seller}).duplicated().to_numpy()
    freight = np.where(dup_seller, freight * f["combined_item_factor"], freight)
    freight = np.where(rng.random(len(I)) < f["free_shipping_rate"], 0.0, freight)
    I["price"] = np.round(price, 2)
    I["freight"] = np.round(freight, 2)
    I["km"] = km

    # --- pagamentos (forma principal decide a aprovação) --------------------
    log("pagamentos")
    tot = pd.Series(I.price + I.freight).groupby(oi).sum().reindex(range(N)).to_numpy()
    mix_types = np.array(["credit_card", "boleto", "debit_card", "voucher"])
    main_type = np.empty(N, dtype=object)
    for y in np.unique(O.year):
        m = np.where(O.year.to_numpy() == y)[0]
        pm = np.array(PAYMENT_MIX.get(y, PAYMENT_MIX[2018]))
        main_type[m] = rng.choice(mix_types, size=len(m), p=pm / pm.sum())
    pay_rows = []
    inst_vals = np.array(list(INSTALLMENT_BASE_WEIGHTS))
    inst_w = np.array(list(INSTALLMENT_BASE_WEIGHTS.values()))

    def installments(v):
        ok = inst_vals <= max(1, v / MIN_INSTALLMENT_VALUE)
        ww = inst_w * ok * np.where(inst_vals > 1, min(1.0, v / 120) ** 0.6, 1)
        return int(rng.choice(inst_vals, p=ww / ww.sum()))

    oid = O.order_id.to_numpy()
    rc = rng.random(N)
    for i in range(N):
        total = round(float(tot[i]), 2)
        mt = main_type[i]
        parts = []
        if mt != "voucher" and rc[i] < VOUCHER_COMBO_RATE and total > 25:
            nv = 1 + int(rng.random() < 0.25) + int(rng.random() < 0.08)
            for _ in range(nv):
                v = float(rng.choice([10, 15, 20, 25, 30, 50])) if rng.random() < 0.6 else round(total * rng.uniform(0.05, 0.3), 2)
                if sum(x[1] for x in parts) + v < total - 5:
                    parts.append(["voucher", v])
        if mt == "credit_card" and VOUCHER_COMBO_RATE <= rc[i] < VOUCHER_COMBO_RATE + TWO_CARDS_RATE and total > 60:
            v = round(total * rng.uniform(0.2, 0.6), 2)
            parts.append(["credit_card", v])
        if mt == "voucher" and total > 40 and rng.random() < 0.35:
            v = round(total * rng.uniform(0.3, 0.7), 2)
            parts.append(["voucher", v])
        rest = round(total - sum(x[1] for x in parts), 2)
        parts.append([mt, rest])
        if rng.random() < 0.5:
            parts = parts[::-1]
        for sq, (pt, v) in enumerate(parts, 1):
            inst = installments(v) if pt == "credit_card" else 1
            pay_rows.append((oid[i], sq, pt, inst, round(v, 2)))
    P = pd.DataFrame(pay_rows, columns=["order_id", "payment_sequential", "payment_type", "payment_installments",
                                        "payment_value"])
    P["payment_installments"] = P.payment_installments.astype(object)

    # --- datas e status (só simulados) -------------------------------------
    log("datas e status")
    order_km = pd.Series(km).groupby(oi).max().reindex(range(N)).to_numpy()
    first_seller = I.seller.to_numpy()[first_pos]
    seller_handling = rng.lognormal(np.log(1.8), 0.4, len(sellers))
    syn = ~O.is_orig.to_numpy()
    pur = O.purchase.to_numpy()
    n = N
    reg = O.cust_reg.to_numpy()
    approve = np.where(main_type == "boleto", rng.uniform(0.6, 3.2, n),
                       np.where(rng.random(n) < 0.06, rng.lognormal(np.log(10 / 24), 0.6, n),
                                rng.lognormal(np.log(12 / 1440), 1.2, n)))
    approved = pur + approve
    doy = pd.to_datetime(pur * DAY, unit="s")
    peak = ((doy.month == 11) & (doy.day >= 15)) | (doy.month == 12)
    handling = seller_handling[first_seller] * np.where(peak, 1.3, 1.0) * rng.lognormal(0, 0.5, n)
    carrier = approved + handling
    wd = pd.to_datetime(carrier * DAY, unit="s").weekday.to_numpy()
    carrier = carrier + np.where(wd == 6, 1, 0)
    reg_f = pd.Series(reg).map(TRANSIT_REGION).to_numpy()
    exp_transit = (1.5 + order_km / 380) * reg_f
    shock = np.ones(n)
    pur_dt = pd.to_datetime(pur * DAY, unit="s")
    for sh in LOGISTIC_SHOCKS:
        a, b, mult = pd.Timestamp(sh[0]), pd.Timestamp(sh[1]), sh[2]
        m = (pur_dt >= a) & (pur_dt <= b)
        if len(sh) > 3:
            m &= O.cust_state.to_numpy() == sh[3]
        shock = np.where(m, np.maximum(shock, mult), shock)
    shock *= np.where(peak, PEAK_SEASON_TRANSIT, 1.0)
    sigma = np.where(np.isin(reg, ["N", "NE"]), 0.45, 0.35)
    transit = exp_transit * shock * rng.lognormal(0, sigma, n)
    transit += np.where(rng.random(n) < 0.03, rng.uniform(4, 20, n), 0)
    delivered = carrier + transit
    delivered = np.floor(delivered) + rng.uniform(8 / 24, 20 / 24, n)
    delivered = np.maximum(delivered, carrier + 0.1)
    prom_mult = pd.Series(reg).map({"N": 1.12, "NE": 1.15, "CO": 1.25, "SE": 1.4, "S": 1.35}).to_numpy()
    promise = np.ceil(2.5 + 2.0 + exp_transit * prom_mult + 5 + rng.integers(0, 5, n))
    estimated = np.floor(pur) + promise

    status = np.full(n, "delivered", dtype=object)
    ra = rng.random(n)
    canc = ra < CANCELED_RATE
    unav = (ra >= CANCELED_RATE) & (ra < CANCELED_RATE + UNAVAILABLE_RATE)
    lost = (ra >= CANCELED_RATE + UNAVAILABLE_RATE) & (ra < CANCELED_RATE + UNAVAILABLE_RATE + LOST_IN_TRANSIT_RATE)
    cut = ts_days(DATA_CUTOFF)
    A, C, D = approved.copy(), carrier.copy(), delivered.copy()
    rb = rng.random(n)
    unpaid = canc & (main_type == "boleto") & (rb < 0.6)
    A[unpaid] = np.nan
    pre_ship = canc & ~unpaid & (rb < 0.75)
    C[unpaid | pre_ship | unav] = np.nan
    D[canc | unav | lost] = np.nan
    status[canc] = "canceled"
    status[unav] = "unavailable"
    status[lost] = "shipped"
    # corte de dados: eventos depois do corte não aconteceram ainda
    D[D > cut] = np.nan
    C[C > cut] = np.nan
    A[A > cut] = np.nan
    normal = ~(canc | unav)
    st_mask = normal & np.isnan(D)
    status[st_mask & ~np.isnan(C)] = "shipped"
    noc = st_mask & np.isnan(C) & ~np.isnan(A)
    status[noc & (cut - A < 1)] = "approved"
    status[noc & (cut - A >= 1)] = np.where(rng.random(int((noc & (cut - A >= 1)).sum())) < 0.5, "invoiced", "processing")
    status[st_mask & np.isnan(A)] = "created"
    # aplica só aos simulados
    O.loc[syn, "order_status"] = status[syn]
    O.loc[syn, "order_approved_at"] = fmt_ts(A[syn])
    O.loc[syn, "order_delivered_carrier_date"] = fmt_ts(C[syn])
    O.loc[syn, "order_delivered_customer_date"] = fmt_ts(D[syn])
    O.loc[syn, "order_estimated_delivery_date"] = fmt_ts(estimated[syn], midnight=True)

    # datas efetivas (originais + simulados) para avaliação e itens
    A_all = to_days(O.order_approved_at)
    D_all = to_days(O.order_delivered_customer_date)
    E_all = to_days(O.order_estimated_delivery_date)
    st_all = O.order_status.to_numpy()

    # shipping_limit_date: aprovação (ou compra) + SLA do vendedor
    base_ship = np.where(np.isnan(A_all), pur, A_all)
    ship_limit = base_ship[oi] + rng.integers(3, 7, len(I)) + (base_ship[oi] % 1) * 0
    I["shipping_limit_date"] = fmt_ts(ship_limit)

    # --- avaliações --------------------------------------------------------
    log("avaliações")
    survey = np.where(~np.isnan(D_all), np.floor(D_all) + 1, np.floor(E_all) + 1)
    survey = np.where(np.isnan(survey), np.floor(pur) + 30, survey)
    in_flight = np.isin(st_all, ["created", "approved", "processing", "invoiced"]) & (survey > cut - 15)
    eligible = (survey <= np.floor(cut)) & ~in_flight
    old_rev = t["order_reviews"].drop_duplicates("order_id").set_index("order_id").review_id
    rev_id = O.order_id.map(old_rev).to_numpy()
    has_old = pd.notna(rev_id)
    take = eligible & (has_old | (rng.random(n) < REVIEW_COVERAGE))
    missing = take & ~has_old
    rev_id[missing] = ids.make(int(missing.sum()))
    delivered_flag = ~np.isnan(D_all) & (st_all == "delivered")
    late = D_all - (E_all + 1)  # entregue depois do fim do dia prometido
    seller_eff = rng.normal(0, 0.45, len(sellers))
    cat_eff = pd.Series(order_cat).map(CATEGORY_SCORE_EFFECT).fillna(0).to_numpy()
    late_pos = np.clip(np.nan_to_num(late, nan=0), 0, 30)
    lat = (seller_eff[first_seller] + cat_eff
           + np.where(np.nan_to_num(late, nan=0) < -7, 0.2, 0)
           - 0.55 * late_pos ** 0.7 - 1.3 * (late_pos > 0)
           - 3.5 * ~delivered_flag
           + rng.logistic(0, 0.85, n))
    thr = np.quantile(lat[take], np.cumsum([SCORE_TARGET[s] for s in (1, 2, 3, 4)]))
    score = 1 + (lat[:, None] > thr[None, :]).sum(1)
    R = pd.DataFrame({"review_id": rev_id[take], "order_id": oid[take], "review_score": score[take],
                      "creation": survey[take], "late": late[take], "deliv": delivered_flag[take]})
    hrs = rng.lognormal(np.log(np.where(R.review_score <= 2, 22, 34)), 0.9)
    R["answer"] = R.creation + np.minimum(hrs, 24 * 40) / 24
    # duplicadas (sujeira)
    nd = int(len(R) * DIRT["duplicate_review"])
    dup = R.sample(nd, random_state=SEED).copy()
    dup["review_id"] = ids.make(nd)
    dup["creation"] = dup.creation + rng.integers(1, 11, nd)
    dup["answer"] = dup.creation + rng.lognormal(np.log(30), 0.9, nd) / 24
    dup["review_score"] = np.clip(dup.review_score + rng.choice([-1, 0, 0, 1], nd), 1, 5)
    gab.add("order_reviews", dup.order_id.to_numpy(), "avaliacao_duplicada_mesmo_pedido", "order_id",
            dup.review_id.to_numpy())
    R = pd.concat([R, dup], ignore_index=True)
    titles, msgs = [], []
    cr = rng.random(len(R))
    tr = rng.random(len(R))
    for sc, lt, dv, a, b in zip(R.review_score, R.late, R.deliv, cr, tr):
        msgs.append(comments.make_comment(int(sc), lt, dv, rng) if a < COMMENT_RATE[sc] else "")
        titles.append(comments.make_title(int(sc), rng) if b < TITLE_RATE[sc] else "")
    R["review_comment_title"] = titles
    R["review_comment_message"] = msgs
    R["review_creation_date"] = fmt_ts(R.creation, date_only=True)
    R["review_answer_timestamp"] = fmt_ts(R.answer)

    # --- sujeira plantada ----------------------------------------------------
    log("sujeira plantada")
    # parcelas 0 / vazias em cartão
    cc_rows = P.index[(P.payment_type == "credit_card") & P.order_id.isin(oid[syn])].to_numpy()
    pick = rng.choice(cc_rows, DIRT["installments_zero"] + DIRT["installments_empty"], replace=False)
    z, e = pick[:DIRT["installments_zero"]], pick[DIRT["installments_zero"]:]
    P.loc[z, "payment_installments"] = 0
    P.loc[e, "payment_installments"] = ""
    gab.add("order_payments", (P.loc[z, "order_id"] + "#" + P.loc[z, "payment_sequential"].astype(str)).to_numpy(),
            "parcela_zero", "payment_installments", 0)
    gab.add("order_payments", (P.loc[e, "order_id"] + "#" + P.loc[e, "payment_sequential"].astype(str)).to_numpy(),
            "parcela_vazia", "payment_installments", "")
    # diferença de centavos e voucher excedente
    syn_oids = oid[syn]
    nc = int(n * DIRT["payment_cents_diff"])
    cents_o = rng.choice(syn_oids, nc, replace=False)
    last_row = P[P.order_id.isin(cents_o)].groupby("order_id").tail(1).index
    delta = np.round(rng.choice([-1, 1], len(last_row)) * rng.integers(1, 10, len(last_row)) / 100, 2)
    P.loc[last_row, "payment_value"] = np.round(P.loc[last_row, "payment_value"] + delta, 2)
    gab.add("order_payments", P.loc[last_row, "order_id"].to_numpy(), "pagamento_difere_itens_centavos",
            "payment_value", delta)
    nvx = int(n * DIRT["payment_voucher_excess"])
    vx = rng.choice(np.setdiff1d(syn_oids, cents_o), nvx, replace=False)
    maxseq = P.groupby("order_id").payment_sequential.max()
    vrows = pd.DataFrame({"order_id": vx, "payment_sequential": maxseq.reindex(vx).to_numpy() + 1,
                          "payment_type": "voucher", "payment_installments": 1,
                          "payment_value": rng.choice([5.0, 10.0, 15.0, 20.0], nvx)})
    P = pd.concat([P, vrows], ignore_index=True)
    gab.add("order_payments", vx, "voucher_excedente_pagamento_maior_que_itens", "payment_value",
            vrows.payment_value.to_numpy())
    # datas
    ofr = O.order_id.to_numpy()
    deliv_syn = np.where(syn & (O.order_status.to_numpy() == "delivered") & (O.order_delivered_customer_date != "").to_numpy())[0]
    k1 = rng.choice(deliv_syn, int(len(deliv_syn) * DIRT["carrier_before_approved"]), replace=False)
    newc = A_all[k1] - rng.uniform(1 / 24, 40 / 24, len(k1))
    O.loc[k1, "order_delivered_carrier_date"] = fmt_ts(newc)
    gab.add("orders", ofr[k1], "coleta_antes_da_aprovacao", "order_delivered_carrier_date", fmt_ts(newc))
    rest = np.setdiff1d(deliv_syn, k1)
    k2 = rng.choice(rest, max(1, int(len(deliv_syn) * DIRT["delivered_without_date"])), replace=False)
    O.loc[k2, "order_delivered_customer_date"] = ""
    gab.add("orders", ofr[k2], "entregue_sem_data_de_entrega", "order_delivered_customer_date", "")
    canc_syn = np.where(syn & (O.order_status.to_numpy() == "canceled") & ~np.isnan(A_all))[0]
    k3 = rng.choice(canc_syn, min(len(canc_syn), max(1, int(n * DIRT["canceled_with_delivery"]))), replace=False)
    cdt = A_all[k3] + rng.uniform(1, 3, len(k3))
    ddt = cdt + rng.uniform(2, 10, len(k3))
    O.loc[k3, "order_delivered_carrier_date"] = fmt_ts(cdt)
    O.loc[k3, "order_delivered_customer_date"] = fmt_ts(ddt)
    gab.add("orders", ofr[k3], "cancelado_com_data_de_entrega", "order_delivered_customer_date", fmt_ts(ddt))
    # produtos com peso 0
    pz = rng.choice(len(products), int(len(products) * DIRT["product_zero_weight"]), replace=False)
    products.iloc[pz, products.columns.get_loc("product_weight_g")] = "0.0"
    gab.add("products", products.product_id.to_numpy()[pz], "peso_zero", "product_weight_g", "0.0")
    # cidades com grafia variante
    accents = {"sao ": "são ", "joao": "joão", "jose": "josé", "goiania": "goiânia", "brasilia": "brasília",
               "belem": "belém", "florianopolis": "florianópolis", "maringa": "maringá", "ribeirao": "ribeirão",
               "uberlandia": "uberlândia", "niteroi": "niterói", "vitoria": "vitória", "parana": "paraná"}
    abbrev = {"sao paulo": "sp", "rio de janeiro": "rj", "belo horizonte": "bh", "porto alegre": "poa",
              "sao bernardo do campo": "sbc", "campinas": "campinas sp"}

    def variant(city, st):
        r = rng.random()
        if r < 0.6:  # normalizável pela staging (caixa, acento, espaços)
            rr = rng.random()
            if rr < 0.35:
                v = next((city.replace(a, b) for a, b in accents.items() if a in city), city.title())
            elif rr < 0.65:
                v = city.upper()
            elif rr < 0.85:
                v = " " + city.replace(" ", "  ") + " "
            else:
                v = city.title()
            return v, "cidade_grafia_normalizavel"
        if city in abbrev and rng.random() < 0.6:
            return abbrev[city], "cidade_invalida_abreviacao"
        if rng.random() < 0.4:
            return f"{city}, {st.lower()}", "cidade_invalida_com_uf"
        w = list(city)
        if len(w) > 4:
            j = rng.integers(1, len(w) - 2)
            w[j], w[j + 1] = w[j + 1], w[j]
        return "".join(w), "cidade_invalida_erro_digitacao"

    for tbl, df, kcol, ccol, scol in [("customers", customers, "customer_id", "customer_city", "customer_state"),
                                      ("sellers", sellers, "seller_id", "seller_city", "seller_state")]:
        idx = rng.choice(len(df), int(len(df) * DIRT["city_variant"]), replace=False)
        # edita uma cópia numpy e grava uma vez só: df.iat célula a célula copiava o frame inteiro
        city_arr = df[ccol].to_numpy(dtype=object, copy=True)
        st_arr, key_arr = df[scol].to_numpy(), df[kcol].to_numpy()
        for ii in idx:
            v, kind = variant(city_arr[ii], st_arr[ii])
            if v == city_arr[ii]:
                continue
            city_arr[ii] = v
            gab.add(tbl, [key_arr[ii]], kind, ccol, [v])
        df[ccol] = city_arr
    # pré-existente: CEP sem coordenada (não plantado; registrado para conferência)
    gz = set(t["geo_zip"].index)
    for tbl, df, kcol, zcol in [("customers", customers, "customer_id", "customer_zip_code_prefix"),
                                ("sellers", sellers, "seller_id", "seller_zip_code_prefix")]:
        m = ~df[zcol].isin(gz)
        gab.add(tbl, df.loc[m, kcol].to_numpy(), "cep_sem_geolocalizacao", zcol, df.loc[m, zcol].to_numpy(),
                kind="pre-existente")

    # --- is_active: comprou nos últimos 12 meses ---------------------------
    last = pd.Series(pur).groupby(O.customer_id.map(cinfo.customer_unique_id).to_numpy()).max()
    has_order = customers.customer_id.isin(set(O.customer_id))
    lu = customers.customer_unique_id.map(last)
    customers.loc[has_order, "is_active"] = np.where(lu[has_order] >= cut - 365, "1", "0")

    # --- escrita -------------------------------------------------------------
    log("gravando CSVs")
    os.makedirs(out, exist_ok=True)
    os.makedirs(f"{out}/_gabarito", exist_ok=True)
    O_out = O.copy()
    O_out["order_purchase_timestamp"] = np.where(O.is_orig, orig_ts := np.concatenate(
        [orig.order_purchase_timestamp.to_numpy(), np.full(n_syn, "", dtype=object)]), fmt_ts(pur))
    O_out = O_out.sort_values("purchase")
    O_out[["order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at",
           "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"]
          ].to_csv(f"{out}/olist_orders_dataset.csv", index=False)
    items_out = pd.DataFrame({
        "order_id": oid[oi], "order_item_id": I.seq.to_numpy(),
        "product_id": products.product_id.to_numpy()[I["prod"].to_numpy()], "seller_id": sellers.seller_id.to_numpy()[I.seller],
        "shipping_limit_date": I.shipping_limit_date, "price": I.price, "freight_value": I.freight})
    items_out.to_csv(f"{out}/olist_order_items_dataset.csv", index=False)
    P.to_csv(f"{out}/olist_order_payments_dataset.csv", index=False)
    R[["review_id", "order_id", "review_score", "review_comment_title", "review_comment_message",
       "review_creation_date", "review_answer_timestamp"]].to_csv(f"{out}/olist_order_reviews_dataset.csv", index=False)
    customers[t["customers"].columns].to_csv(f"{out}/olist_customers_dataset.csv", index=False)
    sellers[t["sellers"].columns].to_csv(f"{out}/olist_sellers_dataset.csv", index=False)
    products[t["products"].columns].to_csv(f"{out}/olist_products_dataset.csv", index=False)
    for g in ["olist_geolocation_dataset.csv", "olist_geolocation_dataset_clean.csv"]:
        shutil.copy(f"{src}/{g}", f"{out}/{g}")
    gab.frame().to_csv(f"{out}/_gabarito/planted_issues.csv", index=False)
    log("fim")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.expanduser("~/Downloads/output"))
    ap.add_argument("--out", default=os.path.expanduser("~/Downloads/output_v2"))
    a = ap.parse_args()
    main(a.src, a.out)
