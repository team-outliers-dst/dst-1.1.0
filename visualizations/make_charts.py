"""Release Day Radar charts. Usage: python make_charts.py <dst-1.1.0-main dir>"""
import sys, re, unicodedata
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------- PATH CONFIGURATION ----------
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
C = ROOT / "data" / "cleaned"
VDATA = C / "vis_data"
OUT = HERE / "visuals"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
                     "figure.dpi": 100})
LANGC = {"Hindi": "#1f4e79", "Tamil": "#c0392b", "Malayalam": "#2e8b57", "Kannada": "#d98c00"}
SHORT = {"Lokah: Chapter 1 – Chandra": "Lokah", "L2: Empuraan": "L2 Empuraan"}
def sn(x): return SHORT.get(x, x)
def save(fig, name): fig.savefig(OUT / name, dpi=160, bbox_inches="tight", facecolor="white"); plt.close(fig)
def mm(s): s = pd.Series(s, dtype=float); return (s - s.min()) / (s.max() - s.min())

# ---------- load ----------
eng = pd.read_csv(C / "movie_engagement.csv")
eng["movie_name"] = eng["movie_name"].where(eng["movie_name"].notna(), None)
master = pd.read_csv(ROOT / "data/raw/movie_master.csv").dropna(subset=["movie_id"])
eng = eng.drop(columns=["movie_name"]).merge(master[["movie_id", "movie_name", "release_date"]], on="movie_id")
eng["release_date"] = pd.to_datetime(eng["release_date"])
eng["short"] = eng["movie_name"].map(sn)
bo = pd.read_csv(VDATA / "box_office.csv")[["movie_id", "first3_days_india_cr", "basis"]]
com = pd.read_csv(C / "analysed_comments.csv", parse_dates=["published_at"])
raw = pd.read_csv(C / "cleaned_comments.csv")
com = com.merge(master[["movie_id", "release_date"]], on="movie_id")
com["release_date"] = pd.to_datetime(com["release_date"]).dt.tz_localize("UTC")
peaks = pd.read_csv(C / "google_trends/monthly_search_interest_peaks.csv")
ts = pd.read_csv(C / "google_trends/combined_time_series_long.csv", parse_dates=["Time"])
# Trends names differ from master names -> match on a cleaned key
key = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
alias = {key("Lokah Chapter 1: Chandra"): key("Lokah: Chapter 1 – Chandra")}
for d, col in ((peaks, "movie_name"), (ts, "movie_name")):
    d["k"] = d[col].map(lambda s: alias.get(key(s), key(s)))
eng["k"] = eng["movie_name"].map(key)
eng = eng.merge(peaks[["k", "peak_search_interest"]], on="k", how="left").merge(bo, on="movie_id")

sent = com.groupby("movie_id")["sentiment"].value_counts(normalize=True).unstack().fillna(0)
sent["net"] = sent["positive"] - sent["negative"]
eng = eng.merge(sent.add_prefix("s_"), left_on="movie_id", right_index=True)
eng["log_vpd"] = np.log10(eng["views_per_day"])
eng["log_bo"] = np.log10(eng["first3_days_india_cr"])
# Buzz index: mean of three min-max components (our own, simple, documented)
eng["c_views"], eng["c_trends"], eng["c_sent"] = mm(eng.log_vpd), mm(eng.peak_search_interest), mm(eng.s_net)
eng["buzz"] = eng[["c_views", "c_trends", "c_sent"]].mean(axis=1)
eng = eng.sort_values("movie_id").reset_index(drop=True)
col = eng["language"].map(LANGC)
eng.to_csv(OUT / "chart_inputs_per_film.csv", index=False)
res = {}

def langlegend(ax, loc="upper left"):
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color=c, label=l) for l, c in LANGC.items()],
              frameon=False, loc=loc, fontsize=9)

# ---------- 1. buzz vs box office ----------
rho, p = spearmanr(eng.buzz, eng.first3_days_india_cr); res["rho_buzz_bo"] = (rho, p)
fig, ax = plt.subplots(figsize=(7.5, 5))
for _, r in eng.iterrows():
    hollow = r.basis != "net"
    ax.scatter(r.buzz, r.first3_days_india_cr, s=110, facecolors="white" if hollow else LANGC[r.language],
               edgecolors=LANGC[r.language], linewidths=2, zorder=3)
    ax.annotate(r.short, (r.buzz, r.first3_days_india_cr), xytext=(7, 5), textcoords="offset points", fontsize=9)
ax.set_yscale("log"); ax.set_xlabel("Buzz index (0-1: trailer views/day, Google Trends peak, comment sentiment)")
ax.set_ylabel("India box office, first 3 days (₹ Cr, log)")
ax.set_title(f"The all-in buzz index did not predict opening size (rank corr. {rho:.2f}, n=8)", loc="left")
langlegend(ax, "lower right"); ax.text(0.01, 0.01, "Box office: Sacnilk India net, first 3 release days", transform=ax.transAxes, fontsize=8, color="grey")
ax.grid(alpha=.25); save(fig, "01_buzz_vs_boxoffice.png")

# ---------- 2. rank slope ----------
cols = [("Trailer\nviews/day", "views_per_day"), ("Google Trends\npeak", "peak_search_interest"),
        ("Comment\nsentiment", "s_net"), ("Box office\nfirst 3 days", "first3_days_india_cr")]
ranks = pd.DataFrame({n: eng[c].rank(ascending=False, method="average") for n, c in cols}); ranks.index = eng.short
fig, ax = plt.subplots(figsize=(8, 5.6))
for i, nm in enumerate(ranks.index):
    ax.plot(range(4), ranks.loc[nm], "-o", color=col[i], lw=2, ms=5)
    ax.text(-0.06, ranks.loc[nm].iloc[0], nm, ha="right", va="center", fontsize=9)
    ax.text(3.06, ranks.loc[nm].iloc[3], nm, ha="left", va="center", fontsize=9)
ax.set_xticks(range(4)); ax.set_xticklabels([c[0] for c in cols]); ax.invert_yaxis(); ax.set_yticks(range(1, 9))
ax.set_ylabel("Rank (1 = highest)"); ax.set_xlim(-0.9, 3.9); ax.spines["left"].set_visible(False); ax.tick_params(axis="y", left=False)
d = (ranks.iloc[:, 0] - ranks.iloc[:, 3]); mover = d.abs().idxmax()
ax.set_title(f"The signals disagree most on {mover}: trailer rank {int(ranks.loc[mover].iloc[0])}, box-office rank {int(ranks.loc[mover].iloc[3])}", loc="left")
ax.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=c, label=l) for l, c in LANGC.items()], frameon=False, loc="upper center", bbox_to_anchor=(.5, -.12), ncol=4, fontsize=9); save(fig, "02_rank_slope.png")

# ---------- 3. trends aligned to release ----------
ts = ts.merge(eng[["k", "release_date", "language", "short"]], on="k")
ts["m"] = (ts.Time.dt.year - ts.release_date.dt.year) * 12 + ts.Time.dt.month - ts.release_date.dt.month
fig, ax = plt.subplots(figsize=(8.5, 4.8)); flat = []
for nm, g in ts.groupby("short"):
    g = g.sort_values("m"); mx = g.search_interest_0_100.max()
    if mx < 3: flat.append(nm); continue
    ax.plot(g.m, g.search_interest_0_100 / mx * 100, "-o", ms=3, color=LANGC[g.language.iloc[0]], lw=1.8)
    ax.text(g.m.iloc[-1] + .15, (g.search_interest_0_100 / mx * 100).iloc[-1], nm, fontsize=8, va="center")
ax.axvline(0, color="k", ls=":", lw=1); ax.text(0.1, 103, "release month", fontsize=8)
ax.set_xlim(-6, 17); ax.set_ylim(-3, 110); ax.set_xlabel("Months from release month"); ax.set_ylabel("Search interest, % of film's own peak")
ax.set_title("Buzz peaks in the release month and is mostly gone within 3 months", loc="left")
ax.text(0.0, -0.17, "Monthly data only: day-level decay is not visible. " + (", ".join(flat) + " ≈0 on the shared Trends scale; omitted." if flat else ""), transform=ax.transAxes, fontsize=8, color="grey")
langlegend(ax, "center right"); ax.grid(alpha=.2); save(fig, "03_trends_release_aligned.png")

# ---------- 4. sentiment diverging ----------
o = eng.sort_values("s_net")
fig, ax = plt.subplots(figsize=(8, 4.6)); y = np.arange(len(o))
ax.barh(y, -o.s_negative * 100, color="#c0392b", label="Negative"); ax.barh(y, o.s_positive * 100, color="#2e8b57", label="Positive")
ax.barh(y, o.s_neutral * 100, left=o.s_positive * 100, color="#d0d0d0", label="Neutral")
ax.set_yticks(y); ax.set_yticklabels(o.short); ax.axvline(0, color="k", lw=.8)
for i, (_, r) in enumerate(o.iterrows()): ax.text(105, i, f"{r.views_per_day:,.0f}/day", va="center", fontsize=8, color="grey")
ax.text(105, len(o) - .3, "Trailer views", fontsize=8, color="grey", fontweight="bold")
ax.set_xlim(-60, 140); ax.set_xlabel("% of ~1,000 sampled comments"); ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(.4, -.14), fontsize=8, ncol=3)
top, bot = o.iloc[-1], o.iloc[0]
ax.set_title(f"{top.short} comments were the most positive ({top.s_net*100:+.0f} net); {bot.short} the least ({bot.s_net*100:+.0f})", loc="left")
save(fig, "04_sentiment_diverging.png")

# ---------- 5. topic heatmap ----------
tg = com[com.topic != "General"]; topics = ["Story", "Acting", "Music", "Direction", "Visuals"]
cnt = tg.groupby(["movie_id", "topic"]).size().unstack().reindex(columns=topics).fillna(0)
shr = cnt.div(cnt.sum(axis=1), axis=0); ms = tg.groupby(["movie_id", "topic"])["sentiment_score"].mean().unstack().reindex(columns=topics)
cov = (com.topic != "General").mean()
fig, axs = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
for ax, M, t, cm, vl in ((axs[0], shr, "Share of topic-tagged comments", "Blues", (0, 1)), (axs[1], ms, "Mean sentiment of those comments", "RdYlGn", (-.6, .6))):
    M = M.loc[eng.movie_id]; im = ax.imshow(M.values, cmap=cm, vmin=vl[0], vmax=vl[1], aspect="auto")
    ax.set_xticks(range(5)); ax.set_xticklabels(topics); ax.set_yticks(range(8)); ax.set_yticklabels([f"{s} (n={int(cnt.loc[m].sum())})" for s, m in zip(eng.short, eng.movie_id)])
    for i in range(8):
        for j in range(5):
            v = M.values[i, j]
            if not np.isnan(v): ax.text(j, i, f"{v:.0%}" if t.startswith("Share") else f"{v:+.2f}", ha="center", va="center", fontsize=8)
    ax.set_title(t, fontsize=10, loc="left"); [s.set_visible(False) for s in ax.spines.values()]
fig.suptitle(f"What people mention: only {cov:.0%} of comments name a topic; Story/Acting/Music dominate", x=0.01, ha="left", fontweight="bold")
save(fig, "05_topic_heatmap.png"); res["topic_cov"] = cov

# ---------- 6. comment timeline ----------
com["wk"] = np.floor((com.published_at - com.release_date).dt.days / 7)
fig, ax = plt.subplots(figsize=(8.5, 4.8)); share = {}
for i, r in eng.iterrows():
    g = com[com.movie_id == r.movie_id]; c = g.groupby("wk").size().sort_index()
    c = c[(c.index >= -8) & (c.index <= 60)]
    ax.plot(c.index, c.values, color=col[i], lw=1.6, alpha=.9); ax.text(c.index.max() + .5, c.values[-1], r.short, fontsize=8, va="center", color=col[i])
    share[r.short] = ((g.published_at - g.release_date).dt.days.between(0, 29)).mean()
ax.set_yscale("log"); ax.set_xlabel("Weeks from release"); ax.set_ylabel("Sampled comments per week (log)"); ax.axvline(0, color="k", ls=":", lw=1)
nlow = sum(v < .10 for v in share.values())
ax.set_title(f"{nlow} of 8 films have under 10% of sampled comments from their first 30 days", loc="left")
ax.text(0.01, 0.02, "Top-1,000 comments per trailer, pulled once on 23 Nov 2026: not a live release-week feed.", transform=ax.transAxes, fontsize=8, color="grey")
langlegend(ax, "upper right"); ax.grid(alpha=.2); ax.set_xlim(-8, 66); save(fig, "06_comment_timeline.png")

# ---------- 7. normalised scorecard ----------
M = pd.DataFrame({"Trailer views/day (log)": mm(eng.log_vpd), "Like rate": mm(eng.like_rate), "Comment rate": mm(eng.comment_rate),
                  "Trends peak": mm(eng.peak_search_interest), "Net sentiment": mm(eng.s_net), "Box office 3-day (log)": mm(eng.log_bo)})
M.index = eng.short; M = M.loc[eng.sort_values(["language", "log_bo"], ascending=[True, False]).short]
fig, ax = plt.subplots(figsize=(8.4, 4.6)); im = ax.imshow(M.values, cmap="YlGnBu", vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(M.shape[1])); ax.set_xticklabels(M.columns, rotation=25, ha="right"); ax.set_yticks(range(8))
lang = eng.set_index("short").language; ax.set_yticklabels([f"{n} · {lang[n]}" for n in M.index])
for i in range(8):
    for j in range(M.shape[1]): ax.text(j, i, f"{M.values[i,j]:.2f}", ha="center", va="center", fontsize=8, color="white" if M.values[i, j] > .6 else "black")
ax.set_title("On one 0-1 scale Dhurandhar leads on reach (views, Trends) but is last on like rate", loc="left"); [s.set_visible(False) for s in ax.spines.values()]
save(fig, "07_normalised_scorecard.png")

# ---------- 8/9. duplicates + language mix ----------
def norm(t): return re.sub(r"[\W_]+", " ", unicodedata.normalize("NFKC", str(t)).lower()).strip()
raw["n"] = raw.comment_text.map(norm); raw["words"] = raw.n.str.split().str.len()
def script(t):
    s = {"Devanagari": 0, "Tamil": 0, "Malayalam": 0, "Kannada": 0, "Telugu": 0, "Latin": 0}
    for ch in str(t):
        o_ = ord(ch)
        if 0x900 <= o_ <= 0x97F: s["Devanagari"] += 1
        elif 0xB80 <= o_ <= 0xBFF: s["Tamil"] += 1
        elif 0xD00 <= o_ <= 0xD7F: s["Malayalam"] += 1
        elif 0xC80 <= o_ <= 0xCFF: s["Kannada"] += 1
        elif 0xC00 <= o_ <= 0xC7F: s["Telugu"] += 1
        elif ch.isalpha() and o_ < 0x250: s["Latin"] += 1
    m = max(s, key=s.get); return m if s[m] > 0 else "Emoji/symbols only"
raw["script"] = raw.comment_text.map(script)
dup = []
for mid, g in raw.groupby("movie_id"):
    g = g[g.words >= 3]; ex = g.duplicated("n", keep=False).mean()
    X = TfidfVectorizer(ngram_range=(1, 2)).fit_transform(g.n); S = cosine_similarity(X); np.fill_diagonal(S, 0)
    nd = (S.max(axis=1) >= .85).mean(); dup.append((mid, ex, nd, len(g)))
dup = pd.DataFrame(dup, columns=["movie_id", "exact", "near", "n"]).merge(eng[["movie_id", "short", "language"]], on="movie_id").sort_values("near")
top = raw[raw.words >= 3].n.value_counts().head(6)
fig, axs = plt.subplots(1, 2, figsize=(13, 4.4), gridspec_kw={"width_ratios": [1.1, 1], "wspace": .75})
y = np.arange(len(dup)); axs[0].barh(y, dup.near * 100, color="#bbbbbb", label="Near-duplicate (cosine ≥ 0.85)"); axs[0].barh(y, dup.exact * 100, color="#c0392b", label="Exact repeat")
axs[0].set_yticks(y); axs[0].set_yticklabels(dup.short); axs[0].set_xlabel("% of comments with 3+ words"); axs[0].legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(.5, -.18), ncol=2)
hi = dup.iloc[-1]; axs[0].set_title(f"Copy-paste comments are rare: max {hi.near:.0%} ({hi.short})", loc="left", fontsize=11)
axs[1].barh(range(len(top))[::-1], top.values, color="#7a7a7a"); axs[1].set_yticks(range(len(top))[::-1]); axs[1].set_yticklabels([t[:38] for t in top.index], fontsize=8)
axs[1].set_xlabel("Times repeated (all films)"); axs[1].set_title("Most repeated 3+ word comments", loc="left", fontsize=11)
fig.text(0.01, -0.02, "Text similarity flags templates only; it cannot prove paid or bot activity.", fontsize=8, color="grey"); save(fig, "08_duplicate_comments.png"); res["dup"] = dup

lm = raw.groupby("movie_id")["script"].value_counts(normalize=True).unstack().fillna(0).reindex(eng.movie_id)
order = [c for c in ["Latin", "Devanagari", "Tamil", "Malayalam", "Kannada", "Telugu", "Emoji/symbols only"] if c in lm.columns]
pal = dict(zip(order, ["#4c78a8", "#1f4e79", "#c0392b", "#2e8b57", "#d98c00", "#8e6bbf", "#bbbbbb"]))
fig, ax = plt.subplots(figsize=(8.5, 4.4)); left = np.zeros(8)
for c in order: ax.barh(range(8), lm[c].values * 100, left=left * 100, color=pal[c], label=c); left += lm[c].values
ax.set_yticks(range(8)); ax.set_yticklabels(eng.short); ax.invert_yaxis(); ax.set_xlabel("% of comments by dominant script"); ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(.5, -.18))
lat = lm["Latin"].mean(); ax.set_title(f"Roman-script text dominates ({lat:.0%} of comments), so Hinglish/Tanglish hides inside 'Latin'", loc="left", fontsize=11)
save(fig, "09_language_mix.png")

# ---------- 10. leave-one-out ----------
rows = []
for i in range(8):
    tr = eng.drop(i); b = np.polyfit(tr.buzz, tr.log_bo, 1)
    rows.append((eng.short[i], eng.log_bo[i], np.polyval(b, eng.buzz[i]), tr.log_bo.mean()))
L = pd.DataFrame(rows, columns=["f", "act", "pred", "base"]); L["err"] = (L.pred - L.act).abs(); L["berr"] = (L.base - L.act).abs()
within2 = (L.err <= np.log10(2)).sum(); res["loo"] = (L.err.mean(), L.berr.mean(), within2)
rk = spearmanr(L.pred, L.act)[0]; res["loo_rank"] = rk
fig, ax = plt.subplots(figsize=(6.4, 5.6)); lim = [0.6, 2.5]; ax.plot(lim, lim, "k--", lw=1)
ax.fill_between(lim, np.array(lim) - np.log10(2), np.array(lim) + np.log10(2), color="#eee", zorder=0)
for i, r in L.iterrows():
    ax.scatter(r.pred, r.act, color=col[i], s=90, zorder=3); ax.annotate(r.f, (r.pred, r.act), xytext=(6, 4), textcoords="offset points", fontsize=9)
ax.set_xlim(lim); ax.set_ylim(lim); ax.set_xlabel("Predicted log10(₹ Cr) from the other 7 films"); ax.set_ylabel("Actual log10(₹ Cr)")
ax.set_title(f"Leaving each film out: {within2}/8 predicted within 2× (shaded band)", loc="left", fontsize=11)
ax.text(0.02, 0.97, f"Mean error {L.err.mean():.2f} log10 vs {L.berr.mean():.2f} for 'always guess the average'", transform=ax.transAxes, fontsize=8, va="top", color="grey")
save(fig, "10_leave_one_out.png"); L.to_csv(OUT / "loo_results.csv", index=False)

# ---------- 11. Friday dashboard (illustrative) ----------
_d = pd.read_csv(VDATA / "daily.csv").sort_values(["movie_name", "day_number"])
d3 = _d.groupby("movie_name").apply(lambda g: g.india_net_cr.iloc[2] / g.india_net_cr.iloc[0] * 100, include_groups=False)
eng["d3"] = eng.movie_name.map(d3)
def call(r):
    if r.d3 >= 150: return ("ADD SCREENS", "#2e8b57")
    if r.d3 <= 75: return ("CUT / PROMOTE", "#c0392b")
    return ("HOLD", "#d98c00")
fig, ax = plt.subplots(figsize=(10.5, 5.4)); ax.axis("off"); hdr = ["Film", "Buzz index", "Net sentiment", "Near-dup %", "Opening 3 days (₹ Cr)", "Day 3 ÷ Day 1", "Call (illustrative)"]; xs = [0, .17, .34, .48, .6, .79, .9]
for x, h in zip(xs, hdr): ax.text(x, 1.02, h, fontweight="bold", fontsize=9, transform=ax.transAxes)
dd = dup.set_index("movie_id")
for i, r in eng.sort_values("buzz", ascending=False).reset_index(drop=True).iterrows():
    yy = .92 - i * .105; c, cc = call(r)
    ax.text(xs[0], yy, r.short, fontsize=10, transform=ax.transAxes, color=LANGC[r.language], fontweight="bold")
    ax.barh(yy + .01, r.buzz * .1, height=.04, left=xs[1], color="#4c78a8", transform=ax.transAxes); ax.text(xs[1] + .11, yy, f"{r.buzz:.2f}", fontsize=9, transform=ax.transAxes)
    ax.text(xs[2], yy, f"{r.s_net*100:+.0f}", fontsize=9, transform=ax.transAxes); ax.text(xs[3], yy, f"{dd.loc[r.movie_id,'near']*100:.0f}%", fontsize=9, transform=ax.transAxes)
    ax.text(xs[4], yy, f"{r.first3_days_india_cr:,.1f}", fontsize=9, transform=ax.transAxes); ax.text(xs[5], yy, f"{r.d3:.0f}%", fontsize=9, transform=ax.transAxes)
    ax.text(xs[6], yy, f"● {c}", color=cc, fontsize=9, fontweight="bold", transform=ax.transAxes)
ax.text(0, -.03, "Mock-up of a Friday check. Call = day 3 vs day 1 India net (known within 72 h): ≥150% add, ≤75% cut/promote. Not validated; n=8.\nDay-of-week confounds it (Fri releases ramp into Sunday; Thu releases peak on the holiday). Screen counts not available.", fontsize=8, color="grey", transform=ax.transAxes, va="top")
fig.suptitle("Friday check: is the box office holding up on day 3?", x=0.01, ha="left", fontweight="bold", fontsize=12); save(fig, "11_friday_dashboard_mock.png")

# ---------- 12. regional heatmap (fix) ----------
b1 = pd.read_csv(C / "google_trends/batch1_by_region_cleaned.csv").set_index("Region"); b2 = pd.read_csv(C / "google_trends/batch2_by_region_cleaned.csv").set_index("Region")
R = pd.concat([b1[["Dhurandhar", "Chhaava", "Coolie", "Good Bad Ugly"]], b2[["L2: Empuraan", "Lokah Chapter 1: Chandra", "Su From So", "Ekka"]]], axis=1).dropna(how="all")
R.columns = ["Dhurandhar", "Chhaava", "Coolie", "Good Bad Ugly", "L2 Empuraan", "Lokah", "Su From So", "Ekka"]
Rn = R / R.max().replace(0, np.nan) * 100
order = Rn.mean(axis=1).sort_values(ascending=False).index; Rn = Rn.loc[order]
fig, ax = plt.subplots(figsize=(8, 8.5)); im = ax.imshow(Rn.values, cmap="YlOrRd", vmin=0, vmax=100, aspect="auto")
ax.set_xticks(range(8)); ax.set_xticklabels(Rn.columns, rotation=30, ha="right"); ax.set_yticks(range(len(Rn))); ax.set_yticklabels(Rn.index, fontsize=8)
tops = {c: Rn[c].idxmax() for c in ["Coolie", "Good Bad Ugly", "L2 Empuraan", "Lokah", "Su From So", "Ekka"]}
ax.set_title(f"Regional films stay local: Su From So peaks in {tops['Su From So']}, Lokah in {tops['Lokah']}, Coolie in {tops['Coolie']}", loc="left", fontsize=11)
ax.text(0, -0.1, "Each film scaled to its own top state (100). Dhurandhar from batch 1; others from batch 2.", transform=ax.transAxes, fontsize=8, color="grey"); [s.set_visible(False) for s in ax.spines.values()]
save(fig, "12_trends_state_heatmap.png"); res["tops"] = tops

# ---------- 13. fixed originals ----------
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
for i, r in eng.iterrows():
    axs[0].scatter(r.lead_cast_popularity, r.views_per_day, color=col[i], s=80); axs[0].annotate(r.short, (r.lead_cast_popularity, r.views_per_day), xytext=(5, 4), textcoords="offset points", fontsize=8)
    rt = r.tmdb_rating if r.tmdb_rating > 0 else np.nan
    if not np.isnan(rt): axs[1].scatter(rt, r.engagement_index, color=col[i], s=80); axs[1].annotate(r.short, (rt, r.engagement_index), xytext=(5, 4), textcoords="offset points", fontsize=8)
axs[0].set_yscale("log"); axs[0].set_xlabel("TMDB lead-cast popularity"); axs[0].set_ylabel("Trailer views/day (log)")
axs[0].set_title("Cast popularity tracks trailer reach, with Dhurandhar far out", loc="left", fontsize=10)
axs[1].set_xlabel("TMDB rating"); axs[1].set_ylabel("Engagement index"); axs[1].set_title("TMDB rating says little about engagement (Ekka: no rating, excluded)", loc="left", fontsize=10)
langlegend(axs[1], "upper right"); [a.grid(alpha=.2) for a in axs]; save(fig, "13_fixed_cast_and_rating.png")

# ---------- numbers for the summary ----------
print("rho buzz~BO %.2f p=%.3f" % res["rho_buzz_bo"])
for c in ["c_views", "c_trends", "c_sent"]: print(c, "rho %.2f" % spearmanr(eng[c], eng.first3_days_india_cr)[0])
print("LOO mean err %.2f baseline %.2f within2 %d rank rho %.2f" % (*res["loo"], res["loo_rank"]))
print(L.assign(resid=(L.act - L.pred).round(2))[["f", "resid"]].to_string(index=False))
print(dup[["short", "exact", "near", "n"]].round(3).to_string(index=False)); print("topic coverage %.2f" % res["topic_cov"]); print("30-day share", {k: round(v, 2) for k, v in share.items()})
print(eng[["short", "buzz", "s_net"]].round(2).to_string(index=False)); print(res["tops"]); print("latin share %.2f" % lat); print(top.to_string())

# ================= NEW: charts using the added Sacnilk daily / summary / OTT data =================
D = pd.read_csv(VDATA / "daily.csv")
S = pd.read_csv(VDATA / "summary.csv")
OTT = pd.read_csv(VDATA / "ott.csv")
D = D.merge(eng[["movie_name", "short", "language"]], on="movie_name")
S = S.merge(eng[["movie_name", "short", "language", "first3_days_india_cr", "s_net", "buzz", "log_vpd"]], on="movie_name")
S["legs"] = S.india_net_cr / S.first3_days_india_cr

# 14. daily decay indexed to day 1
fig, ax = plt.subplots(figsize=(8.5, 5)); dec = {}; ends = {}
for nm, g in D.groupby("short"):
    g = g.sort_values("day_number"); idx = g.india_net_cr / g.india_net_cr.iloc[0] * 100; lg = g.language.iloc[0]
    ax.plot(g.day_number, idx, "-o", ms=4, lw=1.8, color=LANGC[lg]); ends[nm] = (g.day_number.max(), idx.iloc[-1], LANGC[lg])
    dec[nm] = idx.iloc[-1] if g.day_number.max() >= 5 else np.nan
_y = -1e9
for nm, (xd, yv, cc) in sorted(ends.items(), key=lambda kv: kv[1][1]):
    yl = max(yv, _y + 22); _y = yl; ax.text(xd + .15, yl, nm, fontsize=8, va="center", color=cc)
d5 = {nm: (g.sort_values("day_number").india_net_cr.iloc[4] / g.sort_values("day_number").india_net_cr.iloc[0] * 100) for nm, g in D.groupby("short")}
hi5, lo5 = max(d5, key=d5.get), min(d5, key=d5.get)
ax.axhline(100, color="grey", ls=":", lw=1); ax.set_xlabel("Day since release"); ax.set_ylabel("India net, % of day 1")
ax.set_xlim(.8, 8.6); ax.set_xticks(range(1, 8))
ax.set_title(f"By day 5, {hi5} was at {d5[hi5]:.0f}% of its opening day; {lo5} at {d5[lo5]:.0f}%", loc="left")
ax.text(0.01, 0.02, "Dhurandhar has 5 verified days only. Day-of-week and holidays drive much of the wobble.", transform=ax.transAxes, fontsize=8, color="grey")
langlegend(ax, "upper left"); ax.grid(alpha=.2); save(fig, "14_boxoffice_daily_decay.png")

# 15. legs: lifetime / first-3-day multiple vs sentiment
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
o = S.sort_values("legs")
axs[0].barh(o.short, o.legs, color=[LANGC[l] for l in o.language]); axs[0].set_xlabel("Lifetime India net ÷ first-3-day net (×)")
for y_, v in enumerate(o.legs): axs[0].text(v + .1, y_, f"{v:.1f}×", va="center", fontsize=8)
axs[0].set_title(f"{o.short.iloc[-1]} kept earning {o.legs.iloc[-1]:.0f}× its opening; {o.short.iloc[0]} only {o.legs.iloc[0]:.1f}×", loc="left", fontsize=10)
rho_l = spearmanr(S.s_net, S.legs)[0]; rho_b = spearmanr(S.buzz, S.legs)[0]; res["legs"] = (rho_l, rho_b)
for _, r in S.iterrows(): axs[1].scatter(r.s_net * 100, r.legs, color=LANGC[r.language], s=80); axs[1].annotate(r.short, (r.s_net * 100, r.legs), xytext=(5, 4), textcoords="offset points", fontsize=8)
axs[1].set_xlabel("Net comment sentiment (pos% - neg%)"); axs[1].set_ylabel("Legs (×)"); axs[1].set_title(f"Positive comments went with longer legs (rank corr. {rho_l:.2f}, n=8)", loc="left", fontsize=10); axs[1].grid(alpha=.2)
fig.text(0.01, -0.03, "Lifetime totals are as of different dates per film (see summary.csv 'as_of_note'), so legs are approximate.", fontsize=8, color="grey")
save(fig, "15_legs_vs_sentiment.png")

# 16. theatrical window and OTT gap
OTT = OTT.merge(eng[["movie_name", "short", "language"]], on="movie_name")
OTT["gap"] = (pd.to_datetime(OTT.ott_release_date) - pd.to_datetime(OTT.theatrical_release_date)).dt.days
O = OTT.sort_values("gap"); fig, ax = plt.subplots(figsize=(8, 4.4))
ax.barh(O.short, O.gap, color=[LANGC[l] for l in O.language])
for y_, (g, p_) in enumerate(zip(O.gap, O.ott_platform)): ax.text(g + 1, y_, f"{g} d · {p_}", va="center", fontsize=8)
ax.set_xlim(0, O.gap.max() * 1.35); ax.set_xlabel("Days from theatrical release to OTT premiere")
ax.set_title(f"Three films went to OTT after 28 days; Ekka waited {O.gap.max()} days", loc="left", fontsize=11)
save(fig, "16_ott_window.png"); res["ott"] = O[["short", "gap"]]

# 17. budget vs net (films with a reported budget)
B = S.dropna(subset=["reported_budget_cr"]); fig, ax = plt.subplots(figsize=(7, 4.4)); x = np.arange(len(B))
ax.bar(x - .2, B.reported_budget_cr, .4, color="#bbbbbb", label="Reported budget"); ax.bar(x + .2, B.india_net_cr, .4, color=[LANGC[l] for l in B.language], label="India net (lifetime)")
ax.set_xticks(x); ax.set_xticklabels(B.short); ax.set_ylabel("₹ Cr"); ax.legend(frameon=False, fontsize=8)
for i, (_, r) in enumerate(B.iterrows()): ax.text(i + .2, r.india_net_cr + 8, f"{r.india_net_cr / r.reported_budget_cr:.1f}×", ha="center", fontsize=8)
ax.set_title("Only 4 films have a reported budget; Coolie's India net fell short of its budget", loc="left", fontsize=11); save(fig, "17_budget_vs_net.png")

print("--- NEW"); print("legs rho sentiment %.2f buzz %.2f" % res["legs"]); print(S[["short", "first3_days_india_cr", "india_net_cr", "legs"]].round(1).to_string(index=False)); print(d5); print(res["ott"].to_string(index=False))

# 18. which signal predicted what
comp = {"Trailer views/day": eng.views_per_day, "Google Trends peak": eng.peak_search_interest, "Net sentiment": eng.s_net, "Like rate": eng.like_rate}
legs_by = S.set_index("movie_name").legs.reindex(eng.movie_name).values; rows = []
for k, v in comp.items(): rows.append((k, spearmanr(v, eng.first3_days_india_cr)[0], spearmanr(v, legs_by)[0]))
Cc = pd.DataFrame(rows, columns=["sig", "opening", "legs"]).iloc[::-1]; y = np.arange(len(Cc)); fig, ax = plt.subplots(figsize=(8, 4.2))
ax.barh(y + .2, Cc.opening, .4, color="#1f4e79", label="vs opening size (first 3 days)"); ax.barh(y - .2, Cc.legs, .4, color="#d98c00", label="vs legs (lifetime ÷ opening)")
ax.set_yticks(y); ax.set_yticklabels(Cc.sig); ax.axvline(0, color="k", lw=.8); ax.set_xlim(-1, 1); ax.set_xlabel("Spearman rank correlation (n=8; |r| < ~0.7 is not significant)"); ax.legend(frameon=False, fontsize=8, loc="lower right")
ax.set_title("Reach signals went with bigger openings; comment sentiment went with longer legs", loc="left", fontsize=11); save(fig, "18_which_signal_predicted_what.png"); print(Cc.round(2).to_string(index=False))

# 10b. leave-one-out with reach-only index (post-hoc, labelled)
eng["reach"] = eng[["c_views", "c_trends"]].mean(axis=1); rows = []
for i in range(8):
    tr = eng.drop(i); b = np.polyfit(tr.reach, tr.log_bo, 1); rows.append((eng.short[i], eng.log_bo[i], np.polyval(b, eng.reach[i])))
L2 = pd.DataFrame(rows, columns=["f", "act", "pred"]); L2["err"] = (L2.pred - L2.act).abs(); w2 = (L2.err <= np.log10(2)).sum(); rk2 = spearmanr(L2.pred, L2.act)[0]
fig, ax = plt.subplots(figsize=(6.4, 5.6)); ax.plot(lim, lim, "k--", lw=1); ax.fill_between(lim, np.array(lim) - np.log10(2), np.array(lim) + np.log10(2), color="#eee", zorder=0)
for i, r in L2.iterrows(): ax.scatter(r.pred, r.act, color=col[i], s=90, zorder=3); ax.annotate(r.f, (r.pred, r.act), xytext=(6, 4), textcoords="offset points", fontsize=9)
ax.set_xlim(lim); ax.set_ylim(lim); ax.set_xlabel("Predicted log10(₹ Cr), reach index (views + Trends)"); ax.set_ylabel("Actual log10(₹ Cr)")
ax.set_title(f"Reach-only index: {w2}/8 within 2×, rank corr. {rk2:.2f}", loc="left", fontsize=11)
ax.text(0.02, 0.97, f"Mean error {L2.err.mean():.2f} log10. Post-hoc choice after seeing sentiment fail:\ntreat as a hypothesis for next release, not a result.", transform=ax.transAxes, fontsize=8, va="top", color="grey")
save(fig, "10b_leave_one_out_reach_only.png"); print("reach LOO err %.2f within2 %d rho %.2f" % (L2.err.mean(), w2, rk2)); print("full-index rho buzz~BO %.2f" % res["rho_buzz_bo"][0])
