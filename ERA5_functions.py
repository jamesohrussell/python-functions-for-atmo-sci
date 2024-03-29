#==================================================================
# Functions for reading ERA5 in Python
# Author: James Russell 2020
#
#==================================================================
#
# * get_E5_subset_2D
#   - Gets a 2D subset of ERA5 data given central times, 
#      lats, and lons, for a specified variable. Uses all the
#      below functions.
#
# * get_E5_subset_file
#   - Given a time, finds the ERA5 file that is relevant, and
#      outputs the indices corresponding to the closest time 
#      coordinate within that file
#
# * get_E5_subset_2D_coords
#   - Gets the lat and lon indices and the coordinates within
#      a certain area surrounding a central lon and lat
#
# * get_E5_subset_2D_var
#   - Gets a subset of a specific ERA5 variable corresponding
#      to the time, latitude, and longitude coordinates provided
#
#==================================================================
#
# * get_E5_subset_4D
#   - Gets a 4D subset of ERA5 data given times, levels,
#      lats, and lons, for a specified variable. Combines the
#      below functions into one higher level function.
#
# * get_E5_subset_4D_fiti
#   - Given two times, finds the ERA5 files that are relevant,
#      outputs the indices corresponding to the times in the first
#      files, and outputs a list of all relevant times.
#
# * get_E5_subset_4D_coords
#   - Gets the lat and lon indices and lists of the lat and lon
#      coordinates.
#
# * get_E5_subset_4D_levels
#   - Gets the level indices and a list of the levels.
#
# * get_E5_subset_4D_var
#   - Gets a subset of a specific ERA5 variable corresponding
#      to the time, level, latitude, and longitude coordinates
#      provided.
#
#==================================================================

# Import libraries
import numpy as np
import glob
from netCDF4 import Dataset
import time_functions as tfns
import misc_functions as mfns
from scipy.interpolate import interp1d

#==================================================================
# Get subset of a variable from ERA5 files
#==================================================================

def get_E5_ss_4D(datadir,fileid,varname,timestr1,timestr2,
                 lev1,lev2,lat1,lat2,lon1,lon2):
  """
  Get a 4D subset of ERA5 data.

  Input: 
   1,2) Data directory and file identifier
   3) Variable name as in ERA5 files
   4,5) Two strings for the first and last times bounding the 
    data: YYYY-MM-DD hh format
   6,7,8,9,10,11) Ascending order first and last levels, lats, 
    and lons 

  Output:
   1) A 4D array of the variable requested
   2,3,4,5) Lists of the time, level, lat, and lon coords

  Requires 
  """

  # Get files, times, and time indices for first and last file
  files,timi,times = get_E5_ss_4D_fiti(datadir,fileid,
                                        timestr1,timestr2)

  # Read first file and get lats, lons, and their indices 
  fh = Dataset(files[0])
  lati,loni,lats,lons = get_E5_ss_4D_coords(fh,lat1,lat2,
   lon1,lon2)

  # Get levels and their indices 
  levi,levs = get_E5_ss_4D_levels(fh,lev1,lev2)

  # Get the variable 
  var = get_E5_ss_4D_var(files,varname,timi,levi,lati,loni)
  
  # Output the variable and its coordinates
  return(var,times,levs,lats,lons)



#==================================================================
# Get subset of a variable from ERA5 files
#==================================================================

def get_E5_ss_4D_fiti(datadir,fileid,timestr1,timestr2):
  """
  Find all files with data between two times and output the 
   indices of the times within the first and last files

  Input: 
   1,2) Data directory and file identifier
   3,4) Strings indicating the first and last times in format:
       YYYY-MM-DD hh

  Output:
   1) A list of strings indicating the paths and files
   2,3) Either a scalar or list of indices indicating the time 
    index(es) within that file corresponding to either the first
    or last times

  Requires glob and netCDF4
  """

  # Find all files 
  allfiles = sorted(glob.glob(datadir+fileid+"*"))

  # Convert first and last time to same units
  ds0 = Dataset(allfiles[0])
  time1 = tfns.time_since(timestr1+":00:00",
                         ds0.variables["time"].units)
  time2 = tfns.time_since(timestr2+":00:00",
                         ds0.variables["time"].units)

  # Loop over all files and initialize variables
  append = False
  ssfiles = []
  for fi in allfiles:
    fh = Dataset(fi)

    print(fi)

    # Read the times
    times1 = list(fh.variables["time"][:])
    
    # If first and second time is within current file
    if times1[0]<=time1<=times1[-1] and \
       times1[0]<=time2<=times1[-1]:

      print("First and last file")

      # Select the indexes of the relevant times
      timi1 = mfns.k_closest(times1,time1,1)[0]
      timi2 = mfns.k_closest(times1,time2,1)[0]

      # Get times and append file to filenames
      times = times1[timi1:timi2+1]
      ssfiles.append(fi)

      # Break the loop
      break

    # If first time only is within current file
    if times1[0]<=time1<=times1[-1] and not \
       times1[0]<=time2<=times1[-1]:

      print("First file only")

      # Select the index of the relevant time
      timi1 = mfns.k_closest(times1,time1,1)[0]

      # Get times and append file to filenames
      times = times1[timi1:]
      ssfiles.append(fi)

      # Move on to next file
      append=True
      continue

    # If last time is within current file
    if times1[0]<=time2<=times1[-1]:

      print("Last file")
    
      # Select the index of the relevant time
      timi2 = mfns.k_closest(times1,time2,1)[0]

      # Get times
      times.extend(times1[0:timi2+1])
      ssfiles.append(fi)

      # Break the loop
      break

    # Middle times
    if append:

      print("Middle file")
      times.extend(times1)
      ssfiles.append(fi)

  # Make time indices a list
  timi = np.squeeze([timi1,timi2])

  # Return data
  return(ssfiles,timi,times)

#==================================================================
# Get subset of a variable from ERA5 files
#==================================================================

def get_E5_ss_4D_coords(fh,lat1,lat2,lon1,lon2):
  """
  Find the horizontal coordinates and indices for a subset of 
   ERA5 data

  Input: 
   1) A handle for the datafile
   2,3,4,5) The min and max longitudes and latitudes for the subset

  Output:
   1,2) Indices for the longitude and latitude coordinates
   3,4) Lists of the longitude and latitude coordinates 

  Requires numpy 1.16.3 (conda install -c anaconda numpy; 
   https://pypi.org/project/numpy/)
  """

  # Find lat and lon indices
  if lon1<0: lon1 = lon1+360
  if lon2<0: lon2 = lon2+360
  lat = fh.variables["latitude"][:]
  lon = fh.variables["longitude"][:]
  lati  = np.squeeze([mfns.k_closest(lat,lat2,1), 
                      mfns.k_closest(lat,lat1,1)])
  loni  = np.squeeze([mfns.k_closest(lon,lon1,1),
                      mfns.k_closest(lon,lon2,1)])

  # Get coordinates of that subset
  if loni[0]<loni[1]:
    lats = np.squeeze(list(
     fh.variables["latitude"][lati[0]:lati[1]+1]))
    lons = np.squeeze(list(
     fh.variables["longitude"][loni[0]:loni[1]+1]))

  if loni[0]>loni[1]:
    lats = list(fh.variables["latitude"][lati[0]:lati[1]+1])
    lons1 = []
    for l in fh.variables["longitude"][loni[0]:]:
      if l<180:
        lons1.extend([l])
      else:
        lons1.extend([l-360])
    lons2 = list(fh.variables["longitude"][0:loni[1]+1])
    lons = lons1+lons2

  # Return data
  return(lati,loni,lats,lons)



#==================================================================
# Get subset of a variable from ERA5 files
#==================================================================

def get_E5_ss_4D_levels(fh,lev1,lev2):
  """
  Find the vertical coordinates and indices for a subset of 
   ERA5 data

  Input: 
   1) A handle for the datafile
   2,3) The min and max levels

  Output:
   1) Indices for the levels
   2) A list of the levels

  Requires numpy 1.16.3 (conda install -c anaconda numpy; 
   https://pypi.org/project/numpy/)
  """

  # Find lat and lon indices
  lev  = fh.variables["level"][:]
  levi = np.squeeze([mfns.k_closest(lev,lev1,1), 
                     mfns.k_closest(lev,lev2,1)])

  # Get coordinates of that subset
  levs = np.squeeze(list(
   fh.variables["level"][levi[0]:levi[1]+1]))

  # Return data
  return(levi,levs)



#==================================================================
# Get subset of a variable from ERA5 files
#==================================================================

def get_E5_ss_4D_2levels(fh,lev1,lev2):
  """
  Find the vertical coordinates and indices for a subset of 
   ERA5 data

  Input: 
   1) A handle for the datafile
   2,3) The min and max levels

  Output:
   1) Indices for the levels
   2) A list of the levels

  Requires numpy 1.16.3 (conda install -c anaconda numpy; 
   https://pypi.org/project/numpy/)
  """

  # Find lat and lon indices
  lev  = fh.variables["level"][:]
  levi = np.squeeze([mfns.k_closest(lev,lev1,1),
                     mfns.k_closest(lev,lev2,1)])

  # Return data
  return(levi)



#==================================================================
# Get subset of a variable from ERA5 files
#==================================================================

def get_E5_ss_4D_var(files,varname,timi,levi,lati,loni):
  """
  Get a 4D subset of ERA5 data.

  Input: 
   1) A list of files to read
   2) A string of the variable name in ERA5 e.g."CAPE"
   3) The indices corresponding to time
   4,5,6) The indices corresponding to first and last levels,
    longitudes, and latitudes

  Output:
   1) Returns a flattened list of the ERA5 variable corresponding 
    to coordinates from get_E5_subset_2D_coords

  Requires numpy 1.16.3 (conda install -c anaconda numpy; 
   https://pypi.org/project/numpy/)
  """

  # Loop over all files and open the current file
  c = 0
  for fi in files:
    fh = Dataset(fi)
    print("Working on file: "+str(fi))

    # At first time
    if c==0:

      # Read in subset of data (not over Greenwich Meridian)
      if loni[0]<loni[1]:
        varss = np.array(fh.variables[varname][timi[0]:,
         levi[0]:levi[1],lati[0]:lati[1]+1,loni[0]:loni[1]+1])

      # Read in subset of data (over Greenwich Meridian)
      # and concatenate data in longitude
      elif loni[0]>loni[1]:
        varss1  = np.array(fh.variables[varname][timi[0]:,
         levi[0]:levi[1],lati[0]:lati[1]+1,loni[0]:])
        varss2  = np.array(fh.variables[varname][timi[0]:,
         levi[0]:levi[1],lati[0]:lati[1]+1,0:loni[1]+1])
        varss = np.concatenate((varss1,varss2),axis=3)

    # At last time
    elif c==len(files)-1:
    
      # Read in subset of data (not over Greenwich Meridian)
      if loni[0]<loni[1]:
        varss3  = np.array(fh.variables[varname][0:timi[1]+1,
         levi[0]:levi[1],lati[0]:lati[1]+1,loni[0]:loni[1]+1])

      # Read in subset of data (over Greenwich Meridian)
      # and concatenate data in longitude
      elif loni[0]>loni[1]:
        varss1  = np.array(fh.variables[varname][0:timi[1]+1,
         levi[0]:levi[1],lati[0]:lati[1]+1,loni[0]:])
        varss2  = np.array(fh.variables[varname][0:timi[1]+1,
         levi[0]:levi[1],lati[0]:lati[1]+1,0:loni[1]+1])
        varss3 = np.concatenate((varss1,varss2),axis=3)

      # Concatenate data in time
      varss = np.concatenate((varss,varss3),axis=0)

    # Middle times
    else:

      # Read in subset of data (not over Greenwich Meridian)
      if loni[0]<loni[1]:
        varss3  = np.array(fh.variables[varname][:,
         levi[0]:levi[1],lati[0]:lati[1]+1,loni[0]:loni[1]+1])

      # Read in subset of data (over Greenwich Meridian)
      # and concatenate data in longitude
      elif loni[0]>loni[1]:
        varss1  = np.array(fh.variables[varname][:,
         levi[0]:levi[1],lati[0]:lati[1]+1,loni[0]:])
        varss2  = np.array(fh.variables[varname][:,
         levi[0]:levi[1],lati[0]:lati[1]+1,0:loni[1]+1])
        varss3 = np.concatenate((varss1,varss2),axis=3)

      # Concatenate data in time
      varss = np.squeeze(np.concatenate((varss,varss3),axis=0))

    # Advance counter
    c+=1

  # Return data
  return(varss)


#==================================================================
# Get subset of a variable from ERA5 files
#==================================================================

def get_E5_ss_4D_levavgvar(files,varname,timi,levi,lati,loni):
  """
  Get a 4D subset of ERA5 data.

  Input: 
   1) A list of files to read
   2) A string of the variable name in ERA5 e.g."CAPE"
   3) The indices corresponding to time
   4,5,6) The indices corresponding to first and last levels,
    longitudes, and latitudes

  Output:
   1) Returns a flattened list of the ERA5 variable corresponding 
    to coordinates from get_E5_subset_2D_coords

  Requires numpy 1.16.3 (conda install -c anaconda numpy; 
   https://pypi.org/project/numpy/)
  """

  # Loop over all files and open the current file
  c = 0
  for fi in files:
    fh = Dataset(fi)
    print("Working on file: "+str(fi))

    # At first time
    if c==0:

      # Read in subset of data (not over Greenwich Meridian)
      if loni[0]<loni[1]:
        varss = np.mean(fh.variables[varname][timi[0]:,
         levi[0]:levi[1],lati[0]:lati[1]+1,loni[0]:loni[1]+1],
         axis=1)

      # Read in subset of data (over Greenwich Meridian)
      # and concatenate data in longitude
      elif loni[0]>loni[1]:
        varss1  = np.mean(
         fh.variables[varname][timi[0]:,levi[0]:levi[1],
         lati[0]:lati[1]+1,loni[0]:],axis=1)
        varss2  = np.mean(
         fh.variables[varname][timi[0]:,levi[0]:levi[1],
         lati[0]:lati[1]+1,0:loni[1]+1],axis=1)
        varss = np.concatenate((varss1,varss2),axis=2)

    # At last time
    elif c==len(files)-1:
    
      # Read in subset of data (not over Greenwich Meridian)
      if loni[0]<loni[1]:
        varss3  = np.mean(
         fh.variables[varname][0:timi[1]+1,levi[0]:levi[1],
         lati[0]:lati[1]+1,loni[0]:loni[1]+1],axis=1)

      # Read in subset of data (over Greenwich Meridian)
      # and concatenate data in longitude
      elif loni[0]>loni[1]:
        varss1  = np.mean(
         fh.variables[varname][0:timi[1]+1,levi[0]:levi[1],
         lati[0]:lati[1]+1,loni[0]:],axis=1)
        varss2  = np.mean(
         fh.variables[varname][0:timi[1]+1,levi[0]:levi[1],
         lati[0]:lati[1]+1,0:loni[1]+1],axis=1)
        varss3 = np.concatenate((varss1,varss2),axis=2)

      # Concatenate data in time
      varss = np.concatenate((varss,varss3),axis=0)

    # Middle times
    else:

      # Read in subset of data (not over Greenwich Meridian)
      if loni[0]<loni[1]:
        varss3  = np.mean(fh.variables[varname][:,levi[0]:levi[1],
         lati[0]:lati[1]+1,loni[0]:loni[1]+1],axis=1)

      # Read in subset of data (over Greenwich Meridian)
      # and concatenate data in longitude
      elif loni[0]>loni[1]:
        varss1  = np.mean(fh.variables[varname][:,
         levi[0]:levi[1],lati[0]:lati[1]+1,loni[0]:],axis=1)
        varss2  = np.mean(fh.variables[varname][:,
         levi[0]:levi[1],lati[0]:lati[1]+1,0:loni[1]+1],axis=1)
        varss3 = np.concatenate((varss1,varss2),axis=2)

      # Concatenate data in time
      varss = np.squeeze(np.concatenate((varss,varss3),axis=0))

    # Advance counter
    c+=1

  # Return data
  return(varss)

#==================================================================
# Get subset of a variable from ERA5 files
#==================================================================

def get_E5_ss_4D_levdiffvar(files,varname,timi,levi,lati,loni):
  """
  Get a 4D subset of ERA5 data.

  Input: 
   1) A list of files to read
   2) A string of the variable name in ERA5 e.g."CAPE"
   3) The indices corresponding to time
   4,5,6) The indices corresponding to first and last levels,
    longitudes, and latitudes

  Output:
   1) Returns a flattened list of the ERA5 variable corresponding 
    to coordinates from get_E5_subset_2D_coords

  Requires numpy 1.16.3 (conda install -c anaconda numpy; 
   https://pypi.org/project/numpy/)
  """

  # Loop over all files and open the current file
  c = 0
  for fi in files:
    fh = Dataset(fi)
    print("Working on file: "+str(fi))

    # At first time
    if c==0:

      # Read in subset of data (not over Greenwich Meridian)
      if loni[0]<loni[1]:
        varss = fh.variables[varname][timi[0]:,levi[0],
         lati[0]:lati[1]+1,loni[0]:loni[1]+1] - \
         fh.variables[varname][timi[0]:,levi[1],
         lati[0]:lati[1]+1,loni[0]:loni[1]+1]

      # Read in subset of data (over Greenwich Meridian)
      # and concatenate data in longitude
      elif loni[0]>loni[1]:
        varss1  = fh.variables[varname][timi[0]:,levi[0],
         lati[0]:lati[1]+1,loni[0]:] - \
         fh.variables[varname][timi[0]:,levi[1],
         lati[0]:lati[1]+1,loni[0]:]
        varss2  = fh.variables[varname][timi[0]:,levi[0],
         lati[0]:lati[1]+1,0:loni[1]+1] - \
         fh.variables[varname][timi[0]:,levi[1],
         lati[0]:lati[1]+1,0:loni[1]+1]
        varss = np.concatenate((varss1,varss2),axis=2)

    # At last time
    elif c==len(files)-1:
    
      # Read in subset of data (not over Greenwich Meridian)
      if loni[0]<loni[1]:
        varss3  = fh.variables[varname][0:timi[1]+1,levi[0],
         lati[0]:lati[1]+1,loni[0]:loni[1]+1] - \
         fh.variables[varname][0:timi[1]+1,levi[1],
         lati[0]:lati[1]+1,loni[0]:loni[1]+1]

      # Read in subset of data (over Greenwich Meridian)
      # and concatenate data in longitude
      elif loni[0]>loni[1]:
        varss1  = fh.variables[varname][0:timi[1]+1,levi[0],
         lati[0]:lati[1]+1,loni[0]:] - \
         fh.variables[varname][0:timi[1]+1,levi[1],
         lati[0]:lati[1]+1,loni[0]:]
        varss2  = fh.variables[varname][0:timi[1]+1,levi[0],
         lati[0]:lati[1]+1,0:loni[1]+1] - \
         fh.variables[varname][0:timi[1]+1,levi[1],
         lati[0]:lati[1]+1,0:loni[1]+1]
        varss3 = np.concatenate((varss1,varss2),axis=2)

      # Concatenate data in time
      varss = np.concatenate((varss,varss3),axis=0)

    # Middle times
    else:

      # Read in subset of data (not over Greenwich Meridian)
      if loni[0]<loni[1]:
        varss3  = fh.variables[varname][:,levi[0],
         lati[0]:lati[1]+1,loni[0]:loni[1]+1] - \
         fh.variables[varname][:,levi[1],
         lati[0]:lati[1]+1,loni[0]:loni[1]+1]

      # Read in subset of data (over Greenwich Meridian)
      # and concatenate data in longitude
      elif loni[0]>loni[1]:
        varss1  = fh.variables[varname][:,levi[0],
         lati[0]:lati[1]+1,loni[0]:] - \
         fh.variables[varname][:,levi[1],
         lati[0]:lati[1]+1,loni[0]:]
        varss2  = fh.variables[varname][:,levi[0],
         lati[0]:lati[1]+1,0:loni[1]+1] - \
         fh.variables[varname][:,levi[1],
         lati[0]:lati[1]+1,0:loni[1]+1]
        varss3 = np.concatenate((varss1,varss2),axis=2)

      # Concatenate data in time
      varss = np.squeeze(np.concatenate((varss,varss3),axis=0))

    # Advance counter
    c+=1

  # Return data
  return(varss)


#==================================================================
# Get subset of a variable from ERA5 files
#==================================================================

def get_E5_ss_files(dirfileid,timestr1,timestr2):
  """
  Find all files with data between two times and output the 
   indices of the times within the first and last files

  Input: 
   1,2) Data directory and file identifier
   3,4) Strings indicating the first and last times in format:
       YYYY-MM-DD hh

  Output:
   1) A list of strings indicating the paths and files
   2,3) Either a scalar or list of indices indicating the time 
    index(es) within that file corresponding to either the first
    or last times

  Requires glob and netCDF4
  """

  # Find all files 
  allfiles = sorted(glob.glob(f'{dirfileid}*'))

  # Convert first and last time to same units
  ds0 = Dataset(allfiles[0])
  time1 = tfns.time_since(timestr1+":00:00",
                         ds0.variables["time"].units)
  time2 = tfns.time_since(timestr2+":00:00",
                         ds0.variables["time"].units)

  # Initialize variables
  append = False
  ssfiles = []

  # Loop over all files
  ifi=0
  for fi in allfiles:

    # Open current file and read times in files
    fh = Dataset(fi)
    times1 = list(fh.variables["time"][:])

    # If missing data
    if ifi==0 and times1[0]>time1:
      ssfiles.append(fi)
      raise ValueError("Data is unavailable")
    
    # If first and second time within current file
    if times1[0]<=time1<=times1[-1] and \
       times1[0]<=time2<=times1[-1]:
      ssfiles.append(fi)
      break

    # If first time only is within current file
    if times1[0]<=time1<=times1[-1] and not \
       times1[0]<=time2<=times1[-1]:
      ssfiles.append(fi)

      # Set current as previous file
      pfh = fh
      pfi = fi
      ptimes1 = times1
      ifi=ifi+1

      # Move on to next file
      append=True
      continue

    # If first and second time between current and past files
    if ifi>0 and \
      (ptimes1[-1]<time1<times1[0] and \
       ptimes1[-1]<time2<times1[0]):
      ssfiles.append(pfi)
      ssfiles.append(fi)
      break

    # If first time between current and past files 
    # and second is not
    if ifi>0 and \
      (ptimes1[-1]<time1<times1[0] and not\
       ptimes1[-1]<time2<times1[0]):
      ssfiles.append(pfi)

      # Set current as previous file
      pfh = fh
      pfi = fi
      ptimes1 = times1
      ifi=ifi+1

      # Move on to next file
      append=True

    # If last time between current and past files
    if ifi>0 and ptimes1[-1]<time2<times1[0]:
      ssfiles.append(fi)
      break

    # If last time is within current file
    if times1[0]<=time2<=times1[-1]:
      ssfiles.append(fi)
      break

    # Middle times
    if append:

      print("Middle file")
      ssfiles.append(fi)

    # Set current as previous file
    pfh = fh
    pfi = fi
    ptimes1 = times1
    ifi=ifi+1

  # Return data
  return(ssfiles)

#==================================================================
# Get subset of a variable from ERA5 files
#==================================================================

def get_E5_ss_fiti(allfiles,timestr):
  """
  Find the file and output the time indices given a time

  Input: 
   1) A set of paths indicating the files to search
   2) A string indicating the current time in format:
       yyyy-mm-dd HH:MM:SS

  Output:
   1) A handle for the datafile
   2) Indices for the time coordinates
   3) A list of the times from the file
   4) The time to interpolate to, converted to ERA5 time units

  Requires 
  """

  # Select which file the time is within
  ds0 = Dataset(allfiles[0])
  ctime = tfns.time_since(timestr,ds0.variables["time"].units)
  for fi in allfiles:
    fh = Dataset(fi)
    if fh.variables["time"][0]<=ctime<=fh.variables["time"][-1]:
      break

  # Select the index(es) of the relevant time(s) 
  times = list(fh.variables["time"][:])
  if ctime in times:
    timi = times.index(ctime)
  else:
    timi = mfns.k_closest(times,ctime,2)

  return(fh,timi,times,ctime)

#==================================================================
# Get subset of a variable from ERA5 files
#==================================================================

def get_E5_ss_coords(fh,clon,clat,hda):
  """
  Find the horizontal coordinates and indices for a subset of 
   ERA5 data

  Input: 
   1) A handle for the datafile
   2,3) Th
   1,2) Indices for the longitude and latitude coordinatese central longitude and latitude for the subset
   4) Half the size of the subset in degrees (i.e. for a 10x10 
       degree subset hda==5)

  Output:
   3,4) Flattened lists of the longitude and latitude coordinates 

  Requires numpy 1.16.3 (conda install -c anaconda numpy; 
   https://pypi.org/project/numpy/)
  """

  # Find lat and lon indices
  if clon<0: clon = clon+360
  lat = fh.variables["latitude"][:]
  lon = fh.variables["longitude"][:]

  # Set lat and lon ranges
  clatp = clat+hda
  if clatp>90: clatp = 90
  clatm = clat-hda
  if clatm<-90: clatm = -90
  clonp = clon+hda
  if clonp>360: clonp = clonp-360
  clonm = clon-hda
  if clonm<0: clonm = clonm+360

  # Find indices
  lati  = np.squeeze([mfns.k_closest(lat,clatp,1), 
                      mfns.k_closest(lat,clatm,1)])
  loni  = np.squeeze([mfns.k_closest(lon,clonm,1),
                      mfns.k_closest(lon,clonp,1)])
  
  # Return data
  return(loni,lati)

#==================================================================
# Get subset of a variable from ERA5 files
#==================================================================

def get_E5_subset_2D(datadir,fileid,varname,timestr,clon,clat,hda):
  """
  Get a 3D subset of ERA5 data.

  Input: 
   1,2) Data directory anhd filename identifier
   3) A string of the variable name in ERA5 e.g."CAPE"
   4) A string indicating the current time in format:
       yyyy-mm-dd HH:MM:SS
   5,6) The central longitude and latitude for the subset
   7) Half the size of the subset in degrees (i.e. for a 10x10 
       degree subset hda==5)

  Output:
   1,2,3) Returns flattened lists of the ERA5 variable, and it's
           corresponding longitude and latitude coordinates
   

  Requires numpy 1.16.3 (conda install -c anaconda numpy; 
   https://pypi.org/project/numpy/), scipy 1.2.1 (conda install 
   -c anaconda scipy; https://pypi.org/project/scipy/)
  """

  # Get the file handle and time coordinates
  fh,timi,times,ctime = get_E5_ss_file(
   datadir,fileid,timestr)

  # Find lat and lon coordinates and incices
  loni,lati,lonE5,latE5 = get_E5_ss_3D_coords(
   fh,clon,clat,hda)

  # Read in subset of specific variable
  varE5 = get_E5_ss_3D_var(
   fh,varname,timi,loni,lati,times,ctime)

  # Return data
  return(varE5,lonE5,latE5)



#==================================================================
# Get subset of a variable from ERA5 files
#==================================================================

def get_E5_ss_2D_fiti(allfiles,timestr):
  """
  Find the file and output the time indices given a time

  Input: 
   1,2) Data directory anhd filename identifier
   3) A string indicating the current time in format:
       yyyy-mm-dd HH:MM:SS

  Output:
   1) A handle for the datafile
   2) Indices for the time coordinates
   3) A list of the times from the file
   4) The time to interpolate to, converted to ERA5 time units

  Requires 
  """

  # Convert ctime to units in files
  ds0 = Dataset(allfiles[0])
  ctime = tfns.time_since(timestr,ds0.variables["time"].units)

  # Select which file the time is within
  it = 0
  for fi in allfiles:

    # Open file
    fh = Dataset(fi)

    # At first file, check if time before first time
    if (ctime<fh.variables["time"][0] and it==0):

      # Throw error explaining
      raise ValueError("Time is before range of times in files")

    # At last file, check if time after last time
    elif (ctime>fh.variables["time"][-1] and it==len(allfiles)-1):

      # Throw error explaining
      raise ValueError("Time is after range of times in files")

    # Check if time is within current file
    elif fh.variables["time"][0]<=ctime<=fh.variables["time"][-1]:

      # Make list with the current file handle and break loop
      files = [fh]
      break

    # Check if time is after last time in previous file but 
    #  before first time in current file
    elif ("ltinpf" in locals()) and \
         (ltinpf<=ctime<=fh.variables["time"][0]):

      # Make list with previous and current file handle 
      #  and break loop
      files = [pf,fh]
      break

    # Set last time in current file for next iteration
    else:
      ltinpf = fh.variables["time"][-1]
      pf = fh

    # Update counter
    it=it+1

  # Select the index(es) of the relevant time(s)

  # If in the middle of a single file
  if len(files)==1:
    times = list(files[0].variables["time"][:])

    # If at exact time set time index and get time
    if ctime in times:
      timi = [times.index(ctime)]
      times = times[timi[0]]
    # If between two times, set index of and get two closest times
    else:
      timi = mfns.k_closest(times,ctime,2)
      times = [times[timi[0]],times[timi[1]]]

  # If between two files, set index of and get last time of 
  #  first file and first time of last file
  else:
    times = [float(files[0].variables["time"][-1]),
             float(files[1].variables["time"][0])]
    timi = [len(list(files[0].variables["time"][:]))-1,0]

  # Return file handle(s), time indice(s), times(s), and main time
  return(files,timi,times,ctime)

#==================================================================
# Get subset of a variable from ERA5 files
#==================================================================

def get_E5_ss_2D_coords(fh,clon,clat,hda):
  """
  Find the horizontal coordinates and indices for a subset of 
   ERA5 data

  Input: 
   1) A handle for the datafile
   2,3) The central longitude and latitude for the subset
   4) Half the size of the subset in degrees (i.e. for a 10x10 
       degree subset hda==5)

  Output:
   1,2) Indices for the longitude and latitude coordinates
   3,4) Flattened lists of the longitude and latitude coordinates 

  Requires numpy 1.16.3 (conda install -c anaconda numpy; 
   https://pypi.org/project/numpy/)
  """

  # Get longitude and latitude coordinates
  if clon<0: clon = clon+360
  lat = fh.variables["latitude"][:]
  lon = fh.variables["longitude"][:]

  # Set lat and lon ranges
  clatp = clat+hda
  if clatp>90: clatp = 90
  clatm = clat-hda
  if clatm<-90: clatm = -90
  clonp = clon+hda
  if clonp>360: clonp = clonp-360
  clonm = clon-hda
  if clonm<0: clonm = clonm+360

  # Deal with cyclical lons
  if clonp>(lon[-1]+(lon[1]-lon[0])/2): clonp = clonp-360
  if clonm>(lon[-1]+(lon[1]-lon[0])/2): clonm = clonm-360

  # Find indices
  lati  = np.squeeze([mfns.k_closest(lat,clatp,1), 
                      mfns.k_closest(lat,clatm,1)])
  loni  = np.squeeze([mfns.k_closest(lon,clonm,1),
                      mfns.k_closest(lon,clonp,1)])
     
  # Get coordinates of that subset
  lats = fh.variables["latitude"][lati[0]:lati[1]+1]
  if loni[1]>loni[0]:
    lons = fh.variables["longitude"][loni[0]:loni[1]+1]
  if loni[0]>loni[1]:
    lons = np.concatenate([fh.variables["longitude"][loni[0]:],
                           fh.variables["longitude"][0:loni[1]+1]])

  # Return data
  return(loni,lati,lons,lats)



#==================================================================
# Get subset of a variable from ERA5 files
#==================================================================

def get_E5_ss_2D_var(fh,varname,timi,loni,lati,times,ctime):
  """
  Get a 2D subset of ERA5 data.

  Input: 
   1) File handle(s) for the files
   2) A string of the variable name in ERA5 e.g."CAPE"
   3) The indices corresponding to time
   4,5) The indices corresponding to longitude and latitude ranges
   6,7) Times and the central time for interpolation

  Output:
   1) Returns a flattened list of the ERA5 variable corresponding 
    to coordinates from get_E5_subset_2D_coords

  Requires numpy 1.16.3 (conda install -c anaconda numpy; 
   https://pypi.org/project/numpy/), scipy 1.2.1 (conda install 
   -c anaconda scipy; https://pypi.org/project/scipy/)
  """

  # Read in subset of data (interpolate in time if necessary)

  # Instance where at exact time
  if (len(fh)==1) and (len(timi)==1):

    # Not looped over longitude end
    if loni[1]>loni[0]:
      varss = np.squeeze(np.array(fh[0].variables[varname][timi,
                lati[0]:lati[1]+1,loni[0]:loni[1]+1]))
    # Looped over longitude end
    if loni[0]>loni[1]:
      varss = np.concatenate(
       [np.array(fh[0].variables[varname][timi,
         lati[0]:lati[1]+1,loni[0]:])[0,:,:],
        np.array(fh[0].variables[varname][timi,
         lati[0]:lati[1]+1,0:loni[1]+1])[0,:,:]],axis=1)

  # Instance where between times in 1 file, interpolation required
  elif len(fh)==1 and len(timi)==2:

    if loni[1]>loni[0]:
      varall = np.array(fh[0].variables[varname][timi[0]:timi[1]+1,
                lati[0]:lati[1]+1,loni[0]:loni[1]+1])
    elif loni[0]>loni[1]:
      varall = np.concatenate(
       [np.array(fh[0].variables[varname][timi[0]:timi[1]+1,
         lati[0]:lati[1]+1,loni[0]:]),
        np.array(fh[0].variables[varname][timi[0]:timi[1]+1,
         lati[0]:lati[1]+1,0:loni[1]+1])],axis=2)

    varss  = interp1d(times,varall,axis=0)(ctime)

  # Instance where between two files
  elif len(fh)==2 and len(timi)==2:
  
    if loni[1]>loni[0]:
      varall = np.concatenate(
       [np.array(fh[0].variables[varname][timi[0],
         lati[0]:lati[1]+1,loni[0]:loni[1]+1])[None,:,:],
        np.array(fh[1].variables[varname][timi[1],
         lati[0]:lati[1]+1,loni[0]:loni[1]+1])[None,:,:]],axis=0)
    elif loni[0]>loni[1]:
      varall = np.concatenate(
       [np.concatenate([
        fh[0].variables[varname][timi[0],
         lati[0]:lati[1]+1,loni[0]:][None,:,:],
        fh[0].variables[varname][timi[0],
         lati[0]:lati[1]+1,0:loni[1]+1][None,:,:]],axis=2),
        np.concatenate([
        fh[1].variables[varname][timi[1],
         lati[0]:lati[1]+1,loni[0]:][None,:,:],
        fh[1].variables[varname][timi[1],
         lati[0]:lati[1]+1,0:loni[1]+1][None,:,:]],axis=2)]
        ,axis=0)

    varss  = interp1d(times,varall,axis=0)(ctime)

  # Any other instances throw an error
  else:
    raise ValueError("Something went wrong in selecting times")

  # Return data
  return(varss)

