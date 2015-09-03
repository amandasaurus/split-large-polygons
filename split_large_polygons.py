"""
A script that will split polygons above a certain side into 2+ polygons to make them smaller
"""
from __future__ import division
import argparse
import psycopg2
import math



def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--database', type=str, required=False, help="PostgreSQL database name")
    parser.add_argument('-t', '--table', type=str, required=True, help="Table which has the polygons")
    parser.add_argument('-c', '--column', type=str, required=True, help="Geometry column name", metavar="GEOMETRY_COLUMN")
    parser.add_argument('-i', '--id', type=str, required=True, help="Primary key column")
    parser.add_argument('-a', '--area', default=100, type=float, help="Maximum area")
    parser.add_argument('-s', '--srid', default=4326, type=int, help="SRID of the table")
    parser.add_argument('-b', '--buffer', type=float, help="Size of the buffer (in SRID units) to have as an overlap")
    parser.add_argument('-B', '--buffer-percent', type=float, help="Calculate the buffer as this much of a percentage of the shape")

    args = parser.parse_args()

    side_size = math.sqrt(args.area)
    buffer_percent = None
    buffer = None
    if args.buffer is None and args.buffer_percent is not None:
        if args.buffer_percent > 50:
            print "Buffer Percent of {} is too large for the area {}".format(args.buffer_percent, args.area)
            return
        else:
            buffer_percent = args.buffer_percent
    elif args.buffer is not None and args.buffer_percent is None:
        if args.buffer * 2 > side_size:
            print "Buffer of {} is too large for the area {}".format(args.buffer, args.area)
            return
        else:
            buffer = args.buffer
    elif args.buffer is not None and args.buffer_percent is not None:
        print "Cannot specify both -b/--buffer and -B/--buffer-percent at the same time"
        return
    elif args.buffer is None and args.buffer_percent is None:
        # No buffer
        buffer = None
    else:
        assert False, "unreachable code"


    def fmt(string, extras=None):
        """
        formats a string using the args (i.e cli args), make it easier
        """
        fmt_vars = {}
        if extras:
            fmt_vars.update(extras)
        fmt_vars.update(vars(args))
        result = string.format(**fmt_vars)
        return result

    connect_args = {}
    if args.database is not None:
        connect_args['database'] = args.database

    conn = psycopg2.connect(**connect_args)

    print "Splitting things larger than {:,}".format(args.area)

    try:
        step = 0
        while True:
            conn.commit()
            cur = conn.cursor()

            step += 1
            cur.execute(fmt("select count(*) as count from {table} where ST_Area({column}) > {area};"))
            row = cur.fetchall()
            num_to_do = int(row[0][0])
            print "[step {0:3d}] There are {1:,} objects that need splitting".format(step, row[0][0])
            if num_to_do == 0:
                print "Finished"
                break
            
            sql = fmt("select {id} as id, st_xmin({column}) as xmin, st_ymin({column}) as ymin, st_xmax({column}) as xmax, st_ymax({column}) as ymax from {table} where ST_Area({column}) > {area} order by ST_Area({column}) DESC")
            cur.execute(sql)
            rows = cur.fetchall()
            
            if len(rows) == 0:
                print "Finished"
                break

            for row in rows:
                id, xmin, ymin, xmax, ymax = row
                xsize = xmax - xmin
                ysize = ymax - ymin

                # Should we split horizontally or vertically?
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

                if buffer is None and buffer_percent is None:
                    line_to_split = "ST_SetSRID( ST_MakeLine( ST_MakePoint( {x1}, {y1} ), ST_MakePoint( {x2}, {y2} ) ), {srid})".format(x1=x1, y1=y1, x2=x2, y2=y2, srid=args.srid)

                    sql = "insert into {table} ({column}) select ST_Multi((ST_Dump(ST_Split({column}, {line_to_split}))).geom) as {column} from {table} where {id_column} = {id_value};".format(table=args.table, column=args.column, line_to_split=line_to_split, id_column=args.id, id_value=id)
                    cur.execute(sql)
                else:
                    # do it in 2 steps, one where we move to one side, the other where we go to the other
                    if xsize > ysize:
                        if buffer_percent is not None:
                            buffer = xsize * (buffer_percent / 100)
                        # Just a jump to the left ...
                        x1_a = x1 - buffer
                        x2_a = x1_a
                        line_to_split = "ST_SetSRID( ST_MakeLine( ST_MakePoint( {x1}, {y1} ), ST_MakePoint( {x2}, {y2} ) ), {srid})".format(x1=x1_a, y1=y1, x2=x2_a, y2=y2, srid=args.srid)
                        sql = "insert into {table} ({column}) select {column} from (select ST_Multi((ST_Dump(ST_Split({column}, {line_to_split}))).geom) as {column} from {table} where {id_column} = {id_value}) as inner_table where st_xmin({column}) >= {x1};".format(table=args.table, column=args.column, line_to_split=line_to_split, id_column=args.id, id_value=id, x1=x1_a)
                        cur.execute(sql)

                        # ... and then a step to the right!
                        x1_b = x1 + buffer
                        x2_b = x1_b
                        line_to_split = "ST_SetSRID( ST_MakeLine( ST_MakePoint( {x1}, {y1} ), ST_MakePoint( {x2}, {y2} ) ), {srid})".format(x1=x1_b, y1=y1, x2=x2_b, y2=y2, srid=args.srid)
                        sql = "insert into {table} ({column}) select {column} from (select ST_Multi((ST_Dump(ST_Split({column}, {line_to_split}))).geom) as {column} from {table} where {id_column} = {id_value}) as inner_table where st_xmax({column}) <= {x1};".format(table=args.table, column=args.column, line_to_split=line_to_split, id_column=args.id, id_value=id, x1=x1_b)
                        cur.execute(sql)
                    else:
                        if buffer_percent is not None:
                            buffer = ysize * (buffer_percent / 100)
                        y1_a = y1 - buffer
                        y2_a = y1_a
                        line_to_split = "ST_SetSRID( ST_MakeLine( ST_MakePoint( {x1}, {y1} ), ST_MakePoint( {x2}, {y2} ) ), {srid})".format(x1=x1, y1=y1_a, x2=x2, y2=y2_a, srid=args.srid)
                        sql = "insert into {table} ({column}) select {column} from (select ST_Multi((ST_Dump(ST_Split({column}, {line_to_split}))).geom) as {column} from {table} where {id_column} = {id_value}) as inner_table where st_ymin({column}) >= {y1};".format(table=args.table, column=args.column, line_to_split=line_to_split, id_column=args.id, id_value=id, y1=y1_a)
                        cur.execute(sql)

                        y1_b = y1 + buffer
                        y2_b = y1_b
                        line_to_split = "ST_SetSRID( ST_MakeLine( ST_MakePoint( {x1}, {y1} ), ST_MakePoint( {x2}, {y2} ) ), {srid})".format(x1=x1, y1=y1_b, x2=x2, y2=y2_b, srid=args.srid)
                        sql = "insert into {table} ({column}) select {column} from (select ST_Multi((ST_Dump(ST_Split({column}, {line_to_split}))).geom) as {column} from {table} where {id_column} = {id_value}) as inner_table where st_ymax({column}) <= {y1};".format(table=args.table, column=args.column, line_to_split=line_to_split, id_column=args.id, id_value=id, y1=y1_b)
                        cur.execute(sql)

                    
                # remove old
                cur.execute("delete from {table} where {id_column} = {id_value};".format(table=args.table, id_column=args.id, id_value=id))

    finally:
        conn.commit()

if __name__ == '__main__':
    main()
