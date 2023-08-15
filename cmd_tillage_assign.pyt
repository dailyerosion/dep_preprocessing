# -*- coding: utf-8 -*-
'''A Python program to get feature classes describing lidar datasets available
via the Entwine Point cloud format. This intersects the USGS WESM data on exact project
boundaries with the EPT JSON that shows generalized boundaries and has web addresses
for the data. This dataset is then used in later programs to figure out which EPT
datasets to request.'''
import arcpy
# coding: utf-8

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

        output_ept_wesm_file = arcpy.Parameter(
            name="ept_wesm_features",
            displayName="Output EPT WESM Feature",
            datatype="DEFeatureClass",
            parameterType='Required',
            direction="Output")
        params = [output_ept_wesm_file]#None
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
        doTillageAssign(parameters[0].valueAsText, cleanup, messages)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
    

def doTillageAssign(fb, lu6, tillage_table, rc_table, manfield, tillfield, adj_rc_field_name, bulkDir, cleanup):
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
    # manfield - name of management field
    # bulkDir - bulk processing directory
    # tillfield - name of tillage code field
    # adj_rc_field_name - name of residue cover
    # cleanup - T or F, whether to log data

    import sys
    import os
    import arcpy
    import dem_functions2 as df
    import platform
    from os.path import join as opj
    import numpy as np

    #management calculator

    if cleanup:
        # log to file only
        log, nowYmd, logName, startTime = df.setupLoggingNoCh(platform.node(), sys.argv[0], huc12)
    else:
        # log to file and console
        log, nowYmd, logName, startTime = df.setupLoggingNew(platform.node(), sys.argv[0], huc12)

    # ACPF directory where channel and catchment features reside

    adj_rc_field_name = paths['resCoverField']
    rc_field_name = adj_rc_field_name.replace('Adj_', '')

    ## bulk processing (Scratch) directory
    if arcpy.Exists(bulkDir):
        arcpy.Delete_management(bulkDir)
    os.makedirs(bulkDir)


    ## assign tillage codes by average crop residue cover/crop type
    ## 1- no-till planter tillage
    ## 2- very high mulch tillage
    ## 3- high mulch tillage
    ## 4- medium mulch tillage
    ## 5- low mulch tillage
    ## 6- fall moldboard plow (plow

    def getManagement(rescover, crop, coverlist):

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

    def calc_rescover(urow):
        """determine the DEP residue cover given the median residue cover. 
        Minnesota residue cover doubling should already be removed so it 
        equals GEE residue cover"""

        if urow[3] >= 0:#-100 indicates no data
            # adjust residue cover from GEE down 10% due to anchored r2 still having a high intercept
            # needs to be removed after improved GEE regressions
            # adjustment altered to linearly ramp correction from 10% at 0% RC to 0% at 100% RC - 2023.07.26, bkgelder
            res_fraction = urow[3]/100.0                    #0.20
    #         soil_fraction = 1.0 - res_fraction              #0.80
    #         adjustment = 0.1 * soil_fraction                #0.08
    # ##        adjusted_soil_fraction = 0.9 * soil_fraction    
    #         adj_rescover = res_fraction - adjustment        #0.12
            adj_rescover = res_fraction - 0.1

            rescover = max(0.0, adj_rescover)
    ##        print(f"initial residue {res_fraction}, soil {soil_fraction}, adjustment {adjustment}, adj_res {adj_rescover}, final_res {rescover}")

        else:
            rescover = None

        return rescover


    ## fill all crop management fields that are not populated with 3 (error occurs on fields that are in two or more HUC12 databases)
    ##        print('join management data')
    ## these values from David Mulla's calculations
    bcover = [0.25, 0.15, 0.10, 0.05, 0.02]#soybeans
    ccover = [0.70, 0.45, 0.30, 0.15, 0.05]#corn
    ## these values from DEP 2018 paper
    gcover = [0.65, 0.40, 0.12, 0.06, 0.03]#sorghum
    wcover = [0.50, 0.40, 0.20, 0.15, 0.06]#wheat
    ##ecover = wcover#sugarbeets
    ##jcover = wcover#rice

    ##cropList = ['B', bcover
    cropDict = {'B': bcover}
    cropDict.update({'C': ccover})
    cropDict.update({'G': gcover})
    cropDict.update({'W': wcover})
    #sugarbeets
    cropDict.update({'E': wcover})
    #rice
    cropDict.update({'J': wcover})
    #oilseeds (canola, safflower, flax, rape
    cropDict.update({'O': wcover})
    #double crops, assume residue cover calced for winter wheat
    cropDict.update({'L': wcover})

    keys = cropDict.keys()

    arcpy.env.scratchWorkspace = bulkDir
    sgdb = arcpy.env.scratchGDB
    arcpy.env.scratchWorkspace = sgdb
    arcpy.env.overwriteOutput = True

    ## use ACPF directory as workspace since 2 of the 5 rasters or feature classes we need are here already
    arcpy.env.workspace = os.path.dirname(fb)#fileGDB

    repro = arcpy.CopyRows_management(fb, os.path.join(sgdb, 'fbnds_tbl'))

    fbndsTable = arcpy.TableSelect_analysis(repro, os.path.join('in_memory', 'fb_' + huc12))#, 'isAG >= 1')
    ##fbndsTable = arcpy.TableSelect_analysis(fb, os.path.join('in_memory', 'fb_' + huc12))#, 'isAG >= 1')
    df.joinDict(fbndsTable, 'FBndID', lu6, 'FBndID', ['CropRotatn', 'GenLU'])

    arcpy.AddField_management(fbndsTable, manfield, 'TEXT', field_length = 12)
    arcpy.AddField_management(fbndsTable, tillfield, 'TEXT', field_length = 12)
    arcpy.AddField_management(fbndsTable, adj_rc_field_name, 'FLOAT')

    # First calculate default management using larger fields with valid residue cover
    man_array = np.array([])    

    ##zstResCover = tillage_table#paths['mnTillageTable']
    log.debug('determining default management using: ' + tillage_table)

    df.joinDict(fbndsTable, 'FBndID', rc_table, 'FBndID', ['MEDIAN'], [rc_field_name])

    rc_fields = ['GenLU', manfield, 'CropRotatn', rc_field_name, 'FBndID', tillfield, adj_rc_field_name]

        ## Values are 0-100 (1% increments)


    # create a numpy array to store data for default calcuations, then do actual assignments later
    # identify default management by assigning all managements possible then use most common as default
    ##with arcpy.da.UpdateCursor(fbndsTable, rc_fields, where_clause = 'FBndID = \'F071000081505_497\'') as ucur:
    where = ''
    ##where = 'FBndID = \'F071000081505_497\' OR FBndID = \'F071000081505_499\''
    ##with arcpy.da.SearchCursor(fbndsTable, rc_fields, where_clause = where) as scur:
    with arcpy.da.SearchCursor(fbndsTable, rc_fields, where_clause = 'GenLU <> \'LT 10 ac\' AND GenLU <> \'Forest\' AND GenLU <> \'Pasture|Grass|Hay\' AND GenLU <> \'Water/wetland\'') as scur:
        for srow in scur:
            croprotate = srow[2]
            if croprotate is not None:
                mancrop = croprotate[-2]
    ##            field_rotate_length = len(croprotate)
                if srow[3] is not None:
                    adj_rescover = calc_rescover(srow)
                else:
                    adj_rescover = None
                    
                if mancrop in keys:
                    if adj_rescover is not None:
                        coverlist = cropDict[mancrop]
                        calculated_management = getManagement(adj_rescover, mancrop, coverlist)
                        man_array = np.append(man_array, [int(calculated_management)])

    ##            prev_rotate_length = field_rotate_length
                # print(srow)

    ##rotate_length = max(field_rotate_length, prev_rotate_length)

    try:
        defaultManagement = str(int(np.median(man_array)))
    except:
        log.info('default management from default')
        defaultManagement = '3'
    log.info('default management is: ' + defaultManagement)


    # Now calculate management for all fields using defaults if no res cover (or out of bound crop)

    with arcpy.da.UpdateCursor(fbndsTable, rc_fields, where_clause = where) as ucur:
    ##with arcpy.da.UpdateCursor(fbndsTable, rc_fields) as ucur:#, where_clause = 'FBndID = \'F070801050101_595\'') as ucur:
        for urow in ucur:
    ##        if urow[-1] == 'F090201081102_58':
    ##            print(urow)
            managements = ''
            got_man = False
            croprotate = urow[2]
            # no data on crop rotation, managements = 0
            if croprotate is None:
                # use rotate_length to determine?
                managements = '0' * 11

            # else try and determine tillage practice by last crop residue cover
            else:
                mancrop = croprotate[-2]

                if urow[3] is not None and urow[0] not in ['Forest', 'Pasture|Grass|Hay', "Water/wetland"]:
                    adj_rescover = calc_rescover(urow)
                else:
                    adj_rescover = None

                urow[6] = adj_rescover#srow[3]

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

    ######### create a copy for conversion to JSON for HUC12 tillage statistics
    ########copyFbnds = arcpy.CopyRows_management(fbndsTable, paths['tillages'])#os.path.join(fileGDB, os.path.basename(tillages)))
    ####
    df.joinDict(repro, 'FBndID', fbndsTable, 'FBndID', [manfield, tillfield, adj_rc_field_name, rc_field_name])


    till_temp = arcpy.CopyRows_management(repro, opj(sgdb, os.path.basename(tillage_table)))
    ####till_temp = arcpy.CopyRows_management(fbndsTable, opj(sgdb, os.path.basename(tillage_table)))
    ####till_temp2 = arcpy.TableSelect_analysis(fbndsTable, opj(sgdb, os.path.basename(tillage_table) + '_2'))

    till_temp_desc = arcpy.da.Describe(till_temp)
    for c in df.getfields(till_temp):
        if c not in ['OBJECTID', 'FBndID', manfield, tillfield, rc_field_name, adj_rc_field_name]:
            arcpy.DeleteField_management(till_temp, c)

    till_table_result = arcpy.CopyRows_management(till_temp, tillage_table)

    return till_table_result



if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        arcpy.AddMessage("Whoo, hoo! Running from Python Window!")
        cleanup = False

        parameters = ["C:/Program Files/ArcGIS/Pro/bin/Python/envs/arcgispro-py3/pythonw.exe",
    "C:/DEP/Scripts/basics/cmd_ept_wesm_processing.py",
    "C:/DEP/Elev_Base_Data/ept/ept.gdb/ept_resources_2023_05_22"]

        for i in parameters[2:]:
            sys.argv.append(i)
    else:
        arcpy.AddMessage("Whoo, hoo! Command-line enabled!")
        # clean up the folder after done processing
        cleanup = True

    # ept_fc = "C:/DEP/Elev_Base_Data/ept/ept.gdb/ept_resources_2023_05_20"
    ept_fc = sys.argv[1]
    doTillageAssign(ept_fc, cleanup, msgStub())

    arcpy.AddMessage("Back from doTillageAssign!")