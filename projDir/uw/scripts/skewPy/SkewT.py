from numpy import ma,array,linspace,log,cos,sin,pi,zeros,exp,arange,interp,flipud
import numpy as np
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.collections import LineCollection
from matplotlib.ticker import FixedLocator, AutoLocator, ScalarFormatter
import matplotlib.transforms as transforms
import matplotlib.axis as maxis
import matplotlib.artist as artist
from matplotlib.projections import register_projection
from matplotlib.pyplot import rcParams,figure,show,draw
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
import numpy as np
import matplotlib.pyplot as plt
from copy import deepcopy
from scipy import interpolate
import json
import pandas as pd
import math

from thermodynamics import VirtualTemp,Latentc,SatVap,MixRatio,GammaW,\
	VirtualTempFromMixR,MixR2VaporPress,DewPoint,Theta,TempK,VaporPressure
from thermodynamics import Rs_da, Rs_v, Cp_da, Epsilon

try:
    from sharppy.sharptab import profile as sprofile
except ImportError:
    print 'sharppy not installed'

from UserDict import UserDict
from datetime import datetime
import os
import sys

degC = '$^{\circ}$C'

def trapezoid(value, trap_values, yvalues = [-1,1,1,-1]):
    xarr = np.array(trap_values).astype(float)
    yarr = np.array(yvalues)
    return np.interp(value, xarr, yarr)


def fuzzy_trop_index(input_data, weights, mbfs = None):
    trop_score = score_calc(input_data, weights = weights,  mbfs = mbfs)
    score_max = np.argmax(trop_score)
    return score_max

def fuzzy_tropopause(input_data, weights, mbfs = None):
    trop_score = score_calc(input_data, weights = weights,  mbfs = mbfs)
    if trop_score.max() > 0.4:
        score_max = np.argmax(trop_score)
        trop_pressure = input_data['pres'][score_max]
    else: trop_pressure = -999.0
    return trop_pressure


def cdf_betas_sum():

    mbf_dict = {'theta': [280, 300, 330, 360], 
    'dtdp': [-0.1, -0.04, 0.04, 0.1], 
    'T': [-200, -70, -45, -35], 
    'dthetadp': [0.2, 0.5, 100, 101], 
    'drhdp': [-100, -99, -1.0, -0.2],
    'pres': [0, 150, 300, 400],

    }

    return mbf_dict

def score_calc(data, mbfs = None, weights = None):

# NOW CHECK WEIGHTS
# data should be a dictionary
    if mbfs is None: mbfs = cdf_betas_sum()
# just do the defaults if nothing provided, this is likely

    weight_sum = np.sum(np.array([weights[_] for _ in weights.keys()]))

    mu = np.array( [np.sum(np.array([weights[k]*trapezoid(data[k][_],mbfs[k], \
    ) for k in weights.keys()]), axis = 0)/weight_sum for _ in range(data[data.keys()[0]].shape[0])] )

    return mu



def running_mean(x, N, ntimes = 1):
    out = np.convolve(x, np.ones((N,))/N)[(N-1):]
    if ntimes > 1: # if want to do more than once, keep doing it
        for _ in range(ntimes-1):
            out = np.convolve(out, np.ones((N,))/N)[(N-1):]
    return out

def RH(T, Td):
# calculate the RH given temperature and dew point

    TK = T+ 273.15
    TdK = Td + 273.15
    return 100.0*(np.exp((17.625*TdK)/(243.04+TdK))/np.exp((17.625*TK)/(243.04+TK)))

def lowpass_filter(orig_signal, sample_rate, cutoff_hz, numtaps = 29):
    from scipy.signal import lfilter, firwin	
# The Nyquist rate of the signal.
    nyq_rate = sample_rate / 2.

# numtaps is Length of the filter (number of coefficients, i.e. the filter order + 1)

# Use firwin to create a lowpass FIR filter
    fir_coeff = firwin(numtaps, cutoff_hz/nyq_rate)

# Use lfilter to filter the signal with the FIR filter
    filtered_signal = lfilter(fir_coeff, 1.0, orig_signal)

# The first N-1 samples are "corrupted" by the initial conditions
    warmup = numtaps - 1

# The phase delay of the filtered signal
    delay = (warmup / 2) / sample_rate

    return filtered_signal[warmup:], warmup, delay

def FtoC(temp):
    return (temp - 32.)*5/9.

def CtoF(temp):
    return 9.*temp/5 + 32.0

def psyRH(Td, Tw, Pa=1000, p_typ='screen', unit = 'F'):
    """Finds relative humidity from wet/dry thermometer readings using the
    psychrometric equation.
    # TODO: http://www.ncl.ucar.edu/Document/Functions/Built-in/relhum.shtml
    """
    Td, Tw, Pa = np.asarray(Td), np.asarray(Tw), np.asarray(Pa)
    if unit == 'F':
        Td = FtoC(Td)
        Tw = FtoC(Tw)

# Psychrometric coefficient.
    A = 0.000799

# Compute saturation vapor pressure for both temperatures.
    ed = SatVap(Td)
    ewp = SatVap(Tw)

# The psychrometric equation.
    e = ewp - A * Pa * (Td - Tw)  # Ambient vapor pressure.
    rh = e / ed * 100
    if rh < 0: rh = 0
    return rh


def tropopause_index(temp):
    smooth = running_mean(temp, 30)
    smooth = running_mean(smooth, 30)

    deriv = np.gradient(smooth)
    deriv_smooth = running_mean(deriv, 30)
    deriv_smooth = running_mean(deriv_smooth, 30)

    deriv2 = np.gradient(deriv_smooth)*1e4

    try:
        tropopause_indices = np.where( (np.abs(deriv_smooth) < 5e-4) & (temp < -40) & (deriv2 > 3) )[0]
        t_index = tropopause_indices[0]

    except (ValueError, IndexError):
        t_index = -999

    return t_index


class SkewXTick(maxis.XTick):
#Copyright (c) 2008 Ryan May
    def draw(self, renderer):
        if not self.get_visible(): return
        renderer.open_group(self.__name__)

        if self.gridOn:
            self.gridline.draw(renderer)
        if self.tick1On:
            self.tick1line.draw(renderer)
        if self.tick2On:
            self.tick2line.draw(renderer)

        if self.label1On:
            self.label1.draw(renderer)
        if self.label2On:
            self.label2.draw(renderer)

        renderer.close_group(self.__name__)

    def set_clip_path(self, clippath, transform=None):
        artist.Artist.set_clip_path(self, clippath, transform)
        self.tick1line.set_clip_path(clippath, transform)
        self.tick2line.set_clip_path(clippath, transform)
        self.gridline.set_clip_path(clippath, transform)
    set_clip_path.__doc__ = artist.Artist.set_clip_path.__doc__

class SkewXAxis(maxis.XAxis):
#Copyright (c) 2008 Ryan May
    def _get_tick(self, major):
        return SkewXTick(self.axes, 0, '', major=major)

    def draw(self, renderer, *args, **kwargs):
        'Draw the axis lines, grid lines, tick lines and labels'
        ticklabelBoxes = []
        ticklabelBoxes2 = []

        if not self.get_visible(): return
        renderer.open_group(__name__)
        interval = self.get_view_interval()
        for tick, loc, label in self.iter_ticks():
            if tick is None: continue
            if transforms.interval_contains(interval, loc):
                tick.set_label1(label)
                tick.set_label2(label)
            tick.update_position(loc)
            tick.draw(renderer)
            if tick.label1On and tick.label1.get_visible():
                extent = tick.label1.get_window_extent(renderer)
                ticklabelBoxes.append(extent)
            if tick.label2On and tick.label2.get_visible():
                extent = tick.label2.get_window_extent(renderer)
                ticklabelBoxes2.append(extent)

# scale up the axis label box to also find the neighbors, not
# just the tick labels that actually overlap note we need a
# *copy* of the axis label box because we don't wan't to scale
# the actual bbox

        #self._update_label_position(ticklabelBoxes, ticklabelBoxes2)

        self.label.draw(renderer)

        self._update_offset_text_position(ticklabelBoxes, ticklabelBoxes2)
        self.offsetText.set_text( self.major.formatter.get_offset() )
        self.offsetText.draw(renderer)

class SkewXAxes(Axes):
    #Copyright (c) 2008 Ryan May
    # The projection must specify a name.  This will be used be the
    # user to select the projection, i.e. ``subplot(111,
    # projection='skewx')``.
    name = 'skewx'

    def _init_axis(self):
    #Taken from Axes and modified to use our modified X-axis
        "move this out of __init__ because non-separable axes don't use it"
        self.xaxis = SkewXAxis(self)
        self.yaxis = maxis.YAxis(self)
        self._update_transScale()

    def draw(self, *args):
        '''
        draw() is overridden here to allow the data transform to be updated
        before calling the Axes.draw() method.  This allows resizes to be
        properly handled without registering callbacks.  The amount of
        work done here is kept to a minimum.
        '''
        self._update_data_transform()
        Axes.draw(self, *args)

    def _update_data_transform(self):
        '''
        This separates out the creating of the data transform so that
        it alone is updated at draw time.
        '''
        # This transforms x in pixel space to be x + the offset in y from
        # the lower left corner - producing an x-axis sloped 45 degrees
        # down, or x-axis grid lines sloped 45 degrees to the right
        self.transProjection.set(transforms.Affine2D(
            array([[1, 1, -self.bbox.ymin], [0, 1, 0], [0, 0, 1]])))

        # Full data transform
        self.transData.set(self._transDataNonskew + self.transProjection)

    def _set_lim_and_transforms(self):
        """
        This is called once when the plot is created to set up all the
        transforms for the data, text and grids.
        """
        #Get the standard transform setup from the Axes base class
        Axes._set_lim_and_transforms(self)

        #Save the unskewed data transform for our own use when regenerating
        #the data transform. The user might want this as well
        self._transDataNonskew = self.transData

        #Create a wrapper for the data transform, so that any object that
        #grabs this transform will see an updated version when we change it
        self.transData = transforms.TransformWrapper(transforms.IdentityTransform())

        #Create a wrapper for the proj. transform, so that any object that
        #grabs this transform will see an updated version when we change it
        self.transProjection = transforms.TransformWrapper(transforms.IdentityTransform())
        self._update_data_transform()

    def get_xaxis_transform(self, which='grid'):
        """
        Get the transformation used for drawing x-axis labels, ticks
        and gridlines.  The x-direction is in data coordinates and the
        y-direction is in axis coordinates.

        We override here so that the x-axis gridlines get properly
        transformed for the skewed plot.
        """
        return self._xaxis_transform + self.transProjection

    # Disable panning until we find a way to handle the problem with
    # the projection
    def start_pan(self, x, y, button):
        pass

    def end_pan(self):
        pass

    def drag_pan(self, button, key, x, y):
        pass

    def other_housekeeping(self, pmin=100., mixratio=array([])):
        # Added by Thomas Chubb
        self.yaxis.grid(True,ls='-',color='y',lw=0.5)
        pres_levels = np.arange(100, 1100, 100)

        #pres_heights = np.array( [self.data['hght'][np.argmin(np.abs(_ - self.data['pres']))] for _ in pres_levels] )
        #print pres_heights


        # Plot x-grid lines instead of using xaxis.grid().
        # This is because xaxis.grid only plots skew lines 
        # that intersect the lower x axis... a possible fix
        # would be to use twinx() to plot upper and lower
        # grid lines but I think that's messy too.
        for TT in linspace(-100,100,21):
            self.plot([TT,TT],[1100,pmin],color='y',lw=0.5)

        # self.set_ylabel('Pressure (hPa)')`
        self.set_xlabel('Temperature ($^{\circ}$C)', fontsize=12, labelpad=2)
        self.set_ylabel('Pressure (hPa)', labelpad=2, fontsize=12)

        #print self.get_xlabel()
        self.set_yticks(pres_levels)
        self.yaxis.set_major_formatter(ScalarFormatter())
        self.set_xlim(-40,45)
        self.set_ylim(1100.,pmin)
        self.spines['right'].set_visible(False)
        self.spines['bottom'].set_visible(True)
        self.get_yaxis().set_tick_params(which="both",size=0)
        self.get_xaxis().set_tick_params(which="both",size=0)
        self.tick_params(labelsize=12)

    def set_xticklocs(self,xticklocs):
    # Added by Thomas Chubb
        self.set_xticks(xticklocs)

    def add_dry_adiabats(self,T0,P,do_labels=True,**kwargs):
    # Added by Thomas Chubb
        P0=1000.
        T = array([ (st+273.15)*(P/P0)**(Rs_da/Cp_da)-273.15 for st in T0 ])
        labelt = [ (st+273.15)*1**(Rs_da/Cp_da) for st in T0 ]
        if kwargs.has_key('color'): 
            col = kwargs['color']
        else: 
            col = 'k'
        for tt,ll in zip(T,labelt):
            self.plot(tt,P,**kwargs)
        if do_labels:
            if (tt[8] > -50) and (tt[8] < 35):# 20 is default, how far to label the dry adibats
                self.text(tt[8],P[8]+30,'%d'%(ll), fontsize = 8,\
                ha = 'center',va = 'bottom', rotation = -40, color = col)#, bbox={'facecolor':'w','edgecolor':'w'})
        # BF LAST PART IS THE BOX BEHIND THE TEXT I THINK

        return T


    def add_moist_adiabats(self,T0,P,do_labels=True,**kwargs):
    # Added by Thomas Chubb
        T=array([lift_wet(st,P) for st in T0])
        if kwargs.has_key('color'): 
            col=kwargs['color']
        else: 
            col='k'
        for tt in T:
            self.plot(tt,P,**kwargs)
        # if (tt[-1]>-60) and (tt[-1]<-10):
            if do_labels:
                self.text(tt[-1],P[-1],'%d'%tt[0],ha='center',va='bottom',\
                fontsize=8, bbox={'facecolor':'w','edgecolor':'w'},color=col)

    def add_mixratio_isopleths(self,w,P,do_labels=True,**kwargs):
    # Added by Thomas Chubb
        e=array([P*ww/(.622+ww) for ww in w])
        T = 243.5/(17.67/log(e/6.112) - 1)
        if kwargs.has_key('color'): 
            col=kwargs['color']
        else: 
            col='k'

        for tt,mr in zip(T,w):
            self.plot(tt,P.flatten(),**kwargs)
            if do_labels:
                if (tt[-1]>-45) and (tt[-1]<20):
                    if mr*1000<1.:
                        fmt="%4.1f"
                    else:
                        fmt="%d"
                    self.text(tt[-1],P[-1],fmt%(mr*1000),\
                    color=col, fontsize=8,ha='center',va='bottom',\
                    bbox={'facecolor':'w','edgecolor':'w'})

        # Now register the projection with matplotlib so the user can select
        # it.
register_projection(SkewXAxes) # this is probably the big line

class Sounding(UserDict):
# Copyright (c) 2013 Thomas Chubb 
    """Utilities to read, write and plot sounding data quickly and without fuss

    INPUTS:
    filename:   If creating a sounding from a file, the full file name. The 
    format of this file is quite pedantic and needs to conform 
    to the format given by the University of Wyoming soundings 
    (see weather.uwyo.edu/upperair/sounding.html) 
    data: 	Soundings can be made from atmospheric data. This should be 
    in the form of a python dict with (at minimum) the following 
    fields:

    TEMP: dry-bulb temperature (Deg C)
    DWPT: dew point temperature (Deg C)
    PRES: pressure (hPa)
    SKNT: wind speed (knots)
    WDIR: wind direction (deg)

    The following fields are also used, but not required by the 
    plot_skewt routine:

    HGHT (m)
    RELH (%)
    MIXR (g/kg)
    THTA (K)
    THTE (K)
    THTV (K)
    """


    def __init__(self, filename=None, data=None, fmt='UWYO', station_name=None, plot_flag=False, flip_barb=False):
        UserDict.__init__(self)

        self.fmt = fmt
        self.station_name = station_name
        self.flip_barb = flip_barb


        if data is None:
            self.data={}
            self.readfile(filename)
        else:
            self.data=data
            self['SoundingDate']=""
	    self.sounding_date = ''

        # this does some basic QC of the data near the surface
        self.check_bottom_qc()

	if plot_flag:
            self.plot_skewt(parcel=True, parcel_draw=True)

	else:
            #print self.data
	    self.parcel=self.surface_parcel()
        #       print parcel
            self.parcel_pres, self.parcel_tdry, self.parcel_tiso, self.parcel_pwet, self.parcel_twet = self.lift_parcel(
                *self.parcel, plotkey=False)

        #self.cape()

    def plot_skewt(self, imagename=None, title=None, mixdepth=50, pres_s=1000.0, windskip = None, \
                        parcel = False, parcel_draw = False, **kwargs):
        """A wrapper for plotting the skewt diagram for a Sounding instance."""

        self.make_skewt_axes()
        self.add_profile(pres_s=pres_s, **kwargs)
        if parcel:
            self.parcel=self.surface_parcel(mixdepth = mixdepth, pres_s = pres_s)
        #	print parcel
            self.parcel_pres, self.parcel_tdry, self.parcel_tiso, self.parcel_pwet, self.parcel_twet = self.lift_parcel(
                *self.parcel, plotkey = parcel_draw)
        #else: 
        #    self.parcel = None

        # self.skewxaxis.set_xlabel('Temp')
        
        # print dir(self.skewxaxis)

        if isinstance(title, str):
            ttl = self.skewxaxis.set_title(title, fontsize=15)
            ttl.set_position([0.55, 1.06])


        else:
            try:
                self.skewxaxis.set_title("%s, %sZ, Lon: %.2f$^{\circ}$, Lat: %.2f$^{\circ}$"%(self.station, 
                        self.sounding_date, self.lon, self.lat))
            except Exception:
                self.skewxaxis.set_title('Test title')

        if imagename is not None:
            print("saving figure")
            self.fig.savefig(imagename, dpi=100)
    #    return None

    def cape(self):
        p_lcl = self.parcel_pwet[0]
        wet_heights = self.data['hght'][np.bitwise_and(self.data['pres'] <= p_lcl, self.data['pres'] >= 100.)]
        
        f = interpolate.interp1d(self.parcel_pwet, self.parcel_twet)
        xnew = self.data['pres'][np.bitwise_and(self.data['pres'] <= p_lcl, self.data['pres'] >= 100.)]
        Tp_interp = f(xnew) + 273.15   
        
        Te = self.data['temp'][np.bitwise_and(self.data['pres'] <= p_lcl, self.data['pres'] >= 100.)] + 273.15


    # pres : array_like
    # The pressure values (Hectopascals)
    # hght : array_like
    # The corresponding height values (Meters)
    # tmpc : array_like
    # The corresponding temperature values (Celsius)
    # dwpc : array_like
    # The corresponding dewpoint temperature values (Celsius)

    # Optional Keyword Pairs (must use one or the other)

    # wdir : array_like
    # The direction from which the wind is blowing in
    # meteorological degrees
    # wspd : array_like
    # The speed of the wind


        # sharp_data = {'pres': self.data['pres'], 'hght': self.data['hght'], 'tmpc': self.data['temp'], 'dwpc': self.data['dwpt'],
        #                         'wdir': self.data['drct'], 'wspd': self.data['sknt'], 'profile': 'convective'}

        # sharp_prof = sprofile.create_profile(**sharp_data)

        # print 'MUCAPE: {}'.format(sharp_prof.mupcl.bplus)
        # # need to be able to pull out all of the other parameters from the sharppy stuff





        CAPE = (9.8*(Tp_interp[1:] - Te[1:]) / Te[1:]) * (wet_heights[1:] - wet_heights[:-1])

        CAPE[CAPE<=0] = 0.0

	try:
       	    self.fig.text(0.84, 0.60, 'SBCAPE: %d J/kg'%(CAPE.sum()))
	except Exception, cpe:
            print 'Error with the CAPE writing/calculation: {}'.format(cpe)
	    pass
        # self.fig.text(0.84, 0.58, 'CIN: %d J/kg'%(CIN))




        ## Calculate Wet Bulb Temperature
        T_lcl = self.parcel_twet[0]
        Tw = T_lcl
        dp = 1 #Pa
        for i in np.arange(p_lcl*100., self.data['pres'][0]*100.,dp):
            gw = GammaW(Tw+273.15, i)
            Tw = Tw + gw*dp

	try:
            self.fig.text(0.85, 0.10, 'T$_W$: %.1f %s'%(Tw, degC))
	except:
	    pass

        # SFC Specific Humidity
        e_sat = VaporPressure(self.data['temp'][0])
        w_sat = (e_sat*Rs_da) / (Rs_v*(self.data['pres'][0]*100. - e_sat))
        q_sat = w_sat / (w_sat+1) #kg/kg

        e_sfc = VaporPressure(self.data['dwpt'][0])
        w_sfc = (e_sfc*Rs_da) / (Rs_v*(self.data['pres'][0]*100. - e_sfc))
        q_sfc = w_sfc / (w_sfc+1) #kg/kg


	# let's do a mixed q over the lowest 50 mb
	p_sfc = self.data['pres'][0]
	p_sfc_50 = p_sfc - 50.0
	mixed_ind = np.where(self.data['pres'] >= p_sfc_50)[0]
	
	e_mixed = np.average(VaporPressure(self.data['dwpt'][mixed_ind]))
	w_mixed = (e_mixed*Rs_da)/(Rs_v*((self.data['pres'][0]-25)*100 - e_mixed))
	q_mixed = w_mixed/(w_mixed+1)	
	
        RH_sfc = (e_sfc / e_sat)*100.

	try:
            self.fig.text(0.85, 0.08, 'q: %.1f g/kg'%(q_sfc*1000.))
            self.fig.text(0.85, 0.06, 'q$_s$: %.1f g/kg'%(q_sat*1000.))
            self.fig.text(0.85, 0.04, 'RH: %.1f %%'%(RH_sfc))
	except:
	    pass

        if hasattr(self, 'sounding_date'):
            pass
        else:
            self.sounding_date = None

        return CAPE.sum(), self.data['pres'][-1], self.sounding_date, Tw, RH_sfc, q_sfc, q_mixed




    def write_ascii(self, filename=None, json_format=False, varlist=None):
        # This will write out the sounding in an easily readable format

        if varlist is None:
            varlist = ['hght', 'pres', 'temp', 'dwpt', 'sknt', 'drct']

        if filename is None:
            filename = '%s_%s_ascii.txt'%(self.sounding_date, self.station)

        #print self.data.keys()
        # as requested in comment
        if json_format:
            exDict = {'exDict': self.data}
            for k in exDict['exDict'].keys():
                exDict['exDict'][k] = exDict['exDict'][k].tolist()


            with open(filename, 'w') as fi:
                fi.write(json.dumps(exDict)) # use `json.loads` to do the reverse

        else: # just do an ascii
            with open(filename, 'w') as fi:
                fi.write('  '.join(varlist))
                fi.write('\n')
                nlines = len(self.data[varlist[0]])
                print 'nlines: {}'.format(nlines)

                for n in range(nlines):
                    fi.write('%.1f  %.1f  %.1f  %.1f  %.1f  %.1f\n'%(self.data['hght'][n], self.data['pres'][n], 
                                                self.data['temp'][n], self.data['dwpt'][n], self.data['sknt'][n], self.data['drct'][n]))




    def add_profile(self,bloc=0.5, pres_s = 1000.0, **kwargs):
        """Add a new profile to the SkewT plot.

        This is abstracted from plot_skewt to enable the plotting of
        multiple profiles on a single axis, by updating the data attribute.
        For example:

        S=SkewT.Sounding(data={})
        S.make_skewt_axes()
        S.readfile("../examples/94975.2013062800.txt")
        S.add_profile(color="b",bloc=0.5)
        S.readfile("../examples/94975.2013070900.txt")
        S.add_profile(color="r",bloc=1.)

        Use the kwarg 'bloc' to set the alignment of the wind barbs from the centerline 
        (useful if plotting multiple profiles on the one axis)


        Modified 25/07/2013: enforce masking of input data for this 
        function (does not affect the data attribute).
        """

        try: pres = ma.masked_invalid(self.data['pres'])
        except KeyError: raise KeyError, "Pressure in hPa (PRES) is required!"

        try: tc=ma.masked_invalid(self.data['temp'])
        except KeyError: raise KeyError, "Temperature in C (TEMP) is required!"

        try: dwpt=ma.masked_invalid(self.data['dwpt'])
        except KeyError:
            print "Warning: No DWPT available"
            dwpt=ma.masked_array(zeros(pres.shape),mask=False)

        try:
            sknt=self.data['sknt']
            drct=self.data['drct']
            rdir = (270.-drct)*(pi/180.)
            uu = ma.masked_invalid(sknt*cos(rdir))
            vv = ma.masked_invalid(sknt*sin(rdir))
        except KeyError:
            print "Warning: No SKNT/DRCT available"
            uu = ma.masked_array(zeros(pres.shape), mask=True)
            vv = ma.masked_array(zeros(pres.shape), mask=True)

        pres_s = self.data['pres'][0]

        vp = pres <= pres_s # valid pressures to plot
        #	pres_plot = pres[valid_pres]
        #	tc_plot = tc[valid_pres]
        #	dwpt_plot = dwpt[valid_pres]
        # NEW WAY TO ONLY PLOT ABOVE SURFACE PARCEL

        if 'flip_barb' in kwargs.keys():
            kwargs.pop('flip_barb')

        tcprof = self.skewxaxis.plot(tc[vp], pres[vp], zorder = 5, color = 'red', linewidth = 2, **kwargs)
        dpprof = self.skewxaxis.plot(dwpt[vp], pres[vp], zorder = 5, color = 'green', linewidth = 2, **kwargs)


        # this line should no longer cause an exception
        nbarbs = (~uu.mask).sum()

        skip = max(1,int(nbarbs/32))
        barb_levels = np.logspace(np.log10(110), np.log10(950), 25)
        #pres_barbs = np.unique(np.array( [np.argmin(np.abs(_ - self.data['pres'])) for _ in barb_levels] ))
        pres_barbs = np.unique(np.array( [np.argmin(np.abs(_ - pres)) for _ in barb_levels] ))
        pres_barbs = pres_barbs[pres_barbs<pres[vp].shape[0]]

        #print pres_barbs
        #print pres[vp].shape[0]

        vbarb = pres_barbs <= pres_s

        bcol = 'black' # barb color is black

        if kwargs.has_key('alpha'): balph=kwargs['alpha']
        else: balph = 1.

        #	self.wbax.barbs((zeros(pres[vp].shape)+bloc)[::skip]-0.5, pres[vp][::skip],\
        #		uu[vp][::skip], vv[vp][::skip],\
        #		length=6,color=bcol,alpha=balph,lw=0.5, zorder = 10)

        self.wbax.barbs((zeros(pres[vp].shape)+bloc)[pres_barbs]-0.5, pres[vp][pres_barbs],\
        uu[vp][pres_barbs], vv[vp][pres_barbs], length=6, color=bcol, alpha=balph, lw=0.5, zorder=10, flip_barb=self.flip_barb)

        self.skewxaxis.other_housekeeping()

        return tcprof

    def make_skewt_axes(self, pmax=1100., pmin=50.):

        self.fig = figure(figsize = (9,8))
        self.fig.clf()

        rcParams.update({'font.size': 10,})

        P = linspace(pmax, pmin, 37)
        pres_levels = np.arange(1000, 0, -100)

        self.skewxaxis = self.fig.add_axes([.085,.1,.73,.8], projection='skewx')
        self.skewxaxis.set_yscale('log')

        xticklocs = arange(-80,45,10)
        T0 = xticklocs

        w = array([0.0001,0.0004,0.001, 0.002, 0.004, 0.007, 0.01, 0.016, 0.024, 0.032])
        self.skewxaxis.add_mixratio_isopleths(w,P[P>=550],color='purple',ls='--',alpha=1.,lw=0.5)
        self.skewxaxis.add_dry_adiabats(linspace(250,440,20)-273.15,P,color='red',ls='--',alpha=1.,lw=0.5)
        self.skewxaxis.add_moist_adiabats(linspace(8,32,7),P[P>=200],color='g',ls='--',alpha=1.,lw=0.5)
        self.skewxaxis.other_housekeeping()

        #print self.skewxaxis.get_xlabel()

        self.wbax = self.fig.add_axes([0.75,0.1,0.1,0.8],sharey=self.skewxaxis,frameon=False) # wind barb axis
        self.wbax.xaxis.set_ticks([],[])
        self.wbax.yaxis.grid(True,ls='-',color='y',lw=0.5)
        for tick in self.wbax.yaxis.get_major_ticks():
        # tick.label1On = False
            pass
        self.wbax.get_yaxis().set_tick_params(size=0,color='y')
        self.wbax.set_xlim(-1.5,1.5)
        self.wbax.get_yaxis().set_visible(False)

        # Set up standard atmosphere height scale on 
        # LHS of plot. It's jus
        majorLocatorKM   = MultipleLocator(2)
        majorLocatorKFT  = MultipleLocator(5)
        minorLocator     = MultipleLocator(1)

        self.htax=self.fig.add_axes([0.1,0.1,1e-6,0.8], sharey=self.skewxaxis, frameon=False)
        self.htax.xaxis.set_ticks([],[])
        self.htax.spines['left'].set_color('k')
        self.htax.spines['right'].set_visible(False)
        self.htax.get_yaxis().set_tick_params(size=0,color='y')
        self.htax.get_yaxis().set_visible(False)
        pres_heights = np.array( [self.data['hght'][np.argmin(np.abs(_ - self.data['pres']))] for _ in pres_levels] )
        for ph in range(pres_levels.shape[0]):
            self.htax.text(0, pres_levels[ph], '%d m'%pres_heights[ph], fontsize = 8)
        #print pres_heights

        # This is a hack for the xlabel not working!
        self.fig.text(0.40, 0.05, 'Temperature (%s)'%(degC), fontsize=12)

        self.fig.text(0.83, 0.9, 'Sounding Params')
        #$\underline{Sounding Params}$')
        #h0 = interp(0, self.data['temp'], self.data['hght'])
        h0 = self.data['hght'][np.argmin(abs(self.data['temp']-0))]
        h10 = self.data['hght'][np.argmin(abs(self.data['temp']+10))]
        h20 = self.data['hght'][np.argmin(abs(self.data['temp']+20))]
        h30 = self.data['hght'][np.argmin(abs(self.data['temp']+30))]
        h40 = self.data['hght'][np.argmin(abs(self.data['temp']+40))]
        lcl_height = 216*(self.data['temp'][0]-self.data['dwpt'][0])
        wcd = h0 - lcl_height
        mr = MixRatio(SatVap(self.data['dwpt']), self.data['pres']*100)
        pdiff = -1.0*np.diff(self.data['pres'])
        #print mr.shape, pdiff.shape
        # precipitable water
        pw = np.sum(np.array([mr[_]*100.0*pdiff[_]/9.8 for _ in range(pdiff.shape[0]) ]))
        # crude estimate of wet bulb temp
        ##tw = self.data['temp'][0]- (self.data['temp'][0]-self.data['dwpt'][0])/3.
        # now some shear calculations
        wspd6km = self.data['sknt'][np.argmin(abs(self.data['hght']-6000))]
        wdir6km = self.data['drct'][np.argmin(abs(self.data['hght']-6000))]

        udiff = wspd6km*np.cos(np.radians(270-wdir6km)) - self.data['sknt'][3]*np.cos(np.radians(270-self.data['drct'][3]))
        vdiff = wspd6km*np.sin(np.radians(270-wdir6km)) - self.data['sknt'][3]*np.sin(np.radians(270-self.data['drct'][3]))
        # print udiff, vdiff
        shear6km = np.sqrt(udiff**2 + vdiff**2)
        if (math.isnan(shear6km)):
            shear6km = 0

        # 850mb-200mb Shear
        wspd850mb = self.data['sknt'][np.argmin(abs(self.data['pres']-850))]
        wdir850mb = self.data['drct'][np.argmin(abs(self.data['pres']-850))]
        wspd200mb = self.data['sknt'][np.argmin(abs(self.data['pres']-200))]
        wdir200mb = self.data['drct'][np.argmin(abs(self.data['pres']-200))]

        udiff = wspd200mb*np.cos(np.radians(270-wdir200mb)) - wspd850mb*np.cos(np.radians(270-wdir850mb))
        vdiff = wspd200mb*np.sin(np.radians(270-wdir200mb)) - wspd850mb*np.sin(np.radians(270-wdir850mb))
        # print udiff, vdiff
        shear850200mb = np.sqrt(udiff**2 + vdiff**2)
        if (math.isnan(shear850200mb)):
            shear850200mb = 0

        # SFC-700mb Shear
        wspd700mb = self.data['sknt'][np.argmin(abs(self.data['pres']-700))]
        wdir700mb = self.data['drct'][np.argmin(abs(self.data['pres']-700))]

        udiff = wspd700mb*np.cos(np.radians(270-wdir700mb)) - self.data['sknt'][3]*np.cos(np.radians(270-self.data['drct'][3]))
        vdiff = wspd700mb*np.sin(np.radians(270-wdir700mb)) - self.data['sknt'][3]*np.sin(np.radians(270-self.data['drct'][3]))
        # print udiff, vdiff
        shear700mb = np.sqrt(udiff**2 + vdiff**2)
        if (math.isnan(shear700mb)):
            shear700mb = 0


        self.fig.text(0.84, 0.88, '0%s: %d m'%(degC, h0))
        self.fig.text(0.84, 0.86, '-10%s: %d m'%(degC, h10)) ### Move
        self.fig.text(0.84, 0.84, '-20%s: %d m'%(degC, h20))
        self.fig.text(0.84, 0.82, '-30%s: %d m'%(degC, h30)) ### Move
        self.fig.text(0.84, 0.80, '-40%s: %d m'%(degC, h40))
        self.fig.text(0.84, 0.78, 'LCL: %d m'%lcl_height)
        self.fig.text(0.84, 0.76, 'WCD: %d m'%wcd)
        self.fig.text(0.84, 0.74, 'PW: %.1f mm'%pw)
        self.fig.text(0.84, 0.72, '6 km shear: %d kts'%shear6km)
        self.fig.text(0.84, 0.68, '850-200mb shear: \n       %d kts'%shear850200mb) ### Move
        self.fig.text(0.84, 0.64, 'SFC-700mb shear: \n       %d kts'%shear700mb) ### Move
        # self.fig.text(0.84, 0.62, 'Trop: %d hPa'%(tropopause_pressure))
        

        self.fig.text(0.84, 0.20, 'Surface')
        self.fig.text(0.85, 0.18, 'P: %.1f hPa'%self.data['pres'][0])
        self.fig.text(0.85, 0.16, 'H: %d m'%(self.data['hght'][0]))

        self.fig.text(0.85, 0.14, 'T: %.1f %s'%(self.data['temp'][0], degC))
        self.fig.text(0.85, 0.12, 'T$_{D}$: %.1f %s'%(self.data['dwpt'][0], degC))
        ##self.fig.text(0.85, 0.10, 'T$_W$: %.1f %s'%(tw, degC))


        # now do the hodograph?
        self.hodoax = self.fig.add_axes([0.565, 0.68, 0.21, 0.21], frameon=True, polar=True)
        self.hodoax.xaxis.set_ticks([], [])
        self.hodoax.yaxis.set_ticks([], [])
        speed_mask = np.ma.masked_where(self.data['sknt'] > 999, self.data['sknt'])
        angle = 270 - self.data['drct']
        rad_angle = np.radians(angle)
        pres_mask = np.bitwise_and(self.data['pres'] > 200., self.data['drct'] < 361.) # only look at valid winds below 200 mb

        if self.fmt == 'UWYO':
            self.hodoax.plot(rad_angle, self.data['sknt'], c = 'red', linewidth = 3)

        else:
            round_val = 1000.0
            max_height = 12000
            rounded_height = round_val*np.round(self.data['hght'][pres_mask]/round_val)
            print rounded_height
            hodo_sc = self.hodoax.scatter(rad_angle[pres_mask], self.data['sknt'][pres_mask], c=rounded_height, \
            edgecolors='none', s=3, cmap=plt.cm.hsv, vmin=0, vmax=max_height)
            cb_ax = self.fig.add_axes([0.585, 0.665, 0.17, 0.005])
            hodo_cb = plt.colorbar(hodo_sc, cax=cb_ax, orientation='horizontal', fraction=0.06, pad=0.01, drawedges=False)
            hodo_cb.outline.set_visible(False)
            hodo_cb.ax.set_xticklabels((np.arange(0, max_height+round_val, round_val*2)/1000.0).astype(int))
            hodo_cb.ax.tick_params(labelsize=6, axis='x', which='both',length=0)

            # for label in hodo_cb.ax.get_xticks():
            #     label.set_visible(False)



        # legend_heights = np.arange(0, 12000, round_val)

        # legend_radius = 120
        # legend_angle_range = [30, 80]

        # legend_angles = np.linspace(legend_angle_range[0], legend_angle_range[1], len(legend_heights))
        # print 'legend angles: {}'.format(legend angles)

        # self.hodoax.scatter(legend_angles, np.zeros(len(legend_angles), float) + legend_radius, c=legend_heights, 
        #                                 edgecolors='none', s=10, cmap=plt.cm.jet_r, vmin=0, vmax=12000)



        self.hodoax.set_yticks(np.arange(0, 120, 25))
        self.hodoax.tick_params(labelsize=5)
        self.hodoax.set_xticks(np.arange(0, 2*np.pi, np.pi/2))
        self.hodoax.set_xticklabels([])
        self.hodoax.grid(True)
        try:
            self.hodoax.set_rlabel_position(180)
        except AttributeError:
            pass

    def calc_pw(self):
        mr = MixRatio(SatVap(self.data['dwpt']), self.data['pres']*100)
        pdiff = -1.0*np.diff(self.data['pres'])
        #print mr.shape, pdiff.shape
        # precipitable water
        pw = np.sum(np.array([mr[_]*100.0*pdiff[_]/9.8 for _ in range(pdiff.shape[0]) ]))
	return pw	


    def check_bottom_qc(self):
        # This is the check the first few obs to make sure there isn't anything weird at the surface
        pass

        diffs = {k: np.diff(v) for k, v in self.data.iteritems()}

        #print 'vals --> hght: {}, temp: {}, dwpt: {}'.format(self.data['hght'][:10], self.data['temp'][:10], self.data['dwpt'][:10])
        #print 'diffs --> hght: {}, temp: {}, dwpt: {}'.format(diffs['hght'][:10], diffs['temp'][:10], diffs['dwpt'][:10])


    def readfile(self, fname):
    #--------------------------------------------------------------------
    # This *should* be a convenient way to read a uwyo sounding
    #--------------------------------------------------------------------
        if self.fmt == 'UWYO': # READING IN STANDARD UNIVERSITY OF WYOMING FILES
            fid = open(fname)
            lines = fid.readlines()
            nlines = len(lines)
            ndata = nlines-34
            output = {}

            fields = lines[3].split()
            units = lines[4].split()

            # First line for WRF profiles differs from the UWYO soundings
            header = lines[0]
            if header[:5] == '00000':
            # WRF profile
                self.station = '-99999'
                self['Longitude'] = float(header.split()[5].strip(","))
                self['Latitude'] = float(header.split()[6])
                self.sounding_date = header.split()[-1]
            else:
                self.station = header[:5]
                dstr = (' ').join(header.split()[-4:])
                self.sounding_date = datetime.strptime(dstr, "%HZ %d %b %Y").strftime("%Y-%m-%d_%H:%M:%S") 

            if self.station_name is not None: self.station = self.station_name

            for ff in fields:
                output[ff.lower()]=zeros((nlines-34)) - 999.

            lhi=[1, 9,16,23,30,37,46,53,58,65,72]
            rhi=[7,14,21,28,35,42,49,56,63,70,77]

            lcounter = 5
            for line,idx in zip(lines[6:],range(ndata)):
                lcounter += 1

                try: output[fields[0].lower()][idx] = float(line[lhi[0]:rhi[0]])
                except ValueError: 
                    break

                for ii in range(1, len(rhi)):
                    try: 
            # Debug only:
            # print fields[ii].lower(), float(line[lhi[ii]:rhi[ii]].strip())
                        output[fields[ii].lower()][idx]=float(line[lhi[ii]:rhi[ii]].strip())
                    except ValueError: 
                        pass

            for field in fields:
                ff=field.lower()
                self.data[ff]=ma.masked_values(output[ff], -999.)

                return None

        elif self.fmt == 'EDT': # THIS IS FOR READING IN VAISALA EDITED DATA FILE FORMATS, FOR SPECIAL FIELD OPS SOUNDINGS
            rawfile = open(fname).readlines()


            try:
                serial_number = rawfile[1].split('#')[1].strip()
                self.station = '%s, %s'%(rawfile[0].split(':')[1].strip(), serial_number)
                time_string = ' '.join(rawfile[2].split(':')[1:]).strip()
                self.sounding_date = datetime.strptime(time_string, '%Y-%m-%d %H %M %S')

                self.station = self.fmt
                if self.station_name is not None: self.station = self.station_name
                self.station = '%s, %s'%(self.station, serial_number)

            except Exception:
                pass
                self.station = 'test'
                self.sounding_date = None

        # Let's try reading in the Header line to see if we can figure this out, and the skip_header
        # in the file_data line

            done = False

            # loop thru the file lines
            for il, line in enumerate(rawfile):
                if 'elapsed' in line.lower():
                    header_line = il
                    break
                else:
                    pass

            #print 'header line: {}'.format(header_line)
            #print rawfile[header_line].lower()
            header_split = rawfile[header_line].lower().split()
            print header_split

            htcol = header_split.index('heightmsl')
            prescol = header_split.index('p')
            tempcol = header_split.index('temp')
            dewcol = header_split.index('dewp')
            spdcol = header_split.index('speed')
            drctcol = header_split.index('dir')


            #if rawfile[4].split()[0] == 'Time':
            if 'time' in header_split:
                print 'Need to shift the columns'
                htcol -= 1; prescol -= 1; tempcol -= 1; dewcol -= 1; spdcol -= 1; drctcol -= 1


            print 'htcol: {}, prescol: {}, tempcol: {}, dewcol: {}, spdcol: {}, drctcol: {}'.format(
                                                htcol, prescol, tempcol, dewcol, spdcol, drctcol)

            file_data = np.genfromtxt(fname, skip_header=header_line+2)

            height = file_data[:,htcol]
            pres = file_data[:,prescol]
            temp = file_data[:,tempcol]
            dew = file_data[:,dewcol]
            wspd = file_data[:,spdcol]*1.94
            drct = file_data[:,drctcol]

            drct[drct > 360] = 0
            wspd[wspd > 999] = 0

            self.data = {'hght': height, 'pres': pres, 'temp': temp, 'dwpt': dew, 'sknt': wspd, 'drct': drct}



            return None


        elif self.fmt == 'raw': # THIS IS FOR READING IN VAISALA EDITED DATA FILE FORMATS, FOR SPECIAL FIELD OPS SOUNDINGS
            
        # def need to convert this stuff to pandas!

            rawfile = open(fname).readlines()


            try:
                serial_number = rawfile[1].split('#')[1].strip()
                self.station = '%s, %s'%(rawfile[0].split(':')[1].strip(), serial_number)
                time_string = ' '.join(rawfile[2].split(':')[1:]).strip()
                self.sounding_date = datetime.strptime(time_string, '%Y-%m-%d %H %M %S')

                self.station = self.fmt
                if self.station_name is not None: self.station = self.station_name
                self.station = '%s, %s'%(self.station, serial_number)

            except Exception:
                pass
                self.station = 'test'
                self.sounding_date = None

        # Let's try reading in the Header line to see if we can figure this out, and the skip_header
        # in the file_data line

            done = False

            # loop thru the file lines
            for il, line in enumerate(rawfile):
                if 'time' in line.lower():
                    header_line = il
                    break
                else:
                    pass


            nlines = len(rawfile)
            ndata = nlines-30
            print 'nlines: {}, ndata: {}'.format(nlines, ndata)


            #print 'header line: {}'.format(header_line)
            #print rawfile[header_line].lower()
            header_split = rawfile[header_line].lower().split()
            print header_split

            htcol = header_split.index('hgt/msl')
            prescol = header_split.index('pressure')
            tempcol = header_split.index('temp')
            dewcol = header_split.index('dewp')
            spdcol = header_split.index('speed')
            drctcol = header_split.index('dir')


            #if rawfile[4].split()[0] == 'Time':
            # if 'time' in header_split:
            #     print 'Need to shift the columns'
            htcol += 1; prescol += 1; tempcol += 1; dewcol += 1; spdcol += 1; drctcol += 1


            print 'htcol: {}, prescol: {}, tempcol: {}, dewcol: {}, spdcol: {}, drctcol: {}'.format(
                                                htcol, prescol, tempcol, dewcol, spdcol, drctcol)

            file_data = np.genfromtxt(fname, skip_header=header_line+6, skip_footer=20)

            height = file_data[:,htcol]
            pres = file_data[:,prescol]
            temp = file_data[:,tempcol]
            dew = file_data[:,dewcol]
            wspd = file_data[:,spdcol]*1.94
            drct = file_data[:,drctcol]

            drct[drct > 360] = 0
            wspd[wspd > 999] = 0

            self.data = {'hght': height, 'pres': pres, 'temp': temp, 'dwpt': dew, 'sknt': wspd, 'drct': drct}

            #print self.data

            return None



        elif self.fmt == 'EC':
            #print 'Canadian format'
            rawfile = open(fname).readlines()
            for il, line in enumerate(rawfile):
                if 'RS-Number' in line: serial_number = line.split(':')[-1].strip()
                if '*************' in line:
                    data_line = il
                    break
            self.station = self.fmt
            if self.station_name is not None: self.station = self.station_name
            self.station = '%s, %s'%(self.station, serial_number)

            sdata = np.genfromtxt(fname, skip_header = data_line+2)
            u = sdata[:,5]
            v = sdata[:,4]
            

            

            sounding_index = os.path.basename(fname).find('sounding')
            self.sounding_date = os.path.basename(fname)[sounding_index+9:sounding_index+21]
            #print self.sounding_date

            self.data = {'hght': sdata[:,6], 'pres': sdata[:,7], 'temp': sdata[:,2]-273.15, 'dwpt': sdata[:,8]-273.15,
                     'sknt': 1.94*np.sqrt(u**2+v**2), 'drct': 180.0/np.pi*np.arctan2(-u, -v)}


        elif self.fmt == 'lst':

                # this is the Argentine format for the RELAMPAGO field campaign
            print 'RELAMPAGO lst files'

            #data_list = []
            csv = pd.read_csv(fname, names=['pres', 'hght', 'temp', 'dwpt', 'drct', 'sknt'])

            csv_dict = csv.to_dict(orient='list')

            self.data = {k: np.array(v) for k, v in csv_dict.iteritems()}

            return self.data






        elif self.fmt == 'XML': # THIS IS FOR READING IN VAISALA EDITED DATA FILE FORMATS, FOR SPECIAL FIELD OPS SOUNDINGS
            import xml.etree.ElementTree as ET

            #################################
            ### Read in XML Sounding Data ###
            #################################
            tree = ET.parse(fname)
            root = tree.getroot()

            T = np.zeros(len(root))
            P = np.zeros(len(root))
            RH = np.zeros(len(root))
            ws = np.zeros(len(root))
            wd = np.zeros(len(root))
            Hgt = np.zeros(len(root))
            lon = np.zeros(len(root))
            lat = np.zeros(len(root))
            dt = []

            i = 0
            for rows in root.findall('Row'):
                T[i] = float(rows.attrib.get('Temperature'))
                P[i] = float(rows.attrib.get('Pressure'))
                RH[i] = float(rows.attrib.get('Humidity'))
                ws[i] = float(rows.attrib.get('WindSpeed')) ### Units????
                wd[i] = float(rows.attrib.get('WindDir'))
                Hgt[i] = float(rows.attrib.get('Height'))
                lon[i] = float(rows.attrib.get('Longitude'))
                lat[i] = float(rows.attrib.get('Latitude'))
                dt.append(rows.attrib.get('DataSrvTime'))
                i = i + 1


            #######################
            ### Manipulate Data ###
            #######################
            T = T - 273.15
            Td = DewPoint((RH/100.)*SatVap(T))
            ws /= 0.514           # m/s to knots

            year = dt[0][2:4]
            month = dt[0][5:7]
            day = dt[0][8:10]
            hour = dt[0][11:13]
            minute = dt[0][14:16]

            datestr = '20'+year+'-'+month+'-'+day+'_'+hour+minute

            self.station = 'SPURS2'
            self.sounding_date = datestr 
            self.lon = lon[0]
            self.lat = lat[0]

            self.data = {'hght': Hgt, 'pres': P, 'temp': T, 'dwpt': Td, 'sknt': ws, 'drct': wd}

#            print self.data

            return None    




    def lift_parcel(self,startp,startt,startdp, plotkey = False):
        """Lift a parcel to discover certain properties.


        INPUTS:
        startp:  Pressure (hPa)
        startt:  Temperature (C)
        startdp: Dew Point Temperature (C)
        """
        from numpy import interp

        #	print startp, startt, startdp
        assert startt >startdp, "Not a valid parcel. Check Td<Tc"
        Pres=linspace(startp, 50, 100)

        # Lift the dry parcel
        T_dry=(startt+273.15)*(Pres/startp)**(Rs_da/Cp_da)-273.15 

        #	print T_dry

        # Mixing ratio isopleth
        starte=SatVap(startdp)
        startw=MixRatio(starte,startp*100)
        e=Pres*startw/(.622+startw)
        T_iso=243.5/(17.67/log(e/6.112)-1)

        # Solve for the intersection of these lines (LCL).
        # interp requires the x argument (argument 2)
        # to be ascending in order!
        P_lcl=interp(0,T_iso-T_dry,Pres)
        T_lcl=interp(P_lcl,Pres[::-1],T_dry[::-1])

        col=[.6,.6,.6]

        # Plot traces below LCL
        if plotkey:
            self.skewxaxis.plot(T_dry[Pres>=P_lcl],Pres[Pres>=P_lcl],color=col,lw=2,)
            self.skewxaxis.plot(T_iso[Pres>=P_lcl],Pres[Pres>=P_lcl],color=col,lw=2,)
            self.skewxaxis.plot(T_lcl,P_lcl,ls='',marker='o',mec=col,mfc=col)

        # Now lift a wet parcel from the intersection point
        preswet=linspace(P_lcl, 100)
        tempwet=lift_wet(T_lcl, preswet)

        # Plot trace above LCL
        if plotkey:
            self.skewxaxis.plot(tempwet, preswet, color=col, lw=2,)

        # Add text to sounding
        #dtext ="Parcel\n"



        #dtext+="Ps:  %.1fhPa\n"%startp
        #dtext+="Ts:    %.1fC\n"%startt
        #dtext+="Ds:    %.1fC\n"%startdp
        #dtext+="Plcl: %.1fhPa\n"%P_lcl
        #dtext+="Tlcl:  %.1fC\n"%T_lcl


        #self.fig.text(0.83, 0.45, dtext, va='top')

        return Pres, T_dry, T_iso, preswet, tempwet

    def surface_parcel(self,mixdepth=100, pres_s = 1000.0): # added pres_s so can just change for diff regions
        """Returns parameters for a parcel initialised by:
        1. Surface pressure (i.e. pressure of lowest level)
        2. Surface temperature determined from max(theta) of lowest <mixdepth> mbar
        3. Dew point temperature representative of lowest <mixdepth> mbar

        Inputs:
        mixdepth (mbar): depth to average mixing ratio over
        """

        #	print 'mixdepth: ', mixdepth
        pres=self.data["pres"]
        temp=self.data["temp"]
        dwpt=self.data["dwpt"]

        # parcel pressure is surface pressure
        #	pres_s=pres[0]

        # identify the layers for averaging
        #	layers=pres>pres[0]-mixdepth
        # BF ABOVE IS OLD WAY, DOING IT NEW WAY

        # print pres_s
        # print pres
        # print mixdepth

        pres_s = np.max(pres)

        layers = pres>pres_s - mixdepth

        # average theta over mixheight to give
        # parcel temperature
        thta_mix=Theta(temp[layers]+273.15,pres[layers]*100.).max()
        temp_s=TempK(thta_mix,pres_s*100)-273.15

        # average mixing ratio over mixheight
        vpres=SatVap(dwpt)
        mixr=MixRatio(vpres,pres*100)
        mixr_mix=mixr[layers].mean()
        vpres_s=MixR2VaporPress(mixr_mix,pres_s*100)

        # surface dew point temp
        dwpt_s=DewPoint(vpres_s)

        return pres_s,temp_s,dwpt_s




def lift_wet(startt,pres):
#--------------------------------------------------------------------
# Lift a parcel moist adiabatically from startp to endp.
# Init temp is startt in C, pressure levels are in hPa    
#--------------------------------------------------------------------

    temp=startt
    t_out=zeros(pres.shape);t_out[0]=startt
    for ii in range(pres.shape[0]-1):
        delp=pres[ii]-pres[ii+1]
        temp=temp-100*delp*GammaW(temp+273.15,(pres[ii]-delp/2)*100)
        t_out[ii+1]=temp

    return t_out





if __name__=='__main__':

    sounding=Sounding("../examples/94975.2013070900.txt")
    sounding.make_skewt_axes()
    sounding.add_profile(color='r',lw=2)
    sounding.lift_parcel(1033.,10.7,-0.9)

    sounding.fig.savefig("../examples/94975.2013070900.png")
    show()


