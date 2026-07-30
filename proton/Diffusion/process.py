"""process.py serves as the diffusion engine. 

Specifically, one class will implement forward noising, the training loss, and both samplers.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

class Diffuse(nn.Module):
    """
    This is a Gaussian diffusion over tensors
    """
    def __init__(self, backbone, betas, cond_drop_prop = 0.0):
        super().__init__()
        self.backbone = backbone
        self.cond_drop_prob = cond_drop_prob
        betas = betas.double()
        alphas = 1.0 - betas
        alphas_bar = torch.cumprod(alphas, dim=0)
        alphas_bar_prev = F.pad(alphas_bar[:-1], (1, 0), value=1.0)
 
        # everything the samplers will need
        reg = lambda name, val: self.register_buffer(name, val.float())
        reg("betas", betas)
        reg("alphas_bar", alphas_bar)
        reg("sqrt_alphas_bar", alphas_bar.sqrt())
        reg("sqrt_one_minus_alphas_bar", (1 - alphas_bar).sqrt())
        reg("recip_sqrt_alphas", (1.0 / alphas.sqrt()))
        reg("posterior_var", betas * (1 - alphas_bar_prev) / (1 - alphas_bar))


def _gather(values, t, ndim):
    """index a schedule buffer at t and reshape for broadcasting over x"""
    output = values.gather(0, t)
    return output.view(-1, *([1] * (ndim - 1)))

