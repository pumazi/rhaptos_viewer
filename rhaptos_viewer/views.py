# -*- coding: utf-8 -*-
import urllib
import urllib2
from urlparse import urljoin, urlparse
from opensearch import Client as OpenSearchClient
from BeautifulSoup import BeautifulSoup
from pyramid.view import view_config


REPO_HOST = 'cnx.org'
REPO_PORT = 80
OPENSEARCH_URL = 'http://%s:%s/opensearchdescription' % (REPO_HOST, REPO_PORT)
SITE_TITLE = 'Connexions Web Viewer'

def _fix_url(url):
    """Fix a URL to put to this webview rather than the repository."""
    parts = urlparse(url)
    path = parts.path.split('/')
    if path[1] != 'content':
        return url
    id, version = path[:4][-2:]
    path = ['', 'content', '%s@%s' % (id, version)]
    return '/'.join(path)

@view_config(route_name='casa', renderer='casa.jinja2')
def casa(request):
    """The home page for this application."""
    return {'title': SITE_TITLE}

@view_config(route_name='search', renderer='search.jinja2')
def search(request):
    """Search the repository for the given terms."""
    client = OpenSearchClient(OPENSEARCH_URL)
    terms = urllib.unquote(request.params.get('q', '')).decode('utf8')
    results = client.search(terms)
    records = []
    for result in results:
        records.append({'title': result.title,
                        'link': _fix_url(result.link),
                        'summary': result.summary_detail['value'],
                        })
    return {'records': records,
            'q': terms,
            }

@view_config(route_name='module', renderer='module.jinja2')
def module(request):
    module_id = request.matchdict['id']
    module_version = 'latest'
    if '@' in module_id:
        module_id, module_version = module_id.split('@')

    # Request the content from the repository.
    url = 'http://%s:%s/content/%s/%s/' % (REPO_HOST, REPO_PORT,
                                          module_id, module_version)
    title = urllib2.urlopen(url + 'Title').read()
    body = urllib2.urlopen(url + 'body').read()

    soup = BeautifulSoup(body)
    # Transform the relative resource links to point to the origin.
    for img in soup.findAll('img'):
        src = img['src']
        if src.startswith('http'):
            continue
        img['src'] = urljoin(url, src)

    # Transform the relative links to point to the correct local
    # address
    for a in soup.findAll('a'):
        href = a.get('href')
        if not href or href.startswith('#') or href.startswith('http'):
            continue
        # Massage the path into this app's URL scheme.
        href = href.rstrip('/')
        path = href.split('/')

        if path[0] != '':
            # Handle resources like .jar files.
            href = urljoin(url, href)
        elif path[1] == 'content':
            # Handles links to other modules.
            version = path.pop()
            href = "%s@%s" % ('/'.join(path), version)
        else:
            # Hopefully everything else falls into this category but
            # I'm doubtful.
            href = urljoin(url, href)
        a['href'] = href

    return {'title': SITE_TITLE,
            'module_title': title,
            'module_body': str(soup),
            }
