import psycopg2
conn = psycopg2.connect("dbname=indianhills user=mdupont")
cur = conn.cursor()
cur2 = conn.cursor()
cur3 = conn.cursor()

cur.execute("""
Create table if not exists school_route(from_vertex bigint, osm_id bigint, sourcepoint bigint, target_point bigint, leg_cost double precision,  geom geometry(Point,4326));
""")

cur.execute("""
SELECT a.id as vertexid, b.osm_id as placeid FROM ways_vertices_pgr as a INNER JOIN place as b ON (ST_intersects(a.the_geom, b.geometry))
""")
for record in cur:
    aid = record[0]

    #      1     2       3      4        5

    cur2.execute("""
    SELECT * FROM pgr_dijkstra(
    'SELECT gid AS id, source::integer as source, target::integer as target, length::double precision AS cost, the_geom FROM ways',       
    %s,       1590,       false,       false) 
    """ % (aid));
    total = 0

    for r2 in cur2:
        print record
        print r2

        cost = r2[3]
        total = total + cost
        cmd = """insert into school_route (from_vertex, osm_id, sourcepoint, target_point , leg_cost) values (%s,%s,%s,%s,%s)""" % (
            record[0], 
            record[1],
            r2[1],
            r2[2],
            r2[3],
        )
        print cmd
        cur3.execute(cmd     )
        conn.commit()

    

# now create at table for postgis an include the geometry
# we could include that directly in the school route table as well
cur.execute("""
drop table school_ways;
""")
        
cur.execute("""
create table school_ways as select c.leg_cost, a.* from school_route c, ways a where c.target_point = a.gid;
""")

