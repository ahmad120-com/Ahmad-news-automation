import re
import urllib.request
import xml.etree.ElementTree as ET

from urllib.parse import urlparse
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


app = Flask(__name__)

REGISTRATION = "FA23-BDS-048"
NEWS_SOURCE_NAME = "Al Jazeera Media Network"
NEWS_SOURCE_URL = "https://www.aljazeera.com"

RSS_FEEDS = [
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://rsshub.app/aljazeera/english/tag/science-and-technology"
]


def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    return webdriver.Chrome(options=options)


def find_article_link(keyword):
    keyword_words = re.findall(r"[a-z0-9]+", keyword.lower())

    if not keyword_words:
        raise Exception("Please provide a valid search keyword.")

    articles = {}

    for rss_url in RSS_FEEDS:
        try:
            rss_request = urllib.request.Request(
                rss_url,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(rss_request, timeout=30) as response:
                root = ET.fromstring(response.read())

            for item in root.findall(".//item"):
                title = item.findtext("title", "").strip()
                article_url = item.findtext("link", "").strip()
                description = item.findtext("description", "").strip()

                if not title or not article_url:
                    continue

                parsed_url = urlparse(article_url)

                if parsed_url.netloc.lower() not in (
                    "www.aljazeera.com",
                    "aljazeera.com"
                ):
                    continue

                if "/video/" in parsed_url.path.lower():
                    continue

                searchable_text = re.sub(
                    r"[^a-z0-9]+",
                    " ",
                    title.lower() + " " + description.lower()
                )

                score = sum(
                    1 for word in keyword_words
                    if word in searchable_text
                )

                if score > 0:
                    articles[article_url] = (
                        score,
                        title,
                        article_url
                    )

        except Exception as error:
            print(f"RSS feed unavailable: {rss_url}: {error}")

    if not articles:
        raise Exception(
            f"No Al Jazeera article matching '{keyword}' "
            "was found in the available RSS feeds."
        )

    matches = list(articles.values())

    matches.sort(
        key=lambda article: (
            article[0],
            sum(
                1 for word in keyword_words
                if word in article[1].lower()
            )
        ),
        reverse=True
    )

    _, title, article_url = matches[0]

    return title, article_url


def extract_article(article_url):
    driver = create_driver()

    try:
        driver.get(article_url)

        WebDriverWait(driver, 25).until(
            lambda d: d.execute_script(
                "return document.readyState"
            ) == "complete"
        )

        soup = BeautifulSoup(
            driver.page_source,
            "html.parser"
        )

        for element in soup([
            "script",
            "style",
            "nav",
            "header",
            "footer",
            "aside"
        ]):
            element.decompose()

        paragraphs = soup.find_all("p")

        article_paragraphs = []

        for paragraph in paragraphs:
            text = paragraph.get_text(" ", strip=True)

            if len(text) > 40:
                article_paragraphs.append(text)

        article_text = " ".join(article_paragraphs)

        if not article_text:
            raise Exception(
                "Could not extract article text from Al Jazeera."
            )

        return article_text

    finally:
        driver.quit()


def summarize_article(article_text):
    sentences = re.split(
        r"(?<=[.!?])\s+",
        article_text.strip()
    )

    summary = " ".join(sentences[:4])

    return summary[:1200]


@app.route("/", methods=["GET"])
def home():
    return f"""
    <html>
        <head>
            <title>News Automation API</title>
        </head>
        <body>
            <h1>News Automation API</h1>
            <p>Registration Number: {REGISTRATION}</p>
            <p>News Source: {NEWS_SOURCE_NAME}</p>
            <p>News Source URL: {NEWS_SOURCE_URL}</p>
            <p>API Endpoint: /get?keyword=technology</p>
        </body>
    </html>
    """


@app.route("/get", methods=["GET"])
def get_news():
    keyword = request.args.get("keyword", "").strip()

    if not keyword:
        return jsonify({
            "error": "Please provide a keyword."
        }), 400

    try:
        title, article_url = find_article_link(keyword)

        article_text = extract_article(article_url)

        summary = summarize_article(article_text)

        return jsonify({
            "registration": REGISTRATION,
            "newssource": NEWS_SOURCE_NAME,
            "keyword": keyword,
            "url": article_url,
            "summary": summary
        })

    except Exception as error:
        print(f"API error: {error}")

        return jsonify({
            "error": str(error)
        }), 502


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=7000
    )
