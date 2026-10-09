import logging
import re
from pathlib import Path
from typing import Dict, List

import PyPDF2
import pytesseract
from docx import Document
from pdf2image import convert_from_path
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)


class OCRService:
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """
        Extract text dari PDF file.

        Args:
            file_path: Path ke PDF file

        Returns:
            Extracted text
        """
        try:
            logger.info(f"Extracting text from PDF: {file_path}")

            text = ""

            # Coba PyPDF2 terlebih dahulu (faster untuk text-based PDF)
            try:
                with open(file_path, "rb") as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"

                if text.strip():
                    return text
            except Exception as e:
                logger.warning(
                    f"PyPDF2 extraction failed: {e}, trying OCR..."
                )

            # Fallback ke OCR jika PDF text-based extraction gagal (scanned PDF)
            images = convert_from_path(
                file_path,
                dpi=settings.PDF_DPI,
                first_page=1,
                last_page=None,
            )

            for i, image in enumerate(images):
                logger.info(f"Processing PDF page {i + 1}")
                page_text = pytesseract.image_to_string(image)
                text += page_text + "\n"

            return text.strip()

        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise

    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """Extract text dari DOCX file."""
        try:
            logger.info(f"Extracting text from DOCX: {file_path}")

            doc = Document(file_path)
            text = ""

            for para in doc.paragraphs:
                if para.text.strip():
                    text += para.text + "\n"

            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text += cell.text + " "
                    text += "\n"

            return text.strip()

        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {str(e)}")
            raise

    @staticmethod
    def extract_text(file_path: str, file_type: str) -> str:
        """Extract text dari file berdasarkan tipe ('pdf' atau 'docx')."""
        if file_type.lower() == "pdf":
            return OCRService.extract_text_from_pdf(file_path)
        elif file_type.lower() == "docx":
            return OCRService.extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")


class CVParsingService:
    """Service untuk parsing CV data dari extracted text."""

    # Header section yang sering tertangkap sebagai nama oleh heuristic lama
    _SECTION_HEADERS = {
        "education",
        "experience",
        "work experience",
        "professional experience",
        "skills",
        "technical skills",
        "profile",
        "professional summary",
        "summary",
        "objective",
        "about",
        "contact",
        "projects",
        "certifications",
        "languages",
        "achievements",
        "awards",
        "references",
        "qualifications",
        "interests",
        "publications",
        "personal information",
        "pendidikan",
        "pengalaman",
        "pengalaman kerja",
        "keahlian",
        "keterampilan",
        "ringkasan",
        "profil",
        "tentang",
        "proyek",
        "sertifikasi",
        "bahasa",
    }

    # Kata-kata yang jarang muncul di baris nama; dipakai untuk menyaring
    # baris seperti "Bachelor of Computer Science" atau "Software Engineer".
    _NON_NAME_WORDS = {
        "bachelor",
        "master",
        "phd",
        "doctorate",
        "degree",
        "diploma",
        "computer",
        "science",
        "informatics",
        "engineering",
        "technology",
        "information",
        "system",
        "systems",
        "university",
        "college",
        "school",
        "academy",
        "institute",
        "institut",
        "software",
        "engineer",
        "developer",
        "programmer",
        "analyst",
        "manager",
        "consultant",
        "specialist",
        "lead",
        "senior",
        "junior",
        "summary",
        "profile",
        "objective",
        "experience",
        "work",
        "employment",
        "education",
        "skills",
        "projects",
        "certifications",
        "languages",
        "references",
        "contact",
        "about",
        "professional",
        "personal",
        "years",
        "year",
        "month",
        "months",
        "pengalaman",
        "kerja",
        "tahun",
        "bulan",
        "pendidikan",
        "keahlian",
        "keterampilan",
        "profil",
        "ringkasan",
        "s1",
        "s2",
        "s3",
        "d3",
        "d4",
        "smk",
        "sma",
        "of",
        "in",
        "and",
        "the",
        "at",
        "with",
        "for",
    }

    # Sinonim skill → canonical; multi-word didahulukan saat pencarian
    _SKILL_SYNONYMS = {
        # languages
        "python": "python",
        "py": "python",
        "javascript": "javascript",
        "js": "javascript",
        "typescript": "typescript",
        "ts": "typescript",
        "java": "java",
        "c++": "c++",
        "cpp": "c++",
        "c#": "c#",
        "csharp": "c#",
        "php": "php",
        "ruby": "ruby",
        "go": "go",
        "golang": "go",
        "rust": "rust",
        "sql": "sql",
        # frameworks
        "django": "django",
        "flask": "flask",
        "fastapi": "fastapi",
        "fast api": "fastapi",
        "react": "react",
        "reactjs": "react",
        "vue": "vue",
        "vuejs": "vue",
        "angular": "angular",
        "spring": "spring",
        "spring boot": "spring boot",
        "springboot": "spring boot",
        "asp.net": "asp.net",
        "express": "express",
        "expressjs": "express",
        "node": "node.js",
        "nodejs": "node.js",
        "node.js": "node.js",
        "next.js": "next.js",
        "nextjs": "next.js",
        "nestjs": "nestjs",
        "laravel": "laravel",
        "bootstrap": "bootstrap",
        "tailwind css": "tailwind css",
        "tailwind": "tailwind css",
        "html": "html",
        "css": "css",
        "sass": "sass",
        "less": "less",
        "jquery": "jquery",
        "webpack": "webpack",
        "vite": "vite",
        # databases
        "mysql": "mysql",
        "postgresql": "postgresql",
        "postgres": "postgresql",
        "mongodb": "mongodb",
        "redis": "redis",
        "elasticsearch": "elasticsearch",
        "dynamodb": "dynamodb",
        "oracle": "oracle",
        # tools / cloud
        "git": "git",
        "docker": "docker",
        "kubernetes": "kubernetes",
        "k8s": "kubernetes",
        "jenkins": "jenkins",
        "ci/cd": "ci/cd",
        "cicd": "ci/cd",
        "aws": "aws",
        "amazon web services": "aws",
        "gcp": "gcp",
        "google cloud": "gcp",
        "azure": "azure",
        "linux": "linux",
        # data / ml
        "pandas": "pandas",
        "numpy": "numpy",
        "scikit-learn": "scikit-learn",
        "tensorflow": "tensorflow",
        "pytorch": "pytorch",
        "spark": "spark",
        "hadoop": "hadoop",
        # others
        "graphql": "graphql",
        "rest api": "rest api",
        "restful": "rest api",
        "openapi": "openapi",
        "swagger": "swagger",
        "tableau": "tableau",
        "power bi": "power bi",
        "powerbi": "power bi",
        "excel": "excel",
    }

    @staticmethod
    def _is_likely_name(line: str) -> bool:
        """Heuristic sederhana untuk membedakan nama dengan header/URL."""
        stripped = line.strip()
        if not stripped:
            return False
        if len(stripped) < 3 or len(stripped) > 80:
            return False

        lower = stripped.lower()
        if lower in CVParsingService._SECTION_HEADERS:
            return False

        # Lewati baris yang mengandung URL/email/telepon/simbol CV
        if any(token in lower for token in [
            "|", "@", "http", "www", "github.com", "linkedin", "portfolio",
            "tel:", "+", ":", "/",
        ]):
            return False

        if re.search(r"\d", stripped):
            return False

        # Minimal 50% karakter alfabet
        if sum(1 for c in stripped if c.isalpha()) < len(stripped) * 0.5:
            return False

        words = stripped.split()
        # Satu kata UPPERCASE sering header section
        if len(words) == 1 and stripped.isupper():
            return False

        # Lewati baris yang mengandung kata-kata non-nama
        if any(w.lower() in CVParsingService._NON_NAME_WORDS for w in words):
            return False

        return True

    @staticmethod
    def extract_name(text: str) -> str:
        """Extract nama dari CV text dengan filter header section."""
        lines = text.split("\n")

        # Coba 20 baris pertama, lewati header
        for line in lines[:20]:
            if CVParsingService._is_likely_name(line):
                return line.strip()[:100]

        # Cari di seluruh dokumen
        for line in lines:
            if CVParsingService._is_likely_name(line):
                return line.strip()[:100]

        # Fallback terakhir: baris pertama yang tidak kosong
        for line in lines:
            if line.strip():
                return line.strip()[:100]

        return "Unknown"

    @staticmethod
    def extract_email(text: str) -> str:
        """Extract email dari CV text."""
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        matches = re.findall(email_pattern, text)
        return matches[0] if matches else ""

    @staticmethod
    def extract_phone(text: str) -> str:
        """Extract nomor telepon dari CV text."""
        phone_patterns = [
            r"\+62\s?[\d\s\-]{9,}",
            r"62[\d\s\-]{9,}",
            r"\+\d{1,3}[\d\s\-]{9,}",
            r"[\d\s\-]{10,}",
        ]

        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0].replace(" ", "").replace("-", "")

        return ""

    @staticmethod
    def extract_experience_years(text: str) -> int:
        """Extract pengalaman kerja (tahun) dari CV text (EN & ID)."""
        patterns = [
            # English
            r"(\d+)\s+(?:years?|yrs?)\s+(?:of\s+)?(?:work|experience)",
            r"(?:work|experience).*?(\d+)\s+(?:years?|yrs?)",
            r"(\d+)\s+years?",
            # Indonesian
            r"(\d+)\s+(?:tahun|thn).*?(?:pengalaman|kerja)",
            r"(?:pengalaman|kerja).*?(\d+)\s+(?:tahun|thn)",
            r"pengalaman\s+(?:kerja\s+)?(\d+)\s+(?:tahun|thn)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    years = int(matches[0])
                    if 0 <= years <= 70:
                        return years
                except ValueError:
                    pass

        return 0

    @staticmethod
    def extract_education(text: str) -> str:
        """Extract informasi pendidikan dari CV text (EN & ID)."""
        education_keywords = [
            "bachelor",
            "master",
            "phd",
            "diploma",
            "b.s.",
            "m.s.",
            "b.a.",
            "m.a.",
            "degree",
            "university",
            "college",
            "s1",
            "s2",
            "s3",
            "d3",
            "d4",
            "sarjana",
            "magister",
            "doktor",
            "smk",
            "sma",
            "sekolah",
            "universitas",
            "institut",
            "akademi",
        ]

        lines = text.split("\n")
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in education_keywords):
                return line.strip()[:255]

        return ""

    @staticmethod
    def extract_skills(text: str) -> List[str]:
        """Extract skills dari CV text dengan normalisasi sinonim."""
        text_lower = text.lower()
        found = []

        # Urutkan dari sinonim terpanjang supaya "fast api" tidak kalah dari "fast"
        synonyms = sorted(
            CVParsingService._SKILL_SYNONYMS.keys(), key=len, reverse=True
        )

        for synonym in synonyms:
            pattern = r"(?<!\w)" + re.escape(synonym) + r"(?!\w)"
            if re.search(pattern, text_lower):
                canonical = CVParsingService._SKILL_SYNONYMS[synonym]
                if canonical not in found:
                    found.append(canonical)

        return found[:25]

    @staticmethod
    def parse_cv(text: str) -> Dict:
        """Parse CV text dan extract semua informasi."""
        logger.info("Parsing CV data...")

        parsed_data = {
            "name": CVParsingService.extract_name(text),
            "email": CVParsingService.extract_email(text),
            "phone": CVParsingService.extract_phone(text),
            "experience_years": CVParsingService.extract_experience_years(text),
            "education": CVParsingService.extract_education(text),
            "skills": CVParsingService.extract_skills(text),
            "cv_text": text[:5000],
        }

        logger.info(f"CV parsing completed: {parsed_data['name']}")
        return parsed_data


class CVProcessingService:
    """Service untuk complete CV processing pipeline."""

    @staticmethod
    def process_cv_file(file_path: str, file_type: str) -> Dict:
        """
        Process CV file: extract text dan parse data.

        Args:
            file_path: Path ke CV file
            file_type: Tipe file ('pdf' atau 'docx')

        Returns:
            Dictionary dengan parsed CV data
        """
        logger.info(f"Processing CV file: {file_path}")

        text = OCRService.extract_text(file_path, file_type)
        logger.info(f"Extracted {len(text)} characters from CV")

        return CVParsingService.parse_cv(text)