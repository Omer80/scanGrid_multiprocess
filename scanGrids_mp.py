#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 25 19:06:04 2017

@author: ohm
"""
import os
import re
import subprocess
import multiprocessing as mp
import time as timer
import netCDF4
import numpy as np

def available_cpu_count():
    """ Number of available virtual or physical CPUs on this system, i.e.
    user/real as output by time(1) when called with an optimally scaling
    userspace-only program"""

    # cpuset
    # cpuset may restrict the number of *available* processors
    try:
        m = re.search(r'(?m)^Cpus_allowed:\s*(.*)$',
                      open('/proc/self/status').read())
        if m:
            res = bin(int(m.group(1).replace(',', ''), 16)).count('1')
            if res > 0:
                return res
    except IOError:
        pass

    # Python 2.6+
    try:
        import multiprocessing
        return multiprocessing.cpu_count()
    except (ImportError, NotImplementedError):
        pass

    # https://github.com/giampaolo/psutil
    try:
        import psutil
        return psutil.cpu_count()   # psutil.NUM_CPUS on old versions
    except (ImportError, AttributeError):
        pass

    # POSIX
    try:
        res = int(os.sysconf('SC_NPROCESSORS_ONLN'))

        if res > 0:
            return res
    except (AttributeError, ValueError):
        pass

    # Windows
    try:
        res = int(os.environ['NUMBER_OF_PROCESSORS'])

        if res > 0:
            return res
    except (KeyError, ValueError):
        pass

    # jython
    try:
        from java.lang import Runtime
        runtime = Runtime.getRuntime()
        res = runtime.availableProcessors()
        if res > 0:
            return res
    except ImportError:
        pass

    # BSD
    try:
        sysctl = subprocess.Popen(['sysctl', '-n', 'hw.ncpu'],
                                  stdout=subprocess.PIPE)
        scStdout = sysctl.communicate()[0]
        res = int(scStdout)

        if res > 0:
            return res
    except (OSError, ValueError):
        pass

    # Linux
    try:
        res = open('/proc/cpuinfo').read().count('processor\t:')

        if res > 0:
            return res
    except IOError:
        pass

    # Solaris
    try:
        pseudoDevices = os.listdir('/devices/pseudo/')
        res = 0
        for pd in pseudoDevices:
            if re.match(r'^cpuid@[0-9]+$', pd):
                res += 1

        if res > 0:
            return res
    except OSError:
        pass

    # Other UNIXes (heuristic)
    try:
        try:
            dmesg = open('/var/run/dmesg.boot').read()
        except IOError:
            dmesgProcess = subprocess.Popen(['dmesg'], stdout=subprocess.PIPE)
            dmesg = dmesgProcess.communicate()[0]

        res = 0
        while '\ncpu' + str(res) + ':' in dmesg:
            res += 1

        if res > 0:
            return res
    except OSError:
        pass

    raise Exception('Can not determine number of CPUs on this system')

def setup_p_a_scan(fname):
    """
    Opening an netCDF4 file
    """
    with netCDF4.Dataset("%s.nc"%fname, 'w', format='NETCDF4') as rootgrp:
        print "Configuring netCDF4 file."
        rootgrp.description = "p to theta grid scan dataset"
        rootgrp.history = "Created " + timer.ctime(timer.time())
        rootgrp.createDimension("x", 1024)
        rootgrp.createDimension('time', None)
        rootgrp.createDimension('p', None)
        rootgrp.createDimension('a', None)
        time = rootgrp.createVariable('time', 'f8', ('time',),zlib=True)
        time.units = "year"
        x = rootgrp.createVariable('x', 'f4', ('x',),zlib=True)
        p = rootgrp.createVariable('p', 'f4', ('p',),zlib=True)
        a = rootgrp.createVariable('a', 'f4', ('a',),zlib=True)
        x.units = "m"
        a.units = "nondim_strength"
        p.units = "nondim_mmtoyear"
        x[:] = np.linspace(0,100, 1024)
        print "Setting up 1D variables"
        rootgrp.createVariable('u', 'f8', ('p','a','time', 'x',),zlib=True)
    print "Output: netCDF file was created: ", fname+".nc"
    
def save_p_a_snapshot(fname,pstep,astep,tstep,p,a,time,u):
    """ Save snapshot of u
    """
    with netCDF4.Dataset("%s.nc"%fname, 'a') as rootgrp:
        rootgrp['time'][tstep] = time
        rootgrp['p'][pstep] = p
        rootgrp['a'][astep] = a
        rootgrp['u'][pstep,astep,tstep,:] = u

def run_sim_for_p_a(p,a,pstep,astep,step,max_time,u0,fname):
    time_ar=np.arange(0,max_time,step)
    u = np.ones((len(time_ar),1024))
    u[0]=u0
    print "Calculating for p,a:",p,a
    for i,t in enumerate(time_ar[1:]):
        u[i+1] = u[i]*np.cos(t)*np.sin(a)*np.sin(p)
    for tstep,t in enumerate(time_ar):
        save_p_a_snapshot(fname,pstep,astep,tstep,p,a,t,u[tstep])
        
def apply_async_and_save_grid(pmin,pmax,fname,
                              Np=10,Na=10,
                              step=None,max_time=500.0,numproc=10):
    start = timer.time()
    setup_p_a_scan(fname)
    if step is None:
        step=max_time
    p_range = np.linspace(pmin,pmax,Np)
    init = np.random.random((1024))
    a_range = np.linspace(0,1,Na)
    availble_cpus = int(available_cpu_count() - 2)
    numproc=min(numproc,availble_cpus)
    print "Using",numproc," processors"
    pool = mp.Pool(processes=numproc)
    for i,p in enumerate(p_range):
        for j,a in enumerate(a_range):
            pool.apply_async(run_sim_for_p_a,
                             args = (p,a,i,j,step,max_time,init,fname))
    pool.close()
    pool.join()
    print "Took ",timer.time()-start


if __name__ == '__main__':
    pass