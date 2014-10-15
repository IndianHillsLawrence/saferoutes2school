saferoutes2school
=================

calculating the safest routes to school


Idea
====
The idea is that for each home in a city, we would calculate the distance to
each school. The schools could be for certain age groups so we would want to
tag or filter the schools afterwards when we have that information.
Then we would want to be able to find the shortest and safest path to a
school. Based on this info, we would be able to find a safe school district
map.

 	
Create OSM file
===============
create an inputdata.osm with josm 

Run osm2pgrouting
=================
from my version:
https://github.com/h4ck3rm1k3/osm2pgrouting

./osm2pgrouting  -conf mapconfig.xml -file inputdata.osm  -dbname indianhills -user mdupont -host localhost -passwd test -clean

Creating of the topology, this was already done on import, you can do it again
to change the parameters. 
SELECT pgr_createTopology('ways', 0.00001, 'the_geom', 'gid');


osm2pgsql
=========

Run another type of import, because we want to get more attributes
./osm2pgsql  -S default.style -d indianhills -c inputdata.osm

The default.style is modified https://github.com/h4ck3rm1k3/osm2pgsql see branch safe-routes-to-school

import osm data via Nominatim 
=============================


https://github.com/openlawrence/Nominatim

sudo apt-get install g++
sudo php5enmod pgsql
  
./autogen.sh ;  ./configure ;  make
./utils/setup.php --create-db 
./utils/setup.php --create-functions
./utils/setup.php --setup-db
./utils/setup.php  --verbose --ignore-errors --create-partition-functions
./utils/setup.php  --verbose --ignore-errors --create-tables
./utils/setup.php  --verbose --ignore-errors --create-partition-tables

./utils/setup.php  --verbose --ignore-errors --import-data --osm-file inputdata.osm 

Queries
=======

 create view veschool as SELECT place.name -> 'name'::text AS sname,
    place.osm_type,
    place.osm_id,
    place.class,
    place.type,
    place.name,
    place.admin_level,
    place.housenumber,
    place.suitenumber,
    place.street,
    place.addr_place,
    place.isin,
    place.postcode,
    place.country_code,
    place.extratags,
    place.geometry    
   FROM place
  WHERE place.type = 'school'::text
  and place.name -> 'name'::text not like '%histor%'
  and place.name -> 'name'::text  like '%Element%';


SELECT DISTINCT ON(g1.osm_id)g1.osm_id As gref_gid, g1.sname As gref_description, g2.osm_id As gnn_gid, g2.sname As gnn_description , ST_Distance(g1.geometry,g2.geometry)  FROM veschools As g1, veschools As g2  WHERE g1.osm_id <> g2.osm_id AND ST_DWithin(g1.geometry, g2.geometry, 300) and ST_Distance(g1.geometry, g2.geometry) > 0.001  and ORDER BY g1.osm_id, ST_Distance(g1.geometry,g2.geometry) ;

 SELECT c.from_vertex,
    c.leg_cost,
    a.gid,
    a.class_id,
    a.length,
    a.name,
    a.x1,
    a.y1,
    a.x2,
    a.y2,
    a.reverse_cost,
    a.rule,
    a.to_cost,
    a.maxspeed_forward,
    a.maxspeed_backward,
    a.osm_id,
    a.priority,
    a.the_geom,
    a.source,
    a.target
   FROM school_route c,
    ways a
  WHERE c.target_point = a.gid;

Indexes
=======

create index school_route_from_to on school_route (from_vertex, to_vertex);
create index school_route_from on school_route (from_vertex);
create index school_route_to on school_route (to_vertex);
create index  ways_vertices_pgr_id on     ways_vertices_pgr (id);

ways table
==========
                                        Table "public.ways"
      Column       |           Type            | Modifiers | Storage  | Stats target | Description 
-------------------+---------------------------+-----------+----------+--------------+-------------
 gid               | integer                   |           | plain    |              | 
 class_id          | integer                   | not null  | plain    |              | 
 length            | double precision          |           | plain    |              | 
 name              | text                      |           | extended |              | 
 x1                | double precision          |           | plain    |              | 
 y1                | double precision          |           | plain    |              | 
 x2                | double precision          |           | plain    |              | 
 y2                | double precision          |           | plain    |              | 
 reverse_cost      | double precision          |           | plain    |              | 
 rule              | text                      |           | extended |              | 
 to_cost           | double precision          |           | plain    |              | 
 maxspeed_forward  | integer                   |           | plain    |              | 
 maxspeed_backward | integer                   |           | plain    |              | 
 osm_id            | bigint                    |           | plain    |              | 
 priority          | double precision          | default 1 | plain    |              | 
 the_geom          | geometry(LineString,4326) |           | main     |              | 
 source            | integer                   |           | plain    |              | 
 target            | integer                   |           | plain    |              | 
Indexes:
    "ways_gid_idx" UNIQUE, btree (gid)
    "geom_idx" gist (the_geom)
    "source_idx" btree (source)
    "target_idx" btree (target)


school_route
============
                            Table "public.school_route"
    Column    |       Type       | Modifiers | Storage | Stats target | Description 
--------------+------------------+-----------+---------+--------------+-------------
 from_vertex  | bigint           |           | plain   |              | 
 to_vertex    | bigint           |           | plain   |              | 
 sourcepoint  | bigint           |           | plain   |              | 
 target_point | bigint           |           | plain   |              | 
 leg_cost     | double precision |           | plain   |              | 
Indexes:
    "school_route_from" btree (from_vertex)
    "school_route_from_to" btree (from_vertex, to_vertex)
    "school_route_to" btree (to_vertex)


select w.source, count(*) from school_route r, ways w where w.gid=r.sourcepoint
group by w.source order by count(*);

the most used points
====================

create view most_used_points as select
    rp.the_geom,
    count(*)
from
    school_route r,
    ways w,
    ways_vertices_pgr rp
where
    w.gid=r.sourcepoint
    and
    rp.id = w.source    
group by rp.the_geom
order by count(*);

create table most_used_points_t as select * from most_used_points;




create view v_school_route_sum as select c.to_vertext, c.from_vertex, sum(c.leg_cost) from school_route c group by c.from_vertex, c.to_vertex;
drop table v_school_route2;
create table v_school_route2 as select * from v_school_route;

[22265L, 17269L, 19871L]
p 2848, s 19871

Simple list of schools
======================

create table schools_2 as select
     osm_id,
     "isced:level",
     "addr:housename",
     "addr:housenumber",
     name,
     ST_Centroid(ST_Transform(way,4326)) as the_geom
     from  
     planet_osm_point

     where "isced:level" is not null;



create view vschool as select
     osm_id,
     "isced:level",
     "addr:housename",
     "addr:housenumber",
     name,
     ST_asText(ST_Centroid(ST_Transform(way,4326))) as the_geom
     from  
     planet_osm_point
     where "isced:level" = '1' ;
