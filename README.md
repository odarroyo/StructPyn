# StructPyn_Website

StructPyn_Website is a web application designed to generate the capacity curve of regular moment-resisting reinforced concrete frame buildings. This repository contains all the necessary code and files to run the platform, including the `index.py` file and the `.html` files that make up the application.

## Table of Contents

1. [Project Structure](#project-structure)
2. [Installation](#installation)
3. [Usage](#usage)
4. [Demostration Video](#demostration-video)
6. [License](#license)

## Project Structure

The project is organized as follows:

### `static` Folder
Contains all static files used by the application:
- **css**: Contains `main.css`, which configures the containers and layout of the web pages.
- **images**: Includes logos, icons for Instagram, Facebook, email, etc., used for decorating the web pages.
- **manual**: The user manual describing how to use the platform to generate capacity curves.

### `templates` Folder
Contains all HTML files used in the platform:
- **layout.html**: Configures the navigation bar that appears on all pages.
- **home.html**: The homepage showing what the platform does, its modules, and an option to download the user manual.
- **about.html**: The "About" page describing the developer's work, collaborators, and the University's role.
- **contact_us.html**: The "Contact Us" page with a form to send messages, suggestions, or questions to the developer.
- **modulo1.html**: Introduction to the platform, providing context, motivation, project scope, and numerical considerations.
- **modulo2.html**: The first step for obtaining capacity curves, allowing users to input node coordinates and visualize their positions.
- **step2.html**: Configures parameters for generating the model, such as design `sa`, base shear for each column, distributed load on beams, and values of `f'c` and `fy`.
- **step3.html**: Generates fiber sections for columns and allows users to visualize the section.
- **step4.html**: Generates fiber sections for beams and allows users to visualize the section.
- **step5.html**: Generates the capacity curve, showing the pushover of the structure and the deformation of the frame under lateral loads.

### `index.py`
The core of the platform, running analyses and routing each URL using `@app`.

## Installation

To run the platform, follow these steps:

1. Clone the repository:
    ```sh
    git clone https://github.com/DanielaNovoa15/StructPyn.git
    ```

2. Navigate to the project directory:
    ```sh
    cd StructPyn/
    ```

3. Install the required libraries:
    ```sh
    pip install openseespy vfo opsvis opseestools flask django
    ```

## Usage

To run the model:

1. Open the command line and navigate to the project directory:
    ```sh
    cd /path/to/StructPyn_Website/
    ```

2. Install the necessary libraries as listed in the Installation section.

3. Run the application:
    ```sh
    python index.py
    ```

4. Open your web browser and go to `http://localhost:5000` to access the platform.

## Demostration Video

For a better understanding of how models are generated on our platform, we invite you to watch the following demonstration video:
https://youtu.be/wEHps176Kpw

## License

This project is licensed under the terms of the GNU GENERAL PUBLIC LICENSE.

Note: The moral rights of this web application belong to Daniela Novoa Ramírez, and the economic rights belong to the University of La Sabana.
