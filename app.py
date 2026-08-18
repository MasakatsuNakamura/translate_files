import asyncio
import os
import random
import re
from typing import Callable, Optional
import streamlit as st
from googletrans import Translator
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError, async_playwright
from streamlit.runtime.uploaded_file_manager import UploadedFile

# プログレス通知用コールバックの型定義
ProgressCallback = Callable[[int, int, str, str], None]


# -------------------------------------------------------------------
# 1. 翻訳ロジッククラス (FileTranslator)
# -------------------------------------------------------------------
class FileTranslator:
    """翻訳エンジンとファイル翻訳の実行を担当するクラス"""

    def __init__(
        self,
        engine_key: str,
        src_lang: str = "ja",
        dest_lang: str = "en",
        show_browser: bool = False,
    ) -> None:
        self.engine_key: str = engine_key
        self.src_lang: str = src_lang
        self.dest_lang: str = dest_lang
        self.show_browser: bool = show_browser

    async def _translate_by_lib(self, text: str) -> str:
        """googletrans ライブラリによる翻訳"""
        translator = Translator()
        return translator.translate(text, src=self.src_lang, dest=self.dest_lang).text

    async def _translate_by_playwright_api(self, text: str, page: Page) -> str:
        """Playwright内部ネットワーク(page.request)を使用した高速API通信"""
        url = f"https://translate.google.com/translate_a/single?client=gtx&sl={self.src_lang}&tl={self.dest_lang}&dt=t&q={text}"
        response = await page.request.get(url)
        if not response.ok:
            raise RuntimeError(f"HTTP Error: {response.status}")
        data = await response.json()
        return "".join(item[0] for item in data[0] if item[0])

    async def _translate_by_playwright_ui(self, text: str, page: Page) -> str:
        """Playwrightによる画面自動操作（タイムアウト5秒＆スマートウェイト）"""
        TIMEOUT_MS = 5000

        try:
            textarea = page.locator('textarea[aria-label="原文"]')
            await textarea.clear(timeout=TIMEOUT_MS)
            await textarea.fill(text, timeout=TIMEOUT_MS)

            result_span = page.locator('span[jsname="pq348e"]')

            # 固定sleepではなく、翻訳テキストが反映されるまで最大5秒間スマート待機
            await page.wait_for_function(
                """(selector) => {
                    const el = document.querySelector(selector);
                    return el && el.innerText.trim().length > 0;
                }""",
                arg='span[jsname="pq348e"]',
                timeout=TIMEOUT_MS,
            )

            return await result_span.inner_text(timeout=TIMEOUT_MS)

        except PlaywrightTimeoutError:
            raise RuntimeError(
                "Google翻訳の画面操作がタイムアウト（5秒）しました。"
                "画面仕様が変更されたか、ネットワーク接続が遅延しています。"
            )

    async def run(
        self,
        files: list[UploadedFile],
        on_progress: Optional[ProgressCallback] = None,
    ) -> list[tuple[str, str]]:
        """
        設定済みの条件で複数ファイルを順次翻訳・実行する

        Args:
            files: 翻訳対象のファイルリスト (UploadedFile)
            on_progress: 進捗時に呼び出すコールバック関数

        Returns:
            list[tuple[str, str]]: (出力ファイル名, 翻訳テキスト) のリスト
        """
        results: list[tuple[str, str]] = []
        total: int = len(files)
        use_playwright: bool = self.engine_key in ["api", "ui"]

        async def _loop(page: Optional[Page] = None) -> None:
            for idx, file in enumerate(files, start=1):
                if on_progress:
                    on_progress(idx, total, file.name, "翻訳中...")

                text: str = file.read().decode("utf-8")
                if not text.strip():
                    if on_progress:
                        on_progress(idx, total, file.name, "空ファイルのためスキップ")
                    continue

                res_text: str = ""
                if self.engine_key == "lib":
                    res_text = await self._translate_by_lib(text[:5000])
                elif self.engine_key == "api" and page:
                    res_text = await self._translate_by_playwright_api(text[:5000], page)
                elif self.engine_key == "ui" and page:
                    res_text = await self._translate_by_playwright_ui(text[:5000], page)

                results.append((f"translated_{file.name}", res_text))
                await asyncio.sleep(random.uniform(0.5, 1.5))

        if use_playwright:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=not self.show_browser, args=["--no-sandbox"])
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await context.new_page()
                await page.goto(
                    f"https://translate.google.com/?hl=ja&sl={self.src_lang}&tl={self.dest_lang}",
                    wait_until="domcontentloaded",
                )
                await _loop(page)
                await browser.close()
        else:
            await _loop()

        return results


# -------------------------------------------------------------------
# 2. ヘルパー関数
# -------------------------------------------------------------------
def extract_file_number(filename: str) -> int:
    """ファイル名末尾の数値を抽出してソート用に返す"""
    numbers = re.findall(r"\d+", filename)
    return int(numbers[-1]) if numbers else 0


TRANSLATION_ENGINES: dict[str, str] = {
    "googletrans (ライブラリ)": "lib",
    "Playwright (内部API通信)": "api",
    "Playwright (画面自動操作)": "ui",
}


# -------------------------------------------------------------------
# 3. Streamlit UI 構築
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Text Processing Toolkit",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Text Processing Toolkit")
st.caption("テキストファイルの分割・結合・翻訳を一括で処理するモダンWebツール")

tab_split, tab_merge, tab_translate = st.tabs([
    "✂️ テキスト分割 (Split)", 
    "🔗 テキスト結合 (Merge)", 
    "🌐 テキスト翻訳 (Translate)"
])

# --- タブ 1: 分割 (Split) ---
with tab_split:
    st.header("テキストファイルの分割")
    uploaded_file = st.file_uploader("分割したい `.txt` ファイルを選択", type=["txt"], key="split_file")
    max_chars = st.number_input("1ファイルあたりの最大文字数", min_value=100, max_value=50000, value=5000, step=500)

    if st.button("分割を実行する", type="primary", disabled=not uploaded_file):
        content = uploaded_file.read().decode("utf-8")
        base_name = os.path.splitext(uploaded_file.name)[0]

        chunks: list[str] = []
        current_chunk: list[str] = []
        current_len: int = 0

        for line in content.splitlines(keepends=True):
            line_len = len(line)
            if current_len + line_len > max_chars and current_chunk:
                chunks.append("".join(current_chunk))
                current_chunk = [line]
                current_len = line_len
            else:
                current_chunk.append(line)
                current_len += line_len

        if current_chunk:
            chunks.append("".join(current_chunk))

        st.success(f"全 {len(chunks)} 件に分割されました！")

        cols = st.columns(3)
        for idx, chunk in enumerate(chunks, start=1):
            file_name = f"{base_name}_{idx}.txt"
            cols[(idx - 1) % 3].download_button(
                label=f"💾 {file_name} ({len(chunk)}文字)",
                data=chunk,
                file_name=file_name,
                mime="text/plain",
                key=f"dl_split_{idx}",
            )

# --- タブ 2: 結合 (Merge) ---
with tab_merge:
    st.header("複数テキストファイルの結合")
    uploaded_files = st.file_uploader(
        "結合したい複数の `.txt` ファイルを選択",
        type=["txt"],
        accept_multiple_files=True,
        key="merge_files",
    )

    if uploaded_files:
        sorted_files = sorted(uploaded_files, key=lambda f: extract_file_number(f.name))
        st.write("▼ 以下の順序で結合されます:")
        st.code("\n".join([f.name for f in sorted_files]))

        if st.button("結合を実行する", type="primary"):
            merged_content = "".join([f.read().decode("utf-8") for f in sorted_files])
            st.success(f"結合完了！ 合計文字数: {len(merged_content)} 文字")
            st.download_button(
                label="💾 結合されたファイルをダウンロード",
                data=merged_content,
                file_name="merged_output.txt",
                mime="text/plain",
            )

# --- タブ 3: 翻訳 (Translate) ---
with tab_translate:
    st.header("テキストファイルの翻訳")
    trans_files = st.file_uploader(
        "翻訳したい `.txt` ファイルを選択 (複数可)",
        type=["txt"],
        accept_multiple_files=True,
        key="trans_files",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        src_lang = st.text_input("翻訳元言語コード", value="ja")
    with col2:
        dest_lang = st.text_input("翻訳先言語コード", value="en")
    with col3:
        selected_engine_label = st.selectbox("翻訳エンジン", list(TRANSLATION_ENGINES.keys()))

    show_browser = st.checkbox("ブラウザ画面を表示して実行（Playwrightモード時のみ）", value=False)

    if st.button("翻訳を開始する", type="primary", disabled=not trans_files):
        sorted_trans_files = sorted(trans_files, key=lambda f: extract_file_number(f.name))
        engine_key = TRANSLATION_ENGINES[selected_engine_label]

        progress_bar = st.progress(0)
        status_area = st.status("翻訳処理を開始します...", expanded=True)

        # UI更新用のコールバック関数
        def update_ui(idx: int, total: int, filename: str, message: str) -> None:
            status_area.write(f"[{idx}/{total}] {filename}: {message}")
            progress_bar.progress(idx / total)

        # 1. 翻訳クラスをインスタンス化
        translator = FileTranslator(
            engine_key=engine_key,
            src_lang=src_lang,
            dest_lang=dest_lang,
            show_browser=show_browser,
        )

        # 2. 実行 (run)
        try:
            translated_results = asyncio.run(
                translator.run(sorted_trans_files, on_progress=update_ui)
            )
            status_area.update(label="すべての翻訳処理が完了しました！", state="complete")

            st.subheader("📥 翻訳結果のダウンロード")
            dl_cols = st.columns(3)
            for idx, (filename, text_data) in enumerate(translated_results):
                dl_cols[idx % 3].download_button(
                    label=f"💾 {filename}",
                    data=text_data,
                    file_name=filename,
                    mime="text/plain",
                    key=f"dl_trans_{idx}",
                )
        except Exception as e:
            status_area.update(label="エラーが発生しました", state="error")
            st.error(f"処理中にエラーが発生しました: {e}")