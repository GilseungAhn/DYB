import streamlit as st
import pandas as pd

from star_pdf_extractor import extract_star_reading_metrics


st.set_page_config(
    page_title="STAR PDF 점수 인식",
    layout="wide",
)


def format_metric_value(value):
    if isinstance(value, dict) and "min" in value and "max" in value:
        return f'{value["min"]} - {value["max"]}'
    return value


st.title("STAR Reading PDF 점수 인식 결과")

uploaded_file = st.file_uploader(
    "PDF 파일을 업로드하세요",
    type=["pdf"],
)

if uploaded_file is not None:
    try:
        result = extract_star_reading_metrics(uploaded_file)

        st.success("PDF에서 점수를 인식했습니다.")

        scores = result.get("scores", {})
        domain_scores = result.get("domain_scores", {})

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

            # Arrow 변환 오류 방지를 위해 문자열로 통일
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

    except Exception as e:
        st.error("PDF 처리 중 오류가 발생했습니다.")
        st.exception(e)

else:
    st.info("PDF를 업로드하면 인식된 점수가 여기에 표시됩니다.")