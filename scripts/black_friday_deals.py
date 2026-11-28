"""Black Friday Deals page for buytrigger.cards, live at /deals/black-friday/.

TCGplayer's Cyber Weekend store-credit promotion: Fri 27 Nov 2026 14:00 to
Tue 1 Dec 2026 04:00, London. Figures come from the Delta Reign and SV 151
market caches in the repo (TCGCSV, raw, USD), so every rebuild is dated by its
own data. To refresh the page by hand: update TERMS_CHECKED below after
re-reading the TCGplayer terms, then run `python3 scripts/black_friday_deals.py`
and `python3 scripts/build.py`. See ops/runbooks/black-friday-deals-updates.md
in the private ops folder.
"""
from __future__ import annotations

import html as htmlmod
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TITLE = "TCGplayer’s Cyber Weekend Is 10% Credit"
ROUTE = "deals/black-friday"
PATH = "deals/black-friday/"
URL = "https://buytrigger.cards/deals/black-friday/"
HERO = "assets/black-friday-deals-2026/hero-1600x900.webp"
HERO_ALT = (
    "Curated graphic: the English Delta Reign booster pack, the gold Mega Rayquaza ex 141/103 "
    "Mega Hyper Rare, and the Scarlet & Violet 151 Charizard ex 199/165 Special Illustration Rare."
)
HERO_CREDIT = "Card and pack images: TCGplayer. Card artwork © Pokémon. Graphic: BuyTrigger.Cards."
PSA_NEWS_PATH = "news/psa-stops-grading-english-mega-hyper-rares-2026-11-26/"
PSA_NEWS_URL = "https://buytrigger.cards/" + PSA_NEWS_PATH
PSA_ANNOUNCEMENT = (
    "https://www.psacard.com/articles/articleview/15794/"
    "psa-stops-grading-english-mega-hyper-rare-pokemon-cards"
)
TCGPLAYER_TERMS = (
    "https://help.tcgplayer.com/hc/en-us/articles/"
    "360019079273-Promotional-Store-Credit-Disclaimer"
)
PLACEMENT = "black-friday-deals"  # eBay placement becomes story-black-friday-deals
TERMS_CHECKED = "28 November 2026"
BASE_DAY = "2026-11-21"  # earliest day in both public daily caches

# (set key, productId, name, number, set label, rarity, image, alt)
DELTA = [
    ("728061", "Mega Rayquaza ex", "138/103", "Delta Reign", "Special Illustration Rare", "assets/delta-reign/728061.jpg"),
    ("728062", "Mega Rayquaza ex", "141/103", "Delta Reign", "Mega Hyper Rare", "assets/delta-reign/728062.jpg"),
    ("726567", "Kecleon", "117/103", "Delta Reign", "Illustration Rare", "assets/delta-reign/726567.jpg"),
]
SV151 = [
    ("517045", "Charizard ex", "199/165", "Scarlet & Violet 151", "Special Illustration Rare", "assets/sv-151/517045.jpg"),
    ("517046", "Blastoise ex", "200/165", "Scarlet & Violet 151", "Special Illustration Rare", "assets/sv-151/517046.jpg"),
    ("517044", "Venusaur ex", "198/165", "Scarlet & Violet 151", "Special Illustration Rare", "assets/sv-151/517044.jpg"),
    ("513721", "Pikachu", "173/165", "Scarlet & Violet 151", "Illustration Rare", "assets/sv-151/513721.jpg"),
]


def esc(value) -> str:
    return htmlmod.escape(str(value), quote=True)


def pretty(day: str) -> str:
    d = datetime.strptime(day, "%Y-%m-%d")
    return f"{d.day} November {d.year}"


def short(day: str) -> str:
    d = datetime.strptime(day, "%Y-%m-%d")
    return f"{d.day} Nov {d.year}"


def usd(value: float) -> str:
    return f"US${value:,.2f}"


def load_cache(root: Path, key: str) -> dict:
    return json.loads((root / "data" / "market-cache" / f"{key}-current.json").read_text())


def day_prices(cache: dict, day: str) -> dict:
    out = {}
    for card in cache["cards"]:
        for point in card["points"]:
            if point["day"] == day and point.get("status") == "ok" and point.get("usd") is not None:
                out[card["productId"]] = float(point["usd"])
    return out


class SetData:
    """Latest-day and base-day guides. Never raises on a gap, so a daily refresh
    problem cannot stop the site build; gaps are stated on the page instead."""

    def __init__(self, root: Path, key: str, roster: int):
        cache = load_cache(root, key)
        self.latest = cache["sourceDate"]
        self.latest_prices = day_prices(cache, self.latest)
        self.base_prices = day_prices(cache, BASE_DAY)
        self.roster = roster
        both = set(self.latest_prices) & set(self.base_prices)
        self.count = len(both)
        self.total = round(sum(self.latest_prices[p] for p in both), 2)
        self.base_total = round(sum(self.base_prices[p] for p in both), 2)

    @property
    def scope(self) -> str:
        if self.count == self.roster:
            return f"all {self.roster} English cards"
        return f"the {self.count} of {self.roster} English cards with a guide on both dates"

    def line(self, pid: str) -> str:
        now, then = self.latest_prices.get(pid), self.base_prices.get(pid)
        if now is None:
            return f"No market guide recorded on {short(self.latest)}."
        if then is None:
            return f"{usd(now)} as of {short(self.latest)}."
        return f"{usd(now)} as of {short(self.latest)}, from {usd(then)} on {short(BASE_DAY)}."


def ebay_block(name: str, number: str, set_name: str) -> str:
    return (
        f'<div data-ebay-card data-ebay-name="{esc(name)}" data-ebay-number="{esc(number)}" '
        f'data-ebay-set="{esc(set_name)}" data-ebay-placement="story-{PLACEMENT}"></div>'
    )


def card_item(data: SetData, spec) -> str:
    pid, name, number, set_name, rarity, image = spec
    alt = f"Exact English {set_name} {name} {number} {rarity} catalogue reference."
    return (
        "<li>"
        '<div class="chase-strip-card">'
        f'<img src="{esc(image)}" alt="{esc(alt)}" loading="lazy" decoding="async">'
        f'<span class="chase-strip-name">{esc(name)}</span>'
        f'<span class="chase-strip-meta">{esc(number)} · {esc(rarity)} · {esc(set_name)}</span>'
        f'<span class="chase-strip-meta">{esc(data.line(pid))}</span>'
        "</div>"
        f"{ebay_block(name, number, set_name)}"
        "</li>"
    )


def build_data(root: Path = ROOT):
    return SetData(root, "delta-reign", 141), SetData(root, "sv-151", 207)


def description(root: Path = ROOT) -> str:
    dr, sv = build_data(root)
    return (
        "TCGplayer’s Cyber Weekend promotion gives 10% store credit, or 12% for Subscribers, "
        "from 14:00 London on Friday 27 November 2026 to 04:00 on Tuesday 1 December. "
        "It is credit, not an instant discount. Dated prices from our Delta Reign and SV 151 "
        f"trackers, as of {pretty(max(dr.latest, sv.latest))}."
    )


def page_html(root: Path = ROOT) -> str:
    dr, sv = build_data(root)
    as_of = pretty(max(dr.latest, sv.latest))
    base = pretty(BASE_DAY)
    delta_cards = "".join(card_item(dr, s) for s in DELTA)
    sv_cards = "".join(card_item(sv, s) for s in SV151)
    return f'''<header class="reading-head">
<a class="back-link" href="market.html">← Back to Market</a>
<span class="kicker red-text">BLACK FRIDAY / TCGPLAYER</span>
<h1>{TITLE}</h1>
<p>Subscribers get 12%. It’s store credit, not money off at checkout, and it shows up 3–5 business days later.</p>
<p class="news-credit">BuyTrigger.Cards · Terms checked {TERMS_CHECKED}. Card prices as of {as_of}.</p>
</header>
<figure class="reading-image">
<div class="story-cover full-image"><img src="{HERO}" alt="{esc(HERO_ALT)}" width="1600" height="900"></div>
<figcaption>{HERO_CREDIT}</figcaption>
</figure>
<div class="reading-layout">
<article class="article-body">
<p>TCGplayer’s Cyber Weekend promotion on all products starts at 9:00am EST on Friday 27 November 2026 and ends at 11:00pm EST on Monday 30 November 2026. In London, that’s 14:00 on Friday 27 November to 04:00 on Tuesday 1 December.</p>
<p>During that window, buyers receive 10% store credit on eligible products. TCGplayer Subscribers receive 12% instead of 10%. No code is needed.</p>
<p>It is promotional store credit, not an instant discount. TCGplayer says the credit is added to your account 3–5 business days after a qualifying purchase. Subscribers will only see 10% calculated in the cart and at checkout; the full 12% arrives with that later credit.</p>
<p>The credit will not exceed US$50 per qualifying item, and the total credit awarded in the promotional period will not exceed US$1,500 per account. Preorders are eligible. The promotion excludes prior purchases, gift cards, taxes and shipping. Store credit is non-transferable and cannot be combined with other offers.</p>
<p>To get the 12% Subscriber rate, you have to become a Subscriber before you place the order. Subscriber perks are not retroactive. Any extra 1–3% monthly Subscriber loyalty credit is separate, and is available at the start of next month.</p>
<p class="news-source"><a href="{TCGPLAYER_TERMS}" rel="noopener noreferrer">Source: TCGplayer Promotional Store Credit Disclaimer ↗</a></p>
<div data-tcgplayer-banner data-tcgplayer-subid1="banner" data-tcgplayer-subid2="black-friday-deals"></div>
<h2>Where our trackers stood on {as_of}</h2>
<p>If you’re shopping this weekend, here’s the dated context from our own Delta Reign and SV 151 price pages. These are TCGplayer market guides via TCGCSV for raw, ungraded copies, in US dollars. They are guides, not individual sales or offers, and they can move. Our public price pages refresh once a day, and every figure below carries its own date.</p>
<h3>Delta Reign</h3>
<p>On our <a href="prices/delta-reign/">Delta Reign price page</a>, the raw guides for {dr.scope} add up to {usd(dr.total)} as of {pretty(dr.latest)}, against {usd(dr.base_total)} on {base}. The <a href="delta-reign-index.html">Delta Reign index</a> uses the same dated guides.</p>
<section class="story-chase" aria-label="Delta Reign cards on our tracker">
<ul class="chase-strip-row">{delta_cards}</ul>
<p class="chase-strip-credit">Card image: TCGplayer. Card artwork © Pokémon.</p>
</section>
<h3>SV 151</h3>
<p>On our <a href="prices/sv-151/">SV 151 price page</a>, the raw guides for {sv.scope} add up to {usd(sv.total)} as of {pretty(sv.latest)}, against {usd(sv.base_total)} on {base}. The <a href="sv-151-index.html">SV 151 index</a> uses the same dated guides. The <a href="market.html">Market page</a> lists both trackers and the other set indexes.</p>
<section class="story-chase" aria-label="Scarlet &amp; Violet 151 cards on our tracker">
<ul class="chase-strip-row">{sv_cards}</ul>
<p class="chase-strip-credit">Card image: TCGplayer. Card artwork © Pokémon.</p>
</section>
<p>We are not making a call on where any of these guides go next.</p>
<div class="ebay-footnote"><p><strong>About the eBay links.</strong> Each “Buy on eBay” control opens an eBay search (UK or US site depending on your location) for that card’s name, number and set, not a single listing. Search results, seller prices and availability vary. These are affiliate links: as an eBay Partner Network partner, we may earn from qualifying purchases.</p></div>
<h2>Buying English gold Mega Hyper Rares this Black Friday? Read this first</h2>
<figure class="reading-image">
<div class="story-cover full-image"><img src="assets/delta-reign/728062.jpg" alt="Exact English Delta Reign Mega Rayquaza ex 141/103 Mega Hyper Rare catalogue reference." width="200" height="279"></div>
<figcaption>Mega Rayquaza ex 141/103, the English Delta Reign gold Mega Hyper Rare. Card image: TCGplayer. Card artwork © Pokémon.</figcaption>
</figure>
<p>PSA said on 25 November 2026 that, effective immediately, it will no longer accept English-language Mega Hyper Rare Pokémon cards for grading. That is the gold, etched Mega Evolution Pokémon ex treatment. The policy applies to all current and future English-language Mega Hyper Rares unless PSA announces otherwise. Read our <a href="{PSA_NEWS_PATH}">news story</a> and <a href="{PSA_ANNOUNCEMENT}" rel="noopener noreferrer">PSA’s own announcement</a> before you shop this weekend.</p>
<p>PSA wrote: “We’ve identified a manufacturing issue that can cause the gold foil on the front of these cards to deteriorate over time, leaving visible patches or fading.” It has seen this “in raw cards, cards stored in binders, and cards in PSA holders alike, which indicates the cause is in the card itself rather than in how it’s stored or encapsulated.”</p>
<p>Japanese-language versions “were printed at a different facility using different techniques and haven’t shown this issue,” PSA said, and “are not affected.” We are not treating that as a finding about any other language, or about any other grading company.</p>
<p>Cards already submitted or in transit “will be returned ungraded, and the grading service level fee will not be charged.” Existing PSA grades “will not be changed.” If a card is later submitted for Review or Reholder, “it will be evaluated based on its condition at that time.”</p>
<p>On the guarantee, PSA said: “The PSA Guarantee covers errors in our authentication and grading. It doesn’t cover manufacturer defects that degrade the card after it has been assessed and holdered.”</p>
<p>The English cards PSA named are:</p>
<ul>
<li>Mega Evolution: Mega Gardevoir ex 187/132, Mega Lucario ex 188/132</li>
<li>Phantasmal Flames: Mega Charizard X ex 130/094</li>
<li>Ascended Heroes: Mega Charizard Y ex 294/217, Mega Dragonite ex 295/217</li>
<li>Perfect Order: Mega Zygarde ex 124/088</li>
<li>Chaos Rising: Mega Greninja ex 122/086</li>
<li>Pitch Black: Mega Darkrai ex 120/084</li>
<li>Delta Reign: Mega Rayquaza ex 141/103</li>
</ul>
<p class="news-source"><a href="{PSA_ANNOUNCEMENT}" rel="noopener noreferrer">Source: PSA announcement, 25 November 2026 ↗</a></p>
<p class="small">Card prices on this page come from our Delta Reign and SV 151 trackers and are dated as shown. Promotion terms are from TCGplayer’s Promotional Store Credit Disclaimer, checked on {TERMS_CHECKED}. The TCGplayer link above is an affiliate link and we may earn a commission from a purchase through it. This is not buying advice.</p>
</article>
</div>'''


def hub_html() -> str:
    return f'''<section class="page-intro"><span class="kicker red-text">BUYTRIGGER.CARDS / DEALS</span>
<h1>Deals</h1>
<p>Seasonal promotions that matter to Pokémon card collectors, with the official terms, the dates and our own dated price context.</p>
<p><a class="text-link" href="{PATH}">Black Friday Deals: TCGplayer’s Cyber Weekend, 10% store credit →</a></p>
</section>'''


def write_js(path: Path, root: Path = ROOT) -> None:
    payload = (
        "window.BTBlackFridayDeals="
        + json.dumps(
            {"title": TITLE, "description": description(root), "html": page_html(root), "hub": hub_html()},
            ensure_ascii=False,
        )
        + ";\nwindow.BTBlackFridayDeals.page=function(){return window.BTBlackFridayDeals.html;};"
        + "\nwindow.BTBlackFridayDeals.hubPage=function(){return window.BTBlackFridayDeals.hub;};\n"
    )
    path.write_text(payload)


if __name__ == "__main__":
    write_js(ROOT / "black-friday-deals.js")
    print("wrote", ROOT / "black-friday-deals.js")
