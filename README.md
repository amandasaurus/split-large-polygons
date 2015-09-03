split-large-polygons
====================

A script to break large polygons into many more managable smaller polygons. It will look for large polygons and split them in half until none are larger than the specified area. It can optionally include an overlap to prevent rendering artifacts.

Usage
=====

Example usage:

    split-large-polygons.py -d gis -t land_polygons -c the_geom -i gid -a 0.1

This will split the rows in ``land_polygons`` (in the ``gis`` database) into interately smaller polygons until none of them are larger than 0.1 in area. The unit of area is based on your SRID (the default is 4326, but it can be overridden by the ``-s``/``--srid`` option). So this will split things larger than 0.1 square degrees.

The table must have a primary key, which is specified in the ``-i``/``--id`` argument. It will delete the older, larger rows. This currently does not support tables which have any other columns except for the geometry and id columns.

You need PostGIS 2.0 or later, since this programme needs the [ST_Split](http://postgis.refractions.net/documentation/manual-2.0/ST_Split.html) method.

Buffer
------

By default, it will cut the polygons in half with no overlap between the resultant polygons. If you use the ``-b``/``--buffer`` option, an overlap of that many units will be left between each polygon split. This can help with rendering artifacts.

Example:

    split-large-polygons.py -d gis -t land_polygons -c the_geom -i gid -a 0.1 -b 0.01

Here a 0.01 degree overlap will be left between all polygons.

Motivation
==========

I had a table of large polygons of land from http://openstreetmapdata.com/. Large polygons mean that bounding box and indexes are less useful. Lots of small geometries are more effecient and allow better index usage. So I wrote this programme to split large polygons.

Licence
=======

This code is copyrighted and released under the GNU General Public Licence version 3 (or at your option) a later version. See the LICENCE file for more information.

The author is Rory McCann <rory@technomancy.org>.


[![Bitdeli Badge](https://d2weczhvl823v0.cloudfront.net/rory/split-large-polygons/trend.png)](https://bitdeli.com/free "Bitdeli Badge")

