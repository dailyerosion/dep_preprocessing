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
import platform
from arcpy.sa import *
sys.path.append("C:\\DEP\\Scripts\\basics")
sys.path.append("C:\\GitHub\\hydro_dems")
import dem_functions as df
from os.path import join as opj

import pathlib


class msgStub:
    def addMessage(self,text):
        arcpy.AddMessage(text)
    def addErrorMessage(self,text):
        arcpy.AddErrorMessage(text)
    def addWarningMessage(self,text):
        arcpy.AddWarningMessage(text)

# class Toolbox(object):
#     def __init__(self):
#         """Define the toolbox (the name of the toolbox is the name of the
#         .pyt file)."""
#         self.label = "Toolbox"
#         self.alias = "toolbox"

#         # List of tool classes associated with this toolbox
#         self.tools = [Tool]


# class Tool(object):
#     def __init__(self):
#         """Define the tool (tool name is the name of the class)."""
#         self.label = "Sample input rasters, feature classes, and tables to build DEP/WEPP inputs"
#         self.description = "Using flowpaths, sample the elevation, distance along flowpath, field boundary, soils and irrigation datasets. May add BMPs later."
#         self.canRunInBackground = False

#     def getParameterInfo(self):
#         """Define parameter definitions"""

#         param0 = arcpy.Parameter(
#             name = "fElevFile",
#             displayName="Input Punched Elevation Model",
#             datatype="DERasterDataset",
#             parameterType='Required',
#             direction="Input")
        
#         param1 = arcpy.Parameter(
#             name="fpRasterInit",
#             displayName="Flowpath Raster",
#             datatype="DERasterDataset",
#             parameterType='Required',
#             direction="Input")
        
#         param2 = arcpy.Parameter(
#             name="fplRasterInit",
#             displayName="Flowpath Length Raster",
#             datatype="DERasterDataset",
#             parameterType='Required',
#             direction="Input")
        
#         param3 = arcpy.Parameter(
#             name="gordRaster",
#             displayName="Grid Order Raster",
#             datatype="DERasterDataset",
#             parameterType='Required',
#             direction="Input")
        
#         param4 = arcpy.Parameter(
#             name="ss",
#             displayName="Soil Survey Raster",
#             datatype="DERasterDataset",
#             parameterType='Required',
#             direction="Input")
        
#         param5 = arcpy.Parameter(
#             name="irrigation_map",
#             displayName="Grid Order Raster",
#             datatype="DERasterDataset",
#             parameterType='Required',
#             direction="Input")
        
#         param6 = arcpy.Parameter(
#             name="snap",
#             displayName="ACPF Field Boundaries",
#             datatype="DEFeatureClass",
#             parameterType='Required',
#             direction="Input")
        
#     arguments = [pElevFile, fpRasterInit, fplRasterInit, gordRaster, ss, irrigation_map, fieldBoundaries, 
#               lu6, manfield, soilsDir, output, nullOutput, null_flowpaths, procDir, cleanup]
#         param7 = arcpy.Parameter(
#             name = "lu6",
#             displayName="Output Bare Earth Minimum Elevation Model",
#             datatype="DETable",
#             parameterType='Required',
#             direction="Input")
        
#         param8 = arcpy.Parameter(
#             name = "manfield",
#             displayName="Output First Return Maximum Elevation/Surface Model",
#             datatype="DERasterDataset",
#             parameterType='Required',
#             direction="Input")
        
#         param9 = arcpy.Parameter(
#             name = "soilsDir",
#             displayName="Output Bare Earth Return Count Raster",
#             datatype="DERasterDataset",
#             parameterType='Required',
#             direction="Input")
        
#         param10 = arcpy.Parameter(
#             name = "output",
#             displayName="Output Sample table",
#             datatype="DETable",
#             parameterType='Required',
#             direction="Output")
        
#         param11 = arcpy.Parameter(
#             name = "nullOutput",
#             displayName="Output Intensity First Return Minimum Raster",
#             datatype="DERasterDataset",
#             parameterType='Required',
#             direction="Output")
        
#         param12 = arcpy.Parameter(
#             name = "int1rMaxFile",
#             displayName="Output Intensity First Return Maximum Raster",
#             datatype="DERasterDataset",
#             parameterType='Required',
#             direction="Output")
        
#         param13 = arcpy.Parameter(
#             name = "intBeMaxFile",
#             displayName="Output Intensity Bare Earth Maximum Raster",
#             datatype="DERasterDataset",
#             parameterType='Required',
#             direction="Output")
                        
#         params = [param0, param1, param2, param3,
#                   param4, param5, param6, param7,
#                   param8, param9, param10, param11,
#                   param12, param13, param14, param15,
#                   param16]
#         return params


#     def isLicensed(self):
#         """Set whether tool is licensed to execute."""
#         return True

#     def updateParameters(self, parameters):
#         """Modify the values and properties of parameters before internal
#         validation is performed.  This method is called whenever a parameter
#         has been changed."""
#         return

#     def updateMessages(self, parameters):
#         """Modify the messages created by internal validation for each tool
#         parameter.  This method is called after internal validation."""
#         return

#     def execute(self, parameters, messages):
#         """The source code of the tool."""
#         cleanup = False
#         doSampler(parameters[0].valueAsText, cleanup, messages)
#         return

#     def postExecute(self, parameters):
#         """This method takes place after outputs are processed and
#         added to the display."""
#         return

# def doSampler(pElevFile, fpRasterInit, fplRasterInit, gordRaster, ss, irrigation_map, field_or_forest, 
#               lu6, soilsDir, output, nullOutput, null_flowpaths, procDir, cleanup, messages):


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        #Paste arguments into here for use within Python Window
        arcpy.AddMessage("Whoo, hoo! Running from Python Window!")
        cleanup = False

        parameters = ["C:/Program Files/ArcGIS/Pro/bin/Python/envs/arcgispro-py3/pythonw.exe",
    "C:/GitHub/dep_preprocessing/cmd_Sampler_DEP.pyt",
    "M:/DEP/LiDAR_Current/elev_PLib_mean18/07080105/ep3m070801050303.tif",
    "H:/tsklenar/ISA_project/isa_all_good_flowpaths_by_huc/070801050303_isa_paths_composite.tif/unique_id",
    "H:/tsklenar/ISA_project/isa_all_good_flowpaths_by_huc/070801050303_isa_paths_composite.tif/flow_length",
    "M:/DEP/DEP_Flowpaths/HUC12_GridOrder_mean18/07080105/gord_070801050303.tif",
    "D:/DEP/Man_Data_ACPF/dep_ACPF2022/07080105/idepACPF070801050303.gdb/gSSURGO",
    "M:/DEP/Man_Data_Other/wss_gsmsoil_US/spatial/gsmsoilmu_a_us.shp",
    "M:/DEP/Man_Data_Other/lanid2011-2017/lanid2017.tif",
    "D:/DEP_bkg_isa_samples/Man_Data_ACPF/dep_ACPF2022/07080105/idepACPF070801050303.gdb/FB070801050303",
    "D:/DEP_bkg_isa_samples/Man_Data_ACPF/dep_ACPF2022/07080105/idepACPF070801050303.gdb/LU6_070801050303",
    "D:/DEP/Man_Data_ACPF/dep_WEPP_SOL2023",
    "D:/DEP_bkg_isa_samples/Man_Data_ACPF/dep_ACPF2022/07080105/idepACPF070801050303.gdb/smpl3m_mean18070801050303",
    "D:/DEP_bkg_isa_samples/Man_Data_ACPF/dep_ACPF2022/07080105/idepACPF070801050303.gdb/null3m_mean18070801050303",
    "D:/DEP_bkg_isa_samples/Man_Data_ACPF/dep_ACPF2022/07080105/idepACPF070801050303.gdb/null_flowpaths3m_mean18070801050303",
    "E:/DEP_Proc_bkg_isa_samples/DEMProc/Sample_dem2013_3m_070801050303",
    "D:/DEP_bkg_isa_samples/Man_Data_ACPF/dep_ACPF2022/07080105/idepACPF070801050303.gdb/buf_070801050303",
    "M:/DEP/Man_Data_Other/Forest_Cover/LF2022_CC_220_CONUS/Tif/LC22_CC_220.tif"]
    
        for i in parameters[2:]:
            sys.argv.append(i)

    else:
        cleanup = True

    messages = msgStub()

    pElevFile, fpRasterInit, fplRasterInit, gordRaster, ss, statsgo2, irrigation_map, field_or_forest,\
        lu6, soilsDir, output, nullOutput, null_flowpaths, procDir, buffered_huc, canopy_cover_map = [s if s != "" else None for s in sys.argv[1:]]

    # switch a text 'True' into a real Python True
    cleanup = True if cleanup == "True" else False

    arguments = [pElevFile, fpRasterInit, fplRasterInit, gordRaster, ss, statsgo2, irrigation_map, field_or_forest,\
        lu6, soilsDir, output, nullOutput, null_flowpaths, procDir, buffered_huc, canopy_cover_map, cleanup]

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
        huc12, huc8 = df.figureItOut(pElevFile)

        if procDir is not None:
            if not os.path.isdir(procDir):
                os.makedirs(procDir)

            arcpy.env.scratchWorkspace = procDir
            sfldr = arcpy.env.scratchFolder
        else:
            sfldr = arcpy.env.scratchFolder
            procDir = sfldr

        sfldr = arcpy.env.scratchFolder
        sgdb = arcpy.env.scratchGDB
        arcpy.env.scratchWorkspace = sgdb
        arcpy.env.workspace = sgdb

        #figure out where to create log files
        node = platform.node()
        logProc = df.defineLocalProc(node)
        if not os.path.isdir(logProc):
            logProc = sfldr

        if cleanup:
            # log to file only
            log, nowYmd, logName, startTime = df.setupLoggingNoCh(platform.node(), sys.argv[0], huc12)
            arcpy.SetLogHistory = False
        else:
            # log to file and console
            log, nowYmd, logName, startTime = df.setupLoggingNew(platform.node(), sys.argv[0], huc12)
            arcpy.SetLogHistory = True

        # if not os.path.isfile(flib_metadata_template):
        #     log.warning('flib_metadata does not exist')
        # if not os.path.isfile(derivative_metadata):
        #     log.warning('derivative_metadata does not exist')
        log.info("Beginning execution:")
        log.debug('sys.argv is: ' + str(sys.argv) + '\n')
        log.info("Processing HUC: " + huc12)
        messages.addMessage("Log file at " + logName)

        inm = 'in_memory'

#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
        ## SSURGO fiscal year
        solYear = os.path.basename(soilsDir)[-4:]

        solFyFieldName = 'SOL_FY_' + solYear
        ACPFyear = str(int(solYear)-1)
        fields = df.loadFieldNames(ACPFyear)
        cropRotatnFieldName = fields['rotField']#'CropRotatn_CY_' + str(int(ACPFyear))
        managementFieldName = fields['manField']#'Management_CY_' + str(int(ACPFyear))

        log.info(f"cropRotatnFieldName is {cropRotatnFieldName}")
        log.info(f"managementFieldName is {managementFieldName}")

        if arcpy.Exists(lu6) and cropRotatnFieldName not in df.getfields(lu6):
            arcpy.AddField_management(lu6, cropRotatnFieldName, 'TEXT')
            arcpy.CalculateField_management(lu6, cropRotatnFieldName, '!CropRotatn!', 'PYTHON3')

    ## use ACPF directory as workspace since 2 of the 5 rasters or feature classes we need are here already
        arcpy.env.workspace = os.path.dirname(field_or_forest)#fileGDB

        ## convert field polygons to raster so we can use sample
        if arcpy.Exists(ss) and arcpy.Exists(gordRaster):
            log.info('valid grid order and soils, processing')

            gord = Raster(gordRaster)#os.path.join(gordDir, 'gord_' + huc12 + '.tif'))

            arcpy.env.snapRaster = gordRaster#fp#elev
            gordRastObj = arcpy.Raster(gordRaster)
            named_cell_size = gordRastObj.meanCellHeight
            arcpy.env.cellSize = named_cell_size#gordRaster#fp#elev
            sgdb = arcpy.env.scratchGDB
            sfldr = arcpy.env.scratchFolder

        ## relative file for ACPF soil data
            ssRepro = arcpy.ProjectRaster_management(ss, os.path.join(sgdb, 'ssurgo'), gord.spatialReference, 'NEAREST', cell_size = gord.meanCellHeight)

        ## Reproject buffered huc
            # clip extent needs to be in USGS Albers
            # buffer boundary extent by 10000m to make sure we get a large enough irrigation and canopy raster (has caused excess NoData issues otherwise)
            proj_buf_5070 = arcpy.Project_management(buffered_huc, os.path.join(sgdb, 'buf_huc_5070'), 5070)
            desc_bnd = arcpy.Describe(proj_buf_5070)
            extent = desc_bnd.extent

            log.info('clipping and projecting irrigation')
            irrigation_clip = arcpy.Clip_management(irrigation_map, str(extent.XMin-10000) + ' ' + str(extent.YMin-10000) + ' ' + str(extent.XMax+10000) + ' ' + str(extent.YMax+10000), opj(sgdb, 'irrigation_clip'))
            irrigation_reproject = arcpy.ProjectRaster_management(irrigation_clip, os.path.join(sgdb, 'irrigated'), gord.spatialReference, 'NEAREST', cell_size = gord.meanCellHeight)

            if canopy_cover_map is not None:
                log.info('clipping and projecting forest canopy')
                canopy_cover_clip = arcpy.Clip_management(canopy_cover_map, str(extent.XMin-10000) + ' ' + str(extent.YMin-10000) + ' ' + str(extent.XMax+10000) + ' ' + str(extent.YMax+10000), opj(sgdb, 'canopy_clip'))
                canopy_cover_reproject = arcpy.ProjectRaster_management(canopy_cover_clip, os.path.join(sgdb, 'canopy_cover'), gord.spatialReference, 'NEAREST', cell_size = gord.meanCellHeight)

            log.info('clipping and projecting statsgo2')
            statsgo2_clip = arcpy.Clip_analysis(statsgo2, proj_buf_5070, opj(inm, 'statsgo2_clip'))
            # statsgo2_reproject = arcpy.Project_management(statsgo2_clip, os.path.join(sgdb, 'statsgo2_5070'), gord.spatialReference)#, 'NEAREST', cell_size = gord.meanCellHeight)

            log.info('creating raster object for pElevFile')
            # pElevFile = pElevFile.replace('M:', 'N:')
            # pElevFile_local = arcpy.CopyFeatures_management(pElevFile, opj(procDir, os.path.basename(pElevFile)))
            elev = Raster(pElevFile)#_local)
            log.info('done creating raster object for pElevFile')

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
                    arcpy.env.cellSize = fp#elev
                ## create sample table
                    log.debug('sampling')
                    sample_list = [elev, fpLenCm, str(ssRepro), gord, str(irrigation_reproject)]
                    if canopy_cover_map is not None:
                        sample_list.append(str(canopy_cover_reproject))
                    log.info('sampling first time')
                    sampleRaw1 = Sample(sample_list, fp, os.path.join(sgdb, 'smpl_raw6_' + huc12), 'NEAREST')

                    # now test for Null soil values (due to single cell dropouts in ACPF gSSURGO creation...)
                    ssurgo_field_name = df.getfields(sampleRaw1, 'ssurgo*')[0]
                    pl_raster = pathlib.Path(fplRaster)
                    # for multi-band flowpath and flowpath length raster
                    if pl_raster.parent.name.endswith('.tif'):
                        fp_len_test = "_".join([os.path.splitext(pl_raster.parent.name)[0], pl_raster.name])
                        fp_len_field_name = df.getfields(sampleRaw1, "*" + fp_len_test + '*')[0]
                        # arcpy.AlterField_management(sampleRaw1, fp_len_field_name, 'fpLen' + huc12 + '_Band_1')
                    else:
                        fp_len_field_name = df.getfields(sampleRaw1, fpLenCm.name[:5] + '*')[0]
                    gord_field_name = df.getfields(sampleRaw1, gord.name[:5] + '*')[0]
                    elev_field_name = df.getfields(sampleRaw1, elev.name[:5] + '*')[0]
                    irrigated_field_name = df.getfields(sampleRaw1, 'irrigated*')[0]
                    
                    hopefullyEmptyList = [s[0] for s in arcpy.da.SearchCursor(sampleRaw1, [ssurgo_field_name], where_clause = ssurgo_field_name + ' IS NULL')]
                    if len(hopefullyEmptyList) > 0:
                        log.info('resampling due to small gaps in SSURGO')
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

                    srFp = arcpy.Describe(fp).spatialReference
                    xyLyr = arcpy.MakeXYEventLayer_management(sampleRaw1, 'X', 'Y', 'xy_layer', srFp)

                    sample_output_name = 'sample_pts_utm_' + huc12
                    xyOutput = os.path.join(inm, sample_output_name)
                    xyUTM = arcpy.CopyFeatures_management(xyLyr, xyOutput)
                    # send to gdb for later ordered update cursor
                    xy_int_bounds = opj(sgdb, 'int_pts_' + huc12)
                    statsgoFieldName = 'STATSGO2_MUKEY'#addFieldStatsgo.getInput(1)
                    log.info('sampling second time')
                    sampleRaw = arcpy.Intersect_analysis([xyUTM, field_or_forest, statsgo2_clip], xy_int_bounds)
                    if 'FB' in field_or_forest:
                        # remove extra field brought in by intersection
                        arcpy.DeleteField_management(sampleRaw, 'FID_FB' + huc12)
                        arcpy.DeleteField_management(sampleRaw, 'Acres')
                        arcpy.DeleteField_management(sampleRaw, 'isAG')
                        arcpy.DeleteField_management(sampleRaw, 'updateYr')
                        arcpy.DeleteField_management(sampleRaw, 'FB_IN_HUC12')
                    else:#elif arcpy.Exists(forest_units):
                        # arcpy.AddField_management(sampleRaw, 'FB' + huc12, 'TEXT')
                        arcpy.AddField_management(sampleRaw, 'FBndID', 'TEXT')
                        # fields from forest units
                        arcpy.DeleteField_management(sampleRaw, 'gridcode', 'TEXT')
                        arcpy.DeleteField_management(sampleRaw, 'Id', 'TEXT')

                    arcpy.DeleteField_management(sampleRaw, 'FID_sample_pts_utm_' + huc12)

                    arcpy.AlterField_management(sampleRaw, 'MUKEY', statsgoFieldName)

                    statsgo2_stem = pathlib.Path(statsgo2).stem
                    statsgo_fields = df.getfields(statsgo2) + ['FID_' + statsgo2_stem] + ['FID_' + os.path.basename(str(statsgo2_clip))]
                    int_fields = df.getfields(sampleRaw)
                    for s in statsgo_fields:
                        if s in int_fields:
                            if s not in ['SHAPE', 'Shape', statsgoFieldName]:
                                arcpy.DeleteField_management(sampleRaw, s)

                    # test this code ot make it match fpXXXXXXXXXXXX for Daryl's schema
    ##                fpField = df.getfields(sampleRaw, 'fp' + huc12 + '*')[0]
                    fpField = 'fp' + huc12
                    arcpy.AlterField_management(sampleRaw, arcpy.ValidateFieldName(fp.name), fpField)
                    arcpy.AlterField_management(sampleRaw, fp_len_field_name, 'fpLen' + huc12)#'fp' + huc12 + '_tif', 'fp' + huc12)
                    arcpy.AlterField_management(sampleRaw, elev_field_name, 'ep' + str(int(elev.meanCellHeight)) + 'm' + huc12)
                    arcpy.AlterField_management(sampleRaw, gord_field_name, 'gord_' + huc12)
                    arcpy.AlterField_management(sampleRaw, irrigated_field_name, 'irrigated')
                    if canopy_cover_map is not None:
                        cover_field_name = df.getfields(sampleRaw1, 'canopy_cover*')[0]
                        arcpy.AlterField_management(sampleRaw, cover_field_name, 'canopy_cover')

                    ## remove data about original UTM coordinates to avoid confusion
                    arcpy.DeleteField_management(sampleRaw, 'X')
                    arcpy.DeleteField_management(sampleRaw, 'Y')

                    # make sure no 0 values remain (shouldn't after re-write, but...)
                    sample = arcpy.Select_analysis(sampleRaw, os.path.join(sgdb, 'smpl_gord_' + huc12), fpField + ' > 0 AND ep' + str(int(elev.meanCellHeight)) + 'm' + huc12 + ' > 0')

                ## bring in field land cover and management/residue cover data
                    fields_to_join = set([cropRotatnFieldName, 'GenLU', managementFieldName])
                    log.debug(f"fields_to_join: {fields_to_join}")
                    remaining_fields_to_join = fields_to_join
                    if arcpy.Exists(lu6):
                        lu6_fields = set([f for f in arcpy.ListFields(lu6) if f in fields_to_join])
                        df.joinDict(sample, 'FBndID', lu6, 'FBndID', list(lu6_fields))
                        remaining_fields_to_join = fields_to_join - lu6_fields 
                    log.debug(f"remaining_fields_to_join: {remaining_fields_to_join}")
                    for r in remaining_fields_to_join:
                        arcpy.AddField_management(sample, r, 'TEXT')

                    arcpy.AddField_management(sample, 'SOL_Exists', 'SHORT')
                    addFieldStatsgo = arcpy.AddField_management(sample, 'STATSGO_Exists', 'SHORT')
                    statsgoExistsField = addFieldStatsgo.getInput(1)
    
                    # addFieldSoilgrids = arcpy.AddField_management(sample, 'SOILGRIDS_Exists', 'SHORT')
                    # soilgridsFieldName = addFieldSoilgrids.getInput(1)

                    if canopy_cover_map is not None:
                        canopy_cover_field_name = df.getfields(sampleRaw, os.path.basename(str(canopy_cover_reproject)) + '*')[0]
                        # give a value of crop rotation string of all F to those that have canopy cover from LANDFIRE
                        with arcpy.da.UpdateCursor(sample, ['GenLU', managementFieldName, ssurgo_field_name, 'SOL_Exists', fpField, 'fpLen' + huc12, managementFieldName, cropRotatnFieldName, canopy_cover_field_name], sql_clause = (None, 'ORDER BY ' + fpField + ', fpLen' + huc12)) as ucur:
                            for urow in ucur:
                                # set all rows with canopy cover > 0 equal to forest
                                if urow[-1] > 0:
                                    urow[-2] = 'F' * 12
                                # now set the management file to use
                                if urow[-1] >= 90:
                                    urow[-3] = 'J' * 12
                                elif urow[-1] >= 80:
                                    urow[-3] = 'I' * 12
                                elif urow[-1] >= 70:
                                    urow[-3] = 'H' * 12
                                elif urow[-1] >= 60:
                                    urow[-3] = 'G' * 12
                                elif urow[-1] >= 50:
                                    urow[-3] = 'F' * 12
                                elif urow[-1] >= 40:
                                    urow[-3] = 'E' * 12
                                elif urow[-1] >= 30:
                                    urow[-3] = 'D' * 12
                                elif urow[-1] >= 20:
                                    urow[-3] = 'C' * 12
                                elif urow[-1] >= 10:
                                    urow[-3] = 'B' * 12
                                elif urow[-1] >= 0:
                                    urow[-3] = 'A' * 12
                                ucur.updateRow(urow)

                    # create a feature class from sample that preserves Nulls
                    gdbsample = arcpy.Select_analysis(sample, os.path.join(sgdb, 'init_sample'), cropRotatnFieldName + ' IS NOT NULL')

                # ## remove data about original UTM coordinates to avoid confusion
                #     arcpy.DeleteField_management(gdbsample, 'X')
                #     arcpy.DeleteField_management(gdbsample, 'Y')

                    # initialize tracking variables for soil files - all flowpaths end at a missing soil file
                    prevFp = -9999
                    prevSol = -9999
                    deadEndFp = False
# , soilgridsFieldName, soilgridsExistsField
                    with arcpy.da.UpdateCursor(gdbsample, ['GenLU', managementFieldName, ssurgo_field_name, 'SOL_Exists', fpField, statsgoFieldName, statsgoExistsField], sql_clause = (None, 'ORDER BY ' + fpField + ', fpLen' + huc12)) as ucur:
                        for urow in ucur:
                ## only sample those with valid values (All NULLs become 0 in DBF land...)
                            if urow[2] is None:
                                solExists = False
                                ssurgoExists = False
                                statsgoExists = False
                                soilgridsExists = False
                                deadEndFp = True
                            else:
                                # make sure soils file exists at start of any flowpath
                                ssurgoFile = os.path.join(soilsDir, 'DEP_' + str(int(urow[2])) + '.sol')
                                statsgoFile = os.path.join(soilsDir, 'STATSGO_' + str(int(urow[5])) + '.sol')
                                # soilgridsFile = os.path.join(soilsDir, 'SOILGRIDS_' + str(int(urow[7])) + '.sol')
                                # handle areas outside gSSURGO bounds (currently portions of HUC12s in states outside ACPF core)
                                if os.path.isfile(ssurgoFile):
                                    ssurgoExists = True
                                else:
                                    ssurgoExists = False
                                if os.path.isfile(statsgoFile):
                                    statsgoExists = True
                                else:
                                    statsgoExists = False
                                    # if os.path.isfile(soilgridsFile):
                                    #     soilgridsExists = True
                                if prevFp == -9999 or urow[4] != prevFp:
                                    if ssurgoExists:
                                        deadEndFp = False
                                    if statsgoExists:
                                        deadEndFp = False
                                    # if soilgridsExists:
                                        # deadEndFp = False
                                    if ssurgoExists | statsgoExists: #| soilgridsExists:
                                        solExists = True
                                    else:
                                        solExists = False
                                        deadEndFp = True

                                # make sure not at start of any flowpath
                                if prevFp != -9999 and urow[4] == prevFp:
                                    # make sure soils file exists at any change of soil map unit
                                    if urow[2] != prevSol:
                                        if ssurgoExists | statsgoExists and not deadEndFp:
                                        # if os.path.isfile(solFile) and not deadEndFp:
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

                            urow[6] = statsgoExists
##                            urow[8] = soilgridsExists
                            
                            ucur.updateRow(urow)

                    # update field names from joined ACPF tables to be more specific for year
                    arcpy.AlterField_management(gdbsample, ssurgo_field_name, solFyFieldName)
                    # arcpy.AlterField_management(gdbsample, 'CropRotatn', cropRotatnFieldName)

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
                    if canopy_cover_map is None:
                        badSQL = fpField + ' = 0 OR ep' + str(int(elev.meanCellHeight)) + 'm' + huc12 + ' IS NULL OR SOL_Exists = 0 OR ' + cropRotatnFieldName + ' IS NULL OR fpLen' + huc12 + ' IS NULL'
                    else:
                        badSQL = fpField + ' = 0 OR ep' + str(int(elev.meanCellHeight)) + 'm' + huc12 + ' IS NULL OR SOL_Exists = 0 OR fpLen' + huc12 + ' IS NULL'

                    if not os.path.isdir(os.path.dirname(output)):
                        os.makedirs(os.path.dirname(output))
                    if k10counter == 0:
                    
                        albersOutput = os.path.join(sgdb, 'sample_pts_5070_' + huc12)
                        xyAlbers = arcpy.Project_management(gdbsample, albersOutput, 5070)

                        ref_samples_name1 = output.replace(huc12, '070801050902')
                        ref_samples = ref_samples_name1.replace(huc8, '07080105')
                        ref_fields = df.getfields(ref_samples)
                        ref_fields = [r.replace('070801050902', huc12) for r in ref_fields]
                        'D:\\DEP\\Man_Data_ACPF\\dep_ACPF2022\\07080105\\idepACPF070801050902.gdb\\smpl3m_mean18070801050902'

                        for f in fields:
                            if f not in ref_fields:
                                log.warning('missing field: {f}')
                        for f in ref_fields:
                            if f not in fields:
                                log.warning('extra field: {f}')

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
                        # if k10counter == 1:
                        #     arcpy.CopyFeatures_management(k10goodSamples, output_defined)
                        #     arcpy.CopyFeatures_management(k10badsamples, nullOutput)
                        # else:
                        #     arcpy.Append_management([k10goodSamples], output_defined)
                        #     arcpy.Append_management([k10badsamples], nullOutput)
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
        log.info("Finished")
        handlers = log.handlers
        for h in handlers:
            log.info('shutting it down!')
            log.removeHandler(h)
            h.close()
