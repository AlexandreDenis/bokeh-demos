import pandas as pd
import world_countries as wc

SUMMARY_KEYS = ['name', 'city', 'country', 'iata', 'icao', 'tz_db', 'alt']

airport_keys = ['id', 'name', 'city', 'country', 'iata', 'icao', 'lat',
                'lng', 'alt', 'dst', 'tz', 'tz_db']
route_keys = ['airline', 'id', 'source_ap', 'source_ap_id',
              'dest_ap', 'dest_ap_id', 'codeshare', 'stops', 'equip']
airline_keys = ['id', 'name', 'alias', 'iata', 'icao', 'callsign',
                'country', 'active']

airports = pd.read_csv('data/airports.dat', names=airport_keys)
routes = pd.read_csv('data/routes.dat', names=route_keys)

# add the columns we need for visualization to the airports df
airports['color'] = ['green' for x in airports.id]
airports['alpha'] = [1. for x in airports.id]
airports['radius'] = [0.3 for x in airports.id]

sources = set([int(sid)for sid in routes.source_ap_id if sid.isdigit()])
dests = set([int(sid)for sid in routes.dest_ap_id if sid.isdigit()])
active_ap_ids = sources.union(dests)
active_airports = airports[airports.id.isin(map(int, active_ap_ids))]
ghost_airports = airports[~airports.id.isin(active_ap_ids)]

out_routes = routes.groupby('source_ap_id').count().sort('id', ascending=False)
in_routes = routes.groupby('dest_ap_id').count().sort('id', ascending=False)


def get_worldmap():
    grpr = routes.groupby('source_ap_id').count().sort('id', ascending=False)
    countries_ap_grp = airports.groupby('country')
    countries_ap_count = countries_ap_grp.count().sort('id', ascending=False)
    # for max to be canadian flights, second
    _max_aps = 435
    countries_ap_count['alpha'] = map(lambda x: min((float(x)/_max_aps) * 0.7, 0.9), countries_ap_count.id)
    countries_ap_count['country'] = countries_ap_count.index

    world_countries = wc.data.copy()
    worldmap = pd.DataFrame.from_dict(world_countries, orient='index')

    def get_count(country):
        res = countries_ap_count[countries_ap_count['country'] == country]
        return res.id[0] if len(res) else 0

    def get_alpha(country):
        res = countries_ap_count[countries_ap_count['country'] == country]
        if not len(res):
            return 0

        return min((float(res.name[0])/_max_aps) * 0.7, 0.9)

    worldmap['alpha'] = [get_alpha(country) for country in worldmap.name]
    worldmap['count'] = [get_count(country) for country in worldmap.name]

    return worldmap


def color_mapper(airport, destinations):
    def _(id):
        if id in airport['airport'].id.values:
            return "red"
        elif id in destinations:
            return "green"
        elif id in active_ap_ids:
            return "black"
        else:
            return "lightgrey"

    return _

def alpha_mapper(airport, destinations):
    def _(id):
        if id in airport['airport'].id.values:
            return 1.
        elif id in destinations:
            return 1.
        elif id in active_ap_ids:
            return 0.6
        else:
            return 0.4

    return _

def radius_mapper(airport, destinations):
    def _(id):
        try:
            ap_out_routes = out_routes.id[str(id)]
        except KeyError:
            ap_out_routes = 0

        if ap_out_routes > 300:
            return 1.5
        elif ap_out_routes > 200:
            return 1
        elif ap_out_routes > 100:
            return 0.8
        elif ap_out_routes > 50:
            return 0.5
        elif ap_out_routes > 10:
            return 0.2
        else:
            return 0.1
        # if id in airport['airport'].id.values:
        #     return 0.6
        # elif id in destinations:
        #     return 0.5
        # elif id in active_ap_ids:
        #     return 0.2
        # else:
        #     return 0.1

    return _

def get_airport_data(airport_id, airports):
    main_ap = airports[airports.id == int(airport_id)]
    connections = routes[routes.source_ap_id == airport_id].sort('dest_ap_id')
    destinations_id = set([int(x) for x in connections.dest_ap_id.values if x.isdigit()])

    dmain_ap = dict(main_ap)
    airport = {
        'airport': main_ap,
        'connections': connections,
        'destinations': airports[airports.id.isin(destinations_id)],
        'summary': "Selected Airport:\n\n%s" % "\n".join(
            ["%s: %s" % (k, dmain_ap[k].values[0]) for k in SUMMARY_KEYS]
        )
    }

    make_color = color_mapper(airport, destinations_id)
    airports['color'] = [make_color(xid) for xid in airports.id]

    make_alpha = alpha_mapper(airport, destinations_id)
    airports['alpha'] = [make_alpha(xid) for xid in airports.id]

    make_radius = radius_mapper(airport, destinations_id)
    airports['radius'] = [make_radius(xid) for xid in airports.id]

    # import pdb; pdb.set_trace()
    # update the airports destinations df as we've added color and alpha
    conns = set([int(x) for x in connections.dest_ap_id.values if x.isdigit()])
    airport['destinations'] = airports[airports.id.isin(conns)]

    return airport

def get_routes(airport):
    xs, ys = [], []
    main_ap = airport['airport']
    conn_dests = airport['destinations']

    for iata, lng, lat in zip(conn_dests.iata, conn_dests.lng, conn_dests.lat):
        xs.append([float(main_ap.lng), float(lng)])
        ys.append([float(main_ap.lat), float(lat)])

    return {'xs': xs, 'ys': ys}

def create_output(df):
    out = {
        'lng': [float(x) for x in df.lng],
        'lat': [float(x) for x in df.lat],
    }

    for key in ['id', 'alpha', 'radius']:
        if key in df.columns:
            out[key] = [float(x) for x in df[key]]

    if 'color' in df.columns:
        out['color'] = [x for x in df.color]

    return out


def create_dests_source(airport):
    dest_sources = create_output(airport['destinations'])
    dest_sources['radius'] = [x*8 for x in dest_sources['radius']]
    dest_sources['alpha'] = [0.4 for x in dest_sources['radius']]
    dest_sources['name'] = [airports.name[x] for x in dest_sources['id']]
    dest_sources['city'] = [airports.city[x] for x in dest_sources['id']]
    dest_sources['country'] = [airports.country[x] for x in dest_sources['id']]

    return dest_sources