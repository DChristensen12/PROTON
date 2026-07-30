# conditioning.py has the timestep embeddings and classifier free guidance for the diffusion process

import math
import torch

def drop_condition(cond, drop_probability, generator = None):
    """
    This zeros out the condition per sample with the probability drop_probability.
    Returns cond unchanged when it is None or drop_probability is zero.
    """
    if cond is None or drop_probability <= 0:
        return cond
    keep = torch.rand(cond.shape[0], device = cond.device, generator = generator) >= drop_probability
    shape = (-1,) + (1,) * (cond.dim() - 1) # for broadcasting the mask over the feature dims
    return cond * keep.view(shape).to(cond.dtype)

def guided_prediction(backbone, x, t, cond, guidance_scale):
    """This is the guided noise prediction, free of classiferiers"""
    cond_pred = backbone(x, t, cond)
    if guidance_scale == 1.0 or cond is None:
        return cond_pred
    uncond_pred = backbone(x, t, torch.zeros_like(cond))
    return uncond_pred + guidance_scale * (cond_pred  - uncond_pred)

def timestep_embedding(t, dim):
    """
    Sinusoidal embedding of integer timesteps, shape [N, dim]
    The dim should be even, if not it'll get padded with one 0
    """
    half = dim // 2
    freqs = torch.exp(-math.log(10000) * torch.arange(half, dtype = torch.float32) / half).to(t.device)
    args = t.float()[:, None]* freqs[None, :]
    emb = torch.cat([torch.cos(args), torch.sin(args)], dim = -1)
    if dim % 2 == 1:
        emb = torch.nn.functional.pad(emb, (0, 1))
    return emb