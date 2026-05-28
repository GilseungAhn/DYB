# star_pdf_extractor.py
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any, BinaryIO


def _to_text(pdf_input: str | Path | bytes | BinaryIO) -> str:
    """
    PDF에서 텍스트를 추출합니다.

    지원 입력:
    - 파일 경로(str, Path)
    - bytes
    - Streamlit UploadedFile 같은 file-like 객체

    우선 pypdf를 사용하고, 필요하면 pdfplumber로 보완합니다.
    스캔본 PDF처럼 텍스트 레이어가 없는 경우에는 OCR이 별도로 필요합니다.
    """
    def read_with_pypdf(source: Any) -> str:
        from pypdf import PdfReader

        reader = PdfReader(source)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def read_with_pdfplumber(source: Any) -> str:
        import pdfplumber

        with pdfplumber.open(source) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)

    # file-like 객체는 한 번 읽으면 포인터가 이동하므로 bytes로 고정
    if hasattr(pdf_input, "read") and not isinstance(pdf_input, (str, Path, bytes, bytearray)):
        data = pdf_input.read()
        try:
            pdf_input.seek(0)
        except Exception:
            pass
        pdf_input = data

    if isinstance(pdf_input, (bytes, bytearray)):
        bio = io.BytesIO(pdf_input)
        try:
            text = read_with_pypdf(bio)
        except Exception:
            bio.seek(0)
            text = read_with_pdfplumber(bio)

        if not text.strip():
            bio.seek(0)
            text = read_with_pdfplumber(bio)
        return _normalize_text(text)

    path = Path(pdf_input)
    try:
        text = read_with_pypdf(str(path))
    except Exception:
        text = read_with_pdfplumber(str(path))

    if not text.strip():
        text = read_with_pdfplumber(str(path))

    return _normalize_text(text)


def _normalize_text(text: str) -> str:
    """PDF 추출 텍스트에서 자주 생기는 깨짐/공백 문제를 정리합니다."""
    text = text.replace("\u02bc", "'").replace("\u2019", "'").replace("\ufffe", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _first(pattern: str, text: str, flags: int = re.I | re.S) -> str | None:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _num(value: str | None) -> int | float | str | None:
    """숫자 문자열을 int/float로 변환합니다. 범위값은 문자열로 유지합니다."""
    if value is None:
        return None
    value = value.strip()
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def _extract_standard_scores(text: str) -> dict[str, Any]:
    """
    STAR Reading 리포트의 대표 지표를 추출합니다.
    반환 key는 원본 약어를 유지합니다.
    """
    patterns = {
        "SS": r"\bSS\s*\n?\s*\(Scaled Score\)\s*([0-9]+(?:\.[0-9]+)?)",
        "PR": r"\bPR\s*\n?\s*\(Percentile Rank\)\s*([0-9]+(?:\.[0-9]+)?)",
        "GE": r"\bGE\s*\n?\s*\(Grade Equivalent\)\s*([0-9]+(?:\.[0-9]+)?)",
        "IRL": r"\bIRL\s*\n?\s*\(Instructional Reading Level\)\s*([0-9]+(?:\.[0-9]+)?)",
        "Est. ORF": r"\bEst\.\s*ORF\s*\n?\s*\(Estimated Oral Fluency\)\s*([0-9]+(?:\.[0-9]+)?)",
        "ZPD": r"\bZPD\s*\n?\s*\(Zone of Proximal\s+Development\)\s*([0-9]+(?:\.[0-9]+)?\s*-\s*[0-9]+(?:\.[0-9]+)?)",
    }

    out: dict[str, Any] = {}
    for key, pattern in patterns.items():
        value = _first(pattern, text)
        if value is not None:
            out[key] = _num(value)
    return out


def _extract_domain_scores(text: str) -> dict[str, int]:
    """
    Domain Scores 영역의 하위 지표를 추출합니다.
    PDF 추출 과정에서 줄바꿈이 섞여도 잡히도록 패턴을 느슨하게 둡니다.
    """
    domain_patterns = {
        "Literature - Comprehension of Elements and Ideas":
            r"Comprehension of Elements and\s+Ideas\s+([0-9]{1,3})",
        "Literature - Structure, Genre, and Author's Craft":
            r"Structure,\s*Genre,\s*and\s*Author's\s+Craft\s+([0-9]{1,3})",
        "Informational Text - Comprehension of Information and Ideas":
            r"Comprehension of Information\s+and\s+Ideas\s+([0-9]{1,3})",
        "Informational Text - Organization, Purpose, and Language Use":
            r"Organization,\s*Purpose,\s*and\s+Language Use\s+([0-9]{1,3})",
        "Informational Text - Analysis, Evaluation, and Extending Meaning":
            r"Analysis,\s*Evaluation,\s*and\s+Extending Meaning\s+([0-9]{1,3})",
        "Vocabulary - Vocabulary Development":
            r"Vocabulary Development\s+([0-9]{1,3})",
    }

    out: dict[str, int] = {}
    for key, pattern in domain_patterns.items():
        value = _first(pattern, text)
        if value is not None:
            out[key] = int(value)
    return out


def _extract_metadata(text: str) -> dict[str, Any]:
    """리포트 상단의 기본 정보와 시험 시간을 추출합니다."""
    fields = {
        "school": r"School\s*\n?\s*(.+?)\s+Students",
        "students": r"Students\s*\n?\s*(.+?)\s+Date Range",
        "date_range": r"Date Range\s*\n?\s*([0-9/]+[–-][0-9/]+)",
        "test_date": r"Test Date\s*\n?\s*(.+?)\s+Grade",
        "grade": r"Grade\s*\n?\s*([0-9A-Za-z.+-]+)",
        "teacher": r"Teacher\s*\n?\s*(.+?)\s+Class/Group",
        "class_group": r"Class/Group\s*\n?\s*(.+?)\s+Star Reading Enterprise Tests Scores",
        "benchmark_status": r"\bSS\s*\n?\s*\(Scaled Score\)\s*[0-9.]+\s*\n?\s*([A-Za-z/@ ]+Benchmark)",
        "test_duration": r"Test Duration:\s*([0-9]+\s*mins?\s*and\s*[0-9]+\s*secs?)",
    }

    out: dict[str, Any] = {}
    for key, pattern in fields.items():
        value = _first(pattern, text)
        if value is not None:
            out[key] = re.sub(r"\s+", " ", value).strip()
    return out


def extract_star_reading_metrics(pdf_input: str | Path | bytes | BinaryIO) -> dict[str, Any]:
    """
    STAR Reading PDF 리포트에서 숫자 지표를 dictionary로 추출합니다.

    Returns 예시:
    {
        "metadata": {...},
        "scores": {"SS": 898, "PR": 90, "GE": 2.5, "IRL": 1.9, ...},
        "domain_scores": {...},
        "all_metrics": {...}
    }
    """
    text = _to_text(pdf_input)

    scores = _extract_standard_scores(text)
    domain_scores = _extract_domain_scores(text)
    metadata = _extract_metadata(text)

    # 한 곳에서 바로 쓰기 쉬운 flat dictionary
    all_metrics = {
        **scores,
        **domain_scores,
    }

    return {
        "metadata": metadata,
        "scores": scores,
        "domain_scores": domain_scores,
        "all_metrics": all_metrics,
        "raw_text": text,  # 디버깅용. 운영에서 불필요하면 삭제해도 됩니다.
    }


if __name__ == "__main__":
    # 로컬 테스트용:
    # python star_pdf_extractor.py sample.pdf
    import json
    import sys

    if len(sys.argv) < 2:
        raise SystemExit("사용법: python star_pdf_extractor.py sample.pdf")

    result = extract_star_reading_metrics(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
