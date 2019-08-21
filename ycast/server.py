import logging

from flask import Flask, request, url_for

import ycast.vtuner as vtuner
import ycast.radiobrowser as radiobrowser
import ycast.my_stations as my_stations


PATH_ROOT = 'ycast'
PATH_SEARCH = 'search'
PATH_MY_STATIONS = 'my_stations'
PATH_RADIOBROWSER = 'radiobrowser'
PATH_RADIOBROWSER_COUNTRY = 'country'
PATH_RADIOBROWSER_LANGUAGE = 'language'
PATH_RADIOBROWSER_GENRE = 'genre'
PATH_RADIOBROWSER_POPULAR = 'popular'

my_stations_enabled = False
app = Flask(__name__)


def run(config, address='0.0.0.0', port=8010):
    try:
        check_my_stations_feature(config)
        app.run(host=address, port=port)
    except PermissionError:
        logging.error("No permission to create socket. Are you trying to use ports below 1024 without elevated rights?")


def check_my_stations_feature(config):
    global my_stations_enabled
    my_stations_enabled = my_stations.set_config(config)


def get_directories_page(subdir, directories, requestargs):
    page = vtuner.Page()
    if len(directories) == 0:
        page.add(vtuner.Display("No entries found."))
        return page
    for directory in get_paged_elements(directories, requestargs):
        vtuner_directory = vtuner.Directory(directory.name, url_for(subdir, _external=True, directory=directory.name),
                                            directory.item_count)
        page.add(vtuner_directory)
    page.set_count(len(directories))
    return page


def get_stations_page(stations, requestargs):
    page = vtuner.Page()
    if len(stations) == 0:
        page.add(vtuner.Display("No stations found."))
        return page
    for station in get_paged_elements(stations, requestargs):
        page.add(station.to_vtuner())
    page.set_count(len(stations))
    return page


def get_paged_elements(items, requestargs):
    if requestargs.get('startitems'):
        offset = int(requestargs.get('startitems')) - 1
    elif requestargs.get('start'):
        offset = int(requestargs.get('start')) - 1
    else:
        offset = 0
    if offset > len(items):
        logging.warning("Paging offset larger than item count")
        return []
    if requestargs.get('enditems'):
        limit = int(requestargs.get('enditems'))
    elif requestargs.get('start') and requestargs.get('howmany'):
        limit = int(requestargs.get('start')) - 1 + int(requestargs.get('howmany'))
    else:
        limit = len(items)
    if limit < offset:
        logging.warning("Paging limit smaller than offset")
        return []
    if limit > len(items):
        limit = len(items)
    return items[offset:limit]


@app.route('/', defaults={'path': ''})
@app.route('/setupapp/<path:path>')
@app.route('/' + PATH_ROOT + '/', defaults={'path': ''})
def landing(path):
    if request.args.get('token') == '0':
        return vtuner.get_init_token()
    if request.args.get('search'):
        return station_search()
    page = vtuner.Page()
    page.add(vtuner.Directory('Radiobrowser', url_for('radiobrowser_landing', _external=True), 4))
    if my_stations_enabled:
        page.add(vtuner.Directory('My Stations', url_for('my_stations_landing', _external=True),
                                  len(my_stations.get_category_directories())))
    else:
        page.add(vtuner.Display("'My Stations' feature not configured."))
    return page.to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_MY_STATIONS + '/')
def my_stations_landing():
    page = vtuner.Page()
    page.add(vtuner.Previous(url_for("landing", _external=True)))
    directories = my_stations.get_category_directories()
    return get_directories_page('my_stations_category', directories, request.args).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_MY_STATIONS + '/<directory>')
def my_stations_category(directory):
    stations = my_stations.get_stations_by_category(directory)
    return get_stations_page(stations, request.args).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/')
def radiobrowser_landing():
    page = vtuner.Page()
    page.add(vtuner.Previous(url_for('landing', _external=True)))
    page.add(vtuner.Directory('Genres', url_for('radiobrowser_genres', _external=True),
                              len(radiobrowser.get_genre_directories())))
    page.add(vtuner.Directory('Countries', url_for('radiobrowser_countries', _external=True),
                              len(radiobrowser.get_country_directories())))
    page.add(vtuner.Directory('Languages', url_for('radiobrowser_languages', _external=True),
                              len(radiobrowser.get_language_directories())))
    page.add(vtuner.Directory('Most Popular', url_for('radiobrowser_popular', _external=True),
                              len(radiobrowser.get_stations_by_votes())))
    return page.to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/' + PATH_RADIOBROWSER_COUNTRY + '/')
def radiobrowser_countries():
    directories = radiobrowser.get_country_directories()
    return get_directories_page('radiobrowser_country_stations', directories, request.args).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/' + PATH_RADIOBROWSER_COUNTRY + '/<directory>')
def radiobrowser_country_stations(directory):
    stations = radiobrowser.get_stations_by_country(directory)
    return get_stations_page(stations, request.args).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/' + PATH_RADIOBROWSER_LANGUAGE + '/')
def radiobrowser_languages():
    directories = radiobrowser.get_language_directories()
    return get_directories_page('radiobrowser_language_stations', directories, request.args).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/' + PATH_RADIOBROWSER_LANGUAGE + '/<directory>')
def radiobrowser_language_stations(directory):
    stations = radiobrowser.get_stations_by_language(directory)
    return get_stations_page(stations, request.args).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/' + PATH_RADIOBROWSER_GENRE + '/')
def radiobrowser_genres():
    directories = radiobrowser.get_genre_directories()
    return get_directories_page('radiobrowser_genre_stations', directories, request.args).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/' + PATH_RADIOBROWSER_GENRE + '/<directory>')
def radiobrowser_genre_stations(directory):
    stations = radiobrowser.get_stations_by_genre(directory)
    return get_stations_page(stations, request.args).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_RADIOBROWSER + '/' + PATH_RADIOBROWSER_POPULAR + '/')
def radiobrowser_popular():
    stations = radiobrowser.get_stations_by_votes()
    return get_stations_page(stations, request.args).to_string()


@app.route('/' + PATH_ROOT + '/' + PATH_SEARCH + '/')
def station_search():
    query = request.args.get('search')
    if not query or len(query) < 3:
        page = vtuner.Page()
        page.add(vtuner.Previous(url_for('landing', _external=True)))
        page.add(vtuner.Display("Search query too short."))
        page.set_count(1)
        return page.to_string()
    else:
        # TODO: we also need to include 'my station' elements
        stations = radiobrowser.search(query)
        return get_stations_page(stations, request.args).to_string()
