# Paw Print Trials Report formater
# Copyright (c) 2022 John Vedder.  MIT License
#
# Formats the results CSV file downloaded from PawPrintTrials.com into a
# single file HTML report organized by dog and agility class.
# Running averages are computed and plotted for select columns.
#

import csv
import statistics
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
import datetime
import io

# input & output files to use as parameters
csv_file    = 'PawPrint Trials Results.csv'
report_file = 'report.html'
debug_file  = 'dump.html'

# List of columns in the source CSV file. This needs to be updated if the CSV format changes.
# TODO: There should be a way to read this from the CSV file and then handle column name mis-matches
csv_cols = ["Date","Trial","Location","Dog","Handler","Class","Judge","Yards","SCT","Time","YPS","R","S","W","T","F","E","Score","Result","Place","MACH Pts","T2B Pts","Top25","Run ID"]

# List of columns to include for for each table that is output
table_cols = {
    "Master Std":   ["Date","Trial","Location","Judge","Yards","SCT","Time","YPS","Avg YPS","Avg15 YPS","Faults","Score","Avg Score","Avg15 Score","Result","Avg Q Rate","Avg15 Q Rate","Place","MACH Pts","Avg MACH Pts","Avg15 MACH Pts"],
    "Master JWW":   ["Date","Trial","Location","Judge","Yards","SCT","Time","YPS","Avg YPS","Avg15 YPS","Faults","Score","Avg Score","Avg15 Score","Result","Avg Q Rate","Avg15 Q Rate","Place","MACH Pts","Avg MACH Pts","Avg15 MACH Pts"],
    "Prem Std":     ["Date","Trial","Location","Judge","Faults","Score","Result","Avg Q Rate","Avg15 Q Rate","Place","Top25"],
    "Prem JWW":     ["Date","Trial","Location","Judge","Faults","Score","Result","Avg Q Rate","Avg15 Q Rate","Place","Top25"],
    "Master FAST":  ["Date","Trial","Location","Judge","Faults","Score","Avg Score","Avg15 Score","Result","Avg Q Rate","Avg15 Q Rate","Place"],
    "T2B" :         ["Date","Trial","Location","Judge","Faults","Result","Avg Q Rate","Avg15 Q Rate","Place","T2B Pts","Avg T2B Pts","Avg15 T2B Pts"],
    "Other" :       ["Date","Trial","Location","Class","Judge","Yards","SCT","Time","YPS","Avg YPS","Avg15 YPS","Faults","Score","Avg Score","Avg15 Score","Result","Avg Q Rate","Avg15 Q Rate","Place","MACH Pts","Avg MACH Pts","Avg15 MACH Pts","T2B Pts","Avg T2B Pts","Avg15 T2B Pts","Top25"],
}

# List of all colunm names used for dumping the master row table to a debug file
all_cols = ["Date","Trial","Location","Dog","Handler","Class","Group","Judge","Yards","SCT","Time","YPS","Avg YPS","Avg15 YPS","R","S","W","T","F","E","Score","Avg Score","Avg15 Score","Result","Avg Q Rate","Avg15 Q Rate",
            "Place","MACH Pts","Avg MACH Pts","Avg15 MACH Pts","T2B Pts","Avg MACH Pts","Avg15 MACH Pts","Top25","Run ID"]

# Collection of CSS classe to emit
col_css = {
    # Column:        [min-width, text-align]
    "Date" :        ["81px", "left"],
    "Trial":        ["236px", "left"],
    "Location":     ["217px", "left"],
    "Dog":          ["35px", "left"],
    "Handler":      ["100px", "left"],
    "Class":        ["130px", "left"],
    "Group":        ["130px", "left"],
    "Judge":        ["135px", "left"],
    "Yards":        ["44px", "center"],
    "SCT":          ["32px", "center"],
    "Time":         ["41px", "center"],
    "YPS":          ["32px", "center"],
    "Avg YPS":      ["32px", "center"],
    "Avg15 YPS":    ["32px", "center"],
    "Faults":       ["80px", "left"],
    "Score":        ["45px", "center"],
    "Avg Score":    ["45px", "center"],
    "Avg15 Score":  ["45px", "center"],
    "Result":       ["45px", "center"],
    "Avg Q Rate":   ["45px", "center"],
    "Avg15 Q Rate": ["45px", "center"],
    "Place":        ["45px", "center"],
    "MACH Pts":     ["77px", "center"],
    "Avg MACH Pts": ["77px", "center"],
    "Avg15 MACH Pts":["77px", "center"],
    "T2B Pts":      ["60px", "center"],
    "Avg T2B Pts":  ["60px", "center"],
    "Avg15 T2B Pts":["60px", "center"],
    "Top25":        ["46px", "center"]
}

# Global default delimiter for CSV reader.
# TODO: I'm not sure it's necessary
DEFAULT_DELIMITER = ','

# Reads the master CSV input file
def read_csv(file):
    row_count = 0
    rows = [ ]
    print('Reading', file)
    with open(file, newline='', mode='r', encoding='utf-8-sig') as f:
        f.readline( )
        reader = csv.reader(f)
        for r in reader:
            # Reader returns a list of string for each CSV row
            # Convert CSV row to dict with column names as key
            if len(r) > 10:
                row = dict()
                index = 0
                for c in csv_cols:
                    row[c] = r[index]
                    index += 1
                rows.append(row)
                row_count += 1
    print (row_count, 'lines read.')
    return rows

# Remove absence rows 
def remove_absences(rows):
        rows[:] = [r for r in rows if not r["Result"] == 'A']

# Group classes by their common name.
# For example, [Master Std # 1 8"P] and [Master Std # 2 8"P] are in the same group called [Master Std]
def group_classes(rows):
    print('Grouping classes')
    groups = ('Master Std','Master JWW','Prem Std','Prem JWW','Master FAST','T2B','Other')
    for row in rows:
        c = row['Class']
        group = 'Other'
        for g in groups:
            if c.startswith(g):
                group = g
        row['Group'] = group
    return groups

# Creates a reverse sorted list of unique dog names
def group_dogs(rows):
    print('Grouping Dogs')
    dogs = set()
    for row in rows:
        dogs.add(row['Dog'])
    dogs = list(dogs)
    dogs.sort(reverse=True)
    return dogs

# Merge fault count columns into one text column
# For example R=1, W=2, other fault=0 becomes 'R,2W'
def merge_faults(rows):
    print('Merging Faults')
    for row in rows:
        faults = []
        for f in ("R","S","W","T","F","E"):
            if row[f] == '1':
                faults.append(f) 
            elif row[f] != '0':
                faults.append(row[f] + f)
        row['Faults'] = ','.join(faults)

# Calculate the statistics (running averages) for specific columns for all rows
# The calculated stats are added as new 'columns' to the row dictionary as text strings
# NQ rows are assigned an empty string
def calc_stats(rows, dogs, groups):
    print('Calculating stats')
    stat_cols = ["Q Rate", "YPS", "Score", "MACH Pts", "T2B Pts"]
    for dog in dogs:
        print('  Dog:', dog)
        for group in groups:
            print('    Stats:', dog, group)
            table_rows = [row for row in rows if row['Dog']==dog and row['Group']==group]
            for col in stat_cols:
                # history is a running list of values for this stat column
                history = list()
                for row in table_rows:
                    # Q Rate is computed for all rows; other stats only for the Q rows
                    if col == "Q Rate" or row["Result"] == "Q":
                        # Use 100 or 0 for Q or NQ to report average result in percent
                        if col == "Q Rate":
                            value = 100 if row["Result"] == "Q" else 0
                            row["Q Rate"] = value
                        else:
                            value = float(row[col]) if row[col] else 0
                        # append this value to the running list of values for this class
                        history.append(value)
                        row["Avg " + col] = str(round(statistics.mean(history),2))
                        row["Avg15 " + col] = str(round(statistics.mean(history[-15:]),2))
                    else:
                        # No stats for NQ rows (except Q-Rate)
                        row["Avg " + col] = ''
                        row["Avg15 " + col] = ''
    return stat_cols

# Convert a column name to its CSS class name
def col_css_class(c):
    return 'col-' + c.lower().replace(' ','-')

# Convert a row name to its CSS class name
def row_css_class(r):
    return 'row-' + r.lower().replace(' ','-')
    
# Write the header (including CSS) and main body start to the HTML output file
def html_header(w):
    # html header
    w.write('<!DOCTYPE html>')
    w.write('<html>\n')
    w.write('<head>\n')
    w.write('  <style>\n')
    w.write('    body {font-family: Arial, Helvetica, sans-serif;}\n')   
    w.write('    table, th, td {border: 1px solid # ddd;}\n')
    w.write('    table {border-collapse: collapse;}\n')
    w.write('    th, td {padding: 0px 5px; text-align: left;}\n')
    w.write('    th {font-weight: bold; text-decoration: underline;}\n')
    for c in col_css:
        w.write('    .'+ col_css_class(c) + ' {min-width:'+ col_css[c][0] +'; text-align:'+ col_css[c][1] +';}\n')
    w.write('    .row-q  {color:# 000;}\n')
    w.write('    .row-nq {color:# ccc;}\n')
    w.write('    .row-a  {color:# ccc;}\n')
    
    w.write('    .scroll-x {overflow-x:scroll;}\n')
    w.write('  </style>\n')
    w.write('</head>\n')
    # html body
    w.write('<body>\n')

# Write the main body close to the HTML output file
def html_footer(w):
    w.write('</body>\n')
    w.write('</html>\n')

# Write a new section start to the HTML output file
def section_header(w, dog):
    print('  Section:', dog)
    w.write('<section>')
    w.write('<h1>' + dog + '</h1>\n')

# Write a section close to the HTML output file
def section_footer(w):
    w.write('</section>')

# Write a new table start to the HTML output file
def table_header(w, dog, group, cols):
    print('    Table:', dog, group)
    # table heading row
    w.write('<h2>' + dog + ' &ndash; ' + group + '</h2>\n')  
    w.write('<div class="scroll-x">\n')
    w.write('<table>\n')
    w.write('  <thead>\n')
    w.write('  <tr>\n')
    for c in cols:
        w.write('    <th class="' + col_css_class(c) +'" >' + c + '</th>\n')
    w.write('  </tr>\n')
    w.write('  </thead>\n')

# Write a single table row to the HTML output file
def table_row(w, dog, group, cols, row):
    # table body rows
    css_class = 'class="' + row_css_class(row["Result"]) +'"' if row["Result"] else ''
    w.write('  <tr ' + css_class + '>\n')
    for c in cols:
        w.write('    <td class="' + col_css_class(c) +'" >' + row[c] + '</td>\n')
    w.write('  </tr>\n')

# Write an table close to the HTML output file
def table_footer(w):       
    w.write('</table>\n')
    w.write('</div>\n')

# Write an SVG string (of a plot) with a headline to the HTML output file.
def write_svg_plot(w, svg, col):
    w.write('<div class="plot">\n')
    w.write('<h2>' + dog + ' &ndash; ' + group+ ' &ndash; ' + col + '</h2>\n') 
    w.write(svg)
    w.write('</div>')

# Create a plot (x-y graph) of the base columnand its computed stats columns
# Uses the date as the x-axis, groups in months
# plot ois converted to SVG and returned as a large python string
def plot_as_svg(table_rows, base_col):
    # create a list of columns to plott together
    plot_cols = [base_col, "Avg "+base_col, "Avg15 "+base_col ]

    # Do not plot the Q-rate itself, only the averages
    if base_col == "Q Rate":
        plot_cols = plot_cols[1:] 

    # create a blank plot to start with
    plt.close('all')
    fig, ax = plt.subplots()
    # set size
    fig.set_figheight(5)
    fig.set_figwidth(15)

    # set max value for Y-axis based on type of data
    # Note: this get auto-adjusted higher if the data exceeds this limit
    if base_col in ("Q Rate", "Score"):
        y_max=100
    elif base_col in ("YPS"):
        y_max = 5
    else: # ("MACH Pts", "T2B Pts"):
        y_max = 10
        
    # plot y vs x (value vs date) for each column
    for col in plot_cols:
        xdata = []
        ydata = []
        for row in table_rows:
            if row[col]:
                x = datetime.datetime.strptime(row["Date"], "%m/%d/%Y")
                y  = float(row[col]) if row[col] else 0
                # do we need to adjust the max y value of the plot?
                if y > y_max:
                    # round up to extt multiple of 5
                    if (y/5) == int(y/5):
                        y_max = y
                    else:
                        y_max = 5*(int(y/5)+1)
                xdata.append(x)
                ydata.append(y)
        plt.plot(xdata,ydata,'o-')
    # add legend to Y values
    ax.legend( plot_cols )
    # format X-axis to show the dates correctly with ticks at each month
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    fig.autofmt_xdate()
    # set limits of y-axis
    ax.set_ylim(0, y_max)
    # Save plot as SVG to a string buffer in lieu of a file
    buffer = io.StringIO()
    fig.savefig(buffer, format='svg', dpi=1200, bbox_inches='tight')
    svg = buffer.getvalue()
    # clear the plot (to free up memory)
    plt.close('all')
    return svg


# # 
# # Main execution starts here
# #    

# Read the main CSV file into memory
rows = read_csv(csv_file)

# clean up data
remove_absences(rows)
merge_faults(rows)

# Get lists of unique dogs and catlog classes into groups
dogs = group_dogs(rows)
groups = group_classes(rows)

# Calculate and add statistics columns to the data 
stat_cols = calc_stats(rows, dogs, groups)

# Create the HTML output file
print('Writing', report_file)
with open(report_file, 'w') as w:
    html_header(w)
    # each dog gets its own section
    for dog in dogs:
        section_header(w, dog)
        # create a table for each group (aka agility class)
        for group in groups:
            table_rows = [row for row in rows if row['Dog']==dog and row['Group']==group]
            # skip empty tables and odd-ball classes
            if table_rows and (not group == "Other"):
                # Create the table
                table_header(w, dog, group, table_cols[group])
                for row in table_rows:
                    table_row(w, dog, group, table_cols[group], row)
                table_footer(w)
                # Create a plot for each stat_col in this table
                for col in stat_cols:
                    # only show plot if applicable to this group/table
                    if (col in table_cols[group]) or (col == "Q Rate"):
                        print('     Plot:', dog, group, col)
                        svg = plot_as_svg(table_rows, col)
                        write_svg_plot(w, svg, col)
                        svg = None # help garbage collect
        section_footer(w)
    html_footer(w)

# optionally create the debug file with all data in one giant table
if True:
    print('Writing', debug_file)
    with open(debug_file, 'w') as w:
        html_header(w)
        section_header(w, "Debug")
        table_header(w, "Debug", "dump", all_cols)
        for row in rows:
            table_row(w, dog, group, all_cols, row)
        table_footer(w)
        section_footer(w)
        html_footer(w)

# Let the user know this script came to completion
print('Done.')