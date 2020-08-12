import requests
import urllib.parse
import lxml.html as lh

# Raised when the MediaWiki API returns an error.
class MediaWikiError(Exception):
    def __init__(self, message, errors):
        super(MediaWikiError, self).__init__(message)
        self.errors = errors

# Raised when a loop is detected.
class LoopException(Exception):
    pass

# Raised when an invalid page name is passed to trace().
class InvalidPageNameError(Exception):
    pass

# Raised when no valid link is found after parsing.
class LinkNotFoundError(Exception):
    pass

# Checks for valid mainspace Wikipedia page name
def valid_page_name(page):
    NON_MAINSPACE = ['File:',
                     'File talk:',
                     'Wikipedia:',
                     'Wikipedia talk:',
                     'Project:',
                     'Project talk:',
                     'Portal:',
                     'Portal talk:',
                     'Special:',
                     'Help:',
                     'Help talk:',
                     'Template:',
                     'Template talk:',
                     'Talk:',
                     'Category:',
                     'Category talk:']
    return all(not page.startswith(non_main) for non_main in NON_MAINSPACE)

# Remove parentheses from a string, leaving parentheses between <tags> in place.
def remove_parentheses(string):
    nested_parentheses = nesting_level = 0
    result = ''
    for c in string:
        # When outside of parentheses within <tags>
        if nested_parentheses < 1:
            if c == '<':
                nesting_level += 1
            if c == '>':
                nesting_level -= 1

        # When outside of <tags>
        if nesting_level < 1:
            if c == '(':
                nested_parentheses += 1
            if nested_parentheses < 1:
                result += c
            if c == ')':
                nested_parentheses -= 1

        # When inside of <tags>
        else:
            result += c

    return result

# Used to store pages that have been visited in order to detect loops
visited = []

def get_input():
    url = input("Enter the Wikipedia link: ")
    # Exracting the page title from the text.
    content = requests.get(url).text
    index = content.find('</h1>')
    i = 2
    page = content[index - 1]
    while content[index - i] != '>':
        page = content[index - i] + page
        i = i + 1

    return page

# Visits the first non-italicized, not-within-parentheses link of page recursively until the page Philosophy is reached.
def crawl(page=None, end='Philosophy', whole_page=False):
    BASE_URL = 'https://en.wikipedia.org/w/api.php'
    HEADERS = {'User-Agent': 'The Philosophy Game/1.0.0',
               'Accept-Encoding': 'gzip'}
    if page is None:
        rand_page = 'https://en.wikipedia.org/wiki/Special:Random'
        # Extracting the page title from the text.
        content = requests.get(rand_page).text
        index = content.find('</h1>')
        i = 2
        page = content[index - 1]
        while content[index - i] != '>':
            page = content[index - i] + page
            i = i + 1

    if not valid_page_name(page):
        del visited[:]
        raise InvalidPageNameError("Invalid page name: {0!r}".format(page))

    params = {
        'action': 'parse',
        'page': page,
        'prop': 'text',
        'format': 'json',
        'redirects': 1
    }
    if not whole_page:
        params['section'] = 0

    result = requests.get(BASE_URL, params=params, headers=HEADERS).json()

    if 'error' in result:
        del visited[:]
        raise MediaWikiError('MediaWiki error', result['error'])

    page = result['parse']['title']

    # Detect loop
    if page in visited:
        yield page
        del visited[:]
        raise LoopException('Loop detected')

    # This makes sure that we don't yield `page` a second time
    # (whole_page = True indicates that `page` has been processed once already)
    if not whole_page:
        yield page

    # Normal termination
    if page == end:
        del visited[:]
        return

    raw_html = result['parse']['text']['*']
    html = lh.fromstring(raw_html)

    # This takes care of most MediaWiki templates,images, red links, hatnotes,
    # italicized text and anything that's strictly not text-only.
    for elm in html.cssselect('.reference,span,div,.thumb,table,a.new,i,#coordinates'):
        elm.drop_tree()

    html = lh.fromstring(remove_parentheses(lh.tostring(html).decode('utf-8')))
    link_found = False

    for elm, attr, link, pos in html.iterlinks():
        # If the element is not an anchor tag, skip.
        if attr != 'href':
            continue

        next_page = link

        if not next_page.startswith('/wiki/'):
            continue

        next_page = next_page[6:]
        next_page = urllib.parse.unquote(next_page)

        # If page name not valid, skip.
        if not valid_page_name(next_page):
            continue

        # Links use an underscore ('_') instead of a space (' '), this fixes that.
        next_page = next_page.replace('_', ' ')

        # Eliminate named anchor, if any
        pos = next_page.find('#')
        if pos != -1:
            next_page = next_page[:pos]

        link_found = True
        visited.append(page)

        for m in crawl(page=next_page, end=end):
            yield m

        break

    # If link not found in the first section, search the whole page.
    if not link_found:
        if whole_page:
            del visited[:]
            raise LinkNotFoundError(
                'No valid link found in page "{0}"'.format(page)
            )
        else:
            for m in crawl(page=page, end=end, whole_page=True):
                yield m
