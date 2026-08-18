import time
import concurrent.futures
from deep_translator import GoogleTranslator
from deep_translator.exceptions import RequestError
import pandas as pd
import streamlit as st
import charset_normalizer

# ページ設定
st.set_page_config(
    page_title="長文翻訳ツール", page_icon="🌐", layout="centered"
)

# 言語の選択肢（主要なもの）
SUPPORTED_LANGUAGES = {
    "英語 (English)": "en",
    "日本語 (Japanese)": "ja",
    "中国語（簡体字）": "zh-CN",
    "中国語（繁体字）": "zh-TW",
    "韓国語 (Korean)": "ko",
    "フランス語 (French)": "fr",
    "スペイン語 (Spanish)": "es",
    "ドイツ語 (German)": "de",
    "イタリア語 (Italian)": "it",
    "ポルトガル語 (Portuguese)": "pt",
    "ロシア語 (Russian)": "ru",
    "ベトナム語 (Vietnamese)": "vi",
    "タイ語 (Thai)": "th",
    "インドネシア語 (Indonesian)": "id",
}


def translate_chunk(text: str, source_lang: str, target_lang: str) -> str:
  """単一のテキストチャンクを指定された言語に翻訳する関数（リトライ・レートリミット対策付き）"""
  if not text.strip():
    return ""

  max_retries = 3
  backoff_factor = 2

  for attempt in range(max_retries):
    try:
      # Google翻訳のインスタンス生成
      translator = GoogleTranslator(source=source_lang, target=target_lang)
      translated = translator.translate(text)
      # レートリミット回避のためのわずかなウェイト
      time.sleep(0.1)
      return translated
    except RequestError as e:
      # 制限超過やネットワークエラー時の指数バックオフ
      if attempt < max_retries - 1:
        sleep_time = backoff_factor**attempt
        time.sleep(sleep_time)
      else:
        return f"[翻訳エラー: 制限または通信エラー] {text}"
    except Exception as e:
      return f"[エラー] {str(e)}"

  return text


def split_text_into_chunks(text: str, max_chars: int = 400) -> list:
  """長文を適切な文字数（Google翻訳の制限内）の段落や文に分割する"""
  paragraphs = text.split("\n")
  chunks = []
  current_chunk = ""

  for para in paragraphs:
    # 1段落が長すぎる場合はさらに句点等で分割するか、文字数で区切る
    if len(current_chunk) + len(para) + 1 < max_chars:
      current_chunk += para + "\n"
    else:
      if current_chunk:
        chunks.append(current_chunk.strip())
      current_chunk = para + "\n"

  if current_chunk:
    chunks.append(current_chunk.strip())

  return chunks


# --- UIデザイン ---
st.title("🌐 高速長文翻訳ツール")
st.write(
    "テキストファイルやCSVをアップロードして、Google翻訳（無償版）で並列かつ高速に翻訳します。"
)

with st.sidebar:
  st.header("⚙️ 翻訳設定")

  source_name = st.selectbox(
      "元言語", list(SUPPORTED_LANGUAGES.keys()), index=0
  )  # デフォルト: 英語
  target_name = st.selectbox(
      "翻訳先言語", list(SUPPORTED_LANGUAGES.keys()), index=1
  )  # デフォルト: 日本語

  source_lang = SUPPORTED_LANGUAGES[source_name]
  target_lang = SUPPORTED_LANGUAGES[target_name]

  st.markdown("---")
  st.info(
      "💡 **ヒント**\n\n- 無償版APIの制限（Rate Limit）を考慮し、並列スレッド数とリクエスト間隔を調整しています。"
  )

# メインコンテンツ：ファイルアップロード
uploaded_file = st.file_uploader(
    "翻訳するファイルを選択してください（対応形式: .txt, .csv）",
    type=["txt", "csv"],
)

if uploaded_file is not None:
  file_extension = uploaded_file.name.split(".")[-1].lower()

  if file_extension == "txt":
    raw_bytes = uploaded_file.read()
    # 文字コードの自動判定
    detected = charset_normalizer.detect(raw_bytes)
    encoding = detected.get("encoding") or "utf-8"
    try:
      raw_text = raw_bytes.decode(encoding, errors="ignore")
    except Exception:
      raw_text = raw_bytes.decode("utf-8", errors="ignore")

  elif file_extension == "csv":
    # CSVの場合はpandasに任せるか、必要に応じてencodingを指定
    uploaded_file.seek(0)
    try:
      df = pd.read_csv(uploaded_file, encoding="utf-8")
    except UnicodeDecodeError:
      uploaded_file.seek(0)
      df = pd.read_csv(uploaded_file, encoding="shift-jis")
    raw_text = "\n".join(df.iloc[:, 0].astype(str).tolist())

  if raw_text:
    st.subheader("📄 アップロードされたファイルのプレビュー")
    st.text_area("元テキスト（冒頭）", raw_text[:1000] + "...", height=150)

    if st.button("🚀 翻訳を実行する", type="primary"):
      with st.spinner("翻訳処理を実行中...（並列処理中）"):
        # テキストを適切なチャンクに分割
        chunks = split_text_into_chunks(raw_text, max_chars=400)
        total_chunks = len(chunks)

        progress_bar = st.progress(0)
        status_text = st.empty()

        translated_chunks = ["" * total_chunks] * total_chunks

        # 並列処理 (ThreadPoolExecutor) で高速化
        # 無償版の制限（Too Many Requests）を回避するため、同時実行数は控えめ（例: 4〜5スレッド）に設定
        max_workers = 4

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers
        ) as executor:
          # 各チャンクの翻訳タスクをサブミット
          future_to_index = {
              executor.submit(
                  translate_chunk, chunk, source_lang, target_lang
              ): i
              for i, chunk in enumerate(chunks)
          }

          completed = 0
          for future in concurrent.futures.as_completed(future_to_index):
            idx = future_to_index[future]
            try:
              translated_chunks[idx] = future.result()
            except Exception as exc:
              translated_chunks[idx] = f"[エラー: {exc}]"

            completed += 1
            progress_bar.progress(completed / total_chunks)
            status_text.text(
                f"進捗: {completed} / {total_chunks} チャンク完了"
            )

        # 翻訳結果の結合
        final_translated_text = "\n\n".join(translated_chunks)

        st.success("✨ 翻訳が完了しました！")

        # 結果の表示とダウンロード
        st.subheader("📝 翻訳結果")
        st.text_area(
            "翻訳後テキスト", final_translated_text, height=300
        )

        st.download_button(
            label="💾 翻訳結果をテキストファイルでダウンロード",
            data=final_translated_text.encode("utf-8"),
            file_name=f"translated_{target_lang}.txt",
            mime="text/plain",
        )