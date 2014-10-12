import psycopg2
import pprint
conn = psycopg2.connect("dbname=indianhills user=mdupont")
import sys
#cur2 = conn.cursor()
#cur3 = conn.cursor()

def return_list(sql) :
    cur = conn.cursor()
    try :
        cur.execute(sql)

    except Exception as e:
        print sql
        print e
        raise e
    ret = []
    for x in cur:
        ret.append( x[0])

    #pprint.pprint( ret)
    #print "SQL %s got count %s" % (sql, len(ret))
    return ret

def reflect(c):
    p = 0
    for x in c.description:
        print "row[\"%s\"]=s[%s]" % (x.name, p)
        p = p + 1

def schools():
    schools = conn.cursor()
    # first select all the schools
    schools.execute("""select
     osm_id,
     "isced:level",
     "addr:housename",
     "addr:housenumber",
     name,
     ST_asText(ST_Centroid(ST_Transform(way,4326))) as the_geom
     from  
     planet_osm_point

     where "isced:level" is not null;
    """)

    school_data = {}

    for s in schools:
        row = {}
        #print s
        row["osm_id"]=s[0]
        row["isced:level"]=s[1]
        row["addr:housename"]=s[2]
        row["addr:housenumber"]=s[3]
        row["name"]=s[4]
        row["geom_text"]=s[5]
        school_data[row["name"]]=row

    return school_data



def routing_point_for_school(geom_text,  osm_id ):
    """
    We find the closest point in the routine matrix for each school
    """
    dist = """
    round(
    CAST(
    ST_Distance_Sphere(
       ST_Centroid(the_geom),
       ST_GeomFromText('%s')
    )
    As numeric)
    ,2)
    """ % geom_text
    #print "DIST", dist

    sql = """SELECT *, 
    %s As dist_meters
    FROM ways_vertices_pgr
    order by %s
    limit 1;""" % (dist,dist)

    cur = conn.cursor()
    #print sql
    cur.execute(sql)
    #reflect(cur)
    #if len(cur):
    #    try:
    for s in cur:
        row = {}
        row["id"]=s[0] # the routing id
        row["cnt"]=s[1]
        row["chk"]=s[2]
        row["ein"]=s[3]
        row["eout"]=s[4]
        row["the_geom"]=s[5] # geometry of routing point
        row["dist_meters"]=s[6] # the distance
        return row

def find_route(bid, aid):
    cur2 = conn.cursor()

    cur2.execute("""
    SELECT * FROM pgr_dijkstra(
    'SELECT gid AS id, source::integer as source, target::integer as target, length::double precision AS cost, the_geom FROM ways',       
    %s,       %s,       false,       false) 
    """ % (aid, bid));
    total = 0
    legs = []
    for r2 in cur2:
        leg = {
            'row_seq' : r2[0],
            'row_id1' : r2[1], 
            'row_id2' : r2[2],
            'row_cost': r2[3]
        }
        legs.append(leg)
        total = total + float(leg['row_cost'])
    return {
        'from' : aid,
        'to' : bid,
        'total' : total,
        'legs': legs
    }

def add_route_leg(
        cur3,
        bid,     # the school
        aid,     # the house
        row_id1, # source point
        row_id2, # target point 
        row_cost # cost
):
        cmd = """insert into school_route (
        from_vertex, 
        to_vertex, 
        sourcepoint, 
        target_point , 
        leg_cost) values (
        %s, 
        %s,
        %s,
        %s,
        %s)""" % (
            bid,     # the school
            aid,     # the house
            row_id1, # source point
            row_id2, # target point 
            row_cost # cost
        )
        #print cmd
        cur3.execute(cmd     )        
        sys.stdout.write('.')
        conn.commit()

def missing_points():
    """
    get a list of routing points 
    """
    return return_list("""
    select 
        distinct(a.id) 
    from 
        ways_vertices_pgr a 
        left outer join 
        school_route b 
      on 
        a.id=b.to_vertex 
    where 
      b.to_vertex is null
    """)


def process_school(bid, osm_id, limit ):
    # now lets find all the points not associated with school 
    cur = conn.cursor()
    print "process_school(%s,%s,%s )" % (bid, osm_id, limit)
    #

# def process_school_first(bid, osm_id, limit ):
#     cur = conn.cursor()
#     print "process_school(%s,%s,%s )" % (bid, osm_id, limit)
#     # just calculate to each routing point, dont worry about places for now, we can add them later 

#     sql = """
#     select 
#     distinct(g2.id) 
#     from 
#     ways_vertices_pgr g1, 
#     ways_vertices_pgr g2 
#     where 
#     ST_DWithin(g1.the_geom, g2.the_geom, %s) 
#     and g1.id=%s 
#     and g1.id != g2.id;
#     """ % (limit + 0.001, bid)
#     print sql
#     cur.execute(sql)
#     # -- where the node is closer to this school than other schools 
#     for record in cur:
#         #print record
#         aid = record[0]
#         # pass
#         print aid
#         # now get the route to that
#         add_route(cur3, bid, osm_id, aid )


def create_school_route():
    cur = conn.cursor()
    #cur.execute("""drop table school_route;""")

    cur.execute("""
    Create table if not exists school_route(
    from_vertex bigint, 
    to_vertex bigint, 
    sourcepoint bigint, 
    target_point bigint, 
    leg_cost double precision);
    """)

def create_ways():
    # now create at table for postgis an include the geometry
    # we could include that directly in the school route table as well
    cur = conn.cursor()
    #cur.execute("""    drop table school_ways;    """)

    cur.execute("""
    create table if not exists school_ways  as select c.leg_cost, a.* from school_route c, ways a where c.target_point = a.gid;
    """)

# recreate the table holding the routes
#create_school_route()

def all_traversed_points():
    """
    all the traversed points in the routes so far, so we will skip them as well.
    """
    return return_list( """
select
    distinct(r.sourcepoint)
from
    school_route r
""")

def Decimal(x):
    return x

def process_schools():

    return {
        'rp': {2358L: {'addr:housename': None,
                       'addr:housenumber': None,
                       'geom_text': 'POINT(-95.2281896409873 38.9764826248688)',
                       'isced:level': '1',
                       'name': 'Woodlawn Elementary School',
                       'osm_id': 3112669826L,
                       'routing_point': {'chk': None,
                                         'cnt': None,
                                         'dist_meters': Decimal('63.35'),
                                         'ein': None,
                                         'eout': None,
                                         'id': 2358L,
                                         'the_geom': '0101000020E61000001CD71AA5A6CE57C0FB00497DFE7C4340'}},
               2505L: {'addr:housename': None,
                       'addr:housenumber': None,
                       'geom_text': 'POINT(-95.258446516724 38.9645600189159)',
                       'isced:level': '1',
                       'name': 'Hillcrest Elementary School',
                       'osm_id': 3112669817L,
                       'routing_point': {'chk': None,
                                         'cnt': None,
                                         'dist_meters': Decimal('52.39'),
                                         'ein': None,
                                         'eout': None,
                                         'id': 2505L,
                                         'the_geom': '0101000020E6100000F390291F82D057C062484E266E7B4340'}},
               7323L: {'addr:housename': None,
                       'addr:housenumber': None,
                       'geom_text': 'POINT(-95.2702877494731 38.9671719054717)',
                       'isced:level': '1',
                       'name': 'Sunset Hill Elementary School',
                       'osm_id': 3112669825L,
                       'routing_point': {'chk': None,
                                         'cnt': None,
                                         'dist_meters': Decimal('89.12'),
                                         'ein': None,
                                         'eout': None,
                                         'id': 7323L,
                                         'the_geom': '0101000020E610000027A5A0DB4BD157C09C340D8AE67B4340'}},
               16571L: {'addr:housename': None,
                        'addr:housenumber': '2201',
                        'geom_text': 'POINT(-95.2561886012573 38.9440285441441)',
                        'isced:level': '1',
                        'name': 'Schwegler Elementary School',
                        'osm_id': 3112669823L,
                        'routing_point': {'chk': None,
                                          'cnt': None,
                                          'dist_meters': Decimal('47.98'),
                                          'ein': None,
                                          'eout': None,
                                          'id': 16571L,
                                          'the_geom': '0101000020E6100000B69F8CF161D057C010864BD8C8784340'}},
               16932L: {'addr:housename': None,
                        'addr:housenumber': '2521',
                        'geom_text': 'POINT(-95.2992881516219 38.9365535258204)',
                        'isced:level': '1',
                        'name': 'Sunflower Elementary School',
                        'osm_id': 3112669824L,
                        'routing_point': {'chk': None,
                                          'cnt': None,
                                          'dist_meters': Decimal('114.79'),
                                          'ein': None,
                                          'eout': None,
                                          'id': 16932L,
                                          'the_geom': '0101000020E6100000DEFFC70913D357C00AD80E46EC774340'}},
               17269L: {'addr:housename': None,
                        'addr:housenumber': None,
                        'geom_text': 'POINT(-95.3016403901934 38.9632742606496)',
                        'isced:level': '1',
                        'name': 'Quail Run Elementary School',
                        'osm_id': 3112669822L,
                        'routing_point': {'chk': None,
                                          'cnt': None,
                                          'dist_meters': Decimal('62.36'),
                                          'ein': None,
                                          'eout': None,
                                          'id': 17269L,
                                          'the_geom': '0101000020E6100000B73DE6A848D357C0AC30C73C3C7B4340'}},
               18110L: {'addr:housename': None,
                        'addr:housenumber': None,
                        'geom_text': 'POINT(-95.2110256206852 38.9345921838266)',
                        'isced:level': '1',
                        'name': 'Prairie Park Elementary School',
                        'osm_id': 3112669821L,
                        'routing_point': {'chk': None,
                                          'cnt': None,
                                          'dist_meters': Decimal('48.24'),
                                          'ein': None,
                                          'eout': None,
                                          'id': 18110L,
                                          'the_geom': '0101000020E6100000187CF54C8ACD57C074CBB3379D774340'}},
               18433L: {'addr:housename': None,
                        'addr:housenumber': '936',
                        'geom_text': 'POINT(-95.2309065955642 38.9663825175286)',
                        'isced:level': '1',
                        'name': 'New York Elementary School',
                        'osm_id': 3112669819L,
                        'routing_point': {'chk': None,
                                          'cnt': None,
                                          'dist_meters': Decimal('69.95'),
                                          'ein': None,
                                          'eout': None,
                                          'id': 18433L,
                                          'the_geom': '0101000020E6100000389AC871CCCE57C06506E055C57B4340'}},
               19124L: {'addr:housename': None,
                        'addr:housenumber': None,
                        'geom_text': 'POINT(-95.2374201898578 38.950614288905)',
                        'isced:level': '1',
                        'name': 'Cordley Elementary School',
                        'osm_id': 3112669815L,
                        'routing_point': {'chk': None,
                                          'cnt': None,
                                          'dist_meters': Decimal('35.86'),
                                          'ein': None,
                                          'eout': None,
                                          'id': 19124L,
                                          'the_geom': '0101000020E6100000013851A62CCF57C0A5E83702A7794340'}},
               19871L: {'addr:housename': None,
                        'addr:housenumber': None,
                        'geom_text': 'POINT(-95.2711531864179 38.9827085269385)',
                        'isced:level': '1',
                        'name': 'Deerfield Elementary School',
                        'osm_id': 3112669816L,
                        'routing_point': {'chk': None,
                                          'cnt': None,
                                          'dist_meters': Decimal('27.61'),
                                          'ein': None,
                                          'eout': None,
                                          'id': 19871L,
                                          'the_geom': '0101000020E6100000582DFA545FD157C0504FC4C7CC7D4340'}},
               21112L: {'addr:housename': None,
                        'addr:housenumber': '810',
                        'geom_text': 'POINT(-95.2447015742247 38.9737829460492)',
                        'isced:level': '1',
                        'name': 'Pinckney Elementary School',
                        'osm_id': 3112669820L,
                        'routing_point': {'chk': None,
                                          'cnt': None,
                                          'dist_meters': Decimal('29.05'),
                                          'ein': None,
                                          'eout': None,
                                          'id': 21112L,
                                          'the_geom': '0101000020E61000000A100533A6CF57C0BB4967BB9D7C4340'}},
               22265L: {'addr:housename': None,
                        'addr:housenumber': '1101',
                        'geom_text': 'POINT(-95.3274340762724 38.9635176820164)',
                        'isced:level': '1',
                        'name': 'Langston Hughes Elementary School',
                        'osm_id': 3112669818L,
                        'routing_point': {'chk': None,
                                          'cnt': None,
                                          'dist_meters': Decimal('133.40'),
                                          'ein': None,
                                          'eout': None,
                                          'id': 22265L,
                                          'the_geom': '0101000020E6100000A6F8533EDFD457C07769C361697B4340'}},
               23803L: {'addr:housename': None,
                        'addr:housenumber': None,
                        'geom_text': 'POINT(-95.2405040163966 38.9351028409179)',
                        'isced:level': '1',
                        'name': 'Broken Arrow Elementary School',
                        'osm_id': 3112669814L,
                        'routing_point': {'chk': None,
                                          'cnt': None,
                                          'dist_meters': Decimal('27.47'),
                                          'ein': None,
                                          'eout': None,
                                          'id': 23803L,
                                          'the_geom': '0101000020E6100000A4D23E0C63CF57C080D8D2A3A9774340'}}},

        'schools': {'Broken Arrow Elementary School': {'addr:housename': None,
                                                       'addr:housenumber': None,
                                                       'geom_text': 'POINT(-95.2405040163966 38.9351028409179)',
                                                       'isced:level': '1',
                                                       'name': 'Broken Arrow Elementary School',
                                                       'osm_id': 3112669814L,
                                                       'routing_point': {'chk': None,
                                                                         'cnt': None,
                                                                         'dist_meters': Decimal('27.47'),
                                                                         'ein': None,
                                                                         'eout': None,
                                                                         'id': 23803L,
                                                                         'the_geom': '0101000020E6100000A4D23E0C63CF57C080D8D2A3A9774340'}},
                    'Cordley Elementary School': {'addr:housename': None,
                                                  'addr:housenumber': None,
                                                  'geom_text': 'POINT(-95.2374201898578 38.950614288905)',
                                                  'isced:level': '1',
                                                  'name': 'Cordley Elementary School',
                                                  'osm_id': 3112669815L,
                                                  'routing_point': {'chk': None,
                                                                    'cnt': None,
                                                                    'dist_meters': Decimal('35.86'),
                                                                    'ein': None,
                                                                    'eout': None,
                                                                    'id': 19124L,
                                                                    'the_geom': '0101000020E6100000013851A62CCF57C0A5E83702A7794340'}},
                    'Deerfield Elementary School': {'addr:housename': None,
                                                    'addr:housenumber': None,
                                                    'geom_text': 'POINT(-95.2711531864179 38.9827085269385)',
                                                    'isced:level': '1',
                                                    'name': 'Deerfield Elementary School',
                                                    'osm_id': 3112669816L,
                                                    'routing_point': {'chk': None,
                                                                      'cnt': None,
                                                                      'dist_meters': Decimal('27.61'),
                                                                      'ein': None,
                                                                      'eout': None,
                                                                      'id': 19871L,
                                                                      'the_geom': '0101000020E6100000582DFA545FD157C0504FC4C7CC7D4340'}},
                    'Hillcrest Elementary School': {'addr:housename': None,
                                                    'addr:housenumber': None,
                                                    'geom_text': 'POINT(-95.258446516724 38.9645600189159)',
                                                    'isced:level': '1',
                                                    'name': 'Hillcrest Elementary School',
                                                    'osm_id': 3112669817L,
                                                    'routing_point': {'chk': None,
                                                                      'cnt': None,
                                                                      'dist_meters': Decimal('52.39'),
                                                                      'ein': None,
                                                                      'eout': None,
                                                                      'id': 2505L,
                                                                      'the_geom': '0101000020E6100000F390291F82D057C062484E266E7B4340'}},
                    'Langston Hughes Elementary School': {'addr:housename': None,
                                                          'addr:housenumber': '1101',
                                                          'geom_text': 'POINT(-95.3274340762724 38.9635176820164)',
                                                          'isced:level': '1',
                                                          'name': 'Langston Hughes Elementary School',
                                                          'osm_id': 3112669818L,
                                                          'routing_point': {'chk': None,
                                                                            'cnt': None,
                                                                            'dist_meters': Decimal('133.40'),
                                                                            'ein': None,
                                                                            'eout': None,
                                                                            'id': 22265L,
                                                                            'the_geom': '0101000020E6100000A6F8533EDFD457C07769C361697B4340'}},
                    'New York Elementary School': {'addr:housename': None,
                                                   'addr:housenumber': '936',
                                                   'geom_text': 'POINT(-95.2309065955642 38.9663825175286)',
                                                   'isced:level': '1',
                                                   'name': 'New York Elementary School',
                                                   'osm_id': 3112669819L,
                                                   'routing_point': {'chk': None,
                                                                     'cnt': None,
                                                                     'dist_meters': Decimal('69.95'),
                                                                     'ein': None,
                                                                     'eout': None,
                                                                     'id': 18433L,
                                                                     'the_geom': '0101000020E6100000389AC871CCCE57C06506E055C57B4340'}},
                    'Pinckney Elementary School': {'addr:housename': None,
                                                   'addr:housenumber': '810',
                                                   'geom_text': 'POINT(-95.2447015742247 38.9737829460492)',
                                                   'isced:level': '1',
                                                   'name': 'Pinckney Elementary School',
                                                   'osm_id': 3112669820L,
                                                   'routing_point': {'chk': None,
                                                                     'cnt': None,
                                                                     'dist_meters': Decimal('29.05'),
                                                                     'ein': None,
                                                                     'eout': None,
                                                                     'id': 21112L,
                                                                     'the_geom': '0101000020E61000000A100533A6CF57C0BB4967BB9D7C4340'}},
                    'Prairie Park Elementary School': {'addr:housename': None,
                                                       'addr:housenumber': None,
                                                       'geom_text': 'POINT(-95.2110256206852 38.9345921838266)',
                                                       'isced:level': '1',
                                                       'name': 'Prairie Park Elementary School',
                                                       'osm_id': 3112669821L,
                                                       'routing_point': {'chk': None,
                                                                         'cnt': None,
                                                                         'dist_meters': Decimal('48.24'),
                                                                         'ein': None,
                                                                         'eout': None,
                                                                         'id': 18110L,
                                                                         'the_geom': '0101000020E6100000187CF54C8ACD57C074CBB3379D774340'}},
                    'Quail Run Elementary School': {'addr:housename': None,
                                                    'addr:housenumber': None,
                                                    'geom_text': 'POINT(-95.3016403901934 38.9632742606496)',
                                                    'isced:level': '1',
                                                    'name': 'Quail Run Elementary School',
                                                    'osm_id': 3112669822L,
                                                    'routing_point': {'chk': None,
                                                                      'cnt': None,
                                                                      'dist_meters': Decimal('62.36'),
                                                                      'ein': None,
                                                                      'eout': None,
                                                                      'id': 17269L,
                                                                      'the_geom': '0101000020E6100000B73DE6A848D357C0AC30C73C3C7B4340'}},
                    'Schwegler Elementary School': {'addr:housename': None,
                                                    'addr:housenumber': '2201',
                                                    'geom_text': 'POINT(-95.2561886012573 38.9440285441441)',
                                                    'isced:level': '1',
                                                    'name': 'Schwegler Elementary School',
                                                    'osm_id': 3112669823L,
                                                    'routing_point': {'chk': None,
                                                                      'cnt': None,
                                                                      'dist_meters': Decimal('47.98'),
                                                                      'ein': None,
                                                                      'eout': None,
                                                                      'id': 16571L,
                                                                      'the_geom': '0101000020E6100000B69F8CF161D057C010864BD8C8784340'}},
                    'Sunflower Elementary School': {'addr:housename': None,
                                                    'addr:housenumber': '2521',
                                                    'geom_text': 'POINT(-95.2992881516219 38.9365535258204)',
                                                    'isced:level': '1',
                                                    'name': 'Sunflower Elementary School',
                                                    'osm_id': 3112669824L,
                                                    'routing_point': {'chk': None,
                                                                      'cnt': None,
                                                                      'dist_meters': Decimal('114.79'),
                                                                      'ein': None,
                                                                      'eout': None,
                                                                      'id': 16932L,
                                                                      'the_geom': '0101000020E6100000DEFFC70913D357C00AD80E46EC774340'}},
                    'Sunset Hill Elementary School': {'addr:housename': None,
                                                      'addr:housenumber': None,
                                                      'geom_text': 'POINT(-95.2702877494731 38.9671719054717)',
                                                      'isced:level': '1',
                                                      'name': 'Sunset Hill Elementary School',
                                                      'osm_id': 3112669825L,
                                                      'routing_point': {'chk': None,
                                                                        'cnt': None,
                                                                        'dist_meters': Decimal('89.12'),
                                                                        'ein': None,
                                                                        'eout': None,
                                                                        'id': 7323L,
                                                                        'the_geom': '0101000020E610000027A5A0DB4BD157C09C340D8AE67B4340'}},
                    'Woodlawn Elementary School': {'addr:housename': None,
                                                   'addr:housenumber': None,
                                                   'geom_text': 'POINT(-95.2281896409873 38.9764826248688)',
                                                   'isced:level': '1',
                                                   'name': 'Woodlawn Elementary School',
                                                   'osm_id': 3112669826L,
                                                   'routing_point': {'chk': None,
                                                                     'cnt': None,
                                                                     'dist_meters': Decimal('63.35'),
                                                                     'ein': None,
                                                                     'eout': None,
                                                                     'id': 2358L,
                                                                     'the_geom': '0101000020E61000001CD71AA5A6CE57C0FB00497DFE7C4340'}}}}

    srp = {}
    school_data = schools()
    for s in school_data.keys():
        print s
        d = school_data[s]
        #distance = closest_schools(d['osm_id'])
        x = routing_point_for_school(d['geom_text'],d['osm_id'])
        d['routing_point'] = x
        srp[x['id']]=d

    sd= {
        'schools' : school_data,
        'rp' : srp 
    }
    pprint.pprint(sd)
    return sd


def closest_schools_to_point(rpid, srps):
    
    """
    select the schools that are closest to this one, lets pick the second one away so that we have some overlap but not too much
    """
    #     ST_Distance(s.the_geom,rp.the_geom)
    return return_list(
        """
    select
    s.id
from
     ways_vertices_pgr rp,
     ways_vertices_pgr s
where 
    rp.id = %s
    and 
    s.id in (%s)
order by 
    ST_Distance(s.the_geom,rp.the_geom)
    limit 3
    ;
    """ % (
        rpid, 
        ",".join(str(x) for x in srps['rp'].keys())
    )
    )

def process_all_points():
    """
    first get all the points that are not in a route
    then for each point, find the N closest schools and calculate a route to them.
    then pick the shortest route, and add that to the system.
    # optional, for each point along the way, add that as well to the route so that we done need to add them doubled.
    """
    sd = process_schools() 
    
    # we will need to refresh this as well.
    used = all_traversed_points()
    print used;
    missing = missing_points()
    cur3 = conn.cursor()

    for p in missing :
        print "eval p %s" %(p)
        if p not in used : # skip the used
            sl = closest_schools_to_point(p, sd)
            routes = {}
            pprint.pprint(sl)
            if sl is not None:
                mindist = 99999
                minroute = None
                for s in sl :
                    # now for the closest schools we will find the shortest route
                    r = find_route(p,s)
                    #routes[s]=r
                    if r['total'] < mindist:
                        minroute = r
                        mindist= r['total']

                print "p %s, min %s from %s to %s " %(p,mindist, minroute['from'],minroute['to'])

                #pprint.pprint( minroute)

                #now insert this into the school routes,
                for l in minroute['legs'] :
                    add_route_leg(cur3, 
                                  minroute['from'],
                                  minroute['to'],
                                  l['row_id1'],
                                  l['row_id2'],
                                  l['row_cost']
                              )
                #raise Exception()

# main routing
process_all_points()
