# 🏂 Gentemstick Search Hub

ヤフオク・メルカリ・ヤフーフリマの **gentemstick** 出品をまとめて検索するツール。

## 機能

- 🔍 3サイト横断検索（ヤフオク / メルカリ / ヤフーフリマ）
- 💰 価格帯フィルタ（UI上で自由に変更可能）
- 🔤 検索キーワード変更（UI上で自由に変更可能）
- 📊 サイト別フィルタ / 価格ソート
- ⏰ GitHub Actionsで6時間ごとに自動更新

## GitHub Pages

1. このリポジトリをGitHubにpush
2. Settings → Pages → Source: `GitHub Actions` を選択
3. Actions タブから `Scrape & Deploy` を手動実行
4. 自動で `data.json` が生成されてデプロイされます

## ローカル実行

```bash
# デフォルト（gentemstick, ¥30,000〜¥90,000）
python gentemstick_search.py

# パラメータ指定
python gentemstick_search.py --keyword "gentemstick" --min-price 20000 --max-price 100000

# JSONのみ出力（GitHub Actions用）
python gentemstick_search.py --json-only
```

## 必要パッケージ

```bash
pip install requests beautifulsoup4 playwright
playwright install chromium
```
