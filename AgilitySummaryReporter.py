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
import time
import datetime
import io
import os

# input & output files to use as parameters
ppt_csv_file    = 'PawPrint Trials Results.csv'
ftr_csv_file    = 'My Results.csv'
report_file = 'report.html'
debug_file  = 'dump.html'

# List of columns in the 'PawPrintTrials' source CSV files. This needs to be updated if the CSV format changes.
ppt_csv_cols = ["Date","Trial","Location","Dog","Handler","Class","Judge","Yards","SCT","Time","YPS","R","S","W","T","F","E","Score","Result","Place","MACH Pts","T2B Pts","Top25","Run ID"]

# List of columns in the 'FeelTheRush' source CSV files. This needs to be updated if the CSV format changes.
ftr_csv_cols = ["Dogname","Trial Date","Club","Trial Day","Judge","Level","Class","SCT","Points","Time","Qual"]

# List of columns to include for for each table that is output
table_cols = {
    "Master Std":   ["Date","Trial","Location","Judge","Yards","SCT","Time","YPS","Avg YPS","Avg15 YPS","Faults","Result","Avg Q Rate","Avg15 Q Rate","Place","MACH Pts","Avg MACH Pts","Avg15 MACH Pts"],
    "Master JWW":   ["Date","Trial","Location","Judge","Yards","SCT","Time","YPS","Avg YPS","Avg15 YPS","Faults","Result","Avg Q Rate","Avg15 Q Rate","Place","MACH Pts","Avg MACH Pts","Avg15 MACH Pts"],
    "Prem Std":     ["Date","Trial","Location","Judge","Faults","Result","Avg Q Rate","Avg15 Q Rate","Place","Top25"],
    "Prem JWW":     ["Date","Trial","Location","Judge","Faults","Result","Avg Q Rate","Avg15 Q Rate","Place","Top25"],
    "Master FAST":  ["Date","Trial","Location","Judge","Faults","Score","Avg Score","Avg15 Score","Result","Avg Q Rate","Avg15 Q Rate","Place"],
    "T2B" :         ["Date","Trial","Location","Judge","Faults","Result","Avg Q Rate","Avg15 Q Rate","Place","T2B Pts","Avg T2B Pts","Avg15 T2B Pts"],
    "Other" :       ["Date","Trial","Location","Class","Judge","Yards","SCT","Time","YPS","Avg YPS","Avg15 YPS","Faults","Score","Avg Score","Avg15 Score","Result","Avg Q Rate","Avg15 Q Rate","Place","MACH Pts","Avg MACH Pts","Avg15 MACH Pts","T2B Pts","Avg T2B Pts","Avg15 T2B Pts","Top25"],
}

# List of all colunm names used for dumping the master row table to a debug file
all_cols = ["Date","Trial","Location","Dog","Handler","Class","Group","Judge","Yards","SCT","Time","YPS","Avg YPS","Avg15 YPS","R","S","W","T","F","E","Score","Avg Score","Avg15 Score","Result","Avg Q Rate","Avg15 Q Rate",
            "Place","MACH Pts","Avg MACH Pts","Avg15 MACH Pts","T2B Pts","Avg MACH Pts","Avg15 MACH Pts","Top25","Run ID"]

# CSS Properties used and values by column name
css_prop = ("min-width", "text-align", "background-color")
col_css = {
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
    "YPS":          ["32px", "center", "#a569bd"],
    "Avg YPS":      ["32px", "center", "#d693f0"],
    "Avg15 YPS":    ["32px", "center", "#EBDEF0"],
    "Faults":       ["80px", "left"],
    "Score":        ["45px", "center"],
    "Avg Score":    ["45px", "center"],
    "Avg15 Score":  ["45px", "center"],
    "Result":       ["45px", "center"],
    "Avg Q Rate":   ["45px", "center", "#58D68d"],
    "Avg15 Q Rate": ["45px", "center", "#AAE9C5"],
    "Place":        ["45px", "center"],
    "MACH Pts":     ["77px", "center", "#f0d70b"],
    "Avg MACH Pts": ["77px", "center" , "#d3c65e"],
    "Avg15 MACH Pts":["77px", "center", "#f4eec1"],
    "T2B Pts":      ["60px", "center"],
    "Avg T2B Pts":  ["60px", "center"],
    "Avg15 T2B Pts":["60px", "center"],
    "Top25":        ["46px", "center"],

    'Filename':     ["235px", "left"],
    'Run Count':    ["100px", "center"],
    'File Date':    ["200px", "left"],
    'Last Run Date':["200px", "left"],
}

nac_cutoff_day = 1
nac_cutoff_month = 12


# Global default delimiter for CSV reader.
# TODO: I'm not sure it's necessary
DEFAULT_DELIMITER = ','

# Global datetime format strings
# '12/04/2022 02:34 PM'
FORMAT_DATE_TIME = "%m/%d/%Y %I:%M %p"
# '12/04/2022'
FORMAT_DATE = "%m/%d/%Y"

# Reads a CSV input file into a list of dict using the column headings 
def read_csv(file, csv_cols, source):
    row_count = 0
    rows = [ ]
    last_run_date = datetime.datetime(1999, 12, 31, 0, 0).date()
    print('Reading', file)
    with open(file, newline='', mode='r', encoding='utf-8-sig') as f:
        # skip the header row
        f.readline( )
        # read the remainder of the file as CSV rows
        reader = csv.reader(f)
        for r in reader:
            # Reader returns a list of string for each CSV row
            # Convert each CSV row to dict with column names as key
            if len(r) > 5:
                row = dict()
                index = 0
                for c in csv_cols:
                    row[c] = r[index]
                    index += 1
                    if c in ("Date", "Trial Date"):
                        # parse the date field into a date object
                        d = datetime.datetime.strptime(row[c], FORMAT_DATE).date()
                        row["SortDate"] = d
                        if d > last_run_date:
                            last_run_date = d
                rows.append(row)
                row_count += 1
    print (row_count, 'lines read.')
    print ("Last run", last_run_date.strftime(FORMAT_DATE))

    # get the modification date/time of the file
    os_date = os.path.getmtime(file)
    file_date = datetime.datetime.fromtimestamp(os_date)
    print_date = file_date.strftime(FORMAT_DATE_TIME)
    print ("File Date", print_date)
  
    file_meta = dict()
    file_meta['Source'] = source
    file_meta['Filename'] = file
    file_meta['Run Count'] = str(row_count)
    file_meta['File Date'] = file_date.strftime(FORMAT_DATE_TIME)
    file_meta['Last Run Date'] = last_run_date.strftime(FORMAT_DATE)
    return (rows, file_meta)

# Remove absence rows 
def remove_absences(rows):
        rows[:] = [r for r in rows if not r["Result"] == 'A']

# Group classes by their common name.
# For example, [Master Std # 1 8"P] and [Master Std # 2 8"P] are in the same group called [Master Std]
def group_classes(rows):
    print('Grouping classes')
    groups = ('Master Std','Master JWW','Prem Std','Prem JWW','Master FAST','T2B','Other')
    for row in rows:
        c = row.get('Class')
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
        dogs.add(row.get('Dog'))
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
            if row.get(f) == '1':
                faults.append(f) 
            elif row.get(f) != '0':
                faults.append(row.get(f) + f)
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
            table_rows = [row for row in rows if row.get('Dog')==dog and row.get('Group')==group]
            for col in stat_cols:
                # history is a running list of values for this stat column
                history = list()
                for row in table_rows:
                    # Q Rate is computed for all rows; other stats only for the Q rows
                    if col == "Q Rate" or row.get("Result") == "Q":
                        # Use 100 or 0 for Q or NQ to report average result in percent
                        if col == "Q Rate":
                            value = 100 if row.get("Result") == "Q" else 0
                            # save the Q or NQ as a value of 0 or 10 for sane plotting
                            row["Q Rate"] = value / 10 
                        else:
                            value = float(row.get(col)) if row.get(col) else 0
                        # append this value to the running list of values for this class
                        history.append(value)
                        # compute average of *all* values up to this point
                        row["Avg " + col] = str(round(statistics.mean(history),2))
                        # compute average of last 15 values
                        row["Avg15 " + col] = str(round(statistics.mean(history[-15:]),2))
                    else:
                        # No stats for NQ rows (except Q-Rate)
                        row["Avg " + col] = ''
                        row["Avg15 " + col] = ''
    return stat_cols

# Calulate the MACH Pts for National Agility Championship (NAC)
def calc_nac_points(rows, dog, year):
    nac_groups = ("Master Std", "Master JWW")
    nac_rows = [row for row in rows if row.get('Dog')==dog and row.get('Group') in nac_groups]
    # NAC year runs from Dec 1 to Nov 30
    nac_start_date = datetime.datetime(year-2, 12, 1, 0, 0).date()
    nac_end_date   = datetime.datetime(year-1, 11, 30, 0, 0).date()
    nac_points = 0
    for row in nac_rows:
        if nac_start_date <= row.get('SortDate') and  row.get('SortDate') <= nac_end_date:
            pts = int(row.get('MACH Pts',0)) if row.get('MACH Pts') else 0
            # remove negative MACH points
            if pts > 0:
                nac_points += pts
    nac_row = dict()
    nac_row["Result"] = "Q"  # Required for Table CSS and filtering
    nac_row["NAC Year"] = str(year)
    nac_row["Start Date"] = nac_start_date.strftime(FORMAT_DATE)
    nac_row["End Date"] = nac_end_date.strftime(FORMAT_DATE)
    nac_row["MACH Pts"] = str(nac_points)
    return nac_row

# Convert a pretty column name to its clean CSS class name
def col_css_class(c):
    return 'col-' + c.lower().replace(' ','-')

# Convert a pretty row name to its claen CSS class name
def row_css_class(r):
    return 'row-' + r.lower().replace(' ','-')
    
# Write the header (including CSS) and main body start to the HTML output file
def html_header(w):
    # html header
    w.write('<!DOCTYPE html>')
    w.write('<html>\n')
    w.write('<head>\n')
    w.write('<title>Agility Summary Report</title>\n')
    # CSS styling -- include all here to keep the final report a single file
    w.write('  <style>\n')
    w.write('    body {font-family: Arial, Helvetica, sans-serif;}\n')   
    w.write('    table, th, td {border: 1px solid #ddd;}\n')
    w.write('    table {border-collapse: collapse;}\n')
    w.write('    th, td {padding: 0px 5px; text-align: left;}\n')
    w.write('    th {font-weight: bold; text-decoration: underline;}\n')
    # emmit CSS for each table column
    for col in col_css:
        # CSS selector
        w.write('    .'+ col_css_class(col) + ' {')
        i = 0
        # grap the CSS properties for this column
        css = col_css[col]
        # write all the properties if they are not empty
        for prop in css_prop:
            if (i < len(css)) and css[i]:
                w.write(prop + ':' +  css[i] + '; ')
            i += 1
        # close this CSS class
        w.write('}\n')
    # emmit CSS for each type of table row
    w.write('    .row-q  {color:#000;}\n')
    w.write('    .row-nq {color:#ccc;}\n')
    w.write('    .row-a  {color:#ccc;}\n')
    w.write('    .scroll-x {overflow-x:scroll;}\n')
    w.write('  </style>\n')
    # no Javascript (not needed!)
    w.write('</head>\n')
    # html body
    w.write('<body>\n')

# Write the main body close to the HTML output file
def html_footer(w):
    w.write('</body>\n')
    w.write('</html>\n')

# Write a table of file meta data
def file_table(file_metas):
    print('  Source File Table')
    cols = ['Source','Filename','Run Count','File Date','Last Run Date']
    now = datetime.datetime.now().strftime(FORMAT_DATE_TIME)
    w.write('<p><b>Report Date:</b> ' + now + '</p>\n')
    w.write('<h2>Source Files</h2>\n')
    w.write('<table>\n')
    # table heading
    w.write('  <thead>\n')
    w.write('  <tr>\n')
    for c in cols:
        w.write('    <th class="' + col_css_class(c) +'" >' + c + '</th>\n')
    w.write('  </tr>\n')
    w.write('  </thead>\n')
    # table body
    w.write('  <tbody>\n')
    for meta in file_metas:
        w.write('  <tr>\n')
        for c in cols:
            w.write('    <td class="' + col_css_class(c) +'" >' + meta[c] + '</td>\n')
        w.write('  </tr>\n')
    w.write('  </tbody>\n')
    w.write('</table>\n')

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
    css_class = 'class="' + row_css_class(row.get("Result")) +'"' if row.get("Result") else ''
    w.write('  <tr ' + css_class + '>\n')
    for c in cols:
        w.write('    <td class="' + col_css_class(c) +'" >' + row.get(c, '') + '</td>\n')
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

# Create a plot (x-y graph) of the base column and its computed stats columns
# Uses the date as the x-axis, groups in months
# plot is converted to SVG and returned as a large python string
def plot_as_svg(table_rows, base_col):
    # create a list of columns to plott together
    plot_cols = [base_col, "Avg "+base_col, "Avg15 "+base_col ]

    # create a blank plot to start with
    plt.close('all')
    fig, ax = plt.subplots()
    # set size
    fig.set_figheight(5)
    fig.set_figwidth(18)

    # set default max value for Y-axis based on type of data
    # Note: this will be auto-adjusted higher if the data exceeds this limit
    y_maxes = {"Q Rate":100, "YPS":5, "Score":100, "MACH Pts":10, "T2B Pts":15}
    y_max = y_maxes[base_col]
        
    # plot y (value) vs x (date) for each column
    for col in plot_cols:
        xdata = []
        ydata = []
        for row in table_rows:
            if col == "Q Rate" or row.get("Result") == "Q":
                x = datetime.datetime.strptime(row["Date"], FORMAT_DATE)
                y  = float(row.get(col,0)) if row.get(col) else 0
                # do we need to adjust the max y value of the plot?
                if y > y_max:
                    # round up to next multiple of 5
                    if (y/5) == int(y/5):
                        y_max = y
                    else:
                        y_max = 5*(int(y/5)+1)
                xdata.append(x)
                ydata.append(y)
        plt.plot(xdata,ydata,'o-')
    # add legend to Y values
    # first change the base "Q Rate" to a better name
    if base_col == "Q Rate":
        plot_cols[0] = "Q / NQ"
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

file_metas = []
# Read the PawPrintTrials CSV file into memory
(rows, meta) = read_csv(ppt_csv_file, ppt_csv_cols, "PawPrintTrials")
file_metas.append(meta)

# Read the FeelTheRuch CSV file into memory
(ftr_rows, meta) = read_csv(ftr_csv_file, ftr_csv_cols, "FeelTheRush")
file_metas.append(meta)

# TODO: Merge FTR rows into the PPT rows, which is the master table

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
    file_table(file_metas)
    # each dog gets its own section
    for dog in dogs:
        section_header(w, dog)
        # create a table for each group (aka agility class)
        for group in groups:
            table_rows = [row for row in rows if row.get('Dog')==dog and row.get('Group')==group]
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
        # Table of MACH pts for NAC by year
        # TODO: Fixed hard-coded years
        nac_cols = ("NAC Year", "Start Date", "End Date", "MACH Pts")
        table_header(w, dog, "NAC Points", nac_cols)
        for year in (2022, 2023, 2024, 2025):
            row = calc_nac_points(rows, dog, year)
            table_row(w, dog, "NAC Points", nac_cols, row)
        table_footer(w)
        section_footer(w)
    html_footer(w)

# optionally create the debug file with all data in one giant table
if False:
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
