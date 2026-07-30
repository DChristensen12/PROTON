"""this has the beta schedules for the diffusion forward process. Both returns a tensor of T betas."""

import torch
import math

def linear_betas(timesteps, start = 1e-4, end = 0.02):
    """Betas increase linearly from beginning to end"""
    return torch.linspace(start, end, timesteps, dtype = torch.float64)

def cosine_betas(timesteps, s = 0.008):
    """
    cosine schedule, which is gentler noisiing earlier in the process.
    """
    steps = torch.arange(timesteps + 1, dtype = torch.float64) / timesteps
    alphas_bar = torch.cos((steps + s) / (1 + s) * math.pi / 2)**2
    alphas_bar = alphas_bar / alphas_bar[0]
    betas = 1 - alphas_bar[1:] / alphas_bar[:-1]
    return betas.clamp(0, 0.999)