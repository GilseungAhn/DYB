import streamlit as st
import pandas as pd

from star_pdf_extractor import extract_star_reading_metrics


st.set_page_config(
    page_title="예림아 돈벌어보자",
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


def get_pr_level(pr):
    try:
        pr = float(pr)
    except Exception:
        return None

    if pr >= 90:
        return "매우 우수"
    if pr >= 75:
        return "우수"
    if pr >= 50:
        return "평균 이상"
    if pr >= 25:
        return "보통"
    return "집중 관리 필요"


def get_domain_level(score):
    try:
        score = float(score)
    except Exception:
        return "확인 필요"

    if score >= 85:
        return "강점"
    if score >= 70:
        return "양호"
    if score >= 60:
        return "보완 필요"
    return "우선 보완 필요"


def make_score_interpretations(scores):
    rows = []

    if "SS" in scores:
        rows.append({
            "지표": "SS",
            "값": format_metric_value(scores["SS"]),
            "해석": "문항 난이도와 정답 개수를 바탕으로 계산된 STAR Reading의 기본 점수입니다.",
        })

    if "PR" in scores:
        pr_level = get_pr_level(scores["PR"])
        if pr_level:
            meaning = f"같은 학년 학생들과 비교한 백분위 지표입니다. 현재 PR 기준으로는 '{pr_level}' 수준으로 볼 수 있습니다."
        else:
            meaning = "같은 학년 학생들과 비교한 백분위 지표입니다."
        rows.append({
            "지표": "PR",
            "값": format_metric_value(scores["PR"]),
            "해석": meaning,
        })

    if "GE" in scores:
        rows.append({
            "지표": "GE",
            "값": format_metric_value(scores["GE"]),
            "해석": "미국 현지 학생 기준의 읽기 수행 수준을 학년·개월 단위로 보여주는 참고 지표입니다. 독립적으로 해당 학년 책을 모두 읽을 수 있다는 뜻은 아닙니다.",
        })

    if "IRL" in scores:
        rows.append({
            "지표": "IRL",
            "값": format_metric_value(scores["IRL"]),
            "해석": "교사나 학습자의 도움을 받으면서 80% 이상의 이해도를 유지하며 학습할 수 있는 수업용 읽기 수준입니다.",
        })

    if "Est. ORF" in scores:
        rows.append({
            "지표": "Est. ORF",
            "값": format_metric_value(scores["Est. ORF"]),
            "해석": "1분 동안 정확하게 읽을 수 있을 것으로 예상되는 단어 수입니다. 읽기 속도와 정확성을 함께 보는 참고 지표입니다.",
        })

    if "ZPD" in scores:
        rows.append({
            "지표": "ZPD",
            "값": format_metric_value(scores["ZPD"]),
            "해석": "학생의 읽기 성장을 돕기 위한 권장 도서 난이도 범위입니다. 책 추천에는 GE보다 ZPD를 우선 기준으로 사용합니다.",
        })

    return rows


def make_domain_interpretations(domain_scores):
    rows = []
    domain_explanations = {
        "Vocabulary": "어휘와 단어의 의미를 이해하고 활용하는 능력과 관련됩니다.",
        "Literature": "이야기 구조, 등장인물, 배경, 주제 등 문학 텍스트를 이해하는 능력과 관련됩니다.",
        "Informational Text": "정보 글의 중심 내용, 구조, 목적, 근거를 파악하는 능력과 관련됩니다.",
    }

    for domain, score in domain_scores.items():
        level = get_domain_level(score)
        explanation = "읽기 세부 영역의 숙련도를 추정한 점수입니다."

        for key, value in domain_explanations.items():
            if key.lower() in str(domain).lower():
                explanation = value
                break

        rows.append({
            "영역": domain,
            "점수": score,
            "판단": level,
            "해석": explanation,
        })

    return rows


def make_parent_summary(scores, domain_scores):
    messages = []

    pr = scores.get("PR")
    zpd_min, zpd_max = get_zpd_range(scores)

    if pr is not None:
        pr_level = get_pr_level(pr)
        if pr_level:
            messages.append(
                f"현재 학생의 읽기 수준은 같은 학년 기준으로 **{pr_level}** 수준으로 볼 수 있습니다."
            )

    if zpd_min is not None and zpd_max is not None:
        messages.append(
            f"도서 선택은 **ZPD {zpd_min} - {zpd_max}** 범위를 우선 기준으로 보는 것이 좋습니다."
        )

    if domain_scores:
        domain_rows = make_domain_interpretations(domain_scores)
        weak_domains = [
            row["영역"]
            for row in domain_rows
            if row["판단"] in ["보완 필요", "우선 보완 필요"]
        ]
        strong_domains = [
            row["영역"]
            for row in domain_rows
            if row["판단"] == "강점"
        ]

        if strong_domains:
            messages.append(
                "강점 영역은 유지하면서, 같은 수준의 책을 꾸준히 읽어 읽기량을 늘리는 것이 좋습니다."
            )

        if weak_domains:
            messages.append(
                "보완이 필요한 영역은 짧은 글을 읽고 중심 내용 찾기, 근거 찾기, 요약하기 활동을 함께 진행하면 좋습니다."
            )
        else:
            messages.append(
                "뚜렷하게 낮은 영역이 많지 않다면, 현재 수준에 맞는 책을 꾸준히 읽으며 독서 습관을 유지하는 것이 중요합니다."
            )

    if not messages:
        messages.append("인식된 점수를 바탕으로 읽기 수준을 확인했습니다.")

    return messages


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

        if not scores and not domain_scores:
            st.warning("인식된 점수가 없습니다.")

        if scores or domain_scores:
            st.subheader("한눈에 보는 해석")
            for message in make_parent_summary(scores, domain_scores):
                st.markdown(f"- {message}")
            st.caption(
                "※ STAR Reading은 정답 개수나 문항별 피드백보다 전체적인 읽기 능력과 향상도를 확인하는 지표로 보는 것이 좋습니다."
            )

        if scores:
            st.subheader("주요 점수와 해석")
            score_interpretation_df = pd.DataFrame(make_score_interpretations(scores))
            score_interpretation_df["값"] = score_interpretation_df["값"].astype(str)
            st.dataframe(
                score_interpretation_df,
                use_container_width=True,
                hide_index=True,
            )

        if domain_scores:
            st.subheader("도메인 점수와 해석")
            domain_interpretation_df = pd.DataFrame(make_domain_interpretations(domain_scores))
            st.dataframe(
                domain_interpretation_df,
                use_container_width=True,
                hide_index=True,
            )

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

        elif scores:
            st.info("ZPD 점수를 찾지 못해 추천 도서를 표시할 수 없습니다.")

    except FileNotFoundError:
        st.error("books.csv 파일을 찾을 수 없습니다. app.py와 같은 폴더에 books.csv를 넣어주세요.")

    except Exception:
        st.error("PDF 처리 중 오류가 발생했습니다.")
        st.write("PDF 파일 형식이나 내용이 올바른지 확인해 주세요.")

else:
    st.info("PDF를 업로드하면 인식된 점수와 추천 도서가 여기에 표시됩니다.")
