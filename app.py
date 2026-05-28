import streamlit as st
import pandas as pd

from star_pdf_extractor import extract_star_reading_metrics


st.set_page_config(
    page_title="사랑해요 랜퍼스",
    layout="wide",
)


BOOKS_CSV_PATH = "books.csv"


def format_metric_value(value):
    if isinstance(value, dict) and "min" in value and "max" in value:
        return f'{value["min"]} - {value["max"]}'
    return value


def get_zpd_range(scores):
    zpd = scores.get("ZPD")

    if isinstance(zpd, dict):
        zpd_min = zpd.get("min")
        zpd_max = zpd.get("max")

        if zpd_min is not None and zpd_max is not None:
            return float(zpd_min), float(zpd_max)

    if isinstance(zpd, str) and "-" in zpd:
        left, right = zpd.split("-", 1)
        return float(left.strip()), float(right.strip())

    if isinstance(zpd, (tuple, list)) and len(zpd) == 2:
        return float(zpd[0]), float(zpd[1])

    return None, None


def load_books():
    books = pd.read_csv(BOOKS_CSV_PATH)

    books["atos"] = pd.to_numeric(books["atos"], errors="coerce")
    books = books.dropna(subset=["atos"])

    return books


def filter_books_by_zpd(zpd_min, zpd_max):
    books = load_books()

    recommended_books = books[
        (books["atos"] >= zpd_min) &
        (books["atos"] <= zpd_max)
    ].copy()

    recommended_books = recommended_books.sort_values(
        by=["atos", "title"],
        ascending=[True, True],
    )

    return recommended_books


st.title("사랑해요 랜퍼스")

uploaded_file = st.file_uploader(
    "PDF 파일을 업로드하세요",
    type=["pdf"],
)

if uploaded_file is not None:
    try:
        result = extract_star_reading_metrics(uploaded_file)

        scores = result.get("scores", {})
        domain_scores = result.get("domain_scores", {})

        if scores or domain_scores:
            st.success("PDF에서 점수를 인식했습니다.")

        if scores:
            st.subheader("주요 점수")

            score_df = pd.DataFrame(
                [
                    {
                        "지표": metric,
                        "값": format_metric_value(value),
                    }
                    for metric, value in scores.items()
                ]
            )

            score_df["값"] = score_df["값"].astype(str)

            st.dataframe(
                score_df,
                use_container_width=True,
                hide_index=True,
            )

        if domain_scores:
            st.subheader("도메인 점수")

            domain_df = pd.DataFrame(
                [
                    {
                        "영역": metric,
                        "점수": value,
                    }
                    for metric, value in domain_scores.items()
                ]
            )

            st.dataframe(
                domain_df,
                use_container_width=True,
                hide_index=True,
            )

        if not scores and not domain_scores:
            st.warning("인식된 점수가 없습니다.")

        zpd_min, zpd_max = get_zpd_range(scores)

        if zpd_min is not None and zpd_max is not None:
            st.subheader("추천 도서")

            st.write(
                f"학생의 ZPD 범위는 **{zpd_min} - {zpd_max}** 입니다. "
                "아래 도서는 이 범위 안에 있는 책입니다."
            )

            recommended_books = filter_books_by_zpd(zpd_min, zpd_max)

            if recommended_books.empty:
                st.info("현재 도서 DB에서 해당 ZPD 범위에 맞는 책을 찾지 못했습니다.")
            else:
                display_df = recommended_books.rename(
                    columns={
                        "title": "도서명",
                        "author": "저자",
                        "ar_quiz_no": "AR Quiz No.",
                        "atos": "ATOS",
                        "lexile": "Lexile",
                        "interest_level": "Interest Level",
                        "ar_points": "AR Points",
                    }
                )

                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                )

                csv_data = recommended_books.to_csv(index=False).encode("utf-8-sig")

                st.download_button(
                    label="추천 도서 CSV 다운로드",
                    data=csv_data,
                    file_name="recommended_books.csv",
                    mime="text/csv",
                )

        else:
            st.info("ZPD 점수를 찾지 못해 추천 도서를 표시할 수 없습니다.")

    except FileNotFoundError:
        st.error("books.csv 파일을 찾을 수 없습니다. app.py와 같은 폴더에 books.csv를 넣어주세요.")

    except Exception as e:
        st.error("PDF 처리 중 오류가 발생했습니다.")
        st.write("PDF 파일 형식이나 내용이 올바른지 확인해 주세요.")

else:
    st.info("PDF를 업로드하면 인식된 점수와 추천 도서가 여기에 표시됩니다.")