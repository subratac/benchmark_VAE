"""This module is the implementation of the VAE-GAN model
proposed in (https://arxiv.org/pdf/1512.09300.pdf).

Available samplers
-------------------

.. autosummary::
    ~pythae.samplers.NormalSampler
    ~pythae.samplers.GaussianMixtureSampler
    ~pythae.samplers.TwoStageVAESampler
    :nosignatures:

"""

from .vae_gan_model import VAEGAN
from .vae_gan_config import VAEGANConfig

__all__ = ["VAEGAN", "VAEGANConfig"]
