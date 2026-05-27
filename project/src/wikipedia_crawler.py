import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import quote

from utils import normalize_text


class WikipediaCrawler:

    def __init__(self):

        self.base_url = "https://vi.wikipedia.org/wiki/"

        # Reuse TCP connection
        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        })

        # Remove citation patterns
        self.citation_pattern = re.compile(
            r"\[\d+\]|\[[a-zA-Z]+\]|\[cần dẫn nguồn\]"
        )

        # Ignore noisy sections
        self.ignored_sections = {
            "Xem thêm",
            "Tham khảo",
            "Liên kết ngoài",
            "Ghi chú",
            "Chú thích",
            "Tài liệu tham khảo"
        }

    # =====================================
    # CLEAN TEXT
    # =====================================

    def clean_text(self, text):

        if not text:
            return ""

        # Remove citations
        text = self.citation_pattern.sub("", text)

        # Normalize spaces
        text = normalize_text(text)

        return text.strip()

    # =====================================
    # CRAWL PAGE
    # =====================================

    def crawl_page(self, title):

        try:

            # =====================================
            # BUILD URL
            # =====================================

            url = (
                self.base_url
                + quote(title.replace(" ", "_"))
            )

            print(f"\n[CRAWL URL] {url}")

            # =====================================
            # REQUEST
            # =====================================

            response = self.session.get(
                url,
                timeout=20
            )

            print("[STATUS CODE]", response.status_code)

            if response.status_code != 200:

                print("[ERROR] Request failed")

                return []

            # =====================================
            # PARSE HTML
            # =====================================

            soup = BeautifulSoup(
                response.text,
                "lxml"
            )

            print("[HTML LENGTH]", len(response.text))

            # =====================================
            # FIND MAIN CONTENT
            # =====================================

            content_div = soup.select_one(
                "div#mw-content-text .mw-parser-output"
            )

            if content_div is None:

                print("[ERROR] content_div = None")

                return []

            # =====================================
            # REMOVE NOISY BLOCKS
            # =====================================

            garbage_selectors = [
                "table",
                "style",
                "script",
                ".infobox",
                ".navbox",
                ".vertical-navbox",
                ".reference",
                ".reflist",
                ".thumb",
                ".toc",
                ".metadata",
                ".mw-editsection",
                ".mbox-small"
            ]

            garbage_nodes = content_div.select(
                ",".join(garbage_selectors)
            )

            for node in garbage_nodes:

                try:
                    node.decompose()

                except Exception:
                    pass

            # =====================================
            # EXTRACT TAGS
            # =====================================

            tags = content_div.find_all(
                ["h2", "h3", "p"]
            )

            print("[TAG COUNT]", len(tags))

            sections = []

            current_section = "Giới thiệu"

            current_text = []

            # =====================================
            # PROCESS TAGS
            # =====================================

            for tag in tags:

                # -----------------------------
                # SECTION TITLE
                # -----------------------------

                if tag.name in ["h2", "h3"]:

                    # Save previous section
                    if current_text:

                        joined_text = self.clean_text(
                            " ".join(current_text)
                        )

                        if (
                            len(joined_text) > 50
                            and current_section
                            not in self.ignored_sections
                        ):

                            sections.append({
                                "section":
                                current_section,

                                "text":
                                joined_text
                            })

                    # Update section name
                    current_section = self.clean_text(
                        tag.get_text(" ", strip=True)
                    )

                    current_text = []

                # -----------------------------
                # PARAGRAPH
                # -----------------------------

                elif tag.name == "p":

                    text = self.clean_text(
                        tag.get_text(" ", strip=True)
                    )

                    # Skip short/noisy paragraph
                    if len(text) > 30:

                        current_text.append(text)

            # =====================================
            # LAST SECTION
            # =====================================

            if current_text:

                joined_text = self.clean_text(
                    " ".join(current_text)
                )

                if (
                    len(joined_text) > 50
                    and current_section
                    not in self.ignored_sections
                ):

                    sections.append({
                        "section":
                        current_section,

                        "text":
                        joined_text
                    })

            # =====================================
            # DEBUG
            # =====================================

            print("[SECTIONS FOUND]", len(sections))

            if sections:

                print("[FIRST SECTION SAMPLE]")
                print(sections[0])

            return sections

        except Exception as e:

            print(f"[CRAWL ERROR] {e}")

            return []