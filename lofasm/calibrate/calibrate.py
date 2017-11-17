#!/usr/bin/python
#Calibration tool

if __name__ == "__main__":

    import argparse, os
    import lofasmcal as lfc
    import numpy as np

    #Parse arguments
    ap = argparse.ArgumentParser()
    ap.add_argument('files', type=str, help='path to files')
    ap.add_argument('freq', type=float, help='frequency in MHz') #Freq in MHz
    ap.add_argument('station', type=int, help='LoFASM station number')
    ap.add_argument('-v', help='increase verbosity', action='store_true')
    args = ap.parse_args()

    v = args.v
    files = args.files
    freq = args.freq
    station = args.station

    #Read data from files
    dh = lfc.data_handler()
    dh.read_files(files, freq, verbose=v)

    if len(dh.filelist) == 0:
        raise ValueError('No LoFASM files found')

    #Generate galaxy models
    gal = lfc.galaxy()
    g_power = gal.galaxy_power_array(dh.times_array, freq, station, verbose=v)

    #Fit data to model -> get calibration parameters
    fit = lfc.fitter(dh.data, g_power)
    cal_pars = fit.cal_pars()

    #Write calpars file
    path = os.path.dirname(dh.filelist[0])
    cf = lfc.calfile()
    cf.write_calfile(dh.filelist, dh.freqmhz, cal_pars)

    print cal_pars
