import streamlit as st
import PyPDF2
import io
import os
import sys

# 再帰制限を緩和
sys.setrecursionlimit(10000)

def process_large_pdf(input_path, pages_per_split):
    """大容量PDFを分割する（最適化版）"""
    def create_pdf_part(start_page, end_page, reader):
        """PDFの一部を作成"""
        writer = PyPDF2.PdfWriter()
        for page_num in range(start_page, end_page):
            try:
                writer.add_page(reader.pages[page_num])
            except Exception as e:
                print(f"ページ {page_num} の処理中にエラーが発生: {e}")
                continue
        return writer

    # PDFファイルを読み込む
    reader = PyPDF2.PdfReader(input_path, strict=False)
    total_pages = len(reader.pages)
    num_splits = (total_pages + pages_per_split - 1) // pages_per_split

    for i in range(num_splits):
        start_page = i * pages_per_split
        end_page = min((i + 1) * pages_per_split, total_pages)

        try:
            # 分割されたPDFを作成
            output_pdf = create_pdf_part(start_page, end_page, reader)
            
            # メモリストリームに書き出し
            output_stream = io.BytesIO()
            output_pdf.write(output_stream)
            output_stream.seek(0)
            
            # 結果を返す
            yield output_stream
            
            # メモリを解放
            del output_pdf
            del output_stream
            
        except Exception as e:
            print(f"セクション {i+1} の処理中にエラーが発生: {e}")
            continue

@st.cache_resource(show_spinner=False)
def get_pdf_info(pdf_path):
    """PDFファイルの情報を取得（キャッシュ付き）"""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file, strict=False)
        return len(reader.pages)

def main():
    st.set_page_config(
        page_title="PDFlex",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🎯 PDFlex - Flexible PDF Splitter")
    st.write("PDFファイルを指定した枚数で分割することができます。")
    st.write("使用方法: `streamlit run app.py -- input.pdf`")

    if len(sys.argv) < 2:
        st.error("PDFファイルのパスを指定してください。")
        st.write("例: `streamlit run app.py -- path/to/large.pdf`")
        return

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        st.error(f"指定されたファイルが見つかりません: {pdf_path}")
        return

    try:
        with st.spinner("PDFファイルを解析中..."):
            # ファイルサイズを計算
            file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
            
            # PDFの基本情報を取得（キャッシュ利用）
            total_pages = get_pdf_info(pdf_path)
            
            # 情報を表示
            col1, col2 = st.columns(2)
            with col1:
                st.metric("ファイルサイズ", f"{file_size_mb:.1f}MB")
            with col2:
                st.metric("総ページ数", f"{total_pages}ページ")
        
        # 分割ページ数の入力
        pages_per_split = st.number_input(
            "分割するページ数を指定してください",
            min_value=1,
            max_value=total_pages,
            value=min(total_pages, 10)
        )
        
        output_dir = "split_output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        if st.button("分割実行"):
            with st.spinner("PDFを分割中..."):
                try:
                    # プログレスバーを初期化
                    progress_text = st.empty()
                    progress_bar = st.progress(0)
                    
                    # 分割回数を計算
                    num_splits = (total_pages + pages_per_split - 1) // pages_per_split
                    
                    # PDFを分割してファイルに保存
                    st.write("### 分割したPDFファイル")
                    for i, split_pdf in enumerate(process_large_pdf(pdf_path, pages_per_split), 1):
                        # プログレスバーを更新
                        progress = int(i * 100 / num_splits)
                        progress_text.text(f"処理中... {progress}%")
                        progress_bar.progress(progress)
                        
                        # 分割ファイルを保存
                        output_path = os.path.join(output_dir, f"split_{i}.pdf")
                        with open(output_path, 'wb') as f:
                            f.write(split_pdf.getvalue())
                        
                        # ダウンロードボタンを作成
                        with open(output_path, 'rb') as f:
                            st.download_button(
                                label=f"分割ファイル {i} をダウンロード",
                                data=f,
                                file_name=f"split_{i}.pdf",
                                mime="application/pdf"
                            )
                    
                    progress_bar.empty()
                    progress_text.empty()
                    st.success(f"分割が完了しました！ファイルは {output_dir} ディレクトリに保存されています。")
                
                except Exception as e:
                    st.error(f"分割処理中にエラーが発生しました: {str(e)}")
    
    except Exception as e:
        st.error(f"ファイルの読み込み中にエラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main()
