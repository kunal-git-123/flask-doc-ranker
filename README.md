# flask-doc-ranker

A minimalist Flask-based web app for structured document review, live topic browsing, and BM25-powered ranking and AJAX-enhanced navigation.

## Features
- Document editing with change tracking
- Sentence-by-sentence formatting
- Dynamic topic listing via AJAX
- BM25-powered document scoring and updates

## Usage

Start app.py from command prompt or shell. Navigate to `http://localhost:5000` and explore documents by topic, search query, or direct edit. All changes will be go through an additional check and will be automatically indexed. Add new topic and it will be saved as a json file under the first tag name.


## Installation

```bash
git clone https://github.com/kunal-git-123/flask-doc-ranker.git
cd flask-doc-ranker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Author
Built with ❤️ by [Kunal](https://github.com/kunal-git-123) and Bing Copilot ✨  
Inspired by clean UI, sharp indexing, and a shared joy in minimalist design.
