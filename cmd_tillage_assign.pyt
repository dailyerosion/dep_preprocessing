# -*- coding: utf-8 -*-
'''A Python program to get feature classes describing lidar datasets available
via the Entwine Point cloud format. This intersects the USGS WESM data on exact project
boundaries with the EPT JSON that shows generalized boundaries and has web addresses
for the data. This dataset is then used in later programs to figure out which EPT
datasets to request.'''
import arcpy
# coding: utf-8

import sys
import os
import platform
import pathlib
import datetime
import time
import math
from os.path import join as opj
import numpy as np

login = os.getlogin()
    
# if login == 'bkgelder':
#     boxes = ['C:\\Users\\bkgelder\\Box\\Data_Sharing\\Scripts\\basics', 'M:\\DEP\\Scripts\\basics']
# else:
#     boxes = ['C:\\Users\\idep2\\Box\\Scripts\\basics', 'M:\\DEP\\Scripts\\basics']

# for box in boxes:
#     if os.path.isdir(box):
#         sys.path.append(box)

import dem_functions as df


class msgStub:
    def addMessage(self,text):
        arcpy.AddMessage(text)
    def addErrorMessage(self,text):
        arcpy.AddErrorMessage(text)
    def addWarningMessage(self,text):
        arcpy.AddWarningMessage(text)

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Tool]


class Tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "EPT_WESM_download"
        self.description = "Creates a feature class to enable EPT downloads"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            name="ACPF_field_boundaries",
            displayName="ACPF Field Boundaries Polygons",
            datatype="DEFeatureClass",
            parameterType='Required',
            direction="Input")
        
        param1 = arcpy.Parameter(
            name="lu6_table",
            displayName="ACPF Land Use Table",
            datatype="DEFeatureClass",
            parameterType='Required',
            direction="Input")
        
        param2 = arcpy.Parameter(
            name="management_field",
            displayName="Multi-year Management Field",
            datatype="GPString",
            parameterType='Required',
            direction="Input")
        
        param3 = arcpy.Parameter(
            name="tillage_field",
            displayName="Yearly Tillage Field",
            datatype="GPString",
            parameterType='Required',
            direction="Input")
        
        param4 = arcpy.Parameter(
            name="residue_field",
            displayName="Yearly Residue Field",
            datatype="GPString",
            parameterType='Required',
            direction="Input")
        
        param5 = arcpy.Parameter(
            displayName="Local Processing Directory",
            datatype="DEFolder",
            parameterType='Optional',
            direction="Input")
                
        param6 = arcpy.Parameter(
            name="tillage_table",
            displayName="Tillage Table",
            datatype="DETable",
            parameterType='Required',
            direction="Output")
               
        params = [param0, param1, param2, param3,
                  param4, param5, param6]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        cleanup = False
        doTillageSummary(parameters[0].valueAsText, cleanup, messages)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
    
def getManagement(rescover, crop, coverlist):
    '''This function takes a residue cover value and crop type and determines the tillage code'''
    ## assign tillage codes by average crop residue cover/crop type
    ## 1- no-till planter tillage
    ## 2- very high mulch tillage
    ## 3- high mulch tillage
    ## 4- medium mulch tillage
    ## 5- low mulch tillage
    ## 6- fall moldboard plow (plow

    if rescover < 0:
        rescover = 0

    if coverlist is not None:
        if rescover > coverlist[0]:
            management = '1'
        elif rescover > coverlist[1]:
            management = '2'
        elif rescover > coverlist[2]:
            management = '3'
        elif rescover > coverlist[3]:
            management = '4'
        elif rescover > coverlist[4]:
            management = '5'
        else:
            management = '6'
    else:
        management = '0'

    return management

def calc_rescover(urow, option = 'straight'):
    """determine the DEP residue cover given the median residue cover. 
    Minnesota residue cover doubling should already be removed so it 
    equals GEE residue cover"""

    if urow[3] >= 0:#-100 indicates no data
        res_fraction = urow[3]/100.0                    #0.20
        if option == 'uniform':
            # adjust residue cover from GEE down 10% due to anchored r2 still having a high intercept
            # needs to be removed after improved GEE regressions
            adj_rescover = res_fraction - 0.1               #0.10

        elif option == 'linear':
            # adjustment altered to linearly ramp correction from 10% at 0% RC to 0% at 100% RC - 2023.07.26, bkgelder
            soil_fraction = 1.0 - res_fraction              #0.80
            adjustment = 0.1 * soil_fraction                #0.08
            adj_rescover = res_fraction - adjustment        #0.12

        elif option == 'none':
             adj_rescover = res_fraction                    #0.20

        rescover = max(0.0, adj_rescover)
##        print(f"initial residue {res_fraction}, soil {soil_fraction}, adjustment {adjustment}, adj_res {adj_rescover}, final_res {rescover}")

    else:
        rescover = None

    return rescover

def getCropDict(bcover, ccover, gcover, wcover):
    """Create the crop dictionary, add new residue cover levels as needed"""
    cropDict = {'B': bcover}
    cropDict.update({'C': ccover})
    cropDict.update({'G': gcover})
    cropDict.update({'W': wcover})
    #sugarbeets, all following, assume wheat for now
    cropDict.update({'E': wcover})
    #rice
    cropDict.update({'J': wcover})
    #oilseeds (canola, safflower, flax, rape
    cropDict.update({'O': wcover})
    #double crops, assume residue cover calced for winter wheat
    cropDict.update({'L': wcover})

    return cropDict

def flip_flop():
    str_time = str(time.perf_counter())
    last_digit = int(str_time[-1])
    if last_digit % 2 == 0:
        ff = True
    else:
        ff = False
    return ff
        
def doTillageSummary(fb, lu6_table, rc_table, man_field, till_field, rc_field, bulkDir, option, tillage_table, cleanup, messages, log):
    pass

def tillageAssign(fb, lu6_table, rc_table, man_field, till_field, rc_field, bulkDir, option, tillage_table, cleanup, messages, log, ref_year):
    ## man_data_processor
    ## takes residue cover or management data and spicifies crop management files for Daily Erosion Project
    ## 2020/02/11 v2 - added ability to fill in missing managements if not in Minnesota or Iowa BKG
    ## 2020.07.01 v3 - converted to load paths to data from arguments
    ##                      also want to add ability to use CTIC OpTIS data by HUC8 to assign management classes
    ##                    by HUC8 outside of field level data, use slope to rank the fields and
    ##                    assign those with values greater than T to conservation tillage. Those fields
    ##                    with erosion rates less than T are randomly assigned to the remaining tillage class acreages
    ## 2022.03 v3a - updated to new GEE tillage maps, added logging of tillage table used
    ## 2022.04.26 v3b - default is now calculated per HUC12 based on median of fields with valid values
    ## 2022.07.01 v3c - fixed big divergence in how residue was being calculated in Minnesota and elsewhere
    ##                  also moved code to Python 3.X and changed argument structure to make Tim happy (and me too).
    ## 2023.06.15 v3d - added output of median residue cover for ACPF OFE tool
    ## 2023.06.15 v3e - reverted to re-include reduction of residue cover when calculating management code
    ##                  re-named tillage and residue tables due to confusion on what was stored where
    #
    # INPUTS
    # fb - ACPF field boundaries
    # lu6 - ACPF land use table
    # rc_table - median residue cover of field from RS (GEE or Minnesota)
    #
    # OUTPUTS
    # tillage_table - output of tillage code

    # OTHER NECESSARY
    # man_field - name of management field
    # bulkDir - bulk processing directory
    # till_field - name of tillage code field
    # rc_field - name of residue cover
    # cleanup - T or F, whether to log data

    #management calculator

    # adj_rc_field = 'Adj_' + rc_field
    # adj_rc_field = rc_field
    # rc_field = adj_rc_field.replace('Adj_', 'Pct_')

    ## fill all crop management fields by setting breaks between tillage classes)
    # bcover = [0.25, 0.15, 0.10, 0.05, 0.02]#soybeans, ## these values from David Mulla's calculations
    bcover = [0.54, 0.18, 0.06, 0.03, 0.02]# from Eduardo Luquin re-analysis of Bean/Corn rotation in WEPP 2022
    # ccover = [0.70, 0.45, 0.30, 0.15, 0.05]#corn, ## these values from David Mulla's calculations
    ccover = [0.82, 0.57, 0.33, 0.17, 0.08]# from Eduardo Luquin re-analysis of Bean/Corn rotation in WEPP 2022
    cccover = [0.73, 0.27, 0.19, 0.11, 0.07]
    ## these values from DEP 2018 paper
    gcover = [0.65, 0.40, 0.12, 0.06, 0.03]#sorghum
    wcover = [0.50, 0.40, 0.20, 0.15, 0.06]#wheat

    cropDict = getCropDict(bcover, ccover, gcover, wcover)

    keys = cropDict.keys()

    arcpy.env.scratchWorkspace = bulkDir
    sgdb = arcpy.env.scratchGDB
    arcpy.env.scratchWorkspace = sgdb
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = os.path.dirname(fb)#fileGDB

    # repro = arcpy.CopyRows_management(fb, os.path.join(sgdb, 'fbnds_tbl'))

    # fbndsTable = arcpy.TableSelect_analysis(repro, os.path.join('in_memory', 'fb_' + huc12))#, 'isAG >= 1')
    fbndsTable = arcpy.TableSelect_analysis(fb, os.path.join('in_memory', 'fb_' + huc12))#, 'isAG >= 1')
    df.joinDict(fbndsTable, 'FBndID', lu6_table, 'FBndID', ['CropRotatn', 'GenLU'])

    ##zstResCover = tillage_table#paths['mnTillageTable']
    log.debug('determining default management using: ' + tillage_table)

    df.joinDict(fbndsTable, 'FBndID', rc_table, 'FBndID', ['MEDIAN'], [rc_field])

    rc_year = int(tillage_table[-4:])#2023
    lu6_table_path = pathlib.Path(lu6_table)
    acpf_year = lu6_table_path.parent.parent.parent.name[-4:]
    field_len = rc_year - ref_year# + 1
    log.debug(f'field_len is {field_len}')

    arcpy.AddField_management(fbndsTable, man_field, 'TEXT', field_length = field_len)
    arcpy.AddField_management(fbndsTable, till_field, 'TEXT', field_length = field_len)
##    arcpy.AddField_management(fbndsTable, rc_field, 'FLOAT')
    # arcpy.AddField_management(fbndsTable, adj_rc_field, 'FLOAT')

    rc_fields = ['GenLU', man_field, 'CropRotatn', rc_field, 'FBndID', till_field]#, adj_rc_field]

        ## Values are 0-100 (1% increments)

    # First calculate default management using larger fields with valid residue cover
    man_array = np.array([])    

    # create a numpy array to store data for default calcuations, then do actual assignments later
    # identify default management by assigning all managements possible then use most common as default
    ##with arcpy.da.UpdateCursor(fbndsTable, rc_fields, where_clause = 'FBndID = \'F071000081505_497\'') as ucur:
    where = ''
    ##where = 'FBndID = \'F071000081505_497\' OR FBndID = \'F071000081505_499\''
    ##with arcpy.da.SearchCursor(fbndsTable, rc_fields, where_clause = where) as scur:
    with arcpy.da.SearchCursor(fbndsTable, rc_fields, where_clause = 'GenLU <> \'LT 10 ac\' AND GenLU <> \'Forest\' AND GenLU <> \'Pasture|Grass|Hay\' AND GenLU <> \'Water/wetland\'') as scur:
        for srow in scur:
            if srow[2] is not None:
                croprotate = srow[2][:field_len]
            # if croprotate is not None:
                # go two years back in crop rotation to align with spring residue cover type (e.g. 2021 res cover is from 2020 crop)
                mancrop = croprotate[-2]
    ##            field_rotate_length = len(croprotate)
                if srow[3] is not None:
                    adj_rescover = calc_rescover(srow, option)
                else:
                    adj_rescover = None
                    
                if mancrop in keys:
                    if adj_rescover is not None:
                        coverlist = cropDict[mancrop]
                        calculated_management = getManagement(adj_rescover, mancrop, coverlist)
                        man_array = np.append(man_array, [int(calculated_management)])

                # log.debug(f'srow is {srow}')

    ##            prev_rotate_length = field_rotate_length
                # print(srow)

    ##rotate_length = max(field_rotate_length, prev_rotate_length)

    try:
        defaultManagement = str(int(np.median(man_array)))
    except:
        log.info('default management from default')
        defaultManagement = '3'
    log.info('default management is: ' + defaultManagement)
    log.info(f'rc_fields is: {rc_fields}')


    # Now calculate management for all fields using defaults if no res cover (or out of bound crop)

    with arcpy.da.UpdateCursor(fbndsTable, rc_fields, where_clause = where) as ucur:
    ##with arcpy.da.UpdateCursor(fbndsTable, rc_fields) as ucur:#, where_clause = 'FBndID = \'F070801050101_595\'') as ucur:
        for urow in ucur:
    ##        if urow[-1] == 'F090201081102_58':
    ##            print(urow)
            managements = ''
            got_man = False
            # croprotate = urow[2]
            if urow[2] is None:
            # no data on crop rotation, managements = 0
            # if croprotate is None:
                # use rotate_length to determine?
                managements = '0' * field_len

            # else try and determine tillage practice by last crop residue cover
            else:
                croprotate = urow[2][:field_len]
                # go two years back in crop rotation to align with spring residue cover type (e.g. 2021 res cover is from 2020 crop)
                mancrop = croprotate[-2]

                if urow[3] is not None and urow[0] not in ['Forest', 'Pasture|Grass|Hay', "Water/wetland"]:
                    adj_rescover = calc_rescover(urow, option)
                else:
                    adj_rescover = None

##                urow[6] = adj_rescover#srow[3]

                if mancrop in keys:
                    if adj_rescover is not None:
                        coverlist = cropDict[mancrop]
                        got_man = getManagement(adj_rescover, mancrop, coverlist)
                        # identify non-default, looked up residue cover for use in building total management string

                # in future - run pandas on the table at this point.
                # Then get default management from most common management for that crop

                # now calculate managements for the whole time period
                for step, crop in enumerate(croprotate):
                    if crop in keys:
                        if got_man is not False:
                            management = got_man
                        else:
                            management = defaultManagement
                    else:
                        management = '0'
                    managements += management
                
            urow[1] = managements
            till_code_long = managements.replace('0', '')
            if len(till_code_long) == 0:
                till_code = '0'
            else:
                till_code = till_code_long[0]
            urow[5] = till_code
    ##        if urow[-1] == 'F090201081102_58':
            # print(urow)
            ucur.updateRow(urow)

            # log.debug(f'urow is {urow}')

    till_temp_desc = arcpy.da.Describe(fbndsTable)
    for c in df.getfields(fbndsTable):
        if c not in ['OBJECTID', 'FBndID', man_field, till_field, rc_field]:#, adj_rc_field]:
            arcpy.DeleteField_management(fbndsTable, c)

    till_table_result = arcpy.CopyRows_management(fbndsTable, tillage_table)

    log.debug(f'wrapping up at: {datetime.datetime.now()}')

    return till_table_result, field_len



if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        arcpy.AddMessage("Whoo, hoo! Running from Python Window!")
        cleanup = False

        parameters = ["C:/Program Files/ArcGIS/Pro/bin/Python/envs/arcgispro-py3/pythonw.exe",
	"C:/DEP/Scripts/basics/cmd_tillage_assign - Copy.pyt",
	"D:/DEP/Man_Data_ACPF/dep_ACPF2022/07080105/idepACPF070801050903.gdb/FB070801050903",
	"D:/DEP/Man_Data_ACPF/dep_ACPF2022/07080105/idepACPF070801050903.gdb/LU6_070801050903",
	"D:/DEP/Man_Data_ACPF/dep_ACPF2022/07080105/idepACPF070801050903.gdb/huc070801050903_gee_rc2022",
	"E:/DEP_Proc/DEMProc/Manage_dem2013_3m_070801050903",
	"D:/DEP/Man_Data_ACPF/dep_ACPF2022/07080105/idepACPF070801050903.gdb/huc070801050903_till_NewThresholds2022",
	"2017",
	"2022"]
##        ["C:/Program Files/ArcGIS/Pro/bin/Python/envs/arcgispro-py3/pythonw.exe",
##	"C:/DEP/Scripts/basics/cmd_tillage_assign.pyt",
##	"D:/DEP/Man_Data_ACPF/dep_ACPF2022/09030009/idepACPF090300090306.gdb/FB090300090306",
##	"D:/DEP/Man_Data_ACPF/dep_ACPF2022/09030009/idepACPF090300090306.gdb/LU6_090300090306",
##	"D:/DEP/Man_Data_ACPF/dep_ACPF2022/09030009/idepACPF090300090306.gdb/huc090300090306_mn_rc2022",
##	# "Management_CY_2022",
##	# "Till_code_CY_2022",
##	# "Adj_RC_CY_2022",
##	"D:/DEP_Proc/DEMProc/Manage_dem2013_3m_090300090306",
##	"D:/DEP/Man_Data_ACPF/dep_ACPF2022/09030009/idepACPF090300090306.gdb/huc090300090306_till2022",
##	"2017",
##	"2022"]

        for i in parameters[2:]:
            sys.argv.append(i)
    else:
        arcpy.AddMessage("Whoo, hoo! Command-line enabled!")
        # clean up the folder after done processing
        cleanup = True

    fb, lu6_table, rc_table_base, bulkDir, base_tillage_table, start, end = [i for i in sys.argv[1:]]
    messages = msgStub()
    # set log as None for first run
##    log = None

# old code - options were for different ways of apportioning tillage codes based on residue cover - adding 10% everywhere, linear adjustment (0-10% based on initial, or none)
#    doTillageSummary(fb, lu6_table, rc_table_base, bulkDir, option, base_tillage_table, cleanup, messages, log)
##    doTillageSummary(fb, lu6_table, rc_table_base, bulkDir, base_tillage_table, cleanup, messages, log)
    arcpy.AddMessage("Back from doTillageSummary!")


    huc12 = fb[-12:]

    if cleanup:
        # log to file only
        log, nowYmd, logName, startTime = df.setupLoggingNoCh(platform.node(), sys.argv[0], huc12)
    else:
        # log to file and console
        log, nowYmd, logName, startTime = df.setupLoggingNew(platform.node(), sys.argv[0], huc12)

    # ACPF directory where channel and catchment features reside
    log.debug(f'starting up at: {datetime.datetime.now()}')
    messages.addMessage("Tool: Executing with parameters '")

    ## bulk processing (Scratch) directory
    # if arcpy.Exists(bulkDir):
    #     arcpy.Delete_management(bulkDir)
    if not os.path.isdir(bulkDir):
        os.makedirs(bulkDir)

################################################################################
    # run through all the years to create annual tillage table, calculate the tillage codes for each field for that year
    acpf_ref_year = 2010 #date DEP CDL land cover stuff starts
    ACPFyears = [str(a) for a in range(int(start), int(end) + 1)]
    for ACPFyear in ACPFyears:
        log.info(f"Creating tillage data by field for ACPFyear: {ACPFyear}")
        field_dict = df.loadFieldNames(ACPFyear)
        man_field = field_dict['manField']
        till_field = field_dict['tillField']
        rc_field = field_dict['resCoverField']
        # man_field = man_field_base[:-4] + ACPFyear
        # till_field = till_field_base[:-4] + ACPFyear
        rc_table = rc_table_base[:-4] + ACPFyear
        if 'mn_rc' in rc_table:
            if not arcpy.Exists(rc_table):
                rc_table = rc_table.replace('mn_rc', 'gee_rc')
        elif 'rc_mn' in rc_table:
            if not arcpy.Exists(rc_table):
                rc_table = rc_table.replace('rc_mn', 'rc_gee')
        year_tillage_table = base_tillage_table[:-4] + ACPFyear#.replace('_till', '_till' + option.capitalize())
        options = ['uniform', 'linear', 'none']
        # for option in options:
        #     rc_field = rc_field_base[:7] + option.capitalize() + rc_field_base[6:-4] + ACPFyear
        #     tillage_table = year_tillage_table.replace('_till', '_till' + option.capitalize())
        #     doTillageAssign(fb, lu6_table, rc_table, man_field, till_field, rc_field, bulkDir, option, tillage_table, cleanup, messages)
        option = options[2]
        # rc_field = rc_field_base + option.capitalize() + rc_field_base[6:-4] + ACPFyear
        # rc_field = rc_field_base[6:-4] + ACPFyear
##        if ACPFyear == ACPFyears[0]:
##            log = None
        tillage_table_return, field_len = tillageAssign(fb, lu6_table, rc_table, man_field, till_field, rc_field, bulkDir, option, year_tillage_table, cleanup, messages, log, acpf_ref_year)
        if ACPFyear == ACPFyears[0]:
            first_tillage_table = tillage_table_return
##            log = log_return
    arcpy.AddMessage("Back from doTillageAssign!")

################################################################################
    # Create a six year tillage summary table - using median and dynamic values
    # Do this by running through the tillage years again to calculate the dynamic tillage year by year
    # The six year table uses the starting and end dates in the name
    ACPFyear = str(int(start))
##    ACPFyears = [str(a) for a in range(int(start), int(end) + 1)]
    # options = [""]#['uniform']#, 'linear', 'none']
    # for option in options:
    fields_list = ['FBndID']
    for till_year in ACPFyears:
        log.info(f"Creating six year summary of tillage data for: {till_year}")
        field_dict = df.loadFieldNames(till_year)
        till_field = field_dict['tillField']
        man_field = field_dict['manField']
        # year_tillage_table1 = base_tillage_table.replace(ACPFyear, till_year)
        # year_tillage_table2 = year_tillage_table1.replace('_till', '_till' + option.capitalize())
#new
        year_tillage_table2 = base_tillage_table.replace('Thresholds' + ACPFyears[-1], 'Thresholds' + till_year)
        # update till field to the year
        # till_field = till_field_base[:-4] + till_year
        if till_year == ACPFyears[0]:
            # copy the starting tillage table and add last year to name                
            first_year = arcpy.CopyRows_management(first_tillage_table, str(first_tillage_table) + '_' + ACPFyears[-1])
            # first_year = arcpy.CopyRows_management(year_tillage_table2, year_tillage_table2 + '_' + ACPFyears[-1])
            first_man_field = man_field#man_field_base[:-4] + till_year
            fields_list.append(first_man_field)
            first_till_field = till_field

        else:
            # join the tillage table to the starting tillage table
            df.joinDict(first_year, 'FBndID', year_tillage_table2, 'FBndID', [till_field])

        fields_list.append(till_field)


################################################################################
    # Add fields to store the dynamic tillage codes for each year as well as the overall mean tillage code
    
    # field_len = int(till_year) - acpf_ref_year#2008
    log.info(f'field_len for summary is {field_len}')

    field_dict = df.loadFieldNames(ACPFyears[-1])
    curr_man_field = field_dict['manField']
    fields_list.append(curr_man_field)
#new
    if curr_man_field not in df.getfields(first_year):
        arcpy.AddField_management(first_year, curr_man_field, 'TEXT', field_length = field_len)

    dynam_man_field = 'Dynamic_Management' + curr_man_field[-8:]
    fields_list.append(dynam_man_field)
    arcpy.AddField_management(first_year, dynam_man_field, 'TEXT', field_length = field_len)

    # create till code name from string, 'CY' extract from above, and start and end year, e.g. Till_Code_Mean_CY_2017_2022 for the 2017-2022 tillage code
    till_code_mean_field = "_".join(['Till_Code_Mean', curr_man_field[-7:-5], start, end])
    fields_list.append(till_code_mean_field)
    arcpy.AddField_management(first_year, till_code_mean_field, 'TEXT', field_length = 1)#field_len)

    curr_till_field = till_field

################################################################################
    # determine what position field is in list
    # then create a dynamic tillage string and overwrite the current year management string
    curr_man_index = fields_list.index(curr_man_field)
    dynam_man_index = fields_list.index(dynam_man_field)
    first_man_index = fields_list.index(first_man_field)

    curr_till_index = fields_list.index(till_field)
    first_till_index = fields_list.index(first_till_field)

    with arcpy.da.UpdateCursor(first_year, fields_list) as ucur:
##    fbnd = "F070801050902_1"
##    where = f"FBndID = '{fbnd}'"
##    with arcpy.da.UpdateCursor(first_year, fields_list, where_clause = where) as ucur:
        for urow in ucur:
            # create a list of all the tillage code field values
            till_codes = [urow[i] for i in range(first_till_index, curr_till_index+1)]
            dynam_codes = "".join(till_codes)

            # seed with the mean for non-observed years
            all_codes = urow[first_man_index] + dynam_codes#"".join(till_codes)
            urow[dynam_man_index] = all_codes#dynam_codes

            # try to figure out the mean value for all the tillage codes in the timeframe
            try:
                str_arr = np.array(till_codes)
                int_arr = np.asarray(str_arr, dtype = int)
                int_arr_nz = int_arr[int_arr > 0]
                if len(int_arr_nz) > 0:
                    float_mean_management = np.mean(int_arr_nz)
                else:
                    # log.info('default management from default for all zeros')
                    float_mean_management = 0
            except:
                # log.info('default management from default')
                float_mean_management = -1

            # try to randomize the ties, if it's a half, go up half time and down the other
            try:
                ir = float_mean_management.as_integer_ratio()
                if ir[1] == 2:
                    ff = flip_flop()
                    if ff:
                        int_mean_management = math.floor(float_mean_management)
                    else:
                        int_mean_management = math.ceil(float_mean_management)
                else:
                    int_mean_management = round(float_mean_management)
            except:
                int_mean_management = -1

            urow[-1] = str(int_mean_management)
    
##https://stackoverflow.com/questions/4260280/if-else-in-a-list-comprehension
##                                mean_codes = [c for c in dynam_codes if c != '0']
            mean_codes = ""
            for c in all_codes:
                if c != '0':
                    c = str(int_mean_management)
                mean_codes += c
            urow[curr_man_index] = mean_codes

            ucur.updateRow(urow)
