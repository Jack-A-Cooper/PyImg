# PyImgScale - Image Processing Tool

![Alt Text](util/v0.2/upscaled_1.png)

## Overview
PyImgScale is a local GUI image processing application built on PyQt5 and Pillow. It facilitates the upscaling, downscaling, and converting of images between a few common image formats. PyImgScale provides a user-friendly interface to navigate through the filesystem, select images for processing, and manage processing queues. It will make use of multithreading to process images as efficiently as possible over traditional singlethreaded programs.

It is still currently in active development.

## Current Version
v0.2

## Note
PyImgScale is not finished at the moment. There are still a few bugs, code cleaning, and features to implement (image upscaling/downscaling are close to being implemented, but just have not gotten around it just yet!). Single file and batch conversions of files should 

## Features
- **Filesystem Navigation**: Browse through your file system within the app to locate images. Customizable with the ability to change the working directory at any time. Default is set to the directory where the script resides.
- **Image Processing**: Upscale or downscale images with selectable scale factors. Currently allows for 1.5x, 2x, 4x, and 8x upscaling/downscaling. Multithreaded implementation promotes speed and efficiency.
- **Format Conversion**: Convert images between popular formats: PNG, JPG, BMP, TGA, and PDF.
- **Batch Processing**: Process multiple images at once, with progress tracking via a progress bar. Configure settings for single file, batch, or directory processing configurations.
- **Preview Thumbnails**: View thumbnails of the selected images after processing. See at a glance what files you have processed.
- **Customizable Save Directory**: Choose the directory where processed images will be saved. Whenever necessary, configure where you wish to save your processsed images.

## Showcase
![Alt Text](util/v0.2/upscaled_2.png)

![Alt Text](util/v0.2/upscaled_3.png)

![Alt Text](util/v0.2/upscaled_4.png)

![Alt Text](util/v0.2/upscaled_5.png)

## Prerequisites
Before running PyImgScale, ensure you have the following installed:
- Python 3.x
- PyQt5
- Pillow (PIL Fork)

You can install the required packages using pip:
```sh
pip install PyQt5 Pillow
```

## Usage
To start the application, navigate to the script's directory and run:
```sh
python PyImgScale.py
```

Once started, the application will present you with the main interface where you can navigate your filesystem, select images, choose processing options, and initiate image processing.

## Development Status
This tool is currently under development. Some features might not be fully implemented, and functionality is subject to change.

## Contributing
As a very small solo project, contributions to PyImgScale are not welcome. However, please feel free to fork the repository and modify it to your heart's content!

## License
PyImgScale is released under the [MIT License](LICENSE).

## Disclaimer
PyImgScale is in no way related to or apart of 'PyImg'.
