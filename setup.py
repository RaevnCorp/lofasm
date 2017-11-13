#!/usr/bin/python


from distutils.core import setup

setup(
    name='lofasm',
    version='0.1',
    author=['Louis P. Dartez', 'Jing Luo', 'LoFASM Data Analysis Team'],
    author_email='louis.dartez@gmail.com',

    packages=['lofasm', 'lofasm.simulate', 'lofasm.bbx', 'lofasm.formats',
              'lofasm.clean', 'lofasm.data_file_info', 'lofasm.calibrate'],
              
    scripts=['bin/lofasm_plot.py',
             'bin/simulate_signal_as_AA.py',
             'bin/simulate_zeros_as_AA.py',
             'bin/lofasm-chop.py',
             'bin/LoFASM_GUI.py',
             'bin/lofasm2fi3l.py',
             'bin/fbplot.py',
             'bin/applyDelay.py',
             'bin/lofasm2d.py',
             'bin/lightcurve.py',
             'bin/skymap.py',
             'bin/readfile.py',
             'bin/waterfall.py',
             'bin/stethoscope.py',
             'bin/loco2bx.py',
             'bin/lofasm_check_files.py',
             'bin/lofasm2csv.py',
             'bin/simulate_dispered_filterbank.py',
             'bin/cleanfile.py',
             'bin/normalize_data.py',
             'bin/clean_data.py',
             'bin/plotbbx.py'],
             
    description='LoFASM Tools',
    long_description=open('README.md').read(),
    install_requires=[
        "matplotlib >= 1.1.1",
        "numpy >= 1.6.2",
        "scipy",
        "astropy"],
)
