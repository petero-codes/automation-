import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IDLE_TIMEOUT  = 120        # seconds idle before automation starts
TOTAL_RUNTIME = 10 * 3600  # max runtime (10 hours)
LOG_FILE      = str(BASE_DIR / 'idle_automation.log')
AUTO_LAUNCH_LOGGY = False  # Set to False: will NOT launch Loggy on startup, on ESC, or during 120s wait

SHORTS_URL = 'www.youtube.com/shorts'

WIKI_URLS = [
    'en.wikipedia.org/wiki/Special:Random',
    'en.wikipedia.org/wiki/Special:Random',
    'en.wikipedia.org/wiki/Special:Random',
    'simple.wikipedia.org/wiki/Special:Random',
]

TECH_NEWS_URLS = [
    'news.ycombinator.com/',
    'arstechnica.com/',
    'www.theverge.com/',
    'www.wired.com/',
    'techcrunch.com/',
    'www.engadget.com/',
    'www.bbc.com/news/technology',
    'www.technologyreview.com/',
    'thenextweb.com/',
    'www.scientificamerican.com/technology/',
]

REDDIT_URLS = [
    'www.reddit.com/r/technology/',
    'www.reddit.com/r/science/',
    'www.reddit.com/r/worldnews/',
    'www.reddit.com/r/programming/',
    'www.reddit.com/r/todayilearned/',
    'www.reddit.com/r/explainlikeimfive/',
    'www.reddit.com/r/Futurology/',
    'www.reddit.com/r/dataisbeautiful/',
]

GITHUB_URLS = [
    'github.com/trending',
    'github.com/trending/python',
    'github.com/trending/javascript',
    'github.com/explore',
]

NOVEL_URLS = [
    'www.gutenberg.org/cache/epub/1342/pg1342-images.html',
    'www.gutenberg.org/cache/epub/84/pg84-images.html',
    'www.gutenberg.org/cache/epub/74/pg74-images.html',
    'www.gutenberg.org/cache/epub/1661/pg1661-images.html',
    'www.gutenberg.org/cache/epub/2701/pg2701-images.html',
    'www.gutenberg.org/cache/epub/98/pg98-images.html',
    'www.gutenberg.org/cache/epub/11/pg11-images.html',
    'www.gutenberg.org/cache/epub/1260/pg1260-images.html',
    'www.gutenberg.org/cache/epub/5200/pg5200-images.html',
    'www.gutenberg.org/cache/epub/16/pg16-images.html',
    'www.gutenberg.org/cache/epub/345/pg345-images.html',
    'www.gutenberg.org/cache/epub/219/pg219-images.html',
]

ESSAY_TOPICS = [
    "The rapid advancement of artificial intelligence has fundamentally altered how we approach problem solving across every major industry. From predictive diagnostics in medicine to dynamic pricing in retail, machine learning systems now handle decisions that once required years of human expertise.\n\nYet this transformation is not without its shadows. The concentration of AI capability in the hands of a few large technology companies raises genuine concerns about power, accountability, and the democratisation of opportunity.\n\nWhat is needed is not a slowdown of innovation, but a maturation of governance. Open research, auditable systems, and internationally coordinated policy frameworks could allow society to capture the benefits of AI while distributing its risks fairly.\n\n",
    "Climate science is unambiguous: the planet is warming at a rate unprecedented in the last ten thousand years, and human industrial activity is the primary driver. The consequences range from more frequent extreme weather events to rising sea levels that threaten coastal cities on every continent.\n\nThe economic case for rapid decarbonisation is now stronger than the case against it. Renewable energy costs have collapsed over the past decade. Battery storage is following the same trajectory. The industries of the green economy represent the largest employment opportunity of the coming generation.\n\n",
    "The history of computing is a history of abstraction. Each generation of engineers built a higher floor for the next to stand on. Assembly language abstracted machine code. High-level languages abstracted assembly. Garbage collection abstracted memory management.\n\nToday, large language models are beginning to abstract natural language itself into executable computation. A developer can describe intent in plain English and receive working code. This is not a replacement for programming skill, it is a new and powerful tool that amplifies it.\n\n",
]

# Diverse Multi-Genre & E-Commerce / Shopping URLs (25+ Sites)
SHOPPING_AND_EXPLORE_URLS = [
    # E-Commerce & Online Marketplaces
    'www.jumia.com/',
    'www.alibaba.com/',
    'www.aliexpress.com/',
    'www.amazon.com/',
    'www.ebay.com/',
    'www.etsy.com/',
    'www.target.com/',
    # Tech Specs, Gadgets & Reviews
    'www.gsmarena.com/',
    'www.producthunt.com/',
    'www.cnet.com/',
    # Guides, Q&A & Knowledge
    'www.quora.com/',
    'medium.com/',
    'www.wikihow.com/',
    'www.instructables.com/',
    # Travel & Exploration
    'www.booking.com/',
    'www.tripadvisor.com/',
    'www.nationalgeographic.com/',
    'www.lonelyplanet.com/',
    # Lifestyle, Entertainment & Culture
    'www.imdb.com/',
    'www.goodreads.com/',
    'www.allrecipes.com/',
    'www.healthline.com/',
    # Creative, Design & Science
    'www.behance.net/',
    'dribbble.com/',
    'www.nature.com/',
    'www.ted.com/',
]

# notch_range, pause_range, back_prob, distract_prob, distract_range
SCROLL_PROFILES = {
    'reading':  ((1, 3), (2.5, 6.5),  0.10, 0.02, (6.0, 12.0)),
    'scanning': ((2, 5), (1.0, 3.5),  0.05, 0.01, (4.0, 8.0)),
    'novel':    ((1, 2), (3.5, 8.5),  0.12, 0.03, (8.0, 15.0)),
    'reddit':   ((2, 4), (2.0, 5.0),  0.08, 0.02, (5.0, 10.0)),
    'github':   ((1, 3), (2.0, 6.0),  0.08, 0.02, (5.0, 10.0)),
    'code':     ((1, 2), (2.0, 6.0),  0.10, 0.02, (5.0, 10.0)),
    'shopping': ((1, 4), (1.5, 4.5),  0.14, 0.03, (5.0, 10.0)),
}
