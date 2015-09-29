#
# This script was generated with funner for surfit v3.0

# 
# load plugins
# 
load libtclsurfit[info sharedlibextension]
load libsurfit_io[info sharedlibextension]

# remove all previous data and gridding rules
clear_data 

# set name of surface
set map_name "hist_poro" 

# set solver
set_solver "cg" 

# set tolerance for solver
set tol 1e-007

##
## load initial data 
##
 
# load points from text file 
pnts_read "kpor.txt" "kpor"  

area_read "convex_hull.txt" "convex_hull"

hist_from_pnts * 6 0.22 0.28
 
##
## construct grid 
##
grid_get 8000 14000 25 24500 30500 25 
 
##
## create gridding rules
##

# resulting surface at points = points values 
points "kpor" 

area_hist * * 

# resulting surface should tend to be constant or plane 
completer 1 5

##
## run gridding algorithm
##
surfit 

##
## save results 
##

# unload grid from memory
grid_unload 

# save surface to surfit datafile 
surf_save "hist_poro.dat" "hist_poro" 
