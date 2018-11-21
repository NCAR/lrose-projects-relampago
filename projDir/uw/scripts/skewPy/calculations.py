# Brody Fuchs, CSU, October 2013
# brfuchs@atmos.colostate.edu

# Code designed to do some calculations with output RUC/RAP
# data as a sanity check to make sure the numbers look right.
# Things like CAPE will be looked at, also possibly CAPE
# above/below the freezing level
# Also can compute storm level shear, and 200 mb (relative) winds
# Have to chop out some levels if surface is above 1000 mb ********


import numpy as np
import matplotlib.pyplot as plt
from scipy.io.idl import readsav
import scipy.stats as stats
from skewt import SkewT
import scipy.stats as stats


dir = 59
region = 'CO'
md = 100

if region == 'CO': surf_parc_pres = 850.0
else: surf_parc_pres = 1000.0

# for testing purposes, comment when actually using
#surf_parc_pres = 850.0


cells = readsav('./%d/cells.dat'%dir).good_cells
cape = readsav('./%d/cape.dat'%dir).cape
temp = readsav('./%d/ruc_tc.dat'%dir).ruc_tc
dew = readsav('./%d/ruc_td.dat'%dir).ruc_td
h_el = readsav('./%d/hel.dat'%dir).hel
ht = readsav('./%d/ruc_hc.dat'%dir).ruc_hc
pres = np.linspace(1e4, 1e5, 37)
u = readsav('./%d/ruc_u.dat'%dir).ruc_u
v = readsav('./%d/ruc_v.dat'%dir).ruc_v

my_cape = []
ncape = []
wcape = []

print 'SURFACE PARCEL PRESSURE: %d'%surf_parc_pres

parcel_temp = np.zeros(pres.shape[0])
spd = np.zeros(u.shape)
drct = np.zeros(u.shape)
for l in range(u.shape[0]):
    for i in range(u.shape[1]):
	spd[l,i] = np.sqrt(u[l,i]**2 + v[l,i]**2)
	drct[l,i] = np.degrees(np.arctan2(-1.*u[l,i],-1.*v[l,i]))

neg = np.where(drct < 0)
drct[neg] = drct[neg]+360.0

print 'CAPE.shape: %d'%cape.shape[0]

for ic in range(cape.shape[0]):

    c = ic # cell array position to check

    if np.mod(c,50) == 0: print '%2.2f%%'%(100.0*float(c)/cape.shape[0])

    snd_dict = {'pres': pres[::-1]/100.0, 'temp': temp[:,c][::-1], 
		'dwpt': dew[:,c][::-1], 'sknt': spd[:,c][::-1], 'drct': drct[:,c][::-1]}


    s = SkewT.Sounding(data = snd_dict)
    s.plot_skewt(lw = 2, title = 'test', mixdepth = md, pres_s = surf_parc_pres)#, imagename = 'testsnd.png')
    s_surf = s.surface_parcel(mixdepth = md, pres_s = surf_parc_pres)
    p, tdry, tiso, pwet, twet = s.lift_parcel(s_surf[0], s_surf[1], s_surf[2])

    p_lcl = pwet[0]

    atm = pres/100. <= surf_parc_pres # finding pres elements that are above the surface
    p_atm = pres[atm]

    dry = np.where(p_atm/100.0 >= p_lcl)
    moist = np.where(p_atm/100.0 < p_lcl)

    for d in dry[0]:
        p_diff = p-p_atm[d]/100.
        below = np.where(p_diff >= 0)[0][-1] # closest pressure level just below
        above = below + 1
        parcel_temp[d] = np.interp(p_atm[d]/100., [p[above], p[below]], [tdry[above], tdry[below]])

    parcel_temp[0] = twet[-1] # cant interpolate on the end

    for m in moist[0][1:]:
        p_diff = pwet-p_atm[m]/100.
        below = np.where(p_diff >= 0)[0][-1] # closest pressure level just below
        above = below + 1
        parcel_temp[m] = np.interp(p_atm[m]/100., [pwet[above], pwet[below]], [twet[above], twet[below]])

    for i in range(temp[:,c].shape[0]):
        t_diff = temp[i,c] - parcel_temp[i]
        if t_diff <= 0: 
            below = i
            e = i
            break

    # now can get the EL info

    p_el = np.interp(0, [temp[below,c]-parcel_temp[below], temp[below-1,c]-parcel_temp[below-1]], 
                            [p_atm[below],p_atm[below-1]])

    h_el = np.interp(0, [temp[below,c]-parcel_temp[below], temp[below-1,c]-parcel_temp[below-1]], 
                            [ht[below,c],ht[below-1,c]])
    # need T at EL


    for i in range(below, temp[:,c].shape[0]):
        t_diff = temp[i,c] - parcel_temp[i]
        if t_diff >= 0:
            below = i
            l = i
            break
    if l == p_atm.shape[0]: # if LCL = LFC
	p_lfc = p_lcl
    else:
	p_lfc = np.interp(0, [temp[below-1,c]-parcel_temp[below-1], temp[below,c]-parcel_temp[below]], 
                            [p_atm[below-1],p_atm[below]])/100.0
#    h_lfc = np.interp(0, [temp[below-1,c]-parcel_temp[below-1], temp[below,c]-parcel_temp[below]], 
#                            [ht[below-1,c],ht[below,c]])
    h_lfc = np.interp(p_lfc, pres/100., ht[:,c])

    frz = np.where(np.abs(temp[:,c]) == np.abs(temp[:,c]).min())[0][0]

    warm_cape = 0
    calc_cape = 0
    # NEED TO MAKE SURE THERE IS A REASONABLE EL
    if l > e:
	for i in range(e,l-1): # looping from EL to LFC to get CAPE
            calc_cape += 9.81*(parcel_temp[i]-temp[i,c])*1000.0*(ht[i,c]-ht[i+1,c])/(temp[i,c]+273.15)
            if i >= frz:
                warm_cape += 9.81*(parcel_temp[i]-temp[i,c])*1000.0*(ht[i,c]-ht[i+1,c])/(temp[i,c]+273.15)

    # ADD ON A LITTLE NEAR THE EL
        el_cape = 9.81*(parcel_temp[e]-temp[e,c])*1000.0*(h_el-ht[e,c])/(temp[e,c]+273.15)
        calc_cape += el_cape
    # SUBTRACT OFF ANY BELOW THE LFC
        lfc_cape = 9.81*(parcel_temp[l]-temp[l,c])*1000.0*(h_lfc-ht[l,c])/(temp[l,c]+273.15)
        calc_cape += lfc_cape
	warm_cape += lfc_cape
        if (np.abs(el_cape) > 1000) | (np.abs(lfc_cape) > 1000):
	    quit()

        del lfc_cape
        del el_cape
	if calc_cape < 0: calc_cape = 0
#	if ((calc_cape/cape[c]) > 2): 
#        print c, cape[c], calc_cape
#        s.plot_skewt(lw = 2, title = 'cell: %03d, RUC: %d, mine: %d\np_el: %d, p_lfc: %d'
#			%(c,cape[c],calc_cape, p_el/100.0, p_lfc), pres_s = surf_parc_pres,
#			 mixdepth=md, imagename = 'testsnd_%03d.png'%c)

    my_cape.append(calc_cape)
    ncape.append(calc_cape/(1000*(h_el-h_lfc)))
    wcape.append(warm_cape)

    del calc_cape


my_cape = np.array(my_cape)
ncape = np.array(ncape)
wcape = np.array(wcape)

np.save('./%d/my_cape.npy'%dir, my_cape)
np.save('./%d/ncape.npy'%dir, ncape)
np.save('./%d/wcape.npy'%dir, wcape)


fig = plt.figure()
plt.scatter(cape, my_cape, edgecolors = 'none')
slope, intercept, r_value, p_value, std_err = stats.linregress(cape,my_cape)
plt.text(cape.max()*0.23 , my_cape.max()*0.9, 'R$^2$ = %3.2f\nslope = %4.2f'%(r_value**2,slope))
plt.axis('tight')
plt.xlabel('model CAPE')
plt.ylabel('my CAPE')
plt.savefig('./plots/mycape_%s.png'%region)





#fig = plt.figure()
#plt.plot(parcel_temp, pres)
#plt.plot(temp[:,c], pres)
#plt.yscale('log')
#plt.gca().invert_yaxis()

