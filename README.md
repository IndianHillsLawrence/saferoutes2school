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

