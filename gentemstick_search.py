"""
gentemstick 巡回検索スクリプト
ヤフオク・メルカリ・ヤフーフリマの検索結果を取得し、1つのHTMLにまとめる

Usage:
  python gentemstick_search.py
  python gentemstick_search.py --keyword "gentemstick" --min-price 30000 --max-price 90000
"""
import argparse
import requests
from bs4 import BeautifulSoup
import json
import re
import os
import sys
from datetime import datetime

# デフォルト値（CLIで上書き可能）
KEYWORD = "gentemstick"
MIN_PRICE = 30000
MAX_PRICE = 90000

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "gentemstick_search.html")
OUTPUT_JSON = os.path.join(SCRIPT_DIR, "data.json")


def fetch_yahoo_auction():
    """ヤフオクの検索結果を取得"""
    items = []
    url = f"https://auctions.yahoo.co.jp/search/search?p={KEYWORD}&aucminprice={MIN_PRICE}&aucmaxprice={MAX_PRICE}&va={KEYWORD}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # 商品リストを探す
        product_els = soup.select(".Product")
        if not product_els:
            product_els = soup.select("[class*='Product']")

        for el in product_els:
            try:
                # タイトルとリンク
                a_tag = el.select_one("a[href*='page.auctions.yahoo.co.jp']") or el.select_one("a[href*='auctions.yahoo.co.jp']") or el.select_one("a")
                if not a_tag:
                    continue
                title = a_tag.get("title") or a_tag.get_text(strip=True)
                link = a_tag.get("href", "")
                if not title or not link:
                    continue

                # 画像
                img_tag = el.select_one("img")
                img = img_tag.get("src", "") if img_tag else ""

                # 価格
                price_el = el.select_one(".Product__priceValue") or el.select_one("[class*='price']") or el.select_one(".Product__price")
                price_text = price_el.get_text(strip=True) if price_el else ""

                items.append({
                    "title": title[:80],
                    "price": price_text,
                    "link": link,
                    "image": img,
                    "site": "ヤフオク",
                })
            except Exception:
                continue
        print(f"  ヤフオク: {len(items)}件取得")
    except Exception as e:
        print(f"  ヤフオク: エラー - {e}")
    return items


def fetch_mercari():
    """メルカリの検索結果を取得（Playwright使用）"""
    items = []
    url = f"https://jp.mercari.com/search?keyword={KEYWORD}&price_min={MIN_PRICE}&price_max={MAX_PRICE}"
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)  # 追加の待機

            # 商品カードを取得: a[href^='/item/m']
            cards = page.query_selector_all("a[href^='/item/m']")
            seen_links = set()
            for card in cards:
                try:
                    href = card.get_attribute("href") or ""
                    if not href or href in seen_links:
                        continue
                    seen_links.add(href)
                    link = "https://jp.mercari.com" + href

                    # merItemThumbnail の aria-label からタイトルと価格を取得
                    thumb = card.query_selector("[class*='merItemThumbnail'], [id^='m']")
                    aria = thumb.get_attribute("aria-label") if thumb else ""

                    # 画像
                    img_el = card.query_selector("img")
                    img = img_el.get_attribute("src") if img_el else ""

                    # タイトル: span要素から
                    span_el = card.query_selector("span")
                    title = span_el.inner_text() if span_el else ""
                    if not title and aria:
                        title = aria.split("¥")[0].strip()

                    # 価格: figureのテキストまたはaria-labelから
                    price_text = ""
                    fig = card.query_selector("figure")
                    if fig:
                        fig_text = fig.inner_text()
                        price_match = re.search(r"[¥￥]\s?[\d,]+", fig_text)
                        if price_match:
                            price_text = price_match.group()
                    if not price_text and aria:
                        price_match = re.search(r"[¥￥]\s?[\d,]+", aria)
                        if price_match:
                            price_text = price_match.group()

                    if title:
                        items.append({
                            "title": title[:80],
                            "price": price_text,
                            "link": link,
                            "image": img,
                            "site": "メルカリ",
                        })
                except Exception:
                    continue
            browser.close()
        print(f"  メルカリ: {len(items)}件取得")
    except Exception as e:
        print(f"  メルカリ: エラー - {e}")
    return items


def fetch_yahoo_fleamarket():
    """ヤフーフリマの検索結果を取得（Playwright使用）"""
    items = []
    url = f"https://paypayfleamarket.yahoo.co.jp/search/{KEYWORD}?price_range_begin={MIN_PRICE}&price_range_end={MAX_PRICE}"
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            cards = page.query_selector_all("a[href^='/item/']")
            seen = set()
            for card in cards:
                try:
                    href = card.get_attribute("href") or ""
                    if not href or href in seen:
                        continue
                    seen.add(href)
                    link = "https://paypayfleamarket.yahoo.co.jp" + href if href.startswith("/") else href

                    img_el = card.query_selector("img")
                    img = img_el.get_attribute("src") if img_el else ""
                    title = img_el.get_attribute("alt") if img_el else ""

                    price_el = card.query_selector("p")
                    price_text = price_el.inner_text() if price_el else ""

                    if title:
                        items.append({
                            "title": title[:80],
                            "price": price_text,
                            "link": link,
                            "image": img,
                            "site": "ヤフーフリマ",
                        })
                except Exception:
                    continue
            browser.close()
        print(f"  ヤフーフリマ: {len(items)}件取得")
    except Exception as e:
        print(f"  ヤフーフリマ: エラー - {e}")
    return items


def generate_html(all_items):
    """検索結果をHTMLファイルに出力"""
    now = datetime.now().strftime("%Y/%m/%d %H:%M")

    # 価格文字列から数値を抽出してソート
    def parse_price(p_str):
        num = re.sub(r"[^\d]", "", str(p_str))
        return int(num) if num else 9999999
    
    all_items = sorted(all_items, key=lambda x: parse_price(x["price"]))

    def card_html(item):
        img_html = f'<img src="{item["image"]}" alt="" loading="lazy" onerror="this.style.display=\'none\'">' if item["image"] else '<div class="no-img">NO IMAGE</div>'
        return f'''<a class="card" href="{item["link"]}" target="_blank">
  {img_html}
  <div class="info">
    <div class="title">{item["title"]}</div>
    <div class="price">{item["price"]}</div>
    <span class="badge badge-{item["site"]}">{item["site"]}</span>
  </div>
</a>'''

    cards = "\n".join(card_html(i) for i in all_items) if all_items else '<p class="empty">該当商品が見つかりませんでした</p>'

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>gentemstick 巡回検索結果</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', 'Hiragino Sans', sans-serif; background: #f8f9fa; color: #333; min-height: 100vh; }}
  header {{ background: #fff; padding: 20px 24px; border-bottom: 1px solid #e9ecef; box-shadow: 0 2px 4px rgba(0,0,0,0.05); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }}
  header h1 {{ font-size: 1.3rem; color: #2c3e50; }}
  header h1 span {{ color: #3498db; }}
  .meta {{ font-size: .8rem; color: #6c757d; }}

  .section {{ margin: 20px; }}
  .section-header {{ display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; background: #fff; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 12px; }}
  .section-header h2 {{ font-size: 1rem; color: #2c3e50; }}
  .site-links {{ display: flex; gap: 12px; }}
  .site-link {{ color: #3498db; text-decoration: none; font-size: .85rem; padding: 4px 8px; border-radius: 4px; background: #f1f8ff; }}
  .site-link:hover {{ text-decoration: underline; background: #e1f0fe; }}

  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; padding: 0 4px; }}
  .card {{ display: block; background: #fff; border: 1px solid #e9ecef; border-radius: 8px; overflow: hidden; text-decoration: none; color: inherit; transition: transform .15s, box-shadow .15s; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }}
  .card:hover {{ transform: translateY(-3px); box-shadow: 0 6px 12px rgba(0,0,0,0.08); border-color: #3498db; }}
  .card img {{ width: 100%; aspect-ratio: 1; object-fit: cover; background: #f1f3f5; border-bottom: 1px solid #e9ecef; }}
  .no-img {{ width: 100%; aspect-ratio: 1; display: flex; align-items: center; justify-content: center; background: #f1f3f5; color: #adb5bd; font-size: .8rem; border-bottom: 1px solid #e9ecef; }}
  .info {{ padding: 12px; }}
  .title {{ font-size: .85rem; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 8px; color: #495057; }}
  .price {{ font-size: 1.1rem; font-weight: 700; color: #e74c3c; margin-bottom: 6px; }}
  .badge {{ display: inline-block; font-size: .65rem; padding: 3px 8px; border-radius: 12px; font-weight: 600; }}
  .badge-ヤフオク {{ background: #fdf5e6; color: #d35400; border: 1px solid #fde3c2; }}
  .badge-メルカリ {{ background: #e8f4fd; color: #2980b9; border: 1px solid #d1e8fa; }}
  .badge-ヤフーフリマ {{ background: #f4ebf8; color: #8e44ad; border: 1px solid #e8d5f3; }}
  .empty {{ color: #6c757d; padding: 20px; text-align: center; background: #fff; border-radius: 8px; border: 1px dashed #dee2e6; }}

  .total {{ text-align: center; padding: 16px; color: #6c757d; font-size: .8rem; border-top: 1px solid #e9ecef; margin-top: 20px; }}
</style>
</head>
<body>
  <header>
    <div>
      <h1>🏂 <span>gentemstick</span> 巡回検索結果</h1>
      <div class="meta">¥30,000〜¥90,000 ｜ 最終更新: {now} ｜ 合計 {len(all_items)}件</div>
    </div>
  </header>

  <div class="section">
    <div class="section-header" style="border-left: 4px solid #3498db;">
      <h2>すべての検索結果 (安い順)</h2>
      <div class="site-links">
        <a href="https://auctions.yahoo.co.jp/search/search?p={KEYWORD}&aucminprice={MIN_PRICE}&aucmaxprice={MAX_PRICE}" target="_blank" class="site-link">ヤフオク</a>
        <a href="https://jp.mercari.com/search?keyword={KEYWORD}&price_min={MIN_PRICE}&price_max={MAX_PRICE}" target="_blank" class="site-link">メルカリ</a>
        <a href="https://paypayfleamarket.yahoo.co.jp/search/{KEYWORD}?price_range_begin={MIN_PRICE}&price_range_end={MAX_PRICE}" target="_blank" class="site-link">ヤフーフリマ</a>
      </div>
    </div>
    <div class="grid">{cards}</div>
  </div>

  <div class="total">gentemstick 検索 - ヤフオク / メルカリ / ヤフーフリマ</div>
</body>
</html>'''

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✅ HTMLを出力しました: {OUTPUT_HTML}")


def generate_json(all_items):
    """検索結果をJSONファイルに出力（GitHub Pages用）"""
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    data = {
        "keyword": KEYWORD,
        "minPrice": MIN_PRICE,
        "maxPrice": MAX_PRICE,
        "lastUpdated": now,
        "totalCount": len(all_items),
        "items": all_items,
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ JSONを出力しました: {OUTPUT_JSON}")


def parse_args():
    """コマンドライン引数の解析"""
    parser = argparse.ArgumentParser(description="gentemstick 巡回検索スクリプト")
    parser.add_argument("--keyword", default=KEYWORD, help=f"検索キーワード (default: {KEYWORD})")
    parser.add_argument("--min-price", type=int, default=MIN_PRICE, help=f"最低価格 (default: {MIN_PRICE})")
    parser.add_argument("--max-price", type=int, default=MAX_PRICE, help=f"最高価格 (default: {MAX_PRICE})")
    parser.add_argument("--json-only", action="store_true", help="JSONのみ出力（HTML出力とブラウザ表示をスキップ）")
    return parser.parse_args()


def main():
    global KEYWORD, MIN_PRICE, MAX_PRICE

    args = parse_args()
    KEYWORD = args.keyword
    MIN_PRICE = args.min_price
    MAX_PRICE = args.max_price

    print(f"🔍 {KEYWORD} を検索中... (¥{MIN_PRICE:,}〜¥{MAX_PRICE:,})")
    print()

    all_items = []
    all_items.extend(fetch_yahoo_auction())
    all_items.extend(fetch_mercari())
    all_items.extend(fetch_yahoo_fleamarket())

    print(f"\n取得合計: {len(all_items)}件")

    # 指定の価格帯で厳密にフィルタリング
    filtered_items = []
    for item in all_items:
        price_str = str(item.get("price", ""))
        num_str = re.sub(r"[^\d]", "", price_str)
        if num_str:
            try:
                price = int(num_str)
                if MIN_PRICE <= price <= MAX_PRICE:
                    filtered_items.append(item)
            except ValueError:
                pass

    print(f"フィルタ後: {len(filtered_items)}件")

    # JSON出力（GitHub Pages用）
    generate_json(filtered_items)

    if not args.json_only:
        # HTML出力
        generate_html(filtered_items)

        # HTMLを自動で開く
        if sys.platform == "win32":
            os.startfile(OUTPUT_HTML)
        print("ブラウザで開きました。")
    else:
        print("JSON出力のみ完了。")


if __name__ == "__main__":
    main()
