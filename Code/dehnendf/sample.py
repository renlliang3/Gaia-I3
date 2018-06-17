"""
Filename: sample.py
Author: Mathew Bub
Last Revision Date: 2018-06-16

This module contains functions used to generate mock data using Dehnen DF.
The functions initially generate random sample stars in 2D, before adding a
z component to each star. This somewhat generalizes Dehnen DF to 3D. 
"""
import os
import time
import copy
import numpy as np
from galpy.df import dehnendf
from galpy.orbit import Orbit
from galpy.potential import MWPotential2014
from galpy.util.bovy_conversion import time_in_Gyr

def get_samples_with_z(n=1, r_range=None, integration_time=1, 
                       integration_steps=100):
    """
    NAME:
        get_samples_with_z
    
    PURPOSE:
        sample stars with R, vR, and vT using Dehnen DF, then add a z and vz
        component to each sampled star
        
    INPUT:
        n - number of samples to generate (optional; default = 1)
        
        r_range - radial range in kpc in which to sample stars; if None, will 
        sample stars at any radius (optional; default = None)
        
        integration_time - length of time to integrate orbits in Gyr; used for
        adding a z component to each star (optional; default = 1)
        
        integration_steps - number of steps to use in the orbit integration
        (optional; default = 100)
        
    OUTPUT:
        list of integrated galpy.orbit.Orbit objects containing R, vR, vT, z,
        and vz values, representing sampled stars
    """
    import warnings
    warnings.filterwarnings('ignore')
    
    # estimate completion time for larger samples
    estimate_time = (n >= 1000)
    
    print('sampling orbits...')
    if estimate_time:
        average_time = get_average_sample_time(r_range=r_range)
        time_str = estimate_completion_time(n, average_time)
        print('estimated time of completion: ' + time_str)
        
    # convert r_range to natural units
    if r_range is not None:
        r_range = [r/8. for r in r_range]
        
    # sample R, vR, and vT over r_range
    df = dehnendf()
    sampled_ROrbits = df.sample(n=n, rrange=r_range)
    
    print('done at ' + time.strftime('%H:%M:%S', time.localtime()))
    
    # get the R, vR, and vT values from each sampled orbit
    R = np.array([o.R() for o in sampled_ROrbits])
    vRz = np.array([o.vR() for o in sampled_ROrbits])
    vT = np.array([o.vT() for o in sampled_ROrbits])
    
    # divide radial kinetic energy evenly between the R and z directions
    kRz = vRz**2/2
    kR = kRz * np.random.random(n)
    kz = kRz - kR
    
    # convert kinetic energy to velocities, choosing a random starting 
    # direction for vz and retaining the original direction of vR
    vR = np.sqrt(2*kR) * np.sign(vRz)
    vz = np.sqrt(2*kz) * np.random.choice((1, -1), size=n)
    
    # create new orbit objects containing R, vR, vT, z, and vz
    vxvv = [[R[i], vR[i], vT[i], 0, vz[i]] for i in range(n)]
    orbits = [Orbit(vxvv=vxvv[i]) for i in range(n)]
    
    # integrate the orbits for integration_time Gyr
    t = np.linspace(0, integration_time/time_in_Gyr(vo=220., ro=8.), 
                    integration_steps)
    
    print('\nintegrating orbits...')
    if estimate_time:
        average_time = get_average_integration_time(orbits, t)
        time_str = estimate_completion_time(n, average_time)
        print('estimated time of completion: ' + time_str)
        
    for o in orbits:
        o.integrate(t, MWPotential2014)
        
    print('done at ' + time.strftime('%H:%M:%S', time.localtime()))
    
    return orbits

def distribute_over_phi_range(sampled_orbits, phi_range):
    """
    NAME:
        distribute_over_phi_range
        
    PURPOSE:
        uniformly distribute the orbits generated by get_samples_with_z over a 
        certain phi range
        
    INPUT:
        sampled_orbits - galpy.orbit.Orbit objects returned by 
        get_samples_with_z
        
        phi_range - phi range in radians over which to distribute the samples
    
    OUTPUT:
        list of galpy.orbit.Orbit objects containing R, vR, vT, z, vz, and phi,
        representing sampled stars distributed over phi_range
    """
    # get a uniform distribution of phis
    phi = np.random.uniform(*phi_range, len(sampled_orbits))
    
    # add the new phi values to the sampled orbits
    vxvv = np.stack([o.getOrbit()[-1] for o in sampled_orbits], axis=0)
    vxvv = np.concatenate((vxvv, phi.reshape((-1, 1))), axis=1)
    
    # create new orbit objects containing R, vR, vT, z, vz, and phi
    orbits_with_phi = [Orbit(vxvv=vxvv[i]) for i in range(len(sampled_orbits))]
    return orbits_with_phi

def generate_sample_data(n, phi_range, r_range=None):
    """
    NAME:
        generate_sample_data
        
    PURPOSE:
        generate a sample of stars using Dehnen DF
        
    INPUT:
        n - number of samples to generate
        
        phi_range - phi range in radians over which to distribute the samples
        
        r_range - radial range in kpc in which to sample stars; if None, will 
        sample stars at any radius (optional; default = None)
        
    OUTPUT:
        None (saves samples to the data directory)
    """
    # sample orbits over r_range and phi_range
    orbits = get_samples_with_z(n=n, r_range=r_range)
    orbits = distribute_over_phi_range(orbits, phi_range)
    
    # return in physical units
    for o in orbits:
        o.turn_physical_on()
    
    # organize the data into an nx6 array of galactocentric coordinates
    samples = np.stack([[o.x(), o.y(), o.z(), o.vx(), o.vy(), o.vz()] 
                        for o in orbits], axis=0)
    
    # create a directory to hold the samples
    if not os.path.exists('data'):
        os.mkdir('data')
    
    # choose a file name representing the chosen parameters
    if r_range is not None:
        filename = ('{}samples_{}-{}deg_{}-{}kpc'
                    ).format(n, *phi_range, *r_range)
    else:
        filename = '{}samples_{}-{}deg'.format(n, *phi_range)
        
    np.save('data/' + filename, samples)
    
def load_samples(n, phi_range, r_range=None):
    """
    NAME:
        load_samples
        
    PURPOSE:
        load a sample of stars; if the sample does not exist in the data
        directory, generate it first
        
    INPUT:
        n - number of samples to generate
        
        phi_range - phi range in degrees over which to distribute the samples
        
        r_range - radial range in kpc in which to sample stars; if None, will 
        sample stars at any radius (optional; default = None)
        
    OUTPUT:
        nx6 array of rectangular galactocentric coordinates of the form 
        (x, y, z, vx, vy, vz) in [kpc, kpc, kpc, km/s, km/s, km/s],
        representing sampled stars
    """
    # choose a file name representing the chosen parameters
    if r_range is not None:
        filename = ('{}samples_{}-{}deg_{}-{}kpc.npy'
                    ).format(n, *phi_range, *r_range)
    else:
        filename = '{}samples_{}-{}deg.npy'.format(n, *phi_range)
        
    # check if the file already exists
    if not os.path.exists('data/' + filename):
        # generate the file if it does not exist
        generate_sample_data(n=n, phi_range=phi_range, r_range=r_range)
        
    # load the samples
    samples = np.load('data/' + filename)
    return samples

def get_average_sample_time(r_range=None):
    """
    NAME:
        get_average_sample_time
        
    PURPOSE:
        estimate the average time to sample orbits in r_range
        
    INPUT:
        r_range - radial range in kpc in which to sample stars; if None, will 
        sample stars at any radius (optional; default = None)
        
    OUTPUT:
        average sample time
    """
    import warnings
    warnings.filterwarnings('ignore')
    
    if r_range is not None:
        r_range = [r/8. for r in r_range]
    
    df = dehnendf()
    
    # get time to sample 100 stars
    start = time.process_time()
    df.sample(n=100, rrange=r_range)
    end = time.process_time()
    
    return (end-start)/100

def get_average_integration_time(orbits, t):
    """
    NAME:
        get_average_integration_time
        
    PURPOSE:
        estimate the average time to integrate an orbit over time t
        
    INPUT:
        orbits - the orbits that are to be integrated
        
        t - numpy.linspace representing the time over which to integrate
        
    OUTPUT:
        average integration time of a random sample of orbits
    """
    # get a random sample of 100 stars from orbits
    samples = copy.deepcopy(np.random.choice(orbits, size=100, replace=False))
    
    # get time to integrate the random sample
    start = time.process_time()
    for o in samples:
        o.integrate(t, MWPotential2014)
    end = time.process_time()
    
    return (end-start)/100

def estimate_completion_time(n, average_time):
    """
    NAME:
        estimate_completion_time
        
    PURPOSE:
        return the estimated completion time of n iterations of a process that
        takes average_time per iteration
        
    INPUT:
        n - number of iterations
        
        average_time - average time to complete each iteration
        
    OUTPUT:
        string representing estimated time of completion; if the completion
        time is more than 24 hours in the future, also output the date of
        completion
    """
    time_format = '%H:%M:%S'
    
    # add date to output if completion time is more than 24 hours away
    if average_time * n > 86400:
        time_format = '%d %b ' + time_format
        
    # estimate completion time
    completion_time = time.time() + average_time * n
    
    time_str = time.strftime(time_format, time.localtime(completion_time))
    return time_str