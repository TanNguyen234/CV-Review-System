import re

class CVTextCleaner:
    """
    Utility class to clean and normalize raw text extracted from CV PDFs.
    Handles artifact removal, whitespace normalization, and section detection.
    """
    def __init__(self):
        # Common OCR / PDF artifacts
        self.artifact_patterns = [
            r'==>.*?<==',
            r'----- Start of picture text -----.*?----- End of picture text -----',
            r'\bPage \d+ of \d+\b',
        ]

        # Section headers (Case-insensitive mapping to canonical names)
        self.section_mapping = {
            "OBJECTIVE": ["OBJECTIVE", "SUMMARY", "EXECUTIVE SUMMARY", "PROFILE", "ABOUT ME", "MỤC TIÊU NGHỀ NGHIỆP", "TÓM TẮT", "GIỚI THIỆU"],
            "SKILLS": ["SKILLS", "AREAS OF EXPERTISE", "TECHNICAL SKILLS", "COMPETENCIES", "CORE COMPETENCIES", "KỸ NĂNG", "CHUYÊN MÔN", "KỸ NĂNG CHUYÊN MÔN"],
            "EXPERIENCE": ["EXPERIENCE", "WORK EXPERIENCE", "EMPLOYMENT HISTORY", "PROFESSIONAL EXPERIENCE", "WORK HISTORY", "KINH NGHIỆM LÀM VIỆC", "QUÁ TRÌNH LÀM VIỆC", "KINH NGHIỆM"],
            "EDUCATION": ["EDUCATION", "ACADEMIC BACKGROUND", "QUALIFICATIONS", "HỌC VẤN", "TRÌNH ĐỘ HỌC VẤN", "BẰNG CẤP"],
            "PROJECTS": ["PROJECTS", "PERSONAL PROJECTS", "PRODUCT PORTFOLIO", "KEY PROJECTS", "DỰ ÁN", "DỰ ÁN CÁ NHÂN", "CÁC DỰ ÁN"],
            "CERTIFICATIONS": ["CERTIFICATIONS", "AWARDS", "CERTIFICATES", "CHỨNG CHỈ", "GIẢI THƯỞNG"]
        }
        
        # Flattened keywords for regex matching
        self.all_keywords = [kw for sublist in self.section_mapping.values() for kw in sublist]

    def remove_artifacts(self, text: str) -> str:
        """Removes common PDF/OCR artifacts."""
        for pattern in self.artifact_patterns:
            text = re.sub(pattern, ' ', text, flags=re.DOTALL)
        return text

    def normalize_whitespace(self, text: str) -> str:
        """Collapses multiple spaces but preserves newlines."""
        text = text.replace('\xa0', ' ')
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    def clean_symbols(self, text: str) -> str:
        """Removes non-standard characters."""
        text = re.sub(r'[©«»•]', '', text)
        text = re.sub(r'[\*\|]', ' ', text)
        return text

    def normalize_bullets(self, text: str) -> str:
        """Standardizes bullet points."""
        text = re.sub(r'\s*[-•*]\s*', '\n- ', text)
        return text

    def split_sections(self, text: str) -> str:
        """Injects markers for section splitting."""
        for keyword in self.all_keywords:
            # Match keyword if it's the only thing on a line (ignoring spaces/colons)
            pattern = rf'(?m)^\s*({re.escape(keyword)})\s*(?::)?\s*$'
            # Replace with newline markers for easier splitting later
            text = re.sub(pattern, r'\n\n\1\n', text, flags=re.IGNORECASE)
        return text

    def normalize_dates(self, text: str) -> str:
        """Normalizes common date formats."""
        text = re.sub(r'\b(20)(7\d)\b', r'20\2', text)
        text = re.sub(r'\bto CURRENT\b', '- Present', text, flags=re.IGNORECASE)
        text = re.sub(
            r'(\d{2}/\d{4})\s*(to|-)\s*(\d{2}/\d{4}|Present)',
            r'\1 - \3',
            text
        )
        return text

    def finalize(self, text: str) -> str:
        """Final cleanup of spacing."""
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def clean(self, raw_text: str) -> str:
        """Full cleaning pipeline."""
        text = raw_text
        text = self.remove_artifacts(text)
        text = self.clean_symbols(text)
        text = self.normalize_dates(text)
        text = self.normalize_whitespace(text)
        text = self.normalize_bullets(text)
        text = self.split_sections(text)
        text = self.finalize(text)
        return text
