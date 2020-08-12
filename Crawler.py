from utilities import *
import time
import sys
try:
    # Prompting user to input Wikipedia link.
    title = get_input()
    # Printing the article title of the first link in each article.
    for page in crawl(page=title):
        print(page)
        time.sleep(0.5)
except ConnectionError:
    sys.exit('Network error, please check your connection')
except MediaWikiError as e:
    sys.exit('MediaWiki API error {0}: {1}'.format(e.errors['code'],e.errors['info']))
except LoopException:
    sys.exit('Loop detected, exiting...')
except InvalidPageNameError as e:
    sys.exit(e)
except LinkNotFoundError as e:
    sys.exit(e)
