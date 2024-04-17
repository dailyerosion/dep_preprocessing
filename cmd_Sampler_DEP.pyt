##cmd_gen1Samper.py
## Brian Gelder, bkgelder@iastate.edu
## Python 3.7, ArcGIS Pro 2.8 as of 2022.06.09
## Python 2.7, ArcGIS 10.3
## A program that samples the Daily Erosion Project input datasets (flowpaths, DEMs, flowlengths,
## grid order, tillage/residue cover maps, and soils data to generate a DBF of flowpath values
## for Daryl Herzmann to ingest and create WEPP input files.
##
## 2014/04/30 - original coding
## 2019/03/15 - switched to use of joinDict instead of JoinField tool for improved performance
## 2019/03/20 - modified for ingesting residue cover maps from Minnesota (0-200 residue score, 1/2% increments 
## 2019/06/24 - modified to output all tillage data, samples, and null samples as JSON to improve data tracking (Nulls allowed, not 0)
## 2019/08/05 - modified to also output all tillage data, samples, and null samples to ACPF FGDB to further improve data tracking (Nulls allowed, not 0)
## 2019/10/29 - v5 modified to handle different management/residue cover inputs
##              also added specifications of SOL and CDL year for better data tracking
## 2020.05.19 - v7 added testing/fixing empty SSURGO value cells due to some issues in gSSURGO mosaicing for ACPF
## 2021.01.20 - v8 switched to loading paths using limited argument passing
##                  Eventually will add ability to use conservation BMP feature classes to modify overall field management codes
## 2021.11.02 - revised field names that use ACPF and SOL year due to change in 2020 DEP ACPF to use FY2020 soils with 2020 CDL
## 2022.04.20 - added logging, switched prints to log.
## 2022.06.09 - added irrgation map sampling to determine whether a flowpath is irrigated
## 2024.03.27 - moved code to AG Pro 3.2, Python 3.9

# Import system modules
import arcpy
import sys
import os
import traceback
#import datetime
import time
import platform
#from arcpy import env
from arcpy.sa import *
sys.path.append("C:\\DEP\\Scripts\\basics")
import dem_functions as df
from os.path import join as opj



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
        self.label = "Sample input rasters, feature classes, and tables to build DEP/WEPP inputs"
        self.description = "Using flowpaths, sample the elevation, distance along flowpath, field boundary, soils and irrigation datasets. May add BMPs later."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            name="monthly_ept_wesm_mashup",
            displayName="EPT WESM Merged Features",
            datatype="DEFeatureClass",
            parameterType='Required',
            direction="Input")
        
        param1 = arcpy.Parameter(
            name="dem_polygon",
            displayName="Buffered HUC12 Feature",
            datatype="DEFeatureClass",
            parameterType='Required',
            direction="Input")
        
        param2 = arcpy.Parameter(
            name = "pdal_exe",
            displayName="PDAL.exe Location",
            datatype="DEFile",
            parameterType='Required',
            direction="Input")
        
        param3 = arcpy.Parameter(
            name = "gsds",
            displayName="Integer Resolution/Ground Sample Distance of output rasters, multiples joined by comma",
            datatype="GPString",
            parameterType='Required',
            direction="Input")
        param3.values = "3,2,1"#default gsds value to create 3, 2, and 1 meter rasters
        
        param4 = arcpy.Parameter(
            name = "fElevFile",
            displayName="Output Pit-Filled Elevation Model",
            datatype="DERasterDataset",
            parameterType='Required',
            direction="Output")
        
        param5 = arcpy.Parameter(
            name = "procDir",
            displayName="Local Processing Directory",
            datatype="DEFolder",
            parameterType='Optional',
            direction="Input")
        
        param6 = arcpy.Parameter(
            name="snap",
            displayName="Snap Raster",
            datatype="DERasterDataset",
            parameterType='Optional',
            direction="Input")
        
        param7 = arcpy.Parameter(
            name = "bareEarthReturnMinFile",
            displayName="Output Bare Earth Minimum Elevation Model",
            datatype="DERasterDataset",
            parameterType='Optional',
            direction="Output")
        
        param8 = arcpy.Parameter(
            name = "firstReturnMaxFile",
            displayName="Output First Return Maximum Elevation/Surface Model",
            datatype="DERasterDataset",
            parameterType='Optional',
            direction="Output")
        
        param9 = arcpy.Parameter(
            name = "cntFile",
            displayName="Output Bare Earth Return Count Raster",
            datatype="DERasterDataset",
            parameterType='Optional',
            direction="Output")
        
        param10 = arcpy.Parameter(
            name = "cnt1rFile",
            displayName="Output First Return Count Raster",
            datatype="DERasterDataset",
            parameterType='Optional',
            direction="Output")
        
        param11 = arcpy.Parameter(
            name = "int1rMinFile",
            displayName="Output Intensity First Return Minimum Raster",
            datatype="DERasterDataset",
            parameterType='Optional',
            direction="Output")
        
        param12 = arcpy.Parameter(
            name = "int1rMaxFile",
            displayName="Output Intensity First Return Maximum Raster",
            datatype="DERasterDataset",
            parameterType='Optional',
            direction="Output")
        
        param13 = arcpy.Parameter(
            name = "intBeMaxFile",
            displayName="Output Intensity Bare Earth Maximum Raster",
            datatype="DERasterDataset",
            parameterType='Optional',
            direction="Output")
        
        param14 = arcpy.Parameter(
            name = "breakpolys",
            displayName="Output HUC12 Merged Breakline Polygon Features",
            datatype="DEFeatureClass",
            parameterType='Optional',
            direction="Output")
        
        param15 = arcpy.Parameter(
            name = "breaklines",
            displayName="Output HUC12 Merged Breakline Polyline Features",
            datatype="DEFeatureClass",
            parameterType='Optional',
            direction="Output")
        
        param16 = arcpy.Parameter(
            name = "ept_wesm_project_file",
            displayName="EPT WESM Feature for AOI",
            datatype="DEFeatureClass",
            parameterType='Optional',
            direction="Output")
                
        params = [param0, param1, param2, param3,
                  param4, param5, param6, param7,
                  param8, param9, param10, param11,
                  param12, param13, param14, param15,
                  param16]
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
        doSampler(parameters[0].valueAsText, cleanup, messages)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return



if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        #Paste arguments into here for use within Python Window
        arcpy.AddMessage("Whoo, hoo! Running from Python Window!")
        cleanup = False

        parameters = ["C:/Python27/ArcGISx6410.3/pythonw.exe",
        "C:/DEP/Scripts/basics/cmd_gen1Sampler_v8_irrigate.py",
        "//EL3354-02/O$/DEP/LiDAR_Current/elev_PLib_mean18/07020001/ep3m070200010901.tif",
        "//EL3354-02/O$/DEP/DEP_Flowpaths/HUC12_FlowPaths_mean18/07020001/fp070200010901.tif",
        "//EL3354-02/O$/DEP/DEP_Flowpaths/HUC12_FPLengths_mean18/07020001/fpLen070200010901.tif",
        "//EL3354-02/O$/DEP/DEP_Flowpaths/HUC12_GridOrder_mean18/07020001/gord_070200010901.tif",
        "//EL3354-02/D$/DEP/Man_Data_ACPF/dep_ACPF2022/07020001/idepACPF070200010901.gdb/gSSURGO",
        "//EL3354-02/O$/DEP/Man_Data_Other/lanid2011-2017/lanid2017.tif",
        "//EL3354-02/D$/DEP/Man_Data_ACPF/dep_ACPF2022/07020001/idepACPF070200010901.gdb/FB070200010901",
        "//EL3354-02/D$/DEP/Man_Data_ACPF/dep_ACPF2022/07020001/idepACPF070200010901.gdb/LU6_070200010901",
        "Management_CY_2022",
        "//EL3354-02/D$/DEP/Man_Data_ACPF/dep_WEPP_SOL2023",
        "//EL3354-02/D$/DEP/Man_Data_ACPF/dep_ACPF2022/07020001/idepACPF070200010901.gdb/smpl3m_mean18070200010901",
        "//EL3354-02/D$/DEP/Man_Data_ACPF/dep_ACPF2022/07020001/idepACPF070200010901.gdb/null3m_mean18070200010901",
        "//EL3354-02/D$/DEP/Man_Data_ACPF/dep_ACPF2022/07020001/idepACPF070200010901.gdb/null_flowpaths3m_mean18070200010901",
        "D:/DEP_Proc/DEMProc/Sample_dem2013_3m_070200010901"]
    
        for i in parameters[2:]:
            sys.argv.append(i)

    else:
        cleanup = True

    messages = msgStub()

def doSampler(pElevFile, fpRasterInit, fplRasterInit, gordRaster, ss, irrigation_map, fieldBoundaries, 
              lu6, manfield, soilsDir, output, nullOutput, null_flowpaths, procDir, cleanup, messages):

    arguments = [pElevFile, fpRasterInit, fplRasterInit, gordRaster, ss, irrigation_map, fieldBoundaries, 
              lu6, manfield, soilsDir, output, nullOutput, null_flowpaths, procDir, cleanup]

    for a in arguments:
        if a == arguments[0]:
            arg_str = str(a) + '\n'
        else:
            arg_str += str(a) + '\n'

    messages.addMessage("Tool: Executing with parameters:\n" + arg_str)

    arcpy.env.overwriteOutput = True

    arcpy.CheckOutExtension("Spatial")
    arcpy.CheckOutExtension("3D")

    arcpy.env.ZResolution = "0.01"

    try:
        huc12, huc8, named_cell_size = df.figureItOut(pElevFile)

        if cleanup:
            # log to file only
            log, nowYmd, logName, startTime = df.setupLoggingNoCh(platform.node(), sys.argv[0], huc12)
        else:
            # log to file and console
            log, nowYmd, logName, startTime = df.setupLoggingNew(platform.node(), sys.argv[0], huc12)

        # if not os.path.isfile(flib_metadata_template):
        #     log.warning('flib_metadata does not exist')
        # if not os.path.isfile(derivative_metadata):
        #     log.warning('derivative_metadata does not exist')
        log.info("Beginning execution: " + time.asctime())
        log.debug('sys.argv is: ' + str(sys.argv) + '\n')
        log.info("Processing HUC: " + huc12)

        if procDir != "":
            if os.path.isdir(procDir):
                log.info('nuking: ' + procDir)
                df.nukedir(procDir)

            if not os.path.isdir(procDir):
                os.makedirs(procDir)

            arcpy.env.scratchWorkspace = procDir

        sfldr = arcpy.env.scratchFolder
        sgdb = arcpy.env.scratchGDB
        arcpy.env.scratchWorkspace = sgdb
        arcpy.env.workspace = sgdb

        inm = 'in_memory'

# #-------------------------------------------------------------------------------
# pElevFile = sys.argv[1]#paths['pElevFile']
# ## flowpath directory
# fpRasterInit = sys.argv[2]#paths["FPath_Mosaic_out"]#sys.argv[4]
# ## flowpath length directory
# fplRasterInit = sys.argv[3]#paths["FPLen_Mosaic_out"]#sys.argv[5]
# ## grid order directory
# gordRaster = sys.argv[4]#paths["GordRaster"]#sys.argv[6]
# # SSURGO map
# ss = sys.argv[5]#paths['SSURGO']#os.path.join(fileGDB, 'gSSURGO')
# # Irrigation map for determining irrigation status
# irrigation_map = sys.argv[6]#paths["irrigationMap"]

# fieldBoundaries = sys.argv[7]#paths['fieldBoundaries']

# lu6 = sys.argv[8]#paths["LU6"]
# manfield = sys.argv[9]#paths["manField"]

# # DEP soils directory (for SOL file check)
# soilsDir = sys.argv[10]#paths["soilsDir"]#sys.argv[8]

# ## for DBF output
# output = sys.argv[11]#paths["samples"]#Output"]#sys.argv[9]
# nullOutput = sys.argv[12]#paths["nulls"]#Output"]#sys.argv[10]
# null_flowpaths = sys.argv[13] + '_copy'#paths['null_flowpaths']

# ## bulk processing (Scratch) directory
# bulkDir = sys.argv[14]#paths['samplerProcDir']#sys.argv[3]
# if arcpy.Exists(bulkDir):
#     arcpy.Delete_management(bulkDir)
# os.makedirs(bulkDir)

#-------------------------------------------------------------------------------
        ## SSURGO fiscal year
        solYear = os.path.basename(soilsDir)[-4:]

        solFyFieldName = 'SOL_FY_' + solYear
        ACPFyear = str(int(solYear)+1)
        fields = df.loadFieldNames(ACPFyear)
        cropRotatnFieldName = fields['rotfield']#'CropRotatn_CY_' + str(int(ACPFyear))
        managementFieldName = fields['manfield']#'Management_CY_' + str(int(ACPFyear))

        log.info(cropRotatnFieldName)
        log.info(managementFieldName)

    ## use ACPF directory as workspace since 2 of the 5 rasters or feature classes we need are here already
        arcpy.env.workspace = os.path.dirname(fieldBoundaries)#fileGDB

        ## convert field polygons to raster so we can use sample
        if arcpy.Exists(fieldBoundaries) and arcpy.Exists(gordRaster):
        ##        print('processing field boundaries')

            gord = Raster(gordRaster)#os.path.join(gordDir, 'gord_' + huc12 + '.tif'))

            arcpy.env.snapRaster = gordRaster#fp#elev
            arcpy.env.cellSize = gordRaster#fp#elev
            sgdb = arcpy.env.scratchGDB
            sfldr = arcpy.env.scratchFolder

        ## convert field polygons from ACPF to raster so we can use sample
            repro = arcpy.Project_management(fieldBoundaries, os.path.join(sgdb, 'fbnds'), gord.spatialReference)
            # switched to FTR to match previous flowpath step
    ####        ftr2 = arcpy.FeatureToRaster_conversion(repro, 'FBndID', opj(bulkDir, 'FBnd' + huc12 + '.tif'))
        ####        ptr2 = arcpy.PolygonToRaster_conversion(repro, 'FBndID', bulkDir + '\\ptr_FBnd' + huc12 + '.tif',"CELL_CENTER")#,"NONE",str(fp.meanCellHeight))

        ## relative file for ACPF soil data
            ssRepro = arcpy.ProjectRaster_management(ss, os.path.join(sgdb, 'ssurgo'), gord.spatialReference, 'NEAREST', cell_size = gord.meanCellHeight)

        ## Reproject irrigation map
            desc_bnd = arcpy.Describe(fieldBoundaries)#wbd)
            extent = desc_bnd.extent
            elev = Raster(pElevFile)
    ##        extent = elev.extent

            # clip extent needs to be in USGS Albers
            # buffer boundary extent by 10000m to make sure we get a large enough irrigation raster (has caused excess NoData issues otherwise)
            irrigation_clip = arcpy.Clip_management(irrigation_map, str(extent.XMin-10000) + ' ' + str(extent.YMin-10000) + ' ' + str(extent.XMax+10000) + ' ' + str(extent.YMax+10000), opj(sgdb, 'irrigation_clip'))
            irrigation_reproject = arcpy.ProjectRaster_management(irrigation_clip, os.path.join(sgdb, 'irrigated'), gord.spatialReference, 'NEAREST', cell_size = gord.meanCellHeight)


            # handle multiple flowpath rasters (due to defined flowpaths)
            for k10counter in range(0, 1):
    ##        for k10counter in range(0, 10):
                if k10counter == 0:
                    fpRaster = fpRasterInit
                    fplRaster = fplRasterInit
                else:
                    fpRaster = fpRasterInit.replace('fp', 'fp' + str(k10counter * 10) + 'k')
                    fplRaster = fplRasterInit.replace('fpLen', 'fpLen' + str(k10counter * 10) + 'k')
                    k10Output = output.replace('smpl', 'smpl' + str(k10counter * 10) + 'k')
                    k10NullOutput = nullOutput.replace('null', 'null' + str(k10counter * 10) + 'k')
                    log.info(fpRaster)
                    log.info(fplRaster)
                
                if arcpy.Exists(fpRaster):
                ## Set up absolute paths elevation, flowpath (number), and flowpath length rasters
                    fp = Raster(fpRaster)
                    
                    fpLenCm = Raster(fplRaster)

                    arcpy.env.snapRaster = fp#elev
    ##                arcpy.env.extent = fp#elev
                    arcpy.env.cellSize = fp#elev
                ## create sample table
            ##        print('sampling')
                    sample_list = [elev, fpLenCm, ssRepro, gord, irrigation_reproject]
                    sampleRaw1 = Sample(sample_list, fp, os.path.join(sgdb, 'smpl_raw6_' + huc12), 'NEAREST')
    ##                print('rows in sampleRaw1 is ' + str(arcpy.GetCount_management(sampleRaw1)))

                    # now test for Null soil values (due to single cell dropouts in ACPF gSSURGO creation...)
                    ssurgo_field_name = df.getfields(sampleRaw1, 'ssurgo*')[0]
                    fp_len_field_name = df.getfields(sampleRaw1, fpLenCm.name[:5] + '*')[0]
                    gord_field_name = df.getfields(sampleRaw1, gord.name[:5] + '*')[0]
                    elev_field_name = df.getfields(sampleRaw1, elev.name[:5] + '*')[0]
                    irrigated_field_name = df.getfields(sampleRaw1, 'irrigated*')[0]
                    
                    hopefullyEmptyList = [s[0] for s in arcpy.da.SearchCursor(sampleRaw1, [ssurgo_field_name], where_clause = ssurgo_field_name + ' IS NULL')]
                    if len(hopefullyEmptyList) > 0:
    ##                    print('resampling due to small gaps in SSURGO')
                        ssReproCopy = arcpy.CopyRaster_management(ssRepro, str(ssRepro) + '_gaps')
                        joinFields = df.getfields(ssRepro)[3:]
                        ssReproName = str(ssRepro)
                        arcpy.Delete_management(ssRepro)
                        isn = IsNull(ssReproCopy)
                        maj = FocalStatistics(ssReproCopy, NbrRectangle(7, 7, 'CELL'), 'MAJORITY')#MajorityFilter(ssRepro)
                        noGaps = Con(isn == 0, ssReproCopy, maj)
                        ssRepro = arcpy.CopyRaster_management(noGaps, ssReproName)
                        arcpy.JoinField_management(ssRepro, 'VALUE', ss, 'VALUE', joinFields)
                        arcpy.Delete_management(sampleRaw1)
                        sampleRaw1 = Sample(sample_list, fp, os.path.join('in_memory', 'smpl_raw6_' + huc12), 'NEAREST')
    ##                    sampleRaw1 = Sample([elev, fpLenCm, ftr2.getOutput(0), ssRepro, gord], fp, 'in_memory\\smpl_raw_' + huc12, 'NEAREST')
                        

                    srFp = arcpy.Describe(fp).spatialReference
                    xyLyr = arcpy.MakeXYEventLayer_management(sampleRaw1, 'X', 'Y', 'xy_layer', srFp)
                    xyOutput = os.path.join(inm, 'sample_pts_utm_' + huc12)
                    xyUTM = arcpy.CopyFeatures_management(xyLyr, xyOutput)
                    sampleRaw = arcpy.Intersect_analysis([xyUTM, fieldBoundaries], opj(sgdb, 'int_pts_' + huc12))
                    arcpy.DeleteField_management(sampleRaw, 'FID_FB' + huc12)
                    arcpy.DeleteField_management(sampleRaw, 'Acres')
                    arcpy.DeleteField_management(sampleRaw, 'isAG')
                    arcpy.DeleteField_management(sampleRaw, 'updateYr')
                    arcpy.DeleteField_management(sampleRaw, 'FB_IN_HUC12')
                    arcpy.DeleteField_management(sampleRaw, 'FID_sample_pts_utm_' + huc12)

                    # test this code ot make it match fpXXXXXXXXXXXX for Daryl's schema
    ##                fpField = df.getfields(sampleRaw, 'fp' + huc12 + '*')[0]
                    fpField = 'fp' + huc12
                    arcpy.AlterField_management(sampleRaw, arcpy.ValidateFieldName(fp.name), fpField)
                    arcpy.AlterField_management(sampleRaw, fp_len_field_name, 'fpLen' + huc12)#'fp' + huc12 + '_tif', 'fp' + huc12)
                    arcpy.AlterField_management(sampleRaw, elev_field_name, 'ep' + str(int(elev.meanCellHeight)) + 'm' + huc12)
                    arcpy.AlterField_management(sampleRaw, gord_field_name, 'gord_' + huc12)
                    arcpy.AlterField_management(sampleRaw, irrigated_field_name, 'irrigated')

                    # make sure no 0 values remain (shouldn't after re-write, but...)
                    sample = arcpy.Select_analysis(sampleRaw, os.path.join(sgdb, 'smpl_gord_' + huc12), fpField + ' > 0 AND ep' + str(int(elev.meanCellHeight)) + 'm' + huc12 + ' > 0')


                ## bring in field land cover and management/residue cover data
                    df.joinDict(sample, 'FBndID', lu6, 'FBndID', ['CropRotatn', 'GenLU', manfield])

                    arcpy.AddField_management(sample, 'SOL_Exists', 'SHORT')

                    # create a feature class from sample that preserves Nulls
                    gdbsample = arcpy.Select_analysis(sample, os.path.join(sgdb, 'init_sample'), 'CropRotatn IS NOT NULL')

                ## remove data about original UTM coordinates to avoid confusion
                    arcpy.DeleteField_management(gdbsample, 'X')
                    arcpy.DeleteField_management(gdbsample, 'Y')

                    # initialize tracking variables for soil files - all flowpaths end at a missing soil file
                    prevFp = -9999
                    prevSol = -9999
                    deadEndFp = False

                    with arcpy.da.UpdateCursor(gdbsample, ['GenLU', manfield, ssurgo_field_name, 'SOL_Exists', fpField, 'fpLen' + huc12, 'CropRotatn'], sql_clause = (None, 'ORDER BY ' + fpField + ', fpLen' + huc12)) as ucur:
                        for urow in ucur:
                ## only sample those with valid values (All NULLs become 0 in DBF land...)
                            if urow[2] is None:
                                solExists = False
                                deadEndFp = True
                            else:
                                # make sure soils file exists at start of any flowpath
                                solFile = os.path.join(soilsDir, 'DEP_' + str(int(urow[2])) + '.sol')
                                # handle areas outside gSSURGO bounds (currently portions of HUC12s in states outside ACPF core)
                                if prevFp == -9999 or urow[4] != prevFp:
                                    if os.path.isfile(solFile):
                                        solExists = True
                                        deadEndFp = False
                                    else:
                                        solExists = False
                                        deadEndFp = True

                                # make sure soils file exists at any change of soil map unit
                                # make sure not at start of any flowpath
                                if prevFp != -9999 and urow[4] == prevFp:
                                    if urow[2] != prevSol:
                                        if os.path.isfile(solFile) and not deadEndFp:
                                            solExists = True
                                        else:
                                            solExists = False
                                            deadEndFp = True
                                    
                                # update previous values for comparison with next row
                                prevFp = urow[4]
                                prevSol = urow[2]

                                if solExists:
                                    urow[3] = 1
                                else:
                                    urow[3] = 0
                            
                            ucur.updateRow(urow)

                    # update field names from joined ACPF tables to be more specific for year
                    arcpy.AlterField_management(gdbsample, ssurgo_field_name, solFyFieldName)
                    arcpy.AlterField_management(gdbsample, 'CropRotatn', cropRotatnFieldName)

                    # add a unique identifier field
                    fp_basename = os.path.basename(fpRasterInit)
                    if 'X' in fp_basename:
                        fp_id_field = 'fp_id_' + huc12
                        fld_add1 = arcpy.AddField_management(gdbsample, fp_id_field, 'TEXT', 30)

                        # turn 2 digit id into 4 digit
                        i = fp_basename[3:5]
                        rep4 = "%04d" %int(i)

                        with arcpy.da.UpdateCursor(gdbsample, [fpField, fp_id_field]) as ucur:
                            for urow in ucur:
                                fp = urow[0]
                                fp_string = "%04d" %fp
                                year_fp_rep_string = ACPFyear + fp_string + rep4
                                urow[1] = year_fp_rep_string
                                ucur.updateRow(urow)



                    # create queries to define good and bad samples 
                    goodSQL = 'SOL_Exists = 1 AND fpLen' + huc12 + ' IS NOT NULL'
                    badSQL = fpField + ' = 0 OR ep' + str(int(elev.meanCellHeight)) + 'm' + huc12 + ' IS NULL OR SOL_Exists = 0 OR ' + cropRotatnFieldName + ' IS NULL OR fpLen' + huc12 + ' IS NULL'

                    if not os.path.isdir(os.path.dirname(output)):
                        os.makedirs(os.path.dirname(output))
                    if k10counter == 0:
                    
                        albersOutput = os.path.join(sgdb, 'sample_pts_5070_' + huc12)
                        xyAlbers = arcpy.Project_management(gdbsample, albersOutput, 5070)

                        goodsamples = arcpy.Select_analysis(xyAlbers, output, where_clause = goodSQL)
    ##                    print('rows in output is ' + str(arcpy.GetCount_management(goodsamples)))#output)))
                        
                        badsamples = arcpy.Select_analysis(xyAlbers, nullOutput, badSQL)
                        goodcount = int(arcpy.GetCount_management(goodsamples).getOutput(0))
                        badcount = int(arcpy.GetCount_management(badsamples).getOutput(0))
                        if badcount > goodcount:
                            log.warning('More bad samples in HUC12 than good')
                        statOut = arcpy.Statistics_analysis(badsamples, null_flowpaths, fpField + " COUNT", fpField)
                        badfps = int(arcpy.GetCount_management(statOut).getOutput(0))
    ##                    assert badfps < 25, "Bad flowpaths in HUC12 too great"
                        bad_thresh= 10
                        if badfps > bad_thresh:
                            log.warning('Bad flowpaths in HUC12 exceed threshold')
    ##                        assert goodcount/badcount > 50, "Not enough good count entries"
                    else:
                        albersOutput = os.path.join(sgdb, 'sample' + str(k10counter * 10) + 'k' + '_pts_5070_' + huc12)
                        xyAlbers = arcpy.Project_management(gdbsample, albersOutput, 5070)

                        k10goodSamples = arcpy.Select_analysis(xyAlbers, k10Output, goodSQL)
    ##                    print('rows in goodSamples is ' + str(arcpy.GetCount_management(k10goodSamples)))
                        k10badsamples = arcpy.Select_analysis(xyAlbers, k10NullOutput, badSQL)
    ####                    nullOutput_defined = nullOutput.replace('null', 'nulldef')
                        if k10counter == 1:
                            arcpy.CopyFeatures_management(k10goodSamples, output_defined)
                            arcpy.CopyFeatures_management(k10badsamples, nullOutput)
                        else:
                            arcpy.Append_management([k10goodSamples], output_defined)
                            arcpy.Append_management([k10badsamples], nullOutput)
    ##                    print('rows in output is ' + str(arcpy.GetCount_management(output_defined)))

                    if cleanup:
                        arcpy.Delete_management(sampleRaw)
                        arcpy.Delete_management(sample)
                        arcpy.Delete_management(gdbsample)
                        arcpy.Delete_management(xyAlbers)
                        arcpy.Delete_management(xyUTM)

                else:
                    if k10counter > 0:
    ##                    print('breaking for k10 counter = ' + str(k10counter))
                        break
                    else:
                        pass

    except AssertionError:
        log.warning('assertion failure on: ' + huc12)
        sys.exit(1)

    except:
        # Get the traceback object
        #
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]

        # Concatenate information together concerning the error into a message string
        #
        pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
        msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"

        # Print Python error messages for use in Python / Python Window
        #
        log.warning(pymsg)
        log.warning(msgs)

        log.warning('failure on: ' + huc12)
        sys.exit(1)

    finally:
        log.warning("Finished at " + time.asctime())