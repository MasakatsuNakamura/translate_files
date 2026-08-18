# ⚡ Text Processing Toolkit

テキストファイルの**分割・結合・翻訳**をブラウザ上で一括処理できる、モダンで軽量な Streamlit Web アプリケーションです。

レガシーなGUI（Tkinterなど）を排除し、非同期処理（`asyncio`）や Playwright のスマートウェイトを駆使した堅牢で爆速な設計になっています。

---

## ✨ 主な機能

1. **✂️ テキスト分割 (Split)**
   - 大きな `.txt` ファイルを指定した文字数（最大文字数）ごとに自動で綺麗に分割します。
   - 分割されたファイルは個別で即座にダウンロード可能です。
2. **🔗 テキスト結合 (Merge)**
   - 複数の `.txt` ファイルをファイル名の数値順に自動ソートして1つに結合します。
3. **🌐 テキスト翻訳 (Translate)**
   - 複数ファイルを順次自動翻訳。
   - 3つの翻訳エンジンから選択可能：
     - `googletrans (ライブラリ)`
     - `Playwright (内部API通信)` ※ブラウザ非表示で高速
     - `Playwright (画面自動操作)` ※スマートウェイト＆タイムアウト付きで堅牢

---

## 🛠️ 必要要件 (Requirements)

- Python 3.9 以上
- Streamlit
- Playwright

---

## 🚀 インストール & セットアップ手順

リポジトリをクローンまたはダウンロードし、以下の手順でセットアップを行ってください。

### 1. 仮想環境（venv）の作成と有効化

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
