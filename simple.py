import psycopg2
conn = psycopg2.connect("dbname=indianhills user=mdupont")
import sys
#cur2 = conn.cursor()
#cur3 = conn.cursor()

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


def routing_point_for_school(geom_text, osm_id):
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
        #print row

        # now for this school, lets find the route to every other point
        process_school(row["id"], osm_id)

        #except Exception as e:
        #print "nada", e


def process_school(bid, osm_id):
    cur = conn.cursor()
    cur2 = conn.cursor()
    cur3 = conn.cursor()
    # just calculate to each routing point, dont worry about places for now, we can add them later 
    cur.execute("""
    SELECT id from ways_vertices_pgr 
    """)
    for record in cur:
        aid = record[0]

        #      1     2       3      4        5
        
        cur2.execute("""
        SELECT * FROM pgr_dijkstra(
        'SELECT gid AS id, source::integer as source, target::integer as target, length::double precision AS cost, the_geom FROM ways',       
        %s,       %s,       false,       false) 
        """ % (aid, bid));
        total = 0

        for r2 in cur2:
            #print record
            #print r2
            #reflect(cur2)
            
            row_seq=r2[0]
            row_id1=r2[1]
            row_id2=r2[2]
            row_cost=r2[3]
            #print row_cost
            total = total + int(row_cost)
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
                record[0],                 
                osm_id,
                row_id1,
                row_id2,
                row_cost
            )
            #print cmd
            cur3.execute(cmd     )        
            sys.stdout.write('.')
            conn.commit()

    

def create_school_route():
    cur = conn.cursor()
    cur.execute("""drop table school_route;""")

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
    cur.execute("""
    drop table school_ways;
    """)

    cur.execute("""
    create table school_ways as select c.leg_cost, a.* from school_route c, ways a where c.target_point = a.gid;
    """)

# recreate the table holding the routes
create_school_route()

school_data = schools()
for s in school_data.keys():
    print s
    d = school_data[s]
    x = routing_point_for_school(d['geom_text'],d['osm_id'])
    #print x, d
    
