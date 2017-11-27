#!/usr/bin/env python
# Converts .lofasm files to .bbx or .abx files.
# Run with option -h or --help for full usage information.

# Constants
version = 1.0
mjd_epoch = 2451545  # J2000 epoch
mjd_offset = 2400000 # Entries in LoCo files subtracted this from JD
polarizations = "AA,BB,CC,DD,AB,AC,AD,BC,BD,CD"

# Imports
from lofasm import parse_data as pdat
import struct, os, sys, argparse, time, array, shutil
import gzip
from astropy.time import Time
from datetime import datetime
from lofasm.parse_data import IntegrationError

start = time.time()

# Functions
hexlookup = [None]*256
for i in range( 0, 16 ):
    if i < 10:
        ci = chr( ord( '0' ) + i )
    else:
        ci = chr( ord( 'A' ) + i - 10 )
    for j in range( 0, 16 ):
        if j < 10:
            cj = chr( ord( '0' ) + j )
        else:
            cj = chr( ord( 'A' ) + j - 10 )
        pair = ci + cj
        hexlookup[16*i+j] = pair

def hexwrite( fo, string ):
    """Write a string of bytes as hexadecimal pairs "00" through "FF".

    The first argument should be an open writable file object.  The
    second should be a string, interpreted as a list of bytes.
    Linebreaks are inserted after every 80 characters of output.

    """
    n = 0
    for b in string:
        fo.write( hexlookup[ ord( b ) ] )
        n += 2
        if n >= 80:
            fo.write( "\n" )
            n = 0
    return

# Set up argument parser.
parser = argparse.ArgumentParser(
    description = "Convert .lofasm files to .abx or .bbx format.",
    epilog = "Each <basename>.lofasm file will generate up to "
    + "{}".format( len( polarizations.split( ',' ) ) ) + " output "
    + "files of the form <basename>_<xy>.abx or <basename>_<xy>.bbx, "
    + "where <xy> are any of the polarization pairs in '"
    + polarizations + "'.  The --pols option can restrict (or expand) "
    + "this list."
)
parser.add_argument( "files", metavar = "INFILE", nargs = '+',
                    help = "a .lofasm input file" )
parser.add_argument( "-a", "--ascii", action = "store_true",
                     help = "write ASCII .abx files" )
parser.add_argument( "-f", "--force", action = "store_true",
                     help = "overwrite existing files" )
parser.add_argument( "-p", "--pols", action = "store", default = polarizations,
                     help = "specify subset of polarizations, "
                     + "e.g. 'AA,BB,AB'" )

# Process arguments.
args = parser.parse_args()
pols = args.pols.split( ',' )

# Loop over files.
nin = 0  # files processed
nout = 0 # files written
for inname in args.files:

    # Check input file name
    filepols = list( pols )
    splitname = os.path.splitext( inname )
    if splitname[1] != ".lofasm" and splitname[1] != '.gz':
        print "Skipping " + inname + " (not a .lofasm file)"
        continue

    EOF_REACHED = False
    subfile_id = 0

    # Open file and read metadata.
    try:
        crawler = pdat.LoFASMFileCrawler( inname )
        crawler.open()
        header = crawler.getFileHeader()
        tstart = crawler.time_start.datetime.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    except:
        print "Skipping " + inname + " (unable to read metadata)"
        continue
    nin += 1

    # Store header metadata in local variables.
    for key in header.keys():
        field = header[key]
        if field[0] == "station":
            station = field[1]
        elif field[0] == "Nbins":
            nbins = long( field[1] )
        elif field[0] == "fstart":
            fstart = float( field[1] )
        elif field[0] == "fstep":
            fstep = float( "0." + field[1] )*1e6
        elif field[0] == "mjd_day":    # mjd value will be different for each subfile
            mjd_day = int( field[1] )
        elif field[0] == "mjd_msec":
            mjd_msec = float( field[1] )
        elif field[0] == "int_time":
            int_time = float( field[1] )

    ## THROW AWAY THE EMPTY HALF OF THE FREQUENCY BINS 
    nbins = nbins//2
    ##

    while not EOF_REACHED:
        nint = 0 # new subfile
        if subfile_id > 0:
            try:
                crawler.moveToNextBurst()
                t = crawler.time
                t = Time(t) #astropy time object
                mjd = t.mjd
                mjd_day = int(mjd)
                mjd_msec = (mjd-mjd_day) * 8.64e+7
            except EOFError:
                EOF_REACHED = True

        # Compute offset and integration times in seconds
        toff = long( mjd_day ) - ( mjd_epoch - mjd_offset )
        toff *= 86400.0
        toff += float( mjd_msec )*0.001
        int_time *= 1.0;  # since we're keeping things in seconds

        # Set up some more constants for this file.
        realfmt = 'd'*nbins           # Format for struct.pack() on real data
        cplxfmt = 'd'*( 2*nbins )     # Format for struct.pack() on complex data
        cplxbuf = [ 0.0 ]*( 2*nbins ) # Flattened complex list

        # Open data files for each polarization.
        datfiles = {}
        tstart_str = crawler.time.datetime.strftime("%Y%m%d_%H%M%S")
        tstart = tstart_str # for compatibility / laziness
        print "Starting subfile: ", tstart        
        for pol in filepols:
            if args.ascii:
                outname = tstart_str + "_" + pol + ".abx"
            else:
                outname = tstart_str + "_" + pol + ".bbx"
            if os.path.isfile( outname ) and not args.force:
                print "Skipping " + outname + " (output file exists)"
                filepols.remove( pol )
            else:
                try:
                    datfile = open( tstart_str + "_" + pol + ".dat", "wb" )
                    datfiles[pol] = datfile
                except:
                    print "Skipping " + outname + " (could not open data file)"
                    filepols.remove( pol )

        # Loop over integrations.
        #for k in range( 0, nint-1):
        EOF_SUBFILE = False
        while not EOF_SUBFILE:
            # Loop over polarizations.
            for pol in filepols:

                # Get open data file, or skip to next.
                try:
                    datfile = datfiles[pol]
                except:
                    continue

                # Get the data.
                try:
                    crawler.setPol( pol )
                    fdata = crawler.get()[:nbins]
                except:
                    datfile.close()
                    try:
                        os.remove( tstart_str + "_" + pol + ".dat" )
                    except:
                        pass
                    del datfiles[pol]
                    continue

                # Write this integration to data file.
                if pol[0] == pol[1]:
                    if args.ascii:
                        hexwrite( datfile, struct.pack( realfmt, *fdata ) )
                        datfile.write( "\n" )
                    else:
                        datfile.write( struct.pack( realfmt, *fdata ) )
                else:
                    i = 0;
                    for f in fdata:
                        cplxbuf[i] = f.real
                        cplxbuf[i+1] = f.imag
                        i += 2
                    if args.ascii:
                        hexwrite( datfile, struct.pack( cplxfmt, *cplxbuf ) )
                        datfile.write( "\n" )
                    else:
                        datfile.write( struct.pack( cplxfmt, *cplxbuf ) )

            # End loop over polarizations.
            
            # Advance to next integration.
            try:
                crawler.forward( 1 )
                nint += 1
            except IntegrationError: # encountered corrupt data
                EOF_SUBFILE = True
            except EOFError:
                EOF_SUBFILE = True
                EOF_REACHED = True
        print "Closing subfile {} with {} integrations.".format(tstart, nint)
        
        # Close data files.
        for datfile in datfiles:
            datfiles[datfile].close()
        # End loop over integrations.


        # Write header files and concatenate.
        for pol in filepols:
            if args.ascii:
                outname = tstart_str + "_" + pol + ".abx.gz"
            else:
                outname = tstart_str + "_" + pol + ".bbx.gz"
            try:
                hdrfile = open( tstart_str + "_" + pol + ".hdr", "wb" )
            except:
                print "Skipping " + outname + " (could not open header file)"
                continue
            if args.ascii:
                hdrfile.write( "%ABX\n" )
            else:
                hdrfile.write( "%\x02BX\n" )
            hdrfile.write( "%hdr_type: LoFASM-filterbank\n" )
            hdrfile.write( "%hdr_version: " )
            hexwrite( hdrfile, struct.pack( "f", version ) )
            hdrfile.write( "\n" )
            hdrfile.write( "%station: {}\n".format( station ) )
            hdrfile.write( "%channel: {}\n".format( pol ) )
            hdrfile.write( "%start_time: {}\n".format( tstart ) )
            hdrfile.write( "%time_offset_J2000: 0 (s)\n" )
            hdrfile.write( "%frequency_offset_DC: 0 (Hz)\n" )
            hdrfile.write( "%dim1_label: time (s)\n" )
            hdrfile.write( "%dim1_start: {}\n".format( toff ) )
            hdrfile.write( "%dim1_span: {}\n".format( int_time*nint ) ) 
            hdrfile.write( "%dim2_label: frequency (Hz)\n" )
            hdrfile.write( "%dim2_start: {}\n".format( fstart ) )
            hdrfile.write( "%dim2_span: {}\n".format( fstep*nbins ) )
            if pol[0] == pol[1]:
                hdrfile.write( "%data_label: power spectrum (arbitrary)\n" )
            else:
                hdrfile.write( "%data_label: cross spectrum (arbitrary)\n" )
            hdrfile.write( "%data_offset: 0\n" )
            hdrfile.write( "%data_scale: 1\n" )
            hdrfile.write( "%data_type: real64\n" )
            hdrfile.write( "{} {} ".format( nint, nbins ) )
            if pol[0] != pol[1]:
                hdrfile.write( "2 " )
            else:
                hdrfile.write( "1 " )
            if args.ascii:
                hdrfile.write( "64 raw16\n" )
            else:
                hdrfile.write( "64 raw256\n" )
            hdrfile.close()

            # Merge header and data files.
            if os.path.isfile( outname ) and args.force:
                os.remove( outname )
            try:
                hdrfile = open( tstart_str + "_" + pol + ".hdr", "rb" )
                datfile = open( tstart_str + "_" + pol + ".dat", "rb" )
                outfile = gzip.open( outname, "wb" ) #gzip'd output file
            except:
                print "Skipping " + outname + " (could not open file)"
                continue
            try:
                shutil.copyfileobj( hdrfile, outfile )
                shutil.copyfileobj( datfile, outfile )
                hdrfile.close()
                datfile.close()
                outfile.close()
            except:
                print "Skipping " + outname + " (could not write file)"
                continue
            nout += 1
            try:
                os.remove( tstart_str + "_" + pol + ".hdr" )
                os.remove( tstart_str + "_" + pol + ".dat" )
            except:
                print "Keeping " + outname + " hdr/dat files (could not delete)"
        # End loop over polarizations.
        subfile_id += 1
# End loop over input files.

# Finihsed
stop = time.time()
print "Processed {} input files, {} output files, in {} seconds".format(
    nin, nout, stop - start )
