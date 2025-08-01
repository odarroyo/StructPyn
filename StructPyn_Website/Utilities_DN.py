# ====================================================================================================================
# ================================================ IMPORTAR LIBRERIAS ================================================ 
# ====================================================================================================================
# Flask web framework imports for web application functionality
from flask import Flask, render_template,request,session,redirect
# Django configuration imports for static file handling
from django.conf import settings
from django.conf.urls.static import static
# OpenSeesPy imports for structural analysis
from openseespy.opensees import *
import opseestools.utilidades as ut

# Standard library and scientific computing imports
import os
import numpy as np
# Matplotlib configuration for non-interactive plotting
import matplotlib
matplotlib.use('Agg')  # Set backend to 'Agg' for GUI-less rendering
import matplotlib.pyplot as plt
import opsvis as opsv  # OpenSees visualization tools
from PIL import Image  # Python Imaging Library


# ====================================================================================================================
# ======================================== GENERADOR DE SECCIONES (COLUMNAS) ========================================= 
# ====================================================================================================================

def fiber_elemens_Columns(BCol, HCol, c, cT, cM, cB, nT, nM, nB, fc, Fy, yloc):
    """
    Generate fiber element sections for reinforced concrete columns using OpenSees.
    
    This function creates a fiber section model for reinforced concrete columns with 
    confined and unconfined concrete materials and steel reinforcement bars distributed 
    in top, middle, and bottom regions.
    
    Parameters
    ----------
    BCol : float
        Column base width in meters
    HCol : float
        Column height in meters
    c : float
        Concrete cover thickness in meters
    cT : list
        Number of top reinforcement bars for each bar configuration
    cM : list
        Number of middle reinforcement bars for each bar configuration
    cB : list
        Number of bottom reinforcement bars for each bar configuration
    nT : list
        Bar numbers (diameter in eighths of inch) for top reinforcement
        Valid values: 'barnum3', 'barnum4', 'barnum5', 'barnum6', 'barnum7', 'barnum8'
    nM : list
        Bar numbers (diameter in eighths of inch) for middle reinforcement
    nB : list
        Bar numbers (diameter in eighths of inch) for bottom reinforcement
    fc : float
        Concrete compressive strength f'c in KPa
    Fy : float
        Steel yield strength fy in KPa
    yloc : list
        Y coordinates of each node in the structure
        
    Returns
    -------
    tuple
        - sec1 : list
            OpenSees fiber section definition commands
        - tag1 : int
            Section tag number (10)
            
    Notes
    -----
    - Creates materials for confined concrete (tag 1), unconfined concrete (tag 3), 
      and steel (tag 5)
    - Uses Concrete02 material model with fracture energy regularization
    - Uses Hysteretic material model for steel with Dhakal degradation parameters
    - Automatically calculates reinforcement distribution and spacing
    
    Examples
    --------
    >>> BCol, HCol, c = 0.4, 0.4, 0.04
    >>> cT, cM, cB = [4], [2], [4]
    >>> nT, nM, nB = ['barnum4'], ['barnum4'], ['barnum4']
    >>> fc, Fy = 25000, 420000
    >>> yloc = [0, 3, 6, 9]
    >>> section, tag = fiber_elemens_Columns(BCol, HCol, c, cT, cM, cB, nT, nM, nB, fc, Fy, yloc)
    """

    # Calculate story heights from node coordinates and determine median column length
    ylist = [np.around(yloc[i+1]-yloc[i], 2) for i in range(len(yloc)-1)]
    pint = 5  # Number of integration points for fracture energy calculation
    Lcol = np.median(ylist) * 1000  # Convert median height to mm for calculations
    
    # --------------------------------- Material Tags Definition --------------------------------
    Col_Conf = 1    # Confined concrete material tag
    Col_Unconf = 3  # Unconfined concrete material tag
    Steel = 5       # Steel material tag
    
    # --------------------------------- Unconfined Concrete Material --------------------------------
    # Calculate elastic modulus using ACI formula: E = 4400*sqrt(fc) MPa
    E = 4400 * (fc/1000)**0.5 * 1000  # Convert fc to MPa, then back to kPa
    ec = 2 * fc / E  # Peak strain for unconfined concrete (typically ~0.002)
    fcu = 0.2 * fc   # Ultimate strength (20% of peak strength)
    Gfc = fc / 1000  # Fracture energy in N/mm (simplified assumption)
    
    # Calculate ultimate strain using fracture energy regularization
    e20 = ut.e20Lobatto2(Gfc, Lcol, pint, fc/1000, E/1000, ec)
    # Create unconfined concrete material using Concrete02 model
    uniaxialMaterial('Concrete02', Col_Unconf, -fc, -ec, -fcu, -e20)
    
    # --------------------------------- Confined Concrete Material -----------------------------------
    k = 1.3  # Confinement factor for columns (30% strength increase)
    fcc = fc * k     # Confined concrete strength
    ecc = 2 * fcc / E  # Peak strain for confined concrete
    fucc = 0.2 * fcc   # Ultimate strength for confined concrete
    Gfcc = 2 * (fcc / 1000)  # Higher fracture energy for confined concrete
    
    # Calculate ultimate strain for confined concrete
    e20cc = ut.e20Lobatto2(Gfcc, Lcol, pint, fcc/1000, E/1000, ecc)
    # Create confined concrete material
    uniaxialMaterial('Concrete02', Col_Conf, -fcc, -ecc, -fucc, -e20cc)
    
    # ---------------------------------------- Steel Material -----------------------------------------
    Es = 210000000.0  # Steel elastic modulus in Pa (210 GPa)
    
    # Generate steel stress-strain curve using Dhakal degradation model
    # Parameters: fy, fu, esh, esu, esp, alpha, beta
    s, e = ut.dhakal(Fy/1000, Fy/1000*1.5, 0.002, 0.01, 0.1, 96, 12)
    # Create hysteretic steel material with degradation parameters
    uniaxialMaterial('Hysteretic',Steel,s[0],e[0],s[1],e[1],s[3],e[3],s[4],e[4],s[5],e[5],s[7],e[7],1.0,1.0,0.0,0.0)

    # --------------------------------- Section Geometry Calculations --------------------------------
    y1col = HCol / 2.0  # Half height of column section
    z1col = BCol / 2.0  # Half width of column section
    
    # Fiber discretization parameters
    nFibZ = 1        # Number of fibers in Z direction for edge patches
    nFib = 20        # Number of fibers for unconfined concrete patches
    nFibCover = 3    # Number of fibers in cover concrete
    nFibZcore = 10   # Number of fibers in Z direction for core
    nFibCore = 16    # Number of fibers for confined core

    # Bar area dictionary - areas in m² for different bar sizes
    bar_areas = {
        'barnum3': 0.000071,  # #3 bar (9.5mm diameter)
        'barnum4': 0.000127,  # #4 bar (12.7mm diameter)
        'barnum5': 0.000198,  # #5 bar (15.9mm diameter)
        'barnum6': 0.000286,  # #6 bar (19.1mm diameter)
        'barnum7': 0.000387,  # #7 bar (22.2mm diameter)
        'barnum8': 0.000508   # #8 bar (25.4mm diameter)
    }

    # Convert bar numbers to areas for each reinforcement layer
    nTlist = [bar_areas[bar] for bar in nT]  # Top bar areas
    nBlist = [bar_areas[bar] for bar in nB]  # Bottom bar areas
    nMlist = [bar_areas[bar] for bar in nM]  # Middle bar areas

    # Calculate total number of bars and positioning
    NMiddle = sum(cM)  # Total middle bars
    NpMdd = (NMiddle // 2) + (NMiddle % 2)  # Number of middle bar positions (pairs + odd)

    NTop = sum(cT)  # Total top bars
    NpTop = [(ct // 2) + (ct % 2) for ct in cT]  # Top bar positions for each configuration
    
    NBtt = sum(cB)  # Total bottom bars
    NpBtt = [(cb // 2) + (cb % 2) for cb in cB]  # Bottom bar positions for each configuration

    # --------------------------------- Fiber Section Definition --------------------------------
    tag1 = 10  # Section tag number
    # Initialize section array: 6 patches + all bar layers
    sec1 = [0] * (6 + sum(NpTop) + sum(NpBtt) + NpMdd)
    
    # Define fiber section with torsional stiffness
    sec1[0] = ['section', 'Fiber', tag1, '-GJ', 1.0e6]
    
    # Define concrete patches:
    # Core (confined concrete in center)
    sec1[1] = ['patch', 'rect', Col_Conf, nFibCore, nFibZcore, c - y1col, c - z1col, y1col - c, z1col - c]
    # Bottom cover
    sec1[2] = ['patch', 'rect', Col_Unconf, nFib, nFibZ, -y1col, -z1col, y1col, c - z1col]
    # Top cover
    sec1[3] = ['patch', 'rect', Col_Unconf, nFib, nFibZ, -y1col, z1col - c, y1col, z1col]
    # Left cover
    sec1[4] = ['patch', 'rect', Col_Unconf, nFibCover, nFibZ, -y1col, c - z1col, c - y1col, z1col - c]
    # Right cover
    sec1[5] = ['patch', 'rect', Col_Unconf, nFibCover, nFibZ, y1col - c, c - z1col, y1col, z1col - c]

    # --------------------------------- Helper Functions --------------------------------
    def ordenar_lista_par_impar(lista):
        """Sort list to place even numbers first, then odd numbers"""
        pares = [x for x in lista if x % 2 == 0]    # Even numbers
        impares = [x for x in lista if x % 2 != 0]  # Odd numbers
        if pares and impares:
            return [pares[0], impares[0]]
        return lista
    
    def add_steel2(start_idx, bar_count, pos_count, nlist, yloc, z2col, sign=1):
        """
        Add steel reinforcement layers to section
        
        Parameters:
        - start_idx: Starting index in sec1 array
        - bar_count: Number of bars in each configuration
        - pos_count: Number of positions for each configuration  
        - nlist: Bar areas for each configuration
        - yloc: Y coordinate for bars
        - z2col: Spacing between bar positions
        - sign: Direction multiplier (+1 or -1)
        """
        idx = start_idx
        
        # Case 1: Single bar configuration
        if len(bar_count) == 1:
            npunto = pos_count[0]  # Number of bar positions
            for j in range(npunto):
                # Handle odd number of bars (last position gets single bar)
                if j == npunto - 1 and bar_count[0] % 2 == 1:
                    sec1[idx] = ['layer', 'straight', Steel, 1, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                else:
                    # Place two bars symmetrically
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                idx += 1
        
        # Case 2: Two bar configurations
        else:
            # Subcase 2a: Both configurations have even number of bars
            if bar_count[0]%2 == 0 and bar_count[1]%2 == 0:
                # Place first configuration
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                    idx += 1
                
                # Place second configuration
                jini = j+1  # Continue from where first configuration ended
                npunto = pos_count[1]
                for j in range(npunto):
                    j = jini+j
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                    idx += 1
            
            # Subcase 2b: Both configurations have odd number of bars
            elif bar_count[0]%2 == 1 and bar_count[1]%2 == 1:
                # Place first configuration (pairs)
                npunto = pos_count[0]
                for j in range(npunto-1):
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                    idx += 1
                # Place single bar at center for first configuration
                sec1[idx] = ['layer', 'straight', Steel, 1, nlist[0], yloc, z2col/2, yloc, z2col/2]
                idx += 1
                
                # Place second configuration (pairs)
                npunto = pos_count[1]
                jini = j+1
                for j in range(npunto-1):
                    j = jini+j
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                    idx += 1
                # Place single bar at center for second configuration
                sec1[idx] = ['layer', 'straight', Steel, 1, nlist[1], yloc, -z2col/2, yloc, -z2col/2]
                idx += 1
            
            # Subcase 2c: Mixed even/odd configurations
            else:
                # Reorganize to place even configuration first
                bar_count = ordenar_lista_par_impar(bar_count)
                pos_count = [(ct // 2) + (ct % 2) for ct in bar_count]
                
                # Place even configuration (always first after reorganization)
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = ['layer', 'straight', Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                    idx += 1
                
                # Place odd configuration
                if bar_count[1] == 1:
                    # Single bar at center
                    sec1[idx] = ['layer', 'straight', Steel, 1, nlist[1], yloc, 0, yloc, 0]
                    idx += 1
                else:
                    # Multiple odd bars
                    npunto = pos_count[1]
                    jini = j+1
                    for j in range(npunto-1):
                        j = jini+j
                        sec1[idx] = ['layer', 'straight', Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col]
                        idx += 1
                    # Final single bar at center
                    sec1[idx] = ['layer', 'straight', Steel, 1, nlist[1], yloc, 0, yloc, 0]
                    idx += 1

        return idx

    # --------------------------------- Add Steel Reinforcement --------------------------------
    # Add steel bars in TOP, BOTTOM, and MIDDLE positions
    suma = 6  # Start after the 6 concrete patches
    
    # Add top reinforcement
    suma = add_steel2(suma, cT, NpTop, nTlist, y1col - c, (BCol - 2 * c) / (NTop - 1))
    
    # Add bottom reinforcement
    suma = add_steel2(suma, cB, NpBtt, nBlist, c - y1col, (BCol - 2 * c) / (NBtt - 1))

    # Add middle section reinforcement
    y2col = (HCol - 2 * c) / (NpMdd + 1)  # Spacing between middle bars
    y1coln = y1col - y2col  # Starting position for middle bars
    
    for i in range(NpMdd):
        # Handle odd number of middle bars (last position gets single bar)
        if i == NpMdd - 1 and NMiddle % 2 == 1:
            sec1[suma] = ['layer', 'straight', Steel, 1, nMlist[0], y1coln - (c + y2col * i), c - z1col, y1coln - (c + y2col * i), c - z1col]
        else:
            # Place two bars symmetrically
            sec1[suma] = ['layer', 'straight', Steel, 2, nMlist[0], y1coln - (c + y2col * i), z1col - c, y1coln - (c + y2col * i), c - z1col]
        suma += 1

    return sec1, tag1


def Graph_FiberSection_Colums(BCol,HCol,c,cT, cM, cB, nT, nM, nB):
    """
    Generate visualization data for reinforced concrete column fiber sections.
    
    This function creates the geometric data needed to visualize the fiber section
    of a reinforced concrete column, including concrete patches and steel bar locations.
    
    Parameters
    ----------
    BCol : float
        Column base width in meters
    HCol : float
        Column height in meters
    c : float
        Concrete cover thickness in meters
    cT : list
        Number of top reinforcement bars for each bar configuration
    cM : list
        Number of middle reinforcement bars for each bar configuration
    cB : list
        Number of bottom reinforcement bars for each bar configuration
    nT : list
        Bar numbers (diameter in eighths of inch) for top reinforcement
        Valid values: 'barnum3', 'barnum4', 'barnum5', 'barnum6', 'barnum7', 'barnum8'
    nM : list
        Bar numbers (diameter in eighths of inch) for middle reinforcement
    nB : list
        Bar numbers (diameter in eighths of inch) for bottom reinforcement
        
    Returns
    -------
    tuple
        - sec1 : list
            Steel bar layer definitions with coordinates and properties
            Format: (material_tag, num_bars, area, y1, z1, y2, z2)
        - rect_patches : list
            Rectangular patch definitions for concrete regions
            Format: (material_tag, nFibY, nFibZ, y1, z1, y2, z2)
            
    Notes
    -----
    - Material tags: Steel=55, Confined concrete=1, Unconfined concrete=3
    - Automatically handles even/odd bar distributions
    - Calculates optimal bar spacing and positioning
    - Used for section visualization and plotting
    
    Examples
    --------
    >>> BCol, HCol, c = 0.4, 0.4, 0.04
    >>> cT, cM, cB = [4], [2], [4]
    >>> nT, nM, nB = ['barnum4'], ['barnum4'], ['barnum4']
    >>> steel_layers, concrete_patches = Graph_FiberSection_Colums(BCol, HCol, c, cT, cM, cB, nT, nM, nB)
    """
    
    Steel = 55  # Steel material tag for visualization
    
    # Calculate section half-dimensions
    y1col = HCol / 2.0  # Half height
    z1col = BCol / 2.0  # Half width

    bar_areas = {
        'barnum3': 0.000071,
        'barnum4': 0.000127,
        'barnum5': 0.000198,
        'barnum6': 0.000286,
        'barnum7': 0.000387,
        'barnum8': 0.000508
    }

    nTlist = [bar_areas[bar] for bar in nT]
    nBlist = [bar_areas[bar] for bar in nB]
    nMlist = [bar_areas[bar] for bar in nM]

    NMiddle = sum(cM)
    NpMdd = (NMiddle // 2) + (NMiddle % 2)

    NTop = sum(cT)
    NpTop = [(ct // 2) + (ct % 2) for ct in cT]
    
    NBtt = sum(cB)
    NpBtt = [(cb // 2) + (cb % 2) for cb in cB]
    
    
    # Dibujar los parches rectangulares
    # Format: (material_tag, nFibY, nFibZ, y1, z1, y2, z2)
    rect_patches = [
        (1, 16, 10, c - y1col, c - z1col, y1col - c, z1col - c),  # Core (confined)
        (3, 20, 1, -y1col, -z1col, y1col, c - z1col),            # Bottom cover
        (3, 20, 1, -y1col, z1col - c, y1col, z1col),             # Top cover
        (3, 3, 1, -y1col, c - z1col, c - y1col, z1col - c),      # Left cover
        (3, 3, 1, y1col - c, c - z1col, y1col, z1col - c)        # Right cover
    ]
    
    # Initialize array for steel bar visualization data
    sec1 = [0]*(sum(NpTop) + sum(NpBtt) + NpMdd)
    
    def ordenar_lista_par_impar(lista):
        """Sort list to place even numbers first, then odd numbers"""
        pares = [x for x in lista if x % 2 == 0]    # Even numbers
        impares = [x for x in lista if x % 2 != 0]  # Odd numbers
        istrue = 'False'
        if pares and impares:
            istrue = 'True'
            return [pares[0], impares[0]], istrue
        return lista
    
    def add_steel2(start_idx, bar_count, pos_count, nlist, yloc, z2col, sign=1):
        """
        Add steel reinforcement layers to section
        
        Parameters:
        - start_idx: Starting index in sec1 array
        - bar_count: Number of bars in each configuration
        - pos_count: Number of positions for each configuration  
        - nlist: Bar areas for each configuration
        - yloc: Y coordinate for bars
        - z2col: Spacing between bar positions
        - sign: Direction multiplier (+1 or -1)
        """
        idx = start_idx
        
        # Case 1: Single bar configuration
        if len(bar_count) == 1:
            npunto = pos_count[0]  # Number of bar positions
            for j in range(npunto):
                # Handle odd number of bars (last position gets single bar)
                if j == npunto - 1 and bar_count[0] % 2 == 1:
                    sec1[idx] = (Steel, 1, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                else:
                    # Place two bars symmetrically
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                idx += 1
        else:
            # Subcase 2a: Both configurations have even number of bars
            if bar_count[0]%2 == 0 and bar_count[1]%2 == 0:
                # Place first configuration
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                # Place second configuration
                jini = j+1  # Continue from where first configuration ended
                npunto = pos_count[1]
                for j in range(npunto):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
            # Subcase 2b: Both configurations have odd number of bars
            elif bar_count[0]%2 == 1 and bar_count[1]%2 == 1:
                
                npunto = pos_count[0]
                for j in range(npunto-1):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[0], yloc, z2col/2, yloc, z2col/2)
                idx += 1
                
                npunto = pos_count[1]
                jini = j+1
                for j in range(npunto-1):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[1], yloc, -z2col/2, yloc, -z2col/2)
                idx += 1
            
            # Subcase 2c: Mixed even/odd configurations
            else:
                # Reorganize to place even configuration first
                bar_count, istrue = ordenar_lista_par_impar(bar_count)
                pos_count = [(ct // 2) + (ct % 2) for ct in bar_count]
                if istrue == 'True':
                    nlist = [nlist[1],nlist[0]]
                # Como va si o si el numero par primero, se tiene que:
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                # Ahora va el numero impar.,
                if bar_count[1] == 1:
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1
                else:
                    npunto = pos_count[1]
                    jini = j+1
                    for j in range(npunto-1):
                        j = jini+j
                        sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                        idx += 1
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1

        return idx
    

    # Añadir barras de acero en las posiciones TOP, BOTTOM y MIDDLE
    suma = 6
    suma = add_steel2(suma, cT, NpTop, nTlist, y1col - c, (BCol - 2 * c) / (NTop - 1))
    suma = add_steel2(suma, cB, NpBtt, nBlist, c - y1col, (BCol - 2 * c) / (NBtt - 1))

    # Barras en la sección MIDDLE
    y2col = (HCol - 2 * c) / (NpMdd + 1)
    y1coln = y1col - y2col
    for i in range(NpMdd):
        if i == NpMdd - 1 and NMiddle % 2 == 1:
            sec1[suma] = ['layer', 'straight', Steel, 1, nMlist[0], y1coln - (c + y2col * i), c - z1col, y1coln - (c + y2col * i), c - z1col]
        else:
            sec1[suma] = ['layer', 'straight', Steel, 2, nMlist[0], y1coln - (c + y2col * i), z1col - c, y1coln - (c + y2col * i), c - z1col]
        suma += 1

    return sec1, tag1


def Graph_FiberSection_Colums(BCol,HCol,c,cT, cM, cB, nT, nM, nB):
    """
    Generate visualization data for reinforced concrete column fiber sections.
    
    This function creates the geometric data needed to visualize the fiber section
    of a reinforced concrete column, including concrete patches and steel bar locations.
    
    Parameters
    ----------
    BCol : float
        Column base width in meters
    HCol : float
        Column height in meters
    c : float
        Concrete cover thickness in meters
    cT : list
        Number of top reinforcement bars for each bar configuration
    cM : list
        Number of middle reinforcement bars for each bar configuration
    cB : list
        Number of bottom reinforcement bars for each bar configuration
    nT : list
        Bar numbers (diameter in eighths of inch) for top reinforcement
        Valid values: 'barnum3', 'barnum4', 'barnum5', 'barnum6', 'barnum7', 'barnum8'
    nM : list
        Bar numbers (diameter in eighths of inch) for middle reinforcement
    nB : list
        Bar numbers (diameter in eighths of inch) for bottom reinforcement
        
    Returns
    -------
    tuple
        - sec1 : list
            Steel bar layer definitions with coordinates and properties
            Format: (material_tag, num_bars, area, y1, z1, y2, z2)
        - rect_patches : list
            Rectangular patch definitions for concrete regions
            Format: (material_tag, nFibY, nFibZ, y1, z1, y2, z2)
            
    Notes
    -----
    - Material tags: Steel=55, Confined concrete=1, Unconfined concrete=3
    - Automatically handles even/odd bar distributions
    - Calculates optimal bar spacing and positioning
    - Used for section visualization and plotting
    
    Examples
    --------
    >>> BCol, HCol, c = 0.4, 0.4, 0.04
    >>> cT, cM, cB = [4], [2], [4]
    >>> nT, nM, nB = ['barnum4'], ['barnum4'], ['barnum4']
    >>> steel_layers, concrete_patches = Graph_FiberSection_Colums(BCol, HCol, c, cT, cM, cB, nT, nM, nB)
    """
    
    Steel = 55  # Steel material tag for visualization
    
    # Calculate section half-dimensions
    y1col = HCol / 2.0  # Half height
    z1col = BCol / 2.0  # Half width

    bar_areas = {
        'barnum3': 0.000071,
        'barnum4': 0.000127,
        'barnum5': 0.000198,
        'barnum6': 0.000286,
        'barnum7': 0.000387,
        'barnum8': 0.000508
    }

    nTlist = [bar_areas[bar] for bar in nT]
    nBlist = [bar_areas[bar] for bar in nB]
    nMlist = [bar_areas[bar] for bar in nM]

    NMiddle = sum(cM)
    NpMdd = (NMiddle // 2) + (NMiddle % 2)

    NTop = sum(cT)
    NpTop = [(ct // 2) + (ct % 2) for ct in cT]
    
    NBtt = sum(cB)
    NpBtt = [(cb // 2) + (cb % 2) for cb in cB]
    
    
    # Dibujar los parches rectangulares
    # Format: (material_tag, nFibY, nFibZ, y1, z1, y2, z2)
    rect_patches = [
        (1, 16, 10, c - y1col, c - z1col, y1col - c, z1col - c),  # Core (confined)
        (3, 20, 1, -y1col, -z1col, y1col, c - z1col),            # Bottom cover
        (3, 20, 1, -y1col, z1col - c, y1col, z1col),             # Top cover
        (3, 3, 1, -y1col, c - z1col, c - y1col, z1col - c),      # Left cover
        (3, 3, 1, y1col - c, c - z1col, y1col, z1col - c)        # Right cover
    ]
    
    # Initialize array for steel bar visualization data
    sec1 = [0]*(sum(NpTop) + sum(NpBtt) + NpMdd)
    
    def ordenar_lista_par_impar(lista):
        """Sort list to place even numbers first, then odd numbers"""
        pares = [x for x in lista if x % 2 == 0]    # Even numbers
        impares = [x for x in lista if x % 2 != 0]  # Odd numbers
        istrue = 'False'
        if pares and impares:
            istrue = 'True'
            return [pares[0], impares[0]], istrue
        return lista
    
    def add_steel2(start_idx, bar_count, pos_count, nlist, yloc, z2col, sign=1):
        """
        Add steel reinforcement layers to section
        
        Parameters:
        - start_idx: Starting index in sec1 array
        - bar_count: Number of bars in each configuration
        - pos_count: Number of positions for each configuration  
        - nlist: Bar areas for each configuration
        - yloc: Y coordinate for bars
        - z2col: Spacing between bar positions
        - sign: Direction multiplier (+1 or -1)
        """
        idx = start_idx
        
        # Case 1: Single bar configuration
        if len(bar_count) == 1:
            npunto = pos_count[0]  # Number of bar positions
            for j in range(npunto):
                # Handle odd number of bars (last position gets single bar)
                if j == npunto - 1 and bar_count[0] % 2 == 1:
                    sec1[idx] = (Steel, 1, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                else:
                    # Place two bars symmetrically
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                idx += 1
        else:
            # Subcase 2a: Both configurations have even number of bars
            if bar_count[0]%2 == 0 and bar_count[1]%2 == 0:
                # Place first configuration
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                # Place second configuration
                jini = j+1  # Continue from where first configuration ended
                npunto = pos_count[1]
                for j in range(npunto):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
            # Subcase 2b: Both configurations have odd number of bars
            elif bar_count[0]%2 == 1 and bar_count[1]%2 == 1:
                
                npunto = pos_count[0]
                for j in range(npunto-1):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[0], yloc, z2col/2, yloc, z2col/2)
                idx += 1
                
                npunto = pos_count[1]
                jini = j+1
                for j in range(npunto-1):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[1], yloc, -z2col/2, yloc, -z2col/2)
                idx += 1
            
            # Subcase 2c: Mixed even/odd configurations
            else:
                # Reorganize to place even configuration first
                bar_count, istrue = ordenar_lista_par_impar(bar_count)
                pos_count = [(ct // 2) + (ct % 2) for ct in bar_count]
                if istrue == 'True':
                    nlist = [nlist[1],nlist[0]]
                # Como va si o si el numero par primero, se tiene que:
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                # Ahora va el numero impar.,
                if bar_count[1] == 1:
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1
                else:
                    npunto = pos_count[1]
                    jini = j+1
                    for j in range(npunto-1):
                        j = jini+j
                        sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                        idx += 1
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1

        return idx
    

    # Añadir barras de acero en las posiciones TOP, BOTTOM y MIDDLE
    suma = 6
    suma = add_steel2(suma, cT, NpTop, nTlist, y1col - c, (BCol - 2 * c) / (NTop - 1))
    suma = add_steel2(suma, cB, NpBtt, nBlist, c - y1col, (BCol - 2 * c) / (NBtt - 1))

    # Barras en la sección MIDDLE
    y2col = (HCol - 2 * c) / (NpMdd + 1)
    y1coln = y1col - y2col
    for i in range(NpMdd):
        if i == NpMdd - 1 and NMiddle % 2 == 1:
            sec1[suma] = ['layer', 'straight', Steel, 1, nMlist[0], y1coln - (c + y2col * i), c - z1col, y1coln - (c + y2col * i), c - z1col]
        else:
            sec1[suma] = ['layer', 'straight', Steel, 2, nMlist[0], y1coln - (c + y2col * i), z1col - c, y1coln - (c + y2col * i), c - z1col]
        suma += 1

    return sec1, tag1


def Graph_FiberSection_Colums(BCol,HCol,c,cT, cM, cB, nT, nM, nB):
    """
    Generate visualization data for reinforced concrete column fiber sections.
    
    This function creates the geometric data needed to visualize the fiber section
    of a reinforced concrete column, including concrete patches and steel bar locations.
    
    Parameters
    ----------
    BCol : float
        Column base width in meters
    HCol : float
        Column height in meters
    c : float
        Concrete cover thickness in meters
    cT : list
        Number of top reinforcement bars for each bar configuration
    cM : list
        Number of middle reinforcement bars for each bar configuration
    cB : list
        Number of bottom reinforcement bars for each bar configuration
    nT : list
        Bar numbers (diameter in eighths of inch) for top reinforcement
        Valid values: 'barnum3', 'barnum4', 'barnum5', 'barnum6', 'barnum7', 'barnum8'
    nM : list
        Bar numbers (diameter in eighths of inch) for middle reinforcement
    nB : list
        Bar numbers (diameter in eighths of inch) for bottom reinforcement
        
    Returns
    -------
    tuple
        - sec1 : list
            Steel bar layer definitions with coordinates and properties
            Format: (material_tag, num_bars, area, y1, z1, y2, z2)
        - rect_patches : list
            Rectangular patch definitions for concrete regions
            Format: (material_tag, nFibY, nFibZ, y1, z1, y2, z2)
            
    Notes
    -----
    - Material tags: Steel=55, Confined concrete=1, Unconfined concrete=3
    - Automatically handles even/odd bar distributions
    - Calculates optimal bar spacing and positioning
    - Used for section visualization and plotting
    
    Examples
    --------
    >>> BCol, HCol, c = 0.4, 0.4, 0.04
    >>> cT, cM, cB = [4], [2], [4]
    >>> nT, nM, nB = ['barnum4'], ['barnum4'], ['barnum4']
    >>> steel_layers, concrete_patches = Graph_FiberSection_Colums(BCol, HCol, c, cT, cM, cB, nT, nM, nB)
    """
    
    Steel = 55  # Steel material tag for visualization
    
    # Calculate section half-dimensions
    y1col = HCol / 2.0  # Half height
    z1col = BCol / 2.0  # Half width

    bar_areas = {
        'barnum3': 0.000071,
        'barnum4': 0.000127,
        'barnum5': 0.000198,
        'barnum6': 0.000286,
        'barnum7': 0.000387,
        'barnum8': 0.000508
    }

    nTlist = [bar_areas[bar] for bar in nT]
    nBlist = [bar_areas[bar] for bar in nB]
    nMlist = [bar_areas[bar] for bar in nM]

    NMiddle = sum(cM)
    NpMdd = (NMiddle // 2) + (NMiddle % 2)

    NTop = sum(cT)
    NpTop = [(ct // 2) + (ct % 2) for ct in cT]
    
    NBtt = sum(cB)
    NpBtt = [(cb // 2) + (cb % 2) for cb in cB]
    
    
    # Dibujar los parches rectangulares
    # Format: (material_tag, nFibY, nFibZ, y1, z1, y2, z2)
    rect_patches = [
        (1, 16, 10, c - y1col, c - z1col, y1col - c, z1col - c),  # Core (confined)
        (3, 20, 1, -y1col, -z1col, y1col, c - z1col),            # Bottom cover
        (3, 20, 1, -y1col, z1col - c, y1col, z1col),             # Top cover
        (3, 3, 1, -y1col, c - z1col, c - y1col, z1col - c),      # Left cover
        (3, 3, 1, y1col - c, c - z1col, y1col, z1col - c)        # Right cover
    ]
    
    # Initialize array for steel bar visualization data
    sec1 = [0]*(sum(NpTop) + sum(NpBtt) + NpMdd)
    
    def ordenar_lista_par_impar(lista):
        """Sort list to place even numbers first, then odd numbers"""
        pares = [x for x in lista if x % 2 == 0]    # Even numbers
        impares = [x for x in lista if x % 2 != 0]  # Odd numbers
        istrue = 'False'
        if pares and impares:
            istrue = 'True'
            return [pares[0], impares[0]], istrue
        return lista
    
    def add_steel2(start_idx, bar_count, pos_count, nlist, yloc, z2col, sign=1):
        """
        Add steel reinforcement layers to section
        
        Parameters:
        - start_idx: Starting index in sec1 array
        - bar_count: Number of bars in each configuration
        - pos_count: Number of positions for each configuration  
        - nlist: Bar areas for each configuration
        - yloc: Y coordinate for bars
        - z2col: Spacing between bar positions
        - sign: Direction multiplier (+1 or -1)
        """
        idx = start_idx
        
        # Case 1: Single bar configuration
        if len(bar_count) == 1:
            npunto = pos_count[0]  # Number of bar positions
            for j in range(npunto):
                # Handle odd number of bars (last position gets single bar)
                if j == npunto - 1 and bar_count[0] % 2 == 1:
                    sec1[idx] = (Steel, 1, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                else:
                    # Place two bars symmetrically
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                idx += 1
        else:
            # Subcase 2a: Both configurations have even number of bars
            if bar_count[0]%2 == 0 and bar_count[1]%2 == 0:
                # Place first configuration
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                # Place second configuration
                jini = j+1  # Continue from where first configuration ended
                npunto = pos_count[1]
                for j in range(npunto):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
            # Subcase 2b: Both configurations have odd number of bars
            elif bar_count[0]%2 == 1 and bar_count[1]%2 == 1:
                
                npunto = pos_count[0]
                for j in range(npunto-1):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[0], yloc, z2col/2, yloc, z2col/2)
                idx += 1
                
                npunto = pos_count[1]
                jini = j+1
                for j in range(npunto-1):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[1], yloc, -z2col/2, yloc, -z2col/2)
                idx += 1
            
            # Subcase 2c: Mixed even/odd configurations
            else:
                # Reorganize to place even configuration first
                bar_count, istrue = ordenar_lista_par_impar(bar_count)
                pos_count = [(ct // 2) + (ct % 2) for ct in bar_count]
                if istrue == 'True':
                    nlist = [nlist[1],nlist[0]]
                # Como va si o si el numero par primero, se tiene que:
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                # Ahora va el numero impar.,
                if bar_count[1] == 1:
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1
                else:
                    npunto = pos_count[1]
                    jini = j+1
                    for j in range(npunto-1):
                        j = jini+j
                        sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                        idx += 1
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1

        return idx
    

    # Añadir barras de acero en las posiciones TOP, BOTTOM y MIDDLE
    suma = 6
    suma = add_steel2(suma, cT, NpTop, nTlist, y1col - c, (BCol - 2 * c) / (NTop - 1))
    suma = add_steel2(suma, cB, NpBtt, nBlist, c - y1col, (BCol - 2 * c) / (NBtt - 1))

    # Barras en la sección MIDDLE
    y2col = (HCol - 2 * c) / (NpMdd + 1)
    y1coln = y1col - y2col
    for i in range(NpMdd):
        if i == NpMdd - 1 and NMiddle % 2 == 1:
            sec1[suma] = ['layer', 'straight', Steel, 1, nMlist[0], y1coln - (c + y2col * i), c - z1col, y1coln - (c + y2col * i), c - z1col]
        else:
            sec1[suma] = ['layer', 'straight', Steel, 2, nMlist[0], y1coln - (c + y2col * i), z1col - c, y1coln - (c + y2col * i), c - z1col]
        suma += 1

    return sec1, tag1


def Graph_FiberSection_Colums(BCol,HCol,c,cT, cM, cB, nT, nM, nB):
    """
    Generate visualization data for reinforced concrete column fiber sections.
    
    This function creates the geometric data needed to visualize the fiber section
    of a reinforced concrete column, including concrete patches and steel bar locations.
    
    Parameters
    ----------
    BCol : float
        Column base width in meters
    HCol : float
        Column height in meters
    c : float
        Concrete cover thickness in meters
    cT : list
        Number of top reinforcement bars for each bar configuration
    cM : list
        Number of middle reinforcement bars for each bar configuration
    cB : list
        Number of bottom reinforcement bars for each bar configuration
    nT : list
        Bar numbers (diameter in eighths of inch) for top reinforcement
        Valid values: 'barnum3', 'barnum4', 'barnum5', 'barnum6', 'barnum7', 'barnum8'
    nM : list
        Bar numbers (diameter in eighths of inch) for middle reinforcement
    nB : list
        Bar numbers (diameter in eighths of inch) for bottom reinforcement
        
    Returns
    -------
    tuple
        - sec1 : list
            Steel bar layer definitions with coordinates and properties
            Format: (material_tag, num_bars, area, y1, z1, y2, z2)
        - rect_patches : list
            Rectangular patch definitions for concrete regions
            Format: (material_tag, nFibY, nFibZ, y1, z1, y2, z2)
            
    Notes
    -----
    - Material tags: Steel=55, Confined concrete=1, Unconfined concrete=3
    - Automatically handles even/odd bar distributions
    - Calculates optimal bar spacing and positioning
    - Used for section visualization and plotting
    
    Examples
    --------
    >>> BCol, HCol, c = 0.4, 0.4, 0.04
    >>> cT, cM, cB = [4], [2], [4]
    >>> nT, nM, nB = ['barnum4'], ['barnum4'], ['barnum4']
    >>> steel_layers, concrete_patches = Graph_FiberSection_Colums(BCol, HCol, c, cT, cM, cB, nT, nM, nB)
    """
    
    Steel = 55  # Steel material tag for visualization
    
    # Calculate section half-dimensions
    y1col = HCol / 2.0  # Half height
    z1col = BCol / 2.0  # Half width

    bar_areas = {
        'barnum3': 0.000071,
        'barnum4': 0.000127,
        'barnum5': 0.000198,
        'barnum6': 0.000286,
        'barnum7': 0.000387,
        'barnum8': 0.000508
    }

    nTlist = [bar_areas[bar] for bar in nT]
    nBlist = [bar_areas[bar] for bar in nB]
    nMlist = [bar_areas[bar] for bar in nM]

    NMiddle = sum(cM)
    NpMdd = (NMiddle // 2) + (NMiddle % 2)

    NTop = sum(cT)
    NpTop = [(ct // 2) + (ct % 2) for ct in cT]
    
    NBtt = sum(cB)
    NpBtt = [(cb // 2) + (cb % 2) for cb in cB]
    
    
    # Dibujar los parches rectangulares
    # Format: (material_tag, nFibY, nFibZ, y1, z1, y2, z2)
    rect_patches = [
        (1, 16, 10, c - y1col, c - z1col, y1col - c, z1col - c),  # Core (confined)
        (3, 20, 1, -y1col, -z1col, y1col, c - z1col),            # Bottom cover
        (3, 20, 1, -y1col, z1col - c, y1col, z1col),             # Top cover
        (3, 3, 1, -y1col, c - z1col, c - y1col, z1col - c),      # Left cover
        (3, 3, 1, y1col - c, c - z1col, y1col, z1col - c)        # Right cover
    ]
    
    # Initialize array for steel bar visualization data
    sec1 = [0]*(sum(NpTop) + sum(NpBtt) + NpMdd)
    
    def ordenar_lista_par_impar(lista):
        """Sort list to place even numbers first, then odd numbers"""
        pares = [x for x in lista if x % 2 == 0]    # Even numbers
        impares = [x for x in lista if x % 2 != 0]  # Odd numbers
        istrue = 'False'
        if pares and impares:
            istrue = 'True'
            return [pares[0], impares[0]], istrue
        return lista
    
    def add_steel2(start_idx, bar_count, pos_count, nlist, yloc, z2col, sign=1):
        """
        Add steel reinforcement layers to section
        
        Parameters:
        - start_idx: Starting index in sec1 array
        - bar_count: Number of bars in each configuration
        - pos_count: Number of positions for each configuration  
        - nlist: Bar areas for each configuration
        - yloc: Y coordinate for bars
        - z2col: Spacing between bar positions
        - sign: Direction multiplier (+1 or -1)
        """
        idx = start_idx
        
        # Case 1: Single bar configuration
        if len(bar_count) == 1:
            npunto = pos_count[0]  # Number of bar positions
            for j in range(npunto):
                # Handle odd number of bars (last position gets single bar)
                if j == npunto - 1 and bar_count[0] % 2 == 1:
                    sec1[idx] = (Steel, 1, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                else:
                    # Place two bars symmetrically
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                idx += 1
        else:
            # Subcase 2a: Both configurations have even number of bars
            if bar_count[0]%2 == 0 and bar_count[1]%2 == 0:
                # Place first configuration
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                # Place second configuration
                jini = j+1  # Continue from where first configuration ended
                npunto = pos_count[1]
                for j in range(npunto):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
            # Subcase 2b: Both configurations have odd number of bars
            elif bar_count[0]%2 == 1 and bar_count[1]%2 == 1:
                
                npunto = pos_count[0]
                for j in range(npunto-1):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[0], yloc, z2col/2, yloc, z2col/2)
                idx += 1
                
                npunto = pos_count[1]
                jini = j+1
                for j in range(npunto-1):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[1], yloc, -z2col/2, yloc, -z2col/2)
                idx += 1
            
            # Subcase 2c: Mixed even/odd configurations
            else:
                # Reorganize to place even configuration first
                bar_count, istrue = ordenar_lista_par_impar(bar_count)
                pos_count = [(ct // 2) + (ct % 2) for ct in bar_count]
                if istrue == 'True':
                    nlist = [nlist[1],nlist[0]]
                # Como va si o si el numero par primero, se tiene que:
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                # Ahora va el numero impar.,
                if bar_count[1] == 1:
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1
                else:
                    npunto = pos_count[1]
                    jini = j+1
                    for j in range(npunto-1):
                        j = jini+j
                        sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                        idx += 1
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1

        return idx
    

    # Añadir barras de acero en las posiciones TOP, BOTTOM y MIDDLE
    suma = 6
    suma = add_steel2(suma, cT, NpTop, nTlist, y1col - c, (BCol - 2 * c) / (NTop - 1))
    suma = add_steel2(suma, cB, NpBtt, nBlist, c - y1col, (BCol - 2 * c) / (NBtt - 1))

    # Barras en la sección MIDDLE
    y2col = (HCol - 2 * c) / (NpMdd + 1)
    y1coln = y1col - y2col
    for i in range(NpMdd):
        if i == NpMdd - 1 and NMiddle % 2 == 1:
            sec1[suma] = ['layer', 'straight', Steel, 1, nMlist[0], y1coln - (c + y2col * i), c - z1col, y1coln - (c + y2col * i), c - z1col]
        else:
            sec1[suma] = ['layer', 'straight', Steel, 2, nMlist[0], y1coln - (c + y2col * i), z1col - c, y1coln - (c + y2col * i), c - z1col]
        suma += 1

    return sec1, tag1


def Graph_FiberSection_Colums(BCol,HCol,c,cT, cM, cB, nT, nM, nB):
    """
    Generate visualization data for reinforced concrete column fiber sections.
    
    This function creates the geometric data needed to visualize the fiber section
    of a reinforced concrete column, including concrete patches and steel bar locations.
    
    Parameters
    ----------
    BCol : float
        Column base width in meters
    HCol : float
        Column height in meters
    c : float
        Concrete cover thickness in meters
    cT : list
        Number of top reinforcement bars for each bar configuration
    cM : list
        Number of middle reinforcement bars for each bar configuration
    cB : list
        Number of bottom reinforcement bars for each bar configuration
    nT : list
        Bar numbers (diameter in eighths of inch) for top reinforcement
        Valid values: 'barnum3', 'barnum4', 'barnum5', 'barnum6', 'barnum7', 'barnum8'
    nM : list
        Bar numbers (diameter in eighths of inch) for middle reinforcement
    nB : list
        Bar numbers (diameter in eighths of inch) for bottom reinforcement
        
    Returns
    -------
    tuple
        - sec1 : list
            Steel bar layer definitions with coordinates and properties
            Format: (material_tag, num_bars, area, y1, z1, y2, z2)
        - rect_patches : list
            Rectangular patch definitions for concrete regions
            Format: (material_tag, nFibY, nFibZ, y1, z1, y2, z2)
            
    Notes
    -----
    - Material tags: Steel=55, Confined concrete=1, Unconfined concrete=3
    - Automatically handles even/odd bar distributions
    - Calculates optimal bar spacing and positioning
    - Used for section visualization and plotting
    
    Examples
    --------
    >>> BCol, HCol, c = 0.4, 0.4, 0.04
    >>> cT, cM, cB = [4], [2], [4]
    >>> nT, nM, nB = ['barnum4'], ['barnum4'], ['barnum4']
    >>> steel_layers, concrete_patches = Graph_FiberSection_Colums(BCol, HCol, c, cT, cM, cB, nT, nM, nB)
    """
    
    Steel = 55  # Steel material tag for visualization
    
    # Calculate section half-dimensions
    y1col = HCol / 2.0  # Half height
    z1col = BCol / 2.0  # Half width

    bar_areas = {
        'barnum3': 0.000071,
        'barnum4': 0.000127,
        'barnum5': 0.000198,
        'barnum6': 0.000286,
        'barnum7': 0.000387,
        'barnum8': 0.000508
    }

    nTlist = [bar_areas[bar] for bar in nT]
    nBlist = [bar_areas[bar] for bar in nB]
    nMlist = [bar_areas[bar] for bar in nM]

    NMiddle = sum(cM)
    NpMdd = (NMiddle // 2) + (NMiddle % 2)

    NTop = sum(cT)
    NpTop = [(ct // 2) + (ct % 2) for ct in cT]
    
    NBtt = sum(cB)
    NpBtt = [(cb // 2) + (cb % 2) for cb in cB]
    
    
    # Dibujar los parches rectangulares
    # Format: (material_tag, nFibY, nFibZ, y1, z1, y2, z2)
    rect_patches = [
        (1, 16, 10, c - y1col, c - z1col, y1col - c, z1col - c),  # Core (confined)
        (3, 20, 1, -y1col, -z1col, y1col, c - z1col),            # Bottom cover
        (3, 20, 1, -y1col, z1col - c, y1col, z1col),             # Top cover
        (3, 3, 1, -y1col, c - z1col, c - y1col, z1col - c),      # Left cover
        (3, 3, 1, y1col - c, c - z1col, y1col, z1col - c)        # Right cover
    ]
    
    # Initialize array for steel bar visualization data
    sec1 = [0]*(sum(NpTop) + sum(NpBtt) + NpMdd)
    
    def ordenar_lista_par_impar(lista):
        """Sort list to place even numbers first, then odd numbers"""
        pares = [x for x in lista if x % 2 == 0]    # Even numbers
        impares = [x for x in lista if x % 2 != 0]  # Odd numbers
        istrue = 'False'
        if pares and impares:
            istrue = 'True'
            return [pares[0], impares[0]], istrue
        return lista
    
    def add_steel2(start_idx, bar_count, pos_count, nlist, yloc, z2col, sign=1):
        """
        Add steel reinforcement layers to section
        
        Parameters:
        - start_idx: Starting index in sec1 array
        - bar_count: Number of bars in each configuration
        - pos_count: Number of positions for each configuration  
        - nlist: Bar areas for each configuration
        - yloc: Y coordinate for bars
        - z2col: Spacing between bar positions
        - sign: Direction multiplier (+1 or -1)
        """
        idx = start_idx
        
        # Case 1: Single bar configuration
        if len(bar_count) == 1:
            npunto = pos_count[0]  # Number of bar positions
            for j in range(npunto):
                # Handle odd number of bars (last position gets single bar)
                if j == npunto - 1 and bar_count[0] % 2 == 1:
                    sec1[idx] = (Steel, 1, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                else:
                    # Place two bars symmetrically
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                idx += 1
        else:
            # Subcase 2a: Both configurations have even number of bars
            if bar_count[0]%2 == 0 and bar_count[1]%2 == 0:
                # Place first configuration
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                # Place second configuration
                jini = j+1  # Continue from where first configuration ended
                npunto = pos_count[1]
                for j in range(npunto):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
            # Subcase 2b: Both configurations have odd number of bars
            elif bar_count[0]%2 == 1 and bar_count[1]%2 == 1:
                
                npunto = pos_count[0]
                for j in range(npunto-1):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[0], yloc, z2col/2, yloc, z2col/2)
                idx += 1
                
                npunto = pos_count[1]
                jini = j+1
                for j in range(npunto-1):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[1], yloc, -z2col/2, yloc, -z2col/2)
                idx += 1
            
            # Subcase 2c: Mixed even/odd configurations
            else:
                # Reorganize to place even configuration first
                bar_count, istrue = ordenar_lista_par_impar(bar_count)
                pos_count = [(ct // 2) + (ct % 2) for ct in bar_count]
                if istrue == 'True':
                    nlist = [nlist[1],nlist[0]]
                # Como va si o si el numero par primero, se tiene que:
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                # Ahora va el numero impar.,
                if bar_count[1] == 1:
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1
                else:
                    npunto = pos_count[1]
                    jini = j+1
                    for j in range(npunto-1):
                        j = jini+j
                        sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                        idx += 1
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1

        return idx
    

    # Añadir barras de acero en las posiciones TOP, BOTTOM y MIDDLE
    suma = 6
    suma = add_steel2(suma, cT, NpTop, nTlist, y1col - c, (BCol - 2 * c) / (NTop - 1))
    suma = add_steel2(suma, cB, NpBtt, nBlist, c - y1col, (BCol - 2 * c) / (NBtt - 1))

    # Barras en la sección MIDDLE
    y2col = (HCol - 2 * c) / (NpMdd + 1)
    y1coln = y1col - y2col
    for i in range(NpMdd):
        if i == NpMdd - 1 and NMiddle % 2 == 1:
            sec1[suma] = (Steel, 1, nMlist[0], y1coln - (c + y2col * i), c - z1col, y1coln - (c + y2col * i), c - z1col)
        else:
            sec1[suma] = (Steel, 2, nMlist[0], y1coln - (c + y2col * i), z1col - c, y1coln - (c + y2col * i), c - z1col)
        suma += 1

    return sec1, rect_patches


# ====================================================================================================================
# ========================================== GENERADOR DE SECCIONES (VIGAS) ========================================== 
# ====================================================================================================================


def fiber_elemens_Beams(BCol, HCol, c, cT, cB, nT, nB, fc, Fy, xloc):
    """
    Generate fiber element sections for reinforced concrete beams using OpenSees.
    
    This function creates a fiber section model for reinforced concrete beams with 
    confined and unconfined concrete materials and steel reinforcement bars distributed 
    in top and bottom regions only (no middle reinforcement).
    
    Parameters
    ----------
    BCol : float
        Beam width in meters
    HCol : float
        Beam height in meters
    c : float
        Concrete cover thickness in meters
    cT : list
        Number of top reinforcement bars for each bar configuration
    cB : list
        Number of bottom reinforcement bars for each bar configuration
    nT : list
        Bar numbers (diameter in eighths of inch) for top reinforcement
        Valid values: 'barnum3', 'barnum4', 'barnum5', 'barnum6', 'barnum7', 'barnum8'
    nB : list
        Bar numbers (diameter in eighths of inch) for bottom reinforcement
    fc : float
        Concrete compressive strength f'c in KPa
    Fy : float
        Steel yield strength fy in KPa
    xloc : list
        X coordinates of each node in the structure
        
    Returns
    -------
    tuple
        - sec1 : list
            OpenSees fiber section definition commands
        - tag1 : int
            Section tag number (12)
            
    Notes
    -----
    - Creates materials for confined concrete (tag 2), unconfined concrete (tag 4), 
      and steel (tag 7)
    - Uses Concrete02 material model with fracture energy regularization
    - Uses Hysteretic material model for steel with Dhakal degradation parameters
    - Confinement factor k=1.25 (lower than columns due to different confinement)
    - Automatically calculates reinforcement distribution and spacing
    
    Examples
    --------
    >>> BCol, HCol, c = 0.3, 0.5, 0.04
    >>> cT, cB = [3], [4]
    >>> nT, nB = ['barnum4'], ['barnum5']
    >>> fc, Fy = 25000, 420000
    >>> xloc = [0, 4, 8, 12]
    >>> section, tag = fiber_elemens_Beams(BCol, HCol, c, cT, cB, nT, nB, fc, Fy, xloc)
    """
    # longitud de la viga
    xlist = [np.around(xloc[i+1]-xloc[i], 2) for i in range(len(xloc)-1)]
    pint = 5  # Number of integration points
    Lvig = np.median(xlist) * 1000  # Convert median length to mm
    
    # --------------------------------- Material Tags for Beams --------------------------------
    Vig_Conf = 2    # Confined concrete for beams
    Vig_Unconf = 4  # Unconfined concrete for beams
    Steel = 7       # Steel for beams
    
    # --------------------------------- Unconfined Concrete (same as columns) --------------------------------
    E = 4400 * (fc/1000)**0.5 * 1000
    ec = 2 * fc / E
    fcu = 0.2 * fc
    Gfc = fc / 1000
    e20 = ut.e20Lobatto2(Gfc, Lvig, pint, fc/1000, E/1000, ec)
    uniaxialMaterial('Concrete02', Vig_Unconf, -fc, -ec, -fcu, -e20)
    
    # --------------------------------- Confined Concrete (lower confinement than columns) --------------------------------
    k = 1.25  # Lower confinement factor for beams (25% increase vs 30% for columns)
    fcc = fc * k
    ecc = 2 * fcc / E
    fucc = 0.2 * fcc
    Gfcc = 2 * (fcc / 1000)
    e20cc = ut.e20Lobatto2(Gfcc, Lvig, pint, fcc/1000, E/1000, ecc)
    uniaxialMaterial('Concrete02', Vig_Conf, -fcc, -ecc, -fucc, -e20cc)
    
    # --------------------------------- Steel Material (same as columns) --------------------------------
    Es=210000000.0
    s, e = ut.dhakal(Fy/1000, Fy/1000*1.5, 0.002, 0.01, 0.1, 96, 12)
    uniaxialMaterial('Hysteretic',Steel,s[0],e[0],s[1],e[1],s[3],e[3],s[4],e[4],s[5],e[5],s[7],e[7],1.0,1.0,0.0,0.0)  

    # --------------------------------- Section Geometry (same discretization as columns) --------------------------------
    y1col = HCol / 2.0
    z1col = BCol / 2.0
    nFibZ = 1
    nFib = 20
    nFibCover = 3
    nFibZcore = 10
    nFibCore = 16

    bar_areas = {
        'barnum3': 0.000071,
        'barnum4': 0.000127,
        'barnum5': 0.000198,
        'barnum6': 0.000286,
        'barnum7': 0.000387,
        'barnum8': 0.000508
    }

    nTlist = [bar_areas[bar] for bar in nT]
    nBlist = [bar_areas[bar] for bar in nB]
    
    NTop = sum(cT)
    NpTop = [(ct // 2) + (ct % 2) for ct in cT]
    
    NBtt = sum(cB)
    NpBtt = [(cb // 2) + (cb % 2) for cb in cB]

    # --------------------------------- Fiber Section Definition --------------------------------
    tag1 = 12  # Different tag for beam sections
    # Initialize section array: 6 patches + top and bottom bar layers only
    sec1 = [0] * (6 + sum(NpTop) + sum(NpBtt))
    
    # Define section and patches (same structure as columns)
    sec1[0] = ['section', 'Fiber', tag1, '-GJ', 1.0e6]
    sec1[1] = ['patch', 'rect', Vig_Conf, nFibCore, nFibZcore, c - y1col, c - z1col, y1col - c, z1col - c]
    sec1[2] = ['patch', 'rect', Vig_Unconf, nFib, nFibZ, -y1col, -z1col, y1col, c - z1col]
    sec1[3] = ['patch', 'rect', Vig_Unconf, nFib, nFibZ, -y1col, z1col - c, y1col, z1col]
    sec1[4] = ['patch', 'rect', Vig_Unconf, nFibCover, nFibZ, -y1col, c - z1col, c - y1col, z1col - c]
    sec1[5] = ['patch', 'rect', Vig_Unconf, nFibCover, nFibZ, y1col - c, c - z1col, y1col, z1col - c]

    # --------------------------------- Helper Functions --------------------------------
    def ordenar_lista_par_impar(lista):
        """Sort list to place even numbers first, then odd numbers"""
        pares = [x for x in lista if x % 2 == 0]    # Even numbers
        impares = [x for x in lista if x % 2 != 0]  # Odd numbers
        istrue = 'False'
        if pares and impares:
            istrue = 'True'
            return [pares[0], impares[0]], istrue
        return lista
    
    def add_steel2(start_idx, bar_count, pos_count, nlist, yloc, z2col, sign=1):
        """
        Add steel reinforcement layers to section
        
        Parameters:
        - start_idx: Starting index in sec1 array
        - bar_count: Number of bars in each configuration
        - pos_count: Number of positions for each configuration  
        - nlist: Bar areas for each configuration
        - yloc: Y coordinate for bars
        - z2col: Spacing between bar positions
        - sign: Direction multiplier (+1 or -1)
        """
        idx = start_idx
        
        # Case 1: Single bar configuration
        if len(bar_count) == 1:
            npunto = pos_count[0]  # Number of bar positions
            for j in range(npunto):
                # Handle odd number of bars (last position gets single bar)
                if j == npunto - 1 and bar_count[0] % 2 == 1:
                    sec1[idx] = (Steel, 1, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                else:
                    # Place two bars symmetrically
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                idx += 1
        else:
            # Subcase 2a: Both configurations have even number of bars
            if bar_count[0]%2 == 0 and bar_count[1]%2 == 0:
                # Place first configuration
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                # Place second configuration
                jini = j+1  # Continue from where first configuration ended
                npunto = pos_count[1]
                for j in range(npunto):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
            # Subcase 2b: Both configurations have odd number of bars
            elif bar_count[0]%2 == 1 and bar_count[1]%2 == 1:
                
                npunto = pos_count[0]
                for j in range(npunto-1):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[0], yloc, z2col/2, yloc, z2col/2)
                idx += 1
                
                npunto = pos_count[1]
                jini = j+1
                for j in range(npunto-1):
                    j = jini+j
                    sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                sec1[idx] = (Steel, 1, nlist[1], yloc, -z2col/2, yloc, -z2col/2)
                idx += 1
            
            # Subcase 2c: Mixed even/odd configurations
            else:
                # Reorganize to place even configuration first
                bar_count, istrue = ordenar_lista_par_impar(bar_count)
                pos_count = [(ct // 2) + (ct % 2) for ct in bar_count]
                if istrue == 'True':
                    nlist = [nlist[1],nlist[0]]
                # Como va si o si el numero par primero, se tiene que:
                npunto = pos_count[0]
                for j in range(npunto):
                    sec1[idx] = (Steel, 2, nlist[0], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                    idx += 1
                
                # Ahora va el numero impar.,
                if bar_count[1] == 1:
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1
                else:
                    npunto = pos_count[1]
                    jini = j+1
                    for j in range(npunto-1):
                        j = jini+j
                        sec1[idx] = (Steel, 2, nlist[1], yloc, z1col - sign * (c + z2col * j), yloc, sign * (c + z2col * j) - z1col)
                        idx += 1
                    sec1[idx] = (Steel, 1, nlist[1], yloc, 0, yloc, 0)
                    idx += 1

        return idx
    

    # Añadir barras de acero en las posiciones TOP, BOTTOM y MIDDLE
    suma = 6
    suma = add_steel2(suma, cT, NpTop, nTlist, y1col - c, (BCol - 2 * c) / (NTop - 1))
    suma = add_steel2(suma, cB, NpBtt, nBlist, c - y1col, (BCol - 2 * c) / (NBtt - 1))

    # Barras en la sección MIDDLE
    y2col = (HCol - 2 * c) / (NpMdd + 1)
    y1coln = y1col - y2col
    for i in range(NpMdd):
        if i == NpMdd - 1 and NMiddle % 2 == 1:
            sec1[suma] = (Steel, 1, nMlist[0], y1coln - (c + y2col * i), c - z1col, y1coln - (c + y2col * i), c - z1col)
        else:
            sec1[suma] = (Steel, 2, nMlist[0], y1coln - (c + y2col * i), z1col - c, y1coln - (c + y2col * i), c - z1col)
        suma += 1

    return sec1, rect_patches

