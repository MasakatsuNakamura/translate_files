# ⚡ Text Processing Toolkit

テキストファイルの分割・結合・翻訳をブラウザ上で一括処理できる、モダンで軽量な Streamlit Web アプリケーションです。

レガシーなGUI（Tkinterなど）を排除し、非同期処理（asyncio）や Playwright のスマートウェイトを駆使した堅牢で爆速な設計になっています。

---

## ✨ 主な機能

1. ✂️ テキスト分割 (Split)

* 大きな .txt ファイルを指定した文字数（最大文字数）ごとに自動で綺麗に分割します。
* 分割されたファイルは個別で即座にダウンロード可能です。


2. 🔗 テキスト結合 (Merge)

* 複数の .txt ファイルをファイル名の数値順に自動ソートして1つに結合します。


3. 🌐 テキスト翻訳 (Translate)

* 複数ファイルを順次自動翻訳。
* 3つの翻訳エンジンから選択可能：
* googletrans (ライブラリ)
* Playwright (内部API通信) ※ブラウザ非表示で高速
* Playwright (画面自動操作) ※スマートウェイト＆タイムアウト付きで堅牢

---

## 🛠️ 必要要件 (Requirements)

* Python 3.9 以上
* Streamlit
* Playwright

---

## 🚀 インストール & セットアップ手順

リポジトリをクローンまたはダウンロードし、以下の手順でセットアップを行ってください。

### 1. 仮想環境（venv）の作成と有効化

macOS / Linux の場合:

```
python -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell) の場合:

```
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. 依存ライブラリのインストール

```
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Playwright 用ブラウザのインストール

```
playwright install chromium
```

---

## 💻 使い方 (Run)

仮想環境を有効化した状態で、以下のコマンドを実行します。

streamlit run app.py

ブラウザが自動で立ち上がり（または指定のURLにアクセスし）、モダンな Web UI 操作画面が表示されます。

---

## 📦 依存関係 (requirements.txt)

```
streamlit
googletrans==4.0.0-rc1
playwright
```

---

## 👨‍💻 アーキテクチャのこだわり

* UI と ビジネスロジックの分離: 翻訳処理は独立した FileTranslator クラス（オブジェクト指向）にカプセル化。
* スマートウェイト: 固定の sleep を廃止し、Playwright の wait_for_function で必要な瞬間に即座に処理を進める爆速設計。
* 堅牢な例外処理: ネットワーク遅延や画面仕様変更によるタイムアウト（5秒）を適切にキャッチしてクラッシュを防止。
* 型ヒント完備: Python の型アノテーション（Type Hints）を導入し、保守性とエディタ補完を最大化。