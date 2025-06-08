import os
import pytest
from html.parser import HTMLParser

class SimpleHTMLParser(HTMLParser):
    """Simple parser to ensure HTML can be parsed."""
    pass

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))


def discover_html_files():
    html_files = []
    for root, _, files in os.walk(REPO_ROOT):
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
    return html_files


@pytest.mark.parametrize('html_file', discover_html_files())
def test_html_parses(html_file):
    parser = SimpleHTMLParser()
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    try:
        parser.feed(content)
    except Exception as exc:
        pytest.fail(f'Could not parse {html_file}: {exc}')


def test_links_in_index_exist():
    index_path = os.path.join(REPO_ROOT, 'index.html')
    parser = SimpleHTMLParser()
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()
    parser.feed(content)
    links = []
    class LinkParser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                for attr, value in attrs:
                    if attr == 'href' and value.endswith('.html'):
                        links.append(value)
    link_parser = LinkParser()
    link_parser.feed(content)
    missing = [link for link in links if not os.path.exists(os.path.join(REPO_ROOT, link))]
    assert not missing, f'Missing pages referenced in index.html: {missing}'
