# Dog Agility Trial Summary Reporter
# Copyright (c) 2023 John Vedder.  MIT License
# 
# Formats the dog agility results data downloaded from PawPrintTrials.com (PPT)
# and FeelTheRushTrials.com (FTR) into a unified HTML report. The source is a
# CSV file from each site. The report includes running averages and graphs
# for select columns.

import csv
import statistics
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
import time
import datetime
import io
import os

# Input & output files to use as parameters
ppt_csv_file = 'PawPrint Trials Results.csv'
ftr_csv_file = 'My Results.csv'
report_file = 'report.html'
debug_file = 'dump.html'

# List of columns in the 'PawPrintTrials' source CSV files. This needs to be updated if the CSV format changes.
ppt_csv_cols = ["Date","Trial","Location","Dog","Handler","Class","Judge","Yards","SCT","Time","YPS","R","S","W","T","F","E","Score","Result","Place","MACH Pts","T2B Pts","Top25","Run ID"]

# List of columns in the 'FeelTheRush' source CSV files. This needs to be updated if the CSV format changes.
ftr_csv_cols = ["Dogname","Trial Date","Club","Trial Day","Judge","Level","Class","SCT","Points","Time","Qual"]

# List of columns to include for for each table that is output
table_cols = {
    "Master Std":   ["Date","Source","Club","Location","Judge","Trial Num","Yards","SCT","Time","YPS","Avg YPS","Avg15 YPS","Faults","Result","Avg Q Rate","Avg15 Q Rate","Place","MACH Pts","Avg MACH Pts","Avg15 MACH Pts"],
    "Master JWW":   ["Date","Source","Club","Location","Judge","Trial Num","Yards","SCT","Time","YPS","Avg YPS","Avg15 YPS","Faults","Result","Avg Q Rate","Avg15 Q Rate","Place","MACH Pts","Avg MACH Pts","Avg15 MACH Pts"],
    "Premier Std":  ["Date","Source","Club","Location","Judge","Trial Num","Faults","Result","Avg Q Rate","Avg15 Q Rate","Place","Top25"],
    "Premier JWW":  ["Date","Source","Club","Location","Judge","Trial Num","Faults","Result","Avg Q Rate","Avg15 Q Rate","Place","Top25"],
    "Master FAST":  ["Date","Source","Club","Location","Judge","Trial Num","Faults","Score","Avg Score","Avg15 Score","Result","Avg Q Rate","Avg15 Q Rate","Place"],
    "T2B" :         ["Date","Source","Club","Location","Judge","Trial Num","Faults","Result","Avg Q Rate","Avg15 Q Rate","Place","T2B Pts","Avg T2B Pts","Avg15 T2B Pts"],
    "Other" :       ["Date","Source","Club","Location","Class","Trial Num","Judge","Yards","SCT","Time","YPS","Avg YPS","Avg15 YPS","Faults","Score","Avg Score","Avg15 Score","Result","Avg Q Rate","Avg15 Q Rate","Place","MACH Pts","Avg MACH Pts","Avg15 MACH Pts","T2B Pts","Avg T2B Pts","Avg15 T2B Pts","Top25"],
}

# Standard list of class names (called groups because class is a reserved word)
levels =  ('Novice','Open','Excellent','Master','Premier')
classes = ('Std','JWW','FAST','T2B')
groups =  ('Master Std','Master JWW','Premier Std','Premier JWW','Master FAST','T2B','Other')

# CSS Properties used and values by column name
css_prop = ("min-width", "text-align", "background-color")
col_css = {
    "Date" :        ["81px", "left"],
    "Trial":        ["236px", "left"],
    "Club":         ["236px", "left"],
    "Location":     ["217px", "left"],
    "Trial Num":    ["60px","center"],
    "Dog":          ["35px", "left"],
    "Handler":      ["100px", "left"],
    "Class":        ["130px", "left"],
    "Group":        ["130px", "left"],
    "Judge":        ["135px", "left"],
    "Yards":        ["44px", "center"],
    "SCT":          ["32px", "center"],
    "Time":         ["41px", "center"],
    "YPS":          ["32px", "center", "#a569bd"], #dark purple
    "Avg YPS":      ["32px", "center", "#d693f0"], #mid purple
    "Avg15 YPS":    ["32px", "center", "#EBDEF0"], #light purple
    "Faults":       ["80px", "left"],
    "Score":        ["45px", "center"],
    "Avg Score":    ["45px", "center"],
    "Avg15 Score":  ["45px", "center"],
    "Result":       ["45px", "center"],
    "Avg Q Rate":   ["45px", "center", "#58D68d"], #dark green
    "Avg15 Q Rate": ["45px", "center", "#AAE9C5"], #light green
    "Place":        ["45px", "center"],
    "MACH Pts":     ["77px", "center", "#f0d70b"], #dark yellow
    "Avg MACH Pts": ["77px", "center" , "#d3c65e"], #mid yellow
    "Avg15 MACH Pts":["77px", "center", "#f4eec1"], #light yellow
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

# default date to use for missing dates: 12/31/1999
DEFAULT_DATE = datetime.datetime(1999, 12, 31, 0, 0).date()

# Reads a CSV input file into a list of dict using the column headings 
def read_csv(file, csv_cols, source):
    run_count = 0
    runs = []
    last_run_date = DEFAULT_DATE
    print('Reading', file)
    with open(file, newline='', mode='r', encoding='utf-8-sig') as f:
        # skip the header line
        f.readline( )
        # read the remainder of the file as CSV rows
        reader = csv.reader(f)
        for row in reader:
            # Reader returns a list of string for each CSV row
            # Convert each CSV row to dict with column names as key
            if len(row) > 5:
                run = dict()
                run['Source'] = source
                index = 0
                for c in csv_cols:
                    run[c] = row[index]
                    index += 1
                    if c in ("Date", "Trial Date"):
                        # parse the date field into a date object
                        d = datetime.datetime.strptime(run[c], FORMAT_DATE).date()
                        run["SortDate"] = d
                        if d > last_run_date:
                            last_run_date = d
                runs.append(run)
                run_count += 1
    print (run_count, 'lines read.')
    print ("Last run", last_run_date.strftime(FORMAT_DATE))

    # get the modification date/time of the file
    os_date = os.path.getmtime(file)
    file_date = datetime.datetime.fromtimestamp(os_date)
    print_date = file_date.strftime(FORMAT_DATE_TIME)
    print ("File Date", print_date)
  
    file_meta = dict()
    file_meta['Source'] = source
    file_meta['Filename'] = file
    file_meta['Run Count'] = str(run_count)
    file_meta['File Date'] = file_date.strftime(FORMAT_DATE_TIME)
    file_meta['Last Run Date'] = last_run_date.strftime(FORMAT_DATE)
    return (runs, file_meta)

# Gets the agility level from a string that contains the level name
def get_level(text):
    level = ''
    for l in levels:
        if l in text:
            level = l
            break
    # Special case: PPT uses 'Prem' for 'Premier'
    if 'Prem' in text:
        level = 'Premier'
    return level

# Gets the agility class from a string that contains the class name
def get_class(text):
    agility_class = ''
    for c in classes:
        if c in text:
            agility_class = c
            break
    return agility_class

# Maps PawPrintTrials column names into the preferred names
def map_ppt_columns(runs):
    for run in runs:
        # mark the data source
        run['Source'] = 'PawPrint'
        # the 'Trial' field is actually the Club Name
        run['Club'] = run.get('Trial','')
        # 2 trials on same day are marked #1 and #2 in the 'Class' field
        # single trial on a day has neither #1 or #2, so default to #1
        run['Trial Num'] = '2' if '#2' in run.get('Class','') else '1'
        # Define level & class by their simple name.
        # PPT 'Class' includes both the level and class
        ppt_class = run.get('Class','')
        run['PPT Class'] = ppt_class
        run['Level'] = get_level(ppt_class)
        run['Class'] = get_class(ppt_class)

# Maps FeelTheRushTrials column names into the preferred names
def map_ftr_columns(runs):
    for run in runs:
        # mark the data source
        run['Source'] = 'FeelTheRush'
        # use 'Dog', not 'Dogname'
        run['Dog'] = remove_html_tags(run.get('Dogname',''))
        # Use 'Date', not 'Trial Date'
        run['Date'] = run.get('Trial Date', DEFAULT_DATE)
        # for 2 for trials on same day
        run['Trial Num'] = run.get('Trial Day','1')
        # use 'Results', not 'Qual', for Q and NQ
        run['Result'] = run.get('Qual','')
        # map the 'Points' field to 'MACH Pts', 'Score' and 'T2B Pts" based on class
        pts = run.get('Points','0')
        this_class = run.get('Class','')
        if this_class in ('JWW','Std'):
            run['MACH Pts'] = pts
        elif this_class == 'FAST':
            run['Score'] = pts
        elif this_class == 'T2B':
            run['T2B Pts'] = pts
        # Define level & classes by their common name
        ftr_level = run.get('Level','')
        run['FTR Level'] = ftr_level
        run['Level'] = get_level(ftr_level)
        ftr_class = run.get('Class','')
        run['FTR Class'] = ftr_class
        run['Class'] = get_class(ftr_class)

# Removes HTML tags from a text string
def remove_html_tags(text):
    found = True
    while (found):
        left = text.find('<')
        right = text.find('>')
        if (left > -1) and (left < right):
            text = text[:left] + text[right+1:]
        else:
            found = False
    return text

# Remove absence runs 
def remove_absences(runs):
        runs[:] = [r for r in runs if not r.get("Result") == 'A']

# For convenience, create 'Group' field = level & class
def group_level_and_class(runs):
    for run in runs:
        level = run.get('Level','')
        agility_class = run.get('Class','')
        #Special Case: T2B has no level
        if agility_class == 'T2B':
            group = agility_class
        else:
            group = level + ' ' + agility_class
        # Filter our=t unwanted groups (for now) as 'Other'
        # TODO: Remove this check when future dog class list is implemented
        if group not in groups:
            group = "Other"
        run['Group'] = group

# Creates a reverse sorted list of unique dog names
def group_dogs(runs):
    print('Grouping Dogs')
    dogs = set()
    for run in runs:
        if run.get('Dog', False):
            dogs.add(run.get('Dog'))
    dogs = list(dogs)
    dogs.sort(reverse=True)
    return dogs

# Merge fault count columns into one text column
# For example R=1, W=2, other fault=0 becomes 'R,2W'
def merge_faults(runs):
    print('Merging Faults')
    for run in runs:
        faults = []
        for f in ("R","S","W","T","F","E"):
            if run.get(f) == '1':
                faults.append(f) 
            elif run.get(f,'0') != '0':
                faults.append(run.get(f,'0') + f)
        run['Faults'] = ','.join(faults)

# Calculate the statistics (running averages) for specific columns for all runs
# The calculated stats are added as new 'columns' to the run dictionary as text strings
# NQ runs are assigned an empty string
def calc_stats(runs, dogs, groups):
    print('Calculating stats')
    stat_cols = ["Q Rate", "YPS", "Score", "MACH Pts", "T2B Pts"]
    for dog in dogs:
        print('  Dog:', dog)
        for group in groups:
            print('    Stats:', dog, group)
            table_runs = [run for run in runs if run.get('Dog')==dog and run.get('Group')==group]
            for col in stat_cols:
                # history is a running list of values for this stat column
                history = list()
                for run in table_runs:
                    # Q Rate is computed for all runs; other stats only for the Q runs
                    if col == "Q Rate" or run.get("Result") == "Q":
                        # Use 100 or 0 for Q or NQ to report average result in percent
                        if col == "Q Rate":
                            value = 100 if run.get("Result") == "Q" else 0
                            # save the Q or NQ as a value of 0 or 10 for sane plotting
                            run["Q Rate"] = value / 10 
                        else:
                            value = float(run.get(col)) if run.get(col) else 0
                        # append this value to the running list of values for this class
                        history.append(value)
                        # compute average of *all* values up to this point
                        run["Avg " + col] = str(round(statistics.mean(history),2))
                        # compute average of last 15 values
                        run["Avg15 " + col] = str(round(statistics.mean(history[-15:]),2))
                    else:
                        # No stats for NQ runs (except Q-Rate)
                        run["Avg " + col] = ''
                        run["Avg15 " + col] = ''
    return stat_cols

# Calulate the MACH Pts for National Agility Championship (NAC)
def calc_nac_points(runs, dog, year):
    nac_groups = ("Master Std", "Master JWW")
    nac_runs = [run for run in runs if run.get('Dog')==dog and run.get('Group') in nac_groups]
    # NAC year runs from Dec 1 to Nov 30
    nac_start_date = datetime.datetime(year-2, 12, 1, 0, 0).date()
    nac_end_date   = datetime.datetime(year-1, 11, 30, 0, 0).date()
    nac_points = 0
    for run in nac_runs:
        if nac_start_date <= run.get('SortDate') and  run.get('SortDate') <= nac_end_date:
            pts = int(run.get('MACH Pts',0)) if run.get('MACH Pts') else 0
            # remove negative MACH points
            if pts > 0:
                nac_points += pts
    nac_run = dict()
    nac_run["Result"] = "Q"  # Required for Table CSS and filtering
    nac_run["NAC Year"] = str(year)
    nac_run["Start Date"] = nac_start_date.strftime(FORMAT_DATE)
    nac_run["End Date"] = nac_end_date.strftime(FORMAT_DATE)
    nac_run["MACH Pts"] = str(nac_points)
    return nac_run

# Convert a column name to its clean CSS class name
def col_css_class(c):
    return 'col-' + c.lower().replace(' ','-')

# Convert a row name to its clean CSS class name
def row_css_class(r):
    return 'row-' + r.lower().replace(' ','-')
    
# Write the header (including CSS) and main body start to the HTML output file
def write_html_header(w):
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
def write_html_footer(w):
    w.write('</body>\n')
    w.write('</html>\n')

# Write a table of file meta data
def write_file_table(file_metas):
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
def write_section_header(w, dog):
    print('  Section:', dog)
    w.write('<section>')
    w.write('<h1>' + dog + '</h1>\n')

# Write a section close to the HTML output file
def write_section_footer(w):
    w.write('</section>')

# Write a new table start to the HTML output file
def write_table_header(w, dog, group, cols):
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
def write_table_row(w, dog, group, cols, run):
    # table body rows
    css_class = 'class="' + row_css_class(run.get("Result")) +'"' if run.get("Result") else ''
    w.write('  <tr ' + css_class + '>\n')
    for c in cols:
        w.write('    <td class="' + col_css_class(c) +'" >' + str(run.get(c, '')) + '</td>\n')
    w.write('  </tr>\n')

# Write an table close to the HTML output file
def write_table_footer(w):
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
def create_plot_as_svg(table_runs, base_col):
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
        for run in table_runs:
            if base_col == "Q Rate" or run.get("Result") == "Q":
                x = datetime.datetime.strptime(run["Date"], FORMAT_DATE)
                y  = float(run.get(col,0)) if run.get(col) else 0
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
(runs, meta) = read_csv(ppt_csv_file, ppt_csv_cols, "PawPrintTrials")
map_ppt_columns(runs)
file_metas.append(meta)

# Read the FeelTheRuch CSV file into memory
(ftr_runs, meta) = read_csv(ftr_csv_file, ftr_csv_cols, "FeelTheRush")
file_metas.append(meta)
map_ftr_columns(ftr_runs)

# Merge FTR runs into the PPT runs
runs.extend(ftr_runs)
runs.sort(key=lambda r: r['SortDate'])

# clean up data
remove_absences(runs)
group_level_and_class(runs)
merge_faults(runs)


# Get lists of unique dogs and catlog classes into groups
dogs = group_dogs(runs)

# Calculate and add statistics columns to the data 
stat_cols = calc_stats(runs, dogs, groups)

# Create the HTML output file
print('Writing', report_file)
with open(report_file, 'w') as w:
    write_html_header(w)
    write_file_table(file_metas)
    # each dog gets its own section
    for dog in dogs:
        write_section_header(w, dog)
        # create a table for each group (aka agility class)
        for group in groups:
            table_runs = [run for run in runs if run.get('Dog')==dog and run.get('Group')==group]
            # skip empty tables and odd-ball classes
            if table_runs and (not group == "Other"):
                # Create the table
                write_table_header(w, dog, group, table_cols[group])
                for run in table_runs:
                    write_table_row(w, dog, group, table_cols[group], run)
                write_table_footer(w)
                # Create a plot for each stat_col in this table
                for col in stat_cols:
                    # only show plot if applicable to this group/table
                    if (col in table_cols[group]) or (col == "Q Rate"):
                        print('     Plot:', dog, group, col)
                        svg = create_plot_as_svg(table_runs, col)
                        write_svg_plot(w, svg, col)
                        svg = None # help garbage collect
        # Table of MACH pts for NAC by year
        # TODO: Fixed hard-coded years
        nac_cols = ("NAC Year", "Start Date", "End Date", "MACH Pts")
        write_table_header(w, dog, "NAC Points", nac_cols)
        for year in (2022, 2023, 2024, 2025):
            run = calc_nac_points(runs, dog, year)
            write_table_row(w, dog, "NAC Points", nac_cols, run)
        write_table_footer(w)
        write_section_footer(w)
    write_html_footer(w)

# optionally create the debug file with all data in one giant table
if True:
    print('DEBUG: Creating list of columns')

    cols = []
    for run in runs:
        for col in run.keys():
            if col not in cols:
                cols.append(col)
    
    print('DEBUG: Writing', debug_file)
    with open(debug_file, 'w') as w:
        write_html_header(w)
        write_section_header(w, "Debug")
        write_table_header(w, "Debug", "dump", cols)
        for run in runs:
            write_table_row(w, dog, group, cols, run)
        write_table_footer(w)
        write_section_footer(w)
        write_html_footer(w)

# Let the user know this script came to completion
print('Done.')
