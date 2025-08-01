# ============================ IMPORTAR LIBRERIAS ============================
# Flask web framework imports for creating the web application
from flask import Flask, render_template,request,session,redirect, jsonify, session, url_for
# Django imports for handling static files (may not be used in pure Flask app)
from django.conf import settings
from django.conf.urls.static import static
# OpenSeesPy imports for structural analysis
from openseespy.opensees import *
import opseestools.utilidades as ut      # Utility functions for OpenSees
import opseestools.analisis as an        # Analysis functions for OpenSees

# Standard library and scientific computing imports
import os                               # Operating system interface
import numpy as np                      # Numerical computing library
import Utilities_DN as ut_DN           # Custom utilities for fiber sections

# Image processing and encoding libraries
import io                              # Input/output operations in memory
import base64                          # Base64 encoding for image transfer

# Matplotlib configuration and imports
#import matplotlib
#matplotlib.use('Agg')  # Set backend to 'Agg' for non-GUI rendering (commented out)

# Matplotlib plotting libraries
import matplotlib.pyplot as plt        # Main plotting interface
import matplotlib.patches as patches   # Geometric patches for section visualization
import opsvis as opsv                  # OpenSees visualization tools

from PIL import Image                  # Python Imaging Library

# ============================ FLASK APPLICATION SETUP ============================
app = Flask(__name__)                  # Create Flask application instance
app.secret_key = 'supersecretkey'     # Secret key for session management (should be more secure in production)

app.config['UPLOAD_FOLDER'] = 'static' # Configure upload folder for static files

# ============================ MAIN NAVIGATION ROUTES ============================
@app.route('/') # Main landing page route
def home():
    """
    Render the home page of the StructPyn application.
    
    This is the main landing page that users see when they first visit the application.
    
    Returns
    -------
    str
        Rendered HTML template for the home page
        
    Notes
    -----
    This route handles GET requests to the root URL ('/') and serves as the
    entry point for the structural analysis web application.
    """
    return render_template('home.html') # Render the home page template

@app.route('/about')
def about():
    """
    Render the about page with information about the application.
    
    Returns
    -------
    str
        Rendered HTML template for the about page
        
    Notes
    -----
    Provides information about the StructPyn application, its purpose,
    and the team behind its development.
    """
    return render_template('about.html')

@app.route('/contact_us')
def contact_us():
    """
    Render the contact us page with a feedback form.
    
    Returns
    -------
    str
        Rendered HTML template for the contact page
        
    Notes
    -----
    Displays a form where users can submit their name, email, and message
    to provide feedback about the application.
    """
    return render_template('contact_us.html')

@app.route('/contact', methods=['POST'])
def contact():
    """
    Process contact form submissions from users.
    
    Handles POST requests containing user feedback including name, email,
    and message. Currently prints the data to console but can be extended
    to save to database or send emails.
    
    Returns
    -------
    str
        Rendered contact page template with success message
        
    Form Data
    ---------
    name : str
        User's full name
    email : str
        User's email address
    message : str
        User's feedback message
        
    Notes
    -----
    This function processes form data submitted via POST request and
    provides confirmation to the user that their message was received.
    Future enhancements could include email notifications or database storage.
    """
    # Extract form data from POST request
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']
    
    # Process contact form data (currently just console output)
    # TODO: Add database storage or email functionality
    print(f"Name: {name}")
    print(f"Email: {email}")
    print(f"Message: {message}")
    
    # Return confirmation message to user
    return render_template('contact_us.html', message="Thank you for your feedback!")

# ============================ STRUCTURAL ANALYSIS WORKFLOW ROUTES ============================

@app.route('/generate_nodes', methods=['POST'])
def generate_nodes():
    """
    Generate and visualize structural nodes based on coordinate inputs.
    
    Creates a scatter plot showing the structural nodes at the intersection
    of provided X and Y coordinates. Stores coordinates in session for
    use in subsequent analysis steps.
    
    Returns
    -------
    json
        JSON response containing base64-encoded image of the node plot
        
    Request JSON
    ------------
    x : list of float
        X-coordinates for the structural grid
    y : list of float  
        Y-coordinates for the structural grid
        
    Session Variables
    -----------------
    x_coords : list
        Stored X-coordinates for later use
    y_coords : list
        Stored Y-coordinates for later use
        
    Notes
    -----
    - Generates nodes at every intersection of X and Y coordinates
    - Creates a matplotlib figure with customized styling
    - Returns image as base64-encoded string for web display
    - Grid coordinates are essential for defining the structural layout
    
    Examples
    --------
    Request body:
    {
        "x": [0, 4, 8],
        "y": [0, 3, 6, 9]
    }
    
    This would create nodes at: (0,0), (0,3), (0,6), (0,9), (4,0), (4,3), etc.
    """
    # Parse JSON data from AJAX request
    data = request.get_json()
    x_coords = request.json.get('x', [])  # X-coordinates of structural grid
    y_coords = request.json.get('y', [])  # Y-coordinates of structural grid

    # Store coordinates in session for use in subsequent steps
    session['x_coords'] = x_coords
    session['y_coords'] = y_coords
    
    # Create matplotlib figure for node visualization
    plt.figure(figsize=(6, 6))
    ax = plt.gca()
    
    # Plot nodes at intersections of X and Y coordinates
    for i in range(len(x_coords)):
        for j in range(len(y_coords)):
            plt.plot(x_coords[i], y_coords[j], '.k', markersize=9)  # Black dots for nodes
        
    # Set axis labels
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    
    # Customize plot appearance
    ax.grid(True, alpha = 0.4)              # Light grid for reference
    ax.spines['top'].set_visible(False)     # Remove top border
    ax.spines['right'].set_visible(False)   # Remove right border
    
    # Set font properties for professional appearance
    plt.rcParams.update({'font.size': 11, 'font.family': 'Calibri'})
    
    # Convert plot to base64-encoded image for web transmission
    buf = io.BytesIO()                      # Create in-memory buffer
    plt.savefig(buf, format='png', dpi=300) # Save high-resolution image
    buf.seek(0)                             # Reset buffer position
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')  # Encode to base64
    buf.close()                             # Clean up buffer
    
    # Return JSON response with encoded image
    return jsonify(image=image_base64)

@app.route('/modulo1', methods=['GET'])
def modulo1():
    """
    Render the first module page for structural input definition.
    
    Returns
    -------
    str
        Rendered HTML template for module 1
        
    Notes
    -----
    Module 1 typically handles basic structural geometry definition
    including node coordinates and structural layout parameters.
    """
    return render_template('modulo1.html')

@app.route('/modulo2', methods=['GET'])
def modulo2():
    """
    Render the second module page for advanced structural parameters.
    
    Returns
    -------
    str
        Rendered HTML template for module 2
        
    Notes
    -----
    Module 2 handles more advanced structural parameters such as
    loads, material properties, and analysis settings.
    """
    return render_template('modulo2.html')

@app.route('/step2', methods=['GET', 'POST'])
def step2():
    """
    Handle structural loads and material properties input (Step 2).
    
    GET: Renders the step 2 form with previously entered coordinates
    POST: Processes and stores seismic parameters, loads, and material properties
    
    Returns
    -------
    str or json
        GET: Rendered HTML template with coordinate data
        POST: JSON success message
        
    Request JSON (POST)
    -------------------
    sa : float
        Design spectral acceleration in g
    cortes_columnas : list of float
        Base shear forces for each column line in kN
    cargas_vigas : list of float
        Distributed loads on beams in kN/m
    cargas_techo : list of float
        Roof loads in kN/m
    fc_concreto : float
        Concrete compressive strength in MPa
    fy_acero : float
        Steel yield strength in MPa
        
    Session Variables
    -----------------
    sa : float
        Design spectral acceleration
    cortes_columnas : list
        Column base shear forces
    cargas_vigas : list
        Beam distributed loads
    cargas_techo : list
        Roof loads
    fc_concreto : float
        Concrete strength
    fy_acero : float
        Steel yield strength
        
    Notes
    -----
    This step is crucial for defining the loading conditions and material
    properties that will be used in the structural analysis. The spectral
    acceleration is used for seismic analysis calculations.
    """
    if request.method == 'POST':
        # Extract structural parameters from JSON request
        data = request.get_json()
        sa = float(data.get('sa'))                                    # Design spectral acceleration
        cortes_columnas = [float(i) for i in data.get('cortes_columnas')]  # Column base shears
        cargas_vigas = [float(i) for i in data.get('cargas_vigas')]        # Beam distributed loads
        cargas_techo = [float(i) for i in data.get('cargas_techo')]        # Roof loads
        fc_concreto = float(data.get('fc_concreto'))              # Concrete compressive strength
        fy_acero = float(data.get('fy_acero'))                    # Steel yield strength
        
        # Store all parameters in session for later use
        session['sa'] = sa
        session['cortes_columnas'] = cortes_columnas
        session['cargas_vigas'] = cargas_vigas
        session['fc_concreto'] = fc_concreto
        session['fy_acero'] = fy_acero
        
        return jsonify({"message": "success"})
    
    # For GET requests, load coordinates from session and render form
    x_coords = session.get('x_coords', [])
    y_coords = session.get('y_coords', [])
    return render_template('step2.html', x_coords=x_coords, y_coords=y_coords)

@app.route('/step3', methods=['GET', 'POST'])
def step3():
    """
    Handle column section design and reinforcement configuration (Step 3).
    
    GET: Renders the column section design form
    POST: Processes column parameters and generates fiber section visualization
    
    Returns
    -------
    str or json
        GET: Rendered HTML template for step 3
        POST: JSON with base64-encoded section image
        
    Request JSON (POST)
    -------------------
    valBsec : float
        Column width in meters
    valHsec : float
        Column height in meters
    valRsec : float
        Concrete cover in meters
    cbarMdd : list of int
        Number of middle reinforcement bars per configuration
    nbarMdd : list of str
        Bar sizes for middle reinforcement ('barnum3' to 'barnum8')
    cbarTop : list of int
        Number of top reinforcement bars per configuration
    nbarTop : list of str
        Bar sizes for top reinforcement
    cbarBtt : list of int
        Number of bottom reinforcement bars per configuration
    nbarBtt : list of str
        Bar sizes for bottom reinforcement
        
    Session Variables
    -----------------
    BCol, HCol, c : float
        Column dimensions and cover
    cM, nM : list
        Middle reinforcement configuration
    cT, nT : list
        Top reinforcement configuration
    cB, nB : list
        Bottom reinforcement configuration
        
    Notes
    -----
    This step generates a detailed fiber section model for columns including:
    - Concrete core and cover regions
    - Steel reinforcement distribution
    - Visual representation with color-coded bar sizes
    - Proper handling of even/odd bar configurations
    
    The visualization uses different colors for different bar sizes:
    - #3 bars: Brown (#B2796E)
    - #4 bars: Yellow-green (#B0AD70)
    - #5 bars: Green (#7EB070)
    - #6 bars: Cyan (#6EB4B2)
    - #7 bars: Blue (#707CB0)
    - #8 bars: Purple (#B26EB0)
    """
    if request.method == 'POST':
        # Extract column section parameters from JSON request
        data = request.get_json()
        BCol = float(data.get('valBsec'))     # Column width
        HCol = float(data.get('valHsec'))     # Column height
        c = float(data.get('valRsec'))        # Concrete cover
        
        # Extract reinforcement configuration
        cM = [int(i) for i in data.get('cbarMdd')]  # Number of middle bars
        nM = data.get('nbarMdd')                    # Middle bar sizes
        cT = [int(i) for i in data.get('cbarTop')]  # Number of top bars
        nT = data.get('nbarTop')                    # Top bar sizes
        cB = [int(i) for i in data.get('cbarBtt')]  # Number of bottom bars
        nB = data.get('nbarBtt')                    # Bottom bar sizes

        # Ensure all bar parameters are lists (handle single values)
        if isinstance(nM, str):
            nM = [nM]
        if isinstance(nT, str):
            nT = [nT]
        if isinstance(nB, str):
            nB = [nB]

        if isinstance(cM, float):
            cM = [cM]
        if isinstance(cT, float):
            cT = [cT]
        if isinstance(cB, float):
            cB = [cB]

        # Store column parameters in session
        session['BCol'] = BCol
        session['HCol'] = HCol
        session['c'] = c
        session['cM'] = cM
        session['nM'] = nM
        session['cT'] = cT
        session['nT'] = nT
        session['cB'] = cB
        session['nB'] = nB

        # Generate fiber section visualization data
        fiber_layers, rect_patches = ut_DN.Graph_FiberSection_Colums(BCol,HCol,c,cT, cM, cB, nT, nM, nB)

        # Create section visualization plot
        fig, ax = plt.subplots(figsize=(6, 6))
        
        # Define colors for different concrete regions
        colors = {1: '#9F9F9F',   # Confined concrete (gray)
                 3: '#D9D9D9'}    # Unconfined concrete (light gray)

        # Draw concrete patches (rectangular regions)
        for rect in rect_patches:
            _, _, _, y1, x1, y2, x2 = rect  # Extract coordinates
            width = x2 - x1   # Calculate width
            height = y2 - y1  # Calculate height
            color = colors[rect[0]]  # Get color based on material tag
            # Create and add rectangle patch
            rect = patches.Rectangle((x1, y1), width, height, linewidth=1, 
                                   edgecolor='black', facecolor=color)
            ax.add_patch(rect)

        # Draw steel reinforcement bars
        for layer in fiber_layers:
            _, _, mark_size, y1, x1, y2, x2 = layer  # Extract layer data
            
            # Map bar areas to visualization parameters
            if mark_size == 0.000071:    # #3 bar
                mark_size_val = 7
                mark_color = '#B2796E'   # Brown
            elif mark_size == 0.000127:  # #4 bar
                mark_size_val = 8
                mark_color = '#B0AD70'   # Yellow-green
            elif mark_size == 0.000198:  # #5 bar
                mark_size_val = 9
                mark_color = '#7EB070'   # Green
            elif mark_size == 0.000286:  # #6 bar
                mark_size_val = 10
                mark_color = '#6EB4B2'   # Cyan
            elif mark_size == 0.000387:  # #7 bar
                mark_size_val = 11
                mark_color = '#707CB0'   # Blue
            elif mark_size == 0.000508:  # #8 bar
                mark_size_val = 12
                mark_color = '#B26EB0'   # Purple
            
            border_color = 'lightgray'   # Light border for all bars
            
            # Plot steel bars as circles
            x_positions = [x1, x2]
            y_positions = [y1, y2]
            ax.plot(x_positions, y_positions, 'o', markersize=mark_size_val, 
                   color=mark_color, markeredgecolor=border_color, markeredgewidth=1.0)

        # Customize plot appearance
        ax.spines['top'].set_visible(False)     # Remove top border
        ax.spines['right'].set_visible(False)   # Remove right border
        ax.set_aspect('equal', 'box')           # Equal aspect ratio for accurate geometry

        plt.xlabel('Section base')              # X-axis label
        plt.ylabel('Section height')            # Y-axis label

        # Set font properties
        plt.rcParams.update({'font.size': 11, 'font.family': 'Calibri'})
            
        # Convert plot to base64 for web transmission
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()

        return jsonify({"image": image_base64})
    
    return render_template('step3.html')

@app.route('/step4', methods=['GET', 'POST'])
def step4():
    """
    Handle beam section design and reinforcement configuration (Step 4).
    
    GET: Renders the beam section design form
    POST: Processes beam parameters and generates fiber section visualization
    
    Returns
    -------
    str or json
        GET: Rendered HTML template for step 4
        POST: JSON with base64-encoded section image
        
    Request JSON (POST)
    -------------------
    valBsec_Vig : float
        Beam width in meters
    valHsec_Vig : float
        Beam height in meters
    valRsec_Vig : float
        Concrete cover in meters
    cbarTop_Vig : list of int
        Number of top reinforcement bars per configuration
    nbarTop_Vig : list of str
        Bar sizes for top reinforcement ('barnum3' to 'barnum8')
    cbarBtt_Vig : list of int
        Number of bottom reinforcement bars per configuration
    nbarBtt_Vig : list of str
        Bar sizes for bottom reinforcement
        
    Session Variables
    -----------------
    BVig, HVig, c_Vig : float
        Beam dimensions and cover
    cT_Vig, nT_Vig : list
        Top reinforcement configuration
    cB_Vig, nB_Vig : list
        Bottom reinforcement configuration
        
    Notes
    -----
    Similar to step 3 but for beam sections. Key differences:
    - No middle reinforcement (only top and bottom)
    - Different section proportions (typically wider and shallower)
    - Same visualization scheme with color-coded reinforcement
    
    Beam sections are simpler than columns as they typically only require
    top and bottom reinforcement without intermediate bars.
    """
    if request.method == 'POST':
        # Extract beam section parameters (similar to step3 but for beams)
        data = request.get_json()
        BVig = float(data.get('valBsec_Vig'))     # Beam width
        HVig = float(data.get('valHsec_Vig'))     # Beam height
        c_Vig = float(data.get('valRsec_Vig'))    # Beam concrete cover
        
        # Extract beam reinforcement (only top and bottom, no middle)
        cT_Vig = [int(i) for i in data.get('cbarTop_Vig')]  # Top bars
        nT_Vig = data.get('nbarTop_Vig')
        cB_Vig = [int(i) for i in data.get('cbarBtt_Vig')]  # Bottom bars
        nB_Vig = data.get('nbarBtt_Vig')

        # Ensure parameters are lists
        if isinstance(nT_Vig, str):
            nT_Vig = [nT_Vig]
        if isinstance(nB_Vig, str):
            nB_Vig = [nB_Vig]

        if isinstance(cT_Vig, float):
            cT_Vig = [cT_Vig]
        if isinstance(cB_Vig, float):
            cB_Vig = [cB_Vig]

        # Store beam parameters in session
        session['BVig'] = BVig
        session['HVig'] = HVig
        session['c_Vig'] = c_Vig
        session['cT_Vig'] = cT_Vig
        session['nT_Vig'] = nT_Vig
        session['cB_Vig'] = cB_Vig
        session['nB_Vig'] = nB_Vig

        # Generate beam fiber section visualization (same process as columns)
        fiber_layers, rect_patches = ut_DN.Graph_FiberSection_Beams(BVig,HVig,c_Vig, cT_Vig, cB_Vig, nT_Vig, nB_Vig)

        # Create the section graph
        fig, ax = plt.subplots(figsize=(6, 6))
        colors = {1: '#9F9F9F', 3: '#D9D9D9'}

        # Draw concrete patches (rectangular regions)
        for rect in rect_patches:
            _, _, _, y1, x1, y2, x2 = rect  # Extract coordinates
            width = x2 - x1   # Calculate width
            height = y2 - y1  # Calculate height
            color = colors[rect[0]]  # Get color based on material tag
            # Create and add rectangle patch
            rect = patches.Rectangle((x1, y1), width, height, linewidth=1, 
                                   edgecolor='black', facecolor=color)
            ax.add_patch(rect)

        # Draw steel reinforcement bars
        for layer in fiber_layers:
            _, _, mark_size, y1, x1, y2, x2 = layer  # Extract layer data
            
            # Map bar areas to visualization parameters
            if mark_size == 0.000071:    # #3 bar
                mark_size_val = 7
                mark_color = '#B2796E'   # Brown
            elif mark_size == 0.000127:  # #4 bar
                mark_size_val = 8
                mark_color = '#B0AD70'   # Yellow-green
            elif mark_size == 0.000198:  # #5 bar
                mark_size_val = 9
                mark_color = '#7EB070'   # Green
            elif mark_size == 0.000286:  # #6 bar
                mark_size_val = 10
                mark_color = '#6EB4B2'   # Cyan
            elif mark_size == 0.000387:  # #7 bar
                mark_size_val = 11
                mark_color = '#707CB0'   # Blue
            elif mark_size == 0.000508:  # #8 bar
                mark_size_val = 12
                mark_color = '#B26EB0'   # Purple
            
            border_color = 'lightgray'   # Light border for all bars
            
            # Plot steel bars as circles
            x_positions = [x1, x2]
            y_positions = [y1, y2]
            ax.plot(x_positions, y_positions, 'o', markersize=mark_size_val, 
                   color=mark_color, markeredgecolor=border_color, markeredgewidth=1.0)

        # Customize plot appearance
        ax.spines['top'].set_visible(False)     # Remove top border
        ax.spines['right'].set_visible(False)   # Remove right border
        ax.set_aspect('equal', 'box')           # Equal aspect ratio for accurate geometry

        plt.xlabel('Section base')              # X-axis label
        plt.ylabel('Section height')            # Y-axis label

        # Set font properties
        plt.rcParams.update({'font.size': 11, 'font.family': 'Calibri'})
            
        # Convert plot to base64 for web transmission
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()

        return jsonify({"image": image_base64})
    
    return render_template('step4.html')

@app.route('/step5', methods=['GET', 'POST'])
def step5():
    """
    Perform complete structural analysis including pushover analysis (Step 5).
    
    GET: Renders the analysis results page
    POST: Executes full OpenSees analysis and generates capacity curves
    
    Returns
    -------
    str or json
        GET: Rendered HTML template for step 5
        POST: JSON with analysis results and visualization images
        
    Analysis Process
    ----------------
    1. Load all parameters from previous steps
    2. Create OpenSees model with nodes, elements, and materials
    3. Apply gravity loads and perform gravity analysis
    4. Perform eigenvalue analysis for fundamental period
    5. Execute pushover analysis up to 5% roof drift
    6. Generate capacity curve and identify key performance points
    
    Response JSON (POST)
    --------------------
    image : str
        Base64-encoded capacity curve plot
    defo1 : str
        Base64-encoded initial deformed shape
    defo2 : str
        Base64-encoded final pushover deformed shape
        
    Key Analysis Results
    --------------------
    - Fundamental period of vibration
    - Capacity curve (roof drift vs normalized base shear)
    - Maximum capacity point
    - 80% capacity point (for performance assessment)
    - Deformed shapes at different analysis stages
    
    Notes
    -----
    This is the most computationally intensive step that performs:
    
    1. **Model Generation**: Creates 2D frame model with fiber sections
    2. **Mass Assignment**: Distributes masses based on tributary areas
    3. **Rigid Diaphragm**: Implements floor diaphragm constraints
    4. **Gravity Analysis**: Applies dead and live loads
    5. **Pushover Analysis**: Applies lateral forces up to target drift
    6. **Results Processing**: Generates capacity curves and identifies key points
    
    The analysis follows standard pushover procedures with:
    - Inverted triangular load pattern
    - Displacement-controlled analysis
    - Target drift of 5% of building height
    - Performance point identification at maximum and 80% capacity
    
    Error Handling
    --------------
    The analysis may fail due to:
    - Convergence issues in nonlinear analysis
    - Insufficient reinforcement causing early failure
    - Geometric instabilities
    - Material model limitations
    
    Performance Metrics
    -------------------
    - **V/W**: Normalized base shear coefficient
    - **Roof Drift**: Percentage of building height
    - **Ductility**: Ratio of ultimate to yield displacement
    - **Overstrength**: Ratio of maximum to design capacity
    """
    if request.method == 'POST':

        # ============================ 1) LOAD PARAMETERS FROM PREVIOUS STEPS ============================
        # Retrieve all stored parameters from session
        
        # Structural geometry coordinates
        xloc = session.get('x_coords', [])  # X-coordinates of grid
        yloc = session.get('y_coords', [])  # Y-coordinates of grid

        # Seismic design parameters and loads
        Sad = session.get('sa', [])                    # Design spectral acceleration
        CrtBase = session.get('cortes_columnas', [])   # Column base shear forces

        # Load parameters for beams
        val_Mload = session.get('cargas_vigas', [])    # Intermediate floor loads
        val_Rload = session.get('cargas_techo', [])    # Roof loads

        # Material properties (convert to Pa from MPa)
        fc = session.get('fc_concreto', [])*1000       # Concrete strength in Pa
        fy = session.get('fy_acero', [])*1000          # Steel yield strength in Pa

        # Column section properties
        BCol = session.get('BCol')  # Column width
        HCol = session.get('HCol')  # Column height
        c = session.get('c')        # Cover
        cM = session.get('cM')      # Middle bar counts
        nM = session.get('nM')      # Middle bar sizes
        cT = session.get('cT')      # Top bar counts
        nT = session.get('nT')      # Top bar sizes
        cB = session.get('cB')      # Bottom bar counts
        nB = session.get('nB')      # Bottom bar sizes

        # Beam section properties
        BVig = session.get('BVig')      # Beam width
        HVig = session.get('HVig')      # Beam height
        c_Vig = session.get('c_Vig')    # Beam cover
        cT_Vig = session.get('cT_Vig')  # Beam top bars
        nT_Vig = session.get('nT_Vig')  # Beam top bar sizes
        cB_Vig = session.get('cB_Vig')  # Beam bottom bars
        nB_Vig = session.get('nB_Vig')  # Beam bottom bar sizes

        # ============================ 2) INITIALIZE OPENSEES MODEL ============================
        wipe()                                      # Clear any existing model
        diafragma = 1                              # Enable rigid diaphragm (1=yes, 0=no)
        pushlimit = 0.05                           # Pushover drift limit (5%)
        model('basic','-ndm',2,'-ndf',3)           # 2D model with 3 DOF per node (x,y,rotation)

        # ============================ 3) GENERATE STRUCTURAL NODES ============================
        Npisos = len(yloc)-1                       # Number of stories
        nx = len(xloc)                             # Number of bays in X direction
        ny = len(yloc)                             # Number of levels in Y direction
        
        # Create nodes at grid intersections
        for i in range(ny):                        # Loop through Y coordinates (levels)
            for j in range(nx):                    # Loop through X coordinates (bays)
                nnode = 1000*(j+1)+i               # Unique node tag: bay*1000 + level
                node(nnode, xloc[j], yloc[i])      # Create node with coordinates

        # ============================ 4) BOUNDARY CONDITIONS AND MASS ASSIGNMENT ============================
        empotrado = [1,1,1]                        # Fixed boundary condition [x,y,rotation]
        fixY(0.0,*empotrado)                       # Fix all nodes at ground level (y=0)
        
        # Calculate and assign masses based on tributary areas and seismic forces
        Masa_list = np.zeros((Npisos,len(CrtBase))) # Initialize mass matrix
        for piso in range(Npisos):                  # For each story
            for indx, crt in enumerate(CrtBase):    # For each column line
                # Calculate mass from base shear: M = V/(Sa*g), distributed per story
                Masa_list[piso,indx] = ((crt/Sad)/9.81)/Npisos
                
        Wedificio = np.sum(CrtBase)/Sad             # Total building weight
        
        # Assign calculated masses to nodes
        for i in range(1,ny):                       # Skip ground level nodes
            for j in range(nx):                     # For each bay
                nodemass = 1000*(j+1)+i             # Node tag
                # Assign mass in X and Y directions, zero rotational mass
                mass(nodemass,Masa_list[i-1][j],Masa_list[i-1][j],0.0)

        # ============================ 5) RIGID DIAPHRAGM CONSTRAINTS ============================
        if diafragma == 1:                          # If rigid diaphragm is enabled
            for j in range(1,ny):                   # For each floor level
                for i in range(1,nx):               # For each bay (skip first as master)
                    masternode = 1000 + j           # First node of each floor as master
                    slavenode = 1000*(i+1) + j      # Other nodes as slaves
                    # Couple horizontal displacement (DOF 1)
                    equalDOF(masternode,slavenode,1)

        # ============================ 6) GENERATE FIBER SECTIONS ============================
        # Create column fiber section
        sec1, tag1 = ut_DN.fiber_elemens_Columns(BCol, HCol, c, cT, cM, cB, nT, nM, nB, fc, fy, yloc)
        opsv.fib_sec_list_to_cmds(sec1)            # Convert to OpenSees commands
        beamIntegration('Lobatto', tag1, tag1, 5)   # 5-point Lobatto integration

        # Create beam fiber section
        sec2, tag2 = ut_DN.fiber_elemens_Beams(BVig, HVig, c_Vig, cT_Vig, cB_Vig, nT_Vig, nB_Vig, fc, fy, xloc)
        opsv.fib_sec_list_to_cmds(sec2)            # Convert to OpenSees commands
        beamIntegration('Lobatto', tag2, tag2, 5)   # 5-point Lobatto integration

        # ============================ 7) GEOMETRIC TRANSFORMATIONS ============================
        lineal = 1                                  # Linear transformation tag
        geomTransf('Linear',lineal)                 # For beams (small deformations)
        pdelta = 2                                  # P-Delta transformation tag
        geomTransf('PDelta',pdelta)                 # For columns (include P-Delta effects)

        # ============================ 8) GENERATE COLUMN ELEMENTS ============================
        TagColumns = []                             # Store column element tags
        for i in range(ny-1):                       # For each story
            for j in range(nx):                     # For each bay
                nodeI = 1000*(j+1)+i                # Bottom node
                nodeJ = 1000*(j+1)+(i+1)            # Top node
                eltag = 10000*(j+1) + i             # Unique element tag
                TagColumns.append(eltag)            # Store tag
                # Create force-based beam-column element with P-Delta transformation
                element('forceBeamColumn',eltag,nodeI,nodeJ,pdelta,tag1)

        # ============================ 9) GENERATE BEAM ELEMENTS ============================
        TagVigas = []                               # Store beam element tags
        for i in range(1, ny):                      # For each floor level (skip ground)
            for j in range(nx - 1):                 # For each span
                nodeI = 1000 * (j + 1) + i          # Left node
                nodeJ = 1000 * (j + 2) + i          # Right node
                eltag = 100000 * (j + 1) + i        # Unique element tag
                TagVigas.append(eltag)              # Store tag
                # Create force-based beam-column element with linear transformation
                element('forceBeamColumn', eltag, nodeI, nodeJ, lineal, tag2)

        # ============================ 10) APPLY GRAVITY LOADS ============================
        timeSeries('Linear', 1)                    # Linear time series for gravity
        pattern('Plain', 1, 1)                     # Load pattern for gravity loads
        
        # Apply column self-weight loads
        for i in range(nx):                         # For each column line
            for j in range(1, ny):                  # For each story
                nodeCol = 1000 * (i + 1) + j        # Column node
                # Calculate column weight: Volume * unit weight (24 kN/m³ for concrete)
                wcol_list = BCol * HCol * 24 * (yloc[j] - yloc[j - 1])
                load(nodeCol, 0.0, -wcol_list, 0.0) # Apply vertical load (negative = downward)
                
        # Apply beam distributed loads
        for i in range(1,ny):                       # For each floor level
            for j in range(nx-1):                   # For each beam span
                if i == Npisos+1:                   # If roof level
                    eltag = 100000*(j+1) + i
                    # Apply roof loads
                    eleLoad('-ele',eltag,'-type','beamUniform',-val_Rload[j])
                else:                               # If intermediate floor
                    eltag = 100000*(j+1) + i
                    # Apply floor loads
                    eleLoad('-ele',eltag,'-type','beamUniform',-val_Mload[j])

        # Generate initial deformation plot (before analysis)
        fig_defo1 = plt.figure()
        opsv.plot_defo()

        # Convert to base64 for web transmission
        buf_defo1 = io.BytesIO()
        plt.savefig(buf_defo1, format='png')
        buf_defo1.seek(0)
        image_base64_defo1 = base64.b64encode(buf_defo1.read()).decode('utf-8')
        buf_defo1.close()
        plt.close()

        # ============================ 11) GRAVITY ANALYSIS ============================
        w1 = eigen(1)                               # Calculate first eigenvalue
        T = 2 * 3.1416 / np.sqrt(w1)              # Fundamental period T = 2π/√λ
        an.gravedad()                               # Perform gravity analysis
        loadConst('-time', 0.0)                    # Make gravity loads constant

        # ============================ 12) PUSHOVER ANALYSIS ============================
        w2 = eigen(1)                               # Recalculate eigenvalue after gravity
        T2 = 2 * 3.1416 / np.sqrt(w2)             # Updated fundamental period

        # Define lateral load pattern for pushover
        timeSeries('Linear', 2)                     # Linear time series for lateral loads
        pattern('Plain', 2, 2)                      # Lateral load pattern

        # Identify roof node and building height
        tagsnodos = getNodeTags()                   # Get all node tags
        ntecho = tagsnodos[-1]                      # Roof node (highest tag)
        hedif = nodeCoord(ntecho)[1]                # Building height

        # Define pushover load distribution (inverted triangular)
        POnodes = tagsnodos[int(1):int(len(tagsnodos) / nx)]  # Nodes for load application
        posnodes = []
        for i in range(len(POnodes)):
            posnodes.append(i + 1)                  # Position factors for triangular distribution
        valor = sum(posnodes)                       # Normalization factor

        # Apply distributed lateral loads
        for indx, val in enumerate(tagsnodos[int(1):int(len(tagsnodos) / nx)]):
            # Load proportional to height (triangular distribution)
            load(val, (indx + 1) / valor, 0.0, 0.0)

        # Execute pushover analysis
        [dtecho, Vcorte] = an.pushover2(0.05*hedif, 0.001, ntecho, 1, [hedif, Wedificio])

        # Generate final deformation plot
        fig_defo2 = plt.figure()
        opsv.plot_defo()
        plt.title('Pushover deformation')
        plt.xlabel('X Coordinate', fontsize=11)
        plt.ylabel('Y Coordinate', fontsize=11)

        # Convert to base64
        buf_defo2 = io.BytesIO()
        plt.savefig(buf_defo2, format='png')
        buf_defo2.seek(0)
        image_base64_defo2 = base64.b64encode(buf_defo2.read()).decode('utf-8')
        buf_defo2.close()
        plt.close()

        # ============================ PROCESS PUSHOVER RESULTS ============================
        # Convert absolute values to normalized performance metrics
        roof_drift = [(dtecho[i]/hedif)*100 for i in range(len(dtecho))]      # Roof drift as % of height
        base_shear = [Vcorte[i]/Wedificio for i in range(len(Vcorte))]        # Base shear coefficient V/W

        # Identify key performance points
        max_index = np.argmax(base_shear)           # Index of maximum capacity
        max_roof_drift = roof_drift[max_index]      # Roof drift at maximum capacity
        max_base_shear = base_shear[max_index]      # Maximum base shear coefficient

        # Find 80% capacity point (performance assessment criterion)
        base_shear_80 = 0.8 * max_base_shear
        index_80 = np.where(base_shear >= base_shear_80)[0][0]  # First occurrence of 80% capacity
        roof_drift_80 = roof_drift[index_80]
        base_shear_80_actual = base_shear[index_80]

        # ============================ GENERATE CAPACITY CURVE PLOT ============================
        fig = plt.figure()
        # Plot main capacity curve
        plt.plot(roof_drift, base_shear,  label='Capacity curve', color='#13272C')
        # Highlight maximum capacity point
        plt.plot(max_roof_drift, max_base_shear,'D', label='Max capacity', color='#E97132')
        plt.text(max_roof_drift, max_base_shear, 
                f'({np.around(max_roof_drift,2)},{np.around(max_base_shear,2)})', 
                fontsize=9, verticalalignment='bottom')
        # Highlight 80% capacity point
        plt.plot(roof_drift_80, base_shear_80_actual,'X', label='Capacity (80%)', color='#65A753')
        plt.text(roof_drift_80, base_shear_80_actual, 
                f'({np.around(roof_drift_80,2)},{np.around(base_shear_80_actual,2)})', 
                fontsize=9, verticalalignment='bottom')

        # Set labels and title
        plt.xlabel('Roof drift (%)', fontsize=11)
        plt.ylabel('Normalized seismic base shear (V/W)', fontsize=11)
        plt.title('RCFs Capacity curve')
        plt.legend()

        # Customize plot appearance
        plt.grid(True, alpha = 0.4)                 # Light grid
        plt.rcParams.update({'font.family': 'Calibri'})  # Font family

        # Convert capacity curve to base64
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        plt.close()

        # Return all analysis results as JSON
        return jsonify({"image": image_base64, "defo1": image_base64_defo1, "defo2": image_base64_defo2})

    return render_template('step5.html')

# ============================ APPLICATION ENTRY POINT ============================
if __name__ == '__main__':
    """
    Run the Flask development server.
    
    Starts the web application in debug mode for development purposes.
    In production, this should be replaced with a proper WSGI server.
    
    Notes
    -----
    Debug mode enables:
    - Automatic reloading when code changes
    - Detailed error messages in browser
    - Interactive debugger for exceptions
    
    For production deployment, use:
    - Gunicorn, uWSGI, or similar WSGI server
    - Proper environment configuration
    - Security considerations (disable debug mode)
    """
    app.run(debug=True)  # Start Flask development server with debugging enabled


