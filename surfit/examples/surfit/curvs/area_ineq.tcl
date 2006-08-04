#
# This script was generated with funner v2.1beta (www.gridding.info)

# 
# load plugins
# 
load libsurfit[info sharedlibextension]

# remove all previous data and gridding rules
clear_data 

# set name of surface
set map_name "map_area_ineq" 

# set tolerance for cg solver
set tol 1e-005 

##
## load initial data 
##
 
# load area from text file 
area_read "area1.txt" "area1"  
 
# load area from text file 
area_read "area2.txt" "area2"  
 
# load area from text file 
area_read "area3.txt" "area3"  
 
# load area from text file 
area_read "area4.txt" "area4"  
 
# load area from text file 
area_read "area5.txt" "area5"  
 
# load area from text file 
area_read "area6.txt" "area6"  
 
##
## construct grid 
##
grid_get -12 12 0.2 -12 12 0.2 
 
##
## create gridding rules
##

# resulting surface in area = value... 
area 30 "area3"  

# resulting surface in area <= value... 
area_leq 20 "area6"

# resulting surface in area = value... 
area 10 "area1"  

# resulting surface in area = value... 
area undef "area5"  

# resulting surface should tend to be constant or plane 
completer 1 0  

# add "resulting surface in area = value..." with weight 
area_add 20 0.07 "area2"  

# add "resulting surface in area = value..." with weight 
area_add 40 0.07 "area4"  

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
surf_save "area_ineq.dat" "map_area_ineq" 

puts [concat "Maximum value in area6 : " [surf_area_maxz "area6" "map_area_ineq"]]

