import re

from loguru import logger

from flexget import plugin
from flexget.entry import Entry
from flexget.event import event
from flexget.utils.requests import RequestException
from flexget.utils.soup import get_soup

logger = logger.bind(name='estrenosgo')


class EstrenosGO:
    """
    EstrenosGO search plugin.
    """

    schema = {'type': 'boolean', 'default': False}

    base_url = 'https://estrenosgo.in/'
    errors = False

    @plugin.internet(logger)
    def search(self, task, entry, config):
        """
        Search for entries on EstrenosGO
        """

        entries = set()
        logger.debug('Using EstrenosGO!')

        for search_string in entry.get('search_strings', [entry['title']]):
            logger.debug('Search string: {}', search_string)
            # Remove characters after the last space
            # As the search engine is not very good
            cleaned_search_string = re.sub(r'(?<=\s)\S*$', '', search_string)
            logger.debug('Using search: {}', cleaned_search_string)

            query = '/buscar/{0}'.format(cleaned_search_string)
            pageURL = self.base_url + query

            try:
                logger.debug('requesting: {}', pageURL)
                page = task.requests.get(self.base_url + query)
            except RequestException as e:
                logger.error('EstrenosGO request failed: {}', e)
                continue

            soup = get_soup(page.content)

            cardBody = soup.find('div', attrs={'class': 'card-body'})
            # Get p elements without class (Every result is in a p element)
            pElements = cardBody.find_all('p', attrs={'class': False})
            # For each result
            for pElement in pElements:
                # Get the first span element
                spanElement = pElement.find('span')
                # Get the link with class text-decoration-none
                aElement = spanElement.find('a', attrs={'class': 'text-decoration-none'})
                href = aElement.get('href')
               
                if 'serie' in href:
                    qualitySpanElement = spanElement.find('span')
                    title = aElement.text
                    quality = qualitySpanElement.text
                    
                    pageURL = self.base_url + href
                    try:
                        logger.debug('requesting: {}', pageURL)
                        page = task.requests.get(self.base_url + href)
                    except RequestException as e:
                        logger.error('EstrenosGO request failed: {}', e)
                        continue

                    soup = get_soup(page.content)

                    # Get the list of episodes from the table in the page
                    for tr in soup.find('tbody').findAll('tr'):
                        # Episode id is in the first td text
                        episode = tr.find('td').text
                        # Then get the link to the torrent
                        link = tr.find('a', attrs={'class': 'text-white bg-primary rounded-pill d-block shadow-sm text-decoration-none my-1 py-1'})
                        url = link.get('href')
                        logger.debug('Found torrent link: {}', url)
                        # If the url does not starts with http nor https, append https
                        if not url.startswith('http'):
                            url = 'https:' + url
                            logger.debug('Formatted torrent link: {}', url)
                        
                        # Set the title of the entry
                        epTitle = title + ' ' + episode + ' ' + quality

                        e = Entry()

                        e['url'] = url
                        e['title'] = epTitle
                        e['quality'] = quality

                        logger.debug('Found entry: {}', e)

                        entries.add(e)
                else:
                    logger.warning('Not a series link: {}', href)
                    logger.warning('Skipping...')
        return entries


@event('plugin.register')
def register_plugin():
    plugin.register(EstrenosGO, 'estrenosgo', interfaces=['search'], api_ver=2)
