from wikipedia_crawler import (
    WikipediaCrawler
)

crawler = WikipediaCrawler()

sections = crawler.crawl_page(
    "Phố cổ Hội An"
)

print("\nFINAL RESULT")
print(sections)