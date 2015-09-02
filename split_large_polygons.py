"""
A script that will split polygons above a certain side into 2+ polygons to make them smaller
"""
from __future__ import division
import argparse
import psycopg2


def fmt(string, extras=None):
    """
    formats a string using the args (i.e cli args), make it easier
    """
    fmt_vars = {}
    if extras:
        fmt_vars.update(extras)
    fmt_vars.update(vars(args))
    return string.format(**fmt_vars)

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--database', type=str, required=True)
    parser.add_argument('-t', '--table', type=str, required=True)
    parser.add_argument('-c', '--column', type=str, required=True)
    parser.add_argument('-i', '--id', type=str, required=True)
    parser.add_argument('-a', '--area', default=100, type=float)
    parser.add_argument('-s', '--srid', default=4326, type=int)

    args = parser.parse_args()

    try:
        conn = psycopg2.connect(fmt("dbname={database}"))
        cur = conn.cursor()

        while True:
            cur.execute(fmt("select count(*) as count from {table} where ST_Area({column}) > {area};"))
            row = cur.fetchall()
            num_to_do = int(row[0][0])
            print "There are {0} objects that need splitting".format(row[0][0])
            if num_to_do == 0:
                print "Finished"
                break
            
            sql = fmt("select {id} as id, st_xmin({column}) as xmin, st_ymin({column}) as ymin, st_xmax({column}) as xmax, st_ymax({column}) as ymax from {table} where ST_Area({column}) > {area} limit 1000;")
            cur.execute(sql)
            rows = cur.fetchall()
            if len(rows) == 0:
                print "Finished"
                break
            for row in rows:
                id, xmin, ymin, xmax, ymax = row
                xsize = xmax - xmin
                ysize = ymax - ymin
                if xsize > ysize:
                    x1 = xmin + (xsize / 2)
                    x2 = x1
                    y1 = ymin - 0.01
                    y2 = ymax + 0.01
                else:
                    x1 = xmin - 0.01
                    x2 = xmax + 0.01
                    y1 = ymin + (ysize/2)
                    y2 = y1

                line_to_split = "ST_SetSRID( ST_MakeLine( ST_MakePoint( {x1}, {y1} ), ST_MakePoint( {x2}, {y2} ) ), {srid})".format(x1=x1, y1=y1, x2=x2, y2=y2, srid=args.srid)

                sql = "insert into {table} ({column}) select ST_Multi((ST_Dump(ST_Split(the_geom, {line_to_split}))).geom) as {column} from land_polygons where {id_column} = {id_value};".format(table=args.table, column=args.column, line_to_split=line_to_split, id_column=args.id, id_value=id)
                cur.execute(sql)
                cur.execute("delete from {table} where {id_column} = {id_value};".format(table=args.table, id_column=args.id, id_value=id))

    finally:
        conn.commit()

if __name__ == '__main__':
    main()
