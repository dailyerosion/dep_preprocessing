#IDEP_TauDEM_PDWS.py
## Individual processing of HUC12 watersheds to create a channel network and catchments
## This process must be run prior to creating individual flow paths for IDEP2 processing
#
## Pueker-Douglas Watersheds
# Using ArcGIS 10.1 and the TauDEM software, generate a HUC12's set of sub-watersheds
#  and channel network using the Pueker-Douglas and Constant Drop Analysis methods.
#  The script requires a DEM (suggested that the cut version be used) and a feature
#  class of the HUC12 boundary. The HUC12 pour point uses the extract-by-intersecting-
#  the-watershed-boundary-flow-accumulation-raster.
#
# The script is written to be used as a ArcGIS Toolbox script. The required inputs are:
#  - the input DEM, as a raster
#  - the Fill response, as a boolean, default is True and is almost always preferred
#  - the HUC12 watershed boundary - this will be replaced with WBD boundaries
#
# A processing sub-directory (wsTauProc) is used to hold the outputs with generated names
#  following the TauDEM conventions. Inputs and outputs must and will conform to
#  TauDEM format restrictions...GeoTIFF with compression = None.  The script expects that
#  MPICH2 and TauDEM executables are in the PATH, or you can include the following in the 
#  code, modified as appropriate:
#       Set TDIR= C:\program files\taudem\taudem5exe
#       set MDIR= C:\program files\mpich2\bin
#       set path=%MDIR%;%TDIR%
#
# NB: the coding where line continuation is used '\' may be confusing.
#
# 7/3/2016 - added try/except error handling, bkgelder@iastate.edu
# 5/4/2018 - removed commented out commands, bkgelder@iastate.edu
#           also revised for better use from command line, removed arcpy.env import as env
# 2019.06.20 - revised to allow pdCatch and pdChnl to be passed in via command line
# 2020.05.24 - added repairgeometry to pdCatch to handle errors when dissolving pdCatch to watershed
# 2021.04.27 - added the ability to use paths dictionary for versioning, versioned statGDB
# 2021.11.02 - previous addition did not include accessing the 'wShed' name for watershed output
# 2022.01.03 - moved repair geometry up earlier to head off more issues with raster to vector conversion
##            tmpWshed = arcpy.RasterToPolygon_conversion(ProcDir + "\\demw.tif", "TMPwshd.shp")
##            arcpy.RepairGeometry_management(tmpWshed)
# 2022.04.12 - Updated the 'TMPwshd.shp' that still existed in some error handling to tmpWshed
# 2022.04.19 - Added arcpy.env.outputCoordinateSystem to convert ws polygons to UTM
#               conversion errors were causing some issues, see 102400060401 for example

##
##-----------------------------------------------------------------------------------------------------##-------------------------------------------------------------------------------------------------------
##-------------------------------------------------------------------------------------------------------

# Import system modules
import arcpy
from arcpy.sa import *
from subprocess import call
import sys
import os
import traceback
import time
import subprocess
sys.path.append("C:\\DEP\\Scripts\\basics")
import dem_functions as df
import platform

# Set extensions & environments 

arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True
arcpy.env.compression = "NONE"


##-------------------------------------------------------------------------------------------------------

def FlowD8(filledDEM, ProcDir):
    try:
##         in support of the ACPF Toolbox, use ArcGIS FlowDirection, then 
##          mosaic the EOW Flowdirection in on top, then 
##          reclass to a TauDEM format FlowDirection for further processing

        arcFDir = FlowDirection(filledDEM.getOutput(0))#"PElev.tif")

        fauxFDir = Reclassify(arcFDir, "VALUE",
                           RemapRange([[1, 1], [128, 2], [64, 3], [32, 4], [16, 5], [8, 6], [4, 7], [2, 8]]))

        arcpy.CopyRaster_management(fauxFDir, "demp.tif")
        
        # Contributing area     
        callstr = "mpiexec -n " + Ncpus + " AreaD8 " + "-p " + ProcDir + "\\demp.tif " + "-ad8 " + ProcDir + "\\demad8.tif -nc"
        subp = subprocess.check_output(callstr, stderr = subprocess.STDOUT)#, timeout = timeout)
        string = subp.decode(sys.stdout.encoding)
    ####    print(string)
        log.debug(string)
##        call(callstr, shell=True)
######        stdout = subprocess.check_output(callstr, stderr=subprocess.STDOUT, env=env)
######        print(stdout)
##        os.system(callstr)
##        process = subprocess.Popen(callstr, shell=True, stdout=subprocess.PIPE)
##
##        message = "\n"
##        for line in process.stdout.readlines():
##            if isinstance(line, bytes):	    # true in Python 3
##                line = line.decode()
##            message = message + line
##        arcpy.AddMessage(message)
##        print(message)

        arcpy.CalculateStatistics_management(ProcDir + "\\demad8.tif")

    except:
        # Get the traceback object
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]

        # Concatenate information together concerning the error into a message string
        pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
        msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"

        # Return python error messages for use in script tool or Python Window
        arcpy.AddError(pymsg)
        arcpy.AddError(msgs)

        # Print Python error messages for use in Python / Python Window
        print(pymsg + "\n")
        print(msgs)



def extractPoutPts(ws_bndy):#fileGDB, huc12, WSBndsrc):
 
    arcpy.AddMessage("Process old watershed boundary...")
    # ws_bndy_lyr = arcpy.MakeFeatureLayer_management(WSBndsrc, "WSBndy_lyr", "\"HUC12\" = \'" + str(huc12) + "\'")

    #arcpy.FeatureToLine_management(fileGDB + "\\bnd" + huc12, "WS_bnd.shp")
    ws_bnd_shp = arcpy.FeatureToLine_management(ws_bndy, "WS_bnd.shp")
    #arcpy.PolylineToRaster_conversion("WS_bnd.shp", "FID", "rasWSBndy.tif")
    ws_bnd_rstr = arcpy.PolylineToRaster_conversion("WS_bnd.shp", "FID", "rasWSBndy")
            
    arcpy.AddMessage("Extract pour points...")
    #bndFacc = Con('rasWSBndy.tif', 'demad8.tif', '', 'value = 0')
    bndFacc = ExtractByMask("demad8.tif", "rasWSBndy")
    bndFacc.save("bndFAcc.tif")
    
    
    rmean = bndFacc.mean
    stddevX = bndFacc.standardDeviation * 3
    thrsh = int(rmean + stddevX)
    #arcpy.AddMessage(" Flow maximum: " + str(bndFacc.maximum))
    arcpy.AddMessage(" Flow threshhold: " + str(thrsh))

##                PourPts = Con(intD8Facc >= thrsh, intD8Facc)
    PourPts = Con(bndFacc >= thrsh, bndFacc)
    PourPts.save("PourPts.tif")
    
    arcpy.RasterToPoint_conversion(PourPts, "PourPts.shp", "VALUE")
    arcpy.AddField_management("PourPts.shp", "ID", "LONG")
    arcpy.CalculateField_management("PourPts.shp", "ID", '!POINTID!', "PYTHON_9.3")
    
##    arcpy.Delete_management("WSBndy_lyr.shp")
##    arcpy.Delete_management("WS_bnd.shp")
    arcpy.Delete_management("rasWSBndy.tif")



def mkPDougStrm(ProcDir):
    # PeukerDouglas
    # This produces a skeleton of a stream network derived entirely from a 
    #  local filter applied to the topograph

    arcpy.AddMessage("Peuker-Douglas")
    callstr = "mpiexec -n " + Ncpus + " PeukerDouglas " +\
              "-fel " + ProcDir + "\\demfel.tif " +\
              "-ss " + ProcDir + "\\demss.tif"
    subp = subprocess.check_output(callstr, stderr = subprocess.STDOUT)#, timeout = timeout)
    string = subp.decode(sys.stdout.encoding)
####    print(string)
    log.debug(string)
    # call(callstr, shell=True)
    arcpy.CalculateStatistics_management("demss.tif")
    
    
    # Area D8 
    #  check for contamination = false
    callstr = "mpiexec -n " + Ncpus + " Aread8 " +\
              "-p " + ProcDir + "\\demp.tif " +\
              "-o " + ProcDir + "\\PourPts.shp " +\
              "-ad8 " + ProcDir + "\\demssa.tif " +\
              "-wg " + ProcDir + "\\demss.tif -nc"
    subp = subprocess.check_output(callstr, stderr = subprocess.STDOUT)#, timeout = timeout)
    string = subp.decode(sys.stdout.encoding)
####    print(string)
    log.debug(string)
    # call(callstr, shell=True)
    arcpy.CalculateStatistics_management("demssa.tif")
    
    
    # Drop analysis
    callstr = "mpiexec -n " + Ncpus + " Dropanalysis " +\
              "-p " + ProcDir + "\\demp.tif " +\
              "-fel " + ProcDir + "\\demfel.tif " +\
              "-ad8 " + ProcDir + "\\demad8.tif " +\
              "-ssa " + ProcDir + "\\demssa.tif " +\
              "-drp " + ProcDir + "\\demdrp.txt " +\
              "-o " + ProcDir + "\\PourPts.shp -par 1000 2500 50 0"
              #"-o " + ProcDir + "\\PourPts.shp -par 300 10000 50 0"
    subp = subprocess.check_output(callstr, stderr = subprocess.STDOUT)#, timeout = timeout)
    string = subp.decode(sys.stdout.encoding)
####    print(string)
    log.debug(string)
    # call(callstr, shell=True)


    # Get the channel initiation threshold 
    chThresh = getThresh(ProcDir)


    # Creater channel raster by threshhold
    arcpy.AddMessage("  Source threshold: " + str(chThresh))
    
    callstr = "mpiexec -n " + Ncpus + " Threshold -ssa " + ProcDir + "\\demssa.tif -src " + ProcDir + "\\demsrc.tif -thresh " + str(chThresh)
    subp = subprocess.check_output(callstr, stderr = subprocess.STDOUT)#, timeout = timeout)
    string = subp.decode(sys.stdout.encoding)
####    print(string)
    log.debug(string)
    # call(callstr, shell=True)
    arcpy.CalculateStatistics_management("demsrc.tif")
    
    return(chThresh)
    
    
def getThresh(ProcDir):
    inf = open(ProcDir + "\\demdrp.txt")
    lineList = inf.readlines()
    last = lineList[len(lineList)-1].split(':')
    chThresh = int(float(last[1]))

    # if Optimum THreshold VAlue = 0.000, set to 1000, otherwise all will be channels
    # modified from 2500 to 1000 by Brian Gelder, bkgelder@iastate.edu
    if chThresh == 0:
        chThresh = 1000#2500
    
    return(chThresh)



def mkWSheds(ProcDir, sgdb, huc12, WSBndsrc, log, pdCatch, wShed):

    arcpy.AddMessage("Watersheds")
    
    callstr = "mpiexec -n " + Ncpus + " StreamNet " +\
              "-fel " + ProcDir + "\\demfel.tif " +\
              "-p " + ProcDir + "\\demp.tif " +\
              "-ad8 " + ProcDir + "\\demad8.tif " +\
              "-src " + ProcDir + "\\demsrc.tif " +\
              "-ord " + ProcDir + "\\demgord.tif " +\
              "-tree " + ProcDir + "\\demtree.dat " +\
              "-coord " + ProcDir + "\\demcoord.dat " +\
              "-net " + ProcDir + "\\tempnet.shp " +\
              "-w " + ProcDir + "\\demw.tif " +\
              "-o " + ProcDir + "\\PourPts.shp" 
    subp = subprocess.check_output(callstr, stderr = subprocess.STDOUT)#, timeout = timeout)
    string = subp.decode(sys.stdout.encoding)
####    print(string)
    log.debug(string)
    # call(callstr, shell=True)
    arcpy.CalculateStatistics_management("demw.tif")
    
    # Create subwatershed feature class - WSNO joins to channels
    tmpWshed = arcpy.RasterToPolygon_conversion(ProcDir + "\\demw.tif", os.path.join(sgdb, 'tmpwshd'))#"TMPwshd.shp")
    arcpy.RepairGeometry_management(tmpWshed)
    arcpy.AddField_management(tmpWshed, "WSNO", "LONG")
    arcpy.AddField_management(tmpWshed, "Acres", "LONG")
    arcpy.CalculateField_management(tmpWshed, "WSNO", '!GRIDCODE!', "PYTHON_9.3")
    arcpy.CalculateField_management(tmpWshed, "Acres", '!shape.area@ACRES!', "PYTHON_9.3")

    # remove raster2vector artifacts - those with '0' acres
    arcpy.MakeFeatureLayer_management(tmpWshed, "Area_lyr")
    arcpy.SelectLayerByAttribute_management("Area_lyr", "NEW_SELECTION", ' "Acres" = 0 ')
    arcpy.Eliminate_management("Area_lyr", "GT0_wshd.shp")
    
    # save only those features that have centroids in WBD-version of HUC12
    arcpy.MakeFeatureLayer_management("GT0_wshd.shp", "Inside_lyr")
    arcpy.SelectLayerByLocation_management("Inside_lyr", "HAVE_THEIR_CENTER_IN", WSBndsrc)#fileGDB + "\\bnd" + huc12)    
    arcpy.CopyFeatures_management("Inside_lyr", pdCatch)#fileGDB + "\\pdCatch" + huc12)

    # Create the watershed boundary
    try:
        wshed = arcpy.Dissolve_management(pdCatch, wShed, "", "", "SINGLE_PART")
        # wshed generated form dissovle, returns 0 features, huc12 102300030507
        if u'WARNING 000117: Warning empty output generated.' in wshed.getMessage(3):
            log.warning('ERROR -- Dissolve returned valid output with 0 features, attempting to handle with Repair Geometry')
            arcpy.RepairGeometry_management(pdCatch)
            wshed = arcpy.Dissolve_management(pdCatch, wShed, "", "", "SINGLE_PART")
            
    # wshed not generated from dissolve, huc12 102400090403
    except arcpy.ExecuteError:
        
        log.warning(arcpy.GetMessages())#(0))
        log.warning('\n')
##        print(arcpy.GetMessages(2))
##        print('\n')
        print('ERROR -- Dissolve failed, attempting to handle with Repair Geometry')
              
        arcpy.RepairGeometry_management(pdCatch)
        wshed = arcpy.Dissolve_management(pdCatch, wShed, "", "", "SINGLE_PART")
    except:
        # Get the traceback object
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]

        # Concatenate information together concerning the error into a message string
        pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])

        # Return python error messages for use in script tool or Python Window
        arcpy.AddError(pymsg)

        # Print Python error messages for use in Python / Python Window
        log.warning(pymsg + "\n")
        if arcpy.GetMessages(2) not in pymsg:
            msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"
            arcpy.AddError(msgs)
            log.warning(msgs)


    # now check to make sure that repair geometry fixed errors correctly, see error on huc12 070101060208
    wshedDesc = arcpy.Describe(wshed)
    wshedExt = wshedDesc.extent


    wsbndDesc = arcpy.Describe(WSBndsrc)
    wsbndExt = wsbndDesc.extent
    if wshedExt.polygon.area/wsbndExt.polygon.area < 0.9:
        log.warning('subcatchment watershed area too small compared to HUC12 watershed boundary')
        # try a different approach to create watersheds, use NO_SIMPLIFY option

        # copy old stuff for troublshooting?
        arcpy.CopyFeatures_management(tmpWshed, os.path.join(sgdb, 'tmpwshd_dslv_errors'))#"TMPwshd.shp", 'TMPwshd_dslv_errors.shp')
        arcpy.CopyFeatures_management(pdCatch, 'pdCatch_dslv_errors.shp')
        arcpy.CopyFeatures_management(wshed, os.path.join(sgdb, 'WShed' + huc12+ '_dslv_errors'))
        

        # Create subwatershed feature class - WSNO joins to channels
        rtp = arcpy.RasterToPolygon_conversion(ProcDir + "\\demw.tif", tmpWshed, 'NO_SIMPLIFY')#"TMPwshd.shp", 'NO_SIMPLIFY')
        arcpy.AddField_management(rtp, "WSNO", "LONG")
        arcpy.AddField_management(rtp, "Acres", "LONG")
        arcpy.CalculateField_management(rtp, "WSNO", '!GRIDCODE!', "PYTHON_9.3")
        arcpy.CalculateField_management(rtp, "Acres", '!shape.area@ACRES!', "PYTHON_9.3")

        # remove raster2vector artifacts - those with '0' acres
        areaLayer = arcpy.MakeFeatureLayer_management(rtp, "Area_lyr")
        arcpy.SelectLayerByAttribute_management(areaLayer, "NEW_SELECTION", ' "Acres" = 0 ')
        elimWs = arcpy.Eliminate_management(areaLayer, "GT0_wshd.shp")
        
        # save only those features that have centroids in WBD-version of HUC12
        insideLayer = arcpy.MakeFeatureLayer_management(elimWs, "Inside_lyr")
        arcpy.SelectLayerByLocation_management(insideLayer, "HAVE_THEIR_CENTER_IN", WSBndsrc)
        arcpy.CopyFeatures_management(insideLayer, pdCatch)

    # Create the watershed boundary
    try:
        wshed = arcpy.Dissolve_management(pdCatch, wShed, "", "", "SINGLE_PART")
        # wshed generated form dissovle, returns 0 features, huc12 102300030507
        if u'WARNING 000117: Warning empty output generated.' in wshed.getMessage(3):
            log.warning('ERROR -- Dissolve returned valid output with 0 features, attempting to handle with Repair Geometry')
            arcpy.RepairGeometry_management(pdCatch)
            wshed = arcpy.Dissolve_management(pdCatch, wShed, "", "", "SINGLE_PART")
            
    # wshed not generated from dissolve, huc12 102400090403
    except arcpy.ExecuteError:
        
        log.warning(arcpy.GetMessages())#(0))
        log.warning('\n')
##        print(arcpy.GetMessages(2))
##        print('\n')
        log.warning('ERROR -- Dissolve failed, attempting to handle with Repair Geometry')
              
        arcpy.RepairGeometry_management(pdCatch)
        wshed = arcpy.Dissolve_management(pdCatch, wShed, "", "", "SINGLE_PART")
    except:
        # Get the traceback object
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]

        # Concatenate information together concerning the error into a message string
        pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])

        # Return python error messages for use in script tool or Python Window
        arcpy.AddError(pymsg)

        # Print Python error messages for use in Python / Python Window
        log.warning(pymsg + "\n")
        if arcpy.GetMessages(2) not in pymsg:
            msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"
            arcpy.AddError(msgs)
            log.warning(msgs)


    
    # Select only those links in the TauDEM stream network shapefile that are in the wastershed
    #  then copy to a fileGeoDatabase and back to resolve drawing issues that are undefined.
    arcpy.MakeFeatureLayer_management("tempnet.shp", "allChannels_lyr")
    arcpy.SelectLayerByLocation_management("allChannels_lyr", "HAVE_THEIR_CENTER_IN", wshed)#fileGDB + "\\WShed" + huc12)
    
    demnet = arcpy.CopyFeatures_management("allChannels_lyr", sgdb + "\\demnet")
    arcpy.CopyFeatures_management(demnet, pdChnl)
    arcpy.DefineProjection_management(pdChnl, pdCatch)#, fileGDB + "\\pdCatch" + huc12)

    # Do some clean up
    #arcpy.Delete_management("tempnet.shp")
    #arcpy.Delete_management(sgdb + "\\demnet")
##    arcpy.Delete_management("allChannels_lyr")
##    
##    arcpy.Delete_management("Area_lyr")
##    arcpy.Delete_management("Inside_lyr")
##    arcpy.Delete_management("TMPwshd.shp")
##    arcpy.Delete_management("GT0_wshd.shp")

##------------------------------------------------------------------------------
##------------------------------------------------------------------------------
if __name__ == "__main__":

    if len(sys.argv) == 1:
        arcpy.AddMessage("Whoo, hoo! Running from Python Window!")
        cleanup = False

    outputString = 'system arguments are ' + str(sys.argv) + '\n'

    if len(sys.argv) == 1:
        cleanup = False
        parameters = ["C:/Program Files/ArcGIS/Pro/bin/Python/envs/arcgispro-py3/pythonw.exe",
	"C:/DEP/Scripts/basics/cmd_channel_py2_DEP.py",
	"C:/DEP/LiDAR_Current/elev_CLib_mean18/07080105/ec3m070801050901.tif",
	"C:/DEP_Proc/DEMProc/Catch_dem2013_3m_070801050901",
	"C:/DEP/Basedata_Summaries/Basedata_5070.gdb/MW_HUC12_v2022_Status_mean18",
	"C:/DEP/Man_Data_ACPF/dep_ACPF2022/07080105/idepACPF070801050901.gdb/bnd070801050901",
	"C:/DEP/Man_Data_ACPF/dep_ACPF2022/07080105/idepACPF070801050901.gdb/pdCatch_mean18_dem2013_3m_070801050901",
	"C:/DEP/Man_Data_ACPF/dep_ACPF2022/07080105/idepACPF070801050901.gdb/pdChnl_mean18_dem2013_3m_070801050901",
	"C:/DEP/Man_Data_ACPF/dep_ACPF2022/07080105/idepACPF070801050901.gdb/WShed_mean18_dem2013_3m_070801050901"]

        for i in parameters[2:]:
            sys.argv.append(i)

        outputString += 'running via shell'#; parameters were: ' + str(parameters)

    else:
        cleanup = True
        outputString += 'parameters were passed in via command line'

    try:
        inDEM, ProcDir, statGDB, ws_bnd, pdCatch, pdChnl, wShed  = [i for i in sys.argv[1:]]
        # fileGDB = os.path.dirname(pdCatch)#sys.argv[3]

        huc12, huc8 = df.figureItOut(inDEM)

        if cleanup:
            # log to file only
            log, nowYmd, logName, startTime = df.setupLoggingNoCh(platform.node(), sys.argv[0], huc12)
        else:
            # log to file and console
            log, nowYmd, logName, startTime = df.setupLoggingNew(platform.node(), sys.argv[0], huc12)

        log.info('Peukering on ' + huc12)

        if os.path.isdir(ProcDir):
            df.nukedir(ProcDir)
        if not os.path.isdir(ProcDir):
            os.makedirs(ProcDir)

        # copy the HUC12 WS boundary into the ACPF GDB
        # WSBndsrc = arcpy.Select_analysis(statGDB, os.path.join(fileGDB, 'bnd' + huc12), "\"HUC12\" = \'" + str(huc12) + "\'")

        arcpy.env.extent = inDEM
        arcpy.env.snapRaster = inDEM
        arcpy.env.cellSize = inDEM
        arcpy.env.outputCoordinateSystem = inDEM

        Ncpus = str(int(os.environ["NUMBER_OF_PROCESSORS"]) // 2)

        arcpy.env.workspace = ProcDir
        
        arcpy.env.scratchWorkspace = ProcDir
        sgdb = arcpy.env.scratchGDB

        # Heavy lifting
        outFill = Fill(inDEM)
        outFillCopy = arcpy.CopyRaster_management(outFill, "demfel.tif")

        FlowD8(outFillCopy, ProcDir)

        extractPoutPts(ws_bnd)#fileGDB, huc12, WSBndsrc)

        chThresh = mkPDougStrm(ProcDir)

        mkWSheds(ProcDir, sgdb, huc12, ws_bnd, log, pdCatch, wShed)#, WSBndsrc, log, pdCatch, wShed)
                       
        # Keep track of the threshhold
        cursor = arcpy.da.UpdateCursor(statGDB, ["ChannelThreshold"], "\"HUC12\" = \'" + str(huc12) + "\'")
        for row in cursor:
            row[0] = chThresh
            cursor.updateRow(row)
        del row
        del cursor
    except:
        # Get the traceback object
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]

        # Concatenate information together concerning the error into a message string
        pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
        msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"

        # Return python error messages for use in script tool or Python Window
        arcpy.AddError(pymsg)
        arcpy.AddError(msgs)

        # Print Python error messages for use in Python / Python Window
        log.warning(pymsg + "\n")
        log.warning(msgs)

    finally:
        log.info("Ending script execution")
