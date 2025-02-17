# Mediffusion

Diffusion models have significantly impacted the realm of image generation. In a bid to reduce the technical complexity, we aim to lower the entry barrier for the medical community. To achieve this, we have introduced *mediffusion*, a user-friendly diffusion package that can be effortlessly tailored to address medical problems with less than 20 lines of code. We have utilized various codebases, including [guided diffusion](https://github.com/openai/guided-diffusion) and [LDM](https://github.com/CompVis/latent-diffusion), enhancing their robustness for medical use cases. We plan to update this package regularly. Embracing the spirit of open science, we invite you to consider sharing  a demo notebook of your work should you choose to utilize this package.

Happy Coding!

## Setup and Installation

### Step 1: Create a Conda Environment

If you haven't installed Conda yet, you can download it from [here](https://docs.anaconda.com/anaconda/install/). After installing, create a new Conda environment by running:

```bash
conda create --name mediffusion python=3.10
```

Activate the environment:

```bash
conda activate mediffusion
```

### Step 2: Install PyTorch

Install PyTorch specifically for CUDA 11.8 by running:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Step 3: Install The Package

You can install the latest version from github using:

```bash
pip install mediffusion
```

This will install all the necessary packages.

## Training 
### 1. Hyperparameters
Before starting the training, it is recommended that you set up some global constants and environment variables:

```python
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
os.environ['WANDB_API_KEY'] = "WANDB-API-KEY"

TOTAL_IMAGE_SEEN = 40e6
BATCH_SIZE = 36
NUM_DEVICES = 2 # number of devices in CUDA_VISIBLE_DEVICES
TRAIN_ITERATIONS = int(TOTAL_IMAGE_SEEN / (BATCH_SIZE * NUM_DEVICES))
```

### 2. Preparing Data

To prepare the data, you need to create a dataset where each element is a dictionary. The dictionary should have the key "img" and may also contain additional keys like "cls" and "concat" depending on the type of condition. One way to do this is by using MONAI. Below is a sample code snippet:

```python
import monai as mn

train_data_dicts = [
    {"img": "./image1.dcm", "cls": 2},
    {"img": "./image2.dcm", "cls": 0}
]

valid_data_dicts = [
    {"img": "./image9.dcm", "cls": 1}
]

transforms = mn.transforms.Compose([
    mn.transforms.LoadImageD(keys="img"),
    mn.transforms.SelectItemsD(keys=["img","cls"]),
    mn.transforms.ScaleIntensityD(keys=["img"], minv=-1, maxv=1),
    mn.transforms.ToTensorD(keys=["img","cls"], dtype=torch.float, track_meta=False),
])

train_ds = mn.data.Dataset(data=train_data_dicts, transform=transforms) 
valid_ds = mn.data.Dataset(data=valid_data_dicts, transform=transforms)
train_sampler = torch.utils.data.RandomSampler(train_ds, replacement=True, num_samples=TOTAL_IMAGE_SEEN)
```

At the end of this step, you should have `train_ds`, `val_ds` and `train_sampler`.

### 3. Configuring Model

#### Configuration Fields Explanation

Below is a table that provides descriptions for each element in the configuration file:

| Section    | Field                   | Description                                           |
|------------|-------------------------|-------------------------------------------------------|
| diffusion  | timesteps               | The number of timesteps in the diffusion process      |
|            | schedule_name           | The name of the schedule (e.g., "cosine")             |
|            | enforce_zero_terminal_snr | Whether to enforce zero terminal SNR (True/False)    |
|            | schedule_params         | Parameters related to the diffusion schedule          |
|            | -- beta_start           | Starting value for beta in the schedule               |
|            | -- beta_end             | Ending value for beta in the schedule                 |
|            | -- cosine_s             | Parameter for cosine schedule                         |
|            | timestep_respacing      | Can be a list of respacings. For example, with 200 steps, [10,20] means in the first 100, get 10 samples and in the next 100, get 20 samples. |
|            | mean_type               | Type of mean model (e.g., "VELOCITY")                 |
|            | var_type                | Type of variance model (e.g., "LEARNED_RANGE")        |
|            | loss_type               | The type of loss to use (e.g., "MSE")                 |
| optimizer  | lr                      | Learning rate                                         |
|            | type                    | The type of optimizer to use                          |
| validation | classifier_cond_scale   | Classifier guidance scale for validation logging.     |
|            | protocol                | Inference protocol for logging validation results     |
|            | log_original            | Whether to log the original validation data (True/False)     | 
|            | log_concat              | Whether to log the concatenated images (True/False)     |
|            | log_cls_indices         | Whether to log the entire cls vector (default value of -1), or specefic indices from the cls vector (user should provide a list of desired cls indices)     |
| model      | input_size              | The input size of the model. Can be an integer for square and cube images or a list of integers for specific axes, like [64, 64, 32] |
|            | dims                    | Number of dimensions, 2 or 3 for 2D and 3D images     |
|            | attention_resolutions   | List of resolutions for attention layers              |
|            | channel_mult            | List of multipliers for each layer's channels         |
|            | dropout                 | Dropout rate                                          |
|            | in_channels             | Number of input channels (image channels + concat channels) |
|            | out_channels            | Number of output channels (image channels or image channels * 2 if learning the variance) |
|            | model_channels          | Number of convolution channels in the model           |
|            | num_head_channels       | Number of attention head channels                     |
|            | num_heads               | Number of attention heads                             |
|            | num_heads_upsample      | Number of attention head after upsampling             |
|            | num_res_blocks          | List of the number of residual blocks for each layer  |
|            | resblock_updown         | Whether to use residual blocks for down/up sampling (True/False) |
|            | use_checkpoint          | Whether to use checkpointing (True/False)             |
|            | use_new_attention_order | Whether to use the new attention ordering (True/False) |
|            | use_scale_shift_norm    | Whether to use scale-shift normalization (True/False) |
|            | scale_skip_connection   | Whether to scaleskip connections (True/False)         |
|            | num_classes             | Number of classes for conditioning                    |
|            | concat_channels         | Number of concatenatong channels for conditioning (for super-resolution or inpainting) |
|            | guidance_drop_prob      | Drop probability for the classifier free guidance scale training |

For sample configurations, please checkout the `sample_configs` directory.

**Note**: If a field is left out of the config file, the default value is infered based on this file: `mediffusion/default_config/default.yaml`.

#### Instantiating Model

You can instantiate the model using the configuration file and dataset as follows:

```python
from mediffusion import DiffusionModule

model = DiffusionModule(
    "./config.yaml",
    train_ds=train_ds,
    val_ds=valid_ds,
    dl_workers=2,
    train_sampler=train_sampler,
    batch_size=32,               # train batch size
    val_batch_size=16            # validation batch size (recommended size is half of batch_size)
)
```

### 4. Setting Up Trainer
You can set up the trainer using the `Trainer` class:

```python
from mediffusion import Trainer

trainer = Trainer(
    max_steps=TRAIN_ITERATIONS,
    val_check_interval=5000,
    root_directory="./outputs", # where to save the weights and logs
    precision="16-mixed",       # mixed precision training
    devices=-1,                 # use all the devices in CUDA_VISIBLE_DEVICES
    nodes=1,
    wandb_project="Your_Project_Name",
    logger_instance="Your_Logger_Instance",
)
```

### 5. Training the Model

Finally, to train your model, you simply call:

```python
trainer.fit(model)
```

## Prediction 
### 1. Loading the Model

First, import the `DiffusionModule` class and load the pre-trained model checkpoint. The model is then moved to the CUDA device and set to inference mode. Additionally, you may choose to enable half-precision for better performance:

```python
from mediffusion import DiffusionModule

model = DiffusionModule("./config.yaml")
model.load_ckpt("./outputs/pl/last.ckpt", ema=True)
model.cuda().half()
model.eval()
```

### 2. Preparing Input

Prepare the noise and model keyword arguments. Here, `"cls"` specifies the class condition and is set to 0:

```python
import torch

noise = torch.randn(1, 1, 256, 256)
model_kwargs = {"cls": torch.tensor([0]).cuda().half()}
```

**Note**: You can use other keys like `concat` and/or `cls_embed`. To find out more, look at the `tutorials` directory.

### 3. Making Predictions

To make a prediction, use the `predict` method from the `DiffusionModule` class:

```python
img = model.predict(
    noise, 
    model_kwargs=model_kwargs, 
    classifier_cond_scale=4, 
    inference_protocol="DDIM100"
)
```

- `noise`: The input noise tensor
- `model_kwargs`: A dictionary containing additional model configurations (e.g., class conditions)
- `classifier_cond_scale`: The scale used for the classifier free guidance condition during inference
- `inference_protocol`: The inference protocol to be used (e.g., `"DDIM100"`)

The `img` is the generated output based on the model's inference (`C:H:W(:D)`). To save the image, you need to transpose it first, due to the different axis conventions.

**Note**: The model currently supports the following solvers: `DDPM`,`DDIM`,`IDDIM`(for inverse diffusion), and `PLMS`. As an example, `"PLMS100"` means using the `PLMS` solver for `100` steps. 

#### 3.1 Outputting frames from diffusion steps for `DDPM` solver

The solver `DDPM_dump` will output frames corresponding to each diffusion step for the first element in the batch.  (Use a batch size of 1 to output all elements.)  The name of the frames is `os.environ['DDPM_DUMP_OUTPUT_BASENAME']-II-TT.png`, where `II` is the batch element number and `TT` is the diffusion step number.  For each batch, change the value of `os.environ['DDPM_DUMP_OUTPUT_BASENAME']` to include the batch number to avoid overwrites.

Here is code to convert the frames into a gif after the solver has completed:

```python
import glob
from tqdm.auto import tqdm
from PIL import Image

# Output one gif from a collection of input frames
def make_gif(
    base_filename, 
    input_format = "png",
    output_format = "gif", 
    duration = 100,
):
    image_glob      = f"{base_filename}*.{input_format}",
    output_filename = f"{base_filename}.{output_format}", 

    frames = []
    image_filenames = list(reversed(sorted(glob.glob(image_glob))))
    for image in tqdm(image_filenames):
        frames.append(Image.open(image))

    frames[0].save(
        output_filename, 
        format = output_format, 
        append_images = frames,
        save_all = True, 
        duration = duration, 
        loop = 0
    )
    
make_gif(os.environ['DDPM_DUMP_OUTPUT_BASENAME'])
```

## Tutorials

For more hands-on tutorials on how to effectively use this package, please check the `tutorials` folder in the GitHub repository. These tutorials provide step-by-step instructions, Colab notebooks, and explanations to help you get started with the software.

| File Name      | Description | Notebook Link |
|----------------|-------------|---------------|
| 01_2d_ddpm | Getting started with training a simple 2D class-conditioned DDPM. | [📓](https://github.com/BardiaKh/Mediffusion/tree/main/tutorials/01_2d_ddpm.ipynb) |
| 02_2d_inpainting | Image inpainting with 2D diffusion model (repaint method) | [📓](https://github.com/BardiaKh/Mediffusion/tree/main/tutorials/02_2d_inpainting.ipynb) |

## TO-DO

The following features and improvements are currently on our development roadmap:

- [ ] Cross-attention
- [ ] DPM-Solver
- [ ] VAE for LDM

We are actively working on these features and they will be available in future releases.

## Issues and Contributions

### Issues
If you encounter any issues while using this package, we encourage you to open an issue in the GitHub repository. Your feedback helps us to improve the software and resolve any bugs or limitations.

### Contributions
Contributions to the codebase are always welcome. If you have a feature request, bugfix, or any other contribution, feel free to submit a pull request.

### Development Opportunities
If you're interested in actively participating in the development of this package, please send us a Direct Message (DM). We're always open to collaboration and would be delighted to have you on board.

## Citation

If you find this work useful, please consider citing the parent project:

```bibtex
@article{KHOSRAVI2023107832,
    title = {Few-shot biomedical image segmentation using diffusion models: Beyond image generation},
    journal = {Computer Methods and Programs in Biomedicine},
    volume = {242},
    pages = {107832},
    year = {2023},
    issn = {0169-2607},
    doi = {https://doi.org/10.1016/j.cmpb.2023.107832},
    url = {https://www.sciencedirect.com/science/article/pii/S0169260723004984},
    author = {Bardia Khosravi and Pouria Rouzrokh and John P. Mickley and Shahriar Faghani and Kellen Mulford and Linjun Yang and A. Noelle Larson and Benjamin M. Howe and Bradley J. Erickson and Michael J. Taunton and Cody C. Wyles},
}
```
